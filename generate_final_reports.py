import pandas as pd
import numpy as np

# -------------------------- 1. 读取正确的一级科目数据 --------------------------
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
balance_df['科目代码'] = balance_df['科目代码'].astype(str).str.rstrip('.0')
level1_balance = balance_df[balance_df['科目代码'].str.len() == 4].copy()
bal_dict = dict(zip(level1_balance['科目名称'], zip(level1_balance['期末余额_借方'], level1_balance['期末余额_贷方'], level1_balance['本期发生_借方'], level1_balance['本期发生_贷方'])))

# -------------------------- 2. 全往来科目重分类 --------------------------
# 重分类规则：
# 1. 应收类借方=资产，贷方=预收负债
# 2. 应付类贷方=负债，借方=预付资产
ar_debit = bal_dict['应收账款'][0]  # 应收账款借方
ar_credit = bal_dict['应收账款'][1] # 应收账款贷方 → 预收
prepaid = bal_dict['应付账款'][0]  # 应付账款借方 → 预付
ap_credit = bal_dict['应付账款'][1] # 应付账款贷方
other_ar_debit = bal_dict['其他应收款'][0] # 其他应收借方
other_ar_credit = bal_dict['其他应收款'][1] # 其他应收贷方 → 其他应付
other_ap_credit = bal_dict['其他应付款'][1] # 其他应付贷方
other_ap_debit = bal_dict['其他应付款'][0] # 其他应付借方 → 其他应收

# 重分类后金额
final_ar = ar_debit + other_ap_debit
final_prepaid = prepaid
final_other_ar = other_ar_debit
final_ap = ap_credit + ar_credit
final_other_ap = other_ap_credit + other_ar_credit
final_advance = ar_credit # 预收

# -------------------------- 3. 生成正确的资产负债表 --------------------------
# 资产类
monetary = bal_dict['库存现金'][0] + bal_dict['银行存款'][0]
current_assets = monetary + final_ar + final_prepaid + final_other_ar
fixed_assets = bal_dict['固定资产'][0] - bal_dict['累计折旧'][1]
total_assets = current_assets + fixed_assets

# 负债类
current_liab = final_ap + final_other_ap + final_advance + bal_dict['应付职工薪酬'][1] + bal_dict['应交税费'][1]
total_liab = current_liab

# 所有者权益
equity = bal_dict['实收资本'][1] + bal_dict['资本公积'][1] + bal_dict['盈余公积'][1] + (-bal_dict['利润分配'][0])  # 利润分配借方是亏损
total_equity = equity

bs_data = [
    ['一、流动资产', '', ''],
    ['货币资金', monetary, ''],
    ['应收账款', final_ar, ''],
    ['预付款项', final_prepaid, ''],
    ['其他应收款', final_other_ar, ''],
    ['流动资产合计', current_assets, ''],
    ['二、非流动资产', '', ''],
    ['固定资产', fixed_assets, ''],
    ['非流动资产合计', fixed_assets, ''],
    ['资产总计', total_assets, ''],
    ['', '', ''],
    ['一、流动负债', '', ''],
    ['应付账款', final_ap, ''],
    ['预收款项', final_advance, ''],
    ['应付职工薪酬', bal_dict['应付职工薪酬'][1], ''],
    ['应交税费', bal_dict['应交税费'][1], ''],
    ['其他应付款', final_other_ap, ''],
    ['流动负债合计', current_liab, ''],
    ['负债合计', total_liab, ''],
    ['', '', ''],
    ['二、所有者权益', '', ''],
    ['实收资本', bal_dict['实收资本'][1], ''],
    ['资本公积', bal_dict['资本公积'][1], ''],
    ['盈余公积', bal_dict['盈余公积'][1], ''],
    ['未分配利润', -bal_dict['利润分配'][0], ''],
    ['所有者权益合计', total_equity, ''],
    ['负债和所有者权益总计', total_liab + total_equity, '']
]
bs_df = pd.DataFrame(bs_data, columns=['项目', '期末余额', '上年年末余额'])

# -------------------------- 4. 生成正确的利润表（用本期发生额） --------------------------
revenue = bal_dict['主营业务收入'][3]  # 贷方发生额是收入
cost = bal_dict['主营业务成本'][2]     # 借方发生额是成本
tax = bal_dict['税金及附加'][2]
manage_exp = bal_dict['管理费用'][2]
finance_exp = bal_dict['财务费用'][2]
out_business_in = bal_dict['营业外收入'][3]
out_business_out = bal_dict['营业外支出'][2]
income_tax = bal_dict['所得税费用'][2]

op_profit = revenue - cost - tax - manage_exp - finance_exp
total_profit = op_profit + out_business_in - out_business_out
net_profit = total_profit - income_tax

pl_data = [
    ['一、营业收入', revenue],
    ['减：营业成本', cost],
    ['税金及附加', tax],
    ['管理费用', manage_exp],
    ['财务费用', finance_exp],
    ['二、营业利润', op_profit],
    ['加：营业外收入', out_business_in],
    ['减：营业外支出', out_business_out],
    ['三、利润总额', total_profit],
    ['减：所得税费用', income_tax],
    ['四、净利润', net_profit]
]
pl_df = pd.DataFrame(pl_data, columns=['项目', '本年金额'])

# -------------------------- 5. 导出 --------------------------
output_path = '/mnt/c/Users/10606/Desktop/某公司2025年度财务报表_最终重分类版.xlsx'
with pd.ExcelWriter(output_path) as writer:
    bs_df.to_excel(writer, sheet_name='资产负债表', index=False)
    pl_df.to_excel(writer, sheet_name='利润表', index=False)
    
print(f"最终重分类版报表已导出到桌面：{output_path}")
print(f"\n✅ 校验：")
print(f"资产总计：{total_assets:,.2f}")
print(f"负债+所有者权益总计：{total_liab + total_equity:,.2f}")
print(f"差额：{abs(total_assets - (total_liab + total_equity)):,.2f}")
print(f"全年净利润：{net_profit:,.2f}")
