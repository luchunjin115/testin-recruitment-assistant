import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

const server = await createServer({ appType: 'custom', configFile: false, logLevel: 'silent', root: process.cwd(), server: { middlewareMode: true } });
try {
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const service = await server.ssrLoadModule('/src/features/recruitment/services/screeningCenter.ts');
  const pipeline = await server.ssrLoadModule('/src/features/recruitment/services/recruitmentPipeline.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    return { config, headers: {}, status: 200, statusText: 'OK', data: {
      items: [{ application_id: 31, candidate_id: 5, job_id: 2, resume_id: 8, candidate_name: '虚构候选人', masked_phone: '138****0000', current_company: '虚构科技', current_title: '工程师', work_years: 3, education_level: '本科', job_title: '虚构岗位', job_status: 'open', source: 'public_apply', submission_id: 41, submission_reference: 'AP-STAGE9C001', lifecycle_status: 'active', recruitment_stage: 'hr_review', hr_decision: 'pending', final_outcome: null, processing_pool: 'normal', processing_status: 'succeeded', processing_step: 'completed', processing_warning_codes: [], screening_status: 'ready', screening_run_status: 'succeeded', screening_waiting_reason: null, screening_error_message: null, score: 82, display_label: '整体较匹配', report_id: 55, report_is_outdated: false, ability_tags: [{ criterion_id: 'criterion:0001', label: 'Python API', score: 9, importance: 'required', evidence_count: 2, is_outdated: false }], overall_summary: '有可核对证据。', strengths: ['API 交付'], gaps_or_risks: ['规模待核实'], applied_at: '2026-09-03T01:00:00Z', business_updated_at: '2026-09-03T02:00:00Z', allowed_actions: ['view_detail', 'pass', 'backup', 'reject'] }],
      page: 1, page_size: 30, total: 1, total_pages: 1,
    } };
  };
  const page = await service.listScreeningCenterApplications({ view: 'screening', keyword: '虚构候选人', applicationId: 31, processingPool: 'normal', sort: 'score_desc' });
  assert.equal(requests.length, 1, '列表必须只调用一个聚合接口，不能在前端逐行请求');
  assert.equal(requests[0].url, '/screening-center/applications');
  assert.equal(requests[0].params.application_id, 31);
  assert.equal(requests[0].params.view, 'screening');
  assert.equal(requests[0].params.keyword, '虚构候选人');
  assert.equal(page.items[0].abilityTags[0].evidenceCount, 2);
  assert.equal(page.items[0].submissionReference, 'AP-STAGE9C001');
  assert.equal(page.items[0].currentCompany, '虚构科技');

  const pipelineRequests = [];
  v2Http.defaults.adapter = async config => {
    pipelineRequests.push(config);
    return { config, headers: {}, status: 200, statusText: 'OK', data: config.method === 'get' ? [{
      id: 71, application_id: 31, version_number: 1, status: 'draft', position_title: '虚构工程师', currency: 'CNY', salary_period: 'monthly', base_salary_amount: '18888.80', salary_months: '13.0', bonus_note: null, benefits_note: null, valid_until: '2026-10-01', expected_start_date: '2026-10-15', note: null, sent_at: null, responded_at: null, closed_at: null, version: 1, created_at: '2026-09-04T01:00:00Z', updated_at: '2026-09-04T01:00:00Z',
    }] : {
      id: 71, application_id: 31, version_number: 1, status: 'draft', position_title: '虚构工程师', currency: 'CNY', salary_period: 'monthly', base_salary_amount: '18888.80', salary_months: '13.0', bonus_note: null, benefits_note: null, valid_until: '2026-10-01', expected_start_date: '2026-10-15', note: null, sent_at: null, responded_at: null, closed_at: null, version: 1, created_at: '2026-09-04T01:00:00Z', updated_at: '2026-09-04T01:00:00Z',
    } };
  };
  const offers = await pipeline.listApplicationOffers(31);
  assert.equal(offers[0].baseSalaryAmount, '18888.80', '薪资必须以十进制字符串传到前端');
  await pipeline.createApplicationOffer(31, {
    position_title: '虚构工程师', currency: 'CNY', salary_period: 'monthly', base_salary_amount: '18888.80', salary_months: '13.0', bonus_note: null, benefits_note: null, valid_until: '2026-10-01', expected_start_date: '2026-10-15', note: null,
  });
  assert.equal(pipelineRequests[1].data.includes('"base_salary_amount":"18888.80"'), true);

  const [app, layout, center, candidateList, detail, drawer, table, interviewPanel, offerPanel, styles] = await Promise.all([
    readFile(new URL('../src/App.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentLayout.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentCandidateList.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentCandidateDetail.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/ApplicationScreeningDrawer.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/ApplicationEvidenceTable.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/InterviewPipelinePanel.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/OfferPipelinePanel.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/styles/screening.css', import.meta.url), 'utf8'),
  ]);
  assert.ok(app.includes('path="resumes" element={<Navigate to="/app/screening" replace />}'));
  assert.ok(app.includes('path="reports" element={<Navigate to="/app/screening" replace />}'));
  assert.equal(layout.includes("label: '简历管理'"), false);
  assert.equal(layout.includes("label: '初筛报告'"), false);
  assert.ok(layout.includes("label: 'AI 初筛中心'"));
  for (const text of ['初筛申请列表', '只处理尚未通过初筛的申请', "view: 'screening'", '批量重新评估']) assert.ok(center.includes(text), `初筛工作台缺少：${text}`);
  assert.ok(center.includes("useSearchParams"));
  for (const text of ['候选人列表', '每一行代表候选人对一个岗位的招聘进程', "view: 'candidate'", 'workspace="candidate"']) assert.ok(candidateList.includes(text), `候选人工作台缺少：${text}`);
  assert.ok(candidateList.includes('onStateChange={refreshApplicationSummary}'));
  assert.equal(candidateList.includes('onStateChange={() => void load()}'), false, '详情加载不得因为每次渲染产生新回调而循环请求');
  assert.ok(detail.includes('`/app/candidates?application_id=${applicationId}`'));
  for (const text of ['申请概览', '简历', 'AI 岗位匹配建议', '面试', 'Offer', '时间线', '不会触发新的 AI 调用']) assert.ok(drawer.includes(text), `统一详情缺少：${text}`);
  for (const text of ['候选人', '应聘岗位', '初筛状态', '招聘阶段', '来源', 'AI 初筛', 'AI 标签', 'AI 结论', '更新时间', '操作', '暂无可靠标签']) assert.ok(table.includes(text), `高密度表格缺少：${text}`);
  for (const text of ['安排{latest ?', "'下一轮' : '首轮'", '完整安排', '改期', '填写反馈', '取消', '未到场', '更正反馈']) assert.ok(interviewPanel.includes(text), `面试面板缺少：${text}`);
  for (const text of ['创建 Offer 草稿', '标记已发送', '记录接受', '记录拒绝', '公司撤回 Offer', '标记已过期', '确认已录取、等待入职', '确认正式入职', '记录候选人退出', '公司取消流程', '受控重新打开']) assert.ok(offerPanel.includes(text), `9D Offer 面板缺少：${text}`);
  assert.ok(offerPanel.includes('base_salary_amount: values.baseSalaryAmount.trim()'));
  assert.equal(offerPanel.includes('InputNumber'), false, '薪资输入不能经过 JavaScript number/float');
  assert.equal(drawer.includes('timeline.slice(0, 8)'), false, '统一详情不能静默截断审计时间线');
  assert.ok(drawer.includes('if (notifyParent) onStateChange?.(next)'), '普通 GET 读取不得无条件触发父列表刷新');
  assert.ok(candidateList.includes('onPipelineChange={load}'), '9D 操作后必须刷新候选人列表和详情记录');
  assert.ok(styles.includes('.recruitment-offer-history'));
  assert.ok(styles.includes('.recruitment-application-table'));
  assert.match(styles, /@media \(max-width: 760px\)[\s\S]*?\.recruitment-application-table-row[\s\S]*?grid-template-columns: 1fr/);
  assert.equal(`${center}${candidateList}${table}`.includes('raw_text'), false);
  assert.equal(`${center}${candidateList}${table}`.toLowerCase().includes('base_salary'), false, '列表不得读取薪资');
  console.log('STAGE9_SCREENING_CENTER_TEST_OK');
} finally { await server.close(); }
