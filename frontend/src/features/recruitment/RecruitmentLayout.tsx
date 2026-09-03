import React, { useState } from 'react';
import {
  AppstoreOutlined,
  BellOutlined,
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
  { icon: <AppstoreOutlined />, label: '工作台', path: '/app/dashboard' },
  { icon: <TeamOutlined />, label: '候选人', path: '/app/candidates' },
  { icon: <SolutionOutlined />, label: '岗位管理', path: '/app/jobs' },
  { icon: <RobotOutlined />, label: 'AI 初筛中心', path: '/app/screening' },
];

type NavigationProps = {
  onNavigate?: () => void;
};

const Navigation: React.FC<NavigationProps> = ({ onNavigate }) => (
  <nav className="recruitment-nav" aria-label="新版主导航">
    <p className="recruitment-nav-label">工作空间</p>
    {navItems.map(item => item.path ? (
      <NavLink
        className={({ isActive }) => `recruitment-nav-item${isActive ? ' is-active' : ''}`}
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
        className="recruitment-nav-item is-disabled"
        disabled
        key={item.label}
        title="将在阶段 3 后续小步骤中开放"
        type="button"
      >
        {item.icon}
        <span>{item.label}</span>
        <Tag bordered={false} className="recruitment-nav-coming">后续</Tag>
      </button>
    ))}
  </nav>
);

const Brand: React.FC = () => (
  <div className="recruitment-brand">
    <span className="recruitment-brand-mark">H</span>
    <div>
      <strong>HR Agent</strong>
      <span>智能招聘工作台</span>
    </div>
  </div>
);

const SidebarFooter: React.FC = () => (
  <div className="recruitment-sidebar-footer">
    <button aria-disabled="true" className="recruitment-nav-item is-disabled" disabled type="button">
      <SettingOutlined />
      <span>系统设置</span>
    </button>
    <div className="recruitment-profile">
      <Avatar size={34} className="recruitment-profile-avatar">HR</Avatar>
      <div>
        <strong>当前用户</strong>
        <span>身份功能待接入</span>
      </div>
      <MoreOutlined />
    </div>
  </div>
);

const RecruitmentLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const isCandidateCreate = location.pathname === '/app/candidates/new';
  const isCandidateDetail = !isCandidateCreate
    && /^\/app\/candidates\/[^/]+$/.test(location.pathname);
  const pageTitle = location.pathname.startsWith('/app/screening')
      ? 'AI 初筛中心'
    : location.pathname.startsWith('/app/jobs')
      ? '岗位管理'
    : isCandidateCreate
      ? '新增候选人'
    : isCandidateDetail
      ? '候选人详情'
      : location.pathname.startsWith('/app/candidates')
      ? '候选人'
      : '工作台';
  const today = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date());

  return (
    <div className="recruitment-shell">
      <aside className="recruitment-sidebar">
        <Brand />
        <Navigation />
        <SidebarFooter />
      </aside>

      <div className="recruitment-workspace">
        <header className="recruitment-topbar">
          <div className="recruitment-topbar-left">
            <Button
              aria-label="打开导航"
              className="recruitment-icon-button recruitment-mobile-menu-button"
              icon={<MenuOutlined />}
              onClick={() => setMobileMenuOpen(true)}
            />
            <div>
              <p className="recruitment-eyebrow">{today}</p>
              <h1>{pageTitle}</h1>
            </div>
          </div>
          <div className="recruitment-topbar-actions">
            <Input
              aria-label="全局搜索尚未开放"
              className="recruitment-search"
              disabled
              prefix={<SearchOutlined />}
              placeholder="搜索功能将在后续接入"
            />
            <Button
              aria-label="通知功能尚未开放"
              className="recruitment-icon-button"
              disabled
              icon={<BellOutlined />}
            />
          </div>
        </header>
        <Outlet />
      </div>

      <Drawer
        className="recruitment-mobile-drawer"
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

export default RecruitmentLayout;
