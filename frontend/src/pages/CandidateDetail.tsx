import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Descriptions, Tag, Button, Select, Input, Row, Col, Timeline, Spin, Alert, message, Space,
  Modal, DatePicker, Tooltip, Form, Progress,
} from 'antd';
import {
  ArrowLeftOutlined, ReloadOutlined, RobotOutlined, EditOutlined, SaveOutlined,
  ThunderboltOutlined, HistoryOutlined, EyeOutlined, DownloadOutlined, FileTextOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { CandidateDetail, StageChangeLog } from '../types';
import { getCandidate, updateCandidate, updateStage, generateSummary, generateTags, getFollowup, executeHRAction, getStageLogs, generateInterviewSummary } from '../api';
import { STAGES, HR_ACTIONS, STAGE_SOURCE_LABELS } from '../utils/constants';
import StageTag from '../components/StageTag';

const CandidateDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [followup, setFollowup] = useState('');
  const [editingNotes, setEditingNotes] = useState(false);
  const [notes, setNotes] = useState('');
  const [aiLoading, setAiLoading] = useState<string | null>(null);
  const [stageLogs, setStageLogs] = useState<StageChangeLog[]>([]);
  const [actionForm] = Form.useForm();
  const [interviewFeedbackForm] = Form.useForm();
  const [actionModal, setActionModal] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const terminalStages = ['入职', '淘汰'];
  const actionStageRules: Record<string, string[]> = {
    pass_screening: ['新投递', '待筛选'],
    set_interview_time: ['待约面'],
    advance_to_retest: ['已约面', '面试中'],
    send_offer: ['已约面', '面试中', '复试'],
    mark_onboarded: ['offer'],
    mark_eliminated: ['新投递', '待筛选', '待约面', '已约面', '面试中', '复试', 'offer'],
  };

  const load = async () => {
    try {
      const data = await getCandidate(Number(id));
      setCandidate(data);
      setNotes(data.hr_notes || '');
      setFollowup(data.followup_suggestion || '');
      interviewFeedbackForm.setFieldsValue({
        interview_feedback_text: data.interview_feedback_text || '',
        interviewer: data.interviewer || '',
        interview_round: data.interview_round || undefined,
        feedback_time: data.feedback_time ? dayjs(data.feedback_time) : dayjs(),
      });
      const logs = await getStageLogs(Number(id));
      setStageLogs(logs);
    } catch {
      message.error('加载候选人信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleStageChange = async (stage: string) => {
    try {
      await updateStage(Number(id), stage);
      message.success('状态已人工修正');
      load();
    } catch {
      message.error('状态更新失败');
    }
  };

  const isActionAllowed = (actionKey: string) => {
    if (!candidate) return false;
    if (terminalStages.includes(candidate.stage)) return false;
    return (actionStageRules[actionKey] || []).includes(candidate.stage);
  };

  const handleHRAction = async (actionKey: string) => {
    if (!candidate || !isActionAllowed(actionKey)) {
      message.warning('当前阶段不适合执行该操作');
      return;
    }

    if (actionKey !== 'pass_screening') {
      actionForm.resetFields();
      if (actionKey === 'send_offer') {
        actionForm.setFieldsValue({ offer_position: candidate.target_role });
      }
      setActionModal(actionKey);
      return;
    }

    setActionLoading(actionKey);
    try {
      await executeHRAction(Number(id), actionKey);
      const actionDef = HR_ACTIONS.find(a => a.key === actionKey);
      message.success(`操作成功：${actionDef?.label}`);
      load();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '操作失败');
    } finally {
      setActionLoading(null);
    }
  };

  const handleSubmitActionModal = async () => {
    if (!actionModal) return;
    const values = await actionForm.validateFields();
    setActionLoading(actionModal);
    try {
      const payload: Record<string, string> = {};
      Object.entries(values).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') return;
        if (dayjs.isDayjs(value)) {
          payload[key] = ['expected_onboard_date', 'onboard_date'].includes(key)
            ? value.format('YYYY-MM-DD')
            : value.toISOString();
        } else {
          payload[key] = String(value).trim();
        }
      });
      await executeHRAction(Number(id), actionModal, payload);
      const actionDef = HR_ACTIONS.find(a => a.key === actionModal);
      message.success(`操作成功：${actionDef?.label}`);
      setActionModal(null);
      actionForm.resetFields();
      load();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '操作失败');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegenSummary = async () => {
    setAiLoading('summary');
    try {
      const { summary } = await generateSummary(Number(id));
      setCandidate(prev => prev ? { ...prev, ai_summary: summary } : null);
      message.success('摘要已重新生成');
    } catch {
      message.error('生成摘要失败');
    } finally {
      setAiLoading(null);
    }
  };

  const handleRegenTags = async () => {
    setAiLoading('tags');
    try {
      const { tags } = await generateTags(Number(id));
      setCandidate(prev => prev ? { ...prev, ai_tags: tags } : null);
      message.success('标签已重新生成');
    } catch {
      message.error('生成标签失败');
    } finally {
      setAiLoading(null);
    }
  };

  const handleGenFollowup = async () => {
    setAiLoading('followup');
    try {
      const fp = await getFollowup(Number(id));
      setFollowup(fp.followup_suggestion || fp.suggestion);
      setCandidate(prev => prev ? {
        ...prev,
        followup_suggestion: fp.followup_suggestion || fp.suggestion,
        followup_priority: fp.followup_priority,
        followup_reason: fp.followup_reason,
        followup_days_since_update: fp.followup_days_since_update,
        is_overdue: fp.is_overdue,
        overdue_days: fp.overdue_days,
        overdue_reason: fp.overdue_reason,
        last_action_at: fp.last_action_at,
      } : null);
    } catch {
      message.error('生成跟进建议失败');
    } finally {
      setAiLoading(null);
    }
  };

  const handleGenerateInterviewSummary = async () => {
    const values = await interviewFeedbackForm.validateFields();
    setAiLoading('interview_summary');
    try {
      const payload = {
        interview_feedback_text: String(values.interview_feedback_text || '').trim(),
        interviewer: String(values.interviewer || '').trim(),
        interview_round: String(values.interview_round || '').trim(),
        feedback_time: values.feedback_time ? dayjs(values.feedback_time).toISOString() : dayjs().toISOString(),
      };
      const result = await generateInterviewSummary(Number(id), payload);
      setCandidate(prev => prev ? {
        ...prev,
        interview_feedback_text: result.interview_feedback_text,
        interviewer: result.interviewer,
        interview_round: result.interview_round,
        feedback_time: result.feedback_time,
        interview_ai_technical_summary: result.technical_summary,
        interview_ai_communication_summary: result.communication_summary,
        interview_ai_job_match: result.job_match,
        interview_ai_risk_points: result.risk_points,
        interview_ai_recommendation: result.recommendation,
        interview_ai_next_step: result.next_step,
        interview_ai_generated_at: result.generated_at,
      } : null);
      message.success('AI 面试总结已生成');
      load();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '生成 AI 面试总结失败');
    } finally {
      setAiLoading(null);
    }
  };

  const handleSaveNotes = async () => {
    try {
      await updateCandidate(Number(id), { hr_notes: notes } as Parameters<typeof updateCandidate>[1]);
      setEditingNotes(false);
      message.success('备注已保存');
    } catch {
      message.error('保存失败');
    }
  };

  const formatResumeSize = (size?: number | null) => {
    if (!size) return '未知';
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleViewResume = () => {
    if (!candidate?.resume_url) {
      message.warning('当前简历文件不可查看');
      return;
    }
    window.open(candidate.resume_url, '_blank', 'noopener,noreferrer');
  };

  const handleDownloadResume = () => {
    if (!candidate?.resume_url) {
      message.warning('当前简历文件不可下载');
      return;
    }
    const link = document.createElement('a');
    link.href = candidate.resume_url;
    link.download = candidate.resume_filename || 'resume';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>;
  if (!candidate) return <Alert type="error" message="候选人不存在" showIcon />;

  const stageSourceLabel = candidate.stage_source ? STAGE_SOURCE_LABELS[candidate.stage_source] || candidate.stage_source : '';
  const canPreviewResume = ['pdf', 'txt'].includes((candidate.resume_file_type || '').toLowerCase()) && !!candidate.resume_url;
  const hasInterviewInfo = !!(candidate.interview_time || candidate.interview_method || candidate.interviewer || candidate.interview_note);
  const hasRecheckInfo = !!(candidate.recheck_note || candidate.second_interview_time || candidate.second_interviewer);
  const hasOfferInfo = !!(candidate.offer_position || candidate.salary_range || candidate.expected_onboard_date || candidate.offer_note);
  const hasOnboardInfo = !!(candidate.onboard_date || candidate.onboard_note);
  const hasRejectInfo = !!(candidate.reject_reason || candidate.reject_note);
  const hasInterviewAiSummary = !!(
    candidate.interview_ai_technical_summary ||
    candidate.interview_ai_communication_summary ||
    candidate.interview_ai_job_match ||
    candidate.interview_ai_recommendation ||
    candidate.interview_ai_next_step
  );
  const actionModalTitle: Record<string, string> = {
    set_interview_time: '安排面试',
    advance_to_retest: '进入复试确认',
    send_offer: '发放 Offer',
    mark_onboarded: '确认入职',
    mark_eliminated: '淘汰候选人',
  };
  const screeningStatusMap: Record<CandidateDetail['screening_status'], { text: string; color: string }> = {
    pending: { text: '待初筛', color: 'gold' },
    passed: { text: '已通过初筛', color: 'green' },
    backup: { text: '备选', color: 'blue' },
    rejected: { text: '初筛淘汰', color: 'red' },
  };
  const screeningStatus = screeningStatusMap[candidate.screening_status || 'pending'];

  const renderActionModalFields = () => {
    switch (actionModal) {
      case 'set_interview_time':
        return (
          <>
            <Form.Item name="interview_time" label="面试时间" rules={[{ required: true, message: '请选择面试时间' }]}>
              <DatePicker showTime style={{ width: '100%' }} placeholder="选择面试日期和时间" format="YYYY-MM-DD HH:mm" />
            </Form.Item>
            <Form.Item name="interview_method" label="面试方式">
              <Select
                allowClear
                placeholder="请选择面试方式"
                options={['线上面试', '线下面试', '电话面试'].map(item => ({ label: item, value: item }))}
              />
            </Form.Item>
            <Form.Item name="interviewer" label="面试官">
              <Input placeholder="请输入面试官姓名" />
            </Form.Item>
            <Form.Item name="interview_note" label="备注">
              <Input.TextArea rows={3} placeholder="填写面试安排备注" />
            </Form.Item>
          </>
        );
      case 'advance_to_retest':
        return (
          <>
            <Alert type="info" showIcon message="确认将该候选人标记为进入复试吗？" style={{ marginBottom: 16 }} />
            <Form.Item name="recheck_note" label="复试原因 / 一面反馈">
              <Input.TextArea rows={3} placeholder="例如：一面表现良好，进入复试" />
            </Form.Item>
            <Form.Item name="second_interview_time" label="复试时间">
              <DatePicker showTime style={{ width: '100%' }} placeholder="可选" format="YYYY-MM-DD HH:mm" />
            </Form.Item>
            <Form.Item name="second_interviewer" label="复试面试官">
              <Input placeholder="可选" />
            </Form.Item>
          </>
        );
      case 'send_offer':
        return (
          <>
            <Form.Item name="offer_position" label="Offer 岗位" rules={[{ required: true, message: '请输入 Offer 岗位' }]}>
              <Input placeholder="默认使用候选人应聘岗位" />
            </Form.Item>
            <Form.Item name="salary_range" label="薪资范围">
              <Input placeholder="例如：15k-20k" />
            </Form.Item>
            <Form.Item name="expected_onboard_date" label="预计入职时间">
              <DatePicker style={{ width: '100%' }} placeholder="可选" format="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item name="offer_note" label="Offer 备注">
              <Input.TextArea rows={3} placeholder="填写 Offer 备注" />
            </Form.Item>
          </>
        );
      case 'mark_onboarded':
        return (
          <>
            <Alert type="success" showIcon message="确认该候选人已经入职吗？确认后流程将结束。" style={{ marginBottom: 16 }} />
            <Form.Item name="onboard_date" label="实际入职时间">
              <DatePicker style={{ width: '100%' }} placeholder="可选" format="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item name="onboard_note" label="入职备注">
              <Input.TextArea rows={3} placeholder="填写入职备注" />
            </Form.Item>
          </>
        );
      case 'mark_eliminated':
        return (
          <>
            <Alert type="warning" showIcon message="确认淘汰该候选人吗？确认后流程将结束。" style={{ marginBottom: 16 }} />
            <Form.Item name="reject_reason" label="淘汰原因" rules={[{ required: true, message: '请填写淘汰原因' }]}>
              <Input.TextArea rows={3} placeholder="请填写明确的淘汰原因" />
            </Form.Item>
            <Form.Item name="reject_note" label="备注">
              <Input.TextArea rows={3} placeholder="可选" />
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>返回</Button>

      {candidate.is_duplicate && (
        <Alert
          type="warning"
          message={`该候选人标记为重复，原始记录 ID: ${candidate.duplicate_of_id}`}
          showIcon
          style={{ marginBottom: 16 }}
          action={candidate.duplicate_of_id ? (
            <Button size="small" onClick={() => navigate(`/candidates/${candidate.duplicate_of_id}`)}>
              查看原始记录
            </Button>
          ) : undefined}
        />
      )}

      <Row gutter={16}>
        <Col span={16}>
          <Card title={`${candidate.name} - 候选人详情`} style={{ marginBottom: 16 }}>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="姓名">{candidate.name}</Descriptions.Item>
              <Descriptions.Item label="手机号">{candidate.phone}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{candidate.email}</Descriptions.Item>
              <Descriptions.Item label="学校">{candidate.school}</Descriptions.Item>
              <Descriptions.Item label="学历">{candidate.degree}</Descriptions.Item>
              <Descriptions.Item label="专业">{candidate.major}</Descriptions.Item>
              <Descriptions.Item label="应聘岗位">{candidate.target_role}</Descriptions.Item>
              <Descriptions.Item label="工作年限">{candidate.experience_years} 年</Descriptions.Item>
              <Descriptions.Item label="来源渠道"><Tag>{candidate.source_channel}</Tag></Descriptions.Item>
              <Descriptions.Item label="录入时间">{candidate.created_at ? dayjs(candidate.created_at).format('YYYY-MM-DD HH:mm') : ''}</Descriptions.Item>
              <Descriptions.Item label="最近更新">{candidate.updated_at ? dayjs(candidate.updated_at).format('YYYY-MM-DD HH:mm') : ''}</Descriptions.Item>
              <Descriptions.Item label="是否重复">{candidate.is_duplicate ? <Tag color="red">重复</Tag> : <Tag color="green">正常</Tag>}</Descriptions.Item>
              {candidate.hr_notes && (
                <Descriptions.Item label="HR备注" span={2}>{candidate.hr_notes}</Descriptions.Item>
              )}
              {candidate.interview_time && (
                <Descriptions.Item label="面试时间" span={2}>
                  <Tag color="purple">{dayjs(candidate.interview_time).format('YYYY-MM-DD HH:mm')}</Tag>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="技能" span={2}>
                <Space wrap>{(candidate.skills || []).map(s => <Tag key={s} color="blue">{s}</Tag>)}</Space>
              </Descriptions.Item>
              {candidate.experience_desc && (
                <Descriptions.Item label="工作经历" span={2}>
                  <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 13 }}>{candidate.experience_desc}</pre>
                </Descriptions.Item>
              )}
              {candidate.self_intro && (
                <Descriptions.Item label="自我介绍" span={2}>{candidate.self_intro}</Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          <Card title="投递与 AI 初筛信息" style={{ marginBottom: 16 }}>
            {candidate.screening_status === 'pending' && (
              <Alert
                type="info"
                showIcon
                message="当前处于 AI 初筛阶段"
                description="候选人尚未进入正式招聘流程，可在右侧 HR 决策操作中点击通过初筛。"
                style={{ marginBottom: 12 }}
              />
            )}
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="投递来源">{candidate.source_channel || '未填写'}</Descriptions.Item>
              <Descriptions.Item label="当前阶段">
                <StageTag stage={candidate.stage} />
                {stageSourceLabel && <Tag style={{ marginLeft: 4 }}>{stageSourceLabel}</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="初筛处理状态">
                <Tag color={screeningStatus.color}>{screeningStatus.text}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="匹配度">
                {candidate.match_score === null || candidate.match_score === undefined ? (
                  <Tag>未初筛</Tag>
                ) : (
                  <Progress
                    percent={candidate.match_score}
                    size="small"
                    strokeColor={candidate.match_score >= 80 ? '#f5222d' : candidate.match_score >= 60 ? '#faad14' : '#8c8c8c'}
                    style={{ maxWidth: 220 }}
                  />
                )}
              </Descriptions.Item>
              <Descriptions.Item label="推荐等级">
                {candidate.priority_level ? <Tag color={candidate.priority_level === '高优先级' ? 'red' : candidate.priority_level === '中优先级' ? 'gold' : 'default'}>{candidate.priority_level}</Tag> : <Tag>未初筛</Tag>}
              </Descriptions.Item>
              {candidate.screening_result && (
                <Descriptions.Item label="初筛建议">{candidate.screening_result}</Descriptions.Item>
              )}
              {candidate.screening_updated_at && (
                <Descriptions.Item label="初筛时间">{dayjs(candidate.screening_updated_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
              )}
              {candidate.screening_reason && (
                <Descriptions.Item label="AI初筛理由" span={2}>{candidate.screening_reason}</Descriptions.Item>
              )}
              {(candidate.risk_flags || []).length > 0 && (
                <Descriptions.Item label="风险提示" span={2}>
                  <Space wrap>{candidate.risk_flags.map(flag => <Tag key={flag} color={flag === '暂无明显风险' ? 'green' : 'orange'}>{flag}</Tag>)}</Space>
                </Descriptions.Item>
              )}
              {candidate.follow_up_date && (
                <Descriptions.Item label="计划跟进日期">{dayjs(candidate.follow_up_date).format('YYYY-MM-DD')}</Descriptions.Item>
              )}
              {candidate.last_action_at && (
                <Descriptions.Item label="最近动作时间">{dayjs(candidate.last_action_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          <Card
            title={<span><FileTextOutlined /> 简历附件</span>}
            style={{ marginBottom: 16 }}
            extra={candidate.resume_url ? (
              <Space>
                <Button
                  icon={<EyeOutlined />}
                  size="small"
                  onClick={handleViewResume}
                  disabled={!canPreviewResume}
                >
                  查看
                </Button>
                <Button
                  icon={<DownloadOutlined />}
                  size="small"
                  onClick={handleDownloadResume}
                >
                  下载
                </Button>
              </Space>
            ) : undefined}
          >
            {candidate.resume_path ? (
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="文件名">
                  {candidate.resume_filename || '未命名简历'}
                </Descriptions.Item>
                <Descriptions.Item label="文件类型">
                  {(candidate.resume_file_type || '未知').toUpperCase()}
                </Descriptions.Item>
                <Descriptions.Item label="文件大小">
                  {formatResumeSize(candidate.resume_file_size)}
                </Descriptions.Item>
                <Descriptions.Item label="上传时间">
                  {candidate.resume_uploaded_at ? dayjs(candidate.resume_uploaded_at).format('YYYY-MM-DD HH:mm') : '未知'}
                </Descriptions.Item>
                <Descriptions.Item label="查看说明">
                  {canPreviewResume
                    ? '支持直接查看，点击右上角“查看”即可新标签页打开'
                    : candidate.resume_url
                      ? '当前格式建议直接下载查看'
                      : '当前文件暂不可访问'}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <div style={{ color: '#999' }}>未上传简历</div>
            )}
          </Card>

          {(hasInterviewInfo || hasRecheckInfo || hasOfferInfo || hasOnboardInfo || hasRejectInfo) && (
            <Card title="招聘流程信息" style={{ marginBottom: 16 }}>
              {hasInterviewInfo && (
                <Descriptions title="面试安排" bordered column={2} size="small" style={{ marginBottom: 16 }}>
                  {candidate.interview_time && (
                    <Descriptions.Item label="面试时间">{dayjs(candidate.interview_time).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
                  )}
                  {candidate.interview_method && <Descriptions.Item label="面试方式">{candidate.interview_method}</Descriptions.Item>}
                  {candidate.interviewer && <Descriptions.Item label="面试官">{candidate.interviewer}</Descriptions.Item>}
                  {candidate.interview_note && <Descriptions.Item label="面试备注" span={2}>{candidate.interview_note}</Descriptions.Item>}
                </Descriptions>
              )}
              {hasRecheckInfo && (
                <Descriptions title="复试信息" bordered column={2} size="small" style={{ marginBottom: 16 }}>
                  {candidate.recheck_note && <Descriptions.Item label="复试原因 / 一面反馈" span={2}>{candidate.recheck_note}</Descriptions.Item>}
                  {candidate.second_interview_time && (
                    <Descriptions.Item label="复试时间">{dayjs(candidate.second_interview_time).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
                  )}
                  {candidate.second_interviewer && <Descriptions.Item label="复试面试官">{candidate.second_interviewer}</Descriptions.Item>}
                </Descriptions>
              )}
              {hasOfferInfo && (
                <Descriptions title="Offer 信息" bordered column={2} size="small" style={{ marginBottom: 16 }}>
                  {candidate.offer_position && <Descriptions.Item label="Offer 岗位">{candidate.offer_position}</Descriptions.Item>}
                  {candidate.salary_range && <Descriptions.Item label="薪资范围">{candidate.salary_range}</Descriptions.Item>}
                  {candidate.expected_onboard_date && (
                    <Descriptions.Item label="预计入职时间">{dayjs(candidate.expected_onboard_date).format('YYYY-MM-DD')}</Descriptions.Item>
                  )}
                  {candidate.offer_note && <Descriptions.Item label="Offer 备注" span={2}>{candidate.offer_note}</Descriptions.Item>}
                </Descriptions>
              )}
              {hasOnboardInfo && (
                <Descriptions title="入职信息" bordered column={2} size="small" style={{ marginBottom: 16 }}>
                  {candidate.onboard_date && <Descriptions.Item label="实际入职时间">{dayjs(candidate.onboard_date).format('YYYY-MM-DD')}</Descriptions.Item>}
                  {candidate.onboard_note && <Descriptions.Item label="入职备注" span={2}>{candidate.onboard_note}</Descriptions.Item>}
                </Descriptions>
              )}
              {hasRejectInfo && (
                <Descriptions title="淘汰信息" bordered column={2} size="small">
                  {candidate.reject_reason && <Descriptions.Item label="淘汰原因" span={2}>{candidate.reject_reason}</Descriptions.Item>}
                  {candidate.reject_note && <Descriptions.Item label="淘汰备注" span={2}>{candidate.reject_note}</Descriptions.Item>}
                </Descriptions>
              )}
            </Card>
          )}

          <Card
            title={<span><RobotOutlined /> 面试反馈 AI 总结</span>}
            style={{ marginBottom: 16 }}
            extra={
              <Button
                icon={<ReloadOutlined />}
                type="primary"
                size="small"
                loading={aiLoading === 'interview_summary'}
                onClick={handleGenerateInterviewSummary}
              >
                {hasInterviewAiSummary ? '重新生成' : '生成 AI 面试总结'}
              </Button>
            }
          >
            <Form form={interviewFeedbackForm} layout="vertical">
              <Row gutter={12}>
                <Col span={8}>
                  <Form.Item name="interviewer" label="面试官">
                    <Input placeholder="可选" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="interview_round" label="面试轮次">
                    <Select
                      allowClear
                      placeholder="可选"
                      options={['一面', '复试', '终面', '加面'].map(item => ({ label: item, value: item }))}
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="feedback_time" label="反馈时间">
                    <DatePicker showTime style={{ width: '100%' }} format="YYYY-MM-DD HH:mm" />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item
                name="interview_feedback_text"
                label="面试原始反馈"
                rules={[{ required: true, message: '请输入面试原始反馈' }]}
              >
                <Input.TextArea rows={4} placeholder="请输入面试官的原始反馈，例如技术表现、沟通情况、风险点和是否建议进入下一轮" />
              </Form.Item>
            </Form>

            {candidate.interview_feedback_text && (
              <Descriptions bordered column={1} size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="原始面试反馈">
                  <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 13 }}>{candidate.interview_feedback_text}</pre>
                </Descriptions.Item>
              </Descriptions>
            )}

            {hasInterviewAiSummary ? (
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="技术能力总结">{candidate.interview_ai_technical_summary || '反馈未明确描述技术能力'}</Descriptions.Item>
                <Descriptions.Item label="沟通表达总结">{candidate.interview_ai_communication_summary || '反馈未明确描述沟通表达'}</Descriptions.Item>
                <Descriptions.Item label="岗位匹配度判断">{candidate.interview_ai_job_match || '反馈未充分说明岗位匹配度'}</Descriptions.Item>
                <Descriptions.Item label="风险点">
                  <Space wrap>
                    {(candidate.interview_ai_risk_points || []).map(item => <Tag key={item} color="orange">{item}</Tag>)}
                    {(candidate.interview_ai_risk_points || []).length === 0 && <Tag>暂无明确风险点</Tag>}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="推荐结论">
                  <Tag color={
                    candidate.interview_ai_recommendation === '建议 offer' ? 'green'
                      : candidate.interview_ai_recommendation === '建议复试' ? 'blue'
                        : candidate.interview_ai_recommendation === '不建议继续' ? 'red'
                          : 'gold'
                  }>
                    {candidate.interview_ai_recommendation || '待定'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="下一步建议">{candidate.interview_ai_next_step || '建议HR结合完整面试记录复核'}</Descriptions.Item>
                <Descriptions.Item label="生成时间">
                  {candidate.interview_ai_generated_at ? dayjs(candidate.interview_ai_generated_at).format('YYYY-MM-DD HH:mm') : '未生成'}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Alert
                type="info"
                showIcon
                message="填写面试原始反馈后，可生成结构化 AI 面试总结"
                description="总结仅作为辅助参考，不会自动改变候选人阶段或淘汰候选人。"
              />
            )}
          </Card>

          <Card
            title={<span><RobotOutlined /> AI 摘要</span>}
            extra={<Button icon={<ReloadOutlined />} size="small" loading={aiLoading === 'summary'} onClick={handleRegenSummary}>重新生成</Button>}
            style={{ marginBottom: 16 }}
          >
            <p style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
              {candidate.ai_summary || '暂无AI摘要，点击"重新生成"按钮生成'}
            </p>
          </Card>

          <Card
            title={<span><RobotOutlined /> AI 标签</span>}
            extra={<Button icon={<ReloadOutlined />} size="small" loading={aiLoading === 'tags'} onClick={handleRegenTags}>重新生成</Button>}
            style={{ marginBottom: 16 }}
          >
            <Space wrap>
              {(candidate.ai_tags || []).length > 0
                ? candidate.ai_tags.map(t => <Tag key={t} color="purple">{t}</Tag>)
                : <span style={{ color: '#999' }}>暂无标签，点击"重新生成"按钮生成</span>
              }
            </Space>
          </Card>

          <Card
            title="HR 备注"
            extra={
              editingNotes
                ? <Button icon={<SaveOutlined />} size="small" type="primary" onClick={handleSaveNotes}>保存</Button>
                : <Button icon={<EditOutlined />} size="small" onClick={() => setEditingNotes(true)}>编辑</Button>
            }
          >
            {editingNotes ? (
              <Input.TextArea value={notes} onChange={e => setNotes(e.target.value)} rows={3} />
            ) : (
              <p style={{ color: notes ? '#333' : '#999' }}>{notes || '暂无备注'}</p>
            )}
          </Card>
        </Col>

        <Col span={8}>
          <Card title={<span><ThunderboltOutlined /> HR 决策操作</span>} style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 12 }}>
              <span style={{ marginRight: 8 }}>当前状态：</span>
              <StageTag stage={candidate.stage} />
              {stageSourceLabel && (
                <Tag color={candidate.stage_source === 'manual' ? 'orange' : candidate.stage_source === 'hr_action' ? 'blue' : 'default'} style={{ marginLeft: 4 }}>
                  {stageSourceLabel}
                </Tag>
              )}
            </div>
            {terminalStages.includes(candidate.stage) && (
              <Alert
                type="info"
                showIcon
                message="候选人流程已结束，流程推进按钮已禁用"
                style={{ marginBottom: 12 }}
              />
            )}
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              {HR_ACTIONS.map(action => {
                const allowed = isActionAllowed(action.key);
                const tooltip = allowed
                  ? action.description
                  : terminalStages.includes(candidate.stage)
                    ? '候选人流程已结束'
                    : `当前阶段「${candidate.stage}」不适合执行该操作`;
                return (
                  <Tooltip key={action.key} title={tooltip} placement="left">
                    <Button
                      block
                      loading={actionLoading === action.key}
                      disabled={!allowed}
                      onClick={() => handleHRAction(action.key)}
                      danger={action.key === 'mark_eliminated'}
                      type={action.key === 'mark_eliminated' ? 'default' : 'primary'}
                      ghost={action.key !== 'mark_eliminated'}
                    >
                      {action.label}
                    </Button>
                  </Tooltip>
                );
              })}
            </Space>
          </Card>

          <Card title="阶段人工修正" style={{ marginBottom: 16 }} size="small">
            <div style={{ color: '#999', fontSize: 12, marginBottom: 8 }}>
              仅用于修正系统自动判断有误的情况
            </div>
            <Select
              value={candidate.stage}
              style={{ width: '100%' }}
              onChange={handleStageChange}
              options={STAGES.map(s => ({ label: s, value: s }))}
              size="small"
            />
          </Card>

          <Card
            title={<span><RobotOutlined /> AI 跟进建议</span>}
            extra={<Button icon={<ReloadOutlined />} size="small" loading={aiLoading === 'followup'} onClick={handleGenFollowup}>刷新建议</Button>}
            style={{ marginBottom: 16 }}
          >
            {candidate.is_overdue && (
              <Alert
                type="warning"
                showIcon
                message={`当前候选人已超时 ${candidate.overdue_days} 天未跟进`}
                description={candidate.overdue_reason}
                style={{ marginBottom: 12 }}
              />
            )}
            <Space wrap style={{ marginBottom: 8 }}>
              <Tag color={candidate.followup_priority === '高' ? 'red' : candidate.followup_priority === '中' ? 'gold' : 'default'}>
                {candidate.followup_priority || '低'}优先级
              </Tag>
              {candidate.is_overdue && <Tag color="red">超时未跟进</Tag>}
              {candidate.followup_days_since_update >= 3 && <Tag color="orange">{candidate.followup_days_since_update}天未更新</Tag>}
            </Space>
            <p style={{ fontSize: 13, lineHeight: 1.8, color: '#555' }}>
              {followup || candidate.followup_suggestion || '暂无跟进建议'}
            </p>
            {candidate.followup_reason && (
              <div style={{ fontSize: 12, color: '#999', lineHeight: 1.6 }}>
                触发原因：{candidate.followup_reason}
              </div>
            )}
          </Card>

          <Card title={<span><HistoryOutlined /> 阶段变更记录</span>} styles={{ body: { maxHeight: 300, overflow: 'auto' } }} style={{ marginBottom: 16 }}>
            {stageLogs.length > 0 ? (
              <Timeline
                items={stageLogs.map(log => ({
                  color: log.trigger_source === 'hr_action' ? 'blue' : log.trigger_source === 'manual' ? 'orange' : 'green',
                  children: (
                    <div>
                      <div style={{ fontSize: 13 }}>
                        <StageTag stage={log.from_stage} /> <span style={{ margin: '0 4px' }}>&rarr;</span> <StageTag stage={log.to_stage} />
                      </div>
                      <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{log.trigger_reason}</div>
                      <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>
                        <Tag color={log.trigger_source === 'manual' ? 'orange' : log.trigger_source === 'hr_action' ? 'blue' : 'default'} style={{ fontSize: 10 }}>
                          {STAGE_SOURCE_LABELS[log.trigger_source] || log.trigger_source}
                        </Tag>
                        {log.created_at ? dayjs(log.created_at).format('MM-DD HH:mm') : ''}
                      </div>
                    </div>
                  ),
                }))}
              />
            ) : (
              <div style={{ color: '#999', textAlign: 'center', padding: 16 }}>暂无阶段变更记录</div>
            )}
          </Card>

          <Card title="操作日志" styles={{ body: { maxHeight: 400, overflow: 'auto' } }}>
            <Timeline
              items={(candidate.activity_logs || [])
                .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                .map(log => ({
                  color: log.action === 'created' ? 'green' : log.action === 'stage_changed' ? 'blue' : log.action === 'ai_interview_summary' ? 'purple' : 'gray',
                  children: (
                    <div>
                      <div style={{ fontSize: 13 }}>{log.detail}</div>
                      <div style={{ color: '#999', fontSize: 11 }}>
                        {log.created_at ? dayjs(log.created_at).format('MM-DD HH:mm') : ''}
                      </div>
                    </div>
                  ),
                }))}
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title={actionModal ? actionModalTitle[actionModal] : ''}
        open={!!actionModal}
        onOk={handleSubmitActionModal}
        onCancel={() => { setActionModal(null); actionForm.resetFields(); }}
        confirmLoading={!!actionModal && actionLoading === actionModal}
        okText="确认提交"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={actionForm} layout="vertical" preserve={false}>
          {renderActionModalFields()}
        </Form>
      </Modal>
    </div>
  );
};

export default CandidateDetailPage;
