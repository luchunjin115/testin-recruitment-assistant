from __future__ import annotations

from pathlib import Path

import pdfplumber
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from app.services.rebuilt.resume_file_access import (
    ResumeFileAccess,
    ResumeFileAccessError,
    resume_file_access,
)


MIN_EFFECTIVE_CHARACTERS = 10
MAX_PDF_PAGES = 100
MAX_EXTRACTED_CHARACTERS = 1_000_000
PDF_X_TOLERANCE = 2
PDF_Y_TOLERANCE = 3


class ResumePdfExtractorError(ValueError):
    """A stable PDF extraction error suitable for Resume.parse_error."""


class ResumePdfExtractor:
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
                expected_extension=".pdf",
                format_name="PDF",
            )
        except ResumeFileAccessError as exc:
            raise ResumePdfExtractorError(str(exc)) from exc

        try:
            reader = PdfReader(str(target), strict=False)
        except (OSError, PdfReadError, ValueError, RecursionError) as exc:
            raise ResumePdfExtractorError("PDF 文件损坏或无法读取") from exc

        if reader.is_encrypted:
            try:
                decrypt_result = reader.decrypt("")
            except Exception as exc:
                raise ResumePdfExtractorError("PDF 已加密，暂不支持提取") from exc
            if decrypt_result == 0:
                raise ResumePdfExtractorError("PDF 已加密，暂不支持提取")

        try:
            page_count = len(reader.pages)
        except (PdfReadError, ValueError, RecursionError) as exc:
            raise ResumePdfExtractorError("PDF 文件损坏或无法读取") from exc
        if page_count == 0:
            raise ResumePdfExtractorError("PDF 不包含任何页面")
        if page_count > MAX_PDF_PAGES:
            raise ResumePdfExtractorError(
                f"PDF 页数超过 {MAX_PDF_PAGES} 页限制"
            )

        page_texts: list[str] = []
        extracted_characters = 0
        try:
            layout_pdf = pdfplumber.open(target)
        except Exception as exc:
            raise ResumePdfExtractorError("PDF 文件损坏或无法读取") from exc

        try:
            if len(layout_pdf.pages) != page_count:
                raise ResumePdfExtractorError("PDF 页面结构不一致，无法可靠提取")

            for page_number, page in enumerate(layout_pdf.pages, start=1):
                try:
                    page_text = page.extract_text(
                        x_tolerance=PDF_X_TOLERANCE,
                        y_tolerance=PDF_Y_TOLERANCE,
                        layout=False,
                        use_text_flow=False,
                    ) or ""
                except Exception as exc:
                    raise ResumePdfExtractorError(
                        f"PDF 第 {page_number} 页文字提取失败"
                    ) from exc
                stripped_text = page_text.strip()
                if stripped_text:
                    extracted_characters += len(stripped_text)
                    if extracted_characters > MAX_EXTRACTED_CHARACTERS:
                        raise ResumePdfExtractorError("PDF 提取文本超过安全长度限制")
                    page_texts.append(stripped_text)
        finally:
            layout_pdf.close()

        if not page_texts:
            raise ResumePdfExtractorError(
                "PDF 未检测到可提取文字，可能是扫描件，需要 OCR"
            )

        text = "\n\n".join(page_texts)
        self._validate_quality(text)
        return text

    @staticmethod
    def _validate_quality(text: str) -> None:
        effective_characters = [character for character in text if not character.isspace()]
        if len(effective_characters) < MIN_EFFECTIVE_CHARACTERS:
            raise ResumePdfExtractorError("PDF 提取到的有效文字过少，无法可靠使用")

        disallowed_controls = sum(
            1
            for character in text
            if ord(character) < 32 and character not in "\r\n\t"
        )
        replacement_characters = text.count("\ufffd")
        suspicious_count = disallowed_controls + replacement_characters
        if suspicious_count / max(len(text), 1) > 0.01:
            raise ResumePdfExtractorError("PDF 文本提取质量过低，可能存在字体编码问题")


resume_pdf_extractor = ResumePdfExtractor()
