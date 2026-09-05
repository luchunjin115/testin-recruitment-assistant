import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const candidates = [
  { id: 5, name: '同一候选人', email: 'same@example.com', phone: '13800138000',
    current_company: '示例科技', current_title: '资深工程师', source: '内推' },
  { id: 6, name: '人工通过候选人', email: null, phone: null,
    current_company: null, current_title: null, source: 'HR录入' },
];
const jobs = [
  { id: 1, title: '平台工程师', department: '研发部', status: 'open' },
  { id: 2, title: '数据工程师', department: '数据部', status: 'closed' },
  { id: 3, title: '不会显示的备选岗位', department: '产品部', status: 'open' },
];
const makeApplication = overrides => ({
  id: 11, candidate_id: 5, job_id: 1, current_resume_id: 21, source: 'hr_screening',
  lifecycle_status: 'active', recruitment_stage: 'screening_passed', hr_decision: 'passed',
  applied_at: '2026-08-19T08:00:00Z', created_at: '2026-08-19T08:00:00Z',
  updated_at: '2026-08-19T09:00:00Z', ...overrides,
});
const applications = [
  makeApplication({}),
  makeApplication({ id: 12, job_id: 2, current_resume_id: 22, updated_at: '2026-08-19T10:00:00Z' }),
  makeApplication({ id: 13, candidate_id: 6, current_resume_id: 23, source: 'hr_direct', updated_at: '2026-08-19T11:00:00Z' }),
  makeApplication({ id: 14, job_id: 3, recruitment_stage: 'backup', hr_decision: 'backup' }),
];
const server = await createServer({
  appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const service = await server.ssrLoadModule('/src/features/recruitment/services/candidates.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    let data = [];
    if (config.url === '/applications') data = applications.filter(
      item => item.hr_decision === config.params?.hr_decision,
    );
    else if (config.url === '/candidates') data = candidates;
    else if (config.url === '/jobs') data = jobs;
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };
  const snapshot = await service.getRecruitmentCandidates();
  assert.equal(requests.find(request => request.url === '/applications').params.hr_decision, 'passed');
  assert.equal(snapshot.total, 3);
  assert.equal(snapshot.uniqueCandidateCount, 2);
  assert.equal(snapshot.linkedJobCount, 2);
  assert.equal(snapshot.needsAttentionCount, 1);
  assert.deepEqual(snapshot.items.map(item => item.applicationId), [13, 12, 11]);
  assert.equal(snapshot.items.find(item => item.applicationId === 12).jobTitle, '数据工程师');
  assert.equal(snapshot.items.find(item => item.applicationId === 13).applicationSource, 'hr_direct');
  assert.equal('currentScore' in snapshot.items[0], false);
  assert.deepEqual(snapshot.jobs.map(job => job.id), [1, 2]);
  assert.equal(snapshot.items.some(item => item.applicationId === 14), false);

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentCandidateList.tsx', import.meta.url), 'utf8',
  );
  for (const text of [
    'HR 初筛通过 → 面试 → Offer → 入职',
    '每一行代表候选人对一个岗位的招聘进程',
    '候选人列表', '当前没有符合条件的已通过候选人',
    "view: 'candidate'", 'mode="candidate"', 'workspace="candidate"',
  ]) assert.ok(pageSource.includes(text), `候选人 Application 视图缺少边界：${text}`);
  console.log('STAGE7_CANDIDATE_APPLICATION_LIST_TEST_OK');
} finally {
  await server.close();
}
