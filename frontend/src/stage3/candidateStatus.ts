export type CandidateStatusTone = 'info' | 'success' | 'warning' | 'neutral';

export type CandidateStatusMeta = {
  label: string;
  tone: CandidateStatusTone;
  order: number;
  recognized: boolean;
};

const candidateStatusMap: Record<string, Omit<CandidateStatusMeta, 'recognized'>> = {
  new: { label: '新候选人', tone: 'info', order: 10 },
  screening: { label: '待筛选', tone: 'info', order: 20 },
  interview_pending: { label: '待约面', tone: 'warning', order: 30 },
  interview_scheduled: { label: '已约面', tone: 'info', order: 40 },
  interviewing: { label: '面试中', tone: 'info', order: 50 },
  second_interview: { label: '复试', tone: 'info', order: 60 },
  offer: { label: 'Offer 阶段', tone: 'warning', order: 70 },
  hired: { label: '已入职', tone: 'success', order: 80 },
  rejected: { label: '已淘汰', tone: 'warning', order: 90 },
  active: { label: '进行中', tone: 'success', order: 100 },
  passed: { label: '已通过', tone: 'success', order: 110 },
  backup: { label: '备选', tone: 'neutral', order: 120 },
  closed: { label: '已关闭', tone: 'neutral', order: 130 },
};

const normalizeStatus = (status: string) => status.trim().toLowerCase();

export const getCandidateStatusMeta = (status: string): CandidateStatusMeta => {
  const normalized = normalizeStatus(status);
  const known = candidateStatusMap[normalized];
  if (known) return { ...known, recognized: true };
  return {
    label: normalized ? '未识别状态' : '状态未填写',
    tone: 'neutral',
    order: 999,
    recognized: false,
  };
};

export const getCandidateStatusOptionLabel = (status: string) => {
  const meta = getCandidateStatusMeta(status);
  return meta.recognized ? meta.label : `${meta.label}（${status || '空值'}）`;
};

export const sortCandidateStatuses = (statuses: string[]) => [...statuses].sort((left, right) => {
  const leftMeta = getCandidateStatusMeta(left);
  const rightMeta = getCandidateStatusMeta(right);
  return leftMeta.order - rightMeta.order || left.localeCompare(right, 'zh-CN');
});
