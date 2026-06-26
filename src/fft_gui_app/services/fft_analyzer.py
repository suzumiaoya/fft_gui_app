from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import signal

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
            raise ValidationError("没有可用于频谱分析的数据。")
        if not signal_columns:
            raise ValidationError("请至少选择一个信号列。")
        if sample_rate_hz <= 0:
            raise ValidationError("采样率必须大于 0。")
        if spectrum_config.plot_mode not in {"overlay", "separate"}:
            raise ValidationError("不支持的显示方式。")
        if spectrum_config.method not in {"fft", "welch"}:
            raise ValidationError("不支持的频谱分析方法。")

        sample_count = len(frame)
        if sample_count < 2:
            raise ValidationError("频谱分析至少需要 2 个样本点。")

        series_amplitudes_by_name: dict[str, pd.Series] = {}
        frequencies_hz: pd.Series | None = None

        for signal_column in signal_columns:
            signal = frame[signal_column].to_numpy(dtype=float)
            if spectrum_config.remove_mean:
                signal = signal - float(np.mean(signal))
            if spectrum_config.method == "fft":
                frequencies_hz, spectrum_values = self._compute_fft_spectrum(
                    signal_values=signal,
                    sample_rate_hz=sample_rate_hz,
                    spectrum_config=spectrum_config,
                )
            else:
                frequencies_hz, spectrum_values = self._compute_welch_spectrum(
                    signal_values=signal,
                    sample_rate_hz=sample_rate_hz,
                    sample_count=sample_count,
                    spectrum_config=spectrum_config,
                )

            series_amplitudes_by_name[signal_column] = pd.Series(spectrum_values, name=signal_column)

        if frequencies_hz is None:
            raise ValidationError("频谱分析失败，未生成频率轴。")

        return SpectrumResult(
            frequencies_hz=frequencies_hz,
            series_amplitudes_by_name=series_amplitudes_by_name,
            sample_rate_hz=sample_rate_hz,
            sample_count=sample_count,
            method=spectrum_config.method,
            plot_mode=spectrum_config.plot_mode,
            magnitude_mode=spectrum_config.magnitude_mode,
            y_axis_unit=self._resolve_y_axis_unit(spectrum_config),
        )

    def _build_window(self, window: str, sample_count: int) -> np.ndarray:
        if window == "hann":
            return np.hanning(sample_count)
        if window == "none":
            return np.ones(sample_count, dtype=float)
        raise ValidationError("不支持的窗口函数。")

    def _compute_fft_spectrum(
        self,
        signal_values: np.ndarray,
        sample_rate_hz: float,
        spectrum_config: SpectrumConfig,
    ) -> tuple[pd.Series, np.ndarray]:
        sample_count = len(signal_values)
        frequencies_hz = pd.Series(
            np.fft.rfftfreq(sample_count, d=1.0 / sample_rate_hz),
            name="frequency_hz",
        )

        window = self._build_window(spectrum_config.window, sample_count)
        window_scale = float(window.sum())
        if window_scale <= 0:
            raise ValidationError("窗口函数无效，无法计算 FFT 频谱。")

        spectrum = np.fft.rfft(signal_values * window)
        amplitudes = np.abs(spectrum) / window_scale

        if sample_count > 1 and amplitudes.size > 1:
            upper_index = amplitudes.size - 1
            if sample_count % 2 == 0 and upper_index > 1:
                amplitudes[1:-1] *= 2.0
            elif sample_count % 2 != 0:
                amplitudes[1:] *= 2.0

        if spectrum_config.magnitude_mode == "db":
            amplitudes = 20.0 * np.log10(np.maximum(amplitudes, 1e-12))
        elif spectrum_config.magnitude_mode == "log":
            amplitudes = np.log10(np.maximum(amplitudes, 1e-12))
        elif spectrum_config.magnitude_mode != "linear":
            raise ValidationError("FFT 只支持 linear、log 或 db 幅值模式。")

        return frequencies_hz, amplitudes

    def _compute_welch_spectrum(
        self,
        signal_values: np.ndarray,
        sample_rate_hz: float,
        sample_count: int,
        spectrum_config: SpectrumConfig,
    ) -> tuple[pd.Series, np.ndarray]:
        nperseg = spectrum_config.welch_nperseg or min(1024, sample_count)
        noverlap = spectrum_config.welch_noverlap
        if noverlap is None:
            noverlap = nperseg // 2

        if nperseg < 8 or nperseg > sample_count:
            raise ValidationError("Welch 的 nperseg 必须在 8 到样本数之间。")
        if noverlap < 0 or noverlap >= nperseg:
            raise ValidationError("Welch 的 noverlap 必须小于 nperseg。")
        if spectrum_config.welch_window not in {"hann", "boxcar"}:
            raise ValidationError("Welch 仅支持 hann 或 boxcar 窗。")

        frequencies_hz, psd = signal.welch(
            signal_values,
            fs=sample_rate_hz,
            window=spectrum_config.welch_window,
            nperseg=nperseg,
            noverlap=noverlap,
            detrend=False,
            return_onesided=True,
            scaling="density",
        )
        if spectrum_config.magnitude_mode == "db":
            psd = 10.0 * np.log10(np.maximum(psd, 1e-24))
        elif spectrum_config.magnitude_mode == "log":
            psd = np.log10(np.maximum(psd, 1e-24))
        elif spectrum_config.magnitude_mode != "linear":
            raise ValidationError("Welch PSD 只支持 linear、log 或 db 幅值模式。")
        return pd.Series(frequencies_hz, name="frequency_hz"), psd

    def _resolve_y_axis_unit(self, spectrum_config: SpectrumConfig) -> str:
        if spectrum_config.method == "welch":
            if spectrum_config.magnitude_mode == "db":
                return "PSD (dB/Hz)"
            if spectrum_config.magnitude_mode == "log":
                return "log10(PSD)"
            return "PSD"

        if spectrum_config.magnitude_mode == "db":
            return "幅值(dB)"
        if spectrum_config.magnitude_mode == "log":
            return "log10(幅值)"
        return "幅值"
