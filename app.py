"""应用入口 —— 实例化 GUI 并启动 tkinter 主循环。"""

import tkinter as tk

from gui import InvoiceDupChecker


def main() -> None:
    root = tk.Tk()
    app = InvoiceDupChecker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
