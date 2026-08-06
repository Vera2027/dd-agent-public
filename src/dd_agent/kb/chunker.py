from __future__ import annotations

import hashlib
from dataclasses import dataclass

from dd_agent.domain.schemas import Chunk, ParsedDocument, TextUnit


@dataclass(slots=True)
class ChunkingConfig:
    max_chars: int = 600
    overlap_chars: int = 120
    min_chunk_chars: int = 80


class TextChunker:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()
        if self.config.overlap_chars >= self.config.max_chars:
            raise ValueError("overlap_chars must be smaller than max_chars")

    def chunk_document(self, document: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        for unit_index, unit in enumerate(document.text_units):
            pieces = self._split_text(unit.text)
            for chunk_index, piece in enumerate(pieces):
                chunk_id = self._build_chunk_id(document=document, unit=unit, piece=piece, chunk_index=chunk_index)
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        document_name=document.document_name,
                        file_path=document.file_path,
                        file_type=document.file_type,
                        locator_type=unit.locator_type,
                        locator_value=unit.locator_value,
                        text=piece,
                        source_text_unit_index=unit_index,
                        chunk_index_within_unit=chunk_index,
                        metadata={
                            **document.metadata,
                            **unit.metadata,
                            "source_text_length": len(unit.text),
                        },
                    )
                )
        return chunks

    def chunk_documents(self, documents: list[ParsedDocument]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for document in documents:
            chunks.extend(self.chunk_document(document))
        return chunks

    def _split_text(self, text: str) -> list[str]:
        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if len(cleaned) <= self.config.max_chars:
            return [cleaned]

        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(start + self.config.max_chars, len(cleaned))
            if end < len(cleaned):
                break_at = cleaned.rfind("\n", start, end)
                if break_at == -1:
                    break_at = cleaned.rfind("。", start, end)
                if break_at == -1:
                    break_at = cleaned.rfind(" ", start, end)
                if break_at != -1 and break_at > start + self.config.min_chunk_chars:
                    end = break_at + 1
            piece = cleaned[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(cleaned):
                break
            start = max(0, end - self.config.overlap_chars)
        return chunks or [cleaned]

    def _build_chunk_id(self, *, document: ParsedDocument, unit: TextUnit, piece: str, chunk_index: int) -> str:
        digest = hashlib.sha1(
            f"{document.document_name}|{unit.locator_type}|{unit.locator_value}|{chunk_index}|{piece}".encode("utf-8")
        ).hexdigest()[:12]
        return f"{document.file_type}-{unit.locator_value}-{chunk_index}-{digest}"
