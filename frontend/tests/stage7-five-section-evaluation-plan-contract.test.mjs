import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = path => readFile(new URL(path, import.meta.url), 'utf8');
const [types, service, drawer, presentation, screeningDrawer] = await Promise.all([
  read('../src/features/recruitment/types/aiScreening.ts'),
  read('../src/features/recruitment/services/aiScreening.ts'),
  read('../src/features/recruitment/JobEvaluationPlanDrawer.tsx'),
  read('../src/features/recruitment/screeningPresentation.ts'),
  read('../src/features/recruitment/ApplicationScreeningDrawer.tsx'),
]);

test('7R-E 类型合同接收 Schema 3.0 与五段式 input snapshot', () => {
  for (const token of [
    "schemaVersion: '1.0' | '2.0' | '3.0'",
    'jobContext', 'jobBackground', 'evaluationFields',
    'jobResponsibilities', 'candidateRequirements', 'preferredQualifications',
    'sourceUnits', 'sourceUnitId', 'ordinal', 'sourceText',
  ]) assert.ok(types.includes(token), `3.0 类型缺少 ${token}`);
  for (const forbidden of ['description:', 'requirements: LegacyJobEvaluationPlanRequirements']) {
    assert.equal(
      types.slice(types.indexOf('export type JobEvaluationPlan =')).includes(forbidden),
      false,
      `当前计划类型仍依赖旧字段 ${forbidden}`,
    );
  }
});

test('7R-E 事项类型使用 sources[] 多来源且移除 sourceType', () => {
  const itemBlock = types.match(/export type JobEvaluationItem = \{[\s\S]*?\n\};/)?.[0] ?? '';
  assert.ok(itemBlock.includes('sources:'));
  for (const token of ['sourceField', 'sourceUnitId', 'sourceQuote']) assert.ok(itemBlock.includes(token));
  assert.equal(itemBlock.includes('sourceType'), false);
});

test('7R-E warning 使用三类受控对象而非字符串数组', () => {
  for (const code of [
    'limited_basis',
    'priority_signal_conflict',
    'misplaced_non_evaluation_content',
  ]) assert.ok(types.includes(code), `warning 类型缺少 ${code}`);
  for (const field of ['code:', 'message:', 'sourceUnitIds:']) assert.ok(types.includes(field));
  assert.equal(types.includes("export type JobEvaluationPlanWarning = 'limited_basis';"), false);
});

test('7R-E Service 映射 source_review_summary、sources 与 warning 对象', () => {
  for (const token of [
    'source_review_summary', 'sourceReviewSummary',
    'source_unit_id', 'sourceUnitId', 'source_quote', 'sourceQuote',
    'source_unit_ids', 'sourceUnitIds',
  ]) assert.ok(service.includes(token), `计划映射缺少 ${token}`);
  assert.equal(service.includes('structured_coverage:'), false);
});

test('7R-E 抽屉按 required、preferred、general 三组顺序展示', () => {
  const required = drawer.indexOf('任职要求');
  const preferred = drawer.indexOf('加分项');
  const general = drawer.indexOf('岗位职责');
  assert.ok(required >= 0 && preferred > required && general > preferred);
  for (const priority of ["'required'", "'preferred'", "'general'"]) {
    assert.ok(drawer.includes(priority), `缺少 ${priority} 分组`);
  }
});

test('7R-E 抽屉展开并展示每项全部多来源原文', () => {
  for (const token of ['item.sources', 'source.sourceQuote', 'source.sourceField', 'source.sourceUnitId']) {
    assert.ok(drawer.includes(token), `多来源展示缺少 ${token}`);
  }
  assert.ok(/\.map\(source\s*=>/.test(drawer));
});

test('7R-E 抽屉展示三类 warning 的可操作文案', () => {
  for (const token of [
    'limited_basis', '评价依据有限',
    'priority_signal_conflict', '移动到正确字段',
    'misplaced_non_evaluation_content', '宣传',
  ]) assert.ok(drawer.includes(token), `warning 页面缺少 ${token}`);
});

test('7R-E 状态与按钮矩阵覆盖生成、重试、按当前 JD 生成和修改 JD', () => {
  for (const token of [
    '生成评价计划', '重试生成', '按当前 JD 生成', '修改 JD',
    'generateJobEvaluationPlan', 'regenerateJobEvaluationPlan',
    "plan.status === 'generating'", "plan.status === 'ready'",
    "plan.status === 'failed'", "plan.status === 'outdated'",
  ]) assert.ok(drawer.includes(token), `状态按钮矩阵缺少 ${token}`);
});

test('7R-E ready 同输入不可抽卡式反复生成且关闭岗位只读', () => {
  assert.match(drawer, /plan\.status\s*===\s*'ready'[\s\S]*?只读/);
  assert.match(drawer, /job\.status\s*===\s*'closed'[\s\S]*?只读/);
  assert.match(drawer, /job\.status\s*!==\s*'open'[\s\S]*?(disabled|return null)/);
});

test('7R-E 旧计划保持只读并只允许按五段式新规则生成', () => {
  for (const token of ['contractOutdated', '历史只读', '按五段式新规则生成']) {
    assert.ok(drawer.includes(token), `旧计划 UI 缺少 ${token}`);
  }
  for (const forbidden of ['编辑评价计划', 'Rubric', '权重配置', 'unknown']) {
    assert.equal(drawer.includes(forbidden), false, `页面恢复了禁止能力 ${forbidden}`);
  }
});

test('7R-E generating 轮询在终态、关闭抽屉和离开页面时停止', () => {
  for (const token of [
    'PLAN_POLL_INTERVAL_MS', 'window.clearTimeout', 'requestIdRef',
    "'ready'", "'failed'", "'outdated'", 'open', "job.status === 'closed'",
  ]) assert.ok(drawer.includes(token), `轮询停止合同缺少 ${token}`);
});

test('7R-E 初筛等待状态区分五种评价计划原因', () => {
  for (const reason of [
    'plan_missing',
    'plan_generating',
    'plan_failed',
    'plan_outdated',
    'plan_contract_outdated',
  ]) {
    assert.ok(types.includes(reason), `前端类型缺少 ${reason}`);
    assert.ok(service.includes(reason) || presentation.includes(reason), `前端映射缺少 ${reason}`);
  }
  assert.ok(screeningDrawer.includes('waitingReason'));
});
