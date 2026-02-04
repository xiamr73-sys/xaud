import sqlite3
import os
from loguru import logger

DB_FILE = "monitor_data.db"

def init_db():
    """初始化数据库"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # 创建 alerts 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                symbol TEXT PRIMARY KEY,
                first_alert_time REAL,
                alert_count INTEGER,
                first_price REAL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"数据库已初始化: {DB_FILE}")
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")

def load_all_alerts():
    """加载所有报警历史到内存字典"""
    alerts = {}
    try:
        if not os.path.exists(DB_FILE):
            return alerts
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT symbol, first_alert_time, alert_count, first_price FROM alerts')
        rows = cursor.fetchall()
        
        for row in rows:
            symbol, first_time, count, first_price = row
            alerts[symbol] = {
                'first_alert_time': first_time,
                'count': count,
                'first_price': first_price
            }
        
        conn.close()
        logger.info(f"从数据库加载了 {len(alerts)} 条报警记录")
    except Exception as e:
        logger.error(f"加载数据库数据失败: {e}")
        
    return alerts

def upsert_alert(symbol, data):
    """更新或插入单条报警记录"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (symbol, first_alert_time, alert_count, first_price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                first_alert_time=excluded.first_alert_time,
                alert_count=excluded.alert_count,
                first_price=excluded.first_price
        ''', (symbol, data['first_alert_time'], data['count'], data['first_price']))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"写入数据库失败 ({symbol}): {e}")

def delete_alert(symbol):
    """删除单条报警记录"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM alerts WHERE symbol = ?', (symbol,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"删除数据库记录失败 ({symbol}): {e}")

def clear_all_alerts():
    """清空所有记录"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM alerts')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"清空数据库失败: {e}")
