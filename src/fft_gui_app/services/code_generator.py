from __future__ import annotations

from pathlib import Path

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import FilterConfig


class CodeGenerator:
    def render(self, filter_config: FilterConfig, output_base_path: str) -> tuple[Path, Path]:
        normalized_notches = self._validate_config(filter_config)
        base_path = Path(output_base_path)
        header_path = base_path.with_suffix(".h")
        source_path = base_path.with_suffix(".c")

        header_path.write_text(
            self._render_header(filter_config, normalized_notches),
            encoding="utf-8",
        )
        source_path.write_text(
            self._render_source(filter_config, normalized_notches, header_path.name),
            encoding="utf-8",
        )
        return header_path, source_path

    def _validate_config(self, filter_config: FilterConfig) -> list[float]:
        if filter_config.filter_type not in {"lowpass", "highpass"}:
            raise ValidationError("滤波类型必须是 lowpass 或 highpass。")
        if filter_config.sample_rate_hz <= 0:
            raise ValidationError("采样率必须大于 0。")

        nyquist_hz = filter_config.sample_rate_hz / 2.0
        if not (0 < filter_config.cutoff_hz < nyquist_hz):
            raise ValidationError("截止频率必须大于 0 且小于奈奎斯特频率。")

        normalized_notches = sorted(set(float(value) for value in filter_config.notch_freqs_hz))
        for notch_hz in normalized_notches:
            if not (0 < notch_hz < nyquist_hz):
                raise ValidationError("所有陷波频率必须大于 0 且小于奈奎斯特频率。")
        return normalized_notches

    def _render_header(self, filter_config: FilterConfig, normalized_notches: list[float]) -> str:
        return f"""#ifndef FILTER_CONFIG_H
#define FILTER_CONFIG_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {{
#endif

typedef enum FilterType {{
    FILTER_TYPE_LOWPASS = 0,
    FILTER_TYPE_HIGHPASS = 1
}} FilterType;

typedef struct FilterConfig {{
    FilterType filter_type;
    float sample_rate_hz;
    float cutoff_hz;
    const float *notch_freqs_hz;
    size_t notch_count;
}} FilterConfig;

void init_filter_config(FilterConfig *config);
void apply_filter(const FilterConfig *config, const float *input, float *output, size_t length);

#ifdef __cplusplus
}}
#endif

#endif /* FILTER_CONFIG_H */
"""

    def _render_source(
        self,
        filter_config: FilterConfig,
        normalized_notches: list[float],
        header_name: str,
    ) -> str:
        filter_type_constant = (
            "FILTER_TYPE_LOWPASS" if filter_config.filter_type == "lowpass" else "FILTER_TYPE_HIGHPASS"
        )
        if normalized_notches:
            notch_array_body = ", ".join(f"{value:.6f}f" for value in normalized_notches)
            notch_pointer = "k_notch_freqs_hz"
        else:
            notch_array_body = "0.0f"
            notch_pointer = "NULL"

        return f"""#include "{header_name}"

#include <string.h>

static const float k_notch_freqs_hz[] = {{{notch_array_body}}};

void init_filter_config(FilterConfig *config)
{{
    if (config == NULL) {{
        return;
    }}

    config->filter_type = {filter_type_constant};
    config->sample_rate_hz = {filter_config.sample_rate_hz:.6f}f;
    config->cutoff_hz = {filter_config.cutoff_hz:.6f}f;
    config->notch_freqs_hz = {notch_pointer};
    config->notch_count = {len(normalized_notches)};
}}

void apply_filter(const FilterConfig *config, const float *input, float *output, size_t length)
{{
    size_t index;

    if (config == NULL || input == NULL || output == NULL) {{
        return;
    }}

    /* TODO: 在这里接入实际的数字滤波实现。当前版本仅保留输入数据。 */
    for (index = 0; index < length; ++index) {{
        output[index] = input[index];
    }}
}}
"""
