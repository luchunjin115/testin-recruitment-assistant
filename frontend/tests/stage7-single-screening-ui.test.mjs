import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';


const baseItem = {
  application: {
    id: 31,
    candidateId: 5,
    jobId: 2,
    currentResumeId: 8,
    source: 'hr_direct',
    lifecycleStatus: 'active',
    recruitmentStage: 'hr_review',
    aiStatus: 'not_started',
    hrDecision: 'pending',
    currentScreeningResultId: null,
    appliedAt: '2026-08-18T08:00:00Z',
    createdAt: '2026-08-18T08:00:00Z',
    updatedAt: '2026-08-18T09:00:00Z',
  },
  candidateName: '虚构候选人',
  candidateTitle: null,
  candidateSource: null,
  jobTitle: '后端工程师',
  jobDepartment: '研发部',
  jobStatus: 'open',
  currentResult: null,
};

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const actions = await server.ssrLoadModule('/src/features/recruitment/screeningAction.ts');

  assert.deepEqual(actions.getStage7SingleScreeningAction(baseItem, false), {
    allowed: true,
    label: '开始初筛',
    reason: '使用当前简历和已发布评分标准。',
  });
  assert.equal(actions.getStage7SingleScreeningAction(baseItem, true).label, '正在启动');
  assert.equal(actions.getStage7SingleScreeningAction({
    ...baseItem,
    application: { ...baseItem.application, aiStatus: 'failed' },
  }, false).label, '重新尝试');
  assert.equal(actions.getStage7SingleScreeningAction({
    ...baseItem,
    application: { ...baseItem.application, aiStatus: 'blocked' },
  }, false).allowed, false);
  assert.equal(actions.getStage7SingleScreeningAction({
    ...baseItem,
    currentResult: { isOutdated: true },
  }, false).label, '更新初筛');
  assert.equal(actions.getStage7SingleScreeningAction({
    ...baseItem,
    jobStatus: 'closed',
  }, false).reason, '岗位已关闭，不能启动新评分。');
  assert.equal(actions.getStage7SingleScreeningAction({
    ...baseItem,
    application: { ...baseItem.application, currentResumeId: null },
  }, false).label, '缺少简历');

  const pendingIds = new Set();
  assert.equal(actions.beginStage7SingleScreening(pendingIds, 31), true);
  assert.equal(actions.beginStage7SingleScreening(pendingIds, 31), false);
  actions.finishStage7SingleScreening(pendingIds, 31);
  assert.equal(actions.beginStage7SingleScreening(pendingIds, 31), true);

  assert.match(
    actions.getStage7SingleScreeningErrorMessage('RUBRIC_DRAFT_STALE', '评分标准已过期'),
    /重新确认并发布评分标准/,
  );

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url),
    'utf8',
  );
  for (const text of [
    'runStage7ApplicationScreening',
    'pendingScreeningIdsRef',
    'beginStage7SingleScreening',
    'finishStage7SingleScreening',
    'AI 初筛已完成',
    'SCREENING_ALREADY_RUNNING',
    '开始批量初筛',
  ]) {
    assert.ok(pageSource.includes(text), `单人评分页面缺少交互保护：${text}`);
  }

  console.log('STAGE7_SINGLE_SCREENING_UI_TEST_OK');
} finally {
  await server.close();
}
