from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "c8e1a6f4d205_structure_jobs_for_stage6.py"
)


def load_migration_module():
    spec = spec_from_file_location("job_structure_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - fixed test path
        raise RuntimeError("无法加载阶段 6 Job 迁移")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JobStructureMigrationTest(TestCase):
    def setUp(self) -> None:
        self.migration = load_migration_module()

    def test_revision_follows_current_head(self) -> None:
        self.assertEqual(self.migration.revision, "c8e1a6f4d205")
        self.assertEqual(self.migration.down_revision, "f5a7c9e2d104")

    def test_null_and_empty_object_become_empty_v1_without_legacy_snapshot(self) -> None:
        for old_value in (None, {}):
            with self.subTest(old_value=old_value):
                converted, legacy = self.migration._convert_requirements(old_value, None)

                self.assertEqual(converted, self.migration.EMPTY_REQUIREMENTS_V1)
                self.assertIsNone(legacy)

    def test_valid_v1_stays_v1_without_legacy_snapshot(self) -> None:
        old_value = {
            "schema_version": "1.0",
            "responsibilities": ["开发核心服务"],
            "required_skills": ["Python"],
            "preferred_skills": [],
            "minimum_work_years": 3,
            "education_requirement": "bachelor_or_above",
            "required_experiences": [],
            "preferred_experiences": [],
            "keywords": ["后端"],
            "additional_requirements": [],
        }

        converted, legacy = self.migration._convert_requirements(old_value, "旧描述")

        self.assertEqual(converted, old_value)
        self.assertIsNone(legacy)

    def test_known_legacy_fields_are_mapped_and_original_is_snapshotted(self) -> None:
        old_value = {
            "required_skills": [" Python ", "Python", "PostgreSQL"],
            "bonus_skills": ["Docker"],
            "preferred_skills": ["Kubernetes"],
            "job_keywords": ["后端"],
            "keywords": ["异步服务"],
            "experience_requirement": "3 年以上",
            "education_requirement": "本科及以上",
            "required_experiences": ["有 Web 服务经验"],
            "preferred_experiences": ["有招聘系统经验"],
            "summary": "沟通能力良好",
            "risk_keywords": ["频繁跳槽"],
        }

        converted, legacy = self.migration._convert_requirements(old_value, "负责平台开发")

        self.assertEqual(legacy, old_value)
        self.assertEqual(converted["responsibilities"], ["负责平台开发"])
        self.assertEqual(converted["required_skills"], ["Python", "PostgreSQL"])
        self.assertEqual(converted["preferred_skills"], ["Docker", "Kubernetes"])
        self.assertEqual(converted["keywords"], ["后端", "异步服务"])
        self.assertEqual(converted["minimum_work_years"], 3)
        self.assertEqual(converted["education_requirement"], "bachelor_or_above")
        self.assertEqual(converted["additional_requirements"], ["沟通能力良好"])
        self.assertNotIn("risk_keywords", converted)

    def test_unparseable_values_are_preserved_in_additional_and_snapshot(self) -> None:
        old_value = {
            "experience_requirement": "经验丰富即可",
            "education_requirement": "学历面议",
            "unknown_key": {"must_keep": True},
        }

        converted, legacy = self.migration._convert_requirements(old_value, None)

        self.assertEqual(legacy, old_value)
        self.assertEqual(converted["minimum_work_years"], None)
        self.assertEqual(converted["education_requirement"], None)
        self.assertEqual(
            converted["additional_requirements"],
            ["经验丰富即可", "学历面议"],
        )

    def test_non_object_json_is_not_guessed_and_is_snapshotted(self) -> None:
        converted, legacy = self.migration._convert_requirements(["Python"], "旧岗位描述")

        self.assertEqual(legacy, ["Python"])
        self.assertEqual(converted["responsibilities"], ["旧岗位描述"])
        self.assertEqual(converted["required_skills"], [])

    def test_status_mapping_is_explicit(self) -> None:
        expected = {
            "active": "open",
            "open": "open",
            "inactive": "closed",
            "closed": "closed",
            None: "draft",
            "unexpected": "draft",
        }

        for old_value, new_value in expected.items():
            with self.subTest(old_value=old_value):
                self.assertEqual(self.migration._map_status(old_value), new_value)

    def test_open_completeness_requires_all_confirmed_fields(self) -> None:
        requirements = {
            **self.migration.EMPTY_REQUIREMENTS_V1,
            "responsibilities": ["负责开发"],
            "required_skills": ["Python"],
            "minimum_work_years": 0,
            "education_requirement": "none",
        }
        complete = {
            "title": "后端工程师",
            "department": "研发部",
            "location": "上海",
            "employment_type": "full_time",
            "headcount": 1,
            "description": "岗位描述",
            "requirements": requirements,
        }

        self.assertTrue(self.migration._is_open_complete(**complete))
        self.assertFalse(self.migration._is_open_complete(**{**complete, "location": None}))
        self.assertFalse(
            self.migration._is_open_complete(
                **{**complete, "requirements": {**requirements, "required_skills": []}}
            )
        )
