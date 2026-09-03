import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  FileSearchOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Alert, Button, Drawer, Empty, Modal, Select, Skeleton, Tag, Tooltip } from 'antd';
import {
  getAIScreeningApiError,
  getApplicationScreening,
  getJobEvaluationPlan,
  listApplicationScreeningReports,
  reassessApplicationScreening,
  triggerApplicationScreening,
} from './services/aiScreening';
import type { JobStatus } from './services/jobs';
import {
  SCREENING_POLL_INTERVAL_MS,
  SCREENING_STATUS_META,
  SCREENING_WAITING_REASON_META,
  shouldApplyScreeningResponse,
  shouldPollScreeningStatus,
} from './screeningPresentation';
import type { JobEvaluationPlan, ScreeningReport, ScreeningState } from './types/aiScreening';
import ScreeningReportView from './ScreeningReportView';
import PublicApplicationProcessingPanel from './PublicApplicationProcessingPanel';
import type { PublicApplicationWorkbenchSummary } from './services/publicApplicationWorkbench';
import {
  getRecruitmentResume,
  getRecruitmentResumeFileUrl,
  getStoredRecruitmentResumeStructure,
  type RecruitmentResumeDetail,
} from './services/resumes';
import {
  listApplicationInterviews,
  listApplicationTimeline,
  type InterviewListItem,
  type TimelineItem,
} from './services/recruitmentPipeline';
import type { ScreeningCenterItem } from './services/screeningCenter';
import type { ResumeParseDraft } from './types/resumeStructure';

type Props = {
  applicationId: number | null;
  candidateName: string;
  initialState: ScreeningState | null;
  jobId: number | null;
  jobStatus: JobStatus | null;
  jobTitle: string;
  currentResumeId: number | null;
  publicSubmission: PublicApplicationWorkbenchSummary | null;
  open: boolean;
  onClose: () => void;
  onStateChange?: (state: ScreeningState) => void;
  onPublicSubmissionChange?: (summary: PublicApplicationWorkbenchSummary) => void;
  onCurrentResumeChange?: (resumeId: number) => void;
  summary?: ScreeningCenterItem | null;
};

const formatReportDate = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date);
};

const ApplicationScreeningDrawer: React.FC<Props> = ({
  applicationId,
  candidateName,
  initialState,
  jobId,
  jobStatus,
  jobTitle,
  currentResumeId,
  publicSubmission,
  open,
  onClose,
  onStateChange,
  onPublicSubmissionChange,
  onCurrentResumeChange,
  summary,
}) => {
  const [state, setState] = useState<ScreeningState | null>(initialState);
  const [plan, setPlan] = useState<JobEvaluationPlan | null>(null);
  const [reportHistory, setReportHistory] = useState<ScreeningReport[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [initialLoading, setInitialLoading] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [resume, setResume] = useState<RecruitmentResumeDetail | null>(null);
  const [resumeStructureNote, setResumeStructureNote] = useState('正在读取已保存的结构化结果…');
  const [resumeDraft, setResumeDraft] = useState<ResumeParseDraft | null>(null);
  const [interviews, setInterviews] = useState<InterviewListItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [modal, modalContextHolder] = Modal.useModal();
  const requestIdRef = useRef(0);

  const applyState = useCallback((next: ScreeningState) => {
    setState(next);
    setRefreshError(null);
    onStateChange?.(next);
  }, [onStateChange]);

  const loadState = useCallback(async (showLoading = false): Promise<ScreeningState | null> => {
    if (!applicationId || !open) return null;
    const requestId = ++requestIdRef.current;
    if (showLoading) setInitialLoading(true);
    try {
      const next = await getApplicationScreening(applicationId);
      if (shouldApplyScreeningResponse(requestId, requestIdRef.current)) applyState(next);
      return next;
    } catch (error) {
      if (!shouldApplyScreeningResponse(requestId, requestIdRef.current)) return null;
      setRefreshError(getAIScreeningApiError(error).message);
      return null;
    } finally {
      if (showLoading && shouldApplyScreeningResponse(requestId, requestIdRef.current)) {
        setInitialLoading(false);
      }
    }
  }, [applicationId, applyState, open]);

  useEffect(() => {
    if (!open || !applicationId) return undefined;
    let cancelled = false;
    setState(initialState);
    setPlan(null);
    setReportHistory([]);
    setSelectedReportId(null);
    setRefreshError(null);
    void loadState(initialState === null);
    if (jobId) {
      void getJobEvaluationPlan(jobId)
        .then(nextPlan => { if (!cancelled) setPlan(nextPlan); })
        .catch(() => { if (!cancelled) setPlan(null); });
    }
    void listApplicationScreeningReports(applicationId)
      .then(reports => { if (!cancelled) setReportHistory(reports); })
      .catch(() => { if (!cancelled) setReportHistory([]); });
    return () => {
      cancelled = true;
      requestIdRef.current += 1;
    };
    // initialState is intentionally read only when opening or switching Application.
    // Poll responses update the parent snapshot and must not restart the initial request.
  }, [applicationId, jobId, loadState, open]);

  useEffect(() => {
    if (!open || !applicationId || !currentResumeId) return undefined;
    let cancelled = false;
    setResume(null);
    setResumeDraft(null);
    setResumeStructureNote('正在读取已保存的结构化结果…');
    void Promise.allSettled([
      getRecruitmentResume(currentResumeId),
      getStoredRecruitmentResumeStructure(currentResumeId),
      listApplicationInterviews(applicationId),
      listApplicationTimeline(applicationId),
    ]).then(([resumeResult, structureResult, interviewResult, timelineResult]) => {
      if (cancelled) return;
      if (resumeResult.status === 'fulfilled') setResume(resumeResult.value);
      setResumeStructureNote(structureResult.status === 'fulfilled'
        ? structureResult.value.draft
          ? structureResult.value.has_previous_draft && structureResult.value.structure_status === 'failed'
            ? '本次结构化失败，仍保留上一次成功草稿。'
            : '已读取最近一次成功保存的结构化草稿。'
          : '当前没有可读取的结构化草稿。'
        : '结构化状态暂时无法读取；不会触发新的 AI 调用。');
      setResumeDraft(structureResult.status === 'fulfilled' ? structureResult.value.draft : null);
      setInterviews(interviewResult.status === 'fulfilled' ? interviewResult.value : []);
      setTimeline(timelineResult.status === 'fulfilled' ? timelineResult.value : []);
    });
    return () => { cancelled = true; };
  }, [applicationId, currentResumeId, open]);

  useEffect(() => {
    const status = state?.latestRun?.status;
    if (!open || !applicationId || !shouldPollScreeningStatus(status)) return undefined;
    let cancelled = false;
    let timerId: number | undefined;
    const schedule = () => {
      timerId = window.setTimeout(async () => {
        const next = await loadState(false);
        if (!cancelled && (!next || shouldPollScreeningStatus(next.latestRun?.status))) schedule();
      }, SCREENING_POLL_INTERVAL_MS);
    };
    schedule();
    return () => {
      cancelled = true;
      if (timerId !== undefined) window.clearTimeout(timerId);
    };
  }, [applicationId, loadState, open, state?.latestRun?.id, state?.latestRun?.status]);

  const submitAction = async (reassess: boolean) => {
    if (!applicationId || actionPending || jobStatus === 'closed') return;
    setActionPending(true);
    setRefreshError(null);
    try {
      const result = reassess
        ? await reassessApplicationScreening(applicationId)
        : await triggerApplicationScreening(applicationId);
      const next: ScreeningState = {
        applicationId,
        report: result.report ?? state?.report ?? null,
        latestRun: result.run ?? state?.latestRun ?? null,
      };
      applyState(next);
      setSelectedReportId(null);
      void listApplicationScreeningReports(applicationId).then(setReportHistory).catch(() => undefined);
      if (result.reusedReport) {
        modal.info({ title: '已复用当前报告', content: '输入没有变化，普通初筛没有重复调用模型。' });
      } else if (result.reusedRun) {
        modal.info({ title: '已复用正在进行的任务', content: '相同输入已有任务，页面会继续跟踪该运行。' });
      }
    } catch (error) {
      setRefreshError(getAIScreeningApiError(error).message);
    } finally {
      setActionPending(false);
    }
  };

  const confirmReassessment = () => {
    modal.confirm({
      title: '确认重新评估？',
      content: '系统将使用当前最新评价引擎创建新运行。新结果成功前，旧成功报告会继续保留。',
      okText: '重新评估',
      cancelText: '取消',
      onOk: () => submitAction(true),
    });
  };

  const run = state?.latestRun ?? null;
  const currentReport = state?.report ?? null;
  const report = selectedReportId === null
    ? currentReport
    : reportHistory.find(item => item.id === selectedReportId) ?? currentReport;
  const polling = shouldPollScreeningStatus(run?.status);
  const waitingReason = run?.waitingReason ?? null;
  const waitingReasonMeta = waitingReason
    ? SCREENING_WAITING_REASON_META[waitingReason]
    : null;
  const actionDisabled = jobStatus === 'closed' || polling;
  const actionDisabledReason = jobStatus === 'closed'
    ? '岗位关闭时不能开始或重新评估'
    : polling
      ? '当前已有评估正在排队或运行'
      : '';
  const runAlertType = run?.status === 'failed'
    ? 'error'
    : run?.status === 'succeeded'
      ? 'success'
      : run?.status === 'waiting_resume' || run?.status === 'waiting_plan'
        ? 'warning'
        : 'info';

  return (
    <>
    {modalContextHolder}
    <Drawer
      className="recruitment-screening-report-drawer"
      destroyOnClose
      extra={(
        <div className="recruitment-screening-drawer-actions">
          <Button icon={<ReloadOutlined />} onClick={() => void loadState(false)}>刷新</Button>
          <Tooltip title={actionDisabledReason}>
            <span>
              <Button
                disabled={actionDisabled}
                loading={actionPending}
                onClick={report ? confirmReassessment : () => void submitAction(false)}
                type="primary"
              >
                {report ? '重新评估' : '开始初筛'}
              </Button>
            </span>
          </Tooltip>
        </div>
      )}
      onClose={onClose}
      open={open}
      title={applicationId ? `${candidateName} · Application #${applicationId}` : 'AI 初筛报告'}
      width="min(980px, 100vw)"
    >
      <div className="recruitment-unified-detail-sections">
        <section aria-labelledby="application-overview-title" className="recruitment-unified-detail-card">
          <div><span>01</span><h3 id="application-overview-title">申请概览</h3></div>
          <p>{candidateName} · {jobTitle}</p>
          <div className="recruitment-unified-detail-meta">
            <Tag>{summary?.source === 'public_apply' ? '公开投递' : '内部录入'}</Tag>
            {summary && <Tag>{summary.recruitmentStage}</Tag>}
            {summary && <Tag>{summary.hrDecision}</Tag>}
            {summary?.finalOutcome && <Tag color="default">{summary.finalOutcome}</Tag>}
          </div>
        </section>
        <section aria-labelledby="resume-section-title" className="recruitment-unified-detail-card">
          <div><span>02</span><h3 id="resume-section-title">简历</h3></div>
          {resume ? <>
            <p><strong>{resume.filename}</strong> · {resume.parseStatus} · 上传于 {formatReportDate(resume.uploadedAt)}</p>
            <p>{resumeStructureNote}</p>
            {resumeDraft && <p>已保存结构：{resumeDraft.work_experiences.length} 段工作经历、{resumeDraft.project_experiences.length} 个项目、{resumeDraft.skills.length} 项技能。</p>}
            <details className="recruitment-resume-text-preview"><summary>查看已保存的简历文本</summary><pre>{resume.rawText || '当前没有已保存的简历文本。'}</pre></details>
            <Button href={getRecruitmentResumeFileUrl(resume.id, true)} rel="noopener noreferrer" target="_blank">下载当前简历</Button>
          </> : <p>简历元数据暂时无法读取；报告和其它业务记录仍可继续查看。</p>}
        </section>
        <section aria-labelledby="interview-section-title" className="recruitment-unified-detail-card">
          <div><span>04</span><h3 id="interview-section-title">面试</h3></div>
          {interviews.length ? interviews.map(item => <p key={item.id}>第 {item.roundNumber} 轮 · {item.status} · {formatReportDate(item.scheduledStartAt)} · {item.decision}</p>) : <p>暂无面试记录。安排和反馈操作将在面试工作流中进行。</p>}
        </section>
        <section aria-labelledby="offer-section-title" className="recruitment-unified-detail-card is-future">
          <div><span>05</span><h3 id="offer-section-title">Offer</h3></div>
          <p>Offer 是独立业务节点，将在 9D 开放；本阶段不读取薪资，也不提供操作。</p>
        </section>
        <section aria-labelledby="timeline-section-title" className="recruitment-unified-detail-card">
          <div><span>06</span><h3 id="timeline-section-title">时间线</h3></div>
          {timeline.length ? timeline.slice(0, 8).map(item => <p key={`${item.eventType}-${item.sourceId}`}>{formatReportDate(item.occurredAt)} · {item.actorLabel} · {item.reasonCode}{item.reasonDetail ? ` · ${item.reasonDetail}` : ''}</p>) : <p>暂无可展示的招聘事件。</p>}
        </section>
      </div>
      {publicSubmission && currentResumeId && (
        <PublicApplicationProcessingPanel
          currentResumeId={currentResumeId}
          onResumeChange={resumeId => onCurrentResumeChange?.(resumeId)}
          onSummaryChange={summary => onPublicSubmissionChange?.(summary)}
          summary={publicSubmission}
        />
      )}
      <div className="recruitment-screening-context">
        <span><RobotOutlined /> 03 · AI 岗位匹配建议</span>
        <strong>{jobTitle}</strong>
        <p>报告只解释当前简历与岗位的匹配情况，不会代替 HR 作出决定。</p>
      </div>

      {reportHistory.length > 1 && (
        <div className="recruitment-screening-report-history" aria-label="成功报告历史">
          <div><span>报告版本</span><strong>{selectedReportId === null ? '当前成功报告' : '历史只读报告'}</strong></div>
          <Select
            aria-label="选择成功报告版本"
            value={selectedReportId ?? currentReport?.id}
            onChange={reportId => setSelectedReportId(reportId === currentReport?.id ? null : reportId)}
            options={reportHistory.map(item => ({
              value: item.id,
              label: `报告 #${item.id} · ${item.isCurrent ? '当前' : '历史'} · ${item.overallScore} 分 · ${formatReportDate(item.generatedAt)}`,
            }))}
          />
        </div>
      )}

      {initialLoading && !state && <Skeleton active paragraph={{ rows: 10 }} />}

      {refreshError && (
        <Alert
          action={<Button onClick={() => void loadState(false)}>重试</Button>}
          className="recruitment-screening-state-alert"
          description="页面不会展示内部异常。请检查网络或根据后端安全提示稍后重试。"
          message={refreshError}
          showIcon
          type="error"
        />
      )}

      {run && (
        <Alert
          className="recruitment-screening-state-alert"
          description={(
            <div className="recruitment-run-state-copy">
              <span>{SCREENING_STATUS_META[run.status].description}</span>
              {waitingReasonMeta && (
                <strong>{waitingReasonMeta.label}：{waitingReasonMeta.description}</strong>
              )}
              {run.errorCode && <Tag>{run.errorCode}</Tag>}
              {run.errorMessage && <span>{run.errorMessage}</span>}
              {report && (run.status === 'queued' || run.status === 'running' || run.status === 'failed') && (
                <strong>下方旧成功报告仍然保留并可继续查看。</strong>
              )}
            </div>
          )}
          icon={<SafetyCertificateOutlined />}
          message={(
            <span>
              {SCREENING_STATUS_META[run.status].label}
              {polling && <Tag color="processing">每 4 秒自动刷新</Tag>}
            </span>
          )}
          showIcon
          type={runAlertType}
        />
      )}

      {!initialLoading && !report && !run && !refreshError && (
        <Empty
          className="recruitment-screening-report-empty"
          description="当前 Application 尚无成功报告，也没有运行记录。"
          image={<FileSearchOutlined />}
        >
          <Tooltip title={jobStatus === 'closed' ? '岗位关闭时不能开始初筛' : ''}>
            <span><Button disabled={jobStatus === 'closed'} onClick={() => void submitAction(false)} type="primary">开始初筛</Button></span>
          </Tooltip>
        </Empty>
      )}

      {!report && run && ['waiting_resume', 'waiting_plan', 'failed', 'paused'].includes(run.status) && (
        <Empty
          className="recruitment-screening-report-empty"
          description={run.status === 'failed'
            ? '最近运行失败，当前没有可展示的成功报告。处理问题后可重新开始初筛。'
            : '条件满足并完成评估后，完整报告会显示在这里。'}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}

      {report && <ScreeningReportView plan={plan} report={report} />}
    </Drawer>
    </>
  );
};

export default ApplicationScreeningDrawer;
