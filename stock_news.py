import akshare as ak
import pandas as pd
import datetime

def get_hot_news():
    print("正在获取今日热点新闻...")
    try:
        # 使用 stock_news_em (东方财富个股新闻，这里用 symbol='300059' 测试，或者找一个宏观的)
        # 实际上 akshare 没有直接的"全市场热点新闻"统一接口，但可以用 stock_news_em 获取
        # 或者使用 news_cctv 获取新闻联播
        
        print("尝试获取 CCTV 新闻联播文字稿 (宏观情绪)...")
        cctv_df = ak.news_cctv(date=datetime.datetime.now().strftime("%Y%m%d"))
        if not cctv_df.empty:
            print(cctv_df[['title', 'content']].head())
            
        print("\n尝试获取个股新闻 (示例: 贵州茅台)...")
        news_df = ak.stock_news_em(symbol="600519")
        
        # 简单筛选关键词
        keywords = ["上涨", "拉升", "涨停", "利好", "突破", "暴涨", "资金", "买入", "增长"]
        
        print("\n====== 情绪监控: 关键词扫描 ======")
        count = 0
        for index, row in news_df.iterrows():
            title = row.get('title', '')
            content = row.get('content', '')
            time = row.get('public_time', '')
            
            full_text = f"{title} {content}"
            
            # 简单的关键词匹配
            if any(k in full_text for k in keywords):
                print(f"[{time}] {title}")
                count += 1
                if count >= 10: break # 只显示前 10 条
                
        if count == 0:
            print("未找到包含特定关键词的重磅新闻。")
            
    except Exception as e:
        print(f"获取新闻失败: {e}")
        # 备用：尝试获取个股新闻 (例如上证指数)
        try:
            print("尝试获取市场总貌...")
            df = ak.stock_zh_a_spot_em()
            up_count = len(df[df['涨跌幅'] > 0])
            down_count = len(df[df['涨跌幅'] < 0])
            print(f"当前市场情绪: 上涨家数 {up_count}, 下跌家数 {down_count}")
        except:
            pass

if __name__ == "__main__":
    get_hot_news()
