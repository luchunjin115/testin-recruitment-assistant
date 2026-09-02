import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const jobs = [
  { id: 1, title: '开放岗位', department: '研发部', location: '上海',
    employment_type: 'full_time', headcount: 2, job_background: '开放岗位背景',
    job_responsibilities: '负责业务系统开发', candidate_requirements: '熟悉 React',
    preferred_qualifications: null, public_notes: '候选人可见说明',
    status: 'open', created_at: '2026-08-15T08:00:00Z', updated_at: '2026-08-15T09:00:00Z' },
  { id: 2, title: '历史关闭岗位', department: '产品部', location: '北京',
    employment_type: 'full_time', headcount: 1, job_background: '关闭岗位背景',
    job_responsibilities: '负责历史产品', candidate_requirements: '具备产品经验',
    preferred_qualifications: null, public_notes: null,
    status: 'closed', created_at: '2026-08-14T08:00:00Z', updated_at: '2026-08-14T09:00:00Z' },
];
const publicJobs = [{
  id: jobs[0].id,
  title: jobs[0].title,
  department: jobs[0].department,
  location: jobs[0].location,
  employment_type: jobs[0].employment_type,
  job_background: jobs[0].job_background,
  job_responsibilities: jobs[0].job_responsibilities,
  candidate_requirements: jobs[0].candidate_requirements,
  preferred_qualifications: jobs[0].preferred_qualifications,
  public_notes: jobs[0].public_notes,
}];
const candidates = [{
  id: 5, name: '历史候选人', email: null, phone: null, current_company: null,
  work_years: 3, education_level: '本科', source: '内推', status: 'screening',
  applied_job_id: 2, current_title: '产品经理', resume_file_path: null,
  created_at: '2026-08-15T08:00:00Z', updated_at: '2026-08-15T09:00:00Z',
}];
const passedApplications = [{
  id: 12, candidate_id: 5, job_id: 2, current_resume_id: 6, source: 'hr_direct',
  lifecycle_status: 'active', recruitment_stage: 'screening_passed', hr_decision: 'passed',
  applied_at: '2026-08-15T08:00:00Z', created_at: '2026-08-15T08:00:00Z',
  updated_at: '2026-08-15T09:00:00Z',
}];
const server = await createServer({
  appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const application = await server.ssrLoadModule('/src/features/recruitment/services/application.ts');
  const candidate = await server.ssrLoadModule('/src/features/recruitment/services/candidates.ts');
  const dashboard = await server.ssrLoadModule('/src/features/recruitment/services/dashboard.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    let data = [];
    if (config.url === '/public/jobs') data = publicJobs;
    if (config.url === '/jobs') data = config.params?.status === 'open' ? [jobs[0]] : jobs;
    if (config.url === '/candidates') data = candidates;
    if (config.url === '/applications') data = passedApplications;
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };
  const applicationJobs = await application.getRecruitmentApplicationJobs();
  assert.deepEqual(applicationJobs.map(job => job.id), [1]);
  assert.equal(applicationJobs[0].jobResponsibilities, '负责业务系统开发');
  assert.equal(applicationJobs[0].candidateRequirements, '熟悉 React');
  assert.equal(requests[0].url, '/public/jobs');
  assert.equal(requests[0].params, undefined);
  assert.deepEqual((await candidate.getRecruitmentCandidateJobs()).map(job => job.id), [1]);
  const candidateSnapshot = await candidate.getRecruitmentCandidates();
  assert.equal(candidateSnapshot.items[0].jobTitle, '历史关闭岗位');
  assert.equal(candidateSnapshot.items[0].applicationId, 12);
  const dashboardSnapshot = await dashboard.getRecruitmentDashboardSnapshot();
  assert.equal(dashboardSnapshot.openJobs, 1);
  assert.equal(dashboardSnapshot.pendingReview, 1);
  assert.equal(dashboardSnapshot.recentCandidates[0].role, '历史关闭岗位');
  assert.equal(requests.some(request => request.url === '/screening-results'), false);

  const screeningSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url), 'utf8',
  );
  assert.ok(screeningSource.includes('历史关闭岗位') || screeningSource.includes('jobStatus'));
  console.log('RECRUITMENT_JOB_READ_BOUNDARIES_TEST_OK');
} finally {
  await server.close();
}
