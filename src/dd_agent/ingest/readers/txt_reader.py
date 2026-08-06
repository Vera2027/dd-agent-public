from __future__ import annotations

from pathlib import Path

from dd_agent.domain.schemas import FileInfo, ParsedDocument, TextUnit
from dd_agent.ingest.readers.base import BaseReader


class TxtReader(BaseReader):
    supported_suffixes = (".txt",)
    _encodings = ("utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1")

    def read(self, path: Path) -> ParsedDocument:
        file_info = FileInfo.from_path(path)
        raw_text, encoding_used = self._read_text(path)

        text_units: list[TextUnit] = []
        for line_no, line in enumerate(raw_text.splitlines(), start=1):
            if not line.strip():
                continue
            text_units.append(
                TextUnit(
                    document_name=file_info.document_name,
                    file_path=str(file_info.path),
                    file_type=file_info.file_type,
                    locator_type="line",
                    locator_value=line_no,
                    text=line.strip(),
                )
            )

        metadata = self._build_base_metadata(file_info)
        metadata.update(
            {
                "encoding_used": encoding_used,
                "raw_line_count": len(raw_text.splitlines()),
                "non_empty_line_count": len(text_units),
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

    def _read_text(self, path: Path) -> tuple[str, str]:
        last_error: Exception | None = None
        for encoding in self._encodings:
            try:
                return path.read_text(encoding=encoding), encoding
            except UnicodeDecodeError as exc:
                last_error = exc
        raise UnicodeDecodeError(
            "unknown",
            b"",
            0,
            1,
            f"Unable to decode TXT file: {path}. Last error: {last_error}",
        )
