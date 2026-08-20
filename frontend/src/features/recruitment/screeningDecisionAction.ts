import type { Stage7ScreeningCenterItem } from './services/screening';
import type {
  Stage7BackupApplicationInput,
  Stage7BackupReasonCode,
  Stage7DecisionReversalReasonCode,
  Stage7PassApplicationInput,
  Stage7RejectApplicationInput,
  Stage7RejectReasonCode,
  Stage7ReverseDecisionInput,
} from './types/applicationScreening';

export type Stage7DecisionKind = 'pass' | 'backup' | 'reject' | 'undo_rejection';
export type Stage7DecisionEntry = { allowed: boolean; label: string; reason: string };
export type Stage7DecisionSubmission =
  | { action: 'pass'; input: Stage7PassApplicationInput }
  | { action: 'backup'; input: Stage7BackupApplicationInput }
  | { action: 'reject'; input: Stage7RejectApplicationInput }
  | { action: 'undo_rejection'; input: Stage7ReverseDecisionInput };
export type Stage7DecisionBuildResult =
  | { valid: true; submission: Stage7DecisionSubmission }
  | { valid: false; message: string };

export const STAGE7_DECISION_FAIRNESS_PROHIBITED_TERMS = [
  '年龄', '性别', '民族', '婚姻', '已婚', '未婚', '婚育', '生育', '照片', '籍贯',
  '985', '211', '双一流', '学校声誉', '名校', 'age', 'gender', 'race', 'ethnicity',
  'marital', 'married', 'pregnancy', 'birthplace', 'prestigious university',
] as const;

export const STAGE7_BACKUP_REASON_OPTIONS: Array<{ value: Stage7BackupReasonCode; label: string }> = [
  { value: 'minor_capability_gap', label: '存在少量能力差距' },
  { value: 'waiting_for_comparison', label: '等待与其他候选人比较' },
  { value: 'limited_headcount', label: '当前招聘名额有限' },
  { value: 'information_pending', label: '仍有岗位相关信息待补充' },
  { value: 'compensation_pending', label: '薪资条件待确认' },
  { value: 'availability_pending', label: '到岗时间待确认' },
];

export const STAGE7_REJECT_REASON_OPTIONS: Array<{ value: Stage7RejectReasonCode; label: string }> = [
  { value: 'required_skill_missing', label: '缺少岗位必备技能' },
  { value: 'work_experience_insufficient', label: '相关工作年限不足' },
  { value: 'education_requirement_not_met', label: '学历层级未达到岗位要求' },
  { value: 'required_experience_missing', label: '缺少岗位要求的关键经历' },
  { value: 'role_mismatch', label: '经历方向与岗位职责不匹配' },
];

export const STAGE7_REVERSAL_REASON_OPTIONS: Array<{
  value: Stage7DecisionReversalReasonCode;
  label: string;
}> = [
  { value: 'new_evidence', label: '获得新的岗位相关证据' },
  { value: 'candidate_information_updated', label: '候选人资料已更新' },
  { value: 'job_requirements_changed', label: '岗位要求已经变化' },
  { value: 'decision_correction', label: '修正此前误操作' },
  { value: 'hr_reassessment', label: 'HR 重新评估' },
];

export const getStage7DecisionEntry = (
  item: Stage7ScreeningCenterItem,
  pending: boolean,
): Stage7DecisionEntry => {
  const { application } = item;
  if (pending) return { allowed: false, label: '正在处理', reason: '这份申请正在提交，请勿重复操作。' };
  if (application.lifecycleStatus === 'voided') {
    return { allowed: false, label: '申请已作废', reason: '作废申请不能继续执行 HR 决策。' };
  }
  if (application.hrDecision === 'rejected') {
    const allowed = application.lifecycleStatus === 'ended'
      && application.recruitmentStage === 'rejected';
    return {
      allowed,
      label: allowed ? '撤销淘汰' : '不能调整',
      reason: allowed ? '填写反转原因后回到 HR 人工审核。' : '当前淘汰状态不完整，请刷新后重试。',
    };
  }
  if (application.lifecycleStatus !== 'active') {
    return { allowed: false, label: '流程已结束', reason: '只有有效申请可以执行 HR 决策。' };
  }
  return {
    allowed: true,
    label: application.hrDecision === 'pending' ? '作出 HR 决策' : '调整 HR 决策',
    reason: 'HR 可以独立决定通过、备选或淘汰，改变已有决定时需说明原因。',
  };
};

export const getStage7DecisionKinds = (item: Stage7ScreeningCenterItem): Stage7DecisionKind[] => {
  switch (item.application.hrDecision) {
    case 'pending': return ['pass', 'backup', 'reject'];
    case 'passed': return ['backup', 'reject'];
    case 'backup': return ['pass', 'reject'];
    case 'rejected': return ['undo_rejection'];
  }
};

export const getStage7PassPolicy = (item: Stage7ScreeningCenterItem) => {
  const isReversal = item.application.hrDecision !== 'pending';
  return {
    reasonCode: 'meets_requirements' as const,
    detailRequired: isReversal,
    label: '符合岗位要求',
    note: isReversal ? '改变已有决定必须填写岗位相关说明。' : 'HR 根据岗位要求和候选人材料独立判断。',
  };
};

const normalizeDetail = (value: string) => value.trim() || null;
const findProhibitedTerm = (value: string) => {
  const normalized = value.toLocaleLowerCase();
  return STAGE7_DECISION_FAIRNESS_PROHIBITED_TERMS.find(term => {
    const normalizedTerm = term.toLocaleLowerCase();
    if (!/^[\x00-\x7F]+$/.test(normalizedTerm)) return normalized.includes(normalizedTerm);
    const escapedTerm = normalizedTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`(^|[^a-z])${escapedTerm}([^a-z]|$)`).test(normalized);
  });
};

export const buildStage7DecisionSubmission = (
  item: Stage7ScreeningCenterItem,
  kind: Stage7DecisionKind | null,
  reasonCode: string | null,
  reasonDetail: string,
): Stage7DecisionBuildResult => {
  if (!kind) return { valid: false, message: '先选择通过、备选或淘汰。' };
  if (!getStage7DecisionKinds(item).includes(kind)) {
    return { valid: false, message: '当前 HR 决策不允许执行这个操作。' };
  }
  const detail = normalizeDetail(reasonDetail);
  const isReversal = item.application.hrDecision !== 'pending';
  const prohibitedTerm = detail ? findProhibitedTerm(detail) : null;
  if (prohibitedTerm) {
    return { valid: false, message: `决定说明不能使用“${prohibitedTerm}”等与岗位能力无关的敏感依据。` };
  }

  if (kind === 'pass') {
    if (isReversal && !detail) return { valid: false, message: '改变已有决定必须填写岗位相关说明。' };
    return { valid: true, submission: { action: 'pass', input: { reason_code: 'meets_requirements', reason_detail: detail } } };
  }
  if (kind === 'backup') {
    if (!STAGE7_BACKUP_REASON_OPTIONS.some(option => option.value === reasonCode)) {
      return { valid: false, message: '请选择进入备选的岗位相关原因。' };
    }
    if (isReversal && !detail) return { valid: false, message: '改变已有决定必须填写说明。' };
    return { valid: true, submission: { action: 'backup', input: { reason_code: reasonCode as Stage7BackupReasonCode, reason_detail: detail } } };
  }
  if (kind === 'reject') {
    if (!STAGE7_REJECT_REASON_OPTIONS.some(option => option.value === reasonCode)) {
      return { valid: false, message: '请选择淘汰的岗位相关原因。' };
    }
    if (isReversal && !detail) return { valid: false, message: '改变已有决定必须填写说明。' };
    return { valid: true, submission: { action: 'reject', input: { reason_code: reasonCode as Stage7RejectReasonCode, reason_detail: detail, confirmed: true } } };
  }
  if (!STAGE7_REVERSAL_REASON_OPTIONS.some(option => option.value === reasonCode)) {
    return { valid: false, message: '请选择撤销淘汰的原因。' };
  }
  if (!detail) return { valid: false, message: '撤销淘汰必须填写具体说明。' };
  return { valid: true, submission: { action: 'undo_rejection', input: { reason_code: reasonCode as Stage7DecisionReversalReasonCode, reason_detail: detail } } };
};

export const getStage7DecisionErrorMessage = (code: string | null, message: string) => {
  const guidance: Record<string, string> = {
    INVALID_APPLICATION_TRANSITION: '申请状态可能已经变化，请刷新后重新确认。',
    APPLICATION_NOT_FOUND: '这份申请已经不存在，请刷新工作队列。',
  };
  return code && guidance[code] ? `${message} ${guidance[code]}` : message;
};
