from pytdx.hq import TdxHq_API
from pytdx.params import TDXParams

# 连接通达信行情服务器（默认用华泰的免费节点）
api = TdxHq_API()
if api.connect('114.80.80.88', 7709):
    # 获取北部湾港（000582，深市，市场代码0）实时行情
    stock_data = api.get_security_quotes([(0, '000582')])
    if stock_data:
        data = stock_data[0]
        print("=== 北部湾港(000582) 实时行情 ===")
        print(f"当前价格: {data['price']:.2f}元")
        print(f"涨跌幅: {data['price']/data['last_close']*100-100:.2f}%")
        print(f"今开: {data['open']:.2f} 最高: {data['high']:.2f} 最低: {data['low']:.2f}")
        print(f"成交量: {data['vol']/10000:.2f}万手 成交额: {data['amount']/10000:.2f}万元")
        print("\n=== 连接成功！实时行情对接完成 ===")
    else:
        print("获取行情失败，请更换服务器节点")
    api.disconnect()
else:
    print("连接服务器失败，请更换节点")
