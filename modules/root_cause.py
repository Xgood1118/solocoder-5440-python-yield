import pandas as pd
import numpy as np
from scipy import stats
from modules.data_source import (
    get_production_data,
    get_factor_data,
    get_quality_data,
    LINES,
    PRODUCTS,
)
from modules.yield_engine import calculate_yield_by_time, calculate_yield


def analyze_root_causes(line=None, product=None, start_date=None, end_date=None):
    df = get_production_data()
    factor_data = get_factor_data()
    
    filtered_df = df.copy()
    if line:
        filtered_df = filtered_df[filtered_df['产线'] == line]
    if product:
        filtered_df = filtered_df[filtered_df['产品型号'] == product]
    
    daily_yield = calculate_yield_by_time(filtered_df, granularity='day')
    daily_yield = daily_yield[~daily_yield['小样本标记']]
    daily_yield['日期'] = pd.to_datetime(daily_yield['时间粒度']).dt.date
    
    results = []
    
    temp_corr = analyze_temperature_factor(daily_yield, factor_data, line)
    if temp_corr is not None:
        results.append(temp_corr)
    
    humidity_corr = analyze_humidity_factor(daily_yield, factor_data, line)
    if humidity_corr is not None:
        results.append(humidity_corr)
    
    mold_corr = analyze_mold_factor(filtered_df)
    if mold_corr is not None:
        results.append(mold_corr)
    
    material_corr = analyze_material_factor(filtered_df)
    if material_corr is not None:
        results.append(material_corr)
    
    equipment_corr = analyze_equipment_factor(daily_yield, factor_data, filtered_df)
    if equipment_corr is not None:
        results.append(equipment_corr)
    
    operator_corr = analyze_operator_factor(filtered_df)
    if operator_corr is not None:
        results.append(operator_corr)
    
    results = sorted(results, key=lambda x: abs(x['相关系数']), reverse=True)
    
    return {
        '总体良率趋势': daily_yield.to_dict('records'),
        '根因分析结果': results,
        '分析周期': {
            '开始日期': str(daily_yield['日期'].min()) if len(daily_yield) > 0 else None,
            '结束日期': str(daily_yield['日期'].max()) if len(daily_yield) > 0 else None,
        }
    }


def analyze_temperature_factor(daily_yield, factor_data, line=None):
    if len(daily_yield) < 5:
        return None
    
    env_data = factor_data['env_data']
    temps = []
    yields = []
    
    for _, row in daily_yield.iterrows():
        d = row['日期']
        if line:
            key = (d, line)
            if key in env_data:
                temps.append(env_data[key]['温度'])
                yields.append(row['良率(%)'])
        else:
            line_temps = []
            for ln in LINES:
                key = (d, ln)
                if key in env_data:
                    line_temps.append(env_data[key]['温度'])
            if line_temps:
                temps.append(np.mean(line_temps))
                yields.append(row['良率(%)'])
    
    if len(temps) < 5:
        return None
    
    try:
        corr, p_value = stats.pearsonr(temps, yields)
    except Exception:
        corr = 0
        p_value = 1
    
    return {
        '因子': '温度',
        '类别': '环境',
        '相关系数': round(corr, 4),
        'p值': round(p_value, 4),
        '影响方向': '正相关（温度越高良率越高）' if corr > 0 else '负相关（温度越高良率越低）',
        '影响程度': _get_correlation_level(abs(corr)),
        '描述': f'温度与良率的皮尔逊相关系数为 {round(corr, 4)}，{_get_correlation_level(abs(corr))}程度相关。',
        '数据点': len(temps),
    }


def analyze_humidity_factor(daily_yield, factor_data, line=None):
    if len(daily_yield) < 5:
        return None
    
    env_data = factor_data['env_data']
    humidity_values = []
    yields = []
    
    for _, row in daily_yield.iterrows():
        d = row['日期']
        if line:
            key = (d, line)
            if key in env_data:
                humidity_values.append(env_data[key]['湿度'])
                yields.append(row['良率(%)'])
        else:
            line_humidity = []
            for ln in LINES:
                key = (d, ln)
                if key in env_data:
                    line_humidity.append(env_data[key]['湿度'])
            if line_humidity:
                humidity_values.append(np.mean(line_humidity))
                yields.append(row['良率(%)'])
    
    if len(humidity_values) < 5:
        return None
    
    try:
        corr, p_value = stats.pearsonr(humidity_values, yields)
    except Exception:
        corr = 0
        p_value = 1
    
    return {
        '因子': '湿度',
        '类别': '环境',
        '相关系数': round(corr, 4),
        'p值': round(p_value, 4),
        '影响方向': '正相关（湿度越高良率越高）' if corr > 0 else '负相关（湿度越高良率越低）',
        '影响程度': _get_correlation_level(abs(corr)),
        '描述': f'湿度与良率的皮尔逊相关系数为 {round(corr, 4)}，{_get_correlation_level(abs(corr))}程度相关。',
        '数据点': len(humidity_values),
    }


def analyze_mold_factor(filtered_df):
    df = filtered_df.copy()
    
    mold_yield = calculate_yield(df, group_cols=['模具型号'])
    mold_yield = mold_yield[~mold_yield['小样本标记']]
    
    if len(mold_yield) < 2:
        return None
    
    best_mold = mold_yield.loc[mold_yield['良率(%)'].idxmax()]
    worst_mold = mold_yield.loc[mold_yield['良率(%)'].idxmin()]
    yield_diff = best_mold['良率(%)'] - worst_mold['良率(%)']
    
    max_yield = mold_yield['良率(%)'].max()
    min_yield = mold_yield['良率(%)'].min()
    range_pct = (max_yield - min_yield) / max_yield * 100 if max_yield > 0 else 0
    
    return {
        '因子': '模具型号',
        '类别': '模具',
        '相关系数': round(range_pct / 100, 4),
        'p值': None,
        '影响方向': f'{worst_mold["模具型号"]} 表现最差',
        '影响程度': _get_correlation_level(range_pct / 100),
        '描述': f'不同模具型号的良率差异为 {round(yield_diff, 2)}%，最佳模具 {best_mold["模具型号"]}（{best_mold["良率(%)"]}%），最差模具 {worst_mold["模具型号"]}（{worst_mold["良率(%)"]}%）。',
        '详细数据': mold_yield.to_dict('records'),
        '数据点': len(mold_yield),
    }


def analyze_material_factor(filtered_df):
    df = filtered_df.copy()
    
    material_yield = calculate_yield(df, group_cols=['原料批次'])
    material_yield = material_yield[~material_yield['小样本标记']]
    
    if len(material_yield) < 2:
        return None
    
    best_batch = material_yield.loc[material_yield['良率(%)'].idxmax()]
    worst_batch = material_yield.loc[material_yield['良率(%)'].idxmin()]
    yield_diff = best_batch['良率(%)'] - worst_batch['良率(%)']
    
    max_yield = material_yield['良率(%)'].max()
    min_yield = material_yield['良率(%)'].min()
    range_pct = (max_yield - min_yield) / max_yield * 100 if max_yield > 0 else 0
    
    return {
        '因子': '原料批次',
        '类别': '原料',
        '相关系数': round(range_pct / 100, 4),
        'p值': None,
        '影响方向': f'{worst_batch["原料批次"]} 批次表现最差',
        '影响程度': _get_correlation_level(range_pct / 100),
        '描述': f'不同原料批次的良率差异为 {round(yield_diff, 2)}%，最佳批次 {best_batch["原料批次"]}（{best_batch["良率(%)"]}%），最差批次 {worst_batch["原料批次"]}（{worst_batch["良率(%)"]}%）。',
        '详细数据': material_yield.to_dict('records'),
        '数据点': len(material_yield),
    }


def analyze_equipment_factor(daily_yield, factor_data, filtered_df):
    equipment_faults = factor_data['equipment_faults']
    
    total_fault_hours = {}
    for eq, faults in equipment_faults.items():
        total_fault_hours[eq] = sum(f['故障时长(小时)'] for f in faults)
    
    eq_yield = calculate_yield(filtered_df, group_cols=['设备'])
    eq_yield = eq_yield[~eq_yield['小样本标记']]
    
    if len(eq_yield) < 2:
        return None
    
    eq_yield_list = []
    for _, row in eq_yield.iterrows():
        eq = row['设备']
        fault_hours = total_fault_hours.get(eq, 0)
        eq_yield_list.append({
            '设备': eq,
            '良率(%)': row['良率(%)'],
            '故障小时': fault_hours,
        })
    
    if len(eq_yield_list) < 2:
        return None
    
    sorted_eqs = sorted(eq_yield_list, key=lambda x: x['故障小时'])
    mid = len(sorted_eqs) // 2
    low_fault_group = sorted_eqs[:mid]
    high_fault_group = sorted_eqs[mid:]
    
    if len(low_fault_group) == 0 or len(high_fault_group) == 0:
        return None
    
    no_fault_yields = [x['良率(%)'] for x in low_fault_group]
    fault_yields = [x['良率(%)'] for x in high_fault_group]
    
    avg_no_fault = np.mean(no_fault_yields)
    avg_fault = np.mean(fault_yields)
    diff = avg_no_fault - avg_fault
    
    try:
        t_stat, p_value = stats.ttest_ind(fault_yields, no_fault_yields, equal_var=False)
    except Exception:
        p_value = 1.0
    
    worst_eq = max(eq_yield_list, key=lambda x: x['故障小时'])
    best_eq = min(eq_yield_list, key=lambda x: x['故障小时'])
    
    return {
        '因子': '设备故障',
        '类别': '设备',
        '相关系数': round(abs(diff) / 100, 4),
        'p值': round(float(p_value), 4),
        '影响方向': f'{worst_eq["设备"]} 故障最多({round(worst_eq["故障小时"],1)}h)表现最差' if diff > 0 else f'{best_eq["设备"]} 故障最少({round(best_eq["故障小时"],1)}h)表现最差',
        '影响程度': _get_correlation_level(abs(diff) / 10),
        '描述': f'高故障组({len(fault_yields)}台)平均良率 {round(avg_fault, 2)}%，低故障组({len(no_fault_yields)}台)平均良率 {round(avg_no_fault, 2)}%，差异 {round(abs(diff), 2)}%。分组依据: 按设备累计故障时长中位数二分。',
        '详细数据': eq_yield.to_dict('records'),
        '数据点': len(eq_yield_list),
    }


def analyze_operator_factor(filtered_df):
    df = filtered_df.copy()
    
    op_yield = calculate_yield(df, group_cols=['操作工'])
    op_yield = op_yield[~op_yield['小样本标记']]
    
    if len(op_yield) < 2:
        return None
    
    best_op = op_yield.loc[op_yield['良率(%)'].idxmax()]
    worst_op = op_yield.loc[op_yield['良率(%)'].idxmin()]
    yield_diff = best_op['良率(%)'] - worst_op['良率(%)']
    
    max_yield = op_yield['良率(%)'].max()
    min_yield = op_yield['良率(%)'].min()
    range_pct = (max_yield - min_yield) / max_yield * 100 if max_yield > 0 else 0
    
    return {
        '因子': '操作员',
        '类别': '人员',
        '相关系数': round(range_pct / 100, 4),
        'p值': None,
        '影响方向': f'{worst_op["操作工"]} 操作良率最低',
        '影响程度': _get_correlation_level(range_pct / 100),
        '描述': f'不同操作员的良率差异为 {round(yield_diff, 2)}%，最佳操作员 {best_op["操作工"]}（{best_op["良率(%)"]}%），最差操作员 {worst_op["操作工"]}（{worst_op["良率(%)"]}%）。',
        '详细数据': op_yield.to_dict('records'),
        '数据点': len(op_yield),
    }


def _get_correlation_level(corr):
    if corr >= 0.7:
        return '强'
    elif corr >= 0.4:
        return '中等'
    elif corr >= 0.2:
        return '弱'
    else:
        return '极弱'


def analyze_custom_factor(factor_key, line=None, product=None):
    df = get_production_data()
    factor_data = get_factor_data()
    
    filtered_df = df.copy()
    if line:
        filtered_df = filtered_df[filtered_df['产线'] == line]
    if product:
        filtered_df = filtered_df[filtered_df['产品型号'] == product]
    
    factor_map = {
        'temperature': '温度',
        'humidity': '湿度',
        'mold_usage': '模具使用次数',
        'material_batch': '原料批次',
        'equipment_fault': '设备故障',
        'operator': '操作工',
        'shift': '班次',
        'line': '产线',
        'mold_type': '模具型号',
    }
    
    if factor_key not in factor_map:
        return None
    
    factor_name = factor_map[factor_key]
    
    if factor_key in ['material_batch', 'operator', 'shift', 'line', 'mold_type']:
        col_map = {
            'material_batch': '原料批次',
            'operator': '操作工',
            'shift': '班次',
            'line': '产线',
            'mold_type': '模具型号',
        }
        col = col_map[factor_key]
        result = calculate_yield(filtered_df, group_cols=[col])
        result = result[~result['小样本标记']]
        
        return {
            'factor': factor_name,
            'factor_type': 'categorical',
            'factor_key': factor_key,
            'category_col': col,
            'data': result.to_dict('records'),
        }
    elif factor_key in ['temperature', 'humidity']:
        daily_yield = calculate_yield_by_time(filtered_df, granularity='day')
        daily_yield = daily_yield[~daily_yield['小样本标记']]
        daily_yield['日期'] = pd.to_datetime(daily_yield['时间粒度']).dt.date
        
        env_data = factor_data['env_data']
        scatter_data = []
        
        for _, row in daily_yield.iterrows():
            d = row['日期']
            if line:
                key = (d, line)
                if key in env_data:
                    val = env_data[key]['温度'] if factor_key == 'temperature' else env_data[key]['湿度']
                    scatter_data.append({
                        '日期': str(d),
                        '因子值': round(val, 2),
                        '良率(%)': row['良率(%)'],
                    })
            else:
                vals = []
                for ln in LINES:
                    key = (d, ln)
                    if key in env_data:
                        vals.append(env_data[key]['温度'] if factor_key == 'temperature' else env_data[key]['湿度'])
                if vals:
                    scatter_data.append({
                        '日期': str(d),
                        '因子值': round(np.mean(vals), 2),
                        '良率(%)': row['良率(%)'],
                    })
        
        return {
            'factor': factor_name,
            'factor_type': 'continuous',
            'factor_key': factor_key,
            'scatter_data': scatter_data,
        }
    
    return None


def get_factor_correlation_matrix(line=None, product=None):
    result = analyze_root_causes(line=line, product=product)
    factors = result['根因分析结果']
    
    matrix = []
    for f in factors:
        matrix.append({
            '因子': f['因子'],
            '类别': f['类别'],
            '相关系数': f['相关系数'],
            '影响程度': f['影响程度'],
            '影响方向': f['影响方向'],
        })
    
    return matrix
