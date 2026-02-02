import pandas as pd
import numpy as np

class ChanlunSimple:
    def __init__(self, data):
        """
        初始化
        :param data: pandas.DataFrame, 必须包含 'high', 'low' 列 (大小写敏感，内部会统一处理)
        """
        # 统一列名
        self.raw_data = data.copy().reset_index(drop=True)
        # 确保列名是 title case 或者符合内部逻辑
        # 假设输入是 standard akshare format: date, open, close, high, low...
        # 内部使用 Capitalized keys for the dictionary access in the logic provided
        
        # 映射列名为内部使用的格式 (High, Low, Date)
        col_map = {}
        for c in self.raw_data.columns:
            if c.lower() == 'high': col_map[c] = 'High'
            elif c.lower() == 'low': col_map[c] = 'Low'
            elif c.lower() == 'date': col_map[c] = 'Date'
        self.raw_data = self.raw_data.rename(columns=col_map)
        
        self.k_lines = []   # 存储包含处理后的K线
        self.fenxing = []   # 存储分型
        self.bi = []        # 存储笔

    def process_inclusion(self):
        """
        步骤1: 处理K线包含关系
        """
        if len(self.raw_data) < 2:
            return pd.DataFrame()

        # 转换为字典列表以提高遍历性能
        data = self.raw_data.to_dict('records')
        processed = []
        
        # 初始两根K线确定初始方向
        # direction 1: 向上, -1: 向下
        if data[1]['High'] > data[0]['High']:
            direction = 1
        else:
            direction = -1
            
        processed.append(data[0])

        for i in range(1, len(data)):
            curr = data[i].copy()
            prev = processed[-1]
            
            # 判断包含关系
            # 1. 前包后 (Prev 包含 Curr)
            prev_includes_curr = (prev['High'] >= curr['High'] and prev['Low'] <= curr['Low'])
            # 2. 后包前 (Curr 包含 Prev)
            curr_includes_prev = (curr['High'] >= prev['High'] and curr['Low'] <= prev['Low'])
            
            if prev_includes_curr or curr_includes_prev:
                # 发生包含，合并K线
                new_bar = prev.copy() # 继承时间戳等基础信息 (通常是较早的那个时间)
                
                if direction == 1: # 向上趋势：高高低高
                    new_bar['High'] = max(prev['High'], curr['High'])
                    new_bar['Low'] = max(prev['Low'], curr['Low'])
                else: # 向下趋势：低低高低
                    new_bar['High'] = min(prev['High'], curr['High'])
                    new_bar['Low'] = min(prev['Low'], curr['Low'])
                
                # 用合并后的K线替换列表最后一个元素，继续与下一根比较
                processed[-1] = new_bar
                # 方向保持不变
            else:
                # 无包含关系，直接加入
                processed.append(curr)
                
                # 更新趋势方向
                if len(processed) >= 2:
                    if processed[-1]['High'] > processed[-2]['High']:
                        direction = 1
                    elif processed[-1]['High'] < processed[-2]['High']:
                        direction = -1
        
        self.k_lines = pd.DataFrame(processed)
        return self.k_lines

    def find_fenxing(self):
        """
        步骤2: 寻找顶底分型
        """
        if len(self.k_lines) < 3:
            return []
        
        fx_list = []
        df = self.k_lines
        
        # 遍历每根K线 (跳过首尾)
        for i in range(1, len(df) - 1):
            prev = df.iloc[i-1]
            curr = df.iloc[i]
            next_bar = df.iloc[i+1]
            
            # 顶分型: 中间高点最高
            if (curr['High'] > prev['High']) and (curr['High'] > next_bar['High']):
                fx_list.append({
                    'type': 'top',
                    'index': i,         # 在包含处理后列表中的索引
                    'fx_price': curr['High'],
                    'date': curr['Date'],
                    'raw_data': curr
                })
            
            # 底分型: 中间低点最低
            elif (curr['Low'] < prev['Low']) and (curr['Low'] < next_bar['Low']):
                fx_list.append({
                    'type': 'bottom',
                    'index': i,
                    'fx_price': curr['Low'],
                    'date': curr['Date'],
                    'raw_data': curr
                })
                
        self.fenxing = fx_list
        return fx_list

    def find_bi(self):
        """
        步骤3: 简单笔识别
        规则:
        1. 顶底分型交替出现
        2. 顶底之间至少有一根独立K线 (索引差 >= 4)
        3. 顶分型高点 > 底分型低点 (对于向下笔则反之)
        """
        if not self.fenxing:
            return []
            
        bi_list = []
        
        # 寻找第一个潜在的分型起点
        start_fx = self.fenxing[0]
        
        for i in range(1, len(self.fenxing)):
            curr_fx = self.fenxing[i]
            
            # 情况1: 如果遇到同类分型 (如 顶...顶)
            if curr_fx['type'] == start_fx['type']:
                # 取极值更强的那个作为新的起点
                if start_fx['type'] == 'top':
                    if curr_fx['fx_price'] > start_fx['fx_price']:
                        start_fx = curr_fx
                else: # bottom
                    if curr_fx['fx_price'] < start_fx['fx_price']:
                        start_fx = curr_fx
            
            # 情况2: 遇到反向分型 (如 顶...底)
            else:
                # 检查成笔条件
                # 1. K线数量条件: 中间至少隔一根 (index_diff >= 4)
                # 注意：这里用的是包含处理后的K线索引
                index_diff = abs(curr_fx['index'] - start_fx['index'])
                
                # 2. 价格条件
                price_valid = False
                if start_fx['type'] == 'top': # 向下笔
                    price_valid = start_fx['fx_price'] > curr_fx['fx_price']
                else: # 向上笔
                    price_valid = start_fx['fx_price'] < curr_fx['fx_price']
                
                if index_diff >= 4 and price_valid:
                    # 确认成笔
                    bi_list.append({
                        'start_date': start_fx['date'],
                        'end_date': curr_fx['date'],
                        'start_price': start_fx['fx_price'],
                        'end_price': curr_fx['fx_price'],
                        'type': 'down' if start_fx['type'] == 'top' else 'up'
                    })
                    # 当前的结束点成为下一笔的起点
                    start_fx = curr_fx
                else:
                    # 不满足成笔条件，忽略当前分型？
                    # 这是一个简化的处理。严格来说可能需要回溯或延伸。
                    # 这里简单的丢弃不满足条件的当前分型，保留start_fx继续找下一个反向分型
                    # 但是，如果中间出现了一个更极端的同向分型怎么办？
                    # 比如 Top1 -> Bottom1 (无效) -> Top2 (比Top1高)
                    # 这里的逻辑会在下一次循环 (Top2 vs Top1) 时处理同类合并
                    # 所以这里的逻辑基本是自洽的
                    pass
                    
        self.bi = bi_list
        return bi_list
