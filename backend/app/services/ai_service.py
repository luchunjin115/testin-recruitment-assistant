import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from ..config import get_settings
from .mock_llm import mock_llm

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _json_dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, default=_json_default)


class AIService:
    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.llm_provider
        self._client = None

        if self.provider != "mock":
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.settings.llm_api_key,
                    base_url=self.settings.llm_base_url,
                )
            except Exception as e:
                if self.settings.LLM_ENABLE_MOCK_FALLBACK:
                    logger.warning(f"LLM客户端初始化失败，回退到mock模式: {e}")
                    self.provider = "mock"
                else:
                    raise RuntimeError(f"LLM客户端初始化失败: {e}") from e

    def _call_llm(self, system_prompt: str, user_content: str) -> str:
        if self.provider == "mock" or not self._client:
            return ""
        try:
            resp = self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            if self.settings.LLM_ENABLE_MOCK_FALLBACK:
                logger.warning(f"LLM调用失败，回退到mock: {e}")
                return ""
            logger.exception("LLM调用失败")
            raise RuntimeError(f"LLM调用失败: {e}") from e

    def _mock_or_raise(self, message: str, fallback):
        if self.settings.LLM_ENABLE_MOCK_FALLBACK:
            logger.warning(f"{message}，回退到mock")
            return fallback()
        raise RuntimeError(message)

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
                return self._mock_or_raise("LLM返回非JSON，无法解析简历信息", lambda: mock_llm.extract_resume(text))
        return self._mock_or_raise("LLM未返回简历解析结果", lambda: mock_llm.extract_resume(text))

    def generate_summary(self, data: dict) -> str:
        if self.provider == "mock":
            return mock_llm.generate_summary(data)

        prompt = _load_prompt("candidate_summary.txt")
        result = self._call_llm(prompt, _json_dumps(data))
        if result:
            return result
        return self._mock_or_raise("LLM未返回候选人摘要", lambda: mock_llm.generate_summary(data))

    def generate_tags(self, data: dict) -> List[str]:
        if self.provider == "mock":
            return mock_llm.generate_tags(data)

        prompt = _load_prompt("auto_tagging.txt")
        result = self._call_llm(prompt, _json_dumps(data))
        if result:
            try:
                clean = result.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
                return json.loads(clean)
            except json.JSONDecodeError:
                return self._mock_or_raise("LLM返回非JSON，无法解析标签", lambda: mock_llm.generate_tags(data))
        return self._mock_or_raise("LLM未返回候选人标签", lambda: mock_llm.generate_tags(data))

    def generate_followup(self, data: dict) -> str:
        if self.provider == "mock":
            return mock_llm.generate_followup(data)

        prompt = _load_prompt("followup_suggestion.txt")
        result = self._call_llm(prompt, _json_dumps(data))
        if result:
            return result
        return self._mock_or_raise("LLM未返回跟进建议", lambda: mock_llm.generate_followup(data))

    def screen_candidate(self, data: dict) -> dict:
        if self.provider == "mock":
            return mock_llm.screen_candidate(data)

        prompt = _load_prompt("screening.txt")
        result = self._call_llm(prompt, _json_dumps(data))
        if result:
            try:
                clean = result.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
                parsed = json.loads(clean)
                score = int(parsed.get("match_score", 0))
                parsed["match_score"] = max(0, min(100, score))
                if parsed.get("priority_level") not in ["高优先级", "中优先级", "低优先级"]:
                    if parsed["match_score"] >= 80:
                        parsed["priority_level"] = "高优先级"
                    elif parsed["match_score"] >= 60:
                        parsed["priority_level"] = "中优先级"
                    else:
                        parsed["priority_level"] = "低优先级"
                if parsed.get("screening_result") not in ["建议初筛", "备选", "暂缓"]:
                    if parsed["match_score"] >= 80:
                        parsed["screening_result"] = "建议初筛"
                    elif parsed["match_score"] >= 60:
                        parsed["screening_result"] = "备选"
                    else:
                        parsed["screening_result"] = "暂缓"
                if not isinstance(parsed.get("risk_flags"), list):
                    parsed["risk_flags"] = []
                if not parsed["risk_flags"]:
                    parsed["risk_flags"] = ["暂无明显风险"]
                return parsed
            except (ValueError, TypeError, json.JSONDecodeError):
                return self._mock_or_raise("LLM返回初筛结果格式不正确", lambda: mock_llm.screen_candidate(data))
        return self._mock_or_raise("LLM未返回初筛结果", lambda: mock_llm.screen_candidate(data))

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
        result = self._call_llm(prompt, _json_dumps(data))
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
                return self._mock_or_raise("LLM返回面试总结格式不正确", lambda: mock_llm.summarize_interview_feedback(data))
        return self._mock_or_raise("LLM未返回面试总结", lambda: mock_llm.summarize_interview_feedback(data))

    def chat(self, messages: List[dict], context: Optional[dict] = None) -> str:
        if self.provider == "mock":
            return mock_llm.chat(messages, context)

        system_prompt = _load_prompt("copilot_system.txt")
        if context:
            system_prompt += f"\n\n当前系统数据: {_json_dumps(context)}"

        all_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            resp = self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=all_messages,
                temperature=0.7,
            )
            return resp.choices[0].message.content or "抱歉，我暂时无法回答这个问题。"
        except Exception as e:
            if not self.settings.LLM_ENABLE_MOCK_FALLBACK:
                logger.exception("Copilot LLM调用失败")
                raise RuntimeError(f"Copilot LLM调用失败: {e}") from e
            logger.warning(f"Copilot LLM调用失败，回退到mock: {e}")
            return mock_llm.chat(messages, context)


ai_service = AIService()
