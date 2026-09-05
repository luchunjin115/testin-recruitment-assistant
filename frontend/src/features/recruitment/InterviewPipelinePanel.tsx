import React, { useMemo, useState } from 'react';
import { CalendarOutlined, CheckCircleOutlined, EditOutlined, EyeOutlined, StopOutlined, UserDeleteOutlined } from '@ant-design/icons';
import { Button, Checkbox, DatePicker, Descriptions, Form, Input, InputNumber, Modal, Select, Tag, message } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import {
  cancelApplicationInterview,
  getApplicationInterview,
  getRecruitmentPipelineError,
  markApplicationInterviewNoShow,
  rescheduleApplicationInterview,
  scheduleApplicationInterview,
  submitApplicationInterviewFeedback,
  updateApplicationInterviewFeedback,
  type InterviewListItem,
  type InterviewRecord,
} from './services/recruitmentPipeline';
import type { ScreeningCenterItem } from './services/screeningCenter';

type Props = {
  applicationId: number;
  interviews: InterviewListItem[];
  summary: ScreeningCenterItem | null | undefined;
  onChanged: () => Promise<void> | void;
};

type ScheduleValues = {
  roundNumber: number;
  interviewType: 'onsite' | 'video' | 'phone';
  scheduledStartAt: Dayjs;
  durationMinutes: number;
  timezone: string;
  interviewerNames: string[];
  location?: string;
  meetingLink?: string;
  scheduleNote?: string;
  reasonDetail?: string;
};

type FeedbackValues = {
  feedbackSummary: string;
  strengths?: string[];
  concerns?: string[];
  followUpQuestions?: string[];
  decision: 'pending' | 'next_round' | 'proceed_offer' | 'rejected' | 'candidate_withdrew';
  reasonDetail?: string;
  correctionReason?: string;
  confirmed?: boolean;
};

type CloseAction = { kind: 'cancel' | 'no_show'; interview: InterviewListItem } | null;

const TYPE_LABELS = { onsite: '现场面试', video: '视频面试', phone: '电话面试' } as const;
const STATUS_LABELS = { scheduled: '待进行', completed: '已完成', canceled: '已取消', no_show: '未到场' } as const;
const DECISION_LABELS = { pending: '待决定', next_round: '进入下一轮', proceed_offer: '进入 Offer', rejected: '面试淘汰', candidate_withdrew: '候选人退出' } as const;
const REASON_BY_DECISION = {
  pending: 'interview_round_completed',
  next_round: 'interview_next_round',
  proceed_offer: 'interview_proceed_offer',
  rejected: 'interview_rejected',
  candidate_withdrew: 'candidate_withdrew',
} as const;

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
}).format(new Date(value));
const clean = (value?: string) => value?.trim() || null;
const cleanList = (values?: string[]) => Array.from(new Set((values || []).map(value => value.trim()).filter(Boolean)));

const InterviewPipelinePanel: React.FC<Props> = ({ applicationId, interviews, summary, onChanged }) => {
  const [scheduleForm] = Form.useForm<ScheduleValues>();
  const [feedbackForm] = Form.useForm<FeedbackValues>();
  const [scheduleMode, setScheduleMode] = useState<'create' | 'edit' | 'view' | null>(null);
  const [scheduleRecord, setScheduleRecord] = useState<InterviewRecord | null>(null);
  const [feedbackRecord, setFeedbackRecord] = useState<InterviewListItem | null>(null);
  const [feedbackEditing, setFeedbackEditing] = useState(false);
  const [closeAction, setCloseAction] = useState<CloseAction>(null);
  const [closeReason, setCloseReason] = useState('');
  const [closeConfirmed, setCloseConfirmed] = useState(false);
  const [endApplication, setEndApplication] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const latest = useMemo(() => interviews[interviews.length - 1] ?? null, [interviews]);
  const canSchedule = summary?.allowedActions.includes('schedule_interview') || (
    summary?.lifecycleStatus === 'active'
    && summary.recruitmentStage === 'interview'
    && latest !== null
    && (latest.status === 'canceled' || latest.status === 'no_show' || (latest.status === 'completed' && latest.decision === 'next_round'))
  );

  const openCreate = () => {
    setError(null); setScheduleRecord(null); setScheduleMode('create');
    scheduleForm.setFieldsValue({
      roundNumber: latest ? latest.roundNumber + 1 : 1,
      interviewType: 'video', scheduledStartAt: dayjs().add(1, 'day').hour(10).minute(0).second(0),
      durationMinutes: 60, timezone: 'Asia/Shanghai', interviewerNames: [],
    });
  };

  const openScheduleRecord = async (item: InterviewListItem, mode: 'edit' | 'view') => {
    if (pending) return;
    setPending(true); setError(null);
    try {
      const detail = await getApplicationInterview(item.id);
      setScheduleRecord(detail); setScheduleMode(mode);
      if (mode === 'edit') scheduleForm.setFieldsValue({
        roundNumber: detail.roundNumber,
        interviewType: detail.interviewType,
        scheduledStartAt: dayjs(detail.scheduledStartAt),
        durationMinutes: detail.durationMinutes,
        timezone: detail.timezone,
        interviewerNames: detail.interviewerNames,
        location: detail.location || undefined,
        meetingLink: detail.meetingLink || undefined,
        scheduleNote: detail.scheduleNote || undefined,
        reasonDetail: undefined,
      });
    } catch (requestError) { message.error(getRecruitmentPipelineError(requestError)); }
    finally { setPending(false); }
  };

  const submitSchedule = async () => {
    if (!scheduleMode || scheduleMode === 'view' || pending) return;
    let values: ScheduleValues;
    try { values = await scheduleForm.validateFields(); } catch { return; }
    setPending(true); setError(null);
    const common = {
      interview_type: values.interviewType,
      scheduled_start_at: values.scheduledStartAt.toISOString(),
      duration_minutes: values.durationMinutes,
      timezone: values.timezone.trim(),
      interviewer_names: cleanList(values.interviewerNames),
      location: clean(values.location), meeting_link: clean(values.meetingLink), schedule_note: clean(values.scheduleNote),
    };
    try {
      if (scheduleMode === 'create') await scheduleApplicationInterview(applicationId, { ...common, round_number: values.roundNumber });
      else if (scheduleRecord) await rescheduleApplicationInterview(scheduleRecord.id, { ...common, expected_version: scheduleRecord.version, reason_detail: clean(values.reasonDetail) });
      setScheduleMode(null); setScheduleRecord(null); scheduleForm.resetFields();
      message.success(scheduleMode === 'create' ? '面试已安排。' : '面试安排已更新。');
      await onChanged();
    } catch (requestError) { setError(getRecruitmentPipelineError(requestError)); }
    finally { setPending(false); }
  };

  const openFeedback = (item: InterviewListItem, editing: boolean) => {
    setError(null); setFeedbackRecord(item); setFeedbackEditing(editing);
    feedbackForm.setFieldsValue({
      feedbackSummary: item.feedbackSummary || '', strengths: item.strengths,
      concerns: item.concerns, followUpQuestions: item.followUpQuestions,
      decision: item.decision, reasonDetail: undefined, correctionReason: undefined, confirmed: false,
    });
  };

  const submitFeedback = async () => {
    if (!feedbackRecord || pending) return;
    let values: FeedbackValues;
    try { values = await feedbackForm.validateFields(); } catch { return; }
    const highRisk = ['rejected', 'candidate_withdrew'].includes(values.decision);
    if ((highRisk || feedbackEditing) && !values.confirmed) { setError('请勾选确认，避免误结束或误改招聘流程。'); return; }
    if (highRisk && !clean(values.reasonDetail)) { setError('面试淘汰或候选人退出必须填写原因。'); return; }
    if (feedbackEditing && !clean(values.correctionReason)) { setError('更正已提交反馈必须填写更正原因。'); return; }
    const content = {
      expected_version: feedbackRecord.version,
      feedback_summary: values.feedbackSummary.trim(),
      strengths: cleanList(values.strengths), concerns: cleanList(values.concerns),
      follow_up_questions: cleanList(values.followUpQuestions), decision: values.decision,
      confirmed: Boolean(values.confirmed),
    };
    setPending(true); setError(null);
    try {
      if (feedbackEditing) {
        await updateApplicationInterviewFeedback(feedbackRecord.id, {
          ...content, correction_reason: values.correctionReason!.trim(),
        });
      } else {
        await submitApplicationInterviewFeedback(feedbackRecord.id, {
          ...content,
          reason_code: REASON_BY_DECISION[values.decision],
          reason_detail: clean(values.reasonDetail),
        });
      }
      setFeedbackRecord(null); feedbackForm.resetFields();
      message.success(feedbackEditing ? '面试反馈已更正并追加审计。' : '面试反馈已保存。');
      await onChanged();
    } catch (requestError) { setError(getRecruitmentPipelineError(requestError)); }
    finally { setPending(false); }
  };

  const submitCloseAction = async () => {
    if (!closeAction || pending) return;
    if (!closeReason.trim()) { setError('必须填写具体原因。'); return; }
    if (!closeConfirmed) { setError('请勾选确认后再提交。'); return; }
    setPending(true); setError(null);
    try {
      if (closeAction.kind === 'cancel') await cancelApplicationInterview(closeAction.interview.id, closeAction.interview.version, closeReason.trim());
      else await markApplicationInterviewNoShow(closeAction.interview.id, closeAction.interview.version, closeReason.trim(), endApplication);
      setCloseAction(null); setCloseReason(''); setCloseConfirmed(false); setEndApplication(false);
      message.success(closeAction.kind === 'cancel' ? '面试已取消，Application 未自动淘汰。' : endApplication ? '已记录未到场并结束流程。' : '已记录未到场，Application 保持可继续处理。');
      await onChanged();
    } catch (requestError) { setError(getRecruitmentPipelineError(requestError)); }
    finally { setPending(false); }
  };

  return (
    <div className="recruitment-interview-panel">
      <div className="recruitment-pipeline-section-toolbar">
        <div><strong>共 {interviews.length} 轮记录</strong><span>每轮安排和人工反馈独立保存</span></div>
        <Button disabled={!canSchedule} icon={<CalendarOutlined />} onClick={openCreate} size="small" type="primary">安排{latest ? '下一轮' : '首轮'}面试</Button>
      </div>
      {!canSchedule && interviews.length === 0 && <p className="recruitment-pipeline-help">只有 HR 已通过且仍有效的 Application 可以开始面试。</p>}
      <div className="recruitment-interview-history">
        {interviews.map(item => (
          <article className="recruitment-interview-record" key={item.id}>
            <header><div><strong>第 {item.roundNumber} 轮 · {TYPE_LABELS[item.interviewType]}</strong><span>{formatDateTime(item.scheduledStartAt)} · {item.durationMinutes} 分钟 · {item.timezone}</span></div><div><Tag>{STATUS_LABELS[item.status]}</Tag><Tag>{DECISION_LABELS[item.decision]}</Tag><small>v{item.version}</small></div></header>
            <p>{item.interviewerNames.join('、')} · {item.location || '地点未填写'}</p>
            {item.feedbackSummary && <div className="recruitment-interview-feedback"><strong>人工反馈</strong><p>{item.feedbackSummary}</p>{item.strengths.length > 0 && <span>优势：{item.strengths.join('；')}</span>}{item.concerns.length > 0 && <span>关注：{item.concerns.join('；')}</span>}</div>}
            <footer>
              <Button icon={<EyeOutlined />} loading={pending} onClick={() => void openScheduleRecord(item, 'view')} size="small">完整安排</Button>
              {item.status === 'scheduled' && <Button icon={<EditOutlined />} onClick={() => void openScheduleRecord(item, 'edit')} size="small">改期</Button>}
              {item.status === 'scheduled' && <Button icon={<CheckCircleOutlined />} onClick={() => openFeedback(item, false)} size="small" type="primary">填写反馈</Button>}
              {item.status === 'scheduled' && <Button icon={<StopOutlined />} onClick={() => { setCloseAction({ kind: 'cancel', interview: item }); setError(null); }} size="small">取消</Button>}
              {item.status === 'scheduled' && <Button danger icon={<UserDeleteOutlined />} onClick={() => { setCloseAction({ kind: 'no_show', interview: item }); setError(null); }} size="small">未到场</Button>}
              {item.status === 'completed' && <Button icon={<EditOutlined />} onClick={() => openFeedback(item, true)} size="small">更正反馈</Button>}
            </footer>
          </article>
        ))}
      </div>

      <Modal cancelText="取消" confirmLoading={pending} footer={scheduleMode === 'view' ? null : undefined} okText={scheduleMode === 'create' ? '保存面试' : '保存改期'} onCancel={() => { if (!pending) { setScheduleMode(null); setScheduleRecord(null); } }} onOk={() => void submitSchedule()} open={scheduleMode !== null} title={scheduleMode === 'create' ? '安排面试' : scheduleMode === 'edit' ? '修改面试安排' : '完整面试安排'}>
        {error && <div className="recruitment-pipeline-form-error">{error}</div>}
        {scheduleMode === 'view' && scheduleRecord ? <Descriptions bordered column={1} size="small" items={[
          { key: 'time', label: '时间', children: formatDateTime(scheduleRecord.scheduledStartAt) },
          { key: 'type', label: '形式', children: TYPE_LABELS[scheduleRecord.interviewType] },
          { key: 'duration', label: '时长', children: `${scheduleRecord.durationMinutes} 分钟` },
          { key: 'timezone', label: '时区', children: scheduleRecord.timezone },
          { key: 'interviewers', label: '面试官', children: scheduleRecord.interviewerNames.join('、') },
          { key: 'location', label: '地点', children: scheduleRecord.location || '未填写' },
          { key: 'link', label: '会议链接', children: scheduleRecord.meetingLink ? <a href={scheduleRecord.meetingLink} rel="noreferrer" target="_blank">打开会议链接</a> : '未填写' },
          { key: 'note', label: '安排备注', children: scheduleRecord.scheduleNote || '未填写' },
        ]} /> : <Form form={scheduleForm} layout="vertical"><div className="recruitment-interview-form-grid">
          <Form.Item label="面试轮次" name="roundNumber" rules={[{ required: true }]}><InputNumber disabled={scheduleMode === 'edit'} min={1} precision={0} /></Form.Item>
          <Form.Item label="面试形式" name="interviewType" rules={[{ required: true }]}><Select options={[{ value: 'video', label: '视频面试' }, { value: 'onsite', label: '现场面试' }, { value: 'phone', label: '电话面试' }]} /></Form.Item>
          <Form.Item label="开始时间" name="scheduledStartAt" rules={[{ required: true }]}><DatePicker showTime format="YYYY-MM-DD HH:mm" /></Form.Item>
          <Form.Item label="时长（分钟）" name="durationMinutes" rules={[{ required: true }]}><InputNumber min={15} max={480} precision={0} /></Form.Item>
          <Form.Item label="时区" name="timezone" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="面试官" name="interviewerNames" rules={[{ required: true }]}><Select mode="tags" maxCount={10} tokenSeparators={[',', '，', '、']} /></Form.Item>
          <Form.Item label="地点" name="location"><Input /></Form.Item>
          <Form.Item label="会议链接" name="meetingLink" rules={[{ type: 'url' }]}><Input /></Form.Item>
        </div><Form.Item label="安排备注" name="scheduleNote"><Input.TextArea maxLength={2000} rows={2} showCount /></Form.Item>{scheduleMode === 'edit' && <Form.Item label="改期说明" name="reasonDetail"><Input.TextArea maxLength={1000} rows={2} showCount /></Form.Item>}</Form>}
      </Modal>

      <Modal cancelText="取消" confirmLoading={pending} okText={feedbackEditing ? '确认更正' : '保存反馈'} onCancel={() => { if (!pending) { setFeedbackRecord(null); feedbackForm.resetFields(); } }} onOk={() => void submitFeedback()} open={feedbackRecord !== null} title={feedbackEditing ? '更正已提交面试反馈' : '填写面试反馈'}>
        {error && <div className="recruitment-pipeline-form-error">{error}</div>}
        <Form form={feedbackForm} layout="vertical">
          <Form.Item label="汇总反馈" name="feedbackSummary" rules={[{ required: true, min: 1, max: 5000 }]}><Input.TextArea rows={4} showCount maxLength={5000} /></Form.Item>
          <Form.Item label="人工确认的优势" name="strengths"><Select mode="tags" maxCount={20} tokenSeparators={[';', '；']} /></Form.Item>
          <Form.Item label="风险与不足" name="concerns"><Select mode="tags" maxCount={20} tokenSeparators={[';', '；']} /></Form.Item>
          <Form.Item label="后续核实问题" name="followUpQuestions"><Select mode="tags" maxCount={20} tokenSeparators={[';', '；']} /></Form.Item>
          <Form.Item label="本轮决定" name="decision" rules={[{ required: true }]}><Select disabled={feedbackEditing && feedbackRecord?.decision !== 'pending'} options={Object.entries(DECISION_LABELS).map(([value, label]) => ({ value, label }))} /></Form.Item>
          {!feedbackEditing && <Form.Item label="结束流程说明（淘汰或退出时必填）" name="reasonDetail"><Input.TextArea maxLength={1000} rows={2} showCount /></Form.Item>}
          {feedbackEditing && <Form.Item label="更正原因" name="correctionReason" rules={[{ required: true }]}><Input.TextArea maxLength={1000} rows={2} showCount /></Form.Item>}
          <Form.Item name="confirmed" valuePropName="checked"><Checkbox>我已核对候选人、轮次和决定；结束流程或更正记录将追加审计</Checkbox></Form.Item>
        </Form>
      </Modal>

      <Modal cancelText="取消" confirmLoading={pending} okButtonProps={{ danger: closeAction?.kind === 'no_show' }} okText={closeAction?.kind === 'cancel' ? '确认取消面试' : '确认记录未到场'} onCancel={() => { if (!pending) { setCloseAction(null); setCloseReason(''); setCloseConfirmed(false); setEndApplication(false); } }} onOk={() => void submitCloseAction()} open={closeAction !== null} title={closeAction?.kind === 'cancel' ? '取消面试' : '记录候选人未到场'}>
        {error && <div className="recruitment-pipeline-form-error">{error}</div>}
        <Input.TextArea aria-label="操作原因" maxLength={1000} onChange={event => setCloseReason(event.target.value)} placeholder="填写可追溯的具体原因" rows={3} showCount value={closeReason} />
        {closeAction?.kind === 'no_show' && <Checkbox checked={endApplication} className="recruitment-pipeline-confirm" onChange={event => setEndApplication(event.target.checked)}>同时因未到场结束招聘流程</Checkbox>}
        <Checkbox checked={closeConfirmed} className="recruitment-pipeline-confirm" onChange={event => setCloseConfirmed(event.target.checked)}>我已核对本轮面试和操作后果</Checkbox>
      </Modal>
    </div>
  );
};

export default InterviewPipelinePanel;
