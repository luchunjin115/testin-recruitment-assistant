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
  Stage7StageHistory,
  Stage7StageHistoryApiResponse,
  Stage7VoidApplicationInput,
} from '../types/applicationScreening';


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
  hrDecision: value.hr_decision,
  finalOutcome: value.final_outcome,
  appliedAt: value.applied_at,
  createdAt: value.created_at,
  updatedAt: value.updated_at,
});

const mapStage7History = (value: Stage7StageHistoryApiResponse): Stage7StageHistory => ({
  id: value.id,
  applicationId: value.application_id,
  reportId: value.report_id,
  fromRecruitmentStage: value.from_recruitment_stage,
  toRecruitmentStage: value.to_recruitment_stage,
  fromHrDecision: value.from_hr_decision,
  toHrDecision: value.to_hr_decision,
  reasonCode: value.reason_code,
  reasonDetail: value.reason_detail,
  actorType: value.actor_type,
  actorId: value.actor_id,
  actorLabel: value.actor_label,
  createdAt: value.created_at,
});

export const listStage7Applications = async (
  filters: Stage7ApplicationFilters = {},
): Promise<Stage7Application[]> => {
  const response = await v2Http.get<Stage7ApplicationApiResponse[]>('/applications', {
    params: {
      job_id: filters.jobId,
      recruitment_stage: filters.recruitmentStage,
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
