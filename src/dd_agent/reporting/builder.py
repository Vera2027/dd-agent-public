from __future__ import annotations

from dd_agent.kb.index import LocalKnowledgeBase
from dd_agent.reporting.models import FieldCandidate, ModuleEvidenceBundle, StructuredProjectResult, ModuleSpec
from dd_agent.reporting.module_specs import MODULE_SPECS
from dd_agent.reporting.retriever import ModuleEvidenceRetriever


class StructuredResultBuilder:
    def __init__(self, kb: LocalKnowledgeBase) -> None:
        self.kb = kb
        self.retriever = ModuleEvidenceRetriever(kb)

    def build(self, *, top_k_per_query: int = 5, final_top_k: int = 8) -> StructuredProjectResult:
        modules: list[ModuleEvidenceBundle] = []
        for spec in MODULE_SPECS:
            evidence = self.retriever.retrieve(spec, top_k_per_query=top_k_per_query, final_top_k=final_top_k)
            field_candidates = self._build_field_candidates(spec)
            info_gaps = self._build_info_gaps(spec, field_candidates)
            modules.append(
                ModuleEvidenceBundle(
                    module_name=spec.module_name,
                    search_queries=spec.search_queries,
                    evidence=evidence,
                    field_candidates=field_candidates,
                    core_conclusion=self._build_core_conclusion(spec, evidence),
                    evidence_basis=self._build_evidence_basis(evidence),
                    info_gaps=info_gaps,
                    preliminary_judgment=self._build_preliminary_judgment(evidence),
                )
            )

        overall_conclusion = self._build_overall_conclusion(modules)
        overall_reason = self._build_overall_reason(modules)
        return StructuredProjectResult(
            modules=modules,
            overall_screening_conclusion=overall_conclusion,
            overall_screening_reason=overall_reason,
            metadata={
                'module_count': len(modules),
                'document_names': sorted({chunk.document_name for chunk in self.kb.chunks}),
                'chunk_count': len(self.kb.chunks),
                'builder_mode': 'evidence_first_mvp',
            },
        )

    def _build_field_candidates(self, spec: ModuleSpec) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        for field in spec.fields:
            results = self.kb.search(field.field_name, top_k=3)
            if field.field_type == 'fact':
                candidates.append(self._build_fact_candidate(field.field_name, field.field_key, results))
            else:
                candidates.append(self._build_analysis_candidate(field.field_name, field.field_key, results))
        return candidates

    def _build_fact_candidate(self, field_name: str, field_key: str, results) -> FieldCandidate:
        if not results:
            return FieldCandidate(field_name, field_key, 'fact', '材料未体现', '材料未体现', [])
        top = results[0]
        if top.score >= 0.10:
            value = self._trim_candidate(top.text)
            status = 'candidate_extracted'
        elif top.score >= 0.03:
            value = self._trim_candidate(top.text)
            status = '材料提及但信息不足'
        else:
            value = '材料未体现'
            status = '材料未体现'
        return FieldCandidate(field_name, field_key, 'fact', status, value, [self._to_evidence_item(top, field_name)])

    def _build_analysis_candidate(self, field_name: str, field_key: str, results) -> FieldCandidate:
        if not results:
            return FieldCandidate(field_name, field_key, 'analysis', '无法判断', '无法判断', [])
        top = results[0]
        if top.score >= 0.05:
            value = f'已检索到与“{field_name}”相关证据，需结合多条证据综合判断。'
            status = 'candidate_analysis'
        else:
            value = '无法判断'
            status = '无法判断'
        return FieldCandidate(field_name, field_key, 'analysis', status, value, [self._to_evidence_item(top, field_name)])

    def _build_info_gaps(self, spec: ModuleSpec, field_candidates: list[FieldCandidate]) -> list[str]:
        gaps = list(spec.gap_hints)
        for candidate in field_candidates:
            if candidate.status in {'材料未体现', '材料提及但信息不足', '无法判断'}:
                if candidate.field_type == 'fact':
                    gaps.append(f'{candidate.field_name}：{candidate.status}')
                else:
                    gaps.append(f'{candidate.field_name}：证据不足，当前{candidate.status}')
        # dedupe keep order
        seen: set[str] = set()
        deduped: list[str] = []
        for item in gaps:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped or ['当前模块未识别出新增关键缺口']

    def _build_core_conclusion(self, spec: ModuleSpec, evidence) -> str:
        if not evidence:
            return '无法判断'
        doc_names = sorted({item.document_name for item in evidence})
        return f'已检索到与“{spec.module_name}”相关的 {len(evidence)} 条候选证据，覆盖 {len(doc_names)} 份材料，可进入下一步模型综合生成。'

    def _build_evidence_basis(self, evidence) -> str:
        if not evidence:
            return '当前模块未检索到直接证据。'
        doc_names = sorted({item.document_name for item in evidence})
        locators = [f"{item.document_name}:{item.locator_type}={item.locator_value}" for item in evidence[:5]]
        return f"当前模块证据主要来自：{'；'.join(doc_names)}。优先定位：{'；'.join(locators)}。"

    def _build_preliminary_judgment(self, evidence) -> str:
        if not evidence:
            return '无法判断'
        if len(evidence) >= 5:
            return '当前模块已形成较完整的候选证据包，可进入模型综合判断阶段。'
        return '当前模块已有初步候选证据，但证据覆盖仍有限，建议在综合生成前继续补充检索。'

    def _build_overall_conclusion(self, modules: list[ModuleEvidenceBundle]) -> str:
        no_evidence_count = sum(1 for module in modules if not module.evidence)
        if no_evidence_count >= 4:
            return '信息不足，建议补充材料后再判断'
        return '建议进入下一轮沟通'

    def _build_overall_reason(self, modules: list[ModuleEvidenceBundle]) -> str:
        covered = [m.module_name for m in modules if m.evidence]
        missing = [m.module_name for m in modules if not m.evidence]
        parts = []
        if covered:
            parts.append(f"当前已形成候选证据的模块包括：{'、'.join(covered)}。")
        if missing:
            parts.append(f"仍缺直接证据的模块包括：{'、'.join(missing)}。")
        parts.append('该结果为证据优先的结构化草稿，后续应接入生成层对字段值进行严格综合判断。')
        return ''.join(parts)

    def _to_evidence_item(self, result, field_name: str):
        from dd_agent.reporting.models import EvidenceItem

        return EvidenceItem(
            chunk_id=result.chunk_id,
            score=float(result.score),
            document_name=result.document_name,
            locator_type=result.locator_type,
            locator_value=int(result.locator_value),
            text=result.text,
            support=f'支持字段“{field_name}”的候选证据',
            metadata=result.metadata,
        )

    def _trim_candidate(self, text: str, limit: int = 180) -> str:
        cleaned = ' '.join(text.split())
        return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + '...'
