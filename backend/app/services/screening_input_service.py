from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.schemas.screening_evaluation import (
    ScreeningCandidateMaterial,
    ScreeningProfileMaterial,
)


_SENSITIVE_KEYS = {
    "name",
    "phone",
    "email",
    "gender",
    "age",
    "birth_date",
    "birthday",
    "nationality",
    "ethnicity",
    "marital_status",
    "marriage_status",
    "fertility_status",
    "photo",
    "id_card",
    "id_number",
    "address",
    "location",
    "birthplace",
    "native_place",
    "github",
    "linkedin",
}
_SENSITIVE_LINE = re.compile(
    r"(?im)^\s*(?:姓名|手机|电话|联系方式|邮箱|电子邮件|性别|年龄|出生日期|生日|民族|"
    r"婚姻|婚育|生育|籍贯|身份证号?|住址|地址|详细地址|照片|主页|个人主页|github|linkedin)\s*[:：].*$"
)
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")
_ID_CARD = re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)")
_URL = re.compile(r"https?://\S+", re.IGNORECASE)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return dumped
    return {}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for raw in value if (item := _mapping(raw))]


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            continue
        cleaned = item.strip()
        normalized = cleaned.casefold()
        if normalized not in seen:
            seen.add(normalized)
            result.append(cleaned)
    return result


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _profile_from_mapping(value: Mapping[str, Any]) -> ScreeningProfileMaterial:
    basic_info = _mapping(value.get("basic_info"))

    def preferred(key: str) -> Any:
        direct = value.get(key)
        return direct if direct is not None else basic_info.get(key)

    education_records = [
        {
            "degree": _optional_text(item.get("degree")),
            "major": _optional_text(item.get("major")),
            "start_date": _optional_text(item.get("start_date")),
            "end_date": _optional_text(item.get("end_date")),
        }
        for item in _list_of_mappings(value.get("education_records") or value.get("educations"))
    ]
    education_records = [item for item in education_records if any(item.values())]
    work_experiences = [
        {
            "company": _optional_text(item.get("company")),
            "title": _optional_text(item.get("title")),
            "start_date": _optional_text(item.get("start_date")),
            "end_date": _optional_text(item.get("end_date")),
            "description": _optional_text(item.get("description")),
            "tech_stack": _clean_list(item.get("tech_stack")),
        }
        for item in _list_of_mappings(value.get("work_experiences"))
    ]
    work_experiences = [item for item in work_experiences if any(item.values())]
    project_experiences = [
        {
            "project_name": _optional_text(item.get("project_name")),
            "role": _optional_text(item.get("role")),
            "start_date": _optional_text(item.get("start_date")),
            "end_date": _optional_text(item.get("end_date")),
            "description": _optional_text(item.get("description")),
            "tech_stack": _clean_list(item.get("tech_stack")),
            "achievements": _optional_text(item.get("achievements")),
        }
        for item in _list_of_mappings(value.get("project_experiences"))
    ]
    project_experiences = [item for item in project_experiences if any(item.values())]
    return ScreeningProfileMaterial(
        current_title=_optional_text(preferred("current_title")),
        work_years=_optional_int(preferred("work_years")),
        education_level=_optional_text(preferred("education_level")),
        skills=_clean_list(value.get("skills")),
        certifications=_clean_list(value.get("certifications")),
        self_evaluation=_optional_text(value.get("self_evaluation")),
        education_records=education_records,
        work_experiences=work_experiences,
        project_experiences=project_experiences,
    )


def _collect_known_sensitive_values(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key.casefold() in _SENSITIVE_KEYS and isinstance(item, (str, int)):
                text = str(item).strip()
                if (text.isdigit() and len(text) >= 6) or (
                    not text.isdigit() and len(text) >= 2
                ):
                    result.add(text)
            result.update(_collect_known_sensitive_values(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            result.update(_collect_known_sensitive_values(item))
    return result


def _redact_resume_text(raw_text: str | None, sensitive_values: set[str]) -> str | None:
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None
    redacted = _SENSITIVE_LINE.sub("", raw_text)
    for value in sorted(sensitive_values, key=len, reverse=True):
        redacted = redacted.replace(value, "[已移除敏感信息]")
    for pattern in (_EMAIL, _PHONE, _ID_CARD, _URL):
        redacted = pattern.sub("[已移除敏感信息]", redacted)
    redacted = re.sub(r"\n{3,}", "\n\n", redacted).strip()
    if not redacted.replace("[已移除敏感信息]", "").strip():
        return None
    return redacted or None


class ScreeningInputService:
    """Build the only candidate payload allowed to cross the model boundary."""

    @staticmethod
    def build_candidate_material(
        *,
        application_ref: str,
        confirmed_profile: Mapping[str, Any] | None,
        resume_raw_text: str | None,
        resume_snapshot: Mapping[str, Any] | None,
    ) -> ScreeningCandidateMaterial:
        confirmed = _mapping(confirmed_profile)
        snapshot_envelope = _mapping(resume_snapshot)
        snapshot_draft = _mapping(snapshot_envelope.get("draft"))
        snapshot = snapshot_draft or snapshot_envelope
        sensitive_values = _collect_known_sensitive_values(confirmed)
        sensitive_values.update(_collect_known_sensitive_values(snapshot_envelope))
        return ScreeningCandidateMaterial(
            application_ref=application_ref,
            confirmed_profile=_profile_from_mapping(confirmed),
            resume_text=_redact_resume_text(resume_raw_text, sensitive_values),
            structured_resume=_profile_from_mapping(snapshot),
        )


screening_input_service = ScreeningInputService()


__all__ = ["ScreeningInputService", "screening_input_service"]
