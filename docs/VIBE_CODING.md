# Vibe Coding Guide

这份文档用于约束和指导本项目后续的 AI 辅助开发、多人协作开发和开源维护。

目标不是写“所有可能的规则”，而是尽量让后续迭代：

- 不破坏当前主流程
- 不把业务逻辑堆进 GUI
- 不让信号处理与代码生成失去可验证性

## 1. Project Goals

本项目的核心目标有三条：

1. 做一个可用的 CSV 信号分析桌面工具
2. 保持分析逻辑与 GUI 分离，便于持续演化
3. 让分析结果能逐步落到嵌入式代码生成，而不是只停留在可视化

如果某个改动很“炫”，但会明显削弱这三条目标之一，默认不应该优先。

## 2. Non-Negotiables

后续开发请默认遵守这些约束：

- 不要把 FFT、Welch、滤波设计、CSV 清洗逻辑直接写进 `ui/app.py`
- 不要让 GUI 成为唯一的数据验证入口
- 不要在没有测试的情况下改动频谱算法或代码生成公式
- 不要为了快速堆功能而复制一份相似逻辑到多个 service
- 不要引入只服务于某一个临时 UI 控件、但会污染全局模型的字段

## 3. Current Architecture

### 3.1 UI Layer

`src/fft_gui_app/ui/app.py`

职责：

- 用户输入
- 状态组织
- 调用服务层
- matplotlib 绘图与交互

不应该承担：

- 核心信号处理
- 代码生成算法
- CSV 解析规则本身

### 3.2 Service Layer

`src/fft_gui_app/services`

当前主要服务：

- `csv_loader.py`
- `fft_analyzer.py`
- `signal_preprocessor.py`
- `filter_designer.py`
- `filter_preview_service.py`
- `code_generator.py`

这些模块是后续 Vibe coding 的主要落点。

### 3.3 Model Layer

`src/fft_gui_app/models.py`

这里定义了：

- 输入配置
- 频谱配置
- 滤波配置
- 预览结果
- 频谱结果

如果新增功能需要跨 service 和 GUI 共享配置，优先修改这里，而不是传散装参数。

## 4. How To Add Features Safely

建议遵循这个顺序：

1. 先判断功能属于 `UI`、`service`、`model` 还是 `codegen`
2. 先补或修改数据模型
3. 把业务逻辑写进 service
4. 给 service 补 `unittest`
5. 最后接到 GUI

### Good examples

- 加“去均值”：
  - 先加到 `SpectrumConfig`
  - 再改 `FftAnalyzer`
  - 再改 GUI
  - 最后补测试

- 加新的导出滤波格式：
  - 先明确 `FilterConfig`
  - 再改 `CodeGenerator`
  - 再补生成结果测试

### Bad examples

- 在按钮回调里直接写一大段 `numpy/scipy` 运算
- 为了一个控件需求，复制一份 FFT 逻辑到 UI 层
- 生成代码只靠手工 eyeball，不写测试

## 5. Testing Strategy

这个项目的测试以 `unittest` 为主。

运行方式：

```powershell
python -m unittest discover -s tests -v
```

### 必测范围

以下改动默认必须补测试：

- 频谱计算
- Welch 参数行为
- 去均值 / 去趋势
- 滤波器设计
- C 代码生成
- 数值一致性

### 可以只做 smoke test 的范围

- 纯 UI 布局微调
- 按钮文案修改
- 帮助文本修改

### 推荐的测试风格

- 用小而确定的合成信号
- 用明确可验证的预期
- 对频域结果用容差判断，不要过度依赖精确浮点完全相等

## 6. Code Generation Rules

代码生成部分是项目里最容易“看起来能跑，实际上很危险”的区域。

请遵守：

- 任何新增导出逻辑，都必须可被测试读取和验证
- 系数来源必须明确，是运行时设计还是离线设计
- 任何公式都要能找到对应的 Python 侧参考实现或 `scipy` 对照
- 若某个 GUI 参数尚未真正进入 C 运行时实现，必须明确写在生成代码注释里

当前已知边界：

- 导出的 C 滤波器已支持 SOS + DF2T
- notch 参数仍未进入导出的真实运行逻辑

如果后续要补 notch 级联，优先沿用当前 SOS 级联架构，不要重新设计另一套完全独立的运行时框架。

## 7. UI Evolution Rules

GUI 可以继续增强，但请保持克制：

- 常用参数放主区域
- 高级参数保持折叠
- 避免一次性把所有 DSP 选项摊开
- 交互增强优先考虑“分析效率”，不是装饰性动画

当前 GUI 已有：

- 双页签分析
- 坐标悬停
- 滚轮缩放
- 双击恢复视图

后续若新增交互，优先考虑：

- 峰值标注
- 区域框选后重算
- 图层显示开关
- 导出当前图像

## 8. Good Next Tasks

这些任务与当前架构兼容度高，适合后续继续 Vibe coding：

- notch 级联进入导出的 C 真实实现
- 频谱峰值自动标注
- 导出滤波后 CSV
- 保存 / 载入分析参数预设
- STFT / 声谱图
- 图像与报告导出
- 批量分析多个 CSV

## 9. Pull Request Checklist

如果后续在 GitHub 上协作，建议每个 PR 至少回答：

- 这个改动解决了什么问题？
- 影响哪个模块？
- 改了哪些 public model / interface？
- 如何验证？
- 是否新增或更新了测试？
- 是否影响导出的 C 代码行为？

## 10. Suggested Repo Additions

当前仓库已经补充了以下基础开源文件：

- `LICENSE`
- `CONTRIBUTING.md`
- `.gitignore`
- `CHANGELOG.md`
- GitHub issue templates
- GitHub pull request template

后续仍建议补充：

- `docs/` 下更多主题文档
- 示例数据集
- GUI 截图
- GitHub Actions CI

## 11. AI Collaboration Prompting Tips

如果后续继续用 AI 协助开发，建议在任务描述里明确：

- 想改哪个模块
- 是否允许修改模型字段
- 是否要补测试
- 是否允许改导出接口
- 是否要兼容已有 GUI 行为

推荐的任务表达方式：

- “在 `FftAnalyzer` 增加 xxx，并补对应测试”
- “不要改 GUI，只改 service 和 tests”
- “导出的 C 接口保持兼容，但实现升级为 xxx”

不推荐的表达方式：

- “把这个功能加一下”
- “你看着改”
- “顺便优化一下所有东西”

## 12. Bottom Line

对本项目来说，好的 Vibe coding 不是“改得快”，而是：

- 改动边界清晰
- 算法行为可验证
- GUI 不被业务逻辑污染
- 导出的嵌入式代码尽量可信

如果拿不准，优先选择：

- 小步修改
- 先 service 后 GUI
- 先测试后扩展
