from __future__ import annotations

import zipfile
from pathlib import Path

import mammoth
from docx import Document
from docx.document import Document as DocumentObject
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.rebuilt.resume_file_access import (
    ResumeFileAccess,
    ResumeFileAccessError,
    resume_file_access,
)


MAX_DOCX_ARCHIVE_ENTRIES = 2_000
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 1_000_000


class ResumeDocxExtractorError(ValueError):
    """A stable DOCX extraction error suitable for Resume.parse_error."""


class ResumeDocxExtractor:
    def __init__(self, file_access: ResumeFileAccess = resume_file_access) -> None:
        self.file_access = file_access

    def extract(
        self,
        storage_root: Path,
        relative_path: str,
        expected_size: int | None,
    ) -> str:
        try:
            target = self.file_access.resolve(
                storage_root,
                relative_path,
                expected_size,
                expected_extension=".docx",
                format_name="DOCX",
            )
        except ResumeFileAccessError as exc:
            raise ResumeDocxExtractorError(str(exc)) from exc

        contains_text_boxes = self._validate_archive(target)
        try:
            document = Document(target)
        except (OSError, ValueError, KeyError, PackageNotFoundError, zipfile.BadZipFile) as exc:
            raise ResumeDocxExtractorError("DOCX 文件损坏或无法读取") from exc
        except Exception as exc:
            raise ResumeDocxExtractorError("DOCX 文件损坏或无法读取") from exc

        standard_text = self._extract_document_content(document)

        # python-docx intentionally exposes body paragraphs and tables, but not
        # Word/VML text boxes. Resume templates frequently put nearly all visible
        # content in those text boxes, so use Mammoth for that document shape.
        if contains_text_boxes or not standard_text:
            try:
                mammoth_text = self._extract_with_mammoth(target)
            except ResumeDocxExtractorError:
                if standard_text:
                    return standard_text
                raise
            if mammoth_text:
                return mammoth_text

        if standard_text:
            return standard_text
        raise ResumeDocxExtractorError("DOCX 简历没有可提取的有效文本")

    @staticmethod
    def _validate_archive(target: Path) -> bool:
        try:
            with zipfile.ZipFile(target) as archive:
                members = archive.infolist()
                if len(members) > MAX_DOCX_ARCHIVE_ENTRIES:
                    raise ResumeDocxExtractorError("DOCX 文件结构过于复杂")
                if any(member.flag_bits & 0x1 for member in members):
                    raise ResumeDocxExtractorError("DOCX 已加密，暂不支持提取")

                uncompressed_size = sum(member.file_size for member in members)
                if uncompressed_size > MAX_DOCX_UNCOMPRESSED_BYTES:
                    raise ResumeDocxExtractorError("DOCX 解压后内容超过安全限制")

                try:
                    document_xml = archive.read("word/document.xml")
                except KeyError as exc:
                    raise ResumeDocxExtractorError("DOCX 文件损坏或无法读取") from exc
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
            raise ResumeDocxExtractorError("DOCX 文件损坏或无法读取") from exc

        return b"txbxContent" in document_xml

    @classmethod
    def _extract_with_mammoth(cls, target: Path) -> str:
        try:
            with target.open("rb") as source:
                result = mammoth.extract_raw_text(source)
        except Exception as exc:
            raise ResumeDocxExtractorError("DOCX 文件损坏或无法读取") from exc

        parts = [line.strip() for line in result.value.splitlines() if line.strip()]
        character_count = sum(len(part) for part in parts)
        if character_count > MAX_EXTRACTED_CHARACTERS:
            raise ResumeDocxExtractorError("DOCX 提取文本超过安全长度限制")
        return "\n".join(parts)

    @classmethod
    def _extract_document_content(cls, document: DocumentObject) -> str:
        parts: list[str] = []
        character_count = 0

        def append_part(value: str) -> None:
            nonlocal character_count
            cleaned = value.strip()
            if not cleaned:
                return
            character_count += len(cleaned)
            if character_count > MAX_EXTRACTED_CHARACTERS:
                raise ResumeDocxExtractorError("DOCX 提取文本超过安全长度限制")
            parts.append(cleaned)

        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                append_part(block.text)
            elif isinstance(block, Table):
                for row in block.rows:
                    cell_texts: list[str] = []
                    seen_cells: set[int] = set()
                    for cell in row.cells:
                        cell_identity = id(cell._tc)
                        if cell_identity in seen_cells:
                            continue
                        seen_cells.add(cell_identity)
                        paragraphs = [
                            paragraph.text.strip()
                            for paragraph in cell.paragraphs
                            if paragraph.text.strip()
                        ]
                        if paragraphs:
                            cell_texts.append("\n".join(paragraphs))
                    append_part("\t".join(cell_texts))

        return "\n".join(parts)


resume_docx_extractor = ResumeDocxExtractor()
