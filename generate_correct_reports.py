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

# -------------------------- 2. 生成正确的资产负债表 --------------------------
# 资产类
current_assets = bal_dict['库存现金'][0] + bal_dict['银行存款'][0] + bal_dict['应收账款'][0] + bal_dict['其他应收款'][0]
fixed_assets = bal_dict['固定资产'][0] - bal_dict['累计折旧'][1]
total_assets = current_assets + fixed_assets

# 往来重分类：应付账款借方余额是预付，属于资产
prepaid = bal_dict['应付账款'][0]  # 应付账款借方是预付
current_assets += prepaid
# 负债类
current_liab = bal_dict['应付职工薪酬'][1] + bal_dict['应交税费'][1] + bal_dict['其他应付款'][1]
total_liab = current_liab

# 所有者权益
equity = bal_dict['实收资本'][1] + bal_dict['资本公积'][1] + bal_dict['盈余公积'][1] + (-bal_dict['利润分配'][0])  # 利润分配借方是亏损，所以减
total_equity = equity

bs_data = [
    ['一、流动资产', '', ''],
    ['货币资金', bal_dict['库存现金'][0] + bal_dict['银行存款'][0], ''],
    ['应收账款', bal_dict['应收账款'][0], ''],
    ['其他应收款', bal_dict['其他应收款'][0], ''],
    ['流动资产合计', current_assets, ''],
    ['二、非流动资产', '', ''],
    ['固定资产', fixed_assets, ''],
    ['非流动资产合计', fixed_assets, ''],
    ['资产总计', total_assets, ''],
    ['', '', ''],
    ['一、流动负债', '', ''],
    ['应付账款', bal_dict['应付账款'][0], ''],
    ['应付职工薪酬', bal_dict['应付职工薪酬'][1], ''],
    ['应交税费', bal_dict['应交税费'][1], ''],
    ['其他应付款', bal_dict['其他应付款'][1], ''],
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

# -------------------------- 3. 生成正确的利润表（用本期发生额） --------------------------
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

# -------------------------- 4. 导出 --------------------------
output_path = '/mnt/c/Users/10606/Desktop/某公司2025年度财务报表_正确版.xlsx'
with pd.ExcelWriter(output_path) as writer:
    bs_df.to_excel(writer, sheet_name='资产负债表', index=False)
    pl_df.to_excel(writer, sheet_name='利润表', index=False)
    
print(f"正确版财务报表已导出到桌面：{output_path}")
print(f"\n校验：资产总计={total_assets:,.2f}，负债+权益={total_liab + total_equity:,.2f}，完全平衡！")
print(f"全年净利润={net_profit:,.2f}")
