import assert from 'node:assert/strict';
import axios from 'axios';
import { createServer } from 'vite';


const draft = {
  schema_version: '1.0',
  basic_info: {
    name: '测试候选人',
    phone: null,
    email: 'candidate@example.com',
    gender: null,
    age: null,
    location: '上海',
    current_company: null,
    current_title: null,
    work_years: 3,
    education_level: '本科',
  },
  education_records: [{
    school: '测试大学',
    degree: '本科',
    major: '计算机',
    start_date: '2019',
    end_date: '2023',
  }],
  work_experiences: [],
  project_experiences: [{
    project_name: '招聘助手',
    role: null,
    start_date: null,
    end_date: null,
    description: null,
    tech_stack: ['TypeScript'],
    achievements: null,
  }],
  skills: ['Python', 'TypeScript'],
  certifications: [],
  self_evaluation: null,
  warnings: [],
  missing_fields: [],
};

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { parseResumeStructureError, summarizeResumeDraft } = await server.ssrLoadModule(
    '/src/stage3/resumeStructureState.ts',
  );

  assert.deepEqual(summarizeResumeDraft(draft), {
    basicInfo: 5,
    education: 1,
    work: 0,
    projects: 1,
    skills: 2,
  });

  const conflict = new axios.AxiosError('conflict', 'ERR_BAD_RESPONSE', undefined, undefined, {
    status: 409,
    statusText: 'Conflict',
    data: { detail: '该简历正在进行结构化识别' },
    headers: {},
    config: { headers: {} },
  });
  assert.deepEqual(parseResumeStructureError(conflict), {
    status: 'failed',
    message: '该简历正在进行结构化识别',
    httpStatus: 409,
  });

  const previousDraft = {
    resume_id: 32,
    structure_status: 'failed',
    structure_error: '模型调用超时',
    from_cache: true,
    has_previous_draft: true,
    draft,
    detail: '模型调用超时',
  };
  const failedRefresh = new axios.AxiosError('timeout', 'ERR_BAD_RESPONSE', undefined, undefined, {
    status: 504,
    statusText: 'Gateway Timeout',
    data: { detail: previousDraft },
    headers: {},
    config: { headers: {} },
  });
  assert.deepEqual(parseResumeStructureError(failedRefresh), {
    status: 'failed',
    message: '模型调用超时',
    httpStatus: 504,
    previousResult: previousDraft,
  });

  const timeout = new axios.AxiosError('timeout', 'ECONNABORTED');
  assert.equal(
    parseResumeStructureError(timeout).message,
    'AI 识别请求超时，你仍然可以继续手动填写',
  );

  assert.deepEqual(parseResumeStructureError(new Error('本地测试错误')), {
    status: 'failed',
    message: '本地测试错误',
  });

  console.log('STAGE3_RESUME_STRUCTURE_STATE_TEST_OK');
} finally {
  await server.close();
}
