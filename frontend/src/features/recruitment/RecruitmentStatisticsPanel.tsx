import React, { useCallback, useEffect, useState } from 'react';
import { ReloadOutlined } from '@ant-design/icons';
import { Alert, Button, DatePicker, Select, Skeleton, Tag } from 'antd';
import type { Dayjs } from 'dayjs';
import { getRecruitmentJobs, type RecruitmentJob } from './services/jobs';
import {
  getRecruitmentStatistics,
  getRecruitmentStatisticsError,
  type RecruitmentDurationKey,
  type RecruitmentFunnelKey,
  type RecruitmentStatistics,
} from './services/recruitmentStatistics';

const { RangePicker } = DatePicker;

const FUNNEL_LABELS: Record<RecruitmentFunnelKey, string> = {
  applications: '收到申请',
  screening_passed: '通过初筛',
  interview_entered: '进入面试',
  interview_completed: '完成面试',
  offer_sent: 'Offer 已发送',
  offer_accepted: 'Offer 已接受',
  admitted: '确认录取',
  hired: '正式入职',
};

const DURATION_LABELS: Record<RecruitmentDurationKey, string> = {
  application_to_screening_passed: '投递 → 初筛通过',
  screening_passed_to_first_interview: '初筛通过 → 首轮面试创建',
  first_interview_to_last_completed: '首轮创建 → 最后一轮完成',
  offer_entered_to_sent: '进入 Offer → 发出',
  offer_sent_to_response: 'Offer 发出 → 接受 / 拒绝',
  offer_accepted_to_admitted: '接受 Offer → 确认录取',
  admitted_to_hired: '确认录取 → 正式入职',
};

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: RecruitmentStatistics };

type Props = {
  jobId?: number | 'all';
  jobs?: RecruitmentJob[];
  onJobIdChange?: (value: number | 'all') => void;
  refreshKey?: number;
};

const formatHours = (value: number | null) => {
  if (value === null) return '—';
  if (value >= 48) return `${(value / 24).toFixed(1)} 天`;
  return `${value.toFixed(1)} 小时`;
};

const RecruitmentStatisticsPanel: React.FC<Props> = ({
  jobId: controlledJobId,
  jobs: providedJobs,
  onJobIdChange,
  refreshKey = 0,
}) => {
  const [internalJobId, setInternalJobId] = useState<number | 'all'>('all');
  const [internalJobs, setInternalJobs] = useState<RecruitmentJob[]>([]);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const selectedJobId = controlledJobId ?? internalJobId;
  const jobs = providedJobs ?? internalJobs;

  useEffect(() => {
    if (providedJobs) return;
    void getRecruitmentJobs()
      .then(result => setInternalJobs(result.items))
      .catch(() => setInternalJobs([]));
  }, [providedJobs]);

  const load = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      const data = await getRecruitmentStatistics({
        jobId: selectedJobId === 'all' ? undefined : selectedJobId,
        appliedFrom: dateRange?.[0]?.startOf('day').toISOString(),
        appliedTo: dateRange?.[1]?.endOf('day').toISOString(),
      });
      setLoadState({ status: 'ready', data });
    } catch (error) {
      setLoadState({ status: 'error', message: getRecruitmentStatisticsError(error) });
    }
  }, [dateRange, selectedJobId]);

  useEffect(() => { void load(); }, [load, refreshKey]);

  const changeJob = (value: number | 'all') => {
    if (onJobIdChange) onJobIdChange(value);
    else setInternalJobId(value);
  };

  return (
    <section aria-label="招聘流程统计" className="recruitment-statistics-panel">
      <header className="recruitment-statistics-header">
        <div>
          <span className="recruitment-section-kicker">PostgreSQL 业务事实 · 不调用 AI</span>
          <h3>招聘流程统计</h3>
          <p>漏斗按投递时间固定 cohort，里程碑读取历史；当前待办不受日期范围影响。</p>
        </div>
        <div className="recruitment-statistics-filters">
          <Select
            aria-label="按岗位筛选招聘统计"
            onChange={changeJob}
            options={[
              { value: 'all', label: '全部岗位' },
              ...jobs.map(job => ({ value: job.id, label: job.title })),
            ]}
            value={selectedJobId}
          />
          <RangePicker
            allowClear
            aria-label="按投递日期筛选招聘统计"
            onChange={value => setDateRange(value ? [value[0], value[1]] : null)}
            value={dateRange}
          />
          <Button aria-label="刷新招聘流程统计" icon={<ReloadOutlined />} onClick={() => void load()} />
        </div>
      </header>

      {loadState.status === 'loading' && <Skeleton active paragraph={{ rows: 5 }} />}
      {loadState.status === 'error' && (
        <Alert
          action={<Button onClick={() => void load()}>重试</Button>}
          message={loadState.message}
          showIcon
          type="error"
        />
      )}
      {loadState.status === 'ready' && (
        <>
          <div aria-label="招聘漏斗" className="recruitment-funnel-grid">
            {loadState.data.funnel.map((step, index) => (
              <article key={step.key}>
                <span>{FUNNEL_LABELS[step.key]}</span>
                <strong>{step.count}</strong>
                <small>{index === 0 ? 'cohort 总数' : step.conversionRate === null ? '上一环节无样本' : `上一步转化 ${step.conversionRate.toFixed(2)}%`}</small>
              </article>
            ))}
          </div>
          <div className="recruitment-statistics-detail-grid">
            <section>
              <div className="recruitment-statistics-subheading"><h4>阶段平均耗时</h4><span>缺少端点不计入平均值</span></div>
              <div className="recruitment-duration-grid">
                {loadState.data.durations.map(metric => (
                  <article key={metric.key}>
                    <span>{DURATION_LABELS[metric.key]}</span>
                    <strong>{formatHours(metric.averageHours)}</strong>
                    <small>样本 {metric.sampleCount}</small>
                  </article>
                ))}
              </div>
            </section>
            <aside>
              <div className="recruitment-statistics-subheading"><h4>当前待办</h4><Tag color="processing">实时 {loadState.data.todos.total}</Tag></div>
              <dl className="recruitment-todo-snapshot">
                <div><dt>面试待发生</dt><dd>{loadState.data.todos.scheduledInterviews}</dd></div>
                <div><dt>面试待决定</dt><dd>{loadState.data.todos.pendingInterviewDecisions}</dd></div>
                <div><dt>下一轮待创建</dt><dd>{loadState.data.todos.nextRoundNotScheduled}</dd></div>
                <div><dt>Offer 草稿待发送</dt><dd>{loadState.data.todos.draftOffers}</dd></div>
                <div><dt>Offer 待回应</dt><dd>{loadState.data.todos.sentOffers}</dd></div>
                <div><dt>接受后待确认录取</dt><dd>{loadState.data.todos.acceptedOffers}</dd></div>
                <div><dt>录取后待确认入职</dt><dd>{loadState.data.todos.admittedApplications}</dd></div>
              </dl>
            </aside>
          </div>
        </>
      )}
    </section>
  );
};

export default RecruitmentStatisticsPanel;
