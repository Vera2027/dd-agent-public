from __future__ import annotations

from dd_agent.reporting.models import FieldSpec
from dd_agent.reporting.module_specs import MODULE_SPECS


VALUE_KIND_OVERRIDES = {
    'brand_or_product_name': 'list[string]',
    'founders': 'list[string]',
    'core_team_members': 'list[string]',
    'target_customer_type': 'list[string]',
    'track_label': 'list[string]',
    'market_track': 'list[string]',
    'market_target_customer': 'list[string]',
    'payer': 'list[string]',
    'pricing_model': 'list[string]',
    'main_competitors': 'list[string]',
    'use_of_funds': 'list[string]',
    'risk_level': 'enum',
    'followup_team': 'list[string]',
    'followup_product_tech': 'list[string]',
    'followup_market': 'list[string]',
    'followup_business_model': 'list[string]',
    'followup_competition': 'list[string]',
    'followup_financing_operation': 'list[string]',
}

MODULE_SYNTHETIC_FIELDS = [
    {'field_name': '核心结论', 'field_key_suffix': 'core_conclusion', 'field_type': 'analysis', 'field_role': 'normal_field', 'value_source': 'generated', 'value_kind': 'string', 'allowed_status': ['无法判断'], 'validation_rule': '模块级总结，证据不足时输出无法判断'},
    {'field_name': '证据出处', 'field_key_suffix': 'evidence', 'field_type': 'analysis', 'field_role': 'evidence_display', 'value_source': 'generated', 'value_kind': 'list[string]', 'allowed_status': ['未检索到直接证据'], 'validation_rule': '若无直接证据，必须明确输出未检索到直接证据'},
    {'field_name': '证据依据', 'field_key_suffix': 'evidence_reasoning', 'field_type': 'analysis', 'field_role': 'evidence_reasoning', 'value_source': 'generated', 'value_kind': 'string', 'allowed_status': ['无法判断'], 'validation_rule': '解释证据如何支撑判断'},
    {'field_name': '信息缺失项', 'field_key_suffix': 'gaps', 'field_type': 'analysis', 'field_role': 'gap_summary', 'value_source': 'generated', 'value_kind': 'list[string]', 'allowed_status': ['无法判断'], 'validation_rule': '模块级缺口汇总，不作为普通字段状态'},
    {'field_name': '初步判断', 'field_key_suffix': 'preliminary_judgment', 'field_type': 'analysis', 'field_role': 'normal_field', 'value_source': 'generated', 'value_kind': 'string', 'allowed_status': ['无法判断'], 'validation_rule': '模块级综合判断'},
]

REPORT_HEADER_FIELDS = [
    {'module_name': '报告总表头', 'field_name': '项目名称', 'field_key': 'project_name', 'field_type': 'fact', 'field_role': 'normal_field', 'value_source': 'extracted', 'value_kind': 'string', 'required': True, 'allowed_status': ['材料未体现'], 'priority_sources': ['BP封面', '项目简介页', '补充说明', '访谈纪要首页'], 'evidence_required': True, 'validation_rule': '不允许输出无法判断'},
    {'module_name': '报告总表头', 'field_name': '报告生成时间', 'field_key': 'report_generated_at', 'field_type': 'fact', 'field_role': 'normal_field', 'value_source': 'system', 'value_kind': 'string', 'required': True, 'allowed_status': [], 'priority_sources': ['系统运行时间'], 'evidence_required': False, 'validation_rule': '系统自动生成，不走模型'},
    {'module_name': '报告总表头', 'field_name': '输入材料清单', 'field_key': 'input_materials', 'field_type': 'fact', 'field_role': 'normal_field', 'value_source': 'system', 'value_kind': 'list[string]', 'required': True, 'allowed_status': [], 'priority_sources': ['当前全部上传文件名', '系统接收记录'], 'evidence_required': False, 'validation_rule': '系统自动汇总，仅列本次上传材料'},
    {'module_name': '报告总表头', 'field_name': '分析边界说明', 'field_key': 'analysis_boundary', 'field_type': 'fact', 'field_role': 'normal_field', 'value_source': 'system', 'value_kind': 'string', 'required': True, 'allowed_status': [], 'priority_sources': ['系统固定文案'], 'evidence_required': False, 'validation_rule': '必须明确仅基于本次上传材料，不调用外部公开来源'},
    {'module_name': '报告总表头', 'field_name': '总体初筛结论', 'field_key': 'overall_screening_conclusion', 'field_type': 'analysis', 'field_role': 'normal_field', 'value_source': 'generated', 'value_kind': 'enum', 'required': True, 'allowed_status': [], 'priority_sources': ['9个模块初步判断', '风险识别', '追问清单'], 'evidence_required': True, 'validation_rule': '仅允许三个固定枚举值'},
    {'module_name': '报告总表头', 'field_name': '总体初筛结论说明', 'field_key': 'overall_screening_reason', 'field_type': 'analysis', 'field_role': 'normal_field', 'value_source': 'generated', 'value_kind': 'string', 'required': True, 'allowed_status': ['无法判断'], 'priority_sources': ['模块核心结论', '风险识别', '信息缺失项'], 'evidence_required': True, 'validation_rule': '自动生成简明说明，不直接输出状态词'},
]


def _spec_to_row(module_name: str, spec: FieldSpec) -> dict:
    return {
        'module_name': module_name,
        'field_name': spec.field_name,
        'field_key': spec.field_key,
        'field_type': spec.field_type,
        'field_role': spec.field_role,
        'value_source': spec.value_source,
        'value_kind': VALUE_KIND_OVERRIDES.get(spec.field_key, spec.value_kind),
        'required': spec.required,
        'allowed_status': list(spec.allowed_status),
        'priority_sources': list(spec.priority_sources),
        'evidence_required': spec.evidence_required,
        'validation_rule': spec.validation_rule,
    }


def build_schema_registry() -> list[dict]:
    rows = list(REPORT_HEADER_FIELDS)
    for module in MODULE_SPECS:
        for spec in module.fields:
            rows.append(_spec_to_row(module.module_name, spec))
        for item in MODULE_SYNTHETIC_FIELDS:
            rows.append({
                'module_name': module.module_name,
                'field_name': item['field_name'],
                'field_key': f"{module.module_name}_{item['field_key_suffix']}",
                'field_type': item['field_type'],
                'field_role': item['field_role'],
                'value_source': item['value_source'],
                'value_kind': item['value_kind'],
                'required': True,
                'allowed_status': list(item['allowed_status']),
                'priority_sources': [],
                'evidence_required': True,
                'validation_rule': item['validation_rule'],
            })
    return rows
