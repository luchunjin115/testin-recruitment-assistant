import React from 'react';
import {
  BulbOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  FileSearchOutlined,
  QuestionCircleOutlined,
  SwapOutlined,
  WarningOutlined,
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
  V5PersistedCriterionAssessment,
  V5ReportFinding,
} from './types/aiScreening';

const SOURCE_FIELD_LABELS = {
  candidate_requirements: '任职要求',
  preferred_qualifications: '加分项',
  job_responsibilities: '岗位职责',
} as const;

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

const V5AssessmentCard: React.FC<{
  item: V5PersistedCriterionAssessment;
  index: number;
}> = ({ item, index }) => {
  const { assessment, criterion } = item;
  return (
    <article className="recruitment-requirement-item recruitment-v5-assessment">
      <div className={`recruitment-requirement-score ${scoreTone(assessment.score)}`}>
        <strong>{assessment.score}</strong><span>/ 10</span>
      </div>
      <div className="recruitment-requirement-content">
        <div className="recruitment-requirement-heading">
          <div><span>{criterion.criterionId} · {String(index + 1).padStart(2, '0')}</span><h4>{criterion.name}</h4></div>
          <div className="recruitment-requirement-tags">
            <Tag color={criterion.importance === 'required' ? 'red' : criterion.importance === 'preferred' ? 'gold' : 'default'}>
              {PRIORITY_LABELS[criterion.importance]}
            </Tag>
            <Tag color={criterion.origin === 'hr_added' ? 'purple' : 'blue'}>
              {criterion.origin === 'hr_added' ? 'HR 补充' : '来自 JD'}
            </Tag>
          </div>
        </div>
        <p className="recruitment-v5-criterion-description">{criterion.description}</p>
        <p><strong>初筛重点：</strong>{criterion.screeningFocus}</p>
        {criterion.hrNote && <p className="recruitment-plan-hr-note">HR 说明：{criterion.hrNote}</p>}
        {criterion.sources.length > 0 ? (
          <details className="recruitment-report-fact-sources">
            <summary>查看 JD 原文依据（{criterion.sources.length}）</summary>
            {criterion.sources.map(source => (
              <blockquote key={`${source.sourceField}-${source.sourceQuote}`}>
                <span>{SOURCE_FIELD_LABELS[source.sourceField]}</span><p>{source.sourceQuote}</p>
              </blockquote>
            ))}
          </details>
        ) : <p className="recruitment-plan-hr-source">此项由 HR 补充，不冒充 JD 原文。</p>}
        {assessment.score === 0 && (
          <div className="recruitment-zero-score-note">0 分语义：当前可用简历未体现，不等同于候选人不会。</div>
        )}
        <p>{assessment.reason}</p>
        {assessment.calculationNote && <p className="recruitment-calculation-note">判断说明：{assessment.calculationNote}</p>}
        <Collapse
          className="recruitment-evidence-collapse"
          ghost
          items={[{
            key: 'evidence',
            label: assessment.evidence.length > 0 ? `查看简历证据（${assessment.evidence.length}）` : '证据说明',
            children: <EvidenceList evidence={assessment.evidence} />,
          }]}
        />
      </div>
    </article>
  );
};

const FindingList: React.FC<{ findings: V5ReportFinding[]; empty: string }> = ({ findings, empty }) => (
  findings.length === 0
    ? <Empty description={empty} image={Empty.PRESENTED_IMAGE_SIMPLE} />
    : <div className="recruitment-v5-findings">
      {findings.map((finding, index) => (
        <article key={`${index}-${finding.summary}`}>
          <p>{finding.summary}</p>
          {finding.criterionIds.length > 0 && <div>{finding.criterionIds.map(id => <Tag key={id}>{id}</Tag>)}</div>}
          {finding.evidence.length > 0 && (
            <Collapse ghost items={[{ key: 'evidence', label: `查看简历证据（${finding.evidence.length}）`, children: <EvidenceList evidence={finding.evidence} /> }]} />
          )}
        </article>
      ))}
    </div>
);

const ScreeningReportView: React.FC<Props> = ({ report, plan }) => {
  if (report.v5Report) {
    const v5 = report.v5Report;
    return (
      <div className="recruitment-ai-report recruitment-v5-report">
        {!report.isCurrent && (
          <Alert description="这是过去一次成功评价的只读快照，不会覆盖当前报告。" message="正在查看历史报告" showIcon type="info" />
        )}
        {report.isOutdated && (
          <Alert
            className="recruitment-ai-report-outdated"
            description={<div className="recruitment-outdated-reasons">{report.outdatedReasons.map(reason => <Tag key={reason}>{OUTDATED_REASON_LABELS[reason]}</Tag>)}<span>旧报告继续保留；系统不会自动调用 AI，请由 HR 主动重新评估。</span></div>}
            message="当前报告基于旧输入"
            showIcon
            type="warning"
          />
        )}
        <section className="recruitment-report-overview">
          <div className="recruitment-report-score" aria-label={`AI 岗位匹配建议分 ${v5.overallScore} 分`}>
            <Progress format={() => <><strong>{v5.overallScore}</strong><span>/ 100</span></>} percent={v5.overallScore} size={132} strokeColor="#3f6fd9" trailColor="#e8edf7" type="circle" />
            <span>AI 岗位匹配建议分</span>
          </div>
          <div className="recruitment-report-overview-copy">
            <Tag bordered={false} className="recruitment-report-label">{v5.displayLabel}</Tag>
            <h2>AI 建议与 HR 决策相互独立</h2>
            <p>总分由 AI 直接给出，程序不平均、不加权、不重算；展示标签也不会自动通过或淘汰候选人。</p>
            <div className="recruitment-report-overview-meta">
              <span><CalendarOutlined /> 生成于 {formatDateTime(report.generatedAt)}</span>
              <span><CalendarOutlined /> {formatEvaluationReference(report)}</span>
              <span>报告 #{report.id} · Resume #{report.resumeId}</span>
              <span>评价计划 #{report.jobEvaluationPlanId} · Schema 5.0</span>
            </div>
          </div>
        </section>

        <section className="recruitment-report-section recruitment-report-summary">
          <div className="recruitment-report-section-mark"><CheckCircleOutlined /></div>
          <div><span>综合说明</span><h3>当前简历与当前岗位的整体匹配解释</h3><p>{v5.overallSummary}</p></div>
        </section>

        <section className="recruitment-report-section recruitment-report-assessments">
          <div className="recruitment-report-section-mark"><FileSearchOutlined /></div>
          <div className="recruitment-report-section-body">
            <span>评价点逐项结论</span><h3>{v5.criterionAssessments.length} 个已确认评价点</h3>
            <p className="recruitment-report-section-intro">每项 0—10 分；非零分必须有当前简历证据，0 分只表示当前简历未发现相关证据。</p>
            <div className="recruitment-requirement-list">
              {v5.criterionAssessments.map((item, index) => <V5AssessmentCard item={item} index={index} key={item.criterion.criterionId} />)}
            </div>
          </div>
        </section>

        <div className="recruitment-v5-report-grid">
          <section className="recruitment-report-section is-strength"><div className="recruitment-report-section-mark is-highlight"><BulbOutlined /></div><div className="recruitment-report-section-body"><span>主要优势</span><h3>有简历证据支持的匹配点</h3><FindingList findings={v5.strengths} empty="当前报告没有单列主要优势" /></div></section>
          <section className="recruitment-report-section is-gap"><div className="recruitment-report-section-mark is-tradeoff"><SwapOutlined /></div><div className="recruitment-report-section-body"><span>主要差距</span><h3>与岗位要求之间的缺口</h3><FindingList findings={v5.gaps} empty="当前报告没有单列差距" /></div></section>
          <section className="recruitment-report-section is-risk"><div className="recruitment-report-section-mark is-risk"><WarningOutlined /></div><div className="recruitment-report-section-body"><span>风险与事实冲突</span><h3>需要谨慎解释或核对的内容</h3><FindingList findings={v5.risksOrConflicts} empty="当前报告未发现需要单列的风险或事实冲突" /></div></section>
          <section className="recruitment-report-section is-missing"><div className="recruitment-report-section-mark is-question"><QuestionCircleOutlined /></div><div className="recruitment-report-section-body"><span>缺失信息</span><h3>简历没有充分说明的内容</h3><FindingList findings={v5.missingInfo} empty="当前报告没有单列缺失信息" /></div></section>
        </div>

        <section className="recruitment-report-section">
          <div className="recruitment-report-section-mark is-question"><QuestionCircleOutlined /></div>
          <div className="recruitment-report-section-body"><span>HR 后续核实</span><h3>面试或沟通时建议确认的问题</h3><ol className="recruitment-interview-questions">{v5.hrFollowUpQuestions.map((question, index) => <li key={`${index}-${question}`}><span>{String(index + 1).padStart(2, '0')}</span><p>{question}</p></li>)}</ol></div>
        </section>

        <footer className="recruitment-report-versions">
          <span>Prompt {report.promptVersion}</span><span>模型 {report.modelVersion}</span><span>Schema {report.schemaVersion}</span><span>脱敏规则 {report.redactionVersion}</span><span>时间事实 {report.experiencePeriodFactsRuleVersion || '历史版本未记录'}</span>
        </footer>
      </div>
    );
  }
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
