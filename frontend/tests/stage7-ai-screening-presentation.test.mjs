import assert from 'node:assert/strict';
import { createServer } from 'vite';

const server = await createServer({
  appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const presentation = await server.ssrLoadModule('/src/features/recruitment/screeningPresentation.ts');
  assert.deepEqual(Object.keys(presentation.PLAN_STATUS_META).sort(), [
    'failed', 'generating', 'outdated', 'pending_confirmation', 'ready',
  ]);
  assert.deepEqual(Object.keys(presentation.SCREENING_STATUS_META).sort(), [
    'failed', 'paused', 'queued', 'running', 'succeeded', 'waiting_plan', 'waiting_resume',
  ]);
  assert.equal(presentation.shouldPollScreeningStatus('queued'), true);
  assert.equal(presentation.shouldPollScreeningStatus('running'), true);
  for (const status of ['waiting_resume', 'waiting_plan', 'succeeded', 'failed', 'paused', null]) {
    assert.equal(presentation.shouldPollScreeningStatus(status), false, `${status} 不应继续轮询`);
  }
  assert.equal(presentation.shouldApplyScreeningResponse(3, 3), true);
  assert.equal(presentation.shouldApplyScreeningResponse(2, 3), false);
  assert.equal(presentation.SCREENING_POLL_INTERVAL_MS, 4000);
  assert.equal(presentation.OUTDATED_REASON_LABELS.resume_changed, '当前 Resume 已变化');
  assert.equal(presentation.OUTDATED_REASON_LABELS.jd_changed, '岗位 JD 已变化');
  assert.equal(presentation.OUTDATED_REASON_LABELS.evaluation_plan_changed, '当前评价计划已变化');
  assert.equal(
    presentation.SCREENING_WAITING_REASON_META.plan_pending_confirmation.label,
    '评价计划等待 HR 确认',
  );

  assert.equal(presentation.validateBatchSelection([]).valid, false);
  assert.equal(presentation.validateBatchSelection([
    { applicationId: 1, jobId: 7 }, { applicationId: 2, jobId: 8 },
  ]).valid, false);
  assert.equal(presentation.validateBatchSelection([
    { applicationId: 1, jobId: 7 }, { applicationId: 1, jobId: 7 },
  ]).valid, false);
  assert.equal(presentation.validateBatchSelection(
    Array.from({ length: 21 }, (_, index) => ({ applicationId: index + 1, jobId: 7 })),
  ).valid, false);
  const twenty = presentation.validateBatchSelection(
    Array.from({ length: 20 }, (_, index) => ({ applicationId: index + 1, jobId: 7 })),
  );
  assert.equal(twenty.valid, true);
  assert.equal(twenty.applicationIds.length, 20);
  assert.deepEqual(presentation.validateBatchSelection([{ applicationId: 9, jobId: 7 }]), {
    valid: true, jobId: 7, applicationIds: [9],
  });

  const plan = { id: 41, items: [{ key: 'skill:react', title: 'React' }] };
  assert.equal(presentation.getRequirementPlanItem(plan, 41, 'skill:react').title, 'React');
  assert.equal(presentation.getRequirementPlanItem(plan, 42, 'skill:react'), null);
  const v4Plan = {
    id: 44,
    schemaVersion: '4.0',
    requirementFacts: [{ factId: 'fact:0001', sources: [] }],
  };
  assert.equal(
    presentation.getRequirementPlanFact(v4Plan, 44, 'fact:0001').factId,
    'fact:0001',
  );
  assert.equal(presentation.getRequirementPlanFact(v4Plan, 45, 'fact:0001'), null);
  assert.equal(presentation.getScreeningStateLabel(null), '尚未初筛');
  assert.equal(presentation.getScreeningStateLabel({ report: { isOutdated: true }, latestRun: null }), '报告已过期');

  console.log('STAGE7_AI_SCREENING_PRESENTATION_TEST_OK');
} finally {
  await server.close();
}
