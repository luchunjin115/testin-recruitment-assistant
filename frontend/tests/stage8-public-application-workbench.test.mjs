import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const run = {
  id: 51,
  trigger_type: 'automatic',
  status: 'paused',
  current_step: 'trigger_screening',
  attempt_count: 1,
  waiting_reason: 'job_closed',
  error_code: null,
  error_message: null,
  warning_codes: ['RESUME_STRUCTURE_FAILED'],
  started_at: '2026-09-02T10:00:00Z',
  completed_at: null,
  created_at: '2026-09-02T09:59:00Z',
  updated_at: '2026-09-02T10:01:00Z',
};
const summary = {
  submission_id: 41,
  submission_reference: 'AP-STAGE8E001',
  submitted_at: '2026-09-02T09:59:00Z',
  identity_review_status: 'needs_review',
  identity_review_reasons: ['same_name'],
  application_id: 31,
  candidate_id: 5,
  resume_id: 8,
  job_id: 2,
  candidate_name: '虚构候选人',
  job_title: '虚构后端岗位',
  job_status: 'closed',
  resume_filename: 'fictional.txt',
  resume_parse_status: 'parsed',
  lifecycle_status: 'active',
  recruitment_stage: 'applied',
  hr_decision: 'pending',
  latest_run: run,
};

const server = await createServer({
  appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const service = await server.ssrLoadModule(
    '/src/features/recruitment/services/publicApplicationWorkbench.ts',
  );
  const resumes = await server.ssrLoadModule('/src/features/recruitment/services/resumes.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    if (config.url === '/public-application-submissions') {
      return { config, data: [summary], headers: {}, status: 200, statusText: 'OK' };
    }
    if (config.url === '/public-application-submissions/41') {
      return {
        config,
        data: {
          ...summary,
          processing_runs: [run],
          identity_candidates: [{
            id: 5, name: '虚构候选人', phone: '13800000000', email: 'fake@example.com',
            source: 'public_apply', created_at: '2026-09-02T09:59:00Z',
            is_submission_candidate: true,
          }],
        },
        headers: {}, status: 200, statusText: 'OK',
      };
    }
    if (config.url.endsWith('/identity-review')) {
      return {
        config,
        data: {
          ...summary, identity_review_status: 'reviewed', processing_runs: [run],
          identity_candidates: [],
        },
        headers: {}, status: 200, statusText: 'OK',
      };
    }
    if (config.url.endsWith('/retry')) {
      return {
        config,
        data: { ...run, id: 52, trigger_type: 'manual_retry', status: 'queued', waiting_reason: null },
        headers: {}, status: 201, statusText: 'Created',
      };
    }
    if (config.url === '/resumes/8/structure') {
      return {
        config,
        data: {
          resume_id: 8, structure_status: 'succeeded', structure_error: null,
          from_cache: true, has_previous_draft: true, performance: null,
          draft: {
            schema_version: '1.0', basic_info: { name: '虚构候选人' }, education_records: [],
            work_experiences: [], project_experiences: [], skills: ['Python'], certifications: [],
            self_evaluation: null, warnings: [], missing_fields: [],
          },
        },
        headers: {}, status: 200, statusText: 'OK',
      };
    }
    throw new Error(`unexpected request: ${config.url}`);
  };

  const listed = await service.listPublicApplicationSubmissions();
  assert.equal(listed[0].submissionReference, 'AP-STAGE8E001');
  assert.equal(listed[0].latestRun.currentStep, 'trigger_screening');
  assert.equal(service.isPublicApplicationException(listed[0]), true);

  const detail = await service.getPublicApplicationSubmission(41);
  assert.equal(detail.processingRuns[0].id, 51);
  assert.equal(detail.identityCandidates[0].isSubmissionCandidate, true);

  const reviewed = await service.markPublicApplicationIdentityReviewed(41);
  assert.equal(reviewed.identityReviewStatus, 'reviewed');
  const retried = await service.retryPublicApplicationProcessing(41);
  assert.equal(retried.triggerType, 'manual_retry');
  assert.equal(retried.id, 52);
  assert.deepEqual(requests[2].data, JSON.stringify({ confirmed: true }));
  assert.deepEqual(requests[3].data, JSON.stringify({ confirmed: true }));

  const stored = await resumes.getStoredRecruitmentResumeStructure(8);
  assert.equal(stored.from_cache, true);
  assert.equal(requests.at(-1).method, 'get');
  assert.equal(requests.at(-1).url, '/resumes/8/structure');

  const hidden = service.getPublicApplicationWorkbenchError({
    isAxiosError: true,
    response: { status: 500, data: { detail: { code: 'DATABASE_SECRET', message: 'C:/secret' } } },
  });
  assert.equal(hidden.code, null);
  assert.equal(hidden.message, '公开投递状态读取失败，请稍后重试');

  const [centerSource, drawerSource, panelSource, screeningServiceSource] = await Promise.all([
    readFile(new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/ApplicationScreeningDrawer.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/PublicApplicationProcessingPanel.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/services/screening.ts', import.meta.url), 'utf8'),
  ]);
  for (const text of [
    '全部来源', '公开投递 · 正常', '公开投递 · 需人工处理',
    '查看处理与 AI 报告', 'getPublicApplicationSubmission',
  ]) assert.ok(centerSource.includes(text), `统一初筛中心缺少：${text}`);
  assert.ok(drawerSource.includes('PublicApplicationProcessingPanel'));
  assert.ok(screeningServiceSource.includes('listPublicApplicationSubmissions'));
  assert.equal(centerSource.includes('公开投递工作区'), false);
  assert.equal(centerSource.includes('<Tabs'), false);
  for (const text of [
    'POLL_INTERVAL_MS = 4_000', 'POLL_LIMIT = 30', '标记身份已核对',
    '人工重试', '选择当前简历', '这里只读取已保存结果，不会启动新的 AI 调用',
  ]) assert.ok(panelSource.includes(text), `公开投递详情缺少：${text}`);
  assert.equal(panelSource.includes('structureRecruitmentResume'), false);

  console.log('STAGE8_PUBLIC_APPLICATION_WORKBENCH_TEST_OK');
} finally {
  await server.close();
}
