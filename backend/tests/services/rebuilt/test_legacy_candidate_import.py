import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.models.rebuilt.job import Job
from app.services.rebuilt.legacy_candidate_import import (
    build_candidate,
    build_job_requirements,
    build_screening_result,
    load_legacy_snapshot,
    map_candidate_status,
    map_job_status,
    parse_legacy_datetime,
    parse_json_list,
    resolve_resume_path,
)


class LegacyCandidateImportTest(TestCase):
    def test_status_mapping_uses_new_values(self) -> None:
        self.assertEqual(map_candidate_status("新投递"), "new")
        self.assertEqual(map_candidate_status("面试中"), "interviewing")
        self.assertEqual(map_job_status("active"), "open")

    def test_parse_json_list_handles_json_plain_text_and_duplicates(self) -> None:
        self.assertEqual(parse_json_list('["Python", "SQL", "Python"]'), ["Python", "SQL"])
        self.assertEqual(parse_json_list("FastAPI，PostgreSQL"), ["FastAPI", "PostgreSQL"])
        self.assertEqual(parse_json_list(""), [])

    def test_parse_legacy_datetime_uses_china_standard_time_without_tzdata(self) -> None:
        parsed = parse_legacy_datetime("2026-08-04 10:30:00")

        self.assertEqual(parsed.utcoffset().total_seconds(), 8 * 60 * 60)

    def test_build_job_requirements_preserves_structured_legacy_fields(self) -> None:
        requirements = build_job_requirements(
            {
                "requirements": "负责后端服务开发",
                "required_skills": '["Python", "SQL"]',
                "bonus_skills": "Docker",
                "education_requirement": "本科",
            }
        )

        self.assertEqual(requirements["summary"], "负责后端服务开发")
        self.assertEqual(requirements["required_skills"], ["Python", "SQL"])
        self.assertEqual(requirements["bonus_skills"], ["Docker"])
        self.assertEqual(requirements["education_requirement"], "本科")

    def test_resolve_resume_path_uses_restored_upload_filename(self) -> None:
        with TemporaryDirectory() as directory:
            backend_dir = Path(directory)
            uploads_dir = backend_dir / "uploads"
            uploads_dir.mkdir()
            (uploads_dir / "resume.txt").write_text("resume", encoding="utf-8")

            result = resolve_resume_path(
                {
                    "resume_path": "D:/old-computer/uploads/resume.txt",
                    "resume_filename": "resume.txt",
                },
                backend_dir=backend_dir,
                uploads_dir=uploads_dir,
            )

        self.assertEqual(result, "uploads/resume.txt")

    def test_load_snapshot_does_not_change_source_rows(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "legacy.db"
            connection = sqlite3.connect(source)
            connection.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT)")
            connection.execute(
                "CREATE TABLE candidates (id INTEGER PRIMARY KEY, name TEXT, job_id INTEGER)"
            )
            connection.execute("INSERT INTO jobs (id, title) VALUES (1, '后端工程师')")
            connection.execute(
                "INSERT INTO candidates (id, name, job_id) VALUES (1, '候选人', 1)"
            )
            connection.commit()
            connection.close()

            snapshot = load_legacy_snapshot(source)

            verification = sqlite3.connect(source)
            candidate_count = verification.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
            verification.close()

        self.assertEqual(len(snapshot.jobs), 1)
        self.assertEqual(len(snapshot.candidates), 1)
        self.assertEqual(candidate_count, 1)

    def test_build_candidate_maps_only_supported_fields(self) -> None:
        with TemporaryDirectory() as directory:
            backend_dir = Path(directory)
            uploads_dir = backend_dir / "uploads"
            uploads_dir.mkdir()
            (uploads_dir / "resume.txt").write_text("resume", encoding="utf-8")
            job = Job(id=1, title="后端工程师")

            candidate = build_candidate(
                {
                    "name": "候选人",
                    "phone": "13800000000",
                    "email": "candidate@example.com",
                    "experience_years": 5,
                    "degree": "本科",
                    "source_channel": "内推",
                    "stage": "待约面",
                    "resume_path": "D:/old/resume.txt",
                    "resume_filename": "resume.txt",
                    "ai_summary": "后端经验丰富",
                    "ai_tags": '["高潜"]',
                    "skills": '["Python"]',
                    "school": "示例大学",
                    "major": "计算机",
                    "experience_desc": "负责服务端开发",
                },
                job=job,
                backend_dir=backend_dir,
                uploads_dir=uploads_dir,
            )

        self.assertEqual(candidate.status, "interview_pending")
        self.assertEqual(candidate.applied_job, job)
        self.assertEqual(candidate.tags, ["高潜", "Python"])
        self.assertEqual(candidate.resume_file_path, "uploads/resume.txt")
        self.assertEqual(candidate.education_records[0].school, "示例大学")
        self.assertEqual(candidate.work_experiences[0].description, "负责服务端开发")
        self.assertIsNone(candidate.current_company)

    def test_build_screening_result_preserves_old_score_and_source(self) -> None:
        job = Job(id=1, title="后端工程师")
        candidate = build_candidate(
            {"name": "候选人", "stage": "待筛选"},
            job=job,
            backend_dir=Path("backend"),
            uploads_dir=Path("backend/uploads"),
        )

        result = build_screening_result(
            {
                "match_score": 88,
                "screening_status": "passed",
                "risk_flags": '["经验待核实"]',
                "screening_result": "建议初筛",
                "screening_reason": "技能匹配",
                "priority_level": "高优先级",
            },
            candidate=candidate,
            job=job,
        )

        self.assertEqual(result.overall_score, 88)
        self.assertTrue(result.hard_pass)
        self.assertEqual(result.recommendation, "建议初筛")
        self.assertEqual(result.risks, ["经验待核实"])
        self.assertEqual(result.raw_result["source"], "legacy_sqlite_import")
