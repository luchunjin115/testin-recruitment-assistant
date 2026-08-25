import React, { useCallback, useEffect, useRef, useState } from 'react';
import { CheckOutlined, EditOutlined, ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { Alert, Button, Drawer, Empty, Popconfirm, Skeleton, Tag } from 'antd';
import {
  confirmJobEvaluationPlan,
  generateJobEvaluationPlan,
  getAIScreeningApiError,
  getJobEvaluationPlan,
  regenerateJobEvaluationPlan,
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
  const [actionPending, setActionPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
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
    };
  }, [load, open]);

  const plan = loadState.status === 'ready' ? loadState.plan : null;

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
    if (!job || job.status !== 'open' || actionPending) return;
    setActionPending(true);
    setActionError(null);
    try {
      const next = await confirmJobEvaluationPlan(job.id);
      setLoadState({ status: 'ready', plan: next });
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
          按五段式新规则生成 4.0 计划
        </Button>
      );
    }
    if (plan.status === 'pending_confirmation') {
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
    return null;
  };

  const warningDetails = plan?.warnings.map(warning => (
    typeof warning === 'string'
      ? { code: warning, sourceUnitIds: [], factIds: [] }
      : { code: warning.code, sourceUnitIds: warning.sourceUnitIds, factIds: warning.factIds }
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
        description="评价计划只把当前 JD 中可评价的内容保留为原文事实，再用评价维度组织展示；每条事实仍独立评价，不设置维度分、权重或自动淘汰条件。发现不准确时，请修改原 JD。"
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
            <div><span>{plan.schemaVersion === '4.0' ? '原文事实' : '历史事项'}</span><strong>{plan.schemaVersion === '4.0' ? plan.requirementFacts.length : plan.items.length}</strong><p>共审阅 {plan.sourceReviewSummary?.totalUnits ?? '—'} 个 JD 片段</p></div>
            <div><span>当前 JD</span><strong>{plan.isCurrent ? '与当前岗位一致' : '历史输入'}</strong><p>生成于 {formatDateTime(plan.completedAt)}</p></div>
            <div><span>合同版本</span><strong>Schema {plan.schemaVersion}</strong><p>更新于 {formatDateTime(plan.updatedAt)}</p></div>
          </section>

          {plan.status === 'generating' && (
            <Alert description="页面每 4 秒自动刷新；关闭抽屉或离开页面后会停止轮询，但不会取消后台任务。" message="正在生成，请勿重复提交" showIcon type="info" />
          )}
          {plan.status === 'pending_confirmation' && !plan.contractOutdated && (
            <Alert description="请逐项核对评价维度、JD 原文和 warning。确认只改变计划状态，不会改动任何原文事实，也不会再次调用模型。" message="等待 HR 确认后才能开始初筛" showIcon type="warning" />
          )}
          {plan.status === 'ready' && !plan.contractOutdated && (
            <Alert description="同一份 JD 的已确认计划保持只读，不能把反复生成当作抽卡。需要修正时请先修改 JD。" message="当前计划已确认" showIcon type="success" />
          )}
          {plan.contractOutdated && (
            <Alert description="该计划按 1.0—3.0 旧合同生成，只能用于解释历史结果。开放岗位必须生成并确认 4.0 计划，才能继续新的 AI 初筛。" message="历史只读 · 当前评价计划使用旧规则" showIcon type="warning" />
          )}

          {warningDetails.map((warning, index) => {
            const copy = WARNING_COPY[warning.code];
            return (
              <Alert
                className="recruitment-plan-warning"
                description={<div><span>{copy.description}</span>{warning.sourceUnitIds.length > 0 && <code>涉及片段：{warning.sourceUnitIds.join('、')}</code>}{warning.factIds.length > 0 && <code>涉及事实：{warning.factIds.join('、')}</code>}</div>}
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

          {plan.schemaVersion !== '4.0' && plan.items.length > 0 ? PLAN_GROUPS.map(group => {
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
          }) : plan.schemaVersion !== '4.0' && plan.status !== 'failed' && (
            <Empty description="当前计划还没有可展示的评价事项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}

          {plan.schemaVersion === '4.0' && plan.requirementFacts.length === 0 && plan.status !== 'failed' && plan.status !== 'generating' && (
            <Empty description="当前计划还没有可展示的原文事实" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}

          <footer className="recruitment-plan-meta"><span>计划 #{plan.id} · {plan.isCurrent ? '当前 JD' : '历史 JD'}</span><span>评价依据只能通过修改 JD 纠正</span></footer>
        </div>
      )}
    </Drawer>
  );
};

export default JobEvaluationPlanDrawer;
