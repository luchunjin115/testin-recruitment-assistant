import { v2Http } from '../../services/http';

type JobResponse = {
  id: number;
  title: string;
  department: string | null;
  description: string | null;
  requirements: Record<string, unknown> | null;
  status: string;
  created_at: string;
  updated_at: string;
};

type CandidateResponse = {
  id: number;
  applied_job_id: number | null;
};

export type Stage3Job = {
  id: number;
  title: string;
  department: string | null;
  description: string | null;
  status: string;
  requirementSummary: string | null;
  requiredSkills: string[];
  candidateCount: number;
  createdAt: string;
  updatedAt: string;
};

export type JobListSnapshot = {
  items: Stage3Job[];
  total: number;
  openCount: number;
  closedCount: number;
  linkedCandidateCount: number;
};

const asString = (value: unknown): string | null => {
  if (typeof value !== 'string') return null;
  const normalized = value.trim();
  return normalized || null;
};

const asStringList = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is string => typeof item === 'string')
    .map(item => item.trim())
    .filter(Boolean);
};

export const isOpenJobStatus = (status: string) => ['open', 'active'].includes(status.toLowerCase());

export const isClosedJobStatus = (status: string) => ['closed', 'inactive'].includes(status.toLowerCase());

export const getStage3Jobs = async (): Promise<JobListSnapshot> => {
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

  const items = jobsResponse.data.map(job => ({
    id: job.id,
    title: job.title,
    department: job.department,
    description: job.description,
    status: job.status,
    requirementSummary: asString(job.requirements?.summary),
    requiredSkills: asStringList(job.requirements?.required_skills),
    candidateCount: candidateCounts.get(job.id) || 0,
    createdAt: job.created_at,
    updatedAt: job.updated_at,
  }));

  return {
    items,
    total: items.length,
    openCount: items.filter(item => isOpenJobStatus(item.status)).length,
    closedCount: items.filter(item => isClosedJobStatus(item.status)).length,
    linkedCandidateCount: candidatesResponse.data.filter(candidate => candidate.applied_job_id !== null).length,
  };
};
