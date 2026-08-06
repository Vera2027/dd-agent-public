from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from dd_agent.domain.schemas import FileInfo, ParsedDocument


class BaseReader(ABC):
    supported_suffixes: tuple[str, ...] = ()

    def can_read(self, path: Path) -> bool:
        return path.suffix.lower() in self.supported_suffixes

    @abstractmethod
    def read(self, path: Path) -> ParsedDocument:
        raise NotImplementedError

    def _build_base_metadata(self, file_info: FileInfo) -> dict:
        return {
            "document_name": file_info.document_name,
            "file_path": str(file_info.path),
            "file_type": file_info.file_type,
            "size_bytes": file_info.size_bytes,
            "sha256": file_info.sha256,
        }
