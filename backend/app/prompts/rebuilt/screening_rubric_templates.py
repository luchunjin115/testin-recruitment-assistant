from __future__ import annotations

from dataclasses import dataclass

from app.schemas.rebuilt.screening_rubric import (
    RubricCriterionSource,
    RubricDimension,
    RubricSource,
    RubricTemplateKey,
    SemanticRubricCriterion,
)


RUBRIC_TEMPLATE_VERSION = "rubric_templates_v1"


@dataclass(frozen=True, slots=True)
class RubricTemplateDefinition:
    key: RubricTemplateKey
    name: str
    description: str
    source: RubricSource
    version: str
    semantic_items: tuple[SemanticRubricCriterion, ...]


def _item(
    *,
    key: str,
    name: str,
    description: str,
    dimension: RubricDimension,
    share: int,
    high: str,
    mid: str,
    low: str,
) -> SemanticRubricCriterion:
    return SemanticRubricCriterion(
        key=key,
        name=name,
        description=description,
        dimension=dimension,
        suggested_share=share,
        high_score_anchor=high,
        mid_score_anchor=mid,
        low_score_anchor=low,
        source=RubricCriterionSource.TEMPLATE,
    )


_STANDARD = RubricTemplateDefinition(
    key=RubricTemplateKey.STANDARD,
    name="通用岗位模板",
    description="适用于暂时无法明确分类的岗位，重点评价职责、经历、成果和能力证据。",
    source=RubricSource.STANDARD_TEMPLATE,
    version=RUBRIC_TEMPLATE_VERSION,
    semantic_items=(
        _item(
            key="responsibility_alignment",
            name="岗位职责相关性",
            description="评价候选人既往实际职责与当前岗位核心职责的相关程度。",
            dimension=RubricDimension.WORK_EXPERIENCE_RELEVANCE,
            share=50,
            high="有多段直接相关经历，并清楚说明本人承担的核心职责。",
            mid="有部分相关职责，但覆盖范围、持续时间或本人角色不够完整。",
            low="经历与岗位职责关联较弱，或只有笼统表述而缺少本人职责证据。",
        ),
        _item(
            key="experience_depth",
            name="相关经验深度",
            description="评价候选人是否在岗位相关场景中承担过有实质深度的工作。",
            dimension=RubricDimension.WORK_EXPERIENCE_RELEVANCE,
            share=50,
            high="长期承担关键工作，能够说明复杂场景、决策和实际结果。",
            mid="具备相关实践，但复杂度、独立性或结果证据有限。",
            low="仅接触基础任务，或无法证明真实参与深度。",
        ),
        _item(
            key="project_impact",
            name="项目成果与影响",
            description="评价候选人项目成果是否具体、可核对并与岗位目标相关。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            share=50,
            high="成果具体且可核对，能说明本人贡献和对业务或交付的明确影响。",
            mid="有项目成果，但量化程度、本人贡献或岗位相关性不完整。",
            low="只有项目名称或职责罗列，没有可核对的结果证据。",
        ),
        _item(
            key="problem_solving_depth",
            name="问题解决能力",
            description="评价候选人识别、分析和解决岗位相关复杂问题的实际证据。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            share=50,
            high="能够说明复杂问题、分析过程、关键决策、解决方案和最终结果。",
            mid="参与过问题处理，但分析深度、独立性或结果证据有限。",
            low="只有一般性能力描述，没有具体问题和解决过程。",
        ),
        _item(
            key="role_specific_context",
            name="岗位补充场景匹配",
            description="评价岗位补充说明中需要理解上下文的工作场景是否有简历证据支持。",
            dimension=RubricDimension.KEYWORDS_AND_ADDITIONAL,
            share=100,
            high="有直接、完整且可核对的相关场景证据。",
            mid="存在部分相关场景，但范围或结果证据不足。",
            low="没有直接相关场景，或只能依靠宽泛描述推测。",
        ),
    ),
)


_TECHNICAL = RubricTemplateDefinition(
    key=RubricTemplateKey.TECHNICAL,
    name="技术岗位模板",
    description="适用于开发、测试、数据和 AI 等岗位，强调技术实践、复杂问题和项目成果。",
    source=RubricSource.TECHNICAL_TEMPLATE,
    version=RUBRIC_TEMPLATE_VERSION,
    semantic_items=(
        _item(
            key="technical_responsibility_alignment",
            name="技术职责相关性",
            description="评价既往技术职责与当前岗位核心技术工作的相关程度。",
            dimension=RubricDimension.WORK_EXPERIENCE_RELEVANCE,
            share=50,
            high="持续承担高度相关的核心技术职责，并能说明本人边界。",
            mid="承担过部分相关技术职责，但覆盖范围或持续性有限。",
            low="技术职责关联较弱，或只有技术名词而缺少实际职责。",
        ),
        _item(
            key="technical_practice_depth",
            name="技术实践深度",
            description="评价候选人对岗位相关技术的真实使用深度和复杂场景经验。",
            dimension=RubricDimension.WORK_EXPERIENCE_RELEVANCE,
            share=50,
            high="在复杂生产或交付场景中深入使用相关技术，并能说明关键取舍。",
            mid="有实际使用经验，但主要集中在常规场景或缺少关键细节。",
            low="只有技能罗列、学习经历或无法核对的熟练度描述。",
        ),
        _item(
            key="system_design_reasoning",
            name="系统设计与技术判断",
            description="评价候选人是否具备与岗位层级匹配的设计、取舍和技术判断证据。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            share=35,
            high="主导关键设计，能说明约束、方案比较、取舍和验证结果。",
            mid="参与设计或局部决策，但系统范围、独立性或结果有限。",
            low="仅描述实现任务，没有设计依据或技术判断证据。",
        ),
        _item(
            key="complex_problem_solving",
            name="复杂问题解决",
            description="评价定位并解决复杂技术问题的过程和实际结果。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            share=35,
            high="能够完整说明复杂问题、定位过程、方案、验证和复盘。",
            mid="参与过复杂问题处理，但主导程度或证据完整性有限。",
            low="只有问题处理结论，没有过程、本人贡献或结果证据。",
        ),
        _item(
            key="measurable_technical_outcomes",
            name="可验证技术成果",
            description="评价技术工作是否产生可核对的性能、质量、效率或稳定性成果。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            share=30,
            high="成果指标清楚，基线、改进幅度和本人贡献均可核对。",
            mid="存在明确改进，但指标、基线或本人贡献不完整。",
            low="只描述完成任务，没有可核对的技术或业务结果。",
        ),
        _item(
            key="technical_learning_transfer",
            name="技术学习与迁移能力",
            description="评价候选人把新知识应用到真实岗位相关问题中的证据。",
            dimension=RubricDimension.PREFERRED_QUALIFICATIONS,
            share=100,
            high="能够说明主动学习、实际应用、效果验证和经验沉淀。",
            mid="有学习和应用经历，但场景复杂度或结果证据有限。",
            low="只有学习意愿或课程记录，没有实际应用证据。",
        ),
    ),
)


_NON_TECHNICAL = RubricTemplateDefinition(
    key=RubricTemplateKey.NON_TECHNICAL,
    name="非技术岗位模板",
    description="适用于产品、运营、销售和 HR 等岗位，强调业务职责、协作和可验证成果。",
    source=RubricSource.NON_TECHNICAL_TEMPLATE,
    version=RUBRIC_TEMPLATE_VERSION,
    semantic_items=(
        _item(
            key="business_responsibility_alignment",
            name="业务职责相关性",
            description="评价候选人既往业务职责与当前岗位核心职责的相关程度。",
            dimension=RubricDimension.WORK_EXPERIENCE_RELEVANCE,
            share=50,
            high="持续承担高度相关的核心业务职责，并能清楚说明本人范围。",
            mid="承担过部分相关职责，但覆盖范围或持续性有限。",
            low="职责关联较弱，或只有岗位名称而缺少实际工作证据。",
        ),
        _item(
            key="business_scenario_depth",
            name="业务场景深度",
            description="评价候选人在岗位相关业务场景中的理解、判断和执行深度。",
            dimension=RubricDimension.WORK_EXPERIENCE_RELEVANCE,
            share=50,
            high="处理过复杂业务场景，能说明目标、判断、行动和结果。",
            mid="具备相关业务实践，但复杂度、独立性或结果有限。",
            low="只有一般性工作描述，没有具体业务场景证据。",
        ),
        _item(
            key="measurable_business_outcomes",
            name="可验证业务成果",
            description="评价候选人是否取得与岗位目标相关且可核对的业务成果。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            share=40,
            high="成果指标、背景和本人贡献清楚，能够核对实际影响。",
            mid="有明确成果，但指标、基线或本人贡献不完整。",
            low="只描述执行过程，没有可核对的结果。",
        ),
        _item(
            key="planning_and_problem_solving",
            name="规划与问题解决",
            description="评价候选人拆解目标、处理问题并推动结果的实际证据。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            share=30,
            high="能够完整说明目标拆解、关键判断、行动调整和结果复盘。",
            mid="参与过规划或问题处理，但主导程度和证据完整性有限。",
            low="只有宽泛能力描述，没有具体过程和结果。",
        ),
        _item(
            key="cross_functional_delivery",
            name="跨团队协作与交付",
            description="评价候选人协调相关角色并推动岗位目标落地的证据。",
            dimension=RubricDimension.PROJECTS_AND_CAPABILITY,
            share=30,
            high="在复杂协作中明确推动机制、解决阻碍并取得可核对结果。",
            mid="有跨团队协作经历，但本人作用或交付结果不够清晰。",
            low="只提到参与协作，没有说明本人行动和结果。",
        ),
        _item(
            key="role_specific_growth",
            name="岗位相关成长能力",
            description="评价候选人学习新业务并转化为实际岗位成果的证据。",
            dimension=RubricDimension.PREFERRED_QUALIFICATIONS,
            share=100,
            high="能够说明学习背景、实际应用、结果验证和方法沉淀。",
            mid="有学习和应用经历，但成果或复用证据有限。",
            low="只有学习意愿，没有实际应用和结果证据。",
        ),
    ),
)


RUBRIC_TEMPLATES: dict[RubricTemplateKey, RubricTemplateDefinition] = {
    template.key: template for template in (_STANDARD, _TECHNICAL, _NON_TECHNICAL)
}


def get_rubric_template(key: RubricTemplateKey | str) -> RubricTemplateDefinition:
    resolved_key = key if isinstance(key, RubricTemplateKey) else RubricTemplateKey(key)
    template = RUBRIC_TEMPLATES[resolved_key]
    return RubricTemplateDefinition(
        key=template.key,
        name=template.name,
        description=template.description,
        source=template.source,
        version=template.version,
        semantic_items=tuple(item.model_copy(deep=True) for item in template.semantic_items),
    )


__all__ = [
    "RUBRIC_TEMPLATES",
    "RUBRIC_TEMPLATE_VERSION",
    "RubricTemplateDefinition",
    "get_rubric_template",
]
