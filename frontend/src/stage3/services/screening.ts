import { v2Http } from '../../services/http';

type JobResponse = {
  id: number;
  title: string;
  department: string | null;
  status: string;
};

type CandidateResponse = {
  id: number;
  name: string;
  source: string | null;
  status: string;
  applied_job_id: number | null;
};

type ScreeningResultResponse = {
  id: number;
  candidate_id: number;
  job_id: number;
  overall_score: number | null;
  hard_pass: boolean | null;
  skill_score: number | null;
  experience_score: number | null;
  project_score: number | null;
  strengths: string[] | null;
  risks: string[] | null;
  recommendation: string | null;
  reason: string | null;
  raw_result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type Stage3ScreeningJob = {
  id: number;
  title: string;
  department: string | null;
  status: string;
  candidateCount: number;
  resultCount: number;
};

export type Stage3ScreeningResult = {
  id: number;
  candidateId: number;
  candidateName: string;
  candidateSource: string | null;
  candidateStatus: string | null;
  jobId: number;
  jobTitle: string;
  overallScore: number | null;
  hardPass: boolean | null;
  skillScore: number | null;
  experienceScore: number | null;
  projectScore: number | null;
  strengths: string[];
  risks: string[];
  recommendation: string | null;
  reason: string | null;
  priorityLevel: string | null;
  screeningStatus: string | null;
  source: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ScreeningCenterSnapshot = {
  jobs: Stage3ScreeningJob[];
  items: Stage3ScreeningResult[];
  totalCandidates: number;
  totalResults: number;
};

const asString = (value: unknown): string | null => {
  if (typeof value !== 'string') return null;
  const normalized = value.trim();
  return normalized || null;
};

export const getStage3ScreeningCenter = async (): Promise<ScreeningCenterSnapshot> => {
  const [jobsResponse, candidatesResponse, screeningResultsResponse] = await Promise.all([
    v2Http.get<JobResponse[]>('/jobs'),
    v2Http.get<CandidateResponse[]>('/candidates'),
    v2Http.get<ScreeningResultResponse[]>('/screening-results'),
  ]);

  const candidates = new Map(candidatesResponse.data.map(candidate => [candidate.id, candidate]));
  const jobs = new Map(jobsResponse.data.map(job => [job.id, job]));
  const candidateCounts = new Map<number, number>();
  const resultCounts = new Map<number, number>();

  candidatesResponse.data.forEach(candidate => {
    if (candidate.applied_job_id === null) return;
    candidateCounts.set(
      candidate.applied_job_id,
      (candidateCounts.get(candidate.applied_job_id) || 0) + 1,
    );
  });

  screeningResultsResponse.data.forEach(result => {
    resultCounts.set(result.job_id, (resultCounts.get(result.job_id) || 0) + 1);
  });

  const items = screeningResultsResponse.data
    .map(result => {
      const candidate = candidates.get(result.candidate_id);
      const job = jobs.get(result.job_id);
      return {
        id: result.id,
        candidateId: result.candidate_id,
        candidateName: candidate?.name || `候选人 #${result.candidate_id}`,
        candidateSource: candidate?.source || null,
        candidateStatus: candidate?.status || null,
        jobId: result.job_id,
        jobTitle: job?.title || `岗位 #${result.job_id}`,
        overallScore: result.overall_score,
        hardPass: result.hard_pass,
        skillScore: result.skill_score,
        experienceScore: result.experience_score,
        projectScore: result.project_score,
        strengths: result.strengths || [],
        risks: result.risks || [],
        recommendation: result.recommendation,
        reason: result.reason,
        priorityLevel: asString(result.raw_result?.priority_level),
        screeningStatus: asString(result.raw_result?.screening_status),
        source: asString(result.raw_result?.source),
        createdAt: result.created_at,
        updatedAt: result.updated_at,
      };
    })
    .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));

  return {
    jobs: jobsResponse.data.map(job => ({
      id: job.id,
      title: job.title,
      department: job.department,
      status: job.status,
      candidateCount: candidateCounts.get(job.id) || 0,
      resultCount: resultCounts.get(job.id) || 0,
    })),
    items,
    totalCandidates: candidatesResponse.data.length,
    totalResults: items.length,
  };
};
