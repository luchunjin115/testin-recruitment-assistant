import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircleOutlined,
  InboxOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
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
    <section className="recruitment-screening-page">
      <div className="recruitment-page-header">
        <div>
          <span className="recruitment-page-kicker">APPLICATION WORKSPACE</span>
          <h1>HR 初筛工作台</h1>
          <p>保留候选人录入、简历绑定和人工决定；新版 JD 驱动 AI 报告将在后续步骤接入。</p>
        </div>
        <div className="recruitment-page-actions">
          <Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openIntake}>录入待审核申请</Button>
        </div>
      </div>

      <Alert
        showIcon
        icon={<SafetyCertificateOutlined />}
        type="info"
        message="AI 初筛业务正在按新设计重建"
        description="旧 Rubric、权重评分和自动推荐已移除。HR 决策不依赖 AI 状态，仍可根据岗位要求和候选人材料独立操作。"
      />

      <div className="recruitment-screening-toolbar">
        <Select
          value={jobFilter}
          onChange={setJobFilter}
          options={[
            { value: 'all', label: '全部岗位' },
            ...(snapshot?.jobs || []).map(job => ({ value: job.id, label: job.title })),
          ]}
        />
        <Select
          value={decisionFilter}
          onChange={setDecisionFilter}
          options={[
            { value: 'all', label: '全部 HR 决策' },
            ...Object.entries(HR_META).map(([value, meta]) => ({ value, label: meta.label })),
          ]}
        />
      </div>

      {loadState.status === 'loading' && <Skeleton active paragraph={{ rows: 6 }} />}
      {loadState.status === 'error' && (
        <Alert type="error" showIcon message={loadState.message} action={<Button onClick={() => void load()}>重试</Button>} />
      )}
      {loadState.status === 'ready' && items.length === 0 && (
        <Empty image={<InboxOutlined />} description="当前筛选条件下没有 Application" />
      )}
      {loadState.status === 'ready' && items.map(item => {
        const decisionEntry = getStage7DecisionEntry(item, false);
        return (
          <article className="recruitment-screening-card" key={item.application.id}>
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
            </div>
            <Button
              icon={<CheckCircleOutlined />}
              disabled={!decisionEntry.allowed}
              onClick={() => openDecision(item)}
            >
              {decisionEntry.label}
            </Button>
          </article>
        );
      })}

      <Modal
        title="录入待审核 Application"
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
    </section>
  );
};

export default RecruitmentScreeningCenter;
