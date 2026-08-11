import React, { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { appTheme } from './theme';
import './App.css';

const AppLayout = lazy(() => import('./components/AppLayout'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const CandidateForm = lazy(() => import('./pages/CandidateForm'));
const CandidateList = lazy(() => import('./pages/CandidateList'));
const CandidateDetail = lazy(() => import('./pages/CandidateDetail'));
const AIScreeningCenter = lazy(() => import('./pages/AIScreeningCenter'));
const ApplyForm = lazy(() => import('./pages/ApplyForm'));
const JobManagement = lazy(() => import('./pages/JobManagement'));
const Stage3Preview = lazy(() => import('./pages/Stage3Preview'));
const Stage3Dashboard = lazy(() => import('./stage3/Stage3Dashboard'));
const Stage3Layout = lazy(() => import('./stage3/Stage3Layout'));
const Stage3ResumeList = lazy(() => import('./stage3/Stage3ResumeList'));
const Stage3CandidateList = lazy(() => import('./stage3/Stage3CandidateList'));
const Stage3CandidateCreate = lazy(() => import('./stage3/Stage3CandidateCreate'));
const Stage3CandidateDetail = lazy(() => import('./stage3/Stage3CandidateDetail'));
const Stage3JobList = lazy(() => import('./stage3/Stage3JobList'));
const Stage3ScreeningCenter = lazy(() => import('./stage3/Stage3ScreeningCenter'));
const Stage3ReportCenter = lazy(() => import('./stage3/Stage3ReportCenter'));
const Stage3ApplicationForm = lazy(() => import('./stage3/Stage3ApplicationForm'));

const RouteLoading: React.FC = () => (
  <div aria-live="polite" className="app-route-loading" role="status">
    <span aria-hidden="true" className="app-route-loading-indicator" />
    <span>页面加载中...</span>
  </div>
);

const withRouteLoading = (element: React.ReactNode) => (
  <Suspense fallback={<RouteLoading />}>
    {element}
  </Suspense>
);

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={appTheme}
    >
      <Routes>
        <Route path="/apply" element={withRouteLoading(<ApplyForm />)} />
        <Route path="/stage3/apply" element={withRouteLoading(<Stage3ApplicationForm />)} />
        <Route path="/stage3-preview" element={withRouteLoading(<Stage3Preview />)} />
        <Route path="/stage3" element={withRouteLoading(<Stage3Layout />)}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={withRouteLoading(<Stage3Dashboard />)} />
          <Route path="resumes" element={withRouteLoading(<Stage3ResumeList />)} />
          <Route path="candidates" element={withRouteLoading(<Stage3CandidateList />)} />
          <Route path="candidates/new" element={withRouteLoading(<Stage3CandidateCreate />)} />
          <Route path="candidates/:id" element={withRouteLoading(<Stage3CandidateDetail />)} />
          <Route path="jobs" element={withRouteLoading(<Stage3JobList />)} />
          <Route path="screening" element={withRouteLoading(<Stage3ScreeningCenter />)} />
          <Route path="reports" element={withRouteLoading(<Stage3ReportCenter />)} />
        </Route>
        <Route path="/" element={withRouteLoading(<AppLayout />)}>
          <Route index element={withRouteLoading(<Dashboard />)} />
          <Route path="dashboard" element={withRouteLoading(<Dashboard />)} />
          <Route path="form" element={withRouteLoading(<CandidateForm />)} />
          <Route path="upload" element={<Navigate to="/form" replace />} />
          <Route path="ai-screening" element={withRouteLoading(<AIScreeningCenter />)} />
          <Route path="jobs" element={withRouteLoading(<JobManagement />)} />
          <Route path="candidates" element={withRouteLoading(<CandidateList />)} />
          <Route path="candidates/:id" element={withRouteLoading(<CandidateDetail />)} />
        </Route>
      </Routes>
    </ConfigProvider>
  );
};

export default App;
