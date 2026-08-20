import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeftOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  EditOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Alert, Button, Drawer, Empty, Modal, Skeleton, Tag } from 'antd';
import {
  getRecruitmentJobRubric,
  getRecruitmentJobRubricError,
  RecruitmentJobRubric,
  RubricCriterionSource,
  RubricDimension,
  RubricSource,
  RubricStatus,
  RubricTemplateKey,
} from './services/jobRubrics';
import { RecruitmentJob } from './services/jobs';
import RecruitmentJobRubricDraftPanel from './RecruitmentJobRubricDraftPanel';

type RubricLoadState =
  | { status: 'idle' | 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: RecruitmentJobRubric };

type Props = {
  job: RecruitmentJob | null;
  open: boolean;
  onClose: () => void;
};

const dimensionLabels: Record<RubricDimension, string> = {
  must_have_requirements: '必备条件',
  work_experience_relevance: '经验与职责',
  projects_and_capability: '项目 / 成果 / 深度',
  preferred_qualifications: '加分项',
  keywords_and_additional: '关键词 / 补充要求',
};

const sourceLabels: Record<RubricSource, string> = {
  standard_template: '标准模板',
  technical_template: '技术岗模板',
  non_technical_template: '非技术岗模板',
  ai_generated: 'AI 生成',
  hr_manual: 'HR 手动配置',
};

const templateLabels: Record<RubricTemplateKey, string> = {
  standard: '标准',
  technical: '技术岗',
  non_technical: '非技术岗',
};

const statusLabels: Record<RubricStatus, string> = {
  draft: '草稿',
  active: '已生效',
  archived: '已归档',
  abandoned: '已放弃',
};

const criterionSourceLabels: Record<RubricCriterionSource, string> = {
  template: '模板',
  ai_generated: 'AI 生成',
  hr_manual: 'HR 手动',
};

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hour12: false,
}).format(new Date(value));

const RecruitmentJobRubricDrawer: React.FC<Props> = ({ job, onClose, open }) => {
  const [loadState, setLoadState] = useState<RubricLoadState>({ status: 'idle' });
  const [view, setView] = useState<'current' | 'draft'>('current');
  const [draftDirty, setDraftDirty] = useState(false);
  const [draftPending, setDraftPending] = useState(false);
  const latestRequestId = useRef(0);

  const loadRubric = useCallback(async () => {
    if (!job) return;
    const requestId = latestRequestId.current + 1;
    latestRequestId.current = requestId;
    setLoadState({ status: 'loading' });
    try {
      const data = await getRecruitmentJobRubric(job.id);
      if (requestId === latestRequestId.current) setLoadState({ status: 'ready', data });
    } catch (error) {
      if (requestId === latestRequestId.current) {
        setLoadState({ status: 'error', message: getRecruitmentJobRubricError(error).message });
      }
    }
  }, [job]);

  useEffect(() => {
    if (open && job) void loadRubric();
    return () => { latestRequestId.current += 1; };
  }, [job, loadRubric, open]);

  useEffect(() => {
    if (!open) {
      setView('current');
      setDraftDirty(false);
      setDraftPending(false);
    }
  }, [open]);

  const weightItems = useMemo(() => {
    if (loadState.status !== 'ready') return [];
    const { weights } = loadState.data;
    return [
      { key: 'must-have', label: '必备条件', value: weights.mustHaveRequirements, tone: 'navy' },
      { key: 'experience', label: '经验与职责', value: weights.workExperienceRelevance, tone: 'blue' },
      { key: 'projects', label: '项目与能力', value: weights.projectsAndCapability, tone: 'teal' },
      { key: 'preferred', label: '加分项', value: weights.preferredQualifications, tone: 'amber' },
      { key: 'additional', label: '关键词与补充', value: weights.keywordsAndAdditional, tone: 'slate' },
    ];
  }, [loadState]);

  const rubric = loadState.status === 'ready' ? loadState.data : null;

  const leaveDraft = (action: () => void) => {
    if (draftPending) return;
    if (!draftDirty) {
      action();
      return;
    }
    Modal.confirm({
      title: '离开并放弃未保存修改？',
      content: '已保存的 Rubric 草稿不会被删除，当前表单内容将丢失。',
      okText: '放弃修改',
      okType: 'danger',
      cancelText: '继续编辑',
      onOk: () => {
        setDraftDirty(false);
        action();
      },
    });
  };

  return (
    <Drawer
      className="recruitment-rubric-drawer"
      closable={!draftPending}
      destroyOnClose
      keyboard={!draftPending}
      maskClosable={!draftPending}
      extra={view === 'draft' ? (
        <Button disabled={draftPending} icon={<ArrowLeftOutlined />} onClick={() => leaveDraft(() => setView('current'))}>返回正式版本</Button>
      ) : (
        <Button
          disabled={loadState.status !== 'ready'}
          icon={<EditOutlined />}
          onClick={() => setView('draft')}
        >
          编辑评分规则
        </Button>
      )}
      onClose={() => leaveDraft(onClose)}
      open={open}
      title={job ? `${job.title} · 评分规则` : '评分规则'}
      width="min(780px, 100vw)"
    >
      {view === 'draft' && job && rubric ? (
        <RecruitmentJobRubricDraftPanel
          currentVersion={rubric.version}
          jobId={job.id}
          onDirtyChange={setDraftDirty}
          onPendingChange={setDraftPending}
        />
      ) : loadState.status === 'idle' || loadState.status === 'loading' ? (
        <div aria-label="正在读取评分规则" className="recruitment-rubric-loading">
          <Skeleton active paragraph={{ rows: 8 }} />
        </div>
      ) : loadState.status === 'error' ? (
        <div className="recruitment-rubric-feedback">
          <Empty description={<div className="recruitment-empty-copy"><strong>暂时无法查看评分规则</strong><span>{loadState.message}</span></div>} image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button onClick={() => void loadRubric()}>重新读取</Button>
          </Empty>
        </div>
      ) : rubric && (
        <div className="recruitment-rubric-content">
          <section className="recruitment-rubric-hero">
            <div>
              <div className="recruitment-rubric-eyebrow"><AuditOutlined /> CURRENT RUBRIC</div>
              <h3>版本 v{rubric.version}</h3>
              <p>评分时会固定保存本版本快照，后续调整不会改写历史结果。</p>
            </div>
            <div className="recruitment-rubric-status-stack">
              <Tag bordered={false} color={rubric.isStale ? 'warning' : 'success'} icon={rubric.isStale ? <WarningOutlined /> : <CheckCircleOutlined />}>
                {rubric.isStale ? '待重新确认' : statusLabels[rubric.status]}
              </Tag>
              <span>{sourceLabels[rubric.source]}{rubric.templateKey ? ` · ${templateLabels[rubric.templateKey]}` : ''}</span>
            </div>
          </section>

          {rubric.isStale && (
            <Alert
              description={rubric.staleReason || '岗位中参与评分的内容已变化，重新确认前不能用它发起新评分。'}
              message="这把评分尺已过期"
              showIcon
              type="warning"
            />
          )}

          <section aria-labelledby="rubric-weight-title" className="recruitment-rubric-section">
            <div className="recruitment-rubric-section-heading">
              <div><span>01</span><h4 id="rubric-weight-title">五维权重</h4></div>
              <small>总和 100%</small>
            </div>
            <div
              aria-label={`五维权重：${weightItems.map(item => `${item.label} ${item.value}%`).join('，')}`}
              className="recruitment-rubric-weight-track"
              role="img"
            >
              {weightItems.filter(item => item.value > 0).map(item => (
                <span
                  className={`recruitment-rubric-weight-segment is-${item.tone}`}
                  key={item.key}
                  style={{ width: `${item.value}%` }}
                  title={`${item.label} ${item.value}%`}
                />
              ))}
            </div>
            <div className="recruitment-rubric-weight-legend">
              {weightItems.map(item => (
                <div key={item.key}>
                  <i className={`is-${item.tone}`} />
                  <span>{item.label}</span>
                  <strong>{item.value}%</strong>
                </div>
              ))}
            </div>
          </section>

          <Alert
            className="recruitment-rubric-boundary"
            description="年限、学历、必备技能和明确关键词由 Python 直接比较；只有下方需要理解语义的评分项会交给 DeepSeek。"
            icon={<InfoCircleOutlined />}
            message="两种规则各负其责，避免重复扣分"
            showIcon
            type="info"
          />

          <section aria-labelledby="rubric-criteria-title" className="recruitment-rubric-section">
            <div className="recruitment-rubric-section-heading">
              <div><span>02</span><h4 id="rubric-criteria-title">语义评分项</h4></div>
              <small>{rubric.semanticItems.length} 项 · 每项 0—10 分</small>
            </div>
            {rubric.semanticItems.length === 0 ? (
              <Empty description="当前版本还没有语义评分项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <div className="recruitment-rubric-criterion-list">
                {rubric.semanticItems.map((item, index) => (
                  <article className="recruitment-rubric-criterion" key={item.key}>
                    <header>
                      <div className="recruitment-rubric-criterion-title">
                        <span>{String(index + 1).padStart(2, '0')}</span>
                        <div><h5>{item.name}</h5><p>{item.description}</p></div>
                      </div>
                      <div className="recruitment-rubric-criterion-meta">
                        <Tag bordered={false}>{dimensionLabels[item.dimension]}</Tag>
                        <span>{criterionSourceLabels[item.source]} · 建议占比 {item.suggestedShare}%</span>
                      </div>
                    </header>
                    <dl className="recruitment-rubric-anchor-grid">
                      <div className="is-high"><dt>高分表现</dt><dd>{item.highScoreAnchor}</dd></div>
                      <div className="is-mid"><dt>中分表现</dt><dd>{item.midScoreAnchor}</dd></div>
                      <div className="is-low"><dt>低分表现</dt><dd>{item.lowScoreAnchor}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
            )}
          </section>

          <footer className="recruitment-rubric-audit">
            <span>规则 Schema v{rubric.schemaVersion} · 子项 v{rubric.subcriteriaVersion}</span>
            <span>{rubric.confirmedAt ? `确认于 ${formatDateTime(rubric.confirmedAt)}` : `更新于 ${formatDateTime(rubric.updatedAt)}`}</span>
          </footer>
        </div>
      )}
    </Drawer>
  );
};

export default RecruitmentJobRubricDrawer;
