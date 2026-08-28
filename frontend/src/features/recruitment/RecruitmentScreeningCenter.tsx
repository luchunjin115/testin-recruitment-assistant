import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircleOutlined,
  FileSearchOutlined,
  InboxOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Checkbox,
  Empty,
  Form,
  Input,
  message,
  Modal,
  Radio,
  Select,
  Skeleton,
  Tag,
  Upload,
} from 'antd';
import ApplicationScreeningDrawer from './ApplicationScreeningDrawer';
import {
  backupStage7Application,
  getStage7ApplicationApiError,
  intakeStage7Application,
  passStage7Application,
  rejectStage7Application,
  undoStage7ApplicationRejection,
} from './services/applications';
import {
  abandonRecruitmentResume,
  extractRecruitmentResumeText,
  getRecruitmentResumes,
  type RecruitmentResumeDetail,
  type ResumeListSnapshot,
  uploadRecruitmentResume,
} from './services/resumes';
import {
  getStage7ScreeningCenter,
  type Stage7ScreeningCenterItem,
  type Stage7ScreeningCenterSnapshot,
} from './services/screening';
import {
  getAIScreeningApiError,
  reassessJobApplications,
} from './services/aiScreening';
import {
  getScreeningStateLabel,
  SCREENING_STATUS_META,
  validateBatchSelection,
} from './screeningPresentation';
import type {
  ScreeningBatchReassessmentResult,
  ScreeningState,
} from './types/aiScreening';
import {
  buildStage7DecisionSubmission,
  getStage7DecisionEntry,
  getStage7DecisionErrorMessage,
  getStage7DecisionKinds,
  STAGE7_BACKUP_REASON_OPTIONS,
  STAGE7_REJECT_REASON_OPTIONS,
  STAGE7_REVERSAL_REASON_OPTIONS,
  type Stage7DecisionKind,
} from './screeningDecisionAction';
import {
  buildStage7ScreeningIntakeInput,
  getStage7ScreeningIntakeErrorMessage,
  isStage7IntakeResumeFileSupported,
} from './screeningIntakeAction';
import type {
  Stage7ApplicationLifecycleStatus,
  Stage7HRDecision,
} from './types/applicationScreening';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: Stage7ScreeningCenterSnapshot };
type ResumeLoadState =
  | { status: 'idle' | 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ResumeListSnapshot };
type IntakeValues = { name: string; phone: string; email: string; jobId: number; resumeId?: number };

const HR_META: Record<Stage7HRDecision, { label: string; color: string }> = {
  pending: { label: 'HR 待决策', color: 'default' },
  passed: { label: 'HR 已通过', color: 'success' },
  backup: { label: '已进入备选', color: 'warning' },
  rejected: { label: 'HR 已淘汰', color: 'error' },
};
const LIFECYCLE_META: Record<Stage7ApplicationLifecycleStatus, string> = {
  active: '招聘中',
  ended: '流程已结束',
  voided: '申请已作废',
};
const SOURCE_LABELS = {
  hr_direct: 'HR 直接录入',
  hr_screening: 'HR 待审核录入',
  public_apply: '公开投递',
} as const;

const RecruitmentScreeningCenter: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [jobFilter, setJobFilter] = useState<number | 'all'>('all');
  const [decisionFilter, setDecisionFilter] = useState<Stage7HRDecision | 'all'>('all');
  const [intakeOpen, setIntakeOpen] = useState(false);
  const [intakeForm] = Form.useForm<IntakeValues>();
  const [resumeMode, setResumeMode] = useState<'upload' | 'existing'>('upload');
  const [resumeLoad, setResumeLoad] = useState<ResumeLoadState>({ status: 'idle' });
  const [intakeFile, setIntakeFile] = useState<File | null>(null);
  const [preparedResume, setPreparedResume] = useState<RecruitmentResumeDetail | null>(null);
  const [intakePending, setIntakePending] = useState(false);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [decisionItem, setDecisionItem] = useState<Stage7ScreeningCenterItem | null>(null);
  const [decisionKind, setDecisionKind] = useState<Stage7DecisionKind | null>(null);
  const [reasonCode, setReasonCode] = useState<string | null>(null);
  const [reasonDetail, setReasonDetail] = useState('');
  const [decisionPending, setDecisionPending] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [reportApplicationId, setReportApplicationId] = useState<number | null>(null);
  const [selectedApplicationIds, setSelectedApplicationIds] = useState<number[]>([]);
  const [batchPending, setBatchPending] = useState(false);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchResult, setBatchResult] = useState<ScreeningBatchReassessmentResult | null>(null);
  const [modal, modalContextHolder] = Modal.useModal();

  const load = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      setLoadState({ status: 'ready', data: await getStage7ScreeningCenter() });
    } catch {
      setLoadState({ status: 'error', message: '无法读取 Application 工作队列，请稍后重试。' });
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const snapshot = loadState.status === 'ready' ? loadState.data : null;
  const items = useMemo(() => (snapshot?.items || []).filter(item => (
    (jobFilter === 'all' || item.application.jobId === jobFilter)
    && (decisionFilter === 'all' || item.application.hrDecision === decisionFilter)
  )), [decisionFilter, jobFilter, snapshot]);
  const hasActiveFilters = jobFilter !== 'all' || decisionFilter !== 'all';
  const selectedItems = useMemo(() => (snapshot?.items || [])
    .filter(item => selectedApplicationIds.includes(item.application.id)), [selectedApplicationIds, snapshot]);
  const selectedJobId = selectedItems[0]?.application.jobId ?? null;
  const reportItem = snapshot?.items.find(
    item => item.application.id === reportApplicationId,
  ) ?? null;

  const updateScreeningState = useCallback((next: ScreeningState) => {
    setLoadState(current => {
      if (current.status !== 'ready') return current;
      return {
        status: 'ready',
        data: {
          ...current.data,
          items: current.data.items.map(item => item.application.id === next.applicationId
            ? { ...item, screeningState: next, screeningLoadError: null }
            : item),
        },
      };
    });
  }, []);

  const toggleBatchSelection = (item: Stage7ScreeningCenterItem, checked: boolean) => {
    setBatchError(null);
    setBatchResult(null);
    if (!checked) {
      setSelectedApplicationIds(current => current.filter(id => id !== item.application.id));
      return;
    }
    const validation = validateBatchSelection([
      ...selectedItems.map(selected => ({
        applicationId: selected.application.id,
        jobId: selected.application.jobId,
      })),
      { applicationId: item.application.id, jobId: item.application.jobId },
    ]);
    if (!validation.valid) {
      setBatchError(validation.message);
      return;
    }
    setSelectedApplicationIds(current => [...current, item.application.id]);
  };

  const submitBatch = () => {
    if (batchPending) return;
    const validation = validateBatchSelection(selectedItems.map(item => ({
      applicationId: item.application.id,
      jobId: item.application.jobId,
    })));
    if (!validation.valid) {
      setBatchError(validation.message);
      return;
    }
    const selectedJob = snapshot?.jobs.find(job => job.id === validation.jobId);
    if (selectedJob?.status !== 'open') {
      setBatchError('岗位关闭时不能批量重新评估。');
      return;
    }
    modal.confirm({
      title: `确认重新评估 ${validation.applicationIds.length} 人？`,
      content: '所选 Application 属于同一岗位。提交后任务进入后台，旧成功报告会保留到各自新报告成功。',
      okText: '批量重新评估',
      cancelText: '取消',
      onOk: async () => {
        setBatchPending(true);
        setBatchError(null);
        try {
          const result = await reassessJobApplications(validation.jobId, validation.applicationIds);
          setBatchResult(result);
          result.results.forEach(item => {
            const existing = selectedItems.find(
              selected => selected.application.id === item.applicationId,
            )?.screeningState;
            updateScreeningState({
              applicationId: item.applicationId,
              report: item.report ?? existing?.report ?? null,
              latestRun: item.run ?? existing?.latestRun ?? null,
            });
          });
          setSelectedApplicationIds([]);
        } catch (error) {
          setBatchError(getAIScreeningApiError(error).message);
        } finally {
          setBatchPending(false);
        }
      },
    });
  };

  const loadResumes = async () => {
    setResumeLoad({ status: 'loading' });
    try {
      setResumeLoad({ status: 'ready', data: await getRecruitmentResumes() });
    } catch {
      setResumeLoad({ status: 'error', message: '无法读取现有简历。' });
    }
  };

  const openIntake = () => {
    intakeForm.resetFields();
    setResumeMode('upload');
    setIntakeFile(null);
    setPreparedResume(null);
    setIntakeError(null);
    setIntakeOpen(true);
    void loadResumes();
  };

  const closeIntake = async () => {
    if (intakePending) return;
    if (preparedResume) {
      try { await abandonRecruitmentResume(preparedResume.id); } catch { /* 保留给清理任务 */ }
    }
    setIntakeOpen(false);
    setPreparedResume(null);
    setIntakeFile(null);
  };

  const submitIntake = async () => {
    if (intakePending) return;
    let values: IntakeValues;
    try { values = await intakeForm.validateFields(); } catch { return; }
    setIntakePending(true);
    setIntakeError(null);
    let resume = preparedResume;
    try {
      if (resumeMode === 'upload') {
        if (!resume && !intakeFile) throw new Error('请先选择需要上传的简历。');
        if (!resume && intakeFile) {
          resume = await uploadRecruitmentResume(intakeFile);
          setPreparedResume(resume);
        }
        if (!resume) throw new Error('请先选择需要上传的简历。');
        if (resume.parseStatus !== 'parsed') {
          resume = await extractRecruitmentResumeText(resume.id);
          setPreparedResume(resume);
        }
      }
      const resumeId = resumeMode === 'existing' ? values.resumeId ?? null : resume?.id ?? null;
      const built = buildStage7ScreeningIntakeInput({
        name: values.name,
        phone: values.phone,
        email: values.email,
        jobId: values.jobId,
        resumeId,
      });
      if (!built.valid) {
        setIntakeError(built.message);
        return;
      }
      const outcome = await intakeStage7Application(built.input);
      setPreparedResume(null);
      setIntakeFile(null);
      setIntakeOpen(false);
      message.success(outcome.existingApplicationReused
        ? `已找到现有 Application #${outcome.application.id}`
        : `Application #${outcome.application.id} 已进入 HR 工作队列`);
      await load();
    } catch (error) {
      const apiError = getStage7ApplicationApiError(error);
      setIntakeError(getStage7ScreeningIntakeErrorMessage(
        apiError.code,
        error instanceof Error ? error.message : apiError.message,
        apiError.candidateIds,
      ));
    } finally {
      setIntakePending(false);
    }
  };

  const openDecision = (item: Stage7ScreeningCenterItem) => {
    const kinds = getStage7DecisionKinds(item);
    setDecisionItem(item);
    setDecisionKind(kinds.length === 1 ? kinds[0] : null);
    setReasonCode(null);
    setReasonDetail('');
    setDecisionError(null);
  };

  const submitDecision = async () => {
    if (!decisionItem || decisionPending) return;
    const built = buildStage7DecisionSubmission(decisionItem, decisionKind, reasonCode, reasonDetail);
    if (!built.valid) { setDecisionError(built.message); return; }
    setDecisionPending(true);
    setDecisionError(null);
    try {
      const { action, input } = built.submission;
      if (action === 'pass') await passStage7Application(decisionItem.application.id, input);
      else if (action === 'backup') await backupStage7Application(decisionItem.application.id, input);
      else if (action === 'reject') await rejectStage7Application(decisionItem.application.id, input);
      else await undoStage7ApplicationRejection(decisionItem.application.id, input);
      message.success('HR 决策已保存，并写入阶段历史。');
      setDecisionItem(null);
      await load();
    } catch (error) {
      const apiError = getStage7ApplicationApiError(error);
      setDecisionError(getStage7DecisionErrorMessage(apiError.code, apiError.message));
    } finally {
      setDecisionPending(false);
    }
  };

  const reasonOptions: Array<{ value: string; label: string }> = decisionKind === 'backup'
    ? STAGE7_BACKUP_REASON_OPTIONS
    : decisionKind === 'reject'
      ? STAGE7_REJECT_REASON_OPTIONS
      : decisionKind === 'undo_rejection'
        ? STAGE7_REVERSAL_REASON_OPTIONS
        : [];

  return (
    <main className="recruitment-main recruitment-screening-page">
      {modalContextHolder}
      <section className="recruitment-page-heading">
        <div>
          <span className="recruitment-section-kicker">阶段 7 · Application 初筛队列</span>
          <h2>AI 初筛</h2>
          <p>集中查看岗位匹配建议，并由 HR 独立完成通过、备选或淘汰决定。</p>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openIntake}>录入待审核申请</Button>
      </section>

      <section aria-label="AI 与 HR 的职责边界" className="recruitment-screening-boundary">
        <div className="recruitment-screening-boundary-mark"><SafetyCertificateOutlined /></div>
        <div className="recruitment-screening-boundary-copy">
          <span>协作边界</span>
          <strong>AI 解释匹配依据，HR 作出最终决定</strong>
          <p>查看或重新评估只更新 AI 报告，不会改变人工结论或招聘进度。</p>
        </div>
        <div aria-label="AI 建议不会自动改写 HR 决定" className="recruitment-screening-boundary-lanes">
          <div><span>AI</span><strong>生成匹配建议</strong></div>
          <i>不自动改写</i>
          <div><span>HR</span><strong>保留最终决定</strong></div>
        </div>
      </section>

      <section className="recruitment-panel recruitment-screening-workspace">
        <div className="recruitment-screening-toolbar">
          <div className="recruitment-screening-toolbar-heading">
            <h3>申请队列</h3>
            <p>
              {snapshot
                ? `共 ${snapshot.items.length} 份申请，当前显示 ${items.length} 份`
                : '正在读取待审核申请与 AI 初筛状态'}
            </p>
          </div>
          <div className="recruitment-screening-filter-controls">
            <Select
              aria-label="按岗位筛选申请"
              value={jobFilter}
              onChange={setJobFilter}
              options={[
                { value: 'all', label: '全部岗位' },
                ...(snapshot?.jobs || []).map(job => ({ value: job.id, label: job.title })),
              ]}
            />
            <Select
              aria-label="按 HR 决策筛选申请"
              value={decisionFilter}
              onChange={setDecisionFilter}
              options={[
                { value: 'all', label: '全部 HR 决策' },
                ...Object.entries(HR_META).map(([value, meta]) => ({ value, label: meta.label })),
              ]}
            />
            {hasActiveFilters && (
              <Button onClick={() => { setJobFilter('all'); setDecisionFilter('all'); }}>清除筛选</Button>
            )}
            <Button aria-label="刷新申请队列" icon={<ReloadOutlined />} onClick={() => void load()} />
          </div>
        </div>

        <div className="recruitment-screening-batch-bar">
          <div>
            <span>批量操作</span>
            <p>同一开放岗位最多选择 5 份申请；每份申请独立排队、独立成功或失败。</p>
          </div>
          <div className="recruitment-screening-batch-actions">
            <span>已选 <strong>{selectedApplicationIds.length}</strong> / 5</span>
            {selectedApplicationIds.length > 0 && <Button onClick={() => setSelectedApplicationIds([])}>清空</Button>}
            <Button
              disabled={selectedApplicationIds.length === 0}
              loading={batchPending}
              onClick={submitBatch}
              type="primary"
            >
              批量重新评估
            </Button>
          </div>
        </div>

        {batchError && (
          <Alert className="recruitment-screening-inline-alert" closable message={batchError} onClose={() => setBatchError(null)} showIcon type="error" />
        )}

        {batchResult && (
          <Alert
            className="recruitment-screening-inline-alert"
            closable
            description={(
              <div className="recruitment-batch-result-list">
                <span>总计 {batchResult.totalCount} · 复用 {batchResult.reusedCount} · 排队 {batchResult.queuedCount} · 失败 {batchResult.failedCount}</span>
                {batchResult.results.map(result => (
                  <span key={result.applicationId}>
                    Application #{result.applicationId}
                    <Tag color={result.run ? SCREENING_STATUS_META[result.run.status].tone : 'success'}>
                      {result.run ? SCREENING_STATUS_META[result.run.status].label : result.reusedReport ? '复用报告' : '已提交'}
                    </Tag>
                  </span>
                ))}
                {batchResult.failures.map(failure => (
                  <span key={failure.applicationId}>
                    Application #{failure.applicationId}
                    <Tag color="error">{failure.errorCode}</Tag>
                    <span>{failure.errorMessage}{failure.retryable ? ' · 可处理后重试' : ' · 需先处理内容或状态问题'}</span>
                  </span>
                ))}
              </div>
            )}
            message={batchResult.failedCount > 0
              ? `岗位 #${batchResult.jobId} 批量提交已完成，部分 Application 未能提交`
              : `岗位 #${batchResult.jobId} 已处理 ${batchResult.totalCount} 个独立请求`}
            onClose={() => setBatchResult(null)}
            showIcon
            type={batchResult.failedCount > 0 ? 'warning' : 'success'}
          />
        )}

        {loadState.status === 'loading' && (
          <div aria-busy="true" aria-label="申请队列加载中" className="recruitment-screening-loading">
            <Skeleton active paragraph={{ rows: 6 }} />
          </div>
        )}
        {loadState.status === 'error' && (
          <Alert
            action={<Button onClick={() => void load()}>重试</Button>}
            className="recruitment-screening-inline-alert"
            description="请确认本地 API 服务可访问后重试。"
            message={loadState.message}
            showIcon
            type="error"
          />
        )}
        {loadState.status === 'ready' && items.length === 0 && (
          <Empty
            className="recruitment-panel-empty recruitment-screening-empty"
            description={(
              <div className="recruitment-empty-copy">
                <strong>{loadState.data.items.length === 0 ? '目前没有待审核申请' : '没有符合当前条件的申请'}</strong>
                <span>{loadState.data.items.length === 0
                  ? '录入申请并绑定简历后，AI 匹配建议和 HR 处理状态会显示在这里。'
                  : '调整岗位或 HR 决策筛选条件后再查看。'}</span>
              </div>
            )}
            image={<InboxOutlined />}
          >
            {loadState.data.items.length === 0
              ? <Button icon={<PlusOutlined />} onClick={openIntake} type="primary">录入第一份申请</Button>
              : <Button onClick={() => { setJobFilter('all'); setDecisionFilter('all'); }}>清除筛选</Button>}
          </Empty>
        )}
        {loadState.status === 'ready' && items.length > 0 && (
          <div aria-label="AI 初筛申请列表" className="recruitment-screening-list">
            {items.map(item => {
              const aiInProgress = ['queued', 'running'].includes(item.screeningState?.latestRun?.status ?? '');
              const decisionEntry = getStage7DecisionEntry(item, aiInProgress);
              return (
                <article className="recruitment-screening-card" key={item.application.id}>
                  <Checkbox
                    aria-label={`选择 Application #${item.application.id} 进行批量重新评估`}
                    checked={selectedApplicationIds.includes(item.application.id)}
                    disabled={item.jobStatus !== 'open'
                      || (selectedJobId !== null && selectedJobId !== item.application.jobId)
                      || (selectedApplicationIds.length >= 5 && !selectedApplicationIds.includes(item.application.id))}
                    onChange={event => toggleBatchSelection(item, event.target.checked)}
                  />
                  <div>
                    <span>Application #{item.application.id}</span>
                    <h3>{item.candidateName}</h3>
                    <p>{item.candidateTitle || '职位信息未填写'} · {item.jobTitle}</p>
                    <p>当前简历 #{item.application.currentResumeId} · {SOURCE_LABELS[item.application.source]}</p>
                  </div>
                  <div>
                    <Tag color={HR_META[item.application.hrDecision].color}>{HR_META[item.application.hrDecision].label}</Tag>
                    <Tag>{LIFECYCLE_META[item.application.lifecycleStatus]}</Tag>
                    {item.jobStatus === 'closed' && <Tag color="default">岗位已关闭</Tag>}
                    <Tag color={item.screeningState?.latestRun
                      ? SCREENING_STATUS_META[item.screeningState.latestRun.status].tone
                      : item.screeningState?.report?.isOutdated ? 'warning' : 'default'}>
                      {item.screeningLoadError ? '状态读取失败' : getScreeningStateLabel(item.screeningState)}
                    </Tag>
                  </div>
                  <div className="recruitment-screening-card-actions">
                    <Button icon={<FileSearchOutlined />} onClick={() => setReportApplicationId(item.application.id)}>
                      查看 AI 报告
                    </Button>
                    <Button
                      icon={<CheckCircleOutlined />}
                      disabled={!decisionEntry.allowed}
                      onClick={() => openDecision(item)}
                    >
                      {decisionEntry.label}
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <Modal
        title="录入待审核申请"
        open={intakeOpen}
        onCancel={() => void closeIntake()}
        onOk={() => void submitIntake()}
        confirmLoading={intakePending}
        okText="保存到工作队列"
      >
        {intakeError && <Alert type="error" showIcon message={intakeError} />}
        <Form form={intakeForm} layout="vertical">
          <Form.Item name="name" label="候选人姓名" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="phone" label="手机号" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="jobId" label="开放岗位" rules={[{ required: true }]}>
            <Select options={(snapshot?.jobs || []).filter(job => job.status === 'open').map(job => ({ value: job.id, label: job.title }))} />
          </Form.Item>
          <Form.Item label="简历来源">
            <Radio.Group value={resumeMode} onChange={event => setResumeMode(event.target.value)}>
              <Radio value="upload">上传新简历</Radio>
              <Radio value="existing">选择现有简历</Radio>
            </Radio.Group>
          </Form.Item>
          {resumeMode === 'upload' ? (
            <Upload.Dragger
              accept=".pdf,.docx,.txt"
              maxCount={1}
              beforeUpload={file => {
                if (!isStage7IntakeResumeFileSupported(file.name)) {
                  message.error('只支持 PDF、DOCX 或 TXT 简历。');
                  return Upload.LIST_IGNORE;
                }
                setIntakeFile(file);
                return false;
              }}
              onRemove={() => { setIntakeFile(null); return true; }}
            >
              <p><UploadOutlined /> 点击或拖入简历</p>
            </Upload.Dragger>
          ) : (
            <Form.Item name="resumeId" label="现有已解析简历" rules={[{ required: true }]}>
              <Select
                loading={resumeLoad.status === 'loading'}
                options={resumeLoad.status === 'ready'
                  ? resumeLoad.data.items.filter(item => item.parseStatus === 'parsed').map(item => ({ value: item.id, label: `#${item.id} ${item.filename}` }))
                  : []}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal
        title={decisionItem ? `${decisionItem.candidateName} · HR 决策` : 'HR 决策'}
        open={decisionItem !== null}
        onCancel={() => !decisionPending && setDecisionItem(null)}
        onOk={() => void submitDecision()}
        confirmLoading={decisionPending}
        okText="确认保存"
      >
        {decisionError && <Alert type="error" showIcon message={decisionError} />}
        {decisionItem && (
          <>
            <p>HR 决策独立于 AI，可根据岗位要求和当前简历作出判断。</p>
            <Radio.Group
              value={decisionKind}
              onChange={event => { setDecisionKind(event.target.value); setReasonCode(null); }}
            >
              {getStage7DecisionKinds(decisionItem).map(kind => (
                <Radio key={kind} value={kind}>
                  {kind === 'pass' ? '通过' : kind === 'backup' ? '备选' : kind === 'reject' ? '淘汰' : '撤销淘汰'}
                </Radio>
              ))}
            </Radio.Group>
            {reasonOptions.length > 0 && (
              <Select
                style={{ width: '100%', marginTop: 16 }}
                placeholder="选择原因"
                value={reasonCode}
                onChange={setReasonCode}
                options={reasonOptions}
              />
            )}
            <Input.TextArea
              style={{ marginTop: 16 }}
              rows={4}
              placeholder="填写与岗位能力相关的说明；改变已有决定时必填"
              value={reasonDetail}
              onChange={event => setReasonDetail(event.target.value)}
            />
          </>
        )}
      </Modal>

      <ApplicationScreeningDrawer
        applicationId={reportItem?.application.id ?? null}
        candidateName={reportItem?.candidateName ?? ''}
        initialState={reportItem?.screeningState ?? null}
        jobId={reportItem?.application.jobId ?? null}
        jobStatus={reportItem?.jobStatus ?? null}
        jobTitle={reportItem?.jobTitle ?? ''}
        onClose={() => setReportApplicationId(null)}
        onStateChange={updateScreeningState}
        open={reportItem !== null}
      />
    </main>
  );
};

export default RecruitmentScreeningCenter;
