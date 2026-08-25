import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = path => readFile(new URL(path, import.meta.url), 'utf8');
const [types, service, drawer, report] = await Promise.all([
  read('../src/features/recruitment/types/aiScreening.ts'),
  read('../src/features/recruitment/services/aiScreening.ts'),
  read('../src/features/recruitment/JobEvaluationPlanDrawer.tsx'),
  read('../src/features/recruitment/ScreeningReportView.tsx'),
]);

test('7R4-F 类型合同声明 4.0 与 pending_confirmation', () => {
  assert.ok(types.includes("'4.0'"));
  assert.ok(types.includes("'pending_confirmation'"));
});

test('7R4-F RequirementFact 只有原文事实字段且不生成 title', () => {
  const block = types.match(/export type RequirementFact = \{[\s\S]*?\n\};/)?.[0] ?? '';
  for (const token of ['factId', 'category', 'priority', 'sources']) assert.ok(block.includes(token));
  for (const forbidden of ['title:', 'statement:', 'weight:', 'score:']) assert.equal(block.includes(forbidden), false);
});

test('7R4-F EvaluationCriterion 只组织 factIds', () => {
  const block = types.match(/export type EvaluationCriterion = \{[\s\S]*?\n\};/)?.[0] ?? '';
  for (const token of ['criterionId', 'name', 'factIds']) assert.ok(block.includes(token));
  for (const forbidden of ['weight:', 'score:', 'threshold:', 'priority:']) assert.equal(block.includes(forbidden), false);
});

test('7R4-F 前端映射 facts criteria review audit', () => {
  for (const token of [
    'requirement_facts', 'requirementFacts',
    'evaluation_criteria', 'evaluationCriteria',
    'coverage_review_summary', 'coverageReviewSummary',
    'generation_audit', 'generationAudit',
  ]) assert.ok(service.includes(token), `4.0 映射缺少 ${token}`);
});

test('7R4-F 页面提供确认计划且不允许直接编辑事实', () => {
  for (const token of ['确认评价计划', 'confirmJobEvaluationPlan', '修改 JD']) assert.ok(drawer.includes(token));
  for (const forbidden of ['编辑事实', '编辑维度', '编辑评价计划']) assert.equal(drawer.includes(forbidden), false);
});

test('7R4-F 页面按 criterion 展示并逐 fact 渲染原文', () => {
  for (const token of ['evaluationCriteria', 'criterion.factIds', 'requirementFacts', 'fact.sources']) {
    assert.ok(drawer.includes(token), `4.0 展示缺少 ${token}`);
  }
});

test('7R4-F 页面可展开同一 fact 的多个来源', () => {
  for (const token of ['source.sourceQuote', 'source.sourceField', 'source.sourceUnitId']) assert.ok(drawer.includes(token));
});

test('7R4-F 页面覆盖五类受控 warning', () => {
  for (const code of [
    'limited_basis', 'overly_broad_jd', 'conflicting_requirements',
    'ambiguous_requirement', 'non_evaluation_content',
  ]) assert.ok(drawer.includes(code), `4.0 warning 缺少 ${code}`);
});

test('7R4-F pending_confirmation 继续等待而不是开始筛选', () => {
  assert.ok(types.includes('plan_pending_confirmation'));
  assert.ok(service.includes('plan_pending_confirmation'));
});

test('7R4-F 历史 1.0 到 3.0 明确只读', () => {
  for (const version of ["'1.0'", "'2.0'", "'3.0'"]) assert.ok(types.includes(version));
  assert.ok(drawer.includes('历史只读'));
});

test('7R4-F 报告按 criterion 分组但仍逐 fact 展示评价', () => {
  for (const token of ['evaluationCriteria', 'factId', 'requirementAssessments']) assert.ok(report.includes(token));
  for (const forbidden of ['criterionScore', 'criterionWeight']) assert.equal(report.includes(forbidden), false);
});

test('7R4-F public_notes 不进入前端计划快照或确认请求', () => {
  const planBlock = types.slice(types.indexOf('export type JobEvaluationPlan ='));
  assert.equal(planBlock.includes('publicNotes'), false);
  const confirmStart = service.indexOf('confirmJobEvaluationPlan');
  assert.ok(confirmStart >= 0, '4.0 Service 尚未提供确认请求');
  const confirmBlock = service.slice(confirmStart);
  assert.equal(confirmBlock.includes('public_notes'), false);
});
