import { v2Http } from '../../../services/http';
import type { JobStatus } from './jobs';

type JobResponse = {
  id: number;
  title: string;
  department: string | null;
  job_background: string | null;
  job_responsibilities: string | null;
  candidate_requirements: string | null;
  preferred_qualifications: string | null;
  public_notes: string | null;
  status: JobStatus;
  created_at: string;
  updated_at: string;
};

export type RecruitmentApplicationJob = {
  id: number;
  title: string;
  department: string | null;
  jobBackground: string | null;
  jobResponsibilities: string | null;
  candidateRequirements: string | null;
  preferredQualifications: string | null;
  publicNotes: string | null;
  status: JobStatus;
};

export const getRecruitmentApplicationJobs = async (): Promise<RecruitmentApplicationJob[]> => {
  const response = await v2Http.get<JobResponse[]>('/jobs', { params: { status: 'open' } });

  return response.data
    .filter(job => job.status === 'open')
    .map(job => ({
      id: job.id,
      title: job.title,
      department: job.department,
      jobBackground: job.job_background,
      jobResponsibilities: job.job_responsibilities,
      candidateRequirements: job.candidate_requirements,
      preferredQualifications: job.preferred_qualifications,
      publicNotes: job.public_notes,
      status: job.status,
    }))
    .sort((left, right) => left.id - right.id);
};
