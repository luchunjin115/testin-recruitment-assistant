"""Compare old and optimized AI screening prompts on fixed candidate cases.

Usage:
    python scripts/evaluate_screening_prompt.py

The script uses the same LLM settings as the backend .env file. It calls the
model twice per case: once with the old inline prompt and once with
backend/app/prompts/screening.txt.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(str(BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.services.ai_service import _load_prompt  # noqa: E402


OLD_SCREENING_PROMPT = (
    "你是招聘初筛助手。请只基于应聘岗位、学校、学历、专业、技能关键词、"
    "工作经历、自我介绍、简历解析文本，以及job_profile中的岗位要求配置"
    "（必备技能、加分技能、学历要求、经验要求、岗位关键词、风险关键词）判断岗位匹配度。不要使用性别、年龄、"
    "民族、婚育等敏感信息作为筛选依据。结果仅供HR参考，不自动淘汰候选人。"
    "请返回JSON，字段为match_score(0-100整数)、priority_level、"
    "screening_result、screening_reason、risk_flags(字符串数组)。"
)


CASES = [
    {
        "case_name": "强匹配：测试工程师",
        "candidate": {
            "name": "林悦",
            "target_role": "测试工程师",
            "school": "武汉大学",
            "degree": "本科",
            "major": "软件工程",
            "experience_years": 3,
            "skills": ["Python", "Selenium", "Postman", "JMeter", "Jenkins"],
            "experience_desc": "负责 Web 与 App 自动化测试，搭建 Selenium 回归测试，使用 JMeter 做接口压测，并参与 CI 流水线质量门禁。",
            "self_intro": "熟悉测试流程，能独立设计测试用例并推动缺陷闭环。",
            "resume_text": "3年测试经验，覆盖接口测试、自动化测试、性能测试。",
            "job_profile": {
                "title": "测试工程师",
                "description": "负责产品功能、接口、自动化和性能测试。",
                "required_skills": "Python,Selenium,接口测试,Postman",
                "bonus_skills": "JMeter,Jenkins,Appium",
                "education_requirement": "本科",
                "experience_requirement": "2年以上",
                "job_keywords": "测试用例,缺陷跟踪,自动化测试",
                "risk_keywords": "频繁跳槽",
            },
        },
    },
    {
        "case_name": "方向偏差：前端投测试",
        "candidate": {
            "name": "周子航",
            "target_role": "测试工程师",
            "school": "普通本科院校",
            "degree": "本科",
            "major": "数字媒体技术",
            "experience_years": 1,
            "skills": ["JavaScript", "React", "CSS"],
            "experience_desc": "主要负责活动页面开发和组件样式维护，较少接触测试工具。",
            "self_intro": "希望转向测试岗位，学习能力强。",
            "resume_text": "前端开发实习经历，了解基本浏览器调试。",
            "job_profile": {
                "title": "测试工程师",
                "description": "负责接口测试、自动化测试和缺陷管理。",
                "required_skills": "Python,Selenium,接口测试,Postman",
                "bonus_skills": "JMeter,Jenkins",
                "education_requirement": "本科",
                "experience_requirement": "1年以上",
                "job_keywords": "自动化测试,测试用例,缺陷跟踪",
                "risk_keywords": "",
            },
        },
    },
    {
        "case_name": "信息不足：简历过短",
        "candidate": {
            "name": "陈思雨",
            "target_role": "AI应用实习生",
            "school": "",
            "degree": "本科",
            "major": "",
            "experience_years": 0,
            "skills": ["Python"],
            "experience_desc": "",
            "self_intro": "对 AI 很感兴趣，愿意学习。",
            "resume_text": "希望找 AI 实习。",
            "job_profile": {
                "title": "AI应用实习生",
                "description": "参与 Prompt 调优、数据清洗和 AI 应用原型验证。",
                "required_skills": "Python,数据处理",
                "bonus_skills": "Prompt,大模型,机器学习",
                "education_requirement": "本科",
                "experience_requirement": "",
                "job_keywords": "AI应用,Prompt,评估",
                "risk_keywords": "",
            },
        },
    },
]


def clean_json_text(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
    return clean.strip()


def parse_json_or_raw(text: str) -> Any:
    try:
        return json.loads(clean_json_text(text))
    except json.JSONDecodeError:
        return {"raw_output": text}


def call_llm(system_prompt: str, payload: Dict[str, Any]) -> str:
    settings = get_settings()
    if settings.llm_provider == "mock":
        raise RuntimeError("当前 LLM_PROVIDER=mock，无法评估 prompt 差异。请在 .env 中配置真实 LLM_PROVIDER。")

    from openai import OpenAI

    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def compact_result(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {"raw_output": value}
    return {
        "match_score": value.get("match_score"),
        "priority_level": value.get("priority_level"),
        "screening_result": value.get("screening_result"),
        "screening_reason": value.get("screening_reason"),
        "risk_flags": value.get("risk_flags"),
    }


def validate_result(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict) or "raw_output" in value:
        return {"json_valid": False, "schema_ok": False, "issues": ["未返回可解析 JSON"]}

    issues = []
    score = value.get("match_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        issues.append("match_score 不是 0-100 整数")
    if value.get("priority_level") not in ["高优先级", "中优先级", "低优先级"]:
        issues.append("priority_level 枚举不合规")
    if value.get("screening_result") not in ["建议初筛", "备选", "暂缓"]:
        issues.append("screening_result 枚举不合规")
    if not isinstance(value.get("screening_reason"), str) or not value.get("screening_reason", "").strip():
        issues.append("screening_reason 为空")
    if not isinstance(value.get("risk_flags"), list) or not value.get("risk_flags"):
        issues.append("risk_flags 不是非空数组")

    return {"json_valid": True, "schema_ok": not issues, "issues": issues}


def main() -> None:
    optimized_prompt = _load_prompt("screening.txt")
    if not optimized_prompt.strip():
        raise RuntimeError("未找到 backend/app/prompts/screening.txt")

    print("AI 初筛 Prompt 评估：old inline prompt vs optimized screening.txt")
    print("=" * 72)

    for index, item in enumerate(CASES, start=1):
        case_name = item["case_name"]
        candidate = item["candidate"]
        print(f"\n[{index}] {case_name}")
        print("-" * 72)

        old_result = parse_json_or_raw(call_llm(OLD_SCREENING_PROMPT, candidate))
        new_result = parse_json_or_raw(call_llm(optimized_prompt, candidate))

        print("旧 prompt 输出：")
        print(json.dumps(compact_result(old_result), ensure_ascii=False, indent=2))
        print("旧 prompt 格式检查：")
        print(json.dumps(validate_result(old_result), ensure_ascii=False, indent=2))
        print("\n新 prompt 输出：")
        print(json.dumps(compact_result(new_result), ensure_ascii=False, indent=2))
        print("新 prompt 格式检查：")
        print(json.dumps(validate_result(new_result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
