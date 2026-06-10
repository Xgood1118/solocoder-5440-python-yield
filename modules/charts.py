import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']


def _fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_base64


def plot_yield_trend(trend_data, title='良率趋势图'):
    fig, ax = plt.subplots(figsize=(10, 5))
    
    x = range(len(trend_data))
    y = [d['良率(%)'] for d in trend_data]
    labels = [str(d['时间粒度']) for d in trend_data]
    
    ax.plot(x, y, marker='o', linewidth=2, color=COLORS[0], label='良率')
    
    if '控制上限(UCL)' in trend_data[0]:
        ucl = trend_data[0]['控制上限(UCL)']
        lcl = trend_data[0]['控制下限(LCL)']
        mean_val = trend_data[0]['历史均值']
        ax.axhline(y=ucl, color='red', linestyle='--', alpha=0.7, label=f'UCL ({ucl}%)')
        ax.axhline(y=lcl, color='red', linestyle='--', alpha=0.7, label=f'LCL ({lcl}%)')
        ax.axhline(y=mean_val, color='green', linestyle='-.', alpha=0.7, label=f'均值 ({mean_val}%)')
    
    anomalies = [(i, d['良率(%)']) for i, d in enumerate(trend_data) if d.get('异常标记', False)]
    if anomalies:
        anom_x, anom_y = zip(*anomalies)
        ax.scatter(anom_x, anom_y, color='red', s=100, zorder=5, label='异常点')
    
    ax.set_xlabel('时间', fontsize=12)
    ax.set_ylabel('良率 (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylim(bottom=min(y) - 5 if y else 80, top=100)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    if len(labels) > 15:
        step = len(labels) // 10
        ax.set_xticks(x[::step])
        ax.set_xticklabels(labels[::step], rotation=45, ha='right')
    else:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
    
    plt.tight_layout()
    return _fig_to_base64(fig)


def plot_yield_bar(data, category_col, value_col='良率(%)', title='良率对比图'):
    fig, ax = plt.subplots(figsize=(10, 5))
    
    categories = [d[category_col] for d in data]
    values = [d[value_col] for d in data]
    
    colors = [COLORS[i % len(COLORS)] for i in range(len(categories))]
    
    bars = ax.bar(categories, values, color=colors, alpha=0.8)
    
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height + 0.3,
                f'{val}%', ha='center', va='bottom', fontsize=10)
    
    ax.set_xlabel(category_col, fontsize=12)
    ax.set_ylabel('良率 (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylim(bottom=min(values) - 5 if values else 80, top=100)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return _fig_to_base64(fig)


def plot_yield_boxplot(data_by_group, title='良率分布箱线图'):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    groups = list(data_by_group.keys())
    data = [data_by_group[g] for g in groups]
    
    bp = ax.boxplot(data, patch_artist=True, labels=groups)
    
    for patch, color in zip(bp['boxes'], COLORS):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    
    ax.set_ylabel('良率 (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return _fig_to_base64(fig)


def plot_pareto(defect_data, title='不良原因帕累托图'):
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    categories = [d['不良项目分类'] for d in defect_data]
    counts = [d['不良数'] for d in defect_data]
    cumulative = [d['累计占比(%)'] for d in defect_data]
    
    x = range(len(categories))
    
    bars = ax1.bar(x, counts, color=COLORS[0], alpha=0.7, label='不良数')
    ax1.set_xlabel('不良项目', fontsize=12)
    ax1.set_ylabel('不良数', fontsize=12, color=COLORS[0])
    ax1.tick_params(axis='y', labelcolor=COLORS[0])
    
    ax2 = ax1.twinx()
    ax2.plot(x, cumulative, color=COLORS[1], marker='o', linewidth=2, label='累计占比')
    ax2.set_ylabel('累计占比 (%)', fontsize=12, color=COLORS[1])
    ax2.tick_params(axis='y', labelcolor=COLORS[1])
    ax2.set_ylim(0, 110)
    ax2.axhline(y=80, color='red', linestyle='--', alpha=0.7, label='80%线')
    
    for bar, val in zip(bars, counts):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2., height + max(counts) * 0.02,
                str(val), ha='center', va='bottom', fontsize=9)
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, rotation=45, ha='right')
    ax1.set_title(title, fontsize=14, fontweight='bold')
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='center right')
    
    plt.tight_layout()
    return _fig_to_base64(fig)


def plot_fmea_rpn(fmea_data, top_n=10, title='FMEA 风险优先数 (RPN)'):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    data = fmea_data[:top_n]
    modes = [d['失效模式'] for d in data]
    rpn_vals = [d['RPN'] for d in data]
    severity = [d['严重度S'] for d in data]
    occurrence = [d['发生率O'] for d in data]
    detection = [d['探测度D'] for d in data]
    
    y = range(len(modes))
    
    ax.barh(y, rpn_vals, color=COLORS[0], alpha=0.7, label='RPN')
    
    for i, (rpn, s, o, d_val) in enumerate(zip(rpn_vals, severity, occurrence, detection)):
        ax.text(rpn + max(rpn_vals) * 0.02, i,
                f'{rpn} (S={s}, O={o}, D={d_val})',
                va='center', fontsize=9)
    
    ax.set_yticks(y)
    ax.set_yticklabels(modes)
    ax.set_xlabel('RPN 值', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()
    
    plt.tight_layout()
    return _fig_to_base64(fig)


def plot_process_chain(process_data, product_name, title=None):
    if title is None:
        title = f'{product_name} 工序良率链'
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), 
                                   gridspec_kw={'width_ratios': [2, 1]})
    
    processes = [d['工序'] for d in process_data]
    single_yields = [d['单工序良率(%)'] for d in process_data]
    cumulative_yields = [d['累计良率(%)'] for d in process_data]
    
    x = range(len(processes))
    
    colors = [COLORS[1] if y == min(single_yields) else COLORS[0] for y in single_yields]
    
    bars = ax1.bar(x, single_yields, color=colors, alpha=0.7, label='单工序良率')
    ax1.plot(x, cumulative_yields, color=COLORS[2], marker='s', linewidth=2, 
             label='累计良率', markersize=8)
    
    for bar, val in zip(bars, single_yields):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2., height + 0.2,
                f'{val}%', ha='center', va='bottom', fontsize=9)
    
    for xi, val in zip(x, cumulative_yields):
        ax1.text(xi, val + 0.5, f'{val}%', ha='center', va='bottom', 
                fontsize=9, color=COLORS[2])
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(processes, rotation=30, ha='right')
    ax1.set_ylabel('良率 (%)', fontsize=11)
    ax1.set_title('各工序良率', fontsize=12, fontweight='bold')
    ax1.set_ylim(bottom=min(single_yields) - 5, top=100)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.legend(loc='lower left')
    
    final_yield = cumulative_yields[-1]
    bottleneck_idx = single_yields.index(min(single_yields))
    bottleneck = processes[bottleneck_idx]
    
    info_text = (
        f'最终良率: {final_yield}%\n'
        f'瓶颈工序: {bottleneck}\n'
        f'瓶颈良率: {min(single_yields)}%\n'
        f'工序总数: {len(processes)}道'
    )
    ax2.text(0.1, 0.5, info_text, fontsize=11, va='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax2.set_axis_off()
    ax2.set_title('关键指标', fontsize=12, fontweight='bold')
    
    fig.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    return _fig_to_base64(fig)


def plot_factor_scatter(x_data, y_data, x_label, y_label, title='因子-良率散点图'):
    fig, ax = plt.subplots(figsize=(8, 5))
    
    ax.scatter(x_data, y_data, color=COLORS[0], alpha=0.6, s=50)
    
    if len(x_data) > 1:
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        x_sorted = sorted(x_data)
        ax.plot(x_sorted, p(x_sorted), color='red', linestyle='--', 
                label=f'趋势线 (y={z[0]:.2f}x+{z[1]:.2f})', alpha=0.7)
    
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    return _fig_to_base64(fig)


def plot_factor_correlation_bar(correlation_data, title='因子相关性分析'):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    factors = [d['因子'] for d in correlation_data]
    corr_values = [abs(d['相关系数']) for d in correlation_data]
    colors = ['red' if v >= 0.4 else 'orange' if v >= 0.2 else 'green' for v in corr_values]
    
    bars = ax.barh(factors, corr_values, color=colors, alpha=0.7)
    
    for bar, val in zip(bars, corr_values):
        width = bar.get_width()
        ax.text(width + 0.01, bar.get_y() + bar.get_height() / 2,
                f'{val:.3f}', ha='left', va='center', fontsize=10)
    
    ax.axvline(x=0.4, color='red', linestyle='--', alpha=0.5, label='中等相关阈值(0.4)')
    ax.axvline(x=0.7, color='darkred', linestyle='--', alpha=0.5, label='强相关阈值(0.7)')
    
    ax.set_xlabel('相关系数 (绝对值)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.legend(loc='lower right')
    ax.invert_yaxis()
    
    plt.tight_layout()
    return _fig_to_base64(fig)


def plot_multi_line_trend(lines_data, title='多产线良率对比趋势', x_label='时间', y_label='良率 (%)'):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for i, (name, data) in enumerate(lines_data.items()):
        x = range(len(data))
        y = data
        ax.plot(x, y, marker='o', linewidth=2, color=COLORS[i % len(COLORS)], label=name, markersize=4)
    
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.set_ylim(bottom=80, top=100)
    
    plt.tight_layout()
    return _fig_to_base64(fig)
