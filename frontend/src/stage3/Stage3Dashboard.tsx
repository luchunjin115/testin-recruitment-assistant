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
import { Alert, Avatar, Button, Empty, Progress, Skeleton, Tag } from 'antd';
import { Link } from 'react-router-dom';
import { DashboardSnapshot, getStage3DashboardSnapshot } from './services/dashboard';

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

const getScreeningMeta = (score: number | null, recommendation: string | null) => {
  if (score === null) return { label: '待初筛', tone: 'neutral' };
  if (recommendation) {
    const tone = score >= 80 ? 'success' : score >= 60 ? 'warning' : 'neutral';
    return { label: recommendation, tone };
  }
  if (score >= 80) return { label: '建议推进', tone: 'success' };
  if (score >= 60) return { label: '需要复核', tone: 'warning' };
  return { label: '关注风险', tone: 'neutral' };
};

const Stage3Dashboard: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });

  const loadDashboard = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      const data = await getStage3DashboardSnapshot();
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
      <main aria-busy="true" aria-label="工作台数据加载中" className="s3-main">
        <section className="s3-welcome"><Skeleton active paragraph={{ rows: 2 }} title={{ width: '36%' }} /></section>
        <section className="s3-stat-grid">
          {[0, 1, 2, 3].map(item => (
            <article className="s3-stat-card" key={item}><Skeleton active paragraph={false} /></article>
          ))}
        </section>
        <section className="s3-state-panel"><Skeleton active paragraph={{ rows: 5 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="s3-main">
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadDashboard()}>重新加载</Button>}
          className="s3-dashboard-alert"
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
    { label: '待初筛', value: data.pendingScreening, note: '尚未生成筛选结果', icon: <InboxOutlined />, tone: 'orange' },
    { label: '待跟进', value: '—', note: '新版跟进规则待接入', icon: <ClockCircleOutlined />, tone: 'red' },
  ];

  return (
    <main className="s3-main">
      <section className="s3-welcome">
        <div>
          <span className="s3-section-kicker">今日概览 · 数据来源 /api/v2</span>
          <h2>招聘工作概览</h2>
          <p>
            {data.candidateCount === 0
              ? '新版候选人库暂无记录；页面不会填充演示数据。'
              : `${data.pendingScreening} 位候选人尚未生成初筛结果。`}
          </p>
        </div>
        <div className="s3-welcome-actions">
          <Button disabled icon={<UserAddOutlined />}>新增候选人 · 后续</Button>
          <Button disabled icon={<UploadOutlined />} type="primary">上传简历 · 阶段 4</Button>
        </div>
      </section>

      <section aria-label="新版招聘统计" className="s3-stat-grid">
        {stats.map(stat => (
          <article className="s3-stat-card" key={stat.label}>
            <div className={`s3-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="s3-stat-content">
              <span>{stat.label}</span>
              <strong>{stat.value}</strong>
              <small>{stat.note}</small>
            </div>
          </article>
        ))}
      </section>

      <section className="s3-content-grid">
        <article className="s3-panel s3-candidates-panel">
          <div className="s3-panel-header">
            <div>
              <h3>最新候选人</h3>
              <p>最近更新的候选人与真实初筛结果</p>
            </div>
            <Link className="s3-panel-link" to="/stage3/candidates">查看全部候选人</Link>
          </div>
          {data.recentCandidates.length === 0 ? (
            <Empty
              className="s3-panel-empty s3-dashboard-candidate-empty"
              description={
                <div className="s3-empty-copy">
                  <strong>暂无新版候选人记录</strong>
                  <span>页面已连接候选人和筛选结果接口，没有填充样板演示数据。</span>
                </div>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <div aria-label="最新候选人" className="s3-table" role="table">
              <div className="s3-table-head s3-dashboard-table-columns" role="row">
                <span>候选人</span><span>应聘岗位</span><span>AI 匹配</span><span>状态</span><span>更新时间</span>
              </div>
              {data.recentCandidates.map(candidate => {
                const meta = getScreeningMeta(candidate.score, candidate.recommendation);
                return (
                  <div className="s3-table-row s3-dashboard-table-columns" key={candidate.id} role="row">
                    <div className="s3-candidate-cell">
                      <Avatar className="s3-candidate-avatar is-blue">{candidate.name.slice(0, 1)}</Avatar>
                      <div><Link className="s3-candidate-name-link" to={`/stage3/candidates/${candidate.id}`}>{candidate.name}</Link><span>{candidate.source}</span></div>
                    </div>
                    <span className="s3-role-cell">{candidate.role}</span>
                    <div className="s3-score-cell">
                      <strong>{candidate.score ?? '—'}</strong>
                      {candidate.score === null ? (
                        <span className="s3-score-pending">待初筛</span>
                      ) : (
                        <Progress
                          percent={candidate.score}
                          showInfo={false}
                          size="small"
                          strokeColor={candidate.score >= 80 ? '#3f6fd9' : '#8b96a8'}
                          trailColor="#edf0f4"
                        />
                      )}
                    </div>
                    <div><Tag bordered={false} className={`s3-status-tag is-${meta.tone}`}>{meta.label}</Tag></div>
                    <span className="s3-time-cell">{formatDateTime(candidate.updatedAt)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </article>

        <aside className="s3-right-column">
          <article className="s3-panel s3-task-panel">
            <div className="s3-panel-header">
              <div><h3>今日待办</h3><p>新版待办模型尚未接入</p></div>
              <Button aria-label="待办日历尚未开放" className="s3-icon-button is-small" disabled icon={<CalendarOutlined />} />
            </div>
            <Empty
              className="s3-panel-empty is-compact s3-dashboard-task-empty"
              description={
                <div className="s3-empty-copy">
                  <strong>暂无可用的待办数据</strong>
                  <span>跟进规则和任务模型将在后续阶段接入。</span>
                </div>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </article>

          <article className="s3-ai-card">
            <span className="s3-ai-icon"><RobotOutlined /></span>
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

export default Stage3Dashboard;
