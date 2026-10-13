"""实验的公开契约。计算与文件服务不依赖 Streamlit。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import pandas as pd


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    kind: Literal['number', 'text', 'angle'] = 'number'
    label: str | None = None
    help: str | None = None
    format: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    positive: bool = False


@dataclass(frozen=True)
class TableSpec:
    id: str
    title: str
    defaults: pd.DataFrame
    columns: tuple[ColumnSpec, ...]
    fixed_columns: tuple[str, ...] = ()
    variable_rows: bool = False
    optional_cells: tuple[tuple[int, str], ...] = ()
    help: str = ''


@dataclass(frozen=True)
class ParameterSpec:
    id: str
    label: str
    default: float | str | None
    kind: Literal['number', 'text'] = 'number'
    minimum: float | None = None
    maximum: float | None = None
    positive: bool = False
    step: float = 0.1
    format: str = '%g'
    help: str = ''
    optional: bool = False


@dataclass
class InputState:
    tables: dict[str, pd.DataFrame]
    parameters: dict[str, float | str | None]
    sources: dict[str, str]
    revision: int = 0

    def copy(self) -> InputState:
        return InputState({k: v.copy(deep=True) for k, v in self.tables.items()},
                          self.parameters.copy(), self.sources.copy(), self.revision)


@dataclass(frozen=True)
class ValidationIssue:
    message: str
    table: str | None = None
    row: int | None = None
    column: str | None = None
    severity: Literal['error', 'warning'] = 'error'

    def __str__(self) -> str:
        location = ' · '.join(str(v) for v in (
            self.table, f'第 {self.row + 1} 行' if self.row is not None else None,
            self.column,
        ) if v is not None)
        return f'{location}：{self.message}' if location else self.message


@dataclass(frozen=True)
class Metric:
    label: str
    value: str
    unit: str = ''


@dataclass
class ResultBundle:
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    summary: tuple[Metric, ...] = ()
    revision: int = 0


@dataclass(frozen=True)
class DisplayTable:
    title: str
    frame: pd.DataFrame
    math: bool = False


@dataclass(frozen=True)
class Block:
    kind: Literal['markdown', 'latex', 'caption', 'info', 'warning', 'table']
    body: Any


@dataclass
class Explanation:
    """普通内容数据；生成公式文本不执行 UI，也不重新计算实验结果。"""
    blocks: list[Block] = field(default_factory=list)

    def markdown(self, text: str) -> None:
        self.blocks.append(Block('markdown', text))

    def latex(self, text: str) -> None:
        self.blocks.append(Block('latex', text))

    def caption(self, text: str) -> None:
        self.blocks.append(Block('caption', text))

    def info(self, text: str) -> None:
        self.blocks.append(Block('info', text))

    def warning(self, text: str) -> None:
        self.blocks.append(Block('warning', text))

    def table(self, frame: pd.DataFrame) -> None:
        self.blocks.append(Block('table', frame))


def no_issues(inputs: InputState) -> list[ValidationIssue]:
    return []


@dataclass(frozen=True)
class ExperimentSpec:
    id: str
    title: str
    volume: str
    number: int
    introduction: str
    description: str
    tables: tuple[TableSpec, ...]
    parameters: tuple[ParameterSpec, ...]
    compute: Callable[[InputState], ResultBundle]
    explain: Callable[[InputState, ResultBundle], Explanation]
    validate: Callable[[InputState], list[ValidationIssue]] = no_issues
    format_tables: Callable[[InputState, ResultBundle], list[DisplayTable]] | None = None
    build_plot: Callable[[InputState, ResultBundle], Any] | None = None
    plot_kind: Literal['plotly', 'matplotlib'] = 'plotly'
    plot_caption: str = ''
    discussion: str = ''

    def initial_state(self, *, blank: bool = False) -> InputState:
        tables = {}
        sources = {}
        for table in self.tables:
            frame = table.defaults.copy(deep=True)
            editable = [c.name for c in table.columns if c.name not in table.fixed_columns]
            if blank:
                for column in table.columns:
                    if column.name in editable:
                        frame[column.name] = None if column.kind != 'number' else float('nan')
            tables[table.id] = frame
            sources[table.id] = ('空白' if blank or not frame[editable].notna().any().any()
                                 else '示例')
        return InputState(tables, {p.id: p.default for p in self.parameters}, sources)
