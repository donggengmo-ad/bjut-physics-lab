"""共用结构及逐单元格校验。缺测和无效值是不同状态。"""

import math

import pandas as pd

from core.angles import parse_angle
from core.models import ExperimentSpec, InputState, ValidationIssue


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip()) or bool(pd.isna(value))


def normalize(spec: ExperimentSpec, inputs: InputState, *, structure_only=False):
    normalized = inputs.copy()
    issues = []
    expected_ids = {table.id for table in spec.tables}
    if set(inputs.tables) != expected_ids:
        return normalized, [ValidationIssue('输入表与当前实验不匹配。')]
    if set(inputs.parameters) != {p.id for p in spec.parameters}:
        return normalized, [ValidationIssue('实验参数与当前实验不匹配。')]
    for table in spec.tables:
        frame = inputs.tables[table.id]
        expected = [column.name for column in table.columns]
        if list(frame.columns) != expected:
            issues.append(ValidationIssue(f'列名及顺序须为：{"、".join(expected)}', table.title))
            continue
        if not table.variable_rows and len(frame) != len(table.defaults):
            issues.append(ValidationIssue(f'须保留 {len(table.defaults)} 行测量记录。', table.title))
            continue
        if table.variable_rows and not 1 <= len(frame) <= 10000:
            issues.append(ValidationIssue('测量记录应为 1–10000 行。', table.title))
            continue
        frame = frame.reset_index(drop=True).copy()
        for column in table.columns:
            name = column.name
            if name in table.fixed_columns and not table.variable_rows:
                expected_values = table.defaults[name].tolist()
                for row, (value, default) in enumerate(zip(frame[name], expected_values)):
                    if not (is_blank(value) and is_blank(default)) and str(value) != str(default):
                        try:
                            equal = float(value) == float(default)
                        except (TypeError, ValueError):
                            equal = False
                        if not equal:
                            issues.append(ValidationIssue('固定行标识或常量已改变。', table.title, row, name))
                frame[name] = table.defaults[name].values
                continue
            if structure_only:
                continue
            cells = []
            for row, value in enumerate(frame[name]):
                if is_blank(value):
                    cells.append(math.nan if column.kind == 'number' else None)
                    continue
                try:
                    if column.kind == 'number':
                        if isinstance(value, bool):
                            raise ValueError('请填写数值，不接受布尔值。')
                        number = float(value)
                        if not math.isfinite(number):
                            raise ValueError('应为有限数值，不能填写 inf 或 −inf。')
                        if column.positive and number <= 0:
                            raise ValueError('应大于 0。')
                        if column.minimum is not None and number < column.minimum:
                            raise ValueError(f'不能小于 {column.minimum:g}。')
                        if column.maximum is not None and number > column.maximum:
                            raise ValueError(f'不能大于 {column.maximum:g}。')
                        cells.append(number)
                    else:
                        if column.kind == 'angle':
                            parse_angle(value)
                        cells.append(str(value).strip())
                except (ValueError, TypeError) as error:
                    message = str(error) if isinstance(error, ValueError) and not str(error).startswith('could not convert') else '请填写有效数值。'
                    issues.append(ValidationIssue(message, table.title, row, name))
                    cells.append(value)
            frame[name] = cells
        normalized.tables[table.id] = frame
    if structure_only:
        return normalized, issues
    for parameter in spec.parameters:
        value = inputs.parameters[parameter.id]
        if parameter.kind == 'text':
            normalized.parameters[parameter.id] = '' if value is None else str(value)
            continue
        if is_blank(value):
            normalized.parameters[parameter.id] = None
            if not parameter.optional:
                issues.append(ValidationIssue('请填写参数。', column=parameter.label))
            continue
        try:
            if isinstance(value, bool):
                raise ValueError('请填写数值，不接受布尔值。')
            value = float(value)
            if not math.isfinite(value):
                raise ValueError('应为有限数值。')
            if parameter.positive and value <= 0:
                raise ValueError('应大于 0。')
            if parameter.minimum is not None and value < parameter.minimum:
                raise ValueError(f'不能小于 {parameter.minimum:g}。')
            if parameter.maximum is not None and value > parameter.maximum:
                raise ValueError(f'不能大于 {parameter.maximum:g}。')
            normalized.parameters[parameter.id] = value
        except (ValueError, TypeError) as error:
            issues.append(ValidationIssue(str(error), column=parameter.label))
    if not issues:
        issues.extend(spec.validate(normalized))
    return normalized, issues


def measurement_counts(spec: ExperimentSpec, inputs: InputState):
    present = total = 0
    for table in spec.tables:
        frame = inputs.tables[table.id]
        for column in table.columns:
            if column.name in table.fixed_columns:
                continue
            for row, value in enumerate(frame[column.name]):
                if (row, column.name) in table.optional_cells:
                    continue
                total += 1
                present += not is_blank(value)
    return present, total
