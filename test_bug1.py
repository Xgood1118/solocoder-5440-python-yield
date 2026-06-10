import sys
sys.path.insert(0, '.')
from modules.root_cause import analyze_custom_factor

result = analyze_custom_factor('line')
print("Keys:", list(result.keys()))
print("因子类型:", result['因子类型'])
if result['因子类型'] == '分类变量':
    print("数据字段名:", '数据' in result)
    print("data字段名:", 'data' in result)
    if '数据' in result:
        print("数据[0] keys:", list(result['数据'][0].keys()))
