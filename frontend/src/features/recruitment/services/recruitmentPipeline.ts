import { v2Http } from '../../../services/http';

export type InterviewListItem = {
  id: number;
  roundNumber: number;
  interviewType: string;
  status: string;
  scheduledStartAt: string;
  durationMinutes: number;
  timezone: string;
  interviewerNames: string[];
  decision: string;
  version: number;
};

type InterviewResponse = {
  id: number;
  round_number: number;
  interview_type: string;
  status: string;
  scheduled_start_at: string;
  duration_minutes: number;
  timezone: string;
  interviewer_names: string[];
  decision: string;
  version: number;
};

export type TimelineItem = {
  sourceId: number;
  eventType: string;
  reasonCode: string;
  reasonDetail: string | null;
  actorLabel: string;
  occurredAt: string;
};

type TimelineResponse = {
  source_id: number;
  event_type: string;
  reason_code: string;
  reason_detail: string | null;
  actor_label: string;
  occurred_at: string;
};

export const listApplicationInterviews = async (applicationId: number): Promise<InterviewListItem[]> => {
  const response = await v2Http.get<InterviewResponse[]>(`/applications/${applicationId}/interviews`);
  return response.data.map(item => ({
    id: item.id,
    roundNumber: item.round_number,
    interviewType: item.interview_type,
    status: item.status,
    scheduledStartAt: item.scheduled_start_at,
    durationMinutes: item.duration_minutes,
    timezone: item.timezone,
    interviewerNames: item.interviewer_names,
    decision: item.decision,
    version: item.version,
  }));
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
