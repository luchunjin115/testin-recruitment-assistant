from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.services.resume_file_access import (
    ResumeFileAccess,
    ResumeFileAccessError,
    resume_file_access,
)
from app.services.resume_storage import (
    ALLOWED_EXTENSIONS,
    CANONICAL_MIME_TYPES,
    RESUME_NAMESPACE,
    TRASH_DIRECTORY,
)


TRASH_FILE_PATTERN = re.compile(
    rf"^resume-(?P<resume_id>[1-9]\d*)-(?P<token>[0-9a-f]{{32}})"
    rf"(?P<extension>{'|'.join(re.escape(value) for value in sorted(ALLOWED_EXTENSIONS))})$"
)


class UnsupportedResumeCleanupError(ValueError):
    """The stored MIME type cannot be safely matched to an allowed extension."""


class ResumeCleanupValidationError(ValueError):
    """The database metadata and stored file do not describe the same safe file."""


class ResumeCleanupStorageError(RuntimeError):
    """A filesystem operation failed without exposing an absolute path."""


@dataclass(frozen=True, slots=True)
class QuarantinedResumeFile:
    original_path: Path
    quarantined_path: Path


@dataclass(frozen=True, slots=True)
class TrashResumeFile:
    resume_id: int
    path: Path


class ResumeFileCleanup:
    def quarantine(
        self,
        storage_root: Path,
        relative_path: str,
        file_type: str | None,
        expected_size: int | None,
        resume_id: int,
        file_access: ResumeFileAccess = resume_file_access,
    ) -> QuarantinedResumeFile:
        if resume_id <= 0:
            raise ValueError("resume_id must be positive")
        file_format = next(
            (
                (extension, extension.removeprefix(".").upper())
                for extension, mime_type in CANONICAL_MIME_TYPES.items()
                if mime_type == file_type
            ),
            None,
        )
        if file_format is None:
            raise UnsupportedResumeCleanupError("当前文件类型不支持安全清理")

        expected_extension, format_name = file_format
        try:
            original_path = file_access.resolve(
                storage_root,
                relative_path,
                expected_size,
                expected_extension=expected_extension,
                format_name=format_name,
            )
        except ResumeFileAccessError as exc:
            raise ResumeCleanupValidationError(str(exc)) from exc

        root = storage_root.resolve()
        namespace = (root / RESUME_NAMESPACE).resolve()
        trash_directory = (namespace / TRASH_DIRECTORY).resolve()
        if not trash_directory.is_relative_to(namespace):
            raise ResumeCleanupStorageError("简历待清理目录无效")
        quarantined_path = (
            trash_directory
            / f"resume-{resume_id}-{uuid.uuid4().hex}{expected_extension}"
        )

        try:
            trash_directory.mkdir(parents=True, exist_ok=True)
            if quarantined_path.exists():
                raise ResumeCleanupStorageError("简历待清理文件名冲突")
            os.replace(original_path, quarantined_path)
        except ResumeCleanupStorageError:
            raise
        except OSError as exc:
            raise ResumeCleanupStorageError("简历文件进入待清理区失败") from exc

        return QuarantinedResumeFile(
            original_path=original_path,
            quarantined_path=quarantined_path,
        )

    @staticmethod
    def restore(quarantined: QuarantinedResumeFile) -> None:
        try:
            if quarantined.original_path.exists():
                raise ResumeCleanupStorageError("简历原位置已存在文件，无法安全恢复")
            if not quarantined.quarantined_path.is_file():
                raise ResumeCleanupStorageError("待清理简历文件不存在，无法恢复")
            quarantined.original_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(quarantined.quarantined_path, quarantined.original_path)
        except ResumeCleanupStorageError:
            raise
        except OSError as exc:
            raise ResumeCleanupStorageError("简历文件恢复失败") from exc

    @staticmethod
    def purge(quarantined: QuarantinedResumeFile) -> None:
        try:
            quarantined.quarantined_path.unlink(missing_ok=True)
        except OSError as exc:
            raise ResumeCleanupStorageError("待清理简历文件删除失败") from exc

    @staticmethod
    def list_trash_files(
        storage_root: Path,
        limit: int,
    ) -> list[TrashResumeFile]:
        if limit <= 0:
            raise ValueError("limit must be positive")

        root = storage_root.resolve()
        namespace = (root / RESUME_NAMESPACE).resolve()
        trash_directory = namespace / TRASH_DIRECTORY
        if not trash_directory.exists():
            return []
        if trash_directory.is_symlink():
            raise ResumeCleanupStorageError("简历待清理目录不能是符号链接")

        resolved_trash = trash_directory.resolve()
        if not resolved_trash.is_relative_to(namespace):
            raise ResumeCleanupStorageError("简历待清理目录无效")

        entries: list[TrashResumeFile] = []
        try:
            children = sorted(trash_directory.iterdir(), key=lambda value: value.name)
            for child in children:
                if len(entries) >= limit:
                    break
                match = TRASH_FILE_PATTERN.fullmatch(child.name)
                if match is None or child.is_symlink() or not child.is_file():
                    continue
                resolved_child = child.resolve()
                if resolved_child.parent != resolved_trash:
                    continue
                entries.append(
                    TrashResumeFile(
                        resume_id=int(match.group("resume_id")),
                        path=resolved_child,
                    )
                )
        except OSError as exc:
            raise ResumeCleanupStorageError("无法扫描简历待清理目录") from exc
        return entries

    @staticmethod
    def purge_trash_file(storage_root: Path, trash_file: TrashResumeFile) -> None:
        root = storage_root.resolve()
        expected_directory = (root / RESUME_NAMESPACE / TRASH_DIRECTORY).resolve()
        match = TRASH_FILE_PATTERN.fullmatch(trash_file.path.name)
        try:
            target = trash_file.path.resolve()
        except OSError as exc:
            raise ResumeCleanupStorageError("待清理简历文件路径无效") from exc
        if (
            match is None
            or int(match.group("resume_id")) != trash_file.resume_id
            or target.parent != expected_directory
            or not target.is_relative_to(root)
        ):
            raise ResumeCleanupStorageError("待清理简历文件路径无效")
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            raise ResumeCleanupStorageError("待清理简历文件删除失败") from exc


resume_file_cleanup = ResumeFileCleanup()
