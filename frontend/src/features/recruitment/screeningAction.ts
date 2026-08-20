import type { Stage7ScreeningCenterItem } from './services/screening';
import type { Stage7ScreeningRunInput } from './types/applicationScreening';

export type Stage7SingleScreeningAction = {
  allowed: boolean;
  label: string;
  reason: string;
  requiresForceConfirmation?: boolean;
};

export const getStage7SingleScreeningAction = (
  item: Stage7ScreeningCenterItem,
  pending: boolean,
): Stage7SingleScreeningAction => {
  const { application, currentResult, jobStatus } = item;
  if (pending) return { allowed: false, label: '正在启动', reason: '请求已经发送，请勿重复点击。' };
  if (application.aiStatus === 'screening') {
    return { allowed: false, label: '初筛进行中', reason: '服务端已有评分任务正在运行。' };
  }
  if (application.lifecycleStatus !== 'active') {
    return { allowed: false, label: '不能初筛', reason: '这份申请已经结束或作废。' };
  }
  if (jobStatus !== 'open') {
    return {
      allowed: false,
      label: '不能初筛',
      reason: jobStatus === 'closed' ? '岗位已关闭，不能启动新评分。' : '暂时无法确认岗位状态。',
    };
  }
  if (application.currentResumeId === null) {
    return { allowed: false, label: '缺少简历', reason: '先为这份申请绑定当前简历。' };
  }
  if (application.aiStatus === 'blocked') {
    return { allowed: false, label: '等待补充资料', reason: '先补充岗位相关材料，再重新进入初筛。' };
  }
  if (currentResult?.isOutdated) {
    return { allowed: true, label: '更新初筛', reason: '使用最新简历和岗位要求生成新结果。' };
  }
  if (application.aiStatus === 'failed') {
    return { allowed: true, label: '重新尝试', reason: '重新执行上一次未完成的评分。' };
  }
  if (application.aiStatus === 'not_started') {
    return { allowed: true, label: '开始初筛', reason: '使用当前简历和已发布评分标准。' };
  }
  if (application.aiStatus === 'completed' && currentResult) {
    return {
      allowed: true,
      label: '强制重跑',
      reason: '当前结果已最新；如需重新调用模型，必须确认并填写原因。',
      requiresForceConfirmation: true,
    };
  }
  return { allowed: false, label: '结果已最新', reason: '当前输入已经有可复用的成功结果。' };
};

export const buildStage7ForceRerunInput = (reason: string): Stage7ScreeningRunInput | null => {
  const normalizedReason = reason.trim();
  if (!normalizedReason) return null;
  return {
    force: true,
    confirm_force: true,
    reason: normalizedReason,
  };
};

export const beginStage7SingleScreening = (pendingIds: Set<number>, applicationId: number) => {
  if (pendingIds.has(applicationId)) return false;
  pendingIds.add(applicationId);
  return true;
};

export const finishStage7SingleScreening = (pendingIds: Set<number>, applicationId: number) => {
  pendingIds.delete(applicationId);
};

export const getStage7SingleScreeningErrorMessage = (code: string | null, message: string) => {
  const guidance: Record<string, string> = {
    SCREENING_ALREADY_RUNNING: '刷新后查看运行状态，不要重复提交。',
    APPLICATION_RESUME_REQUIRED: '先为这份申请绑定可用简历。',
    JOB_NOT_OPEN_FOR_SCREENING: '岗位重新开放后才能评分。',
    RUBRIC_CRITERIA_INVALID: '先为岗位发布合法的评分标准。',
    RUBRIC_DRAFT_STALE: '岗位要求已经变化，需要重新确认并发布评分标准。',
    SCREENING_NOT_ALLOWED: '刷新申请状态后再确认是否允许评分。',
  };
  return code && guidance[code] ? `${message} ${guidance[code]}` : message;
};
