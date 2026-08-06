from __future__ import annotations

from dataclasses import dataclass
import re

from dd_agent.domain.schemas import ParsedDocument


@dataclass(slots=True)
class DocumentClassification:
    document_role: str
    include_in_project_kb: bool
    reasons: list[str]

    def to_metadata(self) -> dict:
        return {
            'document_role': self.document_role,
            'include_in_project_kb': self.include_in_project_kb,
            'classification_reasons': self.reasons,
        }


SYSTEM_NAME_PATTERNS = [
    '尽调 Agent 系统',
    '本地知识库尽调 Agent 系统',
    '字段映射表',
    '可信输出约束',
    '模块提示词',
    '非目标列表',
]
TEMPLATE_NAME_PATTERNS = [
    '结构化模板',
    '填写方式',
]
REPORT_NAME_PATTERNS = [
    '尽调报告',
    'structured_results',
    'analysis_field_results',
    'fact_field_results',
]
PROJECT_NAME_HINTS = [
    'BP', 'Pitch', 'Deck', '公司介绍', '产品', '白皮书', '创始人', '简历', '访谈', '行业分析', '补充说明',
]

SYSTEM_CONTENT_PATTERNS = [
    '仅基于用户上传材料',
    '系统内部必须为每个字段保留统一的结构化 schema',
    '可信输出约束',
    '模块提示词',
]
TEMPLATE_CONTENT_PATTERNS = [
    '一、报告总表头',
    '模块目标',
    '字段内容',
    '字段明细',
    '证据出处',
    '信息缺失项',
    '初步判断',
]
REPORT_CONTENT_PATTERNS = [
    '总体初筛结论',
    '总体初筛结论说明',
    '项目基础信息',
    '团队判断',
    '产品与技术',
    '市场分析',
    '商业模式',
    '竞争格局',
    '融资与资本信息',
    '风险识别',
    '追问清单',
]


def classify_document(document: ParsedDocument) -> DocumentClassification:
    name = document.document_name
    text = document.raw_text[:6000] if document.raw_text else ''
    reasons: list[str] = []

    def _contains_any(patterns: list[str], haystack: str) -> list[str]:
        return [p for p in patterns if p and p in haystack]

    name_hits_system = _contains_any(SYSTEM_NAME_PATTERNS, name)
    name_hits_template = _contains_any(TEMPLATE_NAME_PATTERNS, name)
    name_hits_report = _contains_any(REPORT_NAME_PATTERNS, name)
    name_hits_project = _contains_any(PROJECT_NAME_HINTS, name)

    text_hits_system = _contains_any(SYSTEM_CONTENT_PATTERNS, text)
    text_hits_template = _contains_any(TEMPLATE_CONTENT_PATTERNS, text)
    report_heading_hits = len(_contains_any(REPORT_CONTENT_PATTERNS, text))

    if name_hits_system or len(text_hits_system) >= 2:
        reasons.extend(name_hits_system or text_hits_system[:2])
        return DocumentClassification('system_definition', False, reasons)

    if name_hits_template or len(text_hits_template) >= 4:
        reasons.extend(name_hits_template or text_hits_template[:4])
        return DocumentClassification('reference_template', False, reasons)

    # Generated/derived reports should not feed back into the same project KB by default.
    if (name_hits_report and '结构化模板' not in name) or report_heading_hits >= 6:
        reasons.extend(name_hits_report or ['detected_report_heading_cluster'])
        return DocumentClassification('generated_output', False, reasons)

    if name_hits_project:
        reasons.extend(name_hits_project[:3])
        return DocumentClassification('project_material', True, reasons)

    # Heuristic fallback: docs with strong schema density are reference-like; otherwise keep them.
    schema_markers = len(re.findall(r'field_|allowed_status|value_source|validation_rule|证据出处|信息缺失项', text))
    if schema_markers >= 8:
        reasons.append('schema_marker_density')
        return DocumentClassification('reference_template', False, reasons)

    return DocumentClassification('project_material', True, ['default_project_material'])
