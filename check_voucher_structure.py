import pandas as pd

# 不设置header，看原始数据
voucher_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx',
    header=None,
    skiprows=0
)
print("记账凭证前10行原始数据：")
for i in range(10):
    print(f"行{i}: {list(voucher_df.iloc[i].values)}")
