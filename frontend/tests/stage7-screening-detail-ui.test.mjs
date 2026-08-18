import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';


const detail = {
  hardRequirementChecks: [
    {
      criterion: 'minimum_work_years',
      requirement: '至少 3 年相关工作经验',
      status: 'passed',
      evidence: ['已确认工作年限：4 年'],
    },
    {
      criterion: 'education_requirement',
      requirement: '本科及以上学历',
      status: 'unknown',
      evidence: [],
    },
    { criterion: 'invalid_item', requirement: '不应展示', status: 'maybe', evidence: [] },
  ],
  dimensionScores: {
    must_have_requirements: {
      configured_weight: '35',
      score_percentage: 82.5,
      evidence_coverage_rate: '0.75',
    },
    invalid_dimension: 'not-an-object',
  },
  resumeEvidence: [
    {
      criterion_key: 'capability_depth',
      source: 'structured_resume',
      locator: '项目经历 / 招聘平台',
      quote: '独立负责服务拆分与数据库设计',
    },
  ],
  rubricSnapshot: {
    version: 3,
    semantic_items: [
      {
        key: 'service_delivery',
        name: '服务交付能力',
        description: '能否独立交付稳定服务',
        dimension: 'projects_and_capability',
      },
      {
        key: 'capability_depth',
        name: '能力深度',
        dimension: 'projects_and_capability',
      },
      {
        key: 'information_gap',
        name: '信息完整性',
        dimension: 'keywords_and_additional',
      },
    ],
  },
  rawResult: {
    semantic_evaluation: {
      evaluations: [
        {
          criterion_key: 'service_delivery',
          score: 8,
          confidence: 'high',
          reason: '有完整交付经历。',
          strengths: ['独立负责'],
          gaps: ['监控细节未说明'],
          evidence: [
            {
              source: 'resume_text',
              locator: '工作经历 / 某科技公司',
              quote: '负责招聘平台后端服务的设计与交付',
            },
          ],
        },
        {
          criterion_key: 'capability_depth',
          score: 7,
          confidence: 'medium',
          reason: '存在能力证据，但细节有限。',
          strengths: [],
          gaps: ['性能指标未量化'],
          evidence: [],
        },
        {
          criterion_key: 'information_gap',
          score: 'unknown',
          confidence: 'low',
          reason: '材料没有覆盖该项。',
          strengths: [],
          gaps: ['需要人工确认'],
          evidence: [],
        },
      ],
    },
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
  const view = await server.ssrLoadModule('/src/features/recruitment/screeningDetailView.ts');

  const criteria = view.getStage7SemanticCriterionViews(detail);
  assert.equal(criteria.length, 3);
  assert.deepEqual(criteria[0], {
    key: 'service_delivery',
    name: '服务交付能力',
    description: '能否独立交付稳定服务',
    dimension: 'projects_and_capability',
    score: 8,
    confidence: 'high',
    reason: '有完整交付经历。',
    strengths: ['独立负责'],
    gaps: ['监控细节未说明'],
    evidence: [{
      source: 'resume_text',
      locator: '工作经历 / 某科技公司',
      quote: '负责招聘平台后端服务的设计与交付',
    }],
  });
  assert.deepEqual(criteria[1].evidence, [{
    source: 'structured_resume',
    locator: '项目经历 / 招聘平台',
    quote: '独立负责服务拆分与数据库设计',
  }]);
  assert.equal(criteria[2].score, 'unknown');
  assert.deepEqual(criteria[2].evidence, []);

  assert.deepEqual(view.getStage7HardRequirementViews(detail), [
    {
      criterion: 'minimum_work_years',
      requirement: '至少 3 年相关工作经验',
      status: 'passed',
      evidence: ['已确认工作年限：4 年'],
    },
    {
      criterion: 'education_requirement',
      requirement: '本科及以上学历',
      status: 'unknown',
      evidence: [],
    },
  ]);
  assert.deepEqual(view.getStage7DimensionViews(detail), [{
    key: 'must_have_requirements',
    configuredWeight: 35,
    scorePercentage: 82.5,
    evidenceCoverageRate: 0.75,
  }]);
  assert.equal(view.getStage7RubricVersion(detail), 3);

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url),
    'utf8',
  );
  const drawerSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningDetailDrawer.tsx', import.meta.url),
    'utf8',
  );
  const styles = await readFile(
    new URL('../src/features/recruitment/styles/screening.css', import.meta.url),
    'utf8',
  );

  for (const text of ['RecruitmentScreeningDetailDrawer', '评分记录']) {
    assert.ok(pageSource.includes(text), `评分中心缺少详情入口：${text}`);
  }
  for (const text of [
    'listStage7ApplicationScreenings',
    'getStage7ScreeningResult',
    '评分历史',
    '硬性条件',
    '语义评分与逐项证据',
    '版本与运行信息',
  ]) {
    assert.ok(drawerSource.includes(text), `评分详情缺少交互：${text}`);
  }
  assert.match(styles, /\.recruitment-screening-detail-layout\s*\{/s);
  assert.match(styles, /\.recruitment-screening-evidence-ledger\s*\{/s);
  assert.match(styles, /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-screening-detail-layout\s*\{/s);

  console.log('STAGE7_SCREENING_DETAIL_UI_TEST_OK');
} finally {
  await server.close();
}
