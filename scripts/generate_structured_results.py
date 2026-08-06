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
from dd_agent.reporting.analysis_generator import AnalysisFieldGenerator, render_structured_report_markdown
from dd_agent.reporting.fact_processor import FactFieldProcessor
from dd_agent.reporting.field_evidence_builder import FieldEvidencePackBuilder
from dd_agent.reporting.validator import StructuredReportValidator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate structured due-diligence report from local KB')
    parser.add_argument('index_dir', help='Directory produced by build_kb.py')
    parser.add_argument('--output-dir', default='artifacts/report_draft', help='Directory to store outputs')
    parser.add_argument('--top-k-per-query', type=int, default=8)
    parser.add_argument('--final-top-k', type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    kb = LocalKnowledgeBase.load(Path(args.index_dir))

    evidence_result = FieldEvidencePackBuilder(kb).build_all(
        top_k_per_query=args.top_k_per_query,
        final_top_k=args.final_top_k,
    )
    fact_result = FactFieldProcessor().process(evidence_result)
    generator = AnalysisFieldGenerator()
    analysis_result = generator.generate(evidence_result, fact_result)
    report = generator.build_structured_report(
        evidence_result=evidence_result,
        fact_result=fact_result,
        analysis_result=analysis_result,
        document_names=sorted({chunk.document_name for chunk in kb.chunks}),
    )
    payload = report.to_dict()
    validation = StructuredReportValidator().validate(
        fact_result=fact_result,
        analysis_result=analysis_result,
        report=report,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'structured_results.json'
    md_path = output_dir / 'structured_results.md'
    validation_path = output_dir / 'validation_results.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    md_path.write_text(render_structured_report_markdown(payload), encoding='utf-8')
    validation_path.write_text(json.dumps(validation.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    summary = {
        'module_count': len(payload['modules']),
        'overall_screening_conclusion': payload['overall_screening_conclusion'],
        'validation_passed': validation.passed,
        'json_path': str(json_path),
        'markdown_path': str(md_path),
        'validation_path': str(validation_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
