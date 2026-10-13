"""集中处理展示精度；禁止把格式化数值送回计算。"""

import math

import pandas as pd

from core.models import DisplayTable, InputState, ResultBundle


def significant(value, digits=4, *, trailing=False):
    if value is None or not math.isfinite(float(value)):
        return '—'
    return format(float(value), f'{"#" if trailing else ""}.{digits}g')


def latex_number(value, digits=4, *, trailing=False):
    text = significant(value, digits, trailing=trailing)
    if 'e' in text:
        mantissa, exponent = text.split('e')
        return rf'{mantissa}\times10^{{{int(exponent)}}}'
    return text


def default_tables(inputs: InputState, result: ResultBundle) -> list[DisplayTable]:
    tables = []
    for title, frame in result.tables.items():
        display = frame.copy()
        if display.index.name is not None:
            display = display.reset_index()
        for column in display:
            if pd.api.types.is_numeric_dtype(display[column]):
                display[column] = display[column].map(lambda value: significant(value, 6))
        tables.append(DisplayTable(title, display))
    return tables
