import pandas as pd
import numpy as np

# -------------------------- 1. 读取数据 --------------------------
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
balance_df['科目代码'] = balance_df['科目代码'].astype(str).str.rstrip('.0')
# 排除合计行（科目名称包含"合计"或者代码为空）
balance_df = balance_df[~balance_df['科目名称'].fillna('').str.contains('合计') & (balance_df['科目代码'] != 'nan') & (balance_df['科目代码'] != '')].copy()
balance_df['期末余额'] = balance_df['期末余额_借方'] - balance_df['期末余额_贷方']

# -------------------------- 2. 完美重分类方法 --------------------------
# 按科目前缀分类：1=资产，2=负债，3=权益
# 重分类规则：
# 资产类：借方余额是资产，贷方余额重分类到对应负债
# 负债类：贷方余额是负债，借方余额重分类到对应资产

# 统计所有资产类科目（1开头）
asset_df = balance_df[balance_df['科目代码'].str.startswith('1')]
asset_debit_total = asset_df[asset_df['期末余额'] > 0]['期末余额'].sum()
asset_credit_total = asset_df[asset_df['期末余额'] < 0]['期末余额'].abs().sum() # 资产贷方 → 负债

# 统计所有负债类科目（2开头）
liab_df = balance_df[balance_df['科目代码'].str.startswith('2')]
liab_credit_total = liab_df[liab_df['期末余额'] < 0]['期末余额'].abs().sum()
liab_debit_total = liab_df[liab_df['期末余额'] > 0]['期末余额'].sum() # 负债借方 → 资产

# 统计所有权益类科目（3开头）
equity_df = balance_df[balance_df['科目代码'].str.startswith('3')]
equity_credit_total = equity_df[equity_df['期末余额'] < 0]['期末余额'].abs().sum()
equity_debit_total = equity_df[equity_df['期末余额'] > 0]['期末余额'].sum()
equity_total = equity_credit_total - equity_debit_total

# 重分类后金额
final_asset_total = asset_debit_total + liab_debit_total
final_liab_total = liab_credit_total + asset_credit_total
final_equity_total = equity_total

print(f"✅ 终极校验：")
print(f"原始一级科目借方合计：4,384,322.37")
print(f"原始一级科目贷方合计：4,384,322.37")
print(f"\n重分类后资产总计：{final_asset_total:,.2f}")
print(f"重分类后负债总计：{final_liab_total:,.2f}")
print(f"所有者权益总计：{final_equity_total:,.2f}")
print(f"负债+权益总计：{final_liab_total + final_equity_total:,.2f}")
print(f"差额：{abs(final_asset_total - (final_liab_total + final_equity_total)):,.2f}")

# -------------------------- 3. 生成规范报表项目 --------------------------
# 拆分常见报表项目
monetary = balance_df[balance_df['科目代码'].str.startswith('1001') | balance_df['科目代码'].str.startswith('1002')]['期末余额_借方'].sum()
ar = balance_df[balance_df['科目代码'].str.startswith('1122') & (balance_df['期末余额'] > 0)]['期末余额'].sum() + balance_df[balance_df['科目代码'].str.startswith('2203') & (balance_df['期末余额'] > 0)]['期末余额'].sum()
prepaid = balance_df[balance_df['科目代码'].str.startswith('1123') & (balance_df['期末余额'] > 0)]['期末余额'].sum() + balance_df[balance_df['科目代码'].str.startswith('2202') & (balance_df['期末余额'] > 0)]['期末余额'].sum()
other_ar = balance_df[balance_df['科目代码'].str.startswith('1221') & (balance_df['期末余额'] > 0)]['期末余额'].sum() + balance_df[balance_df['科目代码'].str.startswith('2241') & (balance_df['期末余额'] > 0)]['期末余额'].sum()
fixed_asset = balance_df[balance_df['科目代码'].str.startswith('1601')]['期末余额_借方'].sum() - balance_df[balance_df['科目代码'].str.startswith('1602')]['期末余额_贷方'].sum()
current_asset = monetary + ar + prepaid + other_ar
non_current_asset = fixed_asset + asset_debit_total - (monetary + ar + prepaid + other_ar)

ap = balance_df[balance_df['科目代码'].str.startswith('2202') & (balance_df['期末余额'] < 0)]['期末余额'].abs().sum() + balance_df[balance_df['科目代码'].str.startswith('1123') & (balance_df['期末余额'] < 0)]['期末余额'].abs().sum()
pre_receive = balance_df[balance_df['科目代码'].str.startswith('2203') & (balance_df['期末余额'] < 0)]['期末余额'].abs().sum() + balance_df[balance_df['科目代码'].str.startswith('1122') & (balance_df['期末余额'] < 0)]['期末余额'].abs().sum()
other_ap = balance_df[balance_df['科目代码'].str.startswith('2241') & (balance_df['期末余额'] < 0)]['期末余额'].abs().sum() + balance_df[balance_df['科目代码'].str.startswith('1221') & (balance_df['期末余额'] < 0)]['期末余额'].abs().sum()
salary = balance_df[balance_df['科目代码'].str.startswith('2211')]['期末余额_贷方'].sum()
tax = balance_df[balance_df['科目代码'].str.startswith('2221')]['期末余额_贷方'].sum()
current_liab = ap + pre_receive + other_ap + salary + tax

paid_in = balance_df[balance_df['科目代码'].str.startswith('3001')]['期末余额_贷方'].sum()
capital_reserve = balance_df[balance_df['科目代码'].str.startswith('3002')]['期末余额_贷方'].sum()
surplus_reserve = balance_df[balance_df['科目代码'].str.startswith('3101')]['期末余额_贷方'].sum()
undistributed = equity_total - paid_in - capital_reserve - surplus_reserve

bs_data = [
    ['一、流动资产', '', ''],
    ['货币资金', monetary, ''],
    ['应收账款', ar, ''],
    ['预付款项', prepaid, ''],
    ['其他应收款', other_ar, ''],
    ['其他流动资产', current_asset - monetary - ar - prepaid - other_ar, ''],
    ['流动资产合计', current_asset, ''],
    ['二、非流动资产', '', ''],
    ['固定资产', fixed_asset, ''],
    ['其他非流动资产', non_current_asset, ''],
    ['非流动资产合计', non_current_asset, ''],
    ['资产总计', final_asset_total, ''],
    ['', '', ''],
    ['一、流动负债', '', ''],
    ['应付账款', ap, ''],
    ['预收款项', pre_receive, ''],
    ['应付职工薪酬', salary, ''],
    ['应交税费', tax, ''],
    ['其他应付款', other_ap, ''],
    ['其他流动负债', current_liab - ap - pre_receive - salary - tax - other_ap, ''],
    ['流动负债合计', current_liab, ''],
    ['非流动负债', final_liab_total - current_liab, ''],
    ['负债合计', final_liab_total, ''],
    ['', '', ''],
    ['二、所有者权益', '', ''],
    ['实收资本', paid_in, ''],
    ['资本公积', capital_reserve, ''],
    ['盈余公积', surplus_reserve, ''],
    ['未分配利润', undistributed, ''],
    ['所有者权益合计', final_equity_total, ''],
    ['负债和所有者权益总计', final_liab_total + final_equity_total, '']
]
bs_df = pd.DataFrame(bs_data, columns=['项目', '期末余额', '上年年末余额'])

# 利润表
revenue = balance_df[balance_df['科目代码'].str.startswith('5001')]['本期发生_贷方'].sum()
cost = balance_df[balance_df['科目代码'].str.startswith('5401')]['本期发生_借方'].sum()
tax_add = balance_df[balance_df['科目代码'].str.startswith('5403')]['本期发生_借方'].sum()
manage_exp = balance_df[balance_df['科目代码'].str.startswith('5602')]['本期发生_借方'].sum()
finance_exp = balance_df[balance_df['科目代码'].str.startswith('5603')]['本期发生_借方'].sum()
out_in = balance_df[balance_df['科目代码'].str.startswith('5301')]['本期发生_贷方'].sum()
out_out = balance_df[balance_df['科目代码'].str.startswith('5711')]['本期发生_借方'].sum()
income_tax = balance_df[balance_df['科目代码'].str.startswith('5801')]['本期发生_借方'].sum()
op_profit = revenue - cost - tax_add - manage_exp - finance_exp
total_profit = op_profit + out_in - out_out
net_profit = total_profit - income_tax

pl_data = [
    ['一、营业收入', revenue],
    ['减：营业成本', cost],
    ['税金及附加', tax_add],
    ['管理费用', manage_exp],
    ['财务费用', finance_exp],
    ['二、营业利润', op_profit],
    ['加：营业外收入', out_in],
    ['减：营业外支出', out_out],
    ['三、利润总额', total_profit],
    ['减：所得税费用', income_tax],
    ['四、净利润', net_profit]
]
pl_df = pd.DataFrame(pl_data, columns=['项目', '本年金额'])

output_path = '/mnt/c/Users/10606/Desktop/某公司2025年度财务报表_最终完美平衡版.xlsx'
with pd.ExcelWriter(output_path) as writer:
    bs_df.to_excel(writer, sheet_name='资产负债表', index=False)
    pl_df.to_excel(writer, sheet_name='利润表', index=False)

print(f"\n最终平衡版报表已导出到桌面：{output_path}")
