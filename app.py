import os
import io
import json
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file, make_response
from flask.json.provider import DefaultJSONProvider

class NumpyJSONProvider(DefaultJSONProvider):
    @staticmethod
    def default(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super(NumpyJSONProvider, NumpyJSONProvider).default(obj)

from modules.yield_engine import (
    get_summary_stats, get_yield_trend, get_yield_by_dimension,
    get_yield_by_combination, compare_lines, compare_shifts,
    compare_workers, get_worker_trend, get_small_sample_records
)
from modules.root_cause import (
    analyze_root_causes, analyze_custom_factor, get_factor_correlation_matrix
)
from modules.quality_tools import (
    pareto_analysis, fmea_analysis, process_yield_chain, get_quality_overview
)
from modules.charts import (
    plot_yield_trend, plot_yield_bar, plot_pareto,
    plot_fmea_rpn, plot_process_chain, plot_factor_correlation_bar,
    plot_factor_scatter, plot_multi_line_trend
)
from modules.report_generator import generate_report, get_report_summary
from modules.data_source import (
    get_available_factors, LINES, PRODUCTS, SHIFTS, WORKERS
)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.json = NumpyJSONProvider(app)


@app.route('/')
def index():
    summary = get_summary_stats()
    quality_overview = get_quality_overview()
    return render_template('index.html',
                         summary=summary,
                         quality_overview=quality_overview)


@app.route('/yield')
def yield_page():
    return render_template('yield.html',
                         lines=LINES,
                         products=PRODUCTS,
                         shifts=SHIFTS,
                         workers=WORKERS)


@app.route('/root-cause')
def root_cause_page():
    return render_template('root_cause.html',
                         lines=LINES,
                         products=PRODUCTS)


@app.route('/quality-tools')
def quality_tools_page():
    return render_template('quality_tools.html',
                         lines=LINES,
                         products=PRODUCTS)


@app.route('/reports')
def reports_page():
    weekly_summary = get_report_summary('weekly')
    monthly_summary = get_report_summary('monthly')
    return render_template('reports.html',
                         weekly_summary=weekly_summary,
                         monthly_summary=monthly_summary)


@app.route('/factor-analyzer')
def factor_analyzer_page():
    factors = get_available_factors()
    return render_template('factor_analyzer.html',
                         factors=factors,
                         lines=LINES,
                         products=PRODUCTS)


@app.route('/api/summary')
def api_summary():
    summary = get_summary_stats()
    return jsonify(summary)


@app.route('/api/yield/trend')
def api_yield_trend():
    line = request.args.get('line')
    product = request.args.get('product')
    granularity = request.args.get('granularity', 'day')
    
    trend_data = get_yield_trend(line=line, product=product, granularity=granularity)
    trend_list = trend_data.to_dict('records')
    
    chart = plot_yield_trend(trend_list, title='良率趋势图')
    
    return jsonify({
        'data': trend_list,
        'chart': chart,
    })


@app.route('/api/yield/by-dimension')
def api_yield_by_dimension():
    dimension = request.args.get('dimension', '产线')
    
    try:
        result = get_yield_by_dimension(dimension)
        data_list = result.to_dict('records')
        chart = plot_yield_bar(data_list, dimension, title=f'{dimension}良率对比')
        return jsonify({
            'data': data_list,
            'chart': chart,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/yield/by-combination')
def api_yield_by_combination():
    dimensions = request.args.getlist('dimensions')
    
    if not dimensions:
        dimensions = ['产线', '产品型号']
    
    try:
        result = get_yield_by_combination(dimensions)
        data_list = result.to_dict('records')
        return jsonify({
            'data': data_list,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/yield/compare-lines')
def api_compare_lines():
    product = request.args.get('product')
    
    result = compare_lines(product=product)
    data_list = result.to_dict('records')
    chart = plot_yield_bar(data_list, '产线', title='各产线良率对比')
    
    return jsonify({
        'data': data_list,
        'chart': chart,
    })


@app.route('/api/yield/compare-shifts')
def api_compare_shifts():
    line = request.args.get('line')
    product = request.args.get('product')
    
    result = compare_shifts(line=line, product=product)
    data_list = result.to_dict('records')
    chart = plot_yield_bar(data_list, '班次', title='各班次良率对比')
    
    return jsonify({
        'data': data_list,
        'chart': chart,
    })


@app.route('/api/yield/compare-workers')
def api_compare_workers():
    line = request.args.get('line')
    product = request.args.get('product')
    
    result = compare_workers(line=line, product=product)
    data_list = result.to_dict('records')
    chart = plot_yield_bar(data_list, '操作工', title='各操作工良率对比')
    
    return jsonify({
        'data': data_list,
        'chart': chart,
    })


@app.route('/api/root-cause')
def api_root_cause():
    line = request.args.get('line')
    product = request.args.get('product')
    
    result = analyze_root_causes(line=line, product=product)
    factors = result['根因分析结果']
    
    corr_chart = plot_factor_correlation_bar(factors, title='因子相关性分析')
    
    return jsonify({
        'trend': result['总体良率趋势'],
        'factors': factors,
        'period': result['分析周期'],
        'correlation_chart': corr_chart,
    })


@app.route('/api/pareto')
def api_pareto():
    line = request.args.get('line')
    product = request.args.get('product')
    
    result = pareto_analysis(line=line, product=product)
    chart = plot_pareto(result['不良项目数据'], title='不良原因帕累托图')
    
    return jsonify({
        **result,
        'chart': chart,
    })


@app.route('/api/fmea')
def api_fmea():
    result = fmea_analysis()
    chart = plot_fmea_rpn(result['全部FMEA数据'], top_n=10, title='FMEA 风险优先数')
    
    return jsonify({
        **result,
        'chart': chart,
    })


@app.route('/api/process-chain')
def api_process_chain():
    product = request.args.get('product')
    
    result = process_yield_chain(product=product)
    
    charts = {}
    for prod_name, data in result.items():
        charts[prod_name] = plot_process_chain(data['工序良率链'], prod_name)
    
    return jsonify({
        'data': result,
        'charts': charts,
    })


@app.route('/api/report/generate', methods=['POST'])
def api_generate_report():
    report_type = request.json.get('type', 'weekly')
    line = request.json.get('line')
    product = request.json.get('product')
    
    try:
        pdf_buffer = generate_report(report_type=report_type, line=line, product=product)
        
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=yield_report_{report_type}.pdf'
        
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/custom-factor')
def api_custom_factor():
    factor_key = request.args.get('factor')
    line = request.args.get('line')
    product = request.args.get('product')
    
    if not factor_key:
        return jsonify({'error': '缺少 factor 参数'}), 400
    
    result = analyze_custom_factor(factor_key, line=line, product=product)
    
    if result is None:
        return jsonify({'error': '无效的因子或数据不足'}), 400
    
    chart = None
    if result['因子类型'] == '分类变量':
        chart = plot_yield_bar(result['数据'], list(result['data'][0].keys())[0],
                              title=f'{result["因子"]}良率对比')
    elif result['因子类型'] == '连续变量':
        x_data = [d['因子值'] for d in result['散点数据']]
        y_data = [d['良率(%)'] for d in result['散点数据']]
        if len(x_data) > 1:
            chart = plot_factor_scatter(x_data, y_data, result['因子'], '良率 (%)',
                                       title=f'{result["因子"]}-良率散点图')
    
    return jsonify({
        **result,
        'chart': chart,
    })


@app.route('/api/available-factors')
def api_available_factors():
    factors = get_available_factors()
    return jsonify({'factors': factors})


@app.route('/api/small-samples')
def api_small_samples():
    result = get_small_sample_records()
    return jsonify({
        'count': len(result),
        'records': result.to_dict('records') if len(result) > 0 else [],
    })


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
