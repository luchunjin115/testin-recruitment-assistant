import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';


const baseItem = {
  application: {
    id: 41,
    candidateId: 8,
    jobId: 3,
    currentResumeId: 12,
    source: 'hr_screening',
    lifecycleStatus: 'active',
    recruitmentStage: 'hr_review',
    aiStatus: 'completed',
    hrDecision: 'pending',
    currentScreeningResultId: 101,
    appliedAt: '2026-08-19T08:00:00Z',
    createdAt: '2026-08-19T08:00:00Z',
    updatedAt: '2026-08-19T09:00:00Z',
  },
  candidateName: '虚构候选人',
  candidateTitle: '后端工程师',
  candidateSource: null,
  jobTitle: '平台后端工程师',
  jobDepartment: '研发部',
  jobStatus: 'open',
  currentResult: {
    id: 101,
    candidateId: 8,
    jobId: 3,
    applicationId: 41,
    resumeId: 12,
    attemptNumber: 1,
    executionStatus: 'completed',
    overallScore: 86,
    hardPass: true,
    recommendation: 'recommend',
    evidenceCoverageRate: 0.8,
    errorCode: null,
    errorMessage: null,
    startedAt: '2026-08-19T08:59:00Z',
    finishedAt: '2026-08-19T09:00:00Z',
    durationMs: 60_000,
    triggerReason: 'initial',
    forceRerun: false,
    isOutdated: false,
    outdatedAt: null,
    createdAt: '2026-08-19T08:59:00Z',
    updatedAt: '2026-08-19T09:00:00Z',
  },
};

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const decisions = await server.ssrLoadModule('/src/features/recruitment/screeningDecisionAction.ts');

  assert.deepEqual(decisions.getStage7DecisionEntry(baseItem, false), {
    allowed: true,
    label: '作出 HR 决策',
    reason: '结合评分证据决定通过、备选或淘汰。',
  });
  assert.deepEqual(decisions.getStage7DecisionKinds(baseItem), ['pass', 'backup', 'reject']);
  assert.equal(decisions.getStage7DecisionEntry(baseItem, true).allowed, false);
  assert.equal(decisions.getStage7DecisionEntry({
    ...baseItem,
    application: { ...baseItem.application, aiStatus: 'screening' },
  }, false).label, '等待评分');
  assert.equal(decisions.getStage7DecisionEntry({
    ...baseItem,
    application: { ...baseItem.application, lifecycleStatus: 'voided' },
  }, false).label, '申请已作废');

  assert.deepEqual(decisions.getStage7PassPolicy(baseItem), {
    reasonCode: 'meets_requirements',
    detailRequired: false,
    label: '符合岗位要求',
    note: '当前 AI 结论、硬性条件和证据覆盖率支持通过。',
  });
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(baseItem, 'pass', null, '  '),
    {
      valid: true,
      submission: {
        action: 'pass',
        input: { reason_code: 'meets_requirements', reason_detail: null },
      },
    },
  );

  const lowMatchItem = {
    ...baseItem,
    currentResult: { ...baseItem.currentResult, recommendation: 'low_match', hardPass: false },
  };
  assert.equal(
    decisions.buildStage7DecisionSubmission(lowMatchItem, 'pass', null, '').valid,
    false,
  );
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(lowMatchItem, 'pass', null, '  HR 核对了岗位相关补充证据  '),
    {
      valid: true,
      submission: {
        action: 'pass',
        input: {
          reason_code: 'manual_override',
          reason_detail: 'HR 核对了岗位相关补充证据',
        },
      },
    },
  );

  assert.equal(decisions.buildStage7DecisionSubmission(baseItem, 'backup', null, '').valid, false);
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(baseItem, 'backup', 'waiting_for_comparison', ''),
    {
      valid: true,
      submission: {
        action: 'backup',
        input: { reason_code: 'waiting_for_comparison', reason_detail: null },
      },
    },
  );
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(baseItem, 'reject', 'role_mismatch', '岗位经历方向不匹配'),
    {
      valid: true,
      submission: {
        action: 'reject',
        input: {
          reason_code: 'role_mismatch',
          reason_detail: '岗位经历方向不匹配',
          confirmed: true,
        },
      },
    },
  );
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(baseItem, 'reject', 'role_mismatch', '候选人年龄不合适'),
    {
      valid: false,
      message: '决定说明不能使用“年龄”等与岗位能力无关的敏感依据。',
    },
  );
  assert.equal(
    decisions.buildStage7DecisionSubmission(
      lowMatchItem,
      'pass',
      null,
      'HR reviewed managed service delivery evidence',
    ).valid,
    true,
  );

  const passedItem = {
    ...baseItem,
    application: {
      ...baseItem.application,
      recruitmentStage: 'screening_passed',
      hrDecision: 'passed',
    },
  };
  assert.deepEqual(decisions.getStage7DecisionKinds(passedItem), ['backup', 'reject']);
  assert.equal(
    decisions.buildStage7DecisionSubmission(passedItem, 'backup', 'limited_headcount', '').valid,
    false,
  );

  const rejectedItem = {
    ...baseItem,
    application: {
      ...baseItem.application,
      lifecycleStatus: 'ended',
      recruitmentStage: 'rejected',
      hrDecision: 'rejected',
    },
  };
  assert.equal(decisions.getStage7DecisionEntry(rejectedItem, false).label, '撤销淘汰');
  assert.deepEqual(decisions.getStage7DecisionKinds(rejectedItem), ['undo_rejection']);
  assert.equal(
    decisions.buildStage7DecisionSubmission(rejectedItem, 'undo_rejection', 'new_evidence', '').valid,
    false,
  );
  assert.deepEqual(
    decisions.buildStage7DecisionSubmission(
      rejectedItem,
      'undo_rejection',
      'new_evidence',
      '补充了可核对的岗位项目证据',
    ),
    {
      valid: true,
      submission: {
        action: 'undo_rejection',
        input: {
          reason_code: 'new_evidence',
          reason_detail: '补充了可核对的岗位项目证据',
        },
      },
    },
  );

  assert.match(
    decisions.getStage7DecisionErrorMessage('INVALID_APPLICATION_TRANSITION', '状态不允许'),
    /刷新后重新确认/,
  );

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url),
    'utf8',
  );
  for (const text of [
    'passStage7Application',
    'backupStage7Application',
    'rejectStage7Application',
    'undoStage7ApplicationRejection',
    'HR 初筛决策单',
    '淘汰是高风险决定',
    'AI 评分只提供证据和建议',
    'decisionGuardRef',
  ]) {
    assert.ok(pageSource.includes(text), `HR 决策页面缺少交互边界：${text}`);
  }

  const styles = await readFile(
    new URL('../src/features/recruitment/styles/screening.css', import.meta.url),
    'utf8',
  );
  assert.match(styles, /\.recruitment-decision-options\s*\{/s);
  assert.match(styles, /\.recruitment-decision-options\s*>\s*button:focus-visible\s*\{/s);
  assert.match(styles, /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-decision-options\s*\{/s);

  console.log('STAGE7_HR_DECISION_UI_TEST_OK');
} finally {
  await server.close();
}
