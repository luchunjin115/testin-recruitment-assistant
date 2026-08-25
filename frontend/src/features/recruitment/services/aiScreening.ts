import axios from 'axios';
import { v2Http } from '../../../services/http';
import type {
  AIScreeningApiError,
  BonusHighlight,
  EvaluationCriterion,
  EvaluationItemCategory,
  EvaluationItemPriority,
  EvaluationItemSourceType,
  FiveSectionSourceField,
  JobEvaluationPlan,
  JobEvaluationPlanInputSnapshot,
  JobEvaluationPlanStatus,
  JobEvaluationPlanWarning,
  JobEvaluationPlanWarningCode,
  LegacyJobEvaluationPlanRequirements,
  RequirementFact,
  RequirementAssessment,
  ScreeningBatchReassessmentResult,
  ScreeningEvidence,
  ScreeningOutdatedReason,
  ScreeningReport,
  ScreeningRun,
  ScreeningRunStatus,
  ScreeningRunTriggerType,
  ScreeningState,
  ScreeningTriggerResult,
  ScreeningWaitingReason,
} from '../types/aiScreening';

type JobEvaluationItemSourceResponse = {
  source_field: FiveSectionSourceField;
  source_unit_id: string;
  source_quote: string;
};

type JobEvaluationItemResponse = {
  key: string;
  title: string;
  category: EvaluationItemCategory;
  priority: EvaluationItemPriority;
  sources?: JobEvaluationItemSourceResponse[];
  source_type?: EvaluationItemSourceType | null;
  source_field?: string | null;
  source_quote?: string | null;
};

type JobEvaluationPlanWarningResponse = 'limited_basis' | {
  code: JobEvaluationPlanWarningCode;
  message: string;
  source_unit_ids: string[];
  fact_ids?: string[];
};

type JobEvaluationPlanSourceReviewSummaryResponse = {
  rule_version: 'five_section_source_units_v1';
  total_units: number;
  reviewed_units: number;
  evaluation_units: number;
  non_evaluation_units: number;
  all_reviewed: boolean;
  units: Array<{
    source_unit_id: string;
    disposition: 'evaluation' | 'non_evaluation';
    non_evaluation_reason:
      | 'company_info'
      | 'benefit'
      | 'promotion'
      | 'recruitment_process'
      | 'candidate_note'
      | 'context'
      | 'other'
      | null;
    item_keys?: string[];
    fact_ids?: string[];
  }>;
};

type RequirementFactResponse = {
  fact_id: string;
  category: EvaluationItemCategory;
  priority: EvaluationItemPriority;
  sources: JobEvaluationItemSourceResponse[];
};

type EvaluationCriterionResponse = {
  criterion_id: string;
  name: string;
  fact_ids: string[];
};

type JobEvaluationPlanCoverageReviewSummaryResponse = {
  status: 'passed' | 'needs_repair';
  findings: Array<{
    code:
      | 'missing_fact'
      | 'unsupported_fact'
      | 'wrong_disposition'
      | 'invalid_atomicity'
      | 'missing_source_merge'
      | 'category_mismatch';
    source_unit_ids: string[];
    fact_ids: string[];
    message: string;
  }>;
  repair_performed: boolean;
  reviewed_source_unit_ids: string[];
};

type JobEvaluationPlanGenerationAuditResponse = {
  business_call_count: number;
  content_repair_count: number;
  infrastructure_retry_count: number;
  calls: Array<{
    role: 'fact_extraction' | 'coverage_review' | 'local_repair' | 'criterion_grouping';
    prompt_version: string;
    model: string;
    input_tokens: number;
    output_tokens: number;
    duration_ms: number;
    infrastructure_retry_count: number;
    result: 'succeeded' | 'failed';
    error_code?: string | null;
  }>;
};

type LegacyJobEvaluationPlanInputSnapshotResponse = {
  job_id: number;
  title: string;
  department: string | null;
  description: string | null;
  requirements: LegacyJobEvaluationPlanRequirements;
};

type JobEvaluationPlanInputSnapshotV3Response = {
  schema_version: '3.0' | '4.0';
  job_context: {
    title: string;
    department: string | null;
    job_background: string | null;
  };
  evaluation_fields: {
    job_responsibilities: string | null;
    candidate_requirements: string | null;
    preferred_qualifications: string | null;
  };
  source_units: Array<{
    source_unit_id: string;
    source_field: FiveSectionSourceField;
    ordinal: number;
    source_text: string;
  }>;
};

type JobEvaluationPlanResponse = {
  id: number;
  job_id: number;
  jd_fingerprint: string;
  status: JobEvaluationPlanStatus;
  is_current: boolean;
  items: JobEvaluationItemResponse[] | null;
  structured_coverage?: {
    source_schema_version: string;
    fields: Array<{ source_field: string; source_value_count: number; item_keys: string[] }>;
    all_covered: boolean;
  } | null;
  source_review_summary?: JobEvaluationPlanSourceReviewSummaryResponse | null;
  requirement_facts?: RequirementFactResponse[] | null;
  evaluation_criteria?: EvaluationCriterionResponse[] | null;
  coverage_review_summary?: JobEvaluationPlanCoverageReviewSummaryResponse | null;
  generation_audit?: JobEvaluationPlanGenerationAuditResponse | null;
  warnings: JobEvaluationPlanWarningResponse[];
  prompt_version: string;
  model_version: string;
  schema_version: '1.0' | '2.0' | '3.0' | '4.0';
  input_fingerprint: string;
  contract_outdated: boolean;
  input_snapshot:
    | LegacyJobEvaluationPlanInputSnapshotResponse
    | JobEvaluationPlanInputSnapshotV3Response;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  updated_at: string;
};

type ScreeningEvidenceResponse = { quote: string; section: string | null };
type RequirementAssessmentResponse = {
  requirement_key: string;
  score: number;
  reason: string;
  calculation_note: string | null;
  experience_period_fact_keys: string[];
  evidence: ScreeningEvidenceResponse[];
};
type BonusHighlightResponse = {
  title: string;
  score: number;
  reason: string;
  evidence: ScreeningEvidenceResponse[];
};
type ScreeningReportResponse = {
  id: number;
  application_id: number;
  job_id: number;
  resume_id: number;
  job_evaluation_plan_id: number;
  overall_score: number;
  display_label: string;
  overall_summary: string;
  requirement_assessments: RequirementAssessmentResponse[];
  bonus_highlights: BonusHighlightResponse[];
  tradeoff_reason: string | null;
  interview_questions: string[];
  input_fingerprint: string;
  jd_fingerprint: string;
  plan_fingerprint: string;
  resume_fingerprint: string;
  prompt_version: string;
  model_version: string;
  schema_version: string;
  redaction_version: string;
  evaluation_reference_at: string | null;
  evaluation_timezone: string | null;
  experience_period_facts_rule_version: string | null;
  is_outdated: boolean;
  outdated_reasons: ScreeningOutdatedReason[];
  outdated_at: string | null;
  generated_at: string;
  updated_at: string;
};
type ScreeningRunResponse = {
  id: number;
  application_id: number;
  job_id: number;
  resume_id: number;
  job_evaluation_plan_id: number | null;
  trigger_type: ScreeningRunTriggerType;
  status: ScreeningRunStatus;
  waiting_reason: ScreeningWaitingReason | null;
  input_fingerprint: string;
  prompt_version: string;
  model_version: string;
  schema_version: string;
  redaction_version: string;
  evaluation_reference_at: string | null;
  evaluation_timezone: string | null;
  experience_period_facts_rule_version: string | null;
  experience_period_facts_fingerprint: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  duration_ms: number | null;
  attempt_count: number;
  created_at: string;
  updated_at: string;
};
type ScreeningStateResponse = {
  application_id: number;
  report: ScreeningReportResponse | null;
  latest_run: ScreeningRunResponse | null;
};
type ScreeningTriggerResponse = {
  application_id: number;
  run: ScreeningRunResponse | null;
  report: ScreeningReportResponse | null;
  reused_report: boolean;
  reused_run: boolean;
};
type ScreeningBatchResponse = { job_id: number; results: ScreeningTriggerResponse[] };

const mapEvidence = (value: ScreeningEvidenceResponse): ScreeningEvidence => ({
  quote: value.quote,
  section: value.section,
});

const mapRequirementAssessment = (
  value: RequirementAssessmentResponse,
): RequirementAssessment => ({
  requirementKey: value.requirement_key,
  score: value.score,
  reason: value.reason,
  calculationNote: value.calculation_note,
  experiencePeriodFactKeys: value.experience_period_fact_keys,
  evidence: value.evidence.map(mapEvidence),
});

const mapBonusHighlight = (value: BonusHighlightResponse): BonusHighlight => ({
  title: value.title,
  score: value.score,
  reason: value.reason,
  evidence: value.evidence.map(mapEvidence),
});

const mapInputSnapshot = (
  value: JobEvaluationPlanResponse['input_snapshot'],
): JobEvaluationPlanInputSnapshot => {
  if ('schema_version' in value && value.schema_version === '4.0') {
    return {
      schemaVersion: '4.0',
      jobContext: {
        title: value.job_context.title,
        department: value.job_context.department,
        jobBackground: value.job_context.job_background,
      },
      evaluationFields: {
        jobResponsibilities: value.evaluation_fields.job_responsibilities,
        candidateRequirements: value.evaluation_fields.candidate_requirements,
        preferredQualifications: value.evaluation_fields.preferred_qualifications,
      },
      sourceUnits: value.source_units.map(unit => ({
        sourceUnitId: unit.source_unit_id,
        sourceField: unit.source_field,
        ordinal: unit.ordinal,
        sourceText: unit.source_text,
      })),
    };
  }
  if ('schema_version' in value && value.schema_version === '3.0') {
    return {
      schemaVersion: value.schema_version,
      jobContext: {
        title: value.job_context.title,
        department: value.job_context.department,
        jobBackground: value.job_context.job_background,
      },
      evaluationFields: {
        jobResponsibilities: value.evaluation_fields.job_responsibilities,
        candidateRequirements: value.evaluation_fields.candidate_requirements,
        preferredQualifications: value.evaluation_fields.preferred_qualifications,
      },
      sourceUnits: value.source_units.map(unit => ({
        sourceUnitId: unit.source_unit_id,
        sourceField: unit.source_field,
        ordinal: unit.ordinal,
        sourceText: unit.source_text,
      })),
    };
  }
  const legacy = value as LegacyJobEvaluationPlanInputSnapshotResponse;
  return {
    jobId: legacy.job_id,
    title: legacy.title,
    department: legacy.department,
    description: legacy.description,
    requirements: legacy.requirements,
  };
};

export const mapJobEvaluationPlan = (value: JobEvaluationPlanResponse): JobEvaluationPlan => ({
  id: value.id,
  jobId: value.job_id,
  jdFingerprint: value.jd_fingerprint,
  status: value.status,
  isCurrent: value.is_current,
  items: (value.items ?? []).map(item => ({
    key: item.key,
    title: item.title,
    category: item.category,
    priority: item.priority,
    sources: (item.sources ?? []).map(source => ({
      sourceField: source.source_field,
      sourceUnitId: source.source_unit_id,
      sourceQuote: source.source_quote,
    })),
    historicalSource: item.source_type ? {
      kind: item.source_type,
      field: item.source_field ?? null,
      quote: item.source_quote ?? null,
    } : null,
  })),
  structuredCoverage: value.structured_coverage ? {
    sourceSchemaVersion: value.structured_coverage.source_schema_version,
    fields: value.structured_coverage.fields.map(field => ({
      sourceField: field.source_field,
      sourceValueCount: field.source_value_count,
      itemKeys: field.item_keys,
    })),
    allCovered: value.structured_coverage.all_covered,
  } : null,
  sourceReviewSummary: value.source_review_summary ? {
    ruleVersion: value.source_review_summary.rule_version,
    totalUnits: value.source_review_summary.total_units,
    reviewedUnits: value.source_review_summary.reviewed_units,
    evaluationUnits: value.source_review_summary.evaluation_units,
    nonEvaluationUnits: value.source_review_summary.non_evaluation_units,
    allReviewed: value.source_review_summary.all_reviewed,
    units: value.source_review_summary.units.map(unit => ({
      sourceUnitId: unit.source_unit_id,
      disposition: unit.disposition,
      nonEvaluationReason: unit.non_evaluation_reason,
      itemKeys: unit.item_keys ?? [],
      factIds: unit.fact_ids ?? [],
    })),
  } : null,
  requirementFacts: (value.requirement_facts ?? []).map((fact): RequirementFact => ({
    factId: fact.fact_id,
    category: fact.category,
    priority: fact.priority,
    sources: fact.sources.map(source => ({
      sourceField: source.source_field,
      sourceUnitId: source.source_unit_id,
      sourceQuote: source.source_quote,
    })),
  })),
  evaluationCriteria: (value.evaluation_criteria ?? []).map((criterion): EvaluationCriterion => ({
    criterionId: criterion.criterion_id,
    name: criterion.name,
    factIds: criterion.fact_ids,
  })),
  coverageReviewSummary: value.coverage_review_summary ? {
    status: value.coverage_review_summary.status,
    findings: value.coverage_review_summary.findings.map(finding => ({
      code: finding.code,
      sourceUnitIds: finding.source_unit_ids,
      factIds: finding.fact_ids,
      message: finding.message,
    })),
    repairPerformed: value.coverage_review_summary.repair_performed,
    reviewedSourceUnitIds: value.coverage_review_summary.reviewed_source_unit_ids,
  } : null,
  generationAudit: value.generation_audit ? {
    businessCallCount: value.generation_audit.business_call_count,
    contentRepairCount: value.generation_audit.content_repair_count,
    infrastructureRetryCount: value.generation_audit.infrastructure_retry_count,
    calls: value.generation_audit.calls.map(call => ({
      role: call.role,
      promptVersion: call.prompt_version,
      model: call.model,
      inputTokens: call.input_tokens,
      outputTokens: call.output_tokens,
      durationMs: call.duration_ms,
      infrastructureRetryCount: call.infrastructure_retry_count,
      result: call.result,
      errorCode: call.error_code ?? null,
    })),
  } : null,
  warnings: value.warnings.map((warning): JobEvaluationPlanWarning => (
    typeof warning === 'string'
      ? warning
      : {
        code: warning.code,
        message: warning.message,
        sourceUnitIds: warning.source_unit_ids,
        factIds: warning.fact_ids ?? [],
      }
  )),
  promptVersion: value.prompt_version,
  modelVersion: value.model_version,
  schemaVersion: value.schema_version,
  inputFingerprint: value.input_fingerprint,
  contractOutdated: value.contract_outdated,
  inputSnapshot: mapInputSnapshot(value.input_snapshot),
  errorCode: value.error_code,
  errorMessage: value.error_message,
  createdAt: value.created_at,
  completedAt: value.completed_at,
  updatedAt: value.updated_at,
});

const mapScreeningReport = (value: ScreeningReportResponse): ScreeningReport => ({
  id: value.id,
  applicationId: value.application_id,
  jobId: value.job_id,
  resumeId: value.resume_id,
  jobEvaluationPlanId: value.job_evaluation_plan_id,
  overallScore: value.overall_score,
  displayLabel: value.display_label,
  overallSummary: value.overall_summary,
  requirementAssessments: value.requirement_assessments.map(mapRequirementAssessment),
  bonusHighlights: value.bonus_highlights.map(mapBonusHighlight),
  tradeoffReason: value.tradeoff_reason,
  interviewQuestions: value.interview_questions,
  inputFingerprint: value.input_fingerprint,
  jdFingerprint: value.jd_fingerprint,
  planFingerprint: value.plan_fingerprint,
  resumeFingerprint: value.resume_fingerprint,
  promptVersion: value.prompt_version,
  modelVersion: value.model_version,
  schemaVersion: value.schema_version,
  redactionVersion: value.redaction_version,
  evaluationReferenceAt: value.evaluation_reference_at,
  evaluationTimezone: value.evaluation_timezone,
  experiencePeriodFactsRuleVersion: value.experience_period_facts_rule_version,
  isOutdated: value.is_outdated,
  outdatedReasons: value.outdated_reasons,
  outdatedAt: value.outdated_at,
  generatedAt: value.generated_at,
  updatedAt: value.updated_at,
});

const mapScreeningRun = (value: ScreeningRunResponse): ScreeningRun => ({
  id: value.id,
  applicationId: value.application_id,
  jobId: value.job_id,
  resumeId: value.resume_id,
  jobEvaluationPlanId: value.job_evaluation_plan_id,
  triggerType: value.trigger_type,
  status: value.status,
  waitingReason: value.waiting_reason === 'plan_pending_confirmation'
    ? 'plan_pending_confirmation'
    : value.waiting_reason,
  inputFingerprint: value.input_fingerprint,
  promptVersion: value.prompt_version,
  modelVersion: value.model_version,
  schemaVersion: value.schema_version,
  redactionVersion: value.redaction_version,
  evaluationReferenceAt: value.evaluation_reference_at,
  evaluationTimezone: value.evaluation_timezone,
  experiencePeriodFactsRuleVersion: value.experience_period_facts_rule_version,
  experiencePeriodFactsFingerprint: value.experience_period_facts_fingerprint,
  startedAt: value.started_at,
  completedAt: value.completed_at,
  errorCode: value.error_code,
  errorMessage: value.error_message,
  inputTokens: value.input_tokens,
  outputTokens: value.output_tokens,
  durationMs: value.duration_ms,
  attemptCount: value.attempt_count,
  createdAt: value.created_at,
  updatedAt: value.updated_at,
});

const mapScreeningState = (value: ScreeningStateResponse): ScreeningState => ({
  applicationId: value.application_id,
  report: value.report ? mapScreeningReport(value.report) : null,
  latestRun: value.latest_run ? mapScreeningRun(value.latest_run) : null,
});

const mapScreeningTrigger = (value: ScreeningTriggerResponse): ScreeningTriggerResult => ({
  applicationId: value.application_id,
  run: value.run ? mapScreeningRun(value.run) : null,
  report: value.report ? mapScreeningReport(value.report) : null,
  reusedReport: value.reused_report,
  reusedRun: value.reused_run,
});

export const getJobEvaluationPlan = async (
  jobId: number,
  signal?: AbortSignal,
): Promise<JobEvaluationPlan> => {
  const response = await v2Http.get<JobEvaluationPlanResponse>(
    `/jobs/${jobId}/evaluation-plan`,
    { signal },
  );
  return mapJobEvaluationPlan(response.data);
};

const postEvaluationPlan = async (
  jobId: number,
  action: 'generate' | 'regenerate',
): Promise<JobEvaluationPlan> => {
  const response = await v2Http.post<JobEvaluationPlanResponse>(
    `/jobs/${jobId}/evaluation-plan/${action}`,
  );
  return mapJobEvaluationPlan(response.data);
};

export const generateJobEvaluationPlan = (jobId: number) => postEvaluationPlan(jobId, 'generate');
export const regenerateJobEvaluationPlan = (jobId: number) => postEvaluationPlan(jobId, 'regenerate');
export const confirmJobEvaluationPlan = async (jobId: number): Promise<JobEvaluationPlan> => {
  const response = await v2Http.post<JobEvaluationPlanResponse>(
    `/jobs/${jobId}/evaluation-plan/confirm`,
  );
  return mapJobEvaluationPlan(response.data);
};

export const getApplicationScreening = async (
  applicationId: number,
  signal?: AbortSignal,
): Promise<ScreeningState> => {
  const response = await v2Http.get<ScreeningStateResponse>(
    `/applications/${applicationId}/screening`,
    { signal },
  );
  return mapScreeningState(response.data);
};

const postApplicationScreening = async (
  applicationId: number,
  reassess: boolean,
): Promise<ScreeningTriggerResult> => {
  const suffix = reassess ? '/re-evaluate' : '';
  const response = await v2Http.post<ScreeningTriggerResponse>(
    `/applications/${applicationId}/screening${suffix}`,
  );
  return mapScreeningTrigger(response.data);
};

export const triggerApplicationScreening = (applicationId: number) => (
  postApplicationScreening(applicationId, false)
);
export const reassessApplicationScreening = (applicationId: number) => (
  postApplicationScreening(applicationId, true)
);

export const reassessJobApplications = async (
  jobId: number,
  applicationIds: number[],
): Promise<ScreeningBatchReassessmentResult> => {
  const response = await v2Http.post<ScreeningBatchResponse>(
    `/jobs/${jobId}/screening/re-evaluate-batch`,
    { application_ids: applicationIds },
  );
  return {
    jobId: response.data.job_id,
    results: response.data.results.map(mapScreeningTrigger),
  };
};

export const switchApplicationCurrentResume = async (
  applicationId: number,
  resumeId: number,
): Promise<void> => {
  await v2Http.put(`/applications/${applicationId}/current-resume`, { resume_id: resumeId });
};

export const getAIScreeningApiError = (error: unknown): AIScreeningApiError => {
  if (!axios.isAxiosError(error)) {
    return { status: null, code: null, message: 'AI 初筛操作失败，请稍后重试' };
  }
  const detail = error.response?.data?.detail;
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) {
    return {
      status: error.response?.status ?? null,
      code: null,
      message: 'AI 初筛操作失败，请稍后重试',
    };
  }
  return {
    status: error.response?.status ?? null,
    code: typeof detail.code === 'string' ? detail.code : null,
    message: typeof detail.message === 'string'
      ? detail.message
      : 'AI 初筛操作失败，请稍后重试',
  };
};
