import type { Stage7ScreeningResultDetail } from './types/applicationScreening';

type UnknownRecord = Record<string, unknown>;

export type Stage7EvidenceView = {
  source: string;
  locator: string | null;
  quote: string;
};

export type Stage7SemanticCriterionView = {
  key: string;
  name: string;
  description: string | null;
  dimension: string;
  score: number | 'unknown' | null;
  confidence: string | null;
  reason: string | null;
  strengths: string[];
  gaps: string[];
  evidence: Stage7EvidenceView[];
};

export type Stage7HardRequirementView = {
  criterion: string;
  requirement: string;
  status: 'passed' | 'failed' | 'unknown';
  evidence: string[];
};

export type Stage7DimensionView = {
  key: string;
  configuredWeight: number | null;
  scorePercentage: number | null;
  evidenceCoverageRate: number | null;
};

export const STAGE7_DIMENSION_LABELS: Record<string, string> = {
  must_have_requirements: '必备技能与硬性要求',
  work_experience_relevance: '工作经历与职责相关性',
  projects_and_capability: '项目、成果与能力深度',
  preferred_qualifications: '加分技能与加分经历',
  keywords_and_additional: '关键词及补充要求',
};

export const STAGE7_CRITERION_LABELS: Record<string, string> = {
  required_skills: '必备技能',
  minimum_work_years: '最低工作年限',
  education_requirement: '学历要求',
  required_experiences: '必备经历',
  responsibility_relevance: '职责相关性',
  work_experience_quality: '工作经历质量',
  project_relevance: '项目相关性',
  capability_depth: '能力深度',
  verified_outcomes: '可核对成果',
  preferred_skills: '加分技能',
  preferred_experiences: '加分经历',
  keywords: '岗位关键词',
  additional_requirements: '补充要求',
};

export const STAGE7_EVIDENCE_SOURCE_LABELS: Record<string, string> = {
  confirmed_profile: 'HR 已确认资料',
  resume_text: '简历原文',
  structured_resume: '结构化简历',
};

const asRecord = (value: unknown): UnknownRecord | null => (
  value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as UnknownRecord
    : null
);

const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

const asString = (value: unknown): string | null => (
  typeof value === 'string' && value.trim() ? value.trim() : null
);

const asNumber = (value: unknown): number | null => {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const asStringArray = (value: unknown): string[] => (
  asArray(value)
    .map(asString)
    .filter((item): item is string => item !== null)
);

const asEvidence = (value: unknown): Stage7EvidenceView | null => {
  const record = asRecord(value);
  const quote = asString(record?.quote);
  if (!record || !quote) return null;
  return {
    source: asString(record.source) || 'unknown',
    locator: asString(record.locator),
    quote,
  };
};

const semanticEvaluations = (detail: Stage7ScreeningResultDetail): UnknownRecord[] => {
  const rawResult = asRecord(detail.rawResult);
  const semantic = asRecord(rawResult?.semantic_evaluation);
  return asArray(semantic?.evaluations)
    .map(asRecord)
    .filter((item): item is UnknownRecord => item !== null);
};

const rubricItems = (detail: Stage7ScreeningResultDetail): UnknownRecord[] => {
  const rubric = asRecord(detail.rubricSnapshot);
  return asArray(rubric?.semantic_items)
    .map(asRecord)
    .filter((item): item is UnknownRecord => item !== null);
};

export const getStage7SemanticCriterionViews = (
  detail: Stage7ScreeningResultDetail,
): Stage7SemanticCriterionView[] => {
  const evaluations = new Map(
    semanticEvaluations(detail)
      .map(item => [asString(item.criterion_key), item] as const)
      .filter((item): item is [string, UnknownRecord] => item[0] !== null),
  );
  const fallbackEvidence = new Map<string, Stage7EvidenceView[]>();
  detail.resumeEvidence.forEach(value => {
    const record = asRecord(value);
    const key = asString(record?.criterion_key);
    const evidence = asEvidence(record);
    if (!key || !evidence) return;
    fallbackEvidence.set(key, [...(fallbackEvidence.get(key) || []), evidence]);
  });

  const rubrics = rubricItems(detail);
  const knownKeys = new Set<string>();
  const views = rubrics.flatMap(item => {
    const key = asString(item.key);
    if (!key) return [];
    knownKeys.add(key);
    const evaluation = evaluations.get(key);
    const rawScore = evaluation?.score;
    const numericScore = asNumber(rawScore);
    const score = rawScore === 'unknown'
      ? 'unknown' as const
      : numericScore !== null && numericScore >= 0 && numericScore <= 10
        ? numericScore
        : null;
    const evidence = asArray(evaluation?.evidence)
      .map(asEvidence)
      .filter((entry): entry is Stage7EvidenceView => entry !== null);
    return [{
      key,
      name: asString(item.name) || key,
      description: asString(item.description),
      dimension: asString(item.dimension) || 'unknown',
      score,
      confidence: asString(evaluation?.confidence),
      reason: asString(evaluation?.reason),
      strengths: asStringArray(evaluation?.strengths),
      gaps: asStringArray(evaluation?.gaps),
      evidence: evidence.length ? evidence : fallbackEvidence.get(key) || [],
    }];
  });

  evaluations.forEach((evaluation, key) => {
    if (knownKeys.has(key)) return;
    const rawScore = evaluation.score;
    const numericScore = asNumber(rawScore);
    views.push({
      key,
      name: key,
      description: null,
      dimension: 'unknown',
      score: rawScore === 'unknown' ? 'unknown' : numericScore,
      confidence: asString(evaluation.confidence),
      reason: asString(evaluation.reason),
      strengths: asStringArray(evaluation.strengths),
      gaps: asStringArray(evaluation.gaps),
      evidence: asArray(evaluation.evidence)
        .map(asEvidence)
        .filter((entry): entry is Stage7EvidenceView => entry !== null),
    });
  });
  return views;
};

export const getStage7HardRequirementViews = (
  detail: Stage7ScreeningResultDetail,
): Stage7HardRequirementView[] => detail.hardRequirementChecks.flatMap(value => {
  const record = asRecord(value);
  const criterion = asString(record?.criterion);
  const rawStatus = asString(record?.status);
  if (!record || !criterion || !['passed', 'failed', 'unknown'].includes(rawStatus || '')) return [];
  return [{
    criterion,
    requirement: asString(record.requirement) || STAGE7_CRITERION_LABELS[criterion] || criterion,
    status: rawStatus as Stage7HardRequirementView['status'],
    evidence: asStringArray(record.evidence),
  }];
});

export const getStage7DimensionViews = (
  detail: Stage7ScreeningResultDetail,
): Stage7DimensionView[] => Object.entries(detail.dimensionScores).flatMap(([key, value]) => {
  const record = asRecord(value);
  if (!record) return [];
  return [{
    key,
    configuredWeight: asNumber(record.configured_weight),
    scorePercentage: asNumber(record.score_percentage),
    evidenceCoverageRate: asNumber(record.evidence_coverage_rate),
  }];
});

export const getStage7RubricVersion = (detail: Stage7ScreeningResultDetail): number | null => {
  const rubric = asRecord(detail.rubricSnapshot);
  return asNumber(rubric?.version);
};
