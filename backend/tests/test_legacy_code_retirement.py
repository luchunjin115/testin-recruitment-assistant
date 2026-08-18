import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RETIRED_BACKEND_AND_TOOL_FILES = (
    "backend/app/config.py",
    "backend/app/database.py",
    "backend/app/seed_data.py",
    "backend/app/routers/__init__.py",
    "backend/app/routers/actions.py",
    "backend/app/routers/ai.py",
    "backend/app/routers/apply.py",
    "backend/app/routers/candidates.py",
    "backend/app/routers/dashboard.py",
    "backend/app/routers/jobs.py",
    "backend/app/routers/resume.py",
    "backend/app/routers/screening.py",
    "backend/app/routers/sync.py",
    "backend/app/models/stage_change_log.py",
    "backend/app/schemas/dashboard.py",
    "backend/app/services/ai_service.py",
    "backend/app/services/dedup_service.py",
    "backend/app/services/file_parser.py",
    "backend/app/services/followup_service.py",
    "backend/app/services/mock_llm.py",
    "backend/app/services/stage_service.py",
    "backend/app/services/sync_adapter.py",
    "backend/app/services/legacy_candidate_import.py",
    "backend/app/prompts/auto_tagging.txt",
    "backend/app/prompts/candidate_summary.txt",
    "backend/app/prompts/copilot_system.txt",
    "backend/app/prompts/followup_suggestion.txt",
    "backend/app/prompts/resume_extraction.txt",
    "backend/app/prompts/screening.txt",
    "scripts/ensure_demo_data.py",
    "scripts/evaluate_screening_prompt.py",
    "scripts/export_csv.py",
    "scripts/import_legacy_candidates.py",
    "scripts/init_db.py",
    "scripts/reset_demo_data.py",
    "backend/tests/services/test_legacy_candidate_import.py",
    "prompts/auto_tagging.md",
    "prompts/candidate_summary.md",
    "prompts/copilot_system.md",
    "prompts/followup_suggestion.md",
    "prompts/resume_extraction.md",
)

FINAL_PACKAGE_REUSED_PATHS = {
    "backend/app/models/activity_log.py": "from app.core.database import Base",
    "backend/app/models/candidate.py": "from app.core.database import Base",
    "backend/app/models/job.py": "from app.core.database import Base",
    "backend/app/schemas/candidate.py": "ConfigDict",
    "backend/app/schemas/job.py": "ConfigDict",
    "backend/app/services/candidate_service.py": "AsyncSession",
    "backend/app/services/job_service.py": "AsyncSession",
}

RETIRED_REBUILT_DIRECTORIES = (
    "backend/app/adapters/rebuilt",
    "backend/app/models/rebuilt",
    "backend/app/prompts/rebuilt",
    "backend/app/schemas/rebuilt",
    "backend/app/services/rebuilt",
    "backend/tests/adapters/rebuilt",
    "backend/tests/api/rebuilt",
    "backend/tests/models/rebuilt",
    "backend/tests/schemas/rebuilt",
    "backend/tests/services/rebuilt",
)


class LegacyCodeRetirementTests(unittest.TestCase):
    def test_retired_backend_and_tool_files_do_not_return(self) -> None:
        for relative_path in RETIRED_BACKEND_AND_TOOL_FILES:
            with self.subTest(path=relative_path):
                self.assertFalse(
                    (PROJECT_ROOT / relative_path).exists(),
                    f"retired file must stay deleted: {relative_path}",
                )

    def test_rebuilt_package_directories_do_not_return(self) -> None:
        for relative_path in RETIRED_REBUILT_DIRECTORIES:
            with self.subTest(path=relative_path):
                self.assertFalse(
                    (PROJECT_ROOT / relative_path).exists(),
                    f"transitional package must stay removed: {relative_path}",
                )

    def test_reused_final_paths_contain_postgresql_implementations(self) -> None:
        for relative_path, expected_marker in FINAL_PACKAGE_REUSED_PATHS.items():
            with self.subTest(path=relative_path):
                source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn(expected_marker, source)
                self.assertNotIn("from app.database", source)


if __name__ == "__main__":
    unittest.main()
