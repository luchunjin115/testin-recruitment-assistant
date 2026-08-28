from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "d6e8f0a2b434_connect_v5_screening_runs_and_history.py"
)


def test_operations_migration_follows_v5_report_revision() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "d6e8f0a2b434"' in source
    assert 'down_revision: str | Sequence[str] | None = "c5d7e9f1a323"' in source


def test_operations_migration_enforces_one_nonterminal_run_per_application() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert "uq_screening_runs_active_application" in source
    assert '["application_id"]' in source
    for status in ("waiting_resume", "waiting_plan", "queued", "running", "paused"):
        assert status in source
    assert "STAGE7_V5_NONTERMINAL_RUN_CONFLICT" in source


def test_operations_migration_links_stage_history_to_report_safely() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert '"stage_histories"' in source
    assert '"report_id"' in source
    assert "fk_stage_histories_report_id_screening_reports" in source
    assert 'ondelete="SET NULL"' in source
    assert "STAGE7_V5_HISTORY_DOWNGRADE_BLOCKED" in source


def test_operations_migration_preserves_current_and_historical_reports() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert '"is_current"' in source
    assert "uq_screening_reports_current_application" in source
    assert "uq_screening_reports_application_id" in source
    assert "STAGE7_V5_REPORT_HISTORY_DOWNGRADE_BLOCKED" in source
