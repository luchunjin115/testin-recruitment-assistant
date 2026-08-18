import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';


const makeItem = ({ id = 1, jobId = 7, aiStatus = 'not_started', jobStatus = 'open' } = {}) => ({
  application: {
    id,
    candidateId: id,
    jobId,
    currentResumeId: 20 + id,
    source: 'hr_direct',
    lifecycleStatus: 'active',
    recruitmentStage: 'hr_review',
    aiStatus,
    hrDecision: 'pending',
    currentScreeningResultId: null,
    appliedAt: '2026-08-18T08:00:00Z',
    createdAt: '2026-08-18T08:00:00Z',
    updatedAt: '2026-08-18T09:00:00Z',
  },
  candidateName: `候选人 ${id}`,
  candidateTitle: null,
  candidateSource: null,
  jobTitle: `岗位 ${jobId}`,
  jobDepartment: null,
  jobStatus,
  currentResult: null,
});

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const batch = await server.ssrLoadModule('/src/features/recruitment/screeningBatchAction.ts');
  const baseOptions = {
    selected: false,
    selectedCount: 0,
    selectedJobId: null,
    batchPending: false,
    singlePending: false,
  };

  assert.equal(batch.getStage7BatchSelectionState(makeItem(), baseOptions).allowed, true);
  assert.match(batch.getStage7BatchSelectionState(makeItem({ jobId: 8 }), {
    ...baseOptions, selectedJobId: 7,
  }).reason, /同一岗位/);
  assert.match(batch.getStage7BatchSelectionState(makeItem(), {
    ...baseOptions, selectedCount: 5, selectedJobId: 7,
  }).reason, /最多选择 5 人/);
  assert.equal(batch.getStage7BatchSelectionState(makeItem({ aiStatus: 'blocked' }), baseOptions).allowed, false);
  assert.equal(batch.getStage7BatchSelectionState(makeItem({ aiStatus: 'screening' }), baseOptions).allowed, false);
  assert.equal(batch.getStage7BatchSelectionState(makeItem({ jobStatus: 'closed' }), baseOptions).allowed, false);

  const guard = { pending: false };
  assert.equal(batch.beginStage7BatchRun(guard), true);
  assert.equal(batch.beginStage7BatchRun(guard), false);
  batch.finishStage7BatchRun(guard);
  assert.equal(batch.beginStage7BatchRun(guard), true);

  assert.deepEqual(batch.getStage7FailedBatchApplicationIds({
    items: [
      { applicationId: 1, status: 'completed' },
      { applicationId: 2, status: 'failed' },
      { applicationId: 3, status: 'blocked' },
      { applicationId: 4, status: 'failed' },
    ],
  }), [2, 4]);

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url),
    'utf8',
  );
  const styles = await readFile(
    new URL('../src/features/recruitment/styles/screening.css', import.meta.url),
    'utf8',
  );
  for (const text of [
    'runStage7ScreeningBatch',
    'batchRunGuardRef',
    '一个批次最多选择 5 人',
    '开始批量初筛',
    '仅重试失败项',
    '批量评分逐项结果',
  ]) {
    assert.ok(pageSource.includes(text), `批量评分页面缺少交互：${text}`);
  }
  assert.match(styles, /\.recruitment-screening-batch-bar\s*\{/s);
  assert.match(styles, /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-screening-batch-bar\s*\{/s);

  console.log('STAGE7_BATCH_SCREENING_UI_TEST_OK');
} finally {
  await server.close();
}
