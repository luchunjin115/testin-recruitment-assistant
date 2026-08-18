import React, { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { appTheme } from './theme';
import './App.css';

const RecruitmentDashboard = lazy(() => import('./features/recruitment/RecruitmentDashboard'));
const RecruitmentLayout = lazy(() => import('./features/recruitment/RecruitmentLayout'));
const RecruitmentResumeList = lazy(() => import('./features/recruitment/RecruitmentResumeList'));
const RecruitmentCandidateList = lazy(() => import('./features/recruitment/RecruitmentCandidateList'));
const RecruitmentCandidateCreate = lazy(() => import('./features/recruitment/RecruitmentCandidateCreate'));
const RecruitmentCandidateDetail = lazy(() => import('./features/recruitment/RecruitmentCandidateDetail'));
const RecruitmentJobList = lazy(() => import('./features/recruitment/RecruitmentJobList'));
const RecruitmentScreeningCenter = lazy(() => import('./features/recruitment/RecruitmentScreeningCenter'));
const RecruitmentReportCenter = lazy(() => import('./features/recruitment/RecruitmentReportCenter'));
const RecruitmentApplicationForm = lazy(() => import('./features/recruitment/RecruitmentApplicationForm'));

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
        <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
        <Route path="/apply" element={withRouteLoading(<RecruitmentApplicationForm />)} />
        <Route path="/app" element={withRouteLoading(<RecruitmentLayout />)}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={withRouteLoading(<RecruitmentDashboard />)} />
          <Route path="resumes" element={withRouteLoading(<RecruitmentResumeList />)} />
          <Route path="candidates" element={withRouteLoading(<RecruitmentCandidateList />)} />
          <Route path="candidates/new" element={withRouteLoading(<RecruitmentCandidateCreate />)} />
          <Route path="candidates/:id" element={withRouteLoading(<RecruitmentCandidateDetail />)} />
          <Route path="jobs" element={withRouteLoading(<RecruitmentJobList />)} />
          <Route path="screening" element={withRouteLoading(<RecruitmentScreeningCenter />)} />
          <Route path="reports" element={withRouteLoading(<RecruitmentReportCenter />)} />
        </Route>
        <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
      </Routes>
    </ConfigProvider>
  );
};

export default App;
