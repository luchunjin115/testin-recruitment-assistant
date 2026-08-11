import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  FileDoneOutlined,
  LinkOutlined,
  ReloadOutlined,
  SearchOutlined,
  TeamOutlined,
  UserAddOutlined,
} from '@ant-design/icons';
import { Alert, Avatar, Button, Empty, Input, Select, Skeleton, Tag } from 'antd';
import { Link, useNavigate } from 'react-router-dom';
import {
  getCandidateStatusMeta,
  getCandidateStatusOptionLabel,
  sortCandidateStatuses,
} from './candidateStatus';
import {
  CandidateListSnapshot,
  getStage3Candidates,
} from './services/candidates';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: CandidateListSnapshot };

const avatarTones = ['blue', 'violet', 'green', 'orange'];

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}).format(new Date(value));

const Stage3CandidateList: React.FC = () => {
  const navigate = useNavigate();
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [jobFilter, setJobFilter] = useState<number | 'all'>('all');

  const loadCandidates = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      const data = await getStage3Candidates();
      setLoadState({ status: 'ready', data });
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法连接新版候选人接口',
      });
    }
  }, []);

  useEffect(() => {
    void loadCandidates();
  }, [loadCandidates]);

  const statusOptions = useMemo(() => {
    if (loadState.status !== 'ready') return [{ value: 'all', label: '全部状态' }];
    const statuses = sortCandidateStatuses(Array.from(new Set(loadState.data.items.map(item => item.status))));
    return [
      { value: 'all', label: '全部状态' },
      ...statuses.map(status => ({ value: status, label: getCandidateStatusOptionLabel(status) })),
    ];
  }, [loadState]);

  const filteredItems = useMemo(() => {
    if (loadState.status !== 'ready') return [];
    const normalizedKeyword = keyword.trim().toLowerCase();

    return loadState.data.items.filter(item => {
      const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
      const matchesJob = jobFilter === 'all' || item.appliedJobId === jobFilter;
      const matchesKeyword = !normalizedKeyword || [
        item.name,
        item.email,
        item.phone,
        item.currentCompany,
        item.currentTitle,
        item.appliedJobTitle,
      ].some(value => value?.toLowerCase().includes(normalizedKeyword));
      return matchesStatus && matchesJob && matchesKeyword;
    });
  }, [jobFilter, keyword, loadState, statusFilter]);

  const resetFilters = () => {
    setKeyword('');
    setStatusFilter('all');
    setJobFilter('all');
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="候选人列表加载中" className="s3-main">
        <section className="s3-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="s3-stat-grid">
          {[0, 1, 2, 3].map(item => <article className="s3-stat-card" key={item}><Skeleton active paragraph={false} /></article>)}
        </section>
        <section className="s3-state-panel"><Skeleton active paragraph={{ rows: 6 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="s3-main">
        <section className="s3-page-heading">
          <div><span className="s3-section-kicker">新版候选人库 · 数据来源 /api/v2</span><h2>候选人</h2><p>集中查看候选人资料和岗位关联。</p></div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadCandidates()}>重新加载</Button>}
          className="s3-dashboard-alert s3-section-gap"
          description={`请确认 FastAPI 已启动，且 /api/v2/candidates 可访问。技术信息：${loadState.message}`}
          message="新版候选人数据加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const stats = [
    { label: '候选人总数', value: data.total, note: '新版候选人表真实记录', icon: <TeamOutlined />, tone: 'blue' },
    { label: '新候选人', value: data.newCount, note: '候选人状态：新候选人', icon: <UserAddOutlined />, tone: 'green' },
    { label: '已关联岗位', value: data.linkedJobCount, note: `当前岗位库 ${data.jobs.length} 个`, icon: <LinkOutlined />, tone: 'orange' },
    { label: '已含简历', value: data.withResumeCount, note: '已记录简历文件路径', icon: <FileDoneOutlined />, tone: 'blue' },
  ];

  return (
      <main className="s3-main">
      <section className="s3-page-heading">
        <div>
          <span className="s3-section-kicker">新版候选人库 · 数据来源 /api/v2</span>
          <h2>候选人</h2>
          <p>通过统一新增页面手动填写资料，也可以上传简历并提取原文后一次确认。</p>
        </div>
        <Button icon={<UserAddOutlined />} onClick={() => navigate('/stage3/candidates/new')} type="primary">新增候选人</Button>
      </section>

      <section aria-label="候选人统计" className="s3-stat-grid">
        {stats.map(stat => (
          <article className="s3-stat-card" key={stat.label}>
            <div className={`s3-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="s3-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      <section className="s3-panel s3-candidate-list-panel">
        <div className="s3-candidate-toolbar">
          <div>
            <h3>候选人列表</h3>
            <p>按更新时间倒序排列，共 {data.total} 位真实候选人</p>
          </div>
          <div className="s3-candidate-filter-controls">
            <Input
              allowClear
              aria-label="搜索候选人"
              onChange={event => setKeyword(event.target.value)}
              placeholder="搜索姓名、联系方式、公司或岗位"
              prefix={<SearchOutlined />}
              value={keyword}
            />
            <Select
              aria-label="按岗位筛选"
              onChange={setJobFilter}
              options={[
                { value: 'all', label: '全部岗位' },
                ...data.jobs.map(job => ({ value: job.id, label: job.title })),
              ]}
              value={jobFilter}
            />
            <Select
              aria-label="按候选人状态筛选"
              className="s3-candidate-status-select"
              onChange={setStatusFilter}
              options={statusOptions}
              value={statusFilter}
            />
            <Button aria-label="刷新候选人列表" icon={<ReloadOutlined />} onClick={() => void loadCandidates()} />
          </div>
        </div>

        {data.total === 0 ? (
          <Empty
            className="s3-panel-empty s3-candidate-empty"
            description={
              <div className="s3-empty-copy">
                <strong>新版候选人库目前没有候选人</strong>
                <span>可以纯手动创建，也可以先上传并提取简历原文。</span>
              </div>
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button icon={<UserAddOutlined />} onClick={() => navigate('/stage3/candidates/new')} type="primary">新增候选人</Button>
          </Empty>
        ) : filteredItems.length === 0 ? (
          <Empty
            className="s3-panel-empty s3-candidate-empty"
            description="没有符合当前搜索和筛选条件的候选人"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button onClick={resetFilters}>清除筛选</Button>
          </Empty>
        ) : (
          <div aria-label="新版候选人列表" className="s3-table" role="table">
            <div className="s3-table-head s3-candidate-table-columns" role="row">
              <span>候选人</span><span>应聘岗位</span><span>当前经历</span><span>学历 / 年限</span><span>来源</span><span>状态</span><span>更新时间</span>
            </div>
            {filteredItems.map(item => {
              const meta = getCandidateStatusMeta(item.status);
              return (
                <div className="s3-table-row s3-candidate-table-columns" key={item.id} role="row">
                  <div className="s3-candidate-cell">
                    <Avatar className={`s3-candidate-avatar is-${avatarTones[item.id % avatarTones.length]}`}>
                      {item.name.slice(0, 1)}
                    </Avatar>
                    <div>
                      <Link className="s3-candidate-name-link" to={`/stage3/candidates/${item.id}`}>{item.name}</Link>
                      <span>{item.email || item.phone || `候选人 #${item.id}`}</span>
                    </div>
                  </div>
                  <span className="s3-role-cell">{item.appliedJobTitle}</span>
                  <div className="s3-candidate-experience">
                    <strong>{item.currentTitle || '当前职位未填写'}</strong>
                    <span>{item.currentCompany || '当前公司未填写'}</span>
                  </div>
                  <div className="s3-candidate-experience">
                    <strong>{item.educationLevel || '学历未填写'}</strong>
                    <span>{item.workYears === null ? '年限未填写' : `${item.workYears} 年经验`}</span>
                  </div>
                  <span className="s3-role-cell">{item.source || '来源未填写'}</span>
                  <div><Tag bordered={false} className={`s3-status-tag is-${meta.tone}`}>{meta.label}</Tag></div>
                  <span className="s3-time-cell">{formatDateTime(item.updatedAt)}</span>
                </div>
              );
            })}
          </div>
        )}
      </section>
      </main>
  );
};

export default Stage3CandidateList;
