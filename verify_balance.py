#!/usr/bin/env python3
import pandas as pd
import numpy as np

# 读取数据
balance_df = pd.read_excel('/mnt/c/Users/10606/Desktop/1/2025年科目余额表.xlsx', header=2)
voucher_df = pd.read_excel('/mnt/c/Users/10606/Desktop/1/2025年记账凭证.xlsx', header=2)

# 重命名余额表列
balance_df.columns = ['科目代码', '科目名称', '期初借方', '期初贷方', '本期借方', '本期贷方', '期末借方', '期末贷方']
balance_df = balance_df.dropna(subset=['科目代码'])
balance_df = balance_df[balance_df['科目代码'] != 'NaN']
balance_df = balance_df[~balance_df['科目代码'].isna()]

# 清理余额表数据
balance_df = balance_df[balance_df['科目代码'] != '合计']

# 转换数字列为数值类型
for col in ['期初借方', '期初贷方', '本期借方', '本期贷方', '期末借方', '期末贷方']:
    balance_df[col] = pd.to_numeric(balance_df[col].astype(str).str.replace(',', '').replace('nan', np.nan), errors='coerce')

print("=" * 60)
print("【第一步：余额表本身平衡检查】")
print("=" * 60)

# 检查余额表本身的借贷平衡
total_initial_debit = balance_df['期初借方'].sum()
total_initial_credit = balance_df['期初贷方'].sum()
total_current_debit = balance_df['本期借方'].sum()
total_current_credit = balance_df['本期贷方'].sum()
total_end_debit = balance_df['期末借方'].sum()
total_end_credit = balance_df['期末贷方'].sum()

print(f"期初借方合计: {total_initial_debit:,.2f}")
print(f"期初贷方合计: {total_initial_credit:,.2f}")
print(f"差异: {abs(total_initial_debit - total_initial_credit):,.2f}")
print()
print(f"本期借方发生额: {total_current_debit:,.2f}")
print(f"本期贷方发生额: {total_current_credit:,.2f}")
print(f"差异: {abs(total_current_debit - total_current_credit):,.2f}")
print()
print(f"期末借方合计: {total_end_debit:,.2f}")
print(f"期末贷方合计: {total_end_credit:,.2f}")
print(f"差异: {abs(total_end_debit - total_end_credit):,.2f}")

print()
print("=" * 60)
print("【第二步：从记账凭证汇总数据】")
print("=" * 60)

# 重命名凭证列
voucher_df.columns = ['凭证类型', '凭证号', '制表日期', '摘要', '科目编号', '科目名称', 
                       '借方金额', '贷方金额', '外币借方', '外币贷方', '汇率', 
                       '数量借方', '数量贷方', '单价', '部门编号', '人员编号', 
                       '项目编号', '往来编号', '附单据', '制表', '记账', '状态']

# 过滤掉表头行
voucher_df = voucher_df[voucher_df['凭证类型'].notna() & (voucher_df['凭证类型'] != '凭证类型')]

# 转换金额列为数值
voucher_df['借方金额'] = pd.to_numeric(voucher_df['借方金额'].astype(str).str.replace(',', '').replace('nan', np.nan), errors='coerce')
voucher_df['贷方金额'] = pd.to_numeric(voucher_df['贷方金额'].astype(str).str.replace(',', '').replace('nan', np.nan), errors='coerce')

voucher_total_debit = voucher_df['借方金额'].sum()
voucher_total_credit = voucher_df['贷方金额'].sum()

print(f"凭证汇总借方合计: {voucher_total_debit:,.2f}")
print(f"凭证汇总贷方合计: {voucher_total_credit:,.2f}")
print(f"凭证数量: {len(voucher_df)}")
print(f"凭证借贷差异: {abs(voucher_total_debit - voucher_total_credit):,.2f}")

print()
print("=" * 60)
print("【第三步：余额表 vs 记账凭证 核对】")
print("=" * 60)

debit_diff = abs(total_current_debit - voucher_total_debit)
credit_diff = abs(total_current_credit - voucher_total_credit)

print(f"余额表本期借方: {total_current_debit:,.2f}")
print(f"凭证汇总借方: {voucher_total_debit:,.2f}")
print(f"差异: {debit_diff:,.2f}")
print()
print(f"余额表本期贷方: {total_current_credit:,.2f}")
print(f"凭证汇总贷方: {voucher_total_credit:,.2f}")
print(f"差异: {credit_diff:,.2f}")

if debit_diff < 0.01 and credit_diff < 0.01:
    print()
    print("✅ 检查结果：余额表与记账凭证 MATCH! 两者完全匹配")
else:
    print()
    print("❌ 检查结果：余额表与记账凭证存在差异！")

print()
print("=" * 60)
print("【第四步：资产/负债类科目余额验算】")
print("=" * 60)

# 筛选资产类和负债类科目，验证期末余额 = 期初余额 + 本期借方 - 本期贷方
mismatched = []
for idx, row in balance_df.iterrows():
    code = row['科目代码']
    if pd.isna(row['期初借方']) and pd.isna(row['期初贷方']):
        continue
    if pd.isna(row['本期借方']) and pd.isna(row['本期贷方']):
        continue
    
    # 判断科目性质（根据期初余额方向）
    if pd.notna(row['期初借方']) and row['期初借方'] > 0:
        # 资产或费用类
        expected_end = row['期初借方'] + (row['本期借方'] or 0) - (row['本期贷方'] or 0)
        actual_end = row['期末借方']
        if pd.notna(expected_end) and pd.notna(actual_end):
            if abs(expected_end - actual_end) > 0.01:
                mismatched.append({
                    '科目代码': code,
                    '科目名称': row['科目名称'],
                    '期初余额': row['期初借方'],
                    '本期借方': row['本期借方'],
                    '本期贷方': row['本期贷方'],
                    '计算期末': expected_end,
                    '实际期末': actual_end,
                    '差异': expected_end - actual_end
                })
    elif pd.notna(row['期初贷方']) and row['期初贷方'] > 0:
        # 负债或权益类
        expected_end = row['期初贷方'] + (row['本期贷方'] or 0) - (row['本期借方'] or 0)
        actual_end = row['期末贷方']
        if pd.notna(expected_end) and pd.notna(actual_end):
            if abs(expected_end - actual_end) > 0.01:
                mismatched.append({
                    '科目代码': code,
                    '科目名称': row['科目名称'],
                    '期初余额': row['期初贷方'],
                    '本期借方': row['本期借方'],
                    '本期贷方': row['本期贷方'],
                    '计算期末': expected_end,
                    '实际期末': actual_end,
                    '差异': expected_end - actual_end
                })

if mismatched:
    print(f"❌ 发现 {len(mismatched)} 个科目余额不匹配:")
    for m in mismatched[:20]:  # 只显示前20个
        print(f"  {m['科目代码']} {m['科目名称']}: 计算={m['计算期末']:,.2f} 实际={m['实际期末']:,.2f} 差异={m['差异']:,.2f}")
else:
    print("✅ 所有科目余额验算通过，余额表内部逻辑正确")
