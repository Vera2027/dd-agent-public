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
from dd_agent.reporting.fact_processor import FactFieldProcessor
from dd_agent.reporting.analysis_generator import AnalysisFieldGenerator, render_analysis_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate analysis field results from local KB')
    parser.add_argument('index_dir', help='Directory produced by build_kb.py')
    parser.add_argument('--output-dir', default='artifacts/analysis_results', help='Directory to store outputs')
    parser.add_argument('--top-k-per-query', type=int, default=8)
    parser.add_argument('--final-top-k', type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    kb = LocalKnowledgeBase.load(Path(args.index_dir))
    evidence_builder = FieldEvidencePackBuilder(kb)
    evidence_result = evidence_builder.build_all(top_k_per_query=args.top_k_per_query, final_top_k=args.final_top_k)
    fact_result = FactFieldProcessor().process(evidence_result)
    analysis_result = AnalysisFieldGenerator().generate(evidence_result, fact_result)
    payload = analysis_result.to_dict()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'analysis_field_results.json'
    md_path = output_dir / 'analysis_field_results.md'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    md_path.write_text(render_analysis_markdown(payload), encoding='utf-8')

    summary = {
        'module_count': len(payload['modules']),
        'analysis_field_count': payload['metadata'].get('analysis_field_count', 0),
        'json_path': str(json_path),
        'markdown_path': str(md_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
