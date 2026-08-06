from __future__ import annotations

from dd_agent.reporting.models import FieldSpec, ModuleSpec


SYSTEM_FACT_FALLBACK = ['材料未体现', '材料提及但信息不足', '需外部核验']
SYSTEM_ANALYSIS_FALLBACK = ['无法判断']


def _fact(
    field_name: str,
    field_key: str,
    *,
    query_groups: list[str],
    priority_sources: list[str],
    allowed_status: list[str] | None = None,
    evidence_limit: int = 5,
) -> FieldSpec:
    return FieldSpec(
        field_name,
        field_key,
        'fact',
        query_groups=query_groups,
        priority_sources=priority_sources,
        allowed_status=allowed_status or SYSTEM_FACT_FALLBACK,
        evidence_limit=evidence_limit,
        field_role='normal_field',
        value_source='extracted',
        value_kind='string',
        required=True,
        evidence_required=True,
        validation_rule='field_type=fact: only extracted value or legal fact fallback statuses are allowed',
    )


def _analysis(
    field_name: str,
    field_key: str,
    *,
    query_groups: list[str],
    priority_sources: list[str],
    evidence_limit: int = 5,
) -> FieldSpec:
    return FieldSpec(
        field_name,
        field_key,
        'analysis',
        query_groups=query_groups,
        priority_sources=priority_sources,
        allowed_status=SYSTEM_ANALYSIS_FALLBACK,
        evidence_limit=evidence_limit,
        field_role='normal_field',
        value_source='generated',
        value_kind='string',
        required=True,
        evidence_required=True,
        validation_rule='field_type=analysis: only generated value or 无法判断 are allowed',
    )


MODULE_SPECS: list[ModuleSpec] = [
    ModuleSpec(
        module_name='项目基础信息',
        search_queries=['项目名称', '公司名称', '主营产品', '融资轮次', '目标客户', '赛道'],
        fields=[
            _fact('公司名称', 'company_name', query_groups=['项目名称', '公司名称', '企业名称', '公司介绍'], priority_sources=['BP封面', '公司介绍页', '补充说明', '会议纪要'], allowed_status=['材料未体现', '材料提及但信息不足']),
            _fact('品牌名称 / 产品名称', 'brand_or_product_name', query_groups=['品牌名称', '产品名称', '产品', '解决方案'], priority_sources=['BP产品页', '演示材料', '截图文档', '补充说明']),
            _fact('成立时间', 'establishment_date', query_groups=['成立时间', '成立于', '公司成立', '创立时间'], priority_sources=['BP', '创始人资料', '补充说明'], allowed_status=['材料未体现', '需外部核验']),
            _fact('注册地 / 主要经营地', 'registered_or_main_location', query_groups=['注册地', '主要经营地', '总部位于', '公司地址'], priority_sources=['BP', '补充说明', '访谈纪要'], allowed_status=['材料未体现', '材料提及但信息不足', '需外部核验']),
            _fact('创始人', 'founders', query_groups=['创始人', '联合创始人', 'CEO Co-founder', '团队创始'], priority_sources=['BP团队页', '创始人简历'], allowed_status=['材料未体现', '材料提及但信息不足']),
            _fact('核心团队成员', 'core_team_members', query_groups=['核心团队成员', '团队成员', '管理团队', 'CTO COO CEO'], priority_sources=['BP团队页', '简历包', '组织说明'], allowed_status=['材料未体现', '材料提及但信息不足']),
            _fact('当前融资轮次', 'current_financing_round', query_groups=['当前融资轮次', '融资轮次', '天使轮', 'Pre-A'], priority_sources=['BP融资页', '融资补充说明', '会议纪要'], allowed_status=['材料未体现', '需外部核验']),
            _fact('历史融资概况', 'financing_history', query_groups=['历史融资', '融资历史', '交易轮次', '投资方'], priority_sources=['BP融资页', '融资说明文档', '创始人口述纪要']),
            _fact('主营产品 / 服务形态', 'main_product_or_service', query_groups=['主营产品', '服务形态', '产品形态', '解决方案'], priority_sources=['BP产品页', '产品手册', '演示截图', '访谈纪要'], allowed_status=['材料未体现']),
            _fact('官网 / 产品链接', 'official_website_or_product_link', query_groups=['官网', '网站', '链接', '产品链接'], priority_sources=['BP页脚', '补充说明', '截图文档'], allowed_status=['材料未体现']),
            _fact('目标客户类型', 'target_customer_type', query_groups=['目标客户', '客户类型', '适用场景', '应用场景'], priority_sources=['BP市场页', '客户案例页', '销售材料', '访谈纪要']),
            _fact('所属赛道标签', 'track_label', query_groups=['所属赛道', '赛道', '行业方向', '应用环节'], priority_sources=['BP', '项目简介', '创始人表述', '行业分析材料']),
        ],
        gap_hints=['工商主体尚未核验', '产品链接可能缺失', '融资轮次和历史融资可能需要进一步核验'],
    ),
    ModuleSpec(
        module_name='团队判断',
        search_queries=['创始人背景', '团队', '核心成员', '销售负责人', '团队分工'],
        fields=[
            _fact('创始人背景', 'founder_background', query_groups=['创始人背景', 'CEO 创始人', '创始人简历', '创始人 教育背景'], priority_sources=['创始人简历', 'BP团队页', '访谈纪要', '自述材料']),
            _fact('过往创业 / 从业经历', 'founder_prior_experience', query_groups=['创始人 从业经历', '创始人 创业经历', 'CEO 曾任', '过往项目'], priority_sources=['简历', '访谈纪要', '项目经历说明']),
            _analysis('核心团队能力匹配度', 'team_capability_fit', query_groups=['技术 产品 销售 交付 运营 团队', '团队分工', '核心岗位', '行业资源'], priority_sources=['团队简历', '岗位分工说明', '组织介绍']),
            _analysis('组织补位情况', 'org_gap_filling_status', query_groups=['组织补位', '招聘需求', '组织结构', '关键岗位'], priority_sources=['团队结构页', '招聘需求', '访谈纪要']),
            _analysis('潜在团队风险', 'team_risk', query_groups=['团队风险', '核心成员', '分工不清', '关键岗位缺失'], priority_sources=['团队履历', '分工材料', '缺失项', '冲突信息']),
        ],
        gap_hints=['可能缺销售负责人背景', '可能缺团队协作历史', '可能缺组织分工说明'],
    ),
    ModuleSpec(
        module_name='产品与技术',
        search_queries=['产品形态', '技术路径', '技术壁垒', '产品成熟度', '客户案例', '数据闭环'],
        fields=[
            _fact('解决的问题', 'problem_to_solve', query_groups=['解决的问题', '痛点', '核心问题', '应用痛点'], priority_sources=['BP产品页', '访谈纪要', '产品说明书']),
            _fact('产品形态', 'product_form', query_groups=['产品形态', '硬件', '软件', '解决方案'], priority_sources=['产品手册', '演示材料', '系统架构图', '截图文档']),
            _fact('技术路径', 'technical_route', query_groups=['技术路径', '核心技术', '技术方案', '技术架构'], priority_sources=['BP技术页', '技术说明', '架构图', '研发材料']),
            _analysis('技术壁垒', 'technical_barrier', query_groups=['技术壁垒', '核心优势', '专利', '难点'], priority_sources=['技术说明', '客户案例', '效果说明', '研发文档']),
            _analysis('产品成熟度', 'product_maturity', query_groups=['产品成熟度', 'MVP', '试点', '量产'], priority_sources=['试点材料', '客户案例', '版本说明', '交付记录']),
            _analysis('可替代性分析', 'substitutability', query_groups=['替代方案', '可替代性', '客户不用会怎样', '竞品对比'], priority_sources=['创始人说明', '客户反馈纪要', '竞品对比材料']),
        ],
        gap_hints=['可能缺量化技术指标', '可能缺真实客户案例', '可能缺路线图或训练闭环说明'],
    ),
    ModuleSpec(
        module_name='市场分析',
        search_queries=['市场空间', '目标客户', '需求', '预算', '采购流程', '市场时机'],
        fields=[
            _fact('所属赛道', 'market_track', query_groups=['所属赛道', '赛道', '行业方向', '市场方向'], priority_sources=['BP市场页', '项目简介', '创始人说明', '行业分析材料']),
            _fact('目标客户', 'market_target_customer', query_groups=['目标客户', '客户', '采购方', '使用方'], priority_sources=['BP市场页', '客户案例', '销售材料', '访谈纪要']),
            _analysis('核心需求真实性', 'demand_authenticity', query_groups=['客户反馈', '试点纪要', '真实需求', '预算来源'], priority_sources=['客户反馈', '试点纪要', '案例复盘']),
            _analysis('市场空间', 'market_size', query_groups=['市场空间', 'TAM', 'SAM', 'SOM', '市场规模'], priority_sources=['BP市场测算', '行业分析材料', '补充说明']),
            _analysis('市场驱动因素', 'market_drivers', query_groups=['市场驱动因素', '技术成熟', '政策变化', '成本下降'], priority_sources=['市场分析页', '访谈纪要', '项目说明']),
            _analysis('市场阻碍因素', 'market_barriers', query_groups=['市场阻碍因素', '决策链长', '预算冻结', '部署复杂'], priority_sources=['客户反馈', '销售难点记录', '行业分析材料', '补充说明']),
            _analysis('市场进入时机', 'market_timing', query_groups=['市场进入时机', '现在进入', '太早', '太晚'], priority_sources=['市场分析材料', '项目进展材料', '竞品对比材料']),
        ],
        gap_hints=['可能缺一手客户访谈', '可能缺预算来源', '可能缺采购链路', '可能缺统一口径市场测算'],
    ),
    ModuleSpec(
        module_name='商业模式',
        search_queries=['收费方式', '收入结构', '客单价', '回款', '毛利', '交付周期'],
        fields=[
            _fact('收费对象', 'payer', query_groups=['收费对象', '谁付钱', '甲方客户', '终端用户'], priority_sources=['BP商业模式页', '报价单', '合同样本', '访谈纪要']),
            _fact('收费方式', 'pricing_model', query_groups=['收费方式', '项目制', '订阅制', '按调用量计费'], priority_sources=['BP', '报价材料', '合同样本', '产品方案']),
            _fact('收入结构', 'revenue_structure', query_groups=['收入结构', '收入来源', '营收构成', '业务构成'], priority_sources=['财务摘要', '业务说明', '管理层访谈纪要']),
            _analysis('客单价与回款逻辑', 'ticket_size_and_collection', query_groups=['客单价', '回款', '付款周期', '收入确认'], priority_sources=['合同', '报价单', '财务摘要', '访谈纪要']),
            _analysis('交付与扩张逻辑', 'delivery_and_scaling_logic', query_groups=['交付周期', '扩张逻辑', '复制', '实施'], priority_sources=['交付说明', '项目实施资料', '客户案例']),
            _analysis('毛利与成本结构', 'margin_and_cost_structure', query_groups=['毛利', '成本结构', '研发成本', '售后成本'], priority_sources=['财务摘要', '经营说明', '项目复盘材料']),
            _analysis('商业模式风险', 'business_model_risk', query_groups=['商业模式风险', '项目制过重', '回款慢', '高度定制化'], priority_sources=['收入结构', '交付方式', '客户结构', '缺失项综合']),
        ],
        gap_hints=['可能缺真实收入数据', '可能缺续费信息', '可能缺交付周期', '可能缺毛利拆解'],
    ),
    ModuleSpec(
        module_name='竞争格局',
        search_queries=['竞品', '差异化', '竞争优势', '竞争劣势', '替代方案', '中标'],
        fields=[
            _fact('主要竞品', 'main_competitors', query_groups=['主要竞品', '竞品', '替代方案', '对比产品'], priority_sources=['BP竞品页', '内部对比材料', '销售输赢单复盘']),
            _analysis('竞品类型划分', 'competitor_types', query_groups=['竞品类型', '创业公司', '大厂', '客户自研'], priority_sources=['竞品对比材料', '项目说明', '客户替代方案记录']),
            _analysis('差异化定位', 'differentiation', query_groups=['差异化', '定位', '更高精度', '更低成本'], priority_sources=['BP竞品页', '产品说明', '客户反馈']),
            _analysis('竞争优势', 'competitive_advantages', query_groups=['竞争优势', '性能对比', '客户为什么选择', '资源优势'], priority_sources=['客户案例', '性能对比', '资源材料']),
            _analysis('竞争劣势', 'competitive_disadvantages', query_groups=['竞争劣势', '输单原因', '品牌弱', '交付慢'], priority_sources=['输单复盘', '客户反馈', '资源短板说明']),
            _analysis('行业进入壁垒', 'entry_barriers', query_groups=['进入壁垒', '客户切换成本', '交付门槛', '合规要求'], priority_sources=['交付门槛', '技术门槛', '合规要求', '客户嵌入深度材料']),
        ],
        gap_hints=['可能缺竞品实测对比', '可能缺赢单输单原因', '可能缺客户替代路径与选择理由'],
    ),
    ModuleSpec(
        module_name='融资与资本信息',
        search_queries=['融资', '投资方', '估值', '资金用途', '股权结构', '资本风险'],
        fields=[
            _fact('历史融资情况', 'financing_history_detail', query_groups=['历史融资', '融资历史', '交易轮次', '投资方'], priority_sources=['BP融资页', '融资说明', '管理层补充纪要']),
            _analysis('投资方结构', 'investor_structure', query_groups=['投资方结构', '财务投资人', '产业投资人', '政府基金'], priority_sources=['BP融资页', '股东说明', '会议纪要']),
            _analysis('估值区间线索', 'valuation_clues', query_groups=['估值', '估值区间', '可比公司', '市场传闻'], priority_sources=['创始人口述纪要', '融资说明', '可比讨论材料']),
            _fact('资金用途', 'use_of_funds', query_groups=['资金用途', '研发', '市场', '扩产', '团队建设'], priority_sources=['融资用途页', '预算说明', '管理层纪要']),
            _analysis('资本加持价值', 'capital_value_add', query_groups=['资本加持', '资源协同', '渠道支持', '品牌信用'], priority_sources=['融资说明', '资源协同说明', '管理层陈述']),
            _analysis('资本风险', 'capital_risk', query_groups=['资本风险', '融资依赖', '估值虚高', '下一轮融资'], priority_sources=['融资节奏', '资金用途', '后续融资计划材料']),
        ],
        gap_hints=['可能缺融资金额', '可能缺股权结构', '可能缺估值区间', '可能缺资金消耗情况'],
    ),
    ModuleSpec(
        module_name='风险识别',
        search_queries=['风险', '合规', '技术风险', '商业化风险', '市场风险', '现金流'],
        fields=[
            _analysis('政策风险', 'policy_risk', query_groups=['政策风险', '监管', '牌照', '合规边界'], priority_sources=['合规说明', '业务边界说明', '客户要求记录']),
            _analysis('技术风险', 'technical_risk', query_groups=['技术风险', '失效', '效果不稳定', '工程难度'], priority_sources=['技术材料', '效果说明', '失败案例', '交付问题记录']),
            _analysis('商业化风险', 'commercialization_risk', query_groups=['商业化风险', '客户不愿付费', '采购周期长', '续费不稳定'], priority_sources=['客户转化材料', '收入资料', '项目交付资料']),
            _analysis('团队风险', 'organization_risk', query_groups=['团队风险', '关键人依赖', '组织能力不足', '团队流失'], priority_sources=['团队材料', '组织结构', '关键岗位说明']),
            _analysis('市场风险', 'market_risk', query_groups=['市场风险', '赛道过热', '需求被高估', '竞争挤压'], priority_sources=['市场分析材料', '客户反馈', '竞品材料']),
            _analysis('资本风险', 'financing_risk', query_groups=['资本风险', '现金流压力', '下一轮难接', '估值体系失衡'], priority_sources=['融资材料', '现金流说明', '后续融资计划']),
            _analysis('信息真实性风险', 'info_authenticity_risk', query_groups=['信息真实性风险', '材料冲突', '数据口径不一致', '案例真实性'], priority_sources=['材料冲突', '数据口径不一致', '证据不闭合情况']),
            _analysis('风险等级', 'risk_level', query_groups=['风险等级', '高 中 低', '主导风险', '主要风险'], priority_sources=['各类风险证据', '缺失项', '冲突信息']),
        ],
        gap_hints=['可能缺合同或验收材料', '可能缺测试数据', '可能缺现金流说明', '可能缺合规边界说明'],
    ),
    ModuleSpec(
        module_name='追问清单',
        search_queries=['追问', '未验证', '下一轮', '关键问题', '客户验证', '融资用途'],
        fields=[
            _analysis('针对团队的追问', 'followup_team', query_groups=['团队 缺失项 风险 追问', '销售负责人', '团队协作历史'], priority_sources=['团队判断中的缺失项', '冲突点', '风险项']),
            _analysis('针对产品与技术的追问', 'followup_product_tech', query_groups=['产品 技术 缺失项 追问', '技术指标', '真实案例'], priority_sources=['产品与技术中的缺失项', '风险项']),
            _analysis('针对市场的追问', 'followup_market', query_groups=['市场 缺失项 追问', '预算来源', '采购链路'], priority_sources=['市场分析中的缺失项', '风险项']),
            _analysis('针对商业模式的追问', 'followup_business_model', query_groups=['商业模式 缺失项 追问', '客单价', '回款'], priority_sources=['商业模式中的缺失项', '风险项']),
            _analysis('针对竞争的追问', 'followup_competition', query_groups=['竞争 缺失项 追问', '输单原因', '客户选择理由'], priority_sources=['竞争格局中的缺失项', '风险项']),
            _analysis('针对融资与经营的追问', 'followup_financing_operation', query_groups=['融资 经营 缺失项 追问', '现金流', '资金用途'], priority_sources=['融资与资本信息中的缺失项', '风险项']),
        ],
        gap_hints=['应围绕最影响投资判断的未验证信息展开'],
    ),
]

MODULE_SPEC_MAP = {spec.module_name: spec for spec in MODULE_SPECS}
