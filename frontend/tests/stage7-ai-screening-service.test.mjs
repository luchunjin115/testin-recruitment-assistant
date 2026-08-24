import assert from 'node:assert/strict';
import { createServer } from 'vite';

const evidence = { quote: '负责 React 招聘系统交付', section: '项目经历' };
const plan = {
  id: 41, job_id: 7, jd_fingerprint: 'a'.repeat(64), status: 'ready', is_current: true,
  items: [{
    key: 'required_skill:react', title: 'React 开发能力', category: 'skill',
    priority: 'required', source_type: 'structured',
    source_field: 'requirements.required_skills', source_quote: null,
  }],
  structured_coverage: {
    source_schema_version: '1.0', all_covered: true,
    fields: [{ source_field: 'requirements.required_skills', source_value_count: 1, item_keys: ['required_skill:react'] }],
  },
  warnings: [], prompt_version: 'plan-v1', model_version: 'fake-plan', schema_version: '1.0',
  contract_outdated: true,
  free_text_coverage: { rule_version: 'jd_source_units_v1', all_reviewed: true, units: [] },
  input_fingerprint: 'b'.repeat(64),
  input_snapshot: {
    job_id: 7, title: '前端工程师', department: '研发部', description: '负责前端',
    requirements: {
      schema_version: '1.0', responsibilities: ['交付功能'], required_skills: ['React'],
      preferred_skills: [], minimum_work_years: null, education_requirement: null,
      required_experiences: [], preferred_experiences: [], keywords: [], additional_requirements: [],
    },
  },
  error_code: null, error_message: null, created_at: '2026-08-20T08:00:00Z',
  completed_at: '2026-08-20T08:01:00Z', updated_at: '2026-08-20T08:01:00Z',
};
const report = {
  id: 51, application_id: 11, job_id: 7, resume_id: 5, job_evaluation_plan_id: 41,
  overall_score: 78, display_label: '整体较匹配', overall_summary: '岗位匹配总结',
  requirement_assessments: [{
    requirement_key: 'required_skill:react', score: 8, reason: '有可核对项目',
    calculation_note: '结合项目复杂度判断', experience_period_fact_keys: [], evidence: [evidence],
  }],
  bonus_highlights: [{ title: '跨团队协作', score: 8, reason: '有实际记录', evidence: [evidence] }],
  tradeoff_reason: '工程能力可部分弥补行业经验差距', interview_questions: ['请说明项目贡献。'],
  input_fingerprint: 'c'.repeat(64), jd_fingerprint: 'a'.repeat(64),
  plan_fingerprint: 'd'.repeat(64), resume_fingerprint: 'e'.repeat(64),
  prompt_version: 'screening_evaluation_v3', model_version: 'fake-screen', schema_version: '2.0', redaction_version: 'redact-v1',
  evaluation_reference_at: '2026-08-19T16:00:00Z', evaluation_timezone: 'Asia/Shanghai',
  experience_period_facts_rule_version: 'experience_period_facts_v1',
  is_outdated: true, outdated_reasons: ['resume_changed'], outdated_at: '2026-08-20T09:00:00Z',
  generated_at: '2026-08-20T08:10:00Z', updated_at: '2026-08-20T09:00:00Z',
};
const run = {
  id: 61, application_id: 11, job_id: 7, resume_id: 5, job_evaluation_plan_id: 41,
  trigger_type: 'single_reassessment', status: 'queued', waiting_reason: null, input_fingerprint: 'f'.repeat(64),
  prompt_version: 'screening_evaluation_v3', model_version: 'fake-screen', schema_version: '2.0', redaction_version: 'redact-v1',
  evaluation_reference_at: '2026-08-19T16:00:00Z', evaluation_timezone: 'Asia/Shanghai',
  experience_period_facts_rule_version: 'experience_period_facts_v1',
  experience_period_facts_fingerprint: '1'.repeat(64),
  started_at: null, completed_at: null, error_code: null, error_message: null,
  input_tokens: null, output_tokens: null, duration_ms: null, attempt_count: 0,
  created_at: '2026-08-20T09:01:00Z', updated_at: '2026-08-20T09:01:00Z',
};
const failedRun = {
  ...run, id: 62, application_id: 12, status: 'failed',
  error_code: 'SCREENING_MODEL_INVALID_RESPONSE', error_message: 'AI 返回内容未通过校验',
  completed_at: '2026-08-20T09:02:00Z', updated_at: '2026-08-20T09:02:00Z',
};

const server = await createServer({
  appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const service = await server.ssrLoadModule('/src/features/recruitment/services/aiScreening.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    let data;
    if (config.url?.includes('evaluation-plan')) data = plan;
    else if (config.url === '/applications/11/screening' && config.method === 'get') {
      data = { application_id: 11, report, latest_run: run };
    } else if (config.url === '/jobs/7/screening/re-evaluate-batch') {
      data = { job_id: 7, results: [
        { application_id: 11, run, report, reused_report: false, reused_run: false },
        { application_id: 12, run: failedRun, report: null, reused_report: false, reused_run: false },
      ] };
    } else if (config.url === '/applications/11/current-resume') {
      data = { id: 11 };
    } else {
      data = { application_id: 11, run, report, reused_report: false, reused_run: false };
    }
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };

  const mappedPlan = await service.getJobEvaluationPlan(7);
  assert.equal(mappedPlan.items[0].historicalSource.field, 'requirements.required_skills');
  assert.deepEqual(mappedPlan.items[0].sources, []);
  assert.equal(mappedPlan.structuredCoverage.allCovered, true);
  assert.equal(mappedPlan.contractOutdated, true);
  assert.equal('freeTextCoverage' in mappedPlan, false);
  assert.equal(mappedPlan.inputSnapshot.requirements.required_skills[0], 'React');
  await service.generateJobEvaluationPlan(7);
  await service.regenerateJobEvaluationPlan(7);

  const state = await service.getApplicationScreening(11);
  assert.equal(state.report.overallScore, 78);
  assert.equal(state.report.displayLabel, '整体较匹配');
  assert.equal(state.report.requirementAssessments[0].calculationNote, '结合项目复杂度判断');
  assert.deepEqual(state.report.requirementAssessments[0].experiencePeriodFactKeys, []);
  assert.equal(state.report.evaluationReferenceAt, '2026-08-19T16:00:00Z');
  assert.equal(state.report.evaluationTimezone, 'Asia/Shanghai');
  assert.equal(state.report.experiencePeriodFactsRuleVersion, 'experience_period_facts_v1');
  assert.equal(state.report.bonusHighlights[0].evidence[0].section, '项目经历');
  assert.deepEqual(state.report.outdatedReasons, ['resume_changed']);
  assert.equal(state.latestRun.status, 'queued');
  assert.equal(state.latestRun.waitingReason, null);
  assert.equal(state.latestRun.triggerType, 'single_reassessment');
  assert.equal(state.latestRun.evaluationReferenceAt, '2026-08-19T16:00:00Z');
  assert.equal(state.latestRun.experiencePeriodFactsFingerprint, '1'.repeat(64));

  await service.triggerApplicationScreening(11);
  await service.reassessApplicationScreening(11);
  const batch = await service.reassessJobApplications(7, [11, 12]);
  assert.equal(batch.results[0].run.id, 61);
  assert.equal(batch.results[0].run.status, 'queued');
  assert.equal(batch.results[1].run.status, 'failed');
  assert.equal(batch.results[0].report.id, 51);
  assert.equal(batch.results[1].report, null);
  await service.switchApplicationCurrentResume(11, 9);

  assert.deepEqual(requests.map(request => [request.method, request.url]), [
    ['get', '/jobs/7/evaluation-plan'],
    ['post', '/jobs/7/evaluation-plan/generate'],
    ['post', '/jobs/7/evaluation-plan/regenerate'],
    ['get', '/applications/11/screening'],
    ['post', '/applications/11/screening'],
    ['post', '/applications/11/screening/re-evaluate'],
    ['post', '/jobs/7/screening/re-evaluate-batch'],
    ['put', '/applications/11/current-resume'],
  ]);
  assert.deepEqual(JSON.parse(requests[6].data), { application_ids: [11, 12] });
  assert.deepEqual(JSON.parse(requests[7].data), { resume_id: 9 });

  const safe = service.getAIScreeningApiError({
    isAxiosError: true,
    response: { status: 409, data: { detail: { code: 'SCREENING_JOB_CLOSED', message: '岗位关闭时不能重新评估' } } },
  });
  assert.deepEqual(safe, { status: 409, code: 'SCREENING_JOB_CLOSED', message: '岗位关闭时不能重新评估' });
  const hidden = service.getAIScreeningApiError(new Error('postgresql://secret'));
  assert.equal(hidden.message.includes('secret'), false);

  console.log('STAGE7_AI_SCREENING_SERVICE_TEST_OK');
} finally {
  await server.close();
}
