import io
import datetime
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from modules.yield_engine import (
    get_yield_trend, get_yield_by_dimension, get_summary_stats,
    compare_lines, compare_shifts, get_small_sample_records
)
from modules.root_cause import analyze_root_causes, get_factor_correlation_matrix
from modules.quality_tools import pareto_analysis, fmea_analysis, process_yield_chain
from modules.charts import (
    plot_yield_trend, plot_yield_bar, plot_pareto,
    plot_fmea_rpn, plot_process_chain, plot_factor_correlation_bar
)


def _register_font():
    try:
        pdfmetrics.registerFont(TTFont('SimHei', 'C:/Windows/Fonts/simhei.ttf'))
        return 'SimHei'
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont('MicrosoftYaHei', 'C:/Windows/Fonts/msyh.ttc'))
            return 'MicrosoftYaHei'
        except Exception:
            return 'Helvetica'


FONT_NAME = _register_font()


def _get_styles():
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=FONT_NAME,
        fontSize=20,
        leading=24,
        spaceAfter=20,
        textColor=colors.darkblue,
        alignment=1,
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontName=FONT_NAME,
        fontSize=16,
        leading=20,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.darkblue,
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontName=FONT_NAME,
        fontSize=13,
        leading=16,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.darkslategray,
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    
    highlight_style = ParagraphStyle(
        'CustomHighlight',
        parent=styles['BodyText'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        spaceAfter=6,
        textColor=colors.red,
        backColor=colors.lightyellow,
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        fontName=FONT_NAME,
        fontSize=9,
        alignment=1,
        textColor=colors.white,
    )
    
    return {
        'title': title_style,
        'heading1': heading1_style,
        'heading2': heading2_style,
        'body': body_style,
        'highlight': highlight_style,
        'table_header': table_header_style,
    }


def generate_report(report_type='weekly', line=None, product=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    
    styles = _get_styles()
    story = []
    
    today = datetime.date.today()
    if report_type == 'weekly':
        period = f"{today - datetime.timedelta(days=7)} ~ {today}"
        title_text = f"周度良率分析报告"
    elif report_type == 'monthly':
        period = f"{today.strftime('%Y年%m月')}"
        title_text = f"月度良率分析报告"
    else:
        period = f"截至 {today}"
        title_text = f"良率分析报告"
    
    story.append(Paragraph(title_text, styles['title']))
    story.append(Paragraph(f"报告周期: {period}", styles['body']))
    
    if line:
        story.append(Paragraph(f"分析产线: {line}", styles['body']))
    if product:
        story.append(Paragraph(f"分析产品: {product}", styles['body']))
    
    story.append(Paragraph(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['body']))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.darkblue))
    story.append(Spacer(1, 0.5 * cm))
    
    story = _add_summary_section(story, styles)
    story.append(PageBreak())
    
    story = _add_yield_trend_section(story, styles, line, product)
    story.append(PageBreak())
    
    story = _add_dimension_comparison_section(story, styles, line, product)
    story.append(PageBreak())
    
    story = _add_root_cause_section(story, styles, line, product)
    story.append(PageBreak())
    
    story = _add_pareto_section(story, styles, line, product)
    story.append(PageBreak())
    
    story = _add_fmea_section(story, styles)
    story.append(PageBreak())
    
    story = _add_process_chain_section(story, styles, product)
    story.append(PageBreak())
    
    story = _add_improvement_suggestions_section(story, styles)
    story.append(PageBreak())
    
    story = _add_small_sample_note_section(story, styles)
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def _add_summary_section(story, styles):
    summary = get_summary_stats()
    
    story.append(Paragraph("一、总体概览", styles['heading1']))
    
    story.append(Paragraph("1.1 核心指标", styles['heading2']))
    
    data = [
        ['指标', '数值'],
        ['总工单数', str(summary['总工单数'])],
        ['总生产数量', f"{summary['总生产数量']:,}"],
        ['总合格数量', f"{summary['总合格数量']:,}"],
        ['总体良率', f"{summary['总体良率']['良率(%)']}%"],
    ]
    
    if summary['总体良率']['小样本标记']:
        data.append(['样本警告', '样本量过小，统计意义不足'])
    
    t = Table(data, colWidths=[8 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))
    
    story.append(Paragraph("1.2 各产线良率", styles['heading2']))
    
    line_data = summary['按产线']
    data = [['产线', '总数量', '合格数量', '良率(%)', '小样本标记']]
    for item in line_data:
        data.append([
            item['产线'],
            str(item['总数量']),
            str(item['合格数量']),
            str(item['良率(%)']),
            '是' if item['小样本标记'] else '否',
        ])
    
    t = Table(data, colWidths=[3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    
    return story


def _add_yield_trend_section(story, styles, line=None, product=None):
    story.append(Paragraph("二、良率趋势分析", styles['heading1']))
    
    story.append(Paragraph("2.1 日度良率趋势", styles['heading2']))
    
    trend_data = get_yield_trend(line=line, product=product, granularity='day')
    if len(trend_data) > 0:
        trend_list = trend_data.to_dict('records')
        img_base64 = plot_yield_trend(trend_list, title='日度良率趋势图')
        
        img_data = base64.b64decode(img_base64)
        img_file = io.BytesIO(img_data)
        img = Image(img_file, width=16 * cm, height=8 * cm)
        story.append(img)
        story.append(Spacer(1, 0.3 * cm))
        
        story.append(Paragraph("趋势说明:", styles['body']))
        mean_val = trend_data['历史均值'].iloc[0] if '历史均值' in trend_data.columns else 0
        std_val = trend_data['标准差'].iloc[0] if '标准差' in trend_data.columns else 0
        anomaly_count = trend_data['异常标记'].sum() if '异常标记' in trend_data.columns else 0
        
        story.append(Paragraph(f"· 历史平均良率: {mean_val}%", styles['body']))
        story.append(Paragraph(f"· 标准差: {std_val}%", styles['body']))
        story.append(Paragraph(f"· 异常点数量: {int(anomaly_count)} 个", styles['body']))
        if anomaly_count > 0:
            story.append(Paragraph(
                f"· 异常判定标准: 超过 ±3σ 范围（{mean_val - 3*std_val}% ~ {mean_val + 3*std_val}%）",
                styles['body']
            ))
    
    return story


def _add_dimension_comparison_section(story, styles, line=None, product=None):
    story.append(Paragraph("三、维度对比分析", styles['heading1']))
    
    story.append(Paragraph("3.1 各产线良率对比", styles['heading2']))
    
    line_compare = compare_lines(product=product)
    line_list = line_compare.to_dict('records')
    img_base64 = plot_yield_bar(line_list, '产线', title='各产线良率对比')
    
    img_data = base64.b64decode(img_base64)
    img_file = io.BytesIO(img_data)
    img = Image(img_file, width=14 * cm, height=7 * cm)
    story.append(img)
    story.append(Spacer(1, 0.3 * cm))
    
    if len(line_list) >= 2:
        best = line_list[0]
        worst = line_list[-1]
        story.append(Paragraph(
            f"产线对比: 最佳产线 {best['产线']}（{best['良率(%)']}%），"
            f"最差产线 {worst['产线']}（{worst['良率(%)']}%），"
            f"差异 {round(best['良率(%)'] - worst['良率(%)'], 2)}%",
            styles['body']
        ))
    
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("3.2 各班次良率对比", styles['heading2']))
    
    shift_compare = compare_shifts(line=line, product=product)
    shift_list = shift_compare.to_dict('records')
    img_base64 = plot_yield_bar(shift_list, '班次', title='各班次良率对比')
    
    img_data = base64.b64decode(img_base64)
    img_file = io.BytesIO(img_data)
    img = Image(img_file, width=14 * cm, height=7 * cm)
    story.append(img)
    
    return story


def _add_root_cause_section(story, styles, line=None, product=None):
    story.append(Paragraph("四、根因分析", styles['heading1']))
    
    root_cause_result = analyze_root_causes(line=line, product=product)
    factors = root_cause_result['根因分析结果']
    
    story.append(Paragraph("4.1 因子相关性排序", styles['heading2']))
    
    if factors:
        img_base64 = plot_factor_correlation_bar(factors, title='因子相关性分析')
        
        img_data = base64.b64decode(img_base64)
        img_file = io.BytesIO(img_data)
        img = Image(img_file, width=14 * cm, height=8 * cm)
        story.append(img)
        story.append(Spacer(1, 0.3 * cm))
        
        story.append(Paragraph("4.2 关键因子分析", styles['heading2']))
        
        top_factors = factors[:3]
        for i, factor in enumerate(top_factors, 1):
            story.append(Paragraph(
                f"Top {i}: {factor['因子']}（{factor['类别']}类）",
                styles['heading2']
            ))
            story.append(Paragraph(f"相关系数: {factor['相关系数']}", styles['body']))
            story.append(Paragraph(f"影响程度: {factor['影响程度']}", styles['body']))
            story.append(Paragraph(f"影响方向: {factor['影响方向']}", styles['body']))
            story.append(Paragraph(f"分析: {factor['描述']}", styles['body']))
            story.append(Spacer(1, 0.2 * cm))
    else:
        story.append(Paragraph("数据不足，无法进行根因分析", styles['body']))
    
    return story


def _add_pareto_section(story, styles, line=None, product=None):
    story.append(Paragraph("五、帕累托分析", styles['heading1']))
    
    pareto_result = pareto_analysis(line=line, product=product)
    defect_data = pareto_result['不良项目数据']
    
    if defect_data:
        img_base64 = plot_pareto(defect_data, title='不良原因帕累托图')
        
        img_data = base64.b64decode(img_base64)
        img_file = io.BytesIO(img_data)
        img = Image(img_file, width=15 * cm, height=9 * cm)
        story.append(img)
        story.append(Spacer(1, 0.3 * cm))
        
        story.append(Paragraph(f"总不良数: {pareto_result['总不良数']} 件", styles['body']))
        story.append(Paragraph(f"TOP5 不良占比: {pareto_result['TOP5占比']}%", styles['body']))
        story.append(Paragraph(pareto_result['二八法则验证'], styles['body']))
        
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("不良项目明细:", styles['heading2']))
        
        data = [['排名', '不良项目', '不良数', '占比(%)', '累计占比(%)']]
        for i, item in enumerate(defect_data[:10], 1):
            data.append([
                str(i),
                item['不良项目分类'],
                str(item['不良数']),
                str(item['占比(%)']),
                str(item['累计占比(%)']),
            ])
        
        t = Table(data, colWidths=[1.5 * cm, 4 * cm, 2.5 * cm, 2.5 * cm, 3.5 * cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.gray),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
    
    return story


def _add_fmea_section(story, styles):
    story.append(Paragraph("六、FMEA 失效模式分析", styles['heading1']))
    
    fmea_result = fmea_analysis()
    all_fmea = fmea_result['全部FMEA数据']
    
    if all_fmea:
        img_base64 = plot_fmea_rpn(all_fmea, top_n=10, title='FMEA 风险优先数 (RPN)')
        
        img_data = base64.b64decode(img_base64)
        img_file = io.BytesIO(img_data)
        img = Image(img_file, width=15 * cm, height=9 * cm)
        story.append(img)
        story.append(Spacer(1, 0.3 * cm))
        
        story.append(Paragraph("FMEA 明细表:", styles['heading2']))
        
        data = [['排名', '失效模式', 'S', 'O', 'D', 'RPN', '工序']]
        for i, item in enumerate(all_fmea[:8], 1):
            data.append([
                str(i),
                item['失效模式'],
                str(item['严重度S']),
                str(item['发生率O']),
                str(item['探测度D']),
                str(item['RPN']),
                item['工序'],
            ])
        
        t = Table(data, colWidths=[1.2 * cm, 3.5 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm, 1.5 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.gray),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
    
    return story


def _add_process_chain_section(story, styles, product=None):
    story.append(Paragraph("七、工序良率链分析", styles['heading1']))
    
    chain_result = process_yield_chain(product=product)
    
    y_pos = 0
    for prod_name, data in chain_result.items():
        story.append(Paragraph(f"7.{y_pos+1} {prod_name} 工序链", styles['heading2']))
        
        img_base64 = plot_process_chain(data['工序良率链'], prod_name)
        
        img_data = base64.b64decode(img_base64)
        img_file = io.BytesIO(img_data)
        img = Image(img_file, width=15 * cm, height=5.5 * cm)
        story.append(img)
        story.append(Spacer(1, 0.2 * cm))
        
        story.append(Paragraph(f"· 最终良率: {data['最终良率(%)']}%", styles['body']))
        story.append(Paragraph(f"· 瓶颈工序: {data['瓶颈工序']}（{data['瓶颈工序良率(%)']}%）", styles['body']))
        story.append(Spacer(1, 0.3 * cm))
        y_pos += 1
    
    return story


def _add_improvement_suggestions_section(story, styles):
    story.append(Paragraph("八、改进建议", styles['heading1']))
    
    fmea_result = fmea_analysis()
    suggestions = fmea_result['改进建议']
    
    if suggestions:
        for i, sug in enumerate(suggestions, 1):
            priority_color = colors.red if sug['建议优先级'] == '高' else colors.orange
            
            story.append(Paragraph(
                f"{i}. {sug['失效模式']}（优先级: {sug['建议优先级']}）",
                styles['heading2']
            ))
            story.append(Paragraph(f"当前 RPN: {sug['当前RPN']}", styles['body']))
            
            for measure in sug['具体措施']:
                story.append(Paragraph(f"· {measure}", styles['body']))
            
            if sug['预期改善']:
                story.append(Paragraph(f"预期改善: {sug['预期改善']}", styles['highlight']))
            
            story.append(Spacer(1, 0.2 * cm))
    
    return story


def _add_small_sample_note_section(story, styles):
    story.append(Paragraph("九、数据质量说明", styles['heading1']))
    
    small_samples = get_small_sample_records()
    
    if len(small_samples) > 0:
        story.append(Paragraph(
            f"警告: 发现 {len(small_samples)} 条小样本数据记录（样本量 < 20），"
            f"这些数据已在统计分析中单独标记，不参与均值计算，仅供参考。",
            styles['highlight']
        ))
        story.append(Spacer(1, 0.3 * cm))
        
        story.append(Paragraph("小样本数据明细:", styles['heading2']))
        
        data = [['工单号', '产品', '产线', '操作工', '数量', '良率(%)']]
        for _, row in small_samples.iterrows():
            yield_rate = round(row['合格数量'] / row['实际完成数量'] * 100, 2) if row['实际完成数量'] > 0 else 0
            data.append([
                row['工单号'],
                row['产品型号'],
                row['产线'],
                row['操作工'],
                str(row['实际完成数量']),
                str(yield_rate),
            ])
        
        t = Table(data, colWidths=[3.5 * cm, 2.5 * cm, 2 * cm, 2.5 * cm, 2 * cm, 2 * cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkorange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.gray),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("未发现小样本数据，数据质量良好。", styles['body']))
    
    return story


def get_report_summary(report_type='weekly'):
    summary = get_summary_stats()
    pareto_result = pareto_analysis()
    fmea_result = fmea_analysis()
    
    return {
        '报告类型': '周度报告' if report_type == 'weekly' else '月度报告',
        '总体良率': summary['总体良率']['良率(%)'],
        '总工单数': summary['总工单数'],
        '总不良数': pareto_result['总不良数'],
        'TOP1不良': pareto_result['不良项目数据'][0]['不良项目分类'] if pareto_result['不良项目数据'] else None,
        '最高RPN': fmea_result['全部FMEA数据'][0]['RPN'] if fmea_result['全部FMEA数据'] else 0,
        '改进建议数': len(fmea_result['改进建议']),
    }
