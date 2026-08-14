import { API_BASE_URL, v2Http } from '../../services/http';
import type {
  ResumeStructureRequest,
  ResumeStructureResponse,
} from '../types/resumeStructure';

export type {
  ResumeBasicInfoDraft,
  ResumeEducationDraft,
  ResumeParseDraft,
  ResumeProjectExperienceDraft,
  ResumeStructureErrorDetail,
  ResumeStructureErrorResponse,
  ResumeStructureFailureWithDraft,
  ResumeStructureRequest,
  ResumeStructureResponse,
  ResumeStructurePerformance,
  ResumeStructureStatus,
  ResumeWorkExperienceDraft,
} from '../types/resumeStructure';

export type ResumeParseStatus = 'uploaded' | 'parsing' | 'parsed' | 'failed';
export const RESUME_STRUCTURE_REQUEST_TIMEOUT_MS = 100_000;

export type ResumeListItem = {
  id: number;
  filename: string;
  candidateId: number | null;
  candidateName: string;
  jobTitle: string;
  fileType: string | null;
  fileSize: number | null;
  parseStatus: ResumeParseStatus;
  parseError: string | null;
  uploadedAt: string;
};

export type ResumeResponse = {
  id: number;
  candidate_id: number | null;
  job_id: number | null;
  filename: string;
  file_path: string;
  file_type: string | null;
  file_size: number | null;
  raw_text: string | null;
  parse_status: ResumeParseStatus;
  parse_error: string | null;
  uploaded_at: string;
  parsed_at: string | null;
};

export type CandidateResumeFile = {
  id: number;
  filename: string;
  fileType: string | null;
  fileSize: number | null;
  parseStatus: ResumeParseStatus;
  uploadedAt: string;
  supportsPreview: boolean;
};

type CandidateResponse = {
  id: number;
  name: string;
  applied_job_id: number | null;
};

type JobResponse = {
  id: number;
  title: string;
};

export type ResumeListSnapshot = {
  items: ResumeListItem[];
  total: number;
  uploaded: number;
  parsing: number;
  parsed: number;
  failed: number;
};

export type Stage3ResumeDetail = {
  id: number;
  candidateId: number | null;
  jobId: number | null;
  filename: string;
  filePath: string;
  fileType: string | null;
  fileSize: number | null;
  rawText: string | null;
  parseStatus: ResumeParseStatus;
  parseError: string | null;
  uploadedAt: string;
  parsedAt: string | null;
};

const mapResumeDetail = (resume: ResumeResponse): Stage3ResumeDetail => ({
  id: resume.id,
  candidateId: resume.candidate_id,
  jobId: resume.job_id,
  filename: resume.filename,
  filePath: resume.file_path,
  fileType: resume.file_type,
  fileSize: resume.file_size,
  rawText: resume.raw_text,
  parseStatus: resume.parse_status,
  parseError: resume.parse_error,
  uploadedAt: resume.uploaded_at,
  parsedAt: resume.parsed_at,
});

export const getStage3Resumes = async (): Promise<ResumeListSnapshot> => {
  const [resumesResponse, candidatesResponse, jobsResponse] = await Promise.all([
    v2Http.get<ResumeResponse[]>('/resumes'),
    v2Http.get<CandidateResponse[]>('/candidates'),
    v2Http.get<JobResponse[]>('/jobs'),
  ]);

  const candidates = new Map(candidatesResponse.data.map(candidate => [candidate.id, candidate]));
  const jobs = new Map(jobsResponse.data.map(job => [job.id, job.title]));
  const items = [...resumesResponse.data]
    .sort((left, right) => Date.parse(right.uploaded_at) - Date.parse(left.uploaded_at))
    .map(resume => {
      const candidate = resume.candidate_id === null
        ? undefined
        : candidates.get(resume.candidate_id);
      const jobId = resume.job_id ?? candidate?.applied_job_id;

      return {
        id: resume.id,
        filename: resume.filename,
        candidateId: resume.candidate_id,
        candidateName: candidate?.name || (
          resume.candidate_id === null ? '待确认候选人' : `候选人 #${resume.candidate_id}`
        ),
        jobTitle: (jobId ? jobs.get(jobId) : undefined) || '未关联岗位',
        fileType: resume.file_type,
        fileSize: resume.file_size,
        parseStatus: resume.parse_status,
        parseError: resume.parse_error,
        uploadedAt: resume.uploaded_at,
      };
    });

  return {
    items,
    total: items.length,
    uploaded: items.filter(item => item.parseStatus === 'uploaded').length,
    parsing: items.filter(item => item.parseStatus === 'parsing').length,
    parsed: items.filter(item => item.parseStatus === 'parsed').length,
    failed: items.filter(item => item.parseStatus === 'failed').length,
  };
};

export const uploadStage3Resume = async (file: File): Promise<Stage3ResumeDetail> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await v2Http.post<ResumeResponse>('/resumes/upload', formData);
  return mapResumeDetail(response.data);
};

export const extractStage3ResumeText = async (
  resumeId: number,
): Promise<Stage3ResumeDetail> => {
  const response = await v2Http.post<ResumeResponse>(`/resumes/${resumeId}/extract-text`);
  return mapResumeDetail(response.data);
};

export const structureStage3Resume = async (
  resumeId: number,
  force = false,
): Promise<ResumeStructureResponse> => {
  const request: ResumeStructureRequest = { force };
  const response = await v2Http.post<ResumeStructureResponse>(
    `/resumes/${resumeId}/structure`,
    request,
    { timeout: RESUME_STRUCTURE_REQUEST_TIMEOUT_MS },
  );
  return response.data;
};

export const abandonStage3Resume = async (resumeId: number): Promise<void> => {
  await v2Http.delete(`/resumes/${resumeId}`);
};

export const getStage3CandidateResumeFiles = async (
  candidateId: number,
): Promise<CandidateResumeFile[]> => {
  const response = await v2Http.get<ResumeResponse[]>('/resumes', {
    params: { candidate_id: candidateId },
  });
  return response.data.map(resume => ({
    id: resume.id,
    filename: resume.filename,
    fileType: resume.file_type,
    fileSize: resume.file_size,
    parseStatus: resume.parse_status,
    uploadedAt: resume.uploaded_at,
    supportsPreview: resume.file_type === 'application/pdf' || resume.file_type === 'text/plain',
  }));
};

export const getStage3ResumeFileUrl = (
  resumeId: number,
  download = false,
) => `${API_BASE_URL}/api/v2/resumes/${resumeId}/file${download ? '?download=true' : ''}`;
