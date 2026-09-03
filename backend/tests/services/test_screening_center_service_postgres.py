from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase

from sqlalchemy import event, func, null, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.job_evaluation_plan import JobEvaluationPlan
from app.models.resume import Resume
from app.models.screening_report import ScreeningReport
from app.schemas.screening_center import ScreeningCenterSort
from app.services.screening_center_service import ScreeningCenterService


NOW = datetime(2026, 9, 3, 6, 0, tzinfo=timezone.utc)
MODELS = (Job, Candidate, Resume, Application, JobEvaluationPlan, ScreeningReport)


async def counts(db: AsyncSession) -> dict[str, int]:
    return {model.__tablename__: int(await db.scalar(select(func.count()).select_from(model)) or 0) for model in MODELS}


class ScreeningCenterServicePostgresTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        settings = Settings(_env_file=None)
        self.engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
        async with AsyncSession(self.engine) as outside:
            self.before = await counts(outside)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.db = AsyncSession(bind=self.connection, expire_on_commit=False, join_transaction_mode="create_savepoint")

    async def asyncTearDown(self) -> None:
        await self.db.close()
        if self.transaction.is_active:
            await self.transaction.rollback()
        await self.connection.close()
        async with AsyncSession(self.engine) as outside:
            after = await counts(outside)
        await self.engine.dispose()
        self.assertEqual(after, self.before)

    async def test_paginated_query_returns_small_evidence_summary_in_two_statements(self) -> None:
        job = Job(title="9C 虚构聚合岗位", status="open")
        candidate = Candidate(name="9C 虚构候选人", phone="13800001234", current_title="后端工程师")
        self.db.add_all([job, candidate])
        await self.db.flush()
        resume = Resume(candidate_id=candidate.id, job_id=job.id, filename="9c-fictional.txt", file_path="tests/9c-fictional.txt", file_type="text/plain", file_size=20, raw_text="不应出现在聚合响应", parse_status="parsed")
        self.db.add(resume)
        await self.db.flush()
        application = Application(candidate_id=candidate.id, job_id=job.id, current_resume_id=resume.id, source="hr_screening", lifecycle_status="active", recruitment_stage="hr_review", hr_decision="pending", final_outcome=None)
        self.db.add(application)
        await self.db.flush()
        criterion = {"criterion_id": "criterion:0001", "name": "Python API", "importance": "required", "description": "核对 API 实践。", "screening_focus": "寻找项目证据。", "origin": "hr_added", "sources": [], "hr_note": "虚构测试"}
        plan = JobEvaluationPlan(job_id=job.id, jd_fingerprint="a" * 64, status="ready", is_current=True, items=null(), structured_coverage=null(), free_text_coverage=null(), source_review_summary=null(), requirement_facts=null(), evaluation_criteria=null(), coverage_review_summary=null(), generation_audit=null(), v5_criteria=[criterion], edit_version=1, confirmed_at=NOW, warnings=[], prompt_version="test-plan", model_version="fake", schema_version="5.0", input_fingerprint="b" * 64, input_snapshot={})
        self.db.add(plan)
        await self.db.flush()
        assessment = {"criterion_id": "criterion:0001", "score": 9, "reason": "有证据。", "calculation_note": None, "experience_period_fact_keys": [], "evidence": [{"quote": "实现 Python API", "section": "项目经历"}]}
        payload = {"overall_score": 88, "display_label": "整体较匹配", "overall_summary": "岗位能力有可靠证据。", "criterion_assessments": [{"criterion": criterion, "assessment": assessment}], "strengths": [{"summary": "具备 API 交付经验。", "criterion_ids": ["criterion:0001"], "evidence": []}], "gaps": [], "risks_or_conflicts": [], "missing_info": [], "hr_follow_up_questions": []}
        report = ScreeningReport(application_id=application.id, job_id=job.id, resume_id=resume.id, job_evaluation_plan_id=plan.id, overall_score=88, display_label="整体较匹配", overall_summary=payload["overall_summary"], requirement_assessments=[], bonus_highlights=[], tradeoff_reason=None, interview_questions=[], input_fingerprint="c" * 64, jd_fingerprint="a" * 64, plan_fingerprint="b" * 64, resume_fingerprint="d" * 64, prompt_version="test-screen", model_version="fake", schema_version="5.0", redaction_version="test", v5_report=payload, is_current=True, is_outdated=False, outdated_reasons=[])
        self.db.add(report)
        await self.db.commit()

        statements = 0
        def count_statement(_connection, _cursor, statement, *_args):
            nonlocal statements
            if statement.lstrip().upper().startswith("SELECT"):
                statements += 1
        event.listen(self.connection.sync_connection, "before_cursor_execute", count_statement)
        try:
            page = await ScreeningCenterService().list_applications(self.db, job_id=job.id, sort=ScreeningCenterSort.SCORE_DESC)
        finally:
            event.remove(self.connection.sync_connection, "before_cursor_execute", count_statement)

        self.assertEqual(statements, 2)
        self.assertEqual(page.total, 1)
        item = page.items[0]
        self.assertEqual(item.masked_phone, "138****1234")
        self.assertEqual(item.score, 88)
        self.assertEqual(item.ability_tags[0].label, "Python API")
        self.assertNotIn("raw_text", item.model_dump())
        self.assertNotIn("v5_report", item.model_dump())
