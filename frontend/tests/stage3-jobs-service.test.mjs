import assert from 'node:assert/strict';
import { createServer } from 'vite';


const requirements = {
  schema_version: '1.0',
  responsibilities: ['负责岗位管理'],
  required_skills: ['React'],
  preferred_skills: ['TypeScript'],
  minimum_work_years: 1,
  education_requirement: 'bachelor_or_above',
  required_experiences: [],
  preferred_experiences: [],
  keywords: ['招聘'],
  additional_requirements: [],
};

const job = {
  id: 8,
  title: '前端工程师',
  department: '研发部',
  location: '上海',
  employment_type: 'full_time',
  headcount: 2,
  description: '负责招聘平台前端',
  requirements,
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
  const jobsService = await server.ssrLoadModule('/src/stage3/services/jobs.ts');
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

  const snapshot = await jobsService.getStage3Jobs();
  assert.equal(snapshot.total, 1);
  assert.equal(snapshot.draftCount, 1);
  assert.equal(snapshot.openCount, 0);
  assert.equal(snapshot.items[0].candidateCount, 1);
  assert.deepEqual(snapshot.items[0].requirements, requirements);

  const input = {
    title: '前端工程师',
    department: '研发部',
    location: '上海',
    employment_type: 'full_time',
    headcount: 2,
    description: '负责招聘平台前端',
    requirements,
  };
  await jobsService.createStage3Job({ ...input, status: 'draft' });
  await jobsService.updateStage3Job(8, input);
  await jobsService.openStage3Job(8);
  await jobsService.closeStage3Job(8);
  await jobsService.reopenStage3Job(8);
  await jobsService.deleteStage3Job(8);

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

  const parsed = jobsService.getStage3JobApiError({
    isAxiosError: true,
    response: {
      status: 422,
      data: {
        detail: {
          code: 'JOB_OPEN_VALIDATION_FAILED',
          message: '岗位信息不完整，暂时不能开放',
          fields: ['location', 'requirements.required_skills'],
        },
      },
    },
  });
  assert.equal(parsed.code, 'JOB_OPEN_VALIDATION_FAILED');
  assert.deepEqual(parsed.fields, ['location', 'requirements.required_skills']);

  console.log('STAGE3_JOBS_SERVICE_TEST_OK');
} finally {
  await server.close();
}
