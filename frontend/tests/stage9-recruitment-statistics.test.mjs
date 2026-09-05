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
  const { v2Http } = await server.ssrLoadModule('/src/services/http.ts');
  const statistics = await server.ssrLoadModule('/src/features/recruitment/services/recruitmentStatistics.ts');
  const requests = [];
  v2Http.defaults.adapter = async config => {
    requests.push(config);
    return {
      config,
      headers: {},
      status: 200,
      statusText: 'OK',
      data: {
        cohort: {
          job_id: 7,
          applied_from: '2026-09-01T00:00:00Z',
          applied_to: '2026-09-30T23:59:59Z',
        },
        funnel: [
          { key: 'applications', count: 4, conversion_rate: null },
          { key: 'screening_passed', count: 3, conversion_rate: 75 },
          { key: 'interview_entered', count: 2, conversion_rate: 66.67 },
          { key: 'interview_completed', count: 2, conversion_rate: 100 },
          { key: 'offer_sent', count: 1, conversion_rate: 50 },
          { key: 'offer_accepted', count: 1, conversion_rate: 100 },
          { key: 'admitted', count: 1, conversion_rate: 100 },
          { key: 'hired', count: 1, conversion_rate: 100 },
        ],
        durations: [
          { key: 'application_to_screening_passed', average_hours: 12.5, sample_count: 2 },
          { key: 'screening_passed_to_first_interview', average_hours: null, sample_count: 0 },
          { key: 'first_interview_to_last_completed', average_hours: 5, sample_count: 2 },
          { key: 'offer_entered_to_sent', average_hours: 8, sample_count: 1 },
          { key: 'offer_sent_to_response', average_hours: 20, sample_count: 1 },
          { key: 'offer_accepted_to_admitted', average_hours: 24, sample_count: 1 },
          { key: 'admitted_to_hired', average_hours: 72, sample_count: 1 },
        ],
        todos: {
          scheduled_interviews: 1,
          pending_interview_decisions: 2,
          next_round_not_scheduled: 3,
          draft_offers: 4,
          sent_offers: 5,
          accepted_offers: 6,
          admitted_applications: 7,
          total: 28,
        },
        generated_at: '2026-09-05T08:00:00Z',
      },
    };
  };

  const result = await statistics.getRecruitmentStatistics({
    jobId: 7,
    appliedFrom: '2026-09-01T00:00:00Z',
    appliedTo: '2026-09-30T23:59:59Z',
  });
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, '/recruitment-statistics');
  assert.equal(requests[0].params.job_id, 7);
  assert.equal(result.funnel[1].conversionRate, 75);
  assert.equal(result.durations[1].averageHours, null, '缺少完整端点时必须保留 null');
  assert.equal(result.durations[1].sampleCount, 0);
  assert.equal(result.todos.acceptedOffers, 6);
  assert.equal(JSON.stringify(result).toLowerCase().includes('salary'), false);

  const [panel, dashboard, center, styles] = await Promise.all([
    readFile(new URL('../src/features/recruitment/RecruitmentStatisticsPanel.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentDashboard.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/RecruitmentScreeningCenter.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/features/recruitment/styles/statistics.css', import.meta.url), 'utf8'),
  ]);
  for (const text of ['招聘流程统计', '漏斗按投递时间固定 cohort', '当前待办', '样本', '不调用 AI']) {
    assert.ok(panel.includes(text), `统计面板缺少：${text}`);
  }
  for (const text of ['收到申请', '通过初筛', '进入面试', '完成面试', 'Offer 已发送', 'Offer 已接受', '确认录取', '正式入职']) {
    assert.ok(panel.includes(text), `漏斗缺少：${text}`);
  }
  assert.ok(dashboard.includes('<RecruitmentStatisticsPanel />'));
  assert.equal(center.includes('<RecruitmentStatisticsPanel'), false, '招聘全流程统计只放在仪表盘，不挤占初筛工作台');
  assert.match(styles, /@media \(max-width: 560px\)[\s\S]*?grid-template-columns: 1fr/);
  assert.equal(panel.toLowerCase().includes('salary'), false);
  assert.equal(panel.includes('候选人姓名'), false);
  console.log('STAGE9_RECRUITMENT_STATISTICS_TEST_OK');
} finally {
  await server.close();
}
