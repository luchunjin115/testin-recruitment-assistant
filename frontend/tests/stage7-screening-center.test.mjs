import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';


const applications = [{
  id: 31,
  candidate_id: 5,
  job_id: 2,
  current_resume_id: 8,
  source: 'hr_direct',
  lifecycle_status: 'active',
  recruitment_stage: 'hr_review',
  ai_status: 'completed',
  hr_decision: 'pending',
  current_screening_result_id: 91,
  applied_at: '2026-08-18T08:00:00Z',
  created_at: '2026-08-18T08:00:00Z',
  updated_at: '2026-08-18T09:00:00Z',
}];

const jobs = [{ id: 2, title: '历史关闭岗位', department: '产品部', status: 'closed' }];
const candidates = [{
  id: 5,
  name: '虚构候选人',
  source: '内推',
  status: 'screening',
  applied_job_id: 2,
  current_title: '产品经理',
}];
const screeningResults = [{
  id: 91,
  candidate_id: 5,
  job_id: 2,
  application_id: 31,
  resume_id: 8,
  attempt_number: 2,
  execution_status: 'completed',
  overall_score: 84,
  hard_pass: true,
  recommendation: 'recommend',
  evidence_coverage_rate: '0.92',
  error_code: null,
  error_message: null,
  started_at: '2026-08-18T08:58:00Z',
  finished_at: '2026-08-18T09:00:00Z',
  duration_ms: 120000,
  trigger_reason: null,
  force_rerun: false,
  is_outdated: true,
  outdated_at: '2026-08-18T10:00:00Z',
  created_at: '2026-08-18T09:00:00Z',
  updated_at: '2026-08-18T10:00:00Z',
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
  const screening = await server.ssrLoadModule('/src/features/recruitment/services/screening.ts');
  const requests = [];

  v2Http.defaults.adapter = async config => {
    requests.push(config);
    let data = [];
    if (config.url === '/applications') data = applications;
    if (config.url === '/jobs') data = jobs;
    if (config.url === '/candidates') data = candidates;
    if (config.url === '/screening-results') data = screeningResults;
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };

  const snapshot = await screening.getStage7ScreeningCenter({
    jobId: 2,
    recruitmentStage: 'hr_review',
    aiStatus: 'completed',
    hrDecision: 'pending',
    lifecycleStatus: 'active',
  });

  assert.equal(snapshot.items.length, 1);
  assert.equal(snapshot.items[0].candidateName, '虚构候选人');
  assert.equal(snapshot.items[0].candidateTitle, '产品经理');
  assert.equal(snapshot.items[0].jobTitle, '历史关闭岗位');
  assert.equal(snapshot.items[0].jobStatus, 'closed');
  assert.equal(snapshot.items[0].currentResult.overallScore, 84);
  assert.equal(snapshot.items[0].currentResult.evidenceCoverageRate, 0.92);
  assert.equal(snapshot.items[0].currentResult.isOutdated, true);

  const applicationRequest = requests.find(request => request.url === '/applications');
  assert.deepEqual(applicationRequest.params, {
    job_id: 2,
    recruitment_stage: 'hr_review',
    ai_status: 'completed',
    hr_decision: 'pending',
    lifecycle_status: 'active',
  });
  assert.deepEqual(requests.map(request => request.url), [
    '/applications', '/jobs', '/candidates', '/screening-results',
  ]);

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url),
    'utf8',
  );
  const styles = await readFile(
    new URL('../src/features/recruitment/styles/screening.css', import.meta.url),
    'utf8',
  );

  for (const text of [
    'Application 工作队列',
    '等待初筛',
    '需要处理',
    'HR 待决策',
    '结果已过期',
    '岗位已关闭',
    '清除筛选',
    '重新加载',
  ]) {
    assert.ok(pageSource.includes(text), `初筛中心缺少页面状态：${text}`);
  }
  assert.ok(pageSource.includes('getStage7ScreeningCenter'), '页面必须读取阶段 7 Application 聚合数据');
  assert.ok(pageSource.includes("status: 'loading'"), '页面必须覆盖首次加载状态');
  assert.ok(pageSource.includes("status: 'error'"), '页面必须覆盖接口失败状态');
  assert.match(styles, /\.recruitment-application-funnel\s*\{[^}]*background:\s*#172033;/s);
  assert.match(styles, /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-application-row\s*\{/s);

  console.log('STAGE7_SCREENING_CENTER_TEST_OK');
} finally {
  await server.close();
}
