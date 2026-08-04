import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircleOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  SolutionOutlined,
  StopOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Drawer,
  Empty,
  Form,
  Input,
  Select,
  Skeleton,
  Tag,
} from 'antd';
import {
  getStage3Jobs,
  isClosedJobStatus,
  isOpenJobStatus,
  JobListSnapshot,
  Stage3Job,
} from './services/jobs';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: JobListSnapshot };

type JobFormValues = {
  title: string;
  department?: string;
  status: string;
  description?: string;
  requirementSummary?: string;
  requiredSkills?: string;
};

const getStatusMeta = (status: string) => {
  if (isOpenJobStatus(status)) return { label: '开放招聘', tone: 'success' };
  if (isClosedJobStatus(status)) return { label: '已关闭', tone: 'neutral' };
  return { label: status || '状态未填写', tone: 'warning' };
};

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}).format(new Date(value));

const Stage3JobList: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Stage3Job | null>(null);
  const [form] = Form.useForm<JobFormValues>();

  const loadJobs = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      setLoadState({ status: 'ready', data: await getStage3Jobs() });
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法连接新版岗位接口',
      });
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const statusOptions = useMemo(() => {
    if (loadState.status !== 'ready') return [{ value: 'all', label: '全部状态' }];
    return [
      { value: 'all', label: '全部状态' },
      ...Array.from(new Set(loadState.data.items.map(item => item.status)))
        .sort()
        .map(status => ({ value: status, label: getStatusMeta(status).label })),
    ];
  }, [loadState]);

  const filteredItems = useMemo(() => {
    if (loadState.status !== 'ready') return [];
    const normalizedKeyword = keyword.trim().toLowerCase();
    return loadState.data.items.filter(item => {
      const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
      const matchesKeyword = !normalizedKeyword || [
        item.title,
        item.department,
        item.description,
        item.requirementSummary,
        ...item.requiredSkills,
      ].some(value => value?.toLowerCase().includes(normalizedKeyword));
      return matchesStatus && matchesKeyword;
    });
  }, [keyword, loadState, statusFilter]);

  const openForm = (job: Stage3Job | null) => {
    setSelectedJob(job);
    form.setFieldsValue(job ? {
      title: job.title,
      department: job.department || undefined,
      status: job.status,
      description: job.description || undefined,
      requirementSummary: job.requirementSummary || undefined,
      requiredSkills: job.requiredSkills.join('、'),
    } : {
      title: '',
      department: undefined,
      status: 'open',
      description: undefined,
      requirementSummary: undefined,
      requiredSkills: undefined,
    });
    setFormOpen(true);
  };

  const resetFilters = () => {
    setKeyword('');
    setStatusFilter('all');
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="岗位列表加载中" className="s3-main">
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
          <div><span className="s3-section-kicker">新版岗位库 · 数据来源 /api/v2</span><h2>岗位管理</h2><p>集中查看招聘岗位、岗位状态和候选人关联。</p></div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadJobs()}>重新加载</Button>}
          className="s3-dashboard-alert s3-section-gap"
          description={`请确认 FastAPI 已启动，且 /api/v2/jobs 与 /api/v2/candidates 可访问。技术信息：${loadState.message}`}
          message="新版岗位数据加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const stats = [
    { label: '岗位总数', value: data.total, note: '新版岗位表真实记录', icon: <SolutionOutlined />, tone: 'blue' },
    { label: '开放岗位', value: data.openCount, note: '当前可以继续招聘', icon: <CheckCircleOutlined />, tone: 'green' },
    { label: '已关闭', value: data.closedCount, note: 'closed / inactive', icon: <StopOutlined />, tone: 'orange' },
    { label: '关联候选人', value: data.linkedCandidateCount, note: '按应聘岗位汇总', icon: <TeamOutlined />, tone: 'blue' },
  ];

  return (
    <main className="s3-main">
      <section className="s3-page-heading">
        <div>
          <span className="s3-section-kicker">新版岗位库 · 数据来源 /api/v2</span>
          <h2>岗位管理</h2>
          <p>查看岗位状态、职责要求和候选人关联；新增与编辑目前只开放表单结构预览。</p>
        </div>
        <Button icon={<PlusOutlined />} onClick={() => openForm(null)} type="primary">新增岗位 · 表单预览</Button>
      </section>

      <section aria-label="岗位统计" className="s3-stat-grid">
        {stats.map(stat => (
          <article className="s3-stat-card" key={stat.label}>
            <div className={`s3-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="s3-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      <section className="s3-panel s3-job-list-panel">
        <div className="s3-job-toolbar">
          <div>
            <h3>岗位列表</h3>
            <p>共 {data.total} 个真实岗位，候选人数来自新版候选人关联</p>
          </div>
          <div className="s3-job-filter-controls">
            <Input
              allowClear
              aria-label="搜索岗位"
              onChange={event => setKeyword(event.target.value)}
              placeholder="搜索岗位、部门、职责或技能"
              prefix={<SearchOutlined />}
              value={keyword}
            />
            <Select
              aria-label="按岗位状态筛选"
              onChange={setStatusFilter}
              options={statusOptions}
              value={statusFilter}
            />
            <Button aria-label="刷新岗位列表" icon={<ReloadOutlined />} onClick={() => void loadJobs()} />
          </div>
        </div>

        {data.total === 0 ? (
          <Empty
            className="s3-panel-empty s3-job-empty"
            description={
              <div className="s3-empty-copy">
                <strong>新版岗位库目前没有岗位</strong>
                <span>页面已成功连接 /api/v2/jobs；后续通过新版岗位表单创建的数据会显示在这里。</span>
              </div>
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button icon={<PlusOutlined />} onClick={() => openForm(null)}>查看新增表单结构</Button>
          </Empty>
        ) : filteredItems.length === 0 ? (
          <Empty
            className="s3-panel-empty s3-job-empty"
            description="没有符合当前搜索和筛选条件的岗位"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button onClick={resetFilters}>清除筛选</Button>
          </Empty>
        ) : (
          <div aria-label="新版岗位列表" className="s3-table" role="table">
            <div className="s3-table-head s3-job-table-columns" role="row">
              <span>岗位</span><span>部门</span><span>岗位要求</span><span>候选人</span><span>状态</span><span>更新时间</span><span>表单</span>
            </div>
            {filteredItems.map(item => {
              const statusMeta = getStatusMeta(item.status);
              return (
                <div className="s3-table-row s3-job-table-columns" key={item.id} role="row">
                  <div className="s3-job-title-cell">
                    <span className="s3-job-mark"><SolutionOutlined /></span>
                    <div><strong>{item.title}</strong><span>岗位 #{item.id}</span></div>
                  </div>
                  <span className="s3-role-cell">{item.department || '部门未填写'}</span>
                  <div className="s3-job-requirement-cell">
                    <strong>{item.requirementSummary || item.description || '岗位要求未填写'}</strong>
                    <div>
                      {item.requiredSkills.slice(0, 3).map(skill => <Tag bordered={false} key={skill}>{skill}</Tag>)}
                      {item.requiredSkills.length > 3 && <span>+{item.requiredSkills.length - 3}</span>}
                    </div>
                  </div>
                  <div className="s3-job-candidate-count"><strong>{item.candidateCount}</strong><span>人</span></div>
                  <div><Tag bordered={false} className={`s3-status-tag is-${statusMeta.tone}`}>{statusMeta.label}</Tag></div>
                  <span className="s3-time-cell">{formatDateTime(item.updatedAt)}</span>
                  <Button icon={<EditOutlined />} onClick={() => openForm(item)} size="small">查看结构</Button>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <Drawer
        className="s3-job-form-drawer"
        extra={(
          <div className="s3-job-form-actions">
            <Button onClick={() => setFormOpen(false)}>关闭</Button>
            <Button disabled type="primary">保存岗位 · 后续</Button>
          </div>
        )}
        onClose={() => setFormOpen(false)}
        open={formOpen}
        title={selectedJob ? `岗位表单结构 · #${selectedJob.id}` : '新增岗位表单结构'}
        width="min(520px, 100vw)"
      >
        <Alert
          description="当前只验证字段和操作布局，保存入口尚未连接 /api/v2 写接口，不会修改 PostgreSQL。"
          message="阶段 3 表单结构预览"
          showIcon
          type="info"
        />
        <Form className="s3-job-form" form={form} layout="vertical">
          <Form.Item label="岗位名称" name="title" required>
            <Input placeholder="例如：高级后端工程师" />
          </Form.Item>
          <div className="s3-job-form-grid">
            <Form.Item label="所属部门" name="department">
              <Input placeholder="例如：技术部" />
            </Form.Item>
            <Form.Item label="岗位状态" name="status" required>
              <Select options={[
                { value: 'open', label: '开放招聘' },
                { value: 'closed', label: '已关闭' },
                { value: 'draft', label: '草稿结构' },
              ]} />
            </Form.Item>
          </div>
          <Form.Item label="岗位描述" name="description">
            <Input.TextArea autoSize={{ minRows: 4, maxRows: 7 }} placeholder="填写岗位职责和工作内容" />
          </Form.Item>
          <Form.Item extra="这里只展示新版 requirements JSONB 对应的摘要字段。" label="任职要求摘要" name="requirementSummary">
            <Input.TextArea autoSize={{ minRows: 4, maxRows: 7 }} placeholder="填写学历、经验和能力要求" />
          </Form.Item>
          <Form.Item extra="多个技能可使用顿号或逗号分隔；当前不会保存。" label="必备技能" name="requiredSkills">
            <Input placeholder="例如：Python、FastAPI、PostgreSQL" />
          </Form.Item>
        </Form>
      </Drawer>
    </main>
  );
};

export default Stage3JobList;
