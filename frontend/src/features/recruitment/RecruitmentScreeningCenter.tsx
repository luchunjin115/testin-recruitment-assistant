import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircleOutlined, FileSearchOutlined, PlusOutlined, ReloadOutlined, SafetyCertificateOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, Button, Checkbox, Empty, Form, Input, Modal, Pagination, Radio, Select, Skeleton, Tag, Upload, message } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
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
type FilterState = { jobId: number | 'all'; source: ScreeningCenterSource | 'all'; decision: ScreeningCenterDecision | 'all'; stage: ScreeningCenterStage | 'all'; lifecycle: ScreeningCenterLifecycle | 'all'; pool: ScreeningCenterProcessingPool; processingStatus: string | 'all'; displayLabel: string | 'all'; sort: ScreeningCenterSort };
type IntakeValues = { name: string; phone: string; email: string; jobId: number; resumeId?: number };
type ResumeLoadState = { status: 'idle' | 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: ResumeListSnapshot };
const INITIAL_FILTERS: FilterState = { jobId: 'all', source: 'all', decision: 'all', stage: 'all', lifecycle: 'all', pool: 'all', processingStatus: 'all', displayLabel: 'all', sort: 'applied_desc' };
const SOURCE_LABELS: Record<ScreeningCenterSource, string> = { hr_direct: 'HR 直接录入', hr_screening: 'HR 待审核录入', public_apply: '公开投递' };
const DECISION_LABELS: Record<ScreeningCenterDecision, string> = { pending: 'HR 待决策', passed: 'HR 已通过', backup: '已进入备选', rejected: 'HR 已淘汰' };
const STAGE_LABELS: Record<ScreeningCenterStage, string> = { applied: '已申请', hr_review: 'HR 审核', screening_passed: '初筛通过', backup: '备选', rejected: '已淘汰', interview: '面试', offer: 'Offer 沟通', offer_accepted: 'Offer 已接受', admitted: '已录取', hired: '已入职' };
const LIFECYCLE_LABELS: Record<ScreeningCenterLifecycle, string> = { active: '招聘中', ended: '流程已结束', voided: '申请已作废' };
const REPORT_META = { not_started: ['尚未开始', 'default'], waiting_resume: ['等待简历', 'warning'], waiting_plan: ['等待评价计划', 'warning'], queued: ['等待评估', 'processing'], running: ['正在评估', 'processing'], ready: ['报告可用', 'success'], failed: ['评估失败', 'error'], paused: ['评估暂停', 'warning'], outdated: ['报告已过期', 'warning'], old_report_retained: ['旧报告保留', 'warning'] } as const;
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value));
const decisionAdapter = (item: ScreeningCenterItem) => ({ application: { lifecycleStatus: item.lifecycleStatus, recruitmentStage: item.recruitmentStage, hrDecision: item.hrDecision } });

const StageRail: React.FC<{ stage: ScreeningCenterStage; lifecycle: ScreeningCenterLifecycle }> = ({ stage, lifecycle }) => {
  const order: ScreeningCenterStage[] = ['applied', 'hr_review', 'screening_passed', 'interview', 'offer', 'offer_accepted', 'admitted', 'hired'];
  const normalized = stage === 'backup' || stage === 'rejected' ? 'hr_review' : stage;
  const active = Math.max(0, order.indexOf(normalized));
  return <ol aria-label={`招聘阶段：${STAGE_LABELS[stage]}`} className={`recruitment-stage-rail is-${lifecycle}`}>
    {['申请', '初筛', '面试', 'Offer', '接受', '录取', '入职'].map((label, index) => <li className={index <= active ? 'is-reached' : ''} key={label}><span />{label}</li>)}
  </ol>;
};

const RecruitmentScreeningCenter: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLinkedApplicationId = Number(searchParams.get('application_id'));
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [jobs, setJobs] = useState<RecruitmentJob[]>([]);
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
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
      const data = await listScreeningCenterApplications({ page, pageSize: 30, applicationId: Number.isInteger(deepLinkedApplicationId) && deepLinkedApplicationId > 0 ? deepLinkedApplicationId : undefined, jobId: filters.jobId === 'all' ? undefined : filters.jobId, source: filters.source === 'all' ? undefined : filters.source, hrDecision: filters.decision === 'all' ? undefined : filters.decision, stage: filters.stage === 'all' ? undefined : filters.stage, lifecycle: filters.lifecycle === 'all' ? undefined : filters.lifecycle, processingPool: filters.pool, processingStatus: filters.processingStatus === 'all' ? undefined : filters.processingStatus, displayLabel: filters.displayLabel === 'all' ? undefined : filters.displayLabel, sort: filters.sort });
      setLoadState({ status: 'ready', data });
      if (Number.isInteger(deepLinkedApplicationId) && deepLinkedApplicationId > 0 && data.items[0]) setSelectedItem(data.items[0]);
    } catch (error) { setLoadState({ status: 'error', message: getScreeningCenterError(error) }); }
  }, [deepLinkedApplicationId, filters, page]);

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

  const openDetail = async (item: ScreeningCenterItem) => {
    setSelectedItem(item); setPublicSubmission(null);
    setSearchParams({ application_id: String(item.applicationId) }, { replace: true });
  };
  const closeDetail = () => { setSelectedItem(null); setPublicSubmission(null); setSearchParams({}, { replace: true }); };
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
      message.success(outcome.existingApplicationReused ? `已找到现有 Application #${outcome.application.id}` : `Application #${outcome.application.id} 已进入 HR 工作队列`);
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
      message.success('HR 决策已保存，并写入阶段历史。'); setDecisionItem(null); await load();
    } catch (error) { const parsed = getStage7ApplicationApiError(error); setDecisionError(getStage7DecisionErrorMessage(parsed.code, parsed.message)); }
    finally { setDecisionPending(false); }
  };

  const items = loadState.status === 'ready' ? loadState.data.items : [];
  const selectedItems = useMemo(() => items.filter(item => selectedApplicationIds.includes(item.applicationId)), [items, selectedApplicationIds]);
  const toggleBatch = (item: ScreeningCenterItem, checked: boolean) => {
    if (!checked) { setSelectedApplicationIds(value => value.filter(id => id !== item.applicationId)); return; }
    if (selectedItems.length >= 5 || (selectedItems[0] && selectedItems[0].jobId !== item.jobId)) { message.warning('批量重新评估最多选择 5 份申请，且必须属于同一岗位。'); return; }
    setSelectedApplicationIds(value => [...value, item.applicationId]);
  };
  const submitBatch = () => {
    if (!selectedItems.length) return;
    modal.confirm({ title: `确认重新评估 ${selectedItems.length} 人？`, content: '旧成功报告会保留到新报告成功，不会自动改变 HR 决策。', okText: '批量重新评估', cancelText: '取消', onOk: async () => {
      setBatchPending(true);
      try {
        const result = await reassessJobApplications(selectedItems[0].jobId, selectedApplicationIds);
        setSelectedApplicationIds([]);
        if (result.failedCount > 0) message.warning(`部分任务未创建：${result.failures.map(item => `#${item.applicationId} ${item.errorMessage}`).join('；')}`);
        else message.success('重新评估任务已进入队列。');
        await load();
      }
      catch (error) { message.error(getAIScreeningApiError(error).message); }
      finally { setBatchPending(false); }
    } });
  };
  const reasonOptions: Array<{ value: string; label: string }> = decisionKind === 'backup' ? STAGE7_BACKUP_REASON_OPTIONS : decisionKind === 'reject' ? STAGE7_REJECT_REASON_OPTIONS : decisionKind === 'undo_rejection' ? STAGE7_REVERSAL_REASON_OPTIONS : [];
  const hasFilters = JSON.stringify(filters) !== JSON.stringify(INITIAL_FILTERS);

  return <main className="recruitment-main recruitment-screening-page recruitment-screening-center-v2">
    {modalContextHolder}
    <section className="recruitment-page-heading"><div><span className="recruitment-section-kicker">阶段 9 · 招聘证据台账</span><h2>AI 初筛中心</h2><p>统一查看内部录入和公开投递；AI 解释匹配依据，HR 作出最终决定。</p></div><div><Button onClick={() => navigate('/app/candidates/new')}>新增已通过候选人</Button><Button type="primary" icon={<PlusOutlined />} onClick={openIntake}>录入待审核申请</Button></div></section>
    <section aria-label="AI 与 HR 的职责边界" className="recruitment-screening-boundary"><div className="recruitment-screening-boundary-mark"><SafetyCertificateOutlined /></div><div className="recruitment-screening-boundary-copy"><span>协作边界</span><strong>报告是辅助证据，不是录用决定</strong><p>无报告会显示真实等待或失败状态，绝不会伪装成 0 分；重新评估也不会覆盖 HR 决策。</p></div></section>
    <section className="recruitment-panel recruitment-screening-workspace">
      <div className="recruitment-screening-toolbar"><div className="recruitment-screening-toolbar-heading"><h3>申请证据队列</h3><p>{loadState.status === 'ready' ? `共 ${loadState.data.total} 份申请` : '正在读取申请和已保存报告'}</p></div><div className="recruitment-screening-filter-controls">
        <Select aria-label="按岗位筛选申请" value={filters.jobId} onChange={jobId => { setPage(1); setFilters(value => ({ ...value, jobId })); }} options={[{ value: 'all', label: '全部岗位' }, ...jobs.map(job => ({ value: job.id, label: job.title }))]} />
        <Select aria-label="按申请来源筛选" value={filters.source} onChange={source => { setPage(1); setFilters(value => ({ ...value, source })); }} options={[{ value: 'all', label: '全部来源' }, ...Object.entries(SOURCE_LABELS).map(([value, label]) => ({ value, label }))]} />
        <Select aria-label="按 HR 决策筛选申请" value={filters.decision} onChange={decision => { setPage(1); setFilters(value => ({ ...value, decision })); }} options={[{ value: 'all', label: '全部 HR 决策' }, ...Object.entries(DECISION_LABELS).map(([value, label]) => ({ value, label }))]} />
        <Select aria-label="按招聘阶段筛选" value={filters.stage} onChange={stage => { setPage(1); setFilters(value => ({ ...value, stage })); }} options={[{ value: 'all', label: '全部招聘阶段' }, ...Object.entries(STAGE_LABELS).map(([value, label]) => ({ value, label }))]} />
        <Select aria-label="按流程状态筛选" value={filters.lifecycle} onChange={lifecycle => { setPage(1); setFilters(value => ({ ...value, lifecycle })); }} options={[{ value: 'all', label: '全部流程状态' }, ...Object.entries(LIFECYCLE_LABELS).map(([value, label]) => ({ value, label }))]} />
        <Select aria-label="按处理池筛选" value={filters.pool} onChange={pool => { setPage(1); setFilters(value => ({ ...value, pool })); }} options={[{ value: 'all', label: '全部处理池' }, { value: 'internal', label: '内部录入' }, { value: 'normal', label: '公开投递 · 正常' }, { value: 'exception', label: '公开投递 · 需人工处理' }]} />
        <Select aria-label="按自动处理状态筛选" value={filters.processingStatus} onChange={processingStatus => { setPage(1); setFilters(value => ({ ...value, processingStatus })); }} options={[{ value: 'all', label: '全部自动处理状态' }, { value: 'queued', label: '等待处理' }, { value: 'running', label: '正在处理' }, { value: 'waiting_screening', label: '等待初筛' }, { value: 'succeeded', label: '自动处理完成' }, { value: 'succeeded_with_warnings', label: '完成，需留意' }, { value: 'failed', label: '处理失败' }, { value: 'paused', label: '等待 HR 处理' }]} />
        <Select aria-label="按 AI 标签筛选" value={filters.displayLabel} onChange={displayLabel => { setPage(1); setFilters(value => ({ ...value, displayLabel })); }} options={[{ value: 'all', label: '全部 AI 标签' }, ...['关联较弱', '存在明显差距', '部分匹配', '整体较匹配', '高度匹配'].map(value => ({ value, label: value }))]} />
        <Select aria-label="排序方式" value={filters.sort} onChange={sort => setFilters(value => ({ ...value, sort }))} options={[{ value: 'applied_desc', label: '最近申请' }, { value: 'updated_desc', label: '最近业务更新' }, { value: 'score_desc', label: 'AI 分数从高到低' }, { value: 'score_asc', label: 'AI 分数从低到高' }]} />
        {hasFilters && <Button onClick={() => { setFilters(INITIAL_FILTERS); setPage(1); }}>清除筛选</Button>}<Button aria-label="刷新申请队列" icon={<ReloadOutlined />} onClick={() => void load()} />
      </div></div>
      {selectedApplicationIds.length > 0 && <div className="recruitment-screening-batchbar"><span>已选同一岗位 {selectedApplicationIds.length} 份申请</span><Button loading={batchPending} onClick={submitBatch} type="primary">批量重新评估</Button></div>}
      {loadState.status === 'loading' && <Skeleton active paragraph={{ rows: 10 }} />}
      {loadState.status === 'error' && <Alert type="error" showIcon message={loadState.message} action={<Button onClick={() => void load()}>重试</Button>} />}
      {loadState.status === 'ready' && items.length === 0 && <Empty className="recruitment-screening-empty" image={<FileSearchOutlined />} description="目前没有符合筛选条件的申请" />}
      {loadState.status === 'ready' && items.length > 0 && <div className="recruitment-evidence-ledger" role="list">{items.map(item => {
        const reportMeta = REPORT_META[item.screeningStatus];
        const decisionAllowed = item.allowedActions.some(action => ['pass', 'backup', 'reject', 'undo_rejection'].includes(action));
        const canBatch = item.allowedActions.includes('reassess_screening');
        return <article className="recruitment-evidence-row" key={item.applicationId} role="listitem">
          <div className="recruitment-evidence-select"><Checkbox aria-label={`选择 ${item.candidateName}`} checked={selectedApplicationIds.includes(item.applicationId)} disabled={!canBatch} onChange={event => toggleBatch(item, event.target.checked)} /></div>
          <div className="recruitment-evidence-identity"><div><strong>{item.candidateName}</strong><Tag bordered={false}>{SOURCE_LABELS[item.source]}</Tag></div><span>{item.maskedPhone || '电话未填写'} · {item.currentTitle || '当前职位未填写'}</span><p>{item.jobTitle}{item.submissionReference ? ` · ${item.submissionReference}` : ` · Application #${item.applicationId}`}</p><StageRail stage={item.recruitmentStage} lifecycle={item.lifecycleStatus} /></div>
          <div className="recruitment-evidence-ai"><div className="recruitment-evidence-score"><strong>{item.score === null ? '—' : item.score}</strong><span>{item.score === null ? '无可用报告' : item.displayLabel}</span><Tag color={reportMeta[1]}>{reportMeta[0]}</Tag></div><div className="recruitment-ability-tags">{item.abilityTags.length ? item.abilityTags.map(tag => <Tag bordered={false} key={tag.criterionId}>{tag.label} · {tag.score}</Tag>) : <span>暂无可靠标签</span>}</div><p className="recruitment-evidence-summary">{item.overallSummary || item.screeningErrorMessage || '报告完成后将在这里显示可核对的整体摘要。'}</p></div>
          <div className="recruitment-evidence-findings"><div className="is-strength"><span>优势证据</span>{item.strengths.length ? item.strengths.map(value => <p key={value}>{value}</p>) : <p>暂无可靠优势摘要</p>}</div><div className="is-risk"><span>差距 / 风险</span>{item.gapsOrRisks.length ? item.gapsOrRisks.map(value => <p key={value}>{value}</p>) : <p>暂无可靠风险摘要</p>}</div></div>
          <div className="recruitment-evidence-state"><div><Tag color={item.lifecycleStatus === 'active' ? 'processing' : 'default'}>{LIFECYCLE_LABELS[item.lifecycleStatus]}</Tag><Tag>{DECISION_LABELS[item.hrDecision]}</Tag></div><strong>{STAGE_LABELS[item.recruitmentStage]}{item.finalOutcome ? ` · ${item.finalOutcome}` : ''}</strong>{item.processingPool === 'exception' && <Tag color="error">自动处理需人工介入</Tag>}<span>申请 {formatDate(item.appliedAt)}</span><span>更新 {formatDate(item.businessUpdatedAt)}</span></div>
          <div className="recruitment-evidence-actions"><Button onClick={() => void openDetail(item)} type="primary">查看处理与 AI 报告</Button><Button disabled={!decisionAllowed} onClick={() => openDecision(item)}>HR 决策</Button>{item.allowedActions.includes('schedule_interview') && <Button onClick={() => void openDetail(item)} icon={<CheckCircleOutlined />}>查看面试入口</Button>}</div>
        </article>;
      })}</div>}
      {loadState.status === 'ready' && loadState.data.total > loadState.data.pageSize && <Pagination current={loadState.data.page} pageSize={loadState.data.pageSize} total={loadState.data.total} showSizeChanger={false} onChange={setPage} />}
    </section>
    <ApplicationScreeningDrawer applicationId={selectedItem?.applicationId ?? null} candidateName={selectedItem?.candidateName ?? ''} currentResumeId={selectedItem?.resumeId ?? null} initialState={null} jobId={selectedItem?.jobId ?? null} jobStatus={selectedItem?.jobStatus ?? null} jobTitle={selectedItem?.jobTitle ?? ''} open={selectedItem !== null} onClose={closeDetail} onStateChange={() => void load()} onPublicSubmissionChange={setPublicSubmission} onCurrentResumeChange={() => void load()} publicSubmission={publicSubmission} summary={selectedItem} />
    <Modal title="录入待审核申请" open={intakeOpen} onCancel={() => void closeIntake()} onOk={() => void submitIntake()} confirmLoading={intakePending} okText="保存到工作队列" cancelText="取消">
      {intakeError && <Alert type="error" showIcon message={intakeError} />}
      <Form form={intakeForm} layout="vertical"><Form.Item name="name" label="候选人姓名" rules={[{ required: true }]}><Input /></Form.Item><Form.Item name="phone" label="手机号" rules={[{ required: true }]}><Input /></Form.Item><Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}><Input /></Form.Item><Form.Item name="jobId" label="开放岗位" rules={[{ required: true }]}><Select options={jobs.filter(job => job.status === 'open').map(job => ({ value: job.id, label: job.title }))} /></Form.Item><Form.Item label="简历来源"><Radio.Group value={resumeMode} onChange={event => setResumeMode(event.target.value)}><Radio value="upload">上传新简历</Radio><Radio value="existing">选择现有简历</Radio></Radio.Group></Form.Item>
        {resumeMode === 'upload' ? <Upload.Dragger accept=".pdf,.docx,.txt" maxCount={1} beforeUpload={file => { if (!isStage7IntakeResumeFileSupported(file.name)) { message.error('只支持 PDF、DOCX 或 TXT 简历。'); return Upload.LIST_IGNORE; } setIntakeFile(file); return false; }} onRemove={() => { setIntakeFile(null); return true; }}><p><UploadOutlined /> 点击或拖入简历</p></Upload.Dragger> : <Form.Item name="resumeId" label="现有已解析简历" rules={[{ required: true }]}><Select loading={resumeLoad.status === 'loading'} options={resumeLoad.status === 'ready' ? resumeLoad.data.items.filter(item => item.parseStatus === 'parsed').map(item => ({ value: item.id, label: `#${item.id} ${item.filename}` })) : []} /></Form.Item>}
      </Form>
    </Modal>
    <Modal title={decisionItem ? `${decisionItem.candidateName} · HR 决策` : 'HR 决策'} open={decisionItem !== null} onCancel={() => !decisionPending && setDecisionItem(null)} onOk={() => void submitDecision()} confirmLoading={decisionPending} okText="保存决定" cancelText="取消">{decisionError && <Alert type="error" showIcon message={decisionError} />}{decisionItem && <div className="recruitment-decision-form"><Radio.Group value={decisionKind} onChange={event => { setDecisionKind(event.target.value); setReasonCode(null); }}>{getStage7DecisionKinds(decisionAdapter(decisionItem)).map(kind => <Radio.Button key={kind} value={kind}>{kind === 'pass' ? '通过' : kind === 'backup' ? '备选' : kind === 'reject' ? '淘汰' : '撤销淘汰'}</Radio.Button>)}</Radio.Group>{reasonOptions.length > 0 && <Select aria-label="选择决定原因" placeholder="选择岗位相关原因" value={reasonCode} onChange={setReasonCode} options={reasonOptions} />}<Input.TextArea aria-label="决定说明" value={reasonDetail} onChange={event => setReasonDetail(event.target.value)} placeholder="改变已有决定或撤销淘汰时，请填写岗位相关说明" rows={4} maxLength={1000} showCount /></div>}</Modal>
  </main>;
};

export default RecruitmentScreeningCenter;
