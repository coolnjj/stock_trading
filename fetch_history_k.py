import requests
import re
import pandas as pd
from datetime import datetime, timedelta

# 新浪历史K线接口，获取最近30个交易日数据
def get_history_k(code, days=30):
    if code.startswith('6'):
        full_code = f'sh{code}'
    else:
        full_code = f'sz{code}'
    # 接口返回最近30天日K数据
    url = f'https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData?symbol={full_code}&scale=240&datalen={days}'
    headers = {'Referer': 'https://finance.sina.com.cn'}
    res = requests.get(url, headers=headers)
    data = re.findall('\[(.*?)\]', res.text)
    k_data = []
    for item in data:
        items = item.replace('"','').split(',')
        if len(items) >= 6:
            date = items[0]
            open_p = float(items[1])
            high = float(items[2])
            low = float(items[3])
            close = float(items[4])
            vol = float(items[5])
            amplitude = (high - low)/low*100
            k_data.append({
                'date': date,
                'open': open_p,
                'high': high,
                'low': low,
                'close': close,
                'vol': vol,
                'amplitude': round(amplitude, 2)
            })
    df = pd.DataFrame(k_data)
    return df

if __name__ == '__main__':
    # 拉取北部湾港和交运股份近30天数据
    bbg = get_history_k('000582', 30)
    jy = get_history_k('600676', 30)
    
    print("=== 北部湾港(000582) 近30日数据统计 ===")
    print(f"平均日内振幅: {bbg['amplitude'].mean():.2f}%")
    print(f"最大振幅: {bbg['amplitude'].max():.2f}% 最小振幅: {bbg['amplitude'].min():.2f}%")
    print(f"平均波动区间: {(bbg['high'] - bbg['low']).mean():.2f}元")
    print(f"近30日涨跌幅: {(bbg.iloc[-1]['close']/bbg.iloc[0]['close']*100-100):.2f}%\n")
    
    print("=== 交运股份(600676) 近30日数据统计 ===")
    print(f"平均日内振幅: {jy['amplitude'].mean():.2f}%")
    print(f"最大振幅: {jy['amplitude'].max():.2f}% 最小振幅: {jy['amplitude'].min():.2f}%")
    print(f"平均波动区间: {(jy['high'] - jy['low']).mean():.2f}元")
    print(f"近30日涨跌幅: {(jy.iloc[-1]['close']/jy.iloc[0]['close']*100-100):.2f}%\n")
    
    # 保存数据到CSV
    bbg.to_csv('/home/wenkun/.openclaw/workspace/bbg_history.csv', index=False)
    jy.to_csv('/home/wenkun/.openclaw/workspace/jy_history.csv', index=False)
    print("历史数据已保存到CSV文件，接下来生成做T策略~")
