import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  FundProjectionScreenOutlined,
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
  InputNumber,
  message,
  Modal,
  Select,
  Skeleton,
  Tag,
} from 'antd';
import {
  closeRecruitmentJob,
  createRecruitmentJob,
  deleteRecruitmentJob,
  EmploymentType,
  getRecruitmentJobApiError,
  getRecruitmentJobs,
  isClosedJobStatus,
  isOpenJobStatus,
  JobListSnapshot,
  JobStatus,
  openRecruitmentJob,
  reopenRecruitmentJob,
  RecruitmentJob,
  RecruitmentJobInput,
  updateRecruitmentJob,
} from './services/jobs';
import JobEvaluationPlanDrawer from './JobEvaluationPlanDrawer';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: JobListSnapshot };

type JobFormValues = {
  title: string;
  department?: string;
  location?: string;
  employmentType?: EmploymentType;
  headcount?: number;
  jobBackground?: string;
  jobResponsibilities?: string;
  candidateRequirements?: string;
  preferredQualifications?: string;
  publicNotes?: string;
};

const statusOptions: { value: 'all' | JobStatus; label: string }[] = [
  { value: 'all', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'open', label: '开放招聘' },
  { value: 'closed', label: '已关闭' },
];

const employmentOptions = [
  { value: 'full_time', label: '全职' },
  { value: 'part_time', label: '兼职' },
  { value: 'internship', label: '实习' },
  { value: 'contract', label: '合同制' },
];

const backendFieldToFormField: Record<string, keyof JobFormValues> = {
  title: 'title',
  department: 'department',
  location: 'location',
  employment_type: 'employmentType',
  headcount: 'headcount',
  job_background: 'jobBackground',
  job_responsibilities: 'jobResponsibilities',
  candidate_requirements: 'candidateRequirements',
  preferred_qualifications: 'preferredQualifications',
  public_notes: 'publicNotes',
};

const getStatusMeta = (status: JobStatus) => {
  if (isOpenJobStatus(status)) return { label: '开放招聘', tone: 'success' };
  if (isClosedJobStatus(status)) return { label: '已关闭', tone: 'neutral' };
  return { label: '草稿', tone: 'warning' };
};

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hour12: false,
}).format(new Date(value));

const optionalText = (value?: string) => value?.trim() || null;

const formatReferenceCounts = (references: Record<string, number> | null) => {
  if (!references) return '';
  const labels: Record<string, string> = {
    candidates: '候选人',
    resumes: '简历',
    applications: '申请',
    reports: '报告',
  };
  const details = Object.entries(references)
    .filter(([, count]) => count > 0)
    .map(([key, count]) => `${labels[key] || key} ${count} 条`);
  return details.length ? `（${details.join('、')}）` : '';
};

const buildJobInput = (values: JobFormValues): RecruitmentJobInput => ({
  title: values.title.trim(),
  department: optionalText(values.department),
  location: optionalText(values.location),
  employment_type: values.employmentType || null,
  headcount: values.headcount ?? null,
  job_background: optionalText(values.jobBackground),
  job_responsibilities: optionalText(values.jobResponsibilities),
  candidate_requirements: optionalText(values.candidateRequirements),
  preferred_qualifications: optionalText(values.preferredQualifications),
  public_notes: optionalText(values.publicNotes),
});

const formValuesFromJob = (job: RecruitmentJob): JobFormValues => ({
  title: job.title,
  department: job.department || undefined,
  location: job.location || undefined,
  employmentType: job.employmentType || undefined,
  headcount: job.headcount || undefined,
  jobBackground: job.jobBackground || undefined,
  jobResponsibilities: job.jobResponsibilities || undefined,
  candidateRequirements: job.candidateRequirements || undefined,
  preferredQualifications: job.preferredQualifications || undefined,
  publicNotes: job.publicNotes || undefined,
});

const RecruitmentJobList: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | JobStatus>('all');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<RecruitmentJob | null>(null);
  const [planJob, setPlanJob] = useState<RecruitmentJob | null>(null);
  const planTriggerRef = useRef<HTMLElement | null>(null);
  const [operationPending, setOperationPending] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [pendingSuccessMessage, setPendingSuccessMessage] = useState<string | null>(null);
  const [form] = Form.useForm<JobFormValues>();
  const [messageApi, messageContext] = message.useMessage();
  const [modalApi, modalContext] = Modal.useModal();

  const loadJobs = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      setLoadState({ status: 'ready', data: await getRecruitmentJobs() });
    } catch (error) {
      setLoadState({ status: 'error', message: error instanceof Error ? error.message : '无法连接新版岗位接口' });
    }
  }, []);

  useEffect(() => { void loadJobs(); }, [loadJobs]);

  useEffect(() => {
    if (loadState.status !== 'ready' || !pendingSuccessMessage) return;
    messageApi.success(pendingSuccessMessage);
    setPendingSuccessMessage(null);
  }, [loadState.status, messageApi, pendingSuccessMessage]);

  const filteredItems = useMemo(() => {
    if (loadState.status !== 'ready') return [];
    const normalizedKeyword = keyword.trim().toLowerCase();
    return loadState.data.items.filter(item => {
      const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
      const matchesKeyword = !normalizedKeyword || [
        item.title,
        item.department,
        item.location,
        item.jobBackground,
        item.jobResponsibilities,
        item.candidateRequirements,
        item.preferredQualifications,
        item.publicNotes,
      ].some(value => value?.toLowerCase().includes(normalizedKeyword));
      return matchesStatus && matchesKeyword;
    });
  }, [keyword, loadState, statusFilter]);

  const openForm = (job: RecruitmentJob | null) => {
    setSelectedJob(job);
    setOperationError(null);
    form.resetFields();
    form.setFieldsValue(job ? formValuesFromJob(job) : { title: '' });
    setDirty(false);
    setFormOpen(true);
  };

  const closeFormNow = () => {
    setFormOpen(false);
    setSelectedJob(null);
    setOperationError(null);
    setDirty(false);
  };

  const requestCloseForm = () => {
    if (!dirty && !form.isFieldsTouched()) {
      closeFormNow();
      return;
    }
    modalApi.confirm({
      title: '放弃未保存的修改？',
      content: '关闭后，本次尚未保存的表单内容会丢失。',
      okText: '放弃修改',
      cancelText: '继续填写',
      okButtonProps: { danger: true },
      onOk: closeFormNow,
    });
  };

  const showOperationError = (error: unknown, jobToEdit?: RecruitmentJob) => {
    const apiError = getRecruitmentJobApiError(error);
    if (apiError.code !== 'JOB_OPEN_VALIDATION_FAILED') {
      setOperationError(apiError.message);
      return;
    }

    if (jobToEdit && (!formOpen || selectedJob?.id !== jobToEdit.id)) openForm(jobToEdit);
    setOperationError(apiError.message);
    const formFields = apiError.fields
      .map(field => backendFieldToFormField[field])
      .filter((field): field is keyof JobFormValues => Boolean(field));
    window.setTimeout(() => {
      form.setFields(formFields.map(name => ({ name, errors: ['开放岗位前必须填写此项'] })));
      if (formFields[0]) form.scrollToField(formFields[0], { block: 'center' });
    });
  };

  const refreshAfterSuccess = async (successMessage: string) => {
    closeFormNow();
    setPendingSuccessMessage(successMessage);
    await loadJobs();
  };

  const saveNewJob = async (status: 'draft' | 'open') => {
    setOperationPending(true);
    setOperationError(null);
    try {
      const values = await form.validateFields();
      await createRecruitmentJob({ ...buildJobInput(values), status });
      await refreshAfterSuccess(status === 'open' ? '岗位已创建并开放' : '岗位草稿已保存');
    } catch (error) {
      if (!(error && typeof error === 'object' && 'errorFields' in error)) showOperationError(error);
    } finally {
      setOperationPending(false);
    }
  };

  const saveExistingJob = async () => {
    if (!selectedJob) return;
    setOperationPending(true);
    setOperationError(null);
    try {
      const values = await form.validateFields();
      await updateRecruitmentJob(selectedJob.id, buildJobInput(values));
      await refreshAfterSuccess('岗位修改已保存');
    } catch (error) {
      if (!(error && typeof error === 'object' && 'errorFields' in error)) showOperationError(error);
    } finally {
      setOperationPending(false);
    }
  };

  const runStatusAction = async (job: RecruitmentJob, action: 'open' | 'close' | 'reopen') => {
    setOperationPending(true);
    setOperationError(null);
    try {
      if (action === 'open') await openRecruitmentJob(job.id);
      if (action === 'close') await closeRecruitmentJob(job.id);
      if (action === 'reopen') await reopenRecruitmentJob(job.id);
      await refreshAfterSuccess(action === 'close' ? '岗位已关闭' : '岗位已开放');
    } catch (error) {
      showOperationError(error, job);
    } finally {
      setOperationPending(false);
    }
  };

  const confirmStatusAction = (job: RecruitmentJob) => {
    const action = job.status === 'draft' ? 'open' : job.status === 'open' ? 'close' : 'reopen';
    const actionLabel = action === 'open' ? '开放岗位' : action === 'close' ? '关闭岗位' : '重新开放';
    modalApi.confirm({
      title: `确认${actionLabel}？`,
      content: action === 'close'
        ? '关闭后，新申请不能再选择该岗位；此操作不会删除历史候选人和初筛结果。'
        : '开放前会检查岗位标准是否填写完整。',
      okText: actionLabel,
      cancelText: '取消',
      onOk: () => runStatusAction(job, action),
    });
  };

  const confirmDelete = (job: RecruitmentJob) => {
    modalApi.confirm({
      title: '确认删除岗位？',
      content: '只能删除没有候选人、申请或初筛记录的草稿或已关闭岗位。删除后无法恢复。',
      okText: '删除岗位',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        setOperationPending(true);
        try {
          await deleteRecruitmentJob(job.id);
          await refreshAfterSuccess('岗位已删除');
        } catch (error) {
          const apiError = getRecruitmentJobApiError(error);
          setOperationError(apiError.code === 'JOB_HAS_REFERENCES'
            ? `岗位已有历史业务数据，不能删除${formatReferenceCounts(apiError.references)}`
            : apiError.message);
        } finally {
          setOperationPending(false);
        }
      },
    });
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="岗位列表加载中" className="recruitment-main">
        <section className="recruitment-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="recruitment-stat-grid recruitment-job-stat-grid">
          {[0, 1, 2, 3, 4].map(item => <article className="recruitment-stat-card" key={item}><Skeleton active paragraph={false} /></article>)}
        </section>
        <section className="recruitment-state-panel"><Skeleton active paragraph={{ rows: 6 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="recruitment-main">
        <section className="recruitment-page-heading">
          <div><span className="recruitment-section-kicker">新版岗位库 · 数据来源 /api/v2</span><h2>岗位管理</h2><p>创建并维护可供招聘流程使用的结构化岗位标准。</p></div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadJobs()}>重新加载</Button>}
          className="recruitment-dashboard-alert recruitment-section-gap"
          description={`请确认 FastAPI 已启动，且新版岗位与候选人接口可访问。技术信息：${loadState.message}`}
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
    { label: '草稿', value: data.draftCount, note: '可以继续补充和编辑', icon: <FileTextOutlined />, tone: 'orange' },
    { label: '开放岗位', value: data.openCount, note: '可供后续申请与初筛选择', icon: <CheckCircleOutlined />, tone: 'green' },
    { label: '已关闭', value: data.closedCount, note: '保留历史数据，可重新开放', icon: <StopOutlined />, tone: 'orange' },
    { label: '关联候选人', value: data.linkedCandidateCount, note: '当前兼容关联统计', icon: <TeamOutlined />, tone: 'blue' },
  ];

  return (
    <main className="recruitment-main">
      {messageContext}
      {modalContext}
      <section className="recruitment-page-heading">
        <div>
          <span className="recruitment-section-kicker">新版岗位库 · 数据来源 /api/v2</span>
          <h2>岗位管理</h2>
          <p>HR 可创建、编辑、开放、关闭和重新开放岗位；岗位状态由独立操作控制。</p>
        </div>
        <Button icon={<PlusOutlined />} onClick={() => openForm(null)} type="primary">新增岗位</Button>
      </section>

      <section aria-label="岗位统计" className="recruitment-stat-grid recruitment-job-stat-grid">
        {stats.map(stat => (
          <article className="recruitment-stat-card" key={stat.label}>
            <div className={`recruitment-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="recruitment-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      {operationError && (
        <Alert
          className="recruitment-section-gap"
          closable
          message="岗位操作没有完成"
          description={operationError}
          onClose={() => setOperationError(null)}
          showIcon
          type="error"
        />
      )}

      <section className="recruitment-panel recruitment-job-list-panel">
        <div className="recruitment-job-toolbar">
          <div><h3>岗位列表</h3><p>共 {data.total} 个岗位；修改状态不会删除历史招聘记录</p></div>
          <div className="recruitment-job-filter-controls">
            <Input
              allowClear aria-label="搜索岗位" onChange={event => setKeyword(event.target.value)}
              placeholder="搜索岗位、部门、地点或五段式 JD" prefix={<SearchOutlined />} value={keyword}
            />
            <Select aria-label="按岗位状态筛选" onChange={setStatusFilter} options={statusOptions} value={statusFilter} />
            <Button aria-label="刷新岗位列表" icon={<ReloadOutlined />} onClick={() => void loadJobs()} />
          </div>
        </div>

        {data.total === 0 ? (
          <Empty
            className="recruitment-panel-empty recruitment-job-empty"
            description={<div className="recruitment-empty-copy"><strong>新版岗位库目前没有岗位</strong><span>先创建草稿，补充完整后再开放招聘。</span></div>}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button icon={<PlusOutlined />} onClick={() => openForm(null)}>新增岗位</Button>
          </Empty>
        ) : filteredItems.length === 0 ? (
          <Empty className="recruitment-panel-empty recruitment-job-empty" description="没有符合当前条件的岗位" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button onClick={() => { setKeyword(''); setStatusFilter('all'); }}>清除筛选</Button>
          </Empty>
        ) : (
          <div aria-label="新版岗位列表" className="recruitment-table" role="table">
            <div className="recruitment-table-head recruitment-job-table-columns" role="row">
              <span>岗位</span><span>部门 / 地点</span><span>岗位职责</span><span>人数</span><span>状态</span><span>更新时间</span><span>操作</span>
            </div>
            {filteredItems.map(item => {
              const statusMeta = getStatusMeta(item.status);
              const actionLabel = item.status === 'draft' ? '开放岗位' : item.status === 'open' ? '关闭岗位' : '重新开放';
              return (
                <div className="recruitment-table-row recruitment-job-table-columns" key={item.id} role="row">
                  <div className="recruitment-job-title-cell">
                    <span className="recruitment-job-mark"><SolutionOutlined /></span>
                    <div><strong>{item.title}</strong><span>岗位 #{item.id}</span></div>
                  </div>
                  <div className="recruitment-job-location-cell"><strong>{item.department || '部门未填写'}</strong><span>{item.location || '地点未填写'}</span></div>
                  <div className="recruitment-job-requirement-cell">
                    <strong>{item.jobResponsibilities || '岗位职责未填写'}</strong>
                    <div><span>{item.candidateRequirements || '任职要求未填写'}</span></div>
                  </div>
                  <div className="recruitment-job-candidate-count"><strong>{item.headcount ?? '—'}</strong><span>招聘 / {item.candidateCount} 候选</span></div>
                  <div><Tag bordered={false} className={`recruitment-status-tag is-${statusMeta.tone}`}>{statusMeta.label}</Tag></div>
                  <span className="recruitment-time-cell">{formatDateTime(item.updatedAt)}</span>
                  <div className="recruitment-job-action-cell">
                    <Button
                      icon={<FundProjectionScreenOutlined />}
                      onClick={event => {
                        planTriggerRef.current = event.currentTarget;
                        setPlanJob(item);
                      }}
                      size="small"
                    >
                      评价计划
                    </Button>
                    <Button icon={<EditOutlined />} onClick={() => openForm(item)} size="small">编辑</Button>
                    <Button disabled={operationPending} onClick={() => confirmStatusAction(item)} size="small">{actionLabel}</Button>
                    {item.status !== 'open' && (
                      <Button danger disabled={operationPending} icon={<DeleteOutlined />} onClick={() => confirmDelete(item)} size="small" aria-label={`删除岗位 ${item.title}`} />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <JobEvaluationPlanDrawer
        job={planJob}
        onClose={() => {
          planTriggerRef.current?.focus();
          setPlanJob(null);
        }}
        open={planJob !== null}
      />

      <Drawer
        className="recruitment-job-form-drawer"
        closable={!operationPending}
        destroyOnClose
        keyboard={!operationPending}
        maskClosable={!operationPending}
        onClose={requestCloseForm}
        open={formOpen}
        title={selectedJob ? `编辑岗位 · #${selectedJob.id}` : '新增岗位'}
        width="min(720px, 100vw)"
      >
        <Alert
          description={selectedJob
            ? '保存修改不会自动改变岗位状态。开放中的岗位修改后仍需满足全部开放条件。'
            : '草稿只要求岗位名称；选择“保存并开放”时会检查所有开放必填项。'}
          message={selectedJob ? `当前状态：${getStatusMeta(selectedJob.status).label}` : '先保存草稿也可以'}
          showIcon
          type="info"
        />
        {operationError && <Alert className="recruitment-job-form-error" message={operationError} showIcon type="error" />}
        <Form
          className="recruitment-job-form"
          form={form}
          layout="vertical"
          onValuesChange={() => setDirty(true)}
        >
          <section className="recruitment-job-form-section">
            <h3>基础信息</h3>
            <Form.Item label="岗位名称" name="title" rules={[{ required: true, whitespace: true, message: '请填写岗位名称' }, { max: 200, message: '岗位名称不能超过 200 个字符' }]}>
              <Input placeholder="例如：高级后端工程师" />
            </Form.Item>
            <div className="recruitment-job-form-grid">
              <Form.Item label="所属部门" name="department" rules={[{ max: 100 }]}><Input placeholder="例如：技术部" /></Form.Item>
              <Form.Item label="工作地点" name="location" rules={[{ max: 100 }]}><Input placeholder="例如：上海 / 远程" /></Form.Item>
              <Form.Item label="用工类型" name="employmentType"><Select allowClear options={employmentOptions} placeholder="请选择" /></Form.Item>
              <Form.Item label="招聘人数" name="headcount"><InputNumber min={1} max={999} precision={0} placeholder="例如：2" /></Form.Item>
            </div>
            <Form.Item label="岗位背景" name="jobBackground" rules={[{ max: 5000, message: '岗位背景不能超过 5000 个字符' }]} extra="选填。介绍招聘背景、团队使命或岗位目标。">
              <Input.TextArea autoSize={{ minRows: 6, maxRows: 14 }} placeholder={'例如：\n为支持 AI 招聘平台升级，团队计划新增该岗位。'} />
            </Form.Item>
          </section>

          <section className="recruitment-job-form-section">
            <h3>职责与要求</h3>
            <Form.Item label="岗位职责" name="jobResponsibilities" rules={[{ max: 10000, message: '岗位职责不能超过 10000 个字符' }]} extra="开放岗位时必填。可保留换行、编号和项目符号。">
              <Input.TextArea autoSize={{ minRows: 6, maxRows: 16 }} placeholder={'例如：\n1. 负责 AI 应用设计与交付\n2. 与产品和后端协作推进上线'} />
            </Form.Item>
            <Form.Item label="任职要求" name="candidateRequirements" rules={[{ max: 10000, message: '任职要求不能超过 10000 个字符' }]} extra="开放岗位时必填。请直接写明必要能力、经验或其他条件。">
              <Input.TextArea autoSize={{ minRows: 6, maxRows: 16 }} placeholder={'例如：\n- 具备后端开发经验\n- 熟悉 PostgreSQL'} />
            </Form.Item>
          </section>

          <section className="recruitment-job-form-section">
            <h3>加分与补充</h3>
            <Form.Item label="加分项" name="preferredQualifications" rules={[{ max: 5000, message: '加分项不能超过 5000 个字符' }]} extra="选填。填写优先考虑但不是开放岗位硬性门槛的条件。">
              <Input.TextArea autoSize={{ minRows: 6, maxRows: 14 }} placeholder={'例如：\n- 有 RAG 项目经验\n- 有招聘系统建设经验'} />
            </Form.Item>
            <Form.Item label="备注" name="publicNotes" rules={[{ max: 5000, message: '备注不能超过 5000 个字符' }]} extra="选填。候选人可见，请勿填写内部招聘信息；该字段不参与 AI 评价。">
              <Input.TextArea autoSize={{ minRows: 6, maxRows: 14 }} placeholder="例如：候选人可提前准备项目介绍" />
            </Form.Item>
          </section>
        </Form>

        <div className="recruitment-job-form-footer">
          <Button disabled={operationPending} onClick={requestCloseForm}>取消</Button>
          {selectedJob ? (
            <>
              {selectedJob.status !== 'open' && (
                <Button danger disabled={operationPending} icon={<DeleteOutlined />} onClick={() => confirmDelete(selectedJob)}>删除岗位</Button>
              )}
              <Button disabled={operationPending || dirty || form.isFieldsTouched()} onClick={() => confirmStatusAction(selectedJob)}>
                {selectedJob.status === 'draft' ? '开放岗位' : selectedJob.status === 'open' ? '关闭岗位' : '重新开放'}
              </Button>
              <Button loading={operationPending} onClick={() => void saveExistingJob()} type="primary">保存修改</Button>
            </>
          ) : (
            <>
              <Button loading={operationPending} onClick={() => void saveNewJob('draft')}>保存草稿</Button>
              <Button loading={operationPending} onClick={() => void saveNewJob('open')} type="primary">保存并开放</Button>
            </>
          )}
        </div>
      </Drawer>
    </main>
  );
};

export default RecruitmentJobList;
