from __future__ import annotations

from dataclasses import dataclass
import json
import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from dd_agent.domain.schemas import Chunk, SearchResult


@dataclass(slots=True)
class SearchIndexArtifacts:
    chunks_path: Path
    vectorizer_path: Path
    matrix_path: Path
    metadata_path: Path


class LocalKnowledgeBase:
    def __init__(self, *, vectorizer: TfidfVectorizer, matrix, chunks: list[Chunk]) -> None:
        self.vectorizer = vectorizer
        self.matrix = matrix
        self.chunks = chunks

    @classmethod
    def build(cls, chunks: list[Chunk]) -> "LocalKnowledgeBase":
        if not chunks:
            raise ValueError("Cannot build knowledge base with zero chunks")
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            min_df=1,
            lowercase=False,
        )
        matrix = vectorizer.fit_transform([chunk.text for chunk in chunks])
        return cls(vectorizer=vectorizer, matrix=matrix, chunks=chunks)

    def search(self, query: str, *, top_k: int = 5) -> list[SearchResult]:
        query = query.strip()
        if not query:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix).ravel()
        top_indices = scores.argsort()[::-1][:top_k]
        results: list[SearchResult] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = self.chunks[int(idx)]
            results.append(
                SearchResult(
                    chunk_id=chunk.chunk_id,
                    score=score,
                    document_name=chunk.document_name,
                    locator_type=chunk.locator_type,
                    locator_value=chunk.locator_value,
                    text=chunk.text,
                    metadata=chunk.metadata,
                )
            )
        return results

    def save(self, output_dir: str | Path) -> SearchIndexArtifacts:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        chunks_path = output_path / "chunks.jsonl"
        with chunks_path.open("w", encoding="utf-8") as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

        vectorizer_path = output_path / "vectorizer.pkl"
        with vectorizer_path.open("wb") as f:
            pickle.dump(self.vectorizer, f)

        matrix_path = output_path / "tfidf_matrix.pkl"
        with matrix_path.open("wb") as f:
            pickle.dump(self.matrix, f)

        metadata_path = output_path / "kb_metadata.json"
        document_profiles = {}
        for chunk in self.chunks:
            profile = document_profiles.setdefault(chunk.document_name, {
                "file_type": chunk.file_type,
                "document_role": chunk.metadata.get("document_role", "unknown"),
                "include_in_project_kb": chunk.metadata.get("include_in_project_kb", True),
            })
            profile.setdefault("file_type", chunk.file_type)
        metadata = {
            "chunk_count": len(self.chunks),
            "document_names": sorted({chunk.document_name for chunk in self.chunks}),
            "document_profiles": document_profiles,
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        return SearchIndexArtifacts(
            chunks_path=chunks_path,
            vectorizer_path=vectorizer_path,
            matrix_path=matrix_path,
            metadata_path=metadata_path,
        )

    @classmethod
    def load(cls, index_dir: str | Path) -> "LocalKnowledgeBase":
        index_path = Path(index_dir)
        chunks: list[Chunk] = []
        with (index_path / "chunks.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                payload = json.loads(line)
                chunks.append(Chunk(**payload))
        with (index_path / "vectorizer.pkl").open("rb") as f:
            vectorizer = pickle.load(f)
        with (index_path / "tfidf_matrix.pkl").open("rb") as f:
            matrix = pickle.load(f)
        return cls(vectorizer=vectorizer, matrix=matrix, chunks=chunks)
