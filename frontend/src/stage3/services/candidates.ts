import { v2Http } from '../../services/http';

export type CandidateListItem = {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  currentCompany: string | null;
  currentTitle: string | null;
  workYears: number | null;
  educationLevel: string | null;
  source: string | null;
  status: string;
  appliedJobId: number | null;
  appliedJobTitle: string;
  hasResume: boolean;
  updatedAt: string;
};

export type CandidateJobOption = {
  id: number;
  title: string;
};

type CandidateResponse = {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  current_company: string | null;
  current_title: string | null;
  work_years: number | null;
  education_level: string | null;
  source: string | null;
  status: string;
  applied_job_id: number | null;
  resume_file_path: string | null;
  created_at: string;
  updated_at: string;
};

type JobResponse = {
  id: number;
  title: string;
};

export type CandidateListSnapshot = {
  items: CandidateListItem[];
  jobs: CandidateJobOption[];
  total: number;
  newCount: number;
  linkedJobCount: number;
  withResumeCount: number;
};

export const getStage3Candidates = async (): Promise<CandidateListSnapshot> => {
  const [candidatesResponse, jobsResponse] = await Promise.all([
    v2Http.get<CandidateResponse[]>('/candidates'),
    v2Http.get<JobResponse[]>('/jobs'),
  ]);

  const jobs = jobsResponse.data.map(job => ({ id: job.id, title: job.title }));
  const jobTitles = new Map(jobs.map(job => [job.id, job.title]));
  const items = [...candidatesResponse.data]
    .sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at))
    .map(candidate => ({
      id: candidate.id,
      name: candidate.name,
      email: candidate.email,
      phone: candidate.phone,
      currentCompany: candidate.current_company,
      currentTitle: candidate.current_title,
      workYears: candidate.work_years,
      educationLevel: candidate.education_level,
      source: candidate.source,
      status: candidate.status,
      appliedJobId: candidate.applied_job_id,
      appliedJobTitle:
        (candidate.applied_job_id ? jobTitles.get(candidate.applied_job_id) : undefined)
        || '未关联岗位',
      hasResume: Boolean(candidate.resume_file_path),
      updatedAt: candidate.updated_at || candidate.created_at,
    }));

  return {
    items,
    jobs,
    total: items.length,
    newCount: items.filter(item => item.status.toLowerCase() === 'new').length,
    linkedJobCount: items.filter(item => item.appliedJobId !== null).length,
    withResumeCount: items.filter(item => item.hasResume).length,
  };
};
