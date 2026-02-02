import akshare as ak
import pandas as pd
import datetime
from tqdm import tqdm
import os
import strategies

def get_sector_stocks(sector_name):
    """
    获取指定板块的股票列表
    """
    print(f"正在查找板块 [{sector_name}] ...")
    try:
        # 1. 获取所有新浪行业板块
        sectors = ak.stock_sector_spot(indicator="新浪行业")
        
        # 2. 模糊匹配板块名称
        matched_sectors = sectors[sectors['板块'].str.contains(sector_name)]
        
        if matched_sectors.empty:
            print(f"未找到名称包含 '{sector_name}' 的板块。")
            print("可用板块示例:", sectors['板块'].head(10).tolist())
            return None
            
        # 默认取第一个匹配的板块
        target_sector = matched_sectors.iloc[0]
        sector_label = target_sector['label']
        sector_real_name = target_sector['板块']
        print(f"匹配到板块: {sector_real_name} (代码: {sector_label})")
        
        # 3. 获取板块成分股
        print(f"正在获取 [{sector_real_name}] 成分股...")
        details = ak.stock_sector_detail(sector=sector_label)
        
        if details.empty:
            print("该板块没有成分股数据。")
            return None
            
        # 转换列名以匹配 scan_stocks 的预期格式 (需要 'code' 和 'name' 列)
        stock_list = details[['code', 'name']]
        return stock_list
        
    except Exception as e:
        print(f"获取板块数据失败: {e}")
        return None

def scan_stocks(sector=None):
    stock_list = None
    
    if sector:
        stock_list = get_sector_stocks(sector)
        if stock_list is None:
            return
    else:
        print("正在获取全量 A 股列表...")
        try:
            # 获取所有 A 股代码和名称
            stock_list = ak.stock_info_a_code_name()
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return

    print(f"共获取到 {len(stock_list)} 只股票，开始筛选...")
    
    results = []
    
    # 为了演示和节省时间，可以限制数量，例如只扫描前 50 个
    # 如果需要全量扫描，请注释掉下面这行切片
    # stock_list = stock_list.head(50) 
    
    for index, row in tqdm(stock_list.iterrows(), total=stock_list.shape[0]):
        symbol = row['code']
        name = row['name']
        
        try:
            # 获取日线数据
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            
            if df.empty or len(df) < 60: # 增加最小数据量要求
                continue
            
            # 整理列名
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
            
            # 计算均线
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma60'] = df['close'].rolling(window=60).mean()
            
            # 计算 KDJ
            df = strategies.calculate_kdj(df)
            
            latest = df.iloc[-1]
            
            matched_patterns = []

            # 策略 1: 综合策略
            if strategies.check_comprehensive_strategy(df):
                matched_patterns.append("综合策略")
            
            # 策略 2: 老鸭头
            if strategies.check_old_duck_head(df):
                matched_patterns.append("老鸭头")
                
            # 策略 3: 平台突破
            if strategies.check_platform_breakout(df):
                matched_patterns.append("平台突破")
                
            # 策略 4: 龙回头
            if strategies.check_dragon_turns_head(df):
                matched_patterns.append("龙回头")
            
            # 只要满足任意一种模式，就记录
            if matched_patterns:
                results.append({
                    '股票代码': symbol,
                    '股票名称': name,
                    '最新价格': latest['close'],
                    '日期': latest['date'],
                    '匹配模式': ", ".join(matched_patterns)
                })
                
        except Exception as e:
            continue

    # 输出结果
    if results:
        df_result = pd.DataFrame(results)
        filename = f"stock_scan_result_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df_result.to_excel(filename, index=False)
        print(f"\n扫描完成！共找到 {len(results)} 只符合条件的股票。")
        print(f"结果已保存至: {filename}")
    else:
        print("\n扫描完成，未找到符合条件的股票。")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="A股 K线扫描程序")
    parser.add_argument("--sector", type=str, help="指定扫描的板块名称 (例如 '玻璃', '半导体')，不指定则全量扫描")
    parser.add_argument("--list-sectors", action="store_true", help="列出所有可用板块")
    
    args = parser.parse_args()
    
    if args.list_sectors:
        try:
            sectors = ak.stock_sector_spot(indicator="新浪行业")
            print("可用板块列表:")
            print(sectors['板块'].tolist())
        except Exception as e:
            print(f"获取板块列表失败: {e}")
    else:
        scan_stocks(sector=args.sector)
