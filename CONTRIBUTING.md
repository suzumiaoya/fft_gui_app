# Contributing Guide

感谢你关注 `fft_gui_app`。

本项目欢迎：

- bug 报告
- 新功能建议
- 测试补充
- GUI 交互改进
- 信号处理与代码生成能力增强

在提交改动前，请先读：

- [README.md](README.md)
- [docs/VIBE_CODING.md](docs/VIBE_CODING.md)

## Development Principles

请优先遵守以下原则：

- 业务逻辑尽量留在 `src/fft_gui_app/services/`
- GUI 负责组织输入和展示，不负责核心算法
- 改动频谱算法、滤波器设计或代码生成时，必须补测试
- 新增参数如果需要跨模块共享，应优先收敛到 `src/fft_gui_app/models.py`

## Local Setup

建议在项目根目录执行：

```powershell
python -m pip install -e .
```

运行应用：

```powershell
python -m fft_gui_app
```

运行测试：

```powershell
python -m unittest discover -s tests -v
```

## Pull Request Expectations

提交 PR 时，建议至少说明：

- 这个改动解决了什么问题
- 改动影响哪些模块
- 是否涉及数据模型或导出接口变化
- 如何验证
- 是否新增或更新测试

## Good First Contributions

如果你第一次参与，比较适合从这些任务开始：

- 改进错误提示文案
- 补充 README 截图
- 增加新的小型单元测试
- 改善图表交互体验
- 修复导出代码中的边缘情况

## Larger Changes

如果改动较大，建议先开一个 issue 或 draft PR，提前说明：

- 目标能力
- 预期用户行为
- 是否影响当前 GUI 主流程
- 是否影响导出的 STM32 C 接口

## Coding Style

- 保持模块职责清晰
- 优先小步改动
- 避免把复杂算法直接塞进按钮回调
- 保持测试可运行、可复现

## Testing Policy

以下改动默认需要测试：

- FFT / Welch 分析逻辑
- 去均值、去趋势等预处理
- 滤波预览
- C 代码生成
- 数值一致性相关逻辑
