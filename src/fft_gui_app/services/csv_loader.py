from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import CsvImportConfig, CsvPreview


@dataclass(slots=True)
class AnalysisFrame:
    dataframe: pd.DataFrame
    sample_rate_hz: float
    inferred_sample_rate_hz: float | None


@dataclass(slots=True)
class SampleRateResolution:
    sample_rate_hz: float
    inferred_sample_rate_hz: float | None


class CsvLoader:
    def load_preview(self, path: str) -> CsvPreview:
        try:
            dataframe = pd.read_csv(path)
        except Exception as exc:  # pragma: no cover - pandas error formatting
            raise ValidationError(f"CSV 读取失败：{exc}") from exc

        if dataframe.empty:
            raise ValidationError("CSV 文件为空，无法分析。")

        return CsvPreview(
            dataframe=dataframe,
            columns=[str(column) for column in dataframe.columns.tolist()],
            row_count=len(dataframe),
            preview_rows=dataframe.head(10).to_dict(orient="records"),
        )

    def build_analysis_frame(self, import_config: CsvImportConfig) -> AnalysisFrame:
        preview = self.load_preview(import_config.file_path)
        dataframe = preview.dataframe.copy()

        if not import_config.signal_columns:
            raise ValidationError("请至少选择一个信号列。")

        missing_columns = [
            column
            for column in [import_config.time_column, *import_config.signal_columns]
            if column is not None and column not in dataframe.columns
        ]
        if missing_columns:
            missing_label = "、".join(sorted(set(missing_columns)))
            raise ValidationError(f"CSV 中缺少列：{missing_label}")

        if (
            import_config.time_column is not None
            and import_config.time_column in import_config.signal_columns
        ):
            raise ValidationError("时间列不能同时作为信号列。")

        columns_to_use = list(import_config.signal_columns)
        if import_config.time_column is not None:
            columns_to_use.append(import_config.time_column)

        cleaned = dataframe.loc[:, columns_to_use].copy()
        for column in columns_to_use:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
        cleaned = cleaned.dropna()

        if cleaned.empty:
            raise ValidationError("选中的时间列或信号列没有可用的数值数据。")

        sample_rate_resolution = self._resolve_sample_rate_from_cleaned_frame(
            cleaned,
            import_config.time_column,
            import_config.manual_sample_rate_hz,
        )

        analysis_frame = cleaned.loc[:, import_config.signal_columns].reset_index(drop=True)
        if len(analysis_frame) < 2:
            raise ValidationError("有效样本数不足，至少需要 2 个样本点。")

        return AnalysisFrame(
            dataframe=analysis_frame,
            sample_rate_hz=sample_rate_resolution.sample_rate_hz,
            inferred_sample_rate_hz=sample_rate_resolution.inferred_sample_rate_hz,
        )

    def resolve_sample_rate(
        self,
        file_path: str | None,
        time_column: str | None,
        manual_sample_rate_hz: float | None,
    ) -> SampleRateResolution:
        if time_column is None:
            return SampleRateResolution(
                sample_rate_hz=self._validate_sample_rate(manual_sample_rate_hz),
                inferred_sample_rate_hz=None,
            )

        if not file_path:
            raise ValidationError("未导入 CSV 时无法通过时间列推导采样率。")

        preview = self.load_preview(file_path)
        dataframe = preview.dataframe.copy()
        if time_column not in dataframe.columns:
            raise ValidationError(f"CSV 中缺少时间列：{time_column}")

        cleaned = pd.DataFrame({time_column: pd.to_numeric(dataframe[time_column], errors="coerce")}).dropna()
        if cleaned.empty:
            raise ValidationError("时间列没有可用的数值数据，无法推导采样率。")

        return self._resolve_sample_rate_from_cleaned_frame(
            cleaned,
            time_column,
            manual_sample_rate_hz,
        )

    def _resolve_sample_rate_from_cleaned_frame(
        self,
        cleaned: pd.DataFrame,
        time_column: str | None,
        manual_sample_rate_hz: float | None,
    ) -> SampleRateResolution:
        inferred_sample_rate_hz = None
        sample_rate_hz = manual_sample_rate_hz

        if time_column is not None:
            time_values = cleaned[time_column].reset_index(drop=True)
            deltas = time_values.diff().dropna()
            if deltas.empty:
                raise ValidationError("时间列样本不足，无法推导采样率。")
            if (deltas <= 0).any():
                raise ValidationError("时间列必须严格递增，且采样间隔必须为正。")

            median_delta = float(deltas.median())
            if median_delta <= 0:
                raise ValidationError("时间列采样间隔无效，无法推导采样率。")
            inferred_sample_rate_hz = 1.0 / median_delta

        if sample_rate_hz is None:
            sample_rate_hz = inferred_sample_rate_hz

        return SampleRateResolution(
            sample_rate_hz=self._validate_sample_rate(sample_rate_hz),
            inferred_sample_rate_hz=inferred_sample_rate_hz,
        )

    def _validate_sample_rate(self, sample_rate_hz: float | None) -> float:
        if sample_rate_hz is None:
            raise ValidationError("没有时间列时，采样率为必填项。")
        if sample_rate_hz <= 0:
            raise ValidationError("采样率必须大于 0。")
        return float(sample_rate_hz)
