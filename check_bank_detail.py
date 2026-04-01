import pandas as pd

# 读取余额表，看银行存款的具体行
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# 找银行存款相关科目
bank_df = balance_df[balance_df['科目名称'].str.contains('银行', na=False)]
print("余额表中银行存款明细：")
print(bank_df)
print(f"\n余额表银行存款借方发生额合计：{bank_df['本期发生_借方'].sum():,.2f}")
print(f"余额表银行存款贷方发生额合计：{bank_df['本期发生_贷方'].sum():,.2f}")

# 核对序时账的银行存款发生额
voucher_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx',
    header=3
)
voucher_df.columns = [col.strip() for col in voucher_df.columns]
voucher_df['借方金额'] = pd.to_numeric(voucher_df['借方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df['贷方金额'] = pd.to_numeric(voucher_df['贷方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

bank_vou = voucher_df[voucher_df['科目名称'].str.contains('银行', na=False)]
print(f"\n序时账银行存款借方发生额合计：{bank_vou['借方金额'].sum():,.2f}")
print(f"序时账银行存款贷方发生额合计：{bank_vou['贷方金额'].sum():,.2f}")
