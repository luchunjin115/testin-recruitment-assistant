import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';


const createSource = await readFile(
  new URL('../src/features/recruitment/RecruitmentCandidateCreate.tsx', import.meta.url),
  'utf8',
);
const candidateService = await readFile(
  new URL('../src/features/recruitment/services/candidates.ts', import.meta.url),
  'utf8',
);
const candidateList = await readFile(
  new URL('../src/features/recruitment/RecruitmentCandidateList.tsx', import.meta.url),
  'utf8',
);
const styles = await readFile(
  new URL('../src/features/recruitment/styles/candidate-create.css', import.meta.url),
  'utf8',
);

for (const text of [
  '阶段 7 · HR 人工直通',
  '这是人工通过入口，不是 AI 自动录用',
  '我已核对岗位和候选人资料，并确认 HR 人工通过',
  '确认人工通过并保存 Application',
  '系统保存完整申请和阶段历史',
]) {
  assert.ok(createSource.includes(text), `缺少 HR 人工直通确认文案：${text}`);
}

assert.match(createSource, /name="phone"[\s\S]*?required:\s*true/);
assert.match(createSource, /name="email"[\s\S]*?required:\s*true/);
assert.match(createSource, /name="appliedJobId"[\s\S]*?required:\s*true/);
assert.ok(createSource.includes('!attachedResume'), '没有简历时必须禁止正式创建 Application');

for (const contract of [
  "source: 'hr_direct'",
  'confirm_hr_pass: true',
  'resume_profile:',
  'intakeStage7Application',
]) {
  assert.ok(candidateService.includes(contract), `HR 直通服务缺少合同：${contract}`);
}

assert.equal(candidateService.includes('runStage7ApplicationScreening'), false);
assert.equal(candidateService.includes('screeningStatus'), false);
assert.ok(createSource.includes('Application 已安全保存'));
assert.ok(createSource.includes("navigate('/app/candidates')"));
assert.ok(candidateList.includes("navigate('/app/candidates/new')"));
assert.equal(candidateList.includes('新增候选人 · 待升级'), false);

assert.match(styles, /\.recruitment-candidate-direct-mark\s*\{[^}]*border:[^;]*#b8e3d0;[^}]*background:\s*#f1fbf6;/s);
assert.match(styles, /\.recruitment-candidate-pass-confirmation\s*\{/);

console.log('STAGE7_HR_DIRECT_CANDIDATE_UI_TEST_OK');
