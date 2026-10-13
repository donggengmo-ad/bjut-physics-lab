# BJUT 物理实验项目指令

## 每次任务必用的项目 skill

在本仓库每次处理用户请求时，先调用并遵守 `$bjut-lab-report`：

- 入口：[.agents/skills/bjut-lab-report/SKILL.md](.agents/skills/bjut-lab-report/SKILL.md)。不要等待用户再次点名 skill。
- 如果 skill 未出现在自动发现列表中，直接读取上述项目文件并应用；同一任务已加载且文件未改变时可复用，仍须在后续任务中应用相关条款。
- skill 是报告内容、数据忠实、公式代入、有效位数、思考题、图表及项目实现规范的统一来源。本文件只负责强制路由，避免维护两套规则。
- 用户最新明确指令优先，尤其是局部更正和例外。按本次任务范围应用规范，不给纯仓库操作强加实验报告工作，不自行扩大修改或发布范围。
- 修改 Streamlit 应用时，同时使用可用的 `developing-with-streamlit` skill。
