import React, { useEffect, useState } from 'react';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, Typography, message } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Job } from '../types';
import { createJob, deleteJob, getJobs, updateJob, updateJobStatus } from '../api';

const { TextArea } = Input;

type JobFormValues = {
  title: string;
  department?: string;
  description?: string;
  requirements?: string;
  required_skills?: string | string[];
  bonus_skills?: string | string[];
  education_requirement?: string;
  experience_requirement?: string;
  job_keywords?: string | string[];
  risk_keywords?: string | string[];
  status: 'active' | 'inactive';
};

const splitTags = (value?: string) =>
  (value || '').split(/[,，;；、\n]+/).map(item => item.trim()).filter(Boolean);

const joinTags = (value?: string | string[]) =>
  Array.isArray(value) ? value.map(item => item.trim()).filter(Boolean).join('，') : (value || '').trim();

const JobManagement: React.FC = () => {
  const [form] = Form.useForm<JobFormValues>();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<Job | null>(null);

  const loadJobs = async () => {
    setLoading(true);
    try {
      setJobs(await getJobs());
    } catch {
      message.error('加载岗位列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const openCreate = () => {
    setEditingJob(null);
    form.resetFields();
    form.setFieldsValue({ status: 'active' });
    setModalOpen(true);
  };

  const openEdit = (job: Job) => {
    setEditingJob(job);
    form.setFieldsValue({
      title: job.title,
      department: job.department,
      description: job.description,
      requirements: job.requirements,
      required_skills: splitTags(job.required_skills),
      bonus_skills: splitTags(job.bonus_skills),
      education_requirement: job.education_requirement,
      experience_requirement: job.experience_requirement,
      job_keywords: splitTags(job.job_keywords),
      risk_keywords: splitTags(job.risk_keywords),
      status: job.status,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const rawValues = await form.validateFields();
    const values = {
      ...rawValues,
      required_skills: joinTags(rawValues.required_skills),
      bonus_skills: joinTags(rawValues.bonus_skills),
      job_keywords: joinTags(rawValues.job_keywords),
      risk_keywords: joinTags(rawValues.risk_keywords),
    };
    setSaving(true);
    try {
      if (editingJob) {
        await updateJob(editingJob.id, values);
        message.success('岗位已更新');
      } else {
        await createJob(values);
        message.success('岗位已新增');
      }
      setModalOpen(false);
      await loadJobs();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '保存岗位失败');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (job: Job, status: 'active' | 'inactive') => {
    try {
      await updateJobStatus(job.id, status);
      message.success(status === 'active' ? '岗位已启用' : '岗位已停用');
      await loadJobs();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '更新岗位状态失败');
    }
  };

  const handleDelete = async (job: Job) => {
    try {
      const result = await deleteJob(job.id);
      message.success(result.message);
      await loadJobs();
    } catch {
      message.error('删除岗位失败');
    }
  };

  const columns: ColumnsType<Job> = [
    {
      title: '岗位名称',
      dataIndex: 'title',
      width: 180,
      render: (title: string, job) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{title}</Typography.Text>
          {job.department && <Typography.Text type="secondary">{job.department}</Typography.Text>}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      render: (text: string) => text || <Typography.Text type="secondary">未填写</Typography.Text>,
    },
    {
      title: '要求',
      dataIndex: 'requirements',
      ellipsis: true,
      render: (text: string) => text || <Typography.Text type="secondary">未填写</Typography.Text>,
    },
    {
      title: '筛选标准',
      width: 220,
      render: (_, job) => (
        <Space size={[4, 4]} wrap>
          {job.required_skills
            ? job.required_skills.split(/[,，;；、\n]+/).filter(Boolean).slice(0, 3).map(skill => (
              <Tag key={skill} color="blue">{skill.trim()}</Tag>
            ))
            : <Typography.Text type="secondary">未配置必备技能</Typography.Text>}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (status: Job['status']) => (
        <Tag color={status === 'active' ? 'green' : 'default'}>
          {status === 'active' ? '启用' : '停用'}
        </Tag>
      ),
    },
    {
      title: '候选人',
      dataIndex: 'candidate_count',
      width: 90,
      render: (count: number) => `${count || 0} 人`,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 120,
      render: (time: string) => time ? new Date(time).toLocaleDateString() : '',
    },
    {
      title: '操作',
      width: 260,
      fixed: 'right',
      render: (_, job) => (
        <Space wrap>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(job)}>
            编辑
          </Button>
          <Button
            size="small"
            type={job.status === 'active' ? 'default' : 'primary'}
            onClick={() => handleStatusChange(job, job.status === 'active' ? 'inactive' : 'active')}
          >
            {job.status === 'active' ? '停用' : '启用'}
          </Button>
          <Popconfirm
            title={job.candidate_count > 0 ? '该岗位已有候选人' : '确认删除岗位'}
            description={job.candidate_count > 0 ? '系统会自动停用该岗位，历史候选人数据不会丢失。' : `确定删除「${job.title}」吗？`}
            onConfirm={() => handleDelete(job)}
            okText={job.candidate_count > 0 ? '停用岗位' : '确认删除'}
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Table
        title={() => (
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Typography.Title level={4} style={{ margin: 0 }}>岗位管理</Typography.Title>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadJobs}>刷新</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增岗位</Button>
            </Space>
          </Space>
        )}
        rowKey="id"
        dataSource={jobs}
        columns={columns}
        loading={loading}
        pagination={false}
        scroll={{ x: 1000 }}
      />

      <Modal
        title={editingJob ? '编辑岗位' : '新增岗位'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width={760}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={{ status: 'active' }}>
          <Form.Item name="title" label="岗位名称" rules={[{ required: true, message: '请输入岗位名称' }]}>
            <Input placeholder="例如：测试工程师" maxLength={100} />
          </Form.Item>
          <Form.Item name="department" label="所属部门">
            <Input placeholder="例如：质量保障部" maxLength={100} />
          </Form.Item>
          <Form.Item name="description" label="岗位描述">
            <TextArea rows={3} placeholder="填写岗位工作内容" maxLength={2000} showCount />
          </Form.Item>
          <Form.Item name="requirements" label="岗位要求">
            <TextArea rows={3} placeholder="填写岗位能力要求" maxLength={2000} showCount />
          </Form.Item>
          <Form.Item
            name="required_skills"
            label="必备技能"
            tooltip="多个技能请用逗号、顿号或换行分隔"
          >
            <Select mode="tags" tokenSeparators={[',', '，', '、']} placeholder="例如：Python、接口测试、Postman" />
          </Form.Item>
          <Form.Item
            name="bonus_skills"
            label="加分技能"
            tooltip="多个技能请用逗号、顿号或换行分隔"
          >
            <Select mode="tags" tokenSeparators={[',', '，', '、']} placeholder="例如：Selenium、JMeter、Jenkins" />
          </Form.Item>
          <Form.Item name="education_requirement" label="学历要求">
            <Input placeholder="例如：本科、硕士" maxLength={100} />
          </Form.Item>
          <Form.Item name="experience_requirement" label="经验要求">
            <Input placeholder="例如：1年以上、3年以上、应届可投" maxLength={100} />
          </Form.Item>
          <Form.Item
            name="job_keywords"
            label="岗位关键词"
            tooltip="用于补充岗位匹配判断，可填写业务、方向、职责关键词"
          >
            <Select mode="tags" tokenSeparators={[',', '，', '、']} placeholder="例如：质量保障、自动化测试、沟通" />
          </Form.Item>
          <Form.Item
            name="risk_keywords"
            label="风险提示关键词"
            tooltip="命中后会在 AI 初筛风险提示中提醒 HR 复核"
          >
            <Select mode="tags" tokenSeparators={[',', '，', '、']} placeholder="例如：无测试经验、缺少SQL经验" />
          </Form.Item>
          <Form.Item name="status" label="岗位状态" rules={[{ required: true, message: '请选择岗位状态' }]}>
            <Select
              options={[
                { label: '启用', value: 'active' },
                { label: '停用', value: 'inactive' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default JobManagement;
