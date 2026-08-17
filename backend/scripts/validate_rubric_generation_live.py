"""Run a small, explicit, paid DeepSeek validation for stage 7 rubric generation."""

from __future__ import annotations

import asyncio
import json

from app.adapters.rebuilt.screening_rubric_generation import (
    DeepSeekRubricGenerationAdapter,
)
from app.core.config import get_settings
from app.schemas.rebuilt.screening_rubric import (
    ManualSemanticCriterionInput,
    RubricGenerationSuggestion,
    RubricTemplateKey,
)


SAMPLES = (
    (
        RubricTemplateKey.TECHNICAL,
        {
            "title": "测试平台开发工程师",
            "department": "质量工程部",
            "description": "负责企业测试平台设计、自动化能力建设和跨团队质量改进。",
            "requirements": {
                "responsibilities": [
                    "设计并交付测试平台能力",
                    "分析复杂质量问题并推动闭环",
                    "与研发团队协作改进交付质量",
                ],
                "required_skills": ["Python", "PostgreSQL"],
                "minimum_work_years": 3,
                "education_requirement": "bachelor_or_above",
            },
        },
    ),
    (
        RubricTemplateKey.NON_TECHNICAL,
        {
            "title": "企业客户成功顾问",
            "department": "客户成功部",
            "description": "负责企业客户落地、业务目标跟进、风险识别和续约协同。",
            "requirements": {
                "responsibilities": [
                    "推动客户完成产品落地",
                    "识别使用风险并协调资源解决",
                    "复盘客户目标和阶段性成果",
                ],
                "required_skills": ["客户沟通", "项目推进"],
                "minimum_work_years": 2,
                "education_requirement": "college_or_above",
            },
        },
    ),
)


async def main() -> None:
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，跳过真实验证")
    adapter = DeepSeekRubricGenerationAdapter(settings=settings)

    for template_key, job_context in SAMPLES:
        result = await adapter.generate(job_context, template_key)
        suggestion = RubricGenerationSuggestion.model_validate_json(result.content)
        if suggestion.template_key is not template_key:
            raise RuntimeError("模型返回模板与请求不一致")
        if not 5 <= len(suggestion.semantic_items) <= 8:
            raise RuntimeError("真实模型未遵守默认生成 5—8 项要求")
        print(
            json.dumps(
                {
                    "case": template_key.value,
                    "model": result.model,
                    "item_count": len(suggestion.semantic_items),
                    "item_names": [item.name for item in suggestion.semantic_items],
                    "dimensions": sorted(
                        {item.dimension.value for item in suggestion.semantic_items}
                    ),
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                },
                ensure_ascii=False,
            )
        )

    manual_item = ManualSemanticCriterionInput(
        name="复杂客户问题推动",
        description="评价候选人推动复杂客户问题解决的经历",
        dimension="projects_and_capability",
        suggested_share=40,
        high_score_anchor="有跨团队推动复杂问题闭环的明确证据",
        mid_score_anchor="有问题协调经历但复杂度或结果证据一般",
        low_score_anchor="只有一般沟通描述，缺少推动过程和结果",
    )
    assisted_result = await adapter.assist_item(SAMPLES[1][1], manual_item)
    assisted = ManualSemanticCriterionInput.model_validate_json(assisted_result.content)
    print(
        json.dumps(
            {
                "case": "item_assistance",
                "model": assisted_result.model,
                "name": assisted.name,
                "dimension": assisted.dimension.value,
                "suggested_share": assisted.suggested_share,
                "input_tokens": assisted_result.input_tokens,
                "output_tokens": assisted_result.output_tokens,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
