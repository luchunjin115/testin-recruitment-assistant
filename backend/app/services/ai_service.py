import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ..config import get_settings
from .mock_llm import mock_llm

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


class AIService:
    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.LLM_PROVIDER
        self._client = None

        if self.provider != "mock":
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.settings.OPENAI_API_KEY,
                    base_url=self.settings.OPENAI_BASE_URL,
                )
            except Exception as e:
                logger.warning(f"LLM客户端初始化失败，回退到mock模式: {e}")
                self.provider = "mock"

    def _call_llm(self, system_prompt: str, user_content: str) -> str:
        if self.provider == "mock" or not self._client:
            return ""
        try:
            resp = self._client.chat.completions.create(
                model=self.settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"LLM调用失败，回退到mock: {e}")
            return ""

    def extract_resume(self, text: str) -> dict:
        if self.provider == "mock":
            return mock_llm.extract_resume(text)

        prompt = _load_prompt("resume_extraction.txt")
        result = self._call_llm(prompt, text)
        if result:
            try:
                clean = result.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
                return json.loads(clean)
            except json.JSONDecodeError:
                logger.warning("LLM返回非JSON，回退到mock解析")
        return mock_llm.extract_resume(text)

    def generate_summary(self, data: dict) -> str:
        if self.provider == "mock":
            return mock_llm.generate_summary(data)

        prompt = _load_prompt("candidate_summary.txt")
        result = self._call_llm(prompt, json.dumps(data, ensure_ascii=False))
        return result if result else mock_llm.generate_summary(data)

    def generate_tags(self, data: dict) -> List[str]:
        if self.provider == "mock":
            return mock_llm.generate_tags(data)

        prompt = _load_prompt("auto_tagging.txt")
        result = self._call_llm(prompt, json.dumps(data, ensure_ascii=False))
        if result:
            try:
                clean = result.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
                return json.loads(clean)
            except json.JSONDecodeError:
                pass
        return mock_llm.generate_tags(data)

    def generate_followup(self, data: dict) -> str:
        if self.provider == "mock":
            return mock_llm.generate_followup(data)

        prompt = _load_prompt("followup_suggestion.txt")
        result = self._call_llm(prompt, json.dumps(data, ensure_ascii=False))
        return result if result else mock_llm.generate_followup(data)

    def screen_candidate(self, data: dict) -> dict:
        if self.provider == "mock":
            return mock_llm.screen_candidate(data)

        prompt = (
            "你是招聘初筛助手。请只基于应聘岗位、学校、学历、专业、技能关键词、"
            "工作经历、自我介绍、简历解析文本，以及job_profile中的岗位要求配置"
            "（必备技能、加分技能、学历要求、经验要求、岗位关键词、风险关键词）判断岗位匹配度。不要使用性别、年龄、"
            "民族、婚育等敏感信息作为筛选依据。结果仅供HR参考，不自动淘汰候选人。"
            "请返回JSON，字段为match_score(0-100整数)、priority_level、"
            "screening_result、screening_reason、risk_flags(字符串数组)。"
        )
        result = self._call_llm(prompt, json.dumps(data, ensure_ascii=False))
        if result:
            try:
                clean = result.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
                parsed = json.loads(clean)
                score = int(parsed.get("match_score", 0))
                parsed["match_score"] = max(0, min(100, score))
                if not isinstance(parsed.get("risk_flags"), list):
                    parsed["risk_flags"] = []
                return parsed
            except (ValueError, TypeError, json.JSONDecodeError):
                logger.warning("LLM返回初筛结果格式不正确，回退到mock初筛")
        return mock_llm.screen_candidate(data)

    def summarize_interview_feedback(self, data: dict) -> dict:
        if self.provider == "mock":
            return mock_llm.summarize_interview_feedback(data)

        prompt = (
            "你是招聘面试反馈整理助手。请只基于候选人已有信息和HR输入的面试原始反馈进行总结，"
            "不要编造反馈中没有的信息，不要自动淘汰候选人，结果仅作为HR辅助参考。"
            "请返回JSON，字段为technical_summary、communication_summary、job_match、"
            "risk_points(字符串数组)、recommendation、next_step。"
            "recommendation只能是：建议复试、建议 offer、待定、不建议继续。"
        )
        result = self._call_llm(prompt, json.dumps(data, ensure_ascii=False))
        if result:
            try:
                clean = result.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
                parsed = json.loads(clean)
                if parsed.get("recommendation") not in ["建议复试", "建议 offer", "待定", "不建议继续"]:
                    parsed["recommendation"] = "待定"
                if not isinstance(parsed.get("risk_points"), list):
                    parsed["risk_points"] = []
                return {
                    "technical_summary": parsed.get("technical_summary") or "反馈未明确描述技术能力。",
                    "communication_summary": parsed.get("communication_summary") or "反馈未明确描述沟通表达。",
                    "job_match": parsed.get("job_match") or "反馈未充分说明岗位匹配度。",
                    "risk_points": parsed.get("risk_points") or ["暂无明确风险点"],
                    "recommendation": parsed.get("recommendation") or "待定",
                    "next_step": parsed.get("next_step") or "建议HR结合完整面试记录复核。",
                }
            except (TypeError, json.JSONDecodeError):
                logger.warning("LLM返回面试总结格式不正确，回退到mock总结")
        return mock_llm.summarize_interview_feedback(data)

    def chat(self, messages: List[dict], context: Optional[dict] = None) -> str:
        if self.provider == "mock":
            return mock_llm.chat(messages, context)

        system_prompt = _load_prompt("copilot_system.txt")
        if context:
            system_prompt += f"\n\n当前系统数据: {json.dumps(context, ensure_ascii=False)}"

        all_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            resp = self._client.chat.completions.create(
                model=self.settings.OPENAI_MODEL,
                messages=all_messages,
                temperature=0.7,
            )
            return resp.choices[0].message.content or "抱歉，我暂时无法回答这个问题。"
        except Exception as e:
            logger.warning(f"Copilot LLM调用失败: {e}")
            return mock_llm.chat(messages, context)


ai_service = AIService()
