from __future__ import annotations

import numpy as np
from scipy import signal

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import FilterConfig


class FilterDesigner:
    def design(self, filter_config: FilterConfig) -> np.ndarray:
        nyquist_hz = self._validate_config(filter_config)
        sos_sections: list[np.ndarray] = []

        butter_sos = self._design_butterworth(filter_config, nyquist_hz)
        if butter_sos is not None:
            sos_sections.append(butter_sos)

        for notch_hz in sorted(set(float(value) for value in filter_config.notch_freqs_hz)):
            b, a = signal.iirnotch(notch_hz, filter_config.notch_q, fs=filter_config.sample_rate_hz)
            sos_sections.append(signal.tf2sos(b, a))

        if not sos_sections:
            raise ValidationError("至少需要配置一种滤波器或一个陷波频率。")

        return np.vstack(sos_sections)

    def _validate_config(self, filter_config: FilterConfig) -> float:
        if filter_config.sample_rate_hz <= 0:
            raise ValidationError("采样率必须大于 0。")
        if filter_config.order < 1 or filter_config.order > 10:
            raise ValidationError("滤波阶数必须在 1 到 10 之间。")
        if filter_config.notch_q <= 0:
            raise ValidationError("陷波 Q 值必须大于 0。")

        nyquist_hz = filter_config.sample_rate_hz / 2.0
        for notch_hz in filter_config.notch_freqs_hz:
            if not (0 < float(notch_hz) < nyquist_hz):
                raise ValidationError("所有陷波频率必须大于 0 且小于奈奎斯特频率。")

        if filter_config.filter_kind not in {"lowpass", "highpass", "bandpass", "bandstop"}:
            raise ValidationError("不支持的滤波类型。")

        low_cutoff = filter_config.low_cutoff_hz
        high_cutoff = filter_config.high_cutoff_hz

        if filter_config.filter_kind in {"lowpass", "highpass"}:
            cutoff_hz = low_cutoff
            if cutoff_hz is None or not (0 < cutoff_hz < nyquist_hz):
                raise ValidationError("截止频率必须大于 0 且小于奈奎斯特频率。")
        else:
            if low_cutoff is None or high_cutoff is None:
                raise ValidationError("带通和带阻滤波必须同时提供上下截止频率。")
            if not (0 < low_cutoff < high_cutoff < nyquist_hz):
                raise ValidationError("带通和带阻频率必须满足 0 < 低截止 < 高截止 < 奈奎斯特频率。")

        return nyquist_hz

    def _design_butterworth(self, filter_config: FilterConfig, nyquist_hz: float) -> np.ndarray | None:
        if filter_config.filter_kind in {"lowpass", "highpass"}:
            cutoff_hz = filter_config.low_cutoff_hz
            if cutoff_hz is None:
                return None
            return signal.butter(
                filter_config.order,
                cutoff_hz / nyquist_hz,
                btype="lowpass" if filter_config.filter_kind == "lowpass" else "highpass",
                output="sos",
            )

        if filter_config.low_cutoff_hz is None or filter_config.high_cutoff_hz is None:
            return None

        return signal.butter(
            filter_config.order,
            [filter_config.low_cutoff_hz / nyquist_hz, filter_config.high_cutoff_hz / nyquist_hz],
            btype="bandpass" if filter_config.filter_kind == "bandpass" else "bandstop",
            output="sos",
        )
