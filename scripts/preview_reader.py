from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dd_agent.ingest.readers.factory import ReaderFactory, collect_supported_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview parsed materials for DD Agent V1")
    parser.add_argument("target", help="Path to one file or a directory")
    parser.add_argument("--show-units", type=int, default=3, help="How many text units to preview per document")
    parser.add_argument(
        "--show-raw-chars",
        type=int,
        default=0,
        help="Show the first N characters of raw_text. Set 0 to hide.",
    )
    parser.add_argument(
        "--export-dir",
        type=str,
        default="",
        help="Optional directory to export parsed JSON and raw_text preview files",
    )
    return parser


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = build_parser()
    args = parser.parse_args()

    target = Path(args.target)
    files = collect_supported_files(target)
    if not files:
        print("No supported files found (.pdf / .docx / .txt)")
        sys.exit(0)

    factory = ReaderFactory()
    export_dir = Path(args.export_dir) if args.export_dir else None
    if export_dir:
        export_dir.mkdir(parents=True, exist_ok=True)

    for file_path in files:
        doc = factory.read_one(file_path)
        print("=" * 80)
        print(f"Document: {doc.document_name}")
        print(json.dumps(doc.metadata, ensure_ascii=False, indent=2))
        print(f"unit_count: {doc.unit_count}")
        print("preview_units:")
        for unit in doc.text_units[: max(0, args.show_units)]:
            snippet = unit.text.replace("\n", " ")[:220]
            print(f"  - ({unit.locator_type}={unit.locator_value}) {snippet}")
        if args.show_raw_chars > 0:
            raw_preview = doc.raw_text[: args.show_raw_chars]
            print("raw_text_preview:")
            print(raw_preview)
        if export_dir:
            base_name = Path(doc.document_name).stem
            (export_dir / f"{base_name}.parsed.json").write_text(
                json.dumps(doc.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (export_dir / f"{base_name}.raw.txt").write_text(doc.raw_text, encoding="utf-8")


if __name__ == "__main__":
    main()
