import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const server = await createServer({ appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(), server: { middlewareMode: true } });
try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const service = await server.ssrLoadModule('/src/features/recruitment/services/screeningCenter.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    return { config, headers: {}, status: 200, statusText: 'OK', data: {
      items: [{ application_id: 31, candidate_id: 5, job_id: 2, resume_id: 8, candidate_name: '虚构候选人', masked_phone: '138****0000', current_title: '工程师', job_title: '虚构岗位', job_status: 'open', source: 'public_apply', submission_id: 41, submission_reference: 'AP-STAGE9C001', lifecycle_status: 'active', recruitment_stage: 'hr_review', hr_decision: 'pending', final_outcome: null, processing_pool: 'normal', processing_status: 'succeeded', processing_step: 'completed', processing_warning_codes: [], screening_status: 'ready', screening_run_status: 'succeeded', screening_waiting_reason: null, screening_error_message: null, score: 82, display_label: '整体较匹配', report_id: 55, report_is_outdated: false, ability_tags: [{ criterion_id: 'criterion:0001', label: 'Python API', score: 9, importance: 'required', evidence_count: 2, is_outdated: false }], overall_summary: '有可核对证据。', strengths: ['API 交付'], gaps_or_risks: ['规模待核实'], applied_at: '2026-09-03T01:00:00Z', business_updated_at: '2026-09-03T02:00:00Z', allowed_actions: ['view_detail', 'pass', 'backup', 'reject'] }],
      page: 1, page_size: 30, total: 1, total_pages: 1,
    } };
  };
  const page = await service.listScreeningCenterApplications({ applicationId: 31, processingPool: 'normal', sort: 'score_desc' });
  assert.equal(requests.length, 1, '列表必须只调用一个聚合接口，不能在前端逐行请求');
  assert.equal(requests[0].url, '/screening-center/applications');
  assert.equal(requests[0].params.application_id, 31);
  assert.equal(page.items[0].abilityTags[0].evidenceCount, 2);
  assert.equal(page.items[0].submissionReference, 'AP-STAGE9C001');

  const [app, layout, center, detail, drawer, styles] = await Promise.all([
    readFile(new URL('../src/App.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentLayout.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentCandidateDetail.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/ApplicationScreeningDrawer.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/styles/screening.css', import.meta.url), 'utf8'),
  ]);
  assert.ok(app.includes('path="resumes" element={<Navigate to="/app/screening" replace />}'));
  assert.ok(app.includes('path="reports" element={<Navigate to="/app/screening" replace />}'));
  assert.equal(layout.includes("label: '简历管理'"), false);
  assert.equal(layout.includes("label: '初筛报告'"), false);
  assert.ok(layout.includes("label: 'AI 初筛中心'"));
  for (const text of ['申请证据队列', '暂无可靠标签', '优势证据', '差距 / 风险', '招聘阶段', '查看处理与 AI 报告']) assert.ok(center.includes(text), `9C 列表缺少：${text}`);
  assert.ok(center.includes("useSearchParams"));
  assert.ok(detail.includes('`/app/screening?application_id=${applicationId}`'));
  for (const text of ['申请概览', '简历', 'AI 岗位匹配建议', '面试', 'Offer', '时间线', '不会触发新的 AI 调用']) assert.ok(drawer.includes(text), `统一详情缺少：${text}`);
  assert.ok(styles.includes('.recruitment-evidence-ledger'));
  assert.match(styles, /@media \(max-width: 760px\)[\s\S]*?\.recruitment-evidence-actions[\s\S]*?min-height: 44px/);
  assert.equal(center.includes('raw_text'), false);
  console.log('STAGE9_SCREENING_CENTER_TEST_OK');
} finally { await server.close(); }
