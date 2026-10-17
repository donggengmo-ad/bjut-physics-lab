# 报告字体资源

项目优先使用运行环境已安装的宋体（SimSun／Songti SC）和 Times New Roman。此目录只分发开源兜底字体，不包含系统商业字体。

- `SourceHanSerifSC-Regular.otf`：Adobe 思源宋体简体中文，版本 2.003，SIL Open Font License 1.1。来源固定到官方 `release` 分支提交 `7889f11bf31170b5d092a083b357c8c8130f89e0`，许可证见 `LICENSE-SourceHanSerif.txt`。
- `LiberationSerif-*.ttf`：Liberation Serif 2.1.5，包含常规、粗体、斜体和粗斜体，SIL Open Font License 1.1。官方下载包链接来自[官方 2.1.5 发布页](https://github.com/liberationfonts/liberation-fonts/releases/tag/2.1.5)，许可证见 `LICENSE-Liberation.txt`。它与 Times New Roman 度量兼容，但不是 Times New Roman。

所有字体原样保存；下载链接、归档成员和 SHA-256 记录在 `sources.json`，由测试校验。应用通过 Matplotlib `addfont` 注册字体，不在请求时下载。新增或升级资源时同时更新来源、许可证、哈希及字体渲染验收，不得只改字体名称。
