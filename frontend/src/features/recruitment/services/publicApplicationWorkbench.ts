import axios from 'axios';
import { v2Http } from '../../../services/http';

export type PublicApplicationIdentityReviewStatus = 'clear' | 'needs_review' | 'reviewed';
export type PublicApplicationIdentityReviewReason = 'same_name' | 'contact_conflict';
export type ApplicationProcessingStatus =
  | 'queued'
  | 'running'
  | 'waiting_screening'
  | 'succeeded'
  | 'succeeded_with_warnings'
  | 'failed'
  | 'paused';
export type ApplicationProcessingStep =
  | 'extract_text'
  | 'structure_resume'
  | 'trigger_screening'
  | 'await_screening'
  | 'completed';
export type ApplicationProcessingWaitingReason =
  | 'job_closed'
  | 'existing_application_resume_choice';

type ProcessingRunApi = {
  id: number;
  trigger_type: 'automatic' | 'manual_retry';
  status: ApplicationProcessingStatus;
  current_step: ApplicationProcessingStep;
  attempt_count: number;
  waiting_reason: ApplicationProcessingWaitingReason | null;
  error_code: string | null;
  error_message: string | null;
  warning_codes: Array<'RESUME_STRUCTURE_FAILED'>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

type WorkbenchSummaryApi = {
  submission_id: number;
  submission_reference: string;
  submitted_at: string;
  identity_review_status: PublicApplicationIdentityReviewStatus;
  identity_review_reasons: PublicApplicationIdentityReviewReason[];
  application_id: number;
  candidate_id: number;
  resume_id: number;
  job_id: number;
  candidate_name: string;
  job_title: string;
  job_status: 'draft' | 'open' | 'closed';
  resume_filename: string;
  resume_parse_status: 'uploaded' | 'parsing' | 'parsed' | 'failed';
  lifecycle_status: 'active' | 'ended' | 'voided';
  recruitment_stage: 'applied' | 'hr_review' | 'screening_passed' | 'backup' | 'rejected';
  hr_decision: 'pending' | 'passed' | 'backup' | 'rejected';
  latest_run: ProcessingRunApi;
};

type IdentityCandidateApi = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  source: string | null;
  created_at: string;
  is_submission_candidate: boolean;
};

type WorkbenchDetailApi = WorkbenchSummaryApi & {
  processing_runs: ProcessingRunApi[];
  identity_candidates: IdentityCandidateApi[];
};

export type ApplicationProcessingRunSummary = {
  id: number;
  triggerType: 'automatic' | 'manual_retry';
  status: ApplicationProcessingStatus;
  currentStep: ApplicationProcessingStep;
  attemptCount: number;
  waitingReason: ApplicationProcessingWaitingReason | null;
  errorCode: string | null;
  errorMessage: string | null;
  warningCodes: Array<'RESUME_STRUCTURE_FAILED'>;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type PublicApplicationWorkbenchSummary = {
  submissionId: number;
  submissionReference: string;
  submittedAt: string;
  identityReviewStatus: PublicApplicationIdentityReviewStatus;
  identityReviewReasons: PublicApplicationIdentityReviewReason[];
  applicationId: number;
  candidateId: number;
  resumeId: number;
  jobId: number;
  candidateName: string;
  jobTitle: string;
  jobStatus: 'draft' | 'open' | 'closed';
  resumeFilename: string;
  resumeParseStatus: 'uploaded' | 'parsing' | 'parsed' | 'failed';
  lifecycleStatus: 'active' | 'ended' | 'voided';
  recruitmentStage: 'applied' | 'hr_review' | 'screening_passed' | 'backup' | 'rejected';
  hrDecision: 'pending' | 'passed' | 'backup' | 'rejected';
  latestRun: ApplicationProcessingRunSummary;
};

export type PublicApplicationIdentityCandidate = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  source: string | null;
  createdAt: string;
  isSubmissionCandidate: boolean;
};

export type PublicApplicationWorkbenchDetail = PublicApplicationWorkbenchSummary & {
  processingRuns: ApplicationProcessingRunSummary[];
  identityCandidates: PublicApplicationIdentityCandidate[];
};

export type PublicApplicationWorkbenchError = {
  status: number | null;
  code: string | null;
  message: string;
};

const SAFE_ERROR_CODES = new Set([
  'PUBLIC_APPLICATION_SUBMISSION_NOT_FOUND',
  'RESUME_STRUCTURE_RESULT_NOT_FOUND',
  'PUBLIC_APPLICATION_IDENTITY_REVIEW_NOT_REQUIRED',
  'APPLICATION_PROCESSING_ACTIVE_RUN',
  'APPLICATION_PROCESSING_RETRY_NOT_ALLOWED',
  'APPLICATION_PROCESSING_PAUSE_NOT_RECOVERED',
  'HR_ACTION_CONFIRMATION_REQUIRED',
  'PUBLIC_APPLICATION_WORKBENCH_OPERATION_FAILED',
]);

const mapRun = (value: ProcessingRunApi): ApplicationProcessingRunSummary => ({
  id: value.id,
  triggerType: value.trigger_type,
  status: value.status,
  currentStep: value.current_step,
  attemptCount: value.attempt_count,
  waitingReason: value.waiting_reason,
  errorCode: value.error_code,
  errorMessage: value.error_message,
  warningCodes: value.warning_codes,
  startedAt: value.started_at,
  completedAt: value.completed_at,
  createdAt: value.created_at,
  updatedAt: value.updated_at,
});

const mapSummary = (value: WorkbenchSummaryApi): PublicApplicationWorkbenchSummary => ({
  submissionId: value.submission_id,
  submissionReference: value.submission_reference,
  submittedAt: value.submitted_at,
  identityReviewStatus: value.identity_review_status,
  identityReviewReasons: value.identity_review_reasons,
  applicationId: value.application_id,
  candidateId: value.candidate_id,
  resumeId: value.resume_id,
  jobId: value.job_id,
  candidateName: value.candidate_name,
  jobTitle: value.job_title,
  jobStatus: value.job_status,
  resumeFilename: value.resume_filename,
  resumeParseStatus: value.resume_parse_status,
  lifecycleStatus: value.lifecycle_status,
  recruitmentStage: value.recruitment_stage,
  hrDecision: value.hr_decision,
  latestRun: mapRun(value.latest_run),
});

const mapDetail = (value: WorkbenchDetailApi): PublicApplicationWorkbenchDetail => ({
  ...mapSummary(value),
  processingRuns: value.processing_runs.map(mapRun),
  identityCandidates: value.identity_candidates.map(candidate => ({
    id: candidate.id,
    name: candidate.name,
    phone: candidate.phone,
    email: candidate.email,
    source: candidate.source,
    createdAt: candidate.created_at,
    isSubmissionCandidate: candidate.is_submission_candidate,
  })),
});

export const listPublicApplicationSubmissions = async (): Promise<PublicApplicationWorkbenchSummary[]> => {
  const response = await v2Http.get<WorkbenchSummaryApi[]>('/public-application-submissions');
  return response.data.map(mapSummary);
};

export const getPublicApplicationSubmission = async (
  submissionId: number,
): Promise<PublicApplicationWorkbenchDetail> => {
  const response = await v2Http.get<WorkbenchDetailApi>(
    `/public-application-submissions/${submissionId}`,
  );
  return mapDetail(response.data);
};

export const markPublicApplicationIdentityReviewed = async (
  submissionId: number,
): Promise<PublicApplicationWorkbenchDetail> => {
  const response = await v2Http.post<WorkbenchDetailApi>(
    `/public-application-submissions/${submissionId}/identity-review`,
    { confirmed: true },
  );
  return mapDetail(response.data);
};

export const retryPublicApplicationProcessing = async (
  submissionId: number,
): Promise<ApplicationProcessingRunSummary> => {
  const response = await v2Http.post<ProcessingRunApi>(
    `/public-application-submissions/${submissionId}/retry`,
    { confirmed: true },
  );
  return mapRun(response.data);
};

export const getPublicApplicationWorkbenchError = (
  error: unknown,
): PublicApplicationWorkbenchError => {
  if (!axios.isAxiosError(error)) {
    return { status: null, code: null, message: '公开投递状态读取失败，请稍后重试' };
  }
  const detail = error.response?.data?.detail;
  const code = detail && typeof detail === 'object' && !Array.isArray(detail)
    && typeof detail.code === 'string' && SAFE_ERROR_CODES.has(detail.code)
    ? detail.code
    : null;
  return {
    status: error.response?.status ?? null,
    code,
    message: code && typeof detail.message === 'string'
      ? detail.message
      : '公开投递状态读取失败，请稍后重试',
  };
};

export const isPublicApplicationException = (
  submission: PublicApplicationWorkbenchSummary,
) => submission.identityReviewStatus === 'needs_review'
  || ['failed', 'paused', 'succeeded_with_warnings'].includes(submission.latestRun.status);

export const isPublicApplicationActive = (status: ApplicationProcessingStatus) => (
  ['queued', 'running', 'waiting_screening'].includes(status)
);
