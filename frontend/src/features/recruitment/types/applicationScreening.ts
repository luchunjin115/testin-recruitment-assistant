export type Stage7ApplicationSource =
  | 'hr_direct'
  | 'hr_screening'
  | 'public_apply';

export type Stage7ApplicationLifecycleStatus = 'active' | 'ended' | 'voided';
export type Stage7RecruitmentStage =
  | 'applied'
  | 'hr_review'
  | 'screening_passed'
  | 'backup'
  | 'rejected';
export type Stage7ApplicationAIStatus =
  | 'not_started'
  | 'screening'
  | 'completed'
  | 'failed'
  | 'blocked';
export type Stage7HRDecision = 'pending' | 'passed' | 'backup' | 'rejected';
export type Stage7ScreeningExecutionStatus = 'screening' | 'completed' | 'failed' | 'blocked';
export type Stage7ScreeningBatchItemStatus =
  | 'completed'
  | 'failed'
  | 'blocked'
  | 'reused'
  | 'skipped';

export type Stage7ApplicationApiResponse = {
  id: number;
  candidate_id: number;
  job_id: number;
  current_resume_id: number;
  source: Stage7ApplicationSource;
  lifecycle_status: Stage7ApplicationLifecycleStatus;
  recruitment_stage: Stage7RecruitmentStage;
  ai_status: Stage7ApplicationAIStatus;
  hr_decision: Stage7HRDecision;
  current_screening_result_id: number | null;
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
  aiStatus: Stage7ApplicationAIStatus;
  hrDecision: Stage7HRDecision;
  currentScreeningResultId: number | null;
  appliedAt: string;
  createdAt: string;
  updatedAt: string;
};

export type Stage7ApplicationFilters = {
  jobId?: number;
  recruitmentStage?: Stage7RecruitmentStage;
  aiStatus?: Stage7ApplicationAIStatus;
  hrDecision?: Stage7HRDecision;
  lifecycleStatus?: Stage7ApplicationLifecycleStatus;
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

export type Stage7ScreeningResultSummaryApiResponse = {
  id: number;
  candidate_id: number;
  job_id: number;
  application_id: number;
  resume_id: number;
  attempt_number: number;
  execution_status: Stage7ScreeningExecutionStatus;
  overall_score: number | null;
  hard_pass: boolean | null;
  recommendation: string | null;
  evidence_coverage_rate: string | number | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  trigger_reason: string | null;
  force_rerun: boolean;
  is_outdated: boolean;
  outdated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Stage7ScreeningResultSummary = {
  id: number;
  candidateId: number;
  jobId: number;
  applicationId: number;
  resumeId: number;
  attemptNumber: number;
  executionStatus: Stage7ScreeningExecutionStatus;
  overallScore: number | null;
  hardPass: boolean | null;
  recommendation: string | null;
  evidenceCoverageRate: number | null;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  triggerReason: string | null;
  forceRerun: boolean;
  isOutdated: boolean;
  outdatedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type Stage7ScreeningResultDetailApiResponse = Stage7ScreeningResultSummaryApiResponse & {
  input_fingerprint: string | null;
  skill_score: number | null;
  experience_score: number | null;
  project_score: number | null;
  strengths: string[] | null;
  risks: string[] | null;
  hard_requirement_checks: unknown[] | null;
  dimension_scores: Record<string, unknown> | null;
  reason: string | null;
  pending_questions: string[] | null;
  resume_evidence: unknown[] | null;
  job_evidence: unknown[] | null;
  candidate_input_snapshot: Record<string, unknown> | null;
  resume_snapshot: Record<string, unknown> | null;
  job_requirements_snapshot: Record<string, unknown> | null;
  rubric_snapshot: Record<string, unknown> | null;
  rules_version: string | null;
  prompt_version: string | null;
  model_provider: string | null;
  model_name: string | null;
  model_config_version: string | null;
  job_schema_version: string | null;
  resume_schema_version: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  estimated_cost: string | number | null;
  actor_type: string | null;
  actor_id: string | null;
  actor_label: string | null;
  raw_result: Record<string, unknown> | null;
};

export type Stage7ScreeningResultDetail = Stage7ScreeningResultSummary & {
  inputFingerprint: string | null;
  skillScore: number | null;
  experienceScore: number | null;
  projectScore: number | null;
  strengths: string[];
  risks: string[];
  hardRequirementChecks: unknown[];
  dimensionScores: Record<string, unknown>;
  reason: string | null;
  pendingQuestions: string[];
  resumeEvidence: unknown[];
  jobEvidence: unknown[];
  candidateInputSnapshot: Record<string, unknown> | null;
  resumeSnapshot: Record<string, unknown> | null;
  jobRequirementsSnapshot: Record<string, unknown> | null;
  rubricSnapshot: Record<string, unknown> | null;
  rulesVersion: string | null;
  promptVersion: string | null;
  modelProvider: string | null;
  modelName: string | null;
  modelConfigVersion: string | null;
  jobSchemaVersion: string | null;
  resumeSchemaVersion: string | null;
  promptTokens: number | null;
  completionTokens: number | null;
  totalTokens: number | null;
  estimatedCost: number | null;
  actorType: string | null;
  actorId: string | null;
  actorLabel: string | null;
  rawResult: Record<string, unknown> | null;
};

export type Stage7ScreeningRunInput = {
  force?: boolean;
  confirm_force?: boolean;
  reason?: string | null;
};

export type Stage7ScreeningRunApiResponse = {
  result: Stage7ScreeningResultDetailApiResponse;
  reused: boolean;
  model_called: boolean;
};

export type Stage7ScreeningRunOutcome = {
  result: Stage7ScreeningResultDetail;
  reused: boolean;
  modelCalled: boolean;
};

export type Stage7ScreeningBatchInput = Stage7ScreeningRunInput & {
  application_ids: number[];
  retry_failed_only?: boolean;
};

export type Stage7ScreeningBatchApiResponse = {
  job_id: number;
  items: Array<{
    application_id: number;
    status: Stage7ScreeningBatchItemStatus;
    screening_result_id: number | null;
    attempt_number: number | null;
    reused: boolean;
    model_called: boolean;
    error_code: string | null;
    error_message: string | null;
  }>;
  summary: {
    selected: number;
    executed: number;
    completed: number;
    failed: number;
    blocked: number;
    reused: number;
    skipped: number;
  };
};

export type Stage7ScreeningBatchOutcome = {
  jobId: number;
  items: Array<{
    applicationId: number;
    status: Stage7ScreeningBatchItemStatus;
    screeningResultId: number | null;
    attemptNumber: number | null;
    reused: boolean;
    modelCalled: boolean;
    errorCode: string | null;
    errorMessage: string | null;
  }>;
  summary: Stage7ScreeningBatchApiResponse['summary'];
};

export type Stage7PassReasonCode = 'meets_requirements' | 'manual_override';
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
  from_recruitment_stage: Stage7RecruitmentStage | null;
  to_recruitment_stage: Stage7RecruitmentStage;
  from_hr_decision: Stage7HRDecision | null;
  to_hr_decision: Stage7HRDecision;
  reason_code: string;
  reason_detail: string | null;
  actor_type: 'hr' | 'system';
  actor_id: string | null;
  actor_label: string;
  screening_result_id: number | null;
  overrides_ai_recommendation: boolean;
  created_at: string;
};

export type Stage7StageHistory = {
  id: number;
  applicationId: number;
  fromRecruitmentStage: Stage7RecruitmentStage | null;
  toRecruitmentStage: Stage7RecruitmentStage;
  fromHrDecision: Stage7HRDecision | null;
  toHrDecision: Stage7HRDecision;
  reasonCode: string;
  reasonDetail: string | null;
  actorType: 'hr' | 'system';
  actorId: string | null;
  actorLabel: string;
  screeningResultId: number | null;
  overridesAiRecommendation: boolean;
  createdAt: string;
};

export type Stage7ApplicationApiError = {
  status: number | null;
  code: string | null;
  message: string;
  applicationIds: number[];
  candidateIds: number[];
};
