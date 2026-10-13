"""可移植的实验备份；不序列化 Python 对象或信任缓存结果。"""

import io
import json
import math
import zipfile

import numpy as np
import pandas as pd

from core.models import ExperimentSpec, InputState, ResultBundle
from core.validation import normalize

SCHEMA_VERSION = 1
SOURCES = {'示例', '已修改示例', '空白', '手工录入', 'CSV 导入', '已修改导入'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def csv_bytes(frame):
    return frame.to_csv(index=False).encode('utf-8-sig')


def read_csv(spec: ExperimentSpec, table_id: str, data: bytes, inputs: InputState):
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError('文件过大，请使用不超过 10 MB 的文件。')
    table = next(t for t in spec.tables if t.id == table_id)
    dtypes = {c.name: 'string' for c in table.columns if c.kind in ('angle', 'text')}
    try:
        frame = pd.read_csv(io.BytesIO(data), dtype=dtypes).drop(columns='Unnamed: 0', errors='ignore')
    except (ValueError, UnicodeError, pd.errors.ParserError) as error:
        raise ValueError('无法读取 CSV，请使用 UTF-8 编码并保留下载模板的列名。') from error
    # 表导入不受其他表中尚未修正的草稿影响。
    isolated = spec.initial_state()
    isolated.parameters = inputs.parameters.copy()
    isolated.tables[table_id] = frame
    normalized, issues = normalize(spec, isolated)
    table_issues = [issue for issue in issues if issue.severity == 'error' and (issue.table == table.title or issue.table is None)]
    if table_issues:
        raise ValueError('\n'.join(map(str, table_issues)))
    return normalized.tables[table_id]


def _scalar(value):
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or pd.isna(value):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)  # 保存无效草稿也必须生成标准 JSON。
    if isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError('备份包含不支持的数据类型。')


def backup_bytes(spec: ExperimentSpec, inputs: InputState):
    payload = {
        'schema_version': SCHEMA_VERSION,
        'experiment_id': spec.id,
        'tables': {key: {'columns': list(frame.columns),
                         'rows': [[_scalar(v) for v in row] for row in frame.itertuples(index=False, name=None)]}
                   for key, frame in inputs.tables.items()},
        'parameters': {key: _scalar(value) for key, value in inputs.parameters.items()},
        'sources': inputs.sources,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')


def read_backup(spec: ExperimentSpec, data: bytes):
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError('文件过大，请使用不超过 10 MB 的文件。')
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise ValueError('无法读取实验备份，请选择本应用导出的 JSON 文件。') from error
    if not isinstance(payload, dict) or payload.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('不支持的备份格式版本。')
    if payload.get('experiment_id') != spec.id:
        raise ValueError('备份属于其他实验，请先切换到对应实验。')
    try:
        tables = {}
        for key, table in payload['tables'].items():
            if (not isinstance(table, dict) or not isinstance(table['columns'], list)
                    or not isinstance(table['rows'], list)
                    or any(not isinstance(row, list) or len(row) != len(table['columns']) for row in table['rows'])
                    or any(isinstance(v, (dict, list)) for row in table['rows'] for v in row)):
                raise ValueError('输入表结构损坏。')
            tables[key] = pd.DataFrame(table['rows'], columns=table['columns'])
        parameters = payload['parameters']
        sources = payload['sources']
        if not isinstance(parameters, dict) or any(isinstance(v, (dict, list)) for v in parameters.values()):
            raise ValueError('参数结构损坏。')
        if not isinstance(sources, dict) or set(sources) != set(tables) or any(v not in SOURCES for v in sources.values()):
            raise ValueError('数据来源记录损坏。')
        state = InputState(tables, parameters, sources)
        _, issues = normalize(spec, state, structure_only=True)
        if issues:
            raise ValueError('\n'.join(map(str, issues)))
        # 数值错误可以作为草稿恢复；计算前仍必须经过完整校验。
        return state
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ValueError(f'备份结构无效：{error}') from error


def result_archive(result: ResultBundle):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for index, (title, frame) in enumerate(result.tables.items(), 1):
            export = frame.reset_index() if frame.index.name is not None else frame
            filename = title.replace('/', '／').replace('\\', '＼')
            archive.writestr(f'{index:02d}_{filename}.csv', csv_bytes(export))
    return buffer.getvalue()
