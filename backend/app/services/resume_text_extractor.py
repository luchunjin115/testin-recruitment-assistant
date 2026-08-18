from __future__ import annotations

from pathlib import Path

from app.services.resume_file_access import (
    ResumeFileAccess,
    ResumeFileAccessError,
    resume_file_access,
)
from app.services.resume_storage import (
    InvalidResumeContentError,
    ResumeFileStorage,
)


class ResumeTextExtractorError(ValueError):
    """A stable extraction error that can be stored without leaking local paths."""


class ResumeTextExtractor:
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
                expected_extension=".txt",
                format_name="TXT",
            )
        except ResumeFileAccessError as exc:
            raise ResumeTextExtractorError(str(exc)) from exc

        try:
            text = ResumeFileStorage.read_text_content(target)
        except InvalidResumeContentError as exc:
            raise ResumeTextExtractorError(str(exc)) from exc
        except OSError as exc:
            raise ResumeTextExtractorError("读取 TXT 简历失败") from exc

        if not text.strip():
            raise ResumeTextExtractorError("TXT 简历没有可提取的有效文本")
        return text


resume_text_extractor = ResumeTextExtractor()
