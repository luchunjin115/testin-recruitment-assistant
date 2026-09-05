import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Button, Descriptions, Empty, Form, Input, Modal, Select, Space, Tag, message } from 'antd';
import {
  acceptApplicationOffer,
  cancelApplicationProcess,
  confirmApplicationAdmission,
  confirmApplicationHire,
  createApplicationOffer,
  declineApplicationOffer,
  expireApplicationOffer,
  getRecruitmentPipelineError,
  listApplicationOffers,
  reopenStage9Application,
  sendApplicationOffer,
  updateApplicationOffer,
  withdrawApplication,
  withdrawApplicationOffer,
  type OfferDetailsInput,
  type OfferRecord,
  type SalaryPeriod,
} from './services/recruitmentPipeline';
import type { ScreeningCenterAllowedAction, ScreeningCenterItem } from './services/screeningCenter';

type Props = {
  applicationId: number;
  summary: ScreeningCenterItem | null | undefined;
  latestInterviewVersion: number | null;
  onChanged: () => Promise<void> | void;
};

type OfferFormValues = {
  positionTitle: string;
  currency: string;
  salaryPeriod: SalaryPeriod;
  baseSalaryAmount: string;
  salaryMonths?: string;
  bonusNote?: string;
  benefitsNote?: string;
  validUntil: string;
  expectedStartDate: string;
  note?: string;
  correctionReason?: string;
};

type PipelineAction = {
  key: ScreeningCenterAllowedAction;
  title: string;
  reasonCode: string;
  offer?: OfferRecord;
};

const STATUS_LABELS: Record<OfferRecord['status'], string> = {
  draft: '草稿', sent: '已发送', accepted: '已接受', declined: '已拒绝', withdrawn: '已撤回', expired: '已过期',
};

const toNullable = (value?: string) => value?.trim() || null;
const toPayload = (values: OfferFormValues): OfferDetailsInput => ({
  position_title: values.positionTitle.trim(),
  currency: values.currency.trim().toUpperCase(),
  salary_period: values.salaryPeriod,
  base_salary_amount: values.baseSalaryAmount.trim(),
  salary_months: values.salaryPeriod === 'monthly' ? toNullable(values.salaryMonths) : null,
  bonus_note: toNullable(values.bonusNote),
  benefits_note: toNullable(values.benefitsNote),
  valid_until: values.validUntil,
  expected_start_date: values.expectedStartDate,
  note: toNullable(values.note),
});

const OfferPipelinePanel: React.FC<Props> = ({ applicationId, summary, latestInterviewVersion, onChanged }) => {
  const [offers, setOffers] = useState<OfferRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingOffer, setEditingOffer] = useState<OfferRecord | null | 'new'>(null);
  const [action, setAction] = useState<PipelineAction | null>(null);
  const [reasonDetail, setReasonDetail] = useState('');
  const [pending, setPending] = useState(false);
  const [form] = Form.useForm<OfferFormValues>();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setOffers(await listApplicationOffers(applicationId));
      setError(null);
    } catch (caught) {
      setError(getRecruitmentPipelineError(caught));
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => { void load(); }, [load]);

  const allowed = useMemo(
    () => new Set(summary?.allowedActions ?? []),
    [summary?.allowedActions],
  );
  const latestOffer = offers[0] ?? null;
  const activeOffer = offers.find(item => ['draft', 'sent', 'accepted'].includes(item.status)) ?? null;
  const reopenExpectedVersion = latestOffer?.version ?? latestInterviewVersion;
  const endExpectedVersion = activeOffer?.version
    ?? (summary?.recruitmentStage === 'interview' ? latestInterviewVersion : null);

  const refreshAfterWrite = async () => {
    await load();
    await onChanged();
  };

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({ currency: 'CNY', salaryPeriod: 'monthly' });
    setEditingOffer('new');
  };

  const openEdit = (offer: OfferRecord) => {
    form.setFieldsValue({
      positionTitle: offer.positionTitle,
      currency: offer.currency,
      salaryPeriod: offer.salaryPeriod,
      baseSalaryAmount: offer.baseSalaryAmount,
      salaryMonths: offer.salaryMonths ?? undefined,
      bonusNote: offer.bonusNote ?? undefined,
      benefitsNote: offer.benefitsNote ?? undefined,
      validUntil: offer.validUntil,
      expectedStartDate: offer.expectedStartDate,
      note: offer.note ?? undefined,
      correctionReason: undefined,
    });
    setEditingOffer(offer);
  };

  const saveOffer = async () => {
    if (pending || editingOffer === null) return;
    let values: OfferFormValues;
    try { values = await form.validateFields(); } catch { return; }
    setPending(true);
    setError(null);
    try {
      if (editingOffer === 'new') {
        await createApplicationOffer(applicationId, toPayload(values));
      } else {
        await updateApplicationOffer(editingOffer.id, {
          ...toPayload(values),
          expected_version: editingOffer.version,
          confirmed: editingOffer.status === 'sent',
          correction_reason: editingOffer.status === 'sent'
            ? toNullable(values.correctionReason)
            : null,
        });
      }
      setEditingOffer(null);
      message.success(editingOffer === 'new' ? 'Offer 草稿已创建并写入审计。' : 'Offer 已保存并增加版本。');
      await refreshAfterWrite();
    } catch (caught) {
      setError(getRecruitmentPipelineError(caught));
    } finally {
      setPending(false);
    }
  };

  const runAction = async () => {
    if (!action || pending || !reasonDetail.trim()) return;
    const expectedVersion = action.offer?.version
      ?? (action.key === 'reopen_stage9' ? reopenExpectedVersion : endExpectedVersion);
    const input = {
      expected_version: expectedVersion,
      reason_code: action.reasonCode,
      reason_detail: reasonDetail.trim(),
      confirmed: true as const,
    };
    setPending(true);
    setError(null);
    try {
      if (action.key === 'send_offer' && action.offer) await sendApplicationOffer(action.offer.id, input);
      else if (action.key === 'accept_offer' && action.offer) await acceptApplicationOffer(action.offer.id, input);
      else if (action.key === 'decline_offer' && action.offer) await declineApplicationOffer(action.offer.id, input);
      else if (action.key === 'withdraw_offer' && action.offer) await withdrawApplicationOffer(action.offer.id, input);
      else if (action.key === 'expire_offer' && action.offer) await expireApplicationOffer(action.offer.id, input);
      else if (action.key === 'confirm_admission') await confirmApplicationAdmission(applicationId, input);
      else if (action.key === 'confirm_hire') await confirmApplicationHire(applicationId, input);
      else if (action.key === 'withdraw_application') await withdrawApplication(applicationId, input);
      else if (action.key === 'cancel_process') await cancelApplicationProcess(applicationId, input);
      else if (action.key === 'reopen_stage9') await reopenStage9Application(applicationId, input);
      setAction(null);
      setReasonDetail('');
      message.success(`${action.title}已完成，Application、Offer、历史与审计已同步刷新。`);
      await refreshAfterWrite();
    } catch (caught) {
      setError(getRecruitmentPipelineError(caught));
    } finally {
      setPending(false);
    }
  };

  const offerAction = (key: PipelineAction['key'], title: string, reasonCode: string, offer: OfferRecord) => (
    <Button key={key} danger={['decline_offer', 'withdraw_offer', 'expire_offer'].includes(key)} onClick={() => {
      setReasonDetail('');
      setAction({ key, title, reasonCode, offer });
    }}>{title}</Button>
  );
  const applicationAction = (key: PipelineAction['key'], title: string, reasonCode: string, danger = false) => (
    <Button key={key} danger={danger} onClick={() => {
      setReasonDetail('');
      setAction({ key, title, reasonCode });
    }}>{title}</Button>
  );

  return <>
    {error && <Alert className="recruitment-offer-alert" message={error} showIcon type="error" action={<Button onClick={() => void load()}>重试</Button>} />}
    <div className="recruitment-offer-toolbar">
      <Space wrap>
        {allowed.has('create_offer') && <Button type="primary" onClick={openCreate}>创建 Offer 草稿</Button>}
        {allowed.has('confirm_admission') && applicationAction('confirm_admission', '确认已录取、等待入职', 'application_admitted')}
        {allowed.has('confirm_hire') && applicationAction('confirm_hire', '确认正式入职', 'application_hired')}
        {allowed.has('withdraw_application') && applicationAction('withdraw_application', '记录候选人退出', 'candidate_withdrew', true)}
        {allowed.has('cancel_process') && applicationAction('cancel_process', '公司取消流程', 'company_canceled', true)}
        {allowed.has('reopen_stage9') && applicationAction('reopen_stage9', '受控重新打开', 'stage9_reopened')}
      </Space>
    </div>
    {loading && !offers.length ? <p>正在按需读取该 Application 的 Offer…</p> : offers.length === 0 ? (
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无 Offer 记录" />
    ) : <div className="recruitment-offer-history">
      {offers.map(offer => <article className="recruitment-offer-record" key={offer.id}>
        <div className="recruitment-offer-record-heading">
          <div><strong>Offer V{offer.versionNumber}</strong><Tag>{STATUS_LABELS[offer.status]}</Tag><span>记录版本 {offer.version}</span></div>
          <Space wrap>
            {allowed.has('edit_offer') && activeOffer?.id === offer.id && <Button onClick={() => openEdit(offer)}>编辑</Button>}
            {allowed.has('send_offer') && activeOffer?.id === offer.id && offerAction('send_offer', '标记已发送', 'offer_sent', offer)}
            {allowed.has('accept_offer') && activeOffer?.id === offer.id && offerAction('accept_offer', '记录接受', 'offer_accepted', offer)}
            {allowed.has('decline_offer') && activeOffer?.id === offer.id && offerAction('decline_offer', '记录拒绝', 'offer_declined', offer)}
            {allowed.has('withdraw_offer') && activeOffer?.id === offer.id && offerAction('withdraw_offer', '公司撤回 Offer', 'offer_withdrawn', offer)}
            {allowed.has('expire_offer') && activeOffer?.id === offer.id && offerAction('expire_offer', '标记已过期', 'offer_expired', offer)}
          </Space>
        </div>
        <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
          <Descriptions.Item label="岗位">{offer.positionTitle}</Descriptions.Item>
          <Descriptions.Item label="基本薪资">{offer.currency} {offer.baseSalaryAmount} / {offer.salaryPeriod === 'monthly' ? '月' : '年'}</Descriptions.Item>
          <Descriptions.Item label="计薪月数">{offer.salaryMonths ?? '不适用'}</Descriptions.Item>
          <Descriptions.Item label="有效期至">{offer.validUntil}</Descriptions.Item>
          <Descriptions.Item label="预计入职">{offer.expectedStartDate}</Descriptions.Item>
          <Descriptions.Item label="奖金说明">{offer.bonusNote ?? '未填写'}</Descriptions.Item>
          <Descriptions.Item label="福利说明">{offer.benefitsNote ?? '未填写'}</Descriptions.Item>
          <Descriptions.Item label="内部备注">{offer.note ?? '未填写'}</Descriptions.Item>
        </Descriptions>
      </article>)}
    </div>}

    <Modal
      title={editingOffer === 'new' ? '创建 Offer 草稿' : `编辑 Offer V${editingOffer?.versionNumber ?? ''}`}
      open={editingOffer !== null}
      onCancel={() => !pending && setEditingOffer(null)}
      onOk={() => void saveOffer()}
      confirmLoading={pending}
      okText="保存 Offer"
      cancelText="取消"
      destroyOnClose
    >
      <Alert message="薪资只会在当前 Application 的 Offer 详情中返回；金额以十进制字符串提交，不经过 JavaScript 浮点运算。" showIcon type="info" />
      <Form className="recruitment-offer-form" form={form} layout="vertical">
        <Form.Item label="Offer 岗位名称" name="positionTitle" rules={[{ required: true, whitespace: true }]}><Input maxLength={200} /></Form.Item>
        <div className="recruitment-offer-form-grid">
          <Form.Item label="币种" name="currency" rules={[{ required: true }, { pattern: /^[A-Za-z]{3}$/, message: '请输入三位币种代码' }]}><Input maxLength={3} /></Form.Item>
          <Form.Item label="薪资周期" name="salaryPeriod" rules={[{ required: true }]}><Select options={[{ value: 'monthly', label: '月薪' }, { value: 'annual', label: '年薪' }]} /></Form.Item>
          <Form.Item label="基本薪资（精确小数）" name="baseSalaryAmount" rules={[{ required: true }, { pattern: /^\d{1,12}(?:\.\d{1,2})?$/, message: '请输入正数，最多两位小数' }]}><Input inputMode="decimal" /></Form.Item>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.salaryPeriod !== current.salaryPeriod}>{({ getFieldValue }) => getFieldValue('salaryPeriod') === 'monthly' ? <Form.Item label="计薪月数" name="salaryMonths" rules={[{ required: true }, { pattern: /^(?:[1-9]|1\d|2[0-4])(?:\.\d)?$/, message: '请输入 1—24，最多一位小数' }]}><Input inputMode="decimal" /></Form.Item> : null}</Form.Item>
          <Form.Item label="Offer 有效期" name="validUntil" rules={[{ required: true }]}><Input type="date" /></Form.Item>
          <Form.Item label="预计入职日期" name="expectedStartDate" rules={[{ required: true }]}><Input type="date" /></Form.Item>
        </div>
        <Form.Item label="奖金说明" name="bonusNote"><Input.TextArea maxLength={5000} rows={2} /></Form.Item>
        <Form.Item label="福利说明" name="benefitsNote"><Input.TextArea maxLength={5000} rows={2} /></Form.Item>
        <Form.Item label="HR 内部备注" name="note"><Input.TextArea maxLength={2000} rows={2} /></Form.Item>
        {editingOffer !== 'new' && editingOffer?.status === 'sent' && <Form.Item label="已发送 Offer 的更正原因" name="correctionReason" rules={[{ required: true, whitespace: true }]}><Input.TextArea maxLength={1000} rows={3} /></Form.Item>}
      </Form>
    </Modal>

    <Modal
      title={action?.title ?? '确认高风险操作'}
      open={action !== null}
      onCancel={() => !pending && setAction(null)}
      onOk={() => void runAction()}
      okButtonProps={{ disabled: !reasonDetail.trim(), danger: Boolean(action && ['decline_offer', 'withdraw_offer', 'expire_offer', 'withdraw_application', 'cancel_process'].includes(action.key)) }}
      confirmLoading={pending}
      okText="确认并写入审计"
      cancelText="取消"
    >
      <Alert message="后端仍会再次校验 confirmed、受控原因、对象版本和当前状态；弹窗本身不是安全边界。" showIcon type="warning" />
      <Input.TextArea aria-label="操作具体说明" value={reasonDetail} onChange={event => setReasonDetail(event.target.value)} placeholder="请填写已核实的具体原因或说明" rows={4} maxLength={1000} showCount />
    </Modal>
  </>;
};

export default OfferPipelinePanel;
