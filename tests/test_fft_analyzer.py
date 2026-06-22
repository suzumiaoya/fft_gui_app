from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from fft_gui_app.models import SpectrumConfig
from fft_gui_app.services.fft_analyzer import FftAnalyzer


class FftAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = FftAnalyzer()

    def test_single_tone_peak_is_detected(self) -> None:
        sample_rate_hz = 1024.0
        tone_hz = 64.0
        sample_count = 1024
        time_axis = np.arange(sample_count) / sample_rate_hz
        frame = pd.DataFrame({"sig": np.sin(2 * np.pi * tone_hz * time_axis)})

        result = self.analyzer.compute(
            frame=frame,
            signal_columns=["sig"],
            spectrum_config=SpectrumConfig(plot_mode="overlay", magnitude_mode="linear", window="none"),
            sample_rate_hz=sample_rate_hz,
        )

        peak_index = int(result.series_amplitudes_by_name["sig"].idxmax())
        peak_frequency = float(result.frequencies_hz.iloc[peak_index])
        self.assertAlmostEqual(peak_frequency, tone_hz, places=6)

    def test_db_mode_and_hann_window_work(self) -> None:
        sample_rate_hz = 100.0
        frame = pd.DataFrame({"sig": [0.0, 1.0, 0.0, -1.0] * 32})

        result = self.analyzer.compute(
            frame=frame,
            signal_columns=["sig"],
            spectrum_config=SpectrumConfig(plot_mode="overlay", magnitude_mode="db", window="hann"),
            sample_rate_hz=sample_rate_hz,
        )

        self.assertEqual(result.magnitude_mode, "db")
        self.assertEqual(len(result.frequencies_hz), len(result.series_amplitudes_by_name["sig"]))

    def test_multiple_series_in_separate_mode_are_returned(self) -> None:
        frame = pd.DataFrame(
            {
                "sig_a": np.linspace(0.0, 1.0, 16),
                "sig_b": np.linspace(1.0, 0.0, 16),
            }
        )

        result = self.analyzer.compute(
            frame=frame,
            signal_columns=["sig_a", "sig_b"],
            spectrum_config=SpectrumConfig(plot_mode="separate", magnitude_mode="linear", window="none"),
            sample_rate_hz=16.0,
        )

        self.assertEqual(result.plot_mode, "separate")
        self.assertEqual(set(result.series_amplitudes_by_name.keys()), {"sig_a", "sig_b"})


if __name__ == "__main__":
    unittest.main()
