import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Alert, Button, Modal, Select, Skeleton, Tag } from 'antd';
import { switchApplicationCurrentResume } from './services/aiScreening';
import {
  getRecruitmentCandidateResumeFiles,
  getRecruitmentResume,
  getRecruitmentResumeFileUrl,
  getStoredRecruitmentResumeStructure,
  type CandidateResumeFile,
  type RecruitmentResumeDetail,
  type ResumeStructureResponse,
} from './services/resumes';
import {
  getPublicApplicationSubmission,
  getPublicApplicationWorkbenchError,
  isPublicApplicationActive,
  markPublicApplicationIdentityReviewed,
  retryPublicApplicationProcessing,
  type ApplicationProcessingRunSummary,
  type PublicApplicationWorkbenchDetail,
  type PublicApplicationWorkbenchSummary,
} from './services/publicApplicationWorkbench';

const POLL_INTERVAL_MS = 4_000;
const POLL_LIMIT = 30;

const STATUS_META = {
  queued: { label: '等待处理', color: 'default' },
  running: { label: '正在处理', color: 'processing' },
  waiting_screening: { label: '等待初筛', color: 'processing' },
  succeeded: { label: '自动处理完成', color: 'success' },
  succeeded_with_warnings: { label: '完成，需留意', color: 'warning' },
  failed: { label: '处理失败', color: 'error' },
  paused: { label: '等待 HR 处理', color: 'warning' },
} as const;

const STEP_META = [
  { key: 'received', label: '受理' },
  { key: 'extract_text', label: '原文' },
  { key: 'structure_resume', label: '结构化' },
  { key: 'screening', label: '初筛' },
] as const;

const STEP_INDEX = {
  extract_text: 1,
  structure_resume: 2,
  trigger_screening: 3,
  await_screening: 3,
  completed: 4,
} as const;

const REASON_LABELS = {
  same_name: '发现同名候选人',
  contact_conflict: '联系方式指向不同候选人',
} as const;

const WAITING_LABELS = {
  job_closed: '岗位已关闭，重新开放后可以人工重试',
  existing_application_resume_choice: '该候选人已有申请，请先选择本次使用的简历',
} as const;

const formatDateTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date);
};

const toSummary = (
  detail: PublicApplicationWorkbenchDetail,
): PublicApplicationWorkbenchSummary => {
  const { processingRuns: _runs, identityCandidates: _candidates, ...summary } = detail;
  return summary;
};

export const PublicApplicationProcessingRail: React.FC<{
  run: ApplicationProcessingRunSummary;
  compact?: boolean;
}> = ({ run, compact = false }) => {
  const currentIndex = STEP_INDEX[run.currentStep];
  return (
    <ol
      aria-label={`公开投递处理进度：${STATUS_META[run.status].label}`}
      className={`recruitment-processing-rail${compact ? ' is-compact' : ''}`}
    >
      {STEP_META.map((step, index) => {
        const failed = run.status === 'failed' && index === currentIndex;
        const paused = run.status === 'paused' && index === currentIndex;
        const warning = step.key === 'structure_resume'
          && run.warningCodes.includes('RESUME_STRUCTURE_FAILED');
        const completed = index < currentIndex || run.currentStep === 'completed';
        const current = index === currentIndex && !completed;
        const state = failed ? 'failed' : warning ? 'warning' : paused ? 'paused'
          : completed ? 'completed' : current ? 'current' : 'pending';
        return (
          <li className={`is-${state}`} key={step.key}>
            <span aria-hidden="true">
              {failed || warning || paused
                ? <ExclamationCircleOutlined />
                : completed ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
            </span>
            <strong>{step.label}</strong>
          </li>
        );
      })}
    </ol>
  );
};

type Props = {
  summary: PublicApplicationWorkbenchSummary;
  currentResumeId: number;
  onResumeChange: (resumeId: number) => void;
  onSummaryChange: (summary: PublicApplicationWorkbenchSummary) => void;
};

const PublicApplicationProcessingPanel: React.FC<Props> = ({
  summary,
  currentResumeId,
  onResumeChange,
  onSummaryChange,
}) => {
  const [detail, setDetail] = useState<PublicApplicationWorkbenchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [pollCount, setPollCount] = useState(0);
  const [pollRevision, setPollRevision] = useState(0);
  const [rawResume, setRawResume] = useState<RecruitmentResumeDetail | null>(null);
  const [structure, setStructure] = useState<ResumeStructureResponse | null>(null);
  const [rawOpen, setRawOpen] = useState(false);
  const [structureOpen, setStructureOpen] = useState(false);
  const [resumeChoiceOpen, setResumeChoiceOpen] = useState(false);
  const [candidateResumes, setCandidateResumes] = useState<CandidateResumeFile[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number>(summary.resumeId);
  const aliveRef = useRef(true);
  const pollCountRef = useRef(0);
  const [modal, modalContextHolder] = Modal.useModal();

  const applyDetail = useCallback((next: PublicApplicationWorkbenchDetail) => {
    if (!aliveRef.current) return;
    setDetail(next);
    setActionError(null);
    onSummaryChange(toSummary(next));
  }, [onSummaryChange]);

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const next = await getPublicApplicationSubmission(summary.submissionId);
      applyDetail(next);
      return next;
    } catch (error) {
      if (aliveRef.current) setActionError(getPublicApplicationWorkbenchError(error).message);
      return null;
    } finally {
      if (showLoading && aliveRef.current) setLoading(false);
    }
  }, [applyDetail, summary.submissionId]);

  useEffect(() => {
    aliveRef.current = true;
    setDetail(null);
    setPollCount(0);
    pollCountRef.current = 0;
    void refresh(true);
    return () => { aliveRef.current = false; };
  }, [refresh]);

  useEffect(() => {
    if (
      !isPublicApplicationActive(summary.latestRun.status)
      || pollCountRef.current >= POLL_LIMIT
    ) return undefined;
    let cancelled = false;
    let timerId: number | undefined;
    const schedule = () => {
      if (cancelled || pollCountRef.current >= POLL_LIMIT) return;
      timerId = window.setTimeout(async () => {
        pollCountRef.current += 1;
        if (aliveRef.current) setPollCount(pollCountRef.current);
        const next = await refresh(false);
        if (!cancelled && next && isPublicApplicationActive(next.latestRun.status)) schedule();
      }, POLL_INTERVAL_MS);
    };
    schedule();
    return () => {
      cancelled = true;
      if (timerId !== undefined) window.clearTimeout(timerId);
    };
  }, [pollRevision, refresh, summary.latestRun.status]);

  const confirmIdentityReview = () => {
    modal.confirm({
      title: '确认已完成人工身份核对？',
      content: '这只记录 HR 已核对，不会合并、删除或改写任何 Candidate。',
      okText: '标记为已核对',
      cancelText: '取消',
      onOk: async () => {
        setActionPending(true);
        setActionError(null);
        try {
          applyDetail(await markPublicApplicationIdentityReviewed(summary.submissionId));
        } catch (error) {
          setActionError(getPublicApplicationWorkbenchError(error).message);
        } finally {
          setActionPending(false);
        }
      },
    });
  };

  const confirmRetry = () => {
    modal.confirm({
      title: `确认从“${summary.latestRun.currentStep}”继续处理？`,
      content: '系统会新建一条人工重试记录，并复用已经成功的步骤；旧运行和旧报告不会删除。',
      okText: '创建人工重试',
      cancelText: '取消',
      onOk: async () => {
        setActionPending(true);
        setActionError(null);
        try {
          const run = await retryPublicApplicationProcessing(summary.submissionId);
          onSummaryChange({ ...summary, latestRun: run });
          await refresh(false);
          pollCountRef.current = 0;
          setPollCount(0);
          setPollRevision(value => value + 1);
        } catch (error) {
          setActionError(getPublicApplicationWorkbenchError(error).message);
        } finally {
          setActionPending(false);
        }
      },
    });
  };

  const showRawText = async () => {
    setActionPending(true);
    setActionError(null);
    try {
      const resume = await getRecruitmentResume(summary.resumeId);
      setRawResume(resume);
      setRawOpen(true);
    } catch (error) {
      setActionError(getPublicApplicationWorkbenchError(error).message);
    } finally {
      setActionPending(false);
    }
  };

  const showStructure = async () => {
    setActionPending(true);
    setActionError(null);
    try {
      setStructure(await getStoredRecruitmentResumeStructure(summary.resumeId));
      setStructureOpen(true);
    } catch (error) {
      setActionError(getPublicApplicationWorkbenchError(error).message);
    } finally {
      setActionPending(false);
    }
  };

  const openResumeChoice = async () => {
    setActionPending(true);
    setActionError(null);
    try {
      const resumes = await getRecruitmentCandidateResumeFiles(summary.candidateId);
      setCandidateResumes(resumes);
      setSelectedResumeId(currentResumeId);
      setResumeChoiceOpen(true);
    } catch (error) {
      setActionError(getPublicApplicationWorkbenchError(error).message);
    } finally {
      setActionPending(false);
    }
  };

  const saveResumeChoice = async () => {
    setActionPending(true);
    setActionError(null);
    try {
      await switchApplicationCurrentResume(summary.applicationId, selectedResumeId);
      onResumeChange(selectedResumeId);
      setResumeChoiceOpen(false);
      await refresh(false);
    } catch (error) {
      setActionError(getPublicApplicationWorkbenchError(error).message);
    } finally {
      setActionPending(false);
    }
  };

  const current = detail ?? summary;
  const run = current.latestRun;
  const polling = isPublicApplicationActive(run.status) && pollCount < POLL_LIMIT;

  return (
    <section aria-label="公开投递自动处理状态" className="recruitment-public-processing">
      {modalContextHolder}
      <header className="recruitment-public-processing-header">
        <div>
          <span>公开投递 · {current.submissionReference}</span>
          <strong>{formatDateTime(current.submittedAt)} 收到</strong>
        </div>
        <div>
          <Tag color={STATUS_META[run.status].color}>{STATUS_META[run.status].label}</Tag>
          {current.identityReviewStatus === 'needs_review' && <Tag color="warning">身份待核对</Tag>}
          {current.identityReviewStatus === 'reviewed' && <Tag color="success">身份已核对</Tag>}
          {polling && <Tag color="processing">每 4 秒刷新 · {pollCount}/{POLL_LIMIT}</Tag>}
        </div>
      </header>

      <PublicApplicationProcessingRail run={run} />

      {loading && !detail && <Skeleton active paragraph={{ rows: 3 }} />}
      {actionError && (
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void refresh(false)}>重试读取</Button>}
          message={actionError}
          showIcon
          type="error"
        />
      )}
      {run.waitingReason && (
        <Alert message={WAITING_LABELS[run.waitingReason]} showIcon type="warning" />
      )}
      {run.errorMessage && (
        <Alert
          description={run.errorCode ? `错误代码：${run.errorCode}` : undefined}
          message={run.errorMessage}
          showIcon
          type="error"
        />
      )}
      {run.warningCodes.includes('RESUME_STRUCTURE_FAILED') && (
        <Alert
          message="结构化简历未成功，但已保存的原文仍会继续进入初筛。"
          showIcon
          type="warning"
        />
      )}

      <div className="recruitment-public-processing-actions">
        <Button
          href={getRecruitmentResumeFileUrl(current.resumeId)}
          icon={<DownloadOutlined />}
          rel="noreferrer"
          target="_blank"
        >
          查看原文件
        </Button>
        <Button icon={<FileTextOutlined />} loading={actionPending} onClick={() => void showRawText()}>
          查看原文
        </Button>
        <Button icon={<SafetyCertificateOutlined />} loading={actionPending} onClick={() => void showStructure()}>
          查看结构化结果
        </Button>
        {run.waitingReason === 'existing_application_resume_choice' && (
          <Button loading={actionPending} onClick={() => void openResumeChoice()} type="primary">
            选择当前简历
          </Button>
        )}
        {current.identityReviewStatus === 'needs_review' && (
          <Button loading={actionPending} onClick={confirmIdentityReview}>
            标记身份已核对
          </Button>
        )}
        {['failed', 'paused'].includes(run.status) && (
          <Button danger loading={actionPending} onClick={confirmRetry}>
            人工重试
          </Button>
        )}
      </div>

      {detail && detail.identityCandidates.length > 0 && (
        <div className="recruitment-identity-review-list">
          <strong>身份核对参考</strong>
          <p>{detail.identityReviewReasons.map(reason => REASON_LABELS[reason]).join('；')}</p>
          {detail.identityCandidates.map(candidate => (
            <article key={candidate.id}>
              <div>
                <strong>{candidate.name}</strong>
                {candidate.isSubmissionCandidate && <Tag color="processing">本次投递</Tag>}
              </div>
              <span>{candidate.phone || '未记录手机号'} · {candidate.email || '未记录邮箱'}</span>
              <small>Candidate #{candidate.id} · {candidate.source || '来源未记录'}</small>
            </article>
          ))}
        </div>
      )}

      {detail && detail.processingRuns.length > 1 && (
        <details className="recruitment-processing-history">
          <summary>查看 {detail.processingRuns.length} 次处理历史</summary>
          <ol>
            {detail.processingRuns.map(history => (
              <li key={history.id}>
                <strong>Run #{history.id} · {STATUS_META[history.status].label}</strong>
                <span>{history.triggerType === 'manual_retry' ? 'HR 人工重试' : '系统自动处理'} · {history.currentStep} · {formatDateTime(history.createdAt)}</span>
              </li>
            ))}
          </ol>
        </details>
      )}

      <Modal
        footer={null}
        onCancel={() => setRawOpen(false)}
        open={rawOpen}
        title={`${current.resumeFilename} · 已提取原文`}
        width={760}
      >
        {rawResume?.rawText
          ? <pre className="recruitment-resume-raw-text">{rawResume.rawText}</pre>
          : <Alert message="当前简历尚无成功提取的原文。" showIcon type="info" />}
      </Modal>

      <Modal
        footer={null}
        onCancel={() => setStructureOpen(false)}
        open={structureOpen}
        title={`${current.resumeFilename} · 已保存结构化结果`}
        width={820}
      >
        {structure && (
          <div className="recruitment-structure-readonly">
            <Alert message="这里只读取已保存结果，不会启动新的 AI 调用。" showIcon type="info" />
            <dl>
              <div><dt>姓名</dt><dd>{structure.draft.basic_info.name || '未识别'}</dd></div>
              <div><dt>当前职位</dt><dd>{structure.draft.basic_info.current_title || '未识别'}</dd></div>
              <div><dt>工作年限</dt><dd>{structure.draft.basic_info.work_years ?? '未识别'}</dd></div>
              <div><dt>教育程度</dt><dd>{structure.draft.basic_info.education_level || '未识别'}</dd></div>
            </dl>
            <div className="recruitment-structure-tags">
              {structure.draft.skills.length > 0
                ? structure.draft.skills.map(skill => <Tag key={skill}>{skill}</Tag>)
                : <span>未识别技能</span>}
            </div>
            <details><summary>教育经历（{structure.draft.education_records.length}）</summary><pre>{JSON.stringify(structure.draft.education_records, null, 2)}</pre></details>
            <details><summary>工作经历（{structure.draft.work_experiences.length}）</summary><pre>{JSON.stringify(structure.draft.work_experiences, null, 2)}</pre></details>
            <details><summary>项目经历（{structure.draft.project_experiences.length}）</summary><pre>{JSON.stringify(structure.draft.project_experiences, null, 2)}</pre></details>
          </div>
        )}
      </Modal>

      <Modal
        confirmLoading={actionPending}
        onCancel={() => !actionPending && setResumeChoiceOpen(false)}
        onOk={() => void saveResumeChoice()}
        okText="保存当前简历"
        open={resumeChoiceOpen}
        title="选择这份 Application 当前使用的简历"
      >
        <Alert
          message={`本次公开投递简历是 #${current.resumeId} ${current.resumeFilename}`}
          showIcon
          type="info"
        />
        <Select
          aria-label="选择当前简历"
          onChange={setSelectedResumeId}
          options={candidateResumes.map(resume => ({
            value: resume.id,
            label: `#${resume.id} ${resume.filename}${resume.id === current.resumeId ? '（本次公开投递）' : ''}`,
          }))}
          style={{ marginTop: 16, width: '100%' }}
          value={selectedResumeId}
        />
      </Modal>
    </section>
  );
};

export default PublicApplicationProcessingPanel;
