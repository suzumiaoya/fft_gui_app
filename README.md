# FFT GUI App

一个面向工程分析与嵌入式落地的 Python 桌面工具，用于：

- 导入 CSV 信号数据
- 做 FFT / Welch 频谱分析与可视化
- 预览滤波前后的时域与频域变化
- 生成可用于 STM32 `float32` 处理链的 C 滤波代码

项目当前以桌面 GUI、分析链路可维护性和后续协作开发友好为优先目标。

## Features

- CSV 导入与预览
  - 支持时间列自动推导采样率
  - 支持手动输入采样率
  - 支持多信号列频谱对比
- 频谱分析
  - `FFT 幅度谱`
  - `Welch PSD`
  - `线性 / 对数 / dB` 幅值模式
  - `Hann / 无窗`
  - 可选 `生成频谱前去均值`
- 图形交互
  - 鼠标悬停显示坐标
  - 滚轮缩放
  - 左键双击恢复默认视图
  - 保留 matplotlib 工具栏进行平移、框选缩放和导航
- 滤波预览
  - 低通 / 高通 / 带通 / 带阻
  - 可选 notch 参数用于 Python 侧预览
  - 原始/滤波后时域对比
  - 原始/滤波后频域对比
- C 代码生成
  - Python 侧离线计算 SOS 系数
  - 导出 STM32 可用的 `Direct Form II Transposed` 流式 biquad 级联实现
  - 支持 `apply_filter_sample` / `apply_filter_block`

## Requirements

- Python `>= 3.13`
- Windows 环境已验证

依赖见 `pyproject.toml`：

- `customtkinter`
- `numpy`
- `pandas`
- `matplotlib`
- `scipy`

## Quick Start

Windows 统一使用项目根目录的 `start.bat` 启动。可以双击该文件，或在 PowerShell 中运行：

```powershell
.\start.bat
```

脚本会查找 Python Launcher 和 PATH 中满足 `pyproject.toml` 要求的 Python（当前为 `>=3.13`），优先复用项目的 `.venv`。首次启动会创建 `.venv`，按 `pyproject.toml` 安装依赖；后续启动会检查版本，仅在缺失或版本不满足时安装。通过依赖一致性与导入检查后自动打开应用。所有安装都在项目虚拟环境中进行。

同时支持从当前 Conda 环境和 `%USERPROFILE%\.conda\environments.txt` 查找 Python。也可以先用 Miniconda 在项目内创建环境，再运行 `start.bat`：

```powershell
conda create --prefix .\.venv python=3.13 pip tk -y
.\start.bat
```

首次安装依赖需要联网。若未找到兼容 Python，请先从 <https://www.python.org/downloads/> 安装 Python 3.13 或更新版本，并启用 Tcl/Tk、pip 和 Python Launcher 或 PATH 选项。安装失败时会保留错误信息，修复网络或 Python 后重新运行即可。

只准备和检查环境、不打开 GUI：

```powershell
.\start.bat -CheckOnly
```

`tools/` 中的脚本负责内部环境检测和依赖管理，由 `start.bat` 调用。原有的 `run.bat` 和安装后的命令行启动入口已移除。

## Usage

### 1. 导入 CSV

- 点击“导入 CSV”
- 选择时间列和一个或多个信号列
- 如果没有时间列，手动填写采样率

### 2. 生成频谱

在“频谱分析”页中：

- 选择 `FFT 幅度谱` 或 `Welch PSD`
- 选择显示方式、幅值模式、窗口函数
- 如需压低 `0 Hz / DC` 峰值，可勾选“生成频谱前去均值”
- 点击“生成频谱”

### 3. 预览滤波效果

在“滤波预览”页中：

- 选择预览列
- 配置滤波类型和频率参数
- 如需更多选项，展开高级参数
- 点击“生成滤波预览”

### 4. 导出 C 代码

- 在“滤波预览”页配置好滤波参数
- 点击“导出 C 代码”
- 会生成 `.h + .c`

## Generated C Code

当前导出的 C 代码面向 STM32 `float32` 处理链，特点如下：

- 系数由 Python/Scipy 离线生成
- 使用二阶节 `SOS` 表达
- 运行时实现为 `Direct Form II Transposed`
- 提供以下接口：

```c
void init_filter_config(FilterConfig *config);
size_t get_filter_section_count(void);
const BiquadSection *get_filter_sections(void);
void init_filter_state(FilterState *state);
float apply_filter_sample(FilterState *state, float input);
void apply_filter_block(FilterState *state, const float *input, float *output, size_t length);
void apply_filter(const FilterConfig *config, FilterState *state, const float *input, float *output, size_t length);
```

### Current Limitation

- GUI/Python 预览支持 notch 参数
- 但导出的 C 运行时首版尚未把独立 notch 级联进真实滤波逻辑
- 导出的代码中会保留 notch 参数字段和说明注释，便于后续扩展

## Project Structure

```text
fft_gui_app/
├─ start.bat                   # 唯一对外启动入口
├─ tools/
│  ├─ start.ps1                # 内部脚本：查找兼容 Python 环境
│  └─ start_app.py             # 内部脚本：检查依赖并启动 GUI
├─ fft_gui_app/                # 源码导入兼容层，供内部模块启动使用
├─ src/fft_gui_app/
│  ├─ services/                # CSV、FFT、滤波预览、代码生成等服务
│  ├─ ui/                      # CustomTkinter GUI
│  ├─ models.py                # 主要数据模型
│  ├─ exceptions.py            # 业务异常
│  └─ __main__.py              # 包入口
├─ docs/                       # 开发文档
├─ tests/                      # 本地测试；新增文件由 Git 忽略
├─ .venv/                      # 本地 Python / Conda 环境，由 Git 忽略
├─ .gitignore
├─ pyproject.toml              # Python 版本、依赖和包配置
└─ README.md
```

## Testing

运行全部测试：

```powershell
python -B -m unittest discover -s tests -v
```

当前测试覆盖：

- CSV 导入与采样率推导
- FFT / Welch 频谱分析
- 去均值与对数幅值模式
- 滤波预处理与滤波预览
- STM32 C 代码生成
- 导出 SOS 系数与 DF2T 数值一致性

`tests/` 已加入 `.gitignore`，新增测试文件只保留在本地；仓库原先已跟踪的测试仍保留。环境检查可使用 `start.bat -CheckOnly`，不会打开应用窗口。

## Development Notes

- GUI 以 `CustomTkinter + matplotlib(TkAgg)` 为基础
- 业务逻辑尽量放在 `services/`，不要堆进窗口类
- 新功能优先补测试，特别是频谱计算和代码生成相关逻辑
- 如果是较大功能，建议先阅读 [docs/VIBE_CODING.md](docs/VIBE_CODING.md)

## Roadmap

建议的后续方向：

- 导出滤波后 CSV
- notch 级联进入导出的 C 真实实现
- 峰值自动标注
- STFT / 声谱图
- 参数预设与项目配置保存
- 图像导出 / 报告导出
- 批量处理多个 CSV

## Contributing

欢迎通过以下方式参与：

- 提交 bug 报告
- 贡献更稳健的滤波算法或导出能力
- 改进 GUI 交互
- 增加更多工程场景下的测试样例

在提交较大改动前，建议先说明：

- 目标问题
- 预期用户行为
- 涉及的数据模型或接口变化
- 测试方式

## Status

当前项目已具备可用的首版能力，适合继续进行：

- 功能迭代
- AI 辅助开发
- 开源协作
- 面向 STM32 的进一步工程化整合
