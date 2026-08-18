import assert from 'node:assert/strict';
import { createServer } from 'vite';


const application = {
  id: 11,
  candidate_id: 2,
  job_id: 7,
  current_resume_id: 5,
  source: 'hr_screening',
  lifecycle_status: 'active',
  recruitment_stage: 'hr_review',
  ai_status: 'completed',
  hr_decision: 'pending',
  current_screening_result_id: 101,
  applied_at: '2026-08-18T08:00:00Z',
  created_at: '2026-08-18T08:00:00Z',
  updated_at: '2026-08-18T08:10:00Z',
};

const screeningSummary = {
  id: 101,
  candidate_id: 2,
  job_id: 7,
  application_id: 11,
  resume_id: 5,
  attempt_number: 2,
  execution_status: 'completed',
  overall_score: 86,
  hard_pass: true,
  recommendation: 'strong_recommend',
  evidence_coverage_rate: '0.8750',
  error_code: null,
  error_message: null,
  started_at: '2026-08-18T08:09:00Z',
  finished_at: '2026-08-18T08:10:00Z',
  duration_ms: 60_000,
  trigger_reason: 'manual_rerun',
  force_rerun: false,
  is_outdated: false,
  outdated_at: null,
  created_at: '2026-08-18T08:09:00Z',
  updated_at: '2026-08-18T08:10:00Z',
};

const screeningDetail = {
  ...screeningSummary,
  input_fingerprint: 'a'.repeat(64),
  skill_score: 90,
  experience_score: 82,
  project_score: 84,
  strengths: ['项目证据充分'],
  risks: [],
  hard_requirement_checks: [{ criterion: 'work_years', status: 'passed' }],
  dimension_scores: { must_have_requirements: { score_percentage: 90 } },
  reason: '岗位相关证据较充分',
  pending_questions: ['确认到岗时间'],
  resume_evidence: [{ source: 'resume_text', quote: 'Python' }],
  job_evidence: [{ requirement: 'Python' }],
  candidate_input_snapshot: { application_ref: 'application-11' },
  resume_snapshot: { resume_id: 5 },
  job_requirements_snapshot: { schema_version: '1.0' },
  rubric_snapshot: { version: 2 },
  rules_version: 'rules:v1;score:v1',
  prompt_version: 'screening_evaluation_v3',
  model_provider: 'deepseek',
  model_name: 'deepseek-v4-flash',
  model_config_version: 'v1',
  job_schema_version: '1.0',
  resume_schema_version: '1.0',
  prompt_tokens: 1000,
  completion_tokens: 500,
  total_tokens: 1500,
  estimated_cost: '0.001200',
  actor_type: 'hr',
  actor_id: null,
  actor_label: '本地 HR（未认证）',
  raw_result: { semantic_evaluation: {} },
};

const history = {
  id: 30,
  application_id: 11,
  from_recruitment_stage: 'applied',
  to_recruitment_stage: 'hr_review',
  from_hr_decision: 'pending',
  to_hr_decision: 'pending',
  reason_code: 'application_created',
  reason_detail: null,
  actor_type: 'system',
  actor_id: null,
  actor_label: 'system',
  screening_result_id: 101,
  overrides_ai_recommendation: false,
  created_at: '2026-08-18T08:10:00Z',
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
  const service = await server.ssrLoadModule('/src/features/recruitment/services/applications.ts');
  const requests = [];

  v2Http.defaults.adapter = async config => {
    requests.push(config);
    let data;
    if (config.url === '/applications' && config.method === 'get') data = [application];
    else if (config.url === '/applications/intake') {
      data = {
        application,
        candidate_resolution: 'reused',
        existing_application_reused: false,
        suspected_duplicate_candidate_ids: [9],
      };
    } else if (config.url === '/applications/11/screenings' && config.method === 'post') {
      data = { result: screeningDetail, reused: false, model_called: true };
    } else if (config.url === '/applications/11/screenings' && config.method === 'get') {
      data = [screeningSummary];
    } else if (config.url === '/screening-results/101') data = screeningDetail;
    else if (config.url === '/jobs/7/screenings/batch') {
      data = {
        job_id: 7,
        items: [{
          application_id: 11,
          status: 'reused',
          screening_result_id: 101,
          attempt_number: 2,
          reused: true,
          model_called: false,
          error_code: null,
          error_message: null,
        }],
        summary: {
          selected: 1,
          executed: 1,
          completed: 0,
          failed: 0,
          blocked: 0,
          reused: 1,
          skipped: 0,
        },
      };
    } else if (config.url === '/applications/11/history') data = [history];
    else data = application;
    return { config, data, headers: {}, status: 200, statusText: 'OK' };
  };

  const applications = await service.listStage7Applications({
    jobId: 7,
    recruitmentStage: 'hr_review',
    aiStatus: 'completed',
    hrDecision: 'pending',
    lifecycleStatus: 'active',
  });
  assert.equal(applications[0].candidateId, 2);
  assert.equal(applications[0].currentScreeningResultId, 101);
  assert.deepEqual(requests[0].params, {
    job_id: 7,
    recruitment_stage: 'hr_review',
    ai_status: 'completed',
    hr_decision: 'pending',
    lifecycle_status: 'active',
  });

  const fetched = await service.getStage7Application(11);
  assert.equal(fetched.aiStatus, 'completed');

  const intakeInput = {
    name: '测试候选人',
    phone: '13800138000',
    email: 'candidate@example.com',
    job_id: 7,
    current_resume_id: 5,
    source: 'hr_screening',
    confirm_hr_pass: false,
  };
  const intake = await service.intakeStage7Application(intakeInput);
  assert.equal(intake.candidateResolution, 'reused');
  assert.deepEqual(intake.suspectedDuplicateCandidateIds, [9]);

  const run = await service.runStage7ApplicationScreening(11, {
    force: true,
    confirm_force: true,
    reason: 'HR 主动复核',
  });
  assert.equal(run.result.evidenceCoverageRate, 0.875);
  assert.equal(run.result.estimatedCost, 0.0012);
  assert.equal(run.result.resumeEvidence[0].quote, 'Python');
  assert.equal(run.modelCalled, true);

  const screenings = await service.listStage7ApplicationScreenings(11);
  assert.equal(screenings[0].attemptNumber, 2);
  const detail = await service.getStage7ScreeningResult(101);
  assert.equal(detail.promptVersion, 'screening_evaluation_v3');

  const batch = await service.runStage7ScreeningBatch(7, {
    application_ids: [11],
    retry_failed_only: true,
  });
  assert.equal(batch.jobId, 7);
  assert.equal(batch.items[0].applicationId, 11);
  assert.equal(batch.summary.reused, 1);

  await service.passStage7Application(11, { reason_code: 'meets_requirements' });
  await service.backupStage7Application(11, { reason_code: 'waiting_for_comparison' });
  await service.rejectStage7Application(11, {
    reason_code: 'required_skill_missing',
    confirmed: true,
  });
  await service.undoStage7ApplicationRejection(11, {
    reason_code: 'new_evidence',
    reason_detail: '补充了可核对材料',
  });
  await service.voidStage7Application(11, { reason_code: 'wrong_job', confirmed: true });
  const histories = await service.listStage7ApplicationHistory(11);
  assert.equal(histories[0].screeningResultId, 101);

  assert.deepEqual(
    requests.slice(1).map(request => [request.method, request.url]),
    [
      ['get', '/applications/11'],
      ['post', '/applications/intake'],
      ['post', '/applications/11/screenings'],
      ['get', '/applications/11/screenings'],
      ['get', '/screening-results/101'],
      ['post', '/jobs/7/screenings/batch'],
      ['post', '/applications/11/pass'],
      ['post', '/applications/11/backup'],
      ['post', '/applications/11/reject'],
      ['post', '/applications/11/undo-rejection'],
      ['post', '/applications/11/void'],
      ['get', '/applications/11/history'],
    ],
  );
  assert.deepEqual(JSON.parse(requests[2].data), intakeInput);
  assert.deepEqual(JSON.parse(requests[3].data), {
    force: true,
    confirm_force: true,
    reason: 'HR 主动复核',
  });

  const parsedError = service.getStage7ApplicationApiError({
    isAxiosError: true,
    response: {
      status: 409,
      data: {
        detail: {
          code: 'BATCH_APPLICATION_JOB_MISMATCH',
          message: '批次包含其他岗位的 Application',
          application_ids: [12, 'invalid'],
          candidate_ids: [2],
        },
      },
    },
  });
  assert.equal(parsedError.code, 'BATCH_APPLICATION_JOB_MISMATCH');
  assert.deepEqual(parsedError.applicationIds, [12]);
  assert.deepEqual(parsedError.candidateIds, [2]);

  console.log('STAGE7_APPLICATION_SERVICE_TEST_OK');
} finally {
  await server.close();
}
