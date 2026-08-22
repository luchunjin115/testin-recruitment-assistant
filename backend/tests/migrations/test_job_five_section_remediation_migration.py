from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase


VERSIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"
NEW_FIELDS = (
    "job_background",
    "job_responsibilities",
    "candidate_requirements",
    "preferred_qualifications",
    "public_notes",
)
OLD_FIELDS = ("description", "requirements", "legacy_requirements")


def find_remediation_migrations() -> list[Path]:
    matches = []
    for path in VERSIONS_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        if all(field in source for field in NEW_FIELDS):
            matches.append(path)
    return matches


def load_module(path: Path):
    spec = spec_from_file_location("job_five_section_remediation_migration", path)
    if spec is None or spec.loader is None:  # pragma: no cover - fixed test path
        raise RuntimeError("无法加载五段式 JD migration")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScalarResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class FakeConnection:
    def __init__(self, job_count: int) -> None:
        self.job_count = job_count
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return ScalarResult(self.job_count)


class JobFiveSectionMigrationContractTest(TestCase):
    def migration(self):
        candidates = find_remediation_migrations()
        self.assertEqual(
            len(candidates),
            1,
            "6R-B 必须新增且只新增一条包含五字段的向前 migration",
        )
        return load_module(candidates[0])

    def test_revision_follows_current_code_head(self) -> None:
        migration = self.migration()
        self.assertEqual(migration.down_revision, "e4c7a1b9d632")

    def test_empty_jobs_table_passes_precondition(self) -> None:
        migration = self.migration()
        self.assertTrue(hasattr(migration, "_require_empty_jobs_table"))

        migration._require_empty_jobs_table(FakeConnection(job_count=0))

    def test_nonempty_jobs_table_stops_with_stable_reason(self) -> None:
        migration = self.migration()
        connection = FakeConnection(job_count=1)

        with self.assertRaisesRegex(
            RuntimeError,
            "STAGE6_FIVE_SECTION_JD_REQUIRES_EMPTY_JOBS",
        ):
            migration._require_empty_jobs_table(connection)

    def test_upgrade_checks_empty_table_before_any_column_change(self) -> None:
        migration = self.migration()
        source = Path(migration.__file__).read_text(encoding="utf-8")

        guard_position = source.index("_require_empty_jobs_table(op.get_bind())")
        first_schema_change = min(
            position
            for marker in ("op.add_column", "op.drop_column")
            if (position := source.index(marker)) >= 0
        )
        self.assertLess(guard_position, first_schema_change)

        for field in NEW_FIELDS:
            self.assertIn(f'op.add_column("jobs", sa.Column("{field}", sa.Text()', source)
        for field in OLD_FIELDS:
            self.assertIn(f'op.drop_column("jobs", "{field}")', source)
