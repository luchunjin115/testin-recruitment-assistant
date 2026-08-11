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
  Stage3ResumeDetail,
  uploadStage3Resume,
} from './services/resumes';
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
    || resumeWorkflow.status === 'extracting';

  const abandonAttachedResume = async () => {
    if (!attachedResume) return true;

    setAbandoning(true);
    try {
      await abandonStage3Resume(attachedResume.id);
      setResumeWorkflow({ status: 'idle' });
      messageApi.success('未绑定的简历文件和记录已清理');
      return true;
    } catch (error) {
      messageApi.error(getRequestErrorMessage(error, '简历清理失败，请重试后再离开'));
      return false;
    } finally {
      setAbandoning(false);
    }
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
    } catch (error) {
      setResumeWorkflow({
        status: 'failed',
        message: getRequestErrorMessage(error, '简历原文提取失败'),
        resume,
      });
    }
  };

  const uploadResume = async (file: File) => {
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
      messageApi.warning('请等待简历上传和原文提取结束');
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
            <span className="s3-section-kicker">阶段 4 · 统一新增候选人</span>
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
              <span className="s3-section-kicker">阶段 4 · 统一新增候选人</span>
              <h2>新增候选人</h2>
              <p>可以纯手动填写，也可以上传简历并保留提取原文，确认后一次性创建并绑定。</p>
            </div>
          </div>
          <Tag bordered={false} color="blue">真实写入 /api/v2</Tag>
        </section>

        <Alert
          className="s3-candidate-create-boundary"
          description="当前已经接通安全上传和 PDF、DOCX、TXT 原文提取。姓名、学历、经历等字段仍由 HR 手动填写；从原文识别并只补充空字段将在下一小步单独实现。"
          message="本步能力边界"
          showIcon
          type="info"
        />

        <Form<Stage3CandidateCreateInput>
          autoComplete="off"
          form={form}
          initialValues={{ source: 'HR手动录入', educationRecords: [], workExperiences: [], projectExperiences: [] }}
          layout="vertical"
          onFinish={values => void handleSubmit(values)}
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
                    label="候选人姓名"
                    name="name"
                    rules={[
                      { required: true, whitespace: true, message: '请输入候选人姓名' },
                      { max: 100, message: '姓名不能超过 100 个字符' },
                    ]}
                  >
                    <Input disabled={submitting} maxLength={100} placeholder="例如：张三" />
                  </Form.Item>
                  <Form.Item label="手机号码" name="phone" rules={[{ max: 20 }]}>
                    <Input disabled={submitting} maxLength={20} placeholder="常用联系电话" />
                  </Form.Item>
                  <Form.Item
                    label="电子邮箱"
                    name="email"
                    rules={[{ type: 'email', message: '请输入有效邮箱地址' }, { max: 100 }]}
                  >
                    <Input disabled={submitting} maxLength={100} placeholder="name@example.com" />
                  </Form.Item>
                  <Form.Item label="性别" name="gender">
                    <Select
                      allowClear
                      disabled={submitting}
                      options={['男', '女', '其他'].map(value => ({ value, label: value }))}
                      placeholder="未填写"
                    />
                  </Form.Item>
                  <Form.Item label="年龄" name="age" rules={[{ type: 'number', min: 0, max: 120 }]}>
                    <InputNumber disabled={submitting} max={120} min={0} placeholder="未填写" />
                  </Form.Item>
                  <Form.Item label="所在城市" name="location" rules={[{ max: 100 }]}>
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
                  <Form.Item label="当前公司" name="currentCompany" rules={[{ max: 200 }]}>
                    <Input disabled={submitting} maxLength={200} placeholder="未填写" />
                  </Form.Item>
                  <Form.Item label="当前职位" name="currentTitle" rules={[{ max: 200 }]}>
                    <Input disabled={submitting} maxLength={200} placeholder="未填写" />
                  </Form.Item>
                  <Form.Item label="工作年限" name="workYears" rules={[{ type: 'number', min: 0, max: 80 }]}>
                    <InputNumber addonAfter="年" disabled={submitting} max={80} min={0} placeholder="未填写" />
                  </Form.Item>
                  <Form.Item label="最高学历" name="educationLevel">
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
                              <strong>教育经历 {index + 1}</strong>
                              <Button danger disabled={submitting} icon={<DeleteOutlined />} onClick={() => remove(field.name)} size="small" type="text">删除</Button>
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
                              <strong>工作经历 {index + 1}</strong>
                              <Button danger disabled={submitting} icon={<DeleteOutlined />} onClick={() => remove(field.name)} size="small" type="text">删除</Button>
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
                              <strong>项目经历 {index + 1}</strong>
                              <Button danger disabled={submitting} icon={<DeleteOutlined />} onClick={() => remove(field.name)} size="small" type="text">删除</Button>
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
                  </section>
                )}
              </Form.List>
            </div>

            <aside className="s3-candidate-create-aside">
              <section className="s3-candidate-resume-card">
                <div className="s3-candidate-resume-heading">
                  <span><FileTextOutlined /></span>
                  <div><h3>简历文件</h3><p>可选；上传后立即提取原文</p></div>
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
                    <Alert message="原文提取完成" showIcon type="success" />
                    <div className="s3-candidate-resume-meta">
                      <strong>{resumeWorkflow.resume.filename}</strong>
                      <span>{resumeWorkflow.resume.fileType || '类型未记录'} · {formatFileSize(resumeWorkflow.resume.fileSize)}</span>
                      <Tag bordered={false} icon={<CheckCircleOutlined />}>Resume #{resumeWorkflow.resume.id}</Tag>
                    </div>
                    <div className="s3-candidate-raw-text">
                      <span>提取原文预览</span>
                      <pre>{resumeWorkflow.resume.rawText}</pre>
                    </div>
                    <Button
                      danger
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
                    使用“取消并返回”或“放弃这份简历”会安全删除未绑定文件。直接关闭页面时仍会暂存；超时自动清理将在下一小步接入。
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
