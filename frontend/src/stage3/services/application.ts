import { v2Http } from '../../services/http';
import type { JobRequirementsV1, JobStatus } from './jobs';

type JobResponse = {
  id: number;
  title: string;
  department: string | null;
  description: string | null;
  requirements: JobRequirementsV1;
  status: JobStatus;
  created_at: string;
  updated_at: string;
};

export type Stage3ApplicationJob = {
  id: number;
  title: string;
  department: string | null;
  description: string | null;
  requirementSummary: string | null;
  requiredSkills: string[];
  status: JobStatus;
};

export const getStage3ApplicationJobs = async (): Promise<Stage3ApplicationJob[]> => {
  const response = await v2Http.get<JobResponse[]>('/jobs', { params: { status: 'open' } });

  return response.data
    .filter(job => job.status === 'open')
    .map(job => ({
      id: job.id,
      title: job.title,
      department: job.department,
      description: job.description,
      requirementSummary: job.requirements.responsibilities[0] || null,
      requiredSkills: job.requirements.required_skills,
      status: job.status,
    }))
    .sort((left, right) => left.id - right.id);
};
