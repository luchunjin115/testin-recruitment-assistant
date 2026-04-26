from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models.activity_log import ActivityLog
from ..models.candidate import Candidate
from ..models.stage_change_log import StageChangeLog


HR_ACTION_MAP = {
    "pass_screening":     {"to_stage": "待约面",  "reason": "通过筛选", "allowed": ["新投递", "待筛选"]},
    "set_interview_time": {"to_stage": "已约面",  "reason": "安排面试", "allowed": ["待约面"]},
    "advance_to_retest":  {"to_stage": "复试",   "reason": "一面通过，进入复试", "allowed": ["已约面", "面试中"]},
    "send_offer":         {"to_stage": "offer",  "reason": "发放 Offer", "allowed": ["已约面", "面试中", "复试"]},
    "mark_onboarded":     {"to_stage": "入职",   "reason": "确认入职", "allowed": ["offer"]},
    "mark_eliminated":    {"to_stage": "淘汰",   "reason": "淘汰候选人", "allowed": ["新投递", "待筛选", "待约面", "已约面", "面试中", "复试", "offer"]},
}

STAGE_SOURCE_LABELS = {
    "system_auto": "系统自动",
    "hr_action": "HR操作",
    "manual": "人工修正",
}


class StageService:
    def _clean(self, value: Optional[str]) -> str:
        return value.strip() if isinstance(value, str) else ""

    def _log_hr_action(self, db: Session, candidate: Candidate, detail: str):
        db.add(ActivityLog(
            candidate_id=candidate.id,
            action="hr_action",
            detail=detail,
            created_at=datetime.now(),
        ))
        db.commit()

    def change_stage(
        self,
        db: Session,
        candidate: Candidate,
        new_stage: str,
        trigger_source: str,
        trigger_reason: str,
    ) -> Candidate:
        old_stage = candidate.stage
        changed_at = datetime.now()

        if old_stage == new_stage:
            return candidate

        if trigger_source == "system_auto" and candidate.stage_source == "manual":
            return candidate

        candidate.stage = new_stage
        candidate.stage_source = trigger_source
        candidate.updated_at = changed_at
        db.flush()

        log = StageChangeLog(
            candidate_id=candidate.id,
            from_stage=old_stage,
            to_stage=new_stage,
            trigger_reason=trigger_reason,
            trigger_source=trigger_source,
            created_at=changed_at,
        )
        db.add(log)

        activity = ActivityLog(
            candidate_id=candidate.id,
            action="stage_changed",
            detail=(
                f"{candidate.name}的状态从「{old_stage}」变更为「{new_stage}」"
                f"（{STAGE_SOURCE_LABELS.get(trigger_source, trigger_source)}：{trigger_reason}）"
            ),
            created_at=changed_at,
        )
        db.add(activity)

        db.commit()
        db.refresh(candidate)
        return candidate

    def execute_hr_action(
        self,
        db: Session,
        candidate: Candidate,
        action_name: str,
        interview_time: Optional[datetime] = None,
        reason: Optional[str] = "",
        interview_method: Optional[str] = "",
        interviewer: Optional[str] = "",
        interview_note: Optional[str] = "",
        recheck_note: Optional[str] = "",
        second_interview_time: Optional[datetime] = None,
        second_interviewer: Optional[str] = "",
        offer_position: Optional[str] = "",
        salary_range: Optional[str] = "",
        expected_onboard_date = None,
        offer_note: Optional[str] = "",
        onboard_date = None,
        onboard_note: Optional[str] = "",
        reject_reason: Optional[str] = "",
        reject_note: Optional[str] = "",
    ) -> Candidate:
        action_def = HR_ACTION_MAP.get(action_name)
        if not action_def:
            raise ValueError(f"未知的HR操作: {action_name}")

        if candidate.stage in ["入职", "淘汰"]:
            raise ValueError("候选人流程已结束，如需调整请使用阶段人工修正")

        allowed = action_def.get("allowed", [])
        if allowed and candidate.stage not in allowed:
            raise ValueError(f"当前阶段「{candidate.stage}」不支持该操作")

        target_stage = action_def["to_stage"]
        base_reason = action_def["reason"]
        clean_reason = self._clean(reason)

        if action_name == "set_interview_time":
            if not interview_time:
                raise ValueError("设置面试时间操作必须提供interview_time")
            candidate.interview_time = interview_time
            candidate.interview_method = self._clean(interview_method)
            candidate.interviewer = self._clean(interviewer)
            candidate.interview_note = self._clean(interview_note)
            db.flush()
            parts = [base_reason, interview_time.strftime("%Y-%m-%d %H:%M")]
            if candidate.interview_method:
                parts.append(candidate.interview_method)
            if candidate.interviewer:
                parts.append(f"面试官：{candidate.interviewer}")
            full_reason = "，".join(parts)
            action_detail = f"安排面试：{candidate.name}（{interview_time.strftime('%Y-%m-%d %H:%M')}）"
        elif action_name == "advance_to_retest":
            candidate.recheck_note = self._clean(recheck_note or clean_reason)
            candidate.second_interview_time = second_interview_time
            candidate.second_interviewer = self._clean(second_interviewer)
            db.flush()
            full_reason = f"{base_reason}: {candidate.recheck_note}" if candidate.recheck_note else base_reason
            action_detail = f"一面通过，进入复试：{candidate.name}"
        elif action_name == "send_offer":
            candidate.offer_position = self._clean(offer_position) or candidate.target_role
            candidate.salary_range = self._clean(salary_range)
            candidate.expected_onboard_date = expected_onboard_date
            candidate.offer_note = self._clean(offer_note)
            db.flush()
            full_reason = f"{base_reason}: {candidate.offer_position}" if candidate.offer_position else base_reason
            action_detail = f"发放 Offer：{candidate.name}（{candidate.offer_position or candidate.target_role}）"
        elif action_name == "mark_onboarded":
            candidate.onboard_date = onboard_date
            candidate.onboard_note = self._clean(onboard_note)
            db.flush()
            full_reason = f"{base_reason}: {candidate.onboard_note}" if candidate.onboard_note else base_reason
            action_detail = f"确认入职：{candidate.name}"
        elif action_name == "mark_eliminated":
            candidate.reject_reason = self._clean(reject_reason or clean_reason)
            if not candidate.reject_reason:
                raise ValueError("淘汰候选人必须填写淘汰原因")
            candidate.reject_note = self._clean(reject_note)
            db.flush()
            full_reason = f"{base_reason}: {candidate.reject_reason}"
            action_detail = f"淘汰候选人：{candidate.reject_reason}"
        else:
            full_reason = f"{base_reason}: {clean_reason}" if clean_reason else base_reason
            action_detail = f"{base_reason}：{candidate.name}"

        candidate = self.change_stage(db, candidate, target_stage, "hr_action", full_reason)
        self._log_hr_action(db, candidate, action_detail)
        db.refresh(candidate)
        return candidate

    def manual_override(
        self,
        db: Session,
        candidate: Candidate,
        new_stage: str,
    ) -> Candidate:
        return self.change_stage(db, candidate, new_stage, "manual", "手动修改阶段")

    def check_auto_interview_start(
        self,
        db: Session,
        candidate: Candidate,
    ) -> Candidate:
        if candidate.stage != "已约面":
            return candidate
        if candidate.stage_source == "manual":
            return candidate
        if not candidate.interview_time:
            return candidate
        if datetime.now() >= candidate.interview_time:
            return self.change_stage(
                db, candidate, "面试中", "system_auto",
                "面试时间已到，自动推进",
            )
        return candidate


stage_service = StageService()
