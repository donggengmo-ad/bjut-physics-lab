# 模块与新增实验

## 目录和处理链

```text
app.py                   导航、侧栏、应用入口
app_pages/*.py           每页两行，调用公共工作台
experiments/__init__.py   10 项轻量注册表，按 ID 延迟加载定义
experiments/exp*.py       输入定义、专业校验、纯计算、显示规则、实验内容
core/models.py           数据类契约
core/session.py          每个会话、每个实验的草稿及当前结果版本
core/validation.py       结构、固定标识、有限数值、参数及角度校验
core/files.py            CSV、版本化 JSON、结果 ZIP
core/formatting.py       仅在展示时舍入
core/plots.py            复用 Plotly 数值的白底报告图
ui/                      通用输入、文件操作、状态、结果、图表
```

处理顺序为原始草稿 → 规范化与校验 → `compute` → 单个 `ResultBundle`。表格、摘要、代入和图表读取同一结果。`explain`、`format_tables` 与 `build_plot` 只做呈现，不重算另一套测量结果。线性拟合也在计算阶段保存。

## 公共契约

- `ExperimentSpec`：稳定 ID、册别、编号、说明、输入表、参数、计算与展示函数；`build_plot=None` 表示无图表。
- `TableSpec`：原始列、列类型、固定行标识、默认表和合法缺测；`variable_rows` 仅用于允许可变记录的实验。
- `ColumnSpec`：`number`、`text`、`angle`；单位写入列名或 label；正数、范围、显示精度均显式声明。
- `ParameterSpec`：数字／文本、默认值、范围、是否可空。人工覆盖使用可空参数表达，例如密立根 `mean_油滴一`。
- `InputState`：原始表、参数、逐表来源、版本号；深复制与控件状态分离。
- `ValidationIssue`：表、零基行号、列、错误原因、级别。呈现时转换为一基行号。
- `ResultBundle`：未舍入数值、结果表、说明、最多四项摘要、对应输入版本。
- `Explanation`：Markdown、公式、表格和说明块，不依赖 Streamlit。

`core` 和实验模块不导入 Streamlit。公开计算函数接收规范化输入，不修改原表。缺测用 NaN／None；无可用计算量用 NaN，展示为“—”，并提供原因或记录数。

## 草稿、控件与失效

`st.session_state['lab_sessions'][experiment_id]` 保存独立会话对象。全局缓存只保存实验定义；`initial_state()` 总是复制默认表。不要修改缓存定义的 DataFrame，也不要全局缓存用户对象。

普通编辑复用稳定的 `editor_sources`。整体导入／清空／载入示例才增加编辑器代数；切换页面后，控件从独立草稿恢复。控件键包含实验、表／参数和代数。

输入变更立即清除旧结果和导出字节，并递增 revision。`evaluate` 对相同 revision 不重复计算。无效输入保留草稿、阻止计算且不显示旧结果；异常写入日志，页面仅显示简明反馈。

结果标签使用 `st.tabs(..., on_change='rerun')` 与 `.open`。输入始终在标签页外渲染。未打开图表不调用绘图；打开后仅缓存当前版本的 JSON／图片字节，不缓存 Matplotlib Figure。每个实验最多保留当前版本的结果和下载内容，计算次数可用于回归观测。

## 文件协议

JSON 格式版本为 1，字段为 `schema_version`、`experiment_id`、`tables`、`parameters`、`sources`。每张表含有 `columns` 和 `rows`。不保存 Python 对象或权威计算结果。

备份允许保存无效数值草稿。非有限值编码为文本，空值编码为 null；恢复先验证结构，再重新进行数值校验。错误的实验 ID、未知版本、表／参数结构会被拒绝。CSV 导入拒绝非法数值、固定标识改变和错误列；兼容旧索引列。上传上限 10 MB。

下载内容通过显式按钮准备，`on_click='ignore'` 避免下载触发重算。恢复和导入的确认弹窗只影响当前实验。导入只替换目标表，不受其他表中尚未修正的数值草稿阻塞。

## 添加实验

1. 复制 `experiments/template.py`，填写稳定 ID、元数据和原始默认表。没有提供示例的实验保持空白。
2. 按 `ColumnSpec` 和 `ParameterSpec` 声明单位、类型、只读标识及约束。
3. 实现 `compute(inputs)`，把所有后续呈现需要的数值放进 `ResultBundle`；写独立数值期望断言。
4. 实现 `explain(inputs, result)`，按报告要求提供公式与代入。需要特殊有效位数时实现 `format_tables`。
5. 有图表时声明 `build_plot` 和 `plot_kind`。Plotly 报告出口当前支持本仓库使用的数值 Scatter、直线标注及刻度；引入新图型时须相应扩展报告渲染或使用 Matplotlib。
6. 在 `EXPERIMENTS` 追加元数据，在 `app_pages` 新建调用 `render_experiment(ID)` 的薄页面。通用工作台无需新增分支。
7. 至少验证默认、空白、部分缺测、非法值、文件往返、不修改输入，以及实际入口。涉及新交互时做真实浏览器录入测试。

Matplotlib 使用 `Figure` 和 `FigureCanvasAgg`，避免 `pyplot.subplots()` 注册全局窗口；导出后清理图对象。新增绘图样式应复用 `core.plots.report_style`。
