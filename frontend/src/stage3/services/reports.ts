import { v2Http } from '../../services/http';

type ReportResponse = {
  id: number;
  candidate_id: number;
  job_id: number;
  screening_id: number | null;
  title: string | null;
  content: string;
  report_type: string;
  format: string;
  report_metadata: Record<string, unknown> | null;
  generated_at: string;
  updated_at: string;
};

type CandidateResponse = {
  id: number;
  name: string;
  source: string | null;
};

type JobResponse = {
  id: number;
  title: string;
  department: string | null;
};

type ScreeningResultResponse = {
  id: number;
  candidate_id: number;
  job_id: number;
  overall_score: number | null;
  recommendation: string | null;
};

export type Stage3ReportJob = {
  id: number;
  title: string;
  reportCount: number;
};

export type Stage3Report = {
  id: number;
  candidateId: number;
  candidateName: string;
  candidateSource: string | null;
  jobId: number;
  jobTitle: string;
  screeningId: number | null;
  screeningScore: number | null;
  screeningRecommendation: string | null;
  title: string;
  content: string;
  reportType: string;
  format: string;
  metadata: Record<string, unknown> | null;
  generatedAt: string;
  updatedAt: string;
};

export type ReportCenterSnapshot = {
  items: Stage3Report[];
  jobs: Stage3ReportJob[];
  totalReports: number;
  totalCandidates: number;
  totalJobs: number;
  totalScreeningResults: number;
};

export const getStage3Reports = async (): Promise<ReportCenterSnapshot> => {
  const [reportsResponse, candidatesResponse, jobsResponse, screeningResponse] = await Promise.all([
    v2Http.get<ReportResponse[]>('/reports'),
    v2Http.get<CandidateResponse[]>('/candidates'),
    v2Http.get<JobResponse[]>('/jobs'),
    v2Http.get<ScreeningResultResponse[]>('/screening-results'),
  ]);

  const candidates = new Map(candidatesResponse.data.map(candidate => [candidate.id, candidate]));
  const jobs = new Map(jobsResponse.data.map(job => [job.id, job]));
  const screeningResults = new Map(screeningResponse.data.map(result => [result.id, result]));
  const reportCounts = new Map<number, number>();

  reportsResponse.data.forEach(report => {
    reportCounts.set(report.job_id, (reportCounts.get(report.job_id) || 0) + 1);
  });

  const items = reportsResponse.data
    .map(report => {
      const candidate = candidates.get(report.candidate_id);
      const job = jobs.get(report.job_id);
      const screening = report.screening_id === null
        ? undefined
        : screeningResults.get(report.screening_id);

      return {
        id: report.id,
        candidateId: report.candidate_id,
        candidateName: candidate?.name || `候选人 #${report.candidate_id}`,
        candidateSource: candidate?.source || null,
        jobId: report.job_id,
        jobTitle: job?.title || `岗位 #${report.job_id}`,
        screeningId: report.screening_id,
        screeningScore: screening?.overall_score ?? null,
        screeningRecommendation: screening?.recommendation ?? null,
        title: report.title?.trim() || `未命名报告 #${report.id}`,
        content: report.content,
        reportType: report.report_type,
        format: report.format,
        metadata: report.report_metadata,
        generatedAt: report.generated_at,
        updatedAt: report.updated_at,
      };
    })
    .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));

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
    totalScreeningResults: screeningResponse.data.length,
  };
};
