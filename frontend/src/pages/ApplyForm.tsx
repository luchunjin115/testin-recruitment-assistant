import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Divider, Form, Input, message, Result, Row, Select, Upload } from 'antd';
import { InboxOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { getActiveJobs, submitApplication } from '../api';
import type { Job } from '../types';
import { DEGREES } from '../utils/constants';
import './ApplyForm.css';

const { TextArea } = Input;
const { Dragger } = Upload;

const ApplyForm: React.FC = () => {
  const [form] = Form.useForm();
  const [phase, setPhase] = useState<'form' | 'submitting' | 'success'>('form');
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);

  const loadJobs = async () => {
    setJobsLoading(true);
    try {
      const result = await getActiveJobs();
      setJobs(result);
      const currentJobId = form.getFieldValue('job_id');
      if (currentJobId && !result.some(job => job.id === currentJobId)) {
        form.setFieldsValue({ job_id: undefined });
      }
    } catch {
      message.error('加载开放岗位失败，请稍后重试');
    } finally {
      setJobsLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const onFinish = async (values: Record<string, unknown>) => {
    setPhase('submitting');
    try {
      const fd = new FormData();
      fd.append('name', (values.name as string).trim());
      fd.append('phone', (values.phone as string).trim());
      fd.append('email', ((values.email as string) || '').trim());
      fd.append('school', ((values.school as string) || '').trim());
      fd.append('degree', ((values.degree as string) || '').trim());
      fd.append('major', ((values.major as string) || '').trim());
      const selectedJob = jobs.find(job => job.id === Number(values.job_id));
      fd.append('job_id', String(values.job_id || ''));
      fd.append('target_role', selectedJob?.title || '');
      fd.append('skills', JSON.stringify(values.skills || []));
      fd.append('self_intro', ((values.self_intro as string) || '').trim());

      const resumeFile = fileList[0]?.originFileObj;
      if (resumeFile) {
        fd.append('file', resumeFile);
      }

      await submitApplication(fd);
      setPhase('success');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '提交失败，请稍后重试');
      setPhase('form');
    }
  };

  const handleReset = () => {
    form.resetFields();
    setFileList([]);
    setPhase('form');
  };

  if (phase === 'success') {
    return (
      <div className="apply-page">
        <div className="apply-header">
          <h1>Testin云测招聘助手</h1>
          <p>智能招聘管理平台</p>
        </div>
        <div className="apply-success">
          <Result
            status="success"
            title="投递成功！"
            subTitle="我们已收到您的信息，会尽快审核。感谢您的投递！"
            extra={[
              <Button type="primary" key="again" onClick={handleReset}>
                继续投递
              </Button>,
            ]}
          />
        </div>
        <div className="apply-footer">Testin云测招聘助手 | 智能招聘管理平台</div>
      </div>
    );
  }

  return (
    <div className="apply-page">
      <div className="apply-header">
        <h1>加入我们</h1>
        <p>请填写您的个人信息，我们将尽快与您联系</p>
      </div>

      <div className="apply-container">
        <Card>
          <Form form={form} layout="vertical" onFinish={onFinish}>
            <Divider orientation="left">基本信息</Divider>
            <Row gutter={24}>
              <Col xs={24} sm={8}>
                <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
                  <Input placeholder="请输入您的姓名" maxLength={50} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="phone"
                  label="手机号"
                  rules={[
                    { required: true, message: '请输入手机号' },
                    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' },
                  ]}
                >
                  <Input placeholder="请输入手机号" maxLength={11} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="email" label="邮箱" rules={[{ type: 'email', message: '请输入有效邮箱' }]}>
                  <Input placeholder="example@email.com" />
                </Form.Item>
              </Col>
            </Row>

            <Divider orientation="left">教育背景</Divider>
            <Row gutter={24}>
              <Col xs={24} sm={8}>
                <Form.Item name="school" label="学校">
                  <Input placeholder="请输入学校名称" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="degree" label="学历">
                  <Select placeholder="请选择学历" allowClear options={DEGREES.map(d => ({ label: d, value: d }))} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="major" label="专业">
                  <Input placeholder="请输入专业" />
                </Form.Item>
              </Col>
            </Row>

            <Divider orientation="left">求职信息</Divider>
            <Row gutter={24}>
              <Col xs={24} sm={12}>
                <Form.Item name="job_id" label="应聘岗位" rules={[{ required: true, message: '请选择应聘岗位' }]}>
                  <Select
                    placeholder={jobs.length ? '请选择应聘岗位' : '当前暂无开放岗位，请稍后再试'}
                    loading={jobsLoading}
                    disabled={jobsLoading || jobs.length === 0}
                    showSearch
                    optionFilterProp="label"
                    options={jobs.map(job => ({
                      label: job.department ? `${job.title}（${job.department}）` : job.title,
                      value: job.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="skills" label="技能关键词">
                  <Select
                    mode="tags"
                    placeholder="输入技能后按回车添加，如 Python、React"
                    tokenSeparators={[',']}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="self_intro" label="自我介绍">
              <TextArea rows={4} placeholder="请简要介绍自己的优势和经历..." maxLength={2000} showCount />
            </Form.Item>

            <Divider orientation="left">简历上传（可选）</Divider>
            <Form.Item>
              <Dragger
                fileList={fileList}
                beforeUpload={(file) => {
                  const ext = file.name.split('.').pop()?.toLowerCase();
                  if (!ext || !['pdf', 'docx', 'txt'].includes(ext)) {
                    message.error('仅支持 PDF、DOCX、TXT 格式');
                    return Upload.LIST_IGNORE;
                  }
                  if (file.size > 10 * 1024 * 1024) {
                    message.error('文件大小不能超过 10MB');
                    return Upload.LIST_IGNORE;
                  }
                  setFileList([{
                    uid: file.uid,
                    name: file.name,
                    size: file.size,
                    type: file.type,
                    status: 'done',
                    originFileObj: file,
                  }]);
                  return false;
                }}
                onRemove={() => {
                  setFileList([]);
                }}
                maxCount={1}
                accept=".pdf,.docx,.txt"
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽文件到此区域上传简历</p>
                <p className="ant-upload-hint">支持 PDF、DOCX、TXT 格式，最大 10MB</p>
              </Dragger>
            </Form.Item>

            <Form.Item style={{ textAlign: 'center', marginTop: 24 }}>
              {jobs.length === 0 && !jobsLoading && (
                <Alert
                  type="warning"
                  showIcon
                  message="当前暂无开放岗位，请稍后再试"
                  action={<Button size="small" icon={<ReloadOutlined />} onClick={loadJobs}>重新加载</Button>}
                  style={{ marginBottom: 16, textAlign: 'left' }}
                />
              )}
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                loading={phase === 'submitting'}
                disabled={jobsLoading || jobs.length === 0}
                icon={<SendOutlined />}
                style={{ minWidth: 200 }}
              >
                提交投递
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>

      <div className="apply-footer">Testin云测招聘助手 | 智能招聘管理平台</div>
    </div>
  );
};

export default ApplyForm;
