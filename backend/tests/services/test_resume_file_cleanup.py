from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from app.services.resume_file_cleanup import (
    ResumeCleanupStorageError,
    ResumeCleanupValidationError,
    ResumeFileCleanup,
    TrashResumeFile,
    UnsupportedResumeCleanupError,
)


class ResumeFileCleanupTest(TestCase):
    def setUp(self) -> None:
        self.cleanup = ResumeFileCleanup()
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.storage_root = Path(self.temp_directory.name)
        self.original_path = (
            self.storage_root / "v2" / "resumes" / "2026" / "08" / "stored.txt"
        )
        self.original_path.parent.mkdir(parents=True)
        self.original_path.write_text("candidate resume", encoding="utf-8")

    def quarantine(self):
        return self.cleanup.quarantine(
            storage_root=self.storage_root,
            relative_path=self.original_path.relative_to(self.storage_root).as_posix(),
            file_type="text/plain",
            expected_size=self.original_path.stat().st_size,
            resume_id=42,
        )

    def test_quarantine_moves_file_into_private_namespace_without_overwrite(self) -> None:
        quarantined = self.quarantine()

        self.assertFalse(self.original_path.exists())
        self.assertTrue(quarantined.quarantined_path.is_file())
        self.assertEqual(quarantined.quarantined_path.parent.name, ".trash")
        self.assertTrue(quarantined.quarantined_path.name.startswith("resume-42-"))
        self.assertNotEqual(quarantined.quarantined_path.name, self.original_path.name)

    def test_restore_returns_quarantined_file_to_original_path(self) -> None:
        quarantined = self.quarantine()

        self.cleanup.restore(quarantined)

        self.assertEqual(self.original_path.read_text(encoding="utf-8"), "candidate resume")
        self.assertFalse(quarantined.quarantined_path.exists())

    def test_purge_removes_quarantined_file(self) -> None:
        quarantined = self.quarantine()

        self.cleanup.purge(quarantined)

        self.assertFalse(self.original_path.exists())
        self.assertFalse(quarantined.quarantined_path.exists())

    def test_rejects_unknown_mime_without_moving_file(self) -> None:
        with self.assertRaisesRegex(UnsupportedResumeCleanupError, "不支持"):
            self.cleanup.quarantine(
                self.storage_root,
                self.original_path.relative_to(self.storage_root).as_posix(),
                "application/octet-stream",
                self.original_path.stat().st_size,
                42,
            )

        self.assertTrue(self.original_path.is_file())

    def test_rejects_path_traversal_without_touching_outside_file(self) -> None:
        outside = self.storage_root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")

        with self.assertRaisesRegex(ResumeCleanupValidationError, "路径无效"):
            self.cleanup.quarantine(
                self.storage_root,
                "outside.txt",
                "text/plain",
                outside.stat().st_size,
                42,
            )

        self.assertEqual(outside.read_text(encoding="utf-8"), "outside")

    def test_move_failure_keeps_original_file(self) -> None:
        with patch("app.services.resume_file_cleanup.os.replace") as replace:
            replace.side_effect = PermissionError("locked")
            with self.assertRaisesRegex(ResumeCleanupStorageError, "待清理区失败"):
                self.quarantine()

        self.assertTrue(self.original_path.is_file())

    def test_restore_refuses_to_overwrite_new_file(self) -> None:
        quarantined = self.quarantine()
        self.original_path.write_text("new file", encoding="utf-8")

        with self.assertRaisesRegex(ResumeCleanupStorageError, "已存在"):
            self.cleanup.restore(quarantined)

        self.assertEqual(self.original_path.read_text(encoding="utf-8"), "new file")
        self.assertTrue(quarantined.quarantined_path.is_file())

    def test_lists_only_recognized_direct_trash_files(self) -> None:
        trash = self.storage_root / "v2" / "resumes" / ".trash"
        trash.mkdir(parents=True)
        valid = trash / f"resume-9-{'a' * 32}.txt"
        valid.write_text("safe trash", encoding="utf-8")
        (trash / "unknown.txt").write_text("ignore", encoding="utf-8")
        nested = trash / "nested"
        nested.mkdir()
        (nested / f"resume-10-{'b' * 32}.txt").write_text("ignore", encoding="utf-8")

        entries = self.cleanup.list_trash_files(self.storage_root, limit=10)

        self.assertEqual(entries, [TrashResumeFile(resume_id=9, path=valid.resolve())])

    def test_trash_listing_respects_batch_limit(self) -> None:
        trash = self.storage_root / "v2" / "resumes" / ".trash"
        trash.mkdir(parents=True)
        for resume_id, token in ((7, "a"), (8, "b")):
            (trash / f"resume-{resume_id}-{token * 32}.txt").write_text(
                "trash",
                encoding="utf-8",
            )

        entries = self.cleanup.list_trash_files(self.storage_root, limit=1)

        self.assertEqual(len(entries), 1)

    def test_purge_trash_file_revalidates_namespace_and_resume_id(self) -> None:
        outside = self.storage_root / f"resume-9-{'a' * 32}.txt"
        outside.write_text("outside", encoding="utf-8")

        with self.assertRaisesRegex(ResumeCleanupStorageError, "路径无效"):
            self.cleanup.purge_trash_file(
                self.storage_root,
                TrashResumeFile(resume_id=9, path=outside),
            )

        self.assertTrue(outside.is_file())

    def test_purge_trash_file_removes_verified_orphan(self) -> None:
        trash = self.storage_root / "v2" / "resumes" / ".trash"
        trash.mkdir(parents=True)
        target = trash / f"resume-9-{'a' * 32}.txt"
        target.write_text("orphan", encoding="utf-8")

        self.cleanup.purge_trash_file(
            self.storage_root,
            TrashResumeFile(resume_id=9, path=target.resolve()),
        )

        self.assertFalse(target.exists())
