import type { Stage7ApplicationIntakeInput } from './types/applicationScreening';

export type Stage7ScreeningIntakeDraft = {
  name: string;
  phone: string;
  email: string;
  jobId: number | null;
  resumeId: number | null;
};

export type Stage7ScreeningIntakeBuildResult =
  | { valid: true; input: Stage7ApplicationIntakeInput }
  | { valid: false; field: keyof Stage7ScreeningIntakeDraft; message: string };

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SUPPORTED_RESUME_EXTENSIONS = ['.pdf', '.docx', '.txt'];

export const isStage7IntakeResumeFileSupported = (filename: string): boolean => {
  const normalized = filename.trim().toLowerCase();
  return SUPPORTED_RESUME_EXTENSIONS.some(extension => normalized.endsWith(extension));
};

export const buildStage7ScreeningIntakeInput = (
  draft: Stage7ScreeningIntakeDraft,
): Stage7ScreeningIntakeBuildResult => {
  const name = draft.name.trim();
  const phone = draft.phone.trim();
  const email = draft.email.trim().toLowerCase();
  const phoneDigits = phone.replace(/\D/g, '');

  if (!name) return { valid: false, field: 'name', message: '请填写候选人姓名。' };
  if (name.length > 100) {
    return { valid: false, field: 'name', message: '候选人姓名不能超过 100 个字符。' };
  }
  if (phoneDigits.length < 7 || phoneDigits.length > 15) {
    return { valid: false, field: 'phone', message: '手机号需要包含 7—15 位数字。' };
  }
  if (email.length > 254 || !EMAIL_PATTERN.test(email)) {
    return { valid: false, field: 'email', message: '请填写有效邮箱地址。' };
  }
  if (!draft.jobId || draft.jobId < 1) {
    return { valid: false, field: 'jobId', message: '请选择一个开放岗位。' };
  }
  if (!draft.resumeId || draft.resumeId < 1) {
    return { valid: false, field: 'resumeId', message: '请选择或上传一份可用简历。' };
  }

  return {
    valid: true,
    input: {
      name,
      phone,
      email,
      job_id: draft.jobId,
      current_resume_id: draft.resumeId,
      source: 'hr_screening',
      confirm_hr_pass: false,
    },
  };
};

export const getStage7ScreeningIntakeErrorMessage = (
  code: string | null,
  fallback: string,
  candidateIds: number[] = [],
): string => {
  if (code === 'CONTACT_IDENTITY_CONFLICT') {
    const candidates = candidateIds.length
      ? ` 涉及候选人：${candidateIds.map(id => `#${id}`).join('、')}。`
      : '';
    return `手机号和邮箱指向了不同候选人，请先人工核对。${candidates}`.trim();
  }
  if (code === 'RESUME_OWNERSHIP_CONFLICT') {
    return '这份简历已经绑定其他候选人，请核对联系方式或改选简历。';
  }
  if (code === 'JOB_NOT_OPEN_FOR_SCREENING') {
    return '所选岗位已经关闭或不存在，请刷新后选择其他开放岗位。';
  }
  if (code === 'APPLICATION_CONTACT_REQUIRED') return '必须提供有效手机号和邮箱。';
  if (code === 'APPLICATION_RESUME_REQUIRED' || code === 'RESUME_NOT_FOUND') {
    return '所选简历不存在或已经不可用，请重新选择。';
  }
  return fallback || '申请录入失败，请检查填写内容后重试。';
};
