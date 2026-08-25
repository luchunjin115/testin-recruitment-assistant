import type {
  EvaluationItemCategory,
  EvaluationItemPriority,
  JobEvaluationPlan,
  JobEvaluationPlanStatus,
  ScreeningOutdatedReason,
  ScreeningRunStatus,
  ScreeningState,
  ScreeningWaitingReason,
} from './types/aiScreening';

export const SCREENING_POLL_INTERVAL_MS = 4_000;

export const PLAN_STATUS_META: Record<
  JobEvaluationPlanStatus,
  { label: string; tone: 'processing' | 'success' | 'error' | 'warning'; description: string }
> = {
  generating: {
    label: '生成中',
    tone: 'processing',
    description: '系统正在把当前 JD 整理为稳定的初筛评价事项。',
  },
  pending_confirmation: {
    label: '待 HR 确认',
    tone: 'warning',
    description: '事实提取与完整性复核已完成，确认前不会用于候选人初筛。',
  },
  ready: {
    label: '已就绪',
    tone: 'success',
    description: '当前 JD 的基础评价事项已就绪，可用于新申请的 AI 初筛。',
  },
  failed: {
    label: '生成失败',
    tone: 'error',
    description: '当前计划不可用于初筛，请根据安全错误提示处理后重新生成。',
  },
  outdated: {
    label: '已过期',
    tone: 'warning',
    description: '这份计划对应旧 JD，不能用于当前 JD 的新申请。',
  },
};

export const SCREENING_STATUS_META: Record<
  ScreeningRunStatus,
  { label: string; tone: 'default' | 'processing' | 'success' | 'error' | 'warning'; description: string }
> = {
  waiting_resume: {
    label: '等待简历',
    tone: 'warning',
    description: '需要一份正文已可靠解析的当前 Resume，系统暂未调用 AI。',
  },
  waiting_plan: {
    label: '等待评价计划',
    tone: 'warning',
    description: '正在等待当前 JD 对应的评价计划就绪，旧计划不会用于新评估。',
  },
  queued: {
    label: '已排队',
    tone: 'processing',
    description: '任务已进入后台队列，可以离开页面；这里会自动刷新进度。',
  },
  running: {
    label: '评估中',
    tone: 'processing',
    description: 'AI 正在后台评估当前简历，请勿重复提交。',
  },
  succeeded: {
    label: '已完成',
    tone: 'success',
    description: '最近一次运行成功，下面展示当前成功报告。',
  },
  failed: {
    label: '运行失败',
    tone: 'error',
    description: '最近一次评估没有生成新报告；已有成功报告不会被删除。',
  },
  paused: {
    label: '已暂停',
    tone: 'default',
    description: '岗位已关闭或当前条件不允许继续，等待任务已暂停。',
  },
};

export const OUTDATED_REASON_LABELS: Record<ScreeningOutdatedReason, string> = {
  resume_changed: '当前 Resume 已变化',
  jd_changed: '岗位 JD 已变化',
  job_evaluation_input_changed: '岗位评价输入已变化',
  evaluation_plan_changed: '当前评价计划已变化',
};

export const SCREENING_WAITING_REASON_META: Record<
  ScreeningWaitingReason,
  { label: string; description: string }
> = {
  job_closed: {
    label: '岗位已关闭',
    description: '岗位关闭后不会开始新的 AI 评估，已有历史报告仍可查看。',
  },
  plan_missing: {
    label: '尚无评价计划',
    description: '请先到岗位页面生成当前 JD 的五段式评价计划。',
  },
  plan_generating: {
    label: '评价计划生成中',
    description: '计划完成后系统会自动续跑等待中的申请，无需重复点击。',
  },
  plan_pending_confirmation: {
    label: '评价计划等待 HR 确认',
    description: '请到岗位页面核对原文事实、评价维度和 warning；确认后系统才会继续初筛。',
  },
  plan_failed: {
    label: '评价计划生成失败',
    description: '请到岗位页面查看安全错误提示，重试生成或修改 JD。',
  },
  plan_outdated: {
    label: '评价计划基于旧 JD',
    description: '请按当前 JD 生成新计划；旧计划只用于解释历史结果。',
  },
  plan_contract_outdated: {
    label: '评价计划使用旧合同',
    description: '请按当前 JD 生成并确认 4.0 计划，1.0—3.0 计划不能用于新申请。',
  },
};

export const PRIORITY_LABELS: Record<EvaluationItemPriority, string> = {
  required: '必需',
  preferred: '优先',
  general: '一般',
};

export const CATEGORY_LABELS: Record<EvaluationItemCategory, string> = {
  skill: '技能',
  experience: '经历',
  responsibility: '职责',
  education: '学历',
  other: '其他',
};

export const shouldPollScreeningStatus = (status: ScreeningRunStatus | null | undefined) => (
  status === 'queued' || status === 'running'
);

export const shouldApplyScreeningResponse = (
  responseRequestId: number,
  latestRequestId: number,
) => responseRequestId === latestRequestId;

export const getScreeningStateLabel = (state: ScreeningState | null): string => {
  if (state?.latestRun) return SCREENING_STATUS_META[state.latestRun.status].label;
  if (state?.report) return state.report.isOutdated ? '报告已过期' : '已有报告';
  return '尚未初筛';
};

export const getRequirementPlanItem = (
  plan: JobEvaluationPlan | null,
  reportPlanId: number,
  requirementKey: string,
) => {
  if (!plan || plan.id !== reportPlanId) return null;
  return plan.items.find(item => item.key === requirementKey) ?? null;
};

export const getRequirementPlanFact = (
  plan: JobEvaluationPlan | null,
  reportPlanId: number,
  factId: string,
) => {
  if (!plan || plan.id !== reportPlanId || plan.schemaVersion !== '4.0') return null;
  return plan.requirementFacts.find(fact => fact.factId === factId) ?? null;
};

export type BatchSelectionItem = { applicationId: number; jobId: number };
export type BatchSelectionValidation =
  | { valid: true; jobId: number; applicationIds: number[] }
  | { valid: false; message: string };

export const validateBatchSelection = (
  selectedItems: BatchSelectionItem[],
): BatchSelectionValidation => {
  if (selectedItems.length === 0) {
    return { valid: false, message: '请先选择至少 1 个 Application。' };
  }
  if (selectedItems.length > 20) {
    return { valid: false, message: '一次最多重新评估 20 个 Application。' };
  }
  const applicationIds = selectedItems.map(item => item.applicationId);
  if (new Set(applicationIds).size !== applicationIds.length) {
    return { valid: false, message: '不能重复选择同一个 Application。' };
  }
  const jobIds = new Set(selectedItems.map(item => item.jobId));
  if (jobIds.size !== 1) {
    return { valid: false, message: '批量重新评估只能选择同一岗位的 Application。' };
  }
  return { valid: true, jobId: selectedItems[0].jobId, applicationIds };
};
