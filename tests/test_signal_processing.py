from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from fft_gui_app.models import FilterConfig, PreprocessConfig
from fft_gui_app.services.filter_preview_service import FilterPreviewService
from fft_gui_app.services.signal_preprocessor import SignalPreprocessor


class SignalProcessingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preprocessor = SignalPreprocessor()
        self.preview_service = FilterPreviewService()

    def test_constant_detrend_removes_mean(self) -> None:
        frame = pd.DataFrame({"sig": np.array([3.0, 4.0, 5.0, 6.0])})
        result = self.preprocessor.apply(frame, "sig", PreprocessConfig(detrend_mode="constant"))
        self.assertAlmostEqual(float(result.mean()), 0.0, places=9)

    def test_linear_detrend_reduces_slope(self) -> None:
        x = np.arange(100, dtype=float)
        frame = pd.DataFrame({"sig": 2.0 * x + 5.0})
        result = self.preprocessor.apply(frame, "sig", PreprocessConfig(detrend_mode="linear"))
        slope = np.polyfit(x, result.to_numpy(dtype=float), 1)[0]
        self.assertAlmostEqual(float(slope), 0.0, places=6)

    def test_lowpass_preview_suppresses_high_frequency(self) -> None:
        sample_rate_hz = 1000.0
        sample_count = 2000
        time_axis = np.arange(sample_count) / sample_rate_hz
        signal_values = np.sin(2 * np.pi * 20.0 * time_axis) + 0.8 * np.sin(2 * np.pi * 200.0 * time_axis)
        frame = pd.DataFrame({"sig": signal_values})

        result = self.preview_service.preview(
            frame=frame,
            signal_column="sig",
            filter_config=FilterConfig(
                filter_kind="lowpass",
                low_cutoff_hz=50.0,
                high_cutoff_hz=None,
                notch_freqs_hz=[],
                notch_q=30.0,
                order=4,
                sample_rate_hz=sample_rate_hz,
            ),
            preprocess_config=PreprocessConfig(detrend_mode="none"),
        )

        freqs = result.frequencies_hz.to_numpy(dtype=float)
        raw = result.raw_spectrum.to_numpy(dtype=float)
        filtered = result.filtered_spectrum.to_numpy(dtype=float)
        idx_20 = int(np.argmin(np.abs(freqs - 20.0)))
        idx_200 = int(np.argmin(np.abs(freqs - 200.0)))

        self.assertEqual(len(result.raw_signal), len(result.filtered_signal))
        self.assertGreater(filtered[idx_20], filtered[idx_200])
        self.assertLess(filtered[idx_200], raw[idx_200])

    def test_notch_preview_suppresses_target_frequency(self) -> None:
        sample_rate_hz = 1000.0
        sample_count = 2000
        time_axis = np.arange(sample_count) / sample_rate_hz
        signal_values = np.sin(2 * np.pi * 50.0 * time_axis) + np.sin(2 * np.pi * 120.0 * time_axis)
        frame = pd.DataFrame({"sig": signal_values})

        result = self.preview_service.preview(
            frame=frame,
            signal_column="sig",
            filter_config=FilterConfig(
                filter_kind="lowpass",
                low_cutoff_hz=300.0,
                high_cutoff_hz=None,
                notch_freqs_hz=[50.0],
                notch_q=30.0,
                order=2,
                sample_rate_hz=sample_rate_hz,
            ),
            preprocess_config=PreprocessConfig(detrend_mode="none"),
        )

        freqs = result.frequencies_hz.to_numpy(dtype=float)
        raw = result.raw_spectrum.to_numpy(dtype=float)
        filtered = result.filtered_spectrum.to_numpy(dtype=float)
        idx_50 = int(np.argmin(np.abs(freqs - 50.0)))

        self.assertLess(filtered[idx_50], raw[idx_50])


if __name__ == "__main__":
    unittest.main()
