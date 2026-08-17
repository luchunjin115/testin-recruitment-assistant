from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "e7b1c9d4a206_add_stage7_application_foundation.py"
)


def load_migration_module():
    spec = spec_from_file_location("stage7_application_foundation_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - fixed test path
        raise RuntimeError("无法加载阶段 7 Application 基础迁移")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage7ApplicationFoundationMigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()

    def test_revision_follows_stage6_head(self) -> None:
        self.assertEqual(self.migration.revision, "e7b1c9d4a206")
        self.assertEqual(self.migration.down_revision, "c8e1a6f4d205")

    def test_default_rubric_weights_match_confirmed_contract(self) -> None:
        self.assertEqual(
            self.migration.DEFAULT_RUBRIC_WEIGHTS,
            {
                "must_have_requirements_weight": 40,
                "work_experience_relevance_weight": 25,
                "projects_and_capability_weight": 20,
                "preferred_qualifications_weight": 10,
                "keywords_and_additional_weight": 5,
            },
        )
        self.assertEqual(sum(self.migration.DEFAULT_RUBRIC_WEIGHTS.values()), 100)

