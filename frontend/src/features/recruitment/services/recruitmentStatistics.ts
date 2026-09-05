import axios from 'axios';
import { v2Http } from '../../../services/http';

export type RecruitmentFunnelKey = 'applications' | 'screening_passed' | 'interview_entered' | 'interview_completed' | 'offer_sent' | 'offer_accepted' | 'admitted' | 'hired';
export type RecruitmentDurationKey = 'application_to_screening_passed' | 'screening_passed_to_first_interview' | 'first_interview_to_last_completed' | 'offer_entered_to_sent' | 'offer_sent_to_response' | 'offer_accepted_to_admitted' | 'admitted_to_hired';

type RecruitmentStatisticsResponse = {
  cohort: { job_id: number | null; applied_from: string | null; applied_to: string | null };
  funnel: Array<{ key: RecruitmentFunnelKey; count: number; conversion_rate: number | null }>;
  durations: Array<{ key: RecruitmentDurationKey; average_hours: number | null; sample_count: number }>;
  todos: {
    scheduled_interviews: number;
    pending_interview_decisions: number;
    next_round_not_scheduled: number;
    draft_offers: number;
    sent_offers: number;
    accepted_offers: number;
    admitted_applications: number;
    total: number;
  };
  generated_at: string;
};

export type RecruitmentStatistics = {
  cohort: { jobId: number | null; appliedFrom: string | null; appliedTo: string | null };
  funnel: Array<{ key: RecruitmentFunnelKey; count: number; conversionRate: number | null }>;
  durations: Array<{ key: RecruitmentDurationKey; averageHours: number | null; sampleCount: number }>;
  todos: {
    scheduledInterviews: number;
    pendingInterviewDecisions: number;
    nextRoundNotScheduled: number;
    draftOffers: number;
    sentOffers: number;
    acceptedOffers: number;
    admittedApplications: number;
    total: number;
  };
  generatedAt: string;
};

export type RecruitmentStatisticsFilters = {
  jobId?: number;
  appliedFrom?: string;
  appliedTo?: string;
};

export const getRecruitmentStatistics = async (
  filters: RecruitmentStatisticsFilters = {},
): Promise<RecruitmentStatistics> => {
  const response = await v2Http.get<RecruitmentStatisticsResponse>('/recruitment-statistics', {
    params: {
      job_id: filters.jobId,
      applied_from: filters.appliedFrom,
      applied_to: filters.appliedTo,
    },
  });
  return {
    cohort: {
      jobId: response.data.cohort.job_id,
      appliedFrom: response.data.cohort.applied_from,
      appliedTo: response.data.cohort.applied_to,
    },
    funnel: response.data.funnel.map(item => ({
      key: item.key,
      count: item.count,
      conversionRate: item.conversion_rate,
    })),
    durations: response.data.durations.map(item => ({
      key: item.key,
      averageHours: item.average_hours,
      sampleCount: item.sample_count,
    })),
    todos: {
      scheduledInterviews: response.data.todos.scheduled_interviews,
      pendingInterviewDecisions: response.data.todos.pending_interview_decisions,
      nextRoundNotScheduled: response.data.todos.next_round_not_scheduled,
      draftOffers: response.data.todos.draft_offers,
      sentOffers: response.data.todos.sent_offers,
      acceptedOffers: response.data.todos.accepted_offers,
      admittedApplications: response.data.todos.admitted_applications,
      total: response.data.todos.total,
    },
    generatedAt: response.data.generated_at,
  };
};

export const getRecruitmentStatisticsError = (error: unknown): string => {
  if (!axios.isAxiosError(error)) return '招聘流程统计读取失败，请稍后重试';
  const detail = error.response?.data?.detail;
  return detail && typeof detail === 'object' && typeof detail.message === 'string'
    ? detail.message
    : '招聘流程统计读取失败，请稍后重试';
};
