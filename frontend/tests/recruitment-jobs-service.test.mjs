import assert from 'node:assert/strict';
import { createServer } from 'vite';


const job = {
  id: 8,
  title: '前端工程师',
  department: '研发部',
  location: '上海',
  employment_type: 'full_time',
  headcount: 2,
  job_background: '建设新一代招聘平台',
  job_responsibilities: '1. 负责招聘平台前端\n2. 保障交付质量',
  candidate_requirements: '- 熟悉 React\n- 具备协作意识',
  preferred_qualifications: '熟悉 TypeScript',
  public_notes: '面试安排将通过邮件通知',
  status: 'draft',
  created_at: '2026-08-15T08:00:00Z',
  updated_at: '2026-08-15T09:00:00Z',
};

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const jobsService = await server.ssrLoadModule('/src/features/recruitment/services/jobs.ts');
  const requests = [];

  v2Http.defaults.adapter = async config => {
    requests.push(config);
    if (config.url === '/candidates') {
      return {
        config,
        data: [{ id: 3, applied_job_id: 8 }],
        headers: {},
        status: 200,
        statusText: 'OK',
      };
    }
    if (config.method === 'delete') {
      return {
        config,
        data: undefined,
        headers: {},
        status: 204,
        statusText: 'No Content',
      };
    }
    return {
      config,
      data: config.method === 'get' ? [job] : job,
      headers: {},
      status: config.method === 'post' && config.url === '/jobs' ? 201 : 200,
      statusText: 'OK',
    };
  };

  const snapshot = await jobsService.getRecruitmentJobs();
  assert.equal(snapshot.total, 1);
  assert.equal(snapshot.draftCount, 1);
  assert.equal(snapshot.openCount, 0);
  assert.equal(snapshot.items[0].candidateCount, 1);
  assert.equal(snapshot.items[0].jobBackground, '建设新一代招聘平台');
  assert.equal(snapshot.items[0].jobResponsibilities, '1. 负责招聘平台前端\n2. 保障交付质量');
  assert.equal(snapshot.items[0].candidateRequirements, '- 熟悉 React\n- 具备协作意识');
  assert.equal(snapshot.items[0].preferredQualifications, '熟悉 TypeScript');
  assert.equal(snapshot.items[0].publicNotes, '面试安排将通过邮件通知');

  const input = {
    title: '前端工程师',
    department: '研发部',
    location: '上海',
    employment_type: 'full_time',
    headcount: 2,
    job_background: '建设新一代招聘平台',
    job_responsibilities: '1. 负责招聘平台前端\n2. 保障交付质量',
    candidate_requirements: '- 熟悉 React\n- 具备协作意识',
    preferred_qualifications: '熟悉 TypeScript',
    public_notes: '面试安排将通过邮件通知',
  };
  await jobsService.createRecruitmentJob({ ...input, status: 'draft' });
  await jobsService.updateRecruitmentJob(8, input);
  await jobsService.openRecruitmentJob(8);
  await jobsService.closeRecruitmentJob(8);
  await jobsService.reopenRecruitmentJob(8);
  await jobsService.deleteRecruitmentJob(8);

  const writeRequests = requests.filter(request => request.url !== '/candidates');
  assert.deepEqual(
    writeRequests.slice(1).map(request => [request.method, request.url]),
    [
      ['post', '/jobs'],
      ['put', '/jobs/8'],
      ['post', '/jobs/8/open'],
      ['post', '/jobs/8/close'],
      ['post', '/jobs/8/reopen'],
      ['delete', '/jobs/8'],
    ],
  );
  assert.deepEqual(JSON.parse(writeRequests[1].data), { ...input, status: 'draft' });
  assert.deepEqual(JSON.parse(writeRequests[2].data), input);

  const parsed = jobsService.getRecruitmentJobApiError({
    isAxiosError: true,
    response: {
      status: 422,
      data: {
        detail: {
          code: 'JOB_OPEN_VALIDATION_FAILED',
          message: '岗位信息不完整，暂时不能开放',
          fields: ['location', 'job_responsibilities', 'candidate_requirements'],
        },
      },
    },
  });
  assert.equal(parsed.code, 'JOB_OPEN_VALIDATION_FAILED');
  assert.deepEqual(parsed.fields, ['location', 'job_responsibilities', 'candidate_requirements']);

  console.log('RECRUITMENT_JOBS_SERVICE_TEST_OK');
} finally {
  await server.close();
}
