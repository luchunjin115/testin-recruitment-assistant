import type { Stage7ScreeningCenterItem } from './services/screening';
import type { Stage7ScreeningBatchOutcome } from './types/applicationScreening';

export type Stage7BatchSelectionState = {
  allowed: boolean;
  reason: string;
};

export type Stage7BatchRunGuard = { pending: boolean };

export const getStage7BatchSelectionState = (
  item: Stage7ScreeningCenterItem,
  options: {
    selected: boolean;
    selectedCount: number;
    selectedJobId: number | null;
    batchPending: boolean;
    singlePending: boolean;
  },
): Stage7BatchSelectionState => {
  const { application, jobStatus } = item;
  if (options.batchPending) return { allowed: false, reason: '当前批次正在执行。' };
  if (options.singlePending || application.aiStatus === 'screening') {
    return { allowed: false, reason: '这份申请正在进行单人评分。' };
  }
  if (options.selected) return { allowed: true, reason: '取消选择这份申请。' };
  if (application.lifecycleStatus !== 'active') return { allowed: false, reason: '申请已结束或作废。' };
  if (jobStatus !== 'open') return { allowed: false, reason: '只有开放岗位可以启动批量评分。' };
  if (application.currentResumeId === null) return { allowed: false, reason: '申请尚未绑定可用简历。' };
  if (application.aiStatus === 'blocked') return { allowed: false, reason: '先补充候选人材料，再单独重新评分。' };
  if (options.selectedJobId !== null && application.jobId !== options.selectedJobId) {
    return { allowed: false, reason: '一个批次只能选择同一岗位。' };
  }
  if (options.selectedCount >= 5) return { allowed: false, reason: '一个批次最多选择 5 人。' };
  if (application.aiStatus === 'completed' && !item.currentResult?.isOutdated) {
    return { allowed: true, reason: '已有最新结果，批次执行时会安全复用。' };
  }
  return { allowed: true, reason: '加入当前岗位的批量初筛。' };
};

export const beginStage7BatchRun = (guard: Stage7BatchRunGuard) => {
  if (guard.pending) return false;
  guard.pending = true;
  return true;
};

export const finishStage7BatchRun = (guard: Stage7BatchRunGuard) => {
  guard.pending = false;
};

export const getStage7FailedBatchApplicationIds = (outcome: Stage7ScreeningBatchOutcome) => (
  outcome.items.filter(item => item.status === 'failed').map(item => item.applicationId)
);
