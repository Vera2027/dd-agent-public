from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dd_agent.kb.index import LocalKnowledgeBase
from dd_agent.reporting.field_evidence_builder import FieldEvidencePackBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build field-level evidence packs from a local KB')
    parser.add_argument('index_dir', help='Directory produced by build_kb.py')
    parser.add_argument('--output-dir', default='artifacts/field_evidence', help='Directory to store outputs')
    parser.add_argument('--top-k-per-query', type=int, default=8)
    parser.add_argument('--final-top-k', type=int, default=5)
    return parser


def render_markdown(payload: dict) -> str:
    lines: list[str] = []
    lines.append('# 字段级 Evidence Pack 草稿\n')
    lines.append(f"- module_count: {payload['metadata'].get('module_count', 0)}")
    lines.append(f"- chunk_count: {payload['metadata'].get('chunk_count', 0)}")
    reference_docs = payload['metadata'].get('reference_like_documents', [])
    lines.append(f"- reference_like_documents: {', '.join(reference_docs) if reference_docs else '无'}\n")
    for module in payload['modules']:
        lines.append(f"## {module['module_name']}\n")
        for field in module['field_packs']:
            lines.append(f"### {field['field_name']}（{field['field_type']}）")
            lines.append(f"- provisional_status: {field['provisional_status'] or 'None'}")
            lines.append(f"- retrieval_summary: {field['retrieval_summary']}")
            lines.append(f"- query_groups: {'；'.join(field['query_groups'])}")
            if field['gap_reasons']:
                lines.append('- gap_reasons:')
                for gap in field['gap_reasons']:
                    lines.append(f'  - {gap}')
            lines.append('- evidence:')
            if field['evidence']:
                for item in field['evidence']:
                    notes = ' / '.join(item['metadata'].get('retrieval_notes', []))
                    lines.append(
                        f"  - {item['document_name']}，{item['locator_type']}={item['locator_value']}，score={item['score']}，"
                        f"raw={item['metadata'].get('raw_score')}，queries={','.join(item['metadata'].get('matched_queries', []))}"
                        + (f"，notes={notes}" if notes else '')
                    )
                    lines.append(f"    {item['text'][:180].replace(chr(10), ' ')}")
            else:
                lines.append('  - 无')
            lines.append('')
    return '\n'.join(lines) + '\n'


def main() -> None:
    args = build_parser().parse_args()
    kb = LocalKnowledgeBase.load(Path(args.index_dir))
    builder = FieldEvidencePackBuilder(kb)
    result = builder.build_all(top_k_per_query=args.top_k_per_query, final_top_k=args.final_top_k)
    payload = result.to_dict()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'field_evidence_packs.json'
    md_path = output_dir / 'field_evidence_packs.md'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    md_path.write_text(render_markdown(payload), encoding='utf-8')

    summary = {
        'module_count': len(payload['modules']),
        'json_path': str(json_path),
        'markdown_path': str(md_path),
        'reference_like_documents': payload['metadata'].get('reference_like_documents', []),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
