from __future__ import annotations

from pathlib import Path

from dd_agent.domain.schemas import ParsedDocument
from dd_agent.ingest.readers.base import BaseReader
from dd_agent.ingest.readers.docx_reader import DocxReader
from dd_agent.ingest.readers.pdf_reader import PdfReaderAdapter
from dd_agent.ingest.readers.txt_reader import TxtReader


class ReaderFactory:
    def __init__(self) -> None:
        self._readers: list[BaseReader] = [
            PdfReaderAdapter(),
            DocxReader(),
            TxtReader(),
        ]

    def get_reader(self, path: Path) -> BaseReader:
        for reader in self._readers:
            if reader.can_read(path):
                return reader
        raise ValueError(f"Unsupported file type: {path.suffix} ({path})")

    def read_one(self, path: str | Path) -> ParsedDocument:
        file_path = Path(path)
        return self.get_reader(file_path).read(file_path)

    def read_many(self, paths: list[str | Path]) -> list[ParsedDocument]:
        return [self.read_one(path) for path in paths]


def collect_supported_files(root: str | Path, *, exclude_globs: list[str] | None = None) -> list[Path]:
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {root_path}")

    exclude_globs = exclude_globs or []

    def _is_excluded(path: Path) -> bool:
        normalized = path.as_posix()
        return any(path.match(pattern) or normalized.endswith(pattern) for pattern in exclude_globs)

    if root_path.is_file():
        if _is_excluded(root_path):
            return []
        return [root_path]

    supported = {".pdf", ".docx", ".txt"}
    return sorted(
        [p for p in root_path.rglob("*") if p.is_file() and p.suffix.lower() in supported and not _is_excluded(p)],
        key=lambda p: str(p).lower(),
    )
