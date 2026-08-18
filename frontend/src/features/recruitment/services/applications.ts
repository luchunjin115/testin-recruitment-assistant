import axios from 'axios';
import { v2Http } from '../../../services/http';
import type {
  Stage7Application,
  Stage7ApplicationApiError,
  Stage7ApplicationApiResponse,
  Stage7ApplicationFilters,
  Stage7ApplicationIntakeApiResponse,
  Stage7ApplicationIntakeInput,
  Stage7ApplicationIntakeOutcome,
  Stage7BackupApplicationInput,
  Stage7PassApplicationInput,
  Stage7RejectApplicationInput,
  Stage7ReverseDecisionInput,
  Stage7ScreeningBatchApiResponse,
  Stage7ScreeningBatchInput,
  Stage7ScreeningBatchOutcome,
  Stage7ScreeningResultDetail,
  Stage7ScreeningResultDetailApiResponse,
  Stage7ScreeningResultSummary,
  Stage7ScreeningResultSummaryApiResponse,
  Stage7ScreeningRunApiResponse,
  Stage7ScreeningRunInput,
  Stage7ScreeningRunOutcome,
  Stage7StageHistory,
  Stage7StageHistoryApiResponse,
  Stage7VoidApplicationInput,
} from '../types/applicationScreening';


const nullableNumber = (value: string | number | null): number | null => {
  if (value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export const mapStage7Application = (
  value: Stage7ApplicationApiResponse,
): Stage7Application => ({
  id: value.id,
  candidateId: value.candidate_id,
  jobId: value.job_id,
  currentResumeId: value.current_resume_id,
  source: value.source,
  lifecycleStatus: value.lifecycle_status,
  recruitmentStage: value.recruitment_stage,
  aiStatus: value.ai_status,
  hrDecision: value.hr_decision,
  currentScreeningResultId: value.current_screening_result_id,
  appliedAt: value.applied_at,
  createdAt: value.created_at,
  updatedAt: value.updated_at,
});

export const mapStage7ScreeningSummary = (
  value: Stage7ScreeningResultSummaryApiResponse,
): Stage7ScreeningResultSummary => ({
  id: value.id,
  candidateId: value.candidate_id,
  jobId: value.job_id,
  applicationId: value.application_id,
  resumeId: value.resume_id,
  attemptNumber: value.attempt_number,
  executionStatus: value.execution_status,
  overallScore: value.overall_score,
  hardPass: value.hard_pass,
  recommendation: value.recommendation,
  evidenceCoverageRate: nullableNumber(value.evidence_coverage_rate),
  errorCode: value.error_code,
  errorMessage: value.error_message,
  startedAt: value.started_at,
  finishedAt: value.finished_at,
  durationMs: value.duration_ms,
  triggerReason: value.trigger_reason,
  forceRerun: value.force_rerun,
  isOutdated: value.is_outdated,
  outdatedAt: value.outdated_at,
  createdAt: value.created_at,
  updatedAt: value.updated_at,
});

export const mapStage7ScreeningDetail = (
  value: Stage7ScreeningResultDetailApiResponse,
): Stage7ScreeningResultDetail => ({
  ...mapStage7ScreeningSummary(value),
  inputFingerprint: value.input_fingerprint,
  skillScore: value.skill_score,
  experienceScore: value.experience_score,
  projectScore: value.project_score,
  strengths: value.strengths || [],
  risks: value.risks || [],
  hardRequirementChecks: value.hard_requirement_checks || [],
  dimensionScores: value.dimension_scores || {},
  reason: value.reason,
  pendingQuestions: value.pending_questions || [],
  resumeEvidence: value.resume_evidence || [],
  jobEvidence: value.job_evidence || [],
  candidateInputSnapshot: value.candidate_input_snapshot,
  resumeSnapshot: value.resume_snapshot,
  jobRequirementsSnapshot: value.job_requirements_snapshot,
  rubricSnapshot: value.rubric_snapshot,
  rulesVersion: value.rules_version,
  promptVersion: value.prompt_version,
  modelProvider: value.model_provider,
  modelName: value.model_name,
  modelConfigVersion: value.model_config_version,
  jobSchemaVersion: value.job_schema_version,
  resumeSchemaVersion: value.resume_schema_version,
  promptTokens: value.prompt_tokens,
  completionTokens: value.completion_tokens,
  totalTokens: value.total_tokens,
  estimatedCost: nullableNumber(value.estimated_cost),
  actorType: value.actor_type,
  actorId: value.actor_id,
  actorLabel: value.actor_label,
  rawResult: value.raw_result,
});

const mapStage7History = (value: Stage7StageHistoryApiResponse): Stage7StageHistory => ({
  id: value.id,
  applicationId: value.application_id,
  fromRecruitmentStage: value.from_recruitment_stage,
  toRecruitmentStage: value.to_recruitment_stage,
  fromHrDecision: value.from_hr_decision,
  toHrDecision: value.to_hr_decision,
  reasonCode: value.reason_code,
  reasonDetail: value.reason_detail,
  actorType: value.actor_type,
  actorId: value.actor_id,
  actorLabel: value.actor_label,
  screeningResultId: value.screening_result_id,
  overridesAiRecommendation: value.overrides_ai_recommendation,
  createdAt: value.created_at,
});

export const listStage7Applications = async (
  filters: Stage7ApplicationFilters = {},
): Promise<Stage7Application[]> => {
  const response = await v2Http.get<Stage7ApplicationApiResponse[]>('/applications', {
    params: {
      job_id: filters.jobId,
      recruitment_stage: filters.recruitmentStage,
      ai_status: filters.aiStatus,
      hr_decision: filters.hrDecision,
      lifecycle_status: filters.lifecycleStatus,
    },
  });
  return response.data.map(mapStage7Application);
};

export const getStage7Application = async (applicationId: number): Promise<Stage7Application> => {
  const response = await v2Http.get<Stage7ApplicationApiResponse>(`/applications/${applicationId}`);
  return mapStage7Application(response.data);
};

export const intakeStage7Application = async (
  input: Stage7ApplicationIntakeInput,
): Promise<Stage7ApplicationIntakeOutcome> => {
  const response = await v2Http.post<Stage7ApplicationIntakeApiResponse>(
    '/applications/intake',
    input,
  );
  return {
    application: mapStage7Application(response.data.application),
    candidateResolution: response.data.candidate_resolution,
    existingApplicationReused: response.data.existing_application_reused,
    suspectedDuplicateCandidateIds: response.data.suspected_duplicate_candidate_ids,
  };
};

export const runStage7ApplicationScreening = async (
  applicationId: number,
  input: Stage7ScreeningRunInput = {},
): Promise<Stage7ScreeningRunOutcome> => {
  const response = await v2Http.post<Stage7ScreeningRunApiResponse>(
    `/applications/${applicationId}/screenings`,
    input,
  );
  return {
    result: mapStage7ScreeningDetail(response.data.result),
    reused: response.data.reused,
    modelCalled: response.data.model_called,
  };
};

export const listStage7ApplicationScreenings = async (
  applicationId: number,
): Promise<Stage7ScreeningResultSummary[]> => {
  const response = await v2Http.get<Stage7ScreeningResultSummaryApiResponse[]>(
    `/applications/${applicationId}/screenings`,
  );
  return response.data.map(mapStage7ScreeningSummary);
};

export const getStage7ScreeningResult = async (
  screeningResultId: number,
): Promise<Stage7ScreeningResultDetail> => {
  const response = await v2Http.get<Stage7ScreeningResultDetailApiResponse>(
    `/screening-results/${screeningResultId}`,
  );
  return mapStage7ScreeningDetail(response.data);
};

export const runStage7ScreeningBatch = async (
  jobId: number,
  input: Stage7ScreeningBatchInput,
): Promise<Stage7ScreeningBatchOutcome> => {
  const response = await v2Http.post<Stage7ScreeningBatchApiResponse>(
    `/jobs/${jobId}/screenings/batch`,
    input,
  );
  return {
    jobId: response.data.job_id,
    items: response.data.items.map(item => ({
      applicationId: item.application_id,
      status: item.status,
      screeningResultId: item.screening_result_id,
      attemptNumber: item.attempt_number,
      reused: item.reused,
      modelCalled: item.model_called,
      errorCode: item.error_code,
      errorMessage: item.error_message,
    })),
    summary: response.data.summary,
  };
};

const runDecision = async <TInput>(
  applicationId: number,
  action: 'pass' | 'backup' | 'reject' | 'undo-rejection' | 'void',
  input: TInput,
): Promise<Stage7Application> => {
  const response = await v2Http.post<Stage7ApplicationApiResponse>(
    `/applications/${applicationId}/${action}`,
    input,
  );
  return mapStage7Application(response.data);
};

export const passStage7Application = (applicationId: number, input: Stage7PassApplicationInput) => (
  runDecision(applicationId, 'pass', input)
);
export const backupStage7Application = (
  applicationId: number,
  input: Stage7BackupApplicationInput,
) => runDecision(applicationId, 'backup', input);
export const rejectStage7Application = (
  applicationId: number,
  input: Stage7RejectApplicationInput,
) => runDecision(applicationId, 'reject', input);
export const undoStage7ApplicationRejection = (
  applicationId: number,
  input: Stage7ReverseDecisionInput,
) => runDecision(applicationId, 'undo-rejection', input);
export const voidStage7Application = (
  applicationId: number,
  input: Stage7VoidApplicationInput,
) => runDecision(applicationId, 'void', input);

export const listStage7ApplicationHistory = async (
  applicationId: number,
): Promise<Stage7StageHistory[]> => {
  const response = await v2Http.get<Stage7StageHistoryApiResponse[]>(
    `/applications/${applicationId}/history`,
  );
  return response.data.map(mapStage7History);
};

export const getStage7ApplicationApiError = (error: unknown): Stage7ApplicationApiError => {
  if (!axios.isAxiosError(error)) {
    return {
      status: null,
      code: null,
      message: 'Application 操作失败，请稍后重试',
      applicationIds: [],
      candidateIds: [],
    };
  }

  const detail = error.response?.data?.detail;
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) {
    return {
      status: error.response?.status ?? null,
      code: null,
      message: 'Application 操作失败，请稍后重试',
      applicationIds: [],
      candidateIds: [],
    };
  }

  return {
    status: error.response?.status ?? null,
    code: typeof detail.code === 'string' ? detail.code : null,
    message: typeof detail.message === 'string'
      ? detail.message
      : 'Application 操作失败，请稍后重试',
    applicationIds: Array.isArray(detail.application_ids)
      ? detail.application_ids.filter((value: unknown): value is number => typeof value === 'number')
      : [],
    candidateIds: Array.isArray(detail.candidate_ids)
      ? detail.candidate_ids.filter((value: unknown): value is number => typeof value === 'number')
      : [],
  };
};
