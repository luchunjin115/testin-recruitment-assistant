import axios from 'axios';
import { v2Http } from '../../../services/http';

export type RubricDimension =
  | 'must_have_requirements'
  | 'work_experience_relevance'
  | 'projects_and_capability'
  | 'preferred_qualifications'
  | 'keywords_and_additional';

export type RubricSource =
  | 'standard_template'
  | 'technical_template'
  | 'non_technical_template'
  | 'ai_generated'
  | 'hr_manual';

export type RubricCriterionSource = 'template' | 'ai_generated' | 'hr_manual';
export type RubricTemplateKey = 'standard' | 'technical' | 'non_technical';
export type RubricStatus = 'draft' | 'active' | 'archived' | 'abandoned';

export type RecruitmentJobRubricSemanticItem = {
  key: string;
  name: string;
  description: string;
  dimension: RubricDimension;
  maxScore: 10;
  suggestedShare: number;
  highScoreAnchor: string;
  midScoreAnchor: string;
  lowScoreAnchor: string;
  source: RubricCriterionSource;
};

export type RecruitmentJobRubricWeights = {
  mustHaveRequirements: number;
  workExperienceRelevance: number;
  projectsAndCapability: number;
  preferredQualifications: number;
  keywordsAndAdditional: number;
};

type JobScreeningRubricResponse = {
  id: number;
  job_id: number;
  version: number;
  weights: {
    must_have_requirements: number;
    work_experience_relevance: number;
    projects_and_capability: number;
    preferred_qualifications: number;
    keywords_and_additional: number;
  };
  schema_version: '2.0';
  subcriteria_version: '2.0';
  recommendation_thresholds_version: '1.0';
  fairness_rules_version: '1.0';
  is_current: boolean;
  source: RubricSource;
  template_key: RubricTemplateKey | null;
  status: RubricStatus;
  semantic_items: Array<{
    key: string;
    name: string;
    description: string;
    dimension: RubricDimension;
    max_score: 10;
    suggested_share: number;
    high_score_anchor: string;
    mid_score_anchor: string;
    low_score_anchor: string;
    source: RubricCriterionSource;
  }>;
  job_fingerprint: string | null;
  is_stale: boolean;
  stale_at: string | null;
  stale_reason: string | null;
  change_reason: string;
  change_detail: string | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type RecruitmentJobRubric = {
  id: number;
  jobId: number;
  version: number;
  weights: RecruitmentJobRubricWeights;
  schemaVersion: string;
  subcriteriaVersion: string;
  recommendationThresholdsVersion: string;
  fairnessRulesVersion: string;
  isCurrent: boolean;
  source: RubricSource;
  templateKey: RubricTemplateKey | null;
  status: RubricStatus;
  semanticItems: RecruitmentJobRubricSemanticItem[];
  jobFingerprint: string | null;
  isStale: boolean;
  staleAt: string | null;
  staleReason: string | null;
  changeReason: string;
  changeDetail: string | null;
  confirmedBy: string | null;
  confirmedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type RecruitmentJobRubricError = {
  status: number | null;
  code: string | null;
  message: string;
};

export type RecruitmentJobRubricTemplateDraftInput = {
  template_key: RubricTemplateKey;
  replace_existing: false;
  change_detail: string;
};

export type RecruitmentJobRubricGenerateInput = {
  template_key: RubricTemplateKey;
  replace_existing: boolean;
  change_detail: string;
};

export type RecruitmentJobRubricAssistItem = {
  name: string;
  description: string;
  dimension: RubricDimension;
  suggestedShare: number;
  highScoreAnchor: string;
  midScoreAnchor: string;
  lowScoreAnchor: string;
};

export type RecruitmentJobRubricItemAssistInput = {
  expectedJobFingerprint: string;
  item: RecruitmentJobRubricAssistItem;
};

export type RecruitmentJobRubricItemAssistResult = {
  jobFingerprint: string;
  suggestion: RecruitmentJobRubricAssistItem;
  metadata: {
    model: string;
    promptVersion: string;
    schemaVersion: string;
    inputTokens: number | null;
    outputTokens: number | null;
  };
};

export type RecruitmentJobRubricShareOptimizationInput = {
  expectedDraftId: number;
  expectedJobFingerprint: string;
  weights: RecruitmentJobRubricWeights;
  semanticItems: RecruitmentJobRubricSemanticItem[];
};

export type RecruitmentJobRubricShareOptimizationResult = {
  jobFingerprint: string;
  rationale: string;
  items: Array<{
    key: string;
    suggestedShare: number;
    reason: string;
  }>;
  metadata: {
    model: string;
    promptVersion: string;
    schemaVersion: string;
    inputTokens: number | null;
    outputTokens: number | null;
  };
};

type ScreeningRubricItemAssistResponse = {
  job_fingerprint: string;
  suggestion: {
    name: string;
    description: string;
    dimension: RubricDimension;
    suggested_share: number;
    high_score_anchor: string;
    mid_score_anchor: string;
    low_score_anchor: string;
  };
  metadata: {
    model: string;
    prompt_version: string;
    schema_version: string;
    input_tokens: number | null;
    output_tokens: number | null;
  };
};

type ScreeningRubricShareOptimizationResponse = {
  job_fingerprint: string;
  suggestion: {
    schema_version: '1.0';
    rationale: string;
    items: Array<{
      key: string;
      suggested_share: number;
      reason: string;
    }>;
  };
  metadata: {
    model: string;
    prompt_version: string;
    schema_version: string;
    input_tokens: number | null;
    output_tokens: number | null;
  };
};

type RecruitmentJobRubricDraftUpdateBase = {
  expectedJobFingerprint: string;
  changeDetail: string;
};

export type RecruitmentJobRubricDraftUpdateInput = RecruitmentJobRubricDraftUpdateBase & (
  | { weights: RecruitmentJobRubricWeights; semanticItems?: RecruitmentJobRubricSemanticItem[] }
  | { weights?: RecruitmentJobRubricWeights; semanticItems: RecruitmentJobRubricSemanticItem[] }
);

const mapRubric = (rubric: JobScreeningRubricResponse): RecruitmentJobRubric => ({
  id: rubric.id,
  jobId: rubric.job_id,
  version: rubric.version,
  weights: {
    mustHaveRequirements: rubric.weights.must_have_requirements,
    workExperienceRelevance: rubric.weights.work_experience_relevance,
    projectsAndCapability: rubric.weights.projects_and_capability,
    preferredQualifications: rubric.weights.preferred_qualifications,
    keywordsAndAdditional: rubric.weights.keywords_and_additional,
  },
  schemaVersion: rubric.schema_version,
  subcriteriaVersion: rubric.subcriteria_version,
  recommendationThresholdsVersion: rubric.recommendation_thresholds_version,
  fairnessRulesVersion: rubric.fairness_rules_version,
  isCurrent: rubric.is_current,
  source: rubric.source,
  templateKey: rubric.template_key,
  status: rubric.status,
  semanticItems: rubric.semantic_items.map(item => ({
    key: item.key,
    name: item.name,
    description: item.description,
    dimension: item.dimension,
    maxScore: item.max_score,
    suggestedShare: item.suggested_share,
    highScoreAnchor: item.high_score_anchor,
    midScoreAnchor: item.mid_score_anchor,
    lowScoreAnchor: item.low_score_anchor,
    source: item.source,
  })),
  jobFingerprint: rubric.job_fingerprint,
  isStale: rubric.is_stale,
  staleAt: rubric.stale_at,
  staleReason: rubric.stale_reason,
  changeReason: rubric.change_reason,
  changeDetail: rubric.change_detail,
  confirmedBy: rubric.confirmed_by,
  confirmedAt: rubric.confirmed_at,
  createdAt: rubric.created_at,
  updatedAt: rubric.updated_at,
});

export const getRecruitmentJobRubric = async (jobId: number): Promise<RecruitmentJobRubric> => {
  const response = await v2Http.get<JobScreeningRubricResponse>(`/jobs/${jobId}/screening-rubric`);
  return mapRubric(response.data);
};

export const getRecruitmentJobRubricDraft = async (jobId: number): Promise<RecruitmentJobRubric> => {
  const response = await v2Http.get<JobScreeningRubricResponse>(`/jobs/${jobId}/screening-rubric/draft`);
  return mapRubric(response.data);
};

export const createRecruitmentJobRubricTemplateDraft = async (
  jobId: number,
  data: RecruitmentJobRubricTemplateDraftInput,
): Promise<RecruitmentJobRubric> => {
  const response = await v2Http.post<JobScreeningRubricResponse>(
    `/jobs/${jobId}/screening-rubric/draft/from-template`,
    data,
  );
  return mapRubric(response.data);
};

export const generateRecruitmentJobRubricDraft = async (
  jobId: number,
  data: RecruitmentJobRubricGenerateInput,
): Promise<RecruitmentJobRubric> => {
  const response = await v2Http.post<JobScreeningRubricResponse>(
    `/jobs/${jobId}/screening-rubric/generate`,
    data,
  );
  return mapRubric(response.data);
};

export const assistRecruitmentJobRubricItem = async (
  jobId: number,
  data: RecruitmentJobRubricItemAssistInput,
): Promise<RecruitmentJobRubricItemAssistResult> => {
  const response = await v2Http.post<ScreeningRubricItemAssistResponse>(
    `/jobs/${jobId}/screening-rubric/draft/assist-item`,
    {
      expected_job_fingerprint: data.expectedJobFingerprint,
      item: {
        name: data.item.name,
        description: data.item.description,
        dimension: data.item.dimension,
        suggested_share: data.item.suggestedShare,
        high_score_anchor: data.item.highScoreAnchor,
        mid_score_anchor: data.item.midScoreAnchor,
        low_score_anchor: data.item.lowScoreAnchor,
      },
    },
  );
  return {
    jobFingerprint: response.data.job_fingerprint,
    suggestion: {
      name: response.data.suggestion.name,
      description: response.data.suggestion.description,
      dimension: response.data.suggestion.dimension,
      suggestedShare: response.data.suggestion.suggested_share,
      highScoreAnchor: response.data.suggestion.high_score_anchor,
      midScoreAnchor: response.data.suggestion.mid_score_anchor,
      lowScoreAnchor: response.data.suggestion.low_score_anchor,
    },
    metadata: {
      model: response.data.metadata.model,
      promptVersion: response.data.metadata.prompt_version,
      schemaVersion: response.data.metadata.schema_version,
      inputTokens: response.data.metadata.input_tokens,
      outputTokens: response.data.metadata.output_tokens,
    },
  };
};

export const optimizeRecruitmentJobRubricShares = async (
  jobId: number,
  data: RecruitmentJobRubricShareOptimizationInput,
): Promise<RecruitmentJobRubricShareOptimizationResult> => {
  const response = await v2Http.post<ScreeningRubricShareOptimizationResponse>(
    `/jobs/${jobId}/screening-rubric/draft/optimize-shares`,
    {
      expected_draft_id: data.expectedDraftId,
      expected_job_fingerprint: data.expectedJobFingerprint,
      weights: {
        must_have_requirements: data.weights.mustHaveRequirements,
        work_experience_relevance: data.weights.workExperienceRelevance,
        projects_and_capability: data.weights.projectsAndCapability,
        preferred_qualifications: data.weights.preferredQualifications,
        keywords_and_additional: data.weights.keywordsAndAdditional,
      },
      semantic_items: data.semanticItems.map(item => ({
        key: item.key,
        name: item.name,
        description: item.description,
        dimension: item.dimension,
        max_score: item.maxScore,
        suggested_share: item.suggestedShare,
        high_score_anchor: item.highScoreAnchor,
        mid_score_anchor: item.midScoreAnchor,
        low_score_anchor: item.lowScoreAnchor,
        source: item.source,
      })),
    },
  );
  return {
    jobFingerprint: response.data.job_fingerprint,
    rationale: response.data.suggestion.rationale,
    items: response.data.suggestion.items.map(item => ({
      key: item.key,
      suggestedShare: item.suggested_share,
      reason: item.reason,
    })),
    metadata: {
      model: response.data.metadata.model,
      promptVersion: response.data.metadata.prompt_version,
      schemaVersion: response.data.metadata.schema_version,
      inputTokens: response.data.metadata.input_tokens,
      outputTokens: response.data.metadata.output_tokens,
    },
  };
};

export const updateRecruitmentJobRubricDraft = async (
  jobId: number,
  data: RecruitmentJobRubricDraftUpdateInput,
): Promise<RecruitmentJobRubric> => {
  const response = await v2Http.put<JobScreeningRubricResponse>(
    `/jobs/${jobId}/screening-rubric/draft`,
    {
      expected_job_fingerprint: data.expectedJobFingerprint,
      ...(data.weights ? {
        weights: {
          must_have_requirements: data.weights.mustHaveRequirements,
          work_experience_relevance: data.weights.workExperienceRelevance,
          projects_and_capability: data.weights.projectsAndCapability,
          preferred_qualifications: data.weights.preferredQualifications,
          keywords_and_additional: data.weights.keywordsAndAdditional,
        },
      } : {}),
      ...(data.semanticItems ? {
        semantic_items: data.semanticItems.map(item => ({
          key: item.key,
          name: item.name,
          description: item.description,
          dimension: item.dimension,
          max_score: item.maxScore,
          suggested_share: item.suggestedShare,
          high_score_anchor: item.highScoreAnchor,
          mid_score_anchor: item.midScoreAnchor,
          low_score_anchor: item.lowScoreAnchor,
          source: item.source,
        })),
      } : {}),
      change_detail: data.changeDetail,
    },
  );
  return mapRubric(response.data);
};

export const getRecruitmentJobRubricError = (error: unknown): RecruitmentJobRubricError => {
  if (!axios.isAxiosError(error)) {
    return { status: null, code: null, message: '读取评分规则失败，请稍后重试' };
  }

  const detail = error.response?.data?.detail;
  if (Array.isArray(detail)) {
    return {
      status: error.response?.status ?? null,
      code: 'RUBRIC_REQUEST_INVALID',
      message: '草稿内容未通过校验，请检查权重范围与总和、评分项必填内容、重复项和公平性限制',
    };
  }

  if (!detail || typeof detail !== 'object') {
    return {
      status: error.response?.status ?? null,
      code: null,
      message: error.response?.status === 404
        ? '该岗位还没有可查看的评分规则'
        : '读取评分规则失败，请稍后重试',
    };
  }

  return {
    status: error.response?.status ?? null,
    code: typeof detail.code === 'string' ? detail.code : null,
    message: typeof detail.message === 'string'
      ? detail.message
      : '读取评分规则失败，请稍后重试',
  };
};
