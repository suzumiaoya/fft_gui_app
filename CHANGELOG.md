# Changelog

All notable changes to this project will be documented in this file.

The format loosely follows Keep a Changelog.

## [Unreleased]

### Added

- Windows `start.bat` launcher with Python and Conda environment discovery
- Automatic Python version and dependency checks against `pyproject.toml`, with missing or incompatible dependencies installed in the project-local `.venv`
- Dependency consistency and import checks before GUI startup, plus `-CheckOnly` mode for environment preparation without opening the GUI
- GitHub-facing README and Vibe coding development guide
- Optional mean removal before spectrum generation
- Log magnitude spectrum option
- Mouse coordinate hover display for plots
- Mouse wheel zoom and double-click reset in plot view
- FFT and Welch spectrum analysis modes
- Filter preview with time-domain and frequency-domain comparison
- STM32-oriented SOS/DF2T C code generation

### Changed

- Standardized application startup on the root-level `start.bat`, with internal bootstrap scripts grouped under `tools/`
- Updated README and contributing instructions for automatic startup and manual Conda environment setup
- Added `tests/` to `.gitignore` for new local test files; previously tracked tests remain in the repository
- Code generation upgraded from placeholder output to runnable float32 filter implementation
- Project documentation expanded for open-source collaboration

### Removed

- Legacy `run.bat` launcher and installed `fft-gui-app` console entry point

## [0.1.0] - 2026-06-26

### Added

- Initial GUI application
- CSV import and preview
- FFT spectrum visualization
- Welch PSD support
- Filter preview workflow
- STM32 C code export
- Unit test coverage for data loading, spectrum analysis, filtering, and code generation
