import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = path => readFile(new URL(path, import.meta.url), 'utf8');
const [plan, drawer, report, center, jobs, styles] = await Promise.all([
  read('../src/features/recruitment/JobEvaluationPlanDrawer.tsx'),
  read('../src/features/recruitment/ApplicationScreeningDrawer.tsx'),
  read('../src/features/recruitment/ScreeningReportView.tsx'),
  read('../src/features/recruitment/RecruitmentScreeningCenter.tsx'),
  read('../src/features/recruitment/RecruitmentJobList.tsx'),
  read('../src/features/recruitment/styles/screening.css'),
]);

for (const text of [
  'AI 初筛的只读评价依据', '评价计划只把当前 JD', '生成评价计划', '重新生成',
  '当前评价计划使用旧规则', '按新规则重新生成',
  'limited_basis', 'structuredCoverage.allCovered', 'PLAN_STATUS_META',
]) assert.ok(plan.includes(text), `评价计划预览缺少：${text}`);
assert.ok(plan.includes("plan.contractOutdated && plan.status === 'ready'"));
assert.ok(plan.includes("runGeneration('generate')"), '旧 ready 计划应复用普通生成动作');

for (const text of [
  '开始初筛', '重新评估', '已复用当前报告', '已复用正在进行的任务',
  '旧成功报告仍然保留', '岗位关闭时不能开始或重新评估',
  'SCREENING_POLL_INTERVAL_MS', 'window.clearTimeout', 'requestIdRef',
  'shouldApplyScreeningResponse', 'shouldPollScreeningStatus',
]) assert.ok(drawer.includes(text), `Application 报告抽屉缺少：${text}`);

for (const text of [
  'AI 岗位匹配建议分', 'displayLabel', 'overallSummary', 'requirementAssessments',
  '当前可用简历未体现，不等同于候选人不会', 'calculationNote', 'EvidenceList',
  'bonusHighlights', 'tradeoffReason', 'interviewQuestions', '当前报告基于旧输入',
  'Prompt', '模型', 'Schema', '脱敏规则', '来自原评价计划',
  '评价基准：按该申请', '历史报告未记录评价基准', '时间事实',
]) assert.ok(report.includes(text), `完整报告缺少：${text}`);

assert.equal(report.includes('JSON.stringify(report'), false, '页面不得展示内部时间事实 JSON');
assert.equal(report.includes('experiencePeriodFactKeys.map'), false, '页面不得展示内部时间事实 key');

for (const text of [
  '批量重新评估', 'selectedApplicationIds.length', 'validateBatchSelection',
  'item.jobStatus !== \'open\'', '查看 AI 报告', 'AI 解释匹配依据，HR 作出最终决定',
  'recruitment-page-heading', 'recruitment-screening-workspace', 'recruitment-screening-empty',
]) assert.ok(center.includes(text), `初筛中心缺少：${text}`);

for (const forbidden of [
  'dangerouslySetInnerHTML', 'raw_text', 'rawResponse', 'apiKey', 'screeningResult',
  'evidenceCoverage', 'unknown', 'weightedScore',
]) {
  assert.equal(`${plan}${drawer}${report}${center}`.includes(forbidden), false, `页面恢复或泄露了禁止内容：${forbidden}`);
}

for (const internalAudit of ['free_text_coverage', 'freeTextCoverage', 'source_units', 'sourceUnits']) {
  assert.equal(plan.includes(internalAudit), false, `评价计划页不得展示内部审计数据：${internalAudit}`);
}

assert.match(styles, /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-report-overview[\s\S]*?grid-template-columns:\s*1fr;/s);
assert.match(
  drawer,
  /initialState is intentionally read only[\s\S]*?\[applicationId, jobId, loadState, open\]\);/,
  '父级状态刷新不能重启初次请求并形成请求循环',
);
assert.ok(styles.includes('.recruitment-screening-evidence-list'), '缺少证据可读样式');
assert.ok(styles.includes('.recruitment-zero-score-note'), '缺少 0 分语义样式');
assert.equal(report.includes('本报告没有需要额外说明的综合权衡'), false, '无权衡说明时不应渲染空壳区域');
assert.match(report, /\{report\.tradeoffReason && \([\s\S]*?recruitment-tradeoff-copy/);
assert.ok(jobs.includes('planTriggerRef.current?.focus()'), '关闭评价计划后应把焦点还给触发按钮');
assert.ok(drawer.includes('Modal.useModal()'), 'AI 报告确认框应使用上下文 Modal，避免静态 API 警告');
assert.ok(center.includes('Modal.useModal()'), '批量确认框应使用上下文 Modal，避免静态 API 警告');
assert.equal(drawer.includes('尚未接入登录/RBAC'), false, '报告抽屉不应向 HR 展示开发边界文案');
assert.ok(styles.includes('@media (prefers-reduced-motion: reduce)'), '动效必须尊重减少动态效果设置');

console.log('STAGE7_AI_SCREENING_UI_TEST_OK');
