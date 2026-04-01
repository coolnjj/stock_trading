import pandas as pd

# 读取科目余额表，正确识别一级科目
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
balance_df['科目代码'] = balance_df['科目代码'].astype(str).str.rstrip('.0')
# 一级科目是代码长度为4的
level1_balance = balance_df[balance_df['科目代码'].str.len() == 4].copy()

print("正确的一级科目余额：")
print(level1_balance[['科目代码', '科目名称', '期末余额_借方', '期末余额_贷方']].to_string(index=False))
print(f"\n期末借方合计：{level1_balance['期末余额_借方'].sum():,.2f}")
print(f"期末贷方合计：{level1_balance['期末余额_贷方'].sum():,.2f}")
