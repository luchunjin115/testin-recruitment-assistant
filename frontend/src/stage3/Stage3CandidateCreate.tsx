import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowLeftOutlined,
  BookOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  DeleteOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SolutionOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import {
  Alert,
  Button,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Skeleton,
  Space,
  Spin,
  Tag,
  Upload,
  message,
} from 'antd';
import type { UploadProps } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  CandidateJobOption,
  createStage3Candidate,
  createStage3CandidateFromResume,
  getStage3CandidateJobs,
  Stage3CandidateCreateInput,
} from './services/candidates';
import {
  abandonStage3Resume,
  extractStage3ResumeText,
  ResumeStructureResponse,
  Stage3ResumeDetail,
  structureStage3Resume,
  uploadStage3Resume,
} from './services/resumes';
import {
  parseResumeStructureError,
  ResumeStructureViewState,
  summarizeResumeDraft,
} from './resumeStructureState';
import {
  areResumeFieldValuesEqual,
  isResumeBasicFieldName,
  mergeResumeBasicInfo,
  ResumeBasicFieldConflict,
  ResumeBasicFieldName,
} from './resumeDraftMerge';
import {
  buildEducationCandidates,
  buildProjectCandidates,
  buildWorkCandidates,
  ResumeExperienceCandidate,
  ResumeExperienceKind,
} from './resumeExperienceImport';
import './styles/index.css';

type JobLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; jobs: CandidateJobOption[] };

type ResumeWorkflow =
  | { status: 'idle' }
  | { status: 'uploading'; filename: string }
  | { status: 'extracting'; resume: Stage3ResumeDetail }
  | { status: 'ready'; resume: Stage3ResumeDetail }
  | { status: 'failed'; message: string; resume?: Stage3ResumeDetail };

type ResumeBasicMergeViewState = {
  filledFields: ResumeBasicFieldName[];
  conflicts: Partial<Record<ResumeBasicFieldName, ResumeBasicFieldConflict>>;
};

type ResumeExperienceImportItemState = {
  selectedKeys: string[];
  importedKeys: string[];
};

type ResumeExperienceImportViewState = Record<
  ResumeExperienceKind,
  ResumeExperienceImportItemState
>;

type ResumeExperienceCandidateTrayProps<TFormValue> = {
  candidates: ResumeExperienceCandidate<TFormValue>[];
  disabled: boolean;
  hasExistingRecords: boolean;
  importedKeys: string[];
  label: string;
  onImport: (keys: string[]) => void;
  onSelectionChange: (keys: string[]) => void;
  selectedKeys: string[];
};

const emptyExperienceImportState = (): ResumeExperienceImportViewState => ({
  education: { selectedKeys: [], importedKeys: [] },
  work: { selectedKeys: [], importedKeys: [] },
  project: { selectedKeys: [], importedKeys: [] },
});

const ResumeExperienceCandidateTray = <TFormValue,>({
  candidates,
  disabled,
  hasExistingRecords,
  importedKeys,
  label,
  onImport,
  onSelectionChange,
  selectedKeys,
}: ResumeExperienceCandidateTrayProps<TFormValue>) => {
  if (candidates.length === 0) return null;

  const availableCandidates = candidates.filter(candidate => !importedKeys.includes(candidate.key));
  const selectedAvailableKeys = selectedKeys.filter(key => (
    availableCandidates.some(candidate => candidate.key === key)
  ));
  const importKeys = selectedAvailableKeys.length > 0
    ? selectedAvailableKeys
    : hasExistingRecords ? [] : availableCandidates.map(candidate => candidate.key);
  const buttonLabel = selectedAvailableKeys.length > 0
    ? `导入所选 ${selectedAvailableKeys.length} 条`
    : hasExistingRecords
      ? '请先勾选要导入的经历'
      : `导入全部 ${availableCandidates.length} 条`;

  const changeSelection = (candidateKey: string, checked: boolean) => {
    onSelectionChange(checked
      ? Array.from(new Set([...selectedKeys, candidateKey]))
      : selectedKeys.filter(key => key !== candidateKey));
  };

  return (
    <div className="s3-candidate-ai-tray">
      <div className="s3-candidate-ai-tray-heading">
        <div>
          <span>AI 识别候选</span>
          <strong>{candidates.length} 条{label}</strong>
        </div>
        <Tag bordered={false} color={hasExistingRecords ? 'gold' : 'blue'}>
          {hasExistingRecords ? '人工记录优先' : '表单当前为空'}
        </Tag>
      </div>
      <p className="s3-candidate-ai-tray-guidance">
        {hasExistingRecords
          ? '表单已有记录，AI 不会自动拼接。请勾选确认需要追加的条目。'
          : '这些内容尚未进入表单。你可以导入全部，也可以先勾选部分条目。'}
      </p>
      <div className="s3-candidate-ai-candidates">
        {candidates.map(candidate => {
          const imported = importedKeys.includes(candidate.key);
          const checked = selectedKeys.includes(candidate.key);
          return (
            <label
              className={`s3-candidate-ai-candidate ${imported ? 'is-imported' : ''}`}
              key={candidate.key}
            >
              <Checkbox
                checked={imported || checked}
                disabled={disabled || imported}
                onChange={event => changeSelection(candidate.key, event.target.checked)}
              />
              <span className="s3-candidate-ai-candidate-copy">
                <span className="s3-candidate-ai-candidate-title">
                  <strong>{candidate.title}</strong>
                  <span>{candidate.subtitle}</span>
                </span>
                {candidate.details.map(detail => <small key={detail}>{detail}</small>)}
                {candidate.tags.length > 0 && (
                  <span className="s3-candidate-ai-candidate-tags">
                    {candidate.tags.slice(0, 5).map(tag => <i key={tag}>{tag}</i>)}
                    {candidate.tags.length > 5 && <i>+{candidate.tags.length - 5}</i>}
                  </span>
                )}
              </span>
              <Tag bordered={false} color={imported ? 'green' : 'default'}>
                {imported ? '已导入' : '待确认'}
              </Tag>
            </label>
          );
        })}
      </div>
      {availableCandidates.length > 0 ? (
        <Button
          disabled={disabled || importKeys.length === 0}
          onClick={() => onImport(importKeys)}
          type={hasExistingRecords ? 'default' : 'primary'}
        >
          {buttonLabel}
        </Button>
      ) : (
        <span className="s3-candidate-ai-tray-complete"><CheckCircleOutlined /> 这组 AI 候选已全部导入</span>
      )}
    </div>
  );
};

const acceptedExtensions = ['.pdf', '.docx', '.txt'];
const maxFileSize = 10 * 1024 * 1024;

const getRequestErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first?.msg === 'string') return first.msg;
    }
    if (error.code === 'ECONNABORTED') return '请求超时，请确认后端服务可用后重试';
  }
  return error instanceof Error && error.message ? error.message : fallback;
};

const formatFileSize = (size: number | null) => {
  if (size === null) return '大小未记录';
  if (size < 1024) return `${size} B`;
  return `${(size / 1024).toFixed(1)} KB`;
};

const Stage3CandidateCreate: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm<Stage3CandidateCreateInput>();
  const [messageApi, messageContext] = message.useMessage();
  const [modal, modalContext] = Modal.useModal();
  const [jobState, setJobState] = useState<JobLoadState>({ status: 'loading' });
  const [resumeWorkflow, setResumeWorkflow] = useState<ResumeWorkflow>({ status: 'idle' });
  const [structureWorkflow, setStructureWorkflow] = useState<ResumeStructureViewState>({
    status: 'idle',
  });
  const [basicMergeState, setBasicMergeState] = useState<ResumeBasicMergeViewState>({
    filledFields: [],
    conflicts: {},
  });
  const [experienceImportState, setExperienceImportState] = useState<ResumeExperienceImportViewState>(
    emptyExperienceImportState,
  );
  const [submitting, setSubmitting] = useState(false);
  const [abandoning, setAbandoning] = useState(false);

  const loadJobs = useCallback(async () => {
    setJobState({ status: 'loading' });
    try {
      setJobState({ status: 'ready', jobs: await getStage3CandidateJobs() });
    } catch (error) {
      setJobState({
        status: 'error',
        message: getRequestErrorMessage(error, '无法读取新版岗位数据'),
      });
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const attachedResume = useMemo(() => {
    if (resumeWorkflow.status === 'ready' || resumeWorkflow.status === 'extracting') {
      return resumeWorkflow.resume;
    }
    if (resumeWorkflow.status === 'failed') return resumeWorkflow.resume;
    return undefined;
  }, [resumeWorkflow]);

  const resumeBusy = resumeWorkflow.status === 'uploading'
    || resumeWorkflow.status === 'extracting'
    || structureWorkflow.status === 'processing';

  const displayedStructureResult = useMemo<ResumeStructureResponse | undefined>(() => {
    if (structureWorkflow.status === 'succeeded') return structureWorkflow.result;
    if (structureWorkflow.status === 'failed') return structureWorkflow.previousResult;
    return undefined;
  }, [structureWorkflow]);

  const structureSummary = useMemo(
    () => displayedStructureResult
      ? summarizeResumeDraft(displayedStructureResult.draft)
      : undefined,
    [displayedStructureResult],
  );

  const educationCandidates = useMemo(
    () => displayedStructureResult
      ? buildEducationCandidates(displayedStructureResult.draft.education_records)
      : [],
    [displayedStructureResult],
  );
  const workCandidates = useMemo(
    () => displayedStructureResult
      ? buildWorkCandidates(displayedStructureResult.draft.work_experiences)
      : [],
    [displayedStructureResult],
  );
  const projectCandidates = useMemo(
    () => displayedStructureResult
      ? buildProjectCandidates(displayedStructureResult.draft.project_experiences)
      : [],
    [displayedStructureResult],
  );

  const abandonAttachedResume = async () => {
    if (!attachedResume) return true;

    setAbandoning(true);
    try {
      await abandonStage3Resume(attachedResume.id);
      setResumeWorkflow({ status: 'idle' });
      setStructureWorkflow({ status: 'idle' });
      setBasicMergeState(previous => ({ ...previous, conflicts: {} }));
      messageApi.success('未绑定的简历文件和记录已清理');
      return true;
    } catch (error) {
      messageApi.error(getRequestErrorMessage(error, '简历清理失败，请重试后再离开'));
      return false;
    } finally {
      setAbandoning(false);
    }
  };

  const mergeBasicInfoIntoForm = (result: ResumeStructureResponse) => {
    const mergeResult = mergeResumeBasicInfo(
      form.getFieldsValue(),
      result.draft.basic_info,
    );
    if (mergeResult.filledFields.length > 0) {
      form.setFieldsValue(mergeResult.fillValues);
    }
    setBasicMergeState(previous => ({
      filledFields: Array.from(new Set([
        ...mergeResult.filledFields,
        ...previous.filledFields.filter(fieldName => (
          mergeResult.matchingFields.includes(fieldName)
        )),
      ])),
      conflicts: mergeResult.conflicts,
    }));
    return mergeResult;
  };

  const syncExperienceImportCandidates = (result: ResumeStructureResponse) => {
    const candidateKeys: Record<ResumeExperienceKind, string[]> = {
      education: buildEducationCandidates(result.draft.education_records).map(item => item.key),
      work: buildWorkCandidates(result.draft.work_experiences).map(item => item.key),
      project: buildProjectCandidates(result.draft.project_experiences).map(item => item.key),
    };
    setExperienceImportState(previous => ({
      education: {
        selectedKeys: [],
        importedKeys: previous.education.importedKeys.filter(key => candidateKeys.education.includes(key)),
      },
      work: {
        selectedKeys: [],
        importedKeys: previous.work.importedKeys.filter(key => candidateKeys.work.includes(key)),
      },
      project: {
        selectedKeys: [],
        importedKeys: previous.project.importedKeys.filter(key => candidateKeys.project.includes(key)),
      },
    }));
  };

  const structureResume = async (resume: Stage3ResumeDetail, force = false) => {
    setStructureWorkflow({ status: 'processing', force });
    try {
      const result = await structureStage3Resume(resume.id, force);
      const mergeResult = mergeBasicInfoIntoForm(result);
      syncExperienceImportCandidates(result);
      setStructureWorkflow({ status: 'succeeded', result });
      const sourceText = result.from_cache ? '已加载保存的 AI 草稿' : 'AI 简历识别完成';
      messageApi.success(
        `${sourceText}：补充 ${mergeResult.filledFields.length} 个空字段，${Object.keys(mergeResult.conflicts).length} 个字段待核对`,
      );
    } catch (error) {
      setStructureWorkflow(parseResumeStructureError(error));
    }
  };

  const changeExperienceSelection = (kind: ResumeExperienceKind, selectedKeys: string[]) => {
    setExperienceImportState(previous => ({
      ...previous,
      [kind]: { ...previous[kind], selectedKeys },
    }));
  };

  const importExperienceCandidates = <TFormValue,>(
    kind: ResumeExperienceKind,
    candidates: ResumeExperienceCandidate<TFormValue>[],
    keys: string[],
    add: (defaultValue?: TFormValue, insertIndex?: number) => void,
    label: string,
  ) => {
    const importCandidates = candidates.filter(candidate => keys.includes(candidate.key));
    importCandidates.forEach(candidate => add(candidate.formValue));
    setExperienceImportState(previous => ({
      ...previous,
      [kind]: {
        selectedKeys: previous[kind].selectedKeys.filter(key => !keys.includes(key)),
        importedKeys: Array.from(new Set([...previous[kind].importedKeys, ...keys])),
      },
    }));
    messageApi.success(`已将 ${importCandidates.length} 条${label}加入表单，请继续核对和修改`);
  };

  const removeExperienceRecord = (
    kind: ResumeExperienceKind,
    listName: 'educationRecords' | 'workExperiences' | 'projectExperiences',
    index: number,
    remove: (index: number | number[]) => void,
  ) => {
    const candidateKey = form.getFieldValue([listName, index, 'aiCandidateKey']);
    remove(index);
    if (typeof candidateKey !== 'string') return;
    setExperienceImportState(previous => ({
      ...previous,
      [kind]: {
        selectedKeys: previous[kind].selectedKeys,
        importedKeys: previous[kind].importedKeys.filter(key => key !== candidateKey),
      },
    }));
  };

  const renderExperienceSource = (
    listName: 'educationRecords' | 'workExperiences' | 'projectExperiences',
    index: number,
  ) => (
    typeof form.getFieldValue([listName, index, 'aiCandidateKey']) === 'string'
      ? <Tag bordered={false} color="blue">AI 导入</Tag>
      : null
  );

  const adoptAiBasicField = (fieldName: ResumeBasicFieldName) => {
    const conflict = basicMergeState.conflicts[fieldName];
    if (!conflict) return;
    form.setFieldValue(fieldName, conflict.aiValue);
    setBasicMergeState(previous => {
      const conflicts = { ...previous.conflicts };
      delete conflicts[fieldName];
      return {
        filledFields: Array.from(new Set([...previous.filledFields, fieldName])),
        conflicts,
      };
    });
    messageApi.success('已采用这一项 AI 结果，你仍可以继续修改');
  };

  const handleFormValuesChange = (changedValues: Partial<Stage3CandidateCreateInput>) => {
    const changedFieldNames = Object.keys(changedValues).filter(isResumeBasicFieldName);
    setBasicMergeState(previous => {
      const filledFields = previous.filledFields.filter(
        fieldName => !changedFieldNames.includes(fieldName),
      );
      const conflicts = { ...previous.conflicts };
      changedFieldNames.forEach(fieldName => {
        const conflict = conflicts[fieldName];
        if (!conflict) return;
        const nextValue = changedValues[fieldName];
        if (areResumeFieldValuesEqual(nextValue, conflict.aiValue)) {
          delete conflicts[fieldName];
        } else if (typeof nextValue === 'string' || typeof nextValue === 'number') {
          conflicts[fieldName] = { ...conflict, currentValue: nextValue };
        }
      });
      return { filledFields, conflicts };
    });
  };

  const renderBasicFieldLabel = (fieldName: ResumeBasicFieldName, label: string) => {
    const wasFilledByAi = basicMergeState.filledFields.includes(fieldName);
    const hasConflict = Boolean(basicMergeState.conflicts[fieldName]);
    return (
      <span className="s3-candidate-field-label">
        <span>{label}</span>
        {wasFilledByAi && <Tag bordered={false} color="blue">AI 补充</Tag>}
        {hasConflict && <Tag bordered={false} color="gold">AI 识别到另一结果</Tag>}
      </span>
    );
  };

  const renderBasicFieldConflict = (fieldName: ResumeBasicFieldName) => {
    const conflict = basicMergeState.conflicts[fieldName];
    if (!conflict) return undefined;
    return (
      <span className="s3-candidate-field-conflict">
        <span>AI 结果：<strong>{String(conflict.aiValue)}</strong></span>
        <Button onClick={() => adoptAiBasicField(fieldName)} size="small" type="link">
          采用 AI 结果
        </Button>
      </span>
    );
  };

  const confirmRestructure = (resume: Stage3ResumeDetail) => {
    if (resumeBusy || submitting || abandoning) return;
    modal.confirm({
      title: '重新识别这份简历？',
      content: '这会发起一次新的 AI 请求。新识别失败时，上一次成功草稿仍会保留。',
      okText: '重新识别',
      cancelText: '保留当前草稿',
      onOk: async () => structureResume(resume, true),
    });
  };

  const confirmAbandon = (navigateAfter: boolean) => {
    if (resumeBusy || submitting || abandoning) return;
    if (!attachedResume) {
      if (navigateAfter) navigate('/stage3/candidates');
      return;
    }

    modal.confirm({
      title: navigateAfter ? '取消创建候选人？' : '放弃当前简历？',
      content: navigateAfter
        ? '当前候选人尚未创建。继续后会删除这份未绑定简历的数据库记录和实际文件。'
        : '继续后会删除这份未绑定简历的数据库记录和实际文件，你可以随后重新上传。',
      okText: navigateAfter ? '删除简历并返回' : '删除这份简历',
      okButtonProps: { danger: true },
      cancelText: '继续编辑',
      onOk: async () => {
        const cleaned = await abandonAttachedResume();
        if (!cleaned) return Promise.reject();
        if (navigateAfter) navigate('/stage3/candidates');
        return undefined;
      },
    });
  };

  const extractResume = async (resume: Stage3ResumeDetail) => {
    setResumeWorkflow({ status: 'extracting', resume });
    try {
      const parsedResume = await extractStage3ResumeText(resume.id);
      setResumeWorkflow({ status: 'ready', resume: parsedResume });
      messageApi.success('简历原文提取完成');
      await structureResume(parsedResume);
    } catch (error) {
      setStructureWorkflow({ status: 'idle' });
      setResumeWorkflow({
        status: 'failed',
        message: getRequestErrorMessage(error, '简历原文提取失败'),
        resume,
      });
    }
  };

  const uploadResume = async (file: File) => {
    setStructureWorkflow({ status: 'idle' });
    setBasicMergeState(previous => ({ ...previous, conflicts: {} }));
    setExperienceImportState(emptyExperienceImportState());
    setResumeWorkflow({ status: 'uploading', filename: file.name });
    try {
      const uploadedResume = await uploadStage3Resume(file);
      await extractResume(uploadedResume);
    } catch (error) {
      setResumeWorkflow({
        status: 'failed',
        message: getRequestErrorMessage(error, '简历上传失败'),
      });
    }
  };

  const beforeUpload: UploadProps['beforeUpload'] = file => {
    const dotIndex = file.name.lastIndexOf('.');
    const extension = dotIndex >= 0 ? file.name.slice(dotIndex).toLowerCase() : '';
    if (!acceptedExtensions.includes(extension)) {
      messageApi.error('请选择 PDF、DOCX 或 TXT 格式的简历');
      return Upload.LIST_IGNORE;
    }
    if (file.size > maxFileSize) {
      messageApi.error('简历文件不能超过 10MB');
      return Upload.LIST_IGNORE;
    }
    void uploadResume(file);
    return false;
  };

  const uploadProps: UploadProps = {
    accept: acceptedExtensions.join(','),
    beforeUpload,
    disabled: resumeBusy || Boolean(attachedResume) || submitting || abandoning,
    fileList: [],
    maxCount: 1,
    multiple: false,
    showUploadList: false,
  };

  const handleSubmit = async (values: Stage3CandidateCreateInput) => {
    if (resumeBusy || abandoning) {
      messageApi.warning('请等待简历上传、原文提取和 AI 识别结束');
      return;
    }

    setSubmitting(true);
    try {
      const candidate = attachedResume
        ? await createStage3CandidateFromResume(attachedResume.id, values)
        : await createStage3Candidate(values);
      messageApi.success(`${candidate.name} 已创建`);
      navigate(`/stage3/candidates/${candidate.id}`);
    } catch (error) {
      messageApi.error(getRequestErrorMessage(error, '候选人创建失败，请稍后重试'));
    } finally {
      setSubmitting(false);
    }
  };

  if (jobState.status === 'loading') {
    return (
      <main aria-busy="true" className="s3-main s3-candidate-create-page">
        <section className="s3-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="s3-state-panel"><Skeleton active paragraph={{ rows: 12 }} /></section>
      </main>
    );
  }

  if (jobState.status === 'error') {
    return (
      <main className="s3-main s3-candidate-create-page">
        <section className="s3-page-heading s3-candidate-create-heading">
          <div>
            <span className="s3-section-kicker">阶段 5 · AI 草稿辅助录入</span>
            <h2>新增候选人</h2>
            <p>岗位数据加载成功后才能建立一致的候选人和简历关联。</p>
          </div>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/stage3/candidates')}>返回列表</Button>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadJobs()}>重新加载</Button>}
          className="s3-section-gap"
          description={jobState.message}
          message="新版岗位数据加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  return (
    <>
      {messageContext}
      {modalContext}
      <main className="s3-main s3-candidate-create-page">
        <section className="s3-page-heading s3-candidate-create-heading">
          <div className="s3-candidate-create-heading-copy">
            <Button
              aria-label="返回候选人列表"
              className="s3-candidate-create-back"
              disabled={resumeBusy || submitting || abandoning}
              icon={<ArrowLeftOutlined />}
              onClick={() => confirmAbandon(true)}
              type="text"
            />
            <div>
              <span className="s3-section-kicker">阶段 5 · AI 草稿辅助录入</span>
              <h2>新增候选人</h2>
              <p>可以纯手动填写，也可以上传简历生成待核对的 AI 草稿，确认后一次性创建并绑定。</p>
            </div>
          </div>
          <Tag bordered={false} color="blue">真实写入 /api/v2</Tag>
        </section>

        <Alert
          className="s3-candidate-create-boundary"
          description="上传后会自动生成 AI 草稿。普通字段只补当前空值；教育、工作和项目经历只展示为候选内容，必须由 HR 明确选择后才进入可编辑表单。人工已有内容不会被覆盖。"
          message="AI 只补空字段，人工内容始终优先"
          showIcon
          type="info"
        />

        <Form<Stage3CandidateCreateInput>
          autoComplete="off"
          form={form}
          initialValues={{ source: 'HR手动录入', educationRecords: [], workExperiences: [], projectExperiences: [] }}
          layout="vertical"
          onFinish={values => void handleSubmit(values)}
          onValuesChange={handleFormValuesChange}
          requiredMark="optional"
        >
          <div className="s3-candidate-create-layout">
            <div className="s3-candidate-create-main">
              <section className="s3-candidate-form-card">
                <div className="s3-candidate-form-card-header">
                  <span><UserOutlined /></span>
                  <div><h3>基本资料</h3><p>姓名为必填，其余信息可以稍后继续完善</p></div>
                </div>
                <div className="s3-candidate-form-grid">
                  <Form.Item
                    extra={renderBasicFieldConflict('name')}
                    label={renderBasicFieldLabel('name', '候选人姓名')}
                    name="name"
                    rules={[
                      { required: true, whitespace: true, message: '请输入候选人姓名' },
                      { max: 100, message: '姓名不能超过 100 个字符' },
                    ]}
                  >
                    <Input disabled={submitting} maxLength={100} placeholder="例如：张三" />
                  </Form.Item>
                  <Form.Item extra={renderBasicFieldConflict('phone')} label={renderBasicFieldLabel('phone', '手机号码')} name="phone" rules={[{ max: 20 }]}>
                    <Input disabled={submitting} maxLength={20} placeholder="常用联系电话" />
                  </Form.Item>
                  <Form.Item
                    extra={renderBasicFieldConflict('email')}
                    label={renderBasicFieldLabel('email', '电子邮箱')}
                    name="email"
                    rules={[{ type: 'email', message: '请输入有效邮箱地址' }, { max: 100 }]}
                  >
                    <Input disabled={submitting} maxLength={100} placeholder="name@example.com" />
                  </Form.Item>
                  <Form.Item extra={renderBasicFieldConflict('gender')} label={renderBasicFieldLabel('gender', '性别')} name="gender">
                    <Select
                      allowClear
                      disabled={submitting}
                      options={['男', '女', '其他'].map(value => ({ value, label: value }))}
                      placeholder="未填写"
                    />
                  </Form.Item>
                  <Form.Item extra={renderBasicFieldConflict('age')} label={renderBasicFieldLabel('age', '年龄')} name="age" rules={[{ type: 'number', min: 0, max: 120 }]}>
                    <InputNumber disabled={submitting} max={120} min={0} placeholder="未填写" />
                  </Form.Item>
                  <Form.Item extra={renderBasicFieldConflict('location')} label={renderBasicFieldLabel('location', '所在城市')} name="location" rules={[{ max: 100 }]}>
                    <Input disabled={submitting} maxLength={100} placeholder="例如：长沙" />
                  </Form.Item>
                </div>
              </section>

              <section className="s3-candidate-form-card">
                <div className="s3-candidate-form-card-header">
                  <span><SolutionOutlined /></span>
                  <div><h3>求职与当前经历</h3><p>岗位将同时写入 Candidate 和关联 Resume</p></div>
                </div>
                <div className="s3-candidate-form-grid">
                  <Form.Item label="应聘岗位" name="appliedJobId">
                    <Select
                      allowClear
                      disabled={submitting}
                      notFoundContent="新版岗位库暂无记录"
                      optionFilterProp="label"
                      options={jobState.jobs.map(job => ({ value: job.id, label: job.title }))}
                      placeholder="选择应聘岗位"
                      showSearch
                    />
                  </Form.Item>
                  <Form.Item label="来源渠道" name="source" rules={[{ max: 50 }]}>
                    <Select
                      disabled={submitting}
                      options={['HR手动录入', '招聘网站', '内推', '邮件', '其他'].map(value => ({ value, label: value }))}
                    />
                  </Form.Item>
                  <Form.Item extra={renderBasicFieldConflict('currentCompany')} label={renderBasicFieldLabel('currentCompany', '当前公司')} name="currentCompany" rules={[{ max: 200 }]}>
                    <Input disabled={submitting} maxLength={200} placeholder="未填写" />
                  </Form.Item>
                  <Form.Item extra={renderBasicFieldConflict('currentTitle')} label={renderBasicFieldLabel('currentTitle', '当前职位')} name="currentTitle" rules={[{ max: 200 }]}>
                    <Input disabled={submitting} maxLength={200} placeholder="未填写" />
                  </Form.Item>
                  <Form.Item extra={renderBasicFieldConflict('workYears')} label={renderBasicFieldLabel('workYears', '工作年限')} name="workYears" rules={[{ type: 'number', min: 0, max: 80 }]}>
                    <InputNumber addonAfter="年" disabled={submitting} max={80} min={0} placeholder="未填写" />
                  </Form.Item>
                  <Form.Item extra={renderBasicFieldConflict('educationLevel')} label={renderBasicFieldLabel('educationLevel', '最高学历')} name="educationLevel">
                    <Select
                      allowClear
                      disabled={submitting}
                      options={['博士', '硕士', '本科', '大专', '高中及以下', '其他'].map(value => ({ value, label: value }))}
                      placeholder="未填写"
                    />
                  </Form.Item>
                </div>
              </section>

              <Form.List name="educationRecords">
                {(fields, { add, remove }) => (
                  <section className="s3-candidate-form-card">
                    <div className="s3-candidate-form-card-header">
                      <span><BookOutlined /></span>
                      <div><h3>教育经历</h3><p>可添加多段院校、学历和专业记录</p></div>
                      <Button disabled={submitting} icon={<PlusOutlined />} onClick={() => add()}>添加教育经历</Button>
                    </div>
                    {fields.length === 0 ? (
                      <p className="s3-candidate-record-empty">暂无教育经历，按需添加</p>
                    ) : (
                      <div className="s3-candidate-record-list">
                        {fields.map((field, index) => (
                          <div className="s3-candidate-record" key={field.key}>
                            <div className="s3-candidate-record-title">
                              <div><strong>教育经历 {index + 1}</strong>{renderExperienceSource('educationRecords', field.name)}</div>
                              <Button danger disabled={submitting} icon={<DeleteOutlined />} onClick={() => removeExperienceRecord('education', 'educationRecords', field.name, remove)} size="small" type="text">删除</Button>
                            </div>
                            <div className="s3-candidate-form-grid is-three">
                              <Form.Item label="院校" name={[field.name, 'school']}><Input disabled={submitting} maxLength={200} /></Form.Item>
                              <Form.Item label="学历" name={[field.name, 'degree']}><Input disabled={submitting} maxLength={50} /></Form.Item>
                              <Form.Item label="专业" name={[field.name, 'major']}><Input disabled={submitting} maxLength={200} /></Form.Item>
                              <Form.Item label="开始时间" name={[field.name, 'startDate']}><Input disabled={submitting} maxLength={20} placeholder="YYYY-MM" /></Form.Item>
                              <Form.Item label="结束时间" name={[field.name, 'endDate']}><Input disabled={submitting} maxLength={20} placeholder="YYYY-MM" /></Form.Item>
                              <div className="s3-candidate-school-flags">
                                <Form.Item name={[field.name, 'is985']} valuePropName="checked"><Checkbox disabled={submitting}>985</Checkbox></Form.Item>
                                <Form.Item name={[field.name, 'is211']} valuePropName="checked"><Checkbox disabled={submitting}>211</Checkbox></Form.Item>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <ResumeExperienceCandidateTray
                      candidates={educationCandidates}
                      disabled={submitting || resumeBusy}
                      hasExistingRecords={fields.length > 0}
                      importedKeys={experienceImportState.education.importedKeys}
                      label="教育经历"
                      onImport={keys => importExperienceCandidates(
                        'education',
                        educationCandidates,
                        keys,
                        add,
                        '教育经历',
                      )}
                      onSelectionChange={keys => changeExperienceSelection('education', keys)}
                      selectedKeys={experienceImportState.education.selectedKeys}
                    />
                  </section>
                )}
              </Form.List>

              <Form.List name="workExperiences">
                {(fields, { add, remove }) => (
                  <section className="s3-candidate-form-card">
                    <div className="s3-candidate-form-card-header">
                      <span><SolutionOutlined /></span>
                      <div><h3>工作经历</h3><p>记录公司、职位、职责和技术关键词</p></div>
                      <Button disabled={submitting} icon={<PlusOutlined />} onClick={() => add()}>添加工作经历</Button>
                    </div>
                    {fields.length === 0 ? (
                      <p className="s3-candidate-record-empty">暂无工作经历，按需添加</p>
                    ) : (
                      <div className="s3-candidate-record-list">
                        {fields.map((field, index) => (
                          <div className="s3-candidate-record" key={field.key}>
                            <div className="s3-candidate-record-title">
                              <div><strong>工作经历 {index + 1}</strong>{renderExperienceSource('workExperiences', field.name)}</div>
                              <Button danger disabled={submitting} icon={<DeleteOutlined />} onClick={() => removeExperienceRecord('work', 'workExperiences', field.name, remove)} size="small" type="text">删除</Button>
                            </div>
                            <div className="s3-candidate-form-grid">
                              <Form.Item label="公司" name={[field.name, 'company']}><Input disabled={submitting} maxLength={200} /></Form.Item>
                              <Form.Item label="职位" name={[field.name, 'title']}><Input disabled={submitting} maxLength={200} /></Form.Item>
                              <Form.Item label="开始时间" name={[field.name, 'startDate']}><Input disabled={submitting} maxLength={20} placeholder="YYYY-MM" /></Form.Item>
                              <Form.Item label="结束时间" name={[field.name, 'endDate']}><Input disabled={submitting} maxLength={20} placeholder="YYYY-MM 或 至今" /></Form.Item>
                              <Form.Item className="is-full" label="技术关键词" name={[field.name, 'techStack']}><Input disabled={submitting} placeholder="用逗号分隔，例如：Python、FastAPI、PostgreSQL" /></Form.Item>
                              <Form.Item className="is-full" label="工作描述" name={[field.name, 'description']}><Input.TextArea disabled={submitting} autoSize={{ minRows: 3, maxRows: 8 }} /></Form.Item>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <ResumeExperienceCandidateTray
                      candidates={workCandidates}
                      disabled={submitting || resumeBusy}
                      hasExistingRecords={fields.length > 0}
                      importedKeys={experienceImportState.work.importedKeys}
                      label="工作经历"
                      onImport={keys => importExperienceCandidates(
                        'work',
                        workCandidates,
                        keys,
                        add,
                        '工作经历',
                      )}
                      onSelectionChange={keys => changeExperienceSelection('work', keys)}
                      selectedKeys={experienceImportState.work.selectedKeys}
                    />
                  </section>
                )}
              </Form.List>

              <Form.List name="projectExperiences">
                {(fields, { add, remove }) => (
                  <section className="s3-candidate-form-card">
                    <div className="s3-candidate-form-card-header">
                      <span><SafetyCertificateOutlined /></span>
                      <div><h3>项目经历</h3><p>记录项目角色、技术栈和成果</p></div>
                      <Button disabled={submitting} icon={<PlusOutlined />} onClick={() => add()}>添加项目经历</Button>
                    </div>
                    {fields.length === 0 ? (
                      <p className="s3-candidate-record-empty">暂无项目经历，按需添加</p>
                    ) : (
                      <div className="s3-candidate-record-list">
                        {fields.map((field, index) => (
                          <div className="s3-candidate-record" key={field.key}>
                            <div className="s3-candidate-record-title">
                              <div><strong>项目经历 {index + 1}</strong>{renderExperienceSource('projectExperiences', field.name)}</div>
                              <Button danger disabled={submitting} icon={<DeleteOutlined />} onClick={() => removeExperienceRecord('project', 'projectExperiences', field.name, remove)} size="small" type="text">删除</Button>
                            </div>
                            <div className="s3-candidate-form-grid">
                              <Form.Item label="项目名称" name={[field.name, 'projectName']}><Input disabled={submitting} maxLength={200} /></Form.Item>
                              <Form.Item label="项目角色" name={[field.name, 'role']}><Input disabled={submitting} maxLength={100} /></Form.Item>
                              <Form.Item label="开始时间" name={[field.name, 'startDate']}><Input disabled={submitting} maxLength={20} placeholder="YYYY-MM" /></Form.Item>
                              <Form.Item label="结束时间" name={[field.name, 'endDate']}><Input disabled={submitting} maxLength={20} placeholder="YYYY-MM" /></Form.Item>
                              <Form.Item className="is-full" label="技术栈" name={[field.name, 'techStack']}><Input disabled={submitting} placeholder="用逗号分隔" /></Form.Item>
                              <Form.Item className="is-full" label="项目描述" name={[field.name, 'description']}><Input.TextArea disabled={submitting} autoSize={{ minRows: 3, maxRows: 8 }} /></Form.Item>
                              <Form.Item className="is-full" label="项目成果" name={[field.name, 'achievements']}><Input.TextArea disabled={submitting} autoSize={{ minRows: 2, maxRows: 6 }} /></Form.Item>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <ResumeExperienceCandidateTray
                      candidates={projectCandidates}
                      disabled={submitting || resumeBusy}
                      hasExistingRecords={fields.length > 0}
                      importedKeys={experienceImportState.project.importedKeys}
                      label="项目经历"
                      onImport={keys => importExperienceCandidates(
                        'project',
                        projectCandidates,
                        keys,
                        add,
                        '项目经历',
                      )}
                      onSelectionChange={keys => changeExperienceSelection('project', keys)}
                      selectedKeys={experienceImportState.project.selectedKeys}
                    />
                  </section>
                )}
              </Form.List>
            </div>

            <aside className="s3-candidate-create-aside">
              <section className="s3-candidate-resume-card">
                <div className="s3-candidate-resume-heading">
                  <span><FileTextOutlined /></span>
                  <div><h3>简历与 AI 草稿</h3><p>上传后依次提取原文并生成待核对草稿</p></div>
                </div>

                {resumeWorkflow.status === 'idle' && (
                  <Upload.Dragger {...uploadProps} className="s3-candidate-uploader">
                    <p className="ant-upload-drag-icon"><CloudUploadOutlined /></p>
                    <p className="ant-upload-text">点击或拖拽简历</p>
                    <p className="ant-upload-hint">PDF、DOCX、TXT，最大 10MB</p>
                  </Upload.Dragger>
                )}

                {resumeWorkflow.status === 'uploading' && (
                  <div aria-live="polite" className="s3-candidate-resume-progress">
                    <Spin />
                    <strong>正在安全上传</strong>
                    <span>{resumeWorkflow.filename}</span>
                  </div>
                )}

                {resumeWorkflow.status === 'extracting' && (
                  <div aria-live="polite" className="s3-candidate-resume-progress">
                    <Spin />
                    <strong>正在提取简历原文</strong>
                    <span>{resumeWorkflow.resume.filename}</span>
                  </div>
                )}

                {resumeWorkflow.status === 'ready' && (
                  <div className="s3-candidate-resume-result">
                    <div className="s3-candidate-resume-track" aria-label="简历处理进度">
                      <span className="is-done"><CheckCircleOutlined /> 文件已上传</span>
                      <i />
                      <span className="is-done"><CheckCircleOutlined /> 原文已提取</span>
                      <i className={displayedStructureResult ? 'is-done' : ''} />
                      <span className={displayedStructureResult ? 'is-done' : ''}>
                        <ThunderboltOutlined /> AI 草稿
                      </span>
                    </div>
                    <div className="s3-candidate-resume-meta">
                      <strong>{resumeWorkflow.resume.filename}</strong>
                      <span>{resumeWorkflow.resume.fileType || '类型未记录'} · {formatFileSize(resumeWorkflow.resume.fileSize)}</span>
                      <Tag bordered={false} icon={<CheckCircleOutlined />}>Resume #{resumeWorkflow.resume.id}</Tag>
                    </div>
                    {structureWorkflow.status === 'idle' && (
                      <Alert
                        action={<Button onClick={() => void structureResume(resumeWorkflow.resume)}>开始识别</Button>}
                        description="原文已经准备好。开始后会生成待 HR 核对的结构化草稿。"
                        message="可以开始 AI 识别"
                        showIcon
                        type="info"
                      />
                    )}
                    {structureWorkflow.status === 'processing' && (
                      <div aria-live="polite" className="s3-candidate-structure-progress">
                        <Spin size="small" />
                        <div>
                          <strong>{structureWorkflow.force ? '正在重新识别' : '正在生成 AI 草稿'}</strong>
                          <span>请保持当前页面开启；等待期间不会长期占用数据库事务。</span>
                        </div>
                      </div>
                    )}
                    {structureWorkflow.status === 'succeeded' && structureSummary && (
                      <div className="s3-candidate-structure-state is-success" aria-live="polite">
                        <Alert
                          description={structureWorkflow.result.from_cache
                            ? '本次直接读取之前保存的草稿，没有再次调用 AI。普通空字段已安全补充，请核对带有 AI 标记的内容。'
                            : '普通空字段已安全补充，人工已有内容保持不变；三类经历已作为候选内容展示，请按需确认导入。'}
                          message={structureWorkflow.result.from_cache
                            ? '已加载保存的 AI 草稿'
                            : 'AI 草稿生成完成'}
                          showIcon
                          type={structureWorkflow.result.from_cache ? 'info' : 'success'}
                        />
                        <div className="s3-candidate-structure-summary">
                          <span><strong>{structureSummary.basicInfo}</strong> 项基本信息</span>
                          <span><strong>{structureSummary.education}</strong> 条教育经历</span>
                          <span><strong>{structureSummary.work}</strong> 条工作经历</span>
                          <span><strong>{structureSummary.projects}</strong> 条项目经历</span>
                          <span><strong>{structureSummary.skills}</strong> 项技能</span>
                        </div>
                        <Button
                          icon={<ReloadOutlined />}
                          onClick={() => confirmRestructure(resumeWorkflow.resume)}
                        >
                          重新识别
                        </Button>
                      </div>
                    )}
                    {structureWorkflow.status === 'failed' && (
                      <div className={`s3-candidate-structure-state ${structureWorkflow.previousResult ? 'is-previous' : 'is-failed'}`} aria-live="polite">
                        <Alert
                          description={structureWorkflow.previousResult
                            ? '最近一次重新识别失败，下面的数量来自上一次成功草稿；原表单和此前已补充的内容保持不变。'
                            : structureWorkflow.httpStatus === 409
                              ? '同一份简历已有识别任务正在执行，没有产生第二次 AI 调用。请稍后再次检查。'
                              : '原文件、提取原文和人工表单均未受影响，你可以继续手动填写或主动重试。'}
                          message={structureWorkflow.previousResult
                            ? `重新识别失败：${structureWorkflow.message}`
                            : structureWorkflow.httpStatus === 409
                              ? '这份简历正在识别'
                              : structureWorkflow.message}
                          showIcon
                          type={structureWorkflow.previousResult || structureWorkflow.httpStatus === 409 ? 'warning' : 'error'}
                        />
                        {structureWorkflow.previousResult && structureSummary && (
                          <div className="s3-candidate-structure-summary">
                            <span><strong>{structureSummary.basicInfo}</strong> 项基本信息</span>
                            <span><strong>{structureSummary.education}</strong> 条教育经历</span>
                            <span><strong>{structureSummary.work}</strong> 条工作经历</span>
                            <span><strong>{structureSummary.projects}</strong> 条项目经历</span>
                            <span><strong>{structureSummary.skills}</strong> 项技能</span>
                          </div>
                        )}
                        <Button
                          icon={<ReloadOutlined />}
                          onClick={() => structureWorkflow.httpStatus === 409
                            ? void structureResume(resumeWorkflow.resume)
                            : confirmRestructure(resumeWorkflow.resume)}
                        >
                          {structureWorkflow.httpStatus === 409 ? '再次检查' : '重新识别'}
                        </Button>
                      </div>
                    )}
                    <div className="s3-candidate-raw-text">
                      <span>提取原文预览</span>
                      <pre>{resumeWorkflow.resume.rawText}</pre>
                    </div>
                    <Button
                      danger
                      disabled={structureWorkflow.status === 'processing'}
                      icon={<DeleteOutlined />}
                      loading={abandoning}
                      onClick={() => confirmAbandon(false)}
                    >
                      放弃这份简历
                    </Button>
                  </div>
                )}

                {resumeWorkflow.status === 'failed' && (
                  <div className="s3-candidate-resume-result">
                    <Alert
                      description={resumeWorkflow.resume
                        ? '文件已经安全保存。你可以重试提取，也可以继续手动填写并确认候选人。'
                        : '本次没有创建可用的 Resume 记录，请重新选择文件。'}
                      message={resumeWorkflow.message}
                      showIcon
                      type="error"
                    />
                    {resumeWorkflow.resume ? (
                      <>
                        <div className="s3-candidate-resume-meta">
                          <strong>{resumeWorkflow.resume.filename}</strong>
                          <span>待绑定 Resume #{resumeWorkflow.resume.id}</span>
                        </div>
                        <Space wrap>
                          <Button disabled={abandoning} icon={<ReloadOutlined />} onClick={() => void extractResume(resumeWorkflow.resume!)}>重新提取</Button>
                          <Button danger icon={<DeleteOutlined />} loading={abandoning} onClick={() => confirmAbandon(false)}>放弃这份简历</Button>
                        </Space>
                      </>
                    ) : (
                      <Button onClick={() => setResumeWorkflow({ status: 'idle' })}>重新选择文件</Button>
                    )}
                  </div>
                )}

                {attachedResume && (
                  <p className="s3-candidate-resume-retention">
                    使用“取消并返回”或“放弃这份简历”会安全删除未绑定文件。AI 识别期间不能主动删除；直接关闭页面时文件仍受未绑定 Resume 的超时清理规则约束。
                  </p>
                )}
              </section>

              <section className="s3-candidate-confirm-card">
                <h3>确认创建</h3>
                <p>{attachedResume
                  ? '将使用单事务创建候选人、经历记录并绑定当前 Resume。'
                  : '未上传简历，将创建一条纯手工候选人记录。'}</p>
                <Button
                  block
                  disabled={resumeBusy || abandoning}
                  htmlType="submit"
                  loading={submitting}
                  size="large"
                  type="primary"
                >
                  {attachedResume ? '确认创建并绑定简历' : '创建候选人'}
                </Button>
                <Button
                  block
                  disabled={resumeBusy || submitting || abandoning}
                  loading={abandoning}
                  onClick={() => confirmAbandon(true)}
                >
                  {attachedResume ? '取消创建并清理简历' : '取消并返回'}
                </Button>
              </section>
            </aside>
          </div>
        </Form>
      </main>
    </>
  );
};

export default Stage3CandidateCreate;
