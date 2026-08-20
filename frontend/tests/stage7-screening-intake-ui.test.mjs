import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';


const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const intake = await server.ssrLoadModule('/src/features/recruitment/screeningIntakeAction.ts');

  assert.deepEqual(
    intake.buildStage7ScreeningIntakeInput({
      name: '  虚构候选人  ',
      phone: ' +86 138-0013-8000 ',
      email: ' TEST.CANDIDATE@EXAMPLE.COM ',
      jobId: 7,
      resumeId: 12,
    }),
    {
      valid: true,
      input: {
        name: '虚构候选人',
        phone: '+86 138-0013-8000',
        email: 'test.candidate@example.com',
        job_id: 7,
        current_resume_id: 12,
        source: 'hr_screening',
        confirm_hr_pass: false,
      },
    },
  );

  for (const [field, draft] of [
    ['name', { name: '', phone: '13800138000', email: 'a@example.com', jobId: 7, resumeId: 12 }],
    ['phone', { name: '测试', phone: '123', email: 'a@example.com', jobId: 7, resumeId: 12 }],
    ['email', { name: '测试', phone: '13800138000', email: 'invalid', jobId: 7, resumeId: 12 }],
    ['jobId', { name: '测试', phone: '13800138000', email: 'a@example.com', jobId: null, resumeId: 12 }],
    ['resumeId', { name: '测试', phone: '13800138000', email: 'a@example.com', jobId: 7, resumeId: null }],
  ]) {
    const result = intake.buildStage7ScreeningIntakeInput(draft);
    assert.equal(result.valid, false);
    assert.equal(result.field, field);
  }

  assert.equal(intake.isStage7IntakeResumeFileSupported('candidate.PDF'), true);
  assert.equal(intake.isStage7IntakeResumeFileSupported('candidate.docx'), true);
  assert.equal(intake.isStage7IntakeResumeFileSupported('candidate.txt'), true);
  assert.equal(intake.isStage7IntakeResumeFileSupported('candidate.exe'), false);

  assert.match(
    intake.getStage7ScreeningIntakeErrorMessage(
      'CONTACT_IDENTITY_CONFLICT',
      'fallback',
      [2, 9],
    ),
    /#2、#9/,
  );
  assert.match(
    intake.getStage7ScreeningIntakeErrorMessage('RESUME_OWNERSHIP_CONFLICT', 'fallback'),
    /绑定其他候选人/,
  );
  assert.match(
    intake.getStage7ScreeningIntakeErrorMessage('JOB_NOT_OPEN_FOR_SCREENING', 'fallback'),
    /开放岗位/,
  );

  const pageSource = await readFile(
    new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url),
    'utf8',
  );
  for (const text of [
    '录入新申请',
    '先保存申请，再由 AI 提供证据',
    'uploadRecruitmentResume',
    'extractRecruitmentResumeText',
    'intakeStage7Application',
    'runStage7ApplicationScreening(applicationId)',
    'existingApplicationReused',
    '失败不会删除已保存申请',
    'intakeGuardRef',
    'source=hr_screening',
  ]) {
    assert.ok(pageSource.includes(text), `录入新申请页面缺少交互边界：${text}`);
  }

  const intakeCall = pageSource.indexOf('intakeStage7Application(buildResult.input)');
  const screeningCall = pageSource.indexOf('runStage7ApplicationScreening(applicationId)');
  assert.ok(intakeCall >= 0 && screeningCall > intakeCall, '必须先保存 Application，再启动 AI 初筛');

  const styles = await readFile(
    new URL('../src/features/recruitment/styles/screening.css', import.meta.url),
    'utf8',
  );
  assert.match(styles, /\.recruitment-intake-rail\s*\{/s);
  assert.match(styles, /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-intake-rail/s);
  assert.match(styles, /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*?\.recruitment-intake-progress/s);

  console.log('STAGE7_SCREENING_INTAKE_UI_TEST_OK');
} finally {
  await server.close();
}
