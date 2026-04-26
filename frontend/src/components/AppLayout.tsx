import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, FloatButton } from 'antd';
import {
  DashboardOutlined,
  FormOutlined,
  TeamOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SolutionOutlined,
} from '@ant-design/icons';
import CopilotChat from './CopilotChat';

const { Header, Sider, Content } = Layout;

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: '数据看板' },
    { key: '/form', icon: <FormOutlined />, label: '新增候选人' },
    { key: '/jobs', icon: <SolutionOutlined />, label: '岗位管理' },
    { key: '/ai-screening', icon: <SafetyCertificateOutlined />, label: 'AI初筛中心' },
    { key: '/candidates', icon: <TeamOutlined />, label: '候选人列表' },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} theme="dark">
        <div style={{
          height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontSize: collapsed ? 14 : 18, fontWeight: 'bold',
          whiteSpace: 'nowrap', overflow: 'hidden', padding: '0 8px',
        }}>
          {collapsed ? '测' : 'Testin云测招聘助手'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff', padding: '0 24px', display: 'flex',
          alignItems: 'center', justifyContent: 'space-between',
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
        }}>
          <h2 style={{ margin: 0, fontSize: 18, color: '#1677ff' }}>Testin云测招聘助手</h2>
          <span style={{ color: '#999', fontSize: 13 }}>Powered by AI | 智能招聘管理平台</span>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8, minHeight: 360 }}>
          <Outlet />
        </Content>
      </Layout>
      <FloatButton
        icon={<RobotOutlined />}
        type="primary"
        tooltip="HR Copilot"
        onClick={() => setChatOpen(true)}
        style={{ right: 24, bottom: 24, width: 48, height: 48 }}
      />
      <CopilotChat open={chatOpen} onClose={() => setChatOpen(false)} />
    </Layout>
  );
};

export default AppLayout;
