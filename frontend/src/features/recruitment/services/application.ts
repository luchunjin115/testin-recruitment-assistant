import axios from 'axios';
import { v2Http } from '../../../services/http';
import type { EmploymentType } from './jobs';

export const PUBLIC_APPLICATION_CONSENT_VERSION = '2026-09-02';
export const PUBLIC_APPLICATION_MAX_FILE_BYTES = 10 * 1024 * 1024;
export const PUBLIC_APPLICATION_FILE_EXTENSIONS = ['.pdf', '.docx', '.txt'] as const;

type PublicJobResponse = {
  id: number;
  title: string;
  department: string | null;
  location: string | null;
  employment_type: EmploymentType | null;
  job_background: string | null;
  job_responsibilities: string | null;
  candidate_requirements: string | null;
  preferred_qualifications: string | null;
  public_notes: string | null;
};

type PublicApplicationAcceptedResponse = {
  submission_reference: string;
  accepted_at: string;
  message: string;
};

type PublicErrorDetail = {
  code?: unknown;
  message?: unknown;
};

export type RecruitmentApplicationJob = {
  id: number;
  title: string;
  department: string | null;
  location: string | null;
  employmentType: EmploymentType | null;
  jobBackground: string | null;
  jobResponsibilities: string | null;
  candidateRequirements: string | null;
  preferredQualifications: string | null;
  publicNotes: string | null;
};

export type PublicApplicationInput = {
  name: string;
  phone: string;
  email: string;
  jobId: number;
  resume: File;
  idempotencyKey: string;
};

export type PublicApplicationAccepted = {
  submissionReference: string;
  acceptedAt: string;
  message: string;
};

export type PublicApplicationApiError = {
  status: number | null;
  code: string | null;
  message: string;
  retryAfterSeconds: number | null;
};

const PUBLIC_ERROR_CODES = new Set([
  'PUBLIC_APPLICATION_INVALID',
  'JOB_NOT_OPEN',
  'IDEMPOTENCY_KEY_REUSED',
  'PUBLIC_APPLICATION_REVIEW_REQUIRED',
  'RESUME_FILE_TOO_LARGE',
  'RESUME_TYPE_UNSUPPORTED',
  'PUBLIC_APPLICATION_VALIDATION_FAILED',
  'PUBLIC_APPLICATION_RATE_LIMITED',
  'PUBLIC_APPLICATION_SAVE_FAILED',
  'PUBLIC_APPLICATION_TEMPORARILY_UNAVAILABLE',
]);

const mapPublicJob = (job: PublicJobResponse): RecruitmentApplicationJob => ({
  id: job.id,
  title: job.title,
  department: job.department,
  location: job.location,
  employmentType: job.employment_type,
  jobBackground: job.job_background,
  jobResponsibilities: job.job_responsibilities,
  candidateRequirements: job.candidate_requirements,
  preferredQualifications: job.preferred_qualifications,
  publicNotes: job.public_notes,
});

export const getRecruitmentApplicationJobs = async (): Promise<RecruitmentApplicationJob[]> => {
  const response = await v2Http.get<PublicJobResponse[]>('/public/jobs');
  return response.data.map(mapPublicJob).sort((left, right) => left.id - right.id);
};

export const submitPublicApplication = async (
  input: PublicApplicationInput,
): Promise<PublicApplicationAccepted> => {
  const formData = new FormData();
  formData.append('name', input.name.trim());
  formData.append('phone', input.phone.trim());
  formData.append('email', input.email.trim().toLowerCase());
  formData.append('job_id', String(input.jobId));
  formData.append('privacy_consent', 'true');
  formData.append('consent_version', PUBLIC_APPLICATION_CONSENT_VERSION);
  formData.append('idempotency_key', input.idempotencyKey);
  formData.append('resume', input.resume, input.resume.name);

  const response = await v2Http.post<PublicApplicationAcceptedResponse>(
    '/public/applications',
    formData,
  );
  return {
    submissionReference: response.data.submission_reference,
    acceptedAt: response.data.accepted_at,
    message: response.data.message,
  };
};

export const getPublicApplicationApiError = (error: unknown): PublicApplicationApiError => {
  const fallback: PublicApplicationApiError = {
    status: null,
    code: null,
    message: '投递暂时未能送达，请检查网络后重试',
    retryAfterSeconds: null,
  };
  if (!axios.isAxiosError(error)) return fallback;

  const status = error.response?.status ?? null;
  const detail = error.response?.data?.detail as PublicErrorDetail | undefined;
  const code = typeof detail?.code === 'string' && PUBLIC_ERROR_CODES.has(detail.code)
    ? detail.code
    : null;
  const safeMessage = code !== null && typeof detail?.message === 'string'
    ? detail.message
    : fallback.message;
  const retryAfterValue = error.response?.headers?.['retry-after'];
  const parsedRetryAfter = Number.parseInt(String(retryAfterValue ?? ''), 10);

  return {
    status,
    code,
    message: safeMessage,
    retryAfterSeconds: Number.isFinite(parsedRetryAfter) && parsedRetryAfter > 0
      ? parsedRetryAfter
      : null,
  };
};
