import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/AppLayout';
import { appTheme } from './theme';
import Dashboard from './pages/Dashboard';
import CandidateForm from './pages/CandidateForm';
import CandidateList from './pages/CandidateList';
import CandidateDetail from './pages/CandidateDetail';
import AIScreeningCenter from './pages/AIScreeningCenter';
import ApplyForm from './pages/ApplyForm';
import JobManagement from './pages/JobManagement';
import Stage3Preview from './pages/Stage3Preview';
import Stage3Dashboard from './stage3/Stage3Dashboard';
import Stage3Layout from './stage3/Stage3Layout';
import Stage3ResumeList from './stage3/Stage3ResumeList';
import Stage3CandidateList from './stage3/Stage3CandidateList';
import Stage3CandidateDetail from './stage3/Stage3CandidateDetail';
import Stage3JobList from './stage3/Stage3JobList';
import Stage3ScreeningCenter from './stage3/Stage3ScreeningCenter';
import Stage3ReportCenter from './stage3/Stage3ReportCenter';
import Stage3ApplicationForm from './stage3/Stage3ApplicationForm';
import './App.css';

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={appTheme}
    >
      <Routes>
        <Route path="/apply" element={<ApplyForm />} />
        <Route path="/stage3/apply" element={<Stage3ApplicationForm />} />
        <Route path="/stage3-preview" element={<Stage3Preview />} />
        <Route path="/stage3" element={<Stage3Layout />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Stage3Dashboard />} />
          <Route path="resumes" element={<Stage3ResumeList />} />
          <Route path="candidates" element={<Stage3CandidateList />} />
          <Route path="candidates/:id" element={<Stage3CandidateDetail />} />
          <Route path="jobs" element={<Stage3JobList />} />
          <Route path="screening" element={<Stage3ScreeningCenter />} />
          <Route path="reports" element={<Stage3ReportCenter />} />
        </Route>
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
