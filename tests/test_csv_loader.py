from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import CsvImportConfig
from fft_gui_app.services.csv_loader import CsvLoader


class CsvLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = CsvLoader()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _write_csv(self, name: str, content: str) -> str:
        path = Path(self.temp_dir.name) / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def test_build_analysis_frame_with_manual_sample_rate(self) -> None:
        path = self._write_csv(
            "manual.csv",
            "sig_a,sig_b\n1,2\n3,4\n5,6\n",
        )
        result = self.loader.build_analysis_frame(
            CsvImportConfig(
                file_path=path,
                time_column=None,
                signal_columns=["sig_a", "sig_b"],
                manual_sample_rate_hz=200.0,
            )
        )

        self.assertEqual(result.sample_rate_hz, 200.0)
        self.assertIsNone(result.inferred_sample_rate_hz)
        self.assertEqual(list(result.dataframe.columns), ["sig_a", "sig_b"])
        self.assertEqual(len(result.dataframe), 3)

    def test_build_analysis_frame_infers_sample_rate_from_time_column(self) -> None:
        path = self._write_csv(
            "time.csv",
            "time,sig\n0.0,1\n0.1,2\n0.2,3\n0.3,4\n",
        )
        result = self.loader.build_analysis_frame(
            CsvImportConfig(
                file_path=path,
                time_column="time",
                signal_columns=["sig"],
                manual_sample_rate_hz=None,
            )
        )

        self.assertAlmostEqual(result.sample_rate_hz, 10.0, places=6)
        self.assertAlmostEqual(result.inferred_sample_rate_hz or 0.0, 10.0, places=6)

    def test_manual_sample_rate_overrides_inferred_value(self) -> None:
        path = self._write_csv(
            "override.csv",
            "time,sig\n0.0,1\n0.1,2\n0.2,3\n",
        )
        result = self.loader.build_analysis_frame(
            CsvImportConfig(
                file_path=path,
                time_column="time",
                signal_columns=["sig"],
                manual_sample_rate_hz=50.0,
            )
        )

        self.assertEqual(result.sample_rate_hz, 50.0)
        self.assertAlmostEqual(result.inferred_sample_rate_hz or 0.0, 10.0, places=6)

    def test_time_column_must_be_strictly_increasing(self) -> None:
        path = self._write_csv(
            "bad_time.csv",
            "time,sig\n0.0,1\n0.1,2\n0.1,3\n",
        )
        with self.assertRaisesRegex(ValidationError, "严格递增"):
            self.loader.build_analysis_frame(
                CsvImportConfig(
                    file_path=path,
                    time_column="time",
                    signal_columns=["sig"],
                    manual_sample_rate_hz=None,
                )
            )

    def test_time_column_cannot_be_signal_column(self) -> None:
        path = self._write_csv(
            "same_column.csv",
            "time\n0.0\n0.1\n0.2\n",
        )
        with self.assertRaisesRegex(ValidationError, "时间列不能同时作为信号列"):
            self.loader.build_analysis_frame(
                CsvImportConfig(
                    file_path=path,
                    time_column="time",
                    signal_columns=["time"],
                    manual_sample_rate_hz=None,
                )
            )

    def test_missing_sample_rate_without_time_column_raises(self) -> None:
        path = self._write_csv(
            "missing_rate.csv",
            "sig\n1\n2\n3\n",
        )
        with self.assertRaisesRegex(ValidationError, "采样率为必填项"):
            self.loader.build_analysis_frame(
                CsvImportConfig(
                    file_path=path,
                    time_column=None,
                    signal_columns=["sig"],
                    manual_sample_rate_hz=None,
                )
            )


if __name__ == "__main__":
    unittest.main()
