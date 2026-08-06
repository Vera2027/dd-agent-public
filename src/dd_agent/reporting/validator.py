from __future__ import annotations

from dataclasses import dataclass

from dd_agent.reporting.analysis_generator import AnalysisGenerationResult, StructuredReportResult
from dd_agent.reporting.fact_processor import FactProcessingResult
from dd_agent.reporting.module_specs import MODULE_SPECS


OVERALL_ALLOWED = {'建议进入下一轮沟通', '信息不足，建议补充材料后再判断', '存在明显风险，谨慎推进'}
RISK_LEVEL_ALLOWED = {'高', '中', '低'}
FACT_BAD = {'无法判断'}
ANALYSIS_BAD = {'材料提及但信息不足'}
EFFECTIVE_FACT_FALLBACKS = {'材料未体现', '材料提及但信息不足', '需外部核验'}


@dataclass(slots=True)
class ValidationIssue:
    level: str
    scope: str
    message: str

    def to_dict(self) -> dict:
        return {'level': self.level, 'scope': self.scope, 'message': self.message}


@dataclass(slots=True)
class ValidationResult:
    passed: bool
    issues: list[ValidationIssue]

    def to_dict(self) -> dict:
        return {'passed': self.passed, 'issues': [i.to_dict() for i in self.issues]}


class StructuredReportValidator:
    def validate(
        self,
        *,
        fact_result: FactProcessingResult,
        analysis_result: AnalysisGenerationResult,
        report: StructuredReportResult,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        fact_map = {field.field_key: field for module in fact_result.modules for field in module.field_results}
        analysis_map = {field.field_key: field for module in analysis_result.modules for field in module.field_results}
        spec_map = {field.field_key: field for module in MODULE_SPECS for field in module.fields}

        for key, field in fact_map.items():
            spec = spec_map[key]
            if field.final_status in FACT_BAD:
                issues.append(ValidationIssue('error', key, 'fact 字段不得输出 无法判断'))
            if field.final_status not in {'extracted', *spec.allowed_status}:
                issues.append(ValidationIssue('error', key, f'fact 字段状态不合法: {field.final_status}'))
            if spec.evidence_required and field.final_status == 'extracted' and not field.selected_evidence:
                issues.append(ValidationIssue('error', key, 'fact 字段输出有效值时缺少证据'))

        for key, field in analysis_map.items():
            spec = spec_map[key]
            if field.final_status in ANALYSIS_BAD:
                issues.append(ValidationIssue('error', key, 'analysis 字段不得输出 材料提及但信息不足'))
            if field.final_status not in {'generated', *spec.allowed_status}:
                issues.append(ValidationIssue('error', key, f'analysis 字段状态不合法: {field.final_status}'))
            if spec.evidence_required and field.final_status == 'generated' and not field.selected_evidence:
                issues.append(ValidationIssue('error', key, 'analysis 字段输出有效值时缺少证据'))

        if report.overall_screening_conclusion not in OVERALL_ALLOWED:
            issues.append(ValidationIssue('error', 'overall_screening_conclusion', '总体初筛结论超出允许枚举'))
        risk_item = analysis_map.get('risk_level')
        if risk_item and risk_item.final_status == 'generated' and str(risk_item.final_value) not in RISK_LEVEL_ALLOWED:
            issues.append(ValidationIssue('error', 'risk_level', '风险等级仅允许 高 / 中 / 低'))

        for module in report.modules:
            if not module.evidence:
                # report renderer can show placeholder, but metadata should already reflect this as a gap rather than silent success.
                if not any('未检索到直接证据' in gap or '证据' in gap for gap in module.info_gaps):
                    issues.append(ValidationIssue('warning', module.module_name, '模块无直接证据，建议在信息缺失项中显式说明'))

        return ValidationResult(passed=not any(i.level == 'error' for i in issues), issues=issues)
