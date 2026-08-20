import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  CheckCircleOutlined,
  FileAddOutlined,
  ReloadOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { Alert, Button, Empty, Input, Modal, Skeleton, Tag } from 'antd';
import {
  createRecruitmentJobRubricTemplateDraft,
  generateRecruitmentJobRubricDraft,
  getRecruitmentJobRubricDraft,
  getRecruitmentJobRubricError,
  RecruitmentJobRubric,
  RubricDimension,
  RubricTemplateKey,
} from './services/jobRubrics';
import RecruitmentJobRubricItemEditor from './RecruitmentJobRubricItemEditor';

type DraftState =
  | { status: 'loading' }
  | { status: 'missing' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: RecruitmentJobRubric };

type Props = {
  currentVersion: number;
  jobId: number;
  onDirtyChange: (dirty: boolean) => void;
  onPendingChange: (pending: boolean) => void;
};

const dimensionLabels: Record<RubricDimension, string> = {
  must_have_requirements: '必备条件',
  work_experience_relevance: '经验与职责',
  projects_and_capability: '项目 / 成果 / 深度',
  preferred_qualifications: '加分项',
  keywords_and_additional: '关键词 / 补充要求',
};

const templateOptions: Array<{
  key: RubricTemplateKey;
  name: string;
  eyebrow: string;
  description: string;
}> = [
  {
    key: 'standard',
    name: '标准模板',
    eyebrow: 'STANDARD',
    description: '通用岗位的平衡评分尺，适合作为稳定起点。',
  },
  {
    key: 'technical',
    name: '技术岗模板',
    eyebrow: 'TECHNICAL',
    description: '更关注项目深度、技术决策和解决问题的证据。',
  },
  {
    key: 'non_technical',
    name: '非技术岗模板',
    eyebrow: 'BUSINESS',
    description: '更关注职责成果、协作方式和业务场景的匹配。',
  },
];

const RecruitmentJobRubricDraftPanel: React.FC<Props> = ({
  currentVersion,
  jobId,
  onDirtyChange,
  onPendingChange,
}) => {
  const [draftState, setDraftState] = useState<DraftState>({ status: 'loading' });
  const [selectedTemplate, setSelectedTemplate] = useState<RubricTemplateKey | null>(null);
  const [changeDetail, setChangeDetail] = useState('');
  const [operationKind, setOperationKind] = useState<'template' | 'ai' | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editorDirty, setEditorDirty] = useState(false);
  const [editorPending, setEditorPending] = useState(false);
  const latestRequestId = useRef(0);

  const operationPending = operationKind !== null;
  const operationFormDirty = (draftState.status === 'missing' || draftState.status === 'ready')
    && (selectedTemplate !== null || changeDetail.length > 0);

  useEffect(() => {
    onDirtyChange(operationFormDirty || editorDirty);
  }, [editorDirty, onDirtyChange, operationFormDirty]);

  useEffect(() => {
    onPendingChange(operationPending || editorPending);
  }, [editorPending, onPendingChange, operationPending]);

  useEffect(() => () => {
    onDirtyChange(false);
    onPendingChange(false);
  }, [onDirtyChange, onPendingChange]);

  const loadDraft = useCallback(async () => {
    const requestId = latestRequestId.current + 1;
    latestRequestId.current = requestId;
    setDraftState({ status: 'loading' });
    setOperationError(null);
    try {
      const data = await getRecruitmentJobRubricDraft(jobId);
      if (requestId === latestRequestId.current) setDraftState({ status: 'ready', data });
    } catch (error) {
      if (requestId !== latestRequestId.current) return;
      const parsed = getRecruitmentJobRubricError(error);
      if (parsed.code === 'RUBRIC_DRAFT_NOT_FOUND') {
        setDraftState({ status: 'missing' });
        return;
      }
      setDraftState({ status: 'error', message: parsed.message });
    }
  }, [jobId]);

  useEffect(() => {
    void loadDraft();
    return () => { latestRequestId.current += 1; };
  }, [loadDraft]);

  const createDraft = async () => {
    const detail = changeDetail.trim();
    if (!selectedTemplate || !detail || operationPending) return;
    const requestId = latestRequestId.current + 1;
    latestRequestId.current = requestId;
    setOperationKind('template');
    setOperationError(null);
    setNotice(null);
    try {
      const data = await createRecruitmentJobRubricTemplateDraft(jobId, {
        template_key: selectedTemplate,
        replace_existing: false,
        change_detail: detail,
      });
      if (requestId === latestRequestId.current) {
        setDraftState({ status: 'ready', data });
        setNotice('草稿已创建，当前正式版本没有变化。');
        setSelectedTemplate(null);
        setChangeDetail('');
      }
    } catch (error) {
      if (requestId !== latestRequestId.current) return;
      const parsed = getRecruitmentJobRubricError(error);
      if (parsed.code === 'RUBRIC_DRAFT_ALREADY_EXISTS') {
        setNotice('该岗位已有草稿，已为你读取最新内容。');
        setOperationKind(null);
        void loadDraft();
        return;
      }
      setOperationError(parsed.message);
    } finally {
      if (requestId === latestRequestId.current) setOperationKind(null);
    }
  };

  const generateDraft = async (replaceExisting: boolean) => {
    const detail = changeDetail.trim();
    if (!selectedTemplate || !detail || operationPending) return;
    const requestId = latestRequestId.current + 1;
    latestRequestId.current = requestId;
    setOperationKind('ai');
    setOperationError(null);
    setNotice(null);
    try {
      const data = await generateRecruitmentJobRubricDraft(jobId, {
        template_key: selectedTemplate,
        replace_existing: replaceExisting,
        change_detail: detail,
      });
      if (requestId === latestRequestId.current) {
        setDraftState({ status: 'ready', data });
        setNotice(replaceExisting
          ? 'AI 已生成新的草稿，原草稿已保留为放弃记录；正式版本没有变化。'
          : 'AI 已根据岗位生成草稿，正式版本没有变化。');
        setSelectedTemplate(null);
        setChangeDetail('');
      }
    } catch (error) {
      if (requestId !== latestRequestId.current) return;
      const parsed = getRecruitmentJobRubricError(error);
      if (parsed.code === 'RUBRIC_DRAFT_ALREADY_EXISTS' && !replaceExisting) {
        setNotice('生成期间检测到已有草稿，已为你读取最新内容。');
        setOperationKind(null);
        void loadDraft();
        return;
      }
      setOperationError(parsed.message);
    } finally {
      if (requestId === latestRequestId.current) setOperationKind(null);
    }
  };

  const confirmReplaceWithAi = () => {
    if (!selectedTemplate || !changeDetail.trim() || operationPending) return;
    Modal.confirm({
      title: '用 AI 生成结果替换当前草稿？',
      content: '当前草稿会保留为已放弃的审计记录，但其中尚未发布的人工修改不会进入新草稿。正式版本和候选人评分不会变化。',
      okText: '确认替换并生成',
      okType: 'danger',
      cancelText: '保留当前草稿',
      onOk: () => generateDraft(true),
    });
  };

  if (draftState.status === 'loading') {
    return (
      <div aria-label="正在查询未发布草稿" className="recruitment-rubric-loading">
        <Skeleton active paragraph={{ rows: 7 }} />
      </div>
    );
  }

  if (draftState.status === 'error') {
    return (
      <div className="recruitment-rubric-feedback">
        <Empty
          description={<div className="recruitment-empty-copy"><strong>暂时无法查询草稿</strong><span>{draftState.message}</span></div>}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button icon={<ReloadOutlined />} onClick={() => void loadDraft()}>重新查询</Button>
        </Empty>
      </div>
    );
  }

  if (draftState.status === 'missing') {
    return (
      <div className="recruitment-rubric-draft-create">
        <section className="recruitment-rubric-draft-intro">
          <div className="recruitment-rubric-eyebrow"><FileAddOutlined /> START A DRAFT</div>
          <h3>选择模板起草，或让 AI 按岗位生成</h3>
          <p>两种方式都只会得到未发布草稿。候选人评分仍继续使用正式版本 v{currentVersion}。</p>
        </section>

        <section aria-labelledby="rubric-template-title" className="recruitment-rubric-template-section">
          <div className="recruitment-rubric-section-heading">
            <div><span>01</span><h4 id="rubric-template-title">选择起草模板</h4></div>
            <small>只能选择一套</small>
          </div>
          <div className="recruitment-rubric-template-grid">
            {templateOptions.map(option => (
              <button
                aria-pressed={selectedTemplate === option.key}
                className={`recruitment-rubric-template-card${selectedTemplate === option.key ? ' is-selected' : ''}`}
                disabled={operationPending}
                key={option.key}
                onClick={() => {
                  setSelectedTemplate(option.key);
                  setOperationError(null);
                }}
                type="button"
              >
                <span>{option.eyebrow}</span>
                <strong>{option.name}</strong>
                <p>{option.description}</p>
                <i>{selectedTemplate === option.key ? '已选择' : '选择此模板'}</i>
              </button>
            ))}
          </div>
        </section>

        <section aria-labelledby="rubric-draft-reason-title" className="recruitment-rubric-template-section">
          <div className="recruitment-rubric-section-heading">
            <div><span>02</span><h4 id="rubric-draft-reason-title">记录起草原因</h4></div>
            <small>{changeDetail.trim().length}/1000</small>
          </div>
          <Input.TextArea
            autoSize={{ minRows: 3, maxRows: 6 }}
            maxLength={1000}
            disabled={operationPending}
            onChange={event => {
              setChangeDetail(event.target.value);
              setOperationError(null);
            }}
            placeholder="例如：根据该技术岗的项目要求建立第一版可编辑草稿"
            value={changeDetail}
          />
          <p className="recruitment-rubric-template-help">这条说明会进入 Rubric 审计记录，帮助后续理解为什么起草。</p>
          <div className={`recruitment-rubric-ai-lane${operationKind === 'ai' ? ' is-running' : ''}`}>
            <div><RobotOutlined /><strong>{operationKind === 'ai' ? 'DeepSeek 正在起草评分标准' : 'AI 岗位专用起草'}</strong></div>
            <ol aria-label="AI 起草流程">
              <li>读取岗位要求</li>
              <li>生成 5～8 个语义项</li>
              <li>交给 HR 继续编辑</li>
            </ol>
            <p aria-live="polite">
              {operationKind === 'ai'
                ? '生成可能需要几十秒，请保持当前窗口打开。'
                : 'AI 只生成需要理解上下文的评分项，不改写年限、学历和明确技能等硬规则。'}
            </p>
          </div>
          {operationError && <Alert message={operationError} showIcon type="error" />}
          <div className="recruitment-rubric-template-action">
            <Button
              disabled={!selectedTemplate || !changeDetail.trim() || operationPending}
              loading={operationKind === 'template'}
              onClick={() => void createDraft()}
            >
              按模板创建草稿
            </Button>
            <Button
              disabled={!selectedTemplate || !changeDetail.trim() || operationPending}
              icon={<RobotOutlined />}
              loading={operationKind === 'ai'}
              onClick={() => void generateDraft(false)}
              type="primary"
            >
              AI 根据岗位生成草稿
            </Button>
          </div>
        </section>
      </div>
    );
  }

  const draft = draftState.data;
  if (editing) {
    return (
      <RecruitmentJobRubricItemEditor
        draft={draft}
        jobId={jobId}
        onCancel={() => {
          setEditorDirty(false);
          setEditing(false);
        }}
        onDirtyChange={setEditorDirty}
        onPendingChange={setEditorPending}
        onSaved={updatedDraft => {
          setDraftState({ status: 'ready', data: updatedDraft });
          setNotice('权重和语义评分项已保存到草稿，正式版本没有变化。');
          setEditorDirty(false);
          setEditing(false);
        }}
      />
    );
  }

  return (
    <div className="recruitment-rubric-draft-summary">
      <section className="recruitment-rubric-draft-hero">
        <div>
          <div className="recruitment-rubric-eyebrow"><FileAddOutlined /> UNPUBLISHED DRAFT</div>
          <h3>草稿 v{draft.version}</h3>
          <p>这份内容还没有发布，当前评分仍使用正式版本 v{currentVersion}。</p>
        </div>
        <Tag bordered={false} color="gold">未发布</Tag>
      </section>

      {notice && <Alert message={notice} showIcon type="success" />}

      <section className="recruitment-rubric-section">
        <div className="recruitment-rubric-section-heading">
          <div><span>01</span><h4>草稿摘要</h4></div>
          <small>{draft.semanticItems.length} 个语义评分项</small>
        </div>
        <div className="recruitment-rubric-draft-metrics">
          <div>
            <span>起草方式</span>
            <strong>
              {draft.source === 'ai_generated'
                ? `AI 生成 · ${draft.templateKey ? templateOptions.find(item => item.key === draft.templateKey)?.name : '标准方向'}`
                : draft.templateKey
                  ? templateOptions.find(item => item.key === draft.templateKey)?.name
                  : '手动起草'}
            </strong>
          </div>
          <div><span>五维权重</span><strong>{Object.values(draft.weights).join(' / ')}</strong></div>
          <div><span>变更说明</span><strong>{draft.changeDetail || '未填写'}</strong></div>
        </div>
      </section>

      <section className="recruitment-rubric-section">
        <div className="recruitment-rubric-section-heading">
          <div><span>02</span><h4>语义项概览</h4></div>
          <small>本步只读</small>
        </div>
        <div className="recruitment-rubric-draft-item-list">
          {draft.semanticItems.map((item, index) => (
            <div key={item.key}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              <div><strong>{item.name}</strong><small>{dimensionLabels[item.dimension]} · 建议占比 {item.suggestedShare}%</small></div>
              <CheckCircleOutlined />
            </div>
          ))}
        </div>
        <div className="recruitment-rubric-draft-next">
          <Button onClick={() => setEditing(true)} type="primary">继续编辑评分项</Button>
          <span>本步不会发布或改变候选人评分。</span>
        </div>
      </section>

      <section className="recruitment-rubric-section recruitment-rubric-ai-replace">
        <div className="recruitment-rubric-section-heading">
          <div><span>03</span><h4>让 AI 重新起草整份内容</h4></div>
          <small>会替换当前未发布草稿</small>
        </div>
        <Alert
          description="生成成功后，当前草稿会保留为已放弃的审计记录；正式版本和候选人评分仍不会变化。生成失败时当前草稿保持不变。"
          message="这是草稿替换操作"
          showIcon
          type="warning"
        />
        <div className="recruitment-rubric-ai-direction-grid" role="group" aria-label="选择 AI 生成方向">
          {templateOptions.map(option => (
            <button
              aria-pressed={selectedTemplate === option.key}
              className={selectedTemplate === option.key ? 'is-selected' : ''}
              disabled={operationPending}
              key={option.key}
              onClick={() => {
                setSelectedTemplate(option.key);
                setOperationError(null);
              }}
              type="button"
            >
              <span>{option.eyebrow}</span>
              <strong>{option.name.replace('模板', '方向')}</strong>
            </button>
          ))}
        </div>
        <Input.TextArea
          autoSize={{ minRows: 2, maxRows: 5 }}
          disabled={operationPending}
          maxLength={1000}
          onChange={event => {
            setChangeDetail(event.target.value);
            setOperationError(null);
          }}
          placeholder="说明为什么需要 AI 重新生成，例如：岗位职责已细化，希望重新聚焦分布式系统项目证据"
          value={changeDetail}
        />
        <div className={`recruitment-rubric-ai-lane${operationKind === 'ai' ? ' is-running' : ''}`}>
          <div><RobotOutlined /><strong>{operationKind === 'ai' ? 'DeepSeek 正在生成替换草稿' : '旧草稿不会被静默覆盖'}</strong></div>
          <p aria-live="polite">
            {operationKind === 'ai'
              ? '正在读取当前岗位并生成 5～8 个评分项，请保持窗口打开。'
              : '选择方向、填写原因并通过最后一次确认后，系统才会请求 AI。'}
          </p>
        </div>
        {operationError && (
          <Alert
            description="当前草稿和正式版本均已保留，可以检查岗位内容或稍后重试。"
            message={operationError}
            showIcon
            type="error"
          />
        )}
        <div className="recruitment-rubric-ai-replace-action">
          <Button
            danger
            disabled={!selectedTemplate || !changeDetail.trim() || operationPending}
            icon={<RobotOutlined />}
            loading={operationKind === 'ai'}
            onClick={confirmReplaceWithAi}
          >
            AI 重新生成并替换草稿
          </Button>
        </div>
      </section>
    </div>
  );
};

export default RecruitmentJobRubricDraftPanel;
