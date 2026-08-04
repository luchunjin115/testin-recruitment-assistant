import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Alert, Button, Empty, Progress, Select, Skeleton, Tag, Tooltip } from 'antd';
import { Link } from 'react-router-dom';
import {
  getStage3ScreeningCenter,
  ScreeningCenterSnapshot,
  Stage3ScreeningResult,
} from './services/screening';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ScreeningCenterSnapshot };

const NO_MEANINGFUL_RISK = '暂无明显风险';

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}).format(new Date(value));

const getRecommendationTone = (recommendation: string | null, score: number | null) => {
  if (recommendation?.includes('建议') || (score !== null && score >= 80)) return 'success';
  if (recommendation?.includes('暂缓') || recommendation?.includes('备选')) return 'warning';
  return 'neutral';
};

const getHardPassMeta = (hardPass: boolean | null) => {
  if (hardPass === true) return { label: '硬性条件通过', tone: 'success' };
  if (hardPass === false) return { label: '硬性条件未通过', tone: 'warning' };
  return { label: '硬性条件未记录', tone: 'neutral' };
};

const hasMeaningfulRisk = (item: Stage3ScreeningResult) => item.risks.some(risk => (
  risk.trim() && risk.trim() !== NO_MEANINGFUL_RISK
));

const sourceLabel = (source: string | null) => {
  if (source === 'legacy_sqlite_import') return '历史数据迁入';
  return source || '来源未记录';
};

const Stage3ScreeningCenter: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [jobFilter, setJobFilter] = useState<number | 'all'>('all');
  const [recommendationFilter, setRecommendationFilter] = useState('all');

  const loadScreeningCenter = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      setLoadState({ status: 'ready', data: await getStage3ScreeningCenter() });
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法连接新版筛选结果接口',
      });
    }
  }, []);

  useEffect(() => {
    void loadScreeningCenter();
  }, [loadScreeningCenter]);

  const recommendationOptions = useMemo(() => {
    if (loadState.status !== 'ready') return [{ value: 'all', label: '全部推荐结果' }];
    return [
      { value: 'all', label: '全部推荐结果' },
      ...Array.from(new Set(
        loadState.data.items
          .map(item => item.recommendation)
          .filter((value): value is string => Boolean(value)),
      )).sort().map(value => ({ value, label: value })),
    ];
  }, [loadState]);

  const filteredItems = useMemo(() => {
    if (loadState.status !== 'ready') return [];
    return loadState.data.items.filter(item => (
      (jobFilter === 'all' || item.jobId === jobFilter)
      && (recommendationFilter === 'all' || item.recommendation === recommendationFilter)
    ));
  }, [jobFilter, loadState, recommendationFilter]);

  const resetFilters = () => {
    setJobFilter('all');
    setRecommendationFilter('all');
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="AI 初筛历史结果加载中" className="s3-main">
        <section className="s3-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="s3-stat-grid">
          {[0, 1, 2, 3].map(item => <article className="s3-stat-card" key={item}><Skeleton active paragraph={false} /></article>)}
        </section>
        <section className="s3-state-panel"><Skeleton active paragraph={{ rows: 8 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="s3-main">
        <section className="s3-page-heading">
          <div><span className="s3-section-kicker">新版 AI 初筛 · 只读历史结果</span><h2>AI 初筛</h2><p>按岗位查看已有筛选结论，不执行新的 AI 任务。</p></div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadScreeningCenter()}>重新加载</Button>}
          className="s3-dashboard-alert s3-section-gap"
          description={`请确认 FastAPI 已启动，且 /api/v2/jobs、/api/v2/candidates 与 /api/v2/screening-results 可访问。技术信息：${loadState.message}`}
          message="新版 AI 初筛数据加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const selectedJob = jobFilter === 'all' ? null : data.jobs.find(job => job.id === jobFilter) || null;
  const scoredItems = filteredItems.filter(item => item.overallScore !== null);
  const averageScore = scoredItems.length
    ? Math.round(scoredItems.reduce((sum, item) => sum + (item.overallScore || 0), 0) / scoredItems.length)
    : null;
  const uniqueCandidateCount = new Set(filteredItems.map(item => item.candidateId)).size;
  const riskResultCount = filteredItems.filter(hasMeaningfulRisk).length;
  const stats = [
    {
      label: '历史结果',
      value: filteredItems.length,
      note: jobFilter === 'all' ? `全库共 ${data.totalResults} 条` : `${selectedJob?.resultCount || 0} 条岗位结果`,
      icon: <RobotOutlined />,
      tone: 'blue',
    },
    {
      label: '覆盖候选人',
      value: uniqueCandidateCount,
      note: selectedJob ? `该岗位关联 ${selectedJob.candidateCount} 人` : `候选人库共 ${data.totalCandidates} 人`,
      icon: <TeamOutlined />,
      tone: 'green',
    },
    {
      label: '平均匹配分',
      value: averageScore ?? '—',
      note: scoredItems.length ? `基于 ${scoredItems.length} 条有效分数` : '当前没有可计算分数',
      icon: <SafetyCertificateOutlined />,
      tone: 'orange',
    },
    {
      label: '含风险结果',
      value: riskResultCount,
      note: '不含“暂无明显风险”',
      icon: <ExclamationCircleOutlined />,
      tone: 'red',
    },
  ];

  const hasActiveFilters = jobFilter !== 'all' || recommendationFilter !== 'all';

  return (
    <main className="s3-main">
      <section className="s3-page-heading s3-screening-heading">
        <div>
          <span className="s3-section-kicker">新版 AI 初筛 · 数据来源 /api/v2 · 只读</span>
          <h2>AI 初筛</h2>
          <p>查看 PostgreSQL 中已有的历史筛选结果；本页不会运行重新筛选、调用 LLM 或写入新结果。</p>
        </div>
        <Tooltip title="重新筛选属于后续 LangGraph 匹配工作流，本步不开放">
          <Button disabled icon={<RobotOutlined />} type="primary">重新筛选 · 后续</Button>
        </Tooltip>
      </section>

      <section aria-label="AI 初筛结果统计" className="s3-stat-grid">
        {stats.map(stat => (
          <article className="s3-stat-card" key={stat.label}>
            <div className={`s3-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="s3-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      <section className="s3-panel s3-screening-panel">
        <div className="s3-screening-toolbar">
          <div>
            <h3>初筛结果列表</h3>
            <p>{selectedJob ? `${selectedJob.title} · ${selectedJob.candidateCount} 名关联候选人` : `全部岗位 · ${data.totalResults} 条历史结果`}</p>
          </div>
          <div className="s3-screening-filter-controls">
            <Select
              aria-label="按岗位筛选初筛结果"
              onChange={setJobFilter}
              options={[
                { value: 'all', label: '全部岗位' },
                ...data.jobs.map(job => ({
                  value: job.id,
                  label: `${job.title}（${job.resultCount} 条）`,
                })),
              ]}
              showSearch
              optionFilterProp="label"
              value={jobFilter}
            />
            <Select
              aria-label="按推荐结果筛选"
              onChange={setRecommendationFilter}
              options={recommendationOptions}
              value={recommendationFilter}
            />
            <Button aria-label="刷新 AI 初筛结果" icon={<ReloadOutlined />} onClick={() => void loadScreeningCenter()} />
          </div>
        </div>

        {data.totalResults === 0 ? (
          <Empty
            className="s3-panel-empty s3-screening-empty"
            description={(
              <div className="s3-empty-copy">
                <strong>新版数据库中还没有筛选结果</strong>
                <span>候选人和岗位可以已经存在，但只有 /api/v2/screening-results 返回记录后，这里才会展示历史结果。</span>
              </div>
            )}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : filteredItems.length === 0 ? (
          <Empty
            className="s3-panel-empty s3-screening-empty"
            description={(
              <div className="s3-empty-copy">
                <strong>{selectedJob && recommendationFilter === 'all' ? '该岗位还没有筛选结果' : '已有历史结果，但当前筛选条件没有匹配项'}</strong>
                <span>{selectedJob && recommendationFilter === 'all'
                  ? `${selectedJob.title} 当前关联 ${selectedJob.candidateCount} 名候选人，本页不会自动为他们生成结果。`
                  : '可以清除岗位和推荐结果筛选，查看已有的历史初筛记录。'}</span>
              </div>
            )}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            {hasActiveFilters && <Button onClick={resetFilters}>清除筛选</Button>}
          </Empty>
        ) : (
          <div aria-label="新版 AI 初筛历史结果" className="s3-screening-list" role="list">
            {filteredItems.map(item => {
              const recommendationTone = getRecommendationTone(item.recommendation, item.overallScore);
              const hardPassMeta = getHardPassMeta(item.hardPass);
              return (
                <article className="s3-screening-result" key={item.id} role="listitem">
                  <div className="s3-screening-result-summary">
                    <div className="s3-screening-score" aria-label={item.overallScore === null ? '匹配分未记录' : `匹配分 ${item.overallScore}`}>
                      <strong>{item.overallScore ?? '—'}</strong>
                      <span>匹配分</span>
                      {item.overallScore !== null && (
                        <Progress
                          percent={item.overallScore}
                          showInfo={false}
                          size="small"
                          strokeColor={item.overallScore >= 80 ? '#3f6fd9' : '#8b96a8'}
                          trailColor="#edf0f4"
                        />
                      )}
                    </div>
                    <div className="s3-screening-candidate">
                      <Link to={`/stage3/candidates/${item.candidateId}`}>{item.candidateName}</Link>
                      <span>{item.candidateSource || `候选人 #${item.candidateId}`}</span>
                    </div>
                    <div className="s3-screening-job">
                      <strong>{item.jobTitle}</strong>
                      <span>岗位 #{item.jobId}</span>
                    </div>
                    <div className="s3-screening-tags">
                      <Tag bordered={false} className={`s3-status-tag is-${recommendationTone}`}>
                        {item.recommendation || '推荐结果未记录'}
                      </Tag>
                      {item.priorityLevel && <Tag bordered={false}>{item.priorityLevel}</Tag>}
                    </div>
                    <div className="s3-screening-updated"><span>更新时间</span><strong>{formatDateTime(item.updatedAt)}</strong></div>
                  </div>

                  <div className="s3-screening-analysis">
                    <div className="s3-screening-reason">
                      <span>筛选理由</span>
                      <p>{item.reason || '该条历史结果未记录筛选理由。'}</p>
                    </div>
                    <div className="s3-screening-evidence">
                      <span>优势项</span>
                      <div>{item.strengths.length
                        ? item.strengths.map(value => <Tag bordered={false} key={value}>{value}</Tag>)
                        : <em>未单独记录</em>}</div>
                    </div>
                    <div className={`s3-screening-evidence${hasMeaningfulRisk(item) ? ' has-risk' : ''}`}>
                      <span>风险项</span>
                      <div>{item.risks.length
                        ? item.risks.map(value => <Tag bordered={false} key={value}>{value}</Tag>)
                        : <em>未记录</em>}</div>
                    </div>
                  </div>

                  <div className="s3-screening-dimensions">
                    <span>技能分 <strong>{item.skillScore ?? '—'}</strong></span>
                    <span>经验分 <strong>{item.experienceScore ?? '—'}</strong></span>
                    <span>项目分 <strong>{item.projectScore ?? '—'}</strong></span>
                    <Tag bordered={false} className={`s3-status-tag is-${hardPassMeta.tone}`}>
                      {item.hardPass === true && <CheckCircleOutlined />} {hardPassMeta.label}
                    </Tag>
                    <span className="s3-screening-source">{sourceLabel(item.source)} · 结果 #{item.id}</span>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
};

export default Stage3ScreeningCenter;
