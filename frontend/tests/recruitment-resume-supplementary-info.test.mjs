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
    buildResumeSkillCandidates,
    buildResumeSupplementaryInfo,
    mergeConfirmedResumeSkills,
  } = await server.ssrLoadModule('/src/features/recruitment/resumeSupplementaryInfo.ts');

  const skillCandidates = buildResumeSkillCandidates([
    ' Python ',
    'FastAPI',
    'Python',
    '',
    'python',
  ]);
  assert.deepEqual(skillCandidates.map(candidate => candidate.value), [
    'Python',
    'FastAPI',
    'python',
  ]);
  assert.equal(
    skillCandidates[0].key,
    buildResumeSkillCandidates(['Python'])[0].key,
  );

  const mergedSkills = mergeConfirmedResumeSkills(
    ['人工标签', 'Python'],
    skillCandidates,
    [skillCandidates[0].key, skillCandidates[1].key],
  );
  assert.deepEqual(mergedSkills, ['人工标签', 'Python', 'FastAPI']);

  const supplementary = buildResumeSupplementaryInfo({
    schema_version: '1.0',
    basic_info: {
      name: null,
      phone: null,
      email: null,
      gender: null,
      age: null,
      location: null,
      current_company: null,
      current_title: null,
      work_years: null,
      education_level: null,
    },
    education_records: [],
    work_experiences: [],
    project_experiences: [],
    skills: [],
    certifications: [' PMP ', 'PMP', '<script>alert(1)</script>'],
    self_evaluation: '  注重工程质量  ',
    warnings: ['日期存在歧义', '日期存在歧义'],
    missing_fields: ['basic_info.phone'],
  });
  assert.deepEqual(supplementary.certifications, ['PMP', '<script>alert(1)</script>']);
  assert.equal(supplementary.selfEvaluation, '注重工程质量');
  assert.deepEqual(supplementary.warnings, ['日期存在歧义']);
  assert.equal('missingFields' in supplementary, false);
  assert.equal(supplementary.hasContent, true);

  const missingOnlySupplementary = buildResumeSupplementaryInfo({
    schema_version: '1.0',
    basic_info: {
      name: null,
      phone: null,
      email: null,
      gender: null,
      age: null,
      location: null,
      current_company: null,
      current_title: null,
      work_years: null,
      education_level: null,
    },
    education_records: [],
    work_experiences: [],
    project_experiences: [],
    skills: [],
    certifications: [],
    self_evaluation: null,
    warnings: [],
    missing_fields: ['basic_info.phone'],
  });
  assert.equal(missingOnlySupplementary.hasContent, false);

  const emptySupplementary = buildResumeSupplementaryInfo({
    schema_version: '1.0',
    basic_info: {
      name: null,
      phone: null,
      email: null,
      gender: null,
      age: null,
      location: null,
      current_company: null,
      current_title: null,
      work_years: null,
      education_level: null,
    },
    education_records: [],
    work_experiences: [],
    project_experiences: [],
    skills: [],
    certifications: [],
    self_evaluation: null,
    warnings: [],
    missing_fields: [],
  });
  assert.equal(emptySupplementary.hasContent, false);

  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const { createRecruitmentCandidate } = await server.ssrLoadModule(
    '/src/features/recruitment/services/candidates.ts',
  );
  let candidateRequest;
  v2Http.defaults.adapter = async config => {
    candidateRequest = config;
    return {
      config,
      data: { id: 88, name: '技能候选人' },
      headers: {},
      status: 201,
      statusText: 'Created',
    };
  };
  await createRecruitmentCandidate({
    name: '技能候选人',
    tags: [' Python ', 'FastAPI', 'Python', ''],
  });
  const candidatePayload = JSON.parse(candidateRequest.data);
  assert.deepEqual(candidatePayload.tags, ['Python', 'FastAPI']);
  assert.equal('certifications' in candidatePayload, false);
  assert.equal('self_evaluation' in candidatePayload, false);
  assert.equal('warnings' in candidatePayload, false);
  assert.equal('missing_fields' in candidatePayload, false);

  console.log('RECRUITMENT_RESUME_SUPPLEMENTARY_INFO_TEST_OK');
} finally {
  await server.close();
}
