import assert from 'node:assert/strict';
import { createServer } from 'vite';


const successPayload = {
  resume_id: 32,
  structure_status: 'succeeded',
  structure_error: null,
  from_cache: false,
  has_previous_draft: false,
  performance: {
    total_ms: 1350,
    preparation_ms: 30,
    model_ms: 1250,
    validation_ms: 10,
    persistence_ms: 40,
  },
  draft: {
    schema_version: '1.0',
    basic_info: {
      name: '测试候选人',
      phone: null,
      email: null,
      gender: null,
      age: null,
      location: '上海',
      current_company: null,
      current_title: null,
      work_years: null,
      education_level: '本科',
    },
    education_records: [],
    work_experiences: [],
    project_experiences: [],
    skills: ['Python'],
    certifications: [],
    self_evaluation: null,
    warnings: [],
    missing_fields: [],
  },
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
  const { structureStage3Resume } = await server.ssrLoadModule(
    '/src/stage3/services/resumes.ts',
  );
  const requests = [];

  v2Http.defaults.adapter = async config => {
    requests.push(config);
    return {
      config,
      data: successPayload,
      headers: {},
      status: 200,
      statusText: 'OK',
    };
  };

  const first = await structureStage3Resume(32);
  const forced = await structureStage3Resume(32, true);

  assert.deepEqual(first, successPayload);
  assert.deepEqual(forced, successPayload);
  assert.equal(requests.length, 2);
  assert.equal(requests[0].method, 'post');
  assert.equal(requests[0].url, '/resumes/32/structure');
  assert.equal(requests[0].timeout, 100_000);
  assert.deepEqual(JSON.parse(requests[0].data), { force: false });
  assert.deepEqual(JSON.parse(requests[1].data), { force: true });

  const originalError = new Error('模拟结构化接口失败');
  v2Http.defaults.adapter = async () => Promise.reject(originalError);

  await assert.rejects(
    structureStage3Resume(32),
    error => error === originalError,
  );

  console.log('STAGE3_RESUME_STRUCTURE_SERVICE_TEST_OK');
} finally {
  await server.close();
}
