import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const semanticItem = {
  key: 'technical_decision_depth',
  name: '技术决策深度',
  description: '评估候选人能否用证据说明技术取舍。',
  dimension: 'projects_and_capability',
  maxScore: 10,
  suggestedShare: 35,
  highScoreAnchor: '有可定位的决策、取舍和成果证据。',
  midScoreAnchor: '能说明方案，但缺少完整的取舍证据。',
  lowScoreAnchor: '只列举技术名称，无决策证据。',
  source: 'template',
};

const response = {
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
    key: semanticItem.key,
    name: semanticItem.name,
    description: semanticItem.description,
    dimension: semanticItem.dimension,
    max_score: semanticItem.maxScore,
    suggested_share: semanticItem.suggestedShare,
    high_score_anchor: semanticItem.highScoreAnchor,
    mid_score_anchor: semanticItem.midScoreAnchor,
    low_score_anchor: semanticItem.lowScoreAnchor,
    source: semanticItem.source,
  }],
  job_fingerprint: 'c'.repeat(64),
  is_stale: false,
  stale_at: null,
  stale_reason: null,
  generation_metadata: { template_version: '1.0' },
  change_reason: 'draft_updated',
  change_detail: '细化技术取舍证据标准',
  created_by: 'local_hr',
  confirmed_by: null,
  confirmed_at: null,
  abandoned_at: null,
  created_at: '2026-08-19T09:00:00Z',
  updated_at: '2026-08-19T10:00:00Z',
};

const assistResponse = {
  job_fingerprint: 'c'.repeat(64),
  suggestion: {
    name: '技术决策深度',
    description: '评估候选人能否结合岗位场景，说明技术方案、约束条件与最终取舍。',
    dimension: 'projects_and_capability',
    suggested_share: 45,
    high_score_anchor: '有可定位的业务约束、多个候选方案、取舍依据和结果证据。',
    mid_score_anchor: '能说明采用的方案与部分原因，但缺少完整约束或结果证据。',
    low_score_anchor: '只列举技术名称，无法说明方案比较、取舍依据或结果。',
  },
  metadata: {
    model: 'deepseek-v4-flash',
    prompt_version: 'rubric_item_assist_v1',
    schema_version: '2.0',
    input_tokens: 420,
    output_tokens: 180,
  },
};

const shareOptimizationResponse = {
  job_fingerprint: 'c'.repeat(64),
  suggestion: {
    schema_version: '1.0',
    rationale: '突出岗位核心职责对应的技术决策证据。',
    items: [{
      key: semanticItem.key,
      suggested_share: 45,
      reason: '该项直接对应岗位的架构取舍职责。',
    }],
  },
  metadata: {
    model: 'deepseek-v4-flash',
    prompt_version: 'rubric_share_optimization_v1',
    schema_version: '1.0',
    input_tokens: 520,
    output_tokens: 160,
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
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const rubricService = await server.ssrLoadModule('/src/features/recruitment/services/jobRubrics.ts');
  const editorModule = await server.ssrLoadModule(
    '/src/features/recruitment/RecruitmentJobRubricItemEditor.tsx',
  );
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    return {
      config,
      data: config.url?.endsWith('/assist-item')
        ? assistResponse
        : config.url?.endsWith('/optimize-shares')
          ? shareOptimizationResponse
          : response,
      headers: {},
      status: 200,
      statusText: 'OK',
    };
  };

  const updated = await rubricService.updateRecruitmentJobRubricDraft(8, {
    expectedJobFingerprint: 'c'.repeat(64),
    semanticItems: [semanticItem],
    changeDetail: '细化技术取舍证据标准',
  });
  assert.equal(updated.semanticItems[0].suggestedShare, 35);
  await rubricService.updateRecruitmentJobRubricDraft(8, {
    expectedJobFingerprint: 'c'.repeat(64),
    weights: {
      mustHaveRequirements: 35,
      workExperienceRelevance: 25,
      projectsAndCapability: 25,
      preferredQualifications: 10,
      keywordsAndAdditional: 5,
    },
    changeDetail: '提高项目成果权重',
  });
  const assisted = await rubricService.assistRecruitmentJobRubricItem(8, {
    expectedJobFingerprint: 'c'.repeat(64),
    item: {
      name: semanticItem.name,
      description: semanticItem.description,
      dimension: semanticItem.dimension,
      suggestedShare: semanticItem.suggestedShare,
      highScoreAnchor: semanticItem.highScoreAnchor,
      midScoreAnchor: semanticItem.midScoreAnchor,
      lowScoreAnchor: semanticItem.lowScoreAnchor,
    },
  });
  assert.equal(assisted.suggestion.description, assistResponse.suggestion.description);
  assert.equal(assisted.suggestion.suggestedShare, 45);
  assert.equal(assisted.metadata.promptVersion, 'rubric_item_assist_v1');
  const optimized = await rubricService.optimizeRecruitmentJobRubricShares(8, {
    expectedDraftId: 18,
    expectedJobFingerprint: 'c'.repeat(64),
    weights: {
      mustHaveRequirements: 40,
      workExperienceRelevance: 25,
      projectsAndCapability: 20,
      preferredQualifications: 10,
      keywordsAndAdditional: 5,
    },
    semanticItems: [semanticItem],
  });
  assert.equal(optimized.items[0].suggestedShare, 45);
  assert.equal(optimized.items[0].reason, '该项直接对应岗位的架构取舍职责。');
  assert.equal(optimized.metadata.promptVersion, 'rubric_share_optimization_v1');
  assert.deepEqual(requests.map(request => [request.method, request.url]), [
    ['put', '/jobs/8/screening-rubric/draft'],
    ['put', '/jobs/8/screening-rubric/draft'],
    ['post', '/jobs/8/screening-rubric/draft/assist-item'],
    ['post', '/jobs/8/screening-rubric/draft/optimize-shares'],
  ]);
  assert.deepEqual(JSON.parse(requests[0].data), {
    expected_job_fingerprint: 'c'.repeat(64),
    semantic_items: [{
      key: semanticItem.key,
      name: semanticItem.name,
      description: semanticItem.description,
      dimension: semanticItem.dimension,
      max_score: 10,
      suggested_share: 35,
      high_score_anchor: semanticItem.highScoreAnchor,
      mid_score_anchor: semanticItem.midScoreAnchor,
      low_score_anchor: semanticItem.lowScoreAnchor,
      source: 'template',
    }],
    change_detail: '细化技术取舍证据标准',
  });
  assert.deepEqual(JSON.parse(requests[1].data), {
    expected_job_fingerprint: 'c'.repeat(64),
    weights: {
      must_have_requirements: 35,
      work_experience_relevance: 25,
      projects_and_capability: 25,
      preferred_qualifications: 10,
      keywords_and_additional: 5,
    },
    change_detail: '提高项目成果权重',
  });
  assert.deepEqual(JSON.parse(requests[2].data), {
    expected_job_fingerprint: 'c'.repeat(64),
    item: {
      name: semanticItem.name,
      description: semanticItem.description,
      dimension: semanticItem.dimension,
      suggested_share: semanticItem.suggestedShare,
      high_score_anchor: semanticItem.highScoreAnchor,
      mid_score_anchor: semanticItem.midScoreAnchor,
      low_score_anchor: semanticItem.lowScoreAnchor,
    },
  });
  assert.deepEqual(JSON.parse(requests[3].data), {
    expected_draft_id: 18,
    expected_job_fingerprint: 'c'.repeat(64),
    weights: response.weights,
    semantic_items: [{
      key: semanticItem.key,
      name: semanticItem.name,
      description: semanticItem.description,
      dimension: semanticItem.dimension,
      max_score: 10,
      suggested_share: 35,
      high_score_anchor: semanticItem.highScoreAnchor,
      mid_score_anchor: semanticItem.midScoreAnchor,
      low_score_anchor: semanticItem.lowScoreAnchor,
      source: 'template',
    }],
  });

  const invalidError = rubricService.getRecruitmentJobRubricError({
    isAxiosError: true,
    response: { status: 422, data: { detail: [{ loc: ['body', 'semantic_items'], msg: 'invalid' }] } },
  });
  assert.equal(invalidError.code, 'RUBRIC_REQUEST_INVALID');
  assert.ok(invalidError.message.includes('公平性限制'));
  assert.ok(invalidError.message.includes('权重范围与总和'));

  assert.equal(editorModule.MIN_RUBRIC_SEMANTIC_ITEMS, 4);
  assert.equal(editorModule.MAX_RUBRIC_SEMANTIC_ITEMS, 10);
  assert.equal(editorModule.sumRubricWeights(editorModule.DEFAULT_RUBRIC_WEIGHTS), 100);
  assert.equal(editorModule.sumRubricWeights({ mustHaveRequirements: 40 }), 40);
  assert.deepEqual(editorModule.createManualRubricItem('AB-CD_12'), {
    key: 'hr_manual_abcd12',
    name: '',
    dimension: 'projects_and_capability',
    maxScore: 10,
    suggestedShare: 20,
    description: '',
    highScoreAnchor: '',
    midScoreAnchor: '',
    lowScoreAnchor: '',
    source: 'hr_manual',
  });

  const editorSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentJobRubricItemEditor.tsx', import.meta.url),
    'utf8',
  );
  const draftSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentJobRubricDraftPanel.tsx', import.meta.url),
    'utf8',
  );
  const drawerSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentJobRubricDrawer.tsx', import.meta.url),
    'utf8',
  );
  const styles = await readFile(
    new URL('../src/features/recruitment/styles/jobs.css', import.meta.url),
    'utf8',
  );

  for (const expectedText of [
    '校准五维配额与语义评分标准',
    '五维总权重',
    '当前合计',
    '恢复默认 40/25/20/10/5',
    '五个维度的权重总和必须恰好为 100',
    '评分项名称',
    '所属维度',
    '建议占比',
    '评分说明',
    '高分表现',
    '中分表现',
    '低分表现',
    '本次修改说明',
    '保存草稿修改',
    '放弃未保存的 Rubric 草稿修改',
    '新增语义评分项',
    '删除评分项',
    '至少保留 4 个语义评分项',
    '已达到 10 项上限',
    'AI 辅助完善',
    'AI 单项校准单',
    '采用这 4 项建议',
    '名称、所属维度和建议占比继续保留 HR 当前设置',
    '点击采用后仍只是未保存的表单修改',
    'AI 优化当前占比',
    'AI 占比校准台',
    '五维总权重保持当前值不变',
    '应用建议占比',
  ]) {
    assert.ok(editorSource.includes(expectedText), `Rubric 语义项编辑器缺少：${expectedText}`);
  }
  assert.ok(draftSource.includes('onSaved={updatedDraft =>'), '保存后必须刷新草稿摘要');
  assert.ok(drawerSource.includes('leaveDraft'), '返回或关闭抽屉必须保护未保存修改');
  assert.ok(drawerSource.includes('maskClosable={!draftPending}'), '保存期间必须禁止点击遮罩关闭');
  assert.ok(editorSource.includes('fields.length > MIN_RUBRIC_SEMANTIC_ITEMS'), '第 4 项必须禁止继续删除');
  assert.ok(editorSource.includes('fields.length >= MAX_RUBRIC_SEMANTIC_ITEMS'), '第 10 项必须禁止继续新增');
  assert.ok(editorSource.includes('values.items.map(trimItem)'), '保存必须支持增删后重新排列的完整评分项列表');
  assert.ok(editorSource.includes('weights: values.weights'), '保存必须同时提交当前五维权重');
  assert.ok(editorSource.includes('disabled={!isWeightTotalValid}'), '权重合计不是 100 时必须禁止保存');
  assert.ok(editorSource.includes("item?.source === 'hr_manual'"), 'AI 单项辅助只能出现在 HR 手动评分项');
  assert.ok(editorSource.includes('assistRecruitmentJobRubricItem(jobId'), '编辑器必须调用单项辅助 API');
  assert.ok(editorSource.includes('description: assistProposal.suggestion.description'), '采用建议必须回填评分说明');
  assert.ok(editorSource.includes('highScoreAnchor: assistProposal.suggestion.highScoreAnchor'), '采用建议必须回填高分锚点');
  assert.ok(!editorSource.includes('suggestedShare: assistProposal.suggestion.suggestedShare'), '单项辅助不得顺带应用占比建议');
  assert.ok(editorSource.includes('optimizeRecruitmentJobRubricShares(jobId'), '编辑器必须调用占比优化 API');
  assert.ok(editorSource.includes("form.setFieldValue('items', currentItems.map(item => ({"), '应用占比建议只能回填当前评分项表单');
  assert.ok(editorSource.includes('suggestedShare: suggestions.get(item.key) ?? item.suggestedShare'), '应用建议必须按稳定 key 回填占比');
  assert.ok(!editorSource.includes('form.setFieldValue(\'weights\', shareOptimizationProposal'), 'AI 占比建议不得改写五维总权重');
  assert.match(styles, /\.recruitment-rubric-editor-anchor-grid\s*\{[^}]*grid-template-columns:\s*repeat\(3,/s);
  assert.match(styles, /\.recruitment-rubric-editor-collection-action\s*\{[^}]*border:\s*1px dashed/s);
  assert.match(styles, /\.recruitment-rubric-weight-inputs\s*\{[^}]*grid-template-columns:\s*repeat\(5,/s);
  assert.match(styles, /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*?\.recruitment-rubric-weight-track > span\s*\{[^}]*transition:\s*none;/s);
  assert.match(styles, /@media\s*\(max-width:\s*820px\)[\s\S]*?\.recruitment-rubric-editor-anchor-grid\s*\{[^}]*grid-template-columns:\s*1fr;/s);
  assert.match(styles, /\.recruitment-rubric-item-assist-ruler\s*>\s*div\s*\{[^}]*grid-template-columns:\s*86px/s);
  assert.match(styles, /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-rubric-item-assist-ruler\s*>\s*div\s*\{[^}]*grid-template-columns:\s*1fr;/s);
  assert.match(styles, /\.recruitment-rubric-share-optimization-ledger article\s*\{[^}]*grid-template-columns:/s);

  console.log('STAGE7_JOB_RUBRIC_ITEM_EDITOR_TEST_OK');
} finally {
  await server.close();
}
