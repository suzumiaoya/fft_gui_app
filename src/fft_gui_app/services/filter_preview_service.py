from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import signal

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import FilterConfig, PreprocessConfig, PreviewResult, SpectrumConfig
from fft_gui_app.services.filter_designer import FilterDesigner
from fft_gui_app.services.fft_analyzer import FftAnalyzer
from fft_gui_app.services.signal_preprocessor import SignalPreprocessor


class FilterPreviewService:
    def __init__(
        self,
        preprocessor: SignalPreprocessor | None = None,
        filter_designer: FilterDesigner | None = None,
        spectrum_analyzer: FftAnalyzer | None = None,
    ) -> None:
        self.preprocessor = preprocessor or SignalPreprocessor()
        self.filter_designer = filter_designer or FilterDesigner()
        self.spectrum_analyzer = spectrum_analyzer or FftAnalyzer()

    def preview(
        self,
        frame: pd.DataFrame,
        signal_column: str,
        filter_config: FilterConfig,
        preprocess_config: PreprocessConfig,
    ) -> PreviewResult:
        processed_signal = self.preprocessor.apply(frame, signal_column, preprocess_config)
        if len(processed_signal) < 2:
            raise ValidationError("预览至少需要 2 个样本点。")

        sos = self.filter_designer.design(filter_config)
        filtered_values = signal.sosfiltfilt(sos, processed_signal.to_numpy(dtype=float))
        filtered_signal = pd.Series(filtered_values, name=f"{signal_column}_filtered")

        time_axis_s = pd.Series(
            np.arange(len(processed_signal), dtype=float) / filter_config.sample_rate_hz,
            name="time_s",
        )

        spectrum_config = SpectrumConfig(
            method="fft",
            plot_mode="overlay",
            magnitude_mode="linear",
            remove_mean=False,
            window="hann",
            welch_window="hann",
            welch_nperseg=None,
            welch_noverlap=None,
        )
        spectrum_frame = pd.DataFrame(
            {
                "raw": processed_signal.to_numpy(dtype=float),
                "filtered": filtered_signal.to_numpy(dtype=float),
            }
        )
        spectrum_result = self.spectrum_analyzer.compute(
            frame=spectrum_frame,
            signal_columns=["raw", "filtered"],
            spectrum_config=spectrum_config,
            sample_rate_hz=filter_config.sample_rate_hz,
        )

        return PreviewResult(
            time_axis_s=time_axis_s,
            raw_signal=processed_signal,
            filtered_signal=filtered_signal,
            raw_spectrum=spectrum_result.series_amplitudes_by_name["raw"],
            filtered_spectrum=spectrum_result.series_amplitudes_by_name["filtered"],
            frequencies_hz=spectrum_result.frequencies_hz,
            sample_rate_hz=filter_config.sample_rate_hz,
            sample_count=len(processed_signal),
            spectrum_method=spectrum_result.method,
            y_axis_unit=spectrum_result.y_axis_unit,
        )
