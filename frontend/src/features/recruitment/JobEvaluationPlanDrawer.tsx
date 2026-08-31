import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  CheckOutlined,
  DeleteOutlined,
  EditOutlined,
  MergeCellsOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { Alert, Button, Checkbox, Collapse, Drawer, Empty, Input, Popconfirm, Select, Skeleton, Tag } from 'antd';
import {
  confirmJobEvaluationPlan,
  createJobEvaluationPlanVersion,
  generateJobEvaluationPlan,
  getAIScreeningApiError,
  getJobEvaluationPlan,
  listJobEvaluationPlans,
  regenerateJobEvaluationPlan,
  saveJobEvaluationPlanDraft,
} from './services/aiScreening';
import type { RecruitmentJob } from './services/jobs';
import {
  CATEGORY_LABELS,
  PLAN_STATUS_META,
  PRIORITY_LABELS,
  shouldApplyScreeningResponse,
} from './screeningPresentation';
import type {
  EvaluationItemPriority,
  FiveSectionSourceField,
  JobEvaluationPlan,
  JobEvaluationPlanWarningCode,
  JobEvaluationPlanV5ImportanceReviewReason,
  V5CriterionDraft,
} from './types/aiScreening';

export const PLAN_POLL_INTERVAL_MS = 4_000;

const PLAN_GROUPS: Array<{
  priority: EvaluationItemPriority;
  eyebrow: string;
  title: string;
  empty: string;
}> = [
  { priority: 'required', eyebrow: 'REQUIRED', title: '任职要求', empty: '当前 JD 没有形成明确的必需事项。' },
  { priority: 'preferred', eyebrow: 'PREFERRED', title: '加分项', empty: '当前 JD 没有形成加分事项。' },
  { priority: 'general', eyebrow: 'GENERAL', title: '岗位职责', empty: '当前 JD 没有形成一般职责事项。' },
];

const SOURCE_FIELD_LABELS: Record<FiveSectionSourceField, string> = {
  candidate_requirements: '任职要求',
  preferred_qualifications: '加分项',
  job_responsibilities: '岗位职责',
};

const WARNING_COPY: Record<JobEvaluationPlanWarningCode, { title: string; description: string }> = {
  limited_basis: {
    title: '评价依据有限',
    description: '当前 JD 只形成了少量明确事项，计划仍可使用，但 HR 应先确认这些依据是否足够。',
  },
  priority_signal_conflict: {
    title: 'JD 中的优先级表达有冲突',
    description: '请修改 JD，把必要条件或优先条件移动到正确字段；页面不会自行猜测或改写优先级。',
  },
  misplaced_non_evaluation_content: {
    title: '评价字段中包含非评价内容',
    description: 'JD 中可能混入公司宣传、福利或招聘流程，请修改 JD 后再生成，避免它们成为评价依据。',
  },
  overly_broad_jd: {
    title: '岗位事实较多',
    description: '当前 JD 形成了 31 条或更多事实，系统没有截断。请重点核对是否存在可合并的重复表述。',
  },
  conflicting_requirements: {
    title: '原文要求存在冲突',
    description: '同一事实在不同原文位置存在优先级或内容冲突。页面保留全部来源，请修改 JD 消除歧义。',
  },
  ambiguous_requirement: {
    title: '部分要求含义模糊',
    description: '这些原文没有被自行补成年限、数量或等级。请确认是否需要回到 JD 写得更明确。',
  },
  non_evaluation_content: {
    title: '评价字段包含非评价内容',
    description: '系统识别到福利、宣传或招聘流程等内容，并且没有把它们变成候选人评价事实。',
  },
  many_criteria: {
    title: '评价点较多',
    description: '当前清单超过 12 项，但系统没有截断。请 HR 检查是否需要合并同一主题。',
  },
  importance_review_required: {
    title: '重要程度需要 HR 复核',
    description: 'AI 建议与原文信号存在差异或复杂语气，请对照来源后修改或明确确认。',
  },
  semantic_support_review_required: {
    title: '语义支持需要 HR 复核',
    description: 'AI 评价点可能扩大了所引 JD 原文的含义，请 HR 对照原文后修改或明确确认。',
  },
};

const IMPORTANCE_REVIEW_REASON_LABELS: Record<JobEvaluationPlanV5ImportanceReviewReason, string> = {
  explicit_strong_signal_mismatch: '原文有明确强约束，但当前建议不一致',
  explicit_weak_signal_mismatch: '原文有明确弱约束，但当前建议不一致',
  no_explicit_signal_non_general: '原文没有明确强弱信号，建议复核是否应为一般项',
  mixed_strength_signals: '同一评价点包含强弱混合表达',
  complex_qualification_language: '原文包含否定、转折或可放宽语义',
  source_field_signal_mismatch: '原文语气与所在 JD 字段的常见含义不同',
  multi_source_signal_conflict: '多处来源的强弱信号不一致',
};

type LoadState =
  | { status: 'idle' | 'loading' }
  | { status: 'empty' }
  | { status: 'error'; message: string; code: string | null }
  | { status: 'ready'; plan: JobEvaluationPlan };

type Props = {
  job: RecruitmentJob | null;
  open: boolean;
  onClose: () => void;
  onEditJob: (job: RecruitmentJob) => void;
};

const formatDateTime = (value: string | null) => {
  if (!value) return '尚未完成';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date);
};

const JobEvaluationPlanDrawer: React.FC<Props> = ({ job, open, onClose, onEditJob }) => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'idle' });
  const [history, setHistory] = useState<JobEvaluationPlan[]>([]);
  const [actionPending, setActionPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draftCriteria, setDraftCriteria] = useState<V5CriterionDraft[]>([]);
  const [mergeSelection, setMergeSelection] = useState<string[]>([]);
  const requestIdRef = useRef(0);

  const load = useCallback(async (showLoading = false): Promise<JobEvaluationPlan | null> => {
    if (!job || !open) return null;
    const requestId = ++requestIdRef.current;
    if (showLoading) setLoadState({ status: 'loading' });
    try {
      const plan = await getJobEvaluationPlan(job.id);
      if (shouldApplyScreeningResponse(requestId, requestIdRef.current)) {
        setLoadState({ status: 'ready', plan });
        setActionError(null);
        void listJobEvaluationPlans(job.id)
          .then(plans => {
            if (shouldApplyScreeningResponse(requestId, requestIdRef.current)) setHistory(plans);
          })
          .catch(() => {
            if (shouldApplyScreeningResponse(requestId, requestIdRef.current)) setHistory([]);
          });
      }
      return plan;
    } catch (error) {
      if (!shouldApplyScreeningResponse(requestId, requestIdRef.current)) return null;
      const parsed = getAIScreeningApiError(error);
      if (parsed.status === 404 || parsed.code === 'JOB_EVALUATION_PLAN_NOT_FOUND') {
        setLoadState({ status: 'empty' });
      } else {
        setLoadState({ status: 'error', message: parsed.message, code: parsed.code });
      }
      return null;
    }
  }, [job, open]);

  useEffect(() => {
    if (open) void load(true);
    return () => {
      requestIdRef.current += 1;
      setActionError(null);
      setEditing(false);
      setMergeSelection([]);
    };
  }, [load, open]);

  const plan = loadState.status === 'ready' ? loadState.plan : null;

  useEffect(() => {
    if (!plan || plan.schemaVersion !== '5.0' || editing) return;
    setDraftCriteria(plan.v5Criteria.map(criterion => ({ ...criterion })));
  }, [editing, plan?.editVersion, plan?.id, plan?.schemaVersion]);

  useEffect(() => {
    if (!open || !job || job.status === 'closed' || plan?.status !== 'generating') return undefined;
    let cancelled = false;
    let timerId: number | undefined;
    const schedule = () => {
      timerId = window.setTimeout(async () => {
        const next = await load(false);
        if (!cancelled && next?.status === 'generating') schedule();
      }, PLAN_POLL_INTERVAL_MS);
    };
    schedule();
    return () => {
      cancelled = true;
      if (timerId !== undefined) window.clearTimeout(timerId);
    };
  }, [job, load, open, plan?.id, plan?.status]);

  const submitPlanAction = async (action: 'generate' | 'regenerate') => {
    if (!job || job.status !== 'open' || actionPending) return;
    setActionPending(true);
    setActionError(null);
    try {
      const next = action === 'regenerate'
        ? await regenerateJobEvaluationPlan(job.id)
        : await generateJobEvaluationPlan(job.id);
      setLoadState({ status: 'ready', plan: next });
    } catch (error) {
      setActionError(getAIScreeningApiError(error).message);
    } finally {
      setActionPending(false);
    }
  };

  const confirmPlan = async () => {
    if (!job || job.status !== 'open' || actionPending || plan?.editVersion === null || plan?.editVersion === undefined) return;
    setActionPending(true);
    setActionError(null);
    try {
      const next = await confirmJobEvaluationPlan(job.id, plan.editVersion);
      setLoadState({ status: 'ready', plan: next });
      setEditing(false);
      setHistory(await listJobEvaluationPlans(job.id));
    } catch (error) {
      setActionError(getAIScreeningApiError(error).message);
    } finally {
      setActionPending(false);
    }
  };

  const updateDraftCriterion = (index: number, patch: Partial<V5CriterionDraft>) => {
    setDraftCriteria(current => current.map((criterion, criterionIndex) => (
      criterionIndex === index ? { ...criterion, ...patch } : criterion
    )));
  };

  const addDraftCriterion = () => {
    setDraftCriteria(current => [...current, {
      criterionId: null,
      name: '',
      importance: 'general',
      description: '',
      screeningFocus: '',
      origin: 'hr_added',
      sources: [],
      hrNote: '',
    }]);
    setEditing(true);
  };

  const removeDraftCriterion = (index: number) => {
    setDraftCriteria(current => current.filter((_, criterionIndex) => criterionIndex !== index));
    setMergeSelection([]);
  };

  const mergeDraftCriteria = () => {
    const selected = draftCriteria.filter((criterion, index) => (
      mergeSelection.includes(criterion.criterionId ?? `new:${index}`)
    ));
    if (selected.length < 2) {
      setActionError('请至少选择 2 个评价点再合并。');
      return;
    }
    const first = selected[0];
    const allFromJd = selected.every(criterion => criterion.origin === 'ai_from_jd');
    const mergedSources = allFromJd
      ? Array.from(new Map(selected.flatMap(criterion => criterion.sources).map(source => [
        `${source.sourceField}:${source.sourceQuote}`,
        source,
      ])).values())
      : [];
    const merged: V5CriterionDraft = {
      criterionId: first.criterionId,
      name: selected.map(criterion => criterion.name).filter(Boolean).join(' / ').slice(0, 200),
      importance: selected.some(criterion => criterion.importance === 'required')
        ? 'required'
        : selected.some(criterion => criterion.importance === 'preferred') ? 'preferred' : 'general',
      description: selected.map(criterion => criterion.description).filter(Boolean).join('；').slice(0, 2_000),
      screeningFocus: selected.map(criterion => criterion.screeningFocus).filter(Boolean).join('；').slice(0, 2_000),
      origin: allFromJd ? 'ai_from_jd' : 'hr_added',
      sources: mergedSources,
      hrNote: allFromJd
        ? first.hrNote
        : `HR 合并：${selected.map(criterion => criterion.name).filter(Boolean).join('、')}`.slice(0, 2_000),
    };
    const selectedKeys = new Set(mergeSelection);
    let inserted = false;
    setDraftCriteria(current => current.flatMap((criterion, index) => {
      const key = criterion.criterionId ?? `new:${index}`;
      if (!selectedKeys.has(key)) return [criterion];
      if (inserted) return [];
      inserted = true;
      return [merged];
    }));
    setMergeSelection([]);
    setEditing(true);
  };

  const saveDraft = async () => {
    if (!job || !plan?.editVersion || actionPending) return;
    const hasInvalid = draftCriteria.length === 0 || draftCriteria.some(criterion => (
      !criterion.name.trim()
      || !criterion.description.trim()
      || !criterion.screeningFocus.trim()
      || (criterion.origin === 'hr_added' && !criterion.hrNote?.trim())
    ));
    if (hasInvalid) {
      setActionError('每个评价点都要填写名称、说明和初筛重点；HR 补充项还要填写补充说明。');
      return;
    }
    setActionPending(true);
    setActionError(null);
    try {
      const next = await saveJobEvaluationPlanDraft(job.id, plan.editVersion, draftCriteria);
      setLoadState({ status: 'ready', plan: next });
      setDraftCriteria(next.v5Criteria.map(criterion => ({ ...criterion })));
      setHistory(await listJobEvaluationPlans(job.id));
      setEditing(false);
    } catch (error) {
      const parsed = getAIScreeningApiError(error);
      setActionError(parsed.status === 409
        ? `${parsed.message} 清单已被其他操作更新，请刷新后再编辑。`
        : parsed.message);
    } finally {
      setActionPending(false);
    }
  };

  const createEditableVersion = async () => {
    if (!job || !plan?.editVersion || actionPending) return;
    setActionPending(true);
    setActionError(null);
    try {
      const next = await createJobEvaluationPlanVersion(job.id, plan.editVersion);
      setLoadState({ status: 'ready', plan: next });
      setDraftCriteria(next.v5Criteria.map(criterion => ({ ...criterion })));
      setHistory(await listJobEvaluationPlans(job.id));
      setEditing(true);
    } catch (error) {
      setActionError(getAIScreeningApiError(error).message);
    } finally {
      setActionPending(false);
    }
  };

  const editJob = () => {
    if (job) onEditJob(job);
  };

  const renderPlanActions = () => {
    if (!job || job.status !== 'open') return null;
    if (!plan) {
      if (loadState.status !== 'empty') return null;
      return (
        <Button loading={actionPending} onClick={() => void submitPlanAction('generate')} type="primary">
          生成评价计划
        </Button>
      );
    }
    if (plan.status === 'generating') return <Button disabled loading>评价计划生成中</Button>;
    if (plan.contractOutdated) {
      return (
        <Button loading={actionPending} onClick={() => void submitPlanAction('generate')} type="primary">
          按五段式新规则生成 5.0 清单
        </Button>
      );
    }
    if (plan.status === 'pending_confirmation') {
      if (plan.schemaVersion === '5.0') {
        return (
          <>
            <Button icon={<EditOutlined />} onClick={() => setEditing(value => !value)}>
              {editing ? '结束编辑' : '编辑清单'}
            </Button>
            {editing && <Button icon={<PlusOutlined />} onClick={addDraftCriterion}>新增评价点</Button>}
            {editing && <Button icon={<MergeCellsOutlined />} disabled={mergeSelection.length < 2} onClick={mergeDraftCriteria}>合并选中</Button>}
            {editing && <Button icon={<SaveOutlined />} loading={actionPending} onClick={() => void saveDraft()}>保存草稿</Button>}
            <Popconfirm
              cancelText="继续核对"
              description="确认后这版清单变为只读，并可用于候选人初筛；当前全部 warning 也视为已由 HR 审核。"
              okText="确认清单"
              onConfirm={confirmPlan}
              title="确认这版评价清单？"
            >
              <Button
                disabled={editing}
                icon={<CheckOutlined />}
                loading={actionPending}
                title={editing ? '请先保存草稿并结束编辑，再确认评价清单' : undefined}
                type="primary"
              >
                确认评价计划
              </Button>
            </Popconfirm>
          </>
        );
      }
      return (
        <>
          <Button icon={<EditOutlined />} onClick={editJob}>修改 JD</Button>
          <Popconfirm
            cancelText="继续核对"
            description="确认后，正在等待计划的申请可以进入 AI 初筛；事实内容不会被改动。"
            okText="确认评价计划"
            onConfirm={confirmPlan}
            title="确认这份评价计划？"
          >
            <Button icon={<CheckOutlined />} loading={actionPending} type="primary">
              确认评价计划
            </Button>
          </Popconfirm>
        </>
      );
    }
    if (plan.status === 'failed') {
      return (
        <>
          <Button icon={<EditOutlined />} onClick={editJob}>修改 JD</Button>
          <Button loading={actionPending} onClick={() => void submitPlanAction('regenerate')} type="primary">重试生成</Button>
        </>
      );
    }
    if (plan.status === 'outdated') {
      return (
        <>
          <Button icon={<EditOutlined />} onClick={editJob}>修改 JD</Button>
          <Button loading={actionPending} onClick={() => void submitPlanAction('generate')} type="primary">按当前 JD 生成</Button>
        </>
      );
    }
    if (plan.status === 'ready' && plan.schemaVersion === '5.0') {
      return (
        <Button icon={<EditOutlined />} loading={actionPending} onClick={() => void createEditableVersion()}>
          创建新编辑版本
        </Button>
      );
    }
    return null;
  };

  const warningDetails = plan?.warnings.map(warning => (
    typeof warning === 'string'
      ? { code: warning, sourceUnitIds: [], factIds: [], criterionId: null, reasons: [] }
      : warning
  )) ?? [];

  return (
    <Drawer
      className="recruitment-plan-drawer"
      destroyOnClose
      extra={(
        <Button
          aria-label="刷新评价计划"
          disabled={actionPending}
          icon={<ReloadOutlined />}
          onClick={() => void load(false)}
        />
      )}
      footer={<div className="recruitment-plan-actions">{renderPlanActions()}</div>}
      onClose={onClose}
      open={open}
      title={job ? `${job.title} · AI 评价计划` : 'AI 评价计划'}
      width="min(780px, 100vw)"
    >
      <Alert
        description="5.0 用完整 JD 生成轻量评价清单，AI 先提建议，HR 可以编辑、补充、合并并确认；importance 只是重要程度，不是权重，也不会自动淘汰候选人。历史 4.0 的评价计划只把当前 JD 原文事实用于解释旧报告，1.0—4.0 均保持只读。"
        icon={<SafetyCertificateOutlined />}
        message="AI 初筛的只读评价依据"
        showIcon
        type="info"
      />

      {job?.status === 'draft' && (
        <Alert className="recruitment-plan-state" description="请先补齐岗位职责和任职要求并开放岗位；草稿不会生成评价计划。" message="岗位仍是草稿" showIcon type="warning" />
      )}
      {job?.status === 'closed' && (
        <Alert className="recruitment-plan-state" description="岗位已关闭，评价计划只读；不能生成、重试或用于新的 AI 初筛。" message="历史内容只读" showIcon type="info" />
      )}
      {loadState.status === 'loading' && (
        <div className="recruitment-plan-loading"><Skeleton active paragraph={{ rows: 8 }} /></div>
      )}
      {loadState.status === 'error' && (
        <Alert action={<Button onClick={() => void load(true)}>重试读取</Button>} className="recruitment-plan-state" description={loadState.message} message={loadState.code ? `评价计划读取失败 · ${loadState.code}` : '评价计划读取失败'} showIcon type="error" />
      )}
      {actionError && (
        <Alert className="recruitment-plan-state" closable message={actionError} onClose={() => setActionError(null)} showIcon type="error" />
      )}
      {loadState.status === 'empty' && job?.status !== 'draft' && (
        <Empty
          className="recruitment-plan-empty"
          description={job?.status === 'open'
            ? '当前开放岗位还没有评价计划。生成后，页面会按评价维度展示全部 JD 原文事实。'
            : '该岗位没有可查看的历史评价计划。'}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}

      {plan && (
        <div className="recruitment-plan-content">
          <section className="recruitment-plan-summary" aria-label="评价计划摘要">
            <div><span>当前状态</span><Tag color={PLAN_STATUS_META[plan.status].tone}>{PLAN_STATUS_META[plan.status].label}</Tag><p>{PLAN_STATUS_META[plan.status].description}</p></div>
            <div><span>{plan.schemaVersion === '5.0' ? '轻量评价点' : plan.schemaVersion === '4.0' ? '原文事实' : '历史事项'}</span><strong>{plan.schemaVersion === '5.0' ? plan.v5Criteria.length : plan.schemaVersion === '4.0' ? plan.requirementFacts.length : plan.items.length}</strong><p>{plan.schemaVersion === '5.0' ? `编辑版本 ${plan.editVersion ?? '—'}` : `共审阅 ${plan.sourceReviewSummary?.totalUnits ?? '—'} 个 JD 片段`}</p></div>
            <div><span>当前 JD</span><strong>{plan.isCurrent ? '与当前岗位一致' : '历史输入'}</strong><p>生成于 {formatDateTime(plan.completedAt)}</p></div>
            <div><span>合同版本</span><strong>Schema {plan.schemaVersion}</strong><p>更新于 {formatDateTime(plan.updatedAt)}</p></div>
          </section>

          {plan.status === 'generating' && (
            <Alert description="页面每 4 秒自动刷新；关闭抽屉或离开页面后会停止轮询，但不会取消后台任务。" message="正在生成，请勿重复提交" showIcon type="info" />
          )}
          {plan.status === 'pending_confirmation' && !plan.contractOutdated && (
            <Alert description={plan.schemaVersion === '5.0' ? '请核对每个评价点的重要程度、说明、初筛重点、JD 原文和 warning。保存不会调用模型；确认后这版只读并可用于初筛。' : '请逐项核对评价维度、JD 原文和 warning。确认只改变计划状态，不会改动任何原文事实，也不会再次调用模型。'} message="等待 HR 确认后才能开始初筛" showIcon type="warning" />
          )}
          {plan.status === 'ready' && !plan.contractOutdated && (
            <Alert description={plan.schemaVersion === '5.0' ? '当前版本已经 HR 确认并保持只读。需要调整时创建新编辑版本，旧版本仍用于解释历史报告。' : '同一份 JD 的已确认计划保持只读，不能把反复生成当作抽卡。需要修正时请先修改 JD。'} message="当前计划已确认" showIcon type="success" />
          )}
          {plan.contractOutdated && (
            <Alert description="该计划按 1.0—4.0 旧合同生成，只能用于解释历史结果。开放岗位必须生成并确认 5.0 清单，才能继续新的 AI 初筛。" message="历史只读 · 当前评价计划使用旧规则" showIcon type="warning" />
          )}

          {warningDetails.map((warning, index) => {
            const copy = WARNING_COPY[warning.code];
            return (
              <Alert
                className="recruitment-plan-warning"
                description={<div><span>{copy.description}</span>{warning.criterionId && <code>评价点：{warning.criterionId}</code>}{warning.reasons.map(reason => <span key={reason}>• {IMPORTANCE_REVIEW_REASON_LABELS[reason]}</span>)}{warning.sourceUnitIds.length > 0 && <code>涉及片段：{warning.sourceUnitIds.join('、')}</code>}{warning.factIds.length > 0 && <code>涉及事实：{warning.factIds.join('、')}</code>}</div>}
                key={`${warning.code}-${index}`}
                message={copy.title}
                showIcon
                type="warning"
              />
            );
          })}

          {plan.status === 'failed' && (
            <Alert description={plan.errorMessage || '当前评价计划未能生成。请重试生成；若仍失败，请修改 JD 后再试。'} message={plan.errorCode ? `生成失败 · ${plan.errorCode}` : '生成失败'} showIcon type="error" />
          )}
          {plan.status === 'outdated' && (
            <Alert description="旧计划继续用于解释已有历史结果，但不能用于当前 JD 的新申请。可查看下方历史内容，并按当前 JD 生成新计划。" message="这份计划基于旧 JD" showIcon type="warning" />
          )}

          {plan.schemaVersion === '4.0' && plan.coverageReviewSummary && (
            <div className="recruitment-plan-verification" aria-label="计划复核摘要">
              <div><span>完整性复核</span><strong>{plan.coverageReviewSummary.status === 'passed' ? '已通过' : '需要修复'}</strong><p>复核 {plan.coverageReviewSummary.reviewedSourceUnitIds.length} 个原文片段</p></div>
              <div><span>生成审计</span><strong>{plan.generationAudit?.businessCallCount ?? '—'} 次业务调用</strong><p>{plan.generationAudit?.contentRepairCount ? '执行过一次局部修复' : '未执行局部修复'}</p></div>
            </div>
          )}

          {plan.schemaVersion === '5.0' && (
            <section className="recruitment-plan-v5" aria-label="5.0 轻量评价清单">
              <div className="recruitment-plan-section-heading">
                <div><span>LIGHTWEIGHT CRITERIA</span><h3>HR 已审核的初筛尺子</h3></div>
                <span>{draftCriteria.length} 个评价点</span>
              </div>
              {(draftCriteria.length < 5 || draftCriteria.length > 12) && (
                <Alert
                  message={draftCriteria.length < 5
                    ? '评价点少于通常的 5 项，请确认依据是否足够。'
                    : '评价点多于通常的 12 项，请检查能否合并。'}
                  showIcon
                  type="warning"
                />
              )}
              <div className="recruitment-plan-v5-list">
                {draftCriteria.map((criterion, index) => {
                  const selectionKey = criterion.criterionId ?? `new:${index}`;
                  const relatedWarnings = warningDetails.filter(warning => warning.criterionId === criterion.criterionId);
                  return (
                    <article className={`recruitment-plan-v5-item ${editing ? 'is-editing' : ''}`} key={selectionKey}>
                      <div className="recruitment-plan-v5-index">
                        {editing && (
                          <Checkbox
                            aria-label={`选择第 ${index + 1} 个评价点用于合并`}
                            checked={mergeSelection.includes(selectionKey)}
                            onChange={event => setMergeSelection(current => event.target.checked
                              ? [...current, selectionKey]
                              : current.filter(key => key !== selectionKey))}
                          />
                        )}
                        <span>{String(index + 1).padStart(2, '0')}</span>
                      </div>
                      <div className="recruitment-plan-v5-body">
                        <div className="recruitment-plan-v5-heading">
                          {editing ? (
                            <Input aria-label={`评价点 ${index + 1} 名称`} value={criterion.name} onChange={event => updateDraftCriterion(index, { name: event.target.value })} />
                          ) : <h4>{criterion.name}</h4>}
                          <div>
                            {editing ? (
                              <Select
                                aria-label={`评价点 ${index + 1} 重要程度`}
                                value={criterion.importance}
                                onChange={importance => updateDraftCriterion(index, { importance })}
                                options={[
                                  { value: 'required', label: '必备' },
                                  { value: 'preferred', label: '优先' },
                                  { value: 'general', label: '一般' },
                                ]}
                              />
                            ) : (
                              <Tag color={criterion.importance === 'required' ? 'red' : criterion.importance === 'preferred' ? 'gold' : 'default'}>
                                {PRIORITY_LABELS[criterion.importance]}
                              </Tag>
                            )}
                            <Tag color={criterion.origin === 'hr_added' ? 'purple' : 'blue'}>
                              {criterion.origin === 'hr_added' ? 'HR 补充' : 'AI 来源 · JD'}
                            </Tag>
                          </div>
                        </div>
                        <code>{criterion.criterionId ?? '保存后由程序分配稳定 ID'}</code>
                        {editing ? (
                          <div className="recruitment-plan-v5-fields">
                            <Input.TextArea aria-label={`评价点 ${index + 1} 说明`} autoSize={{ minRows: 2, maxRows: 6 }} value={criterion.description} onChange={event => updateDraftCriterion(index, { description: event.target.value })} />
                            <Input.TextArea aria-label={`评价点 ${index + 1} 初筛重点`} autoSize={{ minRows: 2, maxRows: 6 }} value={criterion.screeningFocus} onChange={event => updateDraftCriterion(index, { screeningFocus: event.target.value })} />
                            {criterion.origin === 'hr_added' && (
                              <Input.TextArea aria-label={`评价点 ${index + 1} HR 补充说明`} autoSize={{ minRows: 2, maxRows: 5 }} value={criterion.hrNote ?? ''} onChange={event => updateDraftCriterion(index, { hrNote: event.target.value })} />
                            )}
                          </div>
                        ) : (
                          <div className="recruitment-plan-v5-copy">
                            <p>{criterion.description}</p>
                            <strong>初筛重点</strong><p>{criterion.screeningFocus}</p>
                            {criterion.hrNote && <p className="recruitment-plan-hr-note">HR 说明：{criterion.hrNote}</p>}
                          </div>
                        )}
                        {criterion.sources.length > 0 ? (
                          <details className="recruitment-plan-sources" open={relatedWarnings.length > 0}>
                            <summary>{criterion.sources.length} 处 JD 原文依据</summary>
                            {criterion.sources.map(source => (
                              <blockquote key={`${source.sourceField}-${source.sourceQuote}`}>
                                <span>{SOURCE_FIELD_LABELS[source.sourceField]}</span>
                                <p>{source.sourceQuote}</p>
                              </blockquote>
                            ))}
                          </details>
                        ) : <p className="recruitment-plan-hr-source">此项由 HR 补充，不冒充 JD 原文。</p>}
                        {editing && (
                          <Popconfirm title="删除这个评价点？" description="保存草稿后删除才会生效。" onConfirm={() => removeDraftCriterion(index)}>
                            <Button danger icon={<DeleteOutlined />}>删除</Button>
                          </Popconfirm>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          )}

          {plan.schemaVersion === '4.0' && plan.requirementFacts.length > 0 && plan.evaluationCriteria.map(criterion => {
            const criterionFacts = criterion.factIds
              .map(factId => plan.requirementFacts.find(fact => fact.factId === factId))
              .filter((fact): fact is NonNullable<typeof fact> => Boolean(fact));
            return (
              <section className="recruitment-plan-criterion" key={criterion.criterionId} aria-label={`${criterion.name}评价维度`}>
                <div className="recruitment-plan-section-heading">
                  <div><span>EVALUATION CRITERION</span><h3>{criterion.name}</h3></div>
                  <span>{criterionFacts.length} 条事实</span>
                </div>
                <div className="recruitment-plan-fact-list">
                  {criterionFacts.map((fact, index) => (
                    <article className="recruitment-plan-fact" key={fact.factId}>
                      <span className="recruitment-plan-index">{String(index + 1).padStart(2, '0')}</span>
                      <div>
                        <div className="recruitment-plan-fact-heading">
                          <code>{fact.factId}</code>
                          <div>
                            <Tag>{CATEGORY_LABELS[fact.category]}</Tag>
                            <Tag color={fact.priority === 'required' ? 'red' : fact.priority === 'preferred' ? 'gold' : 'default'}>{PRIORITY_LABELS[fact.priority]}</Tag>
                          </div>
                        </div>
                        <p className="recruitment-plan-fact-quote">{fact.sources[0]?.sourceQuote || '原文依据未记录'}</p>
                        <details className="recruitment-plan-sources">
                          <summary>{fact.sources.length} 处 JD 原文依据</summary>
                          {fact.sources.map(source => (
                            <blockquote key={`${source.sourceUnitId}-${source.sourceQuote}`}>
                              <span>{SOURCE_FIELD_LABELS[source.sourceField]} · {source.sourceUnitId}</span>
                              <p>{source.sourceQuote}</p>
                            </blockquote>
                          ))}
                        </details>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}

          {!['4.0', '5.0'].includes(plan.schemaVersion) && plan.items.length > 0 ? PLAN_GROUPS.map(group => {
            const groupItems = plan.items.filter(item => item.priority === group.priority);
            return (
              <section className="recruitment-plan-items" key={group.priority} aria-label={`${group.title}评价事项`}>
                <div className="recruitment-plan-section-heading"><div><span>{group.eyebrow}</span><h3>{group.title}</h3></div><span>{groupItems.length} 项</span></div>
                {groupItems.length === 0 ? (
                  <p className="recruitment-plan-group-empty">{group.empty}</p>
                ) : groupItems.map((item, index) => (
                  <article className="recruitment-plan-item" key={item.key}>
                    <span className="recruitment-plan-index">{String(index + 1).padStart(2, '0')}</span>
                    <div>
                      <div className="recruitment-plan-item-title">
                        <h4>{item.title}</h4>
                        <Tag>{CATEGORY_LABELS[item.category]}</Tag>
                        <Tag color={item.priority === 'required' ? 'red' : item.priority === 'preferred' ? 'gold' : 'default'}>{PRIORITY_LABELS[item.priority]}</Tag>
                      </div>
                      {item.sources.length > 0 ? (
                        <details className="recruitment-plan-sources">
                          <summary>{item.sources.length} 处 JD 原文依据</summary>
                          {item.sources.map(source => (
                            <blockquote key={`${source.sourceUnitId}-${source.sourceQuote}`}>
                              <span>{SOURCE_FIELD_LABELS[source.sourceField]} · {source.sourceUnitId}</span>
                              <p>{source.sourceQuote}</p>
                            </blockquote>
                          ))}
                        </details>
                      ) : (
                        <p>历史来源：{item.historicalSource?.field || item.historicalSource?.kind || '未记录'} · {item.historicalSource?.quote || '原文依据未记录'}</p>
                      )}
                      <code>{item.key}</code>
                    </div>
                  </article>
                ))}
              </section>
            );
          }) : !['4.0', '5.0'].includes(plan.schemaVersion) && plan.status !== 'failed' && (
            <Empty description="当前计划还没有可展示的评价事项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}

          {plan.schemaVersion === '4.0' && plan.requirementFacts.length === 0 && plan.status !== 'failed' && plan.status !== 'generating' && (
            <Empty description="当前计划还没有可展示的原文事实" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}

          {history.length > 1 && (
            <section className="recruitment-plan-history" aria-label="评价计划版本历史">
              <div className="recruitment-plan-section-heading">
                <div><span>VERSION HISTORY</span><h3>只读版本历史</h3></div>
                <span>{history.length} 个版本</span>
              </div>
              <Collapse
                items={history.filter(item => item.id !== plan.id).map(item => ({
                  key: String(item.id),
                  label: `计划 #${item.id} · Schema ${item.schemaVersion} · ${PLAN_STATUS_META[item.status].label}`,
                  children: (
                    <div className="recruitment-plan-history-entry">
                      <p>{item.schemaVersion === '5.0'
                        ? `${item.v5Criteria.length} 个轻量评价点 · 编辑版本 ${item.editVersion ?? '—'}`
                        : '历史 1.0—4.0 计划只用于解释当时报告，不提供编辑。'}</p>
                      {item.schemaVersion === '5.0' && item.v5Criteria.map(criterion => (
                        <div key={criterion.criterionId}><code>{criterion.criterionId}</code><span>{criterion.name}</span><Tag>{PRIORITY_LABELS[criterion.importance]}</Tag></div>
                      ))}
                    </div>
                  ),
                }))}
              />
            </section>
          )}

          <footer className="recruitment-plan-meta"><span>计划 #{plan.id} · {plan.isCurrent ? '当前 JD' : '历史 JD'}</span><span>{plan.schemaVersion === '5.0' ? 'AI 建议，HR 编辑并确认' : '历史计划只读，不改写旧证据'}</span></footer>
        </div>
      )}
    </Drawer>
  );
};

export default JobEvaluationPlanDrawer;
