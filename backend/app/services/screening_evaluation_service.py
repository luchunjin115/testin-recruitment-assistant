from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from pydantic import ValidationError

from app.adapters.screening_evaluation import (
    DeepSeekScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterError,
    ScreeningEvaluationAdapterResult,
)
from app.core.config import Settings, get_settings
from app.prompts.screening_evaluation import SCREENING_EVALUATION_PROMPT_VERSION
from app.prompts.screening_evaluation import (
    SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
)
from app.schemas.experience_period import ExperiencePeriodFactsSnapshot
from app.schemas.job_evaluation_plan import (
    EvaluationCriterion,
    EvaluationItemPriority,
    JobEvaluationPlanInputSnapshot,
    RequirementFact,
    RequirementFactCategory,
)
from app.schemas.screening_evaluation import (
    AIScreeningEvaluationV5Output,
    AIScreeningEvaluationOutput,
    SCREENING_EVALUATION_SCHEMA_VERSION,
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
    BonusHighlight,
    CriterionAssessment,
    PersistedCriterionAssessmentV5,
    RequirementAssessment,
    ScreeningEvaluationPlanInput,
    ScreeningEvaluationPlanInputV5,
    ScreeningEvaluationV5ReportPayload,
    V5ReportFinding,
)
from app.services.experience_period_service import (
    EXPERIENCE_PERIOD_FACTS_RULE_VERSION,
    SCREENING_EVALUATION_TIMEZONE,
    experience_period_service,
)


SCREENING_REDACTION_VERSION = "screening_redaction_v1"


class ScreeningEvaluationServiceError(RuntimeError):
    code = "SCREENING_EVALUATION_FAILED"


class ScreeningEvaluationDisabledError(ScreeningEvaluationServiceError):
    code = "SCREENING_EVALUATION_DISABLED"


class ScreeningEvaluationConfigurationError(ScreeningEvaluationServiceError):
    code = "SCREENING_EVALUATION_CONFIGURATION_ERROR"


class ScreeningEvaluationInputError(ScreeningEvaluationServiceError):
    code = "SCREENING_EVALUATION_INPUT_ERROR"


class ScreeningEvaluationInvalidOutputError(ScreeningEvaluationServiceError):
    code = "SCREENING_EVALUATION_INVALID_MODEL_OUTPUT"


class ScreeningEvaluationUnexpectedError(ScreeningEvaluationServiceError):
    code = "SCREENING_EVALUATION_UNEXPECTED_ERROR"


class ScreeningEvaluationAdapter(Protocol):
    async def evaluate(
        self,
        *,
        job_snapshot: dict[str, Any],
        evaluation_plan: dict[str, Any],
        sanitized_resume: str,
        evaluation_reference_at: str,
        evaluation_timezone: str,
        experience_period_facts: dict[str, Any],
    ) -> ScreeningEvaluationAdapterResult: ...

    async def evaluate_v5(
        self,
        *,
        job_snapshot: dict[str, Any],
        evaluation_plan: dict[str, Any],
        sanitized_resume: str,
        evaluation_reference_at: str,
        evaluation_timezone: str,
        experience_period_facts: dict[str, Any],
    ) -> ScreeningEvaluationAdapterResult: ...


@dataclass(frozen=True, slots=True)
class ScreeningEvaluationMetadata:
    model_version: str
    prompt_version: str
    schema_version: str
    redaction_version: str
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True, slots=True)
class ScreeningEvaluationResult:
    report: AIScreeningEvaluationOutput
    display_label: str
    metadata: ScreeningEvaluationMetadata


@dataclass(frozen=True, slots=True)
class ScreeningEvaluationV5Result:
    report: ScreeningEvaluationV5ReportPayload
    metadata: ScreeningEvaluationMetadata
    behavior_version: str


class ScreeningEvaluationService:
    _SENSITIVE_LINE = re.compile(
        r"^\s*(?:姓名|姓\s*名|候选人姓名|电话|手机|联系方式|邮箱|电子邮箱|身份证(?:号)?|"
        r"住址|家庭住址|详细地址|现居住地|性别|出生日期|出生年月|年龄|婚姻状况|"
        r"婚育状况|民族|籍贯|照片|外貌|name|phone|mobile|e-?mail|id(?:entity)?\s*no|"
        r"candidate\s*name|address|gender|sex|date\s*of\s*birth|dob|age|"
        r"marital\s*status|ethnicity)\s*[:：]",
        re.IGNORECASE,
    )
    _EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    _PHONE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")
    _IDENTITY = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
    _DIRECT_AGE = re.compile(r"(?<!\d)(?:1[6-9]|[2-6]\d)\s*岁")
    _TOP_NAME = re.compile(r"^[\u4e00-\u9fff]{2,4}$")
    _TOP_LATIN_NAME = re.compile(
        r"^[A-Za-z][A-Za-z'’-]+(?:\s+[A-Za-z][A-Za-z'’-]+){1,3}$"
    )
    _NON_NAME_HEADINGS = {
        "个人简历",
        "求职简历",
        "简历",
        "教育经历",
        "工作经历",
        "项目经历",
        "专业技能",
        "自我评价",
    }
    _EXPLICIT_PRIVACY_OUTPUT_LABEL = re.compile(
        r"姓名|电话号码?|手机号码?|电子?邮箱|身份证|家庭住址|详细住址|居住地址"
    )
    _SENSITIVE_OUTPUT_PATTERNS = (
        _EXPLICIT_PRIVACY_OUTPUT_LABEL,
        re.compile(r"性别|出生日期|出生年月|年龄|\d+\s*岁|婚姻|婚育|民族|籍贯"),
        re.compile(r"照片|外貌|长相|颜值|男性|女性|男士|女士"),
        _EMAIL,
        _PHONE,
        _IDENTITY,
    )
    _V5_EXPLICIT_PRIVACY_OUTPUT_PATTERNS = (
        _EXPLICIT_PRIVACY_OUTPUT_LABEL,
        _EMAIL,
        _PHONE,
        _IDENTITY,
    )
    _DECISION_PATTERNS = (
        re.compile(r"建议.{0,8}(?:通过|淘汰|拒绝|录用|发放\s*offer)", re.IGNORECASE),
        re.compile(r"(?:应当|应该|可以|不应|不宜|不予).{0,6}(?:录用|淘汰|拒绝|通过)"),
        re.compile(r"(?:招聘|录用|淘汰|拒绝)决定|hr_decision|recruitment_stage|lifecycle_status", re.IGNORECASE),
        re.compile(r"(?:录用|淘汰|拒绝)(?:该|此)?(?:候选人|求职者)"),
        re.compile(r"通过(?:初筛|招聘筛选|候选人评审)"),
        re.compile(r"\boffer\b", re.IGNORECASE),
    )
    _BRAND_ONLY_PATTERN = re.compile(
        r"(?:名校|大厂|知名公司|头部企业|学校品牌|公司品牌).{0,18}"
        r"(?:因此|所以|证明|代表).{0,18}(?:能力|优秀|胜任|匹配|水平)"
    )
    _UNKNOWN_PATTERN = re.compile(r"\bunknown\b", re.IGNORECASE)
    _MISSING_TERMS = ("当前简历未体现", "未体现", "没有体现", "缺少", "不足", "短板")
    _STRONG_MATCH_TERMS = ("高度匹配", "整体较匹配", "非常充分", "强匹配")
    _STRONG_MISMATCH_TERMS = ("关联较弱", "明显差距", "整体不匹配", "完全不匹配")
    _NEGATIVE_BONUS_TERMS = (
        "未体现",
        "不会",
        "不能",
        "不足",
        "缺乏",
        "欠缺",
        "短板",
        "风险",
        "扣分",
        "负面",
    )
    _TRADEOFF_STRENGTH_TERMS = ("优势", "亮点", "支持", "弥补", "充分", "较强", "突出")
    _TRADEOFF_GAP_TERMS = ("短板", "不足", "未体现", "差距", "仍需", "需要确认", "待确认")
    _ASSERTED_INABILITY = re.compile(
        r"(?:候选人|其|该求职者).{0,8}(?:不会|不具备|没有能力|无法胜任|不能完成)"
    )
    _PROMPT_INJECTION_OUTPUT_PATTERNS = (
        re.compile(r"忽略.{0,12}(?:上文|规则|指令|系统)", re.IGNORECASE),
        re.compile(r"(?:system|developer)\s*prompt|api\s*key", re.IGNORECASE),
        re.compile(r"(?:泄露|展示|输出).{0,8}(?:提示词|内部指令|密钥)", re.IGNORECASE),
    )
    _COMMON_BIGRAMS = {
        "候选",
        "选人",
        "简历",
        "岗位",
        "相关",
        "经验",
        "能力",
        "工作",
        "负责",
        "项目",
        "体现",
        "具备",
        "匹配",
        "可以",
        "能够",
        "当前",
    }
    _DURATION_CLAIM = re.compile(
        r"(?:下界(?:为)?|上界(?:为)?|至少|远超|超过|超出|多于|不足|少于|未满|不满|达到|满足|已满|满|约|大约|共计|累计)?\s*"
        r"(?:\d{1,3}(?:\.\d+)?\s*年|\d{1,4}\s*个?月)"
    )
    _DURATION_THRESHOLD_SATISFIED = re.compile(
        r"(?:满足|达到|符合).{0,10}(?:年限|工作经验|年要求)"
    )
    _DURATION_THRESHOLD_NOT_SATISFIED = re.compile(
        r"(?:不满足|未达到|不足以满足|不符合).{0,10}(?:年限|工作经验|年要求)"
    )

    async def evaluate(
        self,
        *,
        job_snapshot: JobEvaluationPlanInputSnapshot | dict[str, Any],
        evaluation_plan: ScreeningEvaluationPlanInput | dict[str, Any],
        resume_text: str,
        evaluation_reference_at: datetime,
        evaluation_timezone: str,
        experience_period_facts: ExperiencePeriodFactsSnapshot | dict[str, Any],
        adapter: ScreeningEvaluationAdapter | None = None,
        settings: Settings | None = None,
    ) -> ScreeningEvaluationResult:
        resolved_settings = settings or get_settings()
        self._validate_configuration(resolved_settings)
        snapshot, plan, sanitized_resume = self._prepare_inputs(
            job_snapshot,
            evaluation_plan,
            resume_text,
        )
        try:
            period_facts = ExperiencePeriodFactsSnapshot.model_validate(
                experience_period_facts
            )
        except (ValidationError, TypeError, ValueError):
            raise ScreeningEvaluationInputError("经历时间事实输入无效") from None
        expected_reference = evaluation_reference_at.isoformat()
        if (
            period_facts.evaluation_reference_at != expected_reference
            or period_facts.evaluation_timezone != evaluation_timezone
        ):
            raise ScreeningEvaluationInputError("经历时间事实与评价基准不一致")
        snapshot_payload = snapshot.model_dump(mode="json")
        plan_payload = plan.model_dump(mode="json")
        period_facts_payload = period_facts.model_dump(mode="json")

        try:
            resolved_adapter = adapter or DeepSeekScreeningEvaluationAdapter(
                settings=resolved_settings
            )
            adapter_result = await resolved_adapter.evaluate(
                job_snapshot=snapshot_payload,
                evaluation_plan=plan_payload,
                sanitized_resume=sanitized_resume,
                evaluation_reference_at=expected_reference,
                evaluation_timezone=evaluation_timezone,
                experience_period_facts=period_facts_payload,
            )
        except ScreeningEvaluationAdapterError:
            raise
        except Exception:
            raise ScreeningEvaluationUnexpectedError(
                "AI 初筛评价发生未预期错误"
            ) from None

        report = self.parse_and_validate_output(
            adapter_result.content,
            job_snapshot=snapshot,
            evaluation_plan=plan,
            sanitized_resume=sanitized_resume,
            experience_period_facts=period_facts,
        )
        return ScreeningEvaluationResult(
            report=report,
            display_label=self.display_label_for_score(report.overall_score),
            metadata=ScreeningEvaluationMetadata(
                model_version=adapter_result.model,
                prompt_version=SCREENING_EVALUATION_PROMPT_VERSION,
                schema_version=SCREENING_EVALUATION_SCHEMA_VERSION,
                redaction_version=SCREENING_REDACTION_VERSION,
                input_tokens=adapter_result.input_tokens,
                output_tokens=adapter_result.output_tokens,
            ),
        )

    async def evaluate_v5(
        self,
        *,
        job_snapshot: JobEvaluationPlanInputSnapshot | dict[str, Any],
        evaluation_plan: ScreeningEvaluationPlanInputV5 | dict[str, Any],
        resume_text: str,
        evaluation_reference_at: datetime,
        evaluation_timezone: str,
        experience_period_facts: ExperiencePeriodFactsSnapshot | dict[str, Any] | None = None,
        adapter: ScreeningEvaluationAdapter | None = None,
        settings: Settings | None = None,
    ) -> ScreeningEvaluationV5Result:
        """Generate one pure 5.0 report without wiring screening runs or persistence."""

        resolved_settings = settings or get_settings()
        self._validate_v5_configuration(resolved_settings)
        snapshot, plan, sanitized_resume = self._prepare_v5_inputs(
            job_snapshot,
            evaluation_plan,
            resume_text,
        )
        try:
            resolved_adapter = adapter or DeepSeekScreeningEvaluationAdapter(
                settings=resolved_settings
            )
            adapter_result = await resolved_adapter.evaluate_v5(
                job_snapshot=snapshot.model_dump(mode="json"),
                evaluation_plan=plan.model_dump(mode="json"),
                sanitized_resume=sanitized_resume,
                evaluation_reference_at="",
                evaluation_timezone="",
                experience_period_facts={},
            )
        except ScreeningEvaluationAdapterError:
            raise
        except Exception:
            raise ScreeningEvaluationUnexpectedError(
                "5.0 AI 初筛评价发生未预期错误"
            ) from None

        report = self.parse_and_validate_v5_output(
            adapter_result.content,
            evaluation_plan=plan,
            sanitized_resume=sanitized_resume,
        )
        return ScreeningEvaluationV5Result(
            report=report,
            metadata=ScreeningEvaluationMetadata(
                model_version=adapter_result.model,
                prompt_version=SCREENING_EVALUATION_V5_PROMPT_VERSION,
                schema_version=SCREENING_EVALUATION_V5_SCHEMA_VERSION,
                redaction_version=SCREENING_REDACTION_VERSION,
                input_tokens=adapter_result.input_tokens,
                output_tokens=adapter_result.output_tokens,
            ),
            behavior_version=SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
        )

    def parse_and_validate_v5_output(
        self,
        content: str,
        *,
        evaluation_plan: ScreeningEvaluationPlanInputV5 | dict[str, Any],
        sanitized_resume: str,
        experience_period_facts: ExperiencePeriodFactsSnapshot | None = None,
    ) -> ScreeningEvaluationV5ReportPayload:
        try:
            payload = json.loads(content, object_pairs_hook=self._unique_json_object)
            output = AIScreeningEvaluationV5Output.model_validate(payload)
            plan = ScreeningEvaluationPlanInputV5.model_validate(evaluation_plan)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 AI 初筛结果未通过严格结构校验"
            ) from None

        self.validate_v5_criterion_cross_reference(output, plan)
        criteria_by_id = {item.criterion_id: item for item in plan.criteria}
        for assessment in output.criterion_assessments:
            self.validate_v5_evidence_required(assessment)
            self._validate_evidence(assessment.evidence, sanitized_resume)
            self._validate_v5_compatibility_time_fields(assessment)

        self._validate_v5_findings(output, plan, sanitized_resume)
        self._validate_v5_safety(output)

        display_label = self.display_label_for_score(output.overall_score)
        enriched = [
            PersistedCriterionAssessmentV5(
                criterion=criteria_by_id[item.criterion_id],
                assessment=item,
            )
            for item in output.criterion_assessments
        ]
        return ScreeningEvaluationV5ReportPayload(
            overall_score=output.overall_score,
            display_label=display_label,
            overall_summary=output.overall_summary,
            criterion_assessments=enriched,
            strengths=output.strengths,
            gaps=output.gaps,
            risks_or_conflicts=output.risks_or_conflicts,
            missing_info=output.missing_info,
            hr_follow_up_questions=output.hr_follow_up_questions,
        )

    @staticmethod
    def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def _prepare_v5_inputs(
        self,
        job_snapshot: JobEvaluationPlanInputSnapshot | dict[str, Any],
        evaluation_plan: ScreeningEvaluationPlanInputV5 | dict[str, Any],
        resume_text: str,
    ) -> tuple[
        JobEvaluationPlanInputSnapshot,
        ScreeningEvaluationPlanInputV5,
        str,
    ]:
        try:
            snapshot = JobEvaluationPlanInputSnapshot.model_validate(job_snapshot)
            plan = ScreeningEvaluationPlanInputV5.model_validate(evaluation_plan)
        except (ValidationError, TypeError, ValueError):
            raise ScreeningEvaluationInputError("5.0 岗位或评价计划输入无效") from None
        if snapshot.schema_version != "5.0" or snapshot.evaluation_fields is None:
            raise ScreeningEvaluationInputError("5.0 AI 初筛只接受 5.0 岗位快照")
        fields = snapshot.evaluation_fields.model_dump(mode="json")
        for criterion in plan.criteria:
            for source in criterion.sources:
                source_text = fields.get(source.source_field)
                if not isinstance(source_text, str) or source.source_quote not in source_text:
                    raise ScreeningEvaluationInputError(
                        "5.0 评价点来源无法在岗位快照中定位"
                    )
        if not isinstance(resume_text, str) or not resume_text.strip():
            raise ScreeningEvaluationInputError("当前 Resume 原文为空")
        sanitized_resume = self.sanitize_resume_text(resume_text)
        if not sanitized_resume:
            raise ScreeningEvaluationInputError("当前 Resume 脱敏后没有可评价内容")
        return snapshot, plan, sanitized_resume

    @staticmethod
    def validate_v5_criterion_cross_reference(
        report: AIScreeningEvaluationV5Output,
        plan: ScreeningEvaluationPlanInputV5,
    ) -> None:
        expected = [item.criterion_id for item in plan.criteria]
        actual = [item.criterion_id for item in report.criterion_assessments]
        counts = Counter(actual)
        if any(count != 1 for count in counts.values()):
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 AI 初筛评价点存在重复 criterion_id"
            )
        if len(actual) != len(expected) or set(actual) != set(expected):
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 AI 初筛评价点存在未知或遗漏 criterion_id"
            )

    @staticmethod
    def validate_v5_evidence_required(assessment: CriterionAssessment) -> None:
        if assessment.score > 0 and not assessment.evidence:
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 非零分必须至少包含一条当前 Resume 证据"
            )

    def _validate_v5_findings(
        self,
        report: AIScreeningEvaluationV5Output,
        plan: ScreeningEvaluationPlanInputV5,
        sanitized_resume: str,
    ) -> None:
        valid_ids = {item.criterion_id for item in plan.criteria}
        for section_name, findings in (
            ("strengths", report.strengths),
            ("gaps", report.gaps),
            ("risks_or_conflicts", report.risks_or_conflicts),
            ("missing_info", report.missing_info),
        ):
            for finding in findings:
                if any(item not in valid_ids for item in finding.criterion_ids):
                    raise ScreeningEvaluationInvalidOutputError(
                        "5.0 报告分区引用了未知 criterion_id"
                    )
                self._validate_evidence(finding.evidence, sanitized_resume)
                if section_name == "strengths" and not finding.evidence:
                    raise ScreeningEvaluationInvalidOutputError(
                        "5.0 优势必须包含当前 Resume 可定位证据"
                    )
                if not finding.evidence and not finding.criterion_ids:
                    raise ScreeningEvaluationInvalidOutputError(
                        "无直接证据的报告结论必须关联当前评价点"
                    )

    @staticmethod
    def _v5_hr_visible_text(report: AIScreeningEvaluationV5Output) -> tuple[str, ...]:
        texts = [report.overall_summary]
        for assessment in report.criterion_assessments:
            texts.append(assessment.reason)
            if assessment.calculation_note is not None:
                texts.append(assessment.calculation_note)
            for evidence in assessment.evidence:
                texts.append(evidence.quote)
                if evidence.section is not None:
                    texts.append(evidence.section)
        for findings in (
            report.strengths,
            report.gaps,
            report.risks_or_conflicts,
            report.missing_info,
        ):
            for finding in findings:
                texts.append(finding.summary)
                for evidence in finding.evidence:
                    texts.append(evidence.quote)
                    if evidence.section is not None:
                        texts.append(evidence.section)
        texts.extend(report.hr_follow_up_questions)
        return tuple(texts)

    def _validate_v5_safety(self, report: AIScreeningEvaluationV5Output) -> None:
        combined = "\n".join(self._v5_hr_visible_text(report))
        if any(
            pattern.search(combined)
            for pattern in self._V5_EXPLICIT_PRIVACY_OUTPUT_PATTERNS
        ):
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 AI 初筛输出包含不得参与评价的敏感个人属性"
            )
        if any(pattern.search(combined) for pattern in self._DECISION_PATTERNS):
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 AI 初筛不得生成或修改招聘决定"
            )
        if any(pattern.search(combined) for pattern in self._PROMPT_INJECTION_OUTPUT_PATTERNS):
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 AI 初筛输出复述或执行了 Prompt 注入内容"
            )
        if self._UNKNOWN_PATTERN.search(combined):
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 AI 初筛不得使用 unknown 语义"
            )
    @staticmethod
    def _validate_v5_compatibility_time_fields(
        assessment: CriterionAssessment,
    ) -> None:
        if (
            assessment.experience_period_fact_keys
            or assessment.calculation_note is not None
        ):
            raise ScreeningEvaluationInvalidOutputError(
                "5.0 AI 初筛经历时间兼容字段必须为空"
            )

    def parse_and_validate_output(
        self,
        content: str,
        *,
        job_snapshot: JobEvaluationPlanInputSnapshot,
        evaluation_plan: ScreeningEvaluationPlanInput | dict[str, Any],
        sanitized_resume: str,
        experience_period_facts: ExperiencePeriodFactsSnapshot,
    ) -> AIScreeningEvaluationOutput:
        try:
            payload = json.loads(content)
            report = AIScreeningEvaluationOutput.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛结果未通过严格结构校验"
            ) from None

        plan = self._validate_plan_input(evaluation_plan)
        requirement_facts = plan.requirement_facts
        self._validate_requirement_completeness(report, requirement_facts)
        self._validate_assessments(
            report,
            requirement_facts,
            sanitized_resume,
            experience_period_facts,
        )
        self._validate_bonuses(
            report,
            job_snapshot,
            requirement_facts,
            sanitized_resume,
        )
        self._validate_tradeoff(report, requirement_facts)
        self._validate_safety_and_consistency(report)
        self._validate_no_unscoped_duration_claims(report)
        return report

    def _prepare_inputs(
        self,
        job_snapshot: JobEvaluationPlanInputSnapshot | dict[str, Any],
        evaluation_plan: ScreeningEvaluationPlanInput | dict[str, Any],
        resume_text: str,
    ) -> tuple[
        JobEvaluationPlanInputSnapshot,
        ScreeningEvaluationPlanInput,
        str,
    ]:
        try:
            snapshot = JobEvaluationPlanInputSnapshot.model_validate(job_snapshot)
            plan = ScreeningEvaluationPlanInput.model_validate(evaluation_plan)
            requirement_facts: list[RequirementFact] = plan.requirement_facts
            evaluation_criteria: list[EvaluationCriterion] = plan.evaluation_criteria
        except (ValidationError, TypeError, ValueError):
            raise ScreeningEvaluationInputError("岗位或评价计划输入无效") from None
        if snapshot.schema_version != "4.0":
            raise ScreeningEvaluationInputError("AI 初筛只接受 4.0 岗位评价计划")
        fact_ids = [fact.fact_id for fact in requirement_facts]
        grouped_fact_ids = [
            fact_id
            for criterion in evaluation_criteria
            for fact_id in criterion.fact_ids
        ]
        if len(fact_ids) != len(set(fact_ids)):
            raise ScreeningEvaluationInputError("当前岗位评价计划 fact_id 不唯一")
        if Counter(grouped_fact_ids) != Counter({fact_id: 1 for fact_id in fact_ids}):
            raise ScreeningEvaluationInputError(
                "评价维度必须把每条 RequirementFact 恰好归组一次"
            )
        self._validate_fact_sources(snapshot, requirement_facts)
        if not isinstance(resume_text, str) or not resume_text.strip():
            raise ScreeningEvaluationInputError("当前 Resume 原文为空")
        sanitized_resume = self.sanitize_resume_text(resume_text)
        if not sanitized_resume:
            raise ScreeningEvaluationInputError("当前 Resume 脱敏后没有可评价内容")
        return snapshot, plan, sanitized_resume

    @staticmethod
    def _validate_plan_input(
        evaluation_plan: ScreeningEvaluationPlanInput | dict[str, Any],
    ) -> ScreeningEvaluationPlanInput:
        try:
            plan = ScreeningEvaluationPlanInput.model_validate(evaluation_plan)
        except (ValidationError, TypeError, ValueError):
            raise ScreeningEvaluationInputError("岗位评价计划 4.0 输入无效") from None
        fact_ids = [fact.fact_id for fact in plan.requirement_facts]
        grouped_fact_ids = [
            fact_id
            for criterion in plan.evaluation_criteria
            for fact_id in criterion.fact_ids
        ]
        if len(fact_ids) != len(set(fact_ids)) or Counter(grouped_fact_ids) != Counter(
            {fact_id: 1 for fact_id in fact_ids}
        ):
            raise ScreeningEvaluationInputError(
                "评价维度必须把每条 RequirementFact 恰好归组一次"
            )
        return plan

    @staticmethod
    def _validate_fact_sources(
        snapshot: JobEvaluationPlanInputSnapshot,
        requirement_facts: list[RequirementFact],
    ) -> None:
        source_units = {unit.source_unit_id: unit for unit in snapshot.source_units}
        priority_by_field = {
            "candidate_requirements": EvaluationItemPriority.REQUIRED,
            "preferred_qualifications": EvaluationItemPriority.PREFERRED,
            "job_responsibilities": EvaluationItemPriority.GENERAL,
        }
        priority_rank = {
            EvaluationItemPriority.REQUIRED: 3,
            EvaluationItemPriority.PREFERRED: 2,
            EvaluationItemPriority.GENERAL: 1,
        }
        for fact in requirement_facts:
            for source in fact.sources:
                source_unit = source_units.get(source.source_unit_id)
                if (
                    source_unit is None
                    or source.source_field != source_unit.source_field
                    or source.source_quote not in source_unit.source_text
                ):
                    raise ScreeningEvaluationInputError(
                        "RequirementFact source must be traceable to the 4.0 input snapshot"
                    )
            expected_priority = max(
                (priority_by_field[source.source_field] for source in fact.sources),
                key=priority_rank.__getitem__,
            )
            if fact.priority is not expected_priority:
                raise ScreeningEvaluationInputError(
                    "RequirementFact priority must match its source fields"
                )

    @classmethod
    def sanitize_resume_text(cls, resume_text: str) -> str:
        normalized = resume_text.replace("\r\n", "\n").replace("\r", "\n")
        raw_lines = normalized.split("\n")
        has_early_contact_signal = any(
            cls._SENSITIVE_LINE.search(line.strip())
            or cls._EMAIL.search(line)
            or cls._PHONE.search(line)
            for line in raw_lines[:8]
        )
        kept_lines: list[str] = []
        for line in raw_lines:
            stripped = line.strip()
            if cls._SENSITIVE_LINE.search(stripped):
                continue
            if re.fullmatch(r"\[?\s*(?:证件照|个人照片|照片)\s*\]?", stripped):
                continue
            kept_lines.append(line)

        first_content_index = next(
            (index for index, line in enumerate(kept_lines) if line.strip()),
            None,
        )
        if first_content_index is not None:
            first = kept_lines[first_content_index].strip()
            is_chinese_name = (
                cls._TOP_NAME.fullmatch(first) and first not in cls._NON_NAME_HEADINGS
            )
            is_latin_name = (
                has_early_contact_signal
                and cls._TOP_LATIN_NAME.fullmatch(first)
                and first.casefold()
                not in {"curriculum vitae", "personal resume", "software engineer"}
            )
            if is_chinese_name or is_latin_name:
                kept_lines.pop(first_content_index)

        sanitized = "\n".join(kept_lines)
        sanitized = cls._EMAIL.sub("[已移除]", sanitized)
        sanitized = cls._PHONE.sub("[已移除]", sanitized)
        sanitized = cls._IDENTITY.sub("[已移除]", sanitized)
        sanitized = cls._DIRECT_AGE.sub("[已移除]", sanitized)
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
        return sanitized.strip()

    @staticmethod
    def display_label_for_score(score: int) -> str:
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError("综合分必须是 0—100 整数")
        if score <= 29:
            return "关联较弱"
        if score <= 49:
            return "存在明显差距"
        if score <= 69:
            return "部分匹配"
        if score <= 84:
            return "整体较匹配"
        return "高度匹配"

    @staticmethod
    def _validate_requirement_completeness(
        report: AIScreeningEvaluationOutput,
        evaluation_plan: list[RequirementFact],
    ) -> None:
        expected = [fact.fact_id for fact in evaluation_plan]
        actual = [item.requirement_key for item in report.requirement_assessments]
        counts = Counter(actual)
        if any(count != 1 for count in counts.values()):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛基础事项存在重复 requirement_key"
            )
        if set(actual) != set(expected) or len(actual) != len(expected):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛基础事项与当前岗位评价计划不一致"
            )

    def _validate_assessments(
        self,
        report: AIScreeningEvaluationOutput,
        evaluation_plan: list[RequirementFact],
        sanitized_resume: str,
        experience_period_facts: ExperiencePeriodFactsSnapshot,
    ) -> None:
        plan_by_key = {fact.fact_id: fact for fact in evaluation_plan}
        for assessment in report.requirement_assessments:
            if assessment.score == 0:
                if "当前简历未体现" not in assessment.reason:
                    raise ScreeningEvaluationInvalidOutputError(
                        "基础事项 0 分必须说明当前简历未体现"
                    )
                positive_evidence = "\n".join(item.quote for item in assessment.evidence)
                plan_item = plan_by_key[assessment.requirement_key]
                if (
                    assessment.evidence
                    and self._has_semantic_anchor(
                        self._fact_text(plan_item), positive_evidence
                    )
                    and any(
                        term in positive_evidence
                        for term in ("使用", "开发", "负责", "掌握", "熟悉", "完成", "获得")
                    )
                ):
                    raise ScreeningEvaluationInvalidOutputError(
                        "基础事项 0 分与正向证据明显矛盾"
                    )
            elif not assessment.evidence:
                raise ScreeningEvaluationInvalidOutputError(
                    "基础事项 1—10 分必须包含可定位证据"
                )
            self._validate_evidence(assessment.evidence, sanitized_resume)
            if self._ASSERTED_INABILITY.search(assessment.reason):
                raise ScreeningEvaluationInvalidOutputError(
                    "AI 初筛不得把简历未体现写成候选人不会"
                )
            plan_item = plan_by_key[assessment.requirement_key]
            if assessment.calculation_note is not None and not self._allows_calculation_note(
                plan_item
            ):
                raise ScreeningEvaluationInvalidOutputError(
                    "calculation_note 只能解释年限或学历等计算依据"
                )
            self._validate_experience_fact_claims(
                assessment,
                plan_item,
                experience_period_facts,
            )
            if assessment.score > 0:
                self._validate_grounded_reason(
                    assessment.reason,
                    assessment.evidence,
                    sanitized_resume,
                    allow_fact_numbers=bool(assessment.experience_period_fact_keys),
                )
            self._validate_score_reason_direction(assessment)

    def _validate_bonuses(
        self,
        report: AIScreeningEvaluationOutput,
        job_snapshot: JobEvaluationPlanInputSnapshot,
        evaluation_plan: list[RequirementFact],
        sanitized_resume: str,
    ) -> None:
        job_context = self._job_context(job_snapshot, evaluation_plan)
        for bonus in report.bonus_highlights:
            combined = f"{bonus.title}\n{bonus.reason}"
            if any(term in combined for term in self._NEGATIVE_BONUS_TERMS):
                raise ScreeningEvaluationInvalidOutputError(
                    "额外亮点只能表达正向价值"
                )
            if any(
                self._semantically_overlaps(bonus.title, self._fact_text(fact))
                for fact in evaluation_plan
            ):
                raise ScreeningEvaluationInvalidOutputError(
                    "额外亮点不能与岗位基础事项重复"
                )
            if not self._has_semantic_anchor(combined, job_context):
                raise ScreeningEvaluationInvalidOutputError(
                    "额外亮点必须与当前岗位相关"
                )
            self._validate_evidence(bonus.evidence, sanitized_resume)
            self._validate_grounded_reason(
                combined,
                bonus.evidence,
                sanitized_resume,
            )

    @staticmethod
    def _validate_evidence(evidence: list[Any], sanitized_resume: str) -> None:
        haystack = re.sub(r"\s+", " ", sanitized_resume).strip()
        for item in evidence:
            quote = re.sub(r"\s+", " ", item.quote).strip()
            if quote not in haystack:
                raise ScreeningEvaluationInvalidOutputError(
                    "AI 初筛证据无法在本次脱敏 Resume 中定位"
                )

    def _validate_tradeoff(
        self,
        report: AIScreeningEvaluationOutput,
        evaluation_plan: list[RequirementFact],
    ) -> None:
        priority_by_key = {fact.fact_id: fact.priority for fact in evaluation_plan}
        has_low_required = any(
            priority_by_key[item.requirement_key] is EvaluationItemPriority.REQUIRED
            and item.score <= 3
            for item in report.requirement_assessments
        )
        if has_low_required and report.overall_score >= 70:
            reason = report.tradeoff_reason or ""
            if not reason:
                raise ScreeningEvaluationInvalidOutputError(
                    "低 required 分与高综合分并存时必须说明权衡"
                )
            if not any(term in reason for term in self._TRADEOFF_STRENGTH_TERMS) or not any(
                term in reason for term in self._TRADEOFF_GAP_TERMS
            ):
                raise ScreeningEvaluationInvalidOutputError(
                    "权衡说明必须同时解释高分优势和待确认短板"
                )

    def _validate_safety_and_consistency(
        self,
        report: AIScreeningEvaluationOutput,
    ) -> None:
        text_parts = [report.overall_summary, report.tradeoff_reason or ""]
        text_parts.extend(report.interview_questions)
        for assessment in report.requirement_assessments:
            text_parts.extend(
                [assessment.reason, assessment.calculation_note or ""]
            )
        for bonus in report.bonus_highlights:
            text_parts.extend([bonus.title, bonus.reason])
        combined = "\n".join(text_parts)
        if any(pattern.search(combined) for pattern in self._SENSITIVE_OUTPUT_PATTERNS):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛输出包含不得参与评价的敏感个人属性"
            )
        if any(pattern.search(combined) for pattern in self._DECISION_PATTERNS):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛不得生成或修改招聘决定"
            )
        if self._UNKNOWN_PATTERN.search(combined):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛不得使用已废弃的 unknown 语义"
            )
        if self._BRAND_ONLY_PATTERN.search(combined):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛不得只按学校或公司品牌认定能力"
            )
        if self._ASSERTED_INABILITY.search(combined):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛不得把未体现写成候选人不会"
            )
        if report.overall_score >= 70 and any(
            term in report.overall_summary for term in self._STRONG_MISMATCH_TERMS
        ):
            raise ScreeningEvaluationInvalidOutputError(
                "综合摘要与高综合分方向明显矛盾"
            )
        if report.overall_score <= 49 and any(
            term in report.overall_summary for term in self._STRONG_MATCH_TERMS
        ):
            raise ScreeningEvaluationInvalidOutputError(
                "综合摘要与低综合分方向明显矛盾"
            )

    def _validate_score_reason_direction(
        self,
        assessment: RequirementAssessment,
    ) -> None:
        if assessment.score >= 7 and any(
            term in assessment.reason for term in self._MISSING_TERMS
        ):
            raise ScreeningEvaluationInvalidOutputError(
                "基础事项高分与缺失理由方向明显矛盾"
            )
        if assessment.score <= 3 and any(
            term in assessment.reason for term in ("非常充分", "完全满足", "高度匹配")
        ):
            raise ScreeningEvaluationInvalidOutputError(
                "基础事项低分与高匹配理由方向明显矛盾"
            )

    def _validate_grounded_reason(
        self,
        reason: str,
        evidence: list[Any],
        sanitized_resume: str,
        *,
        allow_fact_numbers: bool = False,
    ) -> None:
        source = sanitized_resume.lower()
        for number in re.findall(r"(?<![a-z])\d+(?:\.\d+)?", reason.lower()):
            if number not in source and not allow_fact_numbers:
                raise ScreeningEvaluationInvalidOutputError(
                    "AI 初筛理由包含 Resume 无法支持的数值事实"
                )
        for token in re.findall(r"[a-z][a-z0-9+#.]{1,}", reason.lower()):
            if token not in source and token not in {"api", "ai"}:
                raise ScreeningEvaluationInvalidOutputError(
                    "AI 初筛理由包含 Resume 无法支持的事实"
                )
        evidence_text = "\n".join(item.quote for item in evidence)
        if not self._has_semantic_anchor(reason, evidence_text):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 初筛理由与引用证据缺少可核对联系"
            )

    def _validate_experience_fact_claims(
        self,
        assessment: RequirementAssessment,
        plan_item: RequirementFact,
        snapshot: ExperiencePeriodFactsSnapshot,
    ) -> None:
        keys = list(assessment.experience_period_fact_keys)
        if len(keys) != len(set(keys)):
            raise ScreeningEvaluationInvalidOutputError("经历时间事实 key 不能重复")
        fact_by_key = {fact.key: fact for fact in snapshot.facts}
        if any(key not in fact_by_key for key in keys):
            raise ScreeningEvaluationInvalidOutputError("AI 引用了不存在的经历时间事实")
        if any(not fact_by_key[key].usable_for_reference for key in keys):
            raise ScreeningEvaluationInvalidOutputError(
                "AI 引用了投递后或日期冲突的经历时间事实"
            )
        if keys and not self._allows_calculation_note(plan_item):
            raise ScreeningEvaluationInvalidOutputError(
                "非经历时间事项不得引用经历时间事实"
            )

        combined = "\n".join(
            value for value in (assessment.reason, assessment.calculation_note) if value
        )
        claims = list(self._DURATION_CLAIM.finditer(combined))
        threshold_not_satisfied = bool(
            self._DURATION_THRESHOLD_NOT_SATISFIED.search(combined)
        )
        threshold_satisfied = (
            not threshold_not_satisfied
            and bool(self._DURATION_THRESHOLD_SATISFIED.search(combined))
        )
        if (claims or threshold_satisfied or threshold_not_satisfied) and not keys:
            raise ScreeningEvaluationInvalidOutputError(
                "AI 年限结论必须引用后端经历时间事实"
            )
        if keys and assessment.calculation_note is None:
            raise ScreeningEvaluationInvalidOutputError(
                "引用经历时间事实时必须提供 calculation_note"
            )
        if not claims and not threshold_satisfied and not threshold_not_satisfied:
            return
        bounds = experience_period_service.duration_bounds_for_keys(
            snapshot.facts,
            keys,
        )
        if bounds is None:
            raise ScreeningEvaluationInvalidOutputError("经历时间事实无法支持年限结论")
        lower, upper = bounds
        threshold_months = self._duration_threshold_months(
            self._fact_text(plan_item)
        )
        for claim in claims:
            if self._is_parenthetical_threshold_conversion(
                combined,
                claim,
                threshold_months,
            ):
                continue
            self._validate_duration_claim(claim.group(0), lower, upper)
        if threshold_months is not None:
            if threshold_not_satisfied and upper >= threshold_months:
                raise ScreeningEvaluationInvalidOutputError(
                    "AI 年限门槛结论与后端经历时间事实冲突"
                )
            if threshold_satisfied and lower < threshold_months:
                raise ScreeningEvaluationInvalidOutputError(
                    "AI 年限门槛结论与后端经历时间事实冲突"
                )

    @staticmethod
    def _validate_duration_claim(claim: str, lower: int, upper: int) -> None:
        number_match = re.search(r"\d+(?:\.\d+)?", claim)
        if number_match is None:
            return
        number = float(number_match.group(0))
        threshold_months = number if "月" in claim else number * 12
        if "下界" in claim:
            valid = abs(lower - threshold_months) < 0.001
        elif "上界" in claim:
            valid = abs(upper - threshold_months) < 0.001
        elif any(term in claim for term in ("不足", "少于", "未满", "不满")):
            valid = upper < threshold_months
        elif any(term in claim for term in ("远超", "超过", "超出", "多于")):
            valid = lower > threshold_months
        elif any(term in claim for term in ("至少", "达到", "满足", "已满", "满")):
            valid = lower >= threshold_months
        else:
            valid = lower == upper and abs(lower - threshold_months) < 0.001
        if not valid:
            raise ScreeningEvaluationInvalidOutputError(
                "AI 年限结论与后端经历时间事实冲突"
            )

    @staticmethod
    def _is_parenthetical_threshold_conversion(
        text: str,
        claim: re.Match[str],
        threshold_months: float | None,
    ) -> bool:
        """Treat `至少 2 年（24 个月）` as one threshold, not two durations."""
        if threshold_months is None:
            return False
        claim_text = claim.group(0)
        if "个月" not in claim_text or any(
            term in claim_text
            for term in ("至少", "超过", "多于", "不足", "少于", "未满", "不满", "达到", "满足", "已满")
        ):
            return False
        month_match = re.search(r"\d+(?:\.\d+)?", claim_text)
        if month_match is None or abs(float(month_match.group(0)) - threshold_months) >= 0.001:
            return False
        prefix = text[max(0, claim.start() - 24) : claim.start()]
        year_match = re.search(
            r"(?:至少|不少于|超过)?\s*(\d+(?:\.\d+)?)\s*年\s*[（(]\s*$",
            prefix,
        )
        return bool(
            year_match
            and abs(float(year_match.group(1)) * 12 - threshold_months) < 0.001
        )

    def _validate_no_unscoped_duration_claims(
        self,
        report: AIScreeningEvaluationOutput,
    ) -> None:
        values = [report.overall_summary, report.tradeoff_reason or ""]
        for bonus in report.bonus_highlights:
            values.extend((bonus.title, bonus.reason))
        if any(self._DURATION_CLAIM.search(value) for value in values):
            raise ScreeningEvaluationInvalidOutputError(
                "综合结论中的年限必须放入可校验的逐项评价"
            )

    @staticmethod
    def _duration_threshold_months(title: str) -> float | None:
        match = re.search(r"(?:至少|不少于|超过)?\s*(\d+(?:\.\d+)?)\s*年", title)
        return float(match.group(1)) * 12 if match else None

    @staticmethod
    def _allows_calculation_note(item: RequirementFact) -> bool:
        return item.category in {
            RequirementFactCategory.EXPERIENCE,
            RequirementFactCategory.EDUCATION,
        } or any(
            term in ScreeningEvaluationService._fact_text(item)
            for term in ("年限", "工作年", "学历", "学位")
        )

    def _semantically_overlaps(self, left: str, right: str) -> bool:
        left_normalized = self._semantic_text(left)
        right_normalized = self._semantic_text(right)
        if left_normalized == right_normalized:
            return True
        shorter, longer = sorted((left_normalized, right_normalized), key=len)
        if len(shorter) >= 4 and shorter in longer:
            return True
        left_ascii = set(re.findall(r"[a-z0-9+#.]{2,}", left.lower()))
        right_ascii = set(re.findall(r"[a-z0-9+#.]{2,}", right.lower()))
        return bool(left_ascii and left_ascii == right_ascii)

    def _has_semantic_anchor(self, left: str, right: str) -> bool:
        left_lower = left.lower()
        right_lower = right.lower()
        left_ascii = set(re.findall(r"[a-z][a-z0-9+#.]{1,}", left_lower))
        right_ascii = set(re.findall(r"[a-z][a-z0-9+#.]{1,}", right_lower))
        if left_ascii.intersection(right_ascii):
            return True
        return bool(self._bigrams(left).intersection(self._bigrams(right)))

    def _bigrams(self, value: str) -> set[str]:
        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", value))
        return {
            chinese[index : index + 2]
            for index in range(max(0, len(chinese) - 1))
            if chinese[index : index + 2] not in self._COMMON_BIGRAMS
        }

    @staticmethod
    def _semantic_text(value: str) -> str:
        normalized = value.lower()
        for term in ("额外", "亮点", "优势", "熟练掌握", "熟悉", "具备", "经验", "能力"):
            normalized = normalized.replace(term, "")
        return re.sub(r"[^a-z0-9+#.\u4e00-\u9fff]", "", normalized)

    @staticmethod
    def _job_context(
        snapshot: JobEvaluationPlanInputSnapshot,
        evaluation_plan: list[RequirementFact],
    ) -> str:
        if snapshot.schema_version in {"3.0", "4.0"}:
            assert snapshot.job_context is not None
            assert snapshot.evaluation_fields is not None
            values = [
                snapshot.job_context.title,
                snapshot.job_context.department or "",
                snapshot.job_context.job_background or "",
            ]
            requirements: Any = snapshot.evaluation_fields.model_dump(mode="json")
        else:
            assert snapshot.title is not None
            assert snapshot.requirements is not None
            values = [
                snapshot.title,
                snapshot.department or "",
                snapshot.description or "",
            ]
            requirements = snapshot.requirements.model_dump(mode="json")

        def collect(value: Any) -> None:
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                for item in value.values():
                    collect(item)

        collect(requirements)
        values.extend(
            ScreeningEvaluationService._fact_text(fact)
            for fact in evaluation_plan
        )
        return "\n".join(values)

    @staticmethod
    def _fact_text(fact: RequirementFact) -> str:
        return "\n".join(source.source_quote for source in fact.sources)

    @staticmethod
    def _validate_configuration(settings: Settings) -> None:
        if not settings.SCREENING_EVALUATION_ENABLED:
            raise ScreeningEvaluationDisabledError("AI 初筛评价功能当前未启用")
        if (
            settings.SCREENING_EVALUATION_PROMPT_VERSION
            != SCREENING_EVALUATION_PROMPT_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "AI 初筛 Prompt 版本与当前代码不一致"
            )
        if (
            settings.SCREENING_EVALUATION_SCHEMA_VERSION
            != SCREENING_EVALUATION_SCHEMA_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "AI 初筛 Schema 版本与当前代码不一致"
            )
        if settings.SCREENING_REDACTION_VERSION != SCREENING_REDACTION_VERSION:
            raise ScreeningEvaluationConfigurationError(
                "AI 初筛脱敏规则版本与当前代码不一致"
            )
        if settings.SCREENING_EVALUATION_TIMEZONE != SCREENING_EVALUATION_TIMEZONE:
            raise ScreeningEvaluationConfigurationError(
                "AI 初筛评价时区与当前代码不一致"
            )
        if (
            settings.EXPERIENCE_PERIOD_FACTS_RULE_VERSION
            != EXPERIENCE_PERIOD_FACTS_RULE_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "经历时间事实规则版本与当前代码不一致"
            )

    @staticmethod
    def _validate_v5_configuration(settings: Settings) -> None:
        if not settings.SCREENING_EVALUATION_ENABLED:
            raise ScreeningEvaluationDisabledError("AI 初筛评价功能当前未启用")
        if (
            settings.SCREENING_EVALUATION_V5_PROMPT_VERSION
            != SCREENING_EVALUATION_V5_PROMPT_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "5.0 AI 初筛 Prompt 版本与当前代码不一致"
            )
        if (
            settings.SCREENING_EVALUATION_V5_SCHEMA_VERSION
            != SCREENING_EVALUATION_V5_SCHEMA_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "5.0 AI 初筛 Schema 版本与当前代码不一致"
            )
        if settings.SCREENING_REDACTION_VERSION != SCREENING_REDACTION_VERSION:
            raise ScreeningEvaluationConfigurationError(
                "AI 初筛脱敏规则版本与当前代码不一致"
            )
        if settings.SCREENING_EVALUATION_TIMEZONE != SCREENING_EVALUATION_TIMEZONE:
            raise ScreeningEvaluationConfigurationError(
                "AI 初筛评价时区与当前代码不一致"
            )
        if (
            settings.EXPERIENCE_PERIOD_FACTS_RULE_VERSION
            != EXPERIENCE_PERIOD_FACTS_RULE_VERSION
        ):
            raise ScreeningEvaluationConfigurationError(
                "经历时间事实规则版本与当前代码不一致"
            )


screening_evaluation_service = ScreeningEvaluationService()
