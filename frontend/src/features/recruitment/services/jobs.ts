import axios from 'axios';
import { v2Http } from '../../../services/http';

export type JobStatus = 'draft' | 'open' | 'closed';
export type EmploymentType = 'full_time' | 'part_time' | 'internship' | 'contract';

type JobResponse = {
  id: number;
  title: string;
  department: string | null;
  location: string | null;
  employment_type: EmploymentType | null;
  headcount: number | null;
  job_background: string | null;
  job_responsibilities: string | null;
  candidate_requirements: string | null;
  preferred_qualifications: string | null;
  public_notes: string | null;
  status: JobStatus;
  created_at: string;
  updated_at: string;
};

type CandidateResponse = { id: number; applied_job_id: number | null };

export type RecruitmentJob = {
  id: number;
  title: string;
  department: string | null;
  location: string | null;
  employmentType: EmploymentType | null;
  headcount: number | null;
  jobBackground: string | null;
  jobResponsibilities: string | null;
  candidateRequirements: string | null;
  preferredQualifications: string | null;
  publicNotes: string | null;
  status: JobStatus;
  candidateCount: number;
  createdAt: string;
  updatedAt: string;
};

export type JobListSnapshot = {
  items: RecruitmentJob[];
  total: number;
  draftCount: number;
  openCount: number;
  closedCount: number;
  linkedCandidateCount: number;
};

export type RecruitmentJobInput = {
  title: string;
  department: string | null;
  location: string | null;
  employment_type: EmploymentType | null;
  headcount: number | null;
  job_background: string | null;
  job_responsibilities: string | null;
  candidate_requirements: string | null;
  preferred_qualifications: string | null;
  public_notes: string | null;
};

export type RecruitmentJobCreateInput = RecruitmentJobInput & { status: 'draft' | 'open' };

export type RecruitmentJobApiError = {
  status: number | null;
  code: string | null;
  message: string;
  fields: string[];
  references: Record<string, number> | null;
};

const mapJob = (job: JobResponse, candidateCount = 0): RecruitmentJob => ({
  id: job.id,
  title: job.title,
  department: job.department,
  location: job.location,
  employmentType: job.employment_type,
  headcount: job.headcount,
  jobBackground: job.job_background,
  jobResponsibilities: job.job_responsibilities,
  candidateRequirements: job.candidate_requirements,
  preferredQualifications: job.preferred_qualifications,
  publicNotes: job.public_notes,
  status: job.status,
  candidateCount,
  createdAt: job.created_at,
  updatedAt: job.updated_at,
});

export const isOpenJobStatus = (status: JobStatus) => status === 'open';
export const isClosedJobStatus = (status: JobStatus) => status === 'closed';

export const getRecruitmentJobs = async (): Promise<JobListSnapshot> => {
  const [jobsResponse, candidatesResponse] = await Promise.all([
    v2Http.get<JobResponse[]>('/jobs'),
    v2Http.get<CandidateResponse[]>('/candidates'),
  ]);

  const candidateCounts = new Map<number, number>();
  candidatesResponse.data.forEach(candidate => {
    if (candidate.applied_job_id === null) return;
    candidateCounts.set(
      candidate.applied_job_id,
      (candidateCounts.get(candidate.applied_job_id) || 0) + 1,
    );
  });

  const items = jobsResponse.data.map(job => mapJob(job, candidateCounts.get(job.id) || 0));
  return {
    items,
    total: items.length,
    draftCount: items.filter(item => item.status === 'draft').length,
    openCount: items.filter(item => isOpenJobStatus(item.status)).length,
    closedCount: items.filter(item => isClosedJobStatus(item.status)).length,
    linkedCandidateCount: candidatesResponse.data.filter(candidate => candidate.applied_job_id !== null).length,
  };
};

export const createRecruitmentJob = async (data: RecruitmentJobCreateInput): Promise<RecruitmentJob> => {
  const response = await v2Http.post<JobResponse>('/jobs', data);
  return mapJob(response.data);
};

export const updateRecruitmentJob = async (jobId: number, data: RecruitmentJobInput): Promise<RecruitmentJob> => {
  const response = await v2Http.put<JobResponse>(`/jobs/${jobId}`, data);
  return mapJob(response.data);
};

const runStatusAction = async (jobId: number, action: 'open' | 'close' | 'reopen') => {
  const response = await v2Http.post<JobResponse>(`/jobs/${jobId}/${action}`);
  return mapJob(response.data);
};

export const openRecruitmentJob = (jobId: number) => runStatusAction(jobId, 'open');
export const closeRecruitmentJob = (jobId: number) => runStatusAction(jobId, 'close');
export const reopenRecruitmentJob = (jobId: number) => runStatusAction(jobId, 'reopen');

export const deleteRecruitmentJob = async (jobId: number): Promise<void> => {
  await v2Http.delete(`/jobs/${jobId}`);
};

export const getRecruitmentJobApiError = (error: unknown): RecruitmentJobApiError => {
  if (!axios.isAxiosError(error)) {
    return { status: null, code: null, message: '岗位操作失败，请稍后重试', fields: [], references: null };
  }

  const detail = error.response?.data?.detail;
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) {
    return {
      status: error.response?.status ?? null,
      code: null,
      message: '岗位操作失败，请稍后重试',
      fields: [],
      references: null,
    };
  }

  return {
    status: error.response?.status ?? null,
    code: typeof detail.code === 'string' ? detail.code : null,
    message: typeof detail.message === 'string' ? detail.message : '岗位操作失败，请稍后重试',
    fields: Array.isArray(detail.fields)
      ? detail.fields.filter((field: unknown): field is string => typeof field === 'string')
      : [],
    references: detail.references && typeof detail.references === 'object'
      ? detail.references as Record<string, number>
      : null,
  };
};
