"""发票号提取测试。"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from invoice_extractor import extract_invoice_number


def test_standard():
    r = extract_invoice_number("发票号码: 26312000000945374941")
    assert r.value == "26312000000945374941"
    assert r.status == "ok"


def test_short_label():
    r = extract_invoice_number("发票号：12345678")
    assert r.value == "12345678"
    assert r.status == "ok"


def test_spaced_digits():
    r = extract_invoice_number("发票号码: 2613 7000 0000 7762 8298")
    assert r.value == "26137000000077628298"
    assert r.status == "ok"


def test_fallback():
    r = extract_invoice_number("统一发票监制 26437000000016667619")
    assert r.value == "26437000000016667619"
    assert r.status == "ok"


def test_no_match():
    r = extract_invoice_number("这是一段没有任何发票号的文本")
    assert r.status == "missing"
    assert r.value == ""


def test_multiple_candidates():
    r = extract_invoice_number("发票号码: 12345678 发票号码: 87654321")
    assert r.status == "uncertain"
    assert r.value in ("12345678", "87654321")


def test_too_short():
    r = extract_invoice_number("发票号码: 1234567")
    assert r.status == "missing"


if __name__ == "__main__":
    test_standard()
    test_short_label()
    test_spaced_digits()
    test_fallback()
    test_no_match()
    test_multiple_candidates()
    test_too_short()
    print("All tests passed!")
