import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowLeftOutlined,
  BookOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  FileTextOutlined,
  LockOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  SolutionOutlined,
  UserOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Empty,
  Form,
  Input,
  message,
  Select,
  Skeleton,
  Tag,
  Upload,
} from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import { Link } from 'react-router-dom';
import { getRecruitmentApplicationJobs, RecruitmentApplicationJob } from './services/application';
import './styles/index.css';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; jobs: RecruitmentApplicationJob[] };

type ApplicationFormValues = {
  name?: string;
  phone?: string;
  email?: string;
  school?: string;
  degree?: string;
  major?: string;
  jobId?: number;
  skills?: string;
  selfIntroduction?: string;
};

const acceptedExtensions = ['.pdf', '.doc', '.docx', '.txt'];

const getErrorMessage = (error: unknown) => {
  if (error instanceof Error && error.message) return error.message;
  return '暂时无法读取开放岗位，请稍后重试';
};

const RecruitmentApplicationForm: React.FC = () => {
  const [form] = Form.useForm<ApplicationFormValues>();
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [resumeFiles, setResumeFiles] = useState<UploadFile[]>([]);
  const selectedJobId = Form.useWatch('jobId', form);

  const loadJobs = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      setLoadState({ status: 'ready', jobs: await getRecruitmentApplicationJobs() });
    } catch (error) {
      setLoadState({ status: 'error', message: getErrorMessage(error) });
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const selectedJob = useMemo(() => {
    if (loadState.status !== 'ready') return undefined;
    return loadState.jobs.find(job => job.id === selectedJobId);
  }, [loadState, selectedJobId]);

  const uploadProps: UploadProps = {
    accept: acceptedExtensions.join(','),
    maxCount: 1,
    fileList: resumeFiles,
    beforeUpload: file => {
      const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
      if (!acceptedExtensions.includes(extension)) {
        message.error('请选择 PDF、DOC、DOCX 或 TXT 格式的简历');
        return Upload.LIST_IGNORE;
      }
      if (file.size > 10 * 1024 * 1024) {
        message.error('简历文件不能超过 10MB');
        return Upload.LIST_IGNORE;
      }
      setResumeFiles([file]);
      return false;
    },
    onRemove: () => {
      setResumeFiles([]);
    },
  };

  const renderShell = (content: React.ReactNode) => (
    <div className="recruitment-apply-page">
      <header className="recruitment-apply-header">
        <Link className="recruitment-apply-brand" to="/apply" aria-label="HR Agent 候选人投递">
          <span className="recruitment-apply-brand-mark">HR</span>
          <span>
            <strong>HR Agent</strong>
            <small>候选人投递</small>
          </span>
        </Link>
        <Tag className="recruitment-apply-preview-tag" icon={<LockOutlined />}>表单结构预览 · 不会提交</Tag>
      </header>
      {content}
    </div>
  );

  if (loadState.status === 'loading') {
    return renderShell(
      <main className="recruitment-apply-main" aria-busy="true">
        <div className="recruitment-apply-loading-card">
          <Skeleton active paragraph={{ rows: 10 }} />
        </div>
      </main>,
    );
  }

  if (loadState.status === 'error') {
    return renderShell(
      <main className="recruitment-apply-main">
        <div className="recruitment-apply-state-card">
          <Alert
            showIcon
            type="error"
            message="开放岗位加载失败"
            description={loadState.message}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void loadJobs()}>重新加载</Button>
        </div>
      </main>,
    );
  }

  const hasOpenJobs = loadState.jobs.length > 0;

  return renderShell(
    <main className="recruitment-apply-main">
      <section className="recruitment-apply-intro" aria-labelledby="application-title">
        <Link className="recruitment-apply-back" to="/app/dashboard">
          <ArrowLeftOutlined /> 返回招聘工作台
        </Link>
        <div className="recruitment-apply-eyebrow"><span /> CANDIDATE APPLICATION</div>
        <h1 id="application-title">加入我们，开启下一段职业旅程</h1>
        <p>选择一个正在招聘的岗位，填写个人信息并准备简历。本页目前用于确认新版投递体验，内容不会发送到服务器。</p>
        <div className="recruitment-apply-job-count">
          <strong>{loadState.jobs.length}</strong>
          <span>个开放岗位来自新版岗位数据</span>
        </div>
      </section>

      <div className="recruitment-apply-layout">
        <aside className="recruitment-apply-guide" aria-label="投递说明">
          <div className="recruitment-apply-guide-title">
            <SafetyCertificateOutlined />
            <div>
              <strong>投递前须知</strong>
              <span>请确认本页当前能力边界</span>
            </div>
          </div>
          <ol>
            <li>
              <span>01</span>
              <div><strong>选择岗位</strong><p>岗位来自新版只读接口，当前共有 {loadState.jobs.length} 个开放岗位。</p></div>
            </li>
            <li>
              <span>02</span>
              <div><strong>填写资料</strong><p>可体验完整字段结构，页面刷新后不会保留。</p></div>
            </li>
            <li>
              <span>03</span>
              <div><strong>准备简历</strong><p>文件仅保留在当前浏览器中，不会上传或解析。</p></div>
            </li>
          </ol>
          <div className="recruitment-apply-boundary-note">
            <LockOutlined />
            <span><strong>数据保护说明</strong>提交入口尚未开放，本页不会创建候选人、简历或 AI 结果。</span>
          </div>
        </aside>

        <section className="recruitment-apply-form-card" aria-label="候选人投递表单">
          {!hasOpenJobs && (
            <div className="recruitment-apply-empty-jobs">
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有开放岗位" />
              <p>岗位开放后即可继续填写投递信息，请稍后再来查看。</p>
            </div>
          )}

          {hasOpenJobs && (
            <Form<ApplicationFormValues>
              form={form}
              layout="vertical"
              requiredMark="optional"
              autoComplete="off"
            >
              <div className="recruitment-apply-section-heading">
                <span><UserOutlined /></span>
                <div><strong>基本信息</strong><p>用于后续招聘团队与候选人取得联系</p></div>
              </div>
              <div className="recruitment-apply-grid">
                <Form.Item label="姓名" name="name" rules={[{ required: true, message: '请填写姓名' }]}>
                  <Input placeholder="请输入真实姓名" />
                </Form.Item>
                <Form.Item label="手机号码" name="phone" rules={[{ required: true, message: '请填写手机号码' }]}>
                  <Input placeholder="请输入常用手机号码" />
                </Form.Item>
                <Form.Item className="recruitment-apply-grid-full" label="电子邮箱" name="email" rules={[{ type: 'email', message: '请输入有效邮箱地址' }]}>
                  <Input placeholder="name@example.com" />
                </Form.Item>
              </div>

              <div className="recruitment-apply-divider" />
              <div className="recruitment-apply-section-heading">
                <span><BookOutlined /></span>
                <div><strong>教育背景</strong><p>填写最高学历对应的院校与专业信息</p></div>
              </div>
              <div className="recruitment-apply-grid recruitment-apply-grid-three">
                <Form.Item label="毕业院校" name="school"><Input placeholder="院校名称" /></Form.Item>
                <Form.Item label="最高学历" name="degree">
                  <Select
                    placeholder="请选择"
                    options={['博士', '硕士', '本科', '大专', '其他'].map(value => ({ value, label: value }))}
                  />
                </Form.Item>
                <Form.Item label="所学专业" name="major"><Input placeholder="专业名称" /></Form.Item>
              </div>

              <div className="recruitment-apply-divider" />
              <div className="recruitment-apply-section-heading">
                <span><SolutionOutlined /></span>
                <div><strong>求职信息</strong><p>选择目标岗位并补充与岗位相关的能力</p></div>
              </div>
              <Form.Item label="应聘岗位" name="jobId" rules={[{ required: true, message: '请选择应聘岗位' }]}>
                <Select
                  showSearch
                  optionFilterProp="label"
                  placeholder="选择一个开放岗位"
                  options={loadState.jobs.map(job => ({
                    value: job.id,
                    label: job.department ? `${job.title} · ${job.department}` : job.title,
                  }))}
                />
              </Form.Item>

              {selectedJob && (
                <div className="recruitment-apply-selected-job">
                  <div className="recruitment-apply-selected-job-top">
                    <span><CheckCircleOutlined /></span>
                    <div><strong>{selectedJob.title}</strong><p>{selectedJob.department || '部门未填写'}</p></div>
                    <Tag>招聘中</Tag>
                  </div>
                  <div className="recruitment-apply-selected-job-copy">
                    <div><span>岗位说明</span><p>{selectedJob.description || '该岗位暂未填写岗位说明。'}</p></div>
                    <div>
                      <span>任职要求</span>
                      <p>{selectedJob.requirementSummary || '该岗位暂未填写任职要求。'}</p>
                      {selectedJob.requiredSkills.length > 0 && (
                        <div className="recruitment-apply-selected-job-skills">
                          {selectedJob.requiredSkills.map(skill => <Tag key={skill}>{skill}</Tag>)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <div className="recruitment-apply-grid">
                <Form.Item label="技能关键词" name="skills">
                  <Input placeholder="例如：React、Python、数据分析" />
                </Form.Item>
                <Form.Item label="个人简介" name="selfIntroduction">
                  <Input.TextArea autoSize={{ minRows: 3, maxRows: 6 }} placeholder="简要介绍与目标岗位相关的经历" />
                </Form.Item>
              </div>

              <div className="recruitment-apply-divider" />
              <div className="recruitment-apply-section-heading">
                <span><FileTextOutlined /></span>
                <div><strong>简历文件</strong><p>仅做本地选择演示，不会上传到服务器</p></div>
              </div>
              <Upload.Dragger {...uploadProps} className="recruitment-apply-uploader">
                <p className="ant-upload-drag-icon"><CloudUploadOutlined /></p>
                <p className="ant-upload-text">点击或拖拽简历到这里</p>
                <p className="ant-upload-hint">支持 PDF、DOC、DOCX、TXT，单个文件不超过 10MB</p>
                <Tag icon={<LockOutlined />}>仅本地选择，不会上传</Tag>
              </Upload.Dragger>

              <div className="recruitment-apply-submit-row">
                <div><LockOutlined /><span>当前不会保存任何表单或文件数据</span></div>
                <Button type="primary" size="large" icon={<SendOutlined />} disabled>
                  提交投递 · 后续开放
                </Button>
              </div>
            </Form>
          )}
        </section>
      </div>
    </main>,
  );
};

export default RecruitmentApplicationForm;
