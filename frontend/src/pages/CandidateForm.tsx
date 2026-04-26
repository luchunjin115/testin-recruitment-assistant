import React from 'react';
import { Alert, Button, Card, Col, Divider, Form, Input, InputNumber, Row, Select, Space, Tag, Typography, Upload, message } from 'antd';
import { InboxOutlined, ReloadOutlined, RobotOutlined, UserAddOutlined } from '@ant-design/icons';
import type { RcFile, UploadFile } from 'antd/es/upload/interface';
import { useNavigate } from 'react-router-dom';
import { createHRCandidate, getActiveJobs, parseResumePreview } from '../api';
import type { Job } from '../types';
import { DEGREES } from '../utils/constants';

const { Dragger } = Upload;
const { TextArea } = Input;

const HR_SOURCE_CHANNELS = ['HR手动录入', '企业微信群', '内推', 'Boss直聘', '拉勾', '猎聘', '其他'];

type CandidateFormValues = {
  name?: string;
  phone?: string;
  email?: string;
  school?: string;
  degree?: string;
  major?: string;
  job_id?: number | '__other__';
  target_role?: string;
  experience_years?: number;
  skills?: string[];
  experience_desc?: string;
  self_intro?: string;
  source_channel?: string;
  hr_notes?: string;
};

type ResumeInsight = {
  filledFields: string[];
  rawPreview: string;
  extractedSkills: string[];
};

const FIELD_LABELS: Record<string, string> = {
  name: '姓名',
  phone: '手机号',
  email: '邮箱',
  school: '学校',
  degree: '学历',
  major: '专业',
  target_role: '应聘岗位',
  experience_years: '工作年限',
  skills: '技能关键词',
  experience_desc: '工作经历',
  self_intro: '自我介绍',
};

const isEmptyValue = (value: unknown) => {
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'number') return false;
  if (value === null || value === undefined) return true;
  return String(value).trim() === '';
};

const formatFileSize = (size?: number) => {
  if (!size) return '';
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${size} B`;
};

const CandidateForm: React.FC = () => {
  const [form] = Form.useForm<CandidateFormValues>();
  const navigate = useNavigate();
  const [loading, setLoading] = React.useState(false);
  const [parsingResume, setParsingResume] = React.useState(false);
  const [resumeFile, setResumeFile] = React.useState<File | null>(null);
  const [fileList, setFileList] = React.useState<UploadFile[]>([]);
  const [resumeInsight, setResumeInsight] = React.useState<ResumeInsight | null>(null);
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = React.useState(false);

  const loadJobs = React.useCallback(async () => {
    setJobsLoading(true);
    try {
      setJobs(await getActiveJobs());
    } catch {
      message.error('加载岗位库失败');
    } finally {
      setJobsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const applyResumeSuggestions = React.useCallback((extracted: Record<string, unknown>) => {
    const currentValues = form.getFieldsValue();
    const nextValues: Partial<CandidateFormValues> = {};
    const filledFields: string[] = [];

    const syncField = (field: keyof CandidateFormValues) => {
      const extractedValue = extracted[field];
      if (isEmptyValue(currentValues[field]) && !isEmptyValue(extractedValue)) {
        nextValues[field] = extractedValue as never;
        filledFields.push(field);
      }
    };

    syncField('name');
    syncField('phone');
    syncField('email');
    syncField('school');
    syncField('degree');
    syncField('major');
    syncField('target_role');
    syncField('experience_desc');
    syncField('self_intro');

    if (isEmptyValue(currentValues.experience_years) && !isEmptyValue(extracted.experience_years)) {
      nextValues.experience_years = Number(extracted.experience_years);
      filledFields.push('experience_years');
    }

    if (isEmptyValue(currentValues.skills) && Array.isArray(extracted.skills) && extracted.skills.length > 0) {
      nextValues.skills = extracted.skills.map(item => String(item).trim()).filter(Boolean);
      filledFields.push('skills');
    }

    if (Object.keys(nextValues).length > 0) {
      form.setFieldsValue(nextValues);
    }

    return filledFields;
  }, [form]);

  const handleResumeSelect = async (file: RcFile) => {
    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.docx', '.txt'].includes(extension)) {
      message.error('仅支持 PDF、DOCX、TXT 格式');
      return false;
    }
    if (file.size > 10 * 1024 * 1024) {
      message.error('文件大小不能超过 10MB');
      return false;
    }

    const uploadFile: UploadFile = {
      uid: file.uid,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'done',
      originFileObj: file,
    };

    setResumeFile(file);
    setFileList([uploadFile]);
    setResumeInsight(null);
    setParsingResume(true);

    try {
      const result = await parseResumePreview(file);
      const filledFields = applyResumeSuggestions(result.extracted || {});
      const extractedSkills = Array.isArray(result.extracted?.skills)
        ? result.extracted.skills.map((item: unknown) => String(item).trim()).filter(Boolean)
        : [];

      setResumeInsight({
        filledFields,
        rawPreview: result.raw_text_preview || '',
        extractedSkills,
      });

      if (filledFields.length > 0) {
        message.success(`已根据简历补全空字段：${filledFields.map(field => FIELD_LABELS[field] || field).join('、')}`);
      } else {
        message.info('简历解析完成，当前已保留你手动填写的内容');
      }
    } catch {
      message.warning('简历已选中，但AI解析失败；你仍可继续手动填写并提交');
    } finally {
      setParsingResume(false);
    }

    return false;
  };

  const handleReset = () => {
    form.resetFields();
    setResumeFile(null);
    setFileList([]);
    setResumeInsight(null);
  };

  const onFinish = async (values: CandidateFormValues) => {
    const formData = new FormData();
    formData.append('name', values.name?.trim() || '');
    formData.append('phone', values.phone?.trim() || '');
    formData.append('email', values.email?.trim() || '');
    formData.append('school', values.school?.trim() || '');
    formData.append('degree', values.degree?.trim() || '');
    formData.append('major', values.major?.trim() || '');
    if (typeof values.job_id === 'number') {
      const selectedJob = jobs.find(job => job.id === values.job_id);
      formData.append('job_id', String(values.job_id));
      formData.append('target_role', selectedJob?.title || '');
    } else {
      formData.append('target_role', values.target_role?.trim() || '');
    }
    formData.append('experience_years', values.experience_years !== undefined && values.experience_years !== null ? String(values.experience_years) : '');
    formData.append('experience_desc', values.experience_desc?.trim() || '');
    formData.append('skills', JSON.stringify(values.skills || []));
    formData.append('self_intro', values.self_intro?.trim() || '');
    formData.append('source_channel', values.source_channel || 'HR手动录入');
    formData.append('hr_notes', values.hr_notes?.trim() || '');
    if (resumeFile) {
      formData.append('file', resumeFile);
    }

    setLoading(true);
    try {
      const candidate = await createHRCandidate(formData);
      message.success(`候选人 ${candidate.name} 创建成功`);
      navigate(`/candidates/${candidate.id}`);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '新增候选人失败，请检查信息后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title={<span><UserAddOutlined /> 新增候选人</span>}
      extra={<span style={{ color: '#999' }}>HR后台统一录入入口</span>}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
        message="支持 HR 手动录入，也支持上传简历后由 AI 补全空字段"
        description="上传简历不会覆盖你已经填写的内容；系统默认创建为“新投递”，并写入 Dashboard 最近操作日志。"
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ source_channel: 'HR手动录入' }}
      >
        <Divider orientation="left">简历上传</Divider>
        <Card size="small" style={{ marginBottom: 24, background: '#fafafa' }}>
          <Dragger
            accept=".pdf,.docx,.txt"
            fileList={fileList}
            beforeUpload={handleResumeSelect}
            onRemove={() => {
              setResumeFile(null);
              setFileList([]);
              setResumeInsight(null);
              return true;
            }}
            maxCount={1}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ color: '#1677ff' }} />
            </p>
            <p className="ant-upload-text">点击或拖拽上传简历</p>
            <p className="ant-upload-hint">支持 PDF / DOCX / TXT，上传为可选项</p>
          </Dragger>

          {resumeFile && (
            <div style={{ marginTop: 16 }}>
              <Space wrap>
                <Tag color="blue">{resumeFile.name}</Tag>
                <Tag>{formatFileSize(resumeFile.size)}</Tag>
                {parsingResume && <Tag color="processing"><RobotOutlined /> AI解析中</Tag>}
              </Space>
            </div>
          )}

          {resumeInsight && (
            <Card
              type="inner"
              size="small"
              title="AI补全结果"
              style={{ marginTop: 16 }}
            >
              <Space wrap style={{ marginBottom: 12 }}>
                {resumeInsight.filledFields.length > 0
                  ? resumeInsight.filledFields.map(field => (
                    <Tag key={field} color="green">{FIELD_LABELS[field] || field}</Tag>
                  ))
                  : <Tag>未覆盖任何手动字段</Tag>}
              </Space>
              {resumeInsight.extractedSkills.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <Typography.Text type="secondary">识别到的技能：</Typography.Text>
                  <Space wrap style={{ marginLeft: 8 }}>
                    {resumeInsight.extractedSkills.slice(0, 8).map(skill => (
                      <Tag key={skill} color="blue">{skill}</Tag>
                    ))}
                  </Space>
                </div>
              )}
              {resumeInsight.rawPreview && (
                <Typography.Paragraph
                  style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}
                  ellipsis={{ rows: 4, expandable: true, symbol: '展开预览' }}
                >
                  {resumeInsight.rawPreview}
                </Typography.Paragraph>
              )}
            </Card>
          )}
        </Card>

        <Divider orientation="left">基本信息</Divider>
        <Row gutter={24}>
          <Col span={8}>
            <Form.Item
              name="name"
              label="姓名"
              rules={[
                {
                  validator: async (_, value) => {
                    if ((value && String(value).trim()) || resumeFile) return;
                    throw new Error('请输入姓名，或上传简历补全');
                  },
                },
              ]}
            >
              <Input placeholder="请输入姓名" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="phone"
              label="手机号"
              rules={[
                {
                  validator: async (_, value) => {
                    const text = String(value || '').trim();
                    if (!text) {
                      if (resumeFile) return;
                      throw new Error('请输入手机号，或上传简历补全');
                    }
                    if (!/^1[3-9]\d{9}$/.test(text)) {
                      throw new Error('请输入有效手机号');
                    }
                  },
                },
              ]}
            >
              <Input placeholder="13800138000" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="email" label="邮箱" rules={[{ type: 'email', message: '请输入有效邮箱' }]}>
              <Input placeholder="example@email.com" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item name="school" label="学校">
              <Input placeholder="请输入学校名称" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="degree" label="学历">
              <Select placeholder="请选择学历" options={DEGREES.map(degree => ({ label: degree, value: degree }))} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="major" label="专业">
              <Input placeholder="请输入专业" />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">求职信息</Divider>
        <Row gutter={24}>
          <Col span={8}>
            <Form.Item name="job_id" label="应聘岗位">
              <Select
                placeholder="优先从岗位库选择"
                loading={jobsLoading}
                showSearch
                allowClear
                optionFilterProp="label"
                options={[
                  ...jobs.map(job => ({
                    label: job.department ? `${job.title}（${job.department}）` : job.title,
                    value: job.id,
                  })),
                  { label: '其他/手动输入', value: '__other__' },
                ]}
                dropdownRender={menu => (
                  <>
                    {menu}
                    <div style={{ padding: 8 }}>
                      <Button size="small" block icon={<ReloadOutlined />} onClick={loadJobs}>
                        重新加载岗位库
                      </Button>
                    </div>
                  </>
                )}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="experience_years" label="工作年限">
              <InputNumber min={0} max={50} step={0.5} style={{ width: '100%' }} placeholder="0" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="source_channel" label="来源渠道">
              <Select options={HR_SOURCE_CHANNELS.map(channel => ({ label: channel, value: channel }))} />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item noStyle shouldUpdate={(prev, current) => prev.job_id !== current.job_id}>
          {({ getFieldValue }) => getFieldValue('job_id') === '__other__' ? (
            <Row gutter={24}>
              <Col span={8}>
                <Form.Item
                  name="target_role"
                  label="手动输入岗位"
                  rules={[{ required: true, message: '请输入应聘岗位' }]}
                >
                  <Input placeholder="仅特殊情况手动输入" />
                </Form.Item>
              </Col>
            </Row>
          ) : null}
        </Form.Item>

        <Row gutter={24}>
          <Col span={24}>
            <Form.Item name="skills" label="技能关键词">
              <Select mode="tags" placeholder="输入技能后按回车添加，如 Python、React、测试" tokenSeparators={[',']} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={24}>
          <Col span={12}>
            <Form.Item name="experience_desc" label="工作/实习经历">
              <TextArea rows={4} placeholder="请描述工作或实习经历..." />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="self_intro" label="自我介绍">
              <TextArea rows={4} placeholder="请输入自我介绍..." />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="hr_notes" label="HR备注">
          <TextArea rows={2} placeholder="HR内部备注（候选人不可见）" />
        </Form.Item>

        <Form.Item style={{ marginBottom: 0 }}>
          <Space size="middle">
            <Button type="primary" htmlType="submit" loading={loading} size="large" icon={<UserAddOutlined />}>
              新增候选人
            </Button>
            <Button onClick={handleReset} size="large" icon={<ReloadOutlined />}>
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default CandidateForm;
