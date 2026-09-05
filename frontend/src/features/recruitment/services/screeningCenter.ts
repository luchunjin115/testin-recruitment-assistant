import axios from 'axios';
import { v2Http } from '../../../services/http';

export type ScreeningCenterSource = 'hr_direct' | 'hr_screening' | 'public_apply';
export type ScreeningCenterLifecycle = 'active' | 'ended' | 'voided';
export type ScreeningCenterStage = 'applied' | 'hr_review' | 'screening_passed' | 'backup' | 'rejected' | 'interview' | 'offer' | 'offer_accepted' | 'admitted' | 'hired';
export type ScreeningCenterDecision = 'pending' | 'passed' | 'backup' | 'rejected';
export type ScreeningCenterFinalOutcome = 'screening_rejected' | 'interview_rejected' | 'interview_no_show' | 'offer_declined' | 'offer_withdrawn' | 'offer_expired' | 'candidate_withdrew' | 'company_canceled' | 'hired';
export type ScreeningCenterReportStatus = 'not_started' | 'waiting_resume' | 'waiting_plan' | 'queued' | 'running' | 'ready' | 'failed' | 'paused' | 'outdated' | 'old_report_retained';
export type ScreeningCenterAllowedAction = 'view_detail' | 'start_screening' | 'reassess_screening' | 'pass' | 'backup' | 'reject' | 'undo_rejection' | 'schedule_interview' | 'create_offer' | 'edit_offer' | 'send_offer' | 'accept_offer' | 'decline_offer' | 'withdraw_offer' | 'expire_offer' | 'confirm_admission' | 'confirm_hire' | 'withdraw_application' | 'cancel_process' | 'reopen_stage9';
export type ScreeningCenterSort = 'applied_desc' | 'updated_desc' | 'score_desc' | 'score_asc';
export type ScreeningCenterProcessingPool = 'all' | 'internal' | 'normal' | 'exception';
export type ScreeningCenterView = 'screening' | 'candidate' | 'all';

type AbilityTagResponse = {
  criterion_id: string;
  label: string;
  score: number;
  importance: 'required' | 'preferred' | 'general';
  evidence_count: number;
  is_outdated: boolean;
};

type ScreeningCenterItemResponse = {
  application_id: number;
  candidate_id: number;
  job_id: number;
  resume_id: number;
  candidate_name: string;
  masked_phone: string | null;
  current_company: string | null;
  current_title: string | null;
  work_years: number | null;
  education_level: string | null;
  job_title: string;
  job_status: 'draft' | 'open' | 'closed';
  source: ScreeningCenterSource;
  submission_id: number | null;
  submission_reference: string | null;
  lifecycle_status: ScreeningCenterLifecycle;
  recruitment_stage: ScreeningCenterStage;
  hr_decision: ScreeningCenterDecision;
  final_outcome: ScreeningCenterFinalOutcome | null;
  processing_pool: 'internal' | 'normal' | 'exception';
  processing_status: string | null;
  processing_step: string | null;
  processing_warning_codes: string[];
  screening_status: ScreeningCenterReportStatus;
  screening_run_status: string | null;
  screening_waiting_reason: string | null;
  screening_error_message: string | null;
  score: number | null;
  display_label: string | null;
  report_id: number | null;
  report_is_outdated: boolean;
  ability_tags: AbilityTagResponse[];
  overall_summary: string | null;
  strengths: string[];
  gaps_or_risks: string[];
  applied_at: string;
  business_updated_at: string;
  allowed_actions: ScreeningCenterAllowedAction[];
};

type ScreeningCenterPageResponse = {
  items: ScreeningCenterItemResponse[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type ScreeningCenterAbilityTag = {
  criterionId: string;
  label: string;
  score: number;
  importance: 'required' | 'preferred' | 'general';
  evidenceCount: number;
  isOutdated: boolean;
};

export type ScreeningCenterItem = {
  applicationId: number;
  candidateId: number;
  jobId: number;
  resumeId: number;
  candidateName: string;
  maskedPhone: string | null;
  currentCompany: string | null;
  currentTitle: string | null;
  workYears: number | null;
  educationLevel: string | null;
  jobTitle: string;
  jobStatus: 'draft' | 'open' | 'closed';
  source: ScreeningCenterSource;
  submissionId: number | null;
  submissionReference: string | null;
  lifecycleStatus: ScreeningCenterLifecycle;
  recruitmentStage: ScreeningCenterStage;
  hrDecision: ScreeningCenterDecision;
  finalOutcome: ScreeningCenterFinalOutcome | null;
  processingPool: 'internal' | 'normal' | 'exception';
  processingStatus: string | null;
  processingStep: string | null;
  processingWarningCodes: string[];
  screeningStatus: ScreeningCenterReportStatus;
  screeningRunStatus: string | null;
  screeningWaitingReason: string | null;
  screeningErrorMessage: string | null;
  score: number | null;
  displayLabel: string | null;
  reportId: number | null;
  reportIsOutdated: boolean;
  abilityTags: ScreeningCenterAbilityTag[];
  overallSummary: string | null;
  strengths: string[];
  gapsOrRisks: string[];
  appliedAt: string;
  businessUpdatedAt: string;
  allowedActions: ScreeningCenterAllowedAction[];
};

export type ScreeningCenterPage = {
  items: ScreeningCenterItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
};

export type ScreeningCenterFilters = {
  page?: number;
  pageSize?: number;
  view?: ScreeningCenterView;
  keyword?: string;
  applicationId?: number;
  jobId?: number;
  source?: ScreeningCenterSource;
  hrDecision?: ScreeningCenterDecision;
  stage?: ScreeningCenterStage;
  lifecycle?: ScreeningCenterLifecycle;
  finalOutcome?: ScreeningCenterFinalOutcome;
  processingPool?: ScreeningCenterProcessingPool;
  processingStatus?: string;
  displayLabel?: string;
  scoreMin?: number;
  scoreMax?: number;
  appliedFrom?: string;
  appliedTo?: string;
  sort?: ScreeningCenterSort;
};

const mapItem = (value: ScreeningCenterItemResponse): ScreeningCenterItem => ({
  applicationId: value.application_id,
  candidateId: value.candidate_id,
  jobId: value.job_id,
  resumeId: value.resume_id,
  candidateName: value.candidate_name,
  maskedPhone: value.masked_phone,
  currentCompany: value.current_company,
  currentTitle: value.current_title,
  workYears: value.work_years,
  educationLevel: value.education_level,
  jobTitle: value.job_title,
  jobStatus: value.job_status,
  source: value.source,
  submissionId: value.submission_id,
  submissionReference: value.submission_reference,
  lifecycleStatus: value.lifecycle_status,
  recruitmentStage: value.recruitment_stage,
  hrDecision: value.hr_decision,
  finalOutcome: value.final_outcome,
  processingPool: value.processing_pool,
  processingStatus: value.processing_status,
  processingStep: value.processing_step,
  processingWarningCodes: value.processing_warning_codes,
  screeningStatus: value.screening_status,
  screeningRunStatus: value.screening_run_status,
  screeningWaitingReason: value.screening_waiting_reason,
  screeningErrorMessage: value.screening_error_message,
  score: value.score,
  displayLabel: value.display_label,
  reportId: value.report_id,
  reportIsOutdated: value.report_is_outdated,
  abilityTags: value.ability_tags.map(tag => ({
    criterionId: tag.criterion_id,
    label: tag.label,
    score: tag.score,
    importance: tag.importance,
    evidenceCount: tag.evidence_count,
    isOutdated: tag.is_outdated,
  })),
  overallSummary: value.overall_summary,
  strengths: value.strengths,
  gapsOrRisks: value.gaps_or_risks,
  appliedAt: value.applied_at,
  businessUpdatedAt: value.business_updated_at,
  allowedActions: value.allowed_actions,
});

export const listScreeningCenterApplications = async (
  filters: ScreeningCenterFilters = {},
): Promise<ScreeningCenterPage> => {
  const response = await v2Http.get<ScreeningCenterPageResponse>('/screening-center/applications', {
    params: {
      page: filters.page,
      page_size: filters.pageSize,
      view: filters.view,
      keyword: filters.keyword,
      application_id: filters.applicationId,
      job_id: filters.jobId,
      source: filters.source,
      hr_decision: filters.hrDecision,
      stage: filters.stage,
      lifecycle: filters.lifecycle,
      final_outcome: filters.finalOutcome,
      processing_pool: filters.processingPool,
      processing_status: filters.processingStatus,
      display_label: filters.displayLabel,
      score_min: filters.scoreMin,
      score_max: filters.scoreMax,
      applied_from: filters.appliedFrom,
      applied_to: filters.appliedTo,
      sort: filters.sort,
    },
  });
  return {
    items: response.data.items.map(mapItem),
    page: response.data.page,
    pageSize: response.data.page_size,
    total: response.data.total,
    totalPages: response.data.total_pages,
  };
};

export const getScreeningCenterError = (error: unknown) => {
  if (!axios.isAxiosError(error)) return 'AI 初筛中心读取失败，请稍后重试';
  const detail = error.response?.data?.detail;
  return detail && typeof detail === 'object' && typeof detail.message === 'string'
    ? detail.message
    : 'AI 初筛中心读取失败，请稍后重试';
};
