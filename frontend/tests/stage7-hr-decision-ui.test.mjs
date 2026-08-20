import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const baseItem = {
  application: {
    id: 41, candidateId: 8, jobId: 3, currentResumeId: 12, source: 'hr_screening',
    lifecycleStatus: 'active', recruitmentStage: 'hr_review', hrDecision: 'pending',
    appliedAt: '2026-08-19T08:00:00Z', createdAt: '2026-08-19T08:00:00Z',
    updatedAt: '2026-08-19T09:00:00Z',
  },
  candidateName: '虚构候选人', candidateTitle: '后端工程师', candidateSource: null,
  jobTitle: '平台后端工程师', jobDepartment: '研发部', jobStatus: 'open',
};
const server = await createServer({
  appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const decisions = await server.ssrLoadModule('/src/features/recruitment/screeningDecisionAction.ts');
  assert.deepEqual(decisions.getStage7DecisionEntry(baseItem, false), {
    allowed: true,
    label: '作出 HR 决策',
    reason: 'HR 可以独立决定通过、备选或淘汰，改变已有决定时需说明原因。',
  });
  assert.deepEqual(decisions.getStage7DecisionKinds(baseItem), ['pass', 'backup', 'reject']);
  assert.equal(decisions.getStage7DecisionEntry(baseItem, true).allowed, false);
  assert.equal(decisions.getStage7DecisionEntry({
    ...baseItem,
    application: { ...baseItem.application, lifecycleStatus: 'voided' },
  }, false).label, '申请已作废');

  assert.deepEqual(decisions.getStage7PassPolicy(baseItem), {
    reasonCode: 'meets_requirements', detailRequired: false, label: '符合岗位要求',
    note: 'HR 根据岗位要求和候选人材料独立判断。',
  });
  assert.deepEqual(decisions.buildStage7DecisionSubmission(baseItem, 'pass', null, '  '), {
    valid: true,
    submission: { action: 'pass', input: { reason_code: 'meets_requirements', reason_detail: null } },
  });
  assert.equal(decisions.buildStage7DecisionSubmission(baseItem, 'backup', null, '').valid, false);
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(baseItem, 'backup', 'waiting_for_comparison', ''),
    { valid: true, submission: {
      action: 'backup', input: { reason_code: 'waiting_for_comparison', reason_detail: null },
    } },
  );
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(baseItem, 'reject', 'role_mismatch', '候选人年龄不合适'),
    { valid: false, message: '决定说明不能使用“年龄”等与岗位能力无关的敏感依据。' },
  );

  const passedItem = {
    ...baseItem,
    application: { ...baseItem.application, recruitmentStage: 'screening_passed', hrDecision: 'passed' },
  };
  assert.deepEqual(decisions.getStage7DecisionKinds(passedItem), ['backup', 'reject']);
  assert.equal(
    decisions.buildStage7DecisionSubmission(passedItem, 'backup', 'limited_headcount', '').valid,
    false,
  );
  const rejectedItem = {
    ...baseItem,
    application: {
      ...baseItem.application, lifecycleStatus: 'ended', recruitmentStage: 'rejected',
      hrDecision: 'rejected',
    },
  };
  assert.equal(decisions.getStage7DecisionEntry(rejectedItem, false).label, '撤销淘汰');
  assert.deepEqual(decisions.getStage7DecisionKinds(rejectedItem), ['undo_rejection']);
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(
      rejectedItem, 'undo_rejection', 'new_evidence', '补充了可核对的岗位项目证据',
    ),
    { valid: true, submission: { action: 'undo_rejection', input: {
      reason_code: 'new_evidence', reason_detail: '补充了可核对的岗位项目证据',
    } } },
  );

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url), 'utf8',
  );
  for (const text of [
    'passStage7Application', 'backupStage7Application', 'rejectStage7Application',
    'undoStage7ApplicationRejection', 'HR 决策已保存，并写入阶段历史',
  ]) assert.ok(pageSource.includes(text), `HR 决策页面缺少交互边界：${text}`);
  console.log('STAGE7_HR_DECISION_UI_TEST_OK');
} finally {
  await server.close();
}
