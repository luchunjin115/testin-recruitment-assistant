import React from 'react';
import { CheckCircleOutlined, EyeOutlined } from '@ant-design/icons';
import { Button, Checkbox, Progress, Tag } from 'antd';
import { Link } from 'react-router-dom';
import type { ScreeningCenterItem } from './services/screeningCenter';

type Props = {
  items: ScreeningCenterItem[];
  mode: 'screening' | 'candidate';
  selectedApplicationIds?: number[];
  onToggleSelection?: (item: ScreeningCenterItem, checked: boolean) => void;
  onOpen: (item: ScreeningCenterItem) => void;
  onDecision?: (item: ScreeningCenterItem) => void;
};

const SOURCE_LABELS = {
  hr_direct: 'HR 直通',
  hr_screening: '内部录入',
  public_apply: '公开投递',
} as const;

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

const REPORT_LABELS = {
  not_started: '尚未开始',
  waiting_resume: '等待简历',
  waiting_plan: '等待评价计划',
  queued: '排队中',
  running: '评估中',
  ready: '报告可用',
  failed: '评估失败',
  paused: '等待处理',
  outdated: '报告已过期',
  old_report_retained: '旧报告保留',
} as const;

const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric', month: '2-digit', day: '2-digit',
}).format(new Date(value));

const scoreTone = (score: number | null) => {
  if (score === null) return '#c5ccd8';
  if (score >= 85) return '#d25565';
  if (score >= 70) return '#df9c35';
  return '#5f83cb';
};

const ApplicationEvidenceTable: React.FC<Props> = ({
  items,
  mode,
  selectedApplicationIds = [],
  onToggleSelection,
  onOpen,
  onDecision,
}) => (
  <div
    aria-label={mode === 'screening' ? 'AI 初筛申请表' : '已通过候选人岗位申请表'}
    className={`recruitment-application-table is-${mode}`}
    role="table"
  >
    <div className="recruitment-application-table-head" role="row">
      {mode === 'screening' && <span aria-hidden="true" />}
      <span>候选人</span>
      <span>应聘岗位</span>
      <span>{mode === 'screening' ? '初筛状态' : '招聘阶段'}</span>
      <span>来源</span>
      <span>AI 初筛</span>
      <span>AI 标签</span>
      <span>AI 结论</span>
      <span>更新时间</span>
      <span>操作</span>
    </div>
    {items.map(item => {
      const decisionAllowed = item.allowedActions.some(action => (
        ['pass', 'backup', 'reject', 'undo_rejection'].includes(action)
      ));
      const canBatch = item.allowedActions.includes('reassess_screening');
      const risk = item.gapsOrRisks[0];
      const strength = item.strengths[0];
      return (
        <article className="recruitment-application-table-row" key={item.applicationId} role="row">
          {mode === 'screening' && (
            <div className="recruitment-application-select" role="cell">
              <Checkbox
                aria-label={`选择 ${item.candidateName}`}
                checked={selectedApplicationIds.includes(item.applicationId)}
                disabled={!canBatch}
                onChange={event => onToggleSelection?.(item, event.target.checked)}
              />
            </div>
          )}
          <div className="recruitment-application-person" data-label="候选人" role="cell">
            {mode === 'candidate' ? (
              <Link to={`/app/candidates/${item.candidateId}?application_id=${item.applicationId}`}>
                {item.candidateName}
              </Link>
            ) : <strong>{item.candidateName}</strong>}
            <span>{item.maskedPhone || '电话未填写'}</span>
            <small>
              {[item.currentTitle, item.currentCompany, item.workYears === null ? null : `${item.workYears} 年经验`, item.educationLevel]
                .filter(Boolean).join(' · ') || '职业资料待补充'}
            </small>
          </div>
          <div className="recruitment-application-job" data-label="应聘岗位" role="cell">
            <strong>{item.jobTitle}</strong>
            <span>申请 #{item.applicationId}</span>
          </div>
          <div className="recruitment-application-state" data-label={mode === 'screening' ? '初筛状态' : '招聘阶段'} role="cell">
            <Tag color={mode === 'candidate' && item.lifecycleStatus === 'active' ? 'processing' : undefined}>
              {mode === 'screening' ? DECISION_LABELS[item.hrDecision] : STAGE_LABELS[item.recruitmentStage]}
            </Tag>
            {mode === 'screening' && <span>{STAGE_LABELS[item.recruitmentStage]}</span>}
            {mode === 'candidate' && item.finalOutcome && <span>{FINAL_OUTCOME_LABELS[item.finalOutcome]}</span>}
            {item.processingPool === 'exception' && <small>自动处理需人工介入</small>}
          </div>
          <div className="recruitment-application-source" data-label="来源" role="cell">
            <Tag bordered={false}>{SOURCE_LABELS[item.source]}</Tag>
            {item.submissionReference && <span>{item.submissionReference}</span>}
          </div>
          <div className="recruitment-application-score" data-label="AI 初筛" role="cell">
            <div>
              {item.score === null
                ? <span aria-hidden="true" className="recruitment-application-score-empty" />
                : <Progress percent={item.score} showInfo={false} strokeColor={scoreTone(item.score)} />}
              <strong>{item.score === null ? '—' : item.score}</strong>
            </div>
            <span>{item.displayLabel || REPORT_LABELS[item.screeningStatus]}</span>
            {item.score !== null && item.screeningStatus !== 'ready' && <small>{REPORT_LABELS[item.screeningStatus]}</small>}
          </div>
          <div className="recruitment-application-tags" data-label="AI 标签" role="cell">
            {item.abilityTags.length ? item.abilityTags.map(tag => (
              <Tag bordered={false} key={tag.criterionId}>{tag.label}</Tag>
            )) : <span>暂无可靠标签</span>}
          </div>
          <div className="recruitment-application-summary" data-label="AI 结论" role="cell">
            <p title={item.overallSummary || item.screeningErrorMessage || ''}>
              {item.overallSummary || item.screeningErrorMessage || '报告完成后显示可核对结论。'}
            </p>
            {strength && <small className="is-strength" title={strength}>优势：{strength}</small>}
            {risk && <small className="is-risk" title={risk}>关注：{risk}</small>}
          </div>
          <div className="recruitment-application-time" data-label="更新时间" role="cell">
            <strong>{formatDate(item.businessUpdatedAt)}</strong>
            <span>投递 {formatDate(item.appliedAt)}</span>
          </div>
          <div className="recruitment-application-actions" data-label="操作" role="cell">
            <Button icon={<EyeOutlined />} onClick={() => onOpen(item)} size="small">详情</Button>
            {mode === 'screening' && decisionAllowed && (
              <Button icon={<CheckCircleOutlined />} onClick={() => onDecision?.(item)} size="small" type="primary">
                HR 决策
              </Button>
            )}
          </div>
        </article>
      );
    })}
  </div>
);

export default ApplicationEvidenceTable;
