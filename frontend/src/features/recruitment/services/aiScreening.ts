import axios from 'axios';
import { v2Http } from '../../../services/http';
import type {
  AIScreeningApiError,
  BonusHighlight,
  EvaluationItemCategory,
  EvaluationItemPriority,
  EvaluationItemSourceType,
  JobEvaluationPlan,
  JobEvaluationPlanStatus,
  JobEvaluationPlanWarning,
  LegacyJobEvaluationPlanRequirements,
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
} from '../types/aiScreening';

type JobEvaluationItemResponse = {
  key: string;
  title: string;
  category: EvaluationItemCategory;
  priority: EvaluationItemPriority;
  source_type: EvaluationItemSourceType;
  source_field: string | null;
  source_quote: string | null;
};

type JobEvaluationPlanResponse = {
  id: number;
  job_id: number;
  jd_fingerprint: string;
  status: JobEvaluationPlanStatus;
  is_current: boolean;
  items: JobEvaluationItemResponse[];
  structured_coverage: {
    source_schema_version: string;
    fields: Array<{ source_field: string; source_value_count: number; item_keys: string[] }>;
    all_covered: boolean;
  };
  warnings: JobEvaluationPlanWarning[];
  prompt_version: string;
  model_version: string;
  schema_version: '1.0' | '2.0';
  input_fingerprint: string;
  contract_outdated: boolean;
  input_snapshot: {
    job_id: number;
    title: string;
    department: string | null;
    description: string | null;
    requirements: LegacyJobEvaluationPlanRequirements;
  };
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

export const mapJobEvaluationPlan = (value: JobEvaluationPlanResponse): JobEvaluationPlan => ({
  id: value.id,
  jobId: value.job_id,
  jdFingerprint: value.jd_fingerprint,
  status: value.status,
  isCurrent: value.is_current,
  items: value.items.map(item => ({
    key: item.key,
    title: item.title,
    category: item.category,
    priority: item.priority,
    sourceType: item.source_type,
    sourceField: item.source_field,
    sourceQuote: item.source_quote,
  })),
  structuredCoverage: {
    sourceSchemaVersion: value.structured_coverage.source_schema_version,
    fields: value.structured_coverage.fields.map(field => ({
      sourceField: field.source_field,
      sourceValueCount: field.source_value_count,
      itemKeys: field.item_keys,
    })),
    allCovered: value.structured_coverage.all_covered,
  },
  warnings: value.warnings,
  promptVersion: value.prompt_version,
  modelVersion: value.model_version,
  schemaVersion: value.schema_version,
  inputFingerprint: value.input_fingerprint,
  contractOutdated: value.contract_outdated,
  inputSnapshot: {
    jobId: value.input_snapshot.job_id,
    title: value.input_snapshot.title,
    department: value.input_snapshot.department,
    description: value.input_snapshot.description,
    requirements: value.input_snapshot.requirements,
  },
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
