import React from 'react';
import {
  BulbOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  FileSearchOutlined,
  QuestionCircleOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { Alert, Collapse, Empty, Progress, Tag } from 'antd';
import {
  CATEGORY_LABELS,
  getRequirementPlanFact,
  getRequirementPlanItem,
  OUTDATED_REASON_LABELS,
  PRIORITY_LABELS,
} from './screeningPresentation';
import type {
  JobEvaluationItem,
  JobEvaluationPlan,
  RequirementAssessment,
  RequirementFact,
  ScreeningEvidence,
  ScreeningReport,
} from './types/aiScreening';

type Props = {
  report: ScreeningReport;
  plan: JobEvaluationPlan | null;
};

const formatDateTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date);
};

const formatEvaluationReference = (report: ScreeningReport) => {
  if (!report.evaluationReferenceAt || !report.evaluationTimezone) {
    return '历史报告未记录评价基准';
  }
  const date = new Date(report.evaluationReferenceAt);
  if (Number.isNaN(date.getTime())) return '历史报告未记录评价基准';
  const parts = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: report.evaluationTimezone,
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  const formatted = `${values.year}-${values.month}-${values.day}`;
  return `评价基准：按该申请 ${formatted} 的投递时间计算`;
};

const EvidenceList: React.FC<{ evidence: ScreeningEvidence[] }> = ({ evidence }) => {
  if (evidence.length === 0) {
    return <p className="recruitment-screening-no-evidence">0 分项目允许没有证据，因为当前简历未体现相关内容。</p>;
  }
  return (
    <div className="recruitment-screening-evidence-list">
      {evidence.map((item, index) => (
        <blockquote key={`${item.section || 'resume'}-${index}-${item.quote}`}>
          {item.section && <span>{item.section}</span>}
          <p>“{item.quote}”</p>
        </blockquote>
      ))}
    </div>
  );
};

const scoreTone = (score: number) => {
  if (score >= 8) return 'is-strong';
  if (score >= 5) return 'is-medium';
  if (score > 0) return 'is-low';
  return 'is-zero';
};

const RequirementAssessmentCard: React.FC<{
  assessment: RequirementAssessment;
  fact: RequirementFact | null;
  index: number;
  item: JobEvaluationItem | null;
}> = ({ assessment, fact, index, item }) => (
  <article className="recruitment-requirement-item" key={assessment.requirementKey}>
    <div className={`recruitment-requirement-score ${scoreTone(assessment.score)}`}>
      <strong>{assessment.score}</strong><span>/ 10</span>
    </div>
    <div className="recruitment-requirement-content">
      <div className="recruitment-requirement-heading">
        <div>
          <span>{fact ? fact.factId : `事项 ${String(index + 1).padStart(2, '0')}`}</span>
          <h4>{fact?.sources[0]?.sourceQuote || item?.title || assessment.requirementKey}</h4>
        </div>
        {fact ? (
          <div className="recruitment-requirement-tags">
            <Tag>{CATEGORY_LABELS[fact.category]}</Tag>
            <Tag color={fact.priority === 'required' ? 'red' : fact.priority === 'preferred' ? 'gold' : 'default'}>
              {PRIORITY_LABELS[fact.priority]}
            </Tag>
          </div>
        ) : item ? (
          <Tag color={item.priority === 'required' ? 'red' : item.priority === 'preferred' ? 'gold' : 'default'}>
            {PRIORITY_LABELS[item.priority]}
          </Tag>
        ) : (
          <Tag>来自原评价计划</Tag>
        )}
      </div>
      {fact && (
        <details className="recruitment-report-fact-sources">
          <summary>查看 JD 原文依据（{fact.sources.length}）</summary>
          {fact.sources.map(source => (
            <blockquote key={`${source.sourceUnitId}-${source.sourceQuote}`}>
              <span>{source.sourceField} · {source.sourceUnitId}</span>
              <p>{source.sourceQuote}</p>
            </blockquote>
          ))}
        </details>
      )}
      {assessment.score === 0 && (
        <div className="recruitment-zero-score-note">0 分语义：当前可用简历未体现，不等同于候选人不会。</div>
      )}
      <p>{assessment.reason}</p>
      {assessment.calculationNote && (
        <p className="recruitment-calculation-note">判断说明：{assessment.calculationNote}</p>
      )}
      <Collapse
        className="recruitment-evidence-collapse"
        ghost
        items={[{
          key: 'evidence',
          label: assessment.evidence.length > 0
            ? `查看简历证据（${assessment.evidence.length}）`
            : '证据说明',
          children: <EvidenceList evidence={assessment.evidence} />,
        }]}
      />
    </div>
  </article>
);

const ScreeningReportView: React.FC<Props> = ({ report, plan }) => {
  const matchingV4Plan = plan?.id === report.jobEvaluationPlanId && plan.schemaVersion === '4.0'
    ? plan
    : null;
  const assessmentByFactId = new Map(
    report.requirementAssessments.map(assessment => [assessment.requirementKey, assessment]),
  );
  const groupedFactIds = new Set(
    matchingV4Plan?.evaluationCriteria.flatMap(criterion => criterion.factIds) ?? [],
  );
  const ungroupedAssessments = matchingV4Plan
    ? report.requirementAssessments.filter(assessment => !groupedFactIds.has(assessment.requirementKey))
    : [];

  return (
  <div className="recruitment-ai-report">
    {report.isOutdated && (
      <Alert
        className="recruitment-ai-report-outdated"
        description={(
          <div className="recruitment-outdated-reasons">
            {report.outdatedReasons.map(reason => <Tag key={reason}>{OUTDATED_REASON_LABELS[reason]}</Tag>)}
            <span>旧报告继续保留；系统不会自动调用 AI，请由 HR 主动重新评估。</span>
          </div>
        )}
        message="当前报告基于旧输入"
        showIcon
        type="warning"
      />
    )}

    <section className="recruitment-report-overview">
      <div className="recruitment-report-score" aria-label={`AI 岗位匹配建议分 ${report.overallScore} 分`}>
        <Progress
          format={() => <><strong>{report.overallScore}</strong><span>/ 100</span></>}
          percent={report.overallScore}
          size={132}
          strokeColor="#3f6fd9"
          trailColor="#e8edf7"
          type="circle"
        />
        <span>AI 岗位匹配建议分</span>
      </div>
      <div className="recruitment-report-overview-copy">
        <Tag bordered={false} className="recruitment-report-label">{report.displayLabel}</Tag>
        <h2>这是一份辅助建议，不是 HR 决策</h2>
        <p>展示标签只解释 AI 分数，不会自动通过、备选、淘汰或改变招聘阶段。</p>
        <div className="recruitment-report-overview-meta">
          <span><CalendarOutlined /> 生成于 {formatDateTime(report.generatedAt)}</span>
          <span><CalendarOutlined /> {formatEvaluationReference(report)}</span>
          <span>报告 #{report.id} · Resume #{report.resumeId}</span>
          <span>评价计划 #{report.jobEvaluationPlanId}</span>
        </div>
      </div>
    </section>

    <section className="recruitment-report-section recruitment-report-summary">
      <div className="recruitment-report-section-mark"><CheckCircleOutlined /></div>
      <div>
        <span>综合评价</span>
        <h3>AI 对当前简历与岗位的整体理解</h3>
        <p>{report.overallSummary}</p>
      </div>
    </section>

    <section className="recruitment-report-section recruitment-report-assessments">
      <div className="recruitment-report-section-mark"><FileSearchOutlined /></div>
      <div className="recruitment-report-section-body">
        <span>岗位要求逐项评价</span>
        <h3>{report.requirementAssessments.length} 个基础事项</h3>
        <p className="recruitment-report-section-intro">分数描述简历展示出的匹配度；0 分不代表候选人事实上不会。</p>
        {matchingV4Plan ? (
          <div className="recruitment-report-criteria">
            {matchingV4Plan.evaluationCriteria.map(criterion => {
              const criterionAssessments = criterion.factIds
                .map(factId => ({
                  assessment: assessmentByFactId.get(factId),
                  fact: getRequirementPlanFact(matchingV4Plan, report.jobEvaluationPlanId, factId),
                  factId,
                }))
                .filter(entry => entry.assessment);
              return (
                <section className="recruitment-report-criterion" key={criterion.criterionId}>
                  <header><div><span>EVALUATION CRITERION</span><h4>{criterion.name}</h4></div><Tag>{criterionAssessments.length} 条事实</Tag></header>
                  <div className="recruitment-requirement-list">
                    {criterionAssessments.map((entry, index) => (
                      <RequirementAssessmentCard
                        assessment={entry.assessment!}
                        fact={entry.fact}
                        index={index}
                        item={null}
                        key={entry.factId}
                      />
                    ))}
                  </div>
                </section>
              );
            })}
            {ungroupedAssessments.length > 0 && (
              <section className="recruitment-report-criterion is-historical">
                <header><div><span>HISTORICAL FALLBACK</span><h4>原计划分组未能读取</h4></div><Tag>{ungroupedAssessments.length} 条</Tag></header>
                <div className="recruitment-requirement-list">
                  {ungroupedAssessments.map((assessment, index) => (
                    <RequirementAssessmentCard assessment={assessment} fact={null} index={index} item={null} key={assessment.requirementKey} />
                  ))}
                </div>
              </section>
            )}
          </div>
        ) : (
          <div className="recruitment-requirement-list">
            {report.requirementAssessments.map((assessment, index) => (
              <RequirementAssessmentCard
                assessment={assessment}
                fact={null}
                index={index}
                item={getRequirementPlanItem(plan, report.jobEvaluationPlanId, assessment.requirementKey)}
                key={assessment.requirementKey}
              />
            ))}
          </div>
        )}
      </div>
    </section>

    <section className="recruitment-report-section">
      <div className="recruitment-report-section-mark is-highlight"><BulbOutlined /></div>
      <div className="recruitment-report-section-body">
        <span>候选人额外亮点</span>
        <h3>JD 基础事项之外的岗位相关价值</h3>
        {report.bonusHighlights.length === 0 ? (
          <Empty description="当前简历没有满足规则的额外亮点" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <div className="recruitment-bonus-grid">
            {report.bonusHighlights.map(highlight => (
              <article className="recruitment-bonus-card" key={highlight.title}>
                <div><h4>{highlight.title}</h4><Tag color="green">亮点 {highlight.score} / 10</Tag></div>
                <p>{highlight.reason}</p>
                <Collapse
                  ghost
                  items={[{
                    key: 'evidence',
                    label: `查看简历证据（${highlight.evidence.length}）`,
                    children: <EvidenceList evidence={highlight.evidence} />,
                  }]}
                />
              </article>
            ))}
          </div>
        )}
      </div>
    </section>

    {report.tradeoffReason && (
      <section className="recruitment-report-section">
        <div className="recruitment-report-section-mark is-tradeoff"><SwapOutlined /></div>
        <div className="recruitment-report-section-body">
          <span>综合权衡</span>
          <h3>高分与重要短板如何同时理解</h3>
          <p className="recruitment-tradeoff-copy">{report.tradeoffReason}</p>
        </div>
      </section>
    )}

    <section className="recruitment-report-section">
      <div className="recruitment-report-section-mark is-question"><QuestionCircleOutlined /></div>
      <div className="recruitment-report-section-body">
        <span>面试重点</span>
        <h3>建议进一步核实的问题</h3>
        {report.interviewQuestions.length === 0 ? (
          <Empty description="当前报告没有生成面试问题" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <ol className="recruitment-interview-questions">
            {report.interviewQuestions.map((question, index) => (
              <li key={`${index}-${question}`}><span>{String(index + 1).padStart(2, '0')}</span><p>{question}</p></li>
            ))}
          </ol>
        )}
      </div>
    </section>

    <footer className="recruitment-report-versions">
      <span>Prompt {report.promptVersion}</span>
      <span>模型 {report.modelVersion}</span>
      <span>Schema {report.schemaVersion}</span>
      <span>脱敏规则 {report.redactionVersion}</span>
      <span>时间事实 {report.experiencePeriodFactsRuleVersion || '历史版本未记录'}</span>
    </footer>
  </div>
  );
};

export default ScreeningReportView;
