import type { JobRequirementsV1 } from '../services/jobs';

export type JobEvaluationPlanStatus = 'generating' | 'ready' | 'failed' | 'outdated';
export type EvaluationItemCategory =
  | 'skill'
  | 'experience'
  | 'responsibility'
  | 'education'
  | 'other';
export type EvaluationItemPriority = 'required' | 'preferred' | 'general';
export type EvaluationItemSourceType = 'structured' | 'ai_extracted';
export type JobEvaluationPlanWarning = 'limited_basis';

export type JobEvaluationItem = {
  key: string;
  title: string;
  category: EvaluationItemCategory;
  priority: EvaluationItemPriority;
  sourceType: EvaluationItemSourceType;
  sourceField: string | null;
  sourceQuote: string | null;
};

export type StructuredFieldCoverage = {
  sourceField: string;
  sourceValueCount: number;
  itemKeys: string[];
};

export type JobEvaluationPlan = {
  id: number;
  jobId: number;
  jdFingerprint: string;
  status: JobEvaluationPlanStatus;
  isCurrent: boolean;
  items: JobEvaluationItem[];
  structuredCoverage: {
    sourceSchemaVersion: string;
    fields: StructuredFieldCoverage[];
    allCovered: boolean;
  };
  warnings: JobEvaluationPlanWarning[];
  promptVersion: string;
  modelVersion: string;
  schemaVersion: '1.0' | '2.0';
  inputFingerprint: string;
  contractOutdated: boolean;
  inputSnapshot: {
    jobId: number;
    title: string;
    department: string | null;
    description: string | null;
    requirements: JobRequirementsV1;
  };
  errorCode: string | null;
  errorMessage: string | null;
  createdAt: string;
  completedAt: string | null;
  updatedAt: string;
};

export type ScreeningRunTriggerType =
  | 'automatic'
  | 'single_reassessment'
  | 'batch_reassessment';
export type ScreeningRunStatus =
  | 'waiting_resume'
  | 'waiting_plan'
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'paused';
export type ScreeningOutdatedReason =
  | 'resume_changed'
  | 'jd_changed'
  | 'evaluation_plan_changed';

export type ScreeningEvidence = {
  quote: string;
  section: string | null;
};

export type RequirementAssessment = {
  requirementKey: string;
  score: number;
  reason: string;
  calculationNote: string | null;
  experiencePeriodFactKeys: string[];
  evidence: ScreeningEvidence[];
};

export type BonusHighlight = {
  title: string;
  score: number;
  reason: string;
  evidence: ScreeningEvidence[];
};

export type ScreeningReport = {
  id: number;
  applicationId: number;
  jobId: number;
  resumeId: number;
  jobEvaluationPlanId: number;
  overallScore: number;
  displayLabel: string;
  overallSummary: string;
  requirementAssessments: RequirementAssessment[];
  bonusHighlights: BonusHighlight[];
  tradeoffReason: string | null;
  interviewQuestions: string[];
  inputFingerprint: string;
  jdFingerprint: string;
  planFingerprint: string;
  resumeFingerprint: string;
  promptVersion: string;
  modelVersion: string;
  schemaVersion: string;
  redactionVersion: string;
  evaluationReferenceAt: string | null;
  evaluationTimezone: string | null;
  experiencePeriodFactsRuleVersion: string | null;
  isOutdated: boolean;
  outdatedReasons: ScreeningOutdatedReason[];
  outdatedAt: string | null;
  generatedAt: string;
  updatedAt: string;
};

export type ScreeningRun = {
  id: number;
  applicationId: number;
  jobId: number;
  resumeId: number;
  jobEvaluationPlanId: number | null;
  triggerType: ScreeningRunTriggerType;
  status: ScreeningRunStatus;
  inputFingerprint: string;
  promptVersion: string;
  modelVersion: string;
  schemaVersion: string;
  redactionVersion: string;
  evaluationReferenceAt: string | null;
  evaluationTimezone: string | null;
  experiencePeriodFactsRuleVersion: string | null;
  experiencePeriodFactsFingerprint: string | null;
  startedAt: string | null;
  completedAt: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  inputTokens: number | null;
  outputTokens: number | null;
  durationMs: number | null;
  attemptCount: number;
  createdAt: string;
  updatedAt: string;
};

export type ScreeningState = {
  applicationId: number;
  report: ScreeningReport | null;
  latestRun: ScreeningRun | null;
};

export type ScreeningTriggerResult = {
  applicationId: number;
  run: ScreeningRun | null;
  report: ScreeningReport | null;
  reusedReport: boolean;
  reusedRun: boolean;
};

export type ScreeningBatchReassessmentResult = {
  jobId: number;
  results: ScreeningTriggerResult[];
};

export type AIScreeningApiError = {
  status: number | null;
  code: string | null;
  message: string;
};
