import React, { useCallback, useEffect, useState } from 'react';
import {
  CalendarOutlined,
  ClockCircleOutlined,
  InboxOutlined,
  ReloadOutlined,
  RobotOutlined,
  SolutionOutlined,
  TeamOutlined,
  UploadOutlined,
  UserAddOutlined,
} from '@ant-design/icons';
import { Alert, Avatar, Button, Empty, Skeleton } from 'antd';
import { Link } from 'react-router-dom';
import { DashboardSnapshot, getRecruitmentDashboardSnapshot } from './services/dashboard';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: DashboardSnapshot };

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}).format(new Date(value));

const RecruitmentDashboard: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });

  const loadDashboard = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      const data = await getRecruitmentDashboardSnapshot();
      setLoadState({ status: 'ready', data });
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法连接新版后端接口',
      });
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="工作台数据加载中" className="recruitment-main">
        <section className="recruitment-welcome"><Skeleton active paragraph={{ rows: 2 }} title={{ width: '36%' }} /></section>
        <section className="recruitment-stat-grid">
          {[0, 1, 2, 3].map(item => (
            <article className="recruitment-stat-card" key={item}><Skeleton active paragraph={false} /></article>
          ))}
        </section>
        <section className="recruitment-state-panel"><Skeleton active paragraph={{ rows: 5 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="recruitment-main">
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadDashboard()}>重新加载</Button>}
          className="recruitment-dashboard-alert"
          description={`请确认 FastAPI 已启动，且 /api/v2 可访问。技术信息：${loadState.message}`}
          message="新版工作台数据加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const stats = [
    { label: '开放岗位', value: data.openJobs, note: '来自新版岗位表', icon: <SolutionOutlined />, tone: 'blue' },
    { label: '候选人', value: data.candidateCount, note: 'PostgreSQL 真实记录', icon: <TeamOutlined />, tone: 'green' },
    { label: '待 HR 决策', value: data.pendingReview, note: '有效且尚未决定的 Application', icon: <InboxOutlined />, tone: 'orange' },
    { label: '待跟进', value: '—', note: '新版跟进规则待接入', icon: <ClockCircleOutlined />, tone: 'red' },
  ];

  return (
    <main className="recruitment-main">
      <section className="recruitment-welcome">
        <div>
          <span className="recruitment-section-kicker">今日概览 · 数据来源 /api/v2</span>
          <h2>招聘工作概览</h2>
          <p>
            {data.candidateCount === 0
              ? '新版候选人库暂无记录；页面不会填充演示数据。'
              : `${data.pendingReview} 份 Application 等待 HR 决策。`}
          </p>
        </div>
        <div className="recruitment-welcome-actions">
          <Button disabled icon={<UserAddOutlined />}>新增候选人 · 后续</Button>
          <Button disabled icon={<UploadOutlined />} type="primary">上传简历 · 阶段 4</Button>
        </div>
      </section>

      <section aria-label="新版招聘统计" className="recruitment-stat-grid">
        {stats.map(stat => (
          <article className="recruitment-stat-card" key={stat.label}>
            <div className={`recruitment-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="recruitment-stat-content">
              <span>{stat.label}</span>
              <strong>{stat.value}</strong>
              <small>{stat.note}</small>
            </div>
          </article>
        ))}
      </section>

      <section className="recruitment-content-grid">
        <article className="recruitment-panel recruitment-candidates-panel">
          <div className="recruitment-panel-header">
            <div>
              <h3>最新候选人</h3>
              <p>最近更新的真实候选人记录</p>
            </div>
            <Link className="recruitment-panel-link" to="/app/candidates">查看全部候选人</Link>
          </div>
          {data.recentCandidates.length === 0 ? (
            <Empty
              className="recruitment-panel-empty recruitment-dashboard-candidate-empty"
              description={
                <div className="recruitment-empty-copy">
                  <strong>暂无新版候选人记录</strong>
                  <span>页面已连接候选人接口，没有填充样板演示数据。</span>
                </div>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <div aria-label="最新候选人" className="recruitment-table" role="table">
              <div className="recruitment-table-head recruitment-dashboard-table-columns" role="row">
                <span>候选人</span><span>应聘岗位</span><span>来源</span><span>更新时间</span>
              </div>
              {data.recentCandidates.map(candidate => (
                  <div className="recruitment-table-row recruitment-dashboard-table-columns" key={candidate.id} role="row">
                    <div className="recruitment-candidate-cell">
                      <Avatar className="recruitment-candidate-avatar is-blue">{candidate.name.slice(0, 1)}</Avatar>
                      <div><Link className="recruitment-candidate-name-link" to={`/app/candidates/${candidate.id}`}>{candidate.name}</Link><span>{candidate.source}</span></div>
                    </div>
                    <span className="recruitment-role-cell">{candidate.role}</span>
                    <span>{candidate.source}</span>
                    <span className="recruitment-time-cell">{formatDateTime(candidate.updatedAt)}</span>
                  </div>
              ))}
            </div>
          )}
        </article>

        <aside className="recruitment-right-column">
          <article className="recruitment-panel recruitment-task-panel">
            <div className="recruitment-panel-header">
              <div><h3>今日待办</h3><p>新版待办模型尚未接入</p></div>
              <Button aria-label="待办日历尚未开放" className="recruitment-icon-button is-small" disabled icon={<CalendarOutlined />} />
            </div>
            <Empty
              className="recruitment-panel-empty is-compact recruitment-dashboard-task-empty"
              description={
                <div className="recruitment-empty-copy">
                  <strong>暂无可用的待办数据</strong>
                  <span>跟进规则和任务模型将在后续阶段接入。</span>
                </div>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </article>

          <article className="recruitment-ai-card">
            <span className="recruitment-ai-icon"><RobotOutlined /></span>
            <div>
              <span>AI 招聘助手</span>
              <h3>智能助手尚未接入</h3>
              <p>该能力属于后续阶段，目前不展示模拟对话或虚构结果。</p>
              <Button disabled type="link">开始对话 · 后续阶段</Button>
            </div>
          </article>
        </aside>
      </section>
    </main>
  );
};

export default RecruitmentDashboard;
