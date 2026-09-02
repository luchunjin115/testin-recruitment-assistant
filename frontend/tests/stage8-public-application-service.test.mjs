import assert from 'node:assert/strict';
import { createServer } from 'vite';


const publicJob = {
  id: 18,
  title: '虚构前端工程师',
  department: '演示研发部',
  location: '长沙',
  employment_type: 'full_time',
  job_background: '建设虚构招聘产品。',
  job_responsibilities: '负责候选人体验。',
  candidate_requirements: '熟悉 React。',
  preferred_qualifications: '重视可访问性。',
  public_notes: '仅使用虚构资料演示。',
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
  const service = await server.ssrLoadModule(
    '/src/features/recruitment/services/application.ts',
  );
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    if (config.method === 'get') {
      return { config, data: [publicJob], headers: {}, status: 200, statusText: 'OK' };
    }
    return {
      config,
      data: {
        submission_reference: 'AP-TEST8D01',
        accepted_at: '2026-09-02T18:00:00+08:00',
        message: '投递已收到，招聘团队会在审核后与合适的候选人联系。',
      },
      headers: {},
      status: 202,
      statusText: 'Accepted',
    };
  };

  const jobs = await service.getRecruitmentApplicationJobs();
  assert.equal(requests[0].url, '/public/jobs');
  assert.equal(requests[0].params, undefined, '公开岗位接口不应携带内部 status 查询');
  assert.deepEqual(jobs[0], {
    id: 18,
    title: '虚构前端工程师',
    department: '演示研发部',
    location: '长沙',
    employmentType: 'full_time',
    jobBackground: '建设虚构招聘产品。',
    jobResponsibilities: '负责候选人体验。',
    candidateRequirements: '熟悉 React。',
    preferredQualifications: '重视可访问性。',
    publicNotes: '仅使用虚构资料演示。',
  });

  const resume = new File(['虚构简历'], 'fictional-resume.txt', { type: 'text/plain' });
  const accepted = await service.submitPublicApplication({
    name: '  虚构候选人  ',
    phone: ' +86 138 0000 8001 ',
    email: ' Fictional@Example.COM ',
    jobId: 18,
    resume,
    idempotencyKey: 'c4444444-4444-4444-8444-444444444444',
  });
  assert.equal(requests[1].url, '/public/applications');
  assert.equal(requests[1].method, 'post');
  const body = requests[1].data;
  assert.ok(body instanceof FormData);
  assert.deepEqual([...body.keys()].sort(), [
    'consent_version',
    'email',
    'idempotency_key',
    'job_id',
    'name',
    'phone',
    'privacy_consent',
    'resume',
  ]);
  assert.equal(body.get('name'), '虚构候选人');
  assert.equal(body.get('email'), 'fictional@example.com');
  assert.equal(body.get('privacy_consent'), 'true');
  assert.equal(body.get('consent_version'), '2026-09-02');
  assert.equal(body.get('resume').name, 'fictional-resume.txt');
  assert.deepEqual(accepted, {
    submissionReference: 'AP-TEST8D01',
    acceptedAt: '2026-09-02T18:00:00+08:00',
    message: '投递已收到，招聘团队会在审核后与合适的候选人联系。',
  });

  const safeError = service.getPublicApplicationApiError({
    isAxiosError: true,
    response: {
      status: 429,
      headers: { 'retry-after': '47' },
      data: { detail: { code: 'PUBLIC_APPLICATION_RATE_LIMITED', message: '提交过于频繁，请稍后重试' } },
    },
  });
  assert.deepEqual(safeError, {
    status: 429,
    code: 'PUBLIC_APPLICATION_RATE_LIMITED',
    message: '提交过于频繁，请稍后重试',
    retryAfterSeconds: 47,
  });
  const hiddenError = service.getPublicApplicationApiError({
    isAxiosError: true,
    response: {
      status: 500,
      headers: {},
      data: { detail: { code: 'DATABASE_CONSTRAINT', message: 'secret/path/resume.txt' } },
    },
  });
  assert.equal(hiddenError.code, null);
  assert.equal(hiddenError.message, '投递暂时未能送达，请检查网络后重试');

  assert.deepEqual(service.PUBLIC_APPLICATION_FILE_EXTENSIONS, ['.pdf', '.docx', '.txt']);
  assert.equal(service.PUBLIC_APPLICATION_MAX_FILE_BYTES, 10 * 1024 * 1024);
  console.log('STAGE8_PUBLIC_APPLICATION_SERVICE_TEST_OK');
} finally {
  await server.close();
}
