import { v2Http } from '../../services/http';

type Job = {
  id: number;
  title: string;
  status: string;
};

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

type ScreeningResult = {
  id: number;
  candidate_id: number;
  overall_score: number | null;
  recommendation: string | null;
  updated_at: string;
};

export type RecentCandidate = {
  id: number;
  name: string;
  role: string;
  source: string;
  score: number | null;
  recommendation: string | null;
  updatedAt: string;
};

export type DashboardSnapshot = {
  openJobs: number;
  candidateCount: number;
  pendingScreening: number;
  recentCandidates: RecentCandidate[];
};

export const getStage3DashboardSnapshot = async (): Promise<DashboardSnapshot> => {
  const [jobsResponse, openJobsResponse, candidatesResponse, screeningResultsResponse] = await Promise.all([
    v2Http.get<Job[]>('/jobs'),
    v2Http.get<Job[]>('/jobs', { params: { status: 'open' } }),
    v2Http.get<Candidate[]>('/candidates'),
    v2Http.get<ScreeningResult[]>('/screening-results'),
  ]);

  const jobs = jobsResponse.data;
  const candidates = candidatesResponse.data;
  const screeningResults = screeningResultsResponse.data;
  const jobTitles = new Map(jobs.map(job => [job.id, job.title]));
  const latestScreeningByCandidate = new Map<number, ScreeningResult>();

  screeningResults.forEach(result => {
    const current = latestScreeningByCandidate.get(result.candidate_id);
    if (!current || Date.parse(result.updated_at) > Date.parse(current.updated_at)) {
      latestScreeningByCandidate.set(result.candidate_id, result);
    }
  });

  const recentCandidates = [...candidates]
    .sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at))
    .slice(0, 5)
    .map(candidate => {
      const screening = latestScreeningByCandidate.get(candidate.id);
      return {
        id: candidate.id,
        name: candidate.name,
        role:
          (candidate.applied_job_id ? jobTitles.get(candidate.applied_job_id) : undefined)
          || candidate.current_title
          || '未关联岗位',
        source: candidate.source || '来源未填写',
        score: screening?.overall_score ?? null,
        recommendation: screening?.recommendation ?? null,
        updatedAt: candidate.updated_at || candidate.created_at,
      };
    });

  return {
    openJobs: openJobsResponse.data.filter(job => job.status === 'open').length,
    candidateCount: candidates.length,
    pendingScreening: candidates.filter(candidate => !latestScreeningByCandidate.has(candidate.id)).length,
    recentCandidates,
  };
};
