"""Run two explicit, paid DeepSeek validations for stage 7 candidate evaluation."""

from __future__ import annotations

import asyncio
import json
import sys

from app.adapters.screening_model import DeepSeekScreeningModelAdapter
from app.core.config import get_settings
from app.prompts.screening_rubric_templates import get_rubric_template
from app.schemas.screening_evaluation import ScreeningSemanticEvaluation
from app.schemas.screening_rubric import RubricTemplateKey
from app.services.screening_input_service import ScreeningInputService


JOB_CONTEXT = {
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
        "preferred_skills": ["Redis", "Docker"],
        "minimum_work_years": 3,
        "education_requirement": "bachelor_or_above",
    },
}


SAMPLES = (
    {
        "case": "evidence_rich",
        "application_ref": "application-live-rich",
        "confirmed_profile": {
            "name": "虚构候选人甲",
            "phone": "13800138000",
            "email": "fake-a@example.com",
            "current_title": "测试平台工程师",
            "work_years": 5,
            "education_level": "本科",
            "skills": ["Python", "PostgreSQL", "Redis", "Docker"],
            "work_experiences": [
                {
                    "company": "虚构科技公司",
                    "title": "测试平台工程师",
                    "description": "负责测试平台服务设计、自动化任务编排和稳定性改进。",
                    "tech_stack": ["Python", "PostgreSQL", "Redis"],
                }
            ],
        },
        "resume_raw_text": (
            "姓名：虚构候选人甲\n电话：13800138000\n邮箱：fake-a@example.com\n"
            "工作经历：负责测试平台服务设计和自动化任务编排。\n"
            "项目经历：主导将串行回归任务改造成并行调度，执行时间从 120 分钟缩短到 35 分钟。\n"
            "问题处理：定位任务队列重复消费问题，增加幂等键和失败补偿后将重复执行率降至 0.1%。\n"
            "协作经历：与研发和运维团队共同制定发布质量门禁并推动落地。"
        ),
        "resume_snapshot": {
            "basic_info": {
                "name": "虚构候选人甲",
                "current_title": "测试平台工程师",
                "work_years": 5,
                "education_level": "本科",
            },
            "skills": ["Python", "PostgreSQL", "Redis", "Docker"],
            "project_experiences": [
                {
                    "project_name": "自动化回归平台",
                    "role": "核心开发",
                    "description": "设计并行任务调度和失败补偿。",
                    "achievements": "执行时间从 120 分钟缩短到 35 分钟。",
                    "tech_stack": ["Python", "Redis"],
                }
            ],
        },
    },
    {
        "case": "evidence_sparse",
        "application_ref": "application-live-sparse",
        "confirmed_profile": {
            "name": "虚构候选人乙",
            "phone": "13900139000",
            "email": "fake-b@example.com",
            "skills": ["Python"],
        },
        "resume_raw_text": "姓名：虚构候选人乙\n电话：13900139000\n技能：Python",
        "resume_snapshot": {"skills": ["Python"]},
    },
)


async def main() -> None:
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，跳过真实验证")
    adapter = DeepSeekScreeningModelAdapter(settings=settings)
    criteria = list(get_rubric_template(RubricTemplateKey.TECHNICAL).semantic_items)

    selected_case = sys.argv[1] if len(sys.argv) > 1 else None
    samples = (
        tuple(sample for sample in SAMPLES if sample["case"] == selected_case)
        if selected_case
        else SAMPLES
    )
    if not samples:
        raise RuntimeError("未知的真实验证样本名称")

    for sample in samples:
        material = ScreeningInputService.build_candidate_material(
            application_ref=sample["application_ref"],
            confirmed_profile=sample["confirmed_profile"],
            resume_raw_text=sample["resume_raw_text"],
            resume_snapshot=sample["resume_snapshot"],
        )
        serialized_material = json.dumps(material.model_dump(mode="json"), ensure_ascii=False)
        for prohibited in ("13800138000", "13900139000", "fake-a@example.com", "fake-b@example.com"):
            if prohibited in serialized_material:
                raise RuntimeError("脱敏候选人材料仍包含联系方式")

        result = await adapter.evaluate(JOB_CONTEXT, criteria, material)
        evaluation = ScreeningSemanticEvaluation.model_validate_json(result.content)
        try:
            evaluation.validate_against(criteria, material)
        except ValueError:
            diagnostics = []
            for item in evaluation.evaluations:
                for evidence in item.evidence:
                    if not material.source_contains_quote(
                        evidence.source,
                        evidence.quote,
                    ):
                        diagnostics.append(
                            {
                                "criterion_key": item.criterion_key,
                                "source": evidence.source.value,
                                "locator": evidence.locator,
                                "quote": evidence.quote,
                            }
                        )
            print(
                json.dumps(
                    {"case": sample["case"], "unlocatable_evidence": diagnostics},
                    ensure_ascii=False,
                )
            )
            raise
        print(
            json.dumps(
                {
                    "case": sample["case"],
                    "model": result.model,
                    "scores": [item.score for item in evaluation.evaluations],
                    "confidences": [item.confidence.value for item in evaluation.evaluations],
                    "unknown_count": sum(
                        item.score == "unknown" for item in evaluation.evaluations
                    ),
                    "evidence_count": sum(
                        len(item.evidence) for item in evaluation.evaluations
                    ),
                    "duration_ms": result.duration_ms,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "estimated_cost": (
                        str(result.estimated_cost)
                        if result.estimated_cost is not None
                        else None
                    ),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
