"""External provider adapters."""

from app.adapters.job_evaluation_plan import (
    DeepSeekJobEvaluationPlanAdapter,
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterError,
    JobEvaluationPlanAdapterResult,
)

from app.adapters.resume_structure import (
    DeepSeekResumeStructureAdapter,
    ResumeStructureAdapterError,
    ResumeStructureAdapterResult,
    ResumeStructureAuthenticationError,
    ResumeStructureConfigurationError,
    ResumeStructureEmptyResponseError,
    ResumeStructureInputError,
    ResumeStructureQuotaError,
    ResumeStructureRateLimitError,
    ResumeStructureResponseInterruptedError,
    ResumeStructureServiceUnavailableError,
    ResumeStructureTimeoutError,
    ResumeStructureUpstreamError,
)
from app.adapters.screening_evaluation import (
    DeepSeekScreeningEvaluationAdapter,
    FakeScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterError,
    ScreeningEvaluationAdapterResult,
)

__all__ = [
    name
    for name in globals()
    if name.startswith(
        ("DeepSeek", "Fake", "JobEvaluationPlan", "Resume", "ScreeningEvaluation")
    )
]
