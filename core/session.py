"""单个浏览器会话中的草稿与最新结果；没有进程级用户数据。"""

from dataclasses import dataclass, field
import logging

import pandas as pd

from core.models import ExperimentSpec, InputState, ResultBundle, ValidationIssue
from core.validation import measurement_counts, normalize

logger = logging.getLogger(__name__)


@dataclass
class ExperimentSession:
    inputs: InputState
    editor_sources: dict[str, pd.DataFrame] = field(default_factory=dict)
    generations: dict[str, int] = field(default_factory=dict)
    parameter_generation: int = 0
    result: ResultBundle | None = None
    normalized: InputState | None = None
    issues: list[ValidationIssue] = field(default_factory=list)
    evaluated_revision: int = -1
    calculation_count: int = 0
    status: str = '未填写'
    active_view: str = '结果表格'
    exports: dict[str, bytes] = field(default_factory=dict)
    prepared_revision: int = -1

    @classmethod
    def create(cls, spec: ExperimentSpec):
        state = spec.initial_state()
        return cls(state, {k: v.copy() for k, v in state.tables.items()},
                   {k: 0 for k in state.tables})

    def invalidate(self):
        self.inputs.revision += 1
        self.result = None
        self.exports.clear()
        self.prepared_revision = -1

    def edit_table(self, table_id: str, frame: pd.DataFrame):
        if not self.inputs.tables[table_id].equals(frame):
            self.inputs.tables[table_id] = frame.copy(deep=True)
            source = self.inputs.sources[table_id]
            self.inputs.sources[table_id] = ('已修改示例' if '示例' in source else
                                            '已修改导入' if '导入' in source else '手工录入')
            self.invalidate()

    def edit_parameter(self, parameter_id, value):
        if self.inputs.parameters[parameter_id] != value:
            self.inputs.parameters[parameter_id] = value
            for key, source in self.inputs.sources.items():
                if source == '示例':
                    self.inputs.sources[key] = '已修改示例'
            self.invalidate()

    def replace(self, state: InputState):
        """一次性替换；调用者已完成结构校验和覆盖确认。"""
        state = state.copy()
        state.revision = self.inputs.revision + 1
        self.inputs = state
        self.editor_sources = {k: v.copy() for k, v in state.tables.items()}
        self.generations = {k: self.generations.get(k, 0) + 1 for k in state.tables}
        self.parameter_generation += 1
        self.result = None
        self.exports.clear()
        self.prepared_revision = -1

    def import_table(self, table_id, frame):
        self.inputs.tables[table_id] = frame.copy(deep=True)
        self.inputs.sources[table_id] = 'CSV 导入'
        self.editor_sources[table_id] = frame.copy(deep=True)
        self.generations[table_id] += 1
        self.invalidate()

    def evaluate(self, spec: ExperimentSpec):
        if self.evaluated_revision == self.inputs.revision:
            return
        self.evaluated_revision = self.inputs.revision
        self.normalized, self.issues = normalize(spec, self.inputs)
        self.result = None
        self.exports.clear()
        self.prepared_revision = -1
        if any(issue.severity == 'error' for issue in self.issues):
            self.status = '输入需修正'
            return
        try:
            self.calculation_count += 1
            self.result = spec.compute(self.normalized.copy())
            self.result.revision = self.inputs.revision
            present, total = measurement_counts(spec, self.normalized)
            self.status = ('未填写' if present == 0 else
                           '部分可计算' if present < total or self.result.notes else '结果已更新')
        except Exception:
            logger.exception('实验 %s 计算失败，输入版本 %s', spec.id, self.inputs.revision)
            self.status = '计算失败'
            self.issues = [ValidationIssue('计算未能完成，请保留完整实验备份并通过侧栏反馈。')]

    @property
    def source_label(self):
        sources = set(self.inputs.sources.values())
        if len(sources) == 1:
            source = next(iter(sources))
            return '示例数据' if source == '示例' else source
        return '混合来源'
