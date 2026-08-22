import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';


const jobListSource = await readFile(
  new URL('../src/features/recruitment/RecruitmentJobList.tsx', import.meta.url),
  'utf8',
);
const jobsServiceSource = await readFile(
  new URL('../src/features/recruitment/services/jobs.ts', import.meta.url),
  'utf8',
);
const applicationServiceSource = await readFile(
  new URL('../src/features/recruitment/services/application.ts', import.meta.url),
  'utf8',
);

const sections = [
  ['岗位背景', 'jobBackground', 5000],
  ['岗位职责', 'jobResponsibilities', 10000],
  ['任职要求', 'candidateRequirements', 10000],
  ['加分项', 'preferredQualifications', 5000],
  ['备注', 'publicNotes', 5000],
];


for (const [label, name, limit] of sections) {
  test(`岗位表单使用大型普通文本框：${label}`, () => {
    const itemPattern = new RegExp(
      `<Form\\.Item[^>]*label="${label}"[^>]*name="${name}"[\\s\\S]*?` +
      `<Input\\.TextArea[^>]*autoSize=\\{\\{ minRows: 6, maxRows: [0-9]+ \\}\\}[^>]*`,
    );
    assert.match(jobListSource, itemPattern);
    assert.match(jobListSource, new RegExp(`name="${name}"[\\s\\S]*?max:\\s*${limit}`));
  });
}


test('岗位职责和任职要求定位为开放必填字段', () => {
  assert.match(jobListSource, /job_responsibilities:\s*'jobResponsibilities'/);
  assert.match(jobListSource, /candidate_requirements:\s*'candidateRequirements'/);
  assert.match(jobListSource, /岗位职责[\s\S]*开放岗位时必填/);
  assert.match(jobListSource, /任职要求[\s\S]*开放岗位时必填/);
});


test('备注明确候选人可见且页面不使用 HTML 渲染', () => {
  assert.ok(jobListSource.includes('候选人可见，请勿填写内部招聘信息'));
  assert.equal(jobListSource.includes('dangerouslySetInnerHTML'), false);
});


test('旧细分 JD 控件和旧字段映射退出岗位页面', () => {
  for (const legacyText of [
    '岗位描述', '必备技能', '加分技能', '最低工作年限', '学历要求',
    '必备经历', '加分经历', '岗位关键词', '其他要求',
  ]) {
    assert.equal(jobListSource.includes(legacyText), false, `仍存在旧控件：${legacyText}`);
  }
  for (const legacyName of [
    'name="description"', 'name="requiredSkills"', 'name="preferredSkills"',
    'name="minimumWorkYears"', 'name="educationRequirement"',
    'name="requiredExperiences"', 'name="preferredExperiences"',
    'name="keywords"', 'name="additionalRequirements"',
  ]) {
    assert.equal(jobListSource.includes(legacyName), false, `仍存在旧字段映射：${legacyName}`);
  }
});


test('列表摘要和搜索只依赖五段式普通文本', () => {
  assert.ok(jobListSource.includes("item.jobResponsibilities || '岗位职责未填写'"));
  for (const field of [
    'jobBackground', 'jobResponsibilities', 'candidateRequirements',
    'preferredQualifications', 'publicNotes',
  ]) {
    assert.ok(jobListSource.includes(`item.${field}`), `搜索或摘要缺少 ${field}`);
  }
  assert.equal(jobListSource.includes('item.requirements.'), false);
  assert.equal(jobListSource.includes('item.description'), false);
});


test('前端 Job 类型和现有申请读取方使用五段式合同', () => {
  for (const field of [
    'job_background', 'job_responsibilities', 'candidate_requirements',
    'preferred_qualifications', 'public_notes',
  ]) {
    assert.ok(jobsServiceSource.includes(field), `Job API 类型缺少 ${field}`);
    assert.ok(applicationServiceSource.includes(field), `Application 岗位读取缺少 ${field}`);
  }
  assert.equal(jobsServiceSource.includes('JobRequirementsV1'), false);
  assert.equal(applicationServiceSource.includes('JobRequirementsV1'), false);
  assert.equal(applicationServiceSource.includes('job.requirements'), false);
});
