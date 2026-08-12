import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


RESUME_PARSE_SCHEMA_VERSION = "1.0"

WORK_DESCRIPTION_MAX_LENGTH = 10_000
PROJECT_DESCRIPTION_MAX_LENGTH = 10_000
PROJECT_ACHIEVEMENTS_MAX_LENGTH = 5_000
SELF_EVALUATION_MAX_LENGTH = 5_000

_DATE_PATTERN = re.compile(r"^(\d{4})(?:-(0[1-9]|1[0-2]))?$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_ALLOWED_PATTERN = re.compile(r"^\+?[0-9() .-]+$")


def _optional_text(max_length: int) -> Any:
    return Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            strict=True,
            min_length=1,
            max_length=max_length,
        ),
    ] | None


NameText = _optional_text(100)
PhoneText = _optional_text(20)
EmailText = _optional_text(100)
GenderText = _optional_text(10)
LocationText = _optional_text(100)
CompanyText = _optional_text(200)
TitleText = _optional_text(200)
EducationLevelText = _optional_text(50)
SchoolText = _optional_text(200)
DegreeText = _optional_text(50)
MajorText = _optional_text(200)
ProjectNameText = _optional_text(200)
RoleText = _optional_text(100)
DateText = _optional_text(20)
WorkDescriptionText = _optional_text(WORK_DESCRIPTION_MAX_LENGTH)
ProjectDescriptionText = _optional_text(PROJECT_DESCRIPTION_MAX_LENGTH)
ProjectAchievementsText = _optional_text(PROJECT_ACHIEVEMENTS_MAX_LENGTH)
SelfEvaluationText = _optional_text(SELF_EVALUATION_MAX_LENGTH)

SkillText = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=100),
]
CertificationText = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=200),
]
WarningText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=500),
]
MissingFieldText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=200),
]


class StrictDraftModel(BaseModel):
    """Common model policy for untrusted model-produced draft data."""

    model_config = ConfigDict(extra="forbid", strict=True)


def _clean_unique_string_list(value: Any) -> Any:
    """Trim, remove blank entries, and keep the first exact occurrence."""
    if not isinstance(value, list):
        return value

    cleaned: list[Any] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            cleaned.append(item)
            continue

        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _validate_date(value: str | None, *, allow_present: bool) -> str | None:
    if value is None:
        return None
    if value == "至今":
        if allow_present:
            return value
        raise ValueError("至今只能作为结束时间")
    if not _DATE_PATTERN.fullmatch(value):
        raise ValueError("日期必须为 YYYY、YYYY-MM 或结束时间使用至今")
    return value


def _date_parts(value: str) -> tuple[int, int | None]:
    match = _DATE_PATTERN.fullmatch(value)
    if match is None:  # pragma: no cover - date fields are validated first
        raise ValueError("日期格式无效")
    return int(match.group(1)), int(match.group(2)) if match.group(2) else None


def _validate_date_order(start_date: str | None, end_date: str | None) -> None:
    if start_date is None or end_date is None or end_date == "至今":
        return

    start_year, start_month = _date_parts(start_date)
    end_year, end_month = _date_parts(end_date)
    if start_year > end_year:
        raise ValueError("开始时间不能明显晚于结束时间")
    if (
        start_year == end_year
        and start_month is not None
        and end_month is not None
        and start_month > end_month
    ):
        raise ValueError("开始时间不能明显晚于结束时间")


class ResumeBasicInfoDraft(StrictDraftModel):
    name: NameText
    phone: PhoneText
    email: EmailText
    gender: GenderText
    age: int | None = Field(ge=0, le=120)
    location: LocationText
    current_company: CompanyText
    current_title: TitleText
    work_years: int | None = Field(ge=0, le=80)
    education_level: EducationLevelText

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _PHONE_ALLOWED_PATTERN.fullmatch(value):
            raise ValueError("电话号码包含不支持的字符")
        digit_count = sum(character.isdigit() for character in value)
        if not 6 <= digit_count <= 15:
            raise ValueError("电话号码应包含 6 到 15 位数字")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _EMAIL_PATTERN.fullmatch(value):
            raise ValueError("邮箱格式不合理")
        local_part, domain = value.rsplit("@", 1)
        if (
            len(local_part) > 64
            or local_part.startswith(".")
            or local_part.endswith(".")
            or ".." in local_part
            or domain.startswith(".")
            or domain.endswith(".")
            or ".." in domain
        ):
            raise ValueError("邮箱格式不合理")
        return value


class ResumeEducationDraft(StrictDraftModel):
    school: SchoolText
    degree: DegreeText
    major: MajorText
    start_date: DateText
    end_date: DateText

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, value: str | None) -> str | None:
        return _validate_date(value, allow_present=False)

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, value: str | None) -> str | None:
        return _validate_date(value, allow_present=True)

    @model_validator(mode="after")
    def validate_record(self) -> "ResumeEducationDraft":
        if all(
            value is None
            for value in (self.school, self.degree, self.major, self.start_date, self.end_date)
        ):
            raise ValueError("教育经历不能完全为空")
        _validate_date_order(self.start_date, self.end_date)
        return self


class ResumeWorkExperienceDraft(StrictDraftModel):
    company: CompanyText
    title: TitleText
    start_date: DateText
    end_date: DateText
    description: WorkDescriptionText
    tech_stack: list[SkillText]

    @field_validator("tech_stack", mode="before")
    @classmethod
    def clean_tech_stack(cls, value: Any) -> Any:
        return _clean_unique_string_list(value)

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, value: str | None) -> str | None:
        return _validate_date(value, allow_present=False)

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, value: str | None) -> str | None:
        return _validate_date(value, allow_present=True)

    @model_validator(mode="after")
    def validate_record(self) -> "ResumeWorkExperienceDraft":
        if all(
            value is None
            for value in (self.company, self.title, self.start_date, self.end_date, self.description)
        ) and not self.tech_stack:
            raise ValueError("工作经历不能完全为空")
        _validate_date_order(self.start_date, self.end_date)
        return self


class ResumeProjectExperienceDraft(StrictDraftModel):
    project_name: ProjectNameText
    role: RoleText
    start_date: DateText
    end_date: DateText
    description: ProjectDescriptionText
    tech_stack: list[SkillText]
    achievements: ProjectAchievementsText

    @field_validator("tech_stack", mode="before")
    @classmethod
    def clean_tech_stack(cls, value: Any) -> Any:
        return _clean_unique_string_list(value)

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, value: str | None) -> str | None:
        return _validate_date(value, allow_present=False)

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, value: str | None) -> str | None:
        return _validate_date(value, allow_present=True)

    @model_validator(mode="after")
    def validate_record(self) -> "ResumeProjectExperienceDraft":
        if all(
            value is None
            for value in (
                self.project_name,
                self.role,
                self.start_date,
                self.end_date,
                self.description,
                self.achievements,
            )
        ) and not self.tech_stack:
            raise ValueError("项目经历不能完全为空")
        _validate_date_order(self.start_date, self.end_date)
        return self


class ResumeParseDraft(StrictDraftModel):
    schema_version: Literal[RESUME_PARSE_SCHEMA_VERSION]
    basic_info: ResumeBasicInfoDraft
    education_records: list[ResumeEducationDraft]
    work_experiences: list[ResumeWorkExperienceDraft]
    project_experiences: list[ResumeProjectExperienceDraft]
    skills: list[SkillText]
    certifications: list[CertificationText]
    self_evaluation: SelfEvaluationText
    warnings: list[WarningText]
    missing_fields: list[MissingFieldText]

    @field_validator("skills", "certifications", mode="before")
    @classmethod
    def clean_unique_lists(cls, value: Any) -> Any:
        return _clean_unique_string_list(value)
