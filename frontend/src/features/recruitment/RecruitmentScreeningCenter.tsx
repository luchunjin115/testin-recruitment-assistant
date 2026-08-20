import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FileSearchOutlined,
  HistoryOutlined,
  InboxOutlined,
  PauseCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  StopOutlined,
  UndoOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { Alert, Button, Checkbox, Drawer, Empty, Form, Input, message, Modal, Radio, Select, Skeleton, Tag, Tooltip, Upload } from 'antd';
import { Link } from 'react-router-dom';
import {
  backupStage7Application,
  getStage7ApplicationApiError,
  intakeStage7Application,
  passStage7Application,
  rejectStage7Application,
  runStage7ApplicationScreening,
  runStage7ScreeningBatch,
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
  beginStage7SingleScreening,
  buildStage7ForceRerunInput,
  finishStage7SingleScreening,
  getStage7SingleScreeningAction,
  getStage7SingleScreeningErrorMessage,
} from './screeningAction';
import {
  beginStage7BatchRun,
  finishStage7BatchRun,
  getStage7BatchSelectionState,
  getStage7FailedBatchApplicationIds,
} from './screeningBatchAction';
import {
  buildStage7DecisionSubmission,
  getStage7DecisionEntry,
  getStage7DecisionErrorMessage,
  getStage7DecisionKinds,
  getStage7PassPolicy,
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
import RecruitmentScreeningDetailDrawer from './RecruitmentScreeningDetailDrawer';
import type {
  Stage7ApplicationAIStatus,
  Stage7ApplicationLifecycleStatus,
  Stage7HRDecision,
  Stage7RecruitmentStage,
  Stage7ScreeningBatchItemStatus,
  Stage7ScreeningBatchOutcome,
  Stage7ScreeningRunInput,
} from './types/applicationScreening';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: Stage7ScreeningCenterSnapshot };

type StatusMeta = { label: string; tone: 'info' | 'success' | 'warning' | 'danger' | 'neutral' };

type BatchResultView = {
  outcome: Stage7ScreeningBatchOutcome;
  candidateLabels: Record<number, string>;
};

type IntakeResumeLoadState =
  | { status: 'idle' | 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ResumeListSnapshot };

type IntakeFormValues = {
  name: string;
  phone: string;
  email: string;
  jobId: number;
  resumeId?: number;
};

type IntakeProgress = 'idle' | 'uploading' | 'extracting' | 'saving' | 'screening';

const AI_STATUS_META: Record<Stage7ApplicationAIStatus, StatusMeta> = {
  not_started: { label: '等待初筛', tone: 'neutral' },
  screening: { label: '初筛进行中', tone: 'info' },
  completed: { label: '初筛已完成', tone: 'success' },
  failed: { label: '初筛失败', tone: 'danger' },
  blocked: { label: '等待补充资料', tone: 'warning' },
};

const HR_DECISION_META: Record<Stage7HRDecision, StatusMeta> = {
  pending: { label: 'HR 待决策', tone: 'neutral' },
  passed: { label: 'HR 已通过', tone: 'success' },
  backup: { label: '已进入备选', tone: 'warning' },
  rejected: { label: 'HR 已淘汰', tone: 'danger' },
};

const LIFECYCLE_META: Record<Stage7ApplicationLifecycleStatus, StatusMeta> = {
  active: { label: '招聘中', tone: 'success' },
  ended: { label: '流程已结束', tone: 'neutral' },
  voided: { label: '申请已作废', tone: 'danger' },
};

const BATCH_STATUS_META: Record<Stage7ScreeningBatchItemStatus, StatusMeta> = {
  completed: { label: '评分完成', tone: 'success' },
  failed: { label: '评分失败', tone: 'danger' },
  blocked: { label: '资料不足', tone: 'warning' },
  reused: { label: '复用结果', tone: 'info' },
  skipped: { label: '安全跳过', tone: 'neutral' },
};

const PIPELINE_STAGES: Array<{ value: Stage7RecruitmentStage; label: string; note: string }> = [
  { value: 'applied', label: '已投递', note: '等待进入复核' },
  { value: 'hr_review', label: 'HR 复核', note: '查看 AI 结论' },
  { value: 'screening_passed', label: '已通过', note: '进入后续流程' },
  { value: 'backup', label: '备选', note: '保留候选人' },
  { value: 'rejected', label: '已淘汰', note: '流程已结束' },
];

const aiStatusOptions = [
  { value: 'all', label: '全部 AI 状态' },
  ...Object.entries(AI_STATUS_META).map(([value, meta]) => ({ value, label: meta.label })),
];
const hrDecisionOptions = [
  { value: 'all', label: '全部 HR 决策' },
  ...Object.entries(HR_DECISION_META).map(([value, meta]) => ({ value, label: meta.label })),
];
const lifecycleOptions = [
  { value: 'all', label: '全部生命周期' },
  ...Object.entries(LIFECYCLE_META).map(([value, meta]) => ({ value, label: meta.label })),
];

const SOURCE_LABELS = {
  hr_direct: 'HR 直接录入',
  hr_screening: 'HR 初筛录入',
  public_apply: '公开投递',
} as const;

const DECISION_KIND_META: Record<Stage7DecisionKind, {
  label: string;
  note: string;
  icon: React.ReactNode;
  tone: 'success' | 'warning' | 'danger' | 'neutral';
}> = {
  pass: {
    label: '通过初筛',
    note: '进入候选人业务视图',
    icon: <CheckCircleOutlined />,
    tone: 'success',
  },
  backup: {
    label: '进入备选',
    note: '保留在初筛中心继续比较',
    icon: <PauseCircleOutlined />,
    tone: 'warning',
  },
  reject: {
    label: '淘汰申请',
    note: '结束本岗位申请但保留历史',
    icon: <StopOutlined />,
    tone: 'danger',
  },
  undo_rejection: {
    label: '撤销淘汰',
    note: '恢复为 HR 待审核',
    icon: <UndoOutlined />,
    tone: 'neutral',
  },
};

const formatDateTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
};

const getStatusMessage = (item: Stage7ScreeningCenterItem) => {
  const { application, currentResult } = item;
  if (currentResult?.isOutdated) return '岗位或简历已经变化，当前结论需要重新确认。';
  if (application.aiStatus === 'blocked') return currentResult?.errorMessage || '资料不足，补齐后才能继续评分。';
  if (application.aiStatus === 'failed') return currentResult?.errorMessage || '上一次评分没有完成，可稍后重试。';
  if (application.aiStatus === 'screening') return '评分任务正在运行，请稍后刷新。';
  if (application.aiStatus === 'not_started') return '尚未生成 AI 初筛结论。';
  return currentResult?.recommendation || 'AI 初筛已完成，等待 HR 查看。';
};

const getResumeOperationErrorMessage = (error: unknown, fallback: string) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  return error instanceof Error && error.message ? error.message : fallback;
};

const RecruitmentScreeningCenter: React.FC = () => {
  const [intakeForm] = Form.useForm<IntakeFormValues>();
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [jobFilter, setJobFilter] = useState<number | 'all'>('all');
  const [stageFilter, setStageFilter] = useState<Stage7RecruitmentStage | 'all'>('all');
  const [aiFilter, setAiFilter] = useState<Stage7ApplicationAIStatus | 'all'>('all');
  const [hrFilter, setHrFilter] = useState<Stage7HRDecision | 'all'>('all');
  const [lifecycleFilter, setLifecycleFilter] = useState<Stage7ApplicationLifecycleStatus | 'all'>('all');
  const pendingScreeningIdsRef = useRef(new Set<number>());
  const [pendingScreeningIds, setPendingScreeningIds] = useState<Set<number>>(new Set());
  const [screeningErrors, setScreeningErrors] = useState<Record<number, string>>({});
  const batchRunGuardRef = useRef({ pending: false });
  const [batchPending, setBatchPending] = useState(false);
  const [selectedBatchIds, setSelectedBatchIds] = useState<Set<number>>(new Set());
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchResult, setBatchResult] = useState<BatchResultView | null>(null);
  const [detailItem, setDetailItem] = useState<Stage7ScreeningCenterItem | null>(null);
  const [forceRerunItem, setForceRerunItem] = useState<Stage7ScreeningCenterItem | null>(null);
  const [forceRerunReason, setForceRerunReason] = useState('');
  const decisionGuardRef = useRef({ pending: false });
  const [decisionItem, setDecisionItem] = useState<Stage7ScreeningCenterItem | null>(null);
  const [decisionKind, setDecisionKind] = useState<Stage7DecisionKind | null>(null);
  const [decisionReasonCode, setDecisionReasonCode] = useState<string | null>(null);
  const [decisionReasonDetail, setDecisionReasonDetail] = useState('');
  const [decisionPending, setDecisionPending] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const intakeGuardRef = useRef({ pending: false });
  const [intakeOpen, setIntakeOpen] = useState(false);
  const [intakeResumeMode, setIntakeResumeMode] = useState<'existing' | 'upload'>('upload');
  const [intakeResumeLoad, setIntakeResumeLoad] = useState<IntakeResumeLoadState>({ status: 'idle' });
  const [intakeFile, setIntakeFile] = useState<File | null>(null);
  const [preparedResume, setPreparedResume] = useState<RecruitmentResumeDetail | null>(null);
  const [intakeProgress, setIntakeProgress] = useState<IntakeProgress>('idle');
  const [intakeError, setIntakeError] = useState<string | null>(null);

  const apiFilters = useMemo(() => ({
    jobId: jobFilter === 'all' ? undefined : jobFilter,
    aiStatus: aiFilter === 'all' ? undefined : aiFilter,
    hrDecision: hrFilter === 'all' ? undefined : hrFilter,
    lifecycleStatus: lifecycleFilter === 'all' ? undefined : lifecycleFilter,
  }), [aiFilter, hrFilter, jobFilter, lifecycleFilter]);

  const loadScreeningCenter = useCallback(async (showLoading = true) => {
    if (showLoading) setLoadState({ status: 'loading' });
    try {
      const data = await getStage7ScreeningCenter(apiFilters);
      setLoadState({ status: 'ready', data });
      setJobFilter(current => (
        current === 'all' || data.jobs.some(job => job.id === current) ? current : 'all'
      ));
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法读取 Application 工作队列',
      });
    }
  }, [apiFilters]);

  useEffect(() => {
    void loadScreeningCenter();
  }, [loadScreeningCenter]);

  useEffect(() => {
    setSelectedBatchIds(new Set());
    setBatchError(null);
  }, [aiFilter, hrFilter, jobFilter, lifecycleFilter, stageFilter]);

  const clearFilters = () => {
    setJobFilter('all');
    setStageFilter('all');
    setAiFilter('all');
    setHrFilter('all');
    setLifecycleFilter('all');
  };

  const loadIntakeResumeOptions = async () => {
    setIntakeResumeLoad({ status: 'loading' });
    try {
      setIntakeResumeLoad({ status: 'ready', data: await getRecruitmentResumes() });
    } catch (error) {
      setIntakeResumeLoad({
        status: 'error',
        message: getResumeOperationErrorMessage(error, '无法读取现有简历'),
      });
    }
  };

  const resetIntakeDialog = () => {
    intakeForm.resetFields();
    setIntakeOpen(false);
    setIntakeResumeMode('upload');
    setIntakeResumeLoad({ status: 'idle' });
    setIntakeFile(null);
    setPreparedResume(null);
    setIntakeProgress('idle');
    setIntakeError(null);
  };

  const openIntakeDialog = () => {
    const selectedOpenJob = loadState.status === 'ready'
      && typeof jobFilter === 'number'
      && loadState.data.jobs.some(job => job.id === jobFilter && job.status === 'open')
      ? jobFilter
      : undefined;
    intakeForm.resetFields();
    intakeForm.setFieldsValue({ jobId: selectedOpenJob });
    setIntakeOpen(true);
    setIntakeResumeMode('upload');
    setIntakeFile(null);
    setPreparedResume(null);
    setIntakeProgress('idle');
    setIntakeError(null);
    void loadIntakeResumeOptions();
  };

  const closeIntakeDialog = async () => {
    if (intakeGuardRef.current.pending) return;
    const unboundResume = preparedResume;
    resetIntakeDialog();
    if (unboundResume) {
      try {
        await abandonRecruitmentResume(unboundResume.id);
      } catch {
        message.warning(`未绑定简历 #${unboundResume.id} 没有自动清理，可前往简历管理手动处理。`);
      }
    }
  };

  const changeIntakeResumeMode = async (mode: 'existing' | 'upload') => {
    if (mode === intakeResumeMode || intakeGuardRef.current.pending) return;
    const unboundResume = preparedResume;
    setIntakeResumeMode(mode);
    setIntakeFile(null);
    setPreparedResume(null);
    setIntakeError(null);
    intakeForm.setFieldValue('resumeId', undefined);
    if (unboundResume) {
      try {
        await abandonRecruitmentResume(unboundResume.id);
      } catch {
        message.warning(`未绑定简历 #${unboundResume.id} 没有自动清理，可前往简历管理手动处理。`);
      }
    }
  };

  const selectIntakeFile = async (file: File) => {
    if (!isStage7IntakeResumeFileSupported(file.name)) {
      setIntakeError('只支持 PDF、DOCX 和 TXT 简历。');
      return false;
    }
    const unboundResume = preparedResume;
    setIntakeFile(file);
    setPreparedResume(null);
    setIntakeError(null);
    if (unboundResume) {
      try {
        await abandonRecruitmentResume(unboundResume.id);
      } catch {
        message.warning(`未绑定简历 #${unboundResume.id} 没有自动清理，可前往简历管理手动处理。`);
      }
    }
    return false;
  };

  const submitIntake = async () => {
    if (intakeGuardRef.current.pending) return;
    let values: IntakeFormValues;
    try {
      values = await intakeForm.validateFields();
    } catch {
      return;
    }

    intakeGuardRef.current.pending = true;
    setIntakeError(null);
    let resumeForSubmission = preparedResume;
    let operation: IntakeProgress = 'idle';
    try {
      if (intakeResumeMode === 'upload') {
        if (!resumeForSubmission && !intakeFile) {
          setIntakeError('请先选择一份 PDF、DOCX 或 TXT 简历。');
          return;
        }
        if (!resumeForSubmission && intakeFile) {
          operation = 'uploading';
          setIntakeProgress('uploading');
          resumeForSubmission = await uploadRecruitmentResume(intakeFile);
          setPreparedResume(resumeForSubmission);
        }
        if (resumeForSubmission?.parseStatus !== 'parsed') {
          operation = 'extracting';
          setIntakeProgress('extracting');
          resumeForSubmission = await extractRecruitmentResumeText(resumeForSubmission!.id);
          setPreparedResume(resumeForSubmission);
        }
      }

      const buildResult = buildStage7ScreeningIntakeInput({
        name: values.name,
        phone: values.phone,
        email: values.email,
        jobId: values.jobId,
        resumeId: intakeResumeMode === 'existing' ? (values.resumeId ?? null) : resumeForSubmission?.id ?? null,
      });
      if (!buildResult.valid) {
        setIntakeError(buildResult.message);
        return;
      }

      operation = 'saving';
      setIntakeProgress('saving');
      const intakeOutcome = await intakeStage7Application(buildResult.input);
      const applicationId = intakeOutcome.application.id;
      let screeningMessage: string | null = null;

      if (intakeOutcome.existingApplicationReused) {
        if (resumeForSubmission && intakeResumeMode === 'upload') {
          try {
            await abandonRecruitmentResume(resumeForSubmission.id);
          } catch {
            message.warning(`重复申请已复用，但新上传的简历 #${resumeForSubmission.id} 未能自动清理。`);
          }
        }
        message.info(`已找到同岗位的有效 Application #${applicationId}，没有重复创建或重复评分。`);
      } else {
        setPreparedResume(null);
        operation = 'screening';
        setIntakeProgress('screening');
        try {
          const screeningOutcome = await runStage7ApplicationScreening(applicationId);
          if (screeningOutcome.result.executionStatus === 'completed') {
            message.success('新申请已保存，AI 初筛已完成，等待 HR 决策。');
          } else {
            screeningMessage = screeningOutcome.result.errorMessage
              || (screeningOutcome.result.executionStatus === 'blocked'
                ? '新申请已保存，但资料不足，AI 暂时无法形成结论。'
                : '新申请已保存，但首次 AI 初筛没有完成。');
            message.warning(screeningMessage);
          }
        } catch (error) {
          const apiError = getStage7ApplicationApiError(error);
          screeningMessage = `申请已保存，但 AI 初筛未启动：${apiError.message}`;
          message.warning(screeningMessage);
        }
      }

      if (screeningMessage) {
        setScreeningErrors(current => ({ ...current, [applicationId]: screeningMessage! }));
      }
      if (intakeOutcome.suspectedDuplicateCandidateIds.length) {
        message.warning(`系统发现可能重复的候选人 ${intakeOutcome.suspectedDuplicateCandidateIds.map(id => `#${id}`).join('、')}，请后续人工核对。`);
      } else if (!intakeOutcome.existingApplicationReused) {
        message.info(intakeOutcome.candidateResolution === 'created'
          ? '已创建新的 Candidate，并与本次 Application 关联。'
          : '已按手机号和邮箱复用现有 Candidate。');
      }

      clearFilters();
      await loadScreeningCenter(false);
      resetIntakeDialog();
    } catch (error) {
      if (operation === 'uploading' || operation === 'extracting') {
        setIntakeError(getResumeOperationErrorMessage(error, '简历上传或原文提取失败，请重试。'));
      } else {
        const apiError = getStage7ApplicationApiError(error);
        setIntakeError(getStage7ScreeningIntakeErrorMessage(
          apiError.code,
          apiError.message,
          apiError.candidateIds,
        ));
      }
    } finally {
      intakeGuardRef.current.pending = false;
      setIntakeProgress('idle');
    }
  };

  const runSingleScreening = async (
    item: Stage7ScreeningCenterItem,
    input: Stage7ScreeningRunInput = {},
  ) => {
    const applicationId = item.application.id;
    if (!beginStage7SingleScreening(pendingScreeningIdsRef.current, applicationId)) return false;
    setPendingScreeningIds(new Set(pendingScreeningIdsRef.current));
    setScreeningErrors(current => {
      const next = { ...current };
      delete next[applicationId];
      return next;
    });

    try {
      const outcome = await runStage7ApplicationScreening(applicationId, input);
      if (outcome.result.executionStatus === 'completed') {
        message.success(input.force
          ? '强制重跑已完成，原评分仍保留在历史中'
          : (outcome.reused ? '已读取现有初筛结果' : 'AI 初筛已完成'));
      } else {
        const resultMessage = outcome.result.errorMessage
          || (outcome.result.executionStatus === 'blocked'
            ? '初筛未生成结论，请先补充候选人资料。'
            : '初筛没有完成，可稍后重新尝试。');
        setScreeningErrors(current => ({ ...current, [applicationId]: resultMessage }));
        message.warning(resultMessage);
      }
      await loadScreeningCenter(false);
      return true;
    } catch (error) {
      const apiError = getStage7ApplicationApiError(error);
      const errorMessage = getStage7SingleScreeningErrorMessage(apiError.code, apiError.message);
      setScreeningErrors(current => ({ ...current, [applicationId]: errorMessage }));
      message.error('AI 初筛没有启动，请查看该申请的提示。');
      if (apiError.code === 'SCREENING_ALREADY_RUNNING') await loadScreeningCenter(false);
      return false;
    } finally {
      finishStage7SingleScreening(pendingScreeningIdsRef.current, applicationId);
      setPendingScreeningIds(new Set(pendingScreeningIdsRef.current));
    }
  };

  const openForceRerunConfirmation = (item: Stage7ScreeningCenterItem) => {
    setForceRerunItem(item);
    setForceRerunReason('');
  };

  const closeForceRerunConfirmation = () => {
    if (forceRerunItem && pendingScreeningIds.has(forceRerunItem.application.id)) return;
    setForceRerunItem(null);
    setForceRerunReason('');
  };

  const confirmForceRerun = async () => {
    if (!forceRerunItem) return;
    const input = buildStage7ForceRerunInput(forceRerunReason);
    if (!input) return;
    const submitted = await runSingleScreening(forceRerunItem, input);
    if (submitted) {
      setForceRerunItem(null);
      setForceRerunReason('');
    }
  };

  const openDecisionDialog = (item: Stage7ScreeningCenterItem) => {
    const kinds = getStage7DecisionKinds(item);
    setDecisionItem(item);
    setDecisionKind(kinds.length === 1 ? kinds[0] : null);
    setDecisionReasonCode(null);
    setDecisionReasonDetail('');
    setDecisionError(null);
  };

  const closeDecisionDialog = () => {
    if (decisionGuardRef.current.pending) return;
    setDecisionItem(null);
    setDecisionKind(null);
    setDecisionReasonCode(null);
    setDecisionReasonDetail('');
    setDecisionError(null);
  };

  const selectDecisionKind = (kind: Stage7DecisionKind) => {
    setDecisionKind(kind);
    setDecisionReasonCode(null);
    setDecisionReasonDetail('');
    setDecisionError(null);
  };

  const submitHRDecision = async () => {
    if (!decisionItem || decisionGuardRef.current.pending) return;
    const buildResult = buildStage7DecisionSubmission(
      decisionItem,
      decisionKind,
      decisionReasonCode,
      decisionReasonDetail,
    );
    if (!buildResult.valid) {
      setDecisionError(buildResult.message);
      return;
    }

    decisionGuardRef.current.pending = true;
    setDecisionPending(true);
    setDecisionError(null);
    let succeeded = false;
    try {
      const { action, input } = buildResult.submission;
      if (action === 'pass') await passStage7Application(decisionItem.application.id, input);
      else if (action === 'backup') await backupStage7Application(decisionItem.application.id, input);
      else if (action === 'reject') await rejectStage7Application(decisionItem.application.id, input);
      else await undoStage7ApplicationRejection(decisionItem.application.id, input);

      const successMessages: Record<Stage7DecisionKind, string> = {
        pass: '已通过初筛，Application 将进入候选人业务视图',
        backup: '已进入备选，Application 继续保留在初筛中心',
        reject: '已淘汰本岗位申请，记录和历史均已保留',
        undo_rejection: '已撤销淘汰，Application 回到 HR 待审核',
      };
      message.success(successMessages[action]);
      await loadScreeningCenter(false);
      succeeded = true;
    } catch (error) {
      const apiError = getStage7ApplicationApiError(error);
      setDecisionError(getStage7DecisionErrorMessage(apiError.code, apiError.message));
      if (apiError.code === 'INVALID_APPLICATION_TRANSITION') await loadScreeningCenter(false);
    } finally {
      decisionGuardRef.current.pending = false;
      setDecisionPending(false);
      if (succeeded) {
        setDecisionItem(null);
        setDecisionKind(null);
        setDecisionReasonCode(null);
        setDecisionReasonDetail('');
        setDecisionError(null);
      }
    }
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="Application 工作队列加载中" className="recruitment-main">
        <section className="recruitment-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="recruitment-application-funnel is-loading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="recruitment-stat-grid">
          {[0, 1, 2, 3].map(item => <article className="recruitment-stat-card" key={item}><Skeleton active paragraph={false} /></article>)}
        </section>
        <section className="recruitment-state-panel"><Skeleton active paragraph={{ rows: 8 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="recruitment-main">
        <section className="recruitment-page-heading">
          <div>
            <span className="recruitment-section-kicker">阶段 7 · Application 工作队列</span>
            <h2>AI 初筛中心</h2>
            <p>从真实 Application 状态开始组织初筛工作。</p>
          </div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadScreeningCenter()}>重新加载</Button>}
          className="recruitment-dashboard-alert recruitment-section-gap"
          description={`请确认新版 API 已启动，且 applications、jobs、candidates 和 screening-results 接口可访问。技术信息：${loadState.message}`}
          message="Application 工作队列加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const openJobs = data.jobs.filter(job => job.status === 'open');
  const parsedIntakeResumes = intakeResumeLoad.status === 'ready'
    ? intakeResumeLoad.data.items.filter(resume => resume.parseStatus === 'parsed')
    : [];
  const intakeProgressLabel: Record<Exclude<IntakeProgress, 'idle'>, string> = {
    uploading: '正在安全上传简历文件…',
    extracting: '正在提取简历原文…',
    saving: '正在保存 Candidate 与 Application…',
    screening: '申请已保存，正在运行首次 AI 初筛…',
  };
  const visibleItems = stageFilter === 'all'
    ? data.items
    : data.items.filter(item => item.application.recruitmentStage === stageFilter);
  const needsAttention = visibleItems.filter(item => (
    item.application.aiStatus === 'blocked'
    || item.application.aiStatus === 'failed'
    || item.currentResult?.isOutdated
  )).length;
  const stats = [
    {
      label: '当前申请', value: visibleItems.length, note: '符合当前筛选条件',
      icon: <FileSearchOutlined />, tone: 'blue',
    },
    {
      label: '等待初筛', value: visibleItems.filter(item => item.application.aiStatus === 'not_started').length,
      note: '尚未生成评分结果', icon: <ClockCircleOutlined />, tone: 'orange',
    },
    {
      label: '需要处理', value: needsAttention, note: '失败、资料不足或结果过期',
      icon: <ExclamationCircleOutlined />, tone: 'red',
    },
    {
      label: 'HR 待决策', value: visibleItems.filter(item => item.application.hrDecision === 'pending').length,
      note: '等待人工确认方向', icon: <SafetyCertificateOutlined />, tone: 'green',
    },
  ];
  const hasActiveFilters = jobFilter !== 'all'
    || stageFilter !== 'all'
    || aiFilter !== 'all'
    || hrFilter !== 'all'
    || lifecycleFilter !== 'all';
  const availableDecisionKinds = decisionItem ? getStage7DecisionKinds(decisionItem) : [];
  const decisionBuildResult = decisionItem
    ? buildStage7DecisionSubmission(
      decisionItem,
      decisionKind,
      decisionReasonCode,
      decisionReasonDetail,
    )
    : null;
  const passPolicy = decisionItem && decisionKind === 'pass'
    ? getStage7PassPolicy(decisionItem)
    : null;
  const decisionReasonOptions: Array<{ value: string; label: string }> = decisionKind === 'backup'
    ? STAGE7_BACKUP_REASON_OPTIONS
    : decisionKind === 'reject'
      ? STAGE7_REJECT_REASON_OPTIONS
      : decisionKind === 'undo_rejection'
        ? STAGE7_REVERSAL_REASON_OPTIONS
        : [];
  const decisionDetailRequired = Boolean(
    decisionKind === 'undo_rejection'
    || passPolicy?.detailRequired
    || (decisionItem && decisionItem.application.hrDecision !== 'pending'),
  );
  const selectedBatchItems = data.items.filter(item => selectedBatchIds.has(item.application.id));
  const selectedBatchJobId = selectedBatchItems[0]?.application.jobId ?? null;
  const selectedBatchJobTitle = selectedBatchItems[0]?.jobTitle ?? null;

  const toggleBatchSelection = (item: Stage7ScreeningCenterItem) => {
    const applicationId = item.application.id;
    const selected = selectedBatchIds.has(applicationId);
    const selectionState = getStage7BatchSelectionState(item, {
      selected,
      selectedCount: selectedBatchIds.size,
      selectedJobId: selectedBatchJobId,
      batchPending,
      singlePending: pendingScreeningIds.has(applicationId),
    });
    if (!selectionState.allowed) return;
    setSelectedBatchIds(current => {
      const next = new Set(current);
      if (next.has(applicationId)) next.delete(applicationId);
      else next.add(applicationId);
      return next;
    });
    setBatchError(null);
  };

  const executeBatchScreening = async (
    applicationIds: number[],
    jobId: number,
    candidateLabels: Record<number, string>,
    retryFailedOnly = false,
  ) => {
    if (!beginStage7BatchRun(batchRunGuardRef.current)) return;
    setBatchPending(true);
    setBatchError(null);
    try {
      const outcome = await runStage7ScreeningBatch(jobId, {
        application_ids: applicationIds,
        retry_failed_only: retryFailedOnly,
      });
      setBatchResult({ outcome, candidateLabels });
      setSelectedBatchIds(new Set());
      const { completed, failed, blocked, reused, skipped } = outcome.summary;
      message.info(`批量初筛完成：完成 ${completed}，失败 ${failed}，资料不足 ${blocked}，复用 ${reused}，跳过 ${skipped}`);
      await loadScreeningCenter(false);
    } catch (error) {
      const apiError = getStage7ApplicationApiError(error);
      setBatchError(apiError.message);
      message.error('批量初筛没有启动，请查看批次提示。');
    } finally {
      finishStage7BatchRun(batchRunGuardRef.current);
      setBatchPending(false);
    }
  };

  const runSelectedBatch = () => {
    if (selectedBatchJobId === null || selectedBatchIds.size < 1 || selectedBatchIds.size > 5) return;
    const candidateLabels = Object.fromEntries(
      selectedBatchItems.map(item => [item.application.id, item.candidateName]),
    );
    void executeBatchScreening(
      Array.from(selectedBatchIds),
      selectedBatchJobId,
      candidateLabels,
    );
  };

  const retryFailedBatch = () => {
    if (!batchResult) return;
    const failedIds = getStage7FailedBatchApplicationIds(batchResult.outcome);
    if (!failedIds.length) return;
    void executeBatchScreening(
      failedIds,
      batchResult.outcome.jobId,
      batchResult.candidateLabels,
      true,
    );
  };

  return (
    <main className="recruitment-main">
      <section className="recruitment-page-heading recruitment-screening-heading">
        <div>
          <span className="recruitment-section-kicker">阶段 7 · Application 工作队列 · 实时读取 /api/v2</span>
          <h2>AI 初筛中心</h2>
          <p>查看每份申请停在哪里，并为符合条件的单个申请启动 AI 初筛；AI 结论不会自动改变 HR 决策。</p>
        </div>
        <div className="recruitment-screening-heading-actions">
          <Button
            disabled={batchPending || pendingScreeningIds.size > 0 || decisionPending}
            icon={<PlusOutlined />}
            onClick={openIntakeDialog}
            type="primary"
          >
            录入新申请
          </Button>
          <Tooltip title={selectedBatchIds.size ? `为已选择的 ${selectedBatchIds.size} 人开始评分` : '先在申请队列中勾选同岗位的 1—5 人'}>
            <Button
              disabled={!selectedBatchIds.size || batchPending || pendingScreeningIds.size > 0 || intakeOpen}
              icon={<RobotOutlined />}
              loading={batchPending}
              onClick={runSelectedBatch}
            >
              开始批量初筛{selectedBatchIds.size ? ` · ${selectedBatchIds.size}` : ''}
            </Button>
          </Tooltip>
        </div>
      </section>

      <section aria-label="招聘阶段筛选" className="recruitment-application-funnel">
        <div className="recruitment-application-funnel-intro">
          <span>招聘阶段</span>
          <strong>申请流转轨道</strong>
          <small>点击阶段筛选列表</small>
        </div>
        <div className="recruitment-application-funnel-track">
          {PIPELINE_STAGES.map(stage => {
            const count = data.items.filter(item => item.application.recruitmentStage === stage.value).length;
            const selected = stageFilter === stage.value;
            return (
              <button
                aria-pressed={selected}
                className={selected ? 'is-selected' : ''}
                key={stage.value}
                onClick={() => setStageFilter(selected ? 'all' : stage.value)}
                type="button"
              >
                <span>{stage.label}</span>
                <strong>{count}</strong>
                <small>{stage.note}</small>
              </button>
            );
          })}
        </div>
      </section>

      <section aria-label="Application 队列统计" className="recruitment-stat-grid">
        {stats.map(stat => (
          <article className="recruitment-stat-card" key={stat.label}>
            <div className={`recruitment-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="recruitment-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      <section className="recruitment-panel recruitment-screening-panel">
        <div className="recruitment-screening-toolbar">
          <div>
            <h3>申请队列</h3>
            <p>当前展示 {visibleItems.length} 份 Application；状态以服务端记录为准</p>
          </div>
          <div className="recruitment-screening-filter-controls">
            <Select
              aria-label="按岗位筛选 Application"
              disabled={batchPending}
              onChange={setJobFilter}
              options={[
                { value: 'all', label: '全部岗位' },
                ...data.jobs.map(job => ({
                  value: job.id,
                  label: `${job.title}${job.status === 'closed' ? '（已关闭）' : ''}`,
                })),
              ]}
              optionFilterProp="label"
              showSearch
              value={jobFilter}
            />
            <Select aria-label="按 AI 状态筛选" disabled={batchPending} onChange={setAiFilter} options={aiStatusOptions} value={aiFilter} />
            <Select aria-label="按 HR 决策筛选" disabled={batchPending} onChange={setHrFilter} options={hrDecisionOptions} value={hrFilter} />
            <Select aria-label="按生命周期筛选" disabled={batchPending} onChange={setLifecycleFilter} options={lifecycleOptions} value={lifecycleFilter} />
            {hasActiveFilters && <Button disabled={batchPending} onClick={clearFilters}>清除筛选</Button>}
            <Button aria-label="刷新 Application 工作队列" disabled={batchPending} icon={<ReloadOutlined />} onClick={() => void loadScreeningCenter()} />
          </div>
        </div>

        {(selectedBatchIds.size > 0 || batchError) && (
          <div aria-live="polite" className="recruitment-screening-batch-bar">
            <div>
              <span>批量初筛</span>
              <strong>{selectedBatchIds.size ? `已选择 ${selectedBatchIds.size}/5 人` : '批次未启动'}</strong>
              <small>{selectedBatchJobTitle ? `${selectedBatchJobTitle} · 一个批次最多选择 5 人且只能选择同一岗位` : '请重新选择需要评分的 Application'}</small>
              {batchError && <em role="alert">{batchError}</em>}
            </div>
            <div>
              <Button disabled={batchPending} onClick={() => setSelectedBatchIds(new Set())}>取消选择</Button>
              <Button
                disabled={!selectedBatchIds.size || batchPending || pendingScreeningIds.size > 0}
                loading={batchPending}
                onClick={runSelectedBatch}
                type="primary"
              >
                开始批量初筛
              </Button>
            </div>
          </div>
        )}

        {data.items.length === 0 ? (
          <Empty
            className="recruitment-panel-empty recruitment-screening-empty"
            description={(
              <div className="recruitment-empty-copy">
                <strong>{hasActiveFilters ? '当前筛选条件下没有 Application' : '新版数据库中还没有 Application'}</strong>
                <span>{hasActiveFilters ? '清除筛选后查看其他申请。' : 'Application 会在 HR 录入或公开投递后出现在这里。'}</span>
              </div>
            )}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            {hasActiveFilters && <Button onClick={clearFilters}>清除筛选</Button>}
          </Empty>
        ) : visibleItems.length === 0 ? (
          <Empty
            className="recruitment-panel-empty recruitment-screening-empty"
            description={<div className="recruitment-empty-copy"><strong>该招聘阶段没有申请</strong><span>点击其他阶段，或清除筛选查看全部 Application。</span></div>}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button onClick={clearFilters}>清除筛选</Button>
          </Empty>
        ) : (
          <div aria-label="Application 工作队列" className="recruitment-application-list" role="list">
            {visibleItems.map(item => {
              const { application, currentResult } = item;
              const aiMeta = AI_STATUS_META[application.aiStatus];
              const hrMeta = HR_DECISION_META[application.hrDecision];
              const lifecycleMeta = LIFECYCLE_META[application.lifecycleStatus];
              const attention = application.aiStatus === 'failed'
                || application.aiStatus === 'blocked'
                || Boolean(currentResult?.isOutdated);
              const screeningPending = pendingScreeningIds.has(application.id);
              const rowDecisionPending = decisionPending
                && decisionItem?.application.id === application.id;
              const batchSelected = selectedBatchIds.has(application.id);
              const batchSelection = getStage7BatchSelectionState(item, {
                selected: batchSelected,
                selectedCount: selectedBatchIds.size,
                selectedJobId: selectedBatchJobId,
                batchPending,
                singlePending: screeningPending || rowDecisionPending,
              });
              const selectedBatchPending = batchPending && batchSelected;
              const action = getStage7SingleScreeningAction(
                item,
                screeningPending || selectedBatchPending || rowDecisionPending,
              );
              const decisionEntry = getStage7DecisionEntry(
                item,
                rowDecisionPending || screeningPending || selectedBatchPending,
              );
              return (
                <article
                  aria-busy={screeningPending || selectedBatchPending || rowDecisionPending}
                  className={`recruitment-application-row${attention ? ' needs-attention' : ''}${screeningPending || selectedBatchPending || rowDecisionPending ? ' is-running' : ''}${batchSelected ? ' is-selected' : ''}`}
                  key={application.id}
                  role="listitem"
                >
                  <div className="recruitment-application-id">
                    <Tooltip title={batchSelection.reason}>
                      <span className="recruitment-application-checkbox">
                        <Checkbox
                          aria-label={`选择 Application #${application.id} 加入批量初筛`}
                          checked={batchSelected}
                          disabled={!batchSelection.allowed}
                          onChange={() => toggleBatchSelection(item)}
                        />
                      </span>
                    </Tooltip>
                    <span>APP</span><strong>#{application.id}</strong>
                  </div>
                  <div className="recruitment-application-person">
                    <Link to={`/app/candidates/${application.candidateId}`}>{item.candidateName}</Link>
                    <span>{item.candidateTitle || item.candidateSource || `候选人 #${application.candidateId}`}</span>
                    <small>{SOURCE_LABELS[application.source]} · {formatDateTime(application.appliedAt)} 投递</small>
                  </div>
                  <div className="recruitment-application-job">
                    <strong>{item.jobTitle}</strong>
                    <span>{item.jobDepartment || `岗位 #${application.jobId}`}</span>
                    {item.jobStatus === 'closed' && <Tag bordered={false} className="recruitment-status-tag is-neutral">岗位已关闭</Tag>}
                  </div>
                  <div className="recruitment-application-ai-state">
                    <div>
                      <Tag bordered={false} className={`recruitment-status-tag is-${aiMeta.tone}`}>{aiMeta.label}</Tag>
                      {currentResult?.isOutdated && <Tag bordered={false} className="recruitment-status-tag is-danger">结果已过期</Tag>}
                    </div>
                    <p>{getStatusMessage(item)}</p>
                  </div>
                  <div className="recruitment-application-result">
                    <span>当前结论</span>
                    <strong>{currentResult?.overallScore ?? '—'}<small>{currentResult?.overallScore === null || !currentResult ? '' : ' 分'}</small></strong>
                    <em>{currentResult ? `第 ${currentResult.attemptNumber} 次 · ${currentResult.recommendation || '暂无推荐方向'}` : '还没有评分结果'}</em>
                  </div>
                  <div className="recruitment-application-decision">
                    <Tag bordered={false} className={`recruitment-status-tag is-${hrMeta.tone}`}>{hrMeta.label}</Tag>
                    <Tag bordered={false} className={`recruitment-status-tag is-${lifecycleMeta.tone}`}>{lifecycleMeta.label}</Tag>
                    {!application.currentResumeId && <span>未绑定简历</span>}
                  </div>
                  <div className="recruitment-application-action">
                    <Button
                      className={decisionEntry.allowed ? 'recruitment-decision-entry is-ready' : 'recruitment-decision-entry'}
                      disabled={!decisionEntry.allowed}
                      icon={<SafetyCertificateOutlined />}
                      loading={rowDecisionPending}
                      onClick={() => openDecisionDialog(item)}
                      size="small"
                    >
                      {decisionEntry.label}
                    </Button>
                    <Button
                      icon={<HistoryOutlined />}
                      onClick={() => setDetailItem(item)}
                      size="small"
                    >
                      评分记录
                    </Button>
                    <Button
                      disabled={!action.allowed}
                      loading={screeningPending}
                      onClick={() => {
                        if (action.requiresForceConfirmation) openForceRerunConfirmation(item);
                        else void runSingleScreening(item);
                      }}
                      size="small"
                      type={action.allowed && !action.requiresForceConfirmation ? 'primary' : 'default'}
                    >
                      {action.label}
                    </Button>
                    <span>{decisionEntry.allowed ? decisionEntry.reason : action.reason}</span>
                    {screeningErrors[application.id] && (
                      <em role="alert">{screeningErrors[application.id]}</em>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <Modal
        cancelButtonProps={{ disabled: intakeGuardRef.current.pending }}
        cancelText="取消录入"
        className="recruitment-intake-modal"
        closable={!intakeGuardRef.current.pending}
        confirmLoading={intakeGuardRef.current.pending}
        destroyOnClose
        maskClosable={!intakeGuardRef.current.pending}
        okButtonProps={{ disabled: !openJobs.length }}
        okText="保存并开始 AI 初筛"
        onCancel={() => void closeIntakeDialog()}
        onOk={() => void submitIntake()}
        open={intakeOpen}
        title="录入新申请"
        width={760}
      >
        <div className="recruitment-intake-sheet">
          <header>
            <span>内部初筛入口 · source=hr_screening</span>
            <strong>先保存申请，再由 AI 提供证据</strong>
            <p>本入口不会让候选人直接通过；评分结束后仍须由 HR 作出决定。</p>
          </header>

          <ol aria-label="新申请处理流程" className="recruitment-intake-rail">
            <li className={intakeProgress === 'uploading' || intakeProgress === 'extracting' || intakeProgress === 'saving' || intakeProgress === 'screening' ? 'is-active' : ''}>
              <b>1</b><span><strong>保存申请</strong><small>校验联系方式、岗位和简历</small></span>
            </li>
            <li className={intakeProgress === 'screening' ? 'is-active' : ''}>
              <b>2</b><span><strong>AI 初筛</strong><small>失败不会删除已保存申请</small></span>
            </li>
            <li>
              <b>3</b><span><strong>HR 决策</strong><small>通过后才进入候选人页面</small></span>
            </li>
          </ol>

          {!openJobs.length && (
            <Alert
              description="请先在岗位管理中创建或重新开放岗位，关闭岗位不能接收新申请。"
              message="目前没有可录入申请的开放岗位"
              showIcon
              type="warning"
            />
          )}

          <Form form={intakeForm} layout="vertical" requiredMark="optional">
            <div className="recruitment-intake-contact-grid">
              <Form.Item
                label="候选人姓名"
                name="name"
                rules={[{ required: true, message: '请填写候选人姓名' }, { max: 100, message: '姓名不能超过 100 个字符' }]}
              >
                <Input autoComplete="name" maxLength={100} placeholder="例如：张三" />
              </Form.Item>
              <Form.Item
                label="开放岗位"
                name="jobId"
                rules={[{ required: true, message: '请选择开放岗位' }]}
              >
                <Select
                  disabled={!openJobs.length}
                  optionFilterProp="label"
                  options={openJobs.map(job => ({
                    value: job.id,
                    label: `${job.title}${job.department ? ` · ${job.department}` : ''}`,
                  }))}
                  placeholder="选择本次申请的岗位"
                  showSearch
                />
              </Form.Item>
              <Form.Item
                label="手机号码"
                name="phone"
                rules={[{ required: true, message: '请填写有效手机号' }]}
              >
                <Input autoComplete="tel" placeholder="支持国家区号，例如 +86 13800138000" />
              </Form.Item>
              <Form.Item
                label="电子邮箱"
                name="email"
                rules={[{ required: true, message: '请填写有效邮箱' }, { type: 'email', message: '邮箱格式无效' }]}
              >
                <Input autoComplete="email" placeholder="candidate@example.com" />
              </Form.Item>
            </div>

            <section className="recruitment-intake-resume-section">
              <div className="recruitment-intake-section-heading">
                <div><strong>本次申请使用的简历</strong><span>必须有可提取的原文，才能完成 AI 初筛</span></div>
                <Radio.Group
                  buttonStyle="solid"
                  disabled={intakeGuardRef.current.pending}
                  onChange={event => void changeIntakeResumeMode(event.target.value)}
                  optionType="button"
                  options={[
                    { label: '上传新简历', value: 'upload' },
                    { label: '选择已有简历', value: 'existing' },
                  ]}
                  value={intakeResumeMode}
                />
              </div>

              {intakeResumeMode === 'upload' ? (
                <Upload.Dragger
                  accept=".pdf,.docx,.txt"
                  beforeUpload={file => selectIntakeFile(file)}
                  disabled={intakeGuardRef.current.pending}
                  maxCount={1}
                  multiple={false}
                  showUploadList={false}
                >
                  <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                  <p className="ant-upload-text">{intakeFile ? intakeFile.name : '点击或拖入候选人简历'}</p>
                  <p className="ant-upload-hint">支持 PDF、DOCX、TXT；提交时上传并提取原文</p>
                  {preparedResume && <Tag color="green">已准备 Resume #{preparedResume.id}</Tag>}
                </Upload.Dragger>
              ) : (
                <Form.Item
                  className="recruitment-intake-existing-resume"
                  name="resumeId"
                  rules={[{ required: true, message: '请选择一份已解析简历' }]}
                >
                  <Select
                    disabled={intakeResumeLoad.status === 'loading'}
                    loading={intakeResumeLoad.status === 'loading'}
                    notFoundContent={intakeResumeLoad.status === 'error'
                      ? '简历列表加载失败'
                      : '没有可用的已解析简历'}
                    optionFilterProp="label"
                    options={parsedIntakeResumes.map(resume => ({
                      value: resume.id,
                      label: `${resume.filename} · ${resume.candidateName} · Resume #${resume.id}`,
                    }))}
                    placeholder="按文件名或候选人搜索"
                    showSearch
                  />
                </Form.Item>
              )}

              {intakeResumeMode === 'existing' && intakeResumeLoad.status === 'error' && (
                <Alert
                  action={<Button onClick={() => void loadIntakeResumeOptions()} size="small">重新加载</Button>}
                  message={intakeResumeLoad.message}
                  showIcon
                  type="error"
                />
              )}
            </section>
          </Form>

          {intakeProgress !== 'idle' && (
            <div aria-live="polite" className="recruitment-intake-progress">
              <UploadOutlined />
              <span><strong>{intakeProgressLabel[intakeProgress]}</strong><small>请不要关闭窗口或重复提交</small></span>
            </div>
          )}
          {intakeError && <Alert message={intakeError} role="alert" showIcon type="error" />}
          <footer>联系方式用于安全复用 Candidate；系统不会把手机号、邮箱等敏感资料交给评分模型。</footer>
        </div>
      </Modal>

      <Drawer
        className="recruitment-screening-batch-drawer"
        destroyOnClose
        onClose={() => setBatchResult(null)}
        open={Boolean(batchResult)}
        title="批量评分逐项结果"
        width="min(620px, 100vw)"
      >
        {batchResult && (
          <>
            <Alert
              description="批量评分不会自动通过或淘汰候选人。失败、资料不足和跳过项需要 HR 分别处理。"
              message={`岗位 #${batchResult.outcome.jobId} · 已选择 ${batchResult.outcome.summary.selected} 人，实际执行 ${batchResult.outcome.summary.executed} 人`}
              showIcon
              type="info"
            />
            <div aria-label="批量评分汇总" className="recruitment-screening-batch-summary">
              {([
                ['完成', batchResult.outcome.summary.completed],
                ['失败', batchResult.outcome.summary.failed],
                ['资料不足', batchResult.outcome.summary.blocked],
                ['复用', batchResult.outcome.summary.reused],
                ['跳过', batchResult.outcome.summary.skipped],
              ] as const).map(([label, value]) => <span key={label}><strong>{value}</strong><small>{label}</small></span>)}
            </div>
            <div aria-label="批量评分逐项结果" className="recruitment-screening-batch-results" role="list">
              {batchResult.outcome.items.map(result => {
                const statusMeta = BATCH_STATUS_META[result.status];
                return (
                  <article key={result.applicationId} role="listitem">
                    <div>
                      <strong>{batchResult.candidateLabels[result.applicationId] || `Application #${result.applicationId}`}</strong>
                      <span>Application #{result.applicationId}{result.attemptNumber ? ` · 第 ${result.attemptNumber} 次` : ''}</span>
                    </div>
                    <Tag bordered={false} className={`recruitment-status-tag is-${statusMeta.tone}`}>{statusMeta.label}</Tag>
                    <p>{result.errorMessage || (result.reused ? '已复用相同输入的成功结果。' : result.modelCalled ? '本项已调用评分模型。' : '本项未调用评分模型。')}</p>
                  </article>
                );
              })}
            </div>
            <div className="recruitment-screening-batch-footer">
              <span>{getStage7FailedBatchApplicationIds(batchResult.outcome).length
                ? '仅失败项可以重新组成批次；已完成和 blocked 不会被误重跑。'
                : '当前批次没有可重试的 failed 项。'}</span>
              <Button
                disabled={!getStage7FailedBatchApplicationIds(batchResult.outcome).length || batchPending}
                loading={batchPending}
                onClick={retryFailedBatch}
                type="primary"
              >
                仅重试失败项
              </Button>
            </div>
          </>
        )}
      </Drawer>

      <RecruitmentScreeningDetailDrawer
        item={detailItem}
        onClose={() => setDetailItem(null)}
      />

      <Modal
        cancelButtonProps={{
          disabled: Boolean(forceRerunItem && pendingScreeningIds.has(forceRerunItem.application.id)),
        }}
        cancelText="取消"
        className="recruitment-force-rerun-modal"
        closable={!(forceRerunItem && pendingScreeningIds.has(forceRerunItem.application.id))}
        confirmLoading={Boolean(forceRerunItem && pendingScreeningIds.has(forceRerunItem.application.id))}
        destroyOnClose
        maskClosable={!(forceRerunItem && pendingScreeningIds.has(forceRerunItem.application.id))}
        okButtonProps={{ danger: true, disabled: !forceRerunReason.trim() }}
        okText="确认强制重跑"
        onCancel={closeForceRerunConfirmation}
        onOk={() => void confirmForceRerun()}
        open={forceRerunItem !== null}
        title="确认强制重跑 AI 初筛？"
      >
        {forceRerunItem && (
          <div className="recruitment-force-rerun-content">
            <Alert
              description="系统会真正重新调用一次 DeepSeek，并新增一条不可变评分记录。如果本次运行失败，当前成功结果仍会保留。"
              message="这不是普通重试，可能产生新的模型调用耗时和费用"
              showIcon
              type="warning"
            />
            <dl className="recruitment-force-rerun-context">
              <div><dt>候选人</dt><dd>{forceRerunItem.candidateName}</dd></div>
              <div><dt>岗位</dt><dd>{forceRerunItem.jobTitle}</dd></div>
              <div>
                <dt>当前评分</dt>
                <dd>
                  {forceRerunItem.currentResult?.overallScore ?? '—'} 分
                  {forceRerunItem.currentResult
                    ? ` · 第 ${forceRerunItem.currentResult.attemptNumber} 次`
                    : ''}
                </dd>
              </div>
            </dl>
            <label htmlFor="stage7-force-rerun-reason">重跑原因</label>
            <Input.TextArea
              autoFocus
              id="stage7-force-rerun-reason"
              maxLength={1000}
              onChange={event => setForceRerunReason(event.target.value)}
              placeholder="例如：需要对同一份材料进行人工抽查，重新复核模型判断"
              rows={4}
              showCount
              value={forceRerunReason}
            />
            <p>原因会随本次操作进入审计记录；AI 结果不会自动改变 HR 决策。</p>
          </div>
        )}
      </Modal>

      <Modal
        cancelButtonProps={{ disabled: decisionPending }}
        cancelText="取消"
        className="recruitment-decision-modal"
        closable={!decisionPending}
        confirmLoading={decisionPending}
        destroyOnClose
        maskClosable={!decisionPending}
        okButtonProps={{
          danger: decisionKind === 'reject',
          disabled: !decisionBuildResult?.valid,
        }}
        okText={decisionKind ? `确认${DECISION_KIND_META[decisionKind].label}` : '确认决定'}
        onCancel={closeDecisionDialog}
        onOk={() => void submitHRDecision()}
        open={decisionItem !== null}
        title="HR 初筛决策单"
        width={720}
      >
        {decisionItem && (
          <div className="recruitment-decision-sheet">
            <header className="recruitment-decision-sheet-header">
              <div>
                <span>Application #{decisionItem.application.id}</span>
                <strong>{decisionItem.candidateName}</strong>
                <p>{decisionItem.jobTitle}</p>
              </div>
              <div aria-label="HR 决策状态变化" className="recruitment-decision-transition">
                <span>{HR_DECISION_META[decisionItem.application.hrDecision].label}</span>
                <b>→</b>
                <strong>{decisionKind ? DECISION_KIND_META[decisionKind].label : '请选择去向'}</strong>
              </div>
            </header>

            <div aria-label="可执行的 HR 决策" className="recruitment-decision-options" role="group">
              {availableDecisionKinds.map(kind => {
                const meta = DECISION_KIND_META[kind];
                return (
                  <button
                    aria-pressed={decisionKind === kind}
                    className={`is-${meta.tone}${decisionKind === kind ? ' is-selected' : ''}`}
                    key={kind}
                    onClick={() => selectDecisionKind(kind)}
                    type="button"
                  >
                    {meta.icon}
                    <span><strong>{meta.label}</strong><small>{meta.note}</small></span>
                  </button>
                );
              })}
            </div>

            {decisionKind === 'reject' && (
              <Alert
                description="确认后本岗位申请将结束，但 Candidate、Application、简历、评分和阶段历史都不会删除。"
                message="淘汰是高风险决定，请只使用岗位相关依据"
                showIcon
                type="error"
              />
            )}
            {decisionKind === 'undo_rejection' && (
              <Alert
                description="撤销后只回到 HR 待审核，不会自动通过，也不会自动重新运行 AI 评分。"
                message="本次操作会形成一条新的决定反转历史"
                showIcon
                type="info"
              />
            )}
            {passPolicy && (
              <Alert
                description={passPolicy.note}
                message={passPolicy.label}
                showIcon
                type={passPolicy.reasonCode === 'manual_override' ? 'warning' : 'success'}
              />
            )}

            {decisionKind && decisionKind !== 'pass' && (
              <label className="recruitment-decision-field" htmlFor="stage7-decision-reason-code">
                <span>业务原因 <b>*</b></span>
                <Select
                  id="stage7-decision-reason-code"
                  onChange={value => {
                    setDecisionReasonCode(value);
                    setDecisionError(null);
                  }}
                  options={decisionReasonOptions}
                  placeholder="请选择岗位相关原因"
                  value={decisionReasonCode}
                />
              </label>
            )}

            {decisionKind && (
              <label className="recruitment-decision-field" htmlFor="stage7-decision-reason-detail">
                <span>
                  具体说明 {decisionDetailRequired ? <b>*</b> : <small>选填</small>}
                </span>
                <Input.TextArea
                  id="stage7-decision-reason-detail"
                  maxLength={1000}
                  onChange={event => {
                    setDecisionReasonDetail(event.target.value);
                    setDecisionError(null);
                  }}
                  placeholder="只记录与岗位要求、候选人证据或决定修正有关的事实，不填写性别、年龄、民族、婚姻等敏感依据"
                  rows={4}
                  showCount
                  value={decisionReasonDetail}
                />
              </label>
            )}

            {decisionError && <Alert message={decisionError} role="alert" showIcon type="error" />}
            <footer>
              AI 评分只提供证据和建议；本次决定由 HR 作出，并写入阶段历史与操作日志。
            </footer>
          </div>
        )}
      </Modal>
    </main>
  );
};

export default RecruitmentScreeningCenter;
