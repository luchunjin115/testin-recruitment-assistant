import axios from 'axios';

import type {
  ResumeParseDraft,
  ResumeStructureFailureWithDraft,
  ResumeStructureResponse,
} from './types/resumeStructure';


export type ResumeStructureViewState =
  | { status: 'idle' }
  | { status: 'processing'; force: boolean }
  | { status: 'succeeded'; result: ResumeStructureResponse }
  | {
    status: 'failed';
    message: string;
    httpStatus?: number;
    previousResult?: ResumeStructureFailureWithDraft;
  };

export type ResumeDraftSummary = {
  basicInfo: number;
  education: number;
  work: number;
  projects: number;
  skills: number;
};

const isFailureWithDraft = (value: unknown): value is ResumeStructureFailureWithDraft => {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Partial<ResumeStructureFailureWithDraft>;
  return typeof candidate.detail === 'string'
    && candidate.has_previous_draft === true
    && candidate.structure_status === 'failed'
    && typeof candidate.draft === 'object'
    && candidate.draft !== null;
};

export const parseResumeStructureError = (
  error: unknown,
  fallback = 'AI 简历识别失败，你仍然可以继续手动填写',
): Extract<ResumeStructureViewState, { status: 'failed' }> => {
  if (axios.isAxiosError(error)) {
    const httpStatus = error.response?.status;
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (isFailureWithDraft(detail)) {
      return {
        status: 'failed',
        message: detail.detail,
        httpStatus,
        previousResult: detail,
      };
    }
    if (typeof detail === 'string' && detail.trim()) {
      return { status: 'failed', message: detail, httpStatus };
    }
    if (error.code === 'ECONNABORTED') {
      return {
        status: 'failed',
        message: 'AI 识别请求超时，你仍然可以继续手动填写',
        httpStatus,
      };
    }
  }

  return {
    status: 'failed',
    message: error instanceof Error && error.message ? error.message : fallback,
  };
};

export const summarizeResumeDraft = (draft: ResumeParseDraft): ResumeDraftSummary => ({
  basicInfo: Object.values(draft.basic_info).filter(value => (
    value !== null && (typeof value !== 'string' || value.trim().length > 0)
  )).length,
  education: draft.education_records.length,
  work: draft.work_experiences.length,
  projects: draft.project_experiences.length,
  skills: draft.skills.length,
});
