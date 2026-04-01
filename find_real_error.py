import pandas as pd
import numpy as np

# 读取余额表，只保留末级科目（科目代码长度最长的，或者没有下级的）
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
balance_df['科目代码'] = balance_df['科目代码'].astype(str).str.rstrip('.0')
# 提取科目代码长度
balance_df['代码长度'] = balance_df['科目代码'].str.len()
# 只保留最长代码的末级科目（排除父级科目）
max_len = balance_df['代码长度'].max()
final_balance = balance_df[balance_df['代码长度'] == max_len]

print("="*60)
print("📊 【只统计末级科目后的余额表核对结果】")
print("="*60)
total_debit_end = final_balance['期末余额_借方'].sum()
total_credit_end = final_balance['期末余额_贷方'].sum()
total_debit_period = final_balance['本期发生_借方'].sum()
total_credit_period = final_balance['本期发生_贷方'].sum()

print(f"期末借方余额总和: {total_debit_end:,.2f}")
print(f"期末贷方余额总和: {total_credit_end:,.2f}")
print(f"期末余额差额: {abs(total_debit_end - total_credit_end):,.2f}")
print(f"\n本期借方发生额总和: {total_debit_period:,.2f}")
print(f"本期贷方发生额总和: {total_credit_period:,.2f}")
print(f"本期发生额差额: {abs(total_debit_period - total_credit_period):,.2f}")

# 和序时账末级科目核对
voucher_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx',
    header=3
)
voucher_df.columns = [col.strip() for col in voucher_df.columns]
voucher_df['借方金额'] = pd.to_numeric(voucher_df['借方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df['贷方金额'] = pd.to_numeric(voucher_df['贷方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df['科目编号'] = voucher_df['科目编号'].astype(str).str.rstrip('.0')

# 按末级科目汇总序时账
vou_summary = voucher_df.groupby('科目编号').agg(
    借方发生额=('借方金额', 'sum'),
    贷方发生额=('贷方金额', 'sum')
).reset_index()

# 和余额表末级科目比对
compare = pd.merge(final_balance, vou_summary, left_on='科目代码', right_on='科目编号', how='outer').fillna(0)
compare['借方差异'] = compare['本期发生_借方'] - compare['借方发生额']
compare['贷方差异'] = compare['本期发生_贷方'] - compare['贷方发生额']
diff = compare[(abs(compare['借方差异'])>0.01) | (abs(compare['贷方差异'])>0.01)]

print(f"\n🔍 发现{len(diff)}个末级科目发生额不一致：")
diff = diff[['科目代码', '科目名称', '本期发生_借方', '借方发生额', '借方差异', '本期发生_贷方', '贷方发生额', '贷方差异']]
print(diff.to_string(index=False))
