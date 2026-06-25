from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from fft_gui_app.models import SpectrumConfig
from fft_gui_app.services.fft_analyzer import FftAnalyzer


class FftAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = FftAnalyzer()

    def test_single_tone_fft_peak_is_detected(self) -> None:
        sample_rate_hz = 1024.0
        tone_hz = 64.0
        sample_count = 1024
        time_axis = np.arange(sample_count) / sample_rate_hz
        frame = pd.DataFrame({"sig": np.sin(2 * np.pi * tone_hz * time_axis)})

        result = self.analyzer.compute(
            frame=frame,
            signal_columns=["sig"],
            spectrum_config=SpectrumConfig(
                method="fft",
                plot_mode="overlay",
                magnitude_mode="linear",
                window="none",
                welch_window="hann",
                welch_nperseg=None,
                welch_noverlap=None,
            ),
            sample_rate_hz=sample_rate_hz,
        )

        peak_index = int(result.series_amplitudes_by_name["sig"].idxmax())
        peak_frequency = float(result.frequencies_hz.iloc[peak_index])
        self.assertAlmostEqual(peak_frequency, tone_hz, places=6)
        self.assertEqual(result.method, "fft")

    def test_welch_peak_is_detected(self) -> None:
        sample_rate_hz = 512.0
        tone_hz = 40.0
        sample_count = 2048
        time_axis = np.arange(sample_count) / sample_rate_hz
        frame = pd.DataFrame({"sig": np.sin(2 * np.pi * tone_hz * time_axis)})

        result = self.analyzer.compute(
            frame=frame,
            signal_columns=["sig"],
            spectrum_config=SpectrumConfig(
                method="welch",
                plot_mode="overlay",
                magnitude_mode="linear",
                window="hann",
                welch_window="hann",
                welch_nperseg=512,
                welch_noverlap=256,
            ),
            sample_rate_hz=sample_rate_hz,
        )

        peak_index = int(result.series_amplitudes_by_name["sig"].idxmax())
        peak_frequency = float(result.frequencies_hz.iloc[peak_index])
        self.assertAlmostEqual(peak_frequency, tone_hz, delta=2.0)
        self.assertEqual(result.method, "welch")
        self.assertEqual(result.y_axis_unit, "PSD")

    def test_invalid_welch_overlap_raises(self) -> None:
        frame = pd.DataFrame({"sig": np.linspace(0.0, 1.0, 32)})

        with self.assertRaisesRegex(Exception, "noverlap"):
            self.analyzer.compute(
                frame=frame,
                signal_columns=["sig"],
                spectrum_config=SpectrumConfig(
                    method="welch",
                    plot_mode="overlay",
                    magnitude_mode="linear",
                    window="hann",
                    welch_window="hann",
                    welch_nperseg=16,
                    welch_noverlap=16,
                ),
                sample_rate_hz=64.0,
            )

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
            spectrum_config=SpectrumConfig(
                method="fft",
                plot_mode="separate",
                magnitude_mode="linear",
                window="none",
                welch_window="hann",
                welch_nperseg=None,
                welch_noverlap=None,
            ),
            sample_rate_hz=16.0,
        )

        self.assertEqual(result.plot_mode, "separate")
        self.assertEqual(set(result.series_amplitudes_by_name.keys()), {"sig_a", "sig_b"})


if __name__ == "__main__":
    unittest.main()
