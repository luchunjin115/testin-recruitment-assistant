import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { createServer } from 'vite';

const read = path => readFile(new URL(path, import.meta.url), 'utf8');
const [typesSource, serviceSource, planSource, drawerSource, reportSource, centerSource, decisionSource, stylesSource] = await Promise.all([
  read('../src/features/recruitment/types/aiScreening.ts'),
  read('../src/features/recruitment/services/aiScreening.ts'),
  read('../src/features/recruitment/JobEvaluationPlanDrawer.tsx'),
  read('../src/features/recruitment/ApplicationScreeningDrawer.tsx'),
  read('../src/features/recruitment/ScreeningReportView.tsx'),
  read('../src/features/recruitment/RecruitmentScreeningCenter.tsx'),
  read('../src/features/recruitment/screeningDecisionAction.ts'),
  read('../src/features/recruitment/styles/screening.css'),
]);

test('7R5-G 静态合同覆盖 5.0 编辑、报告、历史、五人批量和安全边界', () => {
  for (const token of [
    "'5.0'", 'V5Criterion', 'V5CriterionDraft', 'ScreeningV5Report',
    'v5Criteria', 'editVersion', 'confirmedAt', 'v5Report', 'isCurrent',
    'strengths', 'gaps', 'risksOrConflicts', 'missingInfo', 'hrFollowUpQuestions',
  ]) assert.ok(typesSource.includes(token), `类型缺少 ${token}`);
  for (const token of [
    '/evaluation-plan/draft', '/evaluation-plan/versions', '/evaluation-plans',
    '/screening/reports', 'edit_version', 'confirmed: true', 'failed_count', 'failures',
  ]) assert.ok(serviceSource.includes(token), `Service 缺少 ${token}`);
  for (const token of [
    '编辑清单', '新增评价点', '删除', '合并选中', '保存草稿', '创建新编辑版本',
    'HR 补充', 'AI 来源 · JD', 'importance_review_required', '只读版本历史',
  ]) assert.ok(planSource.includes(token), `计划页面缺少 ${token}`);
  for (const token of ['成功报告历史', '历史只读报告', 'listApplicationScreeningReports']) {
    assert.ok(drawerSource.includes(token), `报告抽屉缺少 ${token}`);
  }
  for (const token of [
    '评价点逐项结论', '主要优势', '主要差距', '风险与事实冲突', '缺失信息',
    'HR 后续核实', '不平均、不加权、不重算', '来自 JD', 'HR 补充',
  ]) assert.ok(reportSource.includes(token), `5.0 报告缺少 ${token}`);
  for (const token of ['最多选择 5 份申请', 'failedCount', 'failures.map', 'AI 评估进行中']) {
    assert.ok(`${centerSource}${serviceSource}${decisionSource}`.includes(token), `初筛中心缺少 ${token}`);
  }
  for (const selector of ['.recruitment-v5-report-grid', '.recruitment-screening-report-history']) {
    assert.ok(stylesSource.includes(selector), `样式缺少 ${selector}`);
  }
  const runtime = `${typesSource}${serviceSource}${planSource}${drawerSource}${reportSource}${centerSource}`;
  for (const forbidden of ['dangerouslySetInnerHTML', 'rawResponse', 'apiKey', 'weightedScore']) {
    assert.equal(runtime.includes(forbidden), false, `运行边界出现禁止内容 ${forbidden}`);
  }
  assert.equal(/\bfetch\s*\(/.test(`${planSource}${drawerSource}${reportSource}${centerSource}`), false);
  assert.equal(/:\s*any\b/.test(runtime), false);
});

const source = { source_field: 'candidate_requirements', source_quote: '必须具备 Python 后端开发经验' };
const criterion = {
  criterion_id: 'criterion:0001', name: 'Python 后端经验', importance: 'required',
  description: '核对后端交付经验', screening_focus: '寻找可定位项目与职责',
  origin: 'ai_from_jd', sources: [source], hr_note: null,
};
const snapshot = {
  schema_version: '5.0',
  job_context: { title: '后端工程师', department: '研发部', job_background: '建设业务平台' },
  evaluation_fields: {
    job_responsibilities: '负责平台建设',
    candidate_requirements: '必须具备 Python 后端开发经验',
    preferred_qualifications: null,
  },
  source_units: [{
    source_unit_id: 'candidate_requirements:0001', source_field: 'candidate_requirements',
    ordinal: 1, source_text: '必须具备 Python 后端开发经验',
  }],
};
const plan = {
  id: 81, job_id: 7, jd_fingerprint: 'a'.repeat(64), status: 'pending_confirmation', is_current: true,
  items: null, structured_coverage: null, source_review_summary: null, requirement_facts: null,
  evaluation_criteria: null, coverage_review_summary: null, generation_audit: null,
  v5_criteria: [criterion], edit_version: 2, confirmed_at: null,
  warnings: [{
    code: 'importance_review_required', message: '请复核重要程度', criterion_id: 'criterion:0001',
    reasons: ['explicit_strong_signal_mismatch'],
  }],
  prompt_version: 'job_evaluation_plan_lightweight_v2', model_version: 'fake-plan', schema_version: '5.0',
  input_fingerprint: 'b'.repeat(64), input_snapshot: snapshot, contract_outdated: false,
  error_code: null, error_message: null, created_at: '2026-08-27T01:00:00Z',
  completed_at: '2026-08-27T01:01:00Z', updated_at: '2026-08-27T01:01:00Z',
};
const evidence = { quote: '使用 Python 负责订单服务开发与上线', section: '工作经历' };
const report = {
  id: 91, application_id: 11, job_id: 7, resume_id: 5, job_evaluation_plan_id: 81,
  overall_score: 76, display_label: '整体较匹配', overall_summary: '当前简历具备主要后端证据。',
  requirement_assessments: [], bonus_highlights: [], tradeoff_reason: null, interview_questions: [],
  input_fingerprint: 'c'.repeat(64), jd_fingerprint: 'a'.repeat(64), plan_fingerprint: 'd'.repeat(64), resume_fingerprint: 'e'.repeat(64),
  prompt_version: 'screening_evaluation_lightweight_v1', model_version: 'fake-screen', schema_version: '5.0', redaction_version: 'redact-v1',
  evaluation_reference_at: '2026-08-26T16:00:00Z', evaluation_timezone: 'Asia/Shanghai', experience_period_facts_rule_version: 'experience_period_facts_v1',
  v5_report: {
    overall_score: 76, display_label: '整体较匹配', overall_summary: '当前简历具备主要后端证据。',
    criterion_assessments: [{
      criterion,
      assessment: { criterion_id: 'criterion:0001', score: 8, reason: '有可定位项目证据', calculation_note: null, experience_period_fact_keys: [], evidence: [evidence] },
    }],
    strengths: [{ summary: '具备 Python 服务交付证据', criterion_ids: ['criterion:0001'], evidence: [evidence] }],
    gaps: [{ summary: '高并发规模未说明', criterion_ids: ['criterion:0001'], evidence: [] }],
    risks_or_conflicts: [], missing_info: [{ summary: '需确认团队规模', criterion_ids: [], evidence: [] }],
    hr_follow_up_questions: ['请说明订单服务的规模与个人职责。'],
  },
  is_current: true, is_outdated: false, outdated_reasons: [], outdated_at: null,
  generated_at: '2026-08-27T01:05:00Z', updated_at: '2026-08-27T01:05:00Z',
};
const run = {
  id: 101, application_id: 11, job_id: 7, resume_id: 5, job_evaluation_plan_id: 81,
  trigger_type: 'single_reassessment', status: 'queued', waiting_reason: null,
  input_fingerprint: 'f'.repeat(64), prompt_version: 'screening_evaluation_lightweight_v1',
  model_version: 'fake-screen', schema_version: '5.0', redaction_version: 'redact-v1',
  evaluation_reference_at: '2026-08-26T16:00:00Z', evaluation_timezone: 'Asia/Shanghai',
  experience_period_facts_rule_version: 'experience_period_facts_v1', experience_period_facts_fingerprint: '1'.repeat(64),
  started_at: null, completed_at: null, error_code: null, error_message: null,
  input_tokens: null, output_tokens: null, duration_ms: null, attempt_count: 0,
  created_at: '2026-08-27T01:06:00Z', updated_at: '2026-08-27T01:06:00Z',
};

test('7R5-G Service 映射严格 5.0 合同并发送确认字段', async () => {
  const server = await createServer({ appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(), server: { middlewareMode: true } });
  try {
    const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
    const service = await server.ssrLoadModule('/src/features/recruitment/services/aiScreening.ts');
    const requests = [];
    v2Http.defaults.adapter = async config => {
      requests.push(config);
      let data;
      if (config.url === '/jobs/7/evaluation-plans') data = [plan];
      else if (config.url === '/applications/11/screening/reports') data = [report];
      else if (config.url === '/applications/11/screening') data = { application_id: 11, report, latest_run: run };
      else if (config.url === '/jobs/7/screening/re-evaluate-batch') data = {
        job_id: 7, total_count: 2, reused_count: 0, queued_count: 1, failed_count: 1,
        results: [{ application_id: 11, run, report, reused_report: false, reused_run: false }],
        failures: [{ application_id: 12, error_code: 'SCREENING_PLAN_NOT_READY', error_message: '评价清单尚未确认', retryable: true }],
      };
      else data = plan;
      return { config, data, headers: {}, status: 200, statusText: 'OK' };
    };

    const mapped = service.mapJobEvaluationPlan(plan);
    assert.equal(mapped.schemaVersion, '5.0');
    assert.equal(mapped.v5Criteria[0].screeningFocus, '寻找可定位项目与职责');
    assert.equal(mapped.warnings[0].criterionId, 'criterion:0001');
    assert.deepEqual(mapped.warnings[0].reasons, ['explicit_strong_signal_mismatch']);
    assert.equal(mapped.inputSnapshot.schemaVersion, '5.0');

    await service.confirmJobEvaluationPlan(7, 2);
    await service.saveJobEvaluationPlanDraft(7, 2, [{
      criterionId: 'criterion:0001', name: 'Python 后端经验', importance: 'required',
      description: '核对后端交付经验', screeningFocus: '寻找项目证据', origin: 'ai_from_jd',
      sources: [{ sourceField: 'candidate_requirements', sourceQuote: source.source_quote }], hrNote: null,
    }]);
    await service.createJobEvaluationPlanVersion(7, 2);
    assert.equal((await service.listJobEvaluationPlans(7)).length, 1);
    const state = await service.getApplicationScreening(11);
    assert.equal(state.report.v5Report.criterionAssessments[0].assessment.score, 8);
    assert.equal(state.report.v5Report.strengths[0].criterionIds[0], 'criterion:0001');
    assert.equal((await service.listApplicationScreeningReports(11))[0].isCurrent, true);
    const batch = await service.reassessJobApplications(7, [11, 12]);
    assert.deepEqual([batch.totalCount, batch.queuedCount, batch.failedCount], [2, 1, 1]);
    assert.equal(batch.failures[0].retryable, true);

    const bodies = requests.map(request => request.data && JSON.parse(request.data));
    assert.deepEqual(bodies[0], { edit_version: 2 });
    assert.equal(bodies[1].edit_version, 2);
    assert.equal(bodies[1].criteria[0].screening_focus, '寻找项目证据');
    assert.deepEqual(bodies[2], { edit_version: 2 });
    assert.deepEqual(bodies.at(-1), { application_ids: [11, 12], confirmed: true });
  } finally {
    await server.close();
  }
});
