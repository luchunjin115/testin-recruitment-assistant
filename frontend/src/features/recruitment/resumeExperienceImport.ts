import type {
  RecruitmentEducationInput,
  RecruitmentProjectExperienceInput,
  RecruitmentWorkExperienceInput,
} from './services/candidates';
import type {
  ResumeEducationDraft,
  ResumeProjectExperienceDraft,
  ResumeWorkExperienceDraft,
} from './types/resumeStructure';

export type ResumeExperienceKind = 'education' | 'work' | 'project';

export type ResumeExperienceCandidate<TFormValue> = {
  key: string;
  title: string;
  subtitle: string;
  details: string[];
  tags: string[];
  formValue: TFormValue;
};

const textOrUndefined = (value: string | null): string | undefined => (
  value === null ? undefined : value
);

const joinKeywords = (values: string[]): string | undefined => (
  values.length > 0 ? values.join('、') : undefined
);

const buildCandidateKey = (kind: ResumeExperienceKind, value: object): string => (
  `${kind}:${JSON.stringify(value)}`
);

const periodText = (startDate: string | null, endDate: string | null): string | undefined => {
  if (!startDate && !endDate) return undefined;
  return `${startDate || '时间未识别'} — ${endDate || '时间未识别'}`;
};

export const buildEducationCandidates = (
  drafts: ResumeEducationDraft[],
): ResumeExperienceCandidate<RecruitmentEducationInput>[] => drafts.map(draft => {
  const key = buildCandidateKey('education', draft);
  const formValue: RecruitmentEducationInput = {
    aiCandidateKey: key,
    school: textOrUndefined(draft.school),
    degree: textOrUndefined(draft.degree),
    major: textOrUndefined(draft.major),
    startDate: textOrUndefined(draft.start_date),
    endDate: textOrUndefined(draft.end_date),
  };
  return {
    key,
    title: draft.school || '院校名称未识别',
    subtitle: [draft.degree, draft.major].filter(Boolean).join(' · ') || '学历与专业待核对',
    details: [periodText(draft.start_date, draft.end_date)].filter((value): value is string => Boolean(value)),
    tags: [],
    formValue,
  };
});

export const buildWorkCandidates = (
  drafts: ResumeWorkExperienceDraft[],
): ResumeExperienceCandidate<RecruitmentWorkExperienceInput>[] => drafts.map(draft => {
  const key = buildCandidateKey('work', draft);
  const formValue: RecruitmentWorkExperienceInput = {
    aiCandidateKey: key,
    company: textOrUndefined(draft.company),
    title: textOrUndefined(draft.title),
    startDate: textOrUndefined(draft.start_date),
    endDate: textOrUndefined(draft.end_date),
    description: textOrUndefined(draft.description),
    techStack: joinKeywords(draft.tech_stack),
  };
  return {
    key,
    title: draft.company || '公司名称未识别',
    subtitle: draft.title || '职位待核对',
    details: [
      periodText(draft.start_date, draft.end_date),
      draft.description || undefined,
    ].filter((value): value is string => Boolean(value)),
    tags: draft.tech_stack,
    formValue,
  };
});

export const buildProjectCandidates = (
  drafts: ResumeProjectExperienceDraft[],
): ResumeExperienceCandidate<RecruitmentProjectExperienceInput>[] => drafts.map(draft => {
  const key = buildCandidateKey('project', draft);
  const formValue: RecruitmentProjectExperienceInput = {
    aiCandidateKey: key,
    projectName: textOrUndefined(draft.project_name),
    role: textOrUndefined(draft.role),
    startDate: textOrUndefined(draft.start_date),
    endDate: textOrUndefined(draft.end_date),
    description: textOrUndefined(draft.description),
    techStack: joinKeywords(draft.tech_stack),
    achievements: textOrUndefined(draft.achievements),
  };
  return {
    key,
    title: draft.project_name || '项目名称未识别',
    subtitle: draft.role || '项目角色待核对',
    details: [
      periodText(draft.start_date, draft.end_date),
      draft.description || undefined,
      draft.achievements ? `成果：${draft.achievements}` : undefined,
    ].filter((value): value is string => Boolean(value)),
    tags: draft.tech_stack,
    formValue,
  };
});
