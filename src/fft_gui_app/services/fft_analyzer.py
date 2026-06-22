from __future__ import annotations

import numpy as np
import pandas as pd

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import SpectrumConfig, SpectrumResult


class FftAnalyzer:
    def compute(
        self,
        frame: pd.DataFrame,
        signal_columns: list[str],
        spectrum_config: SpectrumConfig,
        sample_rate_hz: float,
    ) -> SpectrumResult:
        if frame.empty:
            raise ValidationError("没有可用于 FFT 的数据。")
        if not signal_columns:
            raise ValidationError("请至少选择一个信号列。")
        if sample_rate_hz <= 0:
            raise ValidationError("采样率必须大于 0。")
        if spectrum_config.plot_mode not in {"overlay", "separate"}:
            raise ValidationError("不支持的显示方式。")

        sample_count = len(frame)
        if sample_count < 2:
            raise ValidationError("FFT 至少需要 2 个样本点。")

        frequencies_hz = pd.Series(
            np.fft.rfftfreq(sample_count, d=1.0 / sample_rate_hz),
            name="frequency_hz",
        )

        window = self._build_window(spectrum_config.window, sample_count)
        window_scale = float(window.sum())
        if window_scale <= 0:
            raise ValidationError("窗口函数无效，无法计算频谱。")

        series_amplitudes_by_name: dict[str, pd.Series] = {}
        for signal_column in signal_columns:
            signal = frame[signal_column].to_numpy(dtype=float)
            spectrum = np.fft.rfft(signal * window)
            amplitudes = np.abs(spectrum) / window_scale

            if sample_count > 1 and amplitudes.size > 1:
                upper_index = amplitudes.size - 1
                if sample_count % 2 == 0 and upper_index > 1:
                    amplitudes[1:-1] *= 2.0
                elif sample_count % 2 != 0:
                    amplitudes[1:] *= 2.0

            if spectrum_config.magnitude_mode == "db":
                amplitudes = 20.0 * np.log10(np.maximum(amplitudes, 1e-12))
            elif spectrum_config.magnitude_mode != "linear":
                raise ValidationError("不支持的幅值模式。")

            series_amplitudes_by_name[signal_column] = pd.Series(
                amplitudes,
                name=signal_column,
            )

        return SpectrumResult(
            frequencies_hz=frequencies_hz,
            series_amplitudes_by_name=series_amplitudes_by_name,
            sample_rate_hz=sample_rate_hz,
            sample_count=sample_count,
            plot_mode=spectrum_config.plot_mode,
            magnitude_mode=spectrum_config.magnitude_mode,
        )

    def _build_window(self, window: str, sample_count: int) -> np.ndarray:
        if window == "hann":
            return np.hanning(sample_count)
        if window == "none":
            return np.ones(sample_count, dtype=float)
        raise ValidationError("不支持的窗口函数。")
