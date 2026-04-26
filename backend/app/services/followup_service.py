import json
from datetime import datetime
from typing import List


TERMINAL_STAGES = ["入职", "淘汰"]

STAGE_RULES = {
    "新投递": {
        "priority": "中",
        "suggestion": "该候选人刚完成投递，建议HR尽快查看简历并完成初筛。",
        "reason": "新投递候选人需要及时进入初筛流程",
    },
    "待筛选": {
        "priority": "中",
        "suggestion": "该候选人处于待筛选阶段，建议HR尽快完成初筛判断。",
        "reason": "候选人已进入待筛选阶段",
    },
    "待约面": {
        "priority": "高",
        "suggestion": "该候选人已通过初筛但尚未安排面试，建议尽快联系候选人确认面试时间。",
        "reason": "待约面候选人需要尽快安排面试",
    },
    "已约面": {
        "priority": "中",
        "suggestion": "该候选人已安排面试，建议HR在面试前确认候选人是否能准时参加。",
        "reason": "已约面候选人需要面试前确认",
    },
    "面试中": {
        "priority": "高",
        "suggestion": "该候选人已进入面试阶段，建议及时录入面试反馈，避免流程停滞。",
        "reason": "面试中候选人需要及时沉淀反馈",
    },
    "复试": {
        "priority": "高",
        "suggestion": "该候选人已进入复试阶段，建议尽快协调复试安排并同步评估结果。",
        "reason": "复试阶段需要保持推进节奏",
    },
    "offer": {
        "priority": "高",
        "suggestion": "该候选人已进入offer阶段，建议HR及时跟进offer接受意向，避免候选人流失。",
        "reason": "offer阶段候选人存在流失风险",
    },
    "入职": {
        "priority": "低",
        "suggestion": "该候选人流程已结束，无需重点跟进。",
        "reason": "候选人已完成入职流程",
    },
    "淘汰": {
        "priority": "低",
        "suggestion": "该候选人流程已结束，无需重点跟进。",
        "reason": "候选人已结束招聘流程",
    },
}

PRIORITY_RANK = {"高": 3, "中": 2, "低": 1}

OVERDUE_RULES = {
    "新投递": {"days": 1, "reason": "新投递超过 1 天未处理", "suggestion": "请尽快完成初筛"},
    "待筛选": {"days": 1, "reason": "待筛选超过 1 天未处理", "suggestion": "请尽快完成筛选判断"},
    "待约面": {"days": 2, "reason": "待约面超过 2 天未安排面试", "suggestion": "请尽快联系候选人安排面试"},
    "复试": {"days": 2, "reason": "复试超过 2 天未处理", "suggestion": "请尽快确认复试结果"},
    "offer": {"days": 3, "reason": "offer 超过 3 天未确认", "suggestion": "请跟进 offer 接受情况"},
}


class FollowupService:
    def generate_followup_suggestion(self, candidate) -> dict:
        stage = candidate.stage or "新投递"
        rule = STAGE_RULES.get(stage, {
            "priority": "中",
            "suggestion": "建议HR根据当前招聘阶段及时跟进候选人。",
            "reason": "候选人处于进行中的招聘流程",
        })

        priority = rule["priority"]
        suggestions = [rule["suggestion"]]
        reasons = [rule["reason"]]
        last_action_at = self._last_action_at(candidate)
        days_since_update = self._days_since(candidate, last_action_at)
        overdue = self.calculate_overdue(candidate, last_action_at)

        if overdue["is_overdue"]:
            priority = "高"
            suggestions.insert(0, f"{overdue['overdue_reason']}，{overdue['suggestion']}。")
            reasons.insert(0, f"{overdue['overdue_reason']}（已超时{overdue['overdue_days']}天）")
        elif days_since_update >= 3 and stage not in TERMINAL_STAGES:
            priority = "高"
            suggestions.insert(0, "该候选人已超过 3 天未更新，建议优先查看。")
            reasons.insert(0, f"超过 3 天未更新（{days_since_update}天未更新）")

        if not self._has_resume(candidate):
            suggestions.append("建议补充简历附件，便于后续评估。")
            reasons.append("缺少简历附件")

        missing_fields = self._missing_key_fields(candidate)
        if missing_fields:
            suggestions.append(f"建议补全关键信息：{'、'.join(missing_fields)}。")
            reasons.append(f"关键信息不完整：{'、'.join(missing_fields)}")

        if not candidate.ai_summary:
            suggestions.append("建议生成AI摘要，帮助HR快速了解候选人背景。")
            reasons.append("缺少AI摘要")

        return {
            "followup_suggestion": " ".join(suggestions),
            "followup_priority": priority,
            "followup_reason": "；".join(reasons),
            "followup_days_since_update": days_since_update,
            "is_overdue": overdue["is_overdue"],
            "overdue_days": overdue["overdue_days"],
            "overdue_reason": overdue["overdue_reason"],
            "last_action_at": last_action_at,
        }

    def calculate_overdue(self, candidate, last_action_at: datetime = None) -> dict:
        stage = candidate.stage or "新投递"
        if stage in TERMINAL_STAGES:
            return self._overdue_result(False, 0, "", "")

        now = datetime.now()
        base_time = last_action_at or self._last_action_at(candidate)

        if stage in ["已约面", "面试中"]:
            interview_time = candidate.interview_time
            if not interview_time or interview_time > now:
                return self._overdue_result(False, 0, "", "")
            delta_days = max((now - interview_time).days, 0)
            if delta_days > 1 and not (candidate.recheck_note or "").strip():
                return self._overdue_result(True, delta_days, "面试时间已过超过 1 天未录入反馈", "请尽快录入面试反馈")
            return self._overdue_result(False, 0, "", "")

        rule = OVERDUE_RULES.get(stage)
        if not rule or not base_time:
            return self._overdue_result(False, 0, "", "")

        delta_days = max((now - base_time).days, 0)
        if delta_days > rule["days"]:
            return self._overdue_result(True, delta_days, rule["reason"], rule["suggestion"])
        return self._overdue_result(False, 0, "", "")

    def generate_followup_suggestions(self, candidates) -> List[dict]:
        return [
            self._summary_item(candidate, self.generate_followup_suggestion(candidate))
            for candidate in candidates
        ]

    def build_dashboard_summary(self, candidates, limit: int = 5) -> dict:
        items = self.generate_followup_suggestions(candidates)
        active_items = [
            item for item in items
            if item["stage"] not in TERMINAL_STAGES
        ]
        high_count = sum(1 for item in active_items if item["followup_priority"] == "高")
        stale_count = sum(1 for item in active_items if item["followup_days_since_update"] >= 3)
        overdue_count = sum(1 for item in active_items if item["is_overdue"])
        today_followup_count = sum(
            1 for item in active_items
            if item["is_overdue"] or item["followup_priority"] in ["高", "中"]
        )

        active_items.sort(
            key=lambda item: (
                PRIORITY_RANK.get(item["followup_priority"], 0),
                item["followup_days_since_update"],
                item["candidate_id"],
            ),
            reverse=True,
        )

        return {
            "high_priority_count": high_count,
            "stale_count": stale_count,
            "overdue_count": overdue_count,
            "today_followup_count": today_followup_count,
            "items": active_items[:limit],
        }

    def _summary_item(self, candidate, suggestion: dict) -> dict:
        return {
            "candidate_id": candidate.id,
            "name": candidate.name,
            "target_role": candidate.target_role or "",
            "stage": candidate.stage or "",
            **suggestion,
        }

    def _days_since(self, candidate, base_time: datetime = None) -> int:
        base_time = base_time or candidate.updated_at or candidate.created_at
        if not base_time:
            return 0
        delta = datetime.now() - base_time
        return max(delta.days, 0)

    def _last_action_at(self, candidate):
        times = [
            candidate.updated_at,
            candidate.created_at,
        ]
        try:
            times.extend([log.created_at for log in candidate.activity_logs if log.created_at])
        except Exception:
            pass
        try:
            times.extend([log.created_at for log in candidate.stage_change_logs if log.created_at])
        except Exception:
            pass
        valid_times = [time for time in times if time]
        return max(valid_times) if valid_times else None

    def _overdue_result(self, is_overdue: bool, overdue_days: int, reason: str, suggestion: str) -> dict:
        return {
            "is_overdue": is_overdue,
            "overdue_days": overdue_days if is_overdue else 0,
            "overdue_reason": reason,
            "suggestion": suggestion,
        }

    def _has_resume(self, candidate) -> bool:
        return bool((candidate.resume_filename or "").strip() or (candidate.resume_path or "").strip())

    def _missing_key_fields(self, candidate) -> List[str]:
        fields = []
        if not (candidate.phone or "").strip():
            fields.append("手机号")
        if not (candidate.email or "").strip():
            fields.append("邮箱")
        if not (candidate.target_role or "").strip():
            fields.append("应聘岗位")
        return fields

    def _skills(self, candidate) -> List[str]:
        skills = candidate.skills
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = []
        return skills if isinstance(skills, list) else []


followup_service = FollowupService()
