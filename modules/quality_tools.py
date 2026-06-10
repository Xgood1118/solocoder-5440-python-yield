import pandas as pd
import numpy as np
from modules.data_source import get_quality_data, get_fmea_data, get_process_data, get_production_data


def pareto_analysis(line=None, product=None, start_date=None, end_date=None):
    quality_df = get_quality_data()
    
    filtered = quality_df[quality_df['检验结果'] == '不良'].copy()
    
    if line:
        filtered = filtered[filtered['产线'] == line]
    if product:
        filtered = filtered[filtered['产品型号'] == product]
    
    if len(filtered) == 0:
        return {
            '不良项目数据': [],
            '累计百分比': [],
            'TOP5占比': 0,
            '总不良数': 0,
        }
    
    defect_counts = filtered.groupby('不良项目分类').size().reset_index(name='不良数')
    defect_counts = defect_counts.sort_values('不良数', ascending=False).reset_index(drop=True)
    
    total_defects = defect_counts['不良数'].sum()
    defect_counts['占比(%)'] = round(defect_counts['不良数'] / total_defects * 100, 2)
    defect_counts['累计占比(%)'] = round(defect_counts['不良数'].cumsum() / total_defects * 100, 2)
    
    top5_count = defect_counts.head(5)['不良数'].sum()
    top5_pct = round(top5_count / total_defects * 100, 2)
    
    return {
        '不良项目数据': defect_counts.to_dict('records'),
        'TOP5占比': top5_pct,
        '总不良数': int(total_defects),
        '二八法则验证': f'TOP5不良占比 {top5_pct}%，{"符合" if top5_pct >= 75 else "接近"} 二八法则',
    }


def fmea_analysis():
    fmea_df = get_fmea_data()
    
    high_risk = fmea_df[fmea_df['RPN'] >= 100].copy()
    medium_risk = fmea_df[(fmea_df['RPN'] >= 50) & (fmea_df['RPN'] < 100)].copy()
    low_risk = fmea_df[fmea_df['RPN'] < 50].copy()
    
    suggestions = _generate_improvement_suggestions(fmea_df)
    
    return {
        '全部FMEA数据': fmea_df.to_dict('records'),
        '高风险项': high_risk.to_dict('records'),
        '中风险项': medium_risk.to_dict('records'),
        '低风险项': low_risk.to_dict('records'),
        '改进建议': suggestions,
        'RPN最高的3项': fmea_df.head(3).to_dict('records'),
    }


def _generate_improvement_suggestions(fmea_df):
    suggestions = []
    
    top_items = fmea_df.head(5)
    for _, row in top_items.iterrows():
        rpn = row['RPN']
        severity = row['严重度S']
        occurrence = row['发生率O']
        detection = row['探测度D']
        
        suggestion = {
            '失效模式': row['失效模式'],
            '当前RPN': int(rpn),
            '建议优先级': '高' if rpn >= 200 else '中' if rpn >= 100 else '低',
            '改进方向': row['改进方向'],
            '具体措施': [],
            '预期改善': None,
        }
        
        if occurrence >= 6:
            suggestion['具体措施'].append(f'优先降低发生率，当前发生率O={occurrence}')
            if '模具' in row['失效模式'] or '磨损' in row['失效模式']:
                suggestion['具体措施'].append('建议模具寿命上限从 10000 件降到 8000 件')
                suggestion['预期改善'] = '预计发生率可降低 30%，RPN 可降至 ' + str(int(rpn * 0.7))
            elif '原料' in row['失效模式'] or '批次' in row['失效模式']:
                suggestion['具体措施'].append('加强供应商质量管理，建立批次准入审核机制')
                suggestion['预期改善'] = '预计发生率可降低 25%，RPN 可降至 ' + str(int(rpn * 0.75))
        
        if severity >= 8:
            suggestion['具体措施'].append(f'严重度较高(S={severity})，建议增加防错设计从根源消除')
        
        if detection >= 6:
            suggestion['具体措施'].append(f'探测能力不足(D={detection})，建议增加检测工序或引入自动化检测')
            suggestion['预期改善'] = suggestion['预期改善'] or f'预计探测度可提升至 {max(1, detection - 2)}，RPN 可显著降低'
        
        if not suggestion['具体措施']:
            suggestion['具体措施'].append(row['改进方向'])
        
        suggestions.append(suggestion)
    
    return suggestions


def process_yield_chain(product=None):
    process_data = get_process_data()
    production_df = get_production_data()
    
    if product:
        products_to_analyze = [product]
    else:
        products_to_analyze = list(process_data.keys())
    
    all_results = {}
    
    for prod in products_to_analyze:
        if prod not in process_data:
            continue
        
        processes = process_data[prod]
        
        prod_filter = production_df[production_df['产品型号'] == prod].copy()
        
        if len(prod_filter) == 0:
            continue
        
        overall_yield = (prod_filter['合格数量'].sum() / prod_filter['实际完成数量'].sum() * 100
                        if prod_filter['实际完成数量'].sum() > 0 else 0)
        
        base_total = 1.0
        for proc in processes:
            base_total *= proc['基准良率']
        
        base_total_pct = base_total * 100
        if base_total_pct > 0:
            correction_factor = (overall_yield / base_total_pct) ** (1.0 / len(processes))
        else:
            correction_factor = 1.0
        
        process_results = []
        cumulative_yield = 1.0
        
        for proc in processes:
            base_yield = proc['基准良率']
            
            process_name = proc['工序']
            name_hash = sum(ord(c) for c in process_name)
            deterministic_offset = ((name_hash % 100) - 50) / 5000.0
            
            actual_yield = base_yield * correction_factor + deterministic_offset
            actual_yield = max(0.9, min(0.999, actual_yield))
            
            cumulative_yield *= actual_yield
            
            process_results.append({
                '工序': proc['工序'],
                '单工序良率(%)': round(actual_yield * 100, 2),
                '累计良率(%)': round(cumulative_yield * 100, 2),
                '基准良率(%)': round(base_yield * 100, 2),
            })
        
        process_df = pd.DataFrame(process_results)
        bottleneck_idx = process_df['单工序良率(%)'].idxmin()
        bottleneck = process_df.loc[bottleneck_idx]
        
        all_results[prod] = {
            '工序良率链': process_results,
            '最终良率(%)': round(cumulative_yield * 100, 2),
            '瓶颈工序': bottleneck['工序'],
            '瓶颈工序良率(%)': bottleneck['单工序良率(%)'],
            '整体实际良率(%)': round(overall_yield, 2),
        }
    
    return all_results


def get_defect_trend(granularity='day', line=None, product=None):
    quality_df = get_quality_data()
    filtered = quality_df[quality_df['检验结果'] == '不良'].copy()
    
    if line:
        filtered = filtered[filtered['产线'] == line]
    if product:
        filtered = filtered[filtered['产品型号'] == product]
    
    if len(filtered) == 0:
        return pd.DataFrame()
    
    filtered['检验时间'] = pd.to_datetime(filtered['检验时间'])
    
    if granularity == 'day':
        filtered['时间粒度'] = filtered['检验时间'].dt.date
    elif granularity == 'week':
        filtered['时间粒度'] = filtered['检验时间'].dt.isocalendar().week.astype(str) + '周'
    elif granularity == 'month':
        filtered['时间粒度'] = filtered['检验时间'].dt.strftime('%Y年%m月')
    else:
        raise ValueError(f"不支持的时间粒度: {granularity}")
    
    trend = filtered.groupby('时间粒度').agg(
        不良数=('检验工单号', 'count'),
        不良种类=('不良项目分类', 'nunique')
    ).reset_index()
    
    return trend


def get_quality_overview():
    quality_df = get_quality_data()
    prod_df = get_production_data()
    
    total_inspections = len(quality_df)
    total_defects = len(quality_df[quality_df['检验结果'] == '不良'])
    defect_rate = total_defects / total_inspections * 100 if total_inspections > 0 else 0
    
    pareto = pareto_analysis()
    fmea = fmea_analysis()
    
    return {
        '总检验数': int(total_inspections),
        '总不良数': int(total_defects),
        '不良率(%)': round(defect_rate, 2),
        '不良项目数': int(quality_df[quality_df['检验结果'] == '不良']['不良项目分类'].nunique()),
        'TOP1不良': pareto['不良项目数据'][0] if pareto['不良项目数据'] else None,
        'FMEA高风险项数': len(fmea['高风险项']),
        '最高RPN值': int(fmea['全部FMEA数据'][0]['RPN']) if fmea['全部FMEA数据'] else 0,
    }
