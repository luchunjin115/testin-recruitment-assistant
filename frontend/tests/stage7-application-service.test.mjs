import assert from 'node:assert/strict';
import { createServer } from 'vite';

const application = {
  id: 11, candidate_id: 2, job_id: 7, current_resume_id: 5,
  source: 'hr_screening', lifecycle_status: 'active', recruitment_stage: 'hr_review',
  hr_decision: 'pending', applied_at: '2026-08-18T08:00:00Z',
  created_at: '2026-08-18T08:00:00Z', updated_at: '2026-08-18T08:10:00Z',
};
const history = {
  id: 30, application_id: 11, from_recruitment_stage: 'applied',
  to_recruitment_stage: 'hr_review', from_hr_decision: 'pending',
  to_hr_decision: 'passed', reason_code: 'meets_requirements', reason_detail: null,
  actor_type: 'hr', actor_id: null, actor_label: '本地 HR（未认证）',
  created_at: '2026-08-18T08:10:00Z',
};
const server = await createServer({
  appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(),
  server: { middlewareMode: true },
});

try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const service = await server.ssrLoadModule('/src/features/recruitment/services/applications.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    let data;
    if (config.url === '/applications') data = [application];
    else if (config.url === '/applications/intake') data = {
      application, candidate_resolution: 'reused', existing_application_reused: false,
      suspected_duplicate_candidate_ids: [9],
    };
    else if (config.url === '/applications/11/history') data = [history];
    else data = application;
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };

  const applications = await service.listStage7Applications({
    jobId: 7, recruitmentStage: 'hr_review', hrDecision: 'pending', lifecycleStatus: 'active',
  });
  assert.equal(applications[0].candidateId, 2);
  assert.equal('aiStatus' in applications[0], false);
  assert.deepEqual(requests[0].params, {
    job_id: 7, recruitment_stage: 'hr_review', hr_decision: 'pending', lifecycle_status: 'active',
  });
  assert.equal((await service.getStage7Application(11)).hrDecision, 'pending');

  const intakeInput = {
    name: '测试候选人', phone: '13800138000', email: 'candidate@example.com',
    job_id: 7, current_resume_id: 5, source: 'hr_screening', confirm_hr_pass: false,
  };
  const intake = await service.intakeStage7Application(intakeInput);
  assert.equal(intake.candidateResolution, 'reused');
  assert.deepEqual(intake.suspectedDuplicateCandidateIds, [9]);

  await service.passStage7Application(11, { reason_code: 'meets_requirements' });
  await service.backupStage7Application(11, { reason_code: 'waiting_for_comparison' });
  await service.rejectStage7Application(11, { reason_code: 'required_skill_missing', confirmed: true });
  await service.undoStage7ApplicationRejection(11, { reason_code: 'new_evidence', reason_detail: '补充材料' });
  await service.voidStage7Application(11, { reason_code: 'wrong_job', confirmed: true });
  const histories = await service.listStage7ApplicationHistory(11);
  assert.equal(histories[0].reasonCode, 'meets_requirements');
  assert.equal('screeningResultId' in histories[0], false);
  assert.deepEqual(requests.slice(1).map(request => [request.method, request.url]), [
    ['get', '/applications/11'], ['post', '/applications/intake'],
    ['post', '/applications/11/pass'], ['post', '/applications/11/backup'],
    ['post', '/applications/11/reject'], ['post', '/applications/11/undo-rejection'],
    ['post', '/applications/11/void'], ['get', '/applications/11/history'],
  ]);
  assert.deepEqual(JSON.parse(requests[2].data), intakeInput);

  const parsedError = service.getStage7ApplicationApiError({
    isAxiosError: true,
    response: { status: 409, data: { detail: {
      code: 'CONTACT_IDENTITY_CONFLICT', message: '联系方式命中了多个 Candidate',
      candidate_ids: [2, 'invalid'],
    } } },
  });
  assert.equal(parsedError.code, 'CONTACT_IDENTITY_CONFLICT');
  assert.deepEqual(parsedError.candidateIds, [2]);
  console.log('STAGE7_APPLICATION_SERVICE_TEST_OK');
} finally {
  await server.close();
}
