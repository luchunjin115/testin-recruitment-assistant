from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PyPDF2 import PdfWriter

from app.services.rebuilt.resume_pdf_extractor import (
    ResumePdfExtractor,
    ResumePdfExtractorError,
)


def build_text_pdf(page_texts: list[str]) -> bytes:
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    page_references: list[str] = []
    for index, text in enumerate(page_texts):
        page_id = 4 + index * 2
        content_id = page_id + 1
        page_references.append(f"{page_id} 0 R")
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
    objects[2] = (
        f"<< /Type /Pages /Kids [{' '.join(page_references)}] "
        f"/Count {len(page_references)} >>"
    ).encode("ascii")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for object_id in range(1, max(objects) + 1):
        offsets[object_id] = len(output)
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(objects[object_id])
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {max(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for object_id in range(1, max(objects) + 1):
        output.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {max(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def build_encrypted_pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    writer.write(output)
    return output.getvalue()


def build_positioned_text_pdf(
    text_objects: list[tuple[float, float, str]],
) -> bytes:
    commands: list[str] = ["BT /F1 12 Tf"]
    for x, y, text in text_objects:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"1 0 0 1 {x} {y} Tm ({escaped}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>"
        ),
        5: (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        ),
    }

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for object_id in range(1, 6):
        offsets[object_id] = len(output)
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(objects[object_id])
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for object_id in range(1, 6):
        output.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size 6 /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


class ResumePdfExtractorTest(TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.storage_root = Path(self.temp_dir.name)
        self.resume_dir = self.storage_root / "v2" / "resumes" / "2026" / "08"
        self.resume_dir.mkdir(parents=True)
        self.extractor = ResumePdfExtractor()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_file(self, name: str, content: bytes) -> tuple[str, Path]:
        path = self.resume_dir / name
        path.write_bytes(content)
        return path.relative_to(self.storage_root).as_posix(), path

    def test_extract_returns_single_page_text(self) -> None:
        content = build_text_pdf(["Candidate resume includes Python and FastAPI experience."])
        relative_path, path = self.create_file("resume.pdf", content)

        text = self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

        self.assertEqual(text, "Candidate resume includes Python and FastAPI experience.")

    def test_extract_preserves_page_order_and_skips_blank_page(self) -> None:
        content = build_text_pdf(
            [
                "First page contains candidate profile information.",
                "",
                "Third page contains project experience information.",
            ]
        )
        relative_path, path = self.create_file("resume.pdf", content)

        text = self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

        self.assertEqual(
            text,
            "First page contains candidate profile information.\n\n"
            "Third page contains project experience information.",
        )

    def test_extract_uses_visual_coordinates_instead_of_content_stream_order(self) -> None:
        content = build_positioned_text_pdf(
            [
                (72, 620, "SECOND SECTION BODY CONTAINS PROJECT DETAILS."),
                (72, 720, "FIRST SECTION HEADING CONTAINS PROFILE."),
                (72, 680, "FIRST SECTION BODY CONTAINS EDUCATION."),
                (72, 650, "SECOND SECTION HEADING CONTAINS PROJECTS."),
            ]
        )
        relative_path, path = self.create_file("resume.pdf", content)

        text = self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

        self.assertEqual(
            text.splitlines(),
            [
                "FIRST SECTION HEADING CONTAINS PROFILE.",
                "FIRST SECTION BODY CONTAINS EDUCATION.",
                "SECOND SECTION HEADING CONTAINS PROJECTS.",
                "SECOND SECTION BODY CONTAINS PROJECT DETAILS.",
            ],
        )

    def test_extract_orders_same_visual_line_from_left_to_right(self) -> None:
        content = build_positioned_text_pdf(
            [
                (320, 700, "RIGHT CONTACT DETAILS"),
                (72, 700, "LEFT CANDIDATE NAME"),
                (72, 660, "NEXT VISUAL LINE CONTENT"),
            ]
        )
        relative_path, path = self.create_file("resume.pdf", content)

        text = self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

        lines = text.splitlines()
        self.assertEqual(lines[0], "LEFT CANDIDATE NAME RIGHT CONTACT DETAILS")
        self.assertEqual(lines[1], "NEXT VISUAL LINE CONTENT")

    def test_extract_rejects_pdf_without_pages(self) -> None:
        content = build_text_pdf([])
        relative_path, path = self.create_file("resume.pdf", content)

        with self.assertRaisesRegex(ResumePdfExtractorError, "不包含任何页面"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_marks_blank_pdf_as_possible_scan(self) -> None:
        content = build_text_pdf(["", ""])
        relative_path, path = self.create_file("resume.pdf", content)

        with self.assertRaisesRegex(ResumePdfExtractorError, "扫描件.*OCR"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_rejects_too_little_effective_text(self) -> None:
        content = build_text_pdf(["short"])
        relative_path, path = self.create_file("resume.pdf", content)

        with self.assertRaisesRegex(ResumePdfExtractorError, "有效文字过少"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_rejects_damaged_pdf(self) -> None:
        relative_path, path = self.create_file("resume.pdf", b"%PDF-1.4\nbroken")

        with self.assertRaisesRegex(ResumePdfExtractorError, "损坏或无法读取"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_rejects_password_encrypted_pdf(self) -> None:
        content = build_encrypted_pdf()
        relative_path, path = self.create_file("resume.pdf", content)

        with self.assertRaisesRegex(ResumePdfExtractorError, "已加密"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_rejects_excessive_page_count(self) -> None:
        content = build_text_pdf(["Resume page with enough text."] * 101)
        relative_path, path = self.create_file("resume.pdf", content)

        with self.assertRaisesRegex(ResumePdfExtractorError, "超过 100 页"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_rejects_excessive_output_text(self) -> None:
        content = build_text_pdf(["Candidate resume contains more than twenty characters."])
        relative_path, path = self.create_file("resume.pdf", content)

        with patch(
            "app.services.rebuilt.resume_pdf_extractor.MAX_EXTRACTED_CHARACTERS",
            20,
        ):
            with self.assertRaisesRegex(ResumePdfExtractorError, "安全长度限制"):
                self.extractor.extract(self.storage_root, relative_path, path.stat().st_size)

    def test_extract_rejects_parent_directory_traversal(self) -> None:
        outside = self.storage_root / "outside.pdf"
        outside.write_bytes(build_text_pdf(["Outside private candidate resume text."]))

        with self.assertRaisesRegex(ResumePdfExtractorError, "路径无效"):
            self.extractor.extract(self.storage_root, "../outside.pdf", outside.stat().st_size)

    def test_extract_rejects_staging_file(self) -> None:
        staging = self.storage_root / "v2" / "resumes" / ".staging"
        staging.mkdir(parents=True)
        path = staging / "temporary.pdf"
        path.write_bytes(build_text_pdf(["Temporary candidate resume text."]))

        with self.assertRaisesRegex(ResumePdfExtractorError, "路径无效"):
            self.extractor.extract(
                self.storage_root,
                path.relative_to(self.storage_root).as_posix(),
                path.stat().st_size,
            )

    def test_extract_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(ResumePdfExtractorError, "文件不存在"):
            self.extractor.extract(
                self.storage_root,
                "v2/resumes/2026/08/missing.pdf",
                100,
            )

    def test_extract_rejects_size_mismatch(self) -> None:
        content = build_text_pdf(["Candidate resume text for size validation."])
        relative_path, path = self.create_file("resume.pdf", content)

        with self.assertRaisesRegex(ResumePdfExtractorError, "大小与上传记录不一致"):
            self.extractor.extract(self.storage_root, relative_path, path.stat().st_size + 1)

    def test_quality_check_rejects_replacement_characters(self) -> None:
        with self.assertRaisesRegex(ResumePdfExtractorError, "字体编码问题"):
            self.extractor._validate_quality("Candidate resume text" + "\ufffd" * 4)
