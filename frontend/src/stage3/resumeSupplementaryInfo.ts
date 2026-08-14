import type { ResumeParseDraft } from './types/resumeStructure';

export type ResumeSkillCandidate = {
  key: string;
  value: string;
};

export type ResumeSupplementaryInfo = {
  certifications: string[];
  selfEvaluation: string | null;
  warnings: string[];
  hasContent: boolean;
};

const cleanUniqueText = (values: string[]): string[] => (
  Array.from(new Set(values.map(value => value.trim()).filter(Boolean)))
);

const buildSkillKey = (value: string): string => `skill:${JSON.stringify(value)}`;

export const buildResumeSkillCandidates = (skills: string[]): ResumeSkillCandidate[] => (
  cleanUniqueText(skills).map(value => ({ key: buildSkillKey(value), value }))
);

export const mergeConfirmedResumeSkills = (
  currentSkills: string[] | undefined,
  candidates: ResumeSkillCandidate[],
  selectedKeys: string[],
): string[] => cleanUniqueText([
  ...(currentSkills || []),
  ...candidates
    .filter(candidate => selectedKeys.includes(candidate.key))
    .map(candidate => candidate.value),
]);

export const buildResumeSupplementaryInfo = (
  draft: ResumeParseDraft,
): ResumeSupplementaryInfo => {
  const certifications = cleanUniqueText(draft.certifications);
  const selfEvaluation = draft.self_evaluation?.trim() || null;
  const warnings = cleanUniqueText(draft.warnings);

  return {
    certifications,
    selfEvaluation,
    warnings,
    hasContent: Boolean(
      certifications.length
      || selfEvaluation
      || warnings.length
    ),
  };
};
