import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
  ReloadOutlined,
  RobotOutlined,
  SearchOutlined,
  TeamOutlined,
  UserAddOutlined,
} from '@ant-design/icons';
import { Alert, Avatar, Button, Empty, Input, Select, Skeleton, Tag, Tooltip } from 'antd';
import { Link, useNavigate } from 'react-router-dom';
import {
  type CandidateListSnapshot,
  getRecruitmentCandidates,
} from './services/candidates';
import type { Stage7ApplicationAIStatus } from './types/applicationScreening';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: CandidateListSnapshot };

type StatusMeta = { label: string; tone: 'info' | 'success' | 'warning' | 'danger' | 'neutral' };

const avatarTones = ['blue', 'violet', 'green', 'orange'];

const AI_STATUS_META: Record<Stage7ApplicationAIStatus, StatusMeta> = {
  not_started: { label: '等待评分', tone: 'neutral' },
  screening: { label: '评分中', tone: 'info' },
  completed: { label: '评分完成', tone: 'success' },
  failed: { label: '评分失败', tone: 'danger' },
  blocked: { label: '资料不足', tone: 'warning' },
};

const SOURCE_LABELS = {
  hr_direct: 'HR 人工直通',
  hr_screening: 'AI 初筛通过',
  public_apply: '公开投递通过',
} as const;

const RECOMMENDATION_LABELS: Record<string, string> = {
  strong_recommend: '强烈推荐',
  recommend: '建议推进',
  review_required: '需要复核',
  low_match: '匹配度较低',
};

const formatDateTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
};

const RecruitmentCandidateList: React.FC = () => {
  const navigate = useNavigate();
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [keyword, setKeyword] = useState('');
  const [aiFilter, setAiFilter] = useState<Stage7ApplicationAIStatus | 'all'>('all');
  const [jobFilter, setJobFilter] = useState<number | 'all'>('all');

  const loadCandidates = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      setLoadState({ status: 'ready', data: await getRecruitmentCandidates() });
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法读取已通过 Application',
      });
    }
  }, []);

  useEffect(() => {
    void loadCandidates();
  }, [loadCandidates]);

  const filteredItems = useMemo(() => {
    if (loadState.status !== 'ready') return [];
    const normalizedKeyword = keyword.trim().toLowerCase();

    return loadState.data.items.filter(item => {
      const matchesAi = aiFilter === 'all' || item.aiStatus === aiFilter;
      const matchesJob = jobFilter === 'all' || item.jobId === jobFilter;
      const matchesKeyword = !normalizedKeyword || [
        item.name,
        item.email,
        item.phone,
        item.currentCompany,
        item.currentTitle,
        item.jobTitle,
        item.jobDepartment,
        `application #${item.applicationId}`,
      ].some(value => value?.toLowerCase().includes(normalizedKeyword));
      return matchesAi && matchesJob && matchesKeyword;
    });
  }, [aiFilter, jobFilter, keyword, loadState]);

  const resetFilters = () => {
    setKeyword('');
    setAiFilter('all');
    setJobFilter('all');
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="已通过 Application 加载中" className="recruitment-main">
        <section className="recruitment-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="recruitment-candidate-entry-rule is-loading"><Skeleton active paragraph={{ rows: 1 }} /></section>
        <section className="recruitment-stat-grid">
          {[0, 1, 2, 3].map(item => <article className="recruitment-stat-card" key={item}><Skeleton active paragraph={false} /></article>)}
        </section>
        <section className="recruitment-state-panel"><Skeleton active paragraph={{ rows: 6 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="recruitment-main">
        <section className="recruitment-page-heading">
          <div>
            <span className="recruitment-section-kicker">阶段 7 · 已通过 Application 业务视图</span>
            <h2>候选人</h2>
            <p>每一行对应一份已经由 HR 通过的岗位申请。</p>
          </div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadCandidates()}>重新加载</Button>}
          className="recruitment-dashboard-alert recruitment-section-gap"
          description={`请确认 applications、candidates、jobs 和 screening-results 接口可访问。技术信息：${loadState.message}`}
          message="已通过候选人数据加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const stats = [
    {
      label: '已通过申请', value: data.total, note: '每一行是一份 Application',
      icon: <CheckCircleOutlined />, tone: 'green',
    },
    {
      label: '实际人数', value: data.uniqueCandidateCount, note: '同一人多岗位只计一次',
      icon: <TeamOutlined />, tone: 'blue',
    },
    {
      label: '覆盖岗位', value: data.linkedJobCount, note: '已有 HR 通过记录',
      icon: <LinkOutlined />, tone: 'orange',
    },
    {
      label: '评分待跟进', value: data.needsAttentionCount, note: '未完成、失败、资料不足或过期',
      icon: <ExclamationCircleOutlined />, tone: 'red',
    },
  ];

  return (
    <main className="recruitment-main">
      <section className="recruitment-page-heading">
        <div>
          <span className="recruitment-section-kicker">阶段 7 · 已通过 Application 业务视图</span>
          <h2>候选人</h2>
          <p>只展示 HR 已通过的岗位申请；AI 后续重跑不会自动改变这里的人员归类。</p>
        </div>
        <Tooltip title="HR 核对资料并人工通过后，系统会自动尝试一次 AI 岗位评分">
          <Button icon={<UserAddOutlined />} onClick={() => navigate('/app/candidates/new')} type="primary">新增候选人</Button>
        </Tooltip>
      </section>

      <section aria-label="候选人页面准入规则" className="recruitment-candidate-entry-rule">
        <div className="recruitment-candidate-entry-rule-mark"><CheckCircleOutlined /></div>
        <div>
          <span>页面准入规则</span>
          <strong>HR 已通过 Application → 进入候选人业务视图</strong>
          <p>待决策、备选和淘汰仍留在 AI 初筛中心；Candidate 可以存在于数据库，但不会因此自动出现在这里。</p>
        </div>
        <div className="recruitment-candidate-entry-rule-count">
          <strong>{data.total}</strong><span>份申请</span><b>/</b><strong>{data.uniqueCandidateCount}</strong><span>人</span>
        </div>
      </section>

      <section aria-label="已通过 Application 统计" className="recruitment-stat-grid">
        {stats.map(stat => (
          <article className="recruitment-stat-card" key={stat.label}>
            <div className={`recruitment-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="recruitment-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      <section className="recruitment-panel recruitment-candidate-list-panel">
        <div className="recruitment-candidate-toolbar">
          <div>
            <h3>已通过申请</h3>
            <p>按 Application 更新时间倒序排列，共 {data.total} 份；同一人通过多个岗位时分行展示</p>
          </div>
          <div className="recruitment-candidate-filter-controls">
            <Input
              allowClear
              aria-label="搜索已通过候选人"
              onChange={event => setKeyword(event.target.value)}
              placeholder="搜索姓名、联系方式、岗位或 Application"
              prefix={<SearchOutlined />}
              value={keyword}
            />
            <Select
              aria-label="按通过岗位筛选"
              onChange={setJobFilter}
              options={[
                { value: 'all', label: '全部岗位' },
                ...data.jobs.map(job => ({ value: job.id, label: job.title })),
              ]}
              value={jobFilter}
            />
            <Select
              aria-label="按 AI 状态筛选"
              className="recruitment-candidate-status-select"
              onChange={setAiFilter}
              options={[
                { value: 'all', label: '全部 AI 状态' },
                ...Object.entries(AI_STATUS_META).map(([value, meta]) => ({ value, label: meta.label })),
              ]}
              value={aiFilter}
            />
            {(keyword || jobFilter !== 'all' || aiFilter !== 'all') && <Button onClick={resetFilters}>清除筛选</Button>}
            <Button aria-label="刷新已通过 Application" icon={<ReloadOutlined />} onClick={() => void loadCandidates()} />
          </div>
        </div>

        {data.total === 0 ? (
          <Empty
            className="recruitment-panel-empty recruitment-candidate-empty"
            description={
              <div className="recruitment-empty-copy">
                <strong>目前没有 HR 已通过的 Application</strong>
                <span>待决策、备选和淘汰不会显示在这里；请先前往 AI 初筛中心处理申请。</span>
              </div>
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button icon={<RobotOutlined />} onClick={() => navigate('/app/screening')} type="primary">前往 AI 初筛中心</Button>
          </Empty>
        ) : filteredItems.length === 0 ? (
          <Empty
            className="recruitment-panel-empty recruitment-candidate-empty"
            description="没有符合当前搜索和筛选条件的已通过申请"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button onClick={resetFilters}>清除筛选</Button>
          </Empty>
        ) : (
          <div aria-label="HR 已通过 Application 列表" className="recruitment-table" role="table">
            <div className="recruitment-table-head recruitment-candidate-table-columns" role="row">
              <span>候选人</span><span>已通过岗位</span><span>当前 AI 证据</span><span>AI 状态</span><span>招聘阶段</span><span>申请来源</span><span>更新时间</span>
            </div>
            {filteredItems.map(item => {
              const aiMeta = AI_STATUS_META[item.aiStatus];
              return (
                <div className="recruitment-table-row recruitment-candidate-table-columns" key={item.applicationId} role="row">
                  <div className="recruitment-candidate-cell">
                    <Avatar className={`recruitment-candidate-avatar is-${avatarTones[item.candidateId % avatarTones.length]}`}>
                      {item.name.slice(0, 1)}
                    </Avatar>
                    <div>
                      <Link className="recruitment-candidate-name-link" to={`/app/candidates/${item.candidateId}`}>{item.name}</Link>
                      <span>{item.email || item.phone || `Candidate #${item.candidateId}`}</span>
                    </div>
                  </div>
                  <div className="recruitment-candidate-application-role">
                    <strong>{item.jobTitle}</strong>
                    <span>{item.jobDepartment || '部门未填写'} · Application #{item.applicationId}</span>
                  </div>
                  <div className="recruitment-candidate-ai-result">
                    <strong>{item.currentScore === null ? '—' : `${item.currentScore} 分`}</strong>
                    <span>{item.currentResultIsOutdated
                      ? '结果已过期'
                      : item.currentRecommendation
                        ? RECOMMENDATION_LABELS[item.currentRecommendation] || item.currentRecommendation
                        : '暂无推荐等级'}</span>
                  </div>
                  <div><Tag bordered={false} className={`recruitment-status-tag is-${aiMeta.tone}`}>{aiMeta.label}</Tag></div>
                  <div><Tag bordered={false} className="recruitment-status-tag is-success">初筛已通过</Tag></div>
                  <span className="recruitment-role-cell">{SOURCE_LABELS[item.applicationSource]}</span>
                  <span className="recruitment-time-cell">{formatDateTime(item.updatedAt)}</span>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
};

export default RecruitmentCandidateList;
