"""发票号提取模块 —— 从发票文本中用正则提取发票号码。"""

import re
from dataclasses import dataclass


@dataclass
class ExtractResult:
    value: str
    status: str  # "ok" / "uncertain" / "missing"


# 发票号码：后跟数字串（传统纸质发票 8 位，电子发票可到 20 位），允许数字间有空格
_INVOICE_RE = re.compile(
    r"发票(?:号|号码)[：:\s]*(\d[\d\s]{6,}\d)"
)

# 兜底：统一发票监制 格式的发票号码（标签与数字被 PDF 布局拆散）
_INVOICE_FALLBACK_RE = re.compile(
    r"制\s*(\d[\d\s]{6,}\d)"
)


def extract_invoice_number(text: str) -> ExtractResult:
    candidates = _find_all(_INVOICE_RE, text)
    cleaned: list[str] = []
    for c in candidates:
        digits = re.sub(r"\s+", "", c)
        if len(digits) >= 8 and digits.isdigit():
            cleaned.append(digits)

    if not cleaned:
        fallback = _find_all(_INVOICE_FALLBACK_RE, text)
        for c in fallback:
            digits = re.sub(r"\s+", "", c)
            if len(digits) >= 8 and digits.isdigit():
                cleaned.append(digits)

    return _decide(cleaned)


def _find_all(pattern: re.Pattern, text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for m in pattern.finditer(text):
        val = m.group(1).strip()
        if val and val not in seen:
            seen.add(val)
            result.append(val)
    return result


def _decide(candidates: list[str]) -> ExtractResult:
    if not candidates:
        return ExtractResult(value="", status="missing")
    if len(candidates) == 1:
        return ExtractResult(value=candidates[0], status="ok")
    return ExtractResult(value=candidates[0], status="uncertain")
