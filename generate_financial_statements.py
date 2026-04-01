#!/usr/bin/env python3
import pandas as pd
import numpy as np

# ============ 数据读取 ============
balance_df = pd.read_excel('/mnt/c/Users/10606/Desktop/1/2025年科目余额表.xlsx', header=2)
balance_df.columns = ['科目代码', '科目名称', '期初借方', '期初贷方', '本期借方', '本期贷方', '期末借方', '期末贷方']
balance_df = balance_df.dropna(subset=['科目代码'])
balance_df = balance_df[balance_df['科目代码'] != '合计']

for col in ['期初借方', '期初贷方', '本期借方', '本期贷方', '期末借方', '期末贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', '').replace('nan', np.nan), errors='coerce')

def g(code, col):
    rows = balance_df[balance_df['科目代码'] == code]
    if len(rows) == 0: return 0.0
    v = rows[col].values[0]
    return float(v) if pd.notna(v) else 0.0

def subs(prefix, col):
    codes = balance_df['科目代码'].astype(str)
    mask = codes.str.startswith(prefix) & (codes.str.len() > len(prefix))
    return balance_df.loc[mask, col].fillna(0).sum()

# ============ 用户指定值 ============
ar_correct = 1896603.92        # 应收账款
prepay_correct = 1082601.51    # 预付账款
cr_correct = 259212.91         # 其他应收款
fixed_net = g('1601', '期末借方') - abs(g('1602', '期末贷方'))  # 固定资产净值
inv_const = 0.0                 # 在建工程

ap_correct = 39086.38          # 应付账款
advance_recv = 64375.00        # 预收账款
salary = 299379.79             # 应付职工薪酬
tax = 39420.30                 # 应交税费
other_pay = 314603.25          # 其他应付款

paid_in = 2915000.0
cap_surp = 83306.0
surp_pub = 16449.24
undist = -73501.32

# ============ 资产负债表 ============
cash = g('1001', '期末借方') + g('1002', '期末借方')
current_assets = cash + ar_correct + prepay_correct + cr_correct
total_non_current = fixed_net + inv_const
total_assets = current_assets + total_non_current

current_liab = ap_correct + advance_recv + salary + tax + other_pay
lt_borrow = abs(g('2501', '期末贷方'))
total_liab = current_liab + lt_borrow

equity_total = paid_in + cap_surp + surp_pub + undist

print("=" * 75)
print("                           资产负债表")
print("                     2025年12月31日")
print("                     编制单位：某公司              单位：元")
print("=" * 75)
print(f"{'资产':<33}{'期末余额':>16}")
print("-" * 75)
print(f"{'流动资产：':<33}")
print(f"{'  货币资金':<31}{cash:>16,.2f}")
print(f"{'  应收账款':<31}{ar_correct:>16,.2f}")
print(f"{'  预付账款':<31}{prepay_correct:>16,.2f}")
print(f"{'  其他应收款':<31}{cr_correct:>16,.2f}")
print(f"{'流动资产合计':<31}{current_assets:>16,.2f}")
print(f"{'非流动资产：':<33}")
print(f"{'  固定资产净值':<31}{fixed_net:>16,.2f}")
print(f"{'  在建工程':<31}{inv_const:>16,.2f}")
print(f"{'非流动资产合计':<31}{total_non_current:>16,.2f}")
print(f"{'资产总计':.<64}{total_assets:>16,.2f}")

print()
print(f"{'负债和所有者权益':<33}{'期末余额':>16}")
print("-" * 75)
print(f"{'流动负债：':<33}")
print(f"{'  应付账款':<31}{ap_correct:>16,.2f}")
print(f"{'  预收账款':<31}{advance_recv:>16,.2f}")
print(f"{'  应付职工薪酬':<31}{salary:>16,.2f}")
print(f"{'  应交税费':<31}{tax:>16,.2f}")
print(f"{'  其他应付款':<31}{other_pay:>16,.2f}")
print(f"{'流动负债合计':<31}{current_liab:>16,.2f}")
print(f"{'非流动负债：':<33}")
print(f"{'  长期借款':<31}{lt_borrow:>16,.2f}")
print(f"{'非流动负债合计':<31}{lt_borrow:>16,.2f}")
print(f"{'负债合计':.<64}{total_liab:>16,.2f}")
print(f"{'所有者权益：':<33}")
print(f"{'  实收资本':<31}{paid_in:>16,.2f}")
print(f"{'  资本公积':<31}{cap_surp:>16,.2f}")
print(f"{'  盈余公积':<31}{surp_pub:>16,.2f}")
print(f"{'  未分配利润':<31}{undist:>16,.2f}")
print(f"{'所有者权益合计':<31}{equity_total:>16,.2f}")
print(f"{'负债和所有者权益总计':.<64}{total_liab + equity_total:>16,.2f}")

bs_diff = abs(total_assets - (total_liab + equity_total))
print(f"\n{'✅ 资产负债表平衡检查':<64}差异={bs_diff:,.2f}{' 【通过】' if bs_diff < 1 else ' 【不通过】'}")

# ============ 利润表 ============
revenue = g('5001', '本期贷方')
cost = g('5401', '本期借方')
tax_surcharge = g('5403', '本期借方')
expense_mgmt = subs('5602', '本期借方')
expense_fin = subs('5603', '本期借方')
other_rev = g('5301', '本期贷方')
other_exp = g('5711', '本期借方')
inc_tax = g('5801', '本期借方')

pretax = revenue - cost - tax_surcharge - expense_mgmt - expense_fin + other_rev - other_exp
net_profit = pretax - inc_tax

print()
print("=" * 75)
print("                             利润表")
print("                          2025年度")
print("                     编制单位：某公司              单位：元")
print("=" * 75)
print(f"{'项目':<42}{'本期金额':>16}")
print("-" * 75)
print(f"{'营业收入':<42}{revenue:>16,.2f}")
print(f"{'  减：营业成本':<42}{cost:>16,.2f}")
print(f"{'毛利润':.<42}{revenue - cost:>16,.2f}")
print(f"{'  减：税金及附加':<42}{tax_surcharge:>16,.2f}")
print(f"{'  减：管理费用':<42}{expense_mgmt:>16,.2f}")
print(f"{'  减：财务费用':<42}{expense_fin:>16,.2f}")
print(f"{'营业利润（亏损）':.<42}{revenue - cost - tax_surcharge - expense_mgmt - expense_fin:>16,.2f}")
print(f"{'  加：营业外收入':<42}{other_rev:>16,.2f}")
print(f"{'  减：营业外支出':<42}{other_exp:>16,.2f}")
print(f"{'利润总额（亏损）':.<42}{pretax:>16,.2f}")
print(f"{'  减：所得税费用':<42}{inc_tax:>16,.2f}")
print(f"{'净利润（亏损）':.<42}{net_profit:>16,.2f}")

# 保存Excel
output = pd.DataFrame({
    '报表项目': ['资产总计', '负债合计', '所有者权益合计', '资产负债率(%)',
                '营业收入', '营业成本', '毛利润', '营业利润', '利润总额', '净利润'],
    '金额': [total_assets, total_liab, equity_total, round(total_liab/total_assets*100,2),
             revenue, cost, revenue-cost,
             revenue-cost-tax_surcharge-expense_mgmt-expense_fin,
             pretax, net_profit]
})
output.to_excel('/mnt/c/Users/10606/Desktop/1/财务报表输出.xlsx', index=False)
print(f"\n✅ 财务报表已保存: /mnt/c/Users/10606/Desktop/1/财务报表输出.xlsx")
