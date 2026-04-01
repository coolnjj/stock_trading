import requests
import re

# 新浪免费实时行情接口，支持A股实时数据，延迟<1分钟
def get_stock_price(code):
    # 深市代码前缀sz，沪市sh
    if code.startswith('6'):
        full_code = f'sh{code}'
    else:
        full_code = f'sz{code}'
    url = f'https://hq.sinajs.cn/list={full_code}'
    headers = {'Referer': 'https://finance.sina.com.cn'}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = re.findall('"([^"]+)"', res.text)[0].split(',')
        if len(data) > 3:
            name = data[0]
            open_price = float(data[1])
            last_close = float(data[2])
            current = float(data[3])
            high = float(data[4])
            low = float(data[5])
            vol = float(data[8])/100
            amount = float(data[9])/10000
            change = current - last_close
            change_pct = change/last_close*100
            print(f"=== {name}({code}) 实时行情（新浪数据源） ===")
            print(f"当前价格: {current:.2f}元")
            print(f"涨跌幅: {change_pct:.2f}% ({change:+.2f}元)")
            print(f"今开: {open_price:.2f} 最高: {high:.2f} 最低: {low:.2f}")
            print(f"成交量: {vol:.2f}万手 成交额: {amount:.2f}万元")
            print("\n✅ 新浪实时行情对接成功！")
            return True
    print("❌ 获取行情失败")
    return False

if __name__ == '__main__':
    get_stock_price('600676')
