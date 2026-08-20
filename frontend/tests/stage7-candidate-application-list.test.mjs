import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';


const candidates = [
  {
    id: 5,
    name: '同一候选人',
    email: 'same@example.com',
    phone: '13800138000',
    current_company: '示例科技',
    current_title: '资深工程师',
    work_years: 6,
    education_level: '本科',
    source: '内推',
    status: 'screening',
    applied_job_id: 1,
    resume_file_path: null,
    created_at: '2026-08-19T08:00:00Z',
    updated_at: '2026-08-19T08:00:00Z',
  },
  {
    id: 6,
    name: '人工通过候选人',
    email: 'direct@example.com',
    phone: '13900139000',
    current_company: null,
    current_title: null,
    work_years: null,
    education_level: null,
    source: 'HR录入',
    status: 'new',
    applied_job_id: null,
    resume_file_path: null,
    created_at: '2026-08-19T08:00:00Z',
    updated_at: '2026-08-19T08:00:00Z',
  },
];

const jobs = [
  { id: 1, title: '平台工程师', department: '研发部', status: 'open' },
  { id: 2, title: '数据工程师', department: '数据部', status: 'closed' },
  { id: 3, title: '不会显示的备选岗位', department: '产品部', status: 'open' },
];

const makeApplication = (overrides) => ({
  id: 11,
  candidate_id: 5,
  job_id: 1,
  current_resume_id: 21,
  source: 'hr_screening',
  lifecycle_status: 'active',
  recruitment_stage: 'screening_passed',
  ai_status: 'completed',
  hr_decision: 'passed',
  current_screening_result_id: 101,
  applied_at: '2026-08-19T08:00:00Z',
  created_at: '2026-08-19T08:00:00Z',
  updated_at: '2026-08-19T09:00:00Z',
  ...overrides,
});

const applications = [
  makeApplication({}),
  makeApplication({
    id: 12,
    job_id: 2,
    current_resume_id: 22,
    current_screening_result_id: 102,
    updated_at: '2026-08-19T10:00:00Z',
  }),
  makeApplication({
    id: 13,
    candidate_id: 6,
    current_resume_id: 23,
    source: 'hr_direct',
    ai_status: 'failed',
    current_screening_result_id: null,
    updated_at: '2026-08-19T11:00:00Z',
  }),
  makeApplication({
    id: 14,
    job_id: 3,
    current_resume_id: 24,
    recruitment_stage: 'backup',
    hr_decision: 'backup',
    current_screening_result_id: null,
    updated_at: '2026-08-19T12:00:00Z',
  }),
];

const makeScreening = (overrides) => ({
  id: 101,
  candidate_id: 5,
  job_id: 1,
  application_id: 11,
  resume_id: 21,
  attempt_number: 1,
  execution_status: 'completed',
  overall_score: 88,
  hard_pass: true,
  recommendation: 'recommend',
  evidence_coverage_rate: '0.8000',
  error_code: null,
  error_message: null,
  started_at: '2026-08-19T08:00:00Z',
  finished_at: '2026-08-19T09:00:00Z',
  duration_ms: 60000,
  trigger_reason: 'initial',
  force_rerun: false,
  is_outdated: false,
  outdated_at: null,
  created_at: '2026-08-19T08:00:00Z',
  updated_at: '2026-08-19T09:00:00Z',
  ...overrides,
});

const screeningResults = [
  makeScreening({}),
  makeScreening({
    id: 102,
    job_id: 2,
    application_id: 12,
    resume_id: 22,
    overall_score: 91,
    recommendation: 'strong_recommend',
    updated_at: '2026-08-19T10:00:00Z',
  }),
];

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const service = await server.ssrLoadModule('/src/features/recruitment/services/candidates.ts');
  const requests = [];

  v2Http.defaults.adapter = async config => {
    requests.push(config);
    let data = [];
    if (config.url === '/applications') {
      data = applications.filter(item => item.hr_decision === config.params?.hr_decision);
    } else if (config.url === '/candidates') data = candidates;
    else if (config.url === '/jobs') data = jobs;
    else if (config.url === '/screening-results') data = screeningResults;
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };

  const snapshot = await service.getRecruitmentCandidates();
  const applicationRequest = requests.find(request => request.url === '/applications');

  assert.equal(applicationRequest.params.hr_decision, 'passed');
  assert.equal(snapshot.total, 3);
  assert.equal(snapshot.uniqueCandidateCount, 2);
  assert.equal(snapshot.linkedJobCount, 2);
  assert.equal(snapshot.needsAttentionCount, 1);
  assert.deepEqual(snapshot.items.map(item => item.applicationId), [13, 12, 11]);
  assert.equal(snapshot.items.filter(item => item.candidateId === 5).length, 2);
  assert.equal(snapshot.items.find(item => item.applicationId === 12).jobTitle, '数据工程师');
  assert.equal(snapshot.items.find(item => item.applicationId === 12).currentScore, 91);
  assert.equal(snapshot.items.find(item => item.applicationId === 13).applicationSource, 'hr_direct');
  assert.deepEqual(snapshot.jobs.map(job => job.id), [1, 2]);
  assert.equal(snapshot.items.some(item => item.applicationId === 14), false);

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentCandidateList.tsx', import.meta.url),
    'utf8',
  );
  for (const text of [
    'HR 已通过 Application → 进入候选人业务视图',
    'AI 后续重跑不会自动改变这里的人员归类',
    'key={item.applicationId}',
    '同一人通过多个岗位时分行展示',
    "navigate('/app/candidates/new')",
    '目前没有 HR 已通过的 Application',
  ]) {
    assert.ok(pageSource.includes(text), `候选人 Application 视图缺少边界：${text}`);
  }

  const styles = await readFile(
    new URL('../src/features/recruitment/styles/candidates.css', import.meta.url),
    'utf8',
  );
  assert.match(styles, /\.recruitment-candidate-entry-rule\s*\{/s);
  assert.match(styles, /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-candidate-entry-rule\s*\{/s);

  console.log('STAGE7_CANDIDATE_APPLICATION_LIST_TEST_OK');
} finally {
  await server.close();
}
