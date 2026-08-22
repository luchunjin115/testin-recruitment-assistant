import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';


const apiJob = {
  id: 8,
  title: 'AI 应用工程师',
  department: '研发部',
  location: '长沙',
  employment_type: 'full_time',
  headcount: 2,
  job_background: '建设 AI 应用平台',
  job_responsibilities: '1. 负责应用设计\n- 完成交付',
  candidate_requirements: '具备后端开发经验',
  preferred_qualifications: '有 RAG 项目经验',
  public_notes: '候选人可提前准备项目介绍',
  status: 'draft',
  created_at: '2026-08-21T08:00:00Z',
  updated_at: '2026-08-21T09:00:00Z',
};
const input = {
  title: apiJob.title,
  department: apiJob.department,
  location: apiJob.location,
  employment_type: apiJob.employment_type,
  headcount: apiJob.headcount,
  job_background: apiJob.job_background,
  job_responsibilities: apiJob.job_responsibilities,
  candidate_requirements: apiJob.candidate_requirements,
  preferred_qualifications: apiJob.preferred_qualifications,
  public_notes: apiJob.public_notes,
};

let server;
let jobsService;
let requests;


before(async () => {
  server = await createServer({
    appType: 'custom',
    configFile: false,
    logLevel: 'silent',
    root: process.cwd(),
    server: { middlewareMode: true },
  });
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  jobsService = await server.ssrLoadModule('/src/features/recruitment/services/jobs.ts');
  requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    const data = config.url === '/candidates'
      ? []
      : config.method === 'get' ? [apiJob] : apiJob;
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };
});


after(async () => {
  await server.close();
});


test('Job 响应映射完整保留五段式字段和内部换行', async () => {
  const snapshot = await jobsService.getRecruitmentJobs();
  const job = snapshot.items[0];

  assert.equal(job.jobBackground, apiJob.job_background);
  assert.equal(job.jobResponsibilities, apiJob.job_responsibilities);
  assert.equal(job.candidateRequirements, apiJob.candidate_requirements);
  assert.equal(job.preferredQualifications, apiJob.preferred_qualifications);
  assert.equal(job.publicNotes, apiJob.public_notes);
});


test('创建和更新请求只发送五段式 JD 字段', async () => {
  requests.length = 0;
  await jobsService.createRecruitmentJob({ ...input, status: 'draft' });
  await jobsService.updateRecruitmentJob(8, input);

  const bodies = requests.map(request => JSON.parse(request.data));
  assert.deepEqual(bodies, [{ ...input, status: 'draft' }, input]);
  for (const body of bodies) {
    assert.equal('description' in body, false);
    assert.equal('requirements' in body, false);
    assert.equal('legacy_requirements' in body, false);
  }
});


test('开放错误字段可定位到职责和任职要求文本框', () => {
  const parsed = jobsService.getRecruitmentJobApiError({
    isAxiosError: true,
    response: {
      status: 422,
      data: {
        detail: {
          code: 'JOB_OPEN_VALIDATION_FAILED',
          message: '岗位信息不完整，暂时不能开放',
          fields: ['job_responsibilities', 'candidate_requirements'],
        },
      },
    },
  });

  assert.deepEqual(parsed.fields, ['job_responsibilities', 'candidate_requirements']);
});
