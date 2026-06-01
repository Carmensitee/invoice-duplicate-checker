"""GUI 模块 —— tkinter 双表格布局，集成发票重复检测流程。"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pdf_reader import extract_text, PDFReadError
from invoice_extractor import extract_invoice_number
from db import InvoiceDB
from version import __version__

STATUS_ICONS = {"ok": "✓", "duplicate": "✗", "missing": "?"}
STATUS_COLORS = {"ok": "#2e7d32", "duplicate": "#c0392b", "missing": "#e67e22"}


class InvoiceDupChecker:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"发票重复检测工具 v{__version__} - by Carmen")
        self.root.geometry("1000x580")
        self.root.minsize(800, 400)

        self.db = InvoiceDB()
        self._check_rows: list[dict] = []

        self._build_ui()
        self._refresh_db_table()

    # ==================================================================
    # 界面构建
    # ==================================================================

    def _build_ui(self) -> None:
        # 顶部标题栏
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        # 左右主区域
        main = ttk.Frame(self.root, padding=(8, 0, 8, 0))
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        self._build_left(main)
        self._build_right(main)

        # 底部状态栏
        self._build_bottom()

    def _build_left(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="已报销发票库", padding=4)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="添加 PDF", command=self._add_to_db).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="删除选中", command=self._remove_from_db).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="删除全部", command=self._clear_db).pack(side=tk.LEFT)
        self._db_count_label = ttk.Label(btn_frame, text="")
        self._db_count_label.pack(side=tk.RIGHT)

        columns = ("number", "filename")
        self.db_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        self.db_tree.heading("number", text="发票号码")
        self.db_tree.heading("filename", text="来源文件")
        self.db_tree.column("number", width=180)
        self.db_tree.column("filename", width=150)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.db_tree.yview)
        self.db_tree.configure(yscrollcommand=scrollbar.set)
        self.db_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.db_tree.tag_configure("duplicate", background="#fdd", foreground="#c0392b")
        self._duplicate_numbers: set[str] = set()

    def _build_right(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="待检查发票", padding=4)
        frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="选择 PDF 文件", command=self._select_files).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="开始比对", command=self._check).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="使用说明", command=self._show_help).pack(side=tk.RIGHT)

        columns = ("number", "filename", "status")
        self.check_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        self.check_tree.heading("number", text="发票号码")
        self.check_tree.heading("filename", text="文件名")
        self.check_tree.heading("status", text="状态")
        self.check_tree.column("number", width=180)
        self.check_tree.column("filename", width=130)
        self.check_tree.column("status", width=70)

        for key, color in STATUS_COLORS.items():
            self.check_tree.tag_configure(key, foreground=color)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.check_tree.yview)
        self.check_tree.configure(yscrollcommand=scrollbar.set)
        self.check_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_bottom(self) -> None:
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill=tk.X)

        self.result_label = ttk.Label(frame, text=f"已报销库共 {len(self.db)} 条记录", foreground="gray")
        self.result_label.pack(side=tk.LEFT)

        self._version_label = ttk.Label(frame, text=f"v{__version__}")
        self._version_label.pack(side=tk.RIGHT)

    # ==================================================================
    # 已报销库操作
    # ==================================================================

    def _add_to_db(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择已报销发票 PDF",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*")],
        )
        if not paths:
            return

        added = 0
        skipped = 0
        failed = 0

        for p in paths:
            try:
                text = extract_text(p)
                result = extract_invoice_number(text)
            except PDFReadError:
                failed += 1
                continue

            if result.status == "missing" or not result.value:
                failed += 1
                continue

            if self.db.contains(result.value):
                skipped += 1
                continue

            self.db.add(result.value, os.path.basename(p))
            added += 1

        self._refresh_db_table()

        msg = f"添加 {added} 条"
        if skipped:
            msg += f"，跳过 {skipped} 条（已存在）"
        if failed:
            msg += f"，{failed} 个文件未能提取发票号"
        messagebox.showinfo("添加结果", msg)

    def _remove_from_db(self) -> None:
        sel = self.db_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在左侧表格中选择要删除的发票号。")
            return

        for iid in sel:
            values = self.db_tree.item(iid, "values")
            number = values[0]
            self.db.remove(number)

        self._refresh_db_table()

    def _clear_db(self) -> None:
        if len(self.db) == 0:
            messagebox.showinfo("提示", "已报销库为空。")
            return
        if not messagebox.askyesno("确认", f"确定要删除全部 {len(self.db)} 条记录吗？此操作不可撤销。"):
            return
        for number in list(self.db.records.keys()):
            self.db.remove(number)
        self._duplicate_numbers.clear()
        self._refresh_db_table()

    def _refresh_db_table(self) -> None:
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        for number, info in self.db.records.items():
            tags = ("duplicate",) if number in self._duplicate_numbers else ()
            self.db_tree.insert("", tk.END, values=(number, info.get("filename", "")), tags=tags)
        self._db_count_label.config(text=f"共 {len(self.db)} 条")
        self.result_label.config(text=f"已报销库共 {len(self.db)} 条记录")

    # ==================================================================
    # 待检查发票
    # ==================================================================

    def _select_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择待检查发票 PDF",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*")],
        )
        if not paths:
            return

        self._duplicate_numbers.clear()
        self._refresh_db_table()
        self._check_rows.clear()
        for p in paths:
            row = {"filepath": p, "filename": os.path.basename(p), "number": "", "status": "missing"}
            self._check_rows.append(row)

        self._extract_check_numbers()
        self._refresh_check_table()

    def _extract_check_numbers(self) -> None:
        for row in self._check_rows:
            try:
                text = extract_text(row["filepath"])
                result = extract_invoice_number(text)
                row["number"] = result.value
                row["status"] = result.status
            except PDFReadError:
                row["number"] = ""
                row["status"] = "missing"

    def _refresh_check_table(self) -> None:
        for item in self.check_tree.get_children():
            self.check_tree.delete(item)
        for row in self._check_rows:
            num = row["number"] or "—"
            icon = STATUS_ICONS.get(row["status"], "?")
            if row["status"] == "duplicate":
                icon = STATUS_ICONS["duplicate"]
            elif row["status"] == "ok":
                icon = STATUS_ICONS["ok"]
            tags = (row["status"],)
            self.check_tree.insert("", tk.END, values=(num, row["filename"], icon), tags=tags)

    # ==================================================================
    # 比对
    # ==================================================================

    def _check(self) -> None:
        if not self._check_rows:
            messagebox.showinfo("提示", "请先选择待检查的 PDF 文件。")
            return

        duplicate_count = 0
        normal_count = 0
        missing_count = 0
        self._duplicate_numbers.clear()

        for row in self._check_rows:
            if not row["number"]:
                row["status"] = "missing"
                missing_count += 1
            elif self.db.contains(row["number"]):
                row["status"] = "duplicate"
                self._duplicate_numbers.add(row["number"])
                duplicate_count += 1
            else:
                row["status"] = "ok"
                normal_count += 1

        self._refresh_db_table()
        self._refresh_check_table()

        parts = [f"共 {len(self._check_rows)} 张"]
        if normal_count:
            parts.append(f"{normal_count} 张正常")
        if duplicate_count:
            parts.append(f"{duplicate_count} 张重复")
        if missing_count:
            parts.append(f"{missing_count} 张未识别")
        self.result_label.config(text="比对结果：" + "，".join(parts), foreground="#c0392b" if duplicate_count else "#2e7d32")

    # ==================================================================
    # 使用说明
    # ==================================================================

    def _show_help(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("使用说明")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        text = tk.Text(dialog, wrap=tk.WORD, padx=16, pady=12, font=("", 10))
        text.pack(fill=tk.BOTH, expand=True)

        instructions = (
            "【发票重复检测工具 — 使用说明】\n\n"
            "用途：检查新发票是否与已报销发票重复，防止重复报销。\n\n"
            "步骤：\n"
            "  1. 点击左侧「添加 PDF」，导入已报销的发票 PDF，\n"
            "     工具会自动提取发票号并保存到数据库。\n\n"
            "  2. 点击右侧「选择 PDF 文件」，导入待检查的新发票。\n\n"
            "  3. 点击「开始比对」，工具会将右侧每张发票的发票号\n"
            "     与左侧已报销库逐一比对。\n\n"
            "  4. 查看结果：\n"
            "     ✓ 绿色 = 未重复，可正常报销\n"
            "     ✗ 红色 = 已报销，重复！\n"
            "     ? 橙色 = 未能提取发票号，需手动核对\n\n"
            "  5. 左侧选中发票号可删除（从已报销库中移除）。\n\n"
            "注意：\n"
            "  • 已报销库数据自动保存，下次打开程序无需重新导入。\n"
            "  • 发票号是唯一标识，确保 PDF 中发票号清晰可读。\n"
        )
        text.insert("1.0", instructions)
        text.config(state=tk.DISABLED)

        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=(0, 12))
