import type { Stage3CandidateCreateInput } from './services/candidates';
import type { ResumeBasicInfoDraft } from './types/resumeStructure';

export const RESUME_BASIC_FIELD_NAMES = [
  'name',
  'phone',
  'email',
  'gender',
  'age',
  'location',
  'currentCompany',
  'currentTitle',
  'workYears',
  'educationLevel',
] as const;

export type ResumeBasicFieldName = typeof RESUME_BASIC_FIELD_NAMES[number];
export type ResumeBasicFieldValue = string | number;

export const isResumeBasicFieldName = (value: string): value is ResumeBasicFieldName => (
  RESUME_BASIC_FIELD_NAMES.includes(value as ResumeBasicFieldName)
);

export type ResumeBasicFieldConflict = {
  currentValue: ResumeBasicFieldValue;
  aiValue: ResumeBasicFieldValue;
};

export type ResumeBasicInfoMergeResult = {
  fillValues: Partial<Stage3CandidateCreateInput>;
  filledFields: ResumeBasicFieldName[];
  matchingFields: ResumeBasicFieldName[];
  conflicts: Partial<Record<ResumeBasicFieldName, ResumeBasicFieldConflict>>;
};

const draftFieldMap: Record<ResumeBasicFieldName, keyof ResumeBasicInfoDraft> = {
  name: 'name',
  phone: 'phone',
  email: 'email',
  gender: 'gender',
  age: 'age',
  location: 'location',
  currentCompany: 'current_company',
  currentTitle: 'current_title',
  workYears: 'work_years',
  educationLevel: 'education_level',
};

export const isEmptyResumeFormValue = (value: unknown): boolean => (
  value === undefined
  || value === null
  || (typeof value === 'string' && value.trim() === '')
);

export const areResumeFieldValuesEqual = (left: unknown, right: unknown): boolean => {
  if (typeof left === 'string' && typeof right === 'string') {
    return left.trim() === right.trim();
  }
  return left === right;
};

export const mergeResumeBasicInfo = (
  currentValues: Partial<Stage3CandidateCreateInput>,
  basicInfo: ResumeBasicInfoDraft,
): ResumeBasicInfoMergeResult => {
  const result: ResumeBasicInfoMergeResult = {
    fillValues: {},
    filledFields: [],
    matchingFields: [],
    conflicts: {},
  };

  RESUME_BASIC_FIELD_NAMES.forEach(fieldName => {
    const aiValue = basicInfo[draftFieldMap[fieldName]];
    if (isEmptyResumeFormValue(aiValue)) return;

    const currentValue = currentValues[fieldName];
    if (isEmptyResumeFormValue(currentValue)) {
      Object.assign(result.fillValues, { [fieldName]: aiValue });
      result.filledFields.push(fieldName);
      return;
    }

    if (areResumeFieldValuesEqual(currentValue, aiValue)) {
      result.matchingFields.push(fieldName);
    } else {
      result.conflicts[fieldName] = {
        currentValue: currentValue as ResumeBasicFieldValue,
        aiValue: aiValue as ResumeBasicFieldValue,
      };
    }
  });

  return result;
};
