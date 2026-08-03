import React from 'react';
import {
  AppstoreOutlined,
  BellOutlined,
  CalendarOutlined,
  CheckCircleFilled,
  ClockCircleOutlined,
  FileTextOutlined,
  InboxOutlined,
  MoreOutlined,
  PlusOutlined,
  RobotOutlined,
  SearchOutlined,
  SettingOutlined,
  SolutionOutlined,
  TeamOutlined,
  UserAddOutlined,
} from '@ant-design/icons';
import { Avatar, Badge, Button, Input, Progress, Tag } from 'antd';
import './Stage3Preview.css';


const navItems = [
  { icon: <AppstoreOutlined />, label: '工作台', active: true },
  { icon: <InboxOutlined />, label: '简历管理' },
  { icon: <TeamOutlined />, label: '候选人' },
  { icon: <SolutionOutlined />, label: '岗位管理' },
  { icon: <RobotOutlined />, label: 'AI 初筛' },
  { icon: <FileTextOutlined />, label: '初筛报告' },
];

const stats = [
  { label: '开放岗位', value: 12, note: '本月新增 3 个', icon: <SolutionOutlined />, tone: 'blue' },
  { label: '候选人', value: 184, note: '较上周 +18', icon: <TeamOutlined />, tone: 'green' },
  { label: '待初筛', value: 26, note: '今日新增 8 份', icon: <InboxOutlined />, tone: 'orange' },
  { label: '待跟进', value: 9, note: '其中 2 人已超时', icon: <ClockCircleOutlined />, tone: 'red' },
];

const candidates = [
  {
    name: '陈雨桐',
    role: '高级后端工程师',
    source: '官网投递',
    score: 92,
    status: '建议推进',
    tone: 'success',
    time: '10 分钟前',
    initials: '陈',
    avatarTone: 'blue',
  },
  {
    name: '周明远',
    role: 'AI 应用工程师',
    source: '员工内推',
    score: 86,
    status: '建议推进',
    tone: 'success',
    time: '32 分钟前',
    initials: '周',
    avatarTone: 'violet',
  },
  {
    name: '林书雅',
    role: '产品经理',
    source: '招聘平台',
    score: 74,
    status: '需要复核',
    tone: 'warning',
    time: '1 小时前',
    initials: '林',
    avatarTone: 'green',
  },
  {
    name: '赵一航',
    role: '前端开发工程师',
    source: '官网投递',
    score: 68,
    status: '关注风险',
    tone: 'neutral',
    time: '2 小时前',
    initials: '赵',
    avatarTone: 'orange',
  },
];

const tasks = [
  { title: '确认陈雨桐的技术面时间', meta: '高级后端工程师 · 今天 14:00', done: false },
  { title: '复核 AI 应用工程师初筛结果', meta: '还有 6 位候选人', done: false },
  { title: '向业务负责人发送候选人报告', meta: '产品经理 · 截止今天', done: false },
  { title: '更新测试开发工程师岗位要求', meta: '已完成', done: true },
];

const Stage3Preview: React.FC = () => {
  return (
    <div className="s3-shell">
      <aside className="s3-sidebar">
        <div className="s3-brand">
          <span className="s3-brand-mark">H</span>
          <div>
            <strong>HR Agent</strong>
            <span>智能招聘工作台</span>
          </div>
        </div>

        <nav className="s3-nav" aria-label="主导航">
          <p className="s3-nav-label">工作空间</p>
          {navItems.map((item) => (
            <button
              className={`s3-nav-item${item.active ? ' is-active' : ''}`}
              key={item.label}
              type="button"
            >
              {item.icon}
              <span>{item.label}</span>
              {item.label === '待初筛' && <span className="s3-nav-count">26</span>}
            </button>
          ))}
        </nav>

        <div className="s3-sidebar-footer">
          <button className="s3-nav-item" type="button">
            <SettingOutlined />
            <span>系统设置</span>
          </button>
          <div className="s3-profile">
            <Avatar size={34} className="s3-profile-avatar">林</Avatar>
            <div>
              <strong>林晓雯</strong>
              <span>招聘负责人</span>
            </div>
            <MoreOutlined />
          </div>
        </div>
      </aside>

      <div className="s3-workspace">
        <header className="s3-topbar">
          <div>
            <p className="s3-eyebrow">2026年8月3日 · 星期一</p>
            <h1>工作台</h1>
          </div>
          <div className="s3-topbar-actions">
            <Input
              className="s3-search"
              prefix={<SearchOutlined />}
              placeholder="搜索候选人、岗位或报告"
              aria-label="全局搜索"
            />
            <Badge dot offset={[-4, 4]}>
              <Button className="s3-icon-button" icon={<BellOutlined />} aria-label="通知" />
            </Badge>
          </div>
        </header>

        <main className="s3-main">
          <section className="s3-welcome">
            <div>
              <span className="s3-section-kicker">今日概览</span>
              <h2>早上好，林经理</h2>
              <p>今天有 8 份新简历等待处理，2 位候选人需要优先跟进。</p>
            </div>
            <div className="s3-welcome-actions">
              <Button icon={<UserAddOutlined />}>新增候选人</Button>
              <Button type="primary" icon={<PlusOutlined />}>上传简历</Button>
            </div>
          </section>

          <section className="s3-stat-grid" aria-label="招聘统计">
            {stats.map((stat) => (
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
                  <p>最近完成解析与初筛的候选人</p>
                </div>
                <Button type="link">查看全部</Button>
              </div>

              <div className="s3-table" role="table" aria-label="最新候选人">
                <div className="s3-table-head" role="row">
                  <span>候选人</span>
                  <span>应聘岗位</span>
                  <span>AI 匹配</span>
                  <span>状态</span>
                  <span>更新时间</span>
                </div>
                {candidates.map((candidate) => (
                  <div className="s3-table-row" role="row" key={candidate.name}>
                    <div className="s3-candidate-cell">
                      <Avatar className={`s3-candidate-avatar is-${candidate.avatarTone}`}>
                        {candidate.initials}
                      </Avatar>
                      <div>
                        <strong>{candidate.name}</strong>
                        <span>{candidate.source}</span>
                      </div>
                    </div>
                    <span className="s3-role-cell">{candidate.role}</span>
                    <div className="s3-score-cell">
                      <strong>{candidate.score}</strong>
                      <Progress
                        percent={candidate.score}
                        showInfo={false}
                        strokeColor={candidate.score >= 80 ? '#3f6fd9' : '#8b96a8'}
                        trailColor="#edf0f4"
                        size="small"
                      />
                    </div>
                    <div>
                      <Tag className={`s3-status-tag is-${candidate.tone}`} bordered={false}>
                        {candidate.status}
                      </Tag>
                    </div>
                    <span className="s3-time-cell">{candidate.time}</span>
                  </div>
                ))}
              </div>
            </article>

            <aside className="s3-right-column">
              <article className="s3-panel s3-task-panel">
                <div className="s3-panel-header">
                  <div>
                    <h3>今日待办</h3>
                    <p>4 项任务 · 1 项已完成</p>
                  </div>
                  <Button className="s3-icon-button is-small" icon={<CalendarOutlined />} />
                </div>
                <div className="s3-task-list">
                  {tasks.map((task) => (
                    <div className={`s3-task${task.done ? ' is-done' : ''}`} key={task.title}>
                      <span className="s3-task-check">
                        {task.done ? <CheckCircleFilled /> : null}
                      </span>
                      <div>
                        <strong>{task.title}</strong>
                        <span>{task.meta}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="s3-ai-card">
                <span className="s3-ai-icon"><RobotOutlined /></span>
                <div>
                  <span>AI 招聘助手</span>
                  <h3>需要我帮你处理什么？</h3>
                  <p>可以尝试：“找出最匹配后端岗位的 5 位候选人”。</p>
                  <Button type="link">开始对话</Button>
                </div>
              </article>
            </aside>
          </section>
        </main>
      </div>
    </div>
  );
};

export default Stage3Preview;
