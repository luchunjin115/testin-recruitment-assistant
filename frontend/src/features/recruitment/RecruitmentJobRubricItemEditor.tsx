import React, { useState } from 'react';
import {
  DeleteOutlined,
  PercentageOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { Alert, Button, Form, Input, InputNumber, Modal, Select, Tag, Tooltip } from 'antd';
import {
  assistRecruitmentJobRubricItem,
  getRecruitmentJobRubricError,
  RecruitmentJobRubric,
  RecruitmentJobRubricItemAssistResult,
  RecruitmentJobRubricShareOptimizationResult,
  RecruitmentJobRubricSemanticItem,
  RecruitmentJobRubricWeights,
  RubricDimension,
  optimizeRecruitmentJobRubricShares,
  updateRecruitmentJobRubricDraft,
} from './services/jobRubrics';

type SemanticItemFormValue = {
  key: string;
  name: string;
  dimension: RubricDimension;
  maxScore: 10;
  suggestedShare: number;
  description: string;
  highScoreAnchor: string;
  midScoreAnchor: string;
  lowScoreAnchor: string;
  source: 'template' | 'ai_generated' | 'hr_manual';
};

type EditorFormValues = {
  weights: RecruitmentJobRubricWeights;
  items: SemanticItemFormValue[];
  changeDetail: string;
};

type ItemAssistProposal = RecruitmentJobRubricItemAssistResult & {
  fieldName: number;
  itemKey: string;
  itemName: string;
};

type ShareOptimizationProposal = RecruitmentJobRubricShareOptimizationResult & {
  requestSignature: string;
  currentItems: Array<{
    key: string;
    name: string;
    suggestedShare: number;
  }>;
};

type Props = {
  draft: RecruitmentJobRubric;
  jobId: number;
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
  onPendingChange: (pending: boolean) => void;
  onSaved: (draft: RecruitmentJobRubric) => void;
};

const dimensionOptions: Array<{ value: RubricDimension; label: string }> = [
  { value: 'must_have_requirements', label: '必备条件' },
  { value: 'work_experience_relevance', label: '经验与职责' },
  { value: 'projects_and_capability', label: '项目 / 成果 / 深度' },
  { value: 'preferred_qualifications', label: '加分项' },
  { value: 'keywords_and_additional', label: '关键词 / 补充要求' },
];

const sourceLabels = {
  template: '模板项',
  ai_generated: 'AI 生成项',
  hr_manual: 'HR 手动项',
};

export const MIN_RUBRIC_SEMANTIC_ITEMS = 4;
export const MAX_RUBRIC_SEMANTIC_ITEMS = 10;
export const DEFAULT_RUBRIC_WEIGHTS: RecruitmentJobRubricWeights = {
  mustHaveRequirements: 40,
  workExperienceRelevance: 25,
  projectsAndCapability: 20,
  preferredQualifications: 10,
  keywordsAndAdditional: 5,
};

type WeightKey = keyof RecruitmentJobRubricWeights;

const weightConfigs: Array<{
  key: WeightKey;
  label: string;
  shortLabel: string;
  min: number;
  max: number;
}> = [
  { key: 'mustHaveRequirements', label: '必备技能与硬性要求', shortLabel: '必备条件', min: 30, max: 50 },
  { key: 'workExperienceRelevance', label: '工作经历与岗位职责', shortLabel: '经历职责', min: 15, max: 35 },
  { key: 'projectsAndCapability', label: '项目、成果与能力深度', shortLabel: '项目深度', min: 10, max: 30 },
  { key: 'preferredQualifications', label: '加分技能与加分经历', shortLabel: '加分项', min: 0, max: 20 },
  { key: 'keywordsAndAdditional', label: '关键词及补充要求', shortLabel: '补充要求', min: 0, max: 10 },
];

export const sumRubricWeights = (
  weights?: Partial<RecruitmentJobRubricWeights>,
): number => weightConfigs.reduce((total, config) => {
  const value = weights?.[config.key];
  return total + (typeof value === 'number' ? value : 0);
}, 0);

export const createManualRubricItem = (
  token = globalThis.crypto.randomUUID(),
): SemanticItemFormValue => ({
  key: `hr_manual_${token.replace(/[^a-z0-9]/gi, '').toLowerCase()}`.slice(0, 64),
  name: '',
  dimension: 'projects_and_capability',
  maxScore: 10,
  suggestedShare: 20,
  description: '',
  highScoreAnchor: '',
  midScoreAnchor: '',
  lowScoreAnchor: '',
  source: 'hr_manual',
});

const toInitialValues = (draft: RecruitmentJobRubric): EditorFormValues => ({
  weights: { ...draft.weights },
  items: draft.semanticItems.map(item => ({
    key: item.key,
    name: item.name,
    dimension: item.dimension,
    maxScore: item.maxScore,
    suggestedShare: item.suggestedShare,
    description: item.description,
    highScoreAnchor: item.highScoreAnchor,
    midScoreAnchor: item.midScoreAnchor,
    lowScoreAnchor: item.lowScoreAnchor,
    source: item.source,
  })),
  changeDetail: '',
});

const trimItem = (
  value: SemanticItemFormValue,
): RecruitmentJobRubricSemanticItem => ({
  key: value.key,
  name: value.name.trim(),
  dimension: value.dimension,
  maxScore: value.maxScore,
  suggestedShare: value.suggestedShare,
  description: value.description.trim(),
  highScoreAnchor: value.highScoreAnchor.trim(),
  midScoreAnchor: value.midScoreAnchor.trim(),
  lowScoreAnchor: value.lowScoreAnchor.trim(),
  source: value.source,
});

const RecruitmentJobRubricItemEditor: React.FC<Props> = ({
  draft,
  jobId,
  onCancel,
  onDirtyChange,
  onPendingChange,
  onSaved,
}) => {
  const [form] = Form.useForm<EditorFormValues>();
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [assistingItemKey, setAssistingItemKey] = useState<string | null>(null);
  const [assistError, setAssistError] = useState<{ itemKey: string; message: string } | null>(null);
  const [assistProposal, setAssistProposal] = useState<ItemAssistProposal | null>(null);
  const [optimizingShares, setOptimizingShares] = useState(false);
  const [shareOptimizationError, setShareOptimizationError] = useState<string | null>(null);
  const [shareOptimizationProposal, setShareOptimizationProposal] = useState<ShareOptimizationProposal | null>(null);
  const watchedWeights = Form.useWatch('weights', form);
  const watchedItems = Form.useWatch('items', form);
  const weights = watchedWeights ?? draft.weights;
  const weightTotal = sumRubricWeights(weights);
  const isWeightTotalValid = weightTotal === 100;
  const itemCount = watchedItems?.length ?? draft.semanticItems.length;

  const markDirty = () => {
    if (dirty) return;
    setDirty(true);
    onDirtyChange(true);
  };

  const requestCancel = () => {
    if (!dirty) {
      onCancel();
      return;
    }
    Modal.confirm({
      title: '放弃未保存的 Rubric 草稿修改？',
      content: '已保存的草稿不会被删除，本次表单修改将丢失。',
      okText: '放弃修改',
      okType: 'danger',
      cancelText: '继续编辑',
      onOk: () => {
        setDirty(false);
        onDirtyChange(false);
        onCancel();
      },
    });
  };

  const saveDraft = async (values: EditorFormValues) => {
    if (pending) return;
    if (sumRubricWeights(values.weights) !== 100) {
      setErrorMessage('五个维度的权重总和必须恰好为 100');
      return;
    }
    if (
      values.items.length < MIN_RUBRIC_SEMANTIC_ITEMS
      || values.items.length > MAX_RUBRIC_SEMANTIC_ITEMS
    ) {
      setErrorMessage('语义评分项总数必须保持在 4～10 项');
      return;
    }
    if (!draft.jobFingerprint) {
      setErrorMessage('草稿缺少岗位内容指纹，请返回后重新读取草稿');
      return;
    }
    setPending(true);
    onPendingChange(true);
    setErrorMessage(null);
    try {
      const semanticItems = values.items.map(trimItem);
      const updated = await updateRecruitmentJobRubricDraft(jobId, {
        expectedJobFingerprint: draft.jobFingerprint,
        weights: values.weights,
        semanticItems,
        changeDetail: values.changeDetail.trim(),
      });
      setDirty(false);
      onDirtyChange(false);
      onSaved(updated);
    } catch (error) {
      setErrorMessage(getRecruitmentJobRubricError(error).message);
    } finally {
      setPending(false);
      onPendingChange(false);
    }
  };

  const assistManualItem = async (fieldName: number) => {
    if (pending) return;
    const fieldsToValidate = [
      'name',
      'dimension',
      'suggestedShare',
      'description',
      'highScoreAnchor',
      'midScoreAnchor',
      'lowScoreAnchor',
    ].map(name => ['items', fieldName, name]);
    try {
      await form.validateFields(fieldsToValidate);
    } catch {
      const currentItem = form.getFieldValue(['items', fieldName]) as SemanticItemFormValue | undefined;
      setAssistError({
        itemKey: currentItem?.key ?? `field-${fieldName}`,
        message: '请先把这一项的名称、维度、占比、说明和三档标准填写完整，再让 AI 帮你校准。',
      });
      return;
    }

    const item = form.getFieldValue(['items', fieldName]) as SemanticItemFormValue | undefined;
    if (!item || item.source !== 'hr_manual') return;
    if (!draft.jobFingerprint) {
      setAssistError({ itemKey: item.key, message: '草稿缺少岗位内容指纹，请返回后重新读取草稿。' });
      return;
    }

    setPending(true);
    setAssistingItemKey(item.key);
    setAssistError(null);
    onPendingChange(true);
    try {
      const result = await assistRecruitmentJobRubricItem(jobId, {
        expectedJobFingerprint: draft.jobFingerprint,
        item: {
          name: item.name.trim(),
          description: item.description.trim(),
          dimension: item.dimension,
          suggestedShare: item.suggestedShare,
          highScoreAnchor: item.highScoreAnchor.trim(),
          midScoreAnchor: item.midScoreAnchor.trim(),
          lowScoreAnchor: item.lowScoreAnchor.trim(),
        },
      });
      setAssistProposal({
        ...result,
        fieldName,
        itemKey: item.key,
        itemName: item.name.trim(),
      });
    } catch (error) {
      const rubricError = getRecruitmentJobRubricError(error);
      setAssistError({
        itemKey: item.key,
        message: rubricError.code
          ? rubricError.message
          : 'AI 暂时没有返回可用建议，当前表单内容没有变化，请稍后重试。',
      });
    } finally {
      setPending(false);
      setAssistingItemKey(null);
      onPendingChange(false);
    }
  };

  const applyAssistProposal = () => {
    if (!assistProposal) return;
    const currentItem = form.getFieldValue(
      ['items', assistProposal.fieldName],
    ) as SemanticItemFormValue | undefined;
    if (!currentItem || currentItem.key !== assistProposal.itemKey) {
      setAssistError({
        itemKey: assistProposal.itemKey,
        message: '评分项位置已经变化，请关闭建议后重新发起 AI 辅助。',
      });
      setAssistProposal(null);
      return;
    }
    form.setFieldValue(['items', assistProposal.fieldName], {
      ...currentItem,
      description: assistProposal.suggestion.description,
      highScoreAnchor: assistProposal.suggestion.highScoreAnchor,
      midScoreAnchor: assistProposal.suggestion.midScoreAnchor,
      lowScoreAnchor: assistProposal.suggestion.lowScoreAnchor,
    });
    markDirty();
    setAssistError(null);
    setAssistProposal(null);
  };

  const optimizeCurrentShares = async () => {
    if (pending) return;
    const currentItems = form.getFieldValue('items') as SemanticItemFormValue[] | undefined;
    if (!currentItems || currentItems.length < MIN_RUBRIC_SEMANTIC_ITEMS) {
      setShareOptimizationError('请先保留至少 4 个完整评分项，再让 AI 优化当前占比。');
      return;
    }
    if (!isWeightTotalValid) {
      setShareOptimizationError('请先让五维总权重合计为 100；AI 不会修改这五个总权重。');
      return;
    }
    const fieldsToValidate = currentItems.flatMap((_, index) => [
      'name',
      'dimension',
      'suggestedShare',
      'description',
      'highScoreAnchor',
      'midScoreAnchor',
      'lowScoreAnchor',
    ].map(name => ['items', index, name]));
    try {
      await form.validateFields(fieldsToValidate);
    } catch {
      setShareOptimizationError('请先补全所有评分项的名称、维度、当前占比、说明和三档评分标准。');
      return;
    }
    if (!draft.jobFingerprint) {
      setShareOptimizationError('草稿缺少岗位内容指纹，请返回后重新读取草稿。');
      return;
    }

    setPending(true);
    setOptimizingShares(true);
    setShareOptimizationError(null);
    onPendingChange(true);
    try {
      const semanticItems = currentItems.map(trimItem);
      const result = await optimizeRecruitmentJobRubricShares(jobId, {
        expectedDraftId: draft.id,
        expectedJobFingerprint: draft.jobFingerprint,
        weights,
        semanticItems,
      });
      setShareOptimizationProposal({
        ...result,
        requestSignature: JSON.stringify(semanticItems),
        currentItems: semanticItems.map(item => ({
          key: item.key,
          name: item.name,
          suggestedShare: item.suggestedShare,
        })),
      });
    } catch (error) {
      const rubricError = getRecruitmentJobRubricError(error);
      setShareOptimizationError(
        rubricError.code
          ? rubricError.message
          : 'AI 暂时没有返回可用的占比建议，当前表单内容没有变化，请稍后重试。',
      );
    } finally {
      setPending(false);
      setOptimizingShares(false);
      onPendingChange(false);
    }
  };

  const applyShareOptimizationProposal = () => {
    if (!shareOptimizationProposal) return;
    const currentItems = form.getFieldValue('items') as SemanticItemFormValue[] | undefined;
    if (!currentItems) return;
    if (JSON.stringify(currentItems.map(trimItem)) !== shareOptimizationProposal.requestSignature) {
      setShareOptimizationError('AI 分析后评分项内容又发生了变化，请关闭建议后重新发起占比优化。');
      setShareOptimizationProposal(null);
      return;
    }
    const suggestions = new Map(
      shareOptimizationProposal.items.map(item => [item.key, item.suggestedShare]),
    );
    if (currentItems.some(item => !suggestions.has(item.key))) {
      setShareOptimizationError('评分项已经变化，请关闭建议后重新发起 AI 占比优化。');
      setShareOptimizationProposal(null);
      return;
    }
    form.setFieldValue('items', currentItems.map(item => ({
      ...item,
      suggestedShare: suggestions.get(item.key) ?? item.suggestedShare,
    })));
    markDirty();
    setShareOptimizationError(null);
    setShareOptimizationProposal(null);
  };

  return (
    <Form
      className="recruitment-rubric-item-editor"
      form={form}
      initialValues={toInitialValues(draft)}
      layout="vertical"
      onFinish={values => void saveDraft(values)}
      onFinishFailed={({ errorFields }) => {
        if (errorFields[0]) form.scrollToField(errorFields[0].name, { behavior: 'auto', block: 'center' });
      }}
      onValuesChange={markDirty}
    >
      <section className="recruitment-rubric-editor-intro">
        <div>
          <span>EDITING DRAFT v{draft.version}</span>
          <h3>校准五维配额与语义评分标准</h3>
          <p>先分配总分方向，再维护具体评分项；所有修改只保存到草稿。</p>
        </div>
        <Tag bordered={false} color="gold">{itemCount} / {MAX_RUBRIC_SEMANTIC_ITEMS} 项 · 未发布</Tag>
      </section>

      <section className="recruitment-rubric-weight-editor">
        <header>
          <div>
            <span>100-POINT ALLOCATION</span>
            <h4>五维总权重</h4>
            <p>这里决定 100 分的大方向；评分项“建议占比”只在各自维度内部生效。</p>
          </div>
          <div className="recruitment-rubric-weight-actions">
            <Button
              disabled={pending}
              htmlType="button"
              icon={<PercentageOutlined />}
              loading={optimizingShares}
              onClick={() => void optimizeCurrentShares()}
              size="small"
              type="primary"
            >
              AI 优化当前占比
            </Button>
            <Button
              disabled={pending}
              htmlType="button"
              icon={<ReloadOutlined />}
              onClick={() => {
                const hasChange = weightConfigs.some(
                  config => weights[config.key] !== DEFAULT_RUBRIC_WEIGHTS[config.key],
                );
                form.setFieldsValue({ weights: { ...DEFAULT_RUBRIC_WEIGHTS } });
                if (hasChange) markDirty();
                setErrorMessage(null);
              }}
              size="small"
            >
              恢复默认 40/25/20/10/5
            </Button>
          </div>
        </header>

        <div className={`recruitment-rubric-weight-total ${isWeightTotalValid ? 'is-valid' : 'is-invalid'}`}>
          <div>
            <span>当前合计</span>
            <strong aria-live="polite">{weightTotal}<small> / 100</small></strong>
          </div>
          <p>
            {isWeightTotalValid
              ? '分配完整，可以保存草稿。'
              : weightTotal < 100
                ? `还需分配 ${100 - weightTotal} 分。`
                : `已超出 ${weightTotal - 100} 分。`}
          </p>
          <div className="recruitment-rubric-weight-track" aria-hidden="true">
            <span style={{ width: `${Math.min(Math.max(weightTotal, 0), 100)}%` }} />
          </div>
        </div>

        <div className="recruitment-rubric-weight-inputs">
          {weightConfigs.map(config => (
            <div key={config.key}>
              <label htmlFor={`rubric-weight-${config.key}`} title={config.label}>{config.shortLabel}</label>
              <Form.Item
                name={['weights', config.key]}
                rules={[
                  { required: true, message: '请填写权重' },
                  {
                    type: 'number',
                    min: config.min,
                    max: config.max,
                    message: `允许范围 ${config.min}～${config.max}`,
                  },
                ]}
              >
                <InputNumber
                  id={`rubric-weight-${config.key}`}
                  max={config.max}
                  min={config.min}
                  precision={0}
                  suffix="%"
                />
              </Form.Item>
              <span>{config.min}～{config.max}</span>
            </div>
          ))}
        </div>
        {shareOptimizationError && (
          <Alert
            closable
            message={shareOptimizationError}
            onClose={() => setShareOptimizationError(null)}
            showIcon
            type="error"
          />
        )}
      </section>

      <Form.List name="items">
        {(fields, { add, remove }) => (
          <div className="recruitment-rubric-editor-list">
            {fields.map((field, index) => {
              const item = form.getFieldValue(['items', field.name]) as SemanticItemFormValue | undefined;
              const canRemove = fields.length > MIN_RUBRIC_SEMANTIC_ITEMS;
              return (
                <article className="recruitment-rubric-editor-item" key={field.key}>
                  <Form.Item hidden name={[field.name, 'key']}><Input /></Form.Item>
                  <Form.Item hidden name={[field.name, 'maxScore']}><InputNumber /></Form.Item>
                  <Form.Item hidden name={[field.name, 'source']}><Input /></Form.Item>
                  <header>
                    <div>
                      <span>{String(index + 1).padStart(2, '0')}</span>
                      <div><strong>{item?.key ?? 'hr_manual_pending'}</strong><small>满分固定 10 分</small></div>
                    </div>
                    <div className="recruitment-rubric-editor-item-actions">
                      <Tag bordered={false}>{sourceLabels[item?.source ?? 'hr_manual']}</Tag>
                      {item?.source === 'hr_manual' && (
                        <Tooltip title="根据当前岗位校准这一项的说明和高、中、低分标准">
                          <Button
                            className="recruitment-rubric-item-assist-button"
                            disabled={pending && assistingItemKey !== item.key}
                            icon={<RobotOutlined />}
                            loading={assistingItemKey === item.key}
                            onClick={() => void assistManualItem(field.name)}
                            size="small"
                            type="text"
                          >
                            AI 辅助完善
                          </Button>
                        </Tooltip>
                      )}
                      <Tooltip title={canRemove ? '从当前草稿移除此项' : '至少保留 4 个语义评分项'}>
                        <span>
                          <Button
                            aria-label={`删除评分项：${item?.name || `第 ${index + 1} 项`}`}
                            danger
                            disabled={!canRemove || pending}
                            icon={<DeleteOutlined />}
                            onClick={() => {
                              Modal.confirm({
                                title: '从草稿中删除这个评分项？',
                                content: '删除会先保留在当前表单中，只有保存草稿后才会写入系统。',
                                okText: '删除评分项',
                                okType: 'danger',
                                cancelText: '保留',
                                onOk: () => {
                                  remove(field.name);
                                  markDirty();
                                  setErrorMessage(null);
                                },
                              });
                            }}
                            size="small"
                            type="text"
                          >
                            删除
                          </Button>
                        </span>
                      </Tooltip>
                    </div>
                  </header>

                  {assistError?.itemKey === item?.key && (
                    <Alert
                      className="recruitment-rubric-item-assist-error"
                      closable
                      message={assistError?.message}
                      onClose={() => setAssistError(null)}
                      showIcon
                      type="error"
                    />
                  )}

                  <div className="recruitment-rubric-editor-basic-grid">
                    <Form.Item
                      label="评分项名称"
                      name={[field.name, 'name']}
                      rules={[
                        { required: true, whitespace: true, message: '请填写评分项名称' },
                        { max: 100, message: '名称不能超过 100 个字符' },
                      ]}
                    >
                      <Input placeholder="例如：系统设计与技术取舍" />
                    </Form.Item>
                    <Form.Item
                      label="所属维度"
                      name={[field.name, 'dimension']}
                      rules={[{ required: true, message: '请选择所属维度' }]}
                    >
                      <Select options={dimensionOptions} />
                    </Form.Item>
                    <Form.Item
                      extra="同维度内的相对重要程度"
                      label="建议占比"
                      name={[field.name, 'suggestedShare']}
                      rules={[{ required: true, message: '请填写建议占比' }]}
                    >
                      <InputNumber min={1} max={100} precision={0} suffix="%" />
                    </Form.Item>
                  </div>

                  <Form.Item
                    label="评分说明"
                    name={[field.name, 'description']}
                    rules={[
                      { required: true, whitespace: true, message: '请填写可从简历核对的评分说明' },
                      { max: 1000, message: '评分说明不能超过 1000 个字符' },
                    ]}
                  >
                    <Input.TextArea autoSize={{ minRows: 2, maxRows: 5 }} placeholder="说明这一项要评估什么，以及应从什么证据判断" />
                  </Form.Item>

                  <div className="recruitment-rubric-editor-anchor-grid">
                    <Form.Item
                      className="is-high"
                      label="高分表现"
                      name={[field.name, 'highScoreAnchor']}
                      rules={[{ required: true, whitespace: true, message: '请填写高分标准' }, { max: 1000 }]}
                    >
                      <Input.TextArea autoSize={{ minRows: 3, maxRows: 7 }} />
                    </Form.Item>
                    <Form.Item
                      className="is-mid"
                      label="中分表现"
                      name={[field.name, 'midScoreAnchor']}
                      rules={[{ required: true, whitespace: true, message: '请填写中分标准' }, { max: 1000 }]}
                    >
                      <Input.TextArea autoSize={{ minRows: 3, maxRows: 7 }} />
                    </Form.Item>
                    <Form.Item
                      className="is-low"
                      label="低分表现"
                      name={[field.name, 'lowScoreAnchor']}
                      rules={[{ required: true, whitespace: true, message: '请填写低分标准' }, { max: 1000 }]}
                    >
                      <Input.TextArea autoSize={{ minRows: 3, maxRows: 7 }} />
                    </Form.Item>
                  </div>
                </article>
              );
            })}
            <div className="recruitment-rubric-editor-collection-action">
              <Button
                block
                disabled={fields.length >= MAX_RUBRIC_SEMANTIC_ITEMS || pending}
                icon={<PlusOutlined />}
                onClick={() => {
                  add(createManualRubricItem());
                  markDirty();
                  setErrorMessage(null);
                }}
                type="dashed"
              >
                新增语义评分项
              </Button>
              <span>
                {fields.length >= MAX_RUBRIC_SEMANTIC_ITEMS
                  ? '已达到 10 项上限；如需新增，请先删除一项。'
                  : fields.length <= MIN_RUBRIC_SEMANTIC_ITEMS
                    ? '当前为 4 项下限，不能继续删除。'
                    : `还可新增 ${MAX_RUBRIC_SEMANTIC_ITEMS - fields.length} 项，至少保留 4 项。`}
              </span>
            </div>
          </div>
        )}
      </Form.List>

      <section className="recruitment-rubric-editor-reason">
        <Form.Item
          extra="例如：提高项目深度权重，并细化技术取舍的证据标准"
          label="本次修改说明"
          name="changeDetail"
          rules={[
            { required: true, whitespace: true, message: '请填写本次修改说明' },
            { max: 1000, message: '修改说明不能超过 1000 个字符' },
          ]}
        >
          <Input.TextArea autoSize={{ minRows: 2, maxRows: 5 }} placeholder="记录为什么修改这份草稿" />
        </Form.Item>
        {errorMessage && <Alert message={errorMessage} showIcon type="error" />}
      </section>

      <div className="recruitment-rubric-editor-actions">
        <span>保存后仍是草稿，不会影响当前候选人评分。</span>
        <div>
          <Button disabled={pending} onClick={requestCancel}>取消编辑</Button>
          <Button
            disabled={!isWeightTotalValid}
            htmlType="submit"
            icon={<SaveOutlined />}
            loading={pending && !assistingItemKey && !optimizingShares}
            title={isWeightTotalValid ? undefined : '五维权重合计为 100 后才能保存'}
            type="primary"
          >
            保存草稿修改
          </Button>
        </div>
      </div>

      <Modal
        cancelText="保留原内容"
        className="recruitment-rubric-item-assist-modal"
        destroyOnClose
        okText="采用这 4 项建议"
        onCancel={() => setAssistProposal(null)}
        onOk={applyAssistProposal}
        open={Boolean(assistProposal)}
        title="AI 单项校准单"
        width={680}
      >
        {assistProposal && (
          <div className="recruitment-rubric-item-assist-sheet">
            <div className="recruitment-rubric-item-assist-summary">
              <span><RobotOutlined /> DEEPSEEK REVIEW</span>
              <h4>{assistProposal.itemName}</h4>
              <p>
                AI 只建议评分说明与三档证据标准；名称、所属维度和建议占比继续保留 HR 当前设置。
                点击采用后仍只是未保存的表单修改。
              </p>
            </div>
            <dl className="recruitment-rubric-item-assist-ruler">
              <div className="is-description">
                <dt>评分说明</dt>
                <dd>{assistProposal.suggestion.description}</dd>
              </div>
              <div className="is-high">
                <dt>9—10 分</dt>
                <dd>{assistProposal.suggestion.highScoreAnchor}</dd>
              </div>
              <div className="is-mid">
                <dt>4—8 分</dt>
                <dd>{assistProposal.suggestion.midScoreAnchor}</dd>
              </div>
              <div className="is-low">
                <dt>0—3 分</dt>
                <dd>{assistProposal.suggestion.lowScoreAnchor}</dd>
              </div>
            </dl>
            <small className="recruitment-rubric-item-assist-meta">
              模型 {assistProposal.metadata.model} · Prompt {assistProposal.metadata.promptVersion}
              {assistProposal.metadata.inputTokens !== null
                ? ` · ${assistProposal.metadata.inputTokens + (assistProposal.metadata.outputTokens ?? 0)} tokens`
                : ''}
            </small>
          </div>
        )}
      </Modal>

      <Modal
        cancelText="保留当前占比"
        className="recruitment-rubric-share-optimization-modal"
        destroyOnClose
        okText="应用建议占比"
        onCancel={() => setShareOptimizationProposal(null)}
        onOk={applyShareOptimizationProposal}
        open={Boolean(shareOptimizationProposal)}
        title="AI 占比校准台"
        width={760}
      >
        {shareOptimizationProposal && (
          <div className="recruitment-rubric-share-optimization-sheet">
            <div className="recruitment-rubric-share-optimization-summary">
              <span><PercentageOutlined /> RELATIVE SHARE REVIEW</span>
              <h4>只校准评分项的维度内相对占比</h4>
              <p>{shareOptimizationProposal.rationale}</p>
              <small>
                五维总权重保持当前值不变。应用后仍只是未保存的表单修改，需要再点击“保存草稿修改”才会写入系统。
              </small>
            </div>
            <div className="recruitment-rubric-share-optimization-ledger">
              {shareOptimizationProposal.items.map(item => {
                const current = shareOptimizationProposal.currentItems.find(
                  candidate => candidate.key === item.key,
                );
                return (
                  <article key={item.key}>
                    <div>
                      <strong>{current?.name ?? item.key}</strong>
                      <small>{item.key}</small>
                    </div>
                    <div className="recruitment-rubric-share-change">
                      <span>{current?.suggestedShare ?? '—'}%</span>
                      <b aria-hidden="true">→</b>
                      <strong>{item.suggestedShare}%</strong>
                    </div>
                    <p>{item.reason}</p>
                  </article>
                );
              })}
            </div>
            <small className="recruitment-rubric-item-assist-meta">
              模型 {shareOptimizationProposal.metadata.model} · Prompt {shareOptimizationProposal.metadata.promptVersion}
              {shareOptimizationProposal.metadata.inputTokens !== null
                ? ` · ${shareOptimizationProposal.metadata.inputTokens + (shareOptimizationProposal.metadata.outputTokens ?? 0)} tokens`
                : ''}
            </small>
          </div>
        )}
      </Modal>
    </Form>
  );
};

export default RecruitmentJobRubricItemEditor;
