from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.services.resume_text_extractor import (
    ResumeTextExtractor,
    ResumeTextExtractorError,
)


class ResumeTextExtractorTest(TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.storage_root = Path(self.temp_dir.name)
        self.resume_dir = self.storage_root / "v2" / "resumes" / "2026" / "08"
        self.resume_dir.mkdir(parents=True)
        self.extractor = ResumeTextExtractor()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_file(self, name: str, content: bytes) -> tuple[str, Path]:
        path = self.resume_dir / name
        path.write_bytes(content)
        return path.relative_to(self.storage_root).as_posix(), path

    def test_extract_returns_complete_utf8_text(self) -> None:
        content = "张三\r\nPython 开发工程师\n项目经历".encode("utf-8")
        relative_path, _ = self.create_file("resume.txt", content)

        text = self.extractor.extract(self.storage_root, relative_path, len(content))

        self.assertEqual(text, content.decode("utf-8"))

    def test_extract_supports_gb18030_text(self) -> None:
        content = "李四\n自动化测试工程师".encode("gb18030")
        relative_path, _ = self.create_file("resume.txt", content)

        text = self.extractor.extract(self.storage_root, relative_path, len(content))

        self.assertEqual(text, "李四\n自动化测试工程师")

    def test_extract_rejects_parent_directory_traversal(self) -> None:
        outside = self.storage_root / "outside.txt"
        outside.write_text("private", encoding="utf-8")

        with self.assertRaisesRegex(ResumeTextExtractorError, "路径无效"):
            self.extractor.extract(self.storage_root, "../outside.txt", outside.stat().st_size)

    def test_extract_rejects_absolute_path_outside_namespace(self) -> None:
        outside = self.storage_root / "outside.txt"
        outside.write_text("private", encoding="utf-8")

        with self.assertRaisesRegex(ResumeTextExtractorError, "路径无效"):
            self.extractor.extract(self.storage_root, str(outside.resolve()), outside.stat().st_size)

    def test_extract_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(ResumeTextExtractorError, "文件不存在"):
            self.extractor.extract(
                self.storage_root,
                "v2/resumes/2026/08/missing.txt",
                10,
            )

    def test_extract_rejects_size_mismatch(self) -> None:
        relative_path, _ = self.create_file("resume.txt", b"resume")

        with self.assertRaisesRegex(ResumeTextExtractorError, "大小与上传记录不一致"):
            self.extractor.extract(self.storage_root, relative_path, 999)

    def test_extract_rejects_missing_size_metadata(self) -> None:
        relative_path, _ = self.create_file("resume.txt", b"resume")

        with self.assertRaisesRegex(ResumeTextExtractorError, "缺少文件大小"):
            self.extractor.extract(self.storage_root, relative_path, None)

    def test_extract_rejects_staging_file(self) -> None:
        staging = self.storage_root / "v2" / "resumes" / ".staging"
        staging.mkdir(parents=True)
        path = staging / "temporary.txt"
        path.write_text("temporary", encoding="utf-8")

        with self.assertRaisesRegex(ResumeTextExtractorError, "路径无效"):
            self.extractor.extract(
                self.storage_root,
                path.relative_to(self.storage_root).as_posix(),
                path.stat().st_size,
            )

    def test_extract_rejects_non_txt_file(self) -> None:
        relative_path, path = self.create_file("resume.pdf", b"%PDF-1.4")

        with self.assertRaisesRegex(ResumeTextExtractorError, "只支持 TXT"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_rejects_blank_text(self) -> None:
        relative_path, path = self.create_file("resume.txt", b" \r\n\t")

        with self.assertRaisesRegex(ResumeTextExtractorError, "没有可提取"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_rejects_binary_control_content(self) -> None:
        content = bytes(range(1, 16)) * 8
        relative_path, path = self.create_file("resume.txt", content)

        with self.assertRaises(ResumeTextExtractorError):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)
