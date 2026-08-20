import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const draftResponse = {
  id: 18,
  job_id: 8,
  version: 4,
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
  is_current: false,
  source: 'technical_template',
  template_key: 'technical',
  status: 'draft',
  semantic_items: [{
    key: 'technical_decision_depth',
    name: '技术决策深度',
    description: '评估技术取舍。',
    dimension: 'projects_and_capability',
    max_score: 10,
    suggested_share: 35,
    high_score_anchor: '有可定位的决策与成果证据。',
    mid_score_anchor: '有方案说明，但缺少完整取舍。',
    low_score_anchor: '只列举技术名称。',
    source: 'template',
  }],
  job_fingerprint: 'b'.repeat(64),
  is_stale: false,
  stale_at: null,
  stale_reason: null,
  generation_metadata: { template_version: '1.0' },
  change_reason: 'template_draft',
  change_detail: '为技术岗建立评分草稿',
  created_by: 'local_hr',
  confirmed_by: null,
  confirmed_at: null,
  abandoned_at: null,
  created_at: '2026-08-19T09:00:00Z',
  updated_at: '2026-08-19T09:00:00Z',
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
    return {
      config,
      data: draftResponse,
      headers: {},
      status: config.method === 'post' ? 201 : 200,
      statusText: config.method === 'post' ? 'Created' : 'OK',
    };
  };

  const existingDraft = await rubricService.getRecruitmentJobRubricDraft(8);
  assert.equal(existingDraft.status, 'draft');
  assert.equal(existingDraft.isCurrent, false);

  const createdDraft = await rubricService.createRecruitmentJobRubricTemplateDraft(8, {
    template_key: 'technical',
    replace_existing: false,
    change_detail: '为技术岗建立评分草稿',
  });
  assert.equal(createdDraft.templateKey, 'technical');
  const generatedDraft = await rubricService.generateRecruitmentJobRubricDraft(8, {
    template_key: 'technical',
    replace_existing: true,
    change_detail: '按细化后的技术岗位要求重新生成',
  });
  assert.equal(generatedDraft.status, 'draft');
  assert.deepEqual(requests.map(request => [request.method, request.url]), [
    ['get', '/jobs/8/screening-rubric/draft'],
    ['post', '/jobs/8/screening-rubric/draft/from-template'],
    ['post', '/jobs/8/screening-rubric/generate'],
  ]);
  assert.deepEqual(JSON.parse(requests[1].data), {
    template_key: 'technical',
    replace_existing: false,
    change_detail: '为技术岗建立评分草稿',
  });
  assert.deepEqual(JSON.parse(requests[2].data), {
    template_key: 'technical',
    replace_existing: true,
    change_detail: '按细化后的技术岗位要求重新生成',
  });

  const missingDraftError = rubricService.getRecruitmentJobRubricError({
    isAxiosError: true,
    response: {
      status: 404,
      data: { detail: { code: 'RUBRIC_DRAFT_NOT_FOUND', message: '岗位没有正在编辑的评分标准草稿' } },
    },
  });
  assert.equal(missingDraftError.code, 'RUBRIC_DRAFT_NOT_FOUND');

  const drawerSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentJobRubricDrawer.tsx', import.meta.url),
    'utf8',
  );
  const draftSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentJobRubricDraftPanel.tsx', import.meta.url),
    'utf8',
  );
  const styles = await readFile(
    new URL('../src/features/recruitment/styles/jobs.css', import.meta.url),
    'utf8',
  );

  assert.ok(drawerSource.includes("setView('draft')"), '编辑入口必须进入草稿流程');
  for (const expectedText of [
    '选择模板起草，或让 AI 按岗位生成',
    '标准模板',
    '技术岗模板',
    '非技术岗模板',
    '记录起草原因',
    '按模板创建草稿',
    'AI 根据岗位生成草稿',
    'DeepSeek 正在起草评分标准',
    'replace_existing: false',
    '草稿摘要',
    '当前评分仍使用正式版本',
    '继续编辑评分项',
    '让 AI 重新起草整份内容',
    '用 AI 生成结果替换当前草稿？',
    '确认替换并生成',
    'replace_existing: replaceExisting',
    '当前草稿和正式版本均已保留',
  ]) {
    assert.ok(draftSource.includes(expectedText), `Rubric 草稿界面缺少：${expectedText}`);
  }
  assert.match(styles, /\.recruitment-rubric-template-grid\s*\{/s);
  assert.match(styles, /\.recruitment-rubric-ai-lane\s*\{[^}]*border-left:\s*3px solid #3857a6/s);
  assert.match(styles, /@media\s*\(max-width:\s*820px\)[\s\S]*?\.recruitment-rubric-ai-direction-grid\s*\{[^}]*grid-template-columns:\s*1fr;/s);

  console.log('STAGE7_JOB_RUBRIC_DRAFT_UI_TEST_OK');
} finally {
  await server.close();
}
