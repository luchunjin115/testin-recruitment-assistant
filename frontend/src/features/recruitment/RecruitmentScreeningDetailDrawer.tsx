import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  HistoryOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Alert, Button, Drawer, Empty, Progress, Skeleton, Tag } from 'antd';
import {
  getStage7ApplicationApiError,
  getStage7ScreeningResult,
  listStage7ApplicationScreenings,
} from './services/applications';
import type { Stage7ScreeningCenterItem } from './services/screening';
import {
  getStage7DimensionViews,
  getStage7HardRequirementViews,
  getStage7RubricVersion,
  getStage7SemanticCriterionViews,
  STAGE7_CRITERION_LABELS,
  STAGE7_DIMENSION_LABELS,
  STAGE7_EVIDENCE_SOURCE_LABELS,
} from './screeningDetailView';
import type {
  Stage7ScreeningExecutionStatus,
  Stage7ScreeningResultDetail,
  Stage7ScreeningResultSummary,
} from './types/applicationScreening';

type Props = {
  item: Stage7ScreeningCenterItem | null;
  onClose: () => void;
};

type HistoryState =
  | { status: 'idle' | 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; items: Stage7ScreeningResultSummary[] };

type DetailState =
  | { status: 'idle' | 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; detail: Stage7ScreeningResultDetail };

type StatusMeta = { label: string; tone: 'info' | 'success' | 'warning' | 'danger' | 'neutral' };

const EXECUTION_META: Record<Stage7ScreeningExecutionStatus, StatusMeta> = {
  screening: { label: '评分中', tone: 'info' },
  completed: { label: '已完成', tone: 'success' },
  failed: { label: '失败', tone: 'danger' },
  blocked: { label: '资料不足', tone: 'warning' },
};

const RECOMMENDATION_LABELS: Record<string, string> = {
  strong_recommend: '强烈推荐',
  recommend: '推荐',
  review_required: '需要人工复核',
  low_match: '匹配度较低',
};

const HARD_STATUS_META = {
  passed: { label: '通过', tone: 'success', icon: <CheckCircleOutlined /> },
  failed: { label: '未通过', tone: 'danger', icon: <CloseCircleOutlined /> },
  unknown: { label: '证据未知', tone: 'warning', icon: <InfoCircleOutlined /> },
} as const;

const CONFIDENCE_LABELS: Record<string, string> = {
  high: '高置信度',
  medium: '中置信度',
  low: '低置信度',
};

const formatDateTime = (value: string | null) => {
  if (!value) return '时间未记录';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date);
};

const formatDuration = (value: number | null) => {
  if (value === null) return '未记录';
  if (value < 1_000) return `${value} ms`;
  return `${(value / 1_000).toFixed(value >= 10_000 ? 1 : 2)} 秒`;
};

const percent = (value: number | null) => (
  value === null ? null : Math.round(value * 100)
);

const detailErrorMessage = (error: unknown, fallback: string) => {
  const parsed = getStage7ApplicationApiError(error);
  return parsed.code || parsed.status ? parsed.message : fallback;
};

const RecruitmentScreeningDetailDrawer: React.FC<Props> = ({ item, onClose }) => {
  const [historyState, setHistoryState] = useState<HistoryState>({ status: 'idle' });
  const [detailState, setDetailState] = useState<DetailState>({ status: 'idle' });
  const [selectedResultId, setSelectedResultId] = useState<number | null>(null);
  const requestVersionRef = useRef(0);

  const loadDetail = useCallback(async (resultId: number) => {
    const requestVersion = ++requestVersionRef.current;
    setSelectedResultId(resultId);
    setDetailState({ status: 'loading' });
    try {
      const detail = await getStage7ScreeningResult(resultId);
      if (requestVersion !== requestVersionRef.current) return;
      setDetailState({ status: 'ready', detail });
    } catch (error) {
      if (requestVersion !== requestVersionRef.current) return;
      setDetailState({
        status: 'error',
        message: detailErrorMessage(error, '无法读取这一次评分的完整详情'),
      });
    }
  }, []);

  useEffect(() => {
    requestVersionRef.current += 1;
    if (!item) {
      setHistoryState({ status: 'idle' });
      setDetailState({ status: 'idle' });
      setSelectedResultId(null);
      return;
    }

    let cancelled = false;
    setHistoryState({ status: 'loading' });
    setDetailState({ status: 'idle' });
    setSelectedResultId(null);
    void listStage7ApplicationScreenings(item.application.id)
      .then(history => {
        if (cancelled) return;
        setHistoryState({ status: 'ready', items: history });
        const currentId = item.application.currentScreeningResultId;
        const initial = history.find(result => result.id === currentId) || history[0];
        if (initial) void loadDetail(initial.id);
      })
      .catch(error => {
        if (cancelled) return;
        setHistoryState({
          status: 'error',
          message: detailErrorMessage(error, '无法读取这份申请的评分历史'),
        });
      });
    return () => {
      cancelled = true;
    };
  }, [item, loadDetail]);

  const detail = detailState.status === 'ready' ? detailState.detail : null;
  const dimensionViews = useMemo(
    () => (detail ? getStage7DimensionViews(detail) : []),
    [detail],
  );
  const hardRequirementViews = useMemo(
    () => (detail ? getStage7HardRequirementViews(detail) : []),
    [detail],
  );
  const semanticViews = useMemo(
    () => (detail ? getStage7SemanticCriterionViews(detail) : []),
    [detail],
  );

  return (
    <Drawer
      className="recruitment-screening-detail-drawer"
      destroyOnClose
      onClose={onClose}
      open={Boolean(item)}
      title={item ? `${item.candidateName} · ${item.jobTitle}` : '评分详情'}
      width="min(980px, 100vw)"
    >
      {item && (
        <div className="recruitment-screening-detail-layout">
          <aside aria-label="评分运行历史" className="recruitment-screening-history-rail">
            <div className="recruitment-screening-history-heading">
              <span><HistoryOutlined /> 评分历史</span>
              <strong>Application #{item.application.id}</strong>
              <small>每次运行都是一份不可覆盖的审计记录</small>
            </div>

            {historyState.status === 'loading' && <Skeleton active paragraph={{ rows: 5 }} />}
            {historyState.status === 'error' && (
              <Alert message="评分历史读取失败" description={historyState.message} showIcon type="error" />
            )}
            {historyState.status === 'ready' && historyState.items.length === 0 && (
              <Empty description="还没有评分运行记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
            {historyState.status === 'ready' && historyState.items.length > 0 && (
              <div className="recruitment-screening-history-list" role="list">
                {historyState.items.map(history => {
                  const statusMeta = EXECUTION_META[history.executionStatus];
                  const current = item.application.currentScreeningResultId === history.id;
                  return (
                    <button
                      aria-pressed={selectedResultId === history.id}
                      className={selectedResultId === history.id ? 'is-selected' : ''}
                      key={history.id}
                      onClick={() => void loadDetail(history.id)}
                      role="listitem"
                      type="button"
                    >
                      <span className="recruitment-screening-history-marker" />
                      <span className="recruitment-screening-history-copy">
                        <strong>第 {history.attemptNumber} 次评分</strong>
                        <small>{formatDateTime(history.startedAt || history.createdAt)}</small>
                        <em>{history.overallScore === null ? '未形成总分' : `${history.overallScore} 分`}</em>
                      </span>
                      <span className="recruitment-screening-history-tags">
                        <Tag bordered={false} className={`recruitment-status-tag is-${statusMeta.tone}`}>{statusMeta.label}</Tag>
                        {current && <Tag bordered={false} color="blue">当前</Tag>}
                        {history.isOutdated && <Tag bordered={false} color="orange">已过期</Tag>}
                        {history.forceRerun && <Tag bordered={false}>强制重跑</Tag>}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </aside>

          <section aria-live="polite" className="recruitment-screening-detail-content">
            {detailState.status === 'idle' && (
              <Empty description="从左侧选择一次评分查看证据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
            {detailState.status === 'loading' && (
              <div aria-busy="true" aria-label="评分详情加载中"><Skeleton active paragraph={{ rows: 12 }} /></div>
            )}
            {detailState.status === 'error' && (
              <Alert
                action={selectedResultId && <Button onClick={() => void loadDetail(selectedResultId)}>重新读取</Button>}
                description={detailState.message}
                message="评分详情读取失败"
                showIcon
                type="error"
              />
            )}
            {detail && (
              <>
                <header className="recruitment-screening-detail-hero">
                  <div className="recruitment-screening-detail-score">
                    <span>第 {detail.attemptNumber} 次评分</span>
                    <strong>{detail.overallScore ?? '—'}<small>{detail.overallScore === null ? '' : ' 分'}</small></strong>
                    <em>{detail.recommendation ? RECOMMENDATION_LABELS[detail.recommendation] || detail.recommendation : '未形成推荐方向'}</em>
                  </div>
                  <div className="recruitment-screening-detail-summary">
                    <div>
                      <Tag bordered={false} className={`recruitment-status-tag is-${EXECUTION_META[detail.executionStatus].tone}`}>
                        {EXECUTION_META[detail.executionStatus].label}
                      </Tag>
                      {detail.isOutdated && <Tag bordered={false} color="orange">结果已过期</Tag>}
                      {detail.forceRerun && <Tag bordered={false}>强制重跑</Tag>}
                    </div>
                    <p>{detail.reason || detail.errorMessage || '本次运行没有记录补充说明。'}</p>
                    <div className="recruitment-screening-coverage">
                      <span>证据覆盖率</span>
                      <Progress
                        percent={percent(detail.evidenceCoverageRate) ?? 0}
                        showInfo={detail.evidenceCoverageRate !== null}
                        size="small"
                        status={detail.evidenceCoverageRate !== null && detail.evidenceCoverageRate < 0.6 ? 'exception' : 'normal'}
                      />
                    </div>
                  </div>
                </header>

                {(detail.executionStatus === 'failed' || detail.executionStatus === 'blocked') && (
                  <Alert
                    className="recruitment-screening-detail-alert"
                    description={detail.errorMessage || '本次运行没有形成完整评分，请根据状态提示处理。'}
                    message={detail.executionStatus === 'blocked' ? '资料不足，未生成虚假 0 分' : '本次评分失败，历史成功结果不会被覆盖'}
                    showIcon
                    type={detail.executionStatus === 'blocked' ? 'warning' : 'error'}
                  />
                )}

                {dimensionViews.length > 0 && (
                  <section className="recruitment-screening-detail-section">
                    <div className="recruitment-screening-detail-section-heading">
                      <span>01</span><div><h4>五维评分</h4><p>由 Python 按已发布 Rubric 统一加权</p></div>
                    </div>
                    <div className="recruitment-screening-dimension-grid">
                      {dimensionViews.map(dimension => (
                        <article key={dimension.key}>
                          <span>{STAGE7_DIMENSION_LABELS[dimension.key] || dimension.key}</span>
                          <strong>{dimension.scorePercentage === null ? '—' : Math.round(dimension.scorePercentage)}<small>{dimension.scorePercentage === null ? '' : '%'}</small></strong>
                          <em>证据 {percent(dimension.evidenceCoverageRate) ?? '—'}%{dimension.configuredWeight === null ? '' : ` · 外框权重 ${dimension.configuredWeight}`}</em>
                        </article>
                      ))}
                    </div>
                  </section>
                )}

                <section className="recruitment-screening-detail-section">
                  <div className="recruitment-screening-detail-section-heading">
                    <span>02</span><div><h4>硬性条件</h4><p>结构化字段由确定性规则比较，不交给模型猜测</p></div>
                  </div>
                  {hardRequirementViews.length ? (
                    <div className="recruitment-screening-hard-list">
                      {hardRequirementViews.map((check, index) => {
                        const meta = HARD_STATUS_META[check.status];
                        return (
                          <article key={`${check.criterion}-${index}`}>
                            <div className={`is-${meta.tone}`}>{meta.icon}</div>
                            <div>
                              <strong>{STAGE7_CRITERION_LABELS[check.criterion] || check.criterion}</strong>
                              <span>{check.requirement}</span>
                              <p>{check.evidence.length ? check.evidence.join('；') : '候选人材料中没有足够的可比较信息。'}</p>
                            </div>
                            <Tag bordered={false} className={`recruitment-status-tag is-${meta.tone}`}>{meta.label}</Tag>
                          </article>
                        );
                      })}
                    </div>
                  ) : <Empty description="本次运行没有硬性条件记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
                </section>

                <section className="recruitment-screening-detail-section">
                  <div className="recruitment-screening-detail-section-heading">
                    <span>03</span><div><h4>语义评分与逐项证据</h4><p>每个分数都回到已发布 Rubric 和可定位的候选人材料</p></div>
                  </div>
                  {semanticViews.length ? (
                    <div className="recruitment-screening-evidence-ledger">
                      {semanticViews.map((criterion, index) => (
                        <article key={criterion.key}>
                          <header>
                            <div>
                              <span>{String(index + 1).padStart(2, '0')} · {STAGE7_DIMENSION_LABELS[criterion.dimension] || '岗位专用语义项'}</span>
                              <strong>{criterion.name}</strong>
                              {criterion.description && <p>{criterion.description}</p>}
                            </div>
                            <div className="recruitment-screening-criterion-score">
                              <strong>{criterion.score === 'unknown' ? '?' : criterion.score ?? '—'}<small>{typeof criterion.score === 'number' ? '/10' : ''}</small></strong>
                              <span>{criterion.score === 'unknown' ? '证据不足' : criterion.confidence ? CONFIDENCE_LABELS[criterion.confidence] || criterion.confidence : '置信度未记录'}</span>
                            </div>
                          </header>
                          <div className="recruitment-screening-criterion-reason">
                            <InfoCircleOutlined />
                            <p>{criterion.reason || '本次运行没有记录该项的评价原因。'}</p>
                          </div>
                          {criterion.evidence.length ? (
                            <div className="recruitment-screening-evidence-quotes">
                              {criterion.evidence.map((evidence, evidenceIndex) => (
                                <blockquote key={`${criterion.key}-${evidenceIndex}`}>
                                  <span>{STAGE7_EVIDENCE_SOURCE_LABELS[evidence.source] || evidence.source}{evidence.locator ? ` · ${evidence.locator}` : ''}</span>
                                  <p>“{evidence.quote}”</p>
                                </blockquote>
                              ))}
                            </div>
                          ) : (
                            <div className="recruitment-screening-no-evidence"><WarningOutlined /> 没有形成可定位证据，不能把 unknown 当作不满足。</div>
                          )}
                          {(criterion.strengths.length > 0 || criterion.gaps.length > 0) && (
                            <div className="recruitment-screening-criterion-signals">
                              <div><span>优势</span><p>{criterion.strengths.length ? criterion.strengths.join('；') : '未记录'}</p></div>
                              <div><span>缺口</span><p>{criterion.gaps.length ? criterion.gaps.join('；') : '未记录'}</p></div>
                            </div>
                          )}
                        </article>
                      ))}
                    </div>
                  ) : <Empty description="本次运行没有生成完整语义评分证据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
                </section>

                {(detail.strengths.length > 0 || detail.risks.length > 0 || detail.pendingQuestions.length > 0) && (
                  <section className="recruitment-screening-detail-section">
                    <div className="recruitment-screening-detail-section-heading">
                      <span>04</span><div><h4>汇总结论</h4><p>把优势、风险和仍需人工确认的资料分开呈现</p></div>
                    </div>
                    <div className="recruitment-screening-signal-grid">
                      <article><span>优势</span><p>{detail.strengths.length ? detail.strengths.join('；') : '未记录'}</p></article>
                      <article><span>风险</span><p>{detail.risks.length ? detail.risks.join('；') : '未记录'}</p></article>
                      <article><span>待确认</span><p>{detail.pendingQuestions.length ? detail.pendingQuestions.join('；') : '没有额外待确认问题'}</p></article>
                    </div>
                  </section>
                )}

                <section className="recruitment-screening-detail-section">
                  <div className="recruitment-screening-detail-section-heading">
                    <span>05</span><div><h4>版本与运行信息</h4><p>用于解释结果来源，不把模型输出当作不可追溯的黑盒</p></div>
                  </div>
                  <dl className="recruitment-screening-version-grid">
                    <div><dt>Rubric 版本</dt><dd>{getStage7RubricVersion(detail) ?? '未记录'}</dd></div>
                    <div><dt>规则版本</dt><dd>{detail.rulesVersion || '未记录'}</dd></div>
                    <div><dt>Prompt 版本</dt><dd>{detail.promptVersion || '未记录'}</dd></div>
                    <div><dt>模型</dt><dd>{[detail.modelProvider, detail.modelName].filter(Boolean).join(' / ') || '未调用或未记录'}</dd></div>
                    <div><dt>运行耗时</dt><dd>{formatDuration(detail.durationMs)}</dd></div>
                    <div><dt>Token</dt><dd>{detail.totalTokens ?? '未记录'}</dd></div>
                    <div><dt>触发原因</dt><dd>{detail.triggerReason || '未记录'}</dd></div>
                    <div><dt>操作人</dt><dd>{detail.actorLabel || '系统'}</dd></div>
                    <div><dt>开始时间</dt><dd>{formatDateTime(detail.startedAt || detail.createdAt)}</dd></div>
                    <div><dt>结束时间</dt><dd>{formatDateTime(detail.finishedAt)}</dd></div>
                  </dl>
                </section>
              </>
            )}
          </section>
        </div>
      )}
    </Drawer>
  );
};

export default RecruitmentScreeningDetailDrawer;
