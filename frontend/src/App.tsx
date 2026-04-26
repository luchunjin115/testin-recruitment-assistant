import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/AppLayout';
import Dashboard from './pages/Dashboard';
import CandidateForm from './pages/CandidateForm';
import CandidateList from './pages/CandidateList';
import CandidateDetail from './pages/CandidateDetail';
import AIScreeningCenter from './pages/AIScreeningCenter';
import ApplyForm from './pages/ApplyForm';
import JobManagement from './pages/JobManagement';
import './App.css';

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <Routes>
        <Route path="/apply" element={<ApplyForm />} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="form" element={<CandidateForm />} />
          <Route path="upload" element={<Navigate to="/form" replace />} />
          <Route path="ai-screening" element={<AIScreeningCenter />} />
          <Route path="jobs" element={<JobManagement />} />
          <Route path="candidates" element={<CandidateList />} />
          <Route path="candidates/:id" element={<CandidateDetail />} />
        </Route>
      </Routes>
    </ConfigProvider>
  );
};

export default App;
