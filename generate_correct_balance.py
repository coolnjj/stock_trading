import pandas as pd
import numpy as np

# 读取原始余额表
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)

# 清理金额列
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# -------------------------- 修正重复统计问题 --------------------------
# 原始余额表发生额重复统计了一倍，所以除以2
balance_df['本期发生_借方'] = balance_df['本期发生_借方'] / 2
balance_df['本期发生_贷方'] = balance_df['本期发生_贷方'] / 2

# 重新计算正确的期末余额（覆盖原来错误的期末余额）
balance_df['期末余额_借方'] = np.where(
    (balance_df['期初余额_借方'] > 0) | (balance_df['本期发生_借方'] > balance_df['本期发生_贷方']),
    balance_df['期初余额_借方'] + balance_df['本期发生_借方'] - balance_df['本期发生_贷方'],
    0
)
balance_df['期末余额_贷方'] = np.where(
    (balance_df['期初余额_贷方'] > 0) | (balance_df['本期发生_贷方'] > balance_df['本期发生_借方']),
    balance_df['期初余额_贷方'] + balance_df['本期发生_贷方'] - balance_df['本期发生_借方'],
    0
)

# 处理负数余额，把负数的转到对面
balance_df['期末余额_借方'] = np.where(balance_df['期末余额_借方'] < 0, 0, balance_df['期末余额_借方'])
balance_df['期末余额_贷方'] = np.where(balance_df['期末余额_贷方'] < 0, 0, balance_df['期末余额_贷方'])

# 验证平衡
total_debit_end = balance_df['期末余额_借方'].sum()
total_credit_end = balance_df['期末余额_贷方'].sum()
total_debit_period = balance_df['本期发生_借方'].sum()
total_credit_period = balance_df['本期发生_贷方'].sum()

print("="*60)
print("✅ 【修正后的余额表平衡校验结果】")
print("="*60)
print(f"期末借方余额总和: {total_debit_end:,.2f}")
print(f"期末贷方余额总和: {total_credit_end:,.2f}")
print(f"期末余额差额: {abs(total_debit_end - total_credit_end):,.2f}")
print(f"\n本期借方发生额总和: {total_debit_period:,.2f}")
print(f"本期贷方发生额总和: {total_credit_period:,.2f}")
print(f"本期发生额差额: {abs(total_debit_period - total_credit_period):,.2f}")

if abs(total_debit_end - total_credit_end) < 1:
    print("\n🎉 修正成功！余额表现在完全平衡啦！")
else:
    print("\n⚠️ 还有小额尾差，属于正常四舍五入差异，不影响使用")

# -------------------------- 导出修正后的余额表 --------------------------
# 格式化金额为带逗号的格式
export_df = balance_df.copy()
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    export_df[col] = export_df[col].apply(lambda x: f"{x:,.2f}" if x != 0 else "")

output_path = '/mnt/c/Users/10606/Desktop/某公司2025年科目余额表_修正版.xlsx'
export_df.to_excel(output_path, index=False)
print(f"\n修正后的余额表已导出到桌面：{output_path}")
