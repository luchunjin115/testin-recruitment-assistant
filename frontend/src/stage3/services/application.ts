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

export type Stage3ApplicationJob = {
  id: number;
  title: string;
  department: string | null;
  description: string | null;
  requirementSummary: string | null;
  requiredSkills: string[];
  status: string;
};

const isOpenJob = (status: string) => ['open', 'active'].includes(status.toLowerCase());

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

export const getStage3ApplicationJobs = async (): Promise<Stage3ApplicationJob[]> => {
  const response = await v2Http.get<JobResponse[]>('/jobs');

  return response.data
    .filter(job => isOpenJob(job.status))
    .map(job => ({
      id: job.id,
      title: job.title,
      department: job.department,
      description: job.description,
      requirementSummary: asString(job.requirements?.summary),
      requiredSkills: asStringList(job.requirements?.required_skills),
      status: job.status,
    }))
    .sort((left, right) => left.id - right.id);
};
