import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const applications = [{
  id: 31, candidate_id: 5, job_id: 2, current_resume_id: 8, source: 'hr_direct',
  lifecycle_status: 'active', recruitment_stage: 'hr_review', hr_decision: 'pending',
  applied_at: '2026-08-18T08:00:00Z', created_at: '2026-08-18T08:00:00Z',
  updated_at: '2026-08-18T09:00:00Z',
}];
const jobs = [{ id: 2, title: '历史关闭岗位', department: '产品部', status: 'closed' }];
const candidates = [{
  id: 5, name: '虚构候选人', source: '内推', status: 'screening',
  applied_job_id: 2, current_title: '产品经理',
}];
const server = await createServer({
  appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(),
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
    if (config.url === '/public-application-submissions') data = [];
    if (config.url === '/applications/31/screening') data = {
      application_id: 31, report: null, latest_run: null,
    };
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };
  const snapshot = await screening.getStage7ScreeningCenter({
    jobId: 2, recruitmentStage: 'hr_review', hrDecision: 'pending', lifecycleStatus: 'active',
  });
  assert.equal(snapshot.items.length, 1);
  assert.equal(snapshot.items[0].candidateName, '虚构候选人');
  assert.equal(snapshot.items[0].jobTitle, '历史关闭岗位');
  assert.equal(snapshot.items[0].jobStatus, 'closed');
  assert.equal(snapshot.items[0].screeningState.applicationId, 31);
  assert.equal('currentResult' in snapshot.items[0], false);
  assert.deepEqual(requests.map(request => request.url), [
    '/applications', '/jobs', '/candidates', '/public-application-submissions',
    '/applications/31/screening',
  ]);
  assert.deepEqual(requests[0].params, {
    job_id: 2, recruitment_stage: 'hr_review', hr_decision: 'pending', lifecycle_status: 'active',
  });

  const [pageSource, tableSource] = await Promise.all([
    readFile(new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/ApplicationEvidenceTable.tsx', import.meta.url), 'utf8'),
  ]);
  for (const text of [
    'AI 初筛中心', '录入待筛申请', 'AI 给出证据', 'HR 明确决定',
    '初筛申请列表', '当前没有符合条件的初筛申请',
    '批量重新评估', "status: 'loading'", "status: 'error'", "view: 'screening'",
  ]) assert.ok(pageSource.includes(text), `申请工作台缺少页面状态：${text}`);
  assert.ok(tableSource.includes('>详情</Button>'), '列表必须能打开单个申请详情');
  for (const technicalCopy of ['hr_decision', 'recruitment_stage', 'lifecycle_status', '尚未接入登录/RBAC']) {
    assert.equal(pageSource.includes(technicalCopy), false, `主工作区不应展示开发字段：${technicalCopy}`);
  }
  assert.equal(pageSource.includes('/screening-results'), false);
  console.log('STAGE7_SCREENING_CENTER_TEST_OK');
} finally {
  await server.close();
}
