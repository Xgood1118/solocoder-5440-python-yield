import pandas as pd
import numpy as np
from modules.data_source import get_production_data, get_quality_data

SMALL_SAMPLE_THRESHOLD = 20


def calculate_yield(df, group_cols=None, filter_conditions=None):
    data = df.copy()
    
    if filter_conditions:
        for col, value in filter_conditions.items():
            if isinstance(value, list):
                data = data[data[col].isin(value)]
            else:
                data = data[data[col] == value]
    
    if group_cols is None:
        total_qty = data['实际完成数量'].sum()
        pass_qty = data['合格数量'].sum()
        yield_rate = (pass_qty / total_qty * 100) if total_qty > 0 else 0
        is_small_sample = total_qty < SMALL_SAMPLE_THRESHOLD
        return {
            '总数量': total_qty,
            '合格数量': pass_qty,
            '良率(%)': round(yield_rate, 2),
            '小样本标记': is_small_sample,
            '备注': '样本量过小，统计意义不足' if is_small_sample else ''
        }
    
    grouped = data.groupby(group_cols).agg(
        总数量=('实际完成数量', 'sum'),
        合格数量=('合格数量', 'sum'),
        工单数=('工单号', 'count')
    ).reset_index()
    
    grouped['良率(%)'] = np.where(
        grouped['总数量'] > 0,
        round(grouped['合格数量'] / grouped['总数量'] * 100, 2),
        0
    )
    grouped['小样本标记'] = grouped['总数量'] < SMALL_SAMPLE_THRESHOLD
    grouped['备注'] = np.where(
        grouped['小样本标记'],
        '样本量过小，统计意义不足',
        ''
    )
    
    return grouped


def calculate_yield_by_time(df, granularity='day', group_cols=None, filter_conditions=None):
    data = df.copy()
    data['生产时间'] = pd.to_datetime(data['生产时间'])
    
    if filter_conditions:
        for col, value in filter_conditions.items():
            if isinstance(value, list):
                data = data[data[col].isin(value)]
            else:
                data = data[data[col] == value]
    
    if granularity == 'day':
        data['时间粒度'] = data['生产时间'].dt.date
    elif granularity == 'week':
        data['时间粒度'] = data['生产时间'].dt.isocalendar().week.astype(str) + '周'
        data['年份'] = data['生产时间'].dt.year
        data['时间粒度'] = data['年份'].astype(str) + '年第' + data['时间粒度']
    elif granularity == 'month':
        data['时间粒度'] = data['生产时间'].dt.strftime('%Y年%m月')
    else:
        raise ValueError(f"不支持的时间粒度: {granularity}")
    
    all_group_cols = ['时间粒度']
    if group_cols:
        all_group_cols.extend(group_cols)
    
    result = calculate_yield(data, group_cols=all_group_cols)
    return result


def detect_anomalies(yield_series, sigma_threshold=3):
    values = yield_series.values
    mean = np.mean(values)
    std = np.std(values)
    
    if std == 0:
        return [False] * len(values), mean, std
    
    anomalies = np.abs(values - mean) > sigma_threshold * std
    return anomalies.tolist(), mean, std


def get_yield_trend(line=None, product=None, worker=None, granularity='day', sigma_threshold=3.0):
    df = get_production_data()
    
    filters = {}
    if line:
        filters['产线'] = line
    if product:
        filters['产品型号'] = product
    if worker:
        filters['操作工'] = worker
    
    trend_data = calculate_yield_by_time(df, granularity=granularity, filter_conditions=filters if filters else None)
    
    if len(trend_data) > 0:
        anomalies, mean_val, std_val = detect_anomalies(
            trend_data['良率(%)'], 
            sigma_threshold=sigma_threshold
        )
        trend_data['异常标记'] = anomalies
        trend_data['历史均值'] = round(mean_val, 2)
        trend_data['标准差'] = round(std_val, 2)
        trend_data['σ倍数'] = sigma_threshold
        trend_data['控制上限(UCL)'] = round(mean_val + sigma_threshold * std_val, 2)
        trend_data['控制下限(LCL)'] = round(mean_val - sigma_threshold * std_val, 2)
    else:
        trend_data['异常标记'] = False
        trend_data['历史均值'] = 0
        trend_data['标准差'] = 0
        trend_data['控制上限(UCL)'] = 0
        trend_data['控制下限(LCL)'] = 0
    
    return trend_data


def get_yield_by_dimension(dimension):
    df = get_production_data()
    
    valid_dimensions = ['产线', '产品型号', '班次', '操作工']
    if dimension not in valid_dimensions:
        raise ValueError(f"维度必须是以下之一: {valid_dimensions}")
    
    result = calculate_yield(df, group_cols=[dimension])
    result = result.sort_values('良率(%)', ascending=False).reset_index(drop=True)
    return result


def get_yield_by_combination(combinations):
    df = get_production_data()
    
    valid_cols = ['产线', '产品型号', '班次', '操作工']
    for col in combinations:
        if col not in valid_cols:
            raise ValueError(f"无效的组合维度: {col}")
    
    result = calculate_yield(df, group_cols=combinations)
    result = result.sort_values('良率(%)', ascending=False).reset_index(drop=True)
    return result


def compare_lines(product=None):
    df = get_production_data()
    filters = {}
    if product:
        filters['产品型号'] = product
    
    result = calculate_yield(df, group_cols=['产线'], filter_conditions=filters)
    result = result.sort_values('良率(%)', ascending=False).reset_index(drop=True)
    return result


def compare_shifts(line=None, product=None):
    df = get_production_data()
    filters = {}
    if line:
        filters['产线'] = line
    if product:
        filters['产品型号'] = product
    
    result = calculate_yield(df, group_cols=['班次'], filter_conditions=filters)
    shift_order = ['早班', '中班', '晚班']
    result['班次'] = pd.Categorical(result['班次'], categories=shift_order, ordered=True)
    result = result.sort_values('班次').reset_index(drop=True)
    return result


def compare_workers(line=None, product=None):
    df = get_production_data()
    filters = {}
    if line:
        filters['产线'] = line
    if product:
        filters['产品型号'] = product
    
    result = calculate_yield(df, group_cols=['操作工'], filter_conditions=filters)
    result = result.sort_values('良率(%)', ascending=False).reset_index(drop=True)
    return result


def get_worker_trend(worker, granularity='day'):
    df = get_production_data()
    df = df[df['操作工'] == worker]
    
    if len(df) == 0:
        return pd.DataFrame()
    
    trend_data = calculate_yield_by_time(df, granularity=granularity)
    
    if len(trend_data) > 1:
        anomalies, mean_val, std_val = detect_anomalies(
            trend_data['良率(%)'], 
            sigma_threshold=3
        )
        trend_data['异常标记'] = anomalies
        trend_data['历史均值'] = round(mean_val, 2)
    else:
        trend_data['异常标记'] = False
        trend_data['历史均值'] = trend_data['良率(%)'].iloc[0] if len(trend_data) > 0 else 0
    
    return trend_data


def get_summary_stats():
    df = get_production_data()
    overall = calculate_yield(df)
    
    by_line = calculate_yield(df, group_cols=['产线'])
    by_product = calculate_yield(df, group_cols=['产品型号'])
    
    return {
        '总体良率': overall,
        '按产线': by_line.to_dict('records'),
        '按产品': by_product.to_dict('records'),
        '总工单数': len(df),
        '总生产数量': int(df['实际完成数量'].sum()),
        '总合格数量': int(df['合格数量'].sum()),
    }


def get_small_sample_records():
    df = get_production_data()
    df['小样本'] = df['实际完成数量'] < SMALL_SAMPLE_THRESHOLD
    small_samples = df[df['小样本']].copy()
    return small_samples
