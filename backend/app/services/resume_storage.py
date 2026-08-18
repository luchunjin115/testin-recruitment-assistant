from __future__ import annotations

import os
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import chardet
from fastapi import UploadFile


RESUME_NAMESPACE = Path("v2") / "resumes"
STAGING_DIRECTORY = ".staging"
TRASH_DIRECTORY = ".trash"
CHUNK_SIZE = 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
CANONICAL_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


class ResumeUploadError(ValueError):
    """Base class for upload errors that are safe to expose to API clients."""


class InvalidResumeFilenameError(ResumeUploadError):
    pass


class UnsupportedResumeTypeError(ResumeUploadError):
    pass


class EmptyResumeFileError(ResumeUploadError):
    pass


class ResumeFileTooLargeError(ResumeUploadError):
    pass


class InvalidResumeContentError(ResumeUploadError):
    pass


class ResumeStorageError(RuntimeError):
    pass


@dataclass(slots=True)
class PreparedResumeFile:
    original_filename: str
    extension: str
    mime_type: str
    file_size: int
    temp_path: Path
    final_path: Path
    relative_path: str


class ResumeFileStorage:
    async def prepare(
        self,
        upload: UploadFile,
        upload_root: Path,
        max_size_bytes: int,
    ) -> PreparedResumeFile:
        original_filename, extension = self._normalize_filename(upload.filename)
        if extension not in ALLOWED_EXTENSIONS:
            supported = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise UnsupportedResumeTypeError(f"不支持的文件扩展名，支持: {supported}")
        if max_size_bytes <= 0:
            raise ValueError("max_size_bytes must be positive")

        root = upload_root.resolve()
        namespace = (root / RESUME_NAMESPACE).resolve()
        self._ensure_within_root(root, namespace)
        staging_dir = namespace / STAGING_DIRECTORY
        now = datetime.now(timezone.utc)
        final_dir = namespace / f"{now.year:04d}" / f"{now.month:02d}"
        stored_name = f"{uuid.uuid4().hex}{extension}"
        temp_path = staging_dir / f"{uuid.uuid4().hex}.part"
        final_path = final_dir / stored_name

        try:
            staging_dir.mkdir(parents=True, exist_ok=True)
            file_size = await self._write_limited(upload, temp_path, max_size_bytes)
            mime_type = self._detect_and_validate_content(temp_path, extension)
        except ResumeUploadError:
            self.discard_path(temp_path)
            raise
        except OSError as exc:
            self.discard_path(temp_path)
            raise ResumeStorageError("文件暂存失败") from exc

        return PreparedResumeFile(
            original_filename=original_filename,
            extension=extension,
            mime_type=mime_type,
            file_size=file_size,
            temp_path=temp_path,
            final_path=final_path,
            relative_path=final_path.relative_to(root).as_posix(),
        )

    def promote(self, prepared: PreparedResumeFile) -> None:
        try:
            prepared.final_path.parent.mkdir(parents=True, exist_ok=True)
            if prepared.final_path.exists():
                raise ResumeStorageError("服务端文件名冲突")
            os.replace(prepared.temp_path, prepared.final_path)
        except ResumeStorageError:
            raise
        except OSError as exc:
            raise ResumeStorageError("文件落盘失败") from exc

    @staticmethod
    def discard(prepared: PreparedResumeFile) -> None:
        ResumeFileStorage.discard_path(prepared.temp_path)
        ResumeFileStorage.discard_path(prepared.final_path)

    @staticmethod
    def discard_path(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise ResumeStorageError(f"文件清理失败: {path.name}") from exc

    @staticmethod
    async def _write_limited(upload: UploadFile, target: Path, max_size_bytes: int) -> int:
        size = 0
        with target.open("xb") as output:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_size_bytes:
                    raise ResumeFileTooLargeError("文件大小超过限制")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())

        if size == 0:
            raise EmptyResumeFileError("不能上传空文件")
        return size

    @staticmethod
    def _normalize_filename(filename: str | None) -> tuple[str, str]:
        raw_name = (filename or "").replace("\\", "/")
        name = PurePosixPath(raw_name).name.strip()
        if not name or name in {".", ".."}:
            raise InvalidResumeFilenameError("文件名不能为空")
        if len(name) > 255:
            raise InvalidResumeFilenameError("文件名不能超过255个字符")
        if any(ord(character) < 32 for character in name):
            raise InvalidResumeFilenameError("文件名包含非法控制字符")
        return name, PurePosixPath(name).suffix.lower()

    @staticmethod
    def _detect_and_validate_content(path: Path, extension: str) -> str:
        with path.open("rb") as source:
            header = source.read(8)

        if header.startswith(b"%PDF-"):
            detected_extension = ".pdf"
        elif zipfile.is_zipfile(path):
            try:
                with zipfile.ZipFile(path) as archive:
                    names = set(archive.namelist())
            except (OSError, zipfile.BadZipFile) as exc:
                raise InvalidResumeContentError("DOCX 文件结构无效") from exc
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise InvalidResumeContentError("压缩文件不是有效的 DOCX 简历")
            detected_extension = ".docx"
        else:
            ResumeFileStorage.read_text_content(path)
            detected_extension = ".txt"

        if detected_extension != extension:
            raise InvalidResumeContentError("文件扩展名与实际内容类型不一致")
        return CANONICAL_MIME_TYPES[detected_extension]

    @staticmethod
    def read_text_content(path: Path) -> str:
        raw = path.read_bytes()
        detection = chardet.detect(raw)
        candidates = [detection.get("encoding"), "utf-8", "gb18030"]
        text = None
        for encoding in dict.fromkeys(value for value in candidates if value):
            try:
                text = raw.decode(encoding, errors="strict")
                break
            except (LookupError, UnicodeDecodeError):
                continue
        if text is None:
            raise InvalidResumeContentError("TXT 文件不是可识别的文本")

        disallowed_controls = sum(
            1
            for character in text
            if ord(character) < 32 and character not in "\r\n\t"
        )
        if disallowed_controls / max(len(text), 1) > 0.01:
            raise InvalidResumeContentError("TXT 文件包含过多二进制控制字符")
        return text

    @staticmethod
    def _ensure_within_root(root: Path, path: Path) -> None:
        if not path.is_relative_to(root):
            raise ResumeStorageError("新版简历目录越出上传根目录")


resume_file_storage = ResumeFileStorage()
