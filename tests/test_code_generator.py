from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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

    def test_render_lowpass_with_multiple_notches(self) -> None:
        header_path, source_path = self.generator.render(
            FilterConfig(
                filter_type="lowpass",
                cutoff_hz=100.0,
                notch_freqs_hz=[50.0, 50.0, 10.0],
                sample_rate_hz=1000.0,
            ),
            self._base_path("lowpass_config"),
        )

        header_text = header_path.read_text(encoding="utf-8")
        source_text = source_path.read_text(encoding="utf-8")

        self.assertIn("extern \"C\"", header_text)
        self.assertIn("typedef struct FilterConfig", header_text)
        self.assertIn("void apply_filter", header_text)
        self.assertIn("FILTER_TYPE_LOWPASS", source_text)
        self.assertIn("10.000000f, 50.000000f", source_text)
        self.assertIn("config->notch_count = 2;", source_text)

    def test_render_highpass_without_notches_uses_null_pointer(self) -> None:
        _, source_path = self.generator.render(
            FilterConfig(
                filter_type="highpass",
                cutoff_hz=20.0,
                notch_freqs_hz=[],
                sample_rate_hz=200.0,
            ),
            self._base_path("highpass_config"),
        )
        source_text = source_path.read_text(encoding="utf-8")

        self.assertIn("FILTER_TYPE_HIGHPASS", source_text)
        self.assertIn("config->notch_freqs_hz = NULL;", source_text)
        self.assertIn("config->notch_count = 0;", source_text)

    def test_invalid_cutoff_raises(self) -> None:
        with self.assertRaisesRegex(ValidationError, "截止频率"):
            self.generator.render(
                FilterConfig(
                    filter_type="lowpass",
                    cutoff_hz=600.0,
                    notch_freqs_hz=[],
                    sample_rate_hz=1000.0,
                ),
                self._base_path("invalid"),
            )


if __name__ == "__main__":
    unittest.main()
