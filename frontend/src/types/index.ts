export interface Candidate {
  id: number;
  name: string;
  phone: string;
  email: string;
  school: string;
  degree: string;
  major: string;
  job_id: number | null;
  target_role: string;
  experience_years: number;
  experience_desc: string;
  skills: string[];
  self_intro: string;
  resume_path: string;
  resume_filename: string;
  resume_file_type: string;
  resume_file_size: number | null;
  resume_url: string;
  resume_uploaded_at: string | null;
  source_channel: string;
  new_candidate_label: string;
  is_today_new: boolean;
  is_recent_3_days_new: boolean;
  stage: string;
  screening_status: 'pending' | 'passed' | 'backup' | 'rejected';
  stage_source: string | null;
  interview_time: string | null;
  interview_method: string;
  interviewer: string;
  interview_note: string;
  interview_feedback_text: string;
  interview_round: string;
  feedback_time: string | null;
  interview_ai_technical_summary: string;
  interview_ai_communication_summary: string;
  interview_ai_job_match: string;
  interview_ai_risk_points: string[];
  interview_ai_recommendation: string;
  interview_ai_next_step: string;
  interview_ai_generated_at: string | null;
  recheck_note: string;
  second_interview_time: string | null;
  second_interviewer: string;
  offer_position: string;
  salary_range: string;
  expected_onboard_date: string | null;
  offer_note: string;
  onboard_date: string | null;
  onboard_note: string;
  reject_reason: string;
  reject_note: string;
  ai_summary: string;
  ai_tags: string[];
  match_score: number | null;
  priority_level: string;
  screening_result: string;
  screening_reason: string;
  risk_flags: string[];
  screening_updated_at: string | null;
  followup_suggestion: string;
  followup_priority: string;
  followup_reason: string;
  followup_days_since_update: number;
  is_overdue: boolean;
  overdue_days: number;
  overdue_reason: string;
  last_action_at: string | null;
  hr_notes: string;
  follow_up_date: string | null;
  is_duplicate: boolean;
  duplicate_of_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateDetail extends Candidate {
  activity_logs: ActivityLog[];
}

export interface ActivityLog {
  id: number;
  candidate_id: number;
  action: string;
  detail: string;
  created_at: string;
}

export interface DashboardStats {
  total_candidates: number;
  new_today: number;
  new_last_3_days: number;
  in_pipeline: number;
  offer_count: number;
  pending_screening_count: number;
  passed_screening_count: number;
  backup_screening_count: number;
  rejected_screening_count: number;
  formal_candidate_count: number;
  funnel: FunnelStage[];
  channels: ChannelDistribution[];
  screening_stats: ScreeningStats;
  followup_summary: FollowupSummary;
  role_distribution: RoleDistributionItem[];
  today_new_candidates: RecentNewCandidateItem[];
}

export interface ScreeningStats {
  total_candidates: number;
  screened_count: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  average_match_score: number;
  unscreened_count: number;
  pending_count: number;
  passed_count: number;
  backup_count: number;
  rejected_count: number;
  formal_candidate_count: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
}

export interface ChannelDistribution {
  channel: string;
  count: number;
}

export interface FollowupSummaryItem {
  candidate_id: number;
  name: string;
  target_role: string;
  stage: string;
  followup_suggestion: string;
  followup_priority: string;
  followup_reason: string;
  followup_days_since_update: number;
  is_overdue: boolean;
  overdue_days: number;
  overdue_reason: string;
  last_action_at: string | null;
}

export interface FollowupSummary {
  high_priority_count: number;
  stale_count: number;
  overdue_count: number;
  today_followup_count: number;
  items: FollowupSummaryItem[];
}

export interface RoleDistributionItem {
  target_role: string;
  count: number;
  high_priority_count: number;
  followup_count: number;
}

export interface RecentNewCandidateItem {
  candidate_id: number;
  name: string;
  target_role: string;
  source_channel: string;
  created_at: string;
  new_candidate_label: string;
}

export interface CandidateFilterOptions {
  target_roles: string[];
  source_channels: string[];
}

export interface Job {
  id: number;
  title: string;
  department: string;
  description: string;
  requirements: string;
  required_skills: string;
  bonus_skills: string;
  education_requirement: string;
  experience_requirement: string;
  job_keywords: string;
  risk_keywords: string;
  status: 'active' | 'inactive';
  candidate_count: number;
  created_at: string;
  updated_at: string;
}

export interface FollowUpAlert {
  candidate_id: number;
  name: string;
  target_role: string;
  stage: string;
  days_since_update: number;
  is_overdue: boolean;
  overdue_days: number;
  overdue_reason: string;
  followup_priority: string;
  followup_suggestion: string;
  last_action_at: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface RecentLog {
  id: number;
  candidate_id: number;
  candidate_name: string;
  action: string;
  detail: string;
  created_at: string;
  updated_at?: string;
  from_stage?: string | null;
  to_stage?: string | null;
  trigger_reason?: string | null;
  trigger_source?: string | null;
}

export interface DailySummary {
  date: string;
  new_count: number;
  stage_changes: number;
  summary_text: string;
}

export interface StageChangeLog {
  id: number;
  candidate_id: number;
  from_stage: string;
  to_stage: string;
  trigger_reason: string;
  trigger_source: string;
  created_at: string;
}

export interface ScreeningResult {
  id: number;
  name: string;
  school: string;
  degree: string;
  major: string;
  target_role: string;
  skills: string[];
  stage: string;
  screening_status: 'pending' | 'passed' | 'backup' | 'rejected';
  match_score: number | null;
  priority_level: string;
  screening_result: string;
  screening_reason: string;
  risk_flags: string[];
  screening_updated_at: string | null;
  created_at: string;
  job_match_summary: string;
  job_requirement_profile: {
    title?: string;
    description?: string;
    requirements?: string;
    required_skills?: string;
    bonus_skills?: string;
    education_requirement?: string;
    experience_requirement?: string;
    job_keywords?: string;
    risk_keywords?: string;
  };
}

export interface ScreeningResultsResponse {
  items: ScreeningResult[];
  total: number;
  stats: ScreeningStats;
  overall_stats: ScreeningStats;
}

export interface ScreeningRunResponse {
  processed_count: number;
  items: ScreeningResult[];
  message?: string;
}

export interface BatchOperationItem {
  candidate_id: number;
  name: string;
  success: boolean;
  message: string;
  from_stage: string | null;
  to_stage: string | null;
}

export interface BatchOperationResponse {
  success_count: number;
  failed_count: number;
  items: BatchOperationItem[];
}

export interface InterviewSummaryRequest {
  interview_feedback_text: string;
  interviewer?: string;
  interview_round?: string;
  feedback_time?: string;
}

export interface InterviewSummaryResponse {
  interview_feedback_text: string;
  interviewer: string;
  interview_round: string;
  feedback_time: string | null;
  technical_summary: string;
  communication_summary: string;
  job_match: string;
  risk_points: string[];
  recommendation: string;
  next_step: string;
  generated_at: string | null;
}
