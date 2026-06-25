from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import signal

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import FilterConfig


class CodeGenerator:
    def render(self, filter_config: FilterConfig, output_base_path: str) -> tuple[Path, Path]:
        normalized_notches = self._validate_config(filter_config)
        sos = self._design_sos(filter_config)
        section_rows = self._normalize_sos_rows(sos)
        if not section_rows:
            raise ValidationError("无法根据当前参数生成有效的滤波器系数。")

        base_path = Path(output_base_path)
        header_path = base_path.with_suffix(".h")
        source_path = base_path.with_suffix(".c")

        header_path.write_text(
            self._render_header(section_count=len(section_rows)),
            encoding="utf-8",
        )
        source_path.write_text(
            self._render_source(
                filter_config=filter_config,
                normalized_notches=normalized_notches,
                section_rows=section_rows,
                header_name=header_path.name,
            ),
            encoding="utf-8",
        )
        return header_path, source_path

    def _validate_config(self, filter_config: FilterConfig) -> list[float]:
        if filter_config.sample_rate_hz <= 0:
            raise ValidationError("采样率必须大于 0。")
        if filter_config.order < 1 or filter_config.order > 10:
            raise ValidationError("滤波阶数必须在 1 到 10 之间。")
        if filter_config.notch_q <= 0:
            raise ValidationError("陷波 Q 值必须大于 0。")

        nyquist_hz = filter_config.sample_rate_hz / 2.0
        if filter_config.filter_kind not in {"lowpass", "highpass", "bandpass", "bandstop"}:
            raise ValidationError("滤波类型必须是 lowpass、highpass、bandpass 或 bandstop。")

        if filter_config.filter_kind in {"lowpass", "highpass"}:
            cutoff_hz = filter_config.low_cutoff_hz
            if cutoff_hz is None or not (0 < cutoff_hz < nyquist_hz):
                raise ValidationError("截止频率必须大于 0 且小于奈奎斯特频率。")
        else:
            low_cutoff_hz = filter_config.low_cutoff_hz
            high_cutoff_hz = filter_config.high_cutoff_hz
            if low_cutoff_hz is None or high_cutoff_hz is None:
                raise ValidationError("带通和带阻滤波必须同时提供上下截止频率。")
            if not (0 < low_cutoff_hz < high_cutoff_hz < nyquist_hz):
                raise ValidationError("带通和带阻频率必须满足 0 < 低截止 < 高截止 < 奈奎斯特频率。")

        normalized_notches = sorted(set(float(value) for value in filter_config.notch_freqs_hz))
        for notch_hz in normalized_notches:
            if not (0 < notch_hz < nyquist_hz):
                raise ValidationError("所有陷波频率必须大于 0 且小于奈奎斯特频率。")
        return normalized_notches

    def _design_sos(self, filter_config: FilterConfig) -> np.ndarray:
        nyquist_hz = filter_config.sample_rate_hz / 2.0

        if filter_config.filter_kind in {"lowpass", "highpass"}:
            cutoff_hz = filter_config.low_cutoff_hz
            if cutoff_hz is None:
                raise ValidationError("低通和高通滤波必须提供截止频率。")
            return signal.butter(
                filter_config.order,
                cutoff_hz / nyquist_hz,
                btype="lowpass" if filter_config.filter_kind == "lowpass" else "highpass",
                output="sos",
            )

        if filter_config.low_cutoff_hz is None or filter_config.high_cutoff_hz is None:
            raise ValidationError("带通和带阻滤波必须同时提供上下截止频率。")

        return signal.butter(
            filter_config.order,
            [filter_config.low_cutoff_hz / nyquist_hz, filter_config.high_cutoff_hz / nyquist_hz],
            btype="bandpass" if filter_config.filter_kind == "bandpass" else "bandstop",
            output="sos",
        )

    def _normalize_sos_rows(self, sos: np.ndarray) -> list[tuple[float, float, float, float, float]]:
        if sos.ndim != 2 or sos.shape[1] != 6:
            raise ValidationError("生成的 SOS 系数格式无效。")

        rows: list[tuple[float, float, float, float, float]] = []
        for row in sos:
            a0 = float(row[3])
            if abs(a0) < 1e-12:
                raise ValidationError("滤波器反馈系数 a0 无效。")
            b0 = float(row[0] / a0)
            b1 = float(row[1] / a0)
            b2 = float(row[2] / a0)
            a1 = float(row[4] / a0)
            a2 = float(row[5] / a0)
            rows.append((b0, b1, b2, a1, a2))
        return rows

    def _render_header(self, section_count: int) -> str:
        return f"""#ifndef FILTER_CONFIG_H
#define FILTER_CONFIG_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {{
#endif

#define FILTER_SECTION_COUNT ({section_count}u)

typedef enum FilterType {{
    FILTER_TYPE_LOWPASS = 0,
    FILTER_TYPE_HIGHPASS = 1,
    FILTER_TYPE_BANDPASS = 2,
    FILTER_TYPE_BANDSTOP = 3
}} FilterType;

typedef struct BiquadSection {{
    float b0;
    float b1;
    float b2;
    float a1;
    float a2;
}} BiquadSection;

typedef struct FilterState {{
    float state[FILTER_SECTION_COUNT][2];
}} FilterState;

typedef struct FilterConfig {{
    FilterType filter_kind;
    float sample_rate_hz;
    float low_cutoff_hz;
    float high_cutoff_hz;
    float notch_q;
    unsigned int order;
    const float *notch_freqs_hz;
    size_t notch_count;
}} FilterConfig;

void init_filter_config(FilterConfig *config);
size_t get_filter_section_count(void);
const BiquadSection *get_filter_sections(void);
void init_filter_state(FilterState *state);
float apply_filter_sample(FilterState *state, float input);
void apply_filter_block(FilterState *state, const float *input, float *output, size_t length);
void apply_filter(const FilterConfig *config, FilterState *state, const float *input, float *output, size_t length);

#ifdef __cplusplus
}}
#endif

#endif /* FILTER_CONFIG_H */
"""

    def _render_source(
        self,
        filter_config: FilterConfig,
        normalized_notches: list[float],
        section_rows: list[tuple[float, float, float, float, float]],
        header_name: str,
    ) -> str:
        filter_type_constant = {
            "lowpass": "FILTER_TYPE_LOWPASS",
            "highpass": "FILTER_TYPE_HIGHPASS",
            "bandpass": "FILTER_TYPE_BANDPASS",
            "bandstop": "FILTER_TYPE_BANDSTOP",
        }[filter_config.filter_kind]

        notch_array_body = ", ".join(f"{value:.6f}f" for value in normalized_notches) if normalized_notches else "0.0f"
        notch_pointer = "k_notch_freqs_hz" if normalized_notches else "NULL"
        notch_comment = ""
        if normalized_notches:
            notch_comment = (
                "/* 注意：首版 STM32 运行时实现未接入独立 notch 级联，"
                "下列 notch 参数仅保留用于配置记录与后续扩展。 */\n"
            )

        section_array_body = ",\n".join(
            "    { %.9ef, %.9ef, %.9ef, %.9ef, %.9ef }" % row for row in section_rows
        )

        low_cutoff_hz = 0.0 if filter_config.low_cutoff_hz is None else filter_config.low_cutoff_hz
        high_cutoff_hz = 0.0 if filter_config.high_cutoff_hz is None else filter_config.high_cutoff_hz

        return f"""#include "{header_name}"

#include <string.h>

/* 系数由 Python/Scipy 离线计算生成，适用于 STM32 float32 处理链。 */
{notch_comment}static const float k_notch_freqs_hz[] = {{{notch_array_body}}};
static const BiquadSection k_filter_sections[FILTER_SECTION_COUNT] = {{
{section_array_body}
}};

void init_filter_config(FilterConfig *config)
{{
    if (config == NULL) {{
        return;
    }}

    config->filter_kind = {filter_type_constant};
    config->sample_rate_hz = {filter_config.sample_rate_hz:.6f}f;
    config->low_cutoff_hz = {low_cutoff_hz:.6f}f;
    config->high_cutoff_hz = {high_cutoff_hz:.6f}f;
    config->notch_q = {filter_config.notch_q:.6f}f;
    config->order = {filter_config.order};
    config->notch_freqs_hz = {notch_pointer};
    config->notch_count = {len(normalized_notches)};
}}

size_t get_filter_section_count(void)
{{
    return FILTER_SECTION_COUNT;
}}

const BiquadSection *get_filter_sections(void)
{{
    return k_filter_sections;
}}

void init_filter_state(FilterState *state)
{{
    if (state == NULL) {{
        return;
    }}

    (void)memset(state, 0, sizeof(*state));
}}

float apply_filter_sample(FilterState *state, float input)
{{
    size_t section_index;
    float section_input = input;

    if (state == NULL) {{
        return input;
    }}

    for (section_index = 0; section_index < FILTER_SECTION_COUNT; ++section_index) {{
        const BiquadSection *section = &k_filter_sections[section_index];
        float *delay = state->state[section_index];
        const float output = (section->b0 * section_input) + delay[0];

        delay[0] = (section->b1 * section_input) - (section->a1 * output) + delay[1];
        delay[1] = (section->b2 * section_input) - (section->a2 * output);
        section_input = output;
    }}

    return section_input;
}}

void apply_filter_block(FilterState *state, const float *input, float *output, size_t length)
{{
    size_t index;

    if (state == NULL || input == NULL || output == NULL) {{
        return;
    }}

    for (index = 0; index < length; ++index) {{
        output[index] = apply_filter_sample(state, input[index]);
    }}
}}

void apply_filter(const FilterConfig *config, FilterState *state, const float *input, float *output, size_t length)
{{
    (void)config;
    apply_filter_block(state, input, output, length);
}}
"""
