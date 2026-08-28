export type Stage7ApplicationSource = 'hr_direct' | 'hr_screening' | 'public_apply';
export type Stage7ApplicationLifecycleStatus = 'active' | 'ended' | 'voided';
export type Stage7RecruitmentStage =
  | 'applied'
  | 'hr_review'
  | 'screening_passed'
  | 'backup'
  | 'rejected';
export type Stage7HRDecision = 'pending' | 'passed' | 'backup' | 'rejected';

export type Stage7ApplicationApiResponse = {
  id: number;
  candidate_id: number;
  job_id: number;
  current_resume_id: number;
  source: Stage7ApplicationSource;
  lifecycle_status: Stage7ApplicationLifecycleStatus;
  recruitment_stage: Stage7RecruitmentStage;
  hr_decision: Stage7HRDecision;
  applied_at: string;
  created_at: string;
  updated_at: string;
};

export type Stage7Application = {
  id: number;
  candidateId: number;
  jobId: number;
  currentResumeId: number;
  source: Stage7ApplicationSource;
  lifecycleStatus: Stage7ApplicationLifecycleStatus;
  recruitmentStage: Stage7RecruitmentStage;
  hrDecision: Stage7HRDecision;
  appliedAt: string;
  createdAt: string;
  updatedAt: string;
};

export type Stage7ApplicationFilters = {
  jobId?: number;
  recruitmentStage?: Stage7RecruitmentStage;
  hrDecision?: Stage7HRDecision;
  lifecycleStatus?: Stage7ApplicationLifecycleStatus;
};

export type Stage7ApplicationResumeProfileInput = {
  gender: string | null;
  age: number | null;
  location: string | null;
  current_company: string | null;
  current_title: string | null;
  work_years: number | null;
  education_level: string | null;
  source: string | null;
  skills: string[] | null;
  education_records: Array<{
    school: string | null;
    degree: string | null;
    major: string | null;
    start_date: string | null;
    end_date: string | null;
    is_985: boolean;
    is_211: boolean;
  }>;
  work_experiences: Array<{
    company: string | null;
    title: string | null;
    start_date: string | null;
    end_date: string | null;
    description: string | null;
    tech_stack: string[] | null;
  }>;
  project_experiences: Array<{
    project_name: string | null;
    role: string | null;
    start_date: string | null;
    end_date: string | null;
    description: string | null;
    tech_stack: string[] | null;
    achievements: string | null;
  }>;
};

export type Stage7ApplicationIntakeInput = {
  candidate_id?: number | null;
  name: string;
  phone: string;
  email: string;
  job_id: number;
  current_resume_id: number;
  source: 'hr_direct' | 'hr_screening';
  confirm_hr_pass: boolean;
  resume_profile?: Stage7ApplicationResumeProfileInput | null;
};

export type Stage7ApplicationIntakeApiResponse = {
  application: Stage7ApplicationApiResponse;
  candidate_resolution: 'created' | 'reused';
  existing_application_reused: boolean;
  suspected_duplicate_candidate_ids: number[];
};

export type Stage7ApplicationIntakeOutcome = {
  application: Stage7Application;
  candidateResolution: 'created' | 'reused';
  existingApplicationReused: boolean;
  suspectedDuplicateCandidateIds: number[];
};

export type Stage7PassReasonCode = 'meets_requirements';
export type Stage7BackupReasonCode =
  | 'minor_capability_gap'
  | 'waiting_for_comparison'
  | 'limited_headcount'
  | 'information_pending'
  | 'compensation_pending'
  | 'availability_pending';
export type Stage7RejectReasonCode =
  | 'required_skill_missing'
  | 'work_experience_insufficient'
  | 'education_requirement_not_met'
  | 'required_experience_missing'
  | 'role_mismatch';
export type Stage7DecisionReversalReasonCode =
  | 'new_evidence'
  | 'candidate_information_updated'
  | 'job_requirements_changed'
  | 'decision_correction'
  | 'hr_reassessment';
export type Stage7VoidReasonCode = 'duplicate_entry' | 'wrong_job' | 'entry_error';

export type Stage7PassApplicationInput = {
  reason_code: Stage7PassReasonCode;
  reason_detail?: string | null;
};
export type Stage7BackupApplicationInput = {
  reason_code: Stage7BackupReasonCode;
  reason_detail?: string | null;
};
export type Stage7RejectApplicationInput = {
  reason_code: Stage7RejectReasonCode;
  reason_detail?: string | null;
  confirmed: boolean;
};
export type Stage7ReverseDecisionInput = {
  reason_code: Stage7DecisionReversalReasonCode;
  reason_detail: string;
};
export type Stage7VoidApplicationInput = {
  reason_code: Stage7VoidReasonCode;
  reason_detail?: string | null;
  confirmed: boolean;
};

export type Stage7StageHistoryApiResponse = {
  id: number;
  application_id: number;
  report_id: number | null;
  from_recruitment_stage: Stage7RecruitmentStage | null;
  to_recruitment_stage: Stage7RecruitmentStage;
  from_hr_decision: Stage7HRDecision | null;
  to_hr_decision: Stage7HRDecision;
  reason_code: string;
  reason_detail: string | null;
  actor_type: 'hr' | 'system';
  actor_id: string | null;
  actor_label: string;
  created_at: string;
};

export type Stage7StageHistory = {
  id: number;
  applicationId: number;
  reportId: number | null;
  fromRecruitmentStage: Stage7RecruitmentStage | null;
  toRecruitmentStage: Stage7RecruitmentStage;
  fromHrDecision: Stage7HRDecision | null;
  toHrDecision: Stage7HRDecision;
  reasonCode: string;
  reasonDetail: string | null;
  actorType: 'hr' | 'system';
  actorId: string | null;
  actorLabel: string;
  createdAt: string;
};

export type Stage7ApplicationApiError = {
  status: number | null;
  code: string | null;
  message: string;
  applicationIds: number[];
  candidateIds: number[];
};
