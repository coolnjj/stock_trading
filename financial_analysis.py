import pandas as pd
import numpy as np

# 读取科目余额表
balance_df = pd.read_excel('/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx')
print("="*50)
print("📊 科目余额表核对结果")
print("="*50)

# 找借方余额和贷方余额列
debit_col = [col for col in balance_df.columns if '借' in col and '余' in col][0]
credit_col = [col for col in balance_df.columns if '贷' in col and '余' in col][0]

total_debit = balance_df[debit_col].sum()
total_credit = balance_df[credit_col].sum()

print(f"借方期末余额总和: {total_debit:,.2f}")
print(f"贷方期末余额总和: {total_credit:,.2f}")
if abs(total_debit - total_credit) < 0.01:
    print("✅ 期末余额借贷平衡！")
else:
    print(f"❌ 期末余额不平！差额: {abs(total_debit - total_credit):,.2f}")

# 读取记账凭证(序时账)
voucher_df = pd.read_excel('/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx')
print("\n" + "="*50)
print("📝 序时账收支分类汇总")
print("="*50)

# 找借方金额和贷方金额列
vou_debit_col = [col for col in voucher_df.columns if '借' in col and ('金额' in col or '方' in col)][0]
vou_credit_col = [col for col in voucher_df.columns if '贷' in col and ('金额' in col or '方' in col)][0]
subject_col = [col for col in voucher_df.columns if '科目' in col or '摘要' in col][0]

# 汇总各科目借贷发生额
summary = voucher_df.groupby(subject_col).agg({
    vou_debit_col: 'sum',
    vou_credit_col: 'sum',
    vou_debit_col: 'count'
}).rename(columns={
    vou_debit_col: '笔数',
    vou_debit_col: '借方总金额',
    vou_credit_col: '贷方总金额'
}).reset_index()
summary['借方总金额'] = summary['借方总金额'].apply(lambda x: f"{x:,.2f}")
summary['贷方总金额'] = summary['贷方总金额'].apply(lambda x: f"{x:,.2f}")
print(summary.to_string(index=False))

print("\n" + "="*50)
print("⚠️  异常大额收支记录（单笔金额≥10000元）")
print("="*50)
# 找大额记录
threshold = 10000
large_debit = voucher_df[voucher_df[vou_debit_col] >= threshold]
large_credit = voucher_df[voucher_df[vou_credit_col] >= threshold]
large_records = pd.concat([large_debit, large_credit]).drop_duplicates()

if len(large_records) == 0:
    print("✅ 没有找到单笔金额≥10000元的大额收支记录")
else:
    # 输出关键列
    show_cols = [col for col in ['日期', '凭证号', subject_col, vou_debit_col, vou_credit_col, '摘要'] if col in voucher_df.columns]
    large_records = large_records[show_cols]
    large_records[vou_debit_col] = large_records[vou_debit_col].apply(lambda x: f"{x:,.2f}" if x > 0 else "")
    large_records[vou_credit_col] = large_records[vou_credit_col].apply(lambda x: f"{x:,.2f}" if x > 0 else "")
    print(large_records.to_string(index=False))
