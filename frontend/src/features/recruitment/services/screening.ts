import { v2Http } from '../../../services/http';
import type { Stage7Application, Stage7ApplicationFilters } from '../types/applicationScreening';
import { listStage7Applications } from './applications';
import type { JobStatus } from './jobs';
import type { ScreeningState } from '../types/aiScreening';
import { getAIScreeningApiError, getApplicationScreening } from './aiScreening';
import {
  listPublicApplicationSubmissions,
  type PublicApplicationWorkbenchSummary,
} from './publicApplicationWorkbench';

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

export type Stage7ScreeningCenterJob = JobResponse;

export type Stage7ScreeningCenterItem = {
  application: Stage7Application;
  candidateName: string;
  candidateTitle: string | null;
  candidateSource: string | null;
  jobTitle: string;
  jobDepartment: string | null;
  jobStatus: JobStatus | null;
  screeningState: ScreeningState | null;
  screeningLoadError: string | null;
  publicSubmission: PublicApplicationWorkbenchSummary | null;
};

export type Stage7ScreeningCenterSnapshot = {
  jobs: Stage7ScreeningCenterJob[];
  items: Stage7ScreeningCenterItem[];
};

export const getStage7ScreeningCenter = async (
  filters: Stage7ApplicationFilters = {},
): Promise<Stage7ScreeningCenterSnapshot> => {
  const [applications, jobsResponse, candidatesResponse, publicSubmissions] = await Promise.all([
    listStage7Applications(filters),
    v2Http.get<JobResponse[]>('/jobs'),
    v2Http.get<CandidateResponse[]>('/candidates'),
    listPublicApplicationSubmissions(),
  ]);
  const jobs = new Map(jobsResponse.data.map(job => [job.id, job]));
  const candidates = new Map(candidatesResponse.data.map(candidate => [candidate.id, candidate]));
  const submissions = new Map(publicSubmissions.map(item => [item.applicationId, item]));

  const items = await Promise.all(applications.map(async application => {
    const candidate = candidates.get(application.candidateId);
    const job = jobs.get(application.jobId);
    let screeningState: ScreeningState | null = null;
    let screeningLoadError: string | null = null;
    try {
      screeningState = await getApplicationScreening(application.id);
    } catch (error) {
      screeningLoadError = getAIScreeningApiError(error).message;
    }
    return {
      application,
      candidateName: candidate?.name || `候选人 #${application.candidateId}`,
      candidateTitle: candidate?.current_title || null,
      candidateSource: candidate?.source || null,
      jobTitle: job?.title || `岗位 #${application.jobId}`,
      jobDepartment: job?.department || null,
      jobStatus: job?.status || null,
      screeningState,
      screeningLoadError,
      publicSubmission: submissions.get(application.id) ?? null,
    };
  }));

  return {
    jobs: [...jobsResponse.data].sort((left, right) => left.id - right.id),
    items,
  };
};
