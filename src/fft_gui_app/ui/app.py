from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from matplotlib import font_manager, rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import CsvImportConfig, FilterConfig, SpectrumConfig, SpectrumResult
from fft_gui_app.services.code_generator import CodeGenerator
from fft_gui_app.services.csv_loader import AnalysisFrame, CsvLoader
from fft_gui_app.services.fft_analyzer import FftAnalyzer


PLOT_MODE_LABELS = {"叠加对比": "overlay", "分别显示": "separate"}
PLOT_MODE_VALUES = {value: label for label, value in PLOT_MODE_LABELS.items()}
MAGNITUDE_MODE_LABELS = {"线性幅值": "linear", "dB": "db"}
MAGNITUDE_MODE_VALUES = {value: label for label, value in MAGNITUDE_MODE_LABELS.items()}
WINDOW_LABELS = {"Hann": "hann", "无窗": "none"}
WINDOW_VALUES = {value: label for label, value in WINDOW_LABELS.items()}
FILTER_TYPE_LABELS = {"低通": "lowpass", "高通": "highpass"}
FILTER_TYPE_VALUES = {value: label for label, value in FILTER_TYPE_LABELS.items()}


def configure_matplotlib_fonts() -> None:
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Zen Hei",
        "Arial Unicode MS",
    ]
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in candidates:
        if font_name in available_fonts:
            rcParams["font.family"] = font_name
            rcParams["axes.unicode_minus"] = False
            return


class FftGuiApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("CSV FFT 频谱分析工具")
        self.geometry("1440x860")
        self.minsize(1200, 760)

        self.csv_loader = CsvLoader()
        self.fft_analyzer = FftAnalyzer()
        self.code_generator = CodeGenerator()

        self.current_csv_path: str | None = None
        self.preview_columns: list[str] = []
        self.analysis_frame: AnalysisFrame | None = None
        self.current_spectrum_result: SpectrumResult | None = None
        self.last_inferred_sample_rate_hz: float | None = None

        self._init_variables()
        self._build_layout()
        self._set_status("请先导入 CSV 文件。")

    def _init_variables(self) -> None:
        self.time_column_var = tk.StringVar(value="")
        self.sample_rate_var = tk.StringVar(value="")
        self.plot_mode_var = tk.StringVar(value="叠加对比")
        self.magnitude_mode_var = tk.StringVar(value="线性幅值")
        self.window_var = tk.StringVar(value="Hann")
        self.filter_type_var = tk.StringVar(value="低通")
        self.cutoff_var = tk.StringVar(value="")
        self.notch_var = tk.StringVar(value="")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.control_frame = ctk.CTkScrollableFrame(self, width=430, corner_radius=0)
        self.control_frame.grid(row=0, column=0, sticky="nsew")
        self.control_frame.grid_columnconfigure(0, weight=1)

        self.plot_frame = ctk.CTkFrame(self, corner_radius=0)
        self.plot_frame.grid(row=0, column=1, sticky="nsew")
        self.plot_frame.grid_rowconfigure(1, weight=1)
        self.plot_frame.grid_columnconfigure(0, weight=1)

        self._build_control_panel()
        self._build_plot_panel()

    def _build_control_panel(self) -> None:
        row = 0

        title = ctk.CTkLabel(
            self.control_frame,
            text="CSV FFT 频谱分析",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=row, column=0, padx=18, pady=(18, 12), sticky="w")
        row += 1

        file_section, file_content = self._section_frame("文件导入")
        file_section.grid(row=row, column=0, padx=18, pady=10, sticky="ew")
        file_content.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(file_content, text="导入 CSV", command=self._on_import_csv).grid(
            row=0, column=0, padx=12, pady=(12, 8), sticky="ew"
        )
        self.file_label = ctk.CTkLabel(file_content, text="当前文件：未选择", justify="left", wraplength=360)
        self.file_label.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="w")
        row += 1

        data_section, data_content = self._section_frame("数据选择")
        data_section.grid(row=row, column=0, padx=18, pady=10, sticky="ew")
        data_content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(data_content, text="时间列").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        self.time_column_menu = ctk.CTkOptionMenu(
            data_content,
            values=[""],
            variable=self.time_column_var,
            command=self._on_time_column_changed,
        )
        self.time_column_menu.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(data_content, text="信号列（可多选）").grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        listbox_frame = ctk.CTkFrame(data_content, fg_color="transparent")
        listbox_frame.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")
        listbox_frame.grid_columnconfigure(0, weight=1)
        listbox_frame.grid_rowconfigure(0, weight=1)

        self.signal_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.EXTENDED,
            exportselection=False,
            height=8,
            activestyle="dotbox",
        )
        self.signal_listbox.grid(row=0, column=0, sticky="ew")
        signal_scroll = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.signal_listbox.yview)
        signal_scroll.grid(row=0, column=1, sticky="ns")
        self.signal_listbox.configure(yscrollcommand=signal_scroll.set)

        ctk.CTkLabel(data_content, text="采样率 Hz").grid(row=4, column=0, padx=12, pady=(0, 4), sticky="w")
        self.sample_rate_entry = ctk.CTkEntry(data_content, textvariable=self.sample_rate_var)
        self.sample_rate_entry.grid(row=5, column=0, padx=12, pady=(0, 6), sticky="ew")
        self.sample_rate_hint = ctk.CTkLabel(data_content, text="有时间列时自动推导，可手动覆盖。", text_color="gray50")
        self.sample_rate_hint.grid(row=6, column=0, padx=12, pady=(0, 12), sticky="w")
        row += 1

        spectrum_section, spectrum_content = self._section_frame("频谱参数")
        spectrum_section.grid(row=row, column=0, padx=18, pady=10, sticky="ew")
        spectrum_content.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(spectrum_content, text="显示方式").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkLabel(spectrum_content, text="幅值模式").grid(row=0, column=1, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkOptionMenu(
            spectrum_content,
            values=list(PLOT_MODE_LABELS.keys()),
            variable=self.plot_mode_var,
        ).grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkOptionMenu(
            spectrum_content,
            values=list(MAGNITUDE_MODE_LABELS.keys()),
            variable=self.magnitude_mode_var,
        ).grid(row=1, column=1, padx=12, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(spectrum_content, text="窗口函数").grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkOptionMenu(
            spectrum_content,
            values=list(WINDOW_LABELS.keys()),
            variable=self.window_var,
        ).grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkButton(spectrum_content, text="生成频谱", command=self._on_generate_spectrum).grid(
            row=3, column=1, padx=12, pady=(0, 12), sticky="ew"
        )
        row += 1

        filter_section, filter_content = self._section_frame("代码生成参数")
        filter_section.grid(row=row, column=0, padx=18, pady=10, sticky="ew")
        filter_content.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(filter_content, text="滤波类型").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkLabel(filter_content, text="截止频率 Hz").grid(row=0, column=1, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkOptionMenu(
            filter_content,
            values=list(FILTER_TYPE_LABELS.keys()),
            variable=self.filter_type_var,
        ).grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkEntry(filter_content, textvariable=self.cutoff_var).grid(
            row=1, column=1, padx=12, pady=(0, 12), sticky="ew"
        )

        ctk.CTkLabel(filter_content, text="陷波频率 Hz（用逗号分隔）").grid(
            row=2, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w"
        )
        ctk.CTkEntry(filter_content, textvariable=self.notch_var).grid(
            row=3, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew"
        )
        ctk.CTkButton(filter_content, text="导出 C 代码", command=self._on_export_code).grid(
            row=4, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew"
        )
        row += 1

        preview_section, preview_content = self._section_frame("CSV 预览")
        preview_section.grid(row=row, column=0, padx=18, pady=(10, 18), sticky="nsew")
        preview_content.grid_columnconfigure(0, weight=1)
        preview_content.grid_rowconfigure(0, weight=1)

        self.preview_tree = ttk.Treeview(preview_content, show="headings", height=10)
        self.preview_tree.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        preview_scroll = ttk.Scrollbar(preview_content, orient="vertical", command=self.preview_tree.yview)
        preview_scroll.grid(row=0, column=1, pady=12, sticky="ns")
        self.preview_tree.configure(yscrollcommand=preview_scroll.set)

    def _build_plot_panel(self) -> None:
        header = ctk.CTkFrame(self.plot_frame, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(header, text="", anchor="w")
        self.status_label.grid(row=0, column=0, padx=16, pady=12, sticky="ew")

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        toolbar_frame = ctk.CTkFrame(self.plot_frame, corner_radius=0)
        toolbar_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(fill="x")

        self._render_placeholder_plot()

    def _section_frame(self, title: str) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        frame = ctk.CTkFrame(self.control_frame)
        frame.grid_columnconfigure(0, weight=1)
        label = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold"))
        label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.grid(row=1, column=0, sticky="ew")
        return frame, content

    def _on_import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 CSV 文件",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if not path:
            return

        try:
            preview = self.csv_loader.load_preview(path)
        except ValidationError as exc:
            self._show_error(str(exc))
            return

        self.current_csv_path = path
        self.preview_columns = preview.columns
        self.analysis_frame = None
        self.current_spectrum_result = None
        self.last_inferred_sample_rate_hz = None

        self.file_label.configure(text=f"当前文件：{path}")
        self._populate_columns(preview.columns)
        self._populate_preview_table(preview.preview_rows, preview.columns)
        self._render_placeholder_plot()
        self._set_status(f"已导入 {Path(path).name}，共 {preview.row_count} 行。")

    def _populate_columns(self, columns: list[str]) -> None:
        menu_values = [""] + columns
        self.time_column_menu.configure(values=menu_values)
        self.time_column_var.set("")
        self.signal_listbox.delete(0, tk.END)
        for column in columns:
            self.signal_listbox.insert(tk.END, column)

        self.sample_rate_var.set("")
        self.sample_rate_hint.configure(text="有时间列时自动推导，可手动覆盖。")

    def _populate_preview_table(self, rows: list[dict[str, object]], columns: list[str]) -> None:
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.preview_tree["columns"] = columns
        for column in columns:
            self.preview_tree.heading(column, text=column)
            self.preview_tree.column(column, width=120, stretch=True, anchor="center")

        for row in rows:
            values = [row.get(column, "") for column in columns]
            self.preview_tree.insert("", tk.END, values=values)

    def _on_time_column_changed(self, _: str) -> None:
        selected = self.time_column_var.get() or None
        if selected is None:
            self.sample_rate_hint.configure(text="有时间列时自动推导，可手动覆盖。")
            return

        try:
            sample_rate_resolution = self.csv_loader.resolve_sample_rate(
                file_path=self.current_csv_path,
                time_column=selected,
                manual_sample_rate_hz=self._parse_optional_float(self.sample_rate_var.get()),
            )
        except ValidationError:
            self.sample_rate_hint.configure(text="时间列已选择；生成频谱时会再次校验采样率。")
            return

        self.last_inferred_sample_rate_hz = sample_rate_resolution.inferred_sample_rate_hz
        if sample_rate_resolution.inferred_sample_rate_hz is not None and not self.sample_rate_var.get().strip():
            self.sample_rate_var.set(f"{sample_rate_resolution.inferred_sample_rate_hz:.6f}")
        if sample_rate_resolution.inferred_sample_rate_hz is not None:
            self.sample_rate_hint.configure(
                text=f"自动推导采样率：{sample_rate_resolution.inferred_sample_rate_hz:.6f} Hz，可手动覆盖。"
            )

    def _on_generate_spectrum(self) -> None:
        try:
            import_config = self._build_import_config()
            analysis = self.csv_loader.build_analysis_frame(import_config)
            spectrum_config = SpectrumConfig(
                plot_mode=PLOT_MODE_LABELS[self.plot_mode_var.get()],
                magnitude_mode=MAGNITUDE_MODE_LABELS[self.magnitude_mode_var.get()],
                window=WINDOW_LABELS[self.window_var.get()],
            )
            spectrum_result = self.fft_analyzer.compute(
                frame=analysis.dataframe,
                signal_columns=import_config.signal_columns,
                spectrum_config=spectrum_config,
                sample_rate_hz=analysis.sample_rate_hz,
            )
        except ValidationError as exc:
            self._show_error(str(exc))
            return

        self.analysis_frame = analysis
        self.current_spectrum_result = spectrum_result
        self.last_inferred_sample_rate_hz = analysis.inferred_sample_rate_hz
        if analysis.inferred_sample_rate_hz is not None:
            self.sample_rate_hint.configure(
                text=f"自动推导采样率：{analysis.inferred_sample_rate_hz:.6f} Hz，可手动覆盖。"
            )
        self._render_spectrum_plot(spectrum_result)
        self._set_status(
            f"频谱生成完成：{len(import_config.signal_columns)} 个信号，"
            f"{analysis.sample_rate_hz:.3f} Hz，{spectrum_result.sample_count} 个样本。"
        )

    def _on_export_code(self) -> None:
        try:
            filter_config = self._build_filter_config()
        except ValidationError as exc:
            self._show_error(str(exc))
            return

        path = filedialog.asksaveasfilename(
            title="导出 C 代码",
            defaultextension=".h",
            initialfile=self._default_code_base_name(),
            filetypes=[("C Header", "*.h"), ("所有文件", "*.*")],
        )
        if not path:
            return

        try:
            header_path, source_path = self.code_generator.render(
                filter_config,
                str(Path(path).with_suffix("")),
            )
        except ValidationError as exc:
            self._show_error(str(exc))
            return

        self._set_status(f"已导出代码：{header_path.name} 和 {source_path.name}")
        messagebox.showinfo("导出成功", f"已生成：\n{header_path}\n{source_path}")

    def _build_import_config(self) -> CsvImportConfig:
        if not self.current_csv_path:
            raise ValidationError("请先导入 CSV 文件。")

        return CsvImportConfig(
            file_path=self.current_csv_path,
            time_column=self.time_column_var.get() or None,
            signal_columns=self._get_selected_signal_columns(),
            manual_sample_rate_hz=self._parse_optional_float(self.sample_rate_var.get()),
        )

    def _build_filter_config(self) -> FilterConfig:
        if not self.current_csv_path:
            raise ValidationError("请先导入 CSV 文件。")

        sample_rate_resolution = self.csv_loader.resolve_sample_rate(
            file_path=self.current_csv_path,
            time_column=self.time_column_var.get() or None,
            manual_sample_rate_hz=self._parse_optional_float(self.sample_rate_var.get()),
        )
        return FilterConfig(
            filter_type=FILTER_TYPE_LABELS[self.filter_type_var.get()],
            cutoff_hz=self._parse_required_float(self.cutoff_var.get(), "截止频率"),
            notch_freqs_hz=self._parse_notch_frequencies(self.notch_var.get()),
            sample_rate_hz=sample_rate_resolution.sample_rate_hz,
        )

    def _get_selected_signal_columns(self) -> list[str]:
        selected_indices = self.signal_listbox.curselection()
        return [self.signal_listbox.get(index) for index in selected_indices]

    def _parse_optional_float(self, raw_value: str) -> float | None:
        if not raw_value.strip():
            return None
        try:
            return float(raw_value)
        except ValueError as exc:
            raise ValidationError("采样率必须是数字。") from exc

    def _parse_required_float(self, raw_value: str, field_name: str) -> float:
        if not raw_value.strip():
            raise ValidationError(f"{field_name}不能为空。")
        try:
            return float(raw_value)
        except ValueError as exc:
            raise ValidationError(f"{field_name}必须是数字。") from exc

    def _parse_notch_frequencies(self, raw_value: str) -> list[float]:
        if not raw_value.strip():
            return []
        values: list[float] = []
        for part in raw_value.split(","):
            text = part.strip()
            if not text:
                continue
            try:
                values.append(float(text))
            except ValueError as exc:
                raise ValidationError("陷波频率必须是用逗号分隔的数字列表。") from exc
        return values

    def _render_placeholder_plot(self) -> None:
        self.figure.clear()
        axis = self.figure.add_subplot(111)
        axis.set_title("频谱图")
        axis.set_xlabel("频率 (Hz)")
        axis.set_ylabel("幅值")
        axis.text(0.5, 0.5, "导入 CSV 后点击“生成频谱”开始分析", ha="center", va="center", transform=axis.transAxes)
        axis.grid(True, alpha=0.25)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _render_spectrum_plot(self, result: SpectrumResult) -> None:
        self.figure.clear()

        if result.plot_mode == "overlay":
            axis = self.figure.add_subplot(111)
            self._draw_overlay(axis, result)
        else:
            axes = self.figure.subplots(
                nrows=len(result.series_amplitudes_by_name),
                ncols=1,
                sharex=True,
                squeeze=False,
            ).flatten()
            for axis, (name, amplitudes) in zip(axes, result.series_amplitudes_by_name.items()):
                axis.plot(result.frequencies_hz, amplitudes, label=name, linewidth=1.2)
                axis.set_ylabel("幅值(dB)" if result.magnitude_mode == "db" else "幅值")
                axis.legend(loc="upper right")
                axis.grid(True, alpha=0.25)
            axes[-1].set_xlabel("频率 (Hz)")
            self.figure.suptitle("FFT 单边频谱")

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _draw_overlay(self, axis, result: SpectrumResult) -> None:
        for name, amplitudes in result.series_amplitudes_by_name.items():
            axis.plot(result.frequencies_hz, amplitudes, label=name, linewidth=1.2)
        axis.set_title("FFT 单边频谱")
        axis.set_xlabel("频率 (Hz)")
        axis.set_ylabel("幅值(dB)" if result.magnitude_mode == "db" else "幅值")
        axis.legend(loc="upper right")
        axis.grid(True, alpha=0.25)

    def _default_code_base_name(self) -> str:
        if self.current_csv_path:
            return f"{Path(self.current_csv_path).stem}_filter_config"
        return "filter_config"

    def _set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def _show_error(self, message: str) -> None:
        self._set_status(message)
        messagebox.showerror("错误", message)


def main() -> None:
    configure_matplotlib_fonts()
    app = FftGuiApp()
    app.mainloop()
