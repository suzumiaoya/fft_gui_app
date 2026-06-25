from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd
from matplotlib import font_manager, rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from fft_gui_app.exceptions import ValidationError
from fft_gui_app.models import (
    CsvImportConfig,
    FilterConfig,
    PreprocessConfig,
    PreviewResult,
    SpectrumConfig,
    SpectrumResult,
)
from fft_gui_app.services.code_generator import CodeGenerator
from fft_gui_app.services.csv_loader import AnalysisFrame, CsvLoader
from fft_gui_app.services.fft_analyzer import FftAnalyzer
from fft_gui_app.services.filter_preview_service import FilterPreviewService


PLOT_MODE_LABELS = {"叠加对比": "overlay", "分别显示": "separate"}
MAGNITUDE_MODE_LABELS = {"线性幅值": "linear", "dB": "db"}
WINDOW_LABELS = {"Hann": "hann", "无窗": "none"}
METHOD_LABELS = {"FFT 幅度谱": "fft", "Welch PSD": "welch"}
WELCH_WINDOW_LABELS = {"Hann": "hann", "矩形窗": "boxcar"}
FILTER_KIND_LABELS = {
    "低通": "lowpass",
    "高通": "highpass",
    "带通": "bandpass",
    "带阻": "bandstop",
}
DETREND_LABELS = {"不处理": "none", "去直流": "constant", "去线性趋势": "linear"}


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

        self.title("CSV FFT 频谱与滤波预览工具")
        self.geometry("1500x900")
        self.minsize(1280, 800)

        self.csv_loader = CsvLoader()
        self.fft_analyzer = FftAnalyzer()
        self.filter_preview_service = FilterPreviewService(spectrum_analyzer=self.fft_analyzer)
        self.code_generator = CodeGenerator()

        self.current_csv_path: str | None = None
        self.preview_columns: list[str] = []
        self.analysis_frame: AnalysisFrame | None = None
        self.current_spectrum_result: SpectrumResult | None = None
        self.current_preview_result: PreviewResult | None = None

        self._init_variables()
        self._build_layout()
        self._set_status("请先导入 CSV 文件。")

    def _init_variables(self) -> None:
        self.time_column_var = tk.StringVar(value="")
        self.sample_rate_var = tk.StringVar(value="")

        self.plot_mode_var = tk.StringVar(value="叠加对比")
        self.magnitude_mode_var = tk.StringVar(value="线性幅值")
        self.window_var = tk.StringVar(value="Hann")
        self.method_var = tk.StringVar(value="FFT 幅度谱")

        self.filter_kind_var = tk.StringVar(value="低通")
        self.low_cutoff_var = tk.StringVar(value="")
        self.high_cutoff_var = tk.StringVar(value="")
        self.notch_var = tk.StringVar(value="")
        self.preview_signal_var = tk.StringVar(value="")

        self.advanced_visible_var = tk.BooleanVar(value=False)
        self.filter_order_var = tk.StringVar(value="4")
        self.notch_q_var = tk.StringVar(value="30")
        self.detrend_var = tk.StringVar(value="去直流")
        self.welch_window_var = tk.StringVar(value="Hann")
        self.welch_nperseg_var = tk.StringVar(value="")
        self.welch_noverlap_var = tk.StringVar(value="")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.control_frame = ctk.CTkScrollableFrame(self, width=460, corner_radius=0)
        self.control_frame.grid(row=0, column=0, sticky="nsew")
        self.control_frame.grid_columnconfigure(0, weight=1)

        self.visual_frame = ctk.CTkFrame(self, corner_radius=0)
        self.visual_frame.grid(row=0, column=1, sticky="nsew")
        self.visual_frame.grid_rowconfigure(1, weight=1)
        self.visual_frame.grid_columnconfigure(0, weight=1)

        self._build_control_panel()
        self._build_visual_panel()

    def _build_control_panel(self) -> None:
        row = 0

        title = ctk.CTkLabel(
            self.control_frame,
            text="FFT 频谱与滤波预览",
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
        self.file_label = ctk.CTkLabel(file_content, text="当前文件：未选择", justify="left", wraplength=390)
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

        tab_section, tab_content = self._section_frame("分析功能")
        tab_section.grid(row=row, column=0, padx=18, pady=10, sticky="ew")
        tab_content.grid_columnconfigure(0, weight=1)
        self.analysis_tabview = ctk.CTkTabview(tab_content)
        self.analysis_tabview.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        self.analysis_tabview.add("频谱分析")
        self.analysis_tabview.add("滤波预览")
        self._build_spectrum_controls(self.analysis_tabview.tab("频谱分析"))
        self._build_preview_controls(self.analysis_tabview.tab("滤波预览"))
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

    def _build_spectrum_controls(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(parent, text="频谱方法").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkLabel(parent, text="显示方式").grid(row=0, column=1, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkOptionMenu(parent, values=list(METHOD_LABELS.keys()), variable=self.method_var).grid(
            row=1, column=0, padx=12, pady=(0, 12), sticky="ew"
        )
        ctk.CTkOptionMenu(parent, values=list(PLOT_MODE_LABELS.keys()), variable=self.plot_mode_var).grid(
            row=1, column=1, padx=12, pady=(0, 12), sticky="ew"
        )

        ctk.CTkLabel(parent, text="幅值模式").grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkLabel(parent, text="窗口函数").grid(row=2, column=1, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkOptionMenu(parent, values=list(MAGNITUDE_MODE_LABELS.keys()), variable=self.magnitude_mode_var).grid(
            row=3, column=0, padx=12, pady=(0, 12), sticky="ew"
        )
        ctk.CTkOptionMenu(parent, values=list(WINDOW_LABELS.keys()), variable=self.window_var).grid(
            row=3, column=1, padx=12, pady=(0, 12), sticky="ew"
        )

        ctk.CTkButton(parent, text="生成频谱", command=self._on_generate_spectrum).grid(
            row=4, column=0, columnspan=2, padx=12, pady=(4, 12), sticky="ew"
        )

    def _build_preview_controls(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(parent, text="预览列").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        self.preview_signal_menu = ctk.CTkOptionMenu(parent, values=[""], variable=self.preview_signal_var)
        self.preview_signal_menu.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(parent, text="滤波类型").grid(row=0, column=1, padx=12, pady=(12, 4), sticky="w")
        self.filter_kind_menu = ctk.CTkOptionMenu(parent, values=list(FILTER_KIND_LABELS.keys()), variable=self.filter_kind_var)
        self.filter_kind_menu.grid(row=1, column=1, padx=12, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(parent, text="低截止频率 Hz").grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkLabel(parent, text="高截止频率 Hz").grid(row=2, column=1, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkEntry(parent, textvariable=self.low_cutoff_var).grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkEntry(parent, textvariable=self.high_cutoff_var).grid(row=3, column=1, padx=12, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(parent, text="陷波频率 Hz（逗号分隔）").grid(
            row=4, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w"
        )
        ctk.CTkEntry(parent, textvariable=self.notch_var).grid(
            row=5, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew"
        )

        self.advanced_toggle = ctk.CTkButton(
            parent,
            text="显示高级参数",
            command=self._toggle_advanced_options,
        )
        self.advanced_toggle.grid(row=6, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="ew")

        self.advanced_frame = ctk.CTkFrame(parent)
        self.advanced_frame.grid(row=7, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")
        self.advanced_frame.grid_columnconfigure((0, 1), weight=1)
        self._build_advanced_controls(self.advanced_frame)
        self.advanced_frame.grid_remove()

        ctk.CTkButton(parent, text="生成滤波预览", command=self._on_generate_preview).grid(
            row=8, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="ew"
        )
        ctk.CTkButton(parent, text="导出 C 代码", command=self._on_export_code).grid(
            row=9, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew"
        )

    def _build_advanced_controls(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text="滤波阶数").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkLabel(parent, text="陷波 Q").grid(row=0, column=1, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkEntry(parent, textvariable=self.filter_order_var).grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkEntry(parent, textvariable=self.notch_q_var).grid(row=1, column=1, padx=12, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(parent, text="预处理").grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkLabel(parent, text="Welch 窗").grid(row=2, column=1, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkOptionMenu(parent, values=list(DETREND_LABELS.keys()), variable=self.detrend_var).grid(
            row=3, column=0, padx=12, pady=(0, 12), sticky="ew"
        )
        ctk.CTkOptionMenu(parent, values=list(WELCH_WINDOW_LABELS.keys()), variable=self.welch_window_var).grid(
            row=3, column=1, padx=12, pady=(0, 12), sticky="ew"
        )

        ctk.CTkLabel(parent, text="Welch nperseg").grid(row=4, column=0, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkLabel(parent, text="Welch noverlap").grid(row=4, column=1, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkEntry(parent, textvariable=self.welch_nperseg_var).grid(row=5, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkEntry(parent, textvariable=self.welch_noverlap_var).grid(row=5, column=1, padx=12, pady=(0, 12), sticky="ew")

    def _build_visual_panel(self) -> None:
        header = ctk.CTkFrame(self.visual_frame, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(header, text="", anchor="w")
        self.status_label.grid(row=0, column=0, padx=16, pady=12, sticky="ew")

        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.visual_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        toolbar_frame = ctk.CTkFrame(self.visual_frame, corner_radius=0)
        toolbar_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(fill="x")

        self._render_placeholder_plot()

    def _section_frame(self, title: str) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        frame = ctk.CTkFrame(self.control_frame)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=12, pady=(10, 4), sticky="w"
        )
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.grid(row=1, column=0, sticky="ew")
        return frame, content

    def _toggle_advanced_options(self) -> None:
        if self.advanced_visible_var.get():
            self.advanced_frame.grid_remove()
            self.advanced_toggle.configure(text="显示高级参数")
            self.advanced_visible_var.set(False)
        else:
            self.advanced_frame.grid()
            self.advanced_toggle.configure(text="隐藏高级参数")
            self.advanced_visible_var.set(True)

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
        self.analysis_frame = None
        self.current_spectrum_result = None
        self.current_preview_result = None
        self.preview_columns = preview.columns

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

        preview_values = columns or [""]
        self.preview_signal_menu.configure(values=preview_values)
        self.preview_signal_var.set(preview_values[0] if preview_values else "")

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
            sample_rate = self.csv_loader.resolve_sample_rate(
                file_path=self.current_csv_path,
                time_column=selected,
                manual_sample_rate_hz=self._parse_optional_float(self.sample_rate_var.get(), "采样率"),
            )
        except ValidationError:
            self.sample_rate_hint.configure(text="时间列已选择；分析时会再次校验采样率。")
            return

        if sample_rate.inferred_sample_rate_hz is not None and not self.sample_rate_var.get().strip():
            self.sample_rate_var.set(f"{sample_rate.inferred_sample_rate_hz:.6f}")
        if sample_rate.inferred_sample_rate_hz is not None:
            self.sample_rate_hint.configure(text=f"自动推导采样率：{sample_rate.inferred_sample_rate_hz:.6f} Hz，可手动覆盖。")

    def _on_generate_spectrum(self) -> None:
        try:
            import_config = self._build_import_config()
            analysis = self.csv_loader.build_analysis_frame(import_config)
            spectrum_config = self._build_spectrum_config(sample_count=len(analysis.dataframe))
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
        self._render_spectrum_plot(spectrum_result)
        self._set_status(
            f"频谱生成完成：{len(import_config.signal_columns)} 个信号，"
            f"{analysis.sample_rate_hz:.3f} Hz，{spectrum_result.method.upper()}。"
        )

    def _on_generate_preview(self) -> None:
        try:
            import_config = self._build_import_config(require_signals=False)
            analysis = self.csv_loader.build_analysis_frame(
                CsvImportConfig(
                    file_path=import_config.file_path,
                    time_column=import_config.time_column,
                    signal_columns=[self._require_preview_signal()],
                    manual_sample_rate_hz=import_config.manual_sample_rate_hz,
                )
            )
            filter_config = self._build_filter_config(sample_rate_hz=analysis.sample_rate_hz)
            preprocess_config = self._build_preprocess_config()
            preview_result = self.filter_preview_service.preview(
                frame=analysis.dataframe,
                signal_column=self._require_preview_signal(),
                filter_config=filter_config,
                preprocess_config=preprocess_config,
            )
        except ValidationError as exc:
            self._show_error(str(exc))
            return

        self.analysis_frame = analysis
        self.current_preview_result = preview_result
        self._render_preview_plot(preview_result)
        self._set_status(
            f"滤波预览完成：{self._require_preview_signal()}，"
            f"{filter_config.filter_kind}，{preview_result.sample_count} 个样本。"
        )

    def _on_export_code(self) -> None:
        try:
            import_config = self._build_import_config(require_signals=False)
            sample_rate_resolution = self.csv_loader.resolve_sample_rate(
                file_path=import_config.file_path,
                time_column=import_config.time_column,
                manual_sample_rate_hz=import_config.manual_sample_rate_hz,
            )
            filter_config = self._build_filter_config(sample_rate_hz=sample_rate_resolution.sample_rate_hz)
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
            header_path, source_path = self.code_generator.render(filter_config, str(Path(path).with_suffix("")))
        except ValidationError as exc:
            self._show_error(str(exc))
            return

        self._set_status(f"已导出代码：{header_path.name} 和 {source_path.name}")
        messagebox.showinfo("导出成功", f"已生成：\n{header_path}\n{source_path}")

    def _build_import_config(self, require_signals: bool = True) -> CsvImportConfig:
        if not self.current_csv_path:
            raise ValidationError("请先导入 CSV 文件。")

        signal_columns = self._get_selected_signal_columns()
        if require_signals and not signal_columns:
            raise ValidationError("请至少选择一个信号列。")

        return CsvImportConfig(
            file_path=self.current_csv_path,
            time_column=self.time_column_var.get() or None,
            signal_columns=signal_columns if signal_columns else [self._require_preview_signal()],
            manual_sample_rate_hz=self._parse_optional_float(self.sample_rate_var.get(), "采样率"),
        )

    def _build_spectrum_config(self, sample_count: int) -> SpectrumConfig:
        method = METHOD_LABELS[self.method_var.get()]
        magnitude_mode = MAGNITUDE_MODE_LABELS[self.magnitude_mode_var.get()]
        if method == "welch":
            magnitude_mode = "linear"

        return SpectrumConfig(
            method=method,
            plot_mode=PLOT_MODE_LABELS[self.plot_mode_var.get()],
            magnitude_mode=magnitude_mode,
            window=WINDOW_LABELS[self.window_var.get()],
            welch_window=WELCH_WINDOW_LABELS[self.welch_window_var.get()],
            welch_nperseg=self._parse_optional_int(
                self.welch_nperseg_var.get(),
                "Welch nperseg",
                default=min(1024, sample_count),
            ),
            welch_noverlap=self._parse_optional_int(
                self.welch_noverlap_var.get(),
                "Welch noverlap",
                default=min(1024, sample_count) // 2,
            ),
        )

    def _build_preprocess_config(self) -> PreprocessConfig:
        return PreprocessConfig(detrend_mode=DETREND_LABELS[self.detrend_var.get()])

    def _build_filter_config(self, sample_rate_hz: float) -> FilterConfig:
        filter_kind = FILTER_KIND_LABELS[self.filter_kind_var.get()]
        low_cutoff = self._parse_optional_float(self.low_cutoff_var.get(), "低截止频率")
        high_cutoff = self._parse_optional_float(self.high_cutoff_var.get(), "高截止频率")

        if filter_kind in {"lowpass", "highpass"} and low_cutoff is None:
            raise ValidationError("低通和高通滤波必须填写低截止频率。")
        if filter_kind in {"bandpass", "bandstop"} and (low_cutoff is None or high_cutoff is None):
            raise ValidationError("带通和带阻滤波必须填写上下截止频率。")

        return FilterConfig(
            filter_kind=filter_kind,
            low_cutoff_hz=low_cutoff,
            high_cutoff_hz=high_cutoff,
            notch_freqs_hz=self._parse_notch_frequencies(self.notch_var.get()),
            notch_q=self._parse_required_float(self.notch_q_var.get(), "陷波 Q"),
            order=self._parse_required_int(self.filter_order_var.get(), "滤波阶数"),
            sample_rate_hz=sample_rate_hz,
        )

    def _get_selected_signal_columns(self) -> list[str]:
        return [self.signal_listbox.get(index) for index in self.signal_listbox.curselection()]

    def _require_preview_signal(self) -> str:
        value = self.preview_signal_var.get().strip()
        if not value:
            raise ValidationError("请选择一个预览列。")
        return value

    def _parse_optional_float(self, raw_value: str, field_name: str) -> float | None:
        if not raw_value.strip():
            return None
        try:
            return float(raw_value)
        except ValueError as exc:
            raise ValidationError(f"{field_name}必须是数字。") from exc

    def _parse_required_float(self, raw_value: str, field_name: str) -> float:
        value = self._parse_optional_float(raw_value, field_name)
        if value is None:
            raise ValidationError(f"{field_name}不能为空。")
        return value

    def _parse_optional_int(self, raw_value: str, field_name: str, default: int | None = None) -> int | None:
        if not raw_value.strip():
            return default
        try:
            return int(raw_value)
        except ValueError as exc:
            raise ValidationError(f"{field_name}必须是整数。") from exc

    def _parse_required_int(self, raw_value: str, field_name: str) -> int:
        value = self._parse_optional_int(raw_value, field_name)
        if value is None:
            raise ValidationError(f"{field_name}不能为空。")
        return value

    def _parse_notch_frequencies(self, raw_value: str) -> list[float]:
        if not raw_value.strip():
            return []
        values: list[float] = []
        for part in raw_value.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                values.append(float(part))
            except ValueError as exc:
                raise ValidationError("陷波频率必须是用逗号分隔的数字列表。") from exc
        return values

    def _render_placeholder_plot(self) -> None:
        self.figure.clear()
        axis = self.figure.add_subplot(111)
        axis.set_title("分析视图")
        axis.set_xlabel("横轴")
        axis.set_ylabel("纵轴")
        axis.text(0.5, 0.5, "导入 CSV 后选择功能并开始分析", ha="center", va="center", transform=axis.transAxes)
        axis.grid(True, alpha=0.25)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _render_spectrum_plot(self, result: SpectrumResult) -> None:
        self.figure.clear()

        ylabel = "PSD" if result.method == "welch" else ("幅值(dB)" if result.magnitude_mode == "db" else "幅值")
        if result.plot_mode == "overlay":
            axis = self.figure.add_subplot(111)
            for name, amplitudes in result.series_amplitudes_by_name.items():
                axis.plot(result.frequencies_hz, amplitudes, label=name, linewidth=1.2)
            axis.set_title("Welch PSD" if result.method == "welch" else "FFT 单边频谱")
            axis.set_xlabel("频率 (Hz)")
            axis.set_ylabel(ylabel)
            axis.legend(loc="upper right")
            axis.grid(True, alpha=0.25)
        else:
            axes = self.figure.subplots(
                nrows=len(result.series_amplitudes_by_name),
                ncols=1,
                sharex=True,
                squeeze=False,
            ).flatten()
            for axis, (name, amplitudes) in zip(axes, result.series_amplitudes_by_name.items()):
                axis.plot(result.frequencies_hz, amplitudes, label=name, linewidth=1.2)
                axis.set_ylabel(ylabel)
                axis.legend(loc="upper right")
                axis.grid(True, alpha=0.25)
            axes[-1].set_xlabel("频率 (Hz)")
            self.figure.suptitle("Welch PSD" if result.method == "welch" else "FFT 单边频谱")

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _render_preview_plot(self, result: PreviewResult) -> None:
        self.figure.clear()
        axes = self.figure.subplots(nrows=2, ncols=1, sharex=False, squeeze=False).flatten()

        axes[0].plot(result.time_axis_s, result.raw_signal, label="原始信号", linewidth=1.0)
        axes[0].plot(result.time_axis_s, result.filtered_signal, label="滤波后信号", linewidth=1.0)
        axes[0].set_title("时域对比")
        axes[0].set_xlabel("时间 (s)")
        axes[0].set_ylabel("幅值")
        axes[0].legend(loc="upper right")
        axes[0].grid(True, alpha=0.25)

        axes[1].plot(result.frequencies_hz, result.raw_spectrum, label="原始频谱", linewidth=1.0)
        axes[1].plot(result.frequencies_hz, result.filtered_spectrum, label="滤波后频谱", linewidth=1.0)
        axes[1].set_title("频域对比")
        axes[1].set_xlabel("频率 (Hz)")
        axes[1].set_ylabel(result.y_axis_unit)
        axes[1].legend(loc="upper right")
        axes[1].grid(True, alpha=0.25)

        self.figure.tight_layout()
        self.canvas.draw_idle()

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
