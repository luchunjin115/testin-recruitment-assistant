from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "c5d7e9f1a323_add_screening_report_v5_payload.py"
)


def test_v5_report_migration_is_one_forward_revision() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "c5d7e9f1a323"' in source
    assert 'down_revision: str | Sequence[str] | None = "b4c6d8e0f212"' in source


def test_v5_report_migration_adds_only_safe_json_payload_contract() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert '"screening_reports"' in source
    assert '"v5_report"' in source
    assert "ck_screening_reports_v5_payload_matches_schema" in source
    assert "jsonb_typeof(v5_report) = 'object'" in source
    assert "raw_response" not in source
    assert "api_key" not in source.lower()
    assert "internal_prompt" not in source


def test_v5_report_migration_blocks_lossy_downgrade() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert "STAGE7_SCREENING_V5_DOWNGRADE_BLOCKED" in source
    assert "WHERE schema_version = '5.0' OR v5_report IS NOT NULL" in source
