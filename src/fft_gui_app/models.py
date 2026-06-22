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
    plot_mode: str
    magnitude_mode: str
    window: str


@dataclass(slots=True)
class FilterConfig:
    filter_type: str
    cutoff_hz: float
    notch_freqs_hz: list[float]
    sample_rate_hz: float


@dataclass(slots=True)
class SpectrumResult:
    frequencies_hz: pd.Series
    series_amplitudes_by_name: dict[str, pd.Series]
    sample_rate_hz: float
    sample_count: int
    plot_mode: str
    magnitude_mode: str


@dataclass(slots=True)
class CsvPreview:
    dataframe: pd.DataFrame
    columns: list[str]
    row_count: int
    preview_rows: list[dict[str, object]]
