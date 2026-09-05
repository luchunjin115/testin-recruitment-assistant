import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCircleFilled,
  CloudUploadOutlined,
  EnvironmentOutlined,
  FileDoneOutlined,
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
  Checkbox,
  Empty,
  Form,
  Input,
  Select,
  Skeleton,
  Tag,
  Upload,
} from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import { Link } from 'react-router-dom';
import {
  getPublicApplicationApiError,
  getRecruitmentApplicationJobs,
  PUBLIC_APPLICATION_CONSENT_VERSION,
  PUBLIC_APPLICATION_FILE_EXTENSIONS,
  PUBLIC_APPLICATION_MAX_FILE_BYTES,
  submitPublicApplication,
} from './services/application';
import type {
  PublicApplicationAccepted,
  PublicApplicationApiError,
  RecruitmentApplicationJob,
} from './services/application';
import type { EmploymentType } from './services/jobs';
import './styles/index.css';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; jobs: RecruitmentApplicationJob[] };

type ApplicationFormValues = {
  name: string;
  phone: string;
  email: string;
  jobId: number;
  privacyConsent: boolean;
};

type SubmissionState =
  | { status: 'idle' }
  | { status: 'error'; error: PublicApplicationApiError }
  | { status: 'success'; accepted: PublicApplicationAccepted };

type SubmissionAttempt = {
  signature: string;
  resume: File;
  idempotencyKey: string;
};

const employmentTypeLabels: Record<EmploymentType, string> = {
  full_time: '全职',
  part_time: '兼职',
  internship: '实习',
  contract: '合同制',
};

const acceptedFileList = PUBLIC_APPLICATION_FILE_EXTENSIONS.join(',');

const getLoadErrorMessage = (error: unknown) => {
  const parsed = getPublicApplicationApiError(error);
  return parsed.message === '投递暂时未能送达，请检查网络后重试'
    ? '暂时无法读取开放岗位，请检查网络后重试'
    : parsed.message;
};

const isValidPublicPhone = (value: string) => {
  const trimmed = value.trim();
  if (!/^\+?[0-9 ()-]+$/.test(trimmed)) return false;
  const digits = trimmed.replace(/\D/g, '');
  return digits.length >= 7 && digits.length <= 15;
};

const formatAcceptedAt = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

const buildSubmissionSignature = (values: ApplicationFormValues) => JSON.stringify({
  name: values.name.trim(),
  phone: values.phone.trim(),
  email: values.email.trim().toLowerCase(),
  jobId: values.jobId,
  consentVersion: PUBLIC_APPLICATION_CONSENT_VERSION,
});

const RecruitmentApplicationForm: React.FC = () => {
  const [form] = Form.useForm<ApplicationFormValues>();
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [resumeFiles, setResumeFiles] = useState<UploadFile[]>([]);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [submissionState, setSubmissionState] = useState<SubmissionState>({ status: 'idle' });
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const attemptRef = useRef<SubmissionAttempt | null>(null);
  const resumeRegionRef = useRef<HTMLDivElement>(null);
  const resultHeadingRef = useRef<HTMLHeadingElement>(null);
  const selectedJobId = Form.useWatch('jobId', form);
  const privacyConsent = Form.useWatch('privacyConsent', form);

  const loadJobs = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      setLoadState({ status: 'ready', jobs: await getRecruitmentApplicationJobs() });
    } catch (error) {
      setLoadState({ status: 'error', message: getLoadErrorMessage(error) });
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (submissionState.status === 'success') resultHeadingRef.current?.focus();
  }, [submissionState.status]);

  const selectedJob = useMemo(() => {
    if (loadState.status !== 'ready') return undefined;
    return loadState.jobs.find(job => job.id === selectedJobId);
  }, [loadState, selectedJobId]);

  const uploadProps: UploadProps = {
    accept: acceptedFileList,
    maxCount: 1,
    fileList: resumeFiles,
    beforeUpload: file => {
      const dotIndex = file.name.lastIndexOf('.');
      const extension = dotIndex >= 0 ? file.name.slice(dotIndex).toLowerCase() : '';
      if (!PUBLIC_APPLICATION_FILE_EXTENSIONS.includes(
        extension as typeof PUBLIC_APPLICATION_FILE_EXTENSIONS[number],
      )) {
        setResumeError('请选择 PDF、DOCX 或 TXT 格式的简历');
        return Upload.LIST_IGNORE;
      }
      if (file.size > PUBLIC_APPLICATION_MAX_FILE_BYTES) {
        setResumeError('简历文件不能超过 10 MB');
        return Upload.LIST_IGNORE;
      }
      setResumeFiles([file]);
      setResumeError(null);
      setSubmissionState({ status: 'idle' });
      return false;
    },
    onRemove: () => {
      setResumeFiles([]);
      setResumeError('请上传一份简历');
      setSubmissionState({ status: 'idle' });
    },
  };

  const handleSubmit = async (values: ApplicationFormValues) => {
    if (submittingRef.current) return;
    const resume = (resumeFiles[0]?.originFileObj || resumeFiles[0]) as File | undefined;
    if (!resume) {
      setResumeError('请上传一份简历');
      resumeRegionRef.current?.focus();
      return;
    }

    const signature = buildSubmissionSignature(values);
    const previousAttempt = attemptRef.current;
    const idempotencyKey = previousAttempt
      && previousAttempt.signature === signature
      && previousAttempt.resume === resume
      ? previousAttempt.idempotencyKey
      : crypto.randomUUID();
    attemptRef.current = { signature, resume, idempotencyKey };
    submittingRef.current = true;
    setSubmitting(true);
    setSubmissionState({ status: 'idle' });
    try {
      const accepted = await submitPublicApplication({
        name: values.name,
        phone: values.phone,
        email: values.email,
        jobId: values.jobId,
        resume,
        idempotencyKey,
      });
      setSubmissionState({ status: 'success', accepted });
    } catch (error) {
      const parsedError = getPublicApplicationApiError(error);
      if (parsedError.code === 'IDEMPOTENCY_KEY_REUSED') attemptRef.current = null;
      if (parsedError.code === 'JOB_NOT_OPEN') {
        form.setFieldValue('jobId', undefined);
        try {
          setLoadState({ status: 'ready', jobs: await getRecruitmentApplicationJobs() });
        } catch {
          // Keep the safe submission error visible; a later page reload can refresh jobs.
        }
      }
      setSubmissionState({ status: 'error', error: parsedError });
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  const startAnotherApplication = () => {
    form.resetFields();
    setResumeFiles([]);
    setResumeError(null);
    setSubmissionState({ status: 'idle' });
    attemptRef.current = null;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  };

  const renderShell = (content: React.ReactNode) => (
    <div className="recruitment-apply-page">
      <header className="recruitment-apply-header">
        <Link className="recruitment-apply-brand" to="/apply" aria-label="HR智聘候选人投递首页">
          <span className="recruitment-apply-brand-mark">HR</span>
          <span>
            <strong>HR智聘</strong>
            <small>候选人投递</small>
          </span>
        </Link>
        <Tag className="recruitment-apply-trust-tag" icon={<SafetyCertificateOutlined />}>
          隐私保护 · 可靠受理
        </Tag>
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
        <div className="recruitment-apply-state-card" role="status">
          <Alert
            showIcon
            type="error"
            message="开放岗位加载失败"
            description={loadState.message}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void loadJobs()}>重新加载岗位</Button>
        </div>
      </main>,
    );
  }

  if (submissionState.status === 'success') {
    const { accepted } = submissionState;
    return renderShell(
      <main className="recruitment-apply-main recruitment-apply-result-main">
        <section className="recruitment-apply-success" aria-labelledby="application-success-title">
          <div className="recruitment-apply-success-mark" aria-hidden="true">
            <CheckCircleFilled />
          </div>
          <span className="recruitment-apply-result-kicker">APPLICATION RECEIVED</span>
          <h1 id="application-success-title" ref={resultHeadingRef} tabIndex={-1}>投递已收到</h1>
          <p>{accepted.message}</p>
          <dl className="recruitment-apply-receipt">
            <div><dt>投递凭证</dt><dd>{accepted.submissionReference}</dd></div>
            <div><dt>受理时间</dt><dd>{formatAcceptedAt(accepted.acceptedAt)}</dd></div>
          </dl>
          <Alert
            showIcon
            type="info"
            message="受理成功不等于 AI 完成或 HR 通过"
            description="系统已经保存投递资料和原简历，后续处理由招聘团队负责；本凭证不提供公开进度查询。"
          />
          <Button type="primary" size="large" onClick={startAnotherApplication}>
            投递另一个岗位
          </Button>
        </section>
      </main>,
    );
  }

  const hasOpenJobs = loadState.jobs.length > 0;

  return renderShell(
    <main className="recruitment-apply-main">
      <section className="recruitment-apply-intro" aria-labelledby="application-title">
        <div className="recruitment-apply-eyebrow"><span /> CANDIDATE APPLICATION</div>
        <h1 id="application-title">选择岗位，提交你的申请资料</h1>
        <p>查看当前开放岗位，只填写招聘联络所需信息。提交成功表示资料和原简历已经收到，后台处理不会阻塞本页。</p>
        <div className="recruitment-apply-job-count" aria-label={`${loadState.jobs.length} 个开放岗位`}>
          <strong>{loadState.jobs.length}</strong>
          <span>个岗位<br />正在接受申请</span>
        </div>
      </section>

      <div className="recruitment-apply-layout">
        <aside className="recruitment-apply-guide" aria-label="投递流程">
          <div className="recruitment-apply-guide-title">
            <FileDoneOutlined />
            <div>
              <strong>申请资料夹</strong>
              <span>三步完成本次投递</span>
            </div>
          </div>
          <ol>
            <li>
              <span>01</span>
              <div><strong>选择开放岗位</strong><p>查看候选人可见的职责、要求与补充说明。</p></div>
            </li>
            <li>
              <span>02</span>
              <div><strong>填写资料并上传</strong><p>提供姓名、手机、邮箱和一份有效简历。</p></div>
            </li>
            <li>
              <span>03</span>
              <div><strong>确认后发送申请</strong><p>页面先返回投递凭证，后续处理不会自动作招聘决定。</p></div>
            </li>
          </ol>
          <div className="recruitment-apply-boundary-note">
            <LockOutlined />
            <span><strong>本地作品集演示</strong>请只使用虚构或完整脱敏的姓名、联系方式和简历，不要填写真实个人资料。</span>
          </div>
        </aside>

        <section className="recruitment-apply-form-card" aria-label="候选人投递表单">
          <div className="recruitment-apply-folder-spine" aria-hidden="true">
            <span className={selectedJob ? 'is-ready' : ''}>岗位</span>
            <span className={resumeFiles.length > 0 ? 'is-ready' : ''}>简历</span>
            <span className={privacyConsent ? 'is-ready' : ''}>同意</span>
          </div>

          {!hasOpenJobs && (
            <div className="recruitment-apply-empty-jobs">
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有开放岗位" />
              <p>有新岗位开放后，就可以在这里提交申请。</p>
            </div>
          )}

          {hasOpenJobs && (
            <Form<ApplicationFormValues>
              form={form}
              layout="vertical"
              requiredMark
              autoComplete="on"
              onFinish={handleSubmit}
              onValuesChange={() => setSubmissionState({ status: 'idle' })}
              scrollToFirstError={{ behavior: 'smooth', block: 'center' }}
            >
              <div className="recruitment-apply-section-heading">
                <span><SolutionOutlined /></span>
                <div><strong>目标岗位</strong><p>请选择一项当前开放的职位</p></div>
              </div>
              <Form.Item label="应聘岗位" name="jobId" rules={[{ required: true, message: '请选择应聘岗位' }]}>
                <Select
                  showSearch
                  optionFilterProp="label"
                  placeholder="选择一个开放岗位"
                  options={loadState.jobs.map(job => ({
                    value: job.id,
                    label: [job.title, job.department, job.location].filter(Boolean).join(' · '),
                  }))}
                />
              </Form.Item>

              {selectedJob && <SelectedJob job={selectedJob} />}

              <div className="recruitment-apply-divider" />
              <div className="recruitment-apply-section-heading">
                <span><UserOutlined /></span>
                <div><strong>联络信息</strong><p>招聘团队只会通过你主动填写的信息联系你</p></div>
              </div>
              <div className="recruitment-apply-grid">
                <Form.Item
                  label="姓名"
                  name="name"
                  rules={[
                    { required: true, whitespace: true, message: '请填写姓名' },
                    { max: 100, message: '姓名不能超过 100 个字符' },
                  ]}
                >
                  <Input autoComplete="name" placeholder="请输入姓名" />
                </Form.Item>
                <Form.Item
                  label="手机号码"
                  name="phone"
                  rules={[
                    { required: true, whitespace: true, message: '请填写手机号码' },
                    { validator: (_, value) => !value || isValidPublicPhone(value) ? Promise.resolve() : Promise.reject(new Error('请输入 7—15 位有效手机号码')) },
                  ]}
                >
                  <Input autoComplete="tel" inputMode="tel" placeholder="可包含合法国家或地区前缀" />
                </Form.Item>
                <Form.Item
                  className="recruitment-apply-grid-full"
                  label="电子邮箱"
                  name="email"
                  rules={[
                    { required: true, whitespace: true, message: '请填写电子邮箱' },
                    { type: 'email', message: '请输入有效邮箱地址' },
                    { max: 254, message: '邮箱不能超过 254 个字符' },
                  ]}
                >
                  <Input autoComplete="email" inputMode="email" placeholder="name@example.com" />
                </Form.Item>
              </div>

              <div className="recruitment-apply-divider" />
              <div className="recruitment-apply-section-heading">
                <span><FileTextOutlined /></span>
                <div><strong>简历文件</strong><p>一份文件，最大 10 MB</p></div>
              </div>
              <div
                className={`recruitment-apply-upload-region${resumeError ? ' has-error' : ''}`}
                ref={resumeRegionRef}
                tabIndex={-1}
                aria-describedby="resume-upload-help"
              >
                <Upload.Dragger {...uploadProps} className="recruitment-apply-uploader">
                  <p className="ant-upload-drag-icon"><CloudUploadOutlined /></p>
                  <p className="ant-upload-text">点击或拖拽简历到这里</p>
                  <p className="ant-upload-hint" id="resume-upload-help">支持 PDF、DOCX、TXT，单个文件不超过 10 MB</p>
                </Upload.Dragger>
                {resumeError && <p className="recruitment-apply-field-error" role="alert">{resumeError}</p>}
              </div>

              <div className="recruitment-apply-consent">
                <Form.Item
                  name="privacyConsent"
                  valuePropName="checked"
                  rules={[{
                    validator: (_, checked) => checked
                      ? Promise.resolve()
                      : Promise.reject(new Error('请阅读并同意隐私说明')),
                  }]}
                >
                  <Checkbox>
                    我已阅读并同意本页隐私说明，确认仅提交虚构或完整脱敏资料，并同意系统为招聘联络、简历处理和初筛保存本次内容。
                  </Checkbox>
                </Form.Item>
                <p>隐私说明版本：{PUBLIC_APPLICATION_CONSENT_VERSION}。提交后不提供候选人账号、公开进度查询或自动撤回。</p>
              </div>

              {submissionState.status === 'error' && (
                <Alert
                  className="recruitment-apply-submit-error"
                  showIcon
                  type="error"
                  role="alert"
                  message="投递未送达"
                  description={submissionState.error.retryAfterSeconds
                    ? `${submissionState.error.message}，请在 ${submissionState.error.retryAfterSeconds} 秒后重试。已填写内容和简历仍保留在本页。`
                    : `${submissionState.error.message}。已填写内容和简历仍保留在本页。`}
                />
              )}

              <div className="recruitment-apply-submit-row">
                <div><LockOutlined /><span>成功只表示资料与原文件已收到</span></div>
                <Button
                  type="primary"
                  size="large"
                  htmlType="submit"
                  icon={<SendOutlined />}
                  loading={submitting}
                  disabled={submitting}
                >
                  {submitting ? '正在发送申请' : '发送申请'}
                </Button>
              </div>
            </Form>
          )}
        </section>
      </div>
    </main>,
  );
};

const SelectedJob: React.FC<{ job: RecruitmentApplicationJob }> = ({ job }) => {
  const sections = [
    { label: '岗位背景', value: job.jobBackground, emptyText: '该岗位暂未填写岗位背景。' },
    { label: '岗位职责', value: job.jobResponsibilities, emptyText: '该岗位暂未填写岗位职责。' },
    { label: '任职要求', value: job.candidateRequirements, emptyText: '该岗位暂未填写任职要求。' },
    { label: '加分项', value: job.preferredQualifications, emptyText: '该岗位暂未填写加分项。' },
    { label: '补充说明', value: job.publicNotes, emptyText: '该岗位暂未填写补充说明。' },
  ];

  return (
    <article className="recruitment-apply-selected-job" aria-label={`${job.title} 岗位详情`}>
      <div className="recruitment-apply-selected-job-top">
        <span><CheckCircleFilled /></span>
        <div>
          <strong>{job.title}</strong>
          <p>{job.department || '所属部门待补充'}</p>
        </div>
        <Tag>正在招聘</Tag>
      </div>
      <div className="recruitment-apply-job-meta">
        <span><EnvironmentOutlined /> {job.location || '工作地点待补充'}</span>
        <span><SolutionOutlined /> {job.employmentType ? employmentTypeLabels[job.employmentType] : '用工类型待补充'}</span>
      </div>
      <div className="recruitment-apply-jd-heading">
        <strong>岗位说明</strong>
        <span>以下内容按招聘信息原始顺序展示</span>
      </div>
      <ol className="recruitment-apply-selected-job-copy">
        {sections.map((section, index) => (
          <li key={section.label}>
            <span className="recruitment-apply-jd-index" aria-hidden="true">
              {String(index + 1).padStart(2, '0')}
            </span>
            <section aria-labelledby={`public-job-${job.id}-section-${index}`}>
              <h3 id={`public-job-${job.id}-section-${index}`}>{section.label}</h3>
              <p>{section.value || section.emptyText}</p>
            </section>
          </li>
        ))}
      </ol>
    </article>
  );
};

export default RecruitmentApplicationForm;
