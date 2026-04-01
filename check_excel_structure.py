import pandas as pd

# 先看余额表结构
balance_df = pd.read_excel('/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx')
print("科目余额表列名：", list(balance_df.columns))
print("\n前5行数据：")
print(balance_df.head())

# 再看序时账结构
voucher_df = pd.read_excel('/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx')
print("\n" + "="*50)
print("记账凭证列名：", list(voucher_df.columns))
print("\n前5行数据：")
print(voucher_df.head())
