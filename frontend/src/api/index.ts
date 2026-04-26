import axios from 'axios';
import type { BatchOperationResponse, Candidate, CandidateDetail, CandidateFilterOptions, ChatMessage, DailySummary, DashboardStats, FollowUpAlert, InterviewSummaryRequest, InterviewSummaryResponse, Job, PaginatedResponse, RecentLog, ScreeningResult, ScreeningResultsResponse, ScreeningRunResponse, StageChangeLog } from '../types';

const api = axios.create({ baseURL: '/api' });

export const createCandidate = (data: Partial<Candidate>) =>
  api.post<Candidate>('/candidates/', data).then(r => r.data);

export const createHRCandidate = (formData: FormData) =>
  api.post<Candidate>('/candidates/hr-create', formData).then(r => r.data);

export const getCandidates = (params: Record<string, string | number>) =>
  api.get<PaginatedResponse<Candidate>>('/candidates/', { params }).then(r => r.data);

export const getCandidateFilterOptions = () =>
  api.get<CandidateFilterOptions>('/candidates/filter-options').then(r => r.data);

export const getJobs = (status?: string) =>
  api.get<Job[]>('/jobs/', { params: status ? { status } : {} }).then(r => r.data);

export const getActiveJobs = () =>
  api.get<Job[]>('/jobs/active').then(r => r.data);

export const createJob = (data: Partial<Job>) =>
  api.post<Job>('/jobs/', data).then(r => r.data);

export const updateJob = (id: number, data: Partial<Job>) =>
  api.put<Job>(`/jobs/${id}`, data).then(r => r.data);

export const updateJobStatus = (id: number, status: 'active' | 'inactive') =>
  api.patch<Job>(`/jobs/${id}/status`, { status }).then(r => r.data);

export const deleteJob = (id: number) =>
  api.delete<{ message: string; action: string }>(`/jobs/${id}`).then(r => r.data);

export const getCandidate = (id: number) =>
  api.get<CandidateDetail>(`/candidates/${id}`).then(r => r.data);

export const updateCandidate = (id: number, data: Partial<Candidate>) =>
  api.patch<Candidate>(`/candidates/${id}`, data).then(r => r.data);

export const updateStage = (id: number, stage: string) =>
  api.patch<Candidate>(`/candidates/${id}/stage`, { stage }).then(r => r.data);

export const deleteCandidate = (id: number) =>
  api.delete(`/candidates/${id}`).then(r => r.data);

export const batchUpdateStatus = (data: { candidate_ids: number[]; target_stage: string; reason: string; source?: string }) =>
  api.post<BatchOperationResponse>('/candidates/batch/status', data).then(r => r.data);

export const batchGenerateFollowup = (candidateIds: number[]) =>
  api.post<BatchOperationResponse>('/candidates/batch/followup', { candidate_ids: candidateIds }).then(r => r.data);

export const batchExportCandidates = (candidateIds: number[]) =>
  api.post('/candidates/batch/export', { candidate_ids: candidateIds }, { responseType: 'blob' }).then(r => {
    const url = window.URL.createObjectURL(new Blob([r.data], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'selected_candidates.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  });

export const executeHRAction = (id: number, action: string, data?: {
  interview_time?: string;
  interview_method?: string;
  interviewer?: string;
  interview_note?: string;
  recheck_note?: string;
  second_interview_time?: string;
  second_interviewer?: string;
  offer_position?: string;
  salary_range?: string;
  expected_onboard_date?: string;
  offer_note?: string;
  onboard_date?: string;
  onboard_note?: string;
  reject_reason?: string;
  reject_note?: string;
  reason?: string;
}) =>
  api.post<Candidate>(`/candidates/${id}/hr-action/${action}`, data || {}).then(r => r.data);

export const passCandidateScreening = (id: number) =>
  api.post<Candidate>(`/candidates/${id}/screening/pass`).then(r => r.data);

export const markCandidateBackup = (id: number) =>
  api.post<Candidate>(`/candidates/${id}/screening/backup`).then(r => r.data);

export const rejectCandidateScreening = (id: number, data: { reject_reason: string; reject_note?: string }) =>
  api.post<Candidate>(`/candidates/${id}/screening/reject`, data).then(r => r.data);

export const getStageLogs = (id: number) =>
  api.get<StageChangeLog[]>(`/candidates/${id}/stage-logs`).then(r => r.data);

export const runBatchScreening = (params?: Record<string, string>) =>
  api.post<ScreeningRunResponse>('/screening/run', null, { params }).then(r => r.data);

export const runSingleScreening = (id: number) =>
  api.post<ScreeningResult>(`/screening/run/${id}`).then(r => r.data);

export const getScreeningResults = (params?: Record<string, string>) =>
  api.get<ScreeningResultsResponse>('/screening/results', { params }).then(r => r.data);

export const uploadResume = (file: File) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/resume/upload', fd).then(r => r.data);
};

export const parseResumePreview = (file: File) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/resume/parse-preview', fd).then(r => r.data);
};

export const generateSummary = (id: number) =>
  api.post<{ summary: string }>(`/ai/summary/${id}`).then(r => r.data);

export const generateTags = (id: number) =>
  api.post<{ tags: string[] }>(`/ai/tags/${id}`).then(r => r.data);

export const getFollowup = (id: number) =>
  api.post<{
    suggestion: string;
    followup_suggestion: string;
    followup_priority: string;
    followup_reason: string;
    followup_days_since_update: number;
    is_overdue: boolean;
    overdue_days: number;
    overdue_reason: string;
    last_action_at: string | null;
  }>(`/ai/followup/${id}`).then(r => r.data);

export const generateInterviewSummary = (id: number, data: InterviewSummaryRequest) =>
  api.post<InterviewSummaryResponse>(`/ai/interview-summary/${id}`, data).then(r => r.data);

export const chatWithCopilot = (messages: ChatMessage[]) =>
  api.post<{ reply: string }>('/ai/chat', { messages }).then(r => r.data);

export const getDashboardStats = () =>
  api.get<DashboardStats>('/dashboard/stats').then(r => r.data);

export const getFollowUpAlerts = () =>
  api.get<FollowUpAlert[]>('/dashboard/follow-ups').then(r => r.data);

export const getRecentLogs = (limit = 20) =>
  api.get<RecentLog[]>('/dashboard/recent-logs', { params: { limit } }).then(r => r.data);

export const getDailySummary = (date?: string) =>
  api.get<DailySummary>('/dashboard/daily-summary', { params: { target_date: date } }).then(r => r.data);

export const triggerSync = () =>
  api.post('/sync/export').then(r => r.data);

export const downloadCSV = () =>
  api.get('/sync/download-csv', { responseType: 'blob' }).then(r => {
    const url = window.URL.createObjectURL(new Blob([r.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'candidates_export.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  });

export const submitApplication = (formData: FormData) =>
  api.post<{ success: boolean; message: string }>('/apply/', formData).then(r => r.data);
