import axios from 'axios';
import { v2Http } from '../../../services/http';

export type InterviewListItem = {
  id: number;
  applicationId: number;
  roundNumber: number;
  interviewType: 'onsite' | 'video' | 'phone';
  status: 'scheduled' | 'completed' | 'canceled' | 'no_show';
  scheduledStartAt: string;
  durationMinutes: number;
  timezone: string;
  interviewerNames: string[];
  location: string | null;
  decision: 'pending' | 'next_round' | 'proceed_offer' | 'rejected' | 'candidate_withdrew';
  feedbackSummary: string | null;
  strengths: string[];
  concerns: string[];
  followUpQuestions: string[];
  feedbackSubmittedByLabel: string | null;
  feedbackSubmittedAt: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
};

export type InterviewRecord = InterviewListItem & {
  meetingLink: string | null;
  scheduleNote: string | null;
};

type InterviewListResponse = {
  id: number;
  application_id: number;
  round_number: number;
  interview_type: 'onsite' | 'video' | 'phone';
  status: 'scheduled' | 'completed' | 'canceled' | 'no_show';
  scheduled_start_at: string;
  duration_minutes: number;
  timezone: string;
  interviewer_names: string[];
  location: string | null;
  decision: 'pending' | 'next_round' | 'proceed_offer' | 'rejected' | 'candidate_withdrew';
  feedback_summary: string | null;
  strengths: string[];
  concerns: string[];
  follow_up_questions: string[];
  feedback_submitted_by_label: string | null;
  feedback_submitted_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

type InterviewDetailResponse = InterviewListResponse & {
  meeting_link: string | null;
  schedule_note: string | null;
};

export type InterviewScheduleInput = {
  round_number: number;
  interview_type: 'onsite' | 'video' | 'phone';
  scheduled_start_at: string;
  duration_minutes: number;
  timezone: string;
  interviewer_names: string[];
  location: string | null;
  meeting_link: string | null;
  schedule_note: string | null;
};

export type InterviewFeedbackInput = {
  expected_version: number;
  feedback_summary: string;
  strengths: string[];
  concerns: string[];
  follow_up_questions: string[];
  decision: 'pending' | 'next_round' | 'proceed_offer' | 'rejected' | 'candidate_withdrew';
  reason_code: 'interview_round_completed' | 'interview_next_round' | 'interview_proceed_offer' | 'interview_rejected' | 'candidate_withdrew';
  reason_detail: string | null;
  confirmed: boolean;
};

export type TimelineItem = {
  sourceId: number;
  eventType: string;
  reasonCode: string;
  reasonDetail: string | null;
  actorLabel: string;
  occurredAt: string;
};

export type OfferStatus = 'draft' | 'sent' | 'accepted' | 'declined' | 'withdrawn' | 'expired';
export type SalaryPeriod = 'monthly' | 'annual';

export type OfferRecord = {
  id: number;
  applicationId: number;
  versionNumber: number;
  status: OfferStatus;
  positionTitle: string;
  currency: string;
  salaryPeriod: SalaryPeriod;
  baseSalaryAmount: string;
  salaryMonths: string | null;
  bonusNote: string | null;
  benefitsNote: string | null;
  validUntil: string;
  expectedStartDate: string;
  note: string | null;
  sentAt: string | null;
  respondedAt: string | null;
  closedAt: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
};

type OfferResponse = {
  id: number;
  application_id: number;
  version_number: number;
  status: OfferStatus;
  position_title: string;
  currency: string;
  salary_period: SalaryPeriod;
  base_salary_amount: string;
  salary_months: string | null;
  bonus_note: string | null;
  benefits_note: string | null;
  valid_until: string;
  expected_start_date: string;
  note: string | null;
  sent_at: string | null;
  responded_at: string | null;
  closed_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type OfferDetailsInput = {
  position_title: string;
  currency: string;
  salary_period: SalaryPeriod;
  base_salary_amount: string;
  salary_months: string | null;
  bonus_note: string | null;
  benefits_note: string | null;
  valid_until: string;
  expected_start_date: string;
  note: string | null;
};

export type ApplicationPipelineResult = {
  id: number;
  lifecycle_status: 'active' | 'ended' | 'voided';
  recruitment_stage: string;
  hr_decision: string;
  final_outcome: string | null;
};

const mapInterview = (item: InterviewListResponse): InterviewListItem => ({
  id: item.id,
  applicationId: item.application_id,
  roundNumber: item.round_number,
  interviewType: item.interview_type,
  status: item.status,
  scheduledStartAt: item.scheduled_start_at,
  durationMinutes: item.duration_minutes,
  timezone: item.timezone,
  interviewerNames: item.interviewer_names,
  location: item.location,
  decision: item.decision,
  feedbackSummary: item.feedback_summary,
  strengths: item.strengths,
  concerns: item.concerns,
  followUpQuestions: item.follow_up_questions,
  feedbackSubmittedByLabel: item.feedback_submitted_by_label,
  feedbackSubmittedAt: item.feedback_submitted_at,
  version: item.version,
  createdAt: item.created_at,
  updatedAt: item.updated_at,
});

type ConfirmedActionInput = {
  expected_version?: number | null;
  reason_code: string;
  reason_detail: string;
  confirmed: true;
};

const mapOffer = (item: OfferResponse): OfferRecord => ({
  id: item.id,
  applicationId: item.application_id,
  versionNumber: item.version_number,
  status: item.status,
  positionTitle: item.position_title,
  currency: item.currency,
  salaryPeriod: item.salary_period,
  baseSalaryAmount: item.base_salary_amount,
  salaryMonths: item.salary_months,
  bonusNote: item.bonus_note,
  benefitsNote: item.benefits_note,
  validUntil: item.valid_until,
  expectedStartDate: item.expected_start_date,
  note: item.note,
  sentAt: item.sent_at,
  respondedAt: item.responded_at,
  closedAt: item.closed_at,
  version: item.version,
  createdAt: item.created_at,
  updatedAt: item.updated_at,
});

type TimelineResponse = {
  source_id: number;
  event_type: string;
  reason_code: string;
  reason_detail: string | null;
  actor_label: string;
  occurred_at: string;
};

export const listApplicationInterviews = async (applicationId: number): Promise<InterviewListItem[]> => {
  const response = await v2Http.get<InterviewListResponse[]>(`/applications/${applicationId}/interviews`);
  return response.data.map(mapInterview);
};

export const getApplicationInterview = async (interviewId: number): Promise<InterviewRecord> => {
  const response = await v2Http.get<InterviewDetailResponse>(`/interviews/${interviewId}`);
  return {
    ...mapInterview(response.data),
    meetingLink: response.data.meeting_link,
    scheduleNote: response.data.schedule_note,
  };
};

export const scheduleApplicationInterview = async (
  applicationId: number,
  input: InterviewScheduleInput,
): Promise<InterviewRecord> => {
  const response = await v2Http.post<InterviewDetailResponse>(`/applications/${applicationId}/interviews`, input);
  return { ...mapInterview(response.data), meetingLink: response.data.meeting_link, scheduleNote: response.data.schedule_note };
};

export const rescheduleApplicationInterview = async (
  interviewId: number,
  input: Omit<InterviewScheduleInput, 'round_number'> & { expected_version: number; reason_detail: string | null },
): Promise<InterviewRecord> => {
  const response = await v2Http.put<InterviewDetailResponse>(`/interviews/${interviewId}/schedule`, input);
  return { ...mapInterview(response.data), meetingLink: response.data.meeting_link, scheduleNote: response.data.schedule_note };
};

export const cancelApplicationInterview = async (interviewId: number, expectedVersion: number, reasonDetail: string) => {
  const response = await v2Http.post<InterviewDetailResponse>(`/interviews/${interviewId}/cancel`, {
    expected_version: expectedVersion, reason_code: 'interview_canceled', reason_detail: reasonDetail, confirmed: true,
  });
  return { ...mapInterview(response.data), meetingLink: response.data.meeting_link, scheduleNote: response.data.schedule_note };
};

export const markApplicationInterviewNoShow = async (
  interviewId: number,
  expectedVersion: number,
  reasonDetail: string,
  endApplication: boolean,
) => {
  const response = await v2Http.post<InterviewDetailResponse>(`/interviews/${interviewId}/no-show`, {
    expected_version: expectedVersion, reason_code: 'interview_no_show', reason_detail: reasonDetail,
    confirmed: true, end_application: endApplication,
  });
  return { ...mapInterview(response.data), meetingLink: response.data.meeting_link, scheduleNote: response.data.schedule_note };
};

export const submitApplicationInterviewFeedback = async (interviewId: number, input: InterviewFeedbackInput) => {
  const response = await v2Http.post<InterviewDetailResponse>(`/interviews/${interviewId}/feedback`, input);
  return { ...mapInterview(response.data), meetingLink: response.data.meeting_link, scheduleNote: response.data.schedule_note };
};

export const updateApplicationInterviewFeedback = async (
  interviewId: number,
  input: Omit<InterviewFeedbackInput, 'reason_code' | 'reason_detail'> & { correction_reason: string },
) => {
  const response = await v2Http.put<InterviewDetailResponse>(`/interviews/${interviewId}/feedback`, {
    ...input, reason_code: 'stage9_correction', confirmed: true,
  });
  return { ...mapInterview(response.data), meetingLink: response.data.meeting_link, scheduleNote: response.data.schedule_note };
};

export const listApplicationTimeline = async (applicationId: number): Promise<TimelineItem[]> => {
  const response = await v2Http.get<TimelineResponse[]>(`/applications/${applicationId}/timeline`);
  return response.data.map(item => ({
    sourceId: item.source_id,
    eventType: item.event_type,
    reasonCode: item.reason_code,
    reasonDetail: item.reason_detail,
    actorLabel: item.actor_label,
    occurredAt: item.occurred_at,
  }));
};

export const listApplicationOffers = async (applicationId: number): Promise<OfferRecord[]> => {
  const response = await v2Http.get<OfferResponse[]>(`/applications/${applicationId}/offers`);
  return response.data.map(mapOffer);
};

export const createApplicationOffer = async (
  applicationId: number,
  input: OfferDetailsInput,
): Promise<OfferRecord> => {
  const response = await v2Http.post<OfferResponse>(`/applications/${applicationId}/offers`, input);
  return mapOffer(response.data);
};

export const updateApplicationOffer = async (
  offerId: number,
  input: OfferDetailsInput & { expected_version: number; confirmed: boolean; correction_reason: string | null },
): Promise<OfferRecord> => {
  const response = await v2Http.put<OfferResponse>(`/offers/${offerId}`, input);
  return mapOffer(response.data);
};

const actOnOffer = async (offerId: number, action: string, input: ConfirmedActionInput) => {
  const response = await v2Http.post<OfferResponse>(`/offers/${offerId}/${action}`, input);
  return mapOffer(response.data);
};

export const sendApplicationOffer = (offerId: number, input: ConfirmedActionInput) => actOnOffer(offerId, 'send', input);
export const acceptApplicationOffer = (offerId: number, input: ConfirmedActionInput) => actOnOffer(offerId, 'accept', input);
export const declineApplicationOffer = (offerId: number, input: ConfirmedActionInput) => actOnOffer(offerId, 'decline', input);
export const withdrawApplicationOffer = (offerId: number, input: ConfirmedActionInput) => actOnOffer(offerId, 'withdraw', input);
export const expireApplicationOffer = (offerId: number, input: ConfirmedActionInput) => actOnOffer(offerId, 'expire', input);

const actOnApplication = async (applicationId: number, action: string, input: ConfirmedActionInput) => {
  const response = await v2Http.post<ApplicationPipelineResult>(`/applications/${applicationId}/${action}`, input);
  return response.data;
};

export const confirmApplicationAdmission = (applicationId: number, input: ConfirmedActionInput) => actOnApplication(applicationId, 'confirm-admission', input);
export const confirmApplicationHire = (applicationId: number, input: ConfirmedActionInput) => actOnApplication(applicationId, 'confirm-hire', input);
export const withdrawApplication = (applicationId: number, input: ConfirmedActionInput) => actOnApplication(applicationId, 'withdraw', input);
export const cancelApplicationProcess = (applicationId: number, input: ConfirmedActionInput) => actOnApplication(applicationId, 'cancel-process', input);
export const reopenStage9Application = (applicationId: number, input: ConfirmedActionInput) => actOnApplication(applicationId, 'reopen-stage9', input);

export const getRecruitmentPipelineError = (error: unknown): string => {
  if (!axios.isAxiosError(error)) return '招聘流程操作失败，请刷新后重试';
  const detail = error.response?.data?.detail;
  return detail && typeof detail === 'object' && typeof detail.message === 'string'
    ? detail.message
    : '招聘流程操作失败，请刷新后重试';
};
