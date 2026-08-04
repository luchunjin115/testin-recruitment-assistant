import { v2Http } from '../../services/http';

export type EducationRecord = {
  id: number;
  school: string | null;
  degree: string | null;
  major: string | null;
  startDate: string | null;
  endDate: string | null;
  is985: boolean;
  is211: boolean;
};

export type WorkExperience = {
  id: number;
  company: string | null;
  title: string | null;
  startDate: string | null;
  endDate: string | null;
  description: string | null;
  techStack: string[];
};

export type ProjectExperience = {
  id: number;
  projectName: string | null;
  role: string | null;
  startDate: string | null;
  endDate: string | null;
  description: string | null;
  techStack: string[];
  achievements: string | null;
};

type CandidateResponse = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  location: string | null;
  current_company: string | null;
  current_title: string | null;
  work_years: number | null;
  education_level: string | null;
  source: string | null;
  status: string;
  applied_job_id: number | null;
  resume_file_path: string | null;
  resume_text: string | null;
  parsed_data: Record<string, unknown> | null;
  ai_summary: string | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
  education_records: Array<{
    id: number;
    school: string | null;
    degree: string | null;
    major: string | null;
    start_date: string | null;
    end_date: string | null;
    is_985: boolean;
    is_211: boolean;
  }>;
  work_experiences: Array<{
    id: number;
    company: string | null;
    title: string | null;
    start_date: string | null;
    end_date: string | null;
    description: string | null;
    tech_stack: string[] | null;
  }>;
  project_experiences: Array<{
    id: number;
    project_name: string | null;
    role: string | null;
    start_date: string | null;
    end_date: string | null;
    description: string | null;
    tech_stack: string[] | null;
    achievements: string | null;
  }>;
};

type JobResponse = {
  id: number;
  title: string;
};

export type CandidateDetailData = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  location: string | null;
  currentCompany: string | null;
  currentTitle: string | null;
  workYears: number | null;
  educationLevel: string | null;
  source: string | null;
  status: string;
  appliedJobTitle: string;
  hasResume: boolean;
  hasResumeText: boolean;
  hasParsedData: boolean;
  aiSummary: string | null;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  educationRecords: EducationRecord[];
  workExperiences: WorkExperience[];
  projectExperiences: ProjectExperience[];
};

export const getStage3CandidateDetail = async (candidateId: number): Promise<CandidateDetailData> => {
  const [candidateResponse, jobsResponse] = await Promise.all([
    v2Http.get<CandidateResponse>(`/candidates/${candidateId}`),
    v2Http.get<JobResponse[]>('/jobs'),
  ]);

  const candidate = candidateResponse.data;
  const jobTitle = candidate.applied_job_id
    ? jobsResponse.data.find(job => job.id === candidate.applied_job_id)?.title
    : undefined;

  return {
    id: candidate.id,
    name: candidate.name,
    phone: candidate.phone,
    email: candidate.email,
    location: candidate.location,
    currentCompany: candidate.current_company,
    currentTitle: candidate.current_title,
    workYears: candidate.work_years,
    educationLevel: candidate.education_level,
    source: candidate.source,
    status: candidate.status,
    appliedJobTitle: jobTitle || '未关联岗位',
    hasResume: Boolean(candidate.resume_file_path),
    hasResumeText: Boolean(candidate.resume_text),
    hasParsedData: Boolean(candidate.parsed_data),
    aiSummary: candidate.ai_summary,
    tags: candidate.tags || [],
    createdAt: candidate.created_at,
    updatedAt: candidate.updated_at,
    educationRecords: candidate.education_records.map(record => ({
      id: record.id,
      school: record.school,
      degree: record.degree,
      major: record.major,
      startDate: record.start_date,
      endDate: record.end_date,
      is985: record.is_985,
      is211: record.is_211,
    })),
    workExperiences: candidate.work_experiences.map(experience => ({
      id: experience.id,
      company: experience.company,
      title: experience.title,
      startDate: experience.start_date,
      endDate: experience.end_date,
      description: experience.description,
      techStack: experience.tech_stack || [],
    })),
    projectExperiences: candidate.project_experiences.map(project => ({
      id: project.id,
      projectName: project.project_name,
      role: project.role,
      startDate: project.start_date,
      endDate: project.end_date,
      description: project.description,
      techStack: project.tech_stack || [],
      achievements: project.achievements,
    })),
  };
};
