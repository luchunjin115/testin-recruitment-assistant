import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const port = Number(process.env.STAGE7_BROWSER_FIXTURE_PORT || 5174);
const dist = resolve(fileURLToPath(new URL('../frontend/dist/', import.meta.url)));
const fixtureMode = process.env.STAGE7_BROWSER_FIXTURE_MODE || 'populated';
const iso = '2026-08-27T08:00:00Z';

const job = {
  id: 1,
  title: '虚构企业前端工程师',
  department: '产品研发部',
  location: '上海 / 可混合办公',
  employment_type: 'full_time',
  headcount: 2,
  job_background: '为虚构招聘工作台建设复杂业务前端；本段只提供岗位背景。',
  job_responsibilities: '负责 React 与 TypeScript 业务模块；与后端协作定义接口；保障可访问性与自动化测试。',
  candidate_requirements: '必须有 React 和 TypeScript 项目证据；能够独立排查线上问题；有跨团队协作经验。',
  preferred_qualifications: '熟悉性能优化更佳；具备设计系统经验更佳。',
  public_notes: '这是 7R5-G 浏览器验收夹具，不对应真实岗位。',
  status: 'open',
  created_at: iso,
  updated_at: iso,
};

const candidates = Array.from({ length: 6 }, (_, index) => ({
  id: 201 + index,
  name: `虚构候选人 A0${index + 1}`,
  email: null,
  phone: null,
  current_company: '虚构科技公司',
  current_title: index === 1 ? '质量工程师' : '前端工程师',
  work_years: 2 + index,
  education_level: 'bachelor',
  source: '7R5-G Fake 浏览器夹具',
  status: 'screening',
  applied_job_id: 1,
  resume_file_path: null,
  created_at: iso,
  updated_at: iso,
}));

const applications = candidates.map((candidate, index) => ({
  id: 101 + index,
  candidate_id: candidate.id,
  job_id: 1,
  current_resume_id: 301 + index,
  source: 'hr_screening',
  lifecycle_status: 'active',
  recruitment_stage: 'hr_review',
  hr_decision: index === 0 ? 'backup' : 'pending',
  applied_at: iso,
  created_at: iso,
  updated_at: iso,
}));

const sourceUnits = [
  ['resp-001', 'job_responsibilities', '负责 React 与 TypeScript 业务模块'],
  ['resp-002', 'job_responsibilities', '与后端协作定义接口'],
  ['resp-003', 'job_responsibilities', '保障可访问性与自动化测试'],
  ['req-001', 'candidate_requirements', '必须有 React 和 TypeScript 项目证据'],
  ['req-002', 'candidate_requirements', '能够独立排查线上问题'],
  ['req-003', 'candidate_requirements', '有跨团队协作经验'],
  ['pref-001', 'preferred_qualifications', '熟悉性能优化更佳'],
  ['pref-002', 'preferred_qualifications', '具备设计系统经验更佳'],
].map(([source_unit_id, source_field, source_text], index) => ({
  source_unit_id,
  source_field,
  ordinal: index + 1,
  source_text,
}));

const baseCriteria = [
  ['criterion-react-ts', 'React 与 TypeScript 交付', 'required', '能够用 React 与 TypeScript 交付复杂业务模块', '核对项目职责、技术选择和可验证结果', 'candidate_requirements', '必须有 React 和 TypeScript 项目证据'],
  ['criterion-api', '接口协作能力', 'general', '能够与后端共同定义和联调接口', '核对接口设计、错误处理和协作边界', 'job_responsibilities', '与后端协作定义接口'],
  ['criterion-quality', '可访问性与测试', 'general', '能够用测试与可访问性实践保障质量', '核对自动化测试范围与无障碍实践', 'job_responsibilities', '保障可访问性与自动化测试'],
  ['criterion-debug', '线上问题排查', 'required', '能够独立定位并解决线上问题', '核对具体故障、定位过程和结果', 'candidate_requirements', '能够独立排查线上问题'],
  ['criterion-performance', '性能优化', 'preferred', '具备前端性能诊断与优化经验', '核对指标、方案与优化前后变化', 'preferred_qualifications', '熟悉性能优化更佳'],
].map(([criterion_id, name, importance, description, screening_focus, source_field, source_quote]) => ({
  criterion_id,
  name,
  importance,
  description,
  screening_focus,
  origin: 'ai_from_jd',
  sources: [{ source_field, source_quote }],
  hr_note: null,
}));

const inputSnapshot = {
  schema_version: '5.0',
  job_context: { title: job.title, department: job.department, job_background: job.job_background },
  evaluation_fields: {
    job_responsibilities: job.job_responsibilities,
    candidate_requirements: job.candidate_requirements,
    preferred_qualifications: job.preferred_qualifications,
  },
  source_units: sourceUnits,
};

const makePlan = ({ id = 401, status = 'pending_confirmation', isCurrent = true, criteria = baseCriteria, editVersion = 3, schemaVersion = '5.0' } = {}) => ({
  id,
  job_id: 1,
  jd_fingerprint: 'a'.repeat(64),
  status,
  is_current: isCurrent,
  items: [],
  structured_coverage: null,
  source_review_summary: null,
  requirement_facts: [],
  evaluation_criteria: [],
  coverage_review_summary: null,
  generation_audit: null,
  v5_criteria: schemaVersion === '5.0' ? criteria : null,
  edit_version: schemaVersion === '5.0' ? editVersion : null,
  confirmed_at: status === 'ready' ? iso : null,
  warnings: schemaVersion === '5.0' ? [{
    code: 'importance_review_required',
    message: '“接口协作能力”的重要程度需要 HR 复核。',
    source_unit_ids: ['resp-002'],
    fact_ids: [],
    criterion_id: 'criterion-api',
    reasons: ['no_explicit_signal_non_general'],
  }] : [],
  prompt_version: schemaVersion === '5.0' ? 'stage7_plan_v5_browser_fixture' : 'stage7_plan_v4_historical_fixture',
  model_version: 'fixture-model-no-network',
  schema_version: schemaVersion,
  input_fingerprint: 'b'.repeat(64),
  contract_outdated: false,
  input_snapshot: schemaVersion === '5.0' ? inputSnapshot : { ...inputSnapshot, schema_version: '4.0' },
  error_code: null,
  error_message: null,
  created_at: iso,
  completed_at: iso,
  updated_at: iso,
});

let currentPlan = makePlan();
const historicalPlan = makePlan({ id: 400, status: 'ready', isCurrent: false, schemaVersion: '4.0' });

const evidence = (quote, section = '项目经历') => [{ quote, section }];
const scores = [9, 7, 6, 8, 0];
const v5Assessments = baseCriteria.map((criterion, index) => ({
  criterion,
  assessment: {
    criterion_id: criterion.criterion_id,
    score: scores[index],
    reason: scores[index] === 0
      ? '当前简历未发现可定位的性能优化证据，不能据此断言候选人不会。'
      : ['有可定位的复杂表单项目及技术栈证据。', '有一次接口契约协作记录。', '简历提到测试，但可访问性细节不足。', '有一次生产故障排查记录。'][index],
    calculation_note: null,
    experience_period_fact_keys: index === 0 ? ['project:0:period'] : [],
    evidence: scores[index] === 0 ? [] : evidence([
      '使用 React 与 TypeScript 交付虚构审批平台。',
      '与后端共同定义错误码并完成联调。',
      '使用组件测试覆盖核心表单。',
      '定位缓存失效导致的页面异常并完成修复。',
    ][index]),
  },
}));

const makeReport = (id = 601, isCurrent = true, outdated = false) => ({
  id,
  application_id: 101,
  job_id: 1,
  resume_id: 301,
  job_evaluation_plan_id: 401,
  overall_score: 76,
  display_label: '较匹配',
  overall_summary: 'AI 建议分为 76 分。React 交付和问题排查证据较强，但性能优化信息缺失；这不是录用决定。',
  requirement_assessments: [],
  bonus_highlights: [],
  tradeoff_reason: null,
  interview_questions: [],
  input_fingerprint: 'c'.repeat(64),
  jd_fingerprint: 'a'.repeat(64),
  plan_fingerprint: 'd'.repeat(64),
  resume_fingerprint: 'e'.repeat(64),
  prompt_version: 'stage7_screening_v5_browser_fixture',
  model_version: 'fixture-model-no-network',
  schema_version: '5.0',
  redaction_version: 'screening_resume_redaction_v1',
  evaluation_reference_at: '2026-08-27T00:00:00Z',
  evaluation_timezone: 'Asia/Shanghai',
  experience_period_facts_rule_version: 'experience_period_facts_v1',
  v5_report: {
    overall_score: 76,
    display_label: '较匹配',
    overall_summary: 'React 交付和问题排查证据较强，但性能优化信息缺失，需要 HR 继续核实。',
    criterion_assessments: v5Assessments,
    strengths: [{ summary: 'React 与 TypeScript 交付证据清晰。', criterion_ids: ['criterion-react-ts'], evidence: evidence('使用 React 与 TypeScript 交付虚构审批平台。') }],
    gaps: [{ summary: '未发现性能优化证据。', criterion_ids: ['criterion-performance'], evidence: [] }],
    risks_or_conflicts: [{ summary: '简历写“独立负责”，但项目职责描述也提到三人协作，需要核实实际边界。', criterion_ids: ['criterion-debug'], evidence: evidence('与三人小组共同完成线上问题处理。') }],
    missing_info: [{ summary: '缺少性能指标和优化前后数据。', criterion_ids: ['criterion-performance'], evidence: [] }],
    hr_follow_up_questions: ['请说明一次性能优化的指标、方案与结果。', '请澄清线上问题排查中个人与团队的职责边界。'],
  },
  is_current: isCurrent,
  is_outdated: outdated,
  outdated_reasons: outdated ? ['evaluation_plan_changed'] : [],
  outdated_at: outdated ? iso : null,
  generated_at: iso,
  updated_at: iso,
});

const currentReport = makeReport();
const historicalReport = {
  ...makeReport(600, false, true),
  schema_version: '4.0',
  v5_report: null,
  overall_score: 68,
  display_label: '历史较匹配',
  overall_summary: '这是旧 4.0 只读报告，用于验证历史兼容。',
  requirement_assessments: [{
    requirement_key: 'historical:react',
    score: 7,
    reason: '旧报告中的历史判断。',
    calculation_note: null,
    experience_period_fact_keys: [],
    evidence: evidence('旧报告证据快照。'),
  }],
  interview_questions: ['这是旧报告中的历史问题。'],
};

const makeRun = (applicationId, status, waitingReason = null) => ({
  id: 700 + applicationId,
  application_id: applicationId,
  job_id: 1,
  resume_id: 200 + applicationId,
  job_evaluation_plan_id: 401,
  trigger_type: 'single_reassessment',
  status,
  waiting_reason: waitingReason,
  input_fingerprint: 'f'.repeat(64),
  prompt_version: 'stage7_screening_v5_browser_fixture',
  model_version: 'fixture-model-no-network',
  schema_version: '5.0',
  redaction_version: 'screening_resume_redaction_v1',
  evaluation_reference_at: '2026-08-27T00:00:00Z',
  evaluation_timezone: 'Asia/Shanghai',
  experience_period_facts_rule_version: 'experience_period_facts_v1',
  experience_period_facts_fingerprint: '9'.repeat(64),
  started_at: status === 'queued' || status.startsWith('waiting') ? null : iso,
  completed_at: status === 'succeeded' || status === 'failed' ? iso : null,
  error_code: status === 'failed' ? 'MODEL_RESPONSE_INVALID' : null,
  error_message: status === 'failed' ? 'Fake 内容校验失败；没有保存部分报告。' : null,
  input_tokens: null,
  output_tokens: null,
  duration_ms: status === 'succeeded' ? 830 : null,
  attempt_count: 1,
  created_at: iso,
  updated_at: iso,
});

const readBody = async request => {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  if (chunks.length === 0) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
};
const sendJson = (response, value, status = 200) => {
  response.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(value));
};
const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
};

createServer(async (request, response) => {
  const url = new URL(request.url || '/', `http://${request.headers.host}`);
  const path = url.pathname;

  if (request.method === 'GET' && path === '/api/v2/jobs') return sendJson(response, [job]);
  if (request.method === 'GET' && path === '/api/v2/candidates') return sendJson(response, fixtureMode === 'empty' ? [] : candidates);
  if (request.method === 'GET' && path === '/api/v2/applications') return sendJson(response, fixtureMode === 'empty' ? [] : applications);
  if (request.method === 'GET' && path === '/api/v2/jobs/1/evaluation-plan') return sendJson(response, currentPlan);
  if (request.method === 'GET' && path === '/api/v2/jobs/1/evaluation-plans') return sendJson(response, [currentPlan, historicalPlan]);

  if (request.method === 'PUT' && path === '/api/v2/jobs/1/evaluation-plan/draft') {
    const body = await readBody(request);
    currentPlan = makePlan({ criteria: body.criteria, editVersion: body.edit_version + 1 });
    return sendJson(response, currentPlan);
  }
  if (request.method === 'POST' && path === '/api/v2/jobs/1/evaluation-plan/confirm') {
    const body = await readBody(request);
    if (body.edit_version !== currentPlan.edit_version) {
      return sendJson(response, { detail: { code: 'PLAN_EDIT_VERSION_CONFLICT', message: '评价清单已被其他 HR 更新，请刷新后再试。' } }, 409);
    }
    currentPlan = makePlan({ status: 'ready', criteria: currentPlan.v5_criteria, editVersion: currentPlan.edit_version });
    return sendJson(response, currentPlan);
  }
  if (request.method === 'POST' && path === '/api/v2/jobs/1/evaluation-plan/versions') {
    currentPlan = makePlan({ id: currentPlan.id + 1, criteria: currentPlan.v5_criteria, editVersion: currentPlan.edit_version + 1 });
    return sendJson(response, currentPlan);
  }
  if (request.method === 'POST' && /^\/api\/v2\/jobs\/1\/evaluation-plan\/(generate|regenerate)$/.test(path)) {
    currentPlan = makePlan();
    return sendJson(response, currentPlan);
  }

  const screeningMatch = path.match(/^\/api\/v2\/applications\/(\d+)\/screening$/);
  if (request.method === 'GET' && screeningMatch) {
    const applicationId = Number(screeningMatch[1]);
    if (applicationId === 101) return sendJson(response, { application_id: applicationId, report: currentReport, latest_run: makeRun(applicationId, 'succeeded') });
    if (applicationId === 102) return sendJson(response, { application_id: applicationId, report: null, latest_run: makeRun(applicationId, 'failed') });
    if (applicationId === 103) return sendJson(response, { application_id: applicationId, report: null, latest_run: makeRun(applicationId, 'waiting_plan', 'plan_pending_confirmation') });
    return sendJson(response, { application_id: applicationId, report: null, latest_run: makeRun(applicationId, 'queued') });
  }
  const reportHistoryMatch = path.match(/^\/api\/v2\/applications\/(\d+)\/screening\/reports$/);
  if (request.method === 'GET' && reportHistoryMatch) {
    return sendJson(response, Number(reportHistoryMatch[1]) === 101 ? [currentReport, historicalReport] : []);
  }

  const reassessMatch = path.match(/^\/api\/v2\/applications\/(\d+)\/screening\/re-evaluate$/);
  if (request.method === 'POST' && reassessMatch) {
    const applicationId = Number(reassessMatch[1]);
    return sendJson(response, { application_id: applicationId, report: applicationId === 101 ? currentReport : null, run: makeRun(applicationId, 'queued'), reused_report: false, reused_run: false });
  }
  if (request.method === 'POST' && path === '/api/v2/jobs/1/screening/re-evaluate-batch') {
    const body = await readBody(request);
    const selected = body.application_ids || [];
    const failedId = selected.at(-1);
    const successIds = selected.slice(0, -1);
    return sendJson(response, {
      job_id: 1,
      total_count: selected.length,
      reused_count: 0,
      queued_count: successIds.length,
      failed_count: failedId === undefined ? 0 : 1,
      results: successIds.map(applicationId => ({ application_id: applicationId, report: applicationId === 101 ? currentReport : null, run: makeRun(applicationId, 'queued'), reused_report: false, reused_run: false })),
      failures: failedId === undefined ? [] : [{ application_id: failedId, error_code: 'FIXTURE_PARTIAL_FAILURE', error_message: 'Fake：该候选人没有可用简历。', retryable: false }],
    });
  }

  const decisionMatch = path.match(/^\/api\/v2\/applications\/(\d+)\/(pass|backup|reject|undo-rejection)$/);
  if (request.method === 'POST' && decisionMatch) {
    const application = applications.find(item => item.id === Number(decisionMatch[1]));
    return sendJson(response, { ...application, hr_decision: decisionMatch[2] === 'pass' ? 'passed' : decisionMatch[2] === 'undo-rejection' ? 'pending' : decisionMatch[2] === 'reject' ? 'rejected' : 'backup' });
  }

  if (path.startsWith('/api/')) return sendJson(response, { detail: { code: 'FIXTURE_NOT_FOUND', message: 'Fake 浏览器夹具未配置此请求。' } }, 404);

  try {
    const requested = path === '/' ? 'index.html' : path.slice(1);
    const candidatePath = resolve(dist, requested);
    const safePath = candidatePath.startsWith(`${dist}${sep}`) ? candidatePath : resolve(dist, 'index.html');
    const body = await readFile(safePath);
    response.writeHead(200, { 'content-type': contentTypes[extname(safePath)] || 'application/octet-stream' });
    response.end(body);
  } catch {
    const body = await readFile(resolve(dist, 'index.html'));
    response.writeHead(200, { 'content-type': contentTypes['.html'] });
    response.end(body);
  }
}).listen(port, '127.0.0.1', () => {
  process.stdout.write(`Stage 7 browser fixture server (${fixtureMode}, no model calls) listening on http://127.0.0.1:${port}\n`);
});
