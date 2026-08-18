import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';


const requirements = {
  schema_version: '1.0',
  responsibilities: ['负责业务系统开发'],
  required_skills: ['React'],
  preferred_skills: [],
  minimum_work_years: 1,
  education_requirement: 'bachelor_or_above',
  required_experiences: [],
  preferred_experiences: [],
  keywords: [],
  additional_requirements: [],
};

const jobs = [
  {
    id: 1,
    title: '开放岗位',
    department: '研发部',
    location: '上海',
    employment_type: 'full_time',
    headcount: 2,
    description: '开放岗位说明',
    requirements,
    status: 'open',
    created_at: '2026-08-15T08:00:00Z',
    updated_at: '2026-08-15T09:00:00Z',
  },
  {
    id: 2,
    title: '历史关闭岗位',
    department: '产品部',
    location: '北京',
    employment_type: 'full_time',
    headcount: 1,
    description: '关闭岗位说明',
    requirements,
    status: 'closed',
    created_at: '2026-08-14T08:00:00Z',
    updated_at: '2026-08-14T09:00:00Z',
  },
];

const candidates = [{
  id: 5,
  name: '历史候选人',
  email: null,
  phone: null,
  current_company: null,
  work_years: 3,
  education_level: '本科',
  source: '内推',
  status: 'screening',
  applied_job_id: 2,
  current_title: '产品经理',
  resume_file_path: null,
  created_at: '2026-08-15T08:00:00Z',
  updated_at: '2026-08-15T09:00:00Z',
}];

const screeningResults = [{
  id: 9,
  candidate_id: 5,
  job_id: 2,
  application_id: 12,
  resume_id: 6,
  attempt_number: 1,
  execution_status: 'completed',
  overall_score: 82,
  hard_pass: true,
  recommendation: '建议推进',
  evidence_coverage_rate: '0.9000',
  error_code: null,
  error_message: null,
  started_at: '2026-08-15T08:00:00Z',
  finished_at: '2026-08-15T09:00:00Z',
  duration_ms: 3600000,
  trigger_reason: null,
  force_rerun: false,
  is_outdated: false,
  outdated_at: null,
  created_at: '2026-08-15T08:00:00Z',
  updated_at: '2026-08-15T09:00:00Z',
}];

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const application = await server.ssrLoadModule('/src/features/recruitment/services/application.ts');
  const candidate = await server.ssrLoadModule('/src/features/recruitment/services/candidates.ts');
  const dashboard = await server.ssrLoadModule('/src/features/recruitment/services/dashboard.ts');
  const requests = [];

  v2Http.defaults.adapter = async config => {
    requests.push(config);
    let data = [];
    if (config.url === '/jobs') data = config.params?.status === 'open' ? [jobs[0]] : jobs;
    if (config.url === '/candidates') data = candidates;
    if (config.url === '/screening-results') data = screeningResults;
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };

  const applicationJobs = await application.getRecruitmentApplicationJobs();
  assert.deepEqual(applicationJobs.map(job => job.id), [1]);
  assert.equal(requests.at(-1).params?.status, 'open');
  assert.equal(applicationJobs[0].requirementSummary, '负责业务系统开发');

  const candidateJobs = await candidate.getRecruitmentCandidateJobs();
  assert.deepEqual(candidateJobs.map(job => job.id), [1]);

  const candidateSnapshot = await candidate.getRecruitmentCandidates();
  assert.equal(candidateSnapshot.items[0].appliedJobTitle, '历史关闭岗位');

  const dashboardSnapshot = await dashboard.getRecruitmentDashboardSnapshot();
  assert.equal(dashboardSnapshot.openJobs, 1);
  assert.equal(dashboardSnapshot.recentCandidates[0].role, '历史关闭岗位');

  const jobRequests = requests.filter(request => request.url === '/jobs');
  assert.equal(jobRequests.filter(request => request.params?.status === 'open').length, 3);
  assert.equal(jobRequests.filter(request => !request.params?.status).length, 2);

  const screeningSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url),
    'utf8',
  );
  assert.ok(screeningSource.includes('岗位已关闭'), '历史关闭岗位结果必须提供清晰状态提示');

  console.log('RECRUITMENT_JOB_READ_BOUNDARIES_TEST_OK');
} finally {
  await server.close();
}
