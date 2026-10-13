"""复制后填写稳定 ID，并在 experiments/__init__.py 注册。"""
import math
import pandas as pd
from core.models import ColumnSpec, TableSpec, ExperimentSpec, ResultBundle, Metric, Explanation
from core.formatting import significant
from core.numerics import finite_mean

ID = 'lower_00_example'
KEY = '测量记录'


def compute(inputs):
    frame = inputs.tables[KEY].copy()
    mean = finite_mean(frame['长度 / mm'])
    return ResultBundle({KEY: frame}, {'mean': mean},
                        summary=(Metric('平均长度', significant(mean, 4), 'mm'),))


def explain(inputs, result):
    document = Explanation()
    document.latex(r'\bar{x}=\frac{1}{n}\sum_{i=1}^{n}x_i')
    if math.isfinite(result.values['mean']):
        document.markdown(f"平均长度：{significant(result.values['mean'], 4)} mm。")
    else:
        document.info('填写至少一个测量值后计算平均值。')
    return document


def get_spec():
    frame = pd.DataFrame({'次数': [1, 2, 3], '长度 / mm': [math.nan] * 3})
    return ExperimentSpec(ID, '示例实验', '下册', 0, '填写测量值，计算平均值。',
        '请补充实验原理、单位、仪器和有效位数要求。',
        (TableSpec(KEY, KEY, frame, (ColumnSpec('次数'), ColumnSpec('长度 / mm', minimum=0.)), ('次数',)),),
        (), compute, explain)
