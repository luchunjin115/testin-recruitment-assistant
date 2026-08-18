import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FileSearchOutlined,
  HistoryOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Alert, Button, Checkbox, Drawer, Empty, message, Select, Skeleton, Tag, Tooltip } from 'antd';
import { Link } from 'react-router-dom';
import {
  getStage7ApplicationApiError,
  runStage7ApplicationScreening,
  runStage7ScreeningBatch,
} from './services/applications';
import {
  getStage7ScreeningCenter,
  type Stage7ScreeningCenterItem,
  type Stage7ScreeningCenterSnapshot,
} from './services/screening';
import {
  beginStage7SingleScreening,
  finishStage7SingleScreening,
  getStage7SingleScreeningAction,
  getStage7SingleScreeningErrorMessage,
} from './screeningAction';
import {
  beginStage7BatchRun,
  finishStage7BatchRun,
  getStage7BatchSelectionState,
  getStage7FailedBatchApplicationIds,
} from './screeningBatchAction';
import RecruitmentScreeningDetailDrawer from './RecruitmentScreeningDetailDrawer';
import type {
  Stage7ApplicationAIStatus,
  Stage7ApplicationLifecycleStatus,
  Stage7HRDecision,
  Stage7RecruitmentStage,
  Stage7ScreeningBatchItemStatus,
  Stage7ScreeningBatchOutcome,
} from './types/applicationScreening';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: Stage7ScreeningCenterSnapshot };

type StatusMeta = { label: string; tone: 'info' | 'success' | 'warning' | 'danger' | 'neutral' };

type BatchResultView = {
  outcome: Stage7ScreeningBatchOutcome;
  candidateLabels: Record<number, string>;
};

const AI_STATUS_META: Record<Stage7ApplicationAIStatus, StatusMeta> = {
  not_started: { label: '等待初筛', tone: 'neutral' },
  screening: { label: '初筛进行中', tone: 'info' },
  completed: { label: '初筛已完成', tone: 'success' },
  failed: { label: '初筛失败', tone: 'danger' },
  blocked: { label: '等待补充资料', tone: 'warning' },
};

const HR_DECISION_META: Record<Stage7HRDecision, StatusMeta> = {
  pending: { label: 'HR 待决策', tone: 'neutral' },
  passed: { label: 'HR 已通过', tone: 'success' },
  backup: { label: '已进入备选', tone: 'warning' },
  rejected: { label: 'HR 已淘汰', tone: 'danger' },
};

const LIFECYCLE_META: Record<Stage7ApplicationLifecycleStatus, StatusMeta> = {
  active: { label: '招聘中', tone: 'success' },
  ended: { label: '流程已结束', tone: 'neutral' },
  voided: { label: '申请已作废', tone: 'danger' },
};

const BATCH_STATUS_META: Record<Stage7ScreeningBatchItemStatus, StatusMeta> = {
  completed: { label: '评分完成', tone: 'success' },
  failed: { label: '评分失败', tone: 'danger' },
  blocked: { label: '资料不足', tone: 'warning' },
  reused: { label: '复用结果', tone: 'info' },
  skipped: { label: '安全跳过', tone: 'neutral' },
};

const PIPELINE_STAGES: Array<{ value: Stage7RecruitmentStage; label: string; note: string }> = [
  { value: 'applied', label: '已投递', note: '等待进入复核' },
  { value: 'hr_review', label: 'HR 复核', note: '查看 AI 结论' },
  { value: 'screening_passed', label: '已通过', note: '进入后续流程' },
  { value: 'backup', label: '备选', note: '保留候选人' },
  { value: 'rejected', label: '已淘汰', note: '流程已结束' },
];

const aiStatusOptions = [
  { value: 'all', label: '全部 AI 状态' },
  ...Object.entries(AI_STATUS_META).map(([value, meta]) => ({ value, label: meta.label })),
];
const hrDecisionOptions = [
  { value: 'all', label: '全部 HR 决策' },
  ...Object.entries(HR_DECISION_META).map(([value, meta]) => ({ value, label: meta.label })),
];
const lifecycleOptions = [
  { value: 'all', label: '全部生命周期' },
  ...Object.entries(LIFECYCLE_META).map(([value, meta]) => ({ value, label: meta.label })),
];

const SOURCE_LABELS = {
  hr_direct: 'HR 直接录入',
  hr_screening: 'HR 初筛录入',
  public_apply: '公开投递',
} as const;

const formatDateTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
};

const getStatusMessage = (item: Stage7ScreeningCenterItem) => {
  const { application, currentResult } = item;
  if (currentResult?.isOutdated) return '岗位或简历已经变化，当前结论需要重新确认。';
  if (application.aiStatus === 'blocked') return currentResult?.errorMessage || '资料不足，补齐后才能继续评分。';
  if (application.aiStatus === 'failed') return currentResult?.errorMessage || '上一次评分没有完成，可稍后重试。';
  if (application.aiStatus === 'screening') return '评分任务正在运行，请稍后刷新。';
  if (application.aiStatus === 'not_started') return '尚未生成 AI 初筛结论。';
  return currentResult?.recommendation || 'AI 初筛已完成，等待 HR 查看。';
};

const RecruitmentScreeningCenter: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [jobFilter, setJobFilter] = useState<number | 'all'>('all');
  const [stageFilter, setStageFilter] = useState<Stage7RecruitmentStage | 'all'>('all');
  const [aiFilter, setAiFilter] = useState<Stage7ApplicationAIStatus | 'all'>('all');
  const [hrFilter, setHrFilter] = useState<Stage7HRDecision | 'all'>('all');
  const [lifecycleFilter, setLifecycleFilter] = useState<Stage7ApplicationLifecycleStatus | 'all'>('all');
  const pendingScreeningIdsRef = useRef(new Set<number>());
  const [pendingScreeningIds, setPendingScreeningIds] = useState<Set<number>>(new Set());
  const [screeningErrors, setScreeningErrors] = useState<Record<number, string>>({});
  const batchRunGuardRef = useRef({ pending: false });
  const [batchPending, setBatchPending] = useState(false);
  const [selectedBatchIds, setSelectedBatchIds] = useState<Set<number>>(new Set());
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchResult, setBatchResult] = useState<BatchResultView | null>(null);
  const [detailItem, setDetailItem] = useState<Stage7ScreeningCenterItem | null>(null);

  const apiFilters = useMemo(() => ({
    jobId: jobFilter === 'all' ? undefined : jobFilter,
    aiStatus: aiFilter === 'all' ? undefined : aiFilter,
    hrDecision: hrFilter === 'all' ? undefined : hrFilter,
    lifecycleStatus: lifecycleFilter === 'all' ? undefined : lifecycleFilter,
  }), [aiFilter, hrFilter, jobFilter, lifecycleFilter]);

  const loadScreeningCenter = useCallback(async (showLoading = true) => {
    if (showLoading) setLoadState({ status: 'loading' });
    try {
      const data = await getStage7ScreeningCenter(apiFilters);
      setLoadState({ status: 'ready', data });
      setJobFilter(current => (
        current === 'all' || data.jobs.some(job => job.id === current) ? current : 'all'
      ));
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法读取 Application 工作队列',
      });
    }
  }, [apiFilters]);

  useEffect(() => {
    void loadScreeningCenter();
  }, [loadScreeningCenter]);

  useEffect(() => {
    setSelectedBatchIds(new Set());
    setBatchError(null);
  }, [aiFilter, hrFilter, jobFilter, lifecycleFilter, stageFilter]);

  const clearFilters = () => {
    setJobFilter('all');
    setStageFilter('all');
    setAiFilter('all');
    setHrFilter('all');
    setLifecycleFilter('all');
  };

  const runSingleScreening = async (item: Stage7ScreeningCenterItem) => {
    const applicationId = item.application.id;
    if (!beginStage7SingleScreening(pendingScreeningIdsRef.current, applicationId)) return;
    setPendingScreeningIds(new Set(pendingScreeningIdsRef.current));
    setScreeningErrors(current => {
      const next = { ...current };
      delete next[applicationId];
      return next;
    });

    try {
      const outcome = await runStage7ApplicationScreening(applicationId);
      if (outcome.result.executionStatus === 'completed') {
        message.success(outcome.reused ? '已读取现有初筛结果' : 'AI 初筛已完成');
      } else {
        const resultMessage = outcome.result.errorMessage
          || (outcome.result.executionStatus === 'blocked'
            ? '初筛未生成结论，请先补充候选人资料。'
            : '初筛没有完成，可稍后重新尝试。');
        setScreeningErrors(current => ({ ...current, [applicationId]: resultMessage }));
        message.warning(resultMessage);
      }
      await loadScreeningCenter(false);
    } catch (error) {
      const apiError = getStage7ApplicationApiError(error);
      const errorMessage = getStage7SingleScreeningErrorMessage(apiError.code, apiError.message);
      setScreeningErrors(current => ({ ...current, [applicationId]: errorMessage }));
      message.error('AI 初筛没有启动，请查看该申请的提示。');
      if (apiError.code === 'SCREENING_ALREADY_RUNNING') await loadScreeningCenter(false);
    } finally {
      finishStage7SingleScreening(pendingScreeningIdsRef.current, applicationId);
      setPendingScreeningIds(new Set(pendingScreeningIdsRef.current));
    }
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="Application 工作队列加载中" className="recruitment-main">
        <section className="recruitment-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="recruitment-application-funnel is-loading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="recruitment-stat-grid">
          {[0, 1, 2, 3].map(item => <article className="recruitment-stat-card" key={item}><Skeleton active paragraph={false} /></article>)}
        </section>
        <section className="recruitment-state-panel"><Skeleton active paragraph={{ rows: 8 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="recruitment-main">
        <section className="recruitment-page-heading">
          <div>
            <span className="recruitment-section-kicker">阶段 7 · Application 工作队列</span>
            <h2>AI 初筛中心</h2>
            <p>从真实 Application 状态开始组织初筛工作。</p>
          </div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadScreeningCenter()}>重新加载</Button>}
          className="recruitment-dashboard-alert recruitment-section-gap"
          description={`请确认新版 API 已启动，且 applications、jobs、candidates 和 screening-results 接口可访问。技术信息：${loadState.message}`}
          message="Application 工作队列加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const visibleItems = stageFilter === 'all'
    ? data.items
    : data.items.filter(item => item.application.recruitmentStage === stageFilter);
  const needsAttention = visibleItems.filter(item => (
    item.application.aiStatus === 'blocked'
    || item.application.aiStatus === 'failed'
    || item.currentResult?.isOutdated
  )).length;
  const stats = [
    {
      label: '当前申请', value: visibleItems.length, note: '符合当前筛选条件',
      icon: <FileSearchOutlined />, tone: 'blue',
    },
    {
      label: '等待初筛', value: visibleItems.filter(item => item.application.aiStatus === 'not_started').length,
      note: '尚未生成评分结果', icon: <ClockCircleOutlined />, tone: 'orange',
    },
    {
      label: '需要处理', value: needsAttention, note: '失败、资料不足或结果过期',
      icon: <ExclamationCircleOutlined />, tone: 'red',
    },
    {
      label: 'HR 待决策', value: visibleItems.filter(item => item.application.hrDecision === 'pending').length,
      note: '等待人工确认方向', icon: <SafetyCertificateOutlined />, tone: 'green',
    },
  ];
  const hasActiveFilters = jobFilter !== 'all'
    || stageFilter !== 'all'
    || aiFilter !== 'all'
    || hrFilter !== 'all'
    || lifecycleFilter !== 'all';
  const selectedBatchItems = data.items.filter(item => selectedBatchIds.has(item.application.id));
  const selectedBatchJobId = selectedBatchItems[0]?.application.jobId ?? null;
  const selectedBatchJobTitle = selectedBatchItems[0]?.jobTitle ?? null;

  const toggleBatchSelection = (item: Stage7ScreeningCenterItem) => {
    const applicationId = item.application.id;
    const selected = selectedBatchIds.has(applicationId);
    const selectionState = getStage7BatchSelectionState(item, {
      selected,
      selectedCount: selectedBatchIds.size,
      selectedJobId: selectedBatchJobId,
      batchPending,
      singlePending: pendingScreeningIds.has(applicationId),
    });
    if (!selectionState.allowed) return;
    setSelectedBatchIds(current => {
      const next = new Set(current);
      if (next.has(applicationId)) next.delete(applicationId);
      else next.add(applicationId);
      return next;
    });
    setBatchError(null);
  };

  const executeBatchScreening = async (
    applicationIds: number[],
    jobId: number,
    candidateLabels: Record<number, string>,
    retryFailedOnly = false,
  ) => {
    if (!beginStage7BatchRun(batchRunGuardRef.current)) return;
    setBatchPending(true);
    setBatchError(null);
    try {
      const outcome = await runStage7ScreeningBatch(jobId, {
        application_ids: applicationIds,
        retry_failed_only: retryFailedOnly,
      });
      setBatchResult({ outcome, candidateLabels });
      setSelectedBatchIds(new Set());
      const { completed, failed, blocked, reused, skipped } = outcome.summary;
      message.info(`批量初筛完成：完成 ${completed}，失败 ${failed}，资料不足 ${blocked}，复用 ${reused}，跳过 ${skipped}`);
      await loadScreeningCenter(false);
    } catch (error) {
      const apiError = getStage7ApplicationApiError(error);
      setBatchError(apiError.message);
      message.error('批量初筛没有启动，请查看批次提示。');
    } finally {
      finishStage7BatchRun(batchRunGuardRef.current);
      setBatchPending(false);
    }
  };

  const runSelectedBatch = () => {
    if (selectedBatchJobId === null || selectedBatchIds.size < 1 || selectedBatchIds.size > 5) return;
    const candidateLabels = Object.fromEntries(
      selectedBatchItems.map(item => [item.application.id, item.candidateName]),
    );
    void executeBatchScreening(
      Array.from(selectedBatchIds),
      selectedBatchJobId,
      candidateLabels,
    );
  };

  const retryFailedBatch = () => {
    if (!batchResult) return;
    const failedIds = getStage7FailedBatchApplicationIds(batchResult.outcome);
    if (!failedIds.length) return;
    void executeBatchScreening(
      failedIds,
      batchResult.outcome.jobId,
      batchResult.candidateLabels,
      true,
    );
  };

  return (
    <main className="recruitment-main">
      <section className="recruitment-page-heading recruitment-screening-heading">
        <div>
          <span className="recruitment-section-kicker">阶段 7 · Application 工作队列 · 实时读取 /api/v2</span>
          <h2>AI 初筛中心</h2>
          <p>查看每份申请停在哪里，并为符合条件的单个申请启动 AI 初筛；AI 结论不会自动改变 HR 决策。</p>
        </div>
        <Tooltip title={selectedBatchIds.size ? `为已选择的 ${selectedBatchIds.size} 人开始评分` : '先在申请队列中勾选同岗位的 1—5 人'}>
          <Button
            disabled={!selectedBatchIds.size || batchPending || pendingScreeningIds.size > 0}
            icon={<RobotOutlined />}
            loading={batchPending}
            onClick={runSelectedBatch}
            type="primary"
          >
            开始批量初筛{selectedBatchIds.size ? ` · ${selectedBatchIds.size}` : ''}
          </Button>
        </Tooltip>
      </section>

      <section aria-label="招聘阶段筛选" className="recruitment-application-funnel">
        <div className="recruitment-application-funnel-intro">
          <span>招聘阶段</span>
          <strong>申请流转轨道</strong>
          <small>点击阶段筛选列表</small>
        </div>
        <div className="recruitment-application-funnel-track">
          {PIPELINE_STAGES.map(stage => {
            const count = data.items.filter(item => item.application.recruitmentStage === stage.value).length;
            const selected = stageFilter === stage.value;
            return (
              <button
                aria-pressed={selected}
                className={selected ? 'is-selected' : ''}
                key={stage.value}
                onClick={() => setStageFilter(selected ? 'all' : stage.value)}
                type="button"
              >
                <span>{stage.label}</span>
                <strong>{count}</strong>
                <small>{stage.note}</small>
              </button>
            );
          })}
        </div>
      </section>

      <section aria-label="Application 队列统计" className="recruitment-stat-grid">
        {stats.map(stat => (
          <article className="recruitment-stat-card" key={stat.label}>
            <div className={`recruitment-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="recruitment-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      <section className="recruitment-panel recruitment-screening-panel">
        <div className="recruitment-screening-toolbar">
          <div>
            <h3>申请队列</h3>
            <p>当前展示 {visibleItems.length} 份 Application；状态以服务端记录为准</p>
          </div>
          <div className="recruitment-screening-filter-controls">
            <Select
              aria-label="按岗位筛选 Application"
              disabled={batchPending}
              onChange={setJobFilter}
              options={[
                { value: 'all', label: '全部岗位' },
                ...data.jobs.map(job => ({
                  value: job.id,
                  label: `${job.title}${job.status === 'closed' ? '（已关闭）' : ''}`,
                })),
              ]}
              optionFilterProp="label"
              showSearch
              value={jobFilter}
            />
            <Select aria-label="按 AI 状态筛选" disabled={batchPending} onChange={setAiFilter} options={aiStatusOptions} value={aiFilter} />
            <Select aria-label="按 HR 决策筛选" disabled={batchPending} onChange={setHrFilter} options={hrDecisionOptions} value={hrFilter} />
            <Select aria-label="按生命周期筛选" disabled={batchPending} onChange={setLifecycleFilter} options={lifecycleOptions} value={lifecycleFilter} />
            {hasActiveFilters && <Button disabled={batchPending} onClick={clearFilters}>清除筛选</Button>}
            <Button aria-label="刷新 Application 工作队列" disabled={batchPending} icon={<ReloadOutlined />} onClick={() => void loadScreeningCenter()} />
          </div>
        </div>

        {(selectedBatchIds.size > 0 || batchError) && (
          <div aria-live="polite" className="recruitment-screening-batch-bar">
            <div>
              <span>批量初筛</span>
              <strong>{selectedBatchIds.size ? `已选择 ${selectedBatchIds.size}/5 人` : '批次未启动'}</strong>
              <small>{selectedBatchJobTitle ? `${selectedBatchJobTitle} · 一个批次最多选择 5 人且只能选择同一岗位` : '请重新选择需要评分的 Application'}</small>
              {batchError && <em role="alert">{batchError}</em>}
            </div>
            <div>
              <Button disabled={batchPending} onClick={() => setSelectedBatchIds(new Set())}>取消选择</Button>
              <Button
                disabled={!selectedBatchIds.size || batchPending || pendingScreeningIds.size > 0}
                loading={batchPending}
                onClick={runSelectedBatch}
                type="primary"
              >
                开始批量初筛
              </Button>
            </div>
          </div>
        )}

        {data.items.length === 0 ? (
          <Empty
            className="recruitment-panel-empty recruitment-screening-empty"
            description={(
              <div className="recruitment-empty-copy">
                <strong>{hasActiveFilters ? '当前筛选条件下没有 Application' : '新版数据库中还没有 Application'}</strong>
                <span>{hasActiveFilters ? '清除筛选后查看其他申请。' : 'Application 会在 HR 录入或公开投递后出现在这里。'}</span>
              </div>
            )}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            {hasActiveFilters && <Button onClick={clearFilters}>清除筛选</Button>}
          </Empty>
        ) : visibleItems.length === 0 ? (
          <Empty
            className="recruitment-panel-empty recruitment-screening-empty"
            description={<div className="recruitment-empty-copy"><strong>该招聘阶段没有申请</strong><span>点击其他阶段，或清除筛选查看全部 Application。</span></div>}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button onClick={clearFilters}>清除筛选</Button>
          </Empty>
        ) : (
          <div aria-label="Application 工作队列" className="recruitment-application-list" role="list">
            {visibleItems.map(item => {
              const { application, currentResult } = item;
              const aiMeta = AI_STATUS_META[application.aiStatus];
              const hrMeta = HR_DECISION_META[application.hrDecision];
              const lifecycleMeta = LIFECYCLE_META[application.lifecycleStatus];
              const attention = application.aiStatus === 'failed'
                || application.aiStatus === 'blocked'
                || Boolean(currentResult?.isOutdated);
              const screeningPending = pendingScreeningIds.has(application.id);
              const batchSelected = selectedBatchIds.has(application.id);
              const batchSelection = getStage7BatchSelectionState(item, {
                selected: batchSelected,
                selectedCount: selectedBatchIds.size,
                selectedJobId: selectedBatchJobId,
                batchPending,
                singlePending: screeningPending,
              });
              const selectedBatchPending = batchPending && batchSelected;
              const action = getStage7SingleScreeningAction(item, screeningPending || selectedBatchPending);
              return (
                <article
                  aria-busy={screeningPending || selectedBatchPending}
                  className={`recruitment-application-row${attention ? ' needs-attention' : ''}${screeningPending || selectedBatchPending ? ' is-running' : ''}${batchSelected ? ' is-selected' : ''}`}
                  key={application.id}
                  role="listitem"
                >
                  <div className="recruitment-application-id">
                    <Tooltip title={batchSelection.reason}>
                      <span className="recruitment-application-checkbox">
                        <Checkbox
                          aria-label={`选择 Application #${application.id} 加入批量初筛`}
                          checked={batchSelected}
                          disabled={!batchSelection.allowed}
                          onChange={() => toggleBatchSelection(item)}
                        />
                      </span>
                    </Tooltip>
                    <span>APP</span><strong>#{application.id}</strong>
                  </div>
                  <div className="recruitment-application-person">
                    <Link to={`/app/candidates/${application.candidateId}`}>{item.candidateName}</Link>
                    <span>{item.candidateTitle || item.candidateSource || `候选人 #${application.candidateId}`}</span>
                    <small>{SOURCE_LABELS[application.source]} · {formatDateTime(application.appliedAt)} 投递</small>
                  </div>
                  <div className="recruitment-application-job">
                    <strong>{item.jobTitle}</strong>
                    <span>{item.jobDepartment || `岗位 #${application.jobId}`}</span>
                    {item.jobStatus === 'closed' && <Tag bordered={false} className="recruitment-status-tag is-neutral">岗位已关闭</Tag>}
                  </div>
                  <div className="recruitment-application-ai-state">
                    <div>
                      <Tag bordered={false} className={`recruitment-status-tag is-${aiMeta.tone}`}>{aiMeta.label}</Tag>
                      {currentResult?.isOutdated && <Tag bordered={false} className="recruitment-status-tag is-danger">结果已过期</Tag>}
                    </div>
                    <p>{getStatusMessage(item)}</p>
                  </div>
                  <div className="recruitment-application-result">
                    <span>当前结论</span>
                    <strong>{currentResult?.overallScore ?? '—'}<small>{currentResult?.overallScore === null || !currentResult ? '' : ' 分'}</small></strong>
                    <em>{currentResult ? `第 ${currentResult.attemptNumber} 次 · ${currentResult.recommendation || '暂无推荐方向'}` : '还没有评分结果'}</em>
                  </div>
                  <div className="recruitment-application-decision">
                    <Tag bordered={false} className={`recruitment-status-tag is-${hrMeta.tone}`}>{hrMeta.label}</Tag>
                    <Tag bordered={false} className={`recruitment-status-tag is-${lifecycleMeta.tone}`}>{lifecycleMeta.label}</Tag>
                    {!application.currentResumeId && <span>未绑定简历</span>}
                  </div>
                  <div className="recruitment-application-action">
                    <Button
                      icon={<HistoryOutlined />}
                      onClick={() => setDetailItem(item)}
                      size="small"
                    >
                      评分记录
                    </Button>
                    <Button
                      disabled={!action.allowed}
                      loading={screeningPending}
                      onClick={() => void runSingleScreening(item)}
                      size="small"
                      type={action.allowed ? 'primary' : 'default'}
                    >
                      {action.label}
                    </Button>
                    <span>{action.reason}</span>
                    {screeningErrors[application.id] && (
                      <em role="alert">{screeningErrors[application.id]}</em>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <Drawer
        className="recruitment-screening-batch-drawer"
        destroyOnClose
        onClose={() => setBatchResult(null)}
        open={Boolean(batchResult)}
        title="批量评分逐项结果"
        width="min(620px, 100vw)"
      >
        {batchResult && (
          <>
            <Alert
              description="批量评分不会自动通过或淘汰候选人。失败、资料不足和跳过项需要 HR 分别处理。"
              message={`岗位 #${batchResult.outcome.jobId} · 已选择 ${batchResult.outcome.summary.selected} 人，实际执行 ${batchResult.outcome.summary.executed} 人`}
              showIcon
              type="info"
            />
            <div aria-label="批量评分汇总" className="recruitment-screening-batch-summary">
              {([
                ['完成', batchResult.outcome.summary.completed],
                ['失败', batchResult.outcome.summary.failed],
                ['资料不足', batchResult.outcome.summary.blocked],
                ['复用', batchResult.outcome.summary.reused],
                ['跳过', batchResult.outcome.summary.skipped],
              ] as const).map(([label, value]) => <span key={label}><strong>{value}</strong><small>{label}</small></span>)}
            </div>
            <div aria-label="批量评分逐项结果" className="recruitment-screening-batch-results" role="list">
              {batchResult.outcome.items.map(result => {
                const statusMeta = BATCH_STATUS_META[result.status];
                return (
                  <article key={result.applicationId} role="listitem">
                    <div>
                      <strong>{batchResult.candidateLabels[result.applicationId] || `Application #${result.applicationId}`}</strong>
                      <span>Application #{result.applicationId}{result.attemptNumber ? ` · 第 ${result.attemptNumber} 次` : ''}</span>
                    </div>
                    <Tag bordered={false} className={`recruitment-status-tag is-${statusMeta.tone}`}>{statusMeta.label}</Tag>
                    <p>{result.errorMessage || (result.reused ? '已复用相同输入的成功结果。' : result.modelCalled ? '本项已调用评分模型。' : '本项未调用评分模型。')}</p>
                  </article>
                );
              })}
            </div>
            <div className="recruitment-screening-batch-footer">
              <span>{getStage7FailedBatchApplicationIds(batchResult.outcome).length
                ? '仅失败项可以重新组成批次；已完成和 blocked 不会被误重跑。'
                : '当前批次没有可重试的 failed 项。'}</span>
              <Button
                disabled={!getStage7FailedBatchApplicationIds(batchResult.outcome).length || batchPending}
                loading={batchPending}
                onClick={retryFailedBatch}
                type="primary"
              >
                仅重试失败项
              </Button>
            </div>
          </>
        )}
      </Drawer>

      <RecruitmentScreeningDetailDrawer
        item={detailItem}
        onClose={() => setDetailItem(null)}
      />
    </main>
  );
};

export default RecruitmentScreeningCenter;
