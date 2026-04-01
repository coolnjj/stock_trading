import pandas as pd
import numpy as np

# -------------------------- 1. 读取基础数据 --------------------------
# 读取科目余额表（一级科目）
balance_cols = ['科目代码', '科目名称', '期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']
balance_df = pd.read_excel(
    '/mnt/c/Users/10606/Desktop/1/某公司2025年科目余额表.xlsx',
    skiprows=4,
    names=balance_cols
)
for col in ['期初余额_借方', '期初余额_贷方', '本期发生_借方', '本期发生_贷方', '期末余额_借方', '期末余额_贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
balance_df['科目代码'] = balance_df['科目代码'].astype(str).str.rstrip('.0')
# 只保留一级科目（代码长度4位）
level1_balance = balance_df[balance_df['科目代码'].str.len() == 4].copy()
# 把借方贷方余额合并成期末余额（正借负贷）
level1_balance['期末余额'] = level1_balance['期末余额_借方'] - level1_balance['期末余额_贷方']
level1_balance['期初余额'] = level1_balance['期初余额_借方'] - level1_balance['期初余额_贷方']
balance_dict = dict(zip(level1_balance['科目名称'], level1_balance['期末余额']))
begin_balance_dict = dict(zip(level1_balance['科目名称'], level1_balance['期初余额']))

# -------------------------- 2. 生成资产负债表 --------------------------
bs_items = [
    # 流动资产
    ('流动资产：', None, None),
    ('货币资金', balance_dict.get('库存现金',0)+balance_dict.get('银行存款',0)+balance_dict.get('其他货币资金',0), 
     begin_balance_dict.get('库存现金',0)+begin_balance_dict.get('银行存款',0)+begin_balance_dict.get('其他货币资金',0)),
    ('应收账款', max(balance_dict.get('应收账款',0), 0), max(begin_balance_dict.get('应收账款',0), 0)),
    ('预付款项', max(balance_dict.get('预付账款',0), 0), max(begin_balance_dict.get('预付账款',0), 0)),
    ('其他应收款', max(balance_dict.get('其他应收款',0), 0), max(begin_balance_dict.get('其他应收款',0), 0)),
    ('存货', balance_dict.get('原材料',0)+balance_dict.get('库存商品',0)+balance_dict.get('周转材料',0)+balance_dict.get('生产成本',0)+balance_dict.get('劳务成本',0),
     begin_balance_dict.get('原材料',0)+begin_balance_dict.get('库存商品',0)+begin_balance_dict.get('周转材料',0)+begin_balance_dict.get('生产成本',0)+begin_balance_dict.get('劳务成本',0)),
    ('流动资产合计', None, None),
    # 非流动资产
    ('非流动资产：', None, None),
    ('固定资产', balance_dict.get('固定资产',0)-abs(balance_dict.get('累计折旧',0)), 
     begin_balance_dict.get('固定资产',0)-abs(begin_balance_dict.get('累计折旧',0))),
    ('长期应收款', max(balance_dict.get('长期应收款',0), 0), max(begin_balance_dict.get('长期应收款',0), 0)),
    ('非流动资产合计', None, None),
    ('资产总计', None, None),
    
    # 流动负债
    ('流动负债：', None, None),
    ('短期借款', abs(min(balance_dict.get('短期借款',0), 0)), abs(min(begin_balance_dict.get('短期借款',0), 0))),
    ('应付账款', abs(min(balance_dict.get('应付账款',0), 0)), abs(min(begin_balance_dict.get('应付账款',0), 0))),
    ('预收款项', abs(min(balance_dict.get('预收账款',0), 0)), abs(min(begin_balance_dict.get('预收账款',0), 0))),
    ('应付职工薪酬', abs(min(balance_dict.get('应付职工薪酬',0), 0)), abs(min(begin_balance_dict.get('应付职工薪酬',0), 0))),
    ('应交税费', abs(min(balance_dict.get('应交税费',0), 0)), abs(min(begin_balance_dict.get('应交税费',0), 0))),
    ('其他应付款', abs(min(balance_dict.get('其他应付款',0), 0)), abs(min(begin_balance_dict.get('其他应付款',0), 0))),
    ('流动负债合计', None, None),
    # 非流动负债
    ('非流动负债：', None, None),
    ('长期借款', abs(min(balance_dict.get('长期借款',0), 0)), abs(min(begin_balance_dict.get('长期借款',0), 0))),
    ('非流动负债合计', None, None),
    ('负债合计', None, None),
    
    # 所有者权益
    ('所有者权益：', None, None),
    ('实收资本', abs(min(balance_dict.get('实收资本',0), 0)), abs(min(begin_balance_dict.get('实收资本',0), 0))),
    ('资本公积', abs(min(balance_dict.get('资本公积',0), 0)), abs(min(begin_balance_dict.get('资本公积',0), 0))),
    ('盈余公积', abs(min(balance_dict.get('盈余公积',0), 0)), abs(min(begin_balance_dict.get('盈余公积',0), 0))),
    ('未分配利润', balance_dict.get('本年利润',0)+balance_dict.get('利润分配',0), 
     begin_balance_dict.get('本年利润',0)+begin_balance_dict.get('利润分配',0)),
    ('所有者权益合计', None, None),
    ('负债和所有者权益总计', None, None),
]

# 计算合计项
bs_data = []
current_assets = 0
non_current_assets = 0
current_liab = 0
non_current_liab = 0
equity = 0
current_assets_begin = 0
for item, end, begin in bs_items:
    if item == '流动资产合计':
        end = current_assets
        current_assets_begin = sum([x[2] for x in bs_data if isinstance(x[2], (int, float)) and '非流动资产' not in str(x[0]) and '负债' not in str(x[0]) and '权益' not in str(x[0])])
        begin = current_assets_begin
    elif item == '非流动资产合计':
        end = non_current_assets
        begin = sum([x[2] for x in bs_data if x[0] in ['固定资产', '长期应收款']])
    elif item == '资产总计':
        end = current_assets + non_current_assets
        begin = current_assets_begin + sum([x[2] for x in bs_data if x[0] in ['固定资产', '长期应收款']])
    elif item == '流动负债合计':
        end = current_liab
        begin = sum([x[2] for x in bs_data if x[0] in ['短期借款', '应付账款', '预收款项', '应付职工薪酬', '应交税费', '其他应付款']])
    elif item == '非流动负债合计':
        end = non_current_liab
        begin = sum([x[2] for x in bs_data if x[0] in ['长期借款']])
    elif item == '负债合计':
        end = current_liab + non_current_liab
        begin = sum([x[2] for x in bs_data if x[0] in ['短期借款', '应付账款', '预收款项', '应付职工薪酬', '应交税费', '其他应付款', '长期借款']])
    elif item == '所有者权益合计':
        end = equity
        begin = sum([x[2] for x in bs_data if x[0] in ['实收资本', '资本公积', '盈余公积', '未分配利润']])
    elif item == '负债和所有者权益总计':
        end = current_liab + non_current_liab + equity
        begin = sum([x[2] for x in bs_data if x[0] in ['短期借款', '应付账款', '预收款项', '应付职工薪酬', '应交税费', '其他应付款', '长期借款', '实收资本', '资本公积', '盈余公积', '未分配利润']])
    elif end is not None:
        if item in ['货币资金', '应收账款', '预付款项', '其他应收款', '存货']:
            current_assets += end
        elif item in ['固定资产', '长期应收款']:
            non_current_assets += end
        elif item in ['短期借款', '应付账款', '预收款项', '应付职工薪酬', '应交税费', '其他应付款', '长期借款']:
            current_liab += end
        elif item in ['实收资本', '资本公积', '盈余公积', '未分配利润']:
            equity += end
    bs_data.append([item, round(end,2) if end is not None else '', round(begin,2) if begin is not None else ''])

bs_df = pd.DataFrame(bs_data, columns=['项目', '期末余额', '上年年末余额'])

# -------------------------- 3. 生成利润表 --------------------------
pl_items = [
    ('一、营业收入', level1_balance[level1_balance['科目名称']=='主营业务收入']['本期发生_贷方'].sum() + level1_balance[level1_balance['科目名称']=='其他业务收入']['本期发生_贷方'].sum()),
    ('减：营业成本', level1_balance[level1_balance['科目名称']=='主营业务成本']['本期发生_借方'].sum() + level1_balance[level1_balance['科目名称']=='其他业务成本']['本期发生_借方'].sum()),
    ('税金及附加', level1_balance[level1_balance['科目名称']=='税金及附加']['本期发生_借方'].sum()),
    ('销售费用', level1_balance[level1_balance['科目名称']=='销售费用']['本期发生_借方'].sum() if '销售费用' in level1_balance['科目名称'].values else 0),
    ('管理费用', level1_balance[level1_balance['科目名称']=='管理费用']['本期发生_借方'].sum()),
    ('研发费用', level1_balance[level1_balance['科目名称']=='研发费用']['本期发生_借方'].sum() if '研发费用' in level1_balance['科目名称'].values else 0),
    ('财务费用', level1_balance[level1_balance['科目名称']=='财务费用']['本期发生_借方'].sum()),
    ('加：其他收益', level1_balance[level1_balance['科目名称']=='其他收益']['本期发生_贷方'].sum() if '其他收益' in level1_balance['科目名称'].values else 0),
    ('投资收益', level1_balance[level1_balance['科目名称']=='投资收益']['本期发生_贷方'].sum() if '投资收益' in level1_balance['科目名称'].values else 0),
    ('二、营业利润', None),
    ('加：营业外收入', level1_balance[level1_balance['科目名称']=='营业外收入']['本期发生_贷方'].sum()),
    ('减：营业外支出', level1_balance[level1_balance['科目名称']=='营业外支出']['本期发生_借方'].sum()),
    ('三、利润总额', None),
    ('减：所得税费用', level1_balance[level1_balance['科目名称']=='所得税费用']['本期发生_借方'].sum()),
    ('四、净利润', None),
]

# 计算利润
pl_data = []
op_profit = 0
total_profit = 0
income_tax = 0
for idx, (item, amount) in enumerate(pl_items):
    if item == '二、营业利润':
        amount = op_profit
    elif item == '三、利润总额':
        total_profit = op_profit + pl_data[-2][1] - pl_data[-1][1]
        amount = total_profit
    elif item == '减：所得税费用':
        income_tax = amount
        amount = income_tax
    elif item == '四、净利润':
        amount = total_profit - income_tax
    else:
        if '减：' in item:
            op_profit -= amount
        elif '加：' in item or '一、' in item:
            op_profit += amount
    pl_data.append([item, round(amount,2) if amount is not None else ''])

pl_df = pd.DataFrame(pl_data, columns=['项目', '本年金额'])

# -------------------------- 4. 导出到Excel --------------------------
output_path = '/mnt/c/Users/10606/Desktop/某公司2025年度财务报表.xlsx'
with pd.ExcelWriter(output_path) as writer:
    bs_df.to_excel(writer, sheet_name='资产负债表', index=False)
    pl_df.to_excel(writer, sheet_name='利润表', index=False)
    
print(f"财务报表已导出到桌面：{output_path}")
