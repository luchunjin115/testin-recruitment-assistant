import assert from 'node:assert/strict';
import { createServer } from 'vite';

const server = await createServer({
  appType: 'custom',
  configFile: false,
  logLevel: 'silent',
  root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const {
    buildEducationCandidates,
    buildProjectCandidates,
    buildWorkCandidates,
  } = await server.ssrLoadModule('/src/features/recruitment/resumeExperienceImport.ts');

  const educationDraft = {
    school: '示例大学',
    degree: '本科',
    major: '软件工程',
    start_date: '2017-09',
    end_date: '2021-06',
  };
  const education = buildEducationCandidates([educationDraft])[0];
  assert.deepEqual(education.formValue, {
    aiCandidateKey: education.key,
    school: '示例大学',
    degree: '本科',
    major: '软件工程',
    startDate: '2017-09',
    endDate: '2021-06',
  });
  assert.equal('is985' in education.formValue, false);
  assert.equal('is211' in education.formValue, false);
  assert.equal(education.key, buildEducationCandidates([educationDraft])[0].key);

  const work = buildWorkCandidates([{
    company: '示例科技',
    title: '测试工程师',
    start_date: '2021-07',
    end_date: '至今',
    description: '负责自动化测试平台建设',
    tech_stack: ['Python', 'Playwright'],
  }])[0];
  assert.deepEqual(work.formValue, {
    aiCandidateKey: work.key,
    company: '示例科技',
    title: '测试工程师',
    startDate: '2021-07',
    endDate: '至今',
    description: '负责自动化测试平台建设',
    techStack: 'Python、Playwright',
  });
  assert.deepEqual(work.tags, ['Python', 'Playwright']);

  const project = buildProjectCandidates([{
    project_name: '招聘助手',
    role: null,
    start_date: null,
    end_date: null,
    description: null,
    tech_stack: [],
    achievements: '处理效率提升 40%',
  }])[0];
  assert.deepEqual(project.formValue, {
    aiCandidateKey: project.key,
    projectName: '招聘助手',
    role: undefined,
    startDate: undefined,
    endDate: undefined,
    description: undefined,
    techStack: undefined,
    achievements: '处理效率提升 40%',
  });
  assert.deepEqual(project.details, ['成果：处理效率提升 40%']);
  assert.equal(project.key.startsWith('project:'), true);

  console.log('RECRUITMENT_RESUME_EXPERIENCE_IMPORT_TEST_OK');
} finally {
  await server.close();
}
