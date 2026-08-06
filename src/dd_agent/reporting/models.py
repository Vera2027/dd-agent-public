from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Literal

ValueSource = Literal['extracted', 'generated', 'system']
FieldRole = Literal['normal_field', 'evidence_display', 'evidence_reasoning', 'gap_summary']

FieldType = Literal['fact', 'analysis']
CandidateStatus = Literal[
    'candidate_extracted',
    'candidate_analysis',
    '材料未体现',
    '材料提及但信息不足',
    '无法判断',
    '需外部核验',
]
ProvisionalFieldStatus = Literal['材料未体现', '材料提及但信息不足', '无法判断', '需外部核验']


@dataclass(slots=True)
class FieldSpec:
    field_name: str
    field_key: str
    field_type: FieldType
    query_groups: list[str] = field(default_factory=list)
    priority_sources: list[str] = field(default_factory=list)
    allowed_status: list[str] = field(default_factory=list)
    evidence_limit: int = 5
    field_role: FieldRole = 'normal_field'
    value_source: ValueSource = 'generated'
    value_kind: str = 'string'
    required: bool = True
    evidence_required: bool = True
    validation_rule: str = ''


@dataclass(slots=True)
class ModuleSpec:
    module_name: str
    search_queries: list[str]
    fields: list[FieldSpec]
    gap_hints: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvidenceItem:
    chunk_id: str
    score: float
    document_name: str
    locator_type: str
    locator_value: int
    text: str
    support: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FieldCandidate:
    field_name: str
    field_key: str
    field_type: FieldType
    status: CandidateStatus
    candidate_value: str
    evidence: list[EvidenceItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['evidence'] = [item.to_dict() for item in self.evidence]
        return payload


@dataclass(slots=True)
class ModuleEvidenceBundle:
    module_name: str
    search_queries: list[str]
    evidence: list[EvidenceItem]
    field_candidates: list[FieldCandidate]
    core_conclusion: str
    evidence_basis: str
    info_gaps: list[str]
    preliminary_judgment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'module_name': self.module_name,
            'search_queries': self.search_queries,
            'evidence': [item.to_dict() for item in self.evidence],
            'field_candidates': [item.to_dict() for item in self.field_candidates],
            'core_conclusion': self.core_conclusion,
            'evidence_basis': self.evidence_basis,
            'info_gaps': self.info_gaps,
            'preliminary_judgment': self.preliminary_judgment,
        }


@dataclass(slots=True)
class StructuredProjectResult:
    modules: list[ModuleEvidenceBundle]
    overall_screening_conclusion: str
    overall_screening_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'metadata': self.metadata,
            'overall_screening_conclusion': self.overall_screening_conclusion,
            'overall_screening_reason': self.overall_screening_reason,
            'modules': [module.to_dict() for module in self.modules],
        }


@dataclass(slots=True)
class FieldEvidencePack:
    field_name: str
    field_key: str
    field_type: FieldType
    query_groups: list[str]
    priority_sources: list[str]
    evidence: list[EvidenceItem]
    provisional_status: ProvisionalFieldStatus | None
    retrieval_summary: str
    gap_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            'field_name': self.field_name,
            'field_key': self.field_key,
            'field_type': self.field_type,
            'query_groups': self.query_groups,
            'priority_sources': self.priority_sources,
            'evidence': [item.to_dict() for item in self.evidence],
            'provisional_status': self.provisional_status,
            'retrieval_summary': self.retrieval_summary,
            'gap_reasons': self.gap_reasons,
        }


@dataclass(slots=True)
class ModuleFieldEvidenceBundle:
    module_name: str
    field_packs: list[FieldEvidencePack]
    module_gap_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            'module_name': self.module_name,
            'field_packs': [pack.to_dict() for pack in self.field_packs],
            'module_gap_hints': self.module_gap_hints,
        }


@dataclass(slots=True)
class FieldEvidenceBuildResult:
    modules: list[ModuleFieldEvidenceBundle]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'metadata': self.metadata,
            'modules': [module.to_dict() for module in self.modules],
        }
