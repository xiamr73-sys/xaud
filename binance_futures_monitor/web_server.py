# -*- coding: utf-8 -*-
import asyncio
import os
from aiohttp import web
import aiohttp_jinja2
import jinja2

# 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
LOG_FILE = "monitor.log"
ALERTS_FILE = "alerts_history.log"

def read_last_lines(file_path, n=50):
    """读取文件最后 n 行"""
    if not os.path.exists(file_path):
        return []
    
    try:
        # 简单粗暴的读取方式，对于小日志文件没问题
        # 生产环境建议使用 seek 倒序读取
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-n:]]
    except Exception:
        return []

def parse_alerts(file_path, n=20):
    """
    解析报警日志
    loguru 的格式通常是:
    2023-10-27 10:00:00.123 | WARNING  | module:func:line - 🚨 ...
    我们需要提取时间和内容
    """
    if not os.path.exists(file_path):
        return [], {}

    alerts = []
    symbol_stats = {} # 统计每个币种的出现次数 {symbol: {'count': 0, 'first_time': '...'}}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 报警日志通常是多行的，以 "🚨" 开头或者 loguru 的头开头
            # 这里我们简单按 loguru 的一条日志可能跨多行来处理
            # 为了简化，我们假设每次写入都是一个完整的块，包含换行
            
            # 策略：按 "202" (年份开头) 分割，或者直接倒序读取原始文本
            # 更好的方法：monitor.py 写入时是一次 logger.warning 写入多行
            # loguru 会把多行消息作为一条记录处理，但在文件中表现为文本
            
            # 我们按 " | WARNING  | " 分割可能比较靠谱，或者按日期时间
            # 简单实现：将文件内容按 "202" 开头的行进行分组
            
            lines = content.split('\n')
            current_alert = {}
            buffer = []
            
            for line in lines:
                if " | WARNING  | " in line:
                    # 保存上一条
                    if current_alert:
                        current_alert['content'] = "\n".join(buffer)
                        alerts.append(current_alert)
                        # 统计逻辑 (针对上一条)
                        process_alert_stats(current_alert, symbol_stats)
                    
                    # 开始新的一条
                    parts = line.split(" | WARNING  | ")
                    time_part = parts[0].split(" | ")[0] # 提取时间
                    msg_start = parts[-1] if len(parts) > 1 else ""
                    
                    current_alert = {'time': time_part}
                    buffer = [msg_start]
                else:
                    if buffer:
                        buffer.append(line)
            
            # 保存最后一条
            if current_alert and buffer:
                current_alert['content'] = "\n".join(buffer)
                alerts.append(current_alert)
                process_alert_stats(current_alert, symbol_stats)
                
    except Exception as e:
        print(f"解析报警日志出错: {e}")
        return [], {}

    # 返回最近的 n 条 和 完整的统计信息
    return alerts[-n:], symbol_stats

import re
def process_alert_stats(alert, stats):
    """
    处理单条报警，更新统计信息
    """
    content = alert.get('content', '')
    if "【高分报警】" not in content:
        return

    # 提取币种名称
    # 尝试匹配 "🚨 【高分报警】 SYMBOL |"
    # 或者之前的正则 /【高分报警】\s+([A-Z0-9\/:]+)/
    # 为了兼容各种怪异名字，使用更宽泛的正则
    match = re.search(r"【高分报警】\s+(.+?)\s+\|", content)
    if match:
        symbol = match.group(1).strip()
        if symbol not in stats:
            stats[symbol] = {'count': 0, 'first_time': alert['time']}
        
        stats[symbol]['count'] += 1

async def index(request):
    """渲染主页"""
    # 读取 index.html 内容并返回
    # 由于我们用了 aiohttp_jinja2，也可以用 template 渲染
    # 这里直接读取静态文件返回，或者使用 jinja2
    return aiohttp_jinja2.render_template('index.html', request, {})

def parse_backtests(file_path, n=20):
    """
    解析回测日志 (monitor.log 中以 🧪 开头的日志)
    """
    if not os.path.exists(file_path):
        return []

    backtests = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 简单解析，回测日志通常是一次性打印多行，但在 loguru 中也是多行文本
            # 格式: ... | INFO | 🧪 【信号回测】 ...
            
            # 策略：找到包含 "🧪 【信号回测】" 的行，并向下读取直到遇到下一个日志头或结束
            # 但 loguru 的多行日志在文件中就是连续的行
            
            i = 0
            while i < len(lines):
                line = lines[i]
                if "🧪 【信号回测】" in line:
                    # 提取时间
                    time_part = line.split(" | ")[0]
                    # 提取内容 (包含当前行和后续缩进行)
                    content_buffer = [line.split("🧪")[-1].strip()] # 标题行
                    
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        # 如果是新的一条日志（有时间戳开头），则结束
                        # 简单判断：如果行首是数字年份 202x，则是新日志
                        if next_line.startswith("202") and " | " in next_line:
                            break
                        content_buffer.append(next_line.strip())
                        j += 1
                    
                    backtests.append({
                        'time': time_part,
                        'content': "\n".join(content_buffer)
                    })
                    i = j - 1
                i += 1
                
    except Exception as e:
        print(f"解析回测日志出错: {e}")
        return []

    return backtests[-n:]

async def get_data(request):
    """API: 获取日志和报警数据"""
    logs = read_last_lines(LOG_FILE, n=50)
    alerts, stats = parse_alerts(ALERTS_FILE, n=20) # 获取最近 20 条报警，但在 parse_alerts 内部统计了所有
    backtests = parse_backtests(LOG_FILE, n=10) # 获取最近 10 条回测
    
    return web.json_response({
        'logs': logs,
        'alerts': alerts,
        'stats': stats, # 新增统计字段
        'backtests': backtests
    })

async def clear_alerts(request):
    """API: 清除报警日志"""
    try:
        # 清空文件内容
        open(ALERTS_FILE, 'w').close()
        return web.json_response({'status': 'ok', 'message': '报警日志已清空'})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def init_app():
    app = web.Application()
    
    # 设置模板引擎
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(TEMPLATES_DIR))
    
    # 路由
    app.router.add_get('/', index)
    app.router.add_get('/api/data', get_data)
    app.router.add_post('/api/clear_alerts', clear_alerts) # 新增清除接口
    
    return app

if __name__ == '__main__':
    # 运行 Web 服务器
    # 获取端口 (适配云环境，默认使用 5001)
    port = int(os.environ.get('PORT', 5001))
    print(f"启动 Web 看板: http://0.0.0.0:{port}", flush=True)
    web.run_app(init_app(), host='0.0.0.0', port=port)
