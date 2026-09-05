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
import OfferPipelinePanel from './OfferPipelinePanel';
import InterviewPipelinePanel from './InterviewPipelinePanel';

type Props = {
  workspace: 'screening' | 'candidate';
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
  onPipelineChange?: () => Promise<void> | void;
  summary?: ScreeningCenterItem | null;
};

const formatReportDate = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date);
};

const STAGE_LABELS = {
  applied: '已申请',
  hr_review: 'HR 初筛',
  screening_passed: '初筛通过',
  backup: '初筛备选',
  rejected: '初筛淘汰',
  interview: '面试中',
  offer: 'Offer 沟通',
  offer_accepted: 'Offer 已接受',
  admitted: '已录取待入职',
  hired: '已正式入职',
} as const;

const DECISION_LABELS = {
  pending: '待 HR 决定',
  passed: 'HR 已通过',
  backup: '备选',
  rejected: '已淘汰',
} as const;

const FINAL_OUTCOME_LABELS = {
  screening_rejected: '初筛淘汰',
  interview_rejected: '面试淘汰',
  interview_no_show: '面试未到场',
  offer_declined: '候选人拒绝 Offer',
  offer_withdrawn: '公司撤回 Offer',
  offer_expired: 'Offer 已过期',
  candidate_withdrew: '候选人退出',
  company_canceled: '公司取消流程',
  hired: '已正式入职',
} as const;

const RESUME_STATUS_LABELS = {
  uploaded: '等待解析',
  parsing: '解析中',
  parsed: '解析完成',
  failed: '解析失败',
} as const;

const TIMELINE_REASON_LABELS: Record<string, string> = {
  application_created: '创建岗位申请',
  public_application_received: '收到公开投递',
  hr_direct_entry: 'HR 内部录入',
  meets_requirements: 'HR 初筛通过',
  minor_capability_gap: '因轻微能力差距转为备选',
  waiting_for_comparison: '等待横向比较',
  limited_headcount: '因名额有限转为备选',
  information_pending: '等待补充信息',
  compensation_pending: '等待薪酬沟通',
  availability_pending: '等待到岗时间确认',
  required_skill_missing: '缺少岗位必需技能',
  work_experience_insufficient: '工作经验不足',
  education_requirement_not_met: '学历要求未满足',
  required_experience_missing: '缺少必需经历',
  role_mismatch: '岗位匹配度不足',
  new_evidence: '根据新证据调整决定',
  candidate_information_updated: '候选人信息更新后调整决定',
  job_requirements_changed: '岗位要求变化后调整决定',
  decision_correction: '修正此前决定',
  hr_reassessment: 'HR 重新评估',
  duplicate_entry: '作废重复申请',
  wrong_job: '作废错误岗位申请',
  entry_error: '作废误录申请',
  ai_screening_completed: 'AI 岗位匹配分析完成',
  ai_screening_failed: 'AI 岗位匹配分析失败',
  interview_scheduled: '安排面试',
  interview_rescheduled: '调整面试安排',
  interview_canceled: '取消面试',
  interview_no_show: '记录面试未到场',
  interview_round_completed: '完成本轮面试',
  interview_next_round: '进入下一轮面试',
  interview_proceed_offer: '面试通过并进入 Offer',
  interview_rejected: '面试淘汰',
  candidate_withdrew: '候选人退出流程',
  offer_created: '创建 Offer 草稿',
  offer_sent: '标记 Offer 已发送',
  offer_accepted: '候选人接受 Offer',
  offer_declined: '候选人拒绝 Offer',
  offer_withdrawn: '公司撤回 Offer',
  offer_expired: '标记 Offer 已过期',
  application_admitted: '确认录取并等待入职',
  application_hired: '确认正式入职',
  company_canceled: '公司取消招聘流程',
  stage9_correction: '更正招聘流程记录',
  stage9_reopened: '重新打开招聘流程',
};

const ApplicationScreeningDrawer: React.FC<Props> = ({
  workspace,
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
  onPipelineChange,
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

  const applyState = useCallback((next: ScreeningState, notifyParent = false) => {
    setState(next);
    setRefreshError(null);
    if (notifyParent) onStateChange?.(next);
  }, [onStateChange]);

  const loadState = useCallback(async (
    showLoading = false,
    notifyParent = false,
  ): Promise<ScreeningState | null> => {
    if (!applicationId || !open) return null;
    const requestId = ++requestIdRef.current;
    if (showLoading) setInitialLoading(true);
    try {
      const next = await getApplicationScreening(applicationId);
      if (shouldApplyScreeningResponse(requestId, requestIdRef.current)) {
        applyState(next, notifyParent);
      }
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

  const refreshPipelineRecords = useCallback(async () => {
    if (!applicationId || !open) return;
    const [interviewResult, timelineResult] = await Promise.allSettled([
      listApplicationInterviews(applicationId),
      listApplicationTimeline(applicationId),
    ]);
    setInterviews(interviewResult.status === 'fulfilled' ? interviewResult.value : []);
    setTimeline(timelineResult.status === 'fulfilled' ? timelineResult.value : []);
  }, [applicationId, open]);

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
    if (!open || !applicationId) return;
    void refreshPipelineRecords();
  }, [applicationId, open, refreshPipelineRecords]);

  useEffect(() => {
    if (!open || !applicationId || !currentResumeId) return undefined;
    let cancelled = false;
    setResume(null);
    setResumeDraft(null);
    setResumeStructureNote('正在读取已保存的结构化结果…');
    void Promise.allSettled([
      getRecruitmentResume(currentResumeId),
      getStoredRecruitmentResumeStructure(currentResumeId),
    ]).then(([resumeResult, structureResult]) => {
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
        const next = await loadState(false, true);
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
      applyState(next, true);
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
      className={`recruitment-screening-report-drawer is-${workspace}`}
      destroyOnClose
      extra={(
        <div className="recruitment-screening-drawer-actions">
          <Button icon={<ReloadOutlined />} onClick={() => void loadState(false, true)}>刷新</Button>
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
      title={applicationId ? `${candidateName} · ${workspace === 'candidate' ? '招聘流程' : '初筛详情'} · 申请 #${applicationId}` : '申请详情'}
      width="min(980px, 100vw)"
    >
      <div className="recruitment-unified-detail-sections">
        <section aria-labelledby="application-overview-title" className="recruitment-unified-detail-card">
          <div><span>申请</span><h3 id="application-overview-title">申请概览</h3></div>
          <p>{candidateName} · {jobTitle}</p>
          <div className="recruitment-unified-detail-meta">
            <Tag>{summary?.source === 'public_apply' ? '公开投递' : '内部录入'}</Tag>
            {summary && <Tag>{STAGE_LABELS[summary.recruitmentStage]}</Tag>}
            {summary && <Tag>{DECISION_LABELS[summary.hrDecision]}</Tag>}
            {summary?.finalOutcome && <Tag color="default">{FINAL_OUTCOME_LABELS[summary.finalOutcome]}</Tag>}
          </div>
        </section>
        <section aria-labelledby="resume-section-title" className="recruitment-unified-detail-card">
          <div><span>材料</span><h3 id="resume-section-title">简历</h3></div>
          {resume ? <>
            <p><strong>{resume.filename}</strong> · {RESUME_STATUS_LABELS[resume.parseStatus]} · 上传于 {formatReportDate(resume.uploadedAt)}</p>
            <p>{resumeStructureNote}</p>
            {resumeDraft && <p>已保存结构：{resumeDraft.work_experiences.length} 段工作经历、{resumeDraft.project_experiences.length} 个项目、{resumeDraft.skills.length} 项技能。</p>}
            <details className="recruitment-resume-text-preview"><summary>查看已保存的简历文本</summary><pre>{resume.rawText || '当前没有已保存的简历文本。'}</pre></details>
            <Button href={getRecruitmentResumeFileUrl(resume.id, true)} rel="noopener noreferrer" target="_blank">下载当前简历</Button>
          </> : <p>简历元数据暂时无法读取；报告和其它业务记录仍可继续查看。</p>}
        </section>
        {workspace === 'candidate' && <section aria-labelledby="interview-section-title" className="recruitment-unified-detail-card">
          <div><span>流程</span><h3 id="interview-section-title">面试</h3></div>
          {applicationId && <InterviewPipelinePanel
            applicationId={applicationId}
            interviews={interviews}
            onChanged={async () => {
              await Promise.all([refreshPipelineRecords(), loadState(false)]);
              await onPipelineChange?.();
            }}
            summary={summary}
          />}
        </section>}
        {workspace === 'candidate' && <section aria-labelledby="offer-section-title" className="recruitment-unified-detail-card recruitment-offer-section">
          <div><span>结果</span><h3 id="offer-section-title">Offer</h3></div>
          {applicationId && <OfferPipelinePanel
            applicationId={applicationId}
            latestInterviewVersion={interviews.length ? interviews[interviews.length - 1].version : null}
            onChanged={async () => {
              await Promise.all([refreshPipelineRecords(), loadState(false)]);
              await onPipelineChange?.();
            }}
            summary={summary}
          />}
        </section>}
        <section aria-labelledby="timeline-section-title" className="recruitment-unified-detail-card">
          <div><span>审计</span><h3 id="timeline-section-title">时间线</h3></div>
          {timeline.length ? timeline.map(item => <p key={`${item.eventType}-${item.sourceId}`}>{formatReportDate(item.occurredAt)} · {item.actorLabel} · {TIMELINE_REASON_LABELS[item.reasonCode] ?? '招聘流程更新'}{item.reasonDetail ? ` · ${item.reasonDetail}` : ''}</p>) : <p>暂无可展示的招聘事件。</p>}
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
        <span><RobotOutlined /> AI 岗位匹配建议</span>
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
