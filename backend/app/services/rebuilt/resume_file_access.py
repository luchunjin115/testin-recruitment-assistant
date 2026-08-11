from __future__ import annotations

from pathlib import Path

from app.services.rebuilt.resume_storage import (
    RESUME_NAMESPACE,
    STAGING_DIRECTORY,
    TRASH_DIRECTORY,
)


class ResumeFileAccessError(ValueError):
    """A safe file access error that never exposes an absolute server path."""


class ResumeFileAccess:
    def resolve(
        self,
        storage_root: Path,
        relative_path: str,
        expected_size: int | None,
        expected_extension: str,
        format_name: str,
    ) -> Path:
        try:
            root = storage_root.resolve()
            namespace = (root / RESUME_NAMESPACE).resolve()
            target = (root / relative_path).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise ResumeFileAccessError("简历文件路径无效") from exc

        if not target.is_relative_to(namespace) or target == namespace:
            raise ResumeFileAccessError("简历文件路径无效")
        private_parts = target.relative_to(namespace).parts
        if STAGING_DIRECTORY in private_parts or TRASH_DIRECTORY in private_parts:
            raise ResumeFileAccessError("简历文件路径无效")
        if target.suffix.lower() != expected_extension:
            raise ResumeFileAccessError(f"当前提取器只支持 {format_name} 文件")
        if not target.is_file():
            raise ResumeFileAccessError("原始简历文件不存在")
        if expected_size is None:
            raise ResumeFileAccessError("简历记录缺少文件大小元数据")

        try:
            actual_size = target.stat().st_size
        except OSError as exc:
            raise ResumeFileAccessError("无法读取简历文件信息") from exc
        if actual_size != expected_size:
            raise ResumeFileAccessError("简历文件大小与上传记录不一致")
        return target


resume_file_access = ResumeFileAccess()
