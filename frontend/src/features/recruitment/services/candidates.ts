import { v2Http } from '../../../services/http';
import type {
  Stage7ApplicationSource,
  Stage7HRDecision,
  Stage7RecruitmentStage,
} from '../types/applicationScreening';
import {
  intakeStage7Application,
  listStage7Applications,
} from './applications';
import type { JobStatus } from './jobs';

export type CandidateListItem = {
  applicationId: number;
  candidateId: number;
  name: string;
  email: string | null;
  phone: string | null;
  currentCompany: string | null;
  currentTitle: string | null;
  candidateSource: string | null;
  jobId: number;
  jobTitle: string;
  jobDepartment: string | null;
  applicationSource: Stage7ApplicationSource;
  recruitmentStage: Stage7RecruitmentStage;
  hrDecision: Stage7HRDecision;
  updatedAt: string;
};

export type CandidateJobOption = {
  id: number;
  title: string;
};

export type RecruitmentCandidateCreateInput = {
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
  educationRecords?: RecruitmentEducationInput[];
  workExperiences?: RecruitmentWorkExperienceInput[];
  projectExperiences?: RecruitmentProjectExperienceInput[];
  confirmHrPass?: boolean;
};

export type RecruitmentEducationInput = {
  aiCandidateKey?: string;
  school?: string;
  degree?: string;
  major?: string;
  startDate?: string;
  endDate?: string;
  is985?: boolean;
  is211?: boolean;
};

export type RecruitmentWorkExperienceInput = {
  aiCandidateKey?: string;
  company?: string;
  title?: string;
  startDate?: string;
  endDate?: string;
  description?: string;
  techStack?: string;
};

export type RecruitmentProjectExperienceInput = {
  aiCandidateKey?: string;
  projectName?: string;
  role?: string;
  startDate?: string;
  endDate?: string;
  description?: string;
  techStack?: string;
  achievements?: string;
};

export type RecruitmentCandidateCreated = {
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
  department: string | null;
  status: JobStatus;
};

export type RecruitmentHrDirectOutcome = {
  applicationId: number;
  candidateId: number;
  candidateResolution: 'created' | 'reused';
  existingApplicationReused: boolean;
  suspectedDuplicateCandidateIds: number[];
};

export type CandidateListSnapshot = {
  items: CandidateListItem[];
  jobs: CandidateJobOption[];
  total: number;
  uniqueCandidateCount: number;
  linkedJobCount: number;
  needsAttentionCount: number;
};

export const getRecruitmentCandidates = async (): Promise<CandidateListSnapshot> => {
  const [applications, candidatesResponse, jobsResponse] = await Promise.all([
    listStage7Applications({ hrDecision: 'passed' }),
    v2Http.get<CandidateResponse[]>('/candidates'),
    v2Http.get<JobResponse[]>('/jobs'),
  ]);

  const candidates = new Map(candidatesResponse.data.map(candidate => [candidate.id, candidate]));
  const jobRecords = new Map(jobsResponse.data.map(job => [job.id, job]));
  const items = applications
    .map(application => {
      const candidate = candidates.get(application.candidateId);
      const job = jobRecords.get(application.jobId);
      return {
        applicationId: application.id,
        candidateId: application.candidateId,
        name: candidate?.name || `候选人 #${application.candidateId}`,
        email: candidate?.email || null,
        phone: candidate?.phone || null,
        currentCompany: candidate?.current_company || null,
        currentTitle: candidate?.current_title || null,
        candidateSource: candidate?.source || null,
        jobId: application.jobId,
        jobTitle: job?.title || `岗位 #${application.jobId}`,
        jobDepartment: job?.department || null,
        applicationSource: application.source,
        recruitmentStage: application.recruitmentStage,
        hrDecision: application.hrDecision,
        updatedAt: application.updatedAt,
      };
    })
    .sort((left, right) => (
      Date.parse(right.updatedAt) - Date.parse(left.updatedAt)
      || right.applicationId - left.applicationId
    ));
  const visibleJobIds = new Set(items.map(item => item.jobId));
  const jobs = jobsResponse.data
    .filter(job => visibleJobIds.has(job.id))
    .map(job => ({ id: job.id, title: job.title }))
    .sort((left, right) => left.id - right.id);

  return {
    items,
    jobs,
    total: items.length,
    uniqueCandidateCount: new Set(items.map(item => item.candidateId)).size,
    linkedJobCount: visibleJobIds.size,
    needsAttentionCount: items.filter(item => !item.email || !item.phone).length,
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

export const buildRecruitmentCandidatePayload = (input: RecruitmentCandidateCreateInput) => {
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

export const createRecruitmentCandidate = async (
  input: RecruitmentCandidateCreateInput,
): Promise<RecruitmentCandidateCreated> => {
  const response = await v2Http.post<CandidateResponse>(
    '/candidates',
    buildRecruitmentCandidatePayload(input),
  );

  return {
    id: response.data.id,
    name: response.data.name,
  };
};

export const createRecruitmentCandidateFromResume = async (
  resumeId: number,
  input: RecruitmentCandidateCreateInput,
): Promise<RecruitmentCandidateCreated> => {
  const response = await v2Http.post<CandidateResponse>('/candidates/from-resume', {
    resume_id: resumeId,
    candidate: buildRecruitmentCandidatePayload(input),
  });

  return {
    id: response.data.id,
    name: response.data.name,
  };
};

export const createRecruitmentHrDirectApplication = async (
  resumeId: number,
  input: RecruitmentCandidateCreateInput,
): Promise<RecruitmentHrDirectOutcome> => {
  const candidate = buildRecruitmentCandidatePayload(input);
  if (!candidate.phone || !candidate.email || !candidate.applied_job_id) {
    throw new Error('HR 人工直通必须填写手机号、邮箱并选择开放岗位');
  }

  const intake = await intakeStage7Application({
    name: candidate.name,
    phone: candidate.phone,
    email: candidate.email,
    job_id: candidate.applied_job_id,
    current_resume_id: resumeId,
    source: 'hr_direct',
    confirm_hr_pass: true,
    resume_profile: {
      gender: candidate.gender,
      age: candidate.age,
      location: candidate.location,
      current_company: candidate.current_company,
      current_title: candidate.current_title,
      work_years: candidate.work_years,
      education_level: candidate.education_level,
      source: candidate.source,
      skills: candidate.tags,
      education_records: candidate.education_records,
      work_experiences: candidate.work_experiences,
      project_experiences: candidate.project_experiences,
    },
  });

  return {
    applicationId: intake.application.id,
    candidateId: intake.application.candidateId,
    candidateResolution: intake.candidateResolution,
    existingApplicationReused: intake.existingApplicationReused,
    suspectedDuplicateCandidateIds: intake.suspectedDuplicateCandidateIds,
  };
};

export const getRecruitmentCandidateJobs = async (): Promise<CandidateJobOption[]> => {
  const response = await v2Http.get<JobResponse[]>('/jobs', { params: { status: 'open' } });
  return response.data
    .filter(job => job.status === 'open')
    .map(job => ({ id: job.id, title: job.title }));
};
