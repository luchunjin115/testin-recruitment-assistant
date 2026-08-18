from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from app.prompts.screening_rubric_templates import get_rubric_template


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

    def test_default_rubric_contains_publishable_standard_semantic_items(self) -> None:
        items = self.migration.DEFAULT_STANDARD_SEMANTIC_ITEMS

        self.assertEqual(len(items), 5)
        self.assertEqual(len({item["key"] for item in items}), 5)
        self.assertTrue(all(item["max_score"] == 10 for item in items))
        self.assertTrue(all(item["source"] == "template" for item in items))
        self.assertEqual(
            items,
            [
                item.model_dump(mode="json")
                for item in get_rubric_template("standard").semantic_items
            ],
        )

    def test_upgrade_declares_v2_rubric_storage_indexes_and_template_backfill(self) -> None:
        operation_mock = Mock()
        with patch.object(self.migration, "op", operation_mock):
            self.migration.upgrade()

        rubric_table_call = next(
            call
            for call in operation_mock.create_table.call_args_list
            if call.args[0] == "job_screening_rubrics"
        )
        column_names = {
            item.name for item in rubric_table_call.args[1:] if hasattr(item, "name")
        }
        self.assertTrue(
            {
                "source",
                "template_key",
                "status",
                "semantic_items",
                "job_fingerprint",
                "is_stale",
                "stale_at",
                "stale_reason",
                "generation_metadata",
                "confirmed_by",
                "confirmed_at",
                "abandoned_at",
                "updated_at",
            }.issubset(column_names)
        )

        index_names = {call.args[0] for call in operation_mock.create_index.call_args_list}
        self.assertIn("uq_job_screening_rubrics_current_job", index_names)
        self.assertIn("uq_job_screening_rubrics_draft_job", index_names)
        self.assertIn("ix_job_screening_rubrics_is_stale", index_names)

        rubric_statement = operation_mock.execute.call_args_list[0].args[0]
        rubric_insert = str(rubric_statement)
        self.assertIn("'standard_template'", rubric_insert)
        self.assertIn("'standard'", rubric_insert)
        self.assertIn("'active'", rubric_insert)
        self.assertIn("CAST(:semantic_items AS jsonb)", rubric_insert)
        semantic_items = rubric_statement.compile().params["semantic_items"]
        self.assertIn("responsibility_alignment", semantic_items)
        self.assertNotIn(":10", rubric_insert)
