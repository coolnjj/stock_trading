import pandas as pd
import numpy as np

# -------------------------- 科目余额表核对 --------------------------
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)

# 清理金额列
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

print("="*60)
print("📊 【科目余额表核对结果】")
print("="*60)
total_debit_end = balance_df['期末余额_借方'].sum()
total_credit_end = balance_df['期末余额_贷方'].sum()
print(f"✅ 期末借方余额总和: {total_debit_end:,.2f}")
print(f"✅ 期末贷方余额总和: {total_credit_end:,.2f}")
if abs(total_debit_end - total_credit_end) < 0.01:
    print("🎉 期末余额借贷完全平衡！")
else:
    print(f"❌ 期末余额不平衡！差额: {abs(total_debit_end - total_credit_end):,.2f}")

total_debit_period = balance_df['本期发生_借方'].sum()
total_credit_period = balance_df['本期发生_贷方'].sum()
print(f"\n✅ 本期借方发生额总和: {total_debit_period:,.2f}")
print(f"✅ 本期贷方发生额总和: {total_credit_period:,.2f}")
if abs(total_debit_period - total_credit_period) < 0.01:
    print("🎉 本期发生额借贷完全平衡！")
else:
    print(f"❌ 本期发生额不平衡！差额: {abs(total_debit_period - total_credit_period):,.2f}")

# -------------------------- 序时账分析 --------------------------
# 读取记账凭证，用第4行（索引3）做表头，数据从第5行开始
voucher_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx',
    header=3
)
# 清理列名
voucher_df.columns = [col.strip() for col in voucher_df.columns]

# 清理金额列
voucher_df['借方金额'] = pd.to_numeric(voucher_df['借方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df['贷方金额'] = pd.to_numeric(voucher_df['贷方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# 提取一级科目（科目名称中'-'前面的部分就是一级科目）
voucher_df['一级科目'] = voucher_df['科目名称'].astype(str).apply(lambda x: x.split('-')[0] if '-' in x else x)

print("\n" + "="*60)
print("📈 【收支分类汇总（按一级科目）】")
print("="*60)
summary = voucher_df.groupby('一级科目').agg(
    交易笔数=('凭证号', 'count'),
    借方总金额=('借方金额', 'sum'),
    贷方总金额=('贷方金额', 'sum')
).reset_index()
# 只显示有发生额的科目
summary = summary[(summary['借方总金额'] > 0) | (summary['贷方总金额'] > 0)]
summary['借方总金额'] = summary['借方总金额'].apply(lambda x: f"{x:,.2f}")
summary['贷方总金额'] = summary['贷方总金额'].apply(lambda x: f"{x:,.2f}")
print(summary.to_string(index=False))

print("\n" + "="*60)
print("⚠️  【大额收支预警（单笔金额≥50000元）】")
print("="*60)
threshold = 50000
large_records = voucher_df[(voucher_df['借方金额'] >= threshold) | (voucher_df['贷方金额'] >= threshold)]
if len(large_records) == 0:
    print("✅ 未发现单笔金额≥50000元的大额收支记录")
else:
    show_cols = ['制表日期', '凭证号', '一级科目', '摘要', '借方金额', '贷方金额']
    large_records = large_records[show_cols].sort_values('制表日期')
    large_records['借方金额'] = large_records['借方金额'].apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
    large_records['贷方金额'] = large_records['贷方金额'].apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
    print(f"共找到{len(large_records)}条大额记录：")
    print(large_records.to_string(index=False))

# 检查序时账借贷平衡
total_vou_debit = voucher_df['借方金额'].sum()
total_vou_credit = voucher_df['贷方金额'].sum()
print("\n" + "="*60)
print("🧐 【序时账借贷平衡校验】")
print("="*60)
print(f"序时账借方总金额: {total_vou_debit:,.2f}")
print(f"序时账贷方总金额: {total_vou_credit:,.2f}")
if abs(total_vou_debit - total_vou_credit) < 0.01:
    print("🎉 序时账借贷完全平衡！")
else:
    print(f"❌ 序时账借贷不平衡！差额: {abs(total_vou_debit - total_vou_credit):,.2f}")
