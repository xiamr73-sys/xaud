# -*- coding: utf-8 -*-
import asyncio
import pandas as pd
from loguru import logger
import ccxt
import aiohttp
from config import get_exchange, DISCORD_WEBHOOK_URL
from utils import calculate_indicators, check_squeeze, check_main_force_lurking, calculate_score, calculate_trade_params, check_obv_trend, check_trend_breakout, check_volume_surge, check_momentum_buildup, check_macd_golden_cross, check_1m_trigger

import time
import os
from db_utils import init_db, load_all_alerts, upsert_alert, delete_alert

# 配置参数
TIMEFRAME = '15m'      # 15分钟 K线，用于捕捉短线趋势和"过去10分钟"的波动
TRIGGER_TIMEFRAME = '1m' # 1分钟 K线，用于高频信号触发
LIMIT = 100            # 获取K线数量
BATCH_SIZE = 10        # 并发批次大小
TOP_N = 200            # 筛选前 N 个成交量最大的币种
SCORE_THRESHOLD = 60   # 报警分数阈值 (调整为 60)
VERIFY_DELAY = 60 * 60 # 1小时后回测验证 (秒)

# 记录活跃的验证任务，防止重复: {symbol: timestamp}
active_verifications = {}

# 记录币种的报警历史 {symbol: {'first_alert_time': timestamp, 'count': 0, 'first_price': float}}
alert_history = {}

async def send_discord_alert(content):
    """
    发送 Discord 报警
    """
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ 警告: 未配置 DISCORD_WEBHOOK_URL，无法发送报警")
        return
        
    try:
        # 打印调试信息 (Cloud Run 日志)
        # print(f"正在发送 Discord 报警... URL: {DISCORD_WEBHOOK_URL[:30]}...") 
        
        async with aiohttp.ClientSession() as session:
            payload = {"content": content}
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as response:
                if response.status != 204:
                    response_text = await response.text()
                    error_msg = f"Discord 推送失败: Status={response.status}, Response={response_text}"
                    print(f"❌ {error_msg}")
                    logger.error(error_msg)
                else:
                    # print("✅ Discord 推送成功")
                    pass
    except Exception as e:
        error_msg = f"Discord 推送异常: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)

async def verify_signal_performance(symbol, entry_price, score, signal_time_str):
    """
    延迟验证信号的表现 (回测)
    独立创建 exchange 连接，防止主程序重连导致连接失效
    """
    exchange = None
    try:
        # 等待回测周期
        await asyncio.sleep(VERIFY_DELAY)
        
        # 建立独立连接
        exchange = await get_exchange()
        
        # 获取过去 ~80 分钟的 1m K线，覆盖 60分钟 窗口
        # 注意: 这种方式是获取"当前"往前推的数据。因为我们是 sleep 后醒来，所以就是获取信号触发后的数据。
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='1m', limit=80)
        
        if not ohlcv:
            return

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 计算区间内的最高价和最低价
        # 假设 entry_price 是信号触发时的收盘价
        highest = df['high'].max()
        lowest = df['low'].min()
        current = df['close'].iloc[-1]
        
        # 计算最大涨跌幅
        max_gain = ((highest - entry_price) / entry_price) * 100
        max_loss = ((lowest - entry_price) / entry_price) * 100
        final_change = ((current - entry_price) / entry_price) * 100
        
        # 记录回测日志
        # 使用特殊的 BACKTEST 级别或直接 INFO/WARNING，这里用 INFO 并带特定前缀方便过滤
        logger.info(
            f"🧪 【信号回测】 {symbol} (Score: {score})\n"
            f"   • 触发时间: {signal_time_str}\n"
            f"   • 入场价格: {entry_price}\n"
            f"   • 1小时后现价: {current} ({final_change:+.2f}%)\n"
            f"   • 期间最高涨幅: {max_gain:+.2f}%\n"
            f"   • 期间最大回撤: {max_loss:+.2f}%"
        )
        
    except Exception as e:
        logger.error(f"回测验证失败 {symbol}: {e}")
    finally:
        # 关闭独立连接
        if exchange:
            await exchange.close()
        # 移除活跃任务标记
        if symbol in active_verifications:
            del active_verifications[symbol]

async def get_top_volume_symbols(exchange, top_n=200):
    """
    获取 24h 成交额最大的前 N 个 USDT 合约交易对
    """
    try:
        tickers = await exchange.fetch_tickers()
        # 筛选 USDT 合约
        usdt_tickers = [
            t for s, t in tickers.items() 
            if '/USDT:USDT' in s and t.get('quoteVolume') is not None
        ]
        
        # 按成交额降序排序
        sorted_tickers = sorted(usdt_tickers, key=lambda x: x['quoteVolume'], reverse=True)
        
        # 取前 N 个的 symbol
        top_symbols = [t['symbol'] for t in sorted_tickers[:top_n]]
        return top_symbols
    except Exception as e:
        logger.error(f"获取热门币种失败: {e}")
        return []

async def fetch_open_interest_history_change(exchange, symbol, timeframe=TIMEFRAME):
    """
    获取 OI 变化率 (尝试获取历史 OI)
    这里为了简化，我们尝试获取最近的 OI 历史。
    如果 fetch_open_interest_history 不可用，则可能需要自行维护状态 (暂且尝试调用)
    
    Returns:
        float: OI 变化率 (%)
    """
    try:
        # Binance 支持 fetchOpenInterestHistory
        # 获取最近 2 个周期的 OI (例如 15m 级别)
        # 注意: ccxt 的 fetch_open_interest_history 参数可能因交易所而异
        # Binance FAPI: period="15m"
        history = await exchange.fetch_open_interest_history(symbol, timeframe=timeframe, limit=2)
        
        if len(history) < 2:
            return 0.0
            
        prev_oi = float(history[-2]['openInterestAmount'])
        curr_oi = float(history[-1]['openInterestAmount'])
        
        if prev_oi == 0:
            return 0.0
            
        change_pct = ((curr_oi - prev_oi) / prev_oi) * 100
        return change_pct
        
    except Exception:
        # 如果获取历史失败，尝试仅获取当前 OI (无法计算变化率，返回0)
        return 0.0

async def fetch_funding_rate(exchange, symbol):
    """
    获取资金费率
    """
    try:
        funding = await exchange.fetch_funding_rate(symbol)
        # funding rate 通常是一个小数，如 0.0001 (0.01%)
        return funding['fundingRate']
    except Exception:
        return 0.0

async def check_btc_trend(exchange):
    """
    检查 BTC 5分钟趋势，判断是否正在急跌
    Returns:
        bool: True if BTC is dumping (crashing), False otherwise
    """
    try:
        # 获取 BTC/USDT 最近 3 根 5m K线
        ohlcv = await exchange.fetch_ohlcv('BTC/USDT:USDT', timeframe='5m', limit=3)
        if not ohlcv or len(ohlcv) < 3:
            return False
            
        # 简单判断：如果最近一根K线跌幅超过 0.5%，或者连续两根阴线且累计跌幅 > 0.8%
        close_now = ohlcv[-1][4]
        open_now = ohlcv[-1][1]
        
        close_prev = ohlcv[-2][4]
        open_prev = ohlcv[-2][1]
        
        # 当前 K 线跌幅
        drop_now = (open_now - close_now) / open_now * 100
        
        # 累计跌幅 (从前一根开盘到当前收盘)
        total_drop = (open_prev - close_now) / open_prev * 100
        
        is_dumping = False
        if drop_now > 0.5:
            is_dumping = True
        elif total_drop > 0.8:
            is_dumping = True
            
        if is_dumping:
            logger.warning(f"⚠️ BTC 正在急跌! (Drop: {drop_now:.2f}% / Total: {total_drop:.2f}%) 暂停多头报警")
            
        return is_dumping
        
    except Exception:
        return False

async def fetch_data_and_analyze(exchange, symbol, btc_dumping=False, top_10_symbols=None, is_new_top_10=False):
    """
    获取单个币种的数据并进行分析
    
    Args:
        is_new_top_10 (bool): 是否是本轮新进入 Top 10 的币种
    Returns:
        tuple: (symbol, score) or (symbol, 0) if failed
    """
    try:
        # 1. 获取 15m K线数据 (大趋势参考)
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
        if not ohlcv or len(ohlcv) < 30: # 稍微提高数据量要求以满足 MACD 计算
            return symbol, 0

        # 转换为 DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 2. 计算技术指标 (含 MACD, RSI, Slope 等新指标)
        df = calculate_indicators(df)
        latest = df.iloc[-1]
        
        # --- 3. 新增: 获取 1m 数据用于高频触发 ---
        ohlcv_1m = await exchange.fetch_ohlcv(symbol, timeframe=TRIGGER_TIMEFRAME, limit=20)
        df_1m = pd.DataFrame()
        if ohlcv_1m and len(ohlcv_1m) > 10:
            df_1m = pd.DataFrame(ohlcv_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms')

        # 4. 获取辅助数据 (OI 和 资金费率)
        # 并发获取以提高效率
        
        # 4.1 OI 变化率 (分别获取 15m 和 1m)
        # 15m OI 用于判断"主力潜伏" (Lurking)
        oi_change_pct_15m = await fetch_open_interest_history_change(exchange, symbol, timeframe=TIMEFRAME)
        
        # 1m OI 用于判断"高频异动" (Trigger)
        oi_change_pct_1m = await fetch_open_interest_history_change(exchange, symbol, timeframe=TRIGGER_TIMEFRAME)
        
        # 4.2 资金费率
        funding_rate = await fetch_funding_rate(exchange, symbol)

        # 5. 执行多维度信号判定
        
        # --- 5.1 15m 趋势判定 (Context) ---
        
        # Squeeze 状态
        is_squeeze = check_squeeze(latest)
        
        # 主力潜伏 (OI 异动) - 使用 15m 数据
        price_volatility = ((latest['high'] - latest['low']) / latest['open']) * 100
        is_obv_rising = check_obv_trend(df)
        is_lurking = check_main_force_lurking(price_volatility, oi_change_pct_15m, is_obv_rising)
        
        # 成交量流向 (Volume Flow)
        is_volume_flow = latest['volume'] > latest.get('VOL_SMA_20', 9999999999)
        
        # 趋势突破 (Breakout)
        is_breakout = check_trend_breakout(latest, df)

        # 成交量激增 (Volume Surge) - 15m
        is_vol_surge = check_volume_surge(df)
        
        # 动能积蓄 (Momentum Buildup)
        is_momentum = check_momentum_buildup(latest, df)
        
        # 新晋榜单强多头
        is_macd_golden = check_macd_golden_cross(df)
        is_new_top_bull = is_new_top_10 and is_macd_golden

        # --- 5.2 1m 触发判定 (Trigger) ---
        # 只有当 1m 出现异动时，才考虑激活"高频报警"
        is_1m_active, trigger_msg = check_1m_trigger(df_1m, oi_change_pct_1m)

        # 6. 综合评分
        score = calculate_score(
            squeeze_active=is_squeeze, 
            lurking_active=is_lurking, 
            volume_flow_active=is_volume_flow, 
            breakout_active=is_breakout,
            vol_surge_active=is_vol_surge,
            momentum_active=is_momentum,
            new_top_bull_active=is_new_top_bull
        )
        
        # 动态调整阈值
        current_threshold = 60
        
        # --- 7. 报警判定逻辑调整 ---
        # 用户要求: "大趋势参考 15min，但信号触发必须参考 1min 的量价和持仓异动"
        # 逻辑: 
        #   如果 1m 触发 (is_1m_active) 且 15m 趋势不差 (分数 > 30 或 有任意一个 15m 正向信号)，则强制报警
        #   或者，如果 15m 分数极高 (例如 > 80)，也报警 (保持原有逻辑)
        
        should_alert = False
        alert_reason = ""
        
        # 策略 A: 1m 异动主导 (高频抢跑)
        if is_1m_active:
            # 过滤: 15m 趋势不能太差 (例如不要在暴跌中去接飞刀)
            # 简单判断: 15m 分数 > 20 或者 有任意正向形态
            if score >= 20: 
                score = max(score, 75) # 强制提分，确保触发
                should_alert = True
                alert_reason = f"⚡ {trigger_msg}"
        
        # 策略 B: 15m 趋势主导 (原有逻辑)
        elif score > current_threshold:
            should_alert = True
            alert_reason = "趋势共振"
            
        # 6. 报警推送
        if should_alert:
            tags = []
            if is_new_top_bull: tags.append("👑 NEW_TOP_BULL")
            if is_vol_surge: tags.append("🔥 VOL_SURGE")
            if is_breakout: tags.append("🚀 BREAKOUT")
            if is_momentum: tags.append("⚡ MOMENTUM")
            if is_squeeze: tags.append("SQUEEZE")
            if is_lurking: tags.append("LURKING")
            if is_volume_flow: tags.append("VOL_FLOW")
            if is_1m_active: tags.append("⚡ 1M_TRIGGER") # 新增标签
            
            # 计算交易参数
            trade_params = calculate_trade_params(latest)
            
            # 格式化交易建议
            trade_msg = ""
            if trade_params:
                long_p = trade_params['long']
                short_p = trade_params['short']
                
                # BTC 趋势过滤
                if btc_dumping:
                    trade_msg = f"\n   📉 [做空建议] SL: {short_p['sl']:.4f} | TP1: {short_p['tp1']:.4f} | RR: {short_p['rr']:.2f}\n   🚫 [多头暂停] BTC 急跌保护中"
                else:
                    # 正常推送
                    funding_boost = ""
                    if funding_rate < 0:
                        funding_boost = " 🔥 [空头回补潜力]"
                        
                    obv_boost = ""
                    if is_obv_rising:
                        obv_boost = " 📈 [OBV趋势确认]"
                    
                    long_warning = " (⚠️ 盈亏比不佳，谨慎入场)" if long_p['rr'] < 1.5 else ""
                    short_warning = " (⚠️ 盈亏比不佳，谨慎入场)" if short_p['rr'] < 1.5 else ""
                    
                    trade_msg = (
                        f"\n   💰 资金费率: {funding_rate:.6f} ({funding_rate*100:.4f}%){funding_boost}\n"
                        f"   📊 能量潮: {obv_boost}\n"
                        f"   📈 [做多建议] SL: {long_p['sl']:.4f} | TP1: {long_p['tp1']:.4f} | RR: {long_p['rr']:.2f}{long_warning}\n"
                        f"   📉 [做空建议] SL: {short_p['sl']:.4f} | TP1: {short_p['tp1']:.4f} | RR: {short_p['rr']:.2f}{short_warning}"
                    )

            logger.warning(
                f"🚨 【高分报警】 {symbol} | Score: {score}\n"
                f"   • 触发: {alert_reason}\n"
                f"   • 状态: {', '.join(tags)}\n"
                f"   • 价格: {latest['close']} (Volat: {price_volatility:.2f}%)\n"
                f"   • OI变动(15m): {oi_change_pct_15m:.2f}%\n"
                f"   • OI变动(1m): {oi_change_pct_1m:.2f}%\n"
                f"   • 布林带缩口: {'YES' if is_squeeze else 'NO'}"
                f"{trade_msg}"
            )

            # 触发异步回测任务
            current_ts = time.time()
            current_price = latest['close']
            
            # --- 更新报警统计与内存清理 ---
            if symbol not in alert_history:
                alert_history[symbol] = {
                    'first_alert_time': current_ts, 
                    'count': 0,
                    'first_price': current_price
                }
                # 新增记录，写入数据库
                upsert_alert(symbol, alert_history[symbol])
            else:
                first_price = alert_history[symbol].get('first_price', current_price)
                price_drop_pct = (first_price - current_price) / first_price * 100
                
                if price_drop_pct > 15.0:
                    logger.info(f"🧹 {symbol} 价格跌破首次报警价 15% (Drop: {price_drop_pct:.2f}%)，重置报警历史")
                    alert_history[symbol] = {
                        'first_alert_time': current_ts, 
                        'count': 0,
                        'first_price': current_price
                    }
                    # 重置记录，写入数据库
                    upsert_alert(symbol, alert_history[symbol])
            
            alert_history[symbol]['count'] += 1
            # 更新计数，写入数据库
            upsert_alert(symbol, alert_history[symbol])
            
            first_time = alert_history[symbol]['first_alert_time']
            alert_count = alert_history[symbol]['count']
            
            first_time_str = (pd.to_datetime(first_time, unit='s') + pd.Timedelta(hours=8)).strftime('%H:%M')
            first_price = alert_history[symbol].get('first_price', latest['close'])
            price_change_from_first = ((latest['close'] - first_price) / first_price) * 100
            
            # 构造 Discord 消息
            discord_msg = (
                f"🚨 **高分报警** {symbol} | Score: {score}\n"
                f"**触发**: {alert_reason}\n"
                f"**价格**: {latest['close']}\n"
                f"**OI变动(1m)**: {oi_change_pct_1m:.2f}%\n"
                f"**首次报警**: {first_time_str} (第 {alert_count} 次)\n"
                f"**首报价格**: {first_price} ({price_change_from_first:+.2f}%)"
            )
            asyncio.create_task(send_discord_alert(discord_msg))

            if symbol not in active_verifications or (current_ts - active_verifications[symbol] > VERIFY_DELAY):
                active_verifications[symbol] = current_ts
                signal_time_str = pd.to_datetime(current_ts, unit='s').strftime('%Y-%m-%d %H:%M:%S')
                asyncio.create_task(
                    verify_signal_performance(symbol, latest['close'], score, signal_time_str)
                )
        
        return symbol, score

    except Exception as e:
        # logger.debug(f"处理 {symbol} 时出错: {str(e)}")
        return symbol, 0

async def main():
    """
    主程序入口
    """
    # 1. 普通日志 (Cloud Run 环境下优先输出到 stderr，如果需要文件则写到 /tmp)
    # logger.add("/tmp/monitor.log", rotation="1 day", encoding="utf-8")
    # 2. 报警专用日志 (仅记录 WARNING 及以上级别)
    logger.add("/tmp/alerts_history.log", level="WARNING", rotation="1 week", encoding="utf-8")
    
    logger.info(f"启动 Binance 合约监控程序 (Top {TOP_N} Volume, Timeframe: {TIMEFRAME})...")
    
    # 启动时加载历史数据
    global alert_history
    alert_history = load_all_alerts()

    last_top_10_set = set()

    while True:
        # 外层循环：确保程序崩溃后能自动重启
        exchange = None
        try:
            exchange = await get_exchange()
            
            # 加载市场信息
            logger.info("正在加载市场信息...")
            await exchange.load_markets()
            
            while True:
                logger.info("正在筛选热门币种...")
                symbols = await get_top_volume_symbols(exchange, TOP_N)
                
                # 识别 Top 10 币种，用于区分对待
                current_top_10 = symbols[:10] if symbols else []
                current_top_10_set = set(current_top_10)
                
                # 计算新进入 Top 10 的币种
                new_in_top_10 = current_top_10_set - last_top_10_set
                
                logger.info(f"本轮扫描 {len(symbols)} 个热门币种... 新晋Top10: {list(new_in_top_10)}")
                
                # 检查 BTC 趋势 (每轮扫描前检查一次，或者在循环内检查)
                # 为了实时性，每批次检查一次可能更好，但会增加请求
                # 权衡之下，每轮扫描前检查一次 BTC 趋势状态
                is_btc_dumping = await check_btc_trend(exchange)
                
                for i in range(0, len(symbols), BATCH_SIZE):
                    batch = symbols[i:i + BATCH_SIZE]
                    # 将 BTC 状态和 Top 10 列表传入分析函数
                    tasks = []
                    for symbol in batch:
                        is_new = symbol in new_in_top_10
                        tasks.append(fetch_data_and_analyze(exchange, symbol, is_btc_dumping, current_top_10, is_new))
                        
                    results = await asyncio.gather(*tasks)
                    
                    # 收集并打印当前批次的最高分，确认程序在工作
                    valid_results = [r for r in results if r and r[1] > 0]
                    if valid_results:
                        max_score_symbol, max_score = max(valid_results, key=lambda x: x[1])
                        # 仅当分数较低时才作为 DEBUG/INFO 打印，避免刷屏
                        # 如果 > 0 但 < THRESHOLD，说明有计算但未触发
                        logger.info(f"批次进度: {i+len(batch)}/{len(symbols)} | 本批次最高分: {max_score} ({max_score_symbol})")
                    else:
                        logger.info(f"批次进度: {i+len(batch)}/{len(symbols)} | 本批次无有效评分")

                    # 批次间增加限频延迟
                    await asyncio.sleep(0.1) 
                
                # 更新 Top 10 记录
                last_top_10_set = current_top_10_set
                
                logger.info("扫描结束，等待 60 秒...")
                await asyncio.sleep(60)

        except KeyboardInterrupt:
            logger.info("程序已手动停止")
            break # 退出外层循环
        except Exception as e:
            logger.exception(f"主程序发生异常，10秒后尝试自动重启: {e}")
            await asyncio.sleep(10) # 冷却时间
        finally:
            if exchange:
                await exchange.close()
                logger.info("交易所连接已关闭 (重启或退出)")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
