import React, { useState } from 'react';
import {
  AppstoreOutlined,
  BellOutlined,
  FileTextOutlined,
  InboxOutlined,
  MenuOutlined,
  MoreOutlined,
  RobotOutlined,
  SearchOutlined,
  SettingOutlined,
  SolutionOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Avatar, Button, Drawer, Input, Tag } from 'antd';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import './styles/index.css';

const navItems = [
  { icon: <AppstoreOutlined />, label: '工作台', path: '/stage3/dashboard' },
  { icon: <InboxOutlined />, label: '简历管理', path: '/stage3/resumes' },
  { icon: <TeamOutlined />, label: '候选人', path: '/stage3/candidates' },
  { icon: <SolutionOutlined />, label: '岗位管理', path: '/stage3/jobs' },
  { icon: <RobotOutlined />, label: 'AI 初筛', path: '/stage3/screening' },
  { icon: <FileTextOutlined />, label: '初筛报告', path: '/stage3/reports' },
];

type NavigationProps = {
  onNavigate?: () => void;
};

const Navigation: React.FC<NavigationProps> = ({ onNavigate }) => (
  <nav className="s3-nav" aria-label="新版主导航">
    <p className="s3-nav-label">工作空间</p>
    {navItems.map(item => item.path ? (
      <NavLink
        className={({ isActive }) => `s3-nav-item${isActive ? ' is-active' : ''}`}
        key={item.label}
        onClick={onNavigate}
        to={item.path}
      >
        {item.icon}
        <span>{item.label}</span>
      </NavLink>
    ) : (
      <button
        aria-disabled="true"
        className="s3-nav-item is-disabled"
        disabled
        key={item.label}
        title="将在阶段 3 后续小步骤中开放"
        type="button"
      >
        {item.icon}
        <span>{item.label}</span>
        <Tag bordered={false} className="s3-nav-coming">后续</Tag>
      </button>
    ))}
  </nav>
);

const Brand: React.FC = () => (
  <div className="s3-brand">
    <span className="s3-brand-mark">H</span>
    <div>
      <strong>HR Agent</strong>
      <span>智能招聘工作台</span>
    </div>
  </div>
);

const SidebarFooter: React.FC = () => (
  <div className="s3-sidebar-footer">
    <button aria-disabled="true" className="s3-nav-item is-disabled" disabled type="button">
      <SettingOutlined />
      <span>系统设置</span>
    </button>
    <div className="s3-profile">
      <Avatar size={34} className="s3-profile-avatar">HR</Avatar>
      <div>
        <strong>当前用户</strong>
        <span>身份功能待接入</span>
      </div>
      <MoreOutlined />
    </div>
  </div>
);

const Stage3Layout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const isCandidateCreate = location.pathname === '/stage3/candidates/new';
  const isCandidateDetail = !isCandidateCreate
    && /^\/stage3\/candidates\/[^/]+$/.test(location.pathname);
  const pageTitle = location.pathname.startsWith('/stage3/resumes')
    ? '简历管理'
    : location.pathname.startsWith('/stage3/reports')
      ? '初筛报告'
    : location.pathname.startsWith('/stage3/screening')
      ? 'AI 初筛'
    : location.pathname.startsWith('/stage3/jobs')
      ? '岗位管理'
    : isCandidateCreate
      ? '新增候选人'
    : isCandidateDetail
      ? '候选人详情'
      : location.pathname.startsWith('/stage3/candidates')
      ? '候选人'
      : '工作台';
  const today = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date());

  return (
    <div className="s3-shell">
      <aside className="s3-sidebar">
        <Brand />
        <Navigation />
        <SidebarFooter />
      </aside>

      <div className="s3-workspace">
        <header className="s3-topbar">
          <div className="s3-topbar-left">
            <Button
              aria-label="打开导航"
              className="s3-icon-button s3-mobile-menu-button"
              icon={<MenuOutlined />}
              onClick={() => setMobileMenuOpen(true)}
            />
            <div>
              <p className="s3-eyebrow">{today}</p>
              <h1>{pageTitle}</h1>
            </div>
          </div>
          <div className="s3-topbar-actions">
            <Input
              aria-label="全局搜索尚未开放"
              className="s3-search"
              disabled
              prefix={<SearchOutlined />}
              placeholder="搜索功能将在后续接入"
            />
            <Button
              aria-label="通知功能尚未开放"
              className="s3-icon-button"
              disabled
              icon={<BellOutlined />}
            />
          </div>
        </header>
        <Outlet />
      </div>

      <Drawer
        className="s3-mobile-drawer"
        onClose={() => setMobileMenuOpen(false)}
        open={mobileMenuOpen}
        placement="left"
        title={<Brand />}
        width={280}
      >
        <Navigation onNavigate={() => setMobileMenuOpen(false)} />
        <SidebarFooter />
      </Drawer>
    </div>
  );
};

export default Stage3Layout;
