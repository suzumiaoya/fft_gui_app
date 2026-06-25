from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import signal

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import FilterConfig
from fft_gui_app.services.code_generator import CodeGenerator


class CodeGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = CodeGenerator()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _base_path(self, name: str) -> str:
        return str(Path(self.temp_dir.name) / name)

    def _extract_section_rows(self, source_text: str) -> list[list[float]]:
        match = re.search(
            r"static const BiquadSection k_filter_sections\[FILTER_SECTION_COUNT\] = \{\n(.*?)\n\};",
            source_text,
            re.S,
        )
        self.assertIsNotNone(match, "未找到 k_filter_sections 系数表。")
        rows = re.findall(r"\{\s*([^{}]+?)\s*\}", match.group(1))
        parsed: list[list[float]] = []
        for row in rows:
            values = [float(value.strip().rstrip("f")) for value in row.split(",")]
            parsed.append(values)
        return parsed

    def _run_df2t(self, sections: list[list[float]], input_signal: np.ndarray) -> np.ndarray:
        states = np.zeros((len(sections), 2), dtype=float)
        output_signal = np.zeros_like(input_signal, dtype=float)

        for sample_index, sample in enumerate(input_signal):
            section_input = float(sample)
            for section_index, row in enumerate(sections):
                b0, b1, b2, a1, a2 = row
                delay0, delay1 = states[section_index]
                section_output = (b0 * section_input) + delay0
                states[section_index, 0] = (b1 * section_input) - (a1 * section_output) + delay1
                states[section_index, 1] = (b2 * section_input) - (a2 * section_output)
                section_input = section_output
            output_signal[sample_index] = section_input

        return output_signal

    def test_render_bandpass_generates_runtime_filter_api(self) -> None:
        header_path, source_path = self.generator.render(
            FilterConfig(
                filter_kind="bandpass",
                low_cutoff_hz=10.0,
                high_cutoff_hz=100.0,
                notch_freqs_hz=[50.0, 50.0, 20.0],
                notch_q=30.0,
                order=4,
                sample_rate_hz=1000.0,
            ),
            self._base_path("bandpass_config"),
        )

        header_text = header_path.read_text(encoding="utf-8")
        source_text = source_path.read_text(encoding="utf-8")

        self.assertIn("typedef struct BiquadSection", header_text)
        self.assertIn("typedef struct FilterState", header_text)
        self.assertIn("size_t get_filter_section_count(void);", header_text)
        self.assertIn("float apply_filter_sample(FilterState *state, float input);", header_text)
        self.assertIn("void apply_filter_block(FilterState *state, const float *input, float *output, size_t length);", header_text)
        self.assertIn("void apply_filter(const FilterConfig *config, FilterState *state, const float *input, float *output, size_t length);", header_text)
        self.assertIn("k_filter_sections[FILTER_SECTION_COUNT]", source_text)
        self.assertIn("apply_filter_sample", source_text)
        self.assertIn("apply_filter_block", source_text)
        self.assertIn("首版 STM32 运行时实现未接入独立 notch 级联", source_text)

    def test_generated_sos_coefficients_match_scipy(self) -> None:
        _, source_path = self.generator.render(
            FilterConfig(
                filter_kind="highpass",
                low_cutoff_hz=20.0,
                high_cutoff_hz=None,
                notch_freqs_hz=[],
                notch_q=30.0,
                order=4,
                sample_rate_hz=200.0,
            ),
            self._base_path("highpass_config"),
        )
        source_text = source_path.read_text(encoding="utf-8")
        parsed_rows = self._extract_section_rows(source_text)

        scipy_sos = signal.butter(4, 20.0 / 100.0, btype="highpass", output="sos")
        expected_rows = []
        for row in scipy_sos:
            a0 = row[3]
            expected_rows.append(
                [
                    float(row[0] / a0),
                    float(row[1] / a0),
                    float(row[2] / a0),
                    float(row[4] / a0),
                    float(row[5] / a0),
                ]
            )

        np.testing.assert_allclose(np.array(parsed_rows), np.array(expected_rows), rtol=1e-6, atol=1e-8)

    def test_generated_df2t_matches_sosfilt(self) -> None:
        _, source_path = self.generator.render(
            FilterConfig(
                filter_kind="lowpass",
                low_cutoff_hz=50.0,
                high_cutoff_hz=None,
                notch_freqs_hz=[],
                notch_q=30.0,
                order=4,
                sample_rate_hz=1000.0,
            ),
            self._base_path("lowpass_df2t"),
        )
        source_text = source_path.read_text(encoding="utf-8")
        parsed_rows = self._extract_section_rows(source_text)

        scipy_sos = signal.butter(4, 50.0 / 500.0, btype="lowpass", output="sos")
        input_signal = np.sin(2 * np.pi * 20.0 * np.arange(512) / 1000.0) + 0.25 * np.sin(
            2 * np.pi * 180.0 * np.arange(512) / 1000.0
        )

        generated_output = self._run_df2t(parsed_rows, input_signal)
        scipy_output = signal.sosfilt(scipy_sos, input_signal)

        np.testing.assert_allclose(generated_output, scipy_output, rtol=1e-5, atol=1e-6)

    def test_invalid_bandpass_cutoff_raises(self) -> None:
        with self.assertRaisesRegex(ValidationError, "带通和带阻频率"):
            self.generator.render(
                FilterConfig(
                    filter_kind="bandpass",
                    low_cutoff_hz=600.0,
                    high_cutoff_hz=700.0,
                    notch_freqs_hz=[],
                    notch_q=30.0,
                    order=4,
                    sample_rate_hz=1000.0,
                ),
                self._base_path("invalid"),
            )


if __name__ == "__main__":
    unittest.main()
