from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal
import hashlib

LocatorType = Literal["page", "paragraph", "line"]
FileType = Literal["pdf", "docx", "txt"]


@dataclass(slots=True)
class TextUnit:
    document_name: str
    file_path: str
    file_type: FileType
    locator_type: LocatorType
    locator_value: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ParsedDocument:
    document_name: str
    file_path: str
    file_type: FileType
    raw_text: str
    text_units: list[TextUnit] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def unit_count(self) -> int:
        return len(self.text_units)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["unit_count"] = self.unit_count
        return payload


@dataclass(slots=True)
class FileInfo:
    path: Path
    document_name: str
    file_type: FileType
    size_bytes: int
    sha256: str

    @classmethod
    def from_path(cls, path: Path) -> "FileInfo":
        suffix = path.suffix.lower().lstrip(".")
        if suffix not in {"pdf", "docx", "txt"}:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        return cls(
            path=path,
            document_name=path.name,
            file_type=suffix,  # type: ignore[assignment]
            size_bytes=path.stat().st_size,
            sha256=_sha256(path),
        )


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    document_name: str
    file_path: str
    file_type: FileType
    locator_type: LocatorType
    locator_value: int
    text: str
    source_text_unit_index: int
    chunk_index_within_unit: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SearchResult:
    chunk_id: str
    score: float
    document_name: str
    locator_type: LocatorType
    locator_value: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
