import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Alert, Button, Drawer, Empty, Skeleton, Tag } from 'antd';
import {
  getAIScreeningApiError,
  getJobEvaluationPlan,
} from './services/aiScreening';
import type { RecruitmentJob } from './services/jobs';
import {
  CATEGORY_LABELS,
  PLAN_STATUS_META,
  PRIORITY_LABELS,
  shouldApplyScreeningResponse,
} from './screeningPresentation';
import type { JobEvaluationPlan } from './types/aiScreening';

type LoadState =
  | { status: 'idle' | 'loading' }
  | { status: 'empty' }
  | { status: 'error'; message: string; code: string | null }
  | { status: 'ready'; plan: JobEvaluationPlan };

type Props = {
  job: RecruitmentJob | null;
  open: boolean;
  onClose: () => void;
};

const formatDateTime = (value: string | null) => {
  if (!value) return '尚未完成';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date);
};

const JobEvaluationPlanDrawer: React.FC<Props> = ({ job, open, onClose }) => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'idle' });
  const requestIdRef = useRef(0);

  const load = useCallback(async () => {
    if (!job || !open) return;
    const requestId = ++requestIdRef.current;
    setLoadState({ status: 'loading' });
    try {
      const plan = await getJobEvaluationPlan(job.id);
      if (shouldApplyScreeningResponse(requestId, requestIdRef.current)) {
        setLoadState({ status: 'ready', plan });
      }
    } catch (error) {
      if (!shouldApplyScreeningResponse(requestId, requestIdRef.current)) return;
      const parsed = getAIScreeningApiError(error);
      if (parsed.status === 404 || parsed.code === 'JOB_EVALUATION_PLAN_NOT_FOUND') {
        setLoadState({ status: 'empty' });
      } else {
        setLoadState({ status: 'error', message: parsed.message, code: parsed.code });
      }
    }
  }, [job, open]);

  useEffect(() => {
    if (open) void load();
    return () => { requestIdRef.current += 1; };
  }, [load, open]);

  const plan = loadState.status === 'ready' ? loadState.plan : null;

  return (
    <Drawer
      className="recruitment-plan-drawer"
      destroyOnClose
      extra={<Button aria-label="刷新评价计划" icon={<ReloadOutlined />} onClick={() => void load()} />}
      onClose={onClose}
      open={open}
      title={job ? `${job.title} · AI 评价计划` : 'AI 评价计划'}
      width="min(760px, 100vw)"
    >
      <Alert
        description="评价计划只把当前 JD 整理为统一的基础评价事项，不包含权重、淘汰阈值，也不是 HR 决策规则。发现内容不准确时，请修改原 JD。"
        icon={<SafetyCertificateOutlined />}
        message="AI 初筛的只读评价依据"
        showIcon
        type="info"
      />

      {loadState.status === 'loading' && (
        <div className="recruitment-plan-loading"><Skeleton active paragraph={{ rows: 8 }} /></div>
      )}

      {loadState.status === 'error' && (
        <Alert
          className="recruitment-plan-state"
          description={loadState.message}
          message={loadState.code ? `评价计划读取失败 · ${loadState.code}` : '评价计划读取失败'}
          showIcon
          type="error"
        />
      )}

      {loadState.status === 'empty' && (
        <Alert
          className="recruitment-plan-state"
          description="阶段 7 正在适配新的五段式 JD；当前不会生成或重新生成评价计划，也不会调用 AI。历史评价计划仍可只读查看。"
          message="五段式评价计划升级中"
          showIcon
          type="warning"
        />
      )}

      {plan && (
        <div className="recruitment-plan-content">
          <section className="recruitment-plan-summary">
            <div>
              <span>当前状态</span>
              <Tag color={PLAN_STATUS_META[plan.status].tone}>{PLAN_STATUS_META[plan.status].label}</Tag>
              <p>{PLAN_STATUS_META[plan.status].description}</p>
            </div>
            <div><span>评价事项</span><strong>{plan.items.length}</strong><p>最多 30 项</p></div>
            <div><span>计划版本</span><strong>Schema {plan.schemaVersion}</strong><p>更新于 {formatDateTime(plan.updatedAt)}</p></div>
          </section>

          {plan.contractOutdated && plan.status === 'ready' && (
            <Alert
              description="该历史计划仅用于解释已有结果；五段式评价计划设计确认前不会重新生成，也不能用于新申请。"
              message="当前评价计划使用旧规则"
              showIcon
              type="warning"
            />
          )}

          {plan.warnings.includes('limited_basis') && (
            <Alert
              description="当前 JD 只形成了 1—4 项明确要求，报告仍可生成，但 HR 应注意评价依据有限。"
              message="评价依据有限"
              showIcon
              type="warning"
            />
          )}

          {plan.status === 'failed' && (
            <Alert
              description={`${plan.errorMessage || '历史评价计划未能生成。'} 五段式评价计划设计确认前不会重新生成。`}
              message={plan.errorCode ? `生成失败 · ${plan.errorCode}` : '生成失败'}
              showIcon
              type="error"
            />
          )}

          {plan.status === 'outdated' && (
            <Alert
              description="旧计划继续用于解释已有历史结果，但不能用于当前 JD 的新申请。"
              message="这份计划基于旧 JD"
              showIcon
              type="warning"
            />
          )}

          {plan.items.length > 0 ? (
            <section className="recruitment-plan-items" aria-label="岗位评价事项">
              <div className="recruitment-plan-section-heading">
                <div><span>评价清单</span><h3>AI 将按这些岗位事实逐项评价</h3></div>
                <span>{plan.structuredCoverage.allCovered ? '结构化字段已完整覆盖' : '结构化字段待检查'}</span>
              </div>
              {plan.items.map((item, index) => (
                <article className="recruitment-plan-item" key={item.key}>
                  <span className="recruitment-plan-index">{String(index + 1).padStart(2, '0')}</span>
                  <div>
                    <div className="recruitment-plan-item-title">
                      <h4>{item.title}</h4>
                      <Tag>{CATEGORY_LABELS[item.category]}</Tag>
                      <Tag color={item.priority === 'required' ? 'red' : item.priority === 'preferred' ? 'gold' : 'default'}>
                        {PRIORITY_LABELS[item.priority]}
                      </Tag>
                    </div>
                    <p>{item.sourceType === 'structured'
                      ? `来自结构化 JD 字段：${item.sourceField || '字段未记录'}`
                      : `来自 JD 原文：${item.sourceQuote || '原文依据未记录'}`}</p>
                    <code>{item.key}</code>
                  </div>
                </article>
              ))}
            </section>
          ) : plan.status !== 'failed' && (
            <Empty description="当前计划还没有可展示的评价事项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}

          <footer className="recruitment-plan-meta">
            <span>生成完成：{formatDateTime(plan.completedAt)}</span>
            <span>Prompt {plan.promptVersion} · 模型 {plan.modelVersion}</span>
          </footer>
        </div>
      )}
    </Drawer>
  );
};

export default JobEvaluationPlanDrawer;
