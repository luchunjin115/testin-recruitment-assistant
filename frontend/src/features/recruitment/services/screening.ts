import { v2Http } from '../../../services/http';
import type {
  Stage7Application,
  Stage7ApplicationFilters,
  Stage7ScreeningResultSummary,
  Stage7ScreeningResultSummaryApiResponse,
} from '../types/applicationScreening';
import {
  listStage7Applications,
  mapStage7ScreeningSummary,
} from './applications';
import type { JobStatus } from './jobs';

type JobResponse = {
  id: number;
  title: string;
  department: string | null;
  status: JobStatus;
};

type CandidateResponse = {
  id: number;
  name: string;
  source: string | null;
  status: string;
  applied_job_id: number | null;
  current_title?: string | null;
};

export type Stage7ScreeningCenterJob = {
  id: number;
  title: string;
  department: string | null;
  status: JobStatus;
};

export type Stage7ScreeningCenterItem = {
  application: Stage7Application;
  candidateName: string;
  candidateTitle: string | null;
  candidateSource: string | null;
  jobTitle: string;
  jobDepartment: string | null;
  jobStatus: JobStatus | null;
  currentResult: Stage7ScreeningResultSummary | null;
};

export type Stage7ScreeningCenterSnapshot = {
  jobs: Stage7ScreeningCenterJob[];
  items: Stage7ScreeningCenterItem[];
};

export const getStage7ScreeningCenter = async (
  filters: Stage7ApplicationFilters = {},
): Promise<Stage7ScreeningCenterSnapshot> => {
  const [applications, jobsResponse, candidatesResponse, screeningResultsResponse] = await Promise.all([
    listStage7Applications(filters),
    v2Http.get<JobResponse[]>('/jobs'),
    v2Http.get<CandidateResponse[]>('/candidates'),
    v2Http.get<Stage7ScreeningResultSummaryApiResponse[]>('/screening-results'),
  ]);

  const jobs = new Map(jobsResponse.data.map(job => [job.id, job]));
  const candidates = new Map(candidatesResponse.data.map(candidate => [candidate.id, candidate]));
  const screeningResults = new Map(
    screeningResultsResponse.data
      .map(mapStage7ScreeningSummary)
      .map(result => [result.id, result]),
  );

  return {
    jobs: jobsResponse.data
      .map(job => ({
        id: job.id,
        title: job.title,
        department: job.department,
        status: job.status,
      }))
      .sort((left, right) => left.id - right.id),
    items: applications.map(application => {
      const candidate = candidates.get(application.candidateId);
      const job = jobs.get(application.jobId);
      return {
        application,
        candidateName: candidate?.name || `候选人 #${application.candidateId}`,
        candidateTitle: candidate?.current_title || null,
        candidateSource: candidate?.source || null,
        jobTitle: job?.title || `岗位 #${application.jobId}`,
        jobDepartment: job?.department || null,
        jobStatus: job?.status || null,
        currentResult: application.currentScreeningResultId === null
          ? null
          : screeningResults.get(application.currentScreeningResultId) || null,
      };
    }),
  };
};
