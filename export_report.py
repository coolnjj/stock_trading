import pandas as pd
import numpy as np

# -------------------------- 读取数据 --------------------------
# 科目余额表
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# 记账凭证
voucher_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx',
    header=3
)
voucher_df.columns = [col.strip() for col in voucher_df.columns]
voucher_df['借方金额'] = pd.to_numeric(voucher_df['借方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df['贷方金额'] = pd.to_numeric(voucher_df['贷方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df['一级科目'] = voucher_df['科目名称'].astype(str).apply(lambda x: x.split('-')[0] if '-' in x else x)

# -------------------------- 生成分析数据 --------------------------
# 1. 余额表核对结果
balance_check = pd.DataFrame({
    '项目': ['期末借方余额总和', '期末贷方余额总和', '期末余额差额', '本期借方发生额总和', '本期贷方发生额总和', '本期发生额差额', '是否平衡'],
    '金额/结果': [
        balance_df['期末余额_借方'].sum(),
        balance_df['期末余额_贷方'].sum(),
        abs(balance_df['期末余额_借方'].sum() - balance_df['期末余额_贷方'].sum()),
        balance_df['本期发生_借方'].sum(),
        balance_df['本期发生_贷方'].sum(),
        abs(balance_df['本期发生_借方'].sum() - balance_df['本期发生_贷方'].sum()),
        '不平衡' if abs(balance_df['期末余额_借方'].sum() - balance_df['期末余额_贷方'].sum()) > 0.01 else '平衡'
    ]
})

# 2. 收支分类汇总
summary = voucher_df.groupby('一级科目').agg(
    交易笔数=('凭证号', 'count'),
    借方总金额=('借方金额', 'sum'),
    贷方总金额=('贷方金额', 'sum')
).reset_index()
summary = summary[(summary['借方总金额'] > 0) | (summary['贷方总金额'] > 0)]

# 3. 大额收支记录
threshold = 50000
large_records = voucher_df[(voucher_df['借方金额'] >= threshold) | (voucher_df['贷方金额'] >= threshold)]
large_records = large_records[['制表日期', '凭证号', '一级科目', '摘要', '借方金额', '贷方金额']].sort_values('制表日期')

# 4. 序时账平衡校验
voucher_check = pd.DataFrame({
    '项目': ['序时账借方总金额', '序时账贷方总金额', '差额', '是否平衡'],
    '金额/结果': [
        voucher_df['借方金额'].sum(),
        voucher_df['贷方金额'].sum(),
        abs(voucher_df['借方金额'].sum() - voucher_df['贷方金额'].sum()),
        '平衡' if abs(voucher_df['借方金额'].sum() - voucher_df['贷方金额'].sum()) < 0.01 else '不平衡'
    ]
})

# -------------------------- 导出到Excel --------------------------
output_path = '/mnt/c/Users/10606/Desktop/某公司2025年财务分析报告.xlsx'
with pd.ExcelWriter(output_path) as writer:
    balance_check.to_excel(writer, sheet_name='余额表核对', index=False)
    summary.to_excel(writer, sheet_name='收支分类汇总', index=False)
    large_records.to_excel(writer, sheet_name='大额收支明细', index=False)
    voucher_check.to_excel(writer, sheet_name='序时账平衡校验', index=False)
    balance_df.to_excel(writer, sheet_name='原始科目余额表', index=False)

print(f"报告已成功导出到桌面：{output_path}")
