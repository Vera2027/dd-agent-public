
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
import re
from typing import Callable, Iterable, Literal

from dd_agent.reporting.models import EvidenceItem, FieldEvidenceBuildResult, FieldEvidencePack
from dd_agent.reporting.module_specs import MODULE_SPECS

FactFinalStatus = Literal['extracted', '材料未体现', '材料提及但信息不足', '需外部核验']

ROUND_KEYWORDS = [
    '种子轮', '天使轮', 'Pre-A', 'Pre A', 'A轮', 'A+轮', 'B轮', 'B+轮', 'C轮', '战略投资', '股权融资', 'IPO',
]
TRACK_KEYWORDS = [
    '机器人', '具身机器人', '触觉传感器', '柔性电子', '多轴压力传感器', '传感器', '消费电子', '工业自动化',
    '智能可穿戴', '数据手套', '人机交互', '仿生机器人', '机器视觉', '工业场景',
]
CUSTOMER_KEYWORDS = [
    '机器人厂商', '工业客户', '工业场景', '消费电子客户', '科研机构', '高校实验室', '灵巧手厂商',
    '可穿戴设备厂商', '系统集成商', '终端客户', 'B端客户', '制造企业',
]
TECH_ROUTE_KEYWORDS = [
    '光学式', '视觉式', '电容式', '压阻式', '压电式', '磁场/感应式', '磁感应', '电磁感应', '柔性电子',
    '多轴压力传感器', '光电读出', '图像重建', '三轴解算', '触觉阵列', '柔性触觉阵列', '平台技术',
]
PRODUCT_FORM_PATTERNS = {
    '软硬一体': ['软硬一体', '软硬结合', '软硬件一体', '整体解决方案'],
    '硬件': ['传感器', '模组', '设备', '薄膜', '阵列', '手套', '硬件'],
    '软件': ['软件', '算法', '算法平台', 'SaaS'],
    'API': ['API', '接口'],
}
PRICING_PATTERNS = {
    '一次性买断': ['买断', '一次性'],
    '订阅制': ['订阅', '年费', '月费'],
    '项目制': ['项目制', '项目交付', '定制化项目'],
    '按调用量计费': ['按调用', '按量计费'],
    '按效果分成': ['分成', '按效果'],
    '软硬件打包收费': ['软硬件', '打包收费'],
    '硬件销售': ['销售', 'BOM', '量产'],
}
USE_OF_FUNDS_KEYWORDS = ['研发', '量产', '市场', '运营', '团队建设', '供应链', '认证', '渠道']
BAD_GENERIC_PERSON_TOKENS = {'联合', '创始人', '三大', '皮肤三大', '团队', '核心', '成员', '等投资', '投资', '融资', '产品及商', '产品', '商业化', '管理'}
BAD_LOCATION_HINTS = ['皮肤', '硅胶', '结构', '光源', '电路', '相机', '弹性体', '接触面', '下方', '上方']
BAD_PRODUCT_TOKENS = {'Phase', 'Demo', 'Confidential', '核心技术', '产品展示', '相关产品'}
BAD_COMPANY_NAME_VALUES = {'企业信息', '公司信息', '基本信息', '企业简介', '公司简介', '项目介绍', '企业概况', '公司概况', '企业资料', '公司资料', '软硬件公司', '机器人公司', '科技公司', '飞行汽车公司'}
GENERIC_COMPANY_TERMS = {'软硬件', '硬件', '软件', '机器人', '飞行汽车', '传感器', '人工智能', 'AI', '消费电子', '智能硬件', '汽车', '无人机', '科技'}
BAD_TRACK_VALUES = {'应用方向', '行业方向', '市场方向', '相关赛道', '所属赛道'}
WEBSITE_LABELS = ['官网', '公司官网', '官方网站', '网站', '产品链接']
MAIN_PRODUCT_LABELS = ['主营产品', '主营业务', '核心产品', '产品矩阵', '解决方案', '产品形态']
TRACK_HINTS = ['机器人', '具身机器人', '触觉感知', '触觉传感器', '电子皮肤', '柔性电子', '人机交互', '智能可穿戴']
COMMERCIAL_CUES = ['收费', '报价', '合同', '销售', '售价', '采购', '收入', '回款', '买断', '订阅', '打包', '项目制']
TARGET_SPLIT_TOKENS = r'[；;、,/]|[•·]'
LOCATION_SUFFIXES = ('省', '市', '区', '县', '镇', '新区', '园区')
BACKGROUND_MARKERS = ['博士', '硕士', '学士', '本科', '毕业于', '师从', '研究方向']
CAREER_MARKERS = ['曾任', '曾在', '历任', '联合创始人', '前CTO', '副教授', '教授', '研究员', '主任研究员', '负责人', '领导经验', '创业', '从业', '任职']
SPEC_SHEET_MARKERS = ['BOM', 'Demo', 'mm3', 'Full Scale', '分辨率', '传感器', '阵列', '薄膜']
PRODUCT_KEY_TERMS = ['传感器', '阵列', '薄膜', '平台', '系统', '方案', '解决方案', '电子皮肤', '模组', '手套']
PRODUCT_NOISE_TERMS = ['目标客户', '所属赛道', '赛道', '机器人', '消费电子', '工业客户', '科研机构', '高校实验室', '数据', '算法', '经营地', '注册地址', '融资']
FINANCING_HEADER_VALUES = {'融资历史', '历史融资', '融资情况', '历史融资情况', '融资历史1', '融资历史 1'}

BAD_NAME_SUBSTRINGS = {'投资', '融资', '产业', '平台', '视觉', '科学', '人工', '智能', '实验室', '机器人', '产品', '研发', '市场', '运营', '客户', '技术'}
GENERIC_PROJECT_NAME_VALUES = {'软硬件公司', '硬件公司', '软件公司', '机器人公司', '科技公司', '企业信息', '公司信息', '飞行汽车公司'}
PRODUCT_SENTENCE_NOISE = {'愿景', '打造', '最领先', '形成规模化订单收入', '探索', '应用场景', '产业内', '开创者', '先行者', '引领者', '定位'}
CUSTOMER_NOISE_TERMS = {'曾在', '主导', '领导', '实验室', '教授', '博士', '毕业于', '研究', '平台赋能', '研发部门', '创始团队成员'}


@dataclass(slots=True)
class FactValueCandidate:
    raw_value: str
    normalized_value: str
    confidence: float
    method: str
    evidence_chunk_id: str
    document_name: str
    locator_type: str
    locator_value: int

    def to_dict(self) -> dict:
        return {
            'raw_value': self.raw_value,
            'normalized_value': self.normalized_value,
            'confidence': self.confidence,
            'method': self.method,
            'evidence_chunk_id': self.evidence_chunk_id,
            'document_name': self.document_name,
            'locator_type': self.locator_type,
            'locator_value': self.locator_value,
        }


@dataclass(slots=True)
class FactFieldResult:
    field_name: str
    field_key: str
    final_status: FactFinalStatus
    final_value: str
    normalized_value: str | None
    selected_evidence: list[EvidenceItem] = field(default_factory=list)
    extracted_candidates: list[FactValueCandidate] = field(default_factory=list)
    conflict_detected: bool = False
    conflict_values: list[str] = field(default_factory=list)
    gap_reasons: list[str] = field(default_factory=list)
    processor_summary: str = ''

    def to_dict(self) -> dict:
        return {
            'field_name': self.field_name,
            'field_key': self.field_key,
            'final_status': self.final_status,
            'final_value': self.final_value,
            'normalized_value': self.normalized_value,
            'selected_evidence': [item.to_dict() for item in self.selected_evidence],
            'extracted_candidates': [item.to_dict() for item in self.extracted_candidates],
            'conflict_detected': self.conflict_detected,
            'conflict_values': self.conflict_values,
            'gap_reasons': self.gap_reasons,
            'processor_summary': self.processor_summary,
        }


@dataclass(slots=True)
class ModuleFactResult:
    module_name: str
    field_results: list[FactFieldResult]

    def to_dict(self) -> dict:
        return {
            'module_name': self.module_name,
            'field_results': [item.to_dict() for item in self.field_results],
        }


@dataclass(slots=True)
class FactProcessingResult:
    modules: list[ModuleFactResult]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'metadata': self.metadata,
            'modules': [module.to_dict() for module in self.modules],
        }


@dataclass(slots=True)
class FactFieldConfig:
    extractor: str
    value_mode: Literal['scalar', 'list', 'summary'] = 'scalar'
    min_evidence_score: float = 0.08
    max_group_count: int | None = None


FIELD_CONFIGS: dict[str, FactFieldConfig] = {
    'company_name': FactFieldConfig('company_name'),
    'brand_or_product_name': FactFieldConfig('product_name', value_mode='list'),
    'establishment_date': FactFieldConfig('date'),
    'registered_or_main_location': FactFieldConfig('location'),
    'founders': FactFieldConfig('person_list', value_mode='list'),
    'core_team_members': FactFieldConfig('team_members', value_mode='list'),
    'current_financing_round': FactFieldConfig('financing_round'),
    'financing_history': FactFieldConfig('financing_history', value_mode='summary'),
    'main_product_or_service': FactFieldConfig('main_product_or_service', value_mode='summary'),
    'official_website_or_product_link': FactFieldConfig('link'),
    'target_customer_type': FactFieldConfig('customer_type', value_mode='list', max_group_count=6),
    'track_label': FactFieldConfig('track_label', value_mode='list'),
    'founder_background': FactFieldConfig('background_summary', value_mode='summary', max_group_count=1),
    'founder_prior_experience': FactFieldConfig('prior_experience', value_mode='summary', max_group_count=1),
    'problem_to_solve': FactFieldConfig('problem_summary', value_mode='summary'),
    'product_form': FactFieldConfig('product_form'),
    'technical_route': FactFieldConfig('technical_route', value_mode='list'),
    'market_track': FactFieldConfig('track_label', value_mode='list'),
    'market_target_customer': FactFieldConfig('customer_type', value_mode='list', max_group_count=6),
    'payer': FactFieldConfig('customer_type', value_mode='list'),
    'pricing_model': FactFieldConfig('pricing_model', value_mode='list'),
    'revenue_structure': FactFieldConfig('revenue_structure', value_mode='summary'),
    'main_competitors': FactFieldConfig('competitors', value_mode='list'),
    'financing_history_detail': FactFieldConfig('financing_history', value_mode='summary'),
    'use_of_funds': FactFieldConfig('use_of_funds', value_mode='list'),
}


class FactFieldProcessor:
    def __init__(self) -> None:
        self.field_specs = {
            field.field_key: field
            for module in MODULE_SPECS
            for field in module.fields
            if field.field_type == 'fact'
        }
        self.extractors: dict[str, Callable[[str, str, EvidenceItem], list[str]]] = {
            'company_name': self._extract_company_names,
            'product_name': self._extract_product_names,
            'date': self._extract_dates,
            'location': self._extract_locations,
            'person_list': self._extract_people,
            'team_members': self._extract_team_members,
            'financing_round': self._extract_financing_rounds,
            'financing_history': self._extract_financing_history,
            'main_product_or_service': self._extract_main_product_or_service,
            'link': self._extract_links,
            'customer_type': self._extract_customer_types,
            'track_label': self._extract_track_labels,
            'background_summary': self._extract_background_summary,
            'prior_experience': self._extract_prior_experience,
            'problem_summary': self._extract_problem_summary,
            'product_form': self._extract_product_form,
            'technical_route': self._extract_technical_route,
            'pricing_model': self._extract_pricing_model,
            'revenue_structure': self._extract_revenue_structure,
            'competitors': self._extract_competitors,
            'use_of_funds': self._extract_use_of_funds,
        }

    def process(self, evidence_result: FieldEvidenceBuildResult) -> FactProcessingResult:
        modules: list[ModuleFactResult] = []
        processed_count = 0
        for module in evidence_result.modules:
            field_results: list[FactFieldResult] = []
            for pack in module.field_packs:
                if pack.field_type != 'fact':
                    continue
                field_results.append(self.process_field_pack(pack))
                processed_count += 1
            modules.append(ModuleFactResult(module_name=module.module_name, field_results=field_results))
        return FactProcessingResult(
            modules=modules,
            metadata={
                'module_count': len(modules),
                'fact_field_count': processed_count,
                'processor_mode': 'fact_field_processor_v2',
            },
        )

    def process_field_pack(self, pack: FieldEvidencePack) -> FactFieldResult:
        spec = self.field_specs[pack.field_key]
        config = FIELD_CONFIGS.get(pack.field_key, FactFieldConfig('generic_summary', value_mode='summary'))
        usable_evidence = self._filter_evidence(pack, min_score=config.min_evidence_score)
        gap_reasons = list(pack.gap_reasons)

        if not usable_evidence:
            final_status = self._pick_gap_status(spec, has_evidence=bool(pack.evidence), prefer_insufficient=bool(pack.evidence))
            return FactFieldResult(
                field_name=pack.field_name,
                field_key=pack.field_key,
                final_status=final_status,
                final_value=final_status,
                normalized_value=None,
                selected_evidence=[],
                extracted_candidates=[],
                gap_reasons=self._dedupe(gap_reasons + [f'字段“{pack.field_name}”没有通过过滤的有效业务证据']),
                processor_summary=f'字段“{pack.field_name}”在 evidence pack 中存在候选，但经过模板/低分过滤后无有效证据。',
            )

        candidates = self._extract_candidates(pack, usable_evidence, config)
        if not candidates:
            return FactFieldResult(
                field_name=pack.field_name,
                field_key=pack.field_key,
                final_status=self._pick_gap_status(spec, has_evidence=True, prefer_insufficient=True),
                final_value=self._pick_gap_status(spec, has_evidence=True, prefer_insufficient=True),
                normalized_value=None,
                selected_evidence=usable_evidence[:2],
                extracted_candidates=[],
                gap_reasons=self._dedupe(gap_reasons + [f'字段“{pack.field_name}”已有证据，但当前规则未能抽出稳定候选值']),
                processor_summary=f'字段“{pack.field_name}”已有 {len(usable_evidence)} 条有效证据，但仍未形成稳定候选值。',
            )

        groups = self._group_candidates(candidates)
        top_groups = sorted(groups.values(), key=self._group_sort_key, reverse=True)
        if pack.field_key == 'company_name':
            selected_groups = self._select_company_name_groups(top_groups)
            conflict_detected, conflict_values = self._detect_conflict(top_groups, config, field_key=pack.field_key)
        elif pack.field_key == 'product_form':
            selected_groups = self._select_product_form_groups(top_groups)
            conflict_detected, conflict_values = False, []
        else:
            max_group_count = config.max_group_count or (1 if config.value_mode == 'scalar' else 4)
            selected_groups = top_groups[:max_group_count]
            conflict_detected, conflict_values = self._detect_conflict(top_groups, config, field_key=pack.field_key)

        final_status: FactFinalStatus = 'extracted'
        if conflict_detected and '需外部核验' in spec.allowed_status:
            final_status = '需外部核验'
            gap_reasons.append(f'字段“{pack.field_name}”出现多个高相似度候选值，当前无法仅凭材料裁定')
        elif conflict_detected:
            gap_reasons.append(f'字段“{pack.field_name}”存在多组候选表达，已按证据支持度选择当前最强候选')

        final_value = self._render_groups_value(selected_groups, config)
        normalized_value = self._render_groups_value(selected_groups, config, normalized=True)
        used_chunk_ids = {
            candidate.evidence_chunk_id
            for group in selected_groups
            for candidate in group['candidates']
        }
        selected_evidence = [item for item in usable_evidence if item.chunk_id in used_chunk_ids][:4]
        summary = (
            f'字段“{pack.field_name}”从 {len(usable_evidence)} 条有效证据中抽出 {len(candidates)} 个候选，'
            f'归并为 {len(groups)} 组，最终状态={final_status}。'
        )
        if conflict_detected:
            summary += f' 冲突候选包括：{"；".join(conflict_values[:3])}。'

        return FactFieldResult(
            field_name=pack.field_name,
            field_key=pack.field_key,
            final_status=final_status,
            final_value=final_value if final_status == 'extracted' else final_status,
            normalized_value=normalized_value,
            selected_evidence=selected_evidence,
            extracted_candidates=candidates[:8],
            conflict_detected=conflict_detected,
            conflict_values=conflict_values,
            gap_reasons=self._dedupe(gap_reasons),
            processor_summary=summary,
        )

    def _pick_gap_status(self, spec, *, has_evidence: bool, prefer_insufficient: bool) -> FactFinalStatus:
        if not has_evidence:
            if '材料未体现' in spec.allowed_status:
                return '材料未体现'
            return spec.allowed_status[0]
        if prefer_insufficient and '材料提及但信息不足' in spec.allowed_status:
            return '材料提及但信息不足'
        if '需外部核验' in spec.allowed_status:
            return '需外部核验'
        if '材料未体现' in spec.allowed_status:
            return '材料未体现'
        return spec.allowed_status[0]

    def _filter_evidence(self, pack: FieldEvidencePack, *, min_score: float) -> list[EvidenceItem]:
        usable: list[EvidenceItem] = []
        for item in pack.evidence:
            notes = item.metadata.get('retrieval_notes', [])
            if any('模板' in note or '字段标签' in note for note in notes):
                continue
            if item.score < min_score:
                continue
            cleaned = self._clean_text(item.text)
            if len(cleaned) < 4:
                continue
            if pack.field_key in {'founders', 'core_team_members', 'founder_background', 'founder_prior_experience'}:
                if self._looks_like_external_executive_quote(cleaned):
                    continue
            usable.append(item)
        if pack.field_key in {'company_name', 'founders', 'core_team_members'}:
            bp_only = [item for item in usable if self._is_bp_document(item.document_name)]
            if bp_only:
                return bp_only
        return usable

    def _is_bp_document(self, document_name: str) -> bool:
        lower = document_name.lower()
        return 'business plan' in lower or re.search(r'(^|[^a-z])bp([^a-z]|$)', lower) is not None

    def _extract_candidates(
        self,
        pack: FieldEvidencePack,
        evidence: list[EvidenceItem],
        config: FactFieldConfig,
    ) -> list[FactValueCandidate]:
        extractor = self.extractors.get(config.extractor, self._extract_generic_summary)
        candidates: list[FactValueCandidate] = []
        for item in evidence:
            raw_values = extractor(self._clean_text(item.text), pack.field_key, item)
            base_confidence = min(0.95, max(0.2, item.score + 0.2))
            for index, raw_value in enumerate(raw_values):
                cleaned_value = self._clean_candidate(raw_value)
                if not cleaned_value:
                    continue
                if self._is_invalid_candidate_for_field(pack.field_key, cleaned_value, item):
                    continue
                normalized_value = self._normalize_value(cleaned_value, config)
                if not normalized_value:
                    continue
                confidence = self._score_candidate(pack.field_key, cleaned_value, normalized_value, item, base_confidence - index * 0.03)
                if confidence < 0.08:
                    continue
                candidates.append(
                    FactValueCandidate(
                        raw_value=cleaned_value,
                        normalized_value=normalized_value,
                        confidence=round(max(0.08, confidence), 4),
                        method=config.extractor,
                        evidence_chunk_id=item.chunk_id,
                        document_name=item.document_name,
                        locator_type=item.locator_type,
                        locator_value=item.locator_value,
                    )
                )
        return candidates

    def _group_candidates(self, candidates: list[FactValueCandidate]) -> dict[str, dict]:
        groups: dict[str, dict] = {}
        for candidate in candidates:
            bucket = groups.setdefault(
                candidate.normalized_value,
                {
                    'normalized_value': candidate.normalized_value,
                    'raw_values': [],
                    'candidates': [],
                    'support_chunk_ids': set(),
                    'support_docs': set(),
                    'total_confidence': 0.0,
                    'max_confidence': 0.0,
                },
            )
            bucket['raw_values'].append(candidate.raw_value)
            bucket['candidates'].append(candidate)
            bucket['support_chunk_ids'].add(candidate.evidence_chunk_id)
            bucket['support_docs'].add(candidate.document_name)
            bucket['total_confidence'] += candidate.confidence
            bucket['max_confidence'] = max(bucket['max_confidence'], candidate.confidence)
        return groups

    def _group_sort_key(self, group: dict) -> tuple:
        return (
            len(group['support_chunk_ids']),
            len(group['support_docs']),
            round(group['total_confidence'], 6),
            round(group['max_confidence'], 6),
            len(group['normalized_value']),
        )

    def _detect_conflict(self, top_groups: list[dict], config: FactFieldConfig, field_key: str | None = None) -> tuple[bool, list[str]]:
        if len(top_groups) <= 1:
            return False, []
        if config.value_mode in {'list', 'summary'}:
            return False, []
        first, second = top_groups[0], top_groups[1]
        if field_key == 'company_name':
            f = first['normalized_value']
            s = second['normalized_value']
            if f in s or s in f:
                return False, []
        first_score = self._group_sort_key(first)
        second_score = self._group_sort_key(second)
        if second_score[:2] >= (1, 1) and second['normalized_value'] != first['normalized_value']:
            if second['total_confidence'] >= first['total_confidence'] * 0.75:
                return True, [first['normalized_value'], second['normalized_value']]
        return False, []

    def _select_company_name_groups(self, top_groups: list[dict]) -> list[dict]:
        if not top_groups:
            return []
        legal_suffixes = ('有限公司', '有限责任公司', '股份有限公司', '科技有限公司', '公司')
        legal_groups = [group for group in top_groups if group['normalized_value'].endswith(legal_suffixes)]
        if legal_groups:
            legal_groups = sorted(legal_groups, key=self._group_sort_key, reverse=True)
            return [legal_groups[0]]
        return [top_groups[0]]

    def _select_product_form_groups(self, top_groups: list[dict]) -> list[dict]:
        if not top_groups:
            return []
        labels = {group['normalized_value'] for group in top_groups}
        if '软硬一体' in labels:
            return [next(group for group in top_groups if group['normalized_value'] == '软硬一体')]
        if '硬件' in labels and '软件' in labels:
            synthetic = dict(top_groups[0])
            synthetic['normalized_value'] = '软硬一体'
            synthetic['raw_values'] = ['软硬一体']
            synthetic['candidates'] = [candidate for group in top_groups if group['normalized_value'] in {'硬件', '软件'} for candidate in group['candidates']]
            synthetic['support_chunk_ids'] = {candidate.evidence_chunk_id for candidate in synthetic['candidates']}
            synthetic['support_docs'] = {candidate.document_name for candidate in synthetic['candidates']}
            synthetic['total_confidence'] = sum(candidate.confidence for candidate in synthetic['candidates'])
            synthetic['max_confidence'] = max((candidate.confidence for candidate in synthetic['candidates']), default=0.0)
            return [synthetic]
        return [top_groups[0]]

    def _render_groups_value(self, groups: list[dict], config: FactFieldConfig, *, normalized: bool = False) -> str:
        values: list[str] = []
        for group in groups:
            group_values = [group['normalized_value']] if normalized else list(dict.fromkeys(group['raw_values']))
            values.extend(group_values)
        if config.value_mode == 'scalar':
            return values[0]
        if config.value_mode == 'list':
            tokens = []
            split_pattern = r'[；;、,]|\s{2,}' if config.extractor in {'person_list', 'team_members'} else r'[；;、,/]|\s{2,}'
            for value in values:
                for part in re.split(split_pattern, value):
                    token = self._clean_candidate(part)
                    if token and token not in tokens:
                        tokens.append(token)
            return '；'.join(tokens[:6])
        deduped_values = []
        for value in values:
            if value not in deduped_values:
                deduped_values.append(value)
        return '；'.join(deduped_values[:4])

    def _is_invalid_candidate_for_field(self, field_key: str, value: str, item: EvidenceItem) -> bool:
        text = self._clean_text(item.text)
        lower_doc = item.document_name.lower()
        if field_key == 'company_name':
            if value in BAD_COMPANY_NAME_VALUES or self._looks_generic_company_phrase(value):
                return True
            if any(token in value for token in ['企业信息', '公司信息', '基本信息', '简介', '概况', '资料']) and not value.endswith(('公司', '有限公司', '有限责任公司', '科技有限公司')):
                return True
            if len(value) <= 4 and not value.endswith(('公司', '有限公司', '有限责任公司', '科技有限公司')):
                if not any(label in text for label in ['公司名称', '企业名称', '项目名称']) and 'business plan' not in lower_doc and 'bp' not in lower_doc:
                    return True
        if field_key == 'brand_or_product_name':
            if value in BAD_COMPANY_NAME_VALUES or value in {'产品名称', '品牌名称'}:
                return True
            if any(token in value for token in ['企业信息', '公司信息', '基本信息']):
                return True
            if len(value) > 28 or any(token in value for token in PRODUCT_SENTENCE_NOISE):
                return True
        if field_key == 'registered_or_main_location':
            if value in {'中国', '国内'}:
                return True
            if len(value) <= 3 and not any(label in text for label in ['主要经营地', '经营地', '经营地址', '办公地址', '注册地址', '注册地']):
                return True
            if any(token in text for token in ['交易轮次', '投资方', '未融资']):
                return True
        if field_key in {'financing_history', 'financing_history_detail'}:
            if '|' in value or '未融资' in value:
                return True
            if value in FINANCING_HEADER_VALUES or re.fullmatch(r'(融资历史|历史融资|融资情况)\s*\d*', value):
                return True
            if len(value) < 6 and not any(token in value for token in ROUND_KEYWORDS + ['投资', '基金', '轮']):
                return True
        if field_key == 'main_product_or_service':
            if not self._is_product_service_phrase(value):
                return True
        if field_key in {'founders', 'core_team_members'}:
            if any(token in value for token in BAD_NAME_SUBSTRINGS):
                return True
            if self._looks_like_external_executive_quote(text):
                return True
        if field_key in {'target_customer_type', 'market_target_customer', 'payer'}:
            if any(token in value for token in CUSTOMER_NOISE_TERMS):
                return True
        if field_key in {'track_label', 'market_track'} and value in BAD_TRACK_VALUES:
            return True
        return False

    def _looks_like_external_executive_quote(self, text: str) -> bool:
        cleaned = self._clean_text(text)
        if not any(token in cleaned for token in ['CEO', 'CTO', 'COO', 'CFO', '董事长', '总裁']):
            return False
        if not any(token in cleaned for token in ['表示', '认为', '判断', '指出']):
            return False
        if not any(token in cleaned for token in ['集团', '董事长兼', '同样判断']):
            return False
        if any(token in cleaned for token in ['创始人', '联合创始人', 'Co-founder', 'Founder', '团队成员', '毕业于', '曾任', '师从']):
            return False
        return True

    def _score_candidate(self, field_key: str, raw_value: str, normalized_value: str, item: EvidenceItem, base_confidence: float) -> float:
        score = max(0.05, base_confidence)
        text = self._clean_text(item.text)
        doc_name = item.document_name.lower()
        if 'business plan' in doc_name or 'bp' in doc_name:
            if field_key in {'company_name', 'brand_or_product_name', 'main_product_or_service', 'official_website_or_product_link', 'track_label', 'market_track', 'target_customer_type', 'market_target_customer', 'founder_background', 'founder_prior_experience', 'core_team_members', 'founders'}:
                score += 0.08
            if field_key == 'company_name':
                score += 0.10
        if item.locator_type == 'page' and item.locator_value <= 3 and field_key in {'company_name', 'establishment_date', 'registered_or_main_location', 'official_website_or_product_link'}:
            score += 0.05
        if field_key == 'company_name':
            if any(label in text for label in ['公司名称', '企业名称', '项目名称']):
                score += 0.24
            if normalized_value.endswith(('有限公司', '有限责任公司', '股份有限公司', '科技有限公司', '公司')):
                score += 0.18
            if normalized_value in BAD_COMPANY_NAME_VALUES or self._looks_generic_project_name(normalized_value) or self._looks_generic_company_phrase(normalized_value):
                score -= 0.6
        elif field_key == 'establishment_date':
            if any(label in text for label in ['成立日期', '成立时间', '创立于', '注册成立', '公司成立']):
                score += 0.24
            if re.search(r'(?:19|20)\d{2}[-/.年](?:0?[1-9]|1[0-2])', raw_value):
                score += 0.08
        elif field_key == 'registered_or_main_location':
            if any(label in text for label in ['主要经营地', '经营地']):
                score += 0.30
            elif any(label in text for label in ['经营地址', '办公地址', '总部位于', '公司地址']):
                score += 0.16
            elif any(label in text for label in ['注册地址', '注册地']):
                score += 0.10
            if len(normalized_value) <= 3:
                score -= 0.12
        elif field_key == 'main_product_or_service':
            if any(label in text for label in MAIN_PRODUCT_LABELS):
                score += 0.22
            if any(token in raw_value for token in ['传感器', '阵列', '电子皮肤', '解决方案', '平台', '系统', '方案']):
                score += 0.14
            if any(token in raw_value for token in PRODUCT_NOISE_TERMS) and not any(term in raw_value for term in PRODUCT_KEY_TERMS):
                score -= 0.28
        elif field_key == 'brand_or_product_name':
            if any(label in text for label in ['产品名称', '品牌名称', '核心产品']):
                score += 0.24
        elif field_key in {'financing_history', 'financing_history_detail'}:
            if any(label in text for label in ['融资历史', '历史融资', '交易轮次', '投资方']) and '|' not in text and '未融资' not in text:
                score += 0.18
            if '投资方：' in raw_value:
                score += 0.22
            if raw_value in FINANCING_HEADER_VALUES or re.fullmatch(r'(融资历史|历史融资|融资情况)\s*\d*', raw_value):
                score -= 0.45
            if '|' in text or '未融资' in text:
                score -= 0.40
        elif field_key == 'official_website_or_product_link':
            if any(label in text for label in WEBSITE_LABELS):
                score += 0.18
            if re.search(r'(https?://|www\.|[A-Za-z0-9.-]+\.(?:com|cn|ai|io|net))', raw_value):
                score += 0.24
        elif field_key in {'track_label', 'market_track'}:
            if any(label in text for label in ['赛道', '行业方向', '应用方向', '市场方向']):
                score += 0.14
            if any(token in raw_value for token in TRACK_HINTS):
                score += 0.10
        elif field_key in {'founder_background', 'founder_prior_experience'}:
            if 'CEO' in text:
                score += 0.10
            if any(token in text for token in ['CEO', '创始人']) and 'CTO' not in text[: max(0, text.find(raw_value) + len(raw_value))]:
                score += 0.08
            if 'CTO' in text and 'CEO' not in text and '创始人' not in text:
                score -= 0.16
        return min(0.98, score)

    def _normalize_value(self, value: str, config: FactFieldConfig) -> str:
        if config.extractor == 'date':
            return self._normalize_date(value)
        if config.value_mode == 'list':
            split_pattern = r'[；;、,]|\s{2,}' if config.extractor in {'person_list', 'team_members'} else r'[；;、,/]|\s{2,}'
            parts = [self._clean_candidate(part) for part in re.split(split_pattern, value)]
            parts = [part for part in parts if part]
            if config.extractor in {'person_list', 'team_members'}:
                deduped = []
                for part in parts:
                    if part not in deduped:
                        deduped.append(part)
                return '；'.join(deduped)
            parts = sorted(dict.fromkeys(parts))
            return '；'.join(parts)
        return self._clean_candidate(value)

    def _clean_text(self, text: str) -> str:
        cleaned = text.replace('Confidential', ' ').replace('\u3000', ' ')
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    def _clean_candidate(self, value: str) -> str:
        value = self._clean_text(value)
        value = value.strip('：:;；，,。.- []()（）“”\" ')
        value = re.sub(r'^[0-9]+[.)、]\s*', '', value)
        value = re.sub(r'^[0-9]{1,2}\s+(?=[\u4e00-\u9fffA-Za-z])', '', value)
        value = re.sub(r'\s{2,}', ' ', value)
        if len(value) <= 1:
            return ''
        if re.fullmatch(r'\d{1,3}', value):
            return ''
        if value in {'项目名称', '公司名称', '产品名称', '融资历史', '相关产品', '产品展示'}:
            return ''
        if value in BAD_GENERIC_PERSON_TOKENS or value in BAD_PRODUCT_TOKENS:
            return ''
        if value.startswith('Phase '):
            return ''
        return value

    def _normalize_date(self, value: str) -> str:
        match = re.search(r'((?:19|20)\d{2})(?:[年\-/.]((?:1[0-2])|(?:0?[1-9])))?(?:[月\-/.]((?:3[01])|(?:[12]\d)|(?:0?[1-9])))?', value)
        if not match:
            return value
        year, month, day = match.group(1), match.group(2), match.group(3)
        if month and day:
            return f'{year}-{int(month):02d}-{int(day):02d}'
        if month:
            return f'{year}-{int(month):02d}'
        return year

    def _dedupe(self, values: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r'[。；;\n]', text)
        return [self._clean_candidate(part) for part in parts if self._clean_candidate(part)]

    def _split_profile_clauses(self, text: str) -> list[str]:
        working = self._clean_text(text)
        working = re.sub(r'(?:(?:CEO|CTO|COO|CFO|CMO)(?:/[^\s]{1,20})?(?:\s+Co-founder)?\s+[\u4e00-\u9fff]{2,4})', ' ', working)
        parts = re.split(r'[•·\n；;]', working)
        clauses = []
        for part in parts:
            cleaned = self._clean_candidate(part)
            if not cleaned:
                continue
            if self._looks_like_spec_sentence(cleaned):
                continue
            clauses.append(cleaned)
        return self._dedupe(clauses)

    def _extract_doc_title(self, document_name: str) -> str:
        stem = re.sub(r'\.(pdf|docx|txt)$', '', document_name, flags=re.I)
        stem = re.sub(r'[_-]?ver[0-9.]+$', '', stem, flags=re.I)
        stem = re.sub(r'[_-]?v[0-9.]+$', '', stem, flags=re.I)
        stem = re.sub(r'[_-]?\d{6,8}$', '', stem)
        stem = re.sub(r'Business\s*Plan.*$', '', stem, flags=re.I)
        stem = re.sub(r'BP.*$', '', stem, flags=re.I)
        stem = re.sub(r'[（(].*?[）)]', '', stem)
        stem = stem.strip(' _-')
        return stem

    def _looks_generic_project_name(self, value: str) -> bool:
        value = self._clean_candidate(value)
        if not value:
            return True
        if value in GENERIC_PROJECT_NAME_VALUES or value in BAD_COMPANY_NAME_VALUES:
            return True
        if len(value) <= 4 and not any(ch.isalpha() for ch in value):
            return True
        if self._looks_generic_company_phrase(value):
            return True
        if re.search(r'软硬件|科技|机器人公司|企业信息|公司信息|飞行汽车公司', value):
            return True
        return False

    def _looks_generic_company_phrase(self, value: str) -> bool:
        value = self._clean_candidate(value)
        if not value:
            return True
        if value in BAD_COMPANY_NAME_VALUES:
            return True
        if value.endswith('公司') and not value.endswith(('有限公司', '有限责任公司', '股份有限公司', '科技有限公司')):
            prefix = value[:-2]
            if prefix in GENERIC_COMPANY_TERMS:
                return True
            if any(term in prefix for term in GENERIC_COMPANY_TERMS):
                return True
            if len(prefix) <= 3:
                return True
        return False

    def _looks_like_location(self, value: str) -> bool:
        if not value or any(token in value for token in BAD_LOCATION_HINTS):
            return False
        if any(value.endswith(suffix) for suffix in LOCATION_SUFFIXES):
            return True
        if re.search(r'(省|市|区|县)', value) and any(token in value for token in ['路', '街', '道', '号', '室', '楼', '栋', '幢', '园', '大厦']):
            return True
        return len(value) <= 8 and bool(re.fullmatch(r'[一-鿿]{2,8}', value))

    def _looks_like_team_profile(self, text: str) -> bool:
        return any(token in text for token in ['CEO', 'CTO', 'COO', 'Co-founder', '师从', '毕业于', '研究方向', '副教授', '博士'])

    def _looks_like_primary_founder_profile(self, text: str) -> bool:
        cleaned = self._clean_text(text)
        role_spans = self._extract_role_name_spans(cleaned)
        if not role_spans:
            founder_without_joint = cleaned.replace('联合创始人', '')
            return 'CEO' in cleaned or '创始人' in founder_without_joint or 'Founder' in cleaned

        owner = self._infer_profile_owner(role_spans, cleaned)
        has_ceo = any('CEO' in span['role'] for span in role_spans)
        has_page_noise = bool(re.search(r'\b\d{1,2}\b\s*(?:Confidential)?', cleaned))

        if len(role_spans) >= 3:
            if owner is None:
                return False
            role = owner['role']
            return 'CEO' in role or ('创始人' in role and '联合创始人' not in role)

        if has_page_noise and len(role_spans) > 1:
            if owner is None:
                return False
            role = owner['role']
            return 'CEO' in role or ('创始人' in role and '联合创始人' not in role)

        if has_ceo:
            return True

        if owner is None:
            return False
        role = owner['role']
        return '创始人' in role and '联合创始人' not in role

    def _looks_like_spec_sentence(self, text: str) -> bool:
        if sum(1 for marker in SPEC_SHEET_MARKERS if marker in text) >= 2:
            return True
        if re.search(r'\b\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?', text):
            return True
        if re.search(r'\bBOM<\d+', text):
            return True
        return False

    def _is_product_service_phrase(self, value: str) -> bool:
        if not value:
            return False
        if len(value) > 32:
            return False
        if any(token in value for token in ['官网', '经营地', '注册地址', '成立日期', '融资']):
            return False
        if any(token in value for token in PRODUCT_SENTENCE_NOISE):
            return False
        if sum(1 for term in ['；', '，', ',', '。'] if term in value) >= 2:
            return False
        product_hits = sum(1 for term in PRODUCT_KEY_TERMS if term in value)
        noise_hits = sum(1 for term in PRODUCT_NOISE_TERMS if term in value)
        if noise_hits and product_hits == 0:
            return False
        if noise_hits >= 2 and '解决方案' not in value and '多轴' not in value and '电子皮肤' not in value and '平台' not in value:
            return False
        if ' ' in value and noise_hits >= 2:
            return False
        if re.search(r'(?:形成|打造|探索|赋能|构建)', value):
            return False
        return product_hits > 0

    def _product_value_priority(self, value: str) -> tuple:
        return (
            1 if re.search(r'[A-Za-z][A-Za-z0-9-]{2,}', value) else 0,
            sum(1 for term in ['传感器', '解决方案', '阵列', '平台', '系统', '电子皮肤', '夹爪', '灵巧手'] if term in value),
            -len(value),
        )

    def _extract_primary_founder_block(self, text: str) -> str:
        cleaned = self._clean_text(text)
        role_spans = self._extract_role_name_spans(cleaned)
        if not role_spans:
            return cleaned
        owner = next((span for span in role_spans if 'CEO' in span['role']), None)
        if owner is None:
            owner = next((span for span in role_spans if '创始人' in span['role'] and '联合创始人' not in span['role']), None)
        if owner is None:
            return ''
        next_start = min((span['start'] for span in role_spans if span['start'] > owner['start']), default=len(cleaned))
        block = self._clean_candidate(cleaned[owner['end']:next_start])
        if block and any(marker in block for marker in BACKGROUND_MARKERS + CAREER_MARKERS):
            return block
        return block or ''

    def _role_exact_matches(self, text: str) -> list[str]:
        pattern = r'((?:CEO|CTO|COO|CFO|CMO)(?:/[^\s]{1,20})?(?:\s+Co-founder)?\s+[\u4e00-\u9fff]{2,4})(?=[\s，,；;。:：]|$)'
        values = re.findall(pattern, text)
        return self._dedupe([self._clean_candidate(value) for value in values if self._clean_candidate(value)])


    def _extract_role_name_spans(self, text: str) -> list[dict]:
        pattern = re.compile(r'((?:CEO|CTO|COO|CFO|CMO)(?:/[^\s]{1,20})?(?:\s+Co-founder)?|联合创始人|创始人|Founder)\s*[:：/]?\s*([\u4e00-\u9fff]{2,4})')
        spans: list[dict] = []
        for match in pattern.finditer(text):
            spans.append({
                'role': self._clean_candidate(match.group(1)),
                'name': self._clean_candidate(match.group(2)),
                'start': match.start(),
                'end': match.end(),
            })
        return spans

    def _infer_profile_owner(self, role_spans: list[dict], text: str) -> dict | None:
        if not role_spans:
            return None
        if len(role_spans) == 1:
            return role_spans[0]
        profile_markers = BACKGROUND_MARKERS + CAREER_MARKERS
        marker_positions = [text.find(marker) for marker in profile_markers if text.find(marker) >= 0]
        if not marker_positions:
            return None
        first_marker_pos = min(marker_positions)
        preceding = [span for span in role_spans if span['start'] < first_marker_pos]
        if not preceding:
            return None
        return max(preceding, key=lambda span: span['start'])

    def _extract_background_fragments(self, text: str) -> list[str]:
        fragments: list[str] = []
        patterns = [
            r'(研究方向[:：]?\s*[^；;。•·]{2,60})',
            r'(师从[^；;。•·]{2,80})',
            r'((?:本科[^；;。•·]{0,30})?毕业于[^；;。•·]{2,80})',
            r'([\u4e00-\u9fffA-Za-z]+大学[^，,；;。•·]{0,10}(?:工学博士|理学博士|博士|硕士|学士))',
        ]
        for pattern in patterns:
            fragments.extend(re.findall(pattern, text))
        cleaned: list[str] = []
        for fragment in fragments:
            value = self._clean_candidate(fragment)
            if not value:
                continue
            if '副教授' in value or (re.search(r'(?:教授|研究员)\s*$', value) and not value.startswith('师从')):
                continue
            cleaned.append(value)
        return self._dedupe(cleaned)

    def _extract_career_fragments(self, text: str) -> list[str]:
        fragments: list[str] = []
        patterns = [
            r'([\u4e00-\u9fffA-Za-z]+大学\s*(?:副教授|教授))',
            r'([^；;。•·]{0,40}(?:曾任|曾在|历任)[^；;。•·]{2,80})',
            r'([^；;。•·]{0,40}(?:研究员|主任研究员|负责人|领导经验|创业|从业|任职)[^；;。•·]{0,80})',
        ]
        for pattern in patterns:
            fragments.extend(re.findall(pattern, text))
        cleaned: list[str] = []
        for fragment in fragments:
            value = self._clean_candidate(fragment)
            if not value:
                continue
            if any(marker in value for marker in ['博士', '硕士', '本科毕业于', '毕业于', '师从', '研究方向']) and not any(job in value for job in ['副教授', '教授', '研究员', '负责人', '领导经验']):
                continue
            cleaned.append(value)
        return self._dedupe(cleaned)

    def _extract_company_names(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values: list[str] = []
        explicit_patterns = [
            r'(?:公司名称|企业名称)[:：]?\s*([\u4e00-\u9fffA-Za-z0-9·()（）\-]{2,50})',
            r'(?:项目名称)[:：]?\s*([\u4e00-\u9fffA-Za-z0-9·()（）\-]{2,40})',
        ]
        for pattern in explicit_patterns:
            values.extend(re.findall(pattern, text))
        values.extend(re.findall(r'([\u4e00-\u9fffA-Za-z0-9·()（）\-]{2,30}(?:有限公司|有限责任公司|股份有限公司|科技有限公司|公司))', text))
        doc_title = self._extract_doc_title(item.document_name)
        if doc_title and re.fullmatch(r'[\u4e00-\u9fffA-Za-z0-9·]{2,12}', doc_title):
            doc_name = item.document_name.lower()
            if 'business plan' in doc_name or 'bp' in doc_name:
                values.append(doc_title)
        cleaned = []
        for value in values:
            value = self._clean_candidate(value)
            if not value:
                continue
            value = re.split(r'[，。；;\n ]', value)[0]
            if value in BAD_COMPANY_NAME_VALUES:
                continue
            if 'Phase' in value:
                continue
            cleaned.append(value)
        return self._dedupe(cleaned)

    def _extract_product_names(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values: list[str] = []
        values.extend(re.findall(r'(?:产品名称|品牌名称|核心产品)[:：]?\s*([^。；;\n]{2,60})', text))
        values.extend(re.findall(r'([\u4e00-\u9fffA-Za-z]{2,20}(?:传感器|阵列|薄膜|平台|方案|系统|手套|电子皮肤))', text))
        cleaned: list[str] = []
        for value in values:
            for part in re.split(TARGET_SPLIT_TOKENS, value):
                part = self._clean_candidate(part)
                if not part:
                    continue
                if any(token in part for token in BAD_PRODUCT_TOKENS) or part.startswith('Phase'):
                    continue
                if not self._is_product_service_phrase(part):
                    continue
                cleaned.append(part)
        prioritized = sorted(self._dedupe(cleaned), key=self._product_value_priority, reverse=True)
        return prioritized

    def _extract_dates(self, text: str, field_key: str, item: EvidenceItem) -> list[str]:
        if field_key == 'establishment_date':
            values: list[str] = []
            label_patterns = [
                r'(?:成立日期|成立时间|成立于|创立于|注册成立(?:日期)?|公司成立(?:日期)?|创办于|成立)[:：]?\s*((?:19|20)\d{2}年\d{1,2}月\d{1,2}日)',
                r'(?:成立日期|成立时间|成立于|创立于|注册成立(?:日期)?|公司成立(?:日期)?|创办于|成立)[:：]?\s*((?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2})',
                r'(?:成立日期|成立时间|成立于|创立于|注册成立(?:日期)?|公司成立(?:日期)?|创办于|成立)[:：]?\s*((?:19|20)\d{2}年\d{1,2}月)',
                r'(?:成立日期|成立时间|成立于|创立于|注册成立(?:日期)?|公司成立(?:日期)?|创办于|成立)[:：]?\s*((?:19|20)\d{2})',
            ]
            for pattern in label_patterns:
                values.extend(re.findall(pattern, text))
                if values:
                    break
            return self._dedupe(values)
        return self._dedupe(re.findall(r'(?:19|20)\d{2}(?:年|[-/.](?:0?[1-9]|1[0-2])(?:[-/.](?:0?[1-9]|[12]\d|3[01]))?)?', text))

    def _extract_locations(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values: list[str] = []
        patterns = [
            r'(?:主要经营地|经营地)[:：]?\s*([^，。；;\n]{2,40})',
            r'(?:经营地址|办公地址|公司地址|总部位于|注册于)[:：]?\s*([^，。；;\n]{2,40})',
            r'(?:注册地址|注册地)[:：]?\s*([^，。；;\n]{2,40})',
            r'(?:公司|总部|办公)(?:位于|落地于)\s*([^，。；;\n]{2,40})',
        ]
        for pattern in patterns:
            values.extend(re.findall(pattern, text))
        cleaned = []
        for value in values:
            value = self._clean_candidate(value)
            if not value:
                continue
            value = re.split(r'[，。；;\n]', value)[0].strip()
            if not value:
                continue
            if any(hint in value for hint in BAD_LOCATION_HINTS):
                continue
            if any(token in value for token in ['大学', '学院', '实验室', '社区']):
                continue
            if self._looks_like_location(value):
                cleaned.append(value)
        return self._dedupe(cleaned)

    def _extract_people(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        if self._looks_like_external_executive_quote(text):
            return []
        values: list[str] = []
        for pattern in [
            r'(?:联合创始人|创始人|CEO|CTO|COO|CFO|Co-founder)\s*[:：/]?\s*([\u4e00-\u9fff]{2,4})',
            r'([\u4e00-\u9fff]{2,4})\s*(?:联合创始人|创始人|CEO|CTO|COO|CFO)',
        ]:
            values.extend(re.findall(pattern, text))
        cleaned = []
        for value in values:
            value = self._clean_candidate(value)
            if not value or value in BAD_GENERIC_PERSON_TOKENS:
                continue
            cleaned.append(value)
        return self._dedupe(cleaned)

    def _extract_team_members(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        if self._looks_like_external_executive_quote(text):
            return []
        values = self._role_exact_matches(text)
        if values:
            return values
        values = []
        for role, name in re.findall(r'(CEO|CTO|COO|CFO|CMO|联合创始人|创始人)\s*(?:Co-founder)?\s*([\u4e00-\u9fff]{2,4})', text):
            values.append(f'{role} {name}')
        return self._dedupe(values) or self._extract_people(text, _, item)

    def _extract_financing_rounds(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values: list[str] = []
        for keyword in ROUND_KEYWORDS:
            if keyword in text:
                values.append(keyword.replace('Pre A', 'Pre-A'))
        return self._dedupe(values)

    def _extract_financing_history(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        cleaned_text = self._clean_text(text)
        if cleaned_text.count('|') >= 4 or '未融资' in cleaned_text:
            return []
        if sum(1 for _ in re.finditer(r'(?:19|20)\d{2}[-/.年](?:0?[1-9]|1[0-2])(?:[-/.月](?:0?[1-9]|[12]\d|3[01]))?', cleaned_text)) >= 3:
            return []
        values: list[str] = []
        label_hits = re.findall(r'(?:融资历史|历史融资情况|历史融资|融资情况)[:：]?\s*([^。；;\n]{6,120})', cleaned_text)
        values.extend(label_hits)
        for sentence in self._split_sentences(cleaned_text):
            if any(token in sentence for token in ['融资', '投资方', '交易时间', '交易金额']) and any(token in sentence for token in ROUND_KEYWORDS + ['投资方', '金额', '基金']):
                values.append(sentence)
        cleaned_values = []
        for value in values:
            value = self._clean_candidate(value)
            if not value:
                continue
            if value in FINANCING_HEADER_VALUES or re.fullmatch(r'(融资历史|历史融资|融资情况)\s*\d*', value):
                continue
            if '|' in value or '未融资' in value:
                continue
            if not any(token in value for token in ROUND_KEYWORDS + ['投资方', '基金', '融资', '金额', '轮']):
                continue
            cleaned_values.append(value)
        return self._dedupe(cleaned_values[:4])

    def _extract_main_product_or_service(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values: list[str] = []
        values.extend([token for token in self._extract_product_names(text, _, item) if len(token) >= 3])
        labeled_values = re.findall(r'(?:主营产品|主营业务|核心产品|产品矩阵|解决方案|产品形态)[:：]?\s*([^。；;\n]{3,120})', text)
        for value in labeled_values:
            for part in re.split(TARGET_SPLIT_TOKENS, value):
                part = self._clean_candidate(part)
                if part:
                    values.append(part)
        for sentence in self._split_sentences(text):
            if 'Phase' in sentence or 'Demo' in sentence or self._looks_like_spec_sentence(sentence):
                continue
            if sum(1 for term in PRODUCT_KEY_TERMS if term in sentence) < 1:
                continue
            if any(label in sentence for label in MAIN_PRODUCT_LABELS) or sum(1 for term in PRODUCT_KEY_TERMS if term in sentence) >= 2:
                for part in re.split(TARGET_SPLIT_TOKENS, sentence):
                    part = self._clean_candidate(part)
                    if part:
                        values.append(part)
        cleaned=[]
        for value in values:
            value = self._clean_candidate(value)
            if not value:
                continue
            if value in BAD_COMPANY_NAME_VALUES or not self._is_product_service_phrase(value):
                continue
            cleaned.append(value)
        prioritized = sorted(self._dedupe(cleaned), key=self._product_value_priority, reverse=True)
        return prioritized[:4]

    def _extract_links(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        compact = re.sub(r'\s+', '', text)
        pattern = r'((?:https?://|www\.)[^\s，。；;]+|[A-Za-z0-9.-]+\.(?:com|cn|ai|io|net)(?:/[^\s，。；;]*)?)'
        values = re.findall(pattern, compact)
        if not values and any(label in text for label in WEBSITE_LABELS):
            labeled = re.findall(r'(?:官网|公司官网|官方网站|网站|产品链接)[:：]?\s*([^，。；;\s]{4,80})', compact)
            values.extend(labeled)
        if not values and 'tactop' in compact.lower():
            values.extend(re.findall(r'([A-Za-z0-9.-]+\.(?:com|cn|ai|io|net)/?[^\s，。；;]*)', compact))
        return self._dedupe(values)

    def _extract_customer_types(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values = [keyword for keyword in CUSTOMER_KEYWORDS if keyword in text]
        values.extend(re.findall(r'(?:面向|应用于|适用于|客户为|目标客户|典型应用场景)[:：]?\s*([^。\n]{2,80})', text))
        values.extend(re.findall(r'[•·]\s*([\u4e00-\u9fffA-Za-z]{2,20})', text))
        cleaned = []
        for value in values:
            value = self._clean_candidate(value)
            if not value:
                continue
            for part in re.split(TARGET_SPLIT_TOKENS, value):
                part = self._clean_candidate(part)
                if not part:
                    continue
                part = part.lstrip('•· ')
                if any(token in part for token in ['原理', '结构', '分辨率', '图像', 'Full Scale']):
                    continue
                cleaned.append(part)
        return self._dedupe(cleaned)

    def _extract_track_labels(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values = [keyword for keyword in TRACK_KEYWORDS + TRACK_HINTS if keyword in text]
        values.extend(re.findall(r'(?:赛道|行业方向|应用环节|市场方向|应用方向)[:：]?\s*([^，。；;]{2,40})', text))
        cleaned = []
        for value in values:
            value = self._clean_candidate(value)
            if not value:
                continue
            for part in re.split(TARGET_SPLIT_TOKENS, value):
                part = self._clean_candidate(part)
                if not part:
                    continue
                if any(token in part for token in ['原理', '结构', '问题']):
                    continue
                cleaned.append(part)
        return self._dedupe(cleaned)

    def _extract_background_summary(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        if not self._looks_like_team_profile(text):
            return []
        founder_block = self._extract_primary_founder_block(text)
        if not founder_block:
            return []
        clauses = self._split_profile_clauses(founder_block)
        values = self._extract_background_fragments(founder_block)
        values.extend([clause for clause in clauses if any(token in clause for token in BACKGROUND_MARKERS)])
        cleaned = []
        for value in values:
            value = self._clean_candidate(value)
            if not value or self._looks_like_spec_sentence(value):
                continue
            if any(token in value for token in ['应用：', '原理：', '结构：']):
                continue
            if '副教授' in value or (re.search(r'(?:教授|研究员)\s*$', value) and not value.startswith('师从')):
                continue
            cleaned.append(value)
        cleaned = self._dedupe(cleaned[:4])
        return ['；'.join(cleaned)] if cleaned else []

    def _extract_prior_experience(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        if not self._looks_like_team_profile(text):
            return []
        founder_block = self._extract_primary_founder_block(text)
        if not founder_block:
            return []
        clauses = self._split_profile_clauses(founder_block)
        values = self._extract_career_fragments(founder_block)
        values.extend([
            clause for clause in clauses
            if any(token in clause for token in ['曾任', '曾在', '历任', '联合创始人', '前CTO', '负责人', '领导经验', '创业', '从业', '任职'])
            or (any(token in clause for token in ['副教授', '教授', '研究员', '主任研究员']) and not any(bg in clause for bg in ['博士', '硕士', '毕业于', '师从', '研究方向']))
        ])
        cleaned = []
        for value in values:
            value = self._clean_candidate(value)
            if not value or self._looks_like_spec_sentence(value):
                continue
            if any(token in value for token in ['应用：', '原理：', '结构：']):
                continue
            if any(token in value for token in ['博士', '硕士', '本科毕业于', '毕业于', '师从', '研究方向']) and not any(job in value for job in ['副教授', '教授', '研究员', '负责人', '领导经验']):
                continue
            cleaned.append(value)
        cleaned = self._dedupe(cleaned[:4])
        return ['；'.join(cleaned)] if cleaned else []

    def _extract_problem_summary(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        sentences = self._split_sentences(text)
        values = [sentence for sentence in sentences if any(token in sentence for token in ['痛点', '问题', '需要', '抗干扰', '实时性', '功耗', '体积', '应用'])]
        cleaned = []
        for value in values:
            value = self._clean_candidate(value)
            if value and not value.startswith('原理'):
                cleaned.append(value)
        return self._dedupe(cleaned[:3])

    def _extract_product_form(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        has_hardware = any(keyword in text for keyword in PRODUCT_FORM_PATTERNS['硬件'])
        has_software = any(keyword in text for keyword in PRODUCT_FORM_PATTERNS['软件'])
        has_api = any(keyword in text for keyword in PRODUCT_FORM_PATTERNS['API'])
        has_explicit_integrated = any(keyword in text for keyword in PRODUCT_FORM_PATTERNS['软硬一体'])
        has_solution_like = any(keyword in text for keyword in ['解决方案', '系统'])

        if has_explicit_integrated or (has_hardware and has_software) or (has_hardware and has_solution_like):
            return ['软硬一体']
        if has_hardware:
            return ['硬件']
        if has_software:
            return ['软件']
        if has_api:
            return ['API']
        return []

    def _extract_technical_route(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values = [keyword for keyword in TECH_ROUTE_KEYWORDS if keyword in text]
        return self._dedupe(values)

    def _extract_pricing_model(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        if not any(token in text for token in COMMERCIAL_CUES):
            return []
        if any(token in text for token in ['光学式', '压阻式', '电容式', '压电式']) and not any(token in text for token in ['收费', '报价', '收入', '合同', '销售', '售价']):
            return []
        values: list[str] = []
        for label, keywords in PRICING_PATTERNS.items():
            if any(keyword in text for keyword in keywords):
                values.append(label)
        return self._dedupe(values)

    def _extract_revenue_structure(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        if not any(token in text for token in COMMERCIAL_CUES):
            return []
        sentences = self._split_sentences(text)
        values = [sentence for sentence in sentences if any(token in sentence for token in ['收入', '收费', '销售', '交付', '回款', '报价'])]
        cleaned = [self._clean_candidate(v) for v in values if self._clean_candidate(v)]
        return self._dedupe(cleaned[:3])

    def _extract_competitors(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values: list[str] = []
        values.extend(re.findall(r'(?:与|相比|对比)([\u4e00-\u9fffA-Za-z0-9、，, ]{2,40})', text))
        values.extend(re.findall(r'([A-Z][A-Za-z0-9]{2,})', text))
        for token in ['相机式', '电容式', '压阻式', '压电式', '光纤式', '客户自研']:
            if token in text:
                values.append(token)
        cleaned: list[str] = []
        for value in values:
            value = self._clean_candidate(value)
            if not value:
                continue
            if any(term in value for term in ['score', 'raw', 'CEO', 'CTO', 'BOM', 'Confidential']):
                continue
            cleaned.append(value)
        return self._dedupe(cleaned[:6])

    def _extract_use_of_funds(self, text: str, _: str, item: EvidenceItem) -> list[str]:
        values = [keyword for keyword in USE_OF_FUNDS_KEYWORDS if keyword in text]
        values.extend(re.findall(r'(?:资金用途|用于|预算)[:：]?\s*([^，。；;]{2,30})', text))
        return self._dedupe(values)

    def _extract_generic_summary(self, text: str, field_key: str, item: EvidenceItem) -> list[str]:
        sentences = self._split_sentences(text)
        return sentences[:3]


def render_fact_markdown(payload: dict) -> str:
    lines: list[str] = []
    lines.append('# Fact 字段处理结果\n')
    lines.append(f"- module_count: {payload['metadata'].get('module_count', 0)}")
    lines.append(f"- fact_field_count: {payload['metadata'].get('fact_field_count', 0)}\n")
    for module in payload['modules']:
        lines.append(f"## {module['module_name']}\n")
        for field in module['field_results']:
            lines.append(f"### {field['field_name']}")
            lines.append(f"- final_status: {field['final_status']}")
            lines.append(f"- final_value: {field['final_value']}")
            if field.get('normalized_value'):
                lines.append(f"- normalized_value: {field['normalized_value']}")
            lines.append(f"- processor_summary: {field['processor_summary']}")
            if field.get('conflict_detected'):
                lines.append(f"- conflict_values: {'；'.join(field.get('conflict_values', []))}")
            if field.get('gap_reasons'):
                lines.append('- gap_reasons:')
                for gap in field['gap_reasons']:
                    lines.append(f'  - {gap}')
            if field.get('selected_evidence'):
                lines.append('- selected_evidence:')
                for item in field['selected_evidence']:
                    lines.append(
                        f"  - {item['document_name']}，{item['locator_type']}={item['locator_value']}，score={item['score']}：{item['text'][:140]}"
                    )
            if field.get('extracted_candidates'):
                lines.append('- extracted_candidates:')
                for candidate in field['extracted_candidates'][:5]:
                    lines.append(
                        f"  - {candidate['raw_value']} => {candidate['normalized_value']} ({candidate['method']}, conf={candidate['confidence']})"
                    )
            lines.append('')
    return '\n'.join(lines) + '\n'


def load_field_evidence_result(path: str) -> FieldEvidenceBuildResult:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    raise NotImplementedError('当前版本未实现从 JSON 回读 dataclass，请直接在脚本侧串联 evidence builder 与 fact processor。')
