from __future__ import annotations

import json
import re
from enum import Enum
from typing import Annotated, Literal, Sequence

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.screening_rubric import (
    FAIRNESS_PROHIBITED_TERMS,
    SemanticRubricCriterion,
)


SCREENING_EVALUATION_SCHEMA_VERSION = "1.0"


ApplicationReference = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        strict=True,
        min_length=13,
        max_length=80,
        pattern=r"^application-[A-Za-z0-9_-]+$",
    ),
]
EvaluationCriterionKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    ),
]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=500),
]
EvidenceQuote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=1_000),
]
ReasonText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=2_000),
]
ResumeText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100_000),
]
SemanticScore = Literal["unknown"] | Annotated[StrictInt, Field(ge=0, le=10)]


_EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")
_ID_CARD_PATTERN = re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)")


def _reject_sensitive_text(value: str) -> str:
    normalized = value.casefold()
    for term in FAIRNESS_PROHIBITED_TERMS:
        normalized_term = term.casefold()
        if normalized_term.isascii():
            if re.search(rf"(?<![a-z]){re.escape(normalized_term)}(?![a-z])", normalized):
                raise ValueError("语义评价输出包含公平性禁止内容")
        elif normalized_term in normalized:
            raise ValueError("语义评价输出包含公平性禁止内容")
    if any(pattern.search(value) for pattern in (_EMAIL_PATTERN, _PHONE_PATTERN, _ID_CARD_PATTERN)):
        raise ValueError("语义评价输出包含联系方式或身份信息")
    return value


class ScreeningConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScreeningEvidenceSource(str, Enum):
    CONFIRMED_PROFILE = "confirmed_profile"
    RESUME_TEXT = "resume_text"
    STRUCTURED_RESUME = "structured_resume"


class ScreeningEducationMaterial(BaseModel):
    degree: ShortText | None = None
    major: ShortText | None = None
    start_date: ShortText | None = None
    end_date: ShortText | None = None

    model_config = ConfigDict(extra="forbid")


class ScreeningWorkMaterial(BaseModel):
    company: ShortText | None = None
    title: ShortText | None = None
    start_date: ShortText | None = None
    end_date: ShortText | None = None
    description: str | None = Field(default=None, min_length=1, max_length=10_000)
    tech_stack: list[ShortText] = Field(default_factory=list, max_length=200)

    model_config = ConfigDict(extra="forbid")


class ScreeningProjectMaterial(BaseModel):
    project_name: ShortText | None = None
    role: ShortText | None = None
    start_date: ShortText | None = None
    end_date: ShortText | None = None
    description: str | None = Field(default=None, min_length=1, max_length=10_000)
    tech_stack: list[ShortText] = Field(default_factory=list, max_length=200)
    achievements: str | None = Field(default=None, min_length=1, max_length=5_000)

    model_config = ConfigDict(extra="forbid")


class ScreeningProfileMaterial(BaseModel):
    current_title: ShortText | None = None
    work_years: StrictInt | None = Field(default=None, ge=0, le=80)
    education_level: ShortText | None = None
    skills: list[ShortText] = Field(default_factory=list, max_length=500)
    certifications: list[ShortText] = Field(default_factory=list, max_length=200)
    self_evaluation: str | None = Field(default=None, min_length=1, max_length=5_000)
    education_records: list[ScreeningEducationMaterial] = Field(
        default_factory=list,
        max_length=100,
    )
    work_experiences: list[ScreeningWorkMaterial] = Field(
        default_factory=list,
        max_length=100,
    )
    project_experiences: list[ScreeningProjectMaterial] = Field(
        default_factory=list,
        max_length=100,
    )

    model_config = ConfigDict(extra="forbid")

    def has_job_related_content(self) -> bool:
        return any(
            (
                self.current_title,
                self.work_years is not None,
                self.education_level,
                self.skills,
                self.certifications,
                self.self_evaluation,
                self.education_records,
                self.work_experiences,
                self.project_experiences,
            )
        )


class ScreeningCandidateMaterial(BaseModel):
    application_ref: ApplicationReference
    confirmed_profile: ScreeningProfileMaterial = Field(
        default_factory=ScreeningProfileMaterial
    )
    resume_text: ResumeText | None = None
    structured_resume: ScreeningProfileMaterial = Field(
        default_factory=ScreeningProfileMaterial
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_minimum_job_related_material(self) -> ScreeningCandidateMaterial:
        if not self.resume_text and not self.confirmed_profile.has_job_related_content():
            raise ValueError("候选人材料不足，不能调用语义评价模型")
        return self

    def serialized_source(self, source: ScreeningEvidenceSource) -> str:
        if source is ScreeningEvidenceSource.RESUME_TEXT:
            return self.resume_text or ""
        profile = (
            self.confirmed_profile
            if source is ScreeningEvidenceSource.CONFIRMED_PROFILE
            else self.structured_resume
        )
        return json.dumps(
            profile.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
        )

    def source_contains_quote(
        self,
        source: ScreeningEvidenceSource | str,
        quote: str,
    ) -> bool:
        source = ScreeningEvidenceSource(source)
        if source is ScreeningEvidenceSource.RESUME_TEXT:
            return quote in (self.resume_text or "")
        profile = (
            self.confirmed_profile
            if source is ScreeningEvidenceSource.CONFIRMED_PROFILE
            else self.structured_resume
        )

        def scalar_values(value: object) -> list[str]:
            if isinstance(value, dict):
                return [
                    text
                    for item in value.values()
                    for text in scalar_values(item)
                ]
            if isinstance(value, list):
                return [text for item in value for text in scalar_values(item)]
            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                return [str(value)]
            return []

        return any(
            quote in source_value
            for source_value in scalar_values(profile.model_dump(mode="python"))
        )


class ScreeningEvidence(BaseModel):
    source: ScreeningEvidenceSource
    locator: ShortText
    quote: EvidenceQuote

    model_config = ConfigDict(extra="forbid")

    @field_validator("locator", "quote")
    @classmethod
    def reject_sensitive_evidence(cls, value: str) -> str:
        return _reject_sensitive_text(value)


class SemanticCriterionEvaluation(BaseModel):
    criterion_key: EvaluationCriterionKey
    score: SemanticScore
    confidence: ScreeningConfidence
    evidence: list[ScreeningEvidence] = Field(default_factory=list, max_length=20)
    reason: ReasonText
    strengths: list[ShortText] = Field(default_factory=list, max_length=20)
    gaps: list[ShortText] = Field(default_factory=list, max_length=20)

    model_config = ConfigDict(extra="forbid")

    @field_validator("reason")
    @classmethod
    def reject_sensitive_reason(cls, value: str) -> str:
        return _reject_sensitive_text(value)

    @field_validator("strengths", "gaps")
    @classmethod
    def reject_sensitive_summary(cls, value: list[str]) -> list[str]:
        return [_reject_sensitive_text(item) for item in value]

    @model_validator(mode="after")
    def validate_unknown_and_evidence_semantics(self) -> SemanticCriterionEvaluation:
        if self.score == "unknown":
            if self.evidence:
                raise ValueError("unknown 评分不能伪装成已有明确证据")
            if self.confidence is not ScreeningConfidence.LOW:
                raise ValueError("unknown 评分的置信度必须为 low")
            if not self.gaps:
                raise ValueError("unknown 评分必须说明缺少什么证据")
        elif not self.evidence:
            raise ValueError("非 unknown 语义评分必须提供可定位证据")
        return self


class ScreeningSemanticEvaluation(BaseModel):
    schema_version: Literal["1.0"] = SCREENING_EVALUATION_SCHEMA_VERSION
    evaluations: list[SemanticCriterionEvaluation] = Field(min_length=4, max_length=10)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_duplicate_criteria(self) -> ScreeningSemanticEvaluation:
        keys = [item.criterion_key.casefold() for item in self.evaluations]
        if len(keys) != len(set(keys)):
            raise ValueError("每个 Rubric 语义评分项必须且只能返回一次")
        return self

    def validate_against(
        self,
        criteria: Sequence[SemanticRubricCriterion],
        candidate_material: ScreeningCandidateMaterial,
    ) -> ScreeningSemanticEvaluation:
        expected_keys = [item.key for item in criteria]
        actual_keys = [item.criterion_key for item in self.evaluations]
        if actual_keys != expected_keys:
            raise ValueError("语义评价必须按 Rubric 顺序完整返回全部评分项")
        for evaluation in self.evaluations:
            for evidence in evaluation.evidence:
                if not candidate_material.source_contains_quote(
                    evidence.source,
                    evidence.quote,
                ):
                    raise ValueError("语义评价证据无法在脱敏候选人材料中定位")
        return self


__all__ = [
    "SCREENING_EVALUATION_SCHEMA_VERSION",
    "ScreeningCandidateMaterial",
    "ScreeningConfidence",
    "ScreeningEducationMaterial",
    "ScreeningEvidence",
    "ScreeningEvidenceSource",
    "ScreeningProfileMaterial",
    "ScreeningProjectMaterial",
    "ScreeningSemanticEvaluation",
    "ScreeningWorkMaterial",
    "SemanticCriterionEvaluation",
]
