from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dd_agent.ingest.document_classifier import classify_document
from dd_agent.ingest.readers.factory import ReaderFactory, collect_supported_files
from dd_agent.kb.chunker import ChunkingConfig, TextChunker
from dd_agent.kb.index import LocalKnowledgeBase


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local TF-IDF knowledge base from materials")
    parser.add_argument("target", help="Path to one file or a directory")
    parser.add_argument("--output-dir", default="artifacts/kb", help="Directory to store KB artifacts")
    parser.add_argument("--max-chars", type=int, default=600)
    parser.add_argument("--overlap-chars", type=int, default=120)
    parser.add_argument("--min-chunk-chars", type=int, default=80)
    parser.add_argument("--fail-on-error", action="store_true", help="Stop immediately if any file cannot be parsed")
    parser.add_argument("--exclude", action="append", default=[], help="Glob/pattern to exclude, repeatable")
    parser.add_argument("--include-non-project-docs", action="store_true", help="Do not filter out templates/system docs/history outputs")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    files = collect_supported_files(Path(args.target), exclude_globs=args.exclude)
    factory = ReaderFactory()

    documents = []
    failed_files: list[dict[str, str]] = []
    excluded_files: list[dict[str, object]] = []
    classification_counts: dict[str, int] = {}
    for path in files:
        try:
            document = factory.read_one(path)
            classification = classify_document(document)
            document.metadata.update(classification.to_metadata())
            classification_counts[classification.document_role] = classification_counts.get(classification.document_role, 0) + 1
            if classification.include_in_project_kb or args.include_non_project_docs:
                documents.append(document)
            else:
                excluded_files.append({
                    "path": str(path),
                    "document_name": document.document_name,
                    "document_role": classification.document_role,
                    "reasons": classification.reasons,
                })
        except Exception as exc:
            failure = {
                "path": str(path),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            failed_files.append(failure)
            if args.fail_on_error:
                raise

    if not documents:
        raise RuntimeError("No project-material documents were successfully included; knowledge base was not built")

    chunker = TextChunker(
        ChunkingConfig(
            max_chars=args.max_chars,
            overlap_chars=args.overlap_chars,
            min_chunk_chars=args.min_chunk_chars,
        )
    )
    chunks = chunker.chunk_documents(documents)
    kb = LocalKnowledgeBase.build(chunks)
    artifacts = kb.save(args.output_dir)

    failures_path = None
    if failed_files:
        failures_path = Path(args.output_dir) / "failed_files.json"
        failures_path.parent.mkdir(parents=True, exist_ok=True)
        failures_path.write_text(json.dumps(failed_files, ensure_ascii=False, indent=2), encoding="utf-8")

    excluded_path = None
    if excluded_files:
        excluded_path = Path(args.output_dir) / "excluded_files.json"
        excluded_path.parent.mkdir(parents=True, exist_ok=True)
        excluded_path.write_text(json.dumps(excluded_files, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "document_count": len(documents),
        "excluded_file_count": len(excluded_files),
        "failed_file_count": len(failed_files),
        "chunk_count": len(chunks),
        "classification_counts": classification_counts,
        "output_dir": str(Path(args.output_dir).resolve()),
        "artifacts": {
            "chunks_path": str(artifacts.chunks_path),
            "vectorizer_path": str(artifacts.vectorizer_path),
            "matrix_path": str(artifacts.matrix_path),
            "metadata_path": str(artifacts.metadata_path),
            "failed_files_path": str(failures_path) if failures_path else None,
            "excluded_files_path": str(excluded_path) if excluded_path else None,
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
