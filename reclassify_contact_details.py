import pandas as pd
import numpy as np

# -------------------------- 1. 读取所有明细科目余额 --------------------------
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
balance_df['科目代码'] = balance_df['科目代码'].astype(str).str.rstrip('.0')

# -------------------------- 2. 筛选所有往来类科目，按末级明细统计借贷余额 --------------------------
# 往来科目代码前缀：应收1122、预付1123、其他应收1221、应付2202、预收2203、其他应付2241
def is_contact_subject(code):
    if not isinstance(code, str):
        return False
    return code.startswith('1122') or code.startswith('1123') or code.startswith('1221') or code.startswith('2202') or code.startswith('2203') or code.startswith('2241')

contact_df = balance_df[balance_df['科目代码'].apply(is_contact_subject)].copy()
# 计算每个明细科目的余额方向：正为借，负为贷
contact_df['期末余额'] = contact_df['期末余额_借方'] - contact_df['期末余额_贷方']

print("所有往来明细科目余额：")
print(contact_df[['科目代码', '科目名称', '期末余额_借方', '期末余额_贷方', '期末余额']].to_string(index=False))

# -------------------------- 3. 按准则正确重分类 --------------------------
# 3.1 应收账款/预收账款：应收的借方+预收的借方=应收账款；应收的贷方+预收的贷方=预收账款
ar_debit = contact_df[contact_df['科目代码'].str.startswith('1122') & (contact_df['期末余额'] > 0)]['期末余额'].sum()
ar_credit = contact_df[contact_df['科目代码'].str.startswith('1122') & (contact_df['期末余额'] < 0)]['期末余额'].abs().sum()
pre_receive_debit = contact_df[contact_df['科目代码'].str.startswith('2203') & (contact_df['期末余额'] > 0)]['期末余额'].sum() if any(contact_df['科目代码'].str.startswith('2203')) else 0
pre_receive_credit = contact_df[contact_df['科目代码'].str.startswith('2203') & (contact_df['期末余额'] < 0)]['期末余额'].abs().sum() if any(contact_df['科目代码'].str.startswith('2203')) else 0

final_ar = ar_debit + pre_receive_debit
final_pre_receive = ar_credit + pre_receive_credit

# 3.2 预付账款/应付账款：预付的借方+应付的借方=预付账款；预付的贷方+应付的贷方=应付账款
pre_pay_debit = contact_df[contact_df['科目代码'].str.startswith('1123') & (contact_df['期末余额'] > 0)]['期末余额'].sum() if any(contact_df['科目代码'].str.startswith('1123')) else 0
pre_pay_credit = contact_df[contact_df['科目代码'].str.startswith('1123') & (contact_df['期末余额'] < 0)]['期末余额'].abs().sum() if any(contact_df['科目代码'].str.startswith('1123')) else 0
ap_debit = contact_df[contact_df['科目代码'].str.startswith('2202') & (contact_df['期末余额'] > 0)]['期末余额'].sum()
ap_credit = contact_df[contact_df['科目代码'].str.startswith('2202') & (contact_df['期末余额'] < 0)]['期末余额'].abs().sum()

final_pre_pay = pre_pay_debit + ap_debit
final_ap = pre_pay_credit + ap_credit

# 3.3 其他应收款/其他应付款：其他应收的借方+其他应付的借方=其他应收；其他应收的贷方+其他应付的贷方=其他应付
other_ar_debit = contact_df[contact_df['科目代码'].str.startswith('1221') & (contact_df['期末余额'] > 0)]['期末余额'].sum()
other_ar_credit = contact_df[contact_df['科目代码'].str.startswith('1221') & (contact_df['期末余额'] < 0)]['期末余额'].abs().sum()
other_ap_debit = contact_df[contact_df['科目代码'].str.startswith('2241') & (contact_df['期末余额'] > 0)]['期末余额'].sum()
other_ap_credit = contact_df[contact_df['科目代码'].str.startswith('2241') & (contact_df['期末余额'] < 0)]['期末余额'].abs().sum()

final_other_ar = other_ar_debit + other_ap_debit
final_other_ap = other_ar_credit + other_ap_credit

print(f"\n✅ 重分类结果：")
print(f"应收账款：{final_ar:,.2f}")
print(f"预收款项：{final_pre_receive:,.2f}")
print(f"预付款项：{final_pre_pay:,.2f}")
print(f"应付账款：{final_ap:,.2f}")
print(f"其他应收款：{final_other_ar:,.2f}")
print(f"其他应付款：{final_other_ap:,.2f}")

# -------------------------- 4. 生成正确重分类的资产负债表 --------------------------
# 资产
monetary = balance_df[balance_df['科目代码'] == '1001']['期末余额_借方'].sum() + balance_df[balance_df['科目代码'] == '1002']['期末余额_借方'].sum()
fixed_assets = balance_df[balance_df['科目代码'] == '1601']['期末余额_借方'].sum() - balance_df[balance_df['科目代码'] == '1602']['期末余额_贷方'].sum()
total_assets = monetary + final_ar + final_pre_pay + final_other_ar + fixed_assets

# 负债
salary = balance_df[balance_df['科目代码'] == '2211']['期末余额_贷方'].sum()
tax = balance_df[balance_df['科目代码'] == '2221']['期末余额_贷方'].sum()
total_liab = final_ap + final_pre_receive + final_other_ap + salary + tax

# 所有者权益
paid_in = balance_df[balance_df['科目代码'] == '3001']['期末余额_贷方'].sum()
capital_reserve = balance_df[balance_df['科目代码'] == '3002']['期末余额_贷方'].sum()
surplus_reserve = balance_df[balance_df['科目代码'] == '3101']['期末余额_贷方'].sum()
undistributed_profit = -balance_df[balance_df['科目代码'] == '3104']['期末余额_借方'].sum()
total_equity = paid_in + capital_reserve + surplus_reserve + undistributed_profit

print(f"\n✅ 报表校验：")
print(f"资产总计：{total_assets:,.2f}")
print(f"负债+所有者权益总计：{total_liab + total_equity:,.2f}")
print(f"差额：{abs(total_assets - (total_liab + total_equity)):,.2f}")

# -------------------------- 5. 导出 --------------------------
bs_data = [
    ['一、流动资产', '', ''],
    ['货币资金', monetary, ''],
    ['应收账款', final_ar, ''],
    ['预付款项', final_pre_pay, ''],
    ['其他应收款', final_other_ar, ''],
    ['流动资产合计', monetary + final_ar + final_pre_pay + final_other_ar, ''],
    ['二、非流动资产', '', ''],
    ['固定资产', fixed_assets, ''],
    ['非流动资产合计', fixed_assets, ''],
    ['资产总计', total_assets, ''],
    ['', '', ''],
    ['一、流动负债', '', ''],
    ['应付账款', final_ap, ''],
    ['预收款项', final_pre_receive, ''],
    ['应付职工薪酬', salary, ''],
    ['应交税费', tax, ''],
    ['其他应付款', final_other_ap, ''],
    ['流动负债合计', total_liab, ''],
    ['负债合计', total_liab, ''],
    ['', '', ''],
    ['二、所有者权益', '', ''],
    ['实收资本', paid_in, ''],
    ['资本公积', capital_reserve, ''],
    ['盈余公积', surplus_reserve, ''],
    ['未分配利润', undistributed_profit, ''],
    ['所有者权益合计', total_equity, ''],
    ['负债和所有者权益总计', total_liab + total_equity, '']
]
bs_df = pd.DataFrame(bs_data, columns=['项目', '期末余额', '上年年末余额'])

# 利润表
revenue = balance_df[balance_df['科目代码'] == '5001']['本期发生_贷方'].sum()
cost = balance_df[balance_df['科目代码'] == '5401']['本期发生_借方'].sum()
tax_add = balance_df[balance_df['科目代码'] == '5403']['本期发生_借方'].sum()
manage_exp = balance_df[balance_df['科目代码'] == '5602']['本期发生_借方'].sum()
finance_exp = balance_df[balance_df['科目代码'] == '5603']['本期发生_借方'].sum()
out_in = balance_df[balance_df['科目代码'] == '5301']['本期发生_贷方'].sum()
out_out = balance_df[balance_df['科目代码'] == '5711']['本期发生_借方'].sum()
income_tax = balance_df[balance_df['科目代码'] == '5801']['本期发生_借方'].sum()
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

output_path = '/mnt/c/Users/10606/Desktop/某公司2025年度财务报表_往来明细重分类版.xlsx'
with pd.ExcelWriter(output_path) as writer:
    bs_df.to_excel(writer, sheet_name='资产负债表', index=False)
    pl_df.to_excel(writer, sheet_name='利润表', index=False)
    contact_df.to_excel(writer, sheet_name='往来明细备查', index=False)

print(f"\n报表已导出到桌面：{output_path}")
