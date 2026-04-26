import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..models.activity_log import ActivityLog
from ..models.candidate import Candidate
from ..models.stage_change_log import StageChangeLog
from ..schemas.candidate import CandidateCreate, CandidateUpdate, HRActionRequest
from .ai_service import ai_service
from .dedup_service import dedup_service
from .file_parser import file_parser
from .followup_service import PRIORITY_RANK, followup_service
from .sync_adapter import sync_adapter


STAGE_SOURCE_LABELS = {
    "system_auto": "系统自动",
    "hr_action": "HR操作",
    "manual": "人工修正",
}

FORMAL_STAGES = ["待约面", "已约面", "面试中", "复试", "offer", "入职", "淘汰"]
SCREENING_POOL_STATUSES = ["pending"]
VALID_SCREENING_STATUSES = ["pending", "passed", "backup", "rejected"]


class CandidateService:
    def create_candidate(self, db: Session, data: CandidateCreate, source: str = "HR手动录入") -> Candidate:
        skills_json = json.dumps(data.skills or [], ensure_ascii=False)
        job_id = data.job_id
        target_role = data.target_role or ""
        if job_id:
            from .job_service import job_service
            job = job_service.get_active_job(db, job_id)
            if not job:
                raise ValueError("所选岗位不存在或已停用")
            target_role = job.title

        candidate = Candidate(
            name=data.name,
            phone=data.phone,
            email=data.email or "",
            school=data.school or "",
            degree=data.degree or "",
            major=data.major or "",
            job_id=job_id,
            target_role=target_role,
            experience_years=data.experience_years or 0,
            experience_desc=data.experience_desc or "",
            skills=skills_json,
            self_intro=data.self_intro or "",
            source_channel=data.source_channel or source,
            stage="新投递",
            screening_status="pending",
            hr_notes=data.hr_notes or "",
        )

        dup_id = dedup_service.check_duplicate(db, {
            "phone": candidate.phone,
            "email": candidate.email,
            "name": candidate.name,
            "school": candidate.school,
            "target_role": candidate.target_role,
        })

        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        if dup_id:
            dedup_service.mark_duplicate(db, candidate.id, dup_id)
            self._log(db, candidate.id, "duplicate_found", f"发现与候选人#{dup_id}重复")

        created_detail = f"候选人{candidate.name}通过{source}录入系统"
        if source == "HR手动录入":
            created_detail = f"HR新增候选人：{candidate.name}（渠道：{candidate.source_channel}）"

        self._log(db, candidate.id, "created", created_detail)

        self._run_ai(db, candidate)
        self._sync(candidate)

        return candidate

    def create_from_resume(
        self,
        db: Session,
        file_path: str,
        raw_text: str,
        original_filename: str = "",
        file_size: Optional[int] = None,
        uploaded_at: Optional[datetime] = None,
    ) -> Candidate:
        extracted = ai_service.extract_resume(raw_text)

        data = CandidateCreate(
            name=extracted.get("name") or "未知",
            phone=extracted.get("phone") or "13800000000",
            email=extracted.get("email") or "",
            school=extracted.get("school", ""),
            degree=extracted.get("degree", ""),
            major=extracted.get("major", ""),
            target_role=extracted.get("target_role", ""),
            experience_years=extracted.get("experience_years", 0),
            experience_desc=extracted.get("experience_desc", ""),
            skills=extracted.get("skills", []),
            self_intro=extracted.get("self_intro", ""),
            source_channel="简历上传",
        )

        candidate = self.create_candidate(db, data, source="简历上传")
        candidate = self.attach_resume(
            db,
            candidate,
            file_path=file_path,
            original_filename=original_filename,
            file_size=file_size,
            uploaded_at=uploaded_at,
        )

        from .stage_service import stage_service
        candidate = stage_service.change_stage(
            db, candidate, "待筛选", "system_auto", "简历上传解析完成，自动进入待筛选",
        )

        return candidate

    def attach_resume(
        self,
        db: Session,
        candidate: Candidate,
        file_path: str,
        original_filename: str = "",
        file_size: Optional[int] = None,
        uploaded_at: Optional[datetime] = None,
    ) -> Candidate:
        resume_file = Path(file_path)
        sanitized_filename = Path(original_filename).name if original_filename else ""
        file_type = ""
        if sanitized_filename:
            file_type = Path(sanitized_filename).suffix.lower().lstrip(".")
        if not file_type:
            file_type = resume_file.suffix.lower().lstrip(".")

        actual_size = file_size
        if actual_size is None and resume_file.exists():
            actual_size = resume_file.stat().st_size

        candidate.resume_path = file_path
        candidate.resume_filename = sanitized_filename or resume_file.name
        candidate.resume_file_type = file_type
        candidate.resume_file_size = actual_size
        candidate.resume_uploaded_at = uploaded_at or datetime.now()
        candidate.updated_at = uploaded_at or datetime.now()
        db.commit()
        db.refresh(candidate)
        return candidate

    def get_candidate(self, db: Session, candidate_id: int) -> Optional[Candidate]:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            from .stage_service import stage_service
            candidate = stage_service.check_auto_interview_start(db, candidate)
        return candidate

    def list_candidates(
        self, db: Session,
        stage: str = None, channel: str = None, keyword: str = None,
        target_role: str = None,
        candidate_scope: str = "formal",
        screening_status: str = None,
        is_today_new: bool = False,
        page: int = 1, page_size: int = 20,
    ) -> Tuple[List[Candidate], int]:
        self._refresh_pending_stage_updates(db)
        query = db.query(Candidate)

        if target_role:
            query = query.filter(Candidate.target_role == target_role)
        if screening_status:
            query = query.filter(Candidate.screening_status == screening_status)
        elif candidate_scope == "backup":
            query = query.filter(Candidate.screening_status == "backup")
        elif candidate_scope == "rejected":
            query = query.filter(or_(
                Candidate.screening_status == "rejected",
                Candidate.stage == "淘汰",
            ))
        else:
            query = query.filter(
                Candidate.screening_status == "passed",
                Candidate.stage != "淘汰",
            )
        if stage:
            query = query.filter(Candidate.stage == stage)
        if channel:
            query = query.filter(Candidate.source_channel == channel)
        if is_today_new:
            today_start, tomorrow_start = self._today_bounds()
            query = query.filter(
                Candidate.created_at >= today_start,
                Candidate.created_at < tomorrow_start,
            )
        if keyword:
            query = query.filter(or_(
                Candidate.name.contains(keyword),
                Candidate.phone.contains(keyword),
                Candidate.email.contains(keyword),
                Candidate.school.contains(keyword),
                Candidate.major.contains(keyword),
                Candidate.target_role.contains(keyword),
                Candidate.skills.contains(keyword),
            ))

        total = query.count()
        candidates = query.order_by(Candidate.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return candidates, total

    def get_filter_options(self, db: Session) -> dict:
        self._refresh_pending_stage_updates(db)
        from ..models.job import Job

        job_rows = db.query(Job.title).filter(
            Job.title.isnot(None),
            Job.title != "",
        ).distinct().all()
        role_rows = db.query(Candidate.target_role).filter(
            Candidate.target_role.isnot(None),
            Candidate.target_role != "",
        ).distinct().all()

        channel_rows = db.query(Candidate.source_channel).filter(
            Candidate.source_channel.isnot(None),
            Candidate.source_channel != "",
        ).distinct().order_by(Candidate.source_channel.asc()).all()

        return {
            "target_roles": sorted({row[0] for row in job_rows}.union({row[0] for row in role_rows})),
            "source_channels": [row[0] for row in channel_rows],
        }

    def update_candidate(self, db: Session, candidate_id: int, data: CandidateUpdate) -> Optional[Candidate]:
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "job_id" in update_data and update_data["job_id"]:
            from .job_service import job_service
            job = job_service.get_active_job(db, update_data["job_id"])
            if not job:
                raise ValueError("所选岗位不存在或已停用")
            update_data["target_role"] = job.title
        if "skills" in update_data and isinstance(update_data["skills"], list):
            update_data["skills"] = json.dumps(update_data["skills"], ensure_ascii=False)

        for key, value in update_data.items():
            setattr(candidate, key, value)

        candidate.updated_at = func.now()
        db.commit()
        db.refresh(candidate)

        self._log(db, candidate_id, "updated", f"更新了候选人{candidate.name}的信息")
        self._sync(candidate)
        return candidate

    def update_stage(self, db: Session, candidate_id: int, new_stage: str) -> Optional[Candidate]:
        from .stage_service import stage_service
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return None
        candidate = stage_service.manual_override(db, candidate, new_stage)
        self._sync(candidate)
        return candidate

    def delete_candidate(self, db: Session, candidate_id: int) -> bool:
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return False
        db.delete(candidate)
        db.commit()
        return True

    def execute_hr_action(
        self, db: Session, candidate_id: int, action_name: str, data: HRActionRequest,
    ) -> Optional[Candidate]:
        if action_name == "pass_screening":
            return self.pass_screening(db, candidate_id)

        from .stage_service import stage_service
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return None
        was_in_screening_pool = candidate.screening_status in SCREENING_POOL_STATUSES
        candidate = stage_service.execute_hr_action(
            db, candidate, action_name,
            interview_time=data.interview_time,
            reason=data.reason or "",
            interview_method=data.interview_method or "",
            interviewer=data.interviewer or "",
            interview_note=data.interview_note or "",
            recheck_note=data.recheck_note or "",
            second_interview_time=data.second_interview_time,
            second_interviewer=data.second_interviewer or "",
            offer_position=data.offer_position or "",
            salary_range=data.salary_range or "",
            expected_onboard_date=data.expected_onboard_date,
            offer_note=data.offer_note or "",
            onboard_date=data.onboard_date,
            onboard_note=data.onboard_note or "",
            reject_reason=data.reject_reason or "",
            reject_note=data.reject_note or "",
        )
        if action_name == "mark_eliminated" and was_in_screening_pool:
            candidate.screening_status = "rejected"
            candidate.updated_at = datetime.now()
            db.commit()
            db.refresh(candidate)
            self._log(db, candidate.id, "screening_rejected", f"初筛淘汰：{candidate.reject_reason or data.reason or '未填写原因'}")
        self._sync(candidate)
        return candidate

    def pass_screening(self, db: Session, candidate_id: int) -> Optional[Candidate]:
        from .stage_service import stage_service

        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return None
        if candidate.stage in ["入职", "淘汰"]:
            raise ValueError("流程已结束的候选人不能直接通过初筛，请先人工修正阶段")

        old_status = candidate.screening_status or "pending"
        candidate.screening_status = "passed"
        candidate.updated_at = datetime.now()
        db.flush()

        if candidate.stage in ["新投递", "待筛选"]:
            candidate = stage_service.change_stage(
                db,
                candidate,
                "待约面",
                "hr_action",
                "通过初筛，进入正式招聘流程",
            )
        else:
            db.commit()
            db.refresh(candidate)
        self._log(
            db,
            candidate.id,
            "screening_passed",
            f"通过初筛：{old_status} -> passed，候选人进入待约面",
        )
        self._sync(candidate)
        return candidate

    def mark_screening_backup(self, db: Session, candidate_id: int) -> Optional[Candidate]:
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return None
        if candidate.screening_status != "passed" or candidate.stage == "淘汰":
            raise ValueError("只有已通过初筛且未淘汰的正式流程候选人可以标记为备选")
        old_status = candidate.screening_status or "pending"
        candidate.screening_status = "backup"
        candidate.updated_at = datetime.now()
        db.commit()
        db.refresh(candidate)
        self._log(
            db,
            candidate.id,
            "screening_backup",
            f"正式流程标记备选：{old_status} -> backup，候选人进入候选人列表备选视图",
        )
        self._sync(candidate)
        return candidate

    def reject_screening(
        self,
        db: Session,
        candidate_id: int,
        reject_reason: str,
        reject_note: str = "",
    ) -> Optional[Candidate]:
        from .stage_service import stage_service

        reason = (reject_reason or "").strip()
        if not reason:
            raise ValueError("初筛淘汰必须填写淘汰原因")

        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return None

        old_status = candidate.screening_status or "pending"
        candidate.screening_status = "rejected"
        candidate.reject_reason = reason
        candidate.reject_note = (reject_note or "").strip()
        candidate.updated_at = datetime.now()
        db.flush()

        candidate = stage_service.change_stage(
            db,
            candidate,
            "淘汰",
            "hr_action",
            f"初筛淘汰: {reason}",
        )
        self._log(
            db,
            candidate.id,
            "screening_rejected",
            f"初筛淘汰：{old_status} -> rejected，原因：{reason}",
        )
        self._sync(candidate)
        return candidate

    def batch_update_stage(
        self,
        db: Session,
        candidate_ids: List[int],
        target_stage: str,
        reason: str,
        source: str = "hr_action",
    ) -> dict:
        from ..schemas.candidate import VALID_STAGES
        from .stage_service import stage_service

        if not candidate_ids:
            raise ValueError("candidate_ids 不能为空")
        if target_stage not in VALID_STAGES:
            raise ValueError(f"无效阶段: {target_stage}")
        if source not in ["hr_action", "manual", "system_auto"]:
            raise ValueError("source 必须为 hr_action / manual / system_auto")

        candidates = db.query(Candidate).filter(Candidate.id.in_(candidate_ids)).all()
        candidate_map = {candidate.id: candidate for candidate in candidates}

        items = []
        for candidate_id in candidate_ids:
            candidate = candidate_map.get(candidate_id)
            if not candidate:
                items.append({
                    "candidate_id": candidate_id,
                    "name": "",
                    "success": False,
                    "message": "候选人不存在",
                    "from_stage": None,
                    "to_stage": target_stage,
                })
                continue

            old_stage = candidate.stage
            try:
                if target_stage in FORMAL_STAGES and target_stage != "淘汰":
                    candidate.screening_status = "passed"
                elif target_stage == "淘汰" and candidate.screening_status in ["pending", "backup"]:
                    candidate.screening_status = "rejected"
                candidate.updated_at = datetime.now()
                db.flush()
                updated = stage_service.change_stage(db, candidate, target_stage, source, reason)
                self._sync(updated)
                items.append({
                    "candidate_id": candidate.id,
                    "name": candidate.name,
                    "success": True,
                    "message": "阶段已更新" if old_stage != target_stage else "阶段未变化",
                    "from_stage": old_stage,
                    "to_stage": updated.stage,
                })
            except Exception as exc:
                db.rollback()
                items.append({
                    "candidate_id": candidate.id,
                    "name": candidate.name,
                    "success": False,
                    "message": str(exc),
                    "from_stage": old_stage,
                    "to_stage": target_stage,
                })

        return self._batch_response(items)

    def batch_generate_followups(self, db: Session, candidate_ids: List[int]) -> dict:
        if not candidate_ids:
            raise ValueError("candidate_ids 不能为空")

        candidates = db.query(Candidate).filter(Candidate.id.in_(candidate_ids)).all()
        candidate_map = {candidate.id: candidate for candidate in candidates}

        items = []
        for candidate_id in candidate_ids:
            candidate = candidate_map.get(candidate_id)
            if not candidate:
                items.append({
                    "candidate_id": candidate_id,
                    "name": "",
                    "success": False,
                    "message": "候选人不存在",
                    "from_stage": None,
                    "to_stage": None,
                })
                continue

            suggestion = followup_service.generate_followup_suggestion(candidate)
            self._log(
                db,
                candidate.id,
                "ai_followup",
                f"批量生成AI跟进建议：{suggestion.get('followup_priority', '')}优先级，{suggestion.get('followup_reason', '')}",
            )
            items.append({
                "candidate_id": candidate.id,
                "name": candidate.name,
                "success": True,
                "message": suggestion.get("followup_suggestion", ""),
                "from_stage": candidate.stage,
                "to_stage": candidate.stage,
            })

        return self._batch_response(items)

    def get_candidates_by_ids(self, db: Session, candidate_ids: List[int]) -> List[Candidate]:
        if not candidate_ids:
            raise ValueError("candidate_ids 不能为空")
        candidates = db.query(Candidate).filter(Candidate.id.in_(candidate_ids)).all()
        candidate_map = {candidate.id: candidate for candidate in candidates}
        return [candidate_map[candidate_id] for candidate_id in candidate_ids if candidate_id in candidate_map]

    def log_batch_export(self, db: Session, candidates: List[Candidate]):
        for candidate in candidates:
            self._log(db, candidate.id, "batch_export_csv", f"批量导出CSV：{candidate.name}")

    def get_stage_change_logs(self, db: Session, candidate_id: int) -> List[dict]:
        logs = db.query(StageChangeLog).filter(
            StageChangeLog.candidate_id == candidate_id,
        ).order_by(StageChangeLog.created_at.desc()).all()
        return [
            {
                "id": log.id,
                "candidate_id": log.candidate_id,
                "from_stage": log.from_stage,
                "to_stage": log.to_stage,
                "trigger_reason": log.trigger_reason,
                "trigger_source": log.trigger_source,
                "created_at": log.created_at,
            }
            for log in logs
        ]

    def regenerate_summary(self, db: Session, candidate_id: int) -> str:
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return ""
        data = self._candidate_to_dict(candidate)
        summary = ai_service.generate_summary(data)
        candidate.ai_summary = summary
        db.commit()
        self._log(db, candidate_id, "ai_processed", "重新生成AI摘要")
        return summary

    def regenerate_tags(self, db: Session, candidate_id: int) -> List[str]:
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return []
        data = self._candidate_to_dict(candidate)
        tags = ai_service.generate_tags(data)
        candidate.ai_tags = json.dumps(tags, ensure_ascii=False)
        db.commit()
        self._log(db, candidate_id, "ai_processed", "重新生成AI标签")
        return tags

    def get_followup_suggestion(self, db: Session, candidate_id: int) -> dict:
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return {}
        return followup_service.generate_followup_suggestion(candidate)

    def generate_interview_summary(
        self,
        db: Session,
        candidate_id: int,
        feedback_text: str,
        interviewer: str = "",
        interview_round: str = "",
        feedback_time: Optional[datetime] = None,
    ) -> Optional[dict]:
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return None

        clean_feedback = (feedback_text or "").strip()
        if not clean_feedback:
            raise ValueError("面试反馈不能为空")

        candidate.interview_feedback_text = clean_feedback
        if interviewer is not None:
            candidate.interviewer = interviewer.strip()
        candidate.interview_round = (interview_round or "").strip()
        candidate.feedback_time = feedback_time or datetime.now()

        data = self._candidate_to_dict(candidate)
        result = ai_service.summarize_interview_feedback(data)
        risk_points = result.get("risk_points") or []
        if not isinstance(risk_points, list):
            risk_points = [str(risk_points)]

        candidate.interview_ai_technical_summary = result.get("technical_summary") or ""
        candidate.interview_ai_communication_summary = result.get("communication_summary") or ""
        candidate.interview_ai_job_match = result.get("job_match") or ""
        candidate.interview_ai_risk_points = json.dumps(risk_points, ensure_ascii=False)
        candidate.interview_ai_recommendation = result.get("recommendation") or "待定"
        candidate.interview_ai_next_step = result.get("next_step") or ""
        candidate.interview_ai_generated_at = datetime.now()
        candidate.updated_at = datetime.now()
        db.commit()
        db.refresh(candidate)

        self._log(
            db,
            candidate.id,
            "ai_interview_summary",
            f"生成 AI 面试总结（来源：ai/system_auto，推荐结论：{candidate.interview_ai_recommendation}）",
        )
        self._sync(candidate)
        return self._interview_summary_to_dict(candidate)

    def run_screening_for_candidate(self, db: Session, candidate_id: int) -> Optional[Candidate]:
        candidate = self.get_candidate(db, candidate_id)
        if not candidate:
            return None
        candidate = self._apply_screening(db, candidate)
        self._sync(candidate)
        return candidate

    def _apply_screening_filters(
        self,
        query,
        target_role: str = None,
        priority_level: str = None,
        screening_status: str = None,
        decision_status: str = None,
        start_date: date = None,
        end_date: date = None,
    ):
        if target_role:
            query = query.filter(Candidate.target_role.contains(target_role))
        if priority_level:
            query = query.filter(Candidate.priority_level == priority_level)
        if screening_status == "screened":
            query = query.filter(or_(
                Candidate.match_score.isnot(None),
                and_(Candidate.priority_level.isnot(None), Candidate.priority_level != ""),
            ))
        elif screening_status == "unscreened":
            query = query.filter(
                Candidate.match_score.is_(None),
                or_(Candidate.priority_level.is_(None), Candidate.priority_level == ""),
            )
        decision_statuses = self._parse_screening_statuses(decision_status)
        if decision_statuses:
            query = query.filter(Candidate.screening_status.in_(decision_statuses))
        if start_date:
            query = query.filter(Candidate.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(Candidate.created_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
        return query

    def run_pending_screening(
        self,
        db: Session,
        target_role: str = None,
        priority_level: str = None,
        screening_status: str = None,
        decision_status: str = None,
        start_date: date = None,
        end_date: date = None,
    ) -> List[Candidate]:
        self._refresh_pending_stage_updates(db)
        query = db.query(Candidate)
        query = self._apply_screening_filters(
            query,
            target_role=target_role,
            priority_level=priority_level,
            screening_status=screening_status,
            decision_status=decision_status,
            start_date=start_date,
            end_date=end_date,
        )
        candidates = query.order_by(Candidate.created_at.desc(), Candidate.id.desc()).all()

        screened = []
        for candidate in candidates:
            screened.append(self._apply_screening(db, candidate))
        return screened

    def list_screening_results(
        self,
        db: Session,
        target_role: str = None,
        priority_level: str = None,
        screening_status: str = None,
        decision_status: str = None,
        sort_by: str = "score_desc",
        sort_order: str = "desc",
        start_date: date = None,
        end_date: date = None,
    ) -> List[Candidate]:
        self._refresh_pending_stage_updates(db)
        query = db.query(Candidate)
        query = self._apply_screening_filters(
            query,
            target_role=target_role,
            priority_level=priority_level,
            screening_status=screening_status,
            decision_status=decision_status,
            start_date=start_date,
            end_date=end_date,
        )

        if sort_by == "score_asc":
            query = query.order_by(
                Candidate.match_score.is_(None),
                Candidate.match_score.asc(),
                Candidate.created_at.desc(),
            )
        elif sort_by == "updated_desc":
            query = query.order_by(
                Candidate.screening_updated_at.is_(None),
                Candidate.screening_updated_at.desc(),
                Candidate.match_score.desc(),
            )
        elif sort_by == "created_at":
            created_sort = Candidate.created_at.asc() if sort_order == "asc" else Candidate.created_at.desc()
            query = query.order_by(created_sort, Candidate.id.desc())
        else:
            query = query.order_by(
                Candidate.match_score.is_(None),
                Candidate.match_score.desc(),
                Candidate.screening_updated_at.desc(),
            )
        return query.all()

    def get_screening_stats(self, db: Session) -> dict:
        self._refresh_pending_stage_updates(db)
        return self.build_screening_stats(db.query(Candidate))

    def build_screening_stats(self, query) -> dict:
        candidates = query.all()
        total = len(candidates)
        high = 0
        medium = 0
        low = 0
        unscreened = 0
        pending = 0
        passed = 0
        backup = 0
        rejected = 0
        scores = []
        for candidate in candidates:
            status = candidate.screening_status or "pending"
            if status == "passed":
                passed += 1
            elif status == "backup":
                backup += 1
            elif status == "rejected":
                rejected += 1
            else:
                pending += 1
            priority = (candidate.priority_level or "").strip()
            is_screened = candidate.match_score is not None or bool(priority)
            if candidate.match_score is not None:
                scores.append(candidate.match_score)
            if not is_screened:
                unscreened += 1
            elif priority == "高优先级":
                high += 1
            elif priority == "中优先级":
                medium += 1
            else:
                low += 1
        screened = high + medium + low
        average = sum(scores) / len(scores) if scores else None
        return {
            "total_candidates": total,
            "screened_count": screened,
            "high_priority_count": high,
            "medium_priority_count": medium,
            "low_priority_count": low,
            "average_match_score": round(float(average), 1) if average is not None else 0,
            "unscreened_count": unscreened,
            "pending_count": pending,
            "passed_count": passed,
            "backup_count": backup,
            "rejected_count": rejected,
            "formal_candidate_count": passed,
        }

    def get_screening_results_with_stats(
        self,
        db: Session,
        target_role: str = None,
        priority_level: str = None,
        screening_status: str = None,
        decision_status: str = None,
        sort_by: str = "score_desc",
        sort_order: str = "desc",
        start_date: date = None,
        end_date: date = None,
    ) -> dict:
        self._refresh_pending_stage_updates(db)
        query = db.query(Candidate)
        query = self._apply_screening_filters(
            query,
            target_role=target_role,
            priority_level=priority_level,
            screening_status=screening_status,
            decision_status=decision_status,
            start_date=start_date,
            end_date=end_date,
        )
        filtered_stats = self.build_screening_stats(query)

        if sort_by == "score_asc":
            query = query.order_by(
                Candidate.match_score.is_(None),
                Candidate.match_score.asc(),
                Candidate.created_at.desc(),
            )
        elif sort_by == "updated_desc":
            query = query.order_by(
                Candidate.screening_updated_at.is_(None),
                Candidate.screening_updated_at.desc(),
                Candidate.match_score.desc(),
            )
        elif sort_by == "created_at":
            created_sort = Candidate.created_at.asc() if sort_order == "asc" else Candidate.created_at.desc()
            query = query.order_by(created_sort, Candidate.id.desc())
        else:
            query = query.order_by(
                Candidate.match_score.is_(None),
                Candidate.match_score.desc(),
                Candidate.screening_updated_at.desc(),
            )

        return {
            "items": query.all(),
            "total": filtered_stats["total_candidates"],
            "stats": filtered_stats,
            "overall_stats": self.get_screening_stats(db),
        }

    def get_followup_summary(self, db: Session, limit: int = 5) -> dict:
        self._refresh_pending_stage_updates(db)
        candidates = db.query(Candidate).filter(
            Candidate.is_duplicate == False,
        ).all()
        return followup_service.build_dashboard_summary(candidates, limit=limit)

    def get_role_distribution(self, db: Session) -> List[dict]:
        self._refresh_pending_stage_updates(db)
        candidates = db.query(Candidate).filter(Candidate.is_duplicate == False).all()
        grouped = {}
        for candidate in candidates:
            role = (candidate.target_role or "未填写岗位").strip() or "未填写岗位"
            if role not in grouped:
                grouped[role] = {
                    "target_role": role,
                    "count": 0,
                    "high_priority_count": 0,
                    "followup_count": 0,
                }
            grouped[role]["count"] += 1
            if candidate.priority_level == "高优先级":
                grouped[role]["high_priority_count"] += 1
            followup = followup_service.generate_followup_suggestion(candidate)
            if followup.get("followup_priority") == "高":
                grouped[role]["followup_count"] += 1

        rows = list(grouped.values())
        rows.sort(
            key=lambda item: (
                item["count"],
                item["high_priority_count"],
                item["followup_count"],
            ),
            reverse=True,
        )
        return rows

    def get_follow_up_alerts(self, db: Session) -> List[dict]:
        self._refresh_pending_stage_updates(db)
        active_stages = ["新投递", "待筛选", "待约面", "已约面", "面试中", "复试", "offer"]
        candidates = db.query(Candidate).filter(
            Candidate.stage.in_(active_stages),
            Candidate.is_duplicate == False,
        ).all()

        alerts = []
        for c in candidates:
            suggestion = followup_service.generate_followup_suggestion(c)
            if suggestion.get("is_overdue"):
                alerts.append({
                    "candidate_id": c.id,
                    "name": c.name,
                    "target_role": c.target_role,
                    "stage": c.stage,
                    "days_since_update": suggestion.get("followup_days_since_update", 0),
                    "is_overdue": suggestion.get("is_overdue", False),
                    "overdue_days": suggestion.get("overdue_days", 0),
                    "overdue_reason": suggestion.get("overdue_reason", ""),
                    "followup_priority": suggestion.get("followup_priority", "低"),
                    "followup_suggestion": suggestion.get("followup_suggestion", ""),
                    "last_action_at": suggestion.get("last_action_at"),
                })

        alerts.sort(
            key=lambda x: (
                PRIORITY_RANK.get(x.get("followup_priority", ""), 0),
                x.get("overdue_days", 0),
                x.get("days_since_update", 0),
            ),
            reverse=True,
        )
        return alerts

    def get_dashboard_stats(self, db: Session) -> dict:
        from ..schemas.candidate import VALID_STAGES

        self._refresh_pending_stage_updates(db)
        total = db.query(Candidate).count()

        today = date.today()
        today_start, tomorrow_start = self._today_bounds()
        recent_start = datetime.combine(today - timedelta(days=2), datetime.min.time())
        new_today = db.query(Candidate).filter(
            Candidate.created_at >= today_start,
            Candidate.created_at < tomorrow_start,
            Candidate.is_duplicate == False,
        ).count()
        new_last_3_days = db.query(Candidate).filter(
            Candidate.created_at >= recent_start,
            Candidate.created_at < tomorrow_start,
            Candidate.is_duplicate == False,
        ).count()
        today_new_rows = db.query(Candidate).filter(
            Candidate.created_at >= today_start,
            Candidate.created_at < tomorrow_start,
            Candidate.is_duplicate == False,
        ).order_by(
            Candidate.created_at.desc(),
            Candidate.id.desc(),
        ).limit(5).all()

        pending_screening_count = db.query(Candidate).filter(
            Candidate.screening_status == "pending",
            Candidate.is_duplicate == False,
        ).count()
        passed_screening_count = db.query(Candidate).filter(
            Candidate.screening_status == "passed",
            Candidate.is_duplicate == False,
        ).count()
        backup_screening_count = db.query(Candidate).filter(
            Candidate.screening_status == "backup",
            Candidate.is_duplicate == False,
        ).count()
        rejected_screening_count = db.query(Candidate).filter(
            or_(
                Candidate.screening_status == "rejected",
                Candidate.stage == "淘汰",
            ),
            Candidate.is_duplicate == False,
        ).count()

        in_pipeline = db.query(Candidate).filter(
            Candidate.screening_status == "passed",
            Candidate.stage != "淘汰",
            Candidate.is_duplicate == False,
        ).count()

        offer_count = db.query(Candidate).filter(
            Candidate.stage == "offer",
            Candidate.is_duplicate == False,
        ).count()

        funnel = []
        for stage in VALID_STAGES:
            count = db.query(Candidate).filter(
                Candidate.stage == stage,
                Candidate.is_duplicate == False,
            ).count()
            funnel.append({"stage": stage, "count": count})

        channel_rows = db.query(
            Candidate.source_channel, func.count(Candidate.id)
        ).filter(Candidate.is_duplicate == False).group_by(
            Candidate.source_channel
        ).all()
        channels = [{"channel": ch, "count": cnt} for ch, cnt in channel_rows]

        return {
            "total_candidates": total,
            "new_today": new_today,
            "new_last_3_days": new_last_3_days,
            "in_pipeline": in_pipeline,
            "offer_count": offer_count,
            "pending_screening_count": pending_screening_count,
            "passed_screening_count": passed_screening_count,
            "backup_screening_count": backup_screening_count,
            "rejected_screening_count": rejected_screening_count,
            "formal_candidate_count": in_pipeline,
            "funnel": funnel,
            "channels": channels,
            "screening_stats": self.get_screening_stats(db),
            "followup_summary": self.get_followup_summary(db),
            "role_distribution": self.get_role_distribution(db),
            "today_new_candidates": [
                {
                    "candidate_id": c.id,
                    "name": c.name,
                    "target_role": c.target_role,
                    "source_channel": c.source_channel,
                    "created_at": c.created_at,
                    "new_candidate_label": "今日新增",
                }
                for c in today_new_rows
            ],
        }

    def get_recent_logs(self, db: Session, limit: int = 20) -> List[dict]:
        self._refresh_pending_stage_updates(db)
        activity_logs = db.query(ActivityLog).filter(
            ActivityLog.action != "stage_changed",
        ).order_by(
            ActivityLog.created_at.desc(),
            ActivityLog.id.desc(),
        ).limit(limit * 3).all()
        stage_logs = db.query(StageChangeLog).order_by(
            StageChangeLog.created_at.desc(),
            StageChangeLog.id.desc(),
        ).limit(limit * 3).all()

        candidate_ids = {log.candidate_id for log in activity_logs}
        candidate_ids.update(log.candidate_id for log in stage_logs)
        candidate_map = {}
        if candidate_ids:
            candidate_rows = db.query(Candidate.id, Candidate.name).filter(
                Candidate.id.in_(candidate_ids),
            ).all()
            candidate_map = {candidate_id: name for candidate_id, name in candidate_rows}

        result = []
        for log in activity_logs:
            result.append({
                "id": log.id,
                "candidate_id": log.candidate_id,
                "candidate_name": candidate_map.get(log.candidate_id, "未知"),
                "action": log.action,
                "detail": log.detail,
                "from_stage": None,
                "to_stage": None,
                "trigger_reason": None,
                "trigger_source": None,
                "created_at": log.created_at,
                "updated_at": log.created_at,
            })

        for log in stage_logs:
            candidate_name = candidate_map.get(log.candidate_id, "未知")
            result.append({
                "id": log.id,
                "candidate_id": log.candidate_id,
                "candidate_name": candidate_name,
                "action": "stage_changed",
                "detail": self._format_stage_change_detail(
                    candidate_name,
                    log.from_stage,
                    log.to_stage,
                    log.trigger_reason,
                    log.trigger_source,
                ),
                "from_stage": log.from_stage,
                "to_stage": log.to_stage,
                "trigger_reason": log.trigger_reason,
                "trigger_source": log.trigger_source,
                "created_at": log.created_at,
                "updated_at": log.created_at,
            })

        result.sort(
            key=lambda item: (
                item["created_at"] or datetime.min,
                item["updated_at"] or datetime.min,
                item["id"],
            ),
            reverse=True,
        )
        return result[:limit]

    def get_daily_summary(self, db: Session, target_date: date = None) -> dict:
        if target_date is None:
            target_date = date.today()

        self._refresh_pending_stage_updates(db)

        new_count = db.query(Candidate).filter(
            func.date(Candidate.created_at) == target_date,
        ).count()

        stage_changes = db.query(StageChangeLog).filter(
            func.date(StageChangeLog.created_at) == target_date,
        ).count()

        summary = f"日期: {target_date}\n新增候选人: {new_count}位\n状态变更: {stage_changes}次\n"
        if new_count > 0:
            summary += "招聘漏斗运转正常，建议及时跟进新投递候选人。"
        else:
            summary += "今日暂无新增候选人，建议关注现有候选人的面试安排和状态推进。"

        return {
            "date": str(target_date),
            "new_count": new_count,
            "stage_changes": stage_changes,
            "summary_text": summary,
        }

    def _run_ai(self, db: Session, candidate: Candidate):
        data = self._candidate_to_dict(candidate)
        try:
            summary = ai_service.generate_summary(data)
            tags = ai_service.generate_tags(data)
            candidate.ai_summary = summary
            candidate.ai_tags = json.dumps(tags, ensure_ascii=False)
            db.commit()
            self._log(db, candidate.id, "ai_processed", "AI自动生成摘要和标签")
        except Exception:
            pass

    def _apply_screening(self, db: Session, candidate: Candidate) -> Candidate:
        data = self._candidate_to_dict(candidate)
        data["resume_text"] = self._load_resume_text(candidate)
        data["job_profile"] = self._get_job_profile(db, candidate)
        result = ai_service.screen_candidate(data)

        candidate.match_score = result.get("match_score")
        candidate.priority_level = result.get("priority_level") or ""
        candidate.screening_result = result.get("screening_result") or ""
        candidate.screening_reason = result.get("screening_reason") or ""
        risk_flags = result.get("risk_flags") or []
        if not isinstance(risk_flags, list):
            risk_flags = [str(risk_flags)]
        candidate.risk_flags = json.dumps(risk_flags, ensure_ascii=False)
        candidate.screening_updated_at = datetime.now()
        candidate.updated_at = datetime.now()
        db.commit()
        db.refresh(candidate)
        self._log(
            db,
            candidate.id,
            "ai_screened",
            f"AI初筛完成：{candidate.match_score}分，{candidate.priority_level}，{candidate.screening_result}",
        )
        return candidate

    def _get_job_profile(self, db: Session, candidate: Candidate) -> dict:
        from ..models.job import Job

        job = None
        if candidate.job_id:
            job = db.query(Job).filter(Job.id == candidate.job_id).first()
        if not job and candidate.target_role:
            job = db.query(Job).filter(func.lower(Job.title) == candidate.target_role.strip().lower()).first()
        if not job:
            return {}
        return {
            "id": job.id,
            "title": job.title,
            "department": job.department or "",
            "description": job.description or "",
            "requirements": job.requirements or "",
            "required_skills": job.required_skills or "",
            "bonus_skills": job.bonus_skills or "",
            "education_requirement": job.education_requirement or "",
            "experience_requirement": job.experience_requirement or "",
            "job_keywords": job.job_keywords or "",
            "risk_keywords": job.risk_keywords or "",
        }

    def _load_resume_text(self, candidate: Candidate) -> str:
        if not candidate.resume_path:
            return ""
        try:
            resume_file = Path(candidate.resume_path)
            if not resume_file.exists():
                return ""
            return file_parser.parse(str(resume_file))[:2000]
        except Exception:
            return ""

    def _sync(self, candidate: Candidate):
        try:
            data = self._candidate_to_dict(candidate)
            sync_adapter.sync_candidate(data)
        except Exception:
            pass

    def _batch_response(self, items: List[dict]) -> dict:
        success_count = sum(1 for item in items if item.get("success"))
        failed_count = len(items) - success_count
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "items": items,
        }

    def _log(self, db: Session, candidate_id: int, action: str, detail: str):
        log = ActivityLog(
            candidate_id=candidate_id,
            action=action,
            detail=detail,
            created_at=datetime.now(),
        )
        db.add(log)
        db.commit()

    def _interview_summary_to_dict(self, candidate: Candidate) -> dict:
        risk_points = candidate.interview_ai_risk_points
        if isinstance(risk_points, str):
            try:
                risk_points = json.loads(risk_points)
            except Exception:
                risk_points = []
        return {
            "interview_feedback_text": candidate.interview_feedback_text or "",
            "interviewer": candidate.interviewer or "",
            "interview_round": candidate.interview_round or "",
            "feedback_time": candidate.feedback_time,
            "technical_summary": candidate.interview_ai_technical_summary or "",
            "communication_summary": candidate.interview_ai_communication_summary or "",
            "job_match": candidate.interview_ai_job_match or "",
            "risk_points": risk_points or [],
            "recommendation": candidate.interview_ai_recommendation or "",
            "next_step": candidate.interview_ai_next_step or "",
            "generated_at": candidate.interview_ai_generated_at,
        }

    def get_new_candidate_marker(self, candidate: Candidate) -> dict:
        is_today_new = False
        is_recent_3_days_new = False
        if candidate.created_at:
            today_start, tomorrow_start = self._today_bounds()
            recent_start = today_start - timedelta(days=2)
            is_today_new = today_start <= candidate.created_at < tomorrow_start
            is_recent_3_days_new = recent_start <= candidate.created_at < tomorrow_start

        label = ""
        if is_today_new:
            label = "今日新增"
        elif is_recent_3_days_new:
            label = "新投递"

        return {
            "new_candidate_label": label,
            "is_today_new": is_today_new,
            "is_recent_3_days_new": is_recent_3_days_new,
        }

    def _today_bounds(self) -> Tuple[datetime, datetime]:
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        tomorrow_start = today_start + timedelta(days=1)
        return today_start, tomorrow_start

    def _parse_screening_statuses(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        if value == "pool":
            return SCREENING_POOL_STATUSES
        statuses = [
            item.strip()
            for item in value.split(",")
            if item.strip() in VALID_SCREENING_STATUSES
        ]
        return statuses

    def _refresh_pending_stage_updates(self, db: Session):
        from .stage_service import stage_service

        due_candidates = db.query(Candidate).filter(
            Candidate.stage == "已约面",
            Candidate.interview_time.isnot(None),
            Candidate.interview_time <= datetime.now(),
            or_(Candidate.stage_source.is_(None), Candidate.stage_source != "manual"),
        ).order_by(Candidate.interview_time.asc(), Candidate.id.asc()).all()

        for candidate in due_candidates:
            stage_service.check_auto_interview_start(db, candidate)

    def _format_stage_change_detail(
        self,
        candidate_name: str,
        from_stage: str,
        to_stage: str,
        trigger_reason: Optional[str],
        trigger_source: Optional[str],
    ) -> str:
        detail = f"{candidate_name}的状态从「{from_stage}」变更为「{to_stage}」"
        if trigger_source and trigger_reason:
            source_label = STAGE_SOURCE_LABELS.get(trigger_source, trigger_source)
            detail += f"（{source_label}：{trigger_reason}）"
        elif trigger_reason:
            detail += f"（{trigger_reason}）"
        return detail

    def _candidate_to_dict(self, c: Candidate) -> dict:
        skills = c.skills
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = []
        ai_tags = c.ai_tags
        if isinstance(ai_tags, str):
            try:
                ai_tags = json.loads(ai_tags)
            except Exception:
                ai_tags = []
        risk_flags = c.risk_flags
        if isinstance(risk_flags, str):
            try:
                risk_flags = json.loads(risk_flags)
            except Exception:
                risk_flags = []
        return {
            "id": c.id, "name": c.name, "phone": c.phone, "email": c.email,
            "school": c.school, "degree": c.degree, "major": c.major,
            "job_id": c.job_id,
            "target_role": c.target_role, "experience_years": c.experience_years,
            "experience_desc": c.experience_desc, "skills": skills,
            "self_intro": c.self_intro, "resume_path": c.resume_path,
            "resume_filename": c.resume_filename,
            "resume_file_type": c.resume_file_type,
            "resume_file_size": c.resume_file_size,
            "resume_uploaded_at": str(c.resume_uploaded_at) if c.resume_uploaded_at else "",
            "source_channel": c.source_channel, "stage": c.stage,
            "screening_status": c.screening_status or "pending",
            **self.get_new_candidate_marker(c),
            "interview_time": str(c.interview_time) if c.interview_time else "",
            "interview_method": c.interview_method,
            "interviewer": c.interviewer,
            "interview_note": c.interview_note,
            "interview_feedback_text": c.interview_feedback_text,
            "interview_round": c.interview_round,
            "feedback_time": str(c.feedback_time) if c.feedback_time else "",
            "interview_ai_technical_summary": c.interview_ai_technical_summary,
            "interview_ai_communication_summary": c.interview_ai_communication_summary,
            "interview_ai_job_match": c.interview_ai_job_match,
            "interview_ai_risk_points": self._interview_summary_to_dict(c).get("risk_points", []),
            "interview_ai_recommendation": c.interview_ai_recommendation,
            "interview_ai_next_step": c.interview_ai_next_step,
            "interview_ai_generated_at": str(c.interview_ai_generated_at) if c.interview_ai_generated_at else "",
            "recheck_note": c.recheck_note,
            "second_interview_time": str(c.second_interview_time) if c.second_interview_time else "",
            "second_interviewer": c.second_interviewer,
            "offer_position": c.offer_position,
            "salary_range": c.salary_range,
            "expected_onboard_date": str(c.expected_onboard_date) if c.expected_onboard_date else "",
            "offer_note": c.offer_note,
            "onboard_date": str(c.onboard_date) if c.onboard_date else "",
            "onboard_note": c.onboard_note,
            "reject_reason": c.reject_reason,
            "reject_note": c.reject_note,
            "ai_summary": c.ai_summary, "ai_tags": ai_tags,
            "match_score": c.match_score,
            "priority_level": c.priority_level,
            "screening_result": c.screening_result,
            "screening_reason": c.screening_reason,
            "risk_flags": risk_flags,
            "screening_updated_at": str(c.screening_updated_at) if c.screening_updated_at else "",
            **followup_service.generate_followup_suggestion(c),
            "hr_notes": c.hr_notes,
            "created_at": str(c.created_at) if c.created_at else "",
            "updated_at": str(c.updated_at) if c.updated_at else "",
        }


candidate_service = CandidateService()
