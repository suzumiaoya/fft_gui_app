from __future__ import annotations

import pandas as pd
from scipy import signal

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import PreprocessConfig


class SignalPreprocessor:
    def apply(
        self,
        frame: pd.DataFrame,
        signal_column: str,
        preprocess_config: PreprocessConfig,
    ) -> pd.Series:
        if signal_column not in frame.columns:
            raise ValidationError(f"未找到信号列：{signal_column}")

        series = frame[signal_column].astype(float).reset_index(drop=True)
        if series.empty:
            raise ValidationError("没有可用于预处理的信号数据。")

        detrend_mode = preprocess_config.detrend_mode
        if detrend_mode == "none":
            return series
        if detrend_mode in {"constant", "linear"}:
            values = signal.detrend(series.to_numpy(dtype=float), type=detrend_mode)
            return pd.Series(values, name=signal_column)

        raise ValidationError("不支持的去趋势模式。")
