"""External provider adapters."""

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

__all__ = [name for name in globals() if name.startswith(("DeepSeek", "Resume"))]
