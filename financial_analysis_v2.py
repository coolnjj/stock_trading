import pandas as pd
import numpy as np

# 读取科目余额表，跳过前3行，自定义列名
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)

# 清理金额列，把逗号去掉转成数值
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

print("="*50)
print("📊 科目余额表核对结果")
print("="*50)
total_debit_end = balance_df['期末余额_借方'].sum()
total_credit_end = balance_df['期末余额_贷方'].sum()
print(f"期末借方余额总和: {total_debit_end:,.2f}")
print(f"期末贷方余额总和: {total_credit_end:,.2f}")
if abs(total_debit_end - total_credit_end) < 0.01:
    print("✅ 期末余额借贷完全平衡！")
else:
    print(f"❌ 期末余额不平！差额: {abs(total_debit_end - total_credit_end):,.2f}")

total_debit_period = balance_df['本期发生_借方'].sum()
total_credit_period = balance_df['本期发生_贷方'].sum()
print(f"\n本期借方发生额总和: {total_debit_period:,.2f}")
print(f"本期贷方发生额总和: {total_credit_period:,.2f}")
if abs(total_debit_period - total_credit_period) < 0.01:
    print("✅ 本期发生额借贷平衡！")
else:
    print(f"❌ 本期发生额不平！差额: {abs(total_debit_period - total_credit_period):,.2f}")

# 读取记账凭证，跳过前2行，用第3行做表头
voucher_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx',
    header=2
)
# 清理列名，去掉空格
voucher_df.columns = [col.strip() for col in voucher_df.columns]
print("\n" + "="*50)
print("📝 序时账字段说明")
print("="*50)
print("可用字段：", list(voucher_df.columns))

# 找借方和贷方金额列
debit_col = [col for col in voucher_df.columns if '借' in str(col) and '金额' in str(col)][0]
credit_col = [col for col in voucher_df.columns if '贷' in str(col) and '金额' in str(col)][0]
subject_col = [col for col in voucher_df.columns if '科目' in str(col) or '名称' in str(col)][0]
summary_col = [col for col in voucher_df.columns if '摘要' in str(col)][0]

# 清理金额列
voucher_df[debit_col] = pd.to_numeric(voucher_df[debit_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df[credit_col] = pd.to_numeric(voucher_df[credit_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

print("\n" + "="*50)
print("📈 收支分类汇总（按一级科目）")
print("="*50)
# 提取一级科目（假设科目名称里空格前面是一级科目，或者取前4个字符）
voucher_df['一级科目'] = voucher_df[subject_col].astype(str).apply(lambda x: x.split()[0] if ' ' in x else x[:4])
summary = voucher_df.groupby('一级科目').agg(
    笔数=('凭证号', 'count'),
    借方总金额=(debit_col, 'sum'),
    贷方总金额=(credit_col, 'sum')
).reset_index()
summary['借方总金额'] = summary['借方总金额'].apply(lambda x: f"{x:,.2f}")
summary['贷方总金额'] = summary['贷方总金额'].apply(lambda x: f"{x:,.2f}")
print(summary.to_string(index=False))

print("\n" + "="*50)
print("⚠️  大额收支预警（单笔金额≥10000元）")
print("="*50)
threshold = 10000
large_records = voucher_df[(voucher_df[debit_col] >= threshold) | (voucher_df[credit_col] >= threshold)]
if len(large_records) == 0:
    print("✅ 未发现单笔金额≥10000元的大额收支记录")
else:
    show_cols = ['制表日期', '凭证号', '一级科目', summary_col, debit_col, credit_col]
    large_records = large_records[show_cols].sort_values('制表日期')
    large_records[debit_col] = large_records[debit_col].apply(lambda x: f"{x:,.2f}" if x > 0 else "")
    large_records[credit_col] = large_records[credit_col].apply(lambda x: f"{x:,.2f}" if x > 0 else "")
    print(f"共找到{len(large_records)}条大额记录：")
    print(large_records.to_string(index=False))
