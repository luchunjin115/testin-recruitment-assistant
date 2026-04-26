import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def run_migrations():
    import sqlite3
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(candidates)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    if "job_id" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN job_id INTEGER")
    if "interview_time" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_time DATETIME")
    if "interview_method" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_method VARCHAR(50) DEFAULT ''")
    if "interviewer" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interviewer VARCHAR(100) DEFAULT ''")
    if "interview_note" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_note TEXT DEFAULT ''")
    if "interview_feedback_text" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_feedback_text TEXT DEFAULT ''")
    if "interview_round" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_round VARCHAR(50) DEFAULT ''")
    if "feedback_time" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN feedback_time DATETIME")
    if "interview_ai_technical_summary" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_ai_technical_summary TEXT DEFAULT ''")
    if "interview_ai_communication_summary" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_ai_communication_summary TEXT DEFAULT ''")
    if "interview_ai_job_match" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_ai_job_match TEXT DEFAULT ''")
    if "interview_ai_risk_points" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_ai_risk_points TEXT DEFAULT '[]'")
    if "interview_ai_recommendation" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_ai_recommendation VARCHAR(50) DEFAULT ''")
    if "interview_ai_next_step" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_ai_next_step TEXT DEFAULT ''")
    if "interview_ai_generated_at" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN interview_ai_generated_at DATETIME")
    if "recheck_note" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN recheck_note TEXT DEFAULT ''")
    if "second_interview_time" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN second_interview_time DATETIME")
    if "second_interviewer" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN second_interviewer VARCHAR(100) DEFAULT ''")
    if "offer_position" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN offer_position VARCHAR(100) DEFAULT ''")
    if "salary_range" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN salary_range VARCHAR(100) DEFAULT ''")
    if "expected_onboard_date" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN expected_onboard_date DATE")
    if "offer_note" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN offer_note TEXT DEFAULT ''")
    if "onboard_date" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN onboard_date DATE")
    if "onboard_note" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN onboard_note TEXT DEFAULT ''")
    if "reject_reason" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN reject_reason TEXT DEFAULT ''")
    if "reject_note" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN reject_note TEXT DEFAULT ''")
    if "stage_source" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN stage_source VARCHAR(20) DEFAULT 'system_auto'")
    if "screening_status" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN screening_status VARCHAR(20) DEFAULT 'pending'")
    if "resume_filename" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN resume_filename VARCHAR(255) DEFAULT ''")
    if "resume_file_type" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN resume_file_type VARCHAR(20) DEFAULT ''")
    if "resume_file_size" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN resume_file_size INTEGER")
    if "resume_uploaded_at" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN resume_uploaded_at DATETIME")
    if "match_score" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN match_score INTEGER")
    if "priority_level" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN priority_level VARCHAR(20) DEFAULT ''")
    if "screening_result" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN screening_result VARCHAR(50) DEFAULT ''")
    if "screening_reason" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN screening_reason TEXT DEFAULT ''")
    if "risk_flags" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN risk_flags TEXT DEFAULT '[]'")
    if "screening_updated_at" not in existing_cols:
        cursor.execute("ALTER TABLE candidates ADD COLUMN screening_updated_at DATETIME")

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
    )
    has_jobs = cursor.fetchone() is not None
    if has_jobs:
        cursor.execute("PRAGMA table_info(jobs)")
        job_cols = {row[1] for row in cursor.fetchall()}
        if "required_skills" not in job_cols:
            cursor.execute("ALTER TABLE jobs ADD COLUMN required_skills TEXT DEFAULT ''")
        if "bonus_skills" not in job_cols:
            cursor.execute("ALTER TABLE jobs ADD COLUMN bonus_skills TEXT DEFAULT ''")
        if "education_requirement" not in job_cols:
            cursor.execute("ALTER TABLE jobs ADD COLUMN education_requirement VARCHAR(100) DEFAULT ''")
        if "experience_requirement" not in job_cols:
            cursor.execute("ALTER TABLE jobs ADD COLUMN experience_requirement VARCHAR(100) DEFAULT ''")
        if "job_keywords" not in job_cols:
            cursor.execute("ALTER TABLE jobs ADD COLUMN job_keywords TEXT DEFAULT ''")
        if "risk_keywords" not in job_cols:
            cursor.execute("ALTER TABLE jobs ADD COLUMN risk_keywords TEXT DEFAULT ''")

    cursor.execute("UPDATE candidates SET stage = '待筛选' WHERE stage = '初筛'")
    cursor.execute("UPDATE candidates SET stage = '新投递' WHERE stage = '待定'")
    cursor.execute("UPDATE candidates SET stage_source = 'system_auto' WHERE stage_source IS NULL OR stage_source = ''")
    cursor.execute("UPDATE candidates SET screening_status = 'pending' WHERE screening_status IS NULL OR screening_status = ''")
    cursor.execute("UPDATE candidates SET screening_status = 'pending' WHERE screening_status NOT IN ('pending', 'passed', 'backup', 'rejected')")
    cursor.execute(
        "UPDATE candidates SET screening_status = 'passed' "
        "WHERE screening_status = 'pending' "
        "AND stage IN ('待约面', '已约面', '面试中', '复试', 'offer', '入职')"
    )
    cursor.execute(
        "UPDATE candidates SET screening_status = 'rejected' "
        "WHERE screening_status = 'pending' AND stage = '淘汰'"
    )
    cursor.execute("UPDATE candidates SET priority_level = '' WHERE priority_level IS NULL")
    cursor.execute("UPDATE candidates SET screening_result = '' WHERE screening_result IS NULL")
    cursor.execute("UPDATE candidates SET screening_reason = '' WHERE screening_reason IS NULL")
    cursor.execute("UPDATE candidates SET risk_flags = '[]' WHERE risk_flags IS NULL OR risk_flags = ''")
    cursor.execute("UPDATE candidates SET interview_feedback_text = '' WHERE interview_feedback_text IS NULL")
    cursor.execute("UPDATE candidates SET interview_round = '' WHERE interview_round IS NULL")
    cursor.execute("UPDATE candidates SET interview_ai_technical_summary = '' WHERE interview_ai_technical_summary IS NULL")
    cursor.execute("UPDATE candidates SET interview_ai_communication_summary = '' WHERE interview_ai_communication_summary IS NULL")
    cursor.execute("UPDATE candidates SET interview_ai_job_match = '' WHERE interview_ai_job_match IS NULL")
    cursor.execute("UPDATE candidates SET interview_ai_risk_points = '[]' WHERE interview_ai_risk_points IS NULL OR interview_ai_risk_points = ''")
    cursor.execute("UPDATE candidates SET interview_ai_recommendation = '' WHERE interview_ai_recommendation IS NULL")
    cursor.execute("UPDATE candidates SET interview_ai_next_step = '' WHERE interview_ai_next_step IS NULL")
    cursor.execute(
        "UPDATE candidates SET resume_filename = "
        "REPLACE(REPLACE(REPLACE(resume_path, 'uploads\\\\', ''), 'uploads/', ''), './uploads/', '') "
        "WHERE (resume_filename IS NULL OR resume_filename = '') AND resume_path IS NOT NULL AND resume_path != ''"
    )
    cursor.execute(
        "UPDATE candidates SET resume_file_type = lower(substr(resume_filename, instr(resume_filename, '.') + 1)) "
        "WHERE (resume_file_type IS NULL OR resume_file_type = '') "
        "AND resume_filename IS NOT NULL AND instr(resume_filename, '.') > 0"
    )

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'activity_logs'"
    )
    has_activity_logs = cursor.fetchone() is not None
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'stage_change_logs'"
    )
    has_stage_change_logs = cursor.fetchone() is not None

    if has_activity_logs:
        cursor.execute("UPDATE activity_logs SET detail = REPLACE(detail, '初筛', '待筛选')")
        cursor.execute("UPDATE activity_logs SET detail = REPLACE(detail, '待定', '新投递')")
        cursor.execute(
            "UPDATE activity_logs SET created_at = CURRENT_TIMESTAMP "
            "WHERE datetime(created_at) > CURRENT_TIMESTAMP"
        )

    if has_stage_change_logs:
        cursor.execute("UPDATE stage_change_logs SET from_stage = '待筛选' WHERE from_stage = '初筛'")
        cursor.execute("UPDATE stage_change_logs SET to_stage = '待筛选' WHERE to_stage = '初筛'")
        cursor.execute("UPDATE stage_change_logs SET from_stage = '新投递' WHERE from_stage = '待定'")
        cursor.execute("UPDATE stage_change_logs SET to_stage = '新投递' WHERE to_stage = '待定'")
        cursor.execute(
            "UPDATE stage_change_logs SET created_at = CURRENT_TIMESTAMP "
            "WHERE datetime(created_at) > CURRENT_TIMESTAMP"
        )

        cursor.execute(
            "SELECT candidate_id, from_stage, to_stage, created_at FROM stage_change_logs"
        )
        existing_stage_logs = set(cursor.fetchall())

        cursor.execute(
            "SELECT candidate_id, detail, created_at FROM activity_logs WHERE action = 'stage_changed'"
        )
        stage_pattern = re.compile(r"状态从「(?P<from_stage>[^」]+)」变更为「(?P<to_stage>[^」]+)」")
        backfill_rows = []
        for candidate_id, detail, created_at in cursor.fetchall():
            match = stage_pattern.search(detail or "")
            if not match:
                continue
            from_stage = match.group("from_stage")
            to_stage = match.group("to_stage")
            if from_stage == "初筛":
                from_stage = "待筛选"
            if to_stage == "初筛":
                to_stage = "待筛选"
            if from_stage == "待定":
                from_stage = "新投递"
            if to_stage == "待定":
                to_stage = "新投递"

            row_key = (candidate_id, from_stage, to_stage, created_at)
            if row_key in existing_stage_logs:
                continue
            backfill_rows.append(
                (candidate_id, from_stage, to_stage, "历史数据回填", "system_auto", created_at)
            )
            existing_stage_logs.add(row_key)

        if backfill_rows:
            cursor.executemany(
                "INSERT INTO stage_change_logs "
                "(candidate_id, from_stage, to_stage, trigger_reason, trigger_source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                backfill_rows,
            )

    conn.commit()
    conn.close()
