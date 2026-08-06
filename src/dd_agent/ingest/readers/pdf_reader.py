from __future__ import annotations

from pathlib import Path
import re

import pdfplumber
from pypdf import PdfReader

from dd_agent.domain.schemas import FileInfo, ParsedDocument, TextUnit
from dd_agent.ingest.readers.base import BaseReader


class PdfReaderAdapter(BaseReader):
    supported_suffixes = (".pdf",)

    def read(self, path: Path) -> ParsedDocument:
        file_info = FileInfo.from_path(path)
        pypdf_reader = PdfReader(str(path))

        text_units: list[TextUnit] = []
        page_texts: list[str] = []
        empty_pages: list[int] = []
        suspicious_pages: list[int] = []

        with pdfplumber.open(str(path)) as plumber_doc:
            page_count = len(plumber_doc.pages)
            for page_index in range(page_count):
                plumber_page = plumber_doc.pages[page_index]
                pypdf_page = pypdf_reader.pages[page_index]
                cleaned, backend = _extract_best_page_text(plumber_page, pypdf_page)
                if not cleaned:
                    empty_pages.append(page_index + 1)
                    continue
                if _looks_suspicious(cleaned):
                    suspicious_pages.append(page_index + 1)
                page_texts.append(cleaned)
                text_units.append(
                    TextUnit(
                        document_name=file_info.document_name,
                        file_path=str(file_info.path),
                        file_type=file_info.file_type,
                        locator_type="page",
                        locator_value=page_index + 1,
                        text=cleaned,
                        metadata={
                            "extraction_backend": backend,
                            "char_count": len(cleaned),
                            "line_count": cleaned.count("\n") + 1,
                        },
                    )
                )

        raw_text = "\n\n".join(page_texts)
        metadata = self._build_base_metadata(file_info)
        metadata.update(
            {
                "page_count": len(pypdf_reader.pages),
                "non_empty_page_count": len(text_units),
                "empty_page_numbers": empty_pages,
                "suspicious_page_numbers": suspicious_pages,
                "extraction_warning": _build_extraction_warning(
                    page_count=len(pypdf_reader.pages),
                    non_empty_pages=len(text_units),
                    suspicious_pages=suspicious_pages,
                ),
            }
        )

        return ParsedDocument(
            document_name=file_info.document_name,
            file_path=str(file_info.path),
            file_type=file_info.file_type,
            raw_text=raw_text,
            text_units=text_units,
            metadata=metadata,
        )


def _extract_best_page_text(plumber_page: pdfplumber.page.Page, pypdf_page) -> tuple[str, str]:
    candidates: list[tuple[str, str]] = []

    try:
        text = plumber_page.extract_text(layout=False, x_tolerance=2, y_tolerance=2) or ""
        candidates.append((_normalize_pdf_text(text), "pdfplumber_plain"))
    except Exception:
        pass

    try:
        text = plumber_page.extract_text(layout=True, x_tolerance=2, y_tolerance=2) or ""
        candidates.append((_normalize_pdf_text(text), "pdfplumber_layout"))
    except Exception:
        pass

    try:
        text = pypdf_page.extract_text() or ""
        candidates.append((_normalize_pdf_text(text), "pypdf"))
    except Exception:
        pass

    if not candidates:
        return "", "none"

    ranked = sorted(candidates, key=lambda item: _score_candidate(item[0]), reverse=True)
    best_text, best_backend = ranked[0]
    return best_text, best_backend


def _normalize_pdf_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def _score_candidate(text: str) -> tuple[int, int, int, int]:
    if not text:
        return (0, 0, 0, 0)
    char_count = len(text)
    line_count = text.count("\n") + 1
    cjk_or_alpha = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", text))
    digit_only_penalty = 0 if not re.fullmatch(r"[\d\W_]+", text) else -100
    return (cjk_or_alpha + digit_only_penalty, char_count, line_count, -text.count("  "))


def _looks_suspicious(text: str) -> bool:
    if len(text) <= 2:
        return True
    alpha_or_cjk = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", text))
    return alpha_or_cjk < max(3, len(text) * 0.08)


def _build_extraction_warning(*, page_count: int, non_empty_pages: int, suspicious_pages: list[int]) -> str | None:
    if non_empty_pages == 0:
        return "PDF may be image-based or contain non-extractable text. OCR is not supported in V1."
    if suspicious_pages:
        return (
            "Some PDF pages were extracted with low confidence or poor reading order. "
            f"Check pages: {suspicious_pages}. Complex layouts exported from slides may need manual review."
        )
    if non_empty_pages < page_count:
        return "Some PDF pages returned empty text. Verify whether those pages are image-based or heavily graphical."
    return None
