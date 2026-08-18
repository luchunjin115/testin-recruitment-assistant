export type ResumeStructureStatus = 'succeeded' | 'failed';

export type ResumeBasicInfoDraft = {
  name: string | null;
  phone: string | null;
  email: string | null;
  gender: string | null;
  age: number | null;
  location: string | null;
  current_company: string | null;
  current_title: string | null;
  work_years: number | null;
  education_level: string | null;
};

export type ResumeEducationDraft = {
  school: string | null;
  degree: string | null;
  major: string | null;
  start_date: string | null;
  end_date: string | null;
};

export type ResumeWorkExperienceDraft = {
  company: string | null;
  title: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
  tech_stack: string[];
};

export type ResumeProjectExperienceDraft = {
  project_name: string | null;
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
  tech_stack: string[];
  achievements: string | null;
};

export type ResumeParseDraft = {
  schema_version: '1.0';
  basic_info: ResumeBasicInfoDraft;
  education_records: ResumeEducationDraft[];
  work_experiences: ResumeWorkExperienceDraft[];
  project_experiences: ResumeProjectExperienceDraft[];
  skills: string[];
  certifications: string[];
  self_evaluation: string | null;
  warnings: string[];
  missing_fields: string[];
};

export type ResumeStructureRequest = {
  force: boolean;
};

export type ResumeStructurePerformance = {
  total_ms: number;
  preparation_ms: number;
  model_ms: number;
  validation_ms: number;
  persistence_ms: number;
};

export type ResumeStructureResponse = {
  resume_id: number;
  structure_status: ResumeStructureStatus;
  structure_error: string | null;
  from_cache: boolean;
  has_previous_draft: boolean;
  draft: ResumeParseDraft;
  performance: ResumeStructurePerformance | null;
};

export type ResumeStructureFailureWithDraft = ResumeStructureResponse & {
  detail: string;
};

export type ResumeStructureErrorDetail = string | ResumeStructureFailureWithDraft;

export type ResumeStructureErrorResponse = {
  detail: ResumeStructureErrorDetail;
};
