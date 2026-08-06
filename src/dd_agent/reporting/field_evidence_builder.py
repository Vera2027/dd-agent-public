from __future__ import annotations

from collections import Counter, defaultdict
import math
import re

from dd_agent.kb.index import LocalKnowledgeBase
from dd_agent.reporting.models import (
    EvidenceItem,
    FieldEvidenceBuildResult,
    FieldEvidencePack,
    FieldSpec,
    ModuleFieldEvidenceBundle,
    ModuleSpec,
)
from dd_agent.reporting.module_specs import MODULE_SPECS

SCHEMA_TERMS = {
    '模块名称', '字段名', 'field_type', 'value_source', 'value_kind', 'allowed_status', 'validation_rule',
    '核心结论', '证据出处', '证据依据', '信息缺失项', '初步判断', '模块目标', '字段内容',
    '固定提示词', '缺失项强制检查', '项目基础信息', '团队判断', '产品与技术', '市场分析',
    '商业模式', '竞争格局', '融资与资本信息', '风险识别', '追问清单', '报告总表头',
}

REFERENCE_DOC_RATIO_THRESHOLD = 0.20


FIELD_FALLBACK_QUERIES = {
    'company_name': ['Business Plan', 'BP', '公司名称', '企业名称', '项目名称'],
    'brand_or_product_name': ['产品名称', '品牌名称', '核心产品', '产品矩阵'],
    'founders': ['CEO Co-founder', 'CTO Co-founder', '团队'],
    'core_team_members': ['CEO Co-founder', 'CTO Co-founder', 'COO', '团队'],
    'founder_background': ['CEO Co-founder', '创始人', 'CEO', '创始人简历', '研究方向', '师从'],
    'founder_prior_experience': ['CEO Co-founder', '创始人', 'CEO', '创始人简历', '曾任', '历任', '创业经历'],
    'payer': ['收费', '报价', '合同'],
    'pricing_model': ['收费', '报价', '合同', '收入'],
    'revenue_structure': ['收入', '营收', '报价', '合同'],
    'market_track': ['机器人', '柔性电子', '触觉传感器'],
    'market_target_customer': ['工业场景', '机器人', '消费电子'],
    'target_customer_type': ['工业场景', '机器人', '消费电子'],
    'market_drivers': ['市场', '客户', '需求', '采购'],
    'market_barriers': ['客户', '预算', '采购', '导入'],
    'market_timing': ['市场', '订单', '采购', '试点'],
    'establishment_date': ['成立日期', '成立时间', '创立于', '注册成立'],
    'registered_or_main_location': ['主要经营地', '经营地', '注册地址', '办公地址'],
    'main_product_or_service': ['主营产品', '核心产品', '产品矩阵', '解决方案', '传感器'],
    'official_website_or_product_link': ['官网', '公司官网', '网站', '产品链接', 'www', 'http'],
    'track_label': ['赛道', '行业方向', '机器人', '触觉传感器', '柔性电子', '具身机器人'],
    'main_competitors': ['竞品', '对比', '相机式', '电容式', '压阻式', '替代方案'],
    'competitor_types': ['创业公司', '相机式', '电容式', '压阻式', '客户自研'],
    'differentiation': ['差异化', '低成本', 'BOM', '抗EMI', '抗干扰', '实时性'],
    'financing_history': ['融资历史', '历史融资', '战略投资', '天使轮', 'Pre-A', '投资方'],
    'financing_history_detail': ['融资历史', '历史融资', '战略投资', '天使轮', 'Pre-A', '投资方'],
}




FIELD_DOMAIN_PREFERENCES = {
    'company_name': {'preferred': {'bp'}, 'disfavored': {'technical', 'qa', 'financing', 'other'}},
    'registered_or_main_location': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa'}},
    'establishment_date': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa'}},
    'brand_or_product_name': {'preferred': {'bp', 'note', 'technical'}, 'disfavored': {'qa'}},
    'main_product_or_service': {'preferred': {'bp', 'technical', 'note'}, 'disfavored': {'qa'}},
    'official_website_or_product_link': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa'}},
    'track_label': {'preferred': {'bp', 'note', 'technical'}, 'disfavored': {'qa'}},
    'founders': {'preferred': {'bp'}, 'disfavored': {'technical', 'qa', 'financing', 'note', 'other'}},
    'core_team_members': {'preferred': {'bp'}, 'disfavored': {'technical', 'qa', 'financing', 'note', 'other'}},
    'founder_background': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa', 'financing'}},
    'founder_prior_experience': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa', 'financing'}},
    'team_capability_fit': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa', 'financing'}},
    'org_gap_filling_status': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa', 'financing'}},
    'team_risk': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa', 'financing'}},
    'payer': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'pricing_model': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'revenue_structure': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'ticket_size_and_collection': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'delivery_and_scaling_logic': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'margin_and_cost_structure': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'business_model_risk': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'investor_structure': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'valuation_clues': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'capital_value_add': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'capital_risk': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa'}},
    'main_competitors': {'preferred': {'bp', 'technical', 'note'}, 'disfavored': {'qa'}},
    'competitor_types': {'preferred': {'bp', 'technical', 'note'}, 'disfavored': {'qa'}},
    'differentiation': {'preferred': {'bp', 'technical', 'note'}, 'disfavored': {'qa'}},
    'competitive_advantages': {'preferred': {'bp', 'technical', 'note'}, 'disfavored': {'qa'}},
    'competitive_disadvantages': {'preferred': {'bp', 'technical', 'note'}, 'disfavored': {'qa'}},
    'entry_barriers': {'preferred': {'bp', 'technical', 'note'}, 'disfavored': {'qa'}},
    'market_track': {'preferred': {'bp', 'note'}, 'disfavored': {'qa'}},
    'market_target_customer': {'preferred': {'bp', 'note'}, 'disfavored': {'qa'}},
    'target_customer_type': {'preferred': {'bp', 'note'}, 'disfavored': {'qa'}},
    'current_financing_round': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa', 'note', 'other'}},
    'financing_history': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa', 'note', 'other'}},
    'financing_history_detail': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa', 'note', 'other'}},
    'use_of_funds': {'preferred': {'bp', 'financing'}, 'disfavored': {'technical', 'qa', 'note', 'other'}},
    'market_drivers': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa'}},
    'market_barriers': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa'}},
    'market_timing': {'preferred': {'bp', 'note'}, 'disfavored': {'technical', 'qa'}},
}


class FieldEvidencePackBuilder:
    def __init__(self, kb: LocalKnowledgeBase) -> None:
        self.kb = kb
        self._doc_profiles = self._build_document_profiles()

    def build_all(self, *, top_k_per_query: int = 8, final_top_k: int = 5) -> FieldEvidenceBuildResult:
        modules: list[ModuleFieldEvidenceBundle] = []
        for spec in MODULE_SPECS:
            modules.append(self.build_module(spec, top_k_per_query=top_k_per_query, final_top_k=final_top_k))
        return FieldEvidenceBuildResult(
            modules=modules,
            metadata={
                'module_count': len(modules),
                'document_names': sorted({chunk.document_name for chunk in self.kb.chunks}),
                'chunk_count': len(self.kb.chunks),
                'builder_mode': 'field_evidence_pack_v1',
                'reference_like_documents': [
                    name for name, profile in self._doc_profiles.items() if profile['is_reference_like']
                ],
            },
        )

    def build_module(self, spec: ModuleSpec, *, top_k_per_query: int = 8, final_top_k: int = 5) -> ModuleFieldEvidenceBundle:
        field_packs = [
            self.build_field_pack(field, top_k_per_query=top_k_per_query, final_top_k=final_top_k)
            for field in spec.fields
        ]
        return ModuleFieldEvidenceBundle(
            module_name=spec.module_name,
            field_packs=field_packs,
            module_gap_hints=spec.gap_hints,
        )

    def build_field_pack(self, field: FieldSpec, *, top_k_per_query: int = 8, final_top_k: int = 5) -> FieldEvidencePack:
        query_groups = field.query_groups or [field.field_name]
        all_queries = list(dict.fromkeys(query_groups + self._fallback_queries(field)))
        aggregated: dict[str, dict] = {}
        query_hits: defaultdict[str, set[str]] = defaultdict(set)
        raw_hit_counter: Counter[str] = Counter()

        for query in all_queries:
            results = self.kb.search(query, top_k=top_k_per_query)
            for rank, result in enumerate(results, start=1):
                profile = self._doc_profiles.get(result.document_name, {})
                effective_score = self._effective_score(
                    raw_score=float(result.score),
                    result_text=result.text,
                    field=field,
                    query=query,
                    rank=rank,
                    is_reference_like=bool(profile.get('is_reference_like')),
                    document_name=result.document_name,
                    locator_type=result.locator_type,
                    locator_value=int(result.locator_value),
                )
                raw_hit_counter[result.chunk_id] += 1
                query_hits[result.chunk_id].add(query)
                payload = aggregated.setdefault(
                    result.chunk_id,
                    {
                        'result': result,
                        'best_score': -math.inf,
                        'raw_max_score': 0.0,
                        'reasons': set(),
                    },
                )
                payload['raw_max_score'] = max(payload['raw_max_score'], float(result.score))
                payload['best_score'] = max(payload['best_score'], effective_score)
                if self._is_schema_like_text(result.text):
                    payload['reasons'].add('命中内容疑似模板/字段标签')
                if profile.get('is_reference_like'):
                    payload['reasons'].add('来源文档疑似系统定义/模板参考文档')
                if self._looks_like_field_label(result.text, field.field_name):
                    payload['reasons'].add('命中内容更像字段标签而非字段取值')

        ranked_payloads = sorted(
            aggregated.values(),
            key=lambda item: (item['best_score'], item['raw_max_score'], len(query_hits[item['result'].chunk_id])),
            reverse=True,
        )

        selected: list[EvidenceItem] = []
        for item in ranked_payloads:
            if len(selected) >= final_top_k:
                break
            result = item['result']
            if item['best_score'] <= 0.01:
                continue
            selected.append(
                EvidenceItem(
                    chunk_id=result.chunk_id,
                    score=round(float(item['best_score']), 6),
                    document_name=result.document_name,
                    locator_type=result.locator_type,
                    locator_value=int(result.locator_value),
                    text=result.text,
                    support=f'支持字段“{field.field_name}”的候选证据',
                    metadata={
                        **result.metadata,
                        'raw_score': round(float(item['raw_max_score']), 6),
                        'matched_queries': sorted(query_hits[result.chunk_id]),
                        'query_hit_count': len(query_hits[result.chunk_id]),
                        'retrieval_notes': sorted(item['reasons']),
                    },
                )
            )

        provisional_status, gap_reasons = self._judge_provisional_status(field, selected, query_groups)
        retrieval_summary = self._build_retrieval_summary(field, selected, provisional_status)
        return FieldEvidencePack(
            field_name=field.field_name,
            field_key=field.field_key,
            field_type=field.field_type,
            query_groups=query_groups,
            priority_sources=field.priority_sources,
            evidence=selected,
            provisional_status=provisional_status,
            retrieval_summary=retrieval_summary,
            gap_reasons=gap_reasons,
        )

    def _build_document_profiles(self) -> dict[str, dict]:
        counts: Counter[str] = Counter()
        schema_counts: Counter[str] = Counter()
        for chunk in self.kb.chunks:
            counts[chunk.document_name] += 1
            if self._is_schema_like_text(chunk.text):
                schema_counts[chunk.document_name] += 1

        profiles: dict[str, dict] = {}
        for document_name, total in counts.items():
            ratio = schema_counts[document_name] / total if total else 0.0
            profiles[document_name] = {
                'total_chunk_count': total,
                'schema_like_chunk_count': schema_counts[document_name],
                'schema_like_ratio': round(ratio, 4),
                'is_reference_like': ratio >= REFERENCE_DOC_RATIO_THRESHOLD,
            }
        return profiles

    def _effective_score(
        self,
        *,
        raw_score: float,
        result_text: str,
        field: FieldSpec,
        query: str,
        rank: int,
        is_reference_like: bool,
        document_name: str,
        locator_type: str,
        locator_value: int,
    ) -> float:
        score = raw_score
        if is_reference_like:
            score -= 0.25
        if self._is_schema_like_text(result_text):
            score -= 0.25
        if self._looks_like_field_label(result_text, field.field_name):
            score -= 0.35
        query_terms = [token for token in re.split(r'[\s/、，,]+', query) if token]
        match_bonus = sum(0.015 for token in query_terms if len(token) >= 2 and token in result_text)
        score += min(match_bonus, 0.08)
        score += max(0.0, 0.03 - 0.003 * (rank - 1))

        domain = self._document_domain(document_name)
        pref = FIELD_DOMAIN_PREFERENCES.get(field.field_key)
        if pref:
            if domain in pref.get('preferred', set()):
                score += 0.08
            if domain in pref.get('disfavored', set()):
                score -= 0.14

        if field.field_key in {'company_name', 'founders', 'core_team_members', 'founder_background', 'founder_prior_experience'}:
            if 'Co-founder' in result_text or 'CEO' in result_text or 'CTO' in result_text or '团队' in result_text:
                score += 0.16
            if result_text.startswith('应用：') or result_text.startswith('结构：') or '工业场景' in result_text:
                score -= 0.16
        if field.field_key in {'founder_background', 'founder_prior_experience'}:
            if any(token in result_text for token in ['师从', '毕业于', '研究方向', '博士', '副教授', '成员', '联合创始人', '前CTO']):
                score += 0.12
            if 'CEO' in result_text or ('创始人' in result_text and '联合创始人' not in result_text):
                score += 0.12
            if any(token in result_text for token in ['CTO', 'COO', 'CFO', 'CMO']) and 'CEO' not in result_text and ('创始人' not in result_text or '联合创始人' in result_text):
                score -= 0.18
            if any(token in result_text for token in ['BOM', 'Demo', 'mm3', 'Full Scale', '传感器']) and '毕业于' not in result_text and '师从' not in result_text:
                score -= 0.18
        if field.field_key in {'team_capability_fit', 'org_gap_filling_status', 'team_risk'}:
            if not any(token in result_text for token in ['CEO', 'CTO', 'COO', '团队', '创始人', '联合创始人', '师从', '毕业于', '分工', '岗位', '招聘']):
                score -= 0.35
            if any(token in result_text for token in ['BOM', 'Demo', 'mm3', 'Full Scale', '传感器', '光学式']) and not any(token in result_text for token in ['团队', '创始人', '岗位', '分工', '销售', '交付', '运营']):
                score -= 0.25
            if locator_type == 'page' and 8 <= locator_value <= 18 and domain == 'bp':
                score += 0.06
        if field.field_key in {'payer', 'pricing_model', 'revenue_structure', 'ticket_size_and_collection', 'delivery_and_scaling_logic', 'business_model_risk'}:
            if any(token in result_text for token in ['光学式', '压阻式', '电容式', '压电式']) and not any(token in result_text for token in ['收费', '收入', '报价', '合同', '销售', '售价']):
                score -= 0.18
            if not any(token in result_text for token in ['收费', '收入', '报价', '合同', '销售', '采购', '回款']):
                score -= 0.24
        if field.field_key in {'market_drivers', 'market_barriers', 'market_timing'}:
            if any(token in result_text for token in ['原理：', '结构：', 'Vcc', 'FSR', '图像']) and not any(token in result_text for token in ['客户', '预算', '采购', '需求', '订单', '试点', '场景', '机器人', '工业']):
                score -= 0.18
            if not any(token in result_text for token in ['客户', '预算', '采购', '需求', '订单', '试点', '场景', '机器人', '工业']):
                score -= 0.22
            if any(token in result_text for token in ['中国青年网', '实施意见', '指南']) and field.field_key != 'market_drivers':
                score -= 0.12
        if field.field_key == 'registered_or_main_location':
            if '皮肤' in result_text or '硅胶' in result_text or '结构' in result_text:
                score -= 0.20
            if any(token in result_text for token in ['大学', '社区', '实验室']):
                score -= 0.14

        if field.field_key in {'company_name', 'establishment_date', 'registered_or_main_location', 'main_product_or_service', 'official_website_or_product_link', 'track_label', 'brand_or_product_name', 'founder_background', 'founder_prior_experience', 'team_capability_fit'}:
            if domain == 'bp':
                score += 0.12
            if locator_type == 'page' and locator_value <= 3:
                score += 0.05

        if field.field_key == 'company_name':
            if any(token in result_text for token in ['公司名称', '企业名称', '项目名称']):
                score += 0.22
            if any(token in result_text for token in ['企业信息', '基本信息', '公司信息']) and not any(token in result_text for token in ['公司名称', '企业名称']):
                score -= 0.30

        if field.field_key == 'establishment_date':
            if any(token in result_text for token in ['成立日期', '成立时间', '创立于', '注册成立', '公司成立']):
                score += 0.22

        if field.field_key == 'registered_or_main_location':
            if any(token in result_text for token in ['主要经营地', '经营地']):
                score += 0.28
            elif any(token in result_text for token in ['经营地址', '办公地址', '总部位于']):
                score += 0.16
            elif any(token in result_text for token in ['注册地址', '注册地']):
                score += 0.10
            elif re.search(r'[一-鿿]{2,6}(?:市|区|县)$', result_text.strip()):
                score -= 0.12

        if field.field_key == 'main_product_or_service':
            if any(token in result_text for token in ['主营产品', '主营业务', '核心产品', '产品矩阵', '解决方案']):
                score += 0.22
            if any(token in result_text for token in ['传感器', '阵列', '电子皮肤', '平台']) and domain in {'bp', 'technical'}:
                score += 0.08

        if field.field_key == 'official_website_or_product_link':
            if any(token in result_text for token in ['官网', '公司官网', '网站', '产品链接']):
                score += 0.18
            if re.search(r'(https?://|www\.|[A-Za-z0-9.-]+\.(?:com|cn|ai|io|net))', result_text):
                score += 0.20

        if field.field_key in {'track_label', 'market_track'}:
            if any(token in result_text for token in ['赛道', '行业方向', '应用方向', '机器人', '触觉', '柔性电子', '具身']):
                score += 0.14

        if field.field_key == 'brand_or_product_name':
            if any(token in result_text for token in ['产品名称', '品牌名称', '核心产品', '产品矩阵']):
                score += 0.20
            if domain == 'bp':
                score += 0.08

        if field.field_key in {'current_financing_round', 'financing_history', 'financing_history_detail', 'use_of_funds'}:
            if any(token in result_text for token in ['交易轮次', '投资方', '融资历史', '融资情况', '资金用途', '本轮融资']) and domain in {'bp', 'financing'}:
                score += 0.16
            if result_text.count('|') >= 4 or '未融资' in result_text:
                score -= 0.35
            if sum(1 for _ in re.finditer(r'(?:19|20)\d{2}[-/.年](?:0?[1-9]|1[0-2])(?:[-/.月](?:0?[1-9]|[12]\d|3[01]))?', result_text)) >= 3:
                score -= 0.18
            if any(token in result_text for token in ['合肥市', '北京市', '杭州市', '苏州市']) and domain != 'bp':
                score -= 0.18

        if field.field_key in {'main_competitors', 'competitor_types', 'differentiation', 'competitive_advantages', 'competitive_disadvantages', 'entry_barriers'}:
            if any(token in result_text for token in ['竞品', '对比', '相机式', '电容式', '压阻式', '替代方案', 'BOM', '抗EMI', '抗干扰', '实时性']):
                score += 0.14

        return score


    def _augment_selected_evidence(self, field: FieldSpec, selected: list[EvidenceItem], *, final_top_k: int) -> list[EvidenceItem]:
        if not selected:
            return selected
        if field.field_key not in {'financing_history', 'financing_history_detail', 'current_financing_round', 'use_of_funds'}:
            return selected
        if any(self._looks_like_financing_payload(item.text) for item in selected):
            return selected[:final_top_k]

        existing_ids = {item.chunk_id for item in selected}
        financing_docs = {item.document_name for item in selected if self._document_domain(item.document_name) == 'financing'}
        if not financing_docs:
            financing_docs = {chunk.document_name for chunk in self.kb.chunks if self._document_domain(chunk.document_name) == 'financing'}

        augmented = list(selected)
        for chunk in self.kb.chunks:
            if chunk.document_name not in financing_docs or chunk.chunk_id in existing_ids:
                continue
            text = chunk.text
            if not self._looks_like_financing_payload(text):
                continue
            augmented.append(
                EvidenceItem(
                    chunk_id=chunk.chunk_id,
                    score=0.24,
                    document_name=chunk.document_name,
                    file_type=chunk.file_type,
                    locator_type=chunk.locator_type,
                    locator_value=int(chunk.locator_value),
                    text=text,
                    support=f'支持字段“{field.field_name}”的候选证据',
                    metadata={**chunk.metadata, 'retrieval_notes': ['基于融资文档结构化行自动补充相邻证据']},
                )
            )
            existing_ids.add(chunk.chunk_id)
            if len(augmented) >= final_top_k:
                break
        return augmented[:final_top_k]

    def _looks_like_financing_payload(self, text: str) -> bool:
        normalized = ' '.join(text.split())
        if not normalized:
            return False
        if re.search(r'(?:战略投资|种子轮|天使轮|Pre-A|Pre A|A轮|A\+轮|B轮|B\+轮|C轮)', normalized) and re.search(r'(?:19|20)\d{2}[-/.年](?:0?[1-9]|1[0-2])', normalized):
            return True
        if '\t' in text and re.search(r'(?:战略投资|种子轮|天使轮|Pre-A|Pre A|A轮|A\+轮|B轮|B\+轮|C轮)', text):
            return True
        if '投资方' in normalized and re.search(r'(?:基金|资本|创投|投资)', normalized):
            return True
        return False

    def _judge_provisional_status(
        self,
        field: FieldSpec,
        evidence_items: list[EvidenceItem],
        query_groups: list[str],
    ) -> tuple[str | None, list[str]]:
        if not evidence_items:
            if field.field_type == 'fact':
                return '材料未体现', [f'字段“{field.field_name}”未检索到可用候选证据']
            return '无法判断', [f'字段“{field.field_name}”未检索到可支撑分析的候选证据']

        strongest = evidence_items[0]
        notes = strongest.metadata.get('retrieval_notes', [])
        gap_reasons: list[str] = []
        suspect_count = 0
        usable_count = 0
        strong_usable_count = 0
        for item in evidence_items:
            item_notes = item.metadata.get('retrieval_notes', [])
            is_suspect = any('模板' in note or '字段标签' in note for note in item_notes)
            if is_suspect:
                suspect_count += 1
            else:
                usable_count += 1
                if item.score >= 0.12:
                    strong_usable_count += 1

        if suspect_count == len(evidence_items):
            gap_reasons.append('当前命中几乎全部来自系统定义/模板化内容，说明知识库输入范围可能有污染')
        elif suspect_count > 0:
            gap_reasons.append('部分高分命中来自模板化或字段标签式内容，需在字段处理阶段继续过滤')

        if field.field_type == 'fact':
            if usable_count == 0:
                return '材料未体现', gap_reasons
            if strongest.score < 0.16 or strong_usable_count == 0:
                gap_reasons.append(f'字段“{field.field_name}”当前只有弱相关线索，需后续抽取器进一步判定')
                return '材料提及但信息不足', gap_reasons
            return None, gap_reasons

        if strong_usable_count < 2:
            gap_reasons.append(f'字段“{field.field_name}”可用于综合判断的独立业务证据不足 2 条')
            return '无法判断', gap_reasons
        return None, gap_reasons

    def _build_retrieval_summary(
        self,
        field: FieldSpec,
        evidence_items: list[EvidenceItem],
        provisional_status: str | None,
    ) -> str:
        if not evidence_items:
            return f'字段“{field.field_name}”未命中可用候选证据。'
        doc_names = sorted({item.document_name for item in evidence_items})
        locators = '；'.join(
            f"{item.document_name}:{item.locator_type}={item.locator_value}" for item in evidence_items[:3]
        )
        suffix = f'；当前 provisional_status={provisional_status}' if provisional_status else '；当前可进入下一步字段处理'
        return (
            f'字段“{field.field_name}”共命中 {len(evidence_items)} 条候选证据，覆盖 {len(doc_names)} 份材料，'
            f'优先定位：{locators}{suffix}。'
        )

    def _is_schema_like_text(self, text: str) -> bool:
        normalized = ' '.join(text.split())
        if not normalized:
            return True
        if normalized in SCHEMA_TERMS:
            return True
        if len(normalized) <= 20 and any(term == normalized for term in SCHEMA_TERMS):
            return True
        schema_term_hits = sum(1 for term in SCHEMA_TERMS if term in normalized)
        if schema_term_hits >= 2 and len(normalized) <= 160:
            return True
        if any(marker in normalized for marker in ('field_type', 'value_source', 'allowed_status', 'validation_rule')):
            return True
        if '必须输出' in normalized and '证据出处' in normalized:
            return True
        if '待填写' in normalized and ('核心结论' in normalized or '项目名称' in normalized):
            return True
        return False

    def _looks_like_field_label(self, text: str, field_name: str) -> bool:
        normalized = ' '.join(text.split())
        if normalized == field_name:
            return True
        if normalized.strip('：:') == field_name:
            return True
        if len(normalized) <= 24 and field_name in normalized and not re.search(r'[，。；;：:]', normalized):
            return True
        return False

    def _fallback_queries(self, field: FieldSpec) -> list[str]:
        return FIELD_FALLBACK_QUERIES.get(field.field_key, [])

    def _document_domain(self, document_name: str) -> str:
        name = document_name.lower()
        if 'business plan' in name or 'bp' in name or 'pitch' in name or 'deck' in name or '商业计划书' in document_name or '商业计划' in document_name:
            return 'bp'
        if '融资' in document_name:
            return 'financing'
        if '问题' in document_name or '疑问' in document_name:
            return 'qa'
        if '梳理' in document_name or '纪要' in document_name or '介绍' in document_name or '补充' in document_name or '企业' in document_name or '公司' in document_name:
            return 'note'
        if '传感器' in document_name or '技术' in document_name:
            return 'technical'
        return 'other'
