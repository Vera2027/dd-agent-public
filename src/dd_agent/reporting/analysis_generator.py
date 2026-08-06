from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import re
from typing import Literal

from dd_agent.reporting.fact_processor import FactFieldResult, FactProcessingResult
from dd_agent.reporting.models import EvidenceItem, FieldEvidenceBuildResult, FieldEvidencePack
from dd_agent.reporting.module_specs import MODULE_SPEC_MAP, MODULE_SPECS

AnalysisFinalStatus = Literal['generated', '无法判断']
OverallConclusion = Literal['建议进入下一轮沟通', '信息不足，建议补充材料后再判断', '存在明显风险，谨慎推进']


@dataclass(slots=True)
class AnalysisFieldResult:
    field_name: str
    field_key: str
    final_status: AnalysisFinalStatus
    final_value: str | list[str]
    selected_evidence: list[EvidenceItem] = field(default_factory=list)
    gap_reasons: list[str] = field(default_factory=list)
    generation_summary: str = ''

    def to_dict(self) -> dict:
        return {
            'field_name': self.field_name,
            'field_key': self.field_key,
            'final_status': self.final_status,
            'final_value': self.final_value,
            'selected_evidence': [item.to_dict() for item in self.selected_evidence],
            'gap_reasons': self.gap_reasons,
            'generation_summary': self.generation_summary,
        }


@dataclass(slots=True)
class ModuleAnalysisResult:
    module_name: str
    field_results: list[AnalysisFieldResult]
    core_conclusion: str
    evidence_basis: str
    info_gaps: list[str]
    preliminary_judgment: str

    def to_dict(self) -> dict:
        return {
            'module_name': self.module_name,
            'field_results': [item.to_dict() for item in self.field_results],
            'core_conclusion': self.core_conclusion,
            'evidence_basis': self.evidence_basis,
            'info_gaps': self.info_gaps,
            'preliminary_judgment': self.preliminary_judgment,
        }


@dataclass(slots=True)
class AnalysisGenerationResult:
    modules: list[ModuleAnalysisResult]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'metadata': self.metadata,
            'modules': [module.to_dict() for module in self.modules],
        }


@dataclass(slots=True)
class StructuredFieldOutput:
    field_name: str
    value: str | list[str]

    def to_dict(self) -> dict:
        return {'field_name': self.field_name, 'value': self.value}


@dataclass(slots=True)
class StructuredModuleOutput:
    module_name: str
    core_conclusion: str
    field_results: list[StructuredFieldOutput]
    evidence: list[EvidenceItem]
    evidence_basis: str
    info_gaps: list[str]
    preliminary_judgment: str

    def to_dict(self) -> dict:
        return {
            'module_name': self.module_name,
            'core_conclusion': self.core_conclusion,
            'field_results': [item.to_dict() for item in self.field_results],
            'evidence': [item.to_dict() for item in self.evidence],
            'evidence_basis': self.evidence_basis,
            'info_gaps': self.info_gaps,
            'preliminary_judgment': self.preliminary_judgment,
        }


@dataclass(slots=True)
class StructuredReportResult:
    project_name: str
    report_generated_at: str
    input_materials: list[str]
    analysis_boundary: str
    overall_screening_conclusion: OverallConclusion
    overall_screening_reason: str
    modules: list[StructuredModuleOutput]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'metadata': {
                **self.metadata,
                'project_name': self.project_name,
                'report_generated_at': self.report_generated_at,
                'input_materials': self.input_materials,
                'analysis_boundary': self.analysis_boundary,
            },
            'overall_screening_conclusion': self.overall_screening_conclusion,
            'overall_screening_reason': self.overall_screening_reason,
            'modules': [module.to_dict() for module in self.modules],
        }


class AnalysisFieldGenerator:
    def __init__(self) -> None:
        self._field_generators = {
            'team_capability_fit': self._gen_team_capability_fit,
            'org_gap_filling_status': self._gen_org_gap_filling_status,
            'team_risk': self._gen_team_risk,
            'technical_barrier': self._gen_technical_barrier,
            'product_maturity': self._gen_product_maturity,
            'substitutability': self._gen_substitutability,
            'demand_authenticity': self._gen_demand_authenticity,
            'market_size': self._gen_market_size,
            'market_drivers': self._gen_market_drivers,
            'market_barriers': self._gen_market_barriers,
            'market_timing': self._gen_market_timing,
            'ticket_size_and_collection': self._gen_ticket_size_and_collection,
            'delivery_and_scaling_logic': self._gen_delivery_and_scaling_logic,
            'margin_and_cost_structure': self._gen_margin_and_cost_structure,
            'business_model_risk': self._gen_business_model_risk,
            'competitor_types': self._gen_competitor_types,
            'differentiation': self._gen_differentiation,
            'competitive_advantages': self._gen_competitive_advantages,
            'competitive_disadvantages': self._gen_competitive_disadvantages,
            'entry_barriers': self._gen_entry_barriers,
            'investor_structure': self._gen_investor_structure,
            'valuation_clues': self._gen_valuation_clues,
            'capital_value_add': self._gen_capital_value_add,
            'capital_risk': self._gen_capital_risk,
            'policy_risk': self._gen_policy_risk,
            'technical_risk': self._gen_technical_risk,
            'commercialization_risk': self._gen_commercialization_risk,
            'organization_risk': self._gen_organization_risk,
            'market_risk': self._gen_market_risk,
            'financing_risk': self._gen_financing_risk,
            'info_authenticity_risk': self._gen_info_authenticity_risk,
            'risk_level': self._gen_risk_level,
            'followup_team': self._gen_followup_team,
            'followup_product_tech': self._gen_followup_product_tech,
            'followup_market': self._gen_followup_market,
            'followup_business_model': self._gen_followup_business_model,
            'followup_competition': self._gen_followup_competition,
            'followup_financing_operation': self._gen_followup_financing_operation,
        }

    def generate(self, evidence_result: FieldEvidenceBuildResult, fact_result: FactProcessingResult) -> AnalysisGenerationResult:
        fact_by_module = {module.module_name: {field.field_key: field for field in module.field_results} for module in fact_result.modules}
        modules: list[ModuleAnalysisResult] = []
        for module_bundle in evidence_result.modules:
            facts = fact_by_module.get(module_bundle.module_name, {})
            field_results: list[AnalysisFieldResult] = []
            for pack in module_bundle.field_packs:
                if pack.field_type != 'analysis':
                    continue
                generator = self._field_generators.get(pack.field_key, self._gen_generic)
                result = generator(module_bundle.module_name, pack, facts)
                field_results.append(result)
            info_gaps = self._build_module_gaps(module_bundle.module_name, facts, field_results)
            core = self._build_module_core_conclusion(module_bundle.module_name, facts, field_results, info_gaps)
            basis = self._build_module_evidence_basis(module_bundle.module_name, facts, field_results)
            preliminary = self._build_module_preliminary_judgment(module_bundle.module_name, facts, field_results, info_gaps)
            modules.append(ModuleAnalysisResult(
                module_name=module_bundle.module_name,
                field_results=field_results,
                core_conclusion=core,
                evidence_basis=basis,
                info_gaps=info_gaps,
                preliminary_judgment=preliminary,
            ))
        return AnalysisGenerationResult(
            modules=modules,
            metadata={
                'module_count': len(modules),
                'analysis_field_count': sum(len(module.field_results) for module in modules),
                'generator_mode': 'analysis_field_generator_v1',
            },
        )

    def build_structured_report(
        self,
        *,
        evidence_result: FieldEvidenceBuildResult,
        fact_result: FactProcessingResult,
        analysis_result: AnalysisGenerationResult,
        document_names: list[str] | None = None,
    ) -> StructuredReportResult:
        fact_by_module = {module.module_name: {field.field_key: field for field in module.field_results} for module in fact_result.modules}
        analysis_by_module = {module.module_name: {field.field_key: field for field in module.field_results} for module in analysis_result.modules}
        analysis_module_meta = {module.module_name: module for module in analysis_result.modules}
        modules: list[StructuredModuleOutput] = []

        for spec in MODULE_SPECS:
            fact_lookup = fact_by_module.get(spec.module_name, {})
            analysis_lookup = analysis_by_module.get(spec.module_name, {})
            module_meta = analysis_module_meta.get(spec.module_name)
            field_outputs: list[StructuredFieldOutput] = []
            evidence = self._collect_module_evidence(fact_lookup, analysis_lookup)
            for field in spec.fields:
                sanitized_fact_value = None
                if field.field_type == 'fact':
                    result = fact_lookup.get(field.field_key)
                    raw_fact_value = result.final_value if result else None
                    if field.field_key == 'founders':
                        sanitized_fact_value = self._sanitize_people_list(raw_fact_value)
                    elif field.field_key == 'core_team_members':
                        sanitized_fact_value = self._sanitize_team_members(raw_fact_value)
                    else:
                        sanitized_fact_value = None
                    value = result.final_value if result else '材料未体现'
                else:
                    result = analysis_lookup.get(field.field_key)
                    value = result.final_value if result else '无法判断'
                rendered_value = sanitized_fact_value or value
                if field.field_key in {'founders', 'core_team_members'} and not sanitized_fact_value and field.field_type == 'fact':
                    rendered_value = '材料提及但信息不足'
                field_outputs.append(StructuredFieldOutput(field_name=field.field_name, value=rendered_value))
            modules.append(StructuredModuleOutput(
                module_name=spec.module_name,
                core_conclusion=module_meta.core_conclusion if module_meta else '无法判断',
                field_results=field_outputs,
                evidence=evidence,
                evidence_basis=module_meta.evidence_basis if module_meta else '未检索到直接证据',
                info_gaps=module_meta.info_gaps if module_meta else list(spec.gap_hints),
                preliminary_judgment=module_meta.preliminary_judgment if module_meta else '无法判断',
            ))

        input_materials = document_names or sorted({name for name in evidence_result.metadata.get('document_names', [])})
        project_name = self._pick_project_name(fact_result, input_materials)
        overall_conclusion, overall_reason = self._build_overall_conclusion(fact_result, analysis_result)
        report_generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        analysis_boundary = (
            '本报告用于项目初筛与投前判断辅助，不构成最终投资决策依据。'
            '报告仅基于本次上传材料生成，不调用外部公开来源；结论受材料完整性、时效性与真实性影响。'
        )
        return StructuredReportResult(
            project_name=project_name,
            report_generated_at=report_generated_at,
            input_materials=input_materials,
            analysis_boundary=analysis_boundary,
            overall_screening_conclusion=overall_conclusion,
            overall_screening_reason=overall_reason,
            modules=modules,
            metadata={
                'builder_mode': 'structured_report_v2',
                'module_count': len(modules),
            },
        )

    # ---------- generic helpers ----------
    def _usable_evidence(self, pack: FieldEvidencePack, min_score: float = 0.10) -> list[EvidenceItem]:
        usable: list[EvidenceItem] = []
        for item in pack.evidence:
            notes = item.metadata.get('retrieval_notes', [])
            if any('模板' in note or '字段标签' in note for note in notes):
                continue
            if item.score < min_score:
                continue
            usable.append(item)
        return usable

    def _fact(self, facts: dict[str, FactFieldResult], field_key: str) -> FactFieldResult | None:
        return facts.get(field_key)

    def _fact_value(self, facts: dict[str, FactFieldResult], field_key: str) -> str | None:
        fact = facts.get(field_key)
        if not fact:
            return None
        if fact.final_status == 'extracted':
            value = fact.normalized_value or fact.final_value
            if field_key == 'founders':
                return self._sanitize_people_list(value)
            if field_key == 'core_team_members':
                return self._sanitize_team_members(value)
            return value
        return None

    def _sanitize_people_list(self, value: str | None) -> str | None:
        if not value:
            return value
        tokens = re.split(r'[；;，,、\s]+', value)
        cleaned = [token for token in tokens if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', token or '')]
        return '；'.join(dict.fromkeys(cleaned)) if cleaned else None

    def _sanitize_team_members(self, value: str | None) -> str | None:
        if not value:
            return value
        matches = re.findall(r'((?:CEO|CTO|COO|CFO|CMO)(?:/[A-Za-z]+)?(?:\s+Co-founder)?\s+[\u4e00-\u9fff]{2,4})(?=[；;，,、]|$)', value)
        cleaned = list(dict.fromkeys(match.strip() for match in matches))
        return '；'.join(cleaned) if cleaned else None

    def _clean_material_stem(self, name: str) -> str:
        stem = re.sub(r'\.(pdf|docx|txt)$', '', name, flags=re.I)
        stem = re.sub(r'[_-]?ver[0-9.]+$', '', stem, flags=re.I)
        stem = re.sub(r'[_-]?v[0-9.]+$', '', stem, flags=re.I)
        stem = re.sub(r'[_-]?\d{6,8}$', '', stem)
        stem = re.sub(r'Business\s*Plan.*$', '', stem, flags=re.I)
        stem = re.sub(r'BP.*$', '', stem, flags=re.I)
        stem = re.sub(r'[（(].*?[)）]', '', stem)
        return stem.strip(' _-')

    def _fact_missing(self, facts: dict[str, FactFieldResult], field_key: str) -> bool:
        fact = facts.get(field_key)
        return not fact or fact.final_status != 'extracted'

    def _has_text(self, evidence: list[EvidenceItem], keywords: list[str]) -> bool:
        return any(keyword in item.text for item in evidence for keyword in keywords)

    def _collect_module_evidence(self, fact_lookup: dict[str, FactFieldResult], analysis_lookup: dict[str, AnalysisFieldResult]) -> list[EvidenceItem]:
        gathered: dict[str, EvidenceItem] = {}
        for result in fact_lookup.values():
            for item in result.selected_evidence[:2]:
                gathered.setdefault(item.chunk_id, item)
        for result in analysis_lookup.values():
            for item in result.selected_evidence[:2]:
                gathered.setdefault(item.chunk_id, item)
        return sorted(gathered.values(), key=lambda item: item.score, reverse=True)[:8]

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = value.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result

    def _join_values(self, values: list[str], limit: int = 3) -> str:
        return '、'.join(values[:limit])

    def _unknown(self, field_name: str, gaps: list[str]) -> AnalysisFieldResult:
        return AnalysisFieldResult(
            field_name=field_name,
            field_key='',
            final_status='无法判断',
            final_value='无法判断',
            selected_evidence=[],
            gap_reasons=self._dedupe(gaps),
            generation_summary=f'字段“{field_name}”证据不足，按 analysis 规则输出“无法判断”。',
        )

    def _pack_unknown(self, pack: FieldEvidencePack, gaps: list[str]) -> AnalysisFieldResult:
        return AnalysisFieldResult(
            field_name=pack.field_name,
            field_key=pack.field_key,
            final_status='无法判断',
            final_value='无法判断',
            selected_evidence=self._usable_evidence(pack)[:2],
            gap_reasons=self._dedupe(gaps),
            generation_summary=f'字段“{pack.field_name}”证据不足，按 analysis 规则输出“无法判断”。',
        )

    def _make_result(self, pack: FieldEvidencePack, value: str | list[str], evidence: list[EvidenceItem], gaps: list[str], summary: str) -> AnalysisFieldResult:
        return AnalysisFieldResult(
            field_name=pack.field_name,
            field_key=pack.field_key,
            final_status='generated',
            final_value=value,
            selected_evidence=evidence[:3],
            gap_reasons=self._dedupe(gaps),
            generation_summary=summary,
        )

    # ---------- field generators ----------
    def _gen_generic(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        gaps = list(pack.gap_reasons)
        if len(usable) < 2:
            gaps.append(f'字段“{pack.field_name}”可用于综合判断的独立证据不足 2 条')
            return self._pack_unknown(pack, gaps)
        docs = sorted({item.document_name for item in usable})
        value = f'材料已出现与“{pack.field_name}”相关的多条业务证据，当前可形成初步判断；但仍需结合更多量化或客户侧材料继续验证。'
        summary = f'字段“{pack.field_name}”使用 {len(usable)} 条候选证据生成通用分析结果。'
        if len(docs) == 1:
            gaps.append('当前分析主要来自单一材料来源，稳健性一般')
        return self._make_result(pack, value, usable, gaps, summary)

    def _gen_team_capability_fit(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        roles = self._fact_value(facts, 'core_team_members') or ''
        founders = self._fact_value(facts, 'founders') or ''
        background = self._fact_value(facts, 'founder_background') or ''
        prior = self._fact_value(facts, 'founder_prior_experience') or ''
        text = '\n'.join(item.text for item in (usable or pack.evidence))
        gaps = list(pack.gap_reasons)
        has_core_roles = ('CEO' in roles and 'CTO' in roles) or ('CEO' in text and 'CTO' in text) or (founders and any(role in roles + text for role in ['CEO', 'CTO', 'COO']))
        has_tech_profile = any(token in (background + prior + text) for token in ['博士', '副教授', '研究员', '毕业于', '师从', '研究方向'])
        if has_core_roles or has_tech_profile:
            value = '当前材料已呈现 CEO/CTO/COO 等核心角色及技术履历线索，说明技术研发和产品实现能力具备一定基础；但销售、交付、运营等商业化角色披露不足，能力闭环仍未完全证实。'
            if 'COO' not in roles and '销售' not in roles and '运营' not in roles:
                gaps.append('商业化角色与交付角色在当前材料中不清晰')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于团队角色、团队页证据与履历线索生成能力匹配度判断。')
        gaps.append('核心团队角色覆盖不完整，难以判断是否具备完整能力闭环')
        return self._pack_unknown(pack, gaps)

    def _gen_org_gap_filling_status(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        roles = self._fact_value(facts, 'core_team_members') or ''
        founders = self._fact_value(facts, 'founders') or ''
        text = '\n'.join(item.text for item in (self._usable_evidence(pack) or pack.evidence))
        gaps = list(pack.gap_reasons)
        if roles or founders or any(token in text for token in ['CEO', 'CTO', 'COO', '创始人', '联合创始人']):
            missing_roles = []
            for role in ['销售', '交付', '运营', '市场']:
                if role not in roles and role not in text:
                    missing_roles.append(role)
            if missing_roles:
                value = f'当前可见组织更偏技术/产品配置，{self._join_values(missing_roles)}等补位信息未在材料中体现。'
                gaps.append('组织补位主要体现为商业化与交付岗位信息缺失')
            else:
                value = '当前材料显示团队角色覆盖相对完整，但各岗位是否已到岗及协同历史仍需进一步核验。'
            return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于团队角色覆盖生成组织补位判断。')
        gaps.append('缺少稳定的团队结构信息')
        return self._pack_unknown(pack, gaps)

    def _gen_team_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        roles = self._fact_value(facts, 'core_team_members') or ''
        founders = self._fact_value(facts, 'founders') or ''
        text = '\n'.join(item.text for item in (self._usable_evidence(pack) or pack.evidence))
        gaps = list(pack.gap_reasons)
        if roles or founders or any(token in text for token in ['CEO', 'CTO', 'COO', '创始人', '联合创始人']):
            risk_parts = ['团队当前更依赖少数核心技术成员']
            if '销售' not in roles and '销售' not in text:
                risk_parts.append('商业化角色缺位或未披露')
            if '交付' not in roles and '运营' not in roles and '交付' not in text and '运营' not in text:
                risk_parts.append('后续规模化交付能力仍待验证')
            return self._make_result(pack, '；'.join(risk_parts) + '。', self._usable_evidence(pack) or pack.evidence, gaps, '基于团队角色与缺口生成团队风险判断。')
        gaps.append('缺少团队分工与协作历史材料')
        return self._pack_unknown(pack, gaps)

    def _gen_technical_barrier(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        route = self._fact_value(facts, 'technical_route') or ''
        if len(usable) < 2 and not route:
            return self._pack_unknown(pack, pack.gap_reasons + ['缺少可支撑技术壁垒的多条独立证据'])
        barrier_clues = []
        if route:
            barrier_clues.append('技术路线线索集中在 ' + route)
        text = '\n'.join(item.text for item in usable)
        if any(word in text for word in ['专利', '发明人', '平台技术']):
            barrier_clues.append('材料出现专利/平台化相关表述')
        if any(word in text for word in ['全球最小', '体积', 'BOM', '抗EMI', '抗干扰']):
            barrier_clues.append('差异点主要落在小型化、成本或抗干扰能力')
        value = '；'.join(barrier_clues[:3]) + '；但缺少量化指标、客户替代成本与长期可靠性验证，当前更适合作为壁垒线索而非已验证壁垒。'
        gaps = list(pack.gap_reasons)
        gaps.append('缺少量化性能指标和客户替代成本证据')
        return self._make_result(pack, value, usable or pack.evidence, gaps, '基于技术路线和对比线索生成技术壁垒分析。')

    def _gen_product_maturity(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        gaps = list(pack.gap_reasons)
        if any(word in text for word in ['Demo', '小试产线', '中试产线', 'Phase', '量产']):
            stage = '样机/试产推进阶段'
            if '量产' in text and ('小试产线' in text or '中试产线' in text):
                stage = '从样机向试产过渡阶段'
            value = f'材料显示项目当前更接近{stage}，已出现版本规划或产线推进线索；但稳定交付、批量客户验证和持续复购证据仍不足。'
            gaps.append('缺少真实客户试点或验收材料')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于版本/产线/阶段性表述生成产品成熟度判断。')
        return self._pack_unknown(pack, gaps + ['缺少明确产品阶段或交付阶段证据'])

    def _gen_substitutability(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        gaps = list(pack.gap_reasons)
        if any(word in text for word in ['对比', '竞品', '相机', '电容式', '压阻式', '替代']):
            value = '材料说明市场上存在相机式、电容式、压阻式等替代路线，项目差异线索主要集中在体积、功耗、抗干扰和读出链路；但缺少客户真实选型证据，因此替代难度仍未充分验证。'
            gaps.append('缺少客户真实选型或输赢单材料')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于竞品/替代方案线索生成可替代性分析。')
        return self._pack_unknown(pack, gaps + ['缺少替代方案或客户选型证据'])

    def _gen_demand_authenticity(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        customer = self._fact_value(facts, 'market_target_customer') or self._fact_value(facts, 'target_customer_type')
        gaps = list(pack.gap_reasons)
        if len(usable) < 2 or not customer:
            gaps.append('缺少客户访谈、付费试点或预算来源材料')
            return self._pack_unknown(pack, gaps)
        value = f'材料已能识别目标客户方向为{customer}，但当前更多是场景与需求表述，缺少付费试点、预算归属和采购推进证据，因此需求真实性仍需下一轮重点验证。'
        return self._make_result(pack, value, usable, gaps + ['缺少预算与采购链路信息'], '基于场景与客户线索生成需求真实性判断。')

    def _gen_market_size(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        gaps = list(pack.gap_reasons)
        if len(usable) < 2 or not self._has_text(usable, ['市场', '空间', '规模', '需求']):
            gaps.append('缺少统一口径的市场空间测算材料')
            return self._pack_unknown(pack, gaps)
        value = '材料对市场空间存在方向性表述，但尚未形成统一口径的 TAM/SAM/SOM 或可进入市场测算，因此目前只能确认赛道方向，不能确认市场空间大小。'
        return self._make_result(pack, value, usable, gaps + ['市场空间估算口径仍不统一'], '基于市场页和需求表述生成市场空间判断。')

    def _gen_market_drivers(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        gaps = list(pack.gap_reasons)
        if not any(token in text for token in ['客户', '需求', '场景', '机器人', '工业', '柔性电子', '可穿戴']):
            return self._pack_unknown(pack, gaps + ['缺少可支撑市场驱动因素的直接材料'])
        drivers = []
        for token in ['工业场景', '机器人', '智能可穿戴', '柔性电子', '抗干扰', '低功耗']:
            if token in text:
                drivers.append(token)
        if len(drivers) >= 2:
            value = f'当前可见的市场驱动因素主要包括{self._join_values(drivers)}等场景/性能需求；但这些驱动仍主要来自项目材料自述，缺少客户侧验证。'
            gaps.append('驱动因素主要来自项目材料自述')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于场景与需求关键词生成市场驱动因素判断。')
        return self._pack_unknown(pack, gaps + ['缺少可支撑市场驱动因素的直接材料'])

    def _gen_market_barriers(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        gaps = list(pack.gap_reasons)
        customer = self._fact_value(facts, 'market_target_customer') or self._fact_value(facts, 'target_customer_type')
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        if customer and any(token in text for token in ['预算', '采购', '导入', '周期', '教育', '部署', '决策链']):
            value = '当前市场阻碍因素更可能集中在客户教育、采购链条、预算归属和导入周期上；但这些阻碍尚缺客户访谈或销售复盘材料直接验证。'
            gaps.append('缺少客户采购流程与预算决策链条材料')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于目标客户线索和材料缺口生成市场阻碍因素判断。')
        return self._pack_unknown(pack, gaps + ['缺少客户采购流程与预算决策链条材料'])

    def _gen_market_timing(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        gaps = list(pack.gap_reasons)
        if self._fact_value(facts, 'market_track') and any(token in text for token in ['现在', '未来', '爆发', '窗口', '机器人', '智能可穿戴']) and any(token in text for token in ['订单', '采购', '预算', '试点', '场景', '需求']):
            value = '材料倾向于把当前时点视为技术路线和应用场景逐步成形的切入窗口；但由于缺少订单转化和客户预算证据，进入时机是否合适仍未完全验证。'
            gaps.append('缺少订单转化和采购节奏证据')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于赛道叙述与项目阶段线索生成市场进入时机判断。')
        return self._pack_unknown(pack, gaps + ['缺少进入窗口与客户转化相关材料'])

    def _gen_ticket_size_and_collection(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        return self._pack_unknown(pack, pack.gap_reasons + ['缺少合同、报价单、客单价与回款周期材料'])

    def _gen_delivery_and_scaling_logic(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        use_of_funds = self._fact_value(facts, 'use_of_funds')
        gaps = list(pack.gap_reasons)
        text = '\n'.join(item.text for item in usable)
        if use_of_funds and any(token in use_of_funds for token in ['研发', '量产', '市场']) and any(token in text for token in ['量产', '产线', '交付', '市场']):
            value = '从资金用途和阶段规划看，当前扩张仍依赖研发、产线与市场推进同步拉动，更接近硬件项目式推进而非已验证的标准化复制。'
            gaps.append('缺少交付周期、实施人效和复购数据')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于资金用途和阶段规划生成交付与扩张逻辑判断。')
        return self._pack_unknown(pack, gaps + ['缺少交付与复制相关材料'])

    def _gen_margin_and_cost_structure(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        gaps = list(pack.gap_reasons)
        if any(token in text for token in ['BOM', '成本', '量产', '研发']):
            value = '材料中能看到部分 BOM、研发和量产线索，说明成本压力大概率集中在硬件制造与研发迭代；但没有毛利率、交付成本与售后成本拆解，暂不能形成完整成本结构判断。'
            gaps.append('缺少毛利率与成本拆解数据')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于 BOM/量产/研发线索生成毛利与成本结构判断。')
        return self._pack_unknown(pack, gaps + ['缺少成本结构材料'])

    def _gen_business_model_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        gaps = list(pack.gap_reasons)
        missing = [
            '收费方式' if self._fact_missing(facts, 'pricing_model') else '',
            '收入结构' if self._fact_missing(facts, 'revenue_structure') else '',
            '收费对象' if self._fact_missing(facts, 'payer') else '',
        ]
        missing = [item for item in missing if item]
        if missing:
            value = f'当前商业模式的主要风险在于{self._join_values(missing)}信息缺失，导致变现路径、回款逻辑和可复制性都无法被有效验证。'
            gaps.append('商业模式关键字段缺失较多')
            return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于商业模式关键字段缺失生成风险判断。')
        return self._pack_unknown(pack, gaps + ['尚未形成可支撑商业模式风险判断的完整证据'])

    def _gen_competitor_types(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        competitor_fact = self._fact_value(facts, 'main_competitors') or ''
        gaps = list(pack.gap_reasons)
        types = []
        if any(token in text + competitor_fact for token in ['创业', '公司']):
            types.append('创业公司')
        if any(token in text + competitor_fact for token in ['相机', '电容式', '压阻式', '光纤', '压电式']):
            types.append('替代技术路线')
        if any(token in text + competitor_fact for token in ['自研', '自建', '客户自研']):
            types.append('客户自研')
        if types:
            value = f'当前可识别的竞品类型主要包括{self._join_values(types)}；但材料没有给出完整竞品池与分层对比。'
            gaps.append('缺少完整竞品池与客户选型记录')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于竞品描述生成竞品类型划分。')
        return self._pack_unknown(pack, gaps + ['缺少可用于竞品分类的稳定材料'])

    def _gen_differentiation(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        route = self._fact_value(facts, 'technical_route') or ''
        competitor_fact = self._fact_value(facts, 'main_competitors') or ''
        gaps = list(pack.gap_reasons)
        clues = []
        for token in ['全球尺寸最小', '低成本', '抗EMI', '抗干扰', '实时性', '功耗', 'BOM']:
            if token in text:
                clues.append(token)
        if not clues and route and competitor_fact:
            clues.extend([token for token in ['低成本', '抗EMI', '抗干扰', '实时性', '功耗'] if token in text + route + competitor_fact])
        if clues:
            value = f'当前差异化线索主要落在{self._join_values(clues)}等性能与工程属性上；但这些优势大多来自项目材料自述，缺少客户侧对比验证。'
            gaps.append('缺少客户视角的差异化验证')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于性能/工程对比线索生成差异化定位。')
        return self._pack_unknown(pack, gaps + ['缺少差异化对比材料'])

    def _gen_competitive_advantages(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        return self._gen_differentiation(module_name, pack, facts)

    def _gen_competitive_disadvantages(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        gaps = list(pack.gap_reasons)
        if self._fact_missing(facts, 'main_competitors'):
            gaps.append('直接竞品信息不完整，难以识别真实短板')
            return self._pack_unknown(pack, gaps)
        value = '当前更大的竞争劣势不是单一技术短板，而是客户选型、品牌背书、赢单输单记录和规模化交付证据仍然不足。'
        gaps.append('缺少赢单/输单复盘与客户替代路径')
        return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于竞品信息缺口生成竞争劣势判断。')

    def _gen_entry_barriers(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        usable = self._usable_evidence(pack)
        text = '\n'.join(item.text for item in usable)
        gaps = list(pack.gap_reasons)
        if any(token in text for token in ['体积', 'BOM', '抗EMI', '平台技术', '柔性']) or self._fact_value(facts, 'technical_route'):
            value = '行业进入壁垒线索主要体现在工程集成、小型化设计、读出链路和材料工艺积累；但客户切换成本与认证门槛尚无直接材料支撑。'
            gaps.append('缺少客户切换成本与认证要求材料')
            return self._make_result(pack, value, usable or pack.evidence, gaps, '基于工程与技术线索生成进入壁垒判断。')
        return self._pack_unknown(pack, gaps + ['缺少进入壁垒相关材料'])

    def _gen_investor_structure(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        financing = self._fact_value(facts, 'financing_history_detail') or self._fact_value(facts, 'financing_history')
        gaps = list(pack.gap_reasons)
        if financing and any(name in financing for name in ['基金', '创投', '中科创星', '投资']):
            value = '现有材料显示项目已获得外部投资方线索，且投资方中可能包含硬科技投资机构或地方科技基金；但缺少完整股东结构与老股东信息。'
            gaps.append('缺少股权结构和完整投资人清单')
            return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于融资记录生成投资方结构判断。')
        return self._pack_unknown(pack, gaps + ['缺少投资方结构材料'])

    def _gen_valuation_clues(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        return self._pack_unknown(pack, pack.gap_reasons + ['缺少估值、稀释比例和可比公司材料'])

    def _gen_capital_value_add(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        financing = self._fact_value(facts, 'financing_history_detail') or ''
        gaps = list(pack.gap_reasons)
        if financing:
            value = '当前可以确认项目已有资本进入线索，但投资方是否真正带来产业协同、渠道资源或品牌背书，材料尚未给出直接证据。'
            gaps.append('缺少投后资源协同与客户导入材料')
            return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于融资线索生成资本加持价值判断。')
        return self._pack_unknown(pack, gaps + ['缺少资本加持材料'])

    def _gen_capital_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        gaps = list(pack.gap_reasons)
        parts = []
        if self._fact_missing(facts, 'financing_history_detail'):
            parts.append('历史融资口径有限')
        if self._fact_missing(facts, 'use_of_funds'):
            parts.append('资金用途不完整')
        parts.append('估值区间和股权结构未披露')
        value = '当前资本风险主要在于' + '、'.join(parts) + '。'
        gaps.append('缺少估值、股权结构和资金消耗材料')
        return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于融资缺口生成资本风险判断。')

    def _gen_policy_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        return self._pack_unknown(pack, pack.gap_reasons + ['缺少合规边界、牌照或监管要求材料'])

    def _gen_technical_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        route = self._fact_value(facts, 'technical_route') or ''
        competitors = self._fact_value(facts, 'main_competitors') or ''
        evidence_items = self._usable_evidence(pack) or pack.evidence
        text = '\n'.join(item.text for item in evidence_items)
        gaps = list(pack.gap_reasons)
        comparison_clues = []
        for token in ['相机式', '电容式', '压阻式', '压电式', '光纤式']:
            if token in competitors or token in text:
                comparison_clues.append(token)
        if route or competitors or comparison_clues:
            if comparison_clues:
                value = f'技术风险主要在于相对{self._join_values(comparison_clues)}等替代路线的优势仍缺少第三方对比验证；当前更多是材料自述的低成本、抗干扰和实时性线索，尚未形成完整验证闭环。'
            else:
                value = '技术风险主要在于量化性能、长期稳定性、量产一致性和客户侧验证仍未充分展开；现阶段更像技术路线成立，但验证闭环尚未闭合。'
            gaps.append('缺少第三方对比测试与长期可靠性数据')
            return self._make_result(pack, value, evidence_items, gaps, '基于技术路线、竞品路线与缺口生成技术风险判断。')
        return self._pack_unknown(pack, gaps + ['技术路线尚不稳定，难以判断技术风险'])

    def _gen_commercialization_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        gaps = list(pack.gap_reasons)
        value = '当前商业化风险主要在于缺少付费客户、续费、客单价、回款周期和标准化交付证据，导致商业闭环尚未被验证。'
        gaps.append('缺少付费客户与收入验证材料')
        return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于商业模式与市场缺口生成商业化风险判断。')

    def _gen_organization_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        return self._gen_team_risk(module_name, pack, facts)

    def _gen_market_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        gaps = list(pack.gap_reasons)
        value = '当前市场风险主要不是赛道是否存在，而是客户需求强度、采购链路和订单转化速度尚无直接材料支撑。'
        gaps.append('缺少客户预算、采购链路与订单转化数据')
        return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于市场缺口生成市场风险判断。')

    def _gen_financing_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        return self._gen_capital_risk(module_name, pack, facts)

    def _gen_info_authenticity_risk(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        gaps = list(pack.gap_reasons)
        conflict_fields = []
        for fact in facts.values():
            if fact.conflict_detected:
                conflict_fields.append(fact.field_name)
        if conflict_fields:
            value = f'当前信息真实性风险主要来自{self._join_values(conflict_fields)}等字段存在冲突或需外部核验，系统不应直接裁定。'
            gaps.append('存在材料冲突或高不确定字段')
            return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于 fact 冲突与核验需求生成信息真实性风险判断。')
        value = '当前信息真实性风险主要来自材料披露不完整，而非已识别出的明确造假线索；但融资、团队与商业化关键信息仍需补充核验。'
        gaps.append('存在多项关键事实字段未闭合')
        return self._make_result(pack, value, self._usable_evidence(pack) or pack.evidence, gaps, '基于关键字段缺失生成信息真实性风险判断。')

    def _gen_risk_level(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        score = 0
        critical_keys = ['company_name', 'founders', 'current_financing_round', 'main_product_or_service', 'target_customer_type', 'use_of_funds']
        missing_count = sum(1 for key in critical_keys if self._fact_missing(facts, key))
        conflict_count = sum(1 for fact in facts.values() if fact.conflict_detected)
        score += missing_count
        score += 2 * conflict_count
        level = '低'
        if score >= 5:
            level = '高'
        elif score >= 2:
            level = '中'
        summary = f'基于关键事实缺失 {missing_count} 项、冲突 {conflict_count} 项，自动计算风险等级={level}。'
        return self._make_result(pack, level, self._usable_evidence(pack) or pack.evidence, list(pack.gap_reasons), summary)

    def _gen_followup_team(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        questions = []
        roles = self._fact_value(facts, 'core_team_members') or ''
        founders = self._fact_value(facts, 'founders') or ''
        founder_list = [item.strip() for item in re.split(r'[;；,，、\s]+', founders) if item.strip()]
        founder_count = len(founder_list)
        if not self._fact_value(facts, 'founder_background'):
            if founder_count >= 2:
                questions.append(f'已识别到 {founder_count} 位创始人，他们各自的教育背景、过往职位和代表性项目分别是什么？')
            elif founder_count == 1:
                questions.append(f'已识别到创始人 {founder_list[0]}，其教育背景、过往职位和代表性项目是什么？是否还有其他联合创始人未披露？')
            else:
                questions.append('BP 中可明确识别的创始人有几位？他们各自的教育背景、过往职位和代表性项目分别是什么？')
        if not any(token in roles for token in ['销售', 'BD', '商务', '客户成功', '增长']):
            questions.append('当前谁负责销售、BD 和客户导入？是否已有对应负责人到岗？')
        if founder_count >= 2 or roles:
            questions.append('当前核心团队成员之间是否有长期协作经历？目前创始人与核心团队各自分工如何划分？')
        else:
            questions.append('当前核心团队是否已有明确分工？创始人、技术、销售和客户导入分别由谁负责？')
        return self._make_result(pack, self._dedupe(questions)[:3], self._usable_evidence(pack) or pack.evidence, list(pack.gap_reasons), '基于团队缺口生成下一轮追问。')

    def _gen_followup_product_tech(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        questions = [
            '当前核心技术指标分别是多少？是否有第三方测试或客户测试数据？',
            '哪些技术环节是完全自研，哪些依赖第三方器件或工艺？',
            '目前产品处于 Demo、小试、中试还是可批量交付阶段？',
        ]
        return self._make_result(pack, questions, self._usable_evidence(pack) or pack.evidence, list(pack.gap_reasons), '基于产品与技术缺口生成下一轮追问。')

    def _gen_followup_market(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        questions = [
            '当前最明确的目标客户是谁？客户最强痛点具体发生在哪个流程？',
            '预算来自哪个部门，采购决策链条和周期分别是什么？',
            '是否已有付费试点、PoC 或样品验证记录？',
        ]
        return self._make_result(pack, questions, self._usable_evidence(pack) or pack.evidence, list(pack.gap_reasons), '基于市场缺口生成下一轮追问。')

    def _gen_followup_business_model(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        questions = [
            '收费对象到底是谁，当前按项目、按硬件销售还是软硬件打包收费？',
            '单客户客单价区间、回款周期和收入确认方式分别是什么？',
            '交付是否高度定制化，复制新客户时需要新增多少实施资源？',
        ]
        return self._make_result(pack, questions, self._usable_evidence(pack) or pack.evidence, list(pack.gap_reasons), '基于商业模式缺口生成下一轮追问。')

    def _gen_followup_competition(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        questions = [
            '最近输掉过哪些单，客户最终为什么没有选你们？',
            '客户为什么会选择你们而不是相机式、电容式或其他替代路线？',
            '你们相对于主要竞品的体积、成本、稳定性和交付周期对比数据是什么？',
        ]
        return self._make_result(pack, questions, self._usable_evidence(pack) or pack.evidence, list(pack.gap_reasons), '基于竞争缺口生成下一轮追问。')

    def _gen_followup_financing_operation(self, module_name: str, pack: FieldEvidencePack, facts: dict[str, FactFieldResult]) -> AnalysisFieldResult:
        questions = [
            '历史融资轮次、金额、时间、投资方和当前股权结构分别是什么？',
            '本轮资金的核心用途、资金消耗节奏和当前现金流可支撑多久？',
            '下一轮融资计划何时启动，触发下一轮的关键业务里程碑是什么？',
        ]
        return self._make_result(pack, questions, self._usable_evidence(pack) or pack.evidence, list(pack.gap_reasons), '基于融资与经营缺口生成下一轮追问。')

    # ---------- module synthesis ----------
    def _build_module_gaps(self, module_name: str, facts: dict[str, FactFieldResult], analysis_fields: list[AnalysisFieldResult]) -> list[str]:
        spec = MODULE_SPEC_MAP[module_name]
        gaps = list(spec.gap_hints)
        for fact in facts.values():
            if fact.final_status != 'extracted':
                gaps.append(f'{fact.field_name}：{fact.final_status}')
            gaps.extend(fact.gap_reasons)
            if fact.conflict_detected:
                gaps.append(f'{fact.field_name}存在冲突候选：' + '；'.join(fact.conflict_values))
        for field in analysis_fields:
            gaps.extend(field.gap_reasons)
            if field.final_status == '无法判断':
                gaps.append(f'{field.field_name}：证据不足，当前无法判断')
        return self._dedupe(gaps)

    def _build_module_evidence_basis(self, module_name: str, facts: dict[str, FactFieldResult], analysis_fields: list[AnalysisFieldResult]) -> str:
        evidence = self._collect_module_evidence(facts, {field.field_key: field for field in analysis_fields})
        if not evidence:
            return '未检索到直接证据。'
        docs = sorted({item.document_name for item in evidence})
        locators = '；'.join(f'{item.document_name}:{item.locator_type}={item.locator_value}' for item in evidence[:5])
        return f'当前模块证据主要来自：{'；'.join(docs)}。优先定位：{locators}。'

    def _build_module_core_conclusion(self, module_name: str, facts: dict[str, FactFieldResult], analysis_fields: list[AnalysisFieldResult], info_gaps: list[str]) -> str:
        if module_name == '项目基础信息':
            track = self._fact_value(facts, 'track_label') or self._fact_value(facts, 'market_track')
            product = self._fact_value(facts, 'main_product_or_service') or self._fact_value(facts, 'brand_or_product_name')
            if product:
                if track:
                    return f'当前材料可将项目初步识别为围绕{track}方向展开，核心产品/方案线索已出现，但主体与融资信息仍需继续核验。'
                return '当前材料已能识别项目的产品方向，但主体名称、成立时间或注册信息仍不稳定。'
            return '项目基础轮廓尚未稳定，主体识别与关键事实字段仍有明显缺口。'
        if module_name == '团队判断':
            if not self._fact_missing(facts, 'core_team_members') or not self._fact_missing(facts, 'founders'):
                return '团队核心角色已有初步识别，技术主干可见；但创始人履历、商业化角色和组织补位信息仍不完整。'
            return '团队信息不足，暂难判断是否具备完整的项目推进能力。'
        if module_name == '产品与技术':
            if not self._fact_missing(facts, 'technical_route'):
                return '技术路线已有较多材料支撑，但产品成熟度、量化性能和客户验证仍不足。'
            return '产品方向有线索，但技术路线和成熟度都未形成可靠判断。'
        if module_name == '市场分析':
            if self._fact_value(facts, 'market_target_customer') or self._fact_value(facts, 'target_customer_type'):
                return '市场切入方向已能初步识别，但需求真实性、预算来源和市场空间仍需穿透验证。'
            return '市场分析仍停留在方向识别，客户与需求强度尚未验证。'
        if module_name == '商业模式':
            return '当前商业模式证据最薄弱，变现方式、客单价和回款逻辑都未闭合。'
        if module_name == '竞争格局':
            return '已有竞品与差异化线索，但真实竞争结构和客户选择理由仍不清楚。'
        if module_name == '融资与资本信息':
            return '融资线索已出现，但估值、股权结构和资金效率仍缺关键材料。'
        if module_name == '风险识别':
            risk_level = next((field.final_value for field in analysis_fields if field.field_key == 'risk_level'), '中')
            return f'当前已识别的主要风险来自信息缺口与商业化验证不足，综合风险等级偏{risk_level}。'
        if module_name == '追问清单':
            return '下一轮沟通应优先围绕客户验证、商业模式、融资真实性和团队补位展开。'
        return '无法判断'

    def _build_module_preliminary_judgment(self, module_name: str, facts: dict[str, FactFieldResult], analysis_fields: list[AnalysisFieldResult], info_gaps: list[str]) -> str:
        unknown_count = sum(1 for field in analysis_fields if field.final_status == '无法判断')
        fact_missing_count = sum(1 for field in facts.values() if field.final_status != 'extracted')
        if module_name == '追问清单':
            return '在完成上述关键问题验证前，不宜直接进入估值和交易层面推进。'
        if fact_missing_count >= 3 or unknown_count >= 2:
            return '当前模块信息仍不闭合，建议继续补证后再做更强判断。'
        return '当前模块已形成初步判断，但仍需结合下一轮材料或访谈继续验证。'

    def _pick_project_name(self, fact_result: FactProcessingResult, input_materials: list[str] | None = None) -> str:
        fact_map = {field.field_key: field for module in fact_result.modules for field in module.field_results}
        generic_values = {'软硬件公司', '硬件公司', '软件公司', '机器人公司', '科技公司', '企业信息', '公司信息', '飞行汽车公司'}

        stem_counts: dict[str, int] = {}
        for name in input_materials or []:
            stem = self._clean_material_stem(name)
            if stem and stem not in generic_values and '杞‖浠?' not in stem and '椋炶姹借溅' not in stem:
                stem_counts[stem] = stem_counts.get(stem, 0) + 1
        repeated_stems = sorted(
            [stem for stem, count in stem_counts.items() if count >= 2],
            key=lambda stem: (stem_counts[stem], len(stem)),
            reverse=True,
        )
        if repeated_stems:
            return repeated_stems[0]

        bp_stems: list[str] = []
        for name in input_materials or []:
            if not re.search(r'(Business\s*Plan|BP|Pitch|Deck)', name, flags=re.I):
                continue
            stem = self._clean_material_stem(name)
            stem = stem
            stem = stem
            stem = re.sub(r'[（(].*?[）)]', '', stem).strip(' _-')
            if stem and stem not in generic_values and '软硬件' not in stem and '飞行汽车' not in stem:
                bp_stems.append(stem)
        if bp_stems:
            return bp_stems[0]

        for key in ['company_name']:
            item = fact_map.get(key)
            if item and item.final_status == 'extracted':
                if isinstance(item.final_value, str) and item.final_value and item.final_value not in {'材料未体现', '材料提及但信息不足', '需外部核验'}:
                    candidate = item.final_value.split('；')[0].strip()
                    if candidate not in generic_values and '软硬件' not in candidate and '飞行汽车' not in candidate:
                        return candidate
        for name in input_materials or []:
            stem = self._clean_material_stem(name)
            stem = stem
            stem = stem
            stem = re.sub(r'[（(].*?[）)]', '', stem).strip(' _-')
            if stem and stem not in generic_values and '软硬件' not in stem and '飞行汽车' not in stem:
                return stem
        return '[待填写]'

    def _sanitize_people_list(self, value: str | None) -> str | None:
        if not value:
            return value
        tokens = re.split(r'[；;，,、\s]+', value)
        cleaned = [token for token in tokens if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', token or '')]
        return '；'.join(dict.fromkeys(cleaned)) if cleaned else None

    def _sanitize_team_members(self, value: str | None) -> str | None:
        if not value:
            return value
        matches = re.findall(
            r'((?:CEO|CTO|COO|CFO|CMO)(?:/[A-Za-z]+)?(?:\s+Co-founder)?\s+[\u4e00-\u9fff]{2,4})(?=[；;，,、]|$)',
            value,
        )
        cleaned = list(dict.fromkeys(match.strip() for match in matches))
        return '；'.join(cleaned) if cleaned else None

    def _clean_material_stem(self, name: str) -> str:
        stem = re.sub(r'\.(pdf|docx|txt)$', '', name, flags=re.I)
        stem = re.sub(r'[_-]?ver[0-9.]+$', '', stem, flags=re.I)
        stem = re.sub(r'[_-]?v[0-9.]+$', '', stem, flags=re.I)
        stem = re.sub(r'[_-]?\d{6,8}$', '', stem)
        stem = re.sub(r'Business\s*Plan.*$', '', stem, flags=re.I)
        stem = re.sub(r'BP.*$', '', stem, flags=re.I)
        stem = re.sub(r'[（(].*?[)）]', '', stem)
        return stem.strip(' _-')

    def _pick_project_name(self, fact_result: FactProcessingResult, input_materials: list[str] | None = None) -> str:
        fact_map = {field.field_key: field for module in fact_result.modules for field in module.field_results}
        generic_values = {'软硬件公司', '硬件公司', '软件公司', '机器人公司', '科技公司', '企业信息', '公司信息', '飞行汽车公司'}

        stem_counts: dict[str, int] = {}
        for name in input_materials or []:
            stem = self._clean_material_stem(name)
            if stem and stem not in generic_values and '软硬件' not in stem and '飞行汽车' not in stem:
                stem_counts[stem] = stem_counts.get(stem, 0) + 1
        repeated_stems = sorted(
            [stem for stem, count in stem_counts.items() if count >= 2],
            key=lambda stem: (stem_counts[stem], len(stem)),
            reverse=True,
        )
        if repeated_stems:
            return repeated_stems[0]

        bp_stems: list[str] = []
        for name in input_materials or []:
            if not re.search(r'(Business\s*Plan|BP|Pitch|Deck)', name, flags=re.I):
                continue
            stem = self._clean_material_stem(name)
            if stem and stem not in generic_values and '软硬件' not in stem and '飞行汽车' not in stem:
                bp_stems.append(stem)
        if bp_stems:
            return bp_stems[0]

        item = fact_map.get('company_name')
        if item and item.final_status == 'extracted' and isinstance(item.final_value, str):
            candidate = item.final_value.split('；')[0].strip()
            if candidate and candidate not in generic_values and '软硬件' not in candidate and '飞行汽车' not in candidate:
                return candidate

        for name in input_materials or []:
            stem = self._clean_material_stem(name)
            if stem and stem not in generic_values and '软硬件' not in stem and '飞行汽车' not in stem:
                return stem
        return '[待填写]'

    def _sanitize_people_list(self, value: str | None) -> str | None:
        if not value:
            return value
        tokens = re.split(r"[；;，,、\s]+", value)
        cleaned = [token for token in tokens if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", token or "")]
        return "；".join(dict.fromkeys(cleaned)) if cleaned else None

    def _sanitize_team_members(self, value: str | None) -> str | None:
        if not value:
            return value
        matches = re.findall(
            r"((?:CEO|CTO|COO|CFO|CMO)(?:/[A-Za-z]+)?(?:\s+Co-founder)?\s+[\u4e00-\u9fff]{2,4})(?=[；;，,、]|$)",
            value,
        )
        cleaned = list(dict.fromkeys(match.strip() for match in matches))
        return "；".join(cleaned) if cleaned else None

    def _clean_material_stem(self, name: str) -> str:
        stem = re.sub(r"\.(pdf|docx|txt)$", "", name, flags=re.I)
        stem = re.sub(r"[_-]?ver[0-9.]+$", "", stem, flags=re.I)
        stem = re.sub(r"[_-]?v[0-9.]+$", "", stem, flags=re.I)
        stem = re.sub(r"[_-]?\d{6,8}$", "", stem)
        stem = re.sub(r"Business\s*Plan.*$", "", stem, flags=re.I)
        stem = re.sub(r"BP.*$", "", stem, flags=re.I)
        stem = re.sub(r"[（(].*?[)）]", "", stem)
        return stem.strip(" _-")

    def _pick_project_name(self, fact_result: FactProcessingResult, input_materials: list[str] | None = None) -> str:
        fact_map = {field.field_key: field for module in fact_result.modules for field in module.field_results}
        generic_values = {"软硬件公司", "硬件公司", "软件公司", "机器人公司", "科技公司", "企业信息", "公司信息", "飞行汽车公司"}

        stem_counts: dict[str, int] = {}
        for name in input_materials or []:
            stem = self._clean_material_stem(name)
            if stem and stem not in generic_values and "软硬件" not in stem and "飞行汽车" not in stem:
                stem_counts[stem] = stem_counts.get(stem, 0) + 1
        repeated_stems = sorted(
            [stem for stem, count in stem_counts.items() if count >= 2],
            key=lambda stem: (stem_counts[stem], len(stem)),
            reverse=True,
        )
        if repeated_stems:
            return repeated_stems[0]

        bp_stems: list[str] = []
        for name in input_materials or []:
            if not re.search(r"(Business\s*Plan|BP|Pitch|Deck)", name, flags=re.I):
                continue
            stem = self._clean_material_stem(name)
            if stem and stem not in generic_values and "软硬件" not in stem and "飞行汽车" not in stem:
                bp_stems.append(stem)
        if bp_stems:
            return bp_stems[0]

        item = fact_map.get("company_name")
        if item and item.final_status == "extracted" and isinstance(item.final_value, str):
            candidate = item.final_value.split("；")[0].strip()
            if candidate and candidate not in generic_values and "软硬件" not in candidate and "飞行汽车" not in candidate:
                return candidate

        for name in input_materials or []:
            stem = self._clean_material_stem(name)
            if stem and stem not in generic_values and "软硬件" not in stem and "飞行汽车" not in stem:
                return stem
        return "[待填写]"

    def _sanitize_people_list(self, value: str | None) -> str | None:
        if not value:
            return value
        tokens = re.split(r"[;\uFF1B,\uFF0C\u3001\s]+", value)
        cleaned = [token for token in tokens if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", token or "")]
        return ";".join(dict.fromkeys(cleaned)) if cleaned else None

    def _sanitize_team_members(self, value: str | None) -> str | None:
        if not value:
            return value
        matches = re.findall(
            r"((?:CEO|CTO|COO|CFO|CMO)(?:/[A-Za-z]+)?(?:\s+Co-founder)?\s+[\u4e00-\u9fff]{2,4})(?=[;\uFF1B,\uFF0C\u3001]|$)",
            value,
        )
        cleaned = list(dict.fromkeys(match.strip() for match in matches))
        return ";".join(cleaned) if cleaned else None

    def _build_overall_conclusion(self, fact_result: FactProcessingResult, analysis_result: AnalysisGenerationResult) -> tuple[OverallConclusion, str]:
        fact_map = {field.field_key: field for module in fact_result.modules for field in module.field_results}
        analysis_map = {field.field_key: field for module in analysis_result.modules for field in module.field_results}
        critical_fact_keys = ['company_name', 'founders', 'main_product_or_service', 'target_customer_type', 'current_financing_round', 'use_of_funds']
        missing_critical = [key for key in critical_fact_keys if key not in fact_map or fact_map[key].final_status != 'extracted']
        conflicts = [field.field_name for field in fact_map.values() if field.conflict_detected]
        unknown_analysis = [field.field_name for field in analysis_map.values() if field.final_status == '无法判断']
        risk_level = analysis_map.get('risk_level').final_value if analysis_map.get('risk_level') else '中'

        visible_conflicts = [name for name in conflicts if name not in {'成立时间'}]
        has_minor_subject_conflict = bool(conflicts) and not visible_conflicts

        if len(missing_critical) >= 3 or len(unknown_analysis) >= 10:
            parts = []
            parts.append(f'关键事实字段仍有 {len(missing_critical)} 项未闭合')
            if visible_conflicts:
                parts.append('存在材料冲突字段：' + '、'.join(visible_conflicts[:3]))
            elif has_minor_subject_conflict:
                parts.append('存在少量主体信息口径冲突，需回到原始材料核对')
            if unknown_analysis:
                parts.append(f'分析字段中仍有 {len(unknown_analysis)} 项无法判断')
            parts.append('当前更适合先补材料，再决定是否推进')
            return '信息不足，建议补充材料后再判断', '；'.join(parts) + '。'

        if risk_level == '高':
            reason = f'综合风险等级为高；主要问题集中在{'、'.join(visible_conflicts[:3]) if visible_conflicts else ('主体信息口径冲突' if has_minor_subject_conflict else '商业化验证和信息闭合')}。'
            return '存在明显风险，谨慎推进', reason

        if conflicts:
            if visible_conflicts:
                parts = ['存在材料冲突字段：' + '、'.join(visible_conflicts[:3]), '当前应先补证并核对口径']
            else:
                parts = ['存在少量主体信息口径冲突', '当前应先补证并核对口径']
            return '信息不足，建议补充材料后再判断', '；'.join(parts) + '。'

        highlights = []
        if fact_map.get('technical_route') and fact_map['technical_route'].final_status == 'extracted':
            highlights.append('技术路线已有明确材料支撑')
        if fact_map.get('core_team_members') and fact_map['core_team_members'].final_status == 'extracted':
            highlights.append('核心团队角色已有初步识别')
        if fact_map.get('financing_history_detail') and fact_map['financing_history_detail'].final_status == 'extracted':
            highlights.append('存在历史融资线索')
        reason = '；'.join(highlights[:3]) if highlights else '关键事实与分析字段已达到初步沟通所需的最低完整度'
        if risk_level == '中':
            reason += '；但仍需围绕商业化与信息核验继续穿透'
        return '建议进入下一轮沟通', reason + '。'


def render_analysis_markdown(payload: dict) -> str:
    lines: list[str] = []
    lines.append('# Analysis 字段生成结果\n')
    lines.append(f"- module_count: {payload['metadata'].get('module_count', 0)}")
    lines.append(f"- analysis_field_count: {payload['metadata'].get('analysis_field_count', 0)}\n")
    for module in payload['modules']:
        lines.append(f"## {module['module_name']}\n")
        lines.append(f"- 核心结论: {module['core_conclusion']}")
        lines.append(f"- 证据依据: {module['evidence_basis']}")
        lines.append(f"- 初步判断: {module['preliminary_judgment']}\n")
        for field in module['field_results']:
            lines.append(f"### {field['field_name']}")
            lines.append(f"- final_status: {field['final_status']}")
            lines.append(f"- final_value: {field['final_value']}")
            lines.append(f"- generation_summary: {field['generation_summary']}")
            if field.get('gap_reasons'):
                lines.append('- gap_reasons:')
                for gap in field['gap_reasons']:
                    lines.append(f'  - {gap}')
            if field.get('selected_evidence'):
                lines.append('- selected_evidence:')
                for item in field['selected_evidence']:
                    lines.append(f"  - {item['document_name']}，{item['locator_type']}={item['locator_value']}，score={item['score']}：{item['text'][:140]}")
            lines.append('')
    return '\n'.join(lines) + '\n'


def render_structured_report_markdown(payload: dict) -> str:
    meta = payload['metadata']
    lines: list[str] = []
    lines.append('# AI/硬科技创业项目初筛尽调报告\n')
    lines.append(f"**项目名称**：{meta.get('project_name', '[待填写]')}")
    lines.append(f"**报告生成时间**：{meta.get('report_generated_at', '[待填写]')}")
    lines.append('**输入材料清单**：')
    for item in meta.get('input_materials', []):
        lines.append(f'- {item}')
    lines.append(f"\n**分析边界说明**：{meta.get('analysis_boundary', '')}\n")
    lines.append(f"**总体初筛结论**：{payload['overall_screening_conclusion']}\n")
    lines.append(f"**总体初筛结论说明**：{payload['overall_screening_reason']}\n")
    for module in payload['modules']:
        lines.append(f"## {module['module_name']}\n")
        lines.append(f"**核心结论**：{module['core_conclusion']}\n")
        for field in module['field_results']:
            value = field['value']
            if isinstance(value, list):
                display = '；'.join(value)
            else:
                display = value
            lines.append(f"- **{field['field_name']}**：{display}")
        lines.append('\n**证据出处**：')
        if module.get('evidence'):
            for item in module['evidence']:
                quote = ' '.join(item['text'].split())[:140]
                lines.append(f"- {item['document_name']}，{item['locator_type']}={item['locator_value']}：\"{quote}\" → {item['support']}")
        else:
            lines.append('- 未检索到直接证据')
        lines.append(f"\n**证据依据**：{module['evidence_basis']}")
        lines.append('\n**信息缺失项**：')
        for gap in module.get('info_gaps', []):
            lines.append(f'- {gap}')
        lines.append(f"\n**初步判断**：{module['preliminary_judgment']}\n")
    return '\n'.join(lines) + '\n'
