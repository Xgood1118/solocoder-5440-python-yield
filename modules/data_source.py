import random
import datetime
import pandas as pd
import numpy as np

random.seed(42)
np.random.seed(42)

LINES = ['A线', 'B线', 'C线']
PRODUCTS = ['产品A', '产品B', '产品C']
SHIFTS = ['早班', '中班', '晚班']
WORKERS = ['张三', '李四', '王五', '赵六', '钱七']
INSPECTORS = ['检验员甲', '检验员乙', '检验员丙']
DEFECT_TYPES = ['尺寸超差', '表面划痕', '装配不良', '功能失效', '包装破损', '标识错误', '焊点虚焊', '漏装零件']
MATERIAL_BATCHES = ['M20240101', 'M20240115', 'M20240201', 'M20240215', 'M20240301']
MOLD_TYPES = ['模具V1', '模具V2', '模具V3']
EQUIPMENTS = ['设备X1', '设备X2', '设备Y1', '设备Y2', '设备Z1']

SHIFT_HOURS = {'早班': 8, '中班': 16, '晚班': 0}

PRODUCT_BASE_YIELD = {
    '产品A': 0.96,
    '产品B': 0.94,
    '产品C': 0.92,
}

LINE_EFFECT = {
    'A线': 0.01,
    'B线': 0.0,
    'C线': -0.015,
}

WORKER_EFFECT = {
    '张三': 0.008,
    '李四': 0.005,
    '王五': 0.0,
    '赵六': -0.01,
    '钱七': -0.02,
}

SHIFT_EFFECT = {
    '早班': 0.005,
    '中班': 0.0,
    '晚班': -0.01,
}

PRODUCTION_ORDERS = []
QUALITY_RECORDS = []
FACTOR_DATA = {}
FMEA_DATA = []
PROCESS_DATA = []


def generate_production_data(days=60):
    orders = []
    start_date = datetime.date.today() - datetime.timedelta(days=days)
    
    order_id = 1
    for day in range(days):
        current_date = start_date + datetime.timedelta(days=day)
        weekday = current_date.weekday()
        if weekday >= 5:
            num_orders = random.randint(3, 6)
        else:
            num_orders = random.randint(8, 15)
        
        for _ in range(num_orders):
            product = random.choice(PRODUCTS)
            line = random.choice(LINES)
            worker = random.choice(WORKERS)
            shift = random.choice(SHIFTS)
            
            plan_qty = random.choice([50, 100, 150, 200, 300, 500])
            
            base_yield = PRODUCT_BASE_YIELD[product]
            base_yield += LINE_EFFECT[line]
            base_yield += WORKER_EFFECT[worker]
            base_yield += SHIFT_EFFECT[shift]
            base_yield += random.uniform(-0.02, 0.02)
            base_yield = max(0.7, min(0.998, base_yield))
            
            actual_qty = int(plan_qty * random.uniform(0.95, 1.02))
            pass_qty = int(actual_qty * base_yield)
            pass_qty = min(pass_qty, actual_qty)
            
            prod_time = datetime.datetime.combine(
                current_date,
                datetime.time(hour=SHIFT_HOURS[shift], minute=random.randint(0, 59))
            )
            
            order_no = f'PO{current_date.strftime("%Y%m%d")}{order_id:04d}'
            orders.append({
                '工单号': order_no,
                '产品型号': product,
                '产线': line,
                '操作工': worker,
                '班次': shift,
                '生产时间': prod_time,
                '计划数量': plan_qty,
                '实际完成数量': actual_qty,
                '合格数量': pass_qty,
                '原料批次': random.choice(MATERIAL_BATCHES),
                '模具型号': random.choice(MOLD_TYPES),
                '设备': random.choice(EQUIPMENTS),
            })
            order_id += 1
    
    small_sample_days = 5
    for _ in range(small_sample_days):
        current_date = start_date + datetime.timedelta(days=random.randint(0, days - 1))
        product = random.choice(PRODUCTS)
        line = random.choice(LINES)
        worker = random.choice(WORKERS)
        shift = random.choice(SHIFTS)
        
        actual_qty = random.randint(1, 5)
        pass_qty = actual_qty
        
        prod_time = datetime.datetime.combine(
            current_date,
            datetime.time(hour=SHIFT_HOURS[shift], minute=random.randint(0, 59))
        )
        
        order_no = f'PO{current_date.strftime("%Y%m%d")}{order_id:04d}'
        orders.append({
            '工单号': order_no,
            '产品型号': product,
            '产线': line,
            '操作工': worker,
            '班次': shift,
            '生产时间': prod_time,
            '计划数量': 10,
            '实际完成数量': actual_qty,
            '合格数量': pass_qty,
            '原料批次': random.choice(MATERIAL_BATCHES),
            '模具型号': random.choice(MOLD_TYPES),
            '设备': random.choice(EQUIPMENTS),
        })
        order_id += 1
    
    return pd.DataFrame(orders)


def generate_quality_data(production_df):
    records = []
    inspect_id = 1
    
    for _, row in production_df.iterrows():
        defect_qty = row['实际完成数量'] - row['合格数量']
        
        for i in range(defect_qty):
            defect_type = random.choice(DEFECT_TYPES)
            inspector = random.choice(INSPECTORS)
            inspect_time = row['生产时间'] + datetime.timedelta(hours=random.uniform(1, 4))
            
            records.append({
                '检验工单号': f'QC{row["生产时间"].strftime("%Y%m%d")}{inspect_id:05d}',
                '关联生产工单号': row['工单号'],
                '检验结果': '不良',
                '不良项目分类': defect_type,
                '检验员': inspector,
                '检验时间': inspect_time,
                '产品型号': row['产品型号'],
                '产线': row['产线'],
            })
            inspect_id += 1
        
        pass_sample = min(int(row['合格数量'] * 0.1), 20)
        for _ in range(pass_sample):
            inspector = random.choice(INSPECTORS)
            inspect_time = row['生产时间'] + datetime.timedelta(hours=random.uniform(1, 4))
            
            records.append({
                '检验工单号': f'QC{row["生产时间"].strftime("%Y%m%d")}{inspect_id:05d}',
                '关联生产工单号': row['工单号'],
                '检验结果': '合格',
                '不良项目分类': None,
                '检验员': inspector,
                '检验时间': inspect_time,
                '产品型号': row['产品型号'],
                '产线': row['产线'],
            })
            inspect_id += 1
    
    return pd.DataFrame(records)


def generate_factor_data(production_df):
    factor_data = {}
    
    dates = sorted(production_df['生产时间'].dt.date.unique())
    
    mold_usage = {}
    for mold in MOLD_TYPES:
        mold_usage[mold] = {}
        cumulative = 0
        for d in dates:
            day_orders = production_df[
                (production_df['生产时间'].dt.date == d) &
                (production_df['模具型号'] == mold)
            ]
            cumulative += day_orders['实际完成数量'].sum()
            mold_usage[mold][d] = cumulative
    
    equipment_faults = {}
    for eq in EQUIPMENTS:
        equipment_faults[eq] = []
        fault_days = random.sample(range(len(dates)), k=random.randint(3, 8))
        for fd_idx in fault_days:
            d = dates[fd_idx]
            equipment_faults[eq].append({
                '日期': d,
                '故障时长(小时)': random.uniform(0.5, 4),
                '故障类型': random.choice(['电气故障', '机械故障', '传感异常', '液压故障']),
            })
    
    env_data = {}
    for d in dates:
        temp_base = 22 + random.uniform(-2, 3)
        humidity_base = 55 + random.uniform(-5, 10)
        
        for line in LINES:
            key = (d, line)
            env_data[key] = {
                '温度': temp_base + random.uniform(-1, 2),
                '湿度': humidity_base + random.uniform(-3, 5),
            }
    
    factor_data['mold_usage'] = mold_usage
    factor_data['equipment_faults'] = equipment_faults
    factor_data['env_data'] = env_data
    factor_data['dates'] = dates
    factor_data['available_factors'] = [
        {'key': 'temperature', 'name': '温度', 'category': '环境', 'unit': '℃'},
        {'key': 'humidity', 'name': '湿度', 'category': '环境', 'unit': '%'},
        {'key': 'mold_usage', 'name': '模具使用次数', 'category': '模具', 'unit': '次'},
        {'key': 'material_batch', 'name': '原料批次', 'category': '原料', 'unit': ''},
        {'key': 'equipment_fault', 'name': '设备故障', 'category': '设备', 'unit': '小时'},
        {'key': 'operator', 'name': '操作员', 'category': '人员', 'unit': ''},
        {'key': 'shift', 'name': '班次', 'category': '人员', 'unit': ''},
        {'key': 'line', 'name': '产线', 'category': '生产', 'unit': ''},
        {'key': 'mold_type', 'name': '模具型号', 'category': '模具', 'unit': ''},
    ]
    
    return factor_data


def generate_fmea_data():
    fmea_list = [
        {'失效模式': '尺寸超差', '严重度S': 7, '发生率O': 6, '探测度D': 4, '工序': '注塑', '改进方向': '优化模具精度，增加SPC监控'},
        {'失效模式': '表面划痕', '严重度S': 5, '发生率O': 7, '探测度D': 3, '工序': '喷涂', '改进方向': '改善作业环境无尘度，更换治具'},
        {'失效模式': '装配不良', '严重度S': 8, '发生率O': 5, '探测度D': 5, '工序': '组装', '改进方向': '设计防错工装，加强员工培训'},
        {'失效模式': '功能失效', '严重度S': 9, '发生率O': 3, '探测度D': 3, '工序': '测试', '改进方向': '加强来料检验，优化测试流程'},
        {'失效模式': '包装破损', '严重度S': 4, '发生率O': 4, '探测度D': 6, '工序': '包装', '改进方向': '选用更坚固包装材料，优化堆叠方式'},
        {'失效模式': '标识错误', '严重度S': 6, '发生率O': 4, '探测度D': 5, '工序': '包装', '改进方向': '引入条码扫描防错系统'},
        {'失效模式': '焊点虚焊', '严重度S': 8, '发生率O': 5, '探测度D': 4, '工序': '焊接', '改进方向': '优化焊接参数，定期校准设备'},
        {'失效模式': '漏装零件', '严重度S': 7, '发生率O': 4, '探测度D': 6, '工序': '组装', '改进方向': '重量检测防错，工序互检制度'},
        {'失效模式': '模具磨损超差', '严重度S': 6, '发生率O': 5, '探测度D': 5, '工序': '注塑', '改进方向': '降低模具寿命上限，增加预防性维护频次'},
        {'失效模式': '原料批次波动', '严重度S': 7, '发生率O': 4, '探测度D': 4, '工序': '注塑', '改进方向': '加强供应商管理，建立批次追溯体系'},
    ]
    
    df = pd.DataFrame(fmea_list)
    df['RPN'] = df['严重度S'] * df['发生率O'] * df['探测度D']
    df = df.sort_values('RPN', ascending=False).reset_index(drop=True)
    return df


def generate_process_data():
    processes = {
        '产品A': [
            {'工序': '注塑', '基准良率': 0.985},
            {'工序': '喷涂', '基准良率': 0.975},
            {'工序': '组装', '基准良率': 0.98},
            {'工序': '测试', '基准良率': 0.99},
            {'工序': '包装', '基准良率': 0.995},
        ],
        '产品B': [
            {'工序': '注塑', '基准良率': 0.98},
            {'工序': '焊接', '基准良率': 0.97},
            {'工序': '组装', '基准良率': 0.975},
            {'工序': '测试', '基准良率': 0.985},
            {'工序': '包装', '基准良率': 0.992},
        ],
        '产品C': [
            {'工序': '注塑', '基准良率': 0.97},
            {'工序': '喷涂', '基准良率': 0.965},
            {'工序': '焊接', '基准良率': 0.975},
            {'工序': '组装', '基准良率': 0.96},
            {'工序': '测试', '基准良率': 0.98},
            {'工序': '包装', '基准良率': 0.99},
        ],
    }
    return processes


production_df = generate_production_data(days=60)
quality_df = generate_quality_data(production_df)
factor_data = generate_factor_data(production_df)
fmea_df = generate_fmea_data()
process_data = generate_process_data()


def get_production_data():
    return production_df.copy()


def get_quality_data():
    return quality_df.copy()


def get_factor_data():
    return factor_data


def get_fmea_data():
    return fmea_df.copy()


def get_process_data():
    return process_data


def get_available_factors():
    return factor_data['available_factors']
