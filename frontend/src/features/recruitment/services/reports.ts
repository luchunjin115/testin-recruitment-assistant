import { v2Http } from '../../../services/http';

type ReportResponse = {
  id: number;
  candidate_id: number;
  job_id: number;
  title: string | null;
  content: string;
  report_type: string;
  format: string;
  report_metadata: Record<string, unknown> | null;
  generated_at: string;
  updated_at: string;
};

type CandidateResponse = { id: number; name: string; source: string | null };
type JobResponse = { id: number; title: string; department: string | null };

export type RecruitmentReportJob = { id: number; title: string; reportCount: number };
export type RecruitmentReport = {
  id: number;
  candidateId: number;
  candidateName: string;
  candidateSource: string | null;
  jobId: number;
  jobTitle: string;
  title: string;
  content: string;
  reportType: string;
  format: string;
  metadata: Record<string, unknown> | null;
  generatedAt: string;
  updatedAt: string;
};
export type ReportCenterSnapshot = {
  items: RecruitmentReport[];
  jobs: RecruitmentReportJob[];
  totalReports: number;
  totalCandidates: number;
  totalJobs: number;
};

export const getRecruitmentReports = async (): Promise<ReportCenterSnapshot> => {
  const [reportsResponse, candidatesResponse, jobsResponse] = await Promise.all([
    v2Http.get<ReportResponse[]>('/reports'),
    v2Http.get<CandidateResponse[]>('/candidates'),
    v2Http.get<JobResponse[]>('/jobs'),
  ]);
  const candidates = new Map(candidatesResponse.data.map(candidate => [candidate.id, candidate]));
  const jobs = new Map(jobsResponse.data.map(job => [job.id, job]));
  const reportCounts = new Map<number, number>();
  reportsResponse.data.forEach(report => {
    reportCounts.set(report.job_id, (reportCounts.get(report.job_id) || 0) + 1);
  });
  const items = reportsResponse.data.map(report => ({
    id: report.id,
    candidateId: report.candidate_id,
    candidateName: candidates.get(report.candidate_id)?.name || `候选人 #${report.candidate_id}`,
    candidateSource: candidates.get(report.candidate_id)?.source || null,
    jobId: report.job_id,
    jobTitle: jobs.get(report.job_id)?.title || `岗位 #${report.job_id}`,
    title: report.title?.trim() || `未命名报告 #${report.id}`,
    content: report.content,
    reportType: report.report_type,
    format: report.format,
    metadata: report.report_metadata,
    generatedAt: report.generated_at,
    updatedAt: report.updated_at,
  })).sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));

  return {
    items,
    jobs: jobsResponse.data.map(job => ({
      id: job.id,
      title: job.title,
      reportCount: reportCounts.get(job.id) || 0,
    })),
    totalReports: items.length,
    totalCandidates: candidatesResponse.data.length,
    totalJobs: jobsResponse.data.length,
  };
};
