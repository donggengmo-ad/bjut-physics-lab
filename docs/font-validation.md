# Matplotlib 字体验收（2026-10-17）

此次覆盖全部五个可绘图实验：弹性模量、非均匀磁场、弗兰克–赫兹、交流谐振和衍射光栅。原生 Matplotlib 图及 Plotly 转报告图均经过公共字体与保存路径。

- 本机实际选用：中文 Songti SC，英文及数字 Times New Roman。
- 剔除操作系统字体后的模拟环境：中文 Source Han Serif SC，英文及数字 Liberation Serif；仅保留项目字体和 Matplotlib 自带符号字体。此项模拟字体条件，不等于在真实 Linux 服务器上验收。
- 对实际 FreeType 字形映射检查中文与拉丁字母／数字归属，验证 `Ω λ φ Δ √ − × ₁ ₂ °` 等符号有字形。
- 发现并修复：系统 Times New Roman 缺少部分 Unicode 上下标；开源字体组合缺少上标负号。普通文本增加 DejaVu Serif 的科学符号逐字兜底，MathText 使用 STIX 符号兜底，保持普通英文／数字的首选字体。
- 发现并修复：光栅标签将中文与 MathText 混在一个字符串，导致 MathText 字体无法处理中文。简单希腊符号改用 Unicode；复杂公式与中文说明分开。
- 五种图在模拟环境分别完成 PNG、SVG、PDF 保存，无缺字警告及 MathText 缺字日志；SVG 不含依赖外部字体的 `<text>`，PDF 包含嵌入字体资源。界面继续提供原有 PNG、SVG 下载，未增加 PDF 下载入口。
- 字体规则或选用字体改变后失效旧图缓存，保留 CSV 等其他导出；有回归覆盖。
- 字体文件保持上游原样，Adobe OTF 与官方固定提交的 Git blob 哈希一致；全部资源及许可证的 SHA-256 由测试校验。

渲染后逐张检查中文、科学符号、标题、坐标、图例、标注及裁切。检查图汇总：

- [本机字体图集](qa/fonts-system-contact.png)
- [仅项目字体图集](qa/fonts-bundled-contact.png)

验证命令：`MPLCONFIGDIR=/tmp/bjut-review-mpl MPLBACKEND=Agg .venv/bin/python -m unittest discover -s tests -v`。本版本共 82 项测试通过，`git diff --check` 通过；项目 skill 的官方 `quick_validate.py` 检查通过。

本记录证明本地与模拟字体环境的结果，不证明线上服务器已完成自动更新。后续字体或图表变更须重新渲染与验收，不能沿用本次结论。
