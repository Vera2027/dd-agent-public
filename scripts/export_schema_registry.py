from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dd_agent.reporting.schema_registry import build_schema_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Export internal field schema registry')
    parser.add_argument('--output-dir', default='artifacts/schema_registry', help='Directory to store schema registry outputs')
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = build_schema_registry()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'schema_registry.json'
    md_path = output_dir / 'schema_registry.md'
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Internal Field Schema Registry\n']
    for row in rows:
        lines.append(f"## {row['module_name']} / {row['field_name']}")
        for key in ['field_key', 'field_type', 'field_role', 'value_source', 'value_kind', 'required', 'allowed_status', 'priority_sources', 'evidence_required', 'validation_rule']:
            lines.append(f"- {key}: {row[key]}")
        lines.append('')
    md_path.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'field_count': len(rows), 'json_path': str(json_path), 'markdown_path': str(md_path)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
