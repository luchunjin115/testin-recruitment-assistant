import React, { useState } from 'react';
import { Card, Upload, Button, message, Descriptions, Tag, Spin, Form, Input, InputNumber, Select, Row, Col, Result } from 'antd';
import { InboxOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { parseResumePreview, createCandidate } from '../api';
import { DEGREES } from '../utils/constants';

const { Dragger } = Upload;
const { TextArea } = Input;

type Phase = 'upload' | 'parsing' | 'preview' | 'success';

const ResumeUpload: React.FC = () => {
  const [phase, setPhase] = useState<Phase>('upload');
  const [extracted, setExtracted] = useState<Record<string, unknown> | null>(null);
  const [rawPreview, setRawPreview] = useState('');
  const [candidateId, setCandidateId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const handleUpload = async (file: File) => {
    const validTypes = ['.pdf', '.docx', '.txt'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(ext)) {
      message.error('仅支持 PDF、DOCX、TXT 格式');
      return false;
    }
    if (file.size > 10 * 1024 * 1024) {
      message.error('文件大小不能超过 10MB');
      return false;
    }

    setPhase('parsing');
    try {
      const result = await parseResumePreview(file);
      setExtracted(result.extracted);
      setRawPreview(result.raw_text_preview);
      form.setFieldsValue({
        ...result.extracted,
        skills: result.extracted.skills || [],
      });
      setPhase('preview');
    } catch {
      message.error('简历解析失败，请重试');
      setPhase('upload');
    }
    return false;
  };

  const handleConfirm = async (values: Record<string, unknown>) => {
    try {
      const data = {
        ...values,
        skills: values.skills || [],
        experience_years: values.experience_years || 0,
        source_channel: '简历上传',
      };
      const candidate = await createCandidate(data as Parameters<typeof createCandidate>[0]);
      setCandidateId(candidate.id);
      setPhase('success');
      message.success('候选人录入成功！');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '录入失败');
    }
  };

  if (phase === 'success') {
    return (
      <Result
        status="success"
        title="候选人录入成功！"
        subTitle="AI已自动生成候选人摘要和推荐标签"
        extra={[
          <Button type="primary" key="detail" onClick={() => navigate(`/candidates/${candidateId}`)}>
            查看候选人详情
          </Button>,
          <Button key="again" onClick={() => { setPhase('upload'); setExtracted(null); form.resetFields(); }}>
            继续上传
          </Button>,
        ]}
      />
    );
  }

  return (
    <div>
      <Card
        title="📄 简历上传 - AI智能解析"
        extra={<span style={{ color: '#999' }}>方案二：简历上传入口</span>}
      >
        {phase === 'upload' && (
          <Dragger
            accept=".pdf,.docx,.txt"
            showUploadList={false}
            beforeUpload={handleUpload}
            style={{ padding: '40px 0' }}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined style={{ fontSize: 48, color: '#1677ff' }} /></p>
            <p style={{ fontSize: 16, fontWeight: 500 }}>点击或拖拽简历文件到此处</p>
            <p style={{ color: '#999' }}>支持 PDF、DOCX、TXT 格式，最大 10MB</p>
          </Dragger>
        )}

        {phase === 'parsing' && (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <p style={{ marginTop: 16, fontSize: 16, color: '#1677ff' }}>AI 正在解析简历，请稍候...</p>
          </div>
        )}

        {phase === 'preview' && (
          <div>
            <Descriptions title="📝 简历原文预览" bordered size="small" column={1} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="文本内容">
                <pre style={{ maxHeight: 200, overflow: 'auto', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}>
                  {rawPreview}
                </pre>
              </Descriptions.Item>
            </Descriptions>

            <Card title="✅ AI提取结果 - 请核对并确认" type="inner">
              <Form form={form} layout="vertical" onFinish={handleConfirm}>
                <Row gutter={24}>
                  <Col span={8}>
                    <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="phone" label="手机号" rules={[
                      { required: true },
                      { pattern: /^1[3-9]\d{9}$/, message: '请输入有效手机号' },
                    ]}>
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="email" label="邮箱">
                      <Input />
                    </Form.Item>
                  </Col>
                </Row>
                <Row gutter={24}>
                  <Col span={8}>
                    <Form.Item name="school" label="学校"><Input /></Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="degree" label="学历">
                      <Select options={DEGREES.map(d => ({ label: d, value: d }))} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="major" label="专业"><Input /></Form.Item>
                  </Col>
                </Row>
                <Row gutter={24}>
                  <Col span={8}>
                    <Form.Item name="target_role" label="应聘岗位"><Input /></Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="experience_years" label="工作年限">
                      <InputNumber min={0} max={50} step={0.5} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="skills" label="技能">
                      <Select mode="tags" />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item name="experience_desc" label="工作经历"><TextArea rows={3} /></Form.Item>
                <Form.Item name="self_intro" label="自我介绍"><TextArea rows={2} /></Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" icon={<CheckCircleOutlined />} size="large">
                    确认录入
                  </Button>
                  <Button style={{ marginLeft: 12 }} onClick={() => { setPhase('upload'); form.resetFields(); }}>
                    重新上传
                  </Button>
                </Form.Item>
              </Form>
            </Card>
          </div>
        )}
      </Card>
    </div>
  );
};

export default ResumeUpload;
