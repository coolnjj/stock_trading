import pandas as pd
import numpy as np

# -------------------------- 1. 读取余额表，智能识别末级科目 --------------------------
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
balance_df['科目代码'] = balance_df['科目代码'].astype(str).str.rstrip('.0')
# 排除空代码行
balance_df = balance_df[balance_df['科目代码'] != 'nan'].copy()

# 智能判断末级科目：如果没有其他科目以当前代码为前缀，则为末级
all_codes = set([str(c) for c in balance_df['科目代码'].tolist()])
def is_final_level(code):
    code = str(code)
    for other_code in all_codes:
        if other_code != code and other_code.startswith(code):
            return False
    return True

balance_df['is_final'] = balance_df['科目代码'].apply(is_final_level)
final_df = balance_df[balance_df['is_final'] == True].copy()
final_df['期末余额'] = final_df['期末余额_借方'] - final_df['期末余额_贷方']

print(f"共识别到{len(final_df)}个末级科目")

# -------------------------- 2. 往来重分类 --------------------------
def get_final_sum(prefix, is_debit):
    if is_debit:
        return final_df[final_df['科目代码'].str.startswith(prefix) & (final_df['期末余额'] > 0)]['期末余额'].sum()
    else:
        return final_df[final_df['科目代码'].str.startswith(prefix) & (final_df['期末余额'] < 0)]['期末余额'].abs().sum()

# 应收账款+预收
ar_debit = get_final_sum('1122', True)
ar_credit = get_final_sum('1122', False)
pre_receive_debit = get_final_sum('2203', True)
pre_receive_credit = get_final_sum('2203', False)
final_ar = ar_debit + pre_receive_debit
final_pre_receive = ar_credit + pre_receive_credit

# 预付+应付
pre_pay_debit = get_final_sum('1123', True)
pre_pay_credit = get_final_sum('1123', False)
ap_debit = get_final_sum('2202', True)
ap_credit = get_final_sum('2202', False)
final_pre_pay = pre_pay_debit + ap_debit
final_ap = pre_pay_credit + ap_credit

# 其他应收+其他应付
other_ar_debit = get_final_sum('1221', True)
other_ar_credit = get_final_sum('1221', False)
other_ap_debit = get_final_sum('2241', True)
other_ap_credit = get_final_sum('2241', False)
final_other_ar = other_ar_debit + other_ap_debit
final_other_ap = other_ar_credit + other_ap_credit

# 其他科目
monetary = final_df[final_df['科目代码'].str.startswith('1001') | final_df['科目代码'].str.startswith('1002')]['期末余额_借方'].sum()
fixed_asset_original = final_df[final_df['科目代码'].str.startswith('1601')]['期末余额_借方'].sum()
accumulated_depreciation = final_df[final_df['科目代码'].str.startswith('1602')]['期末余额_贷方'].sum()
fixed_assets = fixed_asset_original - accumulated_depreciation
salary = final_df[final_df['科目代码'].str.startswith('2211')]['期末余额_贷方'].sum()
tax = final_df[final_df['科目代码'].str.startswith('2221')]['期末余额_贷方'].sum()
paid_in = final_df[final_df['科目代码'].str.startswith('3001')]['期末余额_贷方'].sum()
capital_reserve = final_df[final_df['科目代码'].str.startswith('3002')]['期末余额_贷方'].sum()
surplus_reserve = final_df[final_df['科目代码'].str.startswith('3101')]['期末余额_贷方'].sum()
undistributed_profit = -final_df[final_df['科目代码'].str.startswith('3104')]['期末余额_借方'].sum()

# -------------------------- 3. 生成报表 --------------------------
current_assets = monetary + final_ar + final_pre_pay + final_other_ar
total_assets = current_assets + fixed_assets
total_liab = final_ap + final_pre_receive + final_other_ap + salary + tax
total_equity = paid_in + capital_reserve + surplus_reserve + undistributed_profit

print(f"\n✅ 最终重分类结果：")
print(f"货币资金：{monetary:,.2f} (包含库存现金+银行存款)")
print(f"应收账款：{final_ar:,.2f}")
print(f"预付款项：{final_pre_pay:,.2f}")
print(f"其他应收款：{final_other_ar:,.2f}")
print(f"固定资产：{fixed_assets:,.2f} (原值-累计折旧)")
print(f"资产总计：{total_assets:,.2f}")
print(f"\n应付账款：{final_ap:,.2f}")
print(f"预收款项：{final_pre_receive:,.2f}")
print(f"其他应付款：{final_other_ap:,.2f}")
print(f"应付职工薪酬：{salary:,.2f}")
print(f"应交税费：{tax:,.2f}")
print(f"负债合计：{total_liab:,.2f}")
print(f"\n实收资本：{paid_in:,.2f}")
print(f"资本公积：{capital_reserve:,.2f}")
print(f"盈余公积：{surplus_reserve:,.2f}")
print(f"未分配利润：{undistributed_profit:,.2f}")
print(f"所有者权益合计：{total_equity:,.2f}")
print(f"\n✅ 校验：资产总计 = {total_assets:,.2f}，负债+权益 = {total_liab + total_equity:,.2f}，差额：{abs(total_assets - (total_liab + total_equity)):,.2f}")

# -------------------------- 4. 导出 --------------------------
bs_data = [
    ['一、流动资产', '', ''],
    ['货币资金', monetary, ''],
    ['应收账款', final_ar, ''],
    ['预付款项', final_pre_pay, ''],
    ['其他应收款', final_other_ar, ''],
    ['流动资产合计', current_assets, ''],
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
revenue = final_df[final_df['科目代码'].str.startswith('5001')]['本期发生_贷方'].sum()
cost = final_df[final_df['科目代码'].str.startswith('5401')]['本期发生_借方'].sum()
tax_add = final_df[final_df['科目代码'].str.startswith('5403')]['本期发生_借方'].sum()
manage_exp = final_df[final_df['科目代码'].str.startswith('5602')]['本期发生_借方'].sum()
finance_exp = final_df[final_df['科目代码'].str.startswith('5603')]['本期发生_借方'].sum()
out_in = final_df[final_df['科目代码'].str.startswith('5301')]['本期发生_贷方'].sum()
out_out = final_df[final_df['科目代码'].str.startswith('5711')]['本期发生_借方'].sum()
income_tax = final_df[final_df['科目代码'].str.startswith('5801')]['本期发生_借方'].sum()
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

output_path = '/mnt/c/Users/10606/Desktop/某公司2025年度财务报表_完美版.xlsx'
with pd.ExcelWriter(output_path) as writer:
    bs_df.to_excel(writer, sheet_name='资产负债表', index=False)
    pl_df.to_excel(writer, sheet_name='利润表', index=False)

print(f"\n完美版报表已导出到桌面：{output_path}")
