"""已报销发票数据库 —— JSON 文件持久化，key 为发票号。"""

import json
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.invoice_duplicate_db.json")


class InvoiceDB:
    def __init__(self) -> None:
        self._records: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                self._records = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._records = {}

    def _save(self) -> None:
        try:
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(self._records, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @property
    def numbers(self) -> set[str]:
        return set(self._records.keys())

    @property
    def records(self) -> dict[str, dict]:
        return dict(self._records)

    def add(self, number: str, filename: str) -> None:
        self._records[number] = {
            "filename": filename,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save()

    def remove(self, number: str) -> None:
        if number in self._records:
            del self._records[number]
            self._save()

    def contains(self, number: str) -> bool:
        return number in self._records

    def __len__(self) -> int:
        return len(self._records)
