import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const port = Number(process.env.STAGE7_BROWSER_FIXTURE_PORT || 5174);
const dist = resolve(fileURLToPath(new URL('../frontend/dist/', import.meta.url)));
const fixtureMode = process.env.STAGE7_BROWSER_FIXTURE_MODE || 'populated';
const iso = '2026-08-20T08:00:00Z';
const requirements = {
  schema_version: '1.0',
  responsibilities: ['交付虚构招聘平台模块，仅用于阶段 7 浏览器验收。'],
  required_skills: ['React', 'TypeScript'],
  preferred_skills: ['可访问性'],
  minimum_work_years: 2,
  education_requirement: 'bachelor_or_above',
  required_experiences: ['复杂业务前端'],
  preferred_experiences: ['性能优化'],
  keywords: ['虚构验收'],
  additional_requirements: ['不对应任何真实岗位'],
};
const job = {
  id: 1,
  title: '虚构前端工程师',
  department: '验收测试部',
  location: '虚构地点',
  employment_type: 'full_time',
  headcount: 1,
  description: 'STAGE7_BROWSER_ACCEPTANCE_FIXTURE',
  requirements,
  status: 'open',
  created_at: iso,
  updated_at: iso,
};
const candidate = {
  id: 201,
  name: '虚构验收样本 A01',
  source: '阶段 7 浏览器验收',
  status: 'screening',
  applied_job_id: 1,
  current_title: '虚构岗位经历',
};
const application = {
  id: 101,
  candidate_id: 201,
  job_id: 1,
  current_resume_id: 301,
  source: 'hr_screening',
  lifecycle_status: 'active',
  recruitment_stage: 'hr_review',
  hr_decision: 'backup',
  applied_at: iso,
  created_at: iso,
  updated_at: iso,
};
const plan = {
  id: 401,
  job_id: 1,
  jd_fingerprint: 'a'.repeat(64),
  status: 'ready',
  is_current: true,
  items: [{
    key: 'required_skill:react',
    title: 'React 与 TypeScript 复杂业务前端交付能力',
    category: 'skill',
    priority: 'required',
    source_type: 'structured',
    source_field: 'requirements.required_skills',
    source_quote: null,
  }],
  structured_coverage: {
    source_schema_version: '1.0',
    fields: [{ source_field: 'requirements.required_skills', source_value_count: 2, item_keys: ['required_skill:react'] }],
    all_covered: true,
  },
  warnings: [],
  prompt_version: 'browser-fixture-plan-v1',
  model_version: 'fixture-not-deepseek',
  schema_version: '1.0',
  input_fingerprint: 'b'.repeat(64),
  input_snapshot: { job_id: 1, title: job.title, department: job.department, description: job.description, requirements },
  error_code: null,
  error_message: null,
  created_at: iso,
  completed_at: iso,
  updated_at: iso,
};
const report = {
  id: 601,
  application_id: 101,
  job_id: 1,
  resume_id: 301,
  job_evaluation_plan_id: 401,
  overall_score: 78,
  display_label: '整体较匹配',
  overall_summary: '这是虚构且脱敏的浏览器验收报告，AI 只提供岗位匹配建议。',
  requirement_assessments: [{
    requirement_key: 'required_skill:react',
    score: 8,
    reason: '有可核对的虚构复杂业务前端项目。',
    calculation_note: null,
    evidence: [{ quote: '使用 React 与 TypeScript 交付虚构业务表单。', section: '虚构项目经历' }],
  }],
  bonus_highlights: [],
  tradeoff_reason: null,
  interview_questions: ['请说明你在虚构项目中的具体职责。'],
  input_fingerprint: 'c'.repeat(64),
  jd_fingerprint: 'a'.repeat(64),
  plan_fingerprint: 'd'.repeat(64),
  resume_fingerprint: 'e'.repeat(64),
  prompt_version: 'browser-fixture-screen-v1',
  model_version: 'fixture-not-deepseek',
  schema_version: '1.0',
  redaction_version: 'fixture-redact-v1',
  is_outdated: false,
  outdated_reasons: [],
  outdated_at: null,
  generated_at: iso,
  updated_at: iso,
};
const makeRun = status => ({
  id: 701,
  application_id: 101,
  job_id: 1,
  resume_id: 301,
  job_evaluation_plan_id: 401,
  trigger_type: 'single_reassessment',
  status,
  input_fingerprint: 'f'.repeat(64),
  prompt_version: 'browser-fixture-screen-v1',
  model_version: 'fixture-not-deepseek',
  schema_version: '1.0',
  redaction_version: 'fixture-redact-v1',
  started_at: status === 'queued' ? null : iso,
  completed_at: status === 'succeeded' ? iso : null,
  error_code: null,
  error_message: null,
  input_tokens: null,
  output_tokens: null,
  duration_ms: null,
  attempt_count: 1,
  created_at: iso,
  updated_at: iso,
});

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
  if (request.method === 'GET' && path === '/api/v2/candidates') {
    return sendJson(response, fixtureMode === 'empty' ? [] : [candidate]);
  }
  if (request.method === 'GET' && path === '/api/v2/applications') {
    return sendJson(response, fixtureMode === 'empty' ? [] : [application]);
  }
  if (request.method === 'GET' && path === '/api/v2/jobs/1/evaluation-plan') return sendJson(response, plan);
  if (request.method === 'GET' && path === '/api/v2/applications/101/screening') {
    return sendJson(response, { application_id: 101, report, latest_run: makeRun('succeeded') });
  }
  if (request.method === 'POST' && path === '/api/v2/applications/101/screening/re-evaluate') {
    return sendJson(response, {
      application_id: 101,
      report,
      run: makeRun('queued'),
      reused_report: false,
      reused_run: false,
    });
  }
  if (path.startsWith('/api/')) {
    return sendJson(response, { detail: { code: 'FIXTURE_NOT_FOUND', message: '验收夹具没有配置此请求。' } }, 404);
  }

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
  process.stdout.write(`Stage 7 browser fixture server (${fixtureMode}) listening on http://127.0.0.1:${port}\n`);
});
