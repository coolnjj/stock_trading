import pandas as pd
import numpy as np

# 读取余额表
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
balance_df['科目代码'] = balance_df['科目代码'].astype(str)
# 提取一级科目代码（前4位）
balance_df['一级科目代码'] = balance_df['科目代码'].str[:4]
balance_df['一级科目名称'] = balance_df['科目名称'].astype(str).apply(lambda x: x.split('-')[0] if '-' in x else x)

# 读取序时账
voucher_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年记账凭证.xlsx',
    header=3
)
voucher_df.columns = [col.strip() for col in voucher_df.columns]
voucher_df['借方金额'] = pd.to_numeric(voucher_df['借方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df['贷方金额'] = pd.to_numeric(voucher_df['贷方金额'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
voucher_df['科目编号'] = voucher_df['科目编号'].astype(str)
# 提取一级科目代码（前4位）
voucher_df['一级科目代码'] = voucher_df['科目编号'].str[:4]

print("="*70)
print("🔍 【开始查找余额表不平原因】")
print("="*70)
print("💡 序时账本身完全平衡，说明错误出现在余额表的统计环节，现在开始逐科目核对发生额：")
print("-"*70)

# 按一级科目汇总序时账的发生额
voucher_summary = voucher_df.groupby('一级科目代码').agg(
    序时账借方发生额=('借方金额', 'sum'),
    序时账贷方发生额=('贷方金额', 'sum')
).reset_index()

# 按一级科目汇总余额表的发生额
balance_summary = balance_df.groupby('一级科目代码').agg(
    余额表借方发生额=('本期发生_借方', 'sum'),
    余额表贷方发生额=('本期发生_贷方', 'sum'),
    一级科目名称=('一级科目名称', 'first')
).reset_index()

# 合并比对
compare_df = pd.merge(balance_summary, voucher_summary, on='一级科目代码', how='outer').fillna(0)
# 计算差异
compare_df['借方差异'] = compare_df['余额表借方发生额'] - compare_df['序时账借方发生额']
compare_df['贷方差异'] = compare_df['余额表贷方发生额'] - compare_df['序时账贷方发生额']
# 只保留有差异的科目
diff_df = compare_df[(abs(compare_df['借方差异']) > 0.01) | (abs(compare_df['贷方差异']) > 0.01)]

if len(diff_df) == 0:
    print("✅ 所有科目的本期发生额完全匹配！问题出现在期初余额或者期末结转环节：")
    # 校验期初余额
    total_debit_begin = balance_df['期初余额_借方'].sum()
    total_credit_begin = balance_df['期初余额_贷方'].sum()
    print(f"   期初借方余额总和: {total_debit_begin:,.2f}")
    print(f"   期初贷方余额总和: {total_credit_begin:,.2f}")
    if abs(total_debit_begin - total_credit_begin) > 0.01:
        print(f"❌ 期初余额本身就不平！差额: {abs(total_debit_begin - total_credit_begin):,.2f}")
        print("👉 原因：上一年度结转错误，或者期初余额录入错误")
    else:
        print("✅ 期初余额平衡，问题出现在期末损益结转/本年利润结转环节，请检查结转凭证")
else:
    print(f"❌ 发现{len(diff_df)}个科目的发生额不匹配！这就是余额表不平的原因：")
    print("-"*70)
    diff_df = diff_df[['一级科目代码', '一级科目名称', '余额表借方发生额', '序时账借方发生额', '借方差异', '余额表贷方发生额', '序时账贷方发生额', '贷方差异']]
    # 格式化金额
    for col in ['余额表借方发生额', '序时账借方发生额', '借方差异', '余额表贷方发生额', '序时账贷方发生额', '贷方差异']:
        diff_df[col] = diff_df[col].apply(lambda x: f"{x:,.2f}")
    print(diff_df.to_string(index=False))
    print("\n👉 原因：这些科目在余额表里的统计数和实际序时账的发生额不一致，通常是因为余额表取数时漏了凭证、或者结转凭证没有统计进去")

# 再核对余额表的勾稽关系：期初+本期发生-本期减少=期末
print("\n" + "="*70)
print("🔍 【校验科目余额表勾稽关系】")
print("="*70)
balance_df['计算期末借方'] = balance_df['期初余额_借方'] + balance_df['本期发生_借方'] - balance_df['本期发生_贷方']
balance_df['计算期末贷方'] = balance_df['期初余额_贷方'] + balance_df['本期发生_贷方'] - balance_df['本期发生_借方']
# 找勾稽关系不对的科目
balance_df['期末差异'] = np.where(
    balance_df['期末余额_借方'] > 0,
    balance_df['期末余额_借方'] - balance_df['计算期末借方'],
    balance_df['期末余额_贷方'] - balance_df['计算期末贷方']
)
wrong_balance = balance_df[abs(balance_df['期末差异']) > 0.01]
if len(wrong_balance) == 0:
    print("✅ 所有科目的期初+本期发生=期末，勾稽关系正确")
else:
    print(f"❌ 发现{len(wrong_balance)}个科目的勾稽关系错误（期初+本期发生≠期末）：")
    print(wrong_balance[['科目代码', '科目名称', '期末差异']].to_string(index=False))
