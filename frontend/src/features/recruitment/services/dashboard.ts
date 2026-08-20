import { v2Http } from '../../../services/http';
import { listStage7Applications } from './applications';

type Job = { id: number; title: string; status: string };
type Candidate = {
  id: number;
  name: string;
  source: string | null;
  status: string;
  applied_job_id: number | null;
  current_title: string | null;
  created_at: string;
  updated_at: string;
};

export type RecentCandidate = {
  id: number;
  name: string;
  role: string;
  source: string;
  updatedAt: string;
};

export type DashboardSnapshot = {
  openJobs: number;
  candidateCount: number;
  pendingReview: number;
  recentCandidates: RecentCandidate[];
};

export const getRecruitmentDashboardSnapshot = async (): Promise<DashboardSnapshot> => {
  const [jobsResponse, openJobsResponse, candidatesResponse, applications] = await Promise.all([
    v2Http.get<Job[]>('/jobs'),
    v2Http.get<Job[]>('/jobs', { params: { status: 'open' } }),
    v2Http.get<Candidate[]>('/candidates'),
    listStage7Applications({ hrDecision: 'pending', lifecycleStatus: 'active' }),
  ]);
  const jobTitles = new Map(jobsResponse.data.map(job => [job.id, job.title]));
  const recentCandidates = [...candidatesResponse.data]
    .sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at))
    .slice(0, 5)
    .map(candidate => ({
      id: candidate.id,
      name: candidate.name,
      role: (candidate.applied_job_id ? jobTitles.get(candidate.applied_job_id) : undefined)
        || candidate.current_title
        || '未关联岗位',
      source: candidate.source || '来源未填写',
      updatedAt: candidate.updated_at || candidate.created_at,
    }));

  return {
    openJobs: openJobsResponse.data.filter(job => job.status === 'open').length,
    candidateCount: candidatesResponse.data.length,
    pendingReview: applications.length,
    recentCandidates,
  };
};
