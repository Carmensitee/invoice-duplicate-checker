"""PDF 文本提取模块 —— 使用 pdfplumber 读取 PDF 中的全部文字。"""

import pdfplumber


class PDFReadError(Exception):
    """PDF 读取失败时抛出的异常。"""

    pass


def extract_text(filepath: str) -> str:
    """提取指定 PDF 文件的所有文字内容。

    Args:
        filepath: PDF 文件的绝对或相对路径。

    Returns:
        提取到的全部文字（多页时用换行拼接）。

    Raises:
        PDFReadError: 文件不存在、加密、损坏或无法读取任何文字时。
    """
    try:
        with pdfplumber.open(filepath) as pdf:
            pages_text: list[str] = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            if not pages_text:
                raise PDFReadError(f"文件中未提取到任何文字: {filepath}")
            return "\n".join(pages_text)
    except PDFReadError:
        raise
    except Exception as e:
        raise PDFReadError(f"读取 PDF 失败: {filepath}\n{_friendly_error(e)}") from e


def _friendly_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "password" in msg or "encrypted" in msg:
        return "文件已加密，无法读取。"
    if "not a pdf" in msg or "invalid" in msg or "corrupt" in msg:
        return "文件格式无效或已损坏。"
    return str(exc)
