import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FileSearchOutlined, FilterOutlined, PlusOutlined, ReloadOutlined, SearchOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, Button, Empty, Form, Input, Modal, Pagination, Radio, Select, Skeleton, Upload, message } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ApplicationEvidenceTable from './ApplicationEvidenceTable';
import ApplicationScreeningDrawer from './ApplicationScreeningDrawer';
import { backupStage7Application, getStage7ApplicationApiError, intakeStage7Application, passStage7Application, rejectStage7Application, undoStage7ApplicationRejection } from './services/applications';
import { getRecruitmentJobs, type RecruitmentJob } from './services/jobs';
import { getPublicApplicationSubmission, type PublicApplicationWorkbenchSummary } from './services/publicApplicationWorkbench';
import { getScreeningCenterError, listScreeningCenterApplications, type ScreeningCenterDecision, type ScreeningCenterItem, type ScreeningCenterLifecycle, type ScreeningCenterPage, type ScreeningCenterProcessingPool, type ScreeningCenterSort, type ScreeningCenterSource, type ScreeningCenterStage } from './services/screeningCenter';
import { getAIScreeningApiError, reassessJobApplications } from './services/aiScreening';
import { abandonRecruitmentResume, extractRecruitmentResumeText, getRecruitmentResumes, uploadRecruitmentResume, type RecruitmentResumeDetail, type ResumeListSnapshot } from './services/resumes';
import { buildStage7ScreeningIntakeInput, getStage7ScreeningIntakeErrorMessage, isStage7IntakeResumeFileSupported } from './screeningIntakeAction';
import { buildStage7DecisionSubmission, getStage7DecisionErrorMessage, getStage7DecisionKinds, STAGE7_BACKUP_REASON_OPTIONS, STAGE7_REJECT_REASON_OPTIONS, STAGE7_REVERSAL_REASON_OPTIONS, type Stage7DecisionKind } from './screeningDecisionAction';

type LoadState = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: ScreeningCenterPage };
type ScreeningDecisionFilter = Exclude<ScreeningCenterDecision, 'passed'> | 'all';
type ScreeningStageFilter = Extract<ScreeningCenterStage, 'applied' | 'hr_review' | 'backup' | 'rejected'> | 'all';
type FilterState = {
  keyword: string;
  jobId: number | 'all';
  source: ScreeningCenterSource | 'all';
  decision: ScreeningDecisionFilter;
  stage: ScreeningStageFilter;
  lifecycle: ScreeningCenterLifecycle | 'all';
  pool: ScreeningCenterProcessingPool;
  processingStatus: string | 'all';
  displayLabel: string | 'all';
  sort: ScreeningCenterSort;
};
type IntakeValues = { name: string; phone: string; email: string; jobId: number; resumeId?: number };
type ResumeLoadState = { status: 'idle' | 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: ResumeListSnapshot };

const INITIAL_FILTERS: FilterState = {
  keyword: '', jobId: 'all', source: 'all', decision: 'all', stage: 'all', lifecycle: 'all',
  pool: 'all', processingStatus: 'all', displayLabel: 'all', sort: 'applied_desc',
};
const SOURCE_LABELS: Record<ScreeningCenterSource, string> = { hr_direct: 'HR 直接录入', hr_screening: 'HR 待审核录入', public_apply: '公开投递' };
const DECISION_LABELS: Record<ScreeningDecisionFilter, string> = { all: '全部初筛状态', pending: 'HR 待决策', backup: '初筛备选', rejected: '初筛淘汰' };
const STAGE_OPTIONS: Array<{ value: ScreeningStageFilter; label: string }> = [
  { value: 'all', label: '全部申请阶段' },
  { value: 'applied', label: '已申请' },
  { value: 'hr_review', label: 'HR 初筛' },
  { value: 'backup', label: '初筛备选' },
  { value: 'rejected', label: '初筛淘汰' },
];
const LIFECYCLE_LABELS: Record<ScreeningCenterLifecycle, string> = { active: '处理中', ended: '已结束', voided: '已作废' };
const decisionAdapter = (item: ScreeningCenterItem) => ({ application: { lifecycleStatus: item.lifecycleStatus, recruitmentStage: item.recruitmentStage, hrDecision: item.hrDecision } });

const RecruitmentScreeningCenter: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLinkedApplicationId = Number(searchParams.get('application_id'));
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [jobs, setJobs] = useState<RecruitmentJob[]>([]);
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [keywordInput, setKeywordInput] = useState('');
  const [page, setPage] = useState(1);
  const [selectedItem, setSelectedItem] = useState<ScreeningCenterItem | null>(null);
  const [publicSubmission, setPublicSubmission] = useState<PublicApplicationWorkbenchSummary | null>(null);
  const [decisionItem, setDecisionItem] = useState<ScreeningCenterItem | null>(null);
  const [decisionKind, setDecisionKind] = useState<Stage7DecisionKind | null>(null);
  const [reasonCode, setReasonCode] = useState<string | null>(null);
  const [reasonDetail, setReasonDetail] = useState('');
  const [decisionPending, setDecisionPending] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [selectedApplicationIds, setSelectedApplicationIds] = useState<number[]>([]);
  const [batchPending, setBatchPending] = useState(false);
  const [intakeOpen, setIntakeOpen] = useState(false);
  const [intakeForm] = Form.useForm<IntakeValues>();
  const [resumeMode, setResumeMode] = useState<'upload' | 'existing'>('upload');
  const [resumeLoad, setResumeLoad] = useState<ResumeLoadState>({ status: 'idle' });
  const [intakeFile, setIntakeFile] = useState<File | null>(null);
  const [preparedResume, setPreparedResume] = useState<RecruitmentResumeDetail | null>(null);
  const [intakePending, setIntakePending] = useState(false);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [modal, modalContextHolder] = Modal.useModal();

  const load = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      const data = await listScreeningCenterApplications({
        view: 'screening',
        page,
        pageSize: 30,
        applicationId: Number.isInteger(deepLinkedApplicationId) && deepLinkedApplicationId > 0 ? deepLinkedApplicationId : undefined,
        keyword: filters.keyword || undefined,
        jobId: filters.jobId === 'all' ? undefined : filters.jobId,
        source: filters.source === 'all' ? undefined : filters.source,
        hrDecision: filters.decision === 'all' ? undefined : filters.decision,
        stage: filters.stage === 'all' ? undefined : filters.stage,
        lifecycle: filters.lifecycle === 'all' ? undefined : filters.lifecycle,
        processingPool: filters.pool,
        processingStatus: filters.processingStatus === 'all' ? undefined : filters.processingStatus,
        displayLabel: filters.displayLabel === 'all' ? undefined : filters.displayLabel,
        sort: filters.sort,
      });
      setLoadState({ status: 'ready', data });
      setSelectedApplicationIds(value => value.filter(id => data.items.some(item => item.applicationId === id)));
      if (Number.isInteger(deepLinkedApplicationId) && deepLinkedApplicationId > 0 && data.items[0]) setSelectedItem(data.items[0]);
    } catch (error) {
      setLoadState({ status: 'error', message: getScreeningCenterError(error) });
    }
  }, [deepLinkedApplicationId, filters, page]);

  const refreshApplicationSummary = useCallback(() => {
    void load();
  }, [load]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void getRecruitmentJobs().then(value => setJobs(value.items)).catch(() => setJobs([])); }, []);
  useEffect(() => {
    if (!selectedItem?.submissionId) { setPublicSubmission(null); return undefined; }
    let cancelled = false;
    void getPublicApplicationSubmission(selectedItem.submissionId)
      .then(value => { if (!cancelled) setPublicSubmission(value); })
      .catch(() => { if (!cancelled) setPublicSubmission(null); });
    return () => { cancelled = true; };
  }, [selectedItem?.submissionId]);

  const openDetail = (item: ScreeningCenterItem) => {
    setSelectedItem(item);
    setPublicSubmission(null);
    setSearchParams({ application_id: String(item.applicationId) }, { replace: true });
  };
  const closeDetail = () => { setSelectedItem(null); setPublicSubmission(null); setSearchParams({}, { replace: true }); };
  const applySearch = () => { setPage(1); setFilters(value => ({ ...value, keyword: keywordInput.trim() })); };
  const clearFilters = () => { setKeywordInput(''); setFilters(INITIAL_FILTERS); setPage(1); };

  const openIntake = () => {
    intakeForm.resetFields(); setResumeMode('upload'); setIntakeFile(null); setPreparedResume(null); setIntakeError(null); setIntakeOpen(true);
    setResumeLoad({ status: 'loading' });
    void getRecruitmentResumes().then(data => setResumeLoad({ status: 'ready', data })).catch(() => setResumeLoad({ status: 'error', message: '无法读取现有简历。' }));
  };
  const closeIntake = async () => {
    if (intakePending) return;
    if (preparedResume) { try { await abandonRecruitmentResume(preparedResume.id); } catch { /* 留给清理任务 */ } }
    setIntakeOpen(false); setPreparedResume(null); setIntakeFile(null);
  };
  const submitIntake = async () => {
    if (intakePending) return;
    let values: IntakeValues;
    try { values = await intakeForm.validateFields(); } catch { return; }
    setIntakePending(true); setIntakeError(null);
    let resume = preparedResume;
    try {
      if (resumeMode === 'upload') {
        if (!resume && !intakeFile) throw new Error('请先选择需要上传的简历。');
        if (!resume && intakeFile) { resume = await uploadRecruitmentResume(intakeFile); setPreparedResume(resume); }
        if (resume && resume.parseStatus !== 'parsed') { resume = await extractRecruitmentResumeText(resume.id); setPreparedResume(resume); }
      }
      const built = buildStage7ScreeningIntakeInput({ name: values.name, phone: values.phone, email: values.email, jobId: values.jobId, resumeId: resumeMode === 'existing' ? values.resumeId ?? null : resume?.id ?? null });
      if (!built.valid) { setIntakeError(built.message); return; }
      const outcome = await intakeStage7Application(built.input);
      setPreparedResume(null); setIntakeFile(null); setIntakeOpen(false);
      message.success(outcome.existingApplicationReused ? `已找到现有 Application #${outcome.application.id}` : `Application #${outcome.application.id} 已进入初筛队列`);
      await load();
    } catch (error) {
      const parsed = getStage7ApplicationApiError(error);
      setIntakeError(getStage7ScreeningIntakeErrorMessage(parsed.code, error instanceof Error ? error.message : parsed.message, parsed.candidateIds));
    } finally { setIntakePending(false); }
  };

  const openDecision = (item: ScreeningCenterItem) => {
    const kinds = getStage7DecisionKinds(decisionAdapter(item));
    setDecisionItem(item); setDecisionKind(kinds.length === 1 ? kinds[0] : null); setReasonCode(null); setReasonDetail(''); setDecisionError(null);
  };
  const submitDecision = async () => {
    if (!decisionItem || decisionPending) return;
    const built = buildStage7DecisionSubmission(decisionAdapter(decisionItem), decisionKind, reasonCode, reasonDetail);
    if (!built.valid) { setDecisionError(built.message); return; }
    setDecisionPending(true);
    try {
      const { action, input } = built.submission;
      if (action === 'pass') await passStage7Application(decisionItem.applicationId, input);
      else if (action === 'backup') await backupStage7Application(decisionItem.applicationId, input);
      else if (action === 'reject') await rejectStage7Application(decisionItem.applicationId, input);
      else await undoStage7ApplicationRejection(decisionItem.applicationId, input);
      message.success(action === 'pass' ? 'HR 已确认通过，该 Application 已进入候选人。' : 'HR 初筛决定已保存。');
      setDecisionItem(null);
      await load();
    } catch (error) {
      const parsed = getStage7ApplicationApiError(error);
      setDecisionError(getStage7DecisionErrorMessage(parsed.code, parsed.message));
    } finally { setDecisionPending(false); }
  };

  const items = loadState.status === 'ready' ? loadState.data.items : [];
  const selectedItems = useMemo(() => items.filter(item => selectedApplicationIds.includes(item.applicationId)), [items, selectedApplicationIds]);
  const toggleBatch = (item: ScreeningCenterItem, checked: boolean) => {
    if (!checked) { setSelectedApplicationIds(value => value.filter(id => id !== item.applicationId)); return; }
    if (selectedItems.length >= 5 || (selectedItems[0] && selectedItems[0].jobId !== item.jobId)) {
      message.warning('批量重新评估最多选择 5 份申请，且必须属于同一岗位。'); return;
    }
    setSelectedApplicationIds(value => [...value, item.applicationId]);
  };
  const submitBatch = () => {
    if (!selectedItems.length) return;
    modal.confirm({
      title: `确认重新评估 ${selectedItems.length} 人？`,
      content: '旧成功报告会保留到新报告成功，不会自动改变 HR 决策。',
      okText: '批量重新评估', cancelText: '取消',
      onOk: async () => {
        setBatchPending(true);
        try {
          const result = await reassessJobApplications(selectedItems[0].jobId, selectedApplicationIds);
          setSelectedApplicationIds([]);
          if (result.failedCount > 0) message.warning(`部分任务未创建：${result.failures.map(item => `#${item.applicationId} ${item.errorMessage}`).join('；')}`);
          else message.success('重新评估任务已进入队列。');
          await load();
        } catch (error) { message.error(getAIScreeningApiError(error).message); }
        finally { setBatchPending(false); }
      },
    });
  };
  const reasonOptions: Array<{ value: string; label: string }> = decisionKind === 'backup' ? STAGE7_BACKUP_REASON_OPTIONS : decisionKind === 'reject' ? STAGE7_REJECT_REASON_OPTIONS : decisionKind === 'undo_rejection' ? STAGE7_REVERSAL_REASON_OPTIONS : [];
  const hasFilters = JSON.stringify(filters) !== JSON.stringify(INITIAL_FILTERS);

  return (
    <main className="recruitment-main recruitment-screening-page recruitment-screening-center-v2">
      {modalContextHolder}
      <section className="recruitment-page-heading">
        <div><span className="recruitment-section-kicker">投递 → AI 报告 → HR 初筛</span><h2>AI 初筛中心</h2><p>只处理尚未通过初筛的申请；HR 确认通过后自动进入候选人。</p></div>
        <div><Button onClick={() => navigate('/app/candidates/new')}>HR 直通新增</Button><Button type="primary" icon={<PlusOutlined />} onClick={openIntake}>录入待筛申请</Button></div>
      </section>
      <section aria-label="AI 与 HR 的职责边界" className="recruitment-screening-boundary is-compact">
        <div className="recruitment-screening-flow-step"><span>01</span><strong>接收投递</strong><small>保存一份岗位申请</small></div>
        <i />
        <div className="recruitment-screening-flow-step"><span>02</span><strong>AI 给出证据</strong><small>不自动通过或淘汰</small></div>
        <i />
        <div className="recruitment-screening-flow-step"><span>03</span><strong>HR 明确决定</strong><small>通过后进入候选人</small></div>
      </section>
      <section className="recruitment-panel recruitment-screening-workspace">
        <div className="recruitment-screening-toolbar is-table-toolbar">
          <div className="recruitment-screening-toolbar-heading"><h3>初筛申请列表</h3><p>{loadState.status === 'ready' ? `共 ${loadState.data.total} 份` : '正在读取申请'}</p></div>
          <div className="recruitment-screening-quick-filters">
            <Input allowClear aria-label="搜索初筛申请" onChange={event => setKeywordInput(event.target.value)} onPressEnter={applySearch} placeholder="姓名 / 联系方式 / 岗位 / 申请编号" prefix={<SearchOutlined />} value={keywordInput} />
            <Select aria-label="按岗位筛选申请" value={filters.jobId} onChange={jobId => { setPage(1); setFilters(value => ({ ...value, jobId })); }} options={[{ value: 'all', label: '全部岗位' }, ...jobs.map(job => ({ value: job.id, label: job.title }))]} />
            <Select aria-label="按初筛状态筛选" value={filters.decision} onChange={decision => { setPage(1); setFilters(value => ({ ...value, decision })); }} options={Object.entries(DECISION_LABELS).map(([value, label]) => ({ value, label }))} />
            <Button icon={<SearchOutlined />} onClick={applySearch} type="primary">搜索</Button>
            <Button aria-label="刷新初筛队列" icon={<ReloadOutlined />} onClick={() => void load()} />
          </div>
        </div>
        <details className="recruitment-screening-advanced-filters">
          <summary><FilterOutlined /> 更多筛选</summary>
          <div className="recruitment-screening-filter-controls">
            <Select aria-label="按申请来源筛选" value={filters.source} onChange={source => { setPage(1); setFilters(value => ({ ...value, source })); }} options={[{ value: 'all', label: '全部来源' }, ...Object.entries(SOURCE_LABELS).map(([value, label]) => ({ value, label }))]} />
            <Select aria-label="按申请阶段筛选" value={filters.stage} onChange={stage => { setPage(1); setFilters(value => ({ ...value, stage })); }} options={STAGE_OPTIONS} />
            <Select aria-label="按流程状态筛选" value={filters.lifecycle} onChange={lifecycle => { setPage(1); setFilters(value => ({ ...value, lifecycle })); }} options={[{ value: 'all', label: '全部流程状态' }, ...Object.entries(LIFECYCLE_LABELS).map(([value, label]) => ({ value, label }))]} />
            <Select aria-label="按处理池筛选" value={filters.pool} onChange={pool => { setPage(1); setFilters(value => ({ ...value, pool })); }} options={[{ value: 'all', label: '全部处理池' }, { value: 'internal', label: '内部录入' }, { value: 'normal', label: '公开投递 · 正常' }, { value: 'exception', label: '公开投递 · 需人工处理' }]} />
            <Select aria-label="按自动处理状态筛选" value={filters.processingStatus} onChange={processingStatus => { setPage(1); setFilters(value => ({ ...value, processingStatus })); }} options={[{ value: 'all', label: '全部自动处理状态' }, { value: 'queued', label: '等待处理' }, { value: 'running', label: '正在处理' }, { value: 'waiting_screening', label: '等待初筛' }, { value: 'succeeded', label: '自动处理完成' }, { value: 'succeeded_with_warnings', label: '完成，需留意' }, { value: 'failed', label: '处理失败' }, { value: 'paused', label: '等待 HR 处理' }]} />
            <Select aria-label="按 AI 标签筛选" value={filters.displayLabel} onChange={displayLabel => { setPage(1); setFilters(value => ({ ...value, displayLabel })); }} options={[{ value: 'all', label: '全部 AI 标签' }, ...['关联较弱', '存在明显差距', '部分匹配', '整体较匹配', '高度匹配'].map(value => ({ value, label: value }))]} />
            <Select aria-label="排序方式" value={filters.sort} onChange={sort => setFilters(value => ({ ...value, sort }))} options={[{ value: 'applied_desc', label: '最近申请' }, { value: 'updated_desc', label: '最近业务更新' }, { value: 'score_desc', label: 'AI 分数从高到低' }, { value: 'score_asc', label: 'AI 分数从低到高' }]} />
            {hasFilters && <Button onClick={clearFilters}>清除全部筛选</Button>}
          </div>
        </details>
        {selectedApplicationIds.length > 0 && <div className="recruitment-screening-batchbar"><span>已选同一岗位 {selectedApplicationIds.length} 份申请</span><Button loading={batchPending} onClick={submitBatch} type="primary">批量重新评估</Button></div>}
        {loadState.status === 'loading' && <div className="recruitment-screening-loading"><Skeleton active paragraph={{ rows: 10 }} /></div>}
        {loadState.status === 'error' && <Alert className="recruitment-screening-inline-alert" type="error" showIcon message={loadState.message} action={<Button onClick={() => void load()}>重试</Button>} />}
        {loadState.status === 'ready' && items.length === 0 && <Empty className="recruitment-screening-empty" image={<FileSearchOutlined />} description="当前没有符合条件的初筛申请" />}
        {loadState.status === 'ready' && items.length > 0 && <ApplicationEvidenceTable items={items} mode="screening" onDecision={openDecision} onOpen={openDetail} onToggleSelection={toggleBatch} selectedApplicationIds={selectedApplicationIds} />}
        {loadState.status === 'ready' && loadState.data.total > loadState.data.pageSize && <Pagination className="recruitment-application-pagination" current={loadState.data.page} pageSize={loadState.data.pageSize} total={loadState.data.total} showSizeChanger={false} onChange={setPage} />}
      </section>
      <ApplicationScreeningDrawer applicationId={selectedItem?.applicationId ?? null} candidateName={selectedItem?.candidateName ?? ''} currentResumeId={selectedItem?.resumeId ?? null} initialState={null} jobId={selectedItem?.jobId ?? null} jobStatus={selectedItem?.jobStatus ?? null} jobTitle={selectedItem?.jobTitle ?? ''} open={selectedItem !== null} onClose={closeDetail} onStateChange={refreshApplicationSummary} onPipelineChange={load} onPublicSubmissionChange={setPublicSubmission} onCurrentResumeChange={refreshApplicationSummary} publicSubmission={publicSubmission} summary={selectedItem} workspace="screening" />
      <Modal title="录入待筛申请" open={intakeOpen} onCancel={() => void closeIntake()} onOk={() => void submitIntake()} confirmLoading={intakePending} okText="保存到初筛队列" cancelText="取消">
        {intakeError && <Alert type="error" showIcon message={intakeError} />}
        <Form form={intakeForm} layout="vertical"><Form.Item name="name" label="候选人姓名" rules={[{ required: true }]}><Input /></Form.Item><Form.Item name="phone" label="手机号" rules={[{ required: true }]}><Input /></Form.Item><Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}><Input /></Form.Item><Form.Item name="jobId" label="开放岗位" rules={[{ required: true }]}><Select options={jobs.filter(job => job.status === 'open').map(job => ({ value: job.id, label: job.title }))} /></Form.Item><Form.Item label="简历来源"><Radio.Group value={resumeMode} onChange={event => setResumeMode(event.target.value)}><Radio value="upload">上传新简历</Radio><Radio value="existing">选择现有简历</Radio></Radio.Group></Form.Item>
          {resumeMode === 'upload' ? <Upload.Dragger accept=".pdf,.docx,.txt" maxCount={1} beforeUpload={file => { if (!isStage7IntakeResumeFileSupported(file.name)) { message.error('只支持 PDF、DOCX 或 TXT 简历。'); return Upload.LIST_IGNORE; } setIntakeFile(file); return false; }} onRemove={() => { setIntakeFile(null); return true; }}><p><UploadOutlined /> 点击或拖入简历</p></Upload.Dragger> : <Form.Item name="resumeId" label="现有已解析简历" rules={[{ required: true }]}><Select loading={resumeLoad.status === 'loading'} options={resumeLoad.status === 'ready' ? resumeLoad.data.items.filter(item => item.parseStatus === 'parsed').map(item => ({ value: item.id, label: `#${item.id} ${item.filename}` })) : []} /></Form.Item>}
        </Form>
      </Modal>
      <Modal title={decisionItem ? `${decisionItem.candidateName} · HR 初筛决定` : 'HR 初筛决定'} open={decisionItem !== null} onCancel={() => !decisionPending && setDecisionItem(null)} onOk={() => void submitDecision()} confirmLoading={decisionPending} okText="保存决定" cancelText="取消">{decisionError && <Alert type="error" showIcon message={decisionError} />}{decisionItem && <div className="recruitment-decision-form"><Radio.Group value={decisionKind} onChange={event => { setDecisionKind(event.target.value); setReasonCode(null); }}>{getStage7DecisionKinds(decisionAdapter(decisionItem)).map(kind => <Radio.Button key={kind} value={kind}>{kind === 'pass' ? '通过' : kind === 'backup' ? '备选' : kind === 'reject' ? '淘汰' : '撤销淘汰'}</Radio.Button>)}</Radio.Group>{reasonOptions.length > 0 && <Select aria-label="选择决定原因" placeholder="选择岗位相关原因" value={reasonCode} onChange={setReasonCode} options={reasonOptions} />}<Input.TextArea aria-label="决定说明" value={reasonDetail} onChange={event => setReasonDetail(event.target.value)} placeholder="改变已有决定或撤销淘汰时，请填写岗位相关说明" rows={4} maxLength={1000} showCount /></div>}</Modal>
    </main>
  );
};

export default RecruitmentScreeningCenter;
