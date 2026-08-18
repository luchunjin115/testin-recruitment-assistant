import assert from 'node:assert/strict';
import { createServer } from 'vite';

const basicInfo = {
  name: 'AI 姓名',
  phone: '13800000000',
  email: 'candidate@example.com',
  gender: '女',
  age: 28,
  location: '上海',
  current_company: '示例科技',
  current_title: '测试工程师',
  work_years: 5,
  education_level: '本科',
};

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const {
    areResumeFieldValuesEqual,
    isEmptyResumeFormValue,
    mergeResumeBasicInfo,
  } = await server.ssrLoadModule('/src/features/recruitment/resumeDraftMerge.ts');

  assert.equal(isEmptyResumeFormValue(undefined), true);
  assert.equal(isEmptyResumeFormValue(null), true);
  assert.equal(isEmptyResumeFormValue('   '), true);
  assert.equal(isEmptyResumeFormValue(0), false);
  assert.equal(areResumeFieldValuesEqual(' AI 姓名 ', 'AI 姓名'), true);

  const merged = mergeResumeBasicInfo({
    name: '人工姓名',
    phone: '   ',
    age: 0,
    location: '上海',
    source: '内推',
    appliedJobId: 12,
  }, basicInfo);

  assert.deepEqual(merged.fillValues, {
    phone: '13800000000',
    email: 'candidate@example.com',
    gender: '女',
    currentCompany: '示例科技',
    currentTitle: '测试工程师',
    workYears: 5,
    educationLevel: '本科',
  });
  assert.deepEqual(merged.filledFields, [
    'phone',
    'email',
    'gender',
    'currentCompany',
    'currentTitle',
    'workYears',
    'educationLevel',
  ]);
  assert.deepEqual(merged.matchingFields, ['location']);
  assert.deepEqual(merged.conflicts, {
    name: { currentValue: '人工姓名', aiValue: 'AI 姓名' },
    age: { currentValue: 0, aiValue: 28 },
  });
  assert.equal('source' in merged.fillValues, false);
  assert.equal('appliedJobId' in merged.fillValues, false);

  const missingAiValues = mergeResumeBasicInfo({}, {
    ...basicInfo,
    name: null,
    phone: '   ',
    age: null,
  });
  assert.equal('name' in missingAiValues.fillValues, false);
  assert.equal('phone' in missingAiValues.fillValues, false);
  assert.equal('age' in missingAiValues.fillValues, false);

  console.log('RECRUITMENT_RESUME_DRAFT_MERGE_TEST_OK');
} finally {
  await server.close();
}
