from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class CsvImportConfig:
    file_path: str
    time_column: str | None
    signal_columns: list[str]
    manual_sample_rate_hz: float | None


@dataclass(slots=True)
class SpectrumConfig:
    method: str
    plot_mode: str
    magnitude_mode: str
    window: str
    welch_window: str
    welch_nperseg: int | None
    welch_noverlap: int | None


@dataclass(slots=True)
class FilterConfig:
    filter_kind: str
    low_cutoff_hz: float | None
    high_cutoff_hz: float | None
    notch_freqs_hz: list[float]
    notch_q: float
    order: int
    sample_rate_hz: float


@dataclass(slots=True)
class SpectrumResult:
    frequencies_hz: pd.Series
    series_amplitudes_by_name: dict[str, pd.Series]
    sample_rate_hz: float
    sample_count: int
    method: str
    plot_mode: str
    magnitude_mode: str
    y_axis_unit: str


@dataclass(slots=True)
class PreprocessConfig:
    detrend_mode: str


@dataclass(slots=True)
class PreviewResult:
    time_axis_s: pd.Series
    raw_signal: pd.Series
    filtered_signal: pd.Series
    raw_spectrum: pd.Series
    filtered_spectrum: pd.Series
    frequencies_hz: pd.Series
    sample_rate_hz: float
    sample_count: int
    spectrum_method: str
    y_axis_unit: str


@dataclass(slots=True)
class CsvPreview:
    dataframe: pd.DataFrame
    columns: list[str]
    row_count: int
    preview_rows: list[dict[str, object]]
