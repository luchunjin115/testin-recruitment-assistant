export type LegacyJobEvaluationPlanRequirements = {
  schema_version: '1.0';
  responsibilities: string[];
  required_skills: string[];
  preferred_skills: string[];
  minimum_work_years: number | null;
  education_requirement: string | null;
  required_experiences: string[];
  preferred_experiences: string[];
  keywords: string[];
  additional_requirements: string[];
};

export type JobEvaluationPlanStatus =
  | 'generating'
  | 'pending_confirmation'
  | 'ready'
  | 'failed'
  | 'outdated';
export type EvaluationItemCategory =
  | 'skill'
  | 'experience'
  | 'responsibility'
  | 'education'
  | 'other';
export type EvaluationItemPriority = 'required' | 'preferred' | 'general';
export type EvaluationItemSourceType = 'structured' | 'ai_extracted';
export type FiveSectionSourceField =
  | 'job_responsibilities'
  | 'candidate_requirements'
  | 'preferred_qualifications';
export type JobEvaluationPlanWarningCode =
  | 'limited_basis'
  | 'priority_signal_conflict'
  | 'misplaced_non_evaluation_content'
  | 'overly_broad_jd'
  | 'conflicting_requirements'
  | 'ambiguous_requirement'
  | 'non_evaluation_content'
  | 'many_criteria'
  | 'importance_review_required'
  | 'semantic_support_review_required';

export type JobEvaluationPlanV5ImportanceReviewReason =
  | 'explicit_strong_signal_mismatch'
  | 'explicit_weak_signal_mismatch'
  | 'no_explicit_signal_non_general'
  | 'mixed_strength_signals'
  | 'complex_qualification_language'
  | 'source_field_signal_mismatch'
  | 'multi_source_signal_conflict';

export type JobEvaluationPlanWarningDetail = {
  code: JobEvaluationPlanWarningCode;
  message: string;
  sourceUnitIds: string[];
  factIds: string[];
  criterionId: string | null;
  reasons: JobEvaluationPlanV5ImportanceReviewReason[];
};

export type JobEvaluationPlanWarning = 'limited_basis' | JobEvaluationPlanWarningDetail;

export type JobEvaluationItem = {
  key: string;
  title: string;
  category: EvaluationItemCategory;
  priority: EvaluationItemPriority;
  sources: Array<{
    sourceField: FiveSectionSourceField;
    sourceUnitId: string;
    sourceQuote: string;
  }>;
  historicalSource: {
    kind: EvaluationItemSourceType;
    field: string | null;
    quote: string | null;
  } | null;
};

export type RequirementFactSource = {
  sourceField: FiveSectionSourceField;
  sourceUnitId: string;
  sourceQuote: string;
};

export type RequirementFact = {
  factId: string;
  category: EvaluationItemCategory;
  priority: EvaluationItemPriority;
  sources: RequirementFactSource[];
};

export type EvaluationCriterion = {
  criterionId: string;
  name: string;
  factIds: string[];
};

export type V5CriterionSource = {
  sourceField: FiveSectionSourceField;
  sourceQuote: string;
};

export type V5CriterionOrigin = 'ai_from_jd' | 'hr_added';

export type V5Criterion = {
  criterionId: string;
  name: string;
  importance: EvaluationItemPriority;
  description: string;
  screeningFocus: string;
  origin: V5CriterionOrigin;
  sources: V5CriterionSource[];
  hrNote: string | null;
};

export type V5CriterionDraft = Omit<V5Criterion, 'criterionId'> & {
  criterionId: string | null;
};

export type StructuredFieldCoverage = {
  sourceField: string;
  sourceValueCount: number;
  itemKeys: string[];
};

export type JobEvaluationPlanSourceReviewSummary = {
  ruleVersion: 'five_section_source_units_v1';
  totalUnits: number;
  reviewedUnits: number;
  evaluationUnits: number;
  nonEvaluationUnits: number;
  allReviewed: boolean;
  units: Array<{
    sourceUnitId: string;
    disposition: 'evaluation' | 'non_evaluation';
    nonEvaluationReason:
      | 'company_info'
      | 'benefit'
      | 'promotion'
      | 'recruitment_process'
      | 'candidate_note'
      | 'context'
      | 'other'
      | null;
    itemKeys: string[];
    factIds: string[];
  }>;
};

export type JobEvaluationPlanCoverageReviewSummary = {
  status: 'passed' | 'needs_repair';
  findings: Array<{
    code:
      | 'missing_fact'
      | 'unsupported_fact'
      | 'wrong_disposition'
      | 'invalid_atomicity'
      | 'missing_source_merge'
      | 'category_mismatch';
    sourceUnitIds: string[];
    factIds: string[];
    message: string;
  }>;
  repairPerformed: boolean;
  reviewedSourceUnitIds: string[];
};

export type JobEvaluationPlanGenerationAudit = {
  businessCallCount: number;
  contentRepairCount: number;
  infrastructureRetryCount: number;
  calls: Array<{
    role: 'fact_extraction' | 'coverage_review' | 'local_repair' | 'criterion_grouping';
    promptVersion: string;
    model: string;
    inputTokens: number;
    outputTokens: number;
    durationMs: number;
    infrastructureRetryCount: number;
    result: 'succeeded' | 'failed';
    errorCode: string | null;
  }>;
};

export type LegacyJobEvaluationPlanInputSnapshot = {
  jobId: number;
  title: string;
  department: string | null;
  description: string | null;
  requirements: LegacyJobEvaluationPlanRequirements;
};

export type JobEvaluationPlanInputSnapshotV3 = {
  schemaVersion: '3.0';
  jobContext: {
    title: string;
    department: string | null;
    jobBackground: string | null;
  };
  evaluationFields: {
    jobResponsibilities: string | null;
    candidateRequirements: string | null;
    preferredQualifications: string | null;
  };
  sourceUnits: Array<{
    sourceUnitId: string;
    sourceField: FiveSectionSourceField;
    ordinal: number;
    sourceText: string;
  }>;
};

export type JobEvaluationPlanInputSnapshotV4 = {
  schemaVersion: '4.0' | '5.0';
  jobContext: {
    title: string;
    department: string | null;
    jobBackground: string | null;
  };
  evaluationFields: {
    jobResponsibilities: string | null;
    candidateRequirements: string | null;
    preferredQualifications: string | null;
  };
  sourceUnits: Array<{
    sourceUnitId: string;
    sourceField: FiveSectionSourceField;
    ordinal: number;
    sourceText: string;
  }>;
};

export type JobEvaluationPlanInputSnapshot =
  | LegacyJobEvaluationPlanInputSnapshot
  | JobEvaluationPlanInputSnapshotV3
  | JobEvaluationPlanInputSnapshotV4;

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
  } | null;
  sourceReviewSummary: JobEvaluationPlanSourceReviewSummary | null;
  requirementFacts: RequirementFact[];
  evaluationCriteria: EvaluationCriterion[];
  coverageReviewSummary: JobEvaluationPlanCoverageReviewSummary | null;
  generationAudit: JobEvaluationPlanGenerationAudit | null;
  v5Criteria: V5Criterion[];
  editVersion: number | null;
  confirmedAt: string | null;
  warnings: JobEvaluationPlanWarning[];
  promptVersion: string;
  modelVersion: string;
  schemaVersion: '1.0' | '2.0' | '3.0' | '4.0' | '5.0';
  inputFingerprint: string;
  contractOutdated: boolean;
  inputSnapshot: JobEvaluationPlanInputSnapshot;
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
  | 'job_evaluation_input_changed'
  | 'evaluation_plan_changed';
export type ScreeningWaitingReason =
  | 'job_closed'
  | 'plan_missing'
  | 'plan_generating'
  | 'plan_pending_confirmation'
  | 'plan_failed'
  | 'plan_outdated'
  | 'plan_contract_outdated';

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

export type V5ReportFinding = {
  summary: string;
  criterionIds: string[];
  evidence: ScreeningEvidence[];
};

export type V5PersistedCriterionAssessment = {
  criterion: V5Criterion;
  assessment: Omit<RequirementAssessment, 'requirementKey'> & { criterionId: string };
};

export type ScreeningV5Report = {
  overallScore: number;
  displayLabel: string;
  overallSummary: string;
  criterionAssessments: V5PersistedCriterionAssessment[];
  strengths: V5ReportFinding[];
  gaps: V5ReportFinding[];
  risksOrConflicts: V5ReportFinding[];
  missingInfo: V5ReportFinding[];
  hrFollowUpQuestions: string[];
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
  v5Report: ScreeningV5Report | null;
  isCurrent: boolean;
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
  waitingReason: ScreeningWaitingReason | null;
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
  totalCount: number;
  reusedCount: number;
  queuedCount: number;
  failedCount: number;
  results: ScreeningTriggerResult[];
  failures: Array<{
    applicationId: number;
    errorCode: string;
    errorMessage: string;
    retryable: boolean;
  }>;
};

export type AIScreeningApiError = {
  status: number | null;
  code: string | null;
  message: string;
};
