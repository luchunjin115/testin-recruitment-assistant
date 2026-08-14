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

export type Stage3CandidateCreateInput = {
  name: string;
  phone?: string;
  email?: string;
  gender?: string;
  age?: number;
  location?: string;
  currentCompany?: string;
  currentTitle?: string;
  workYears?: number;
  educationLevel?: string;
  tags?: string[];
  source?: string;
  appliedJobId?: number;
  educationRecords?: Stage3EducationInput[];
  workExperiences?: Stage3WorkExperienceInput[];
  projectExperiences?: Stage3ProjectExperienceInput[];
};

export type Stage3EducationInput = {
  aiCandidateKey?: string;
  school?: string;
  degree?: string;
  major?: string;
  startDate?: string;
  endDate?: string;
  is985?: boolean;
  is211?: boolean;
};

export type Stage3WorkExperienceInput = {
  aiCandidateKey?: string;
  company?: string;
  title?: string;
  startDate?: string;
  endDate?: string;
  description?: string;
  techStack?: string;
};

export type Stage3ProjectExperienceInput = {
  aiCandidateKey?: string;
  projectName?: string;
  role?: string;
  startDate?: string;
  endDate?: string;
  description?: string;
  techStack?: string;
  achievements?: string;
};

export type Stage3CandidateCreated = {
  id: number;
  name: string;
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

const cleanText = (value?: string) => value?.trim() || null;

const splitKeywords = (value?: string) => {
  const items = value
    ?.split(/[,，、;；\n]+/)
    .map(item => item.trim())
    .filter(Boolean);
  return items?.length ? Array.from(new Set(items)) : null;
};

const cleanKeywordList = (values?: string[]) => {
  const items = values?.map(value => value.trim()).filter(Boolean);
  return items?.length ? Array.from(new Set(items)) : null;
};

const buildCandidatePayload = (input: Stage3CandidateCreateInput) => {
  const educationRecords = (input.educationRecords || []).filter(record => (
    Boolean(
      record.school?.trim()
      || record.degree?.trim()
      || record.major?.trim()
      || record.startDate?.trim()
      || record.endDate?.trim()
      || record.is985
      || record.is211,
    )
  ));
  const workExperiences = (input.workExperiences || []).filter(record => (
    Boolean(
      record.company?.trim()
      || record.title?.trim()
      || record.startDate?.trim()
      || record.endDate?.trim()
      || record.description?.trim()
      || record.techStack?.trim(),
    )
  ));
  const projectExperiences = (input.projectExperiences || []).filter(record => (
    Boolean(
      record.projectName?.trim()
      || record.role?.trim()
      || record.startDate?.trim()
      || record.endDate?.trim()
      || record.description?.trim()
      || record.techStack?.trim()
      || record.achievements?.trim(),
    )
  ));

  return {
    name: input.name.trim(),
    phone: cleanText(input.phone),
    email: cleanText(input.email),
    gender: cleanText(input.gender),
    age: input.age ?? null,
    location: cleanText(input.location),
    current_company: cleanText(input.currentCompany),
    current_title: cleanText(input.currentTitle),
    work_years: input.workYears ?? null,
    education_level: cleanText(input.educationLevel),
    tags: cleanKeywordList(input.tags),
    source: cleanText(input.source) || 'HR手动录入',
    status: 'new',
    applied_job_id: input.appliedJobId ?? null,
    education_records: educationRecords.map(record => ({
      school: cleanText(record.school),
      degree: cleanText(record.degree),
      major: cleanText(record.major),
      start_date: cleanText(record.startDate),
      end_date: cleanText(record.endDate),
      is_985: Boolean(record.is985),
      is_211: Boolean(record.is211),
    })),
    work_experiences: workExperiences.map(record => ({
      company: cleanText(record.company),
      title: cleanText(record.title),
      start_date: cleanText(record.startDate),
      end_date: cleanText(record.endDate),
      description: cleanText(record.description),
      tech_stack: splitKeywords(record.techStack),
    })),
    project_experiences: projectExperiences.map(record => ({
      project_name: cleanText(record.projectName),
      role: cleanText(record.role),
      start_date: cleanText(record.startDate),
      end_date: cleanText(record.endDate),
      description: cleanText(record.description),
      tech_stack: splitKeywords(record.techStack),
      achievements: cleanText(record.achievements),
    })),
  };
};

export const createStage3Candidate = async (
  input: Stage3CandidateCreateInput,
): Promise<Stage3CandidateCreated> => {
  const response = await v2Http.post<CandidateResponse>(
    '/candidates',
    buildCandidatePayload(input),
  );

  return {
    id: response.data.id,
    name: response.data.name,
  };
};

export const createStage3CandidateFromResume = async (
  resumeId: number,
  input: Stage3CandidateCreateInput,
): Promise<Stage3CandidateCreated> => {
  const response = await v2Http.post<CandidateResponse>('/candidates/from-resume', {
    resume_id: resumeId,
    candidate: buildCandidatePayload(input),
  });

  return {
    id: response.data.id,
    name: response.data.name,
  };
};

export const getStage3CandidateJobs = async (): Promise<CandidateJobOption[]> => {
  const response = await v2Http.get<JobResponse[]>('/jobs');
  return response.data.map(job => ({ id: job.id, title: job.title }));
};
