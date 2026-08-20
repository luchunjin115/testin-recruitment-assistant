import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const rubricResponse = {
  id: 17,
  job_id: 8,
  version: 3,
  weights: {
    must_have_requirements: 40,
    work_experience_relevance: 25,
    projects_and_capability: 20,
    preferred_qualifications: 10,
    keywords_and_additional: 5,
  },
  schema_version: '2.0',
  subcriteria_version: '2.0',
  recommendation_thresholds_version: '1.0',
  fairness_rules_version: '1.0',
  is_current: true,
  source: 'technical_template',
  template_key: 'technical',
  status: 'active',
  semantic_items: [{
    key: 'system_design_depth',
    name: '系统设计深度',
    description: '评估候选人能否解释关键技术取舍。',
    dimension: 'projects_and_capability',
    max_score: 10,
    suggested_share: 30,
    high_score_anchor: '能结合可量化成果解释取舍。',
    mid_score_anchor: '能说明主要方案，但取舍证据不完整。',
    low_score_anchor: '只列出技术名称，缺少实际决策。',
    source: 'template',
  }],
  job_fingerprint: 'a'.repeat(64),
  is_stale: false,
  stale_at: null,
  stale_reason: null,
  generation_metadata: null,
  change_reason: 'draft_published',
  change_detail: '确认技术岗评分规则',
  created_by: 'hr-1',
  confirmed_by: 'hr-1',
  confirmed_at: '2026-08-19T08:00:00Z',
  abandoned_at: null,
  created_at: '2026-08-19T07:00:00Z',
  updated_at: '2026-08-19T08:00:00Z',
};

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const rubricService = await server.ssrLoadModule('/src/features/recruitment/services/jobRubrics.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    return { config, data: rubricResponse, headers: {}, status: 200, statusText: 'OK' };
  };

  const rubric = await rubricService.getRecruitmentJobRubric(8);
  assert.deepEqual(requests.map(request => [request.method, request.url]), [
    ['get', '/jobs/8/screening-rubric'],
  ]);
  assert.equal(rubric.jobId, 8);
  assert.equal(rubric.version, 3);
  assert.equal(rubric.weights.projectsAndCapability, 20);
  assert.equal(rubric.semanticItems[0].highScoreAnchor, '能结合可量化成果解释取舍。');

  const drawerSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentJobRubricDrawer.tsx', import.meta.url),
    'utf8',
  );
  const listSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentJobList.tsx', import.meta.url),
    'utf8',
  );
  const styles = await readFile(
    new URL('../src/features/recruitment/styles/jobs.css', import.meta.url),
    'utf8',
  );

  for (const expectedText of [
    '评分规则',
    '版本 v',
    '五维权重',
    '语义评分项',
    '高分表现',
    '中分表现',
    '低分表现',
    '待重新确认',
    'Python',
    'DeepSeek',
    '编辑评分规则',
  ]) {
    assert.ok(drawerSource.includes(expectedText), `Rubric 只读界面缺少：${expectedText}`);
  }
  assert.ok(listSource.includes('setRubricJob(item)'), '岗位列表必须提供评分规则入口');
  assert.match(styles, /\.recruitment-rubric-weight-track\s*\{[^}]*display:\s*flex;/s);
  assert.match(styles, /@media\s*\(max-width:\s*820px\)[\s\S]*?\.recruitment-rubric-anchor-grid/s);

  console.log('STAGE7_JOB_RUBRIC_READONLY_UI_TEST_OK');
} finally {
  await server.close();
}
