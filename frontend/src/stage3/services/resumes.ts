import { v2Http } from '../../services/http';

export type ResumeParseStatus = 'uploaded' | 'parsing' | 'parsed' | 'failed';

export type ResumeListItem = {
  id: number;
  filename: string;
  candidateId: number;
  candidateName: string;
  jobTitle: string;
  fileType: string | null;
  fileSize: number | null;
  parseStatus: ResumeParseStatus;
  parseError: string | null;
  uploadedAt: string;
};

type ResumeResponse = {
  id: number;
  candidate_id: number;
  job_id: number | null;
  filename: string;
  file_type: string | null;
  file_size: number | null;
  parse_status: ResumeParseStatus;
  parse_error: string | null;
  uploaded_at: string;
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
      const candidate = candidates.get(resume.candidate_id);
      const jobId = resume.job_id ?? candidate?.applied_job_id;

      return {
        id: resume.id,
        filename: resume.filename,
        candidateId: resume.candidate_id,
        candidateName: candidate?.name || `候选人 #${resume.candidate_id}`,
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
