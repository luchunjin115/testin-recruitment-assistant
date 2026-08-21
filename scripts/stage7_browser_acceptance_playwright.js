async (page) => {
  const result = {
    fixture: 'STAGE7_BROWSER_ACCEPTANCE_FIXTURE',
    pages: [],
    planStates: {},
    screeningStates: {},
    responsive: {},
    accessibility: {},
    actions: {},
    polling: {},
    console: {},
    network: {},
    screenshots: [],
  };

  const projectConsole = [];
  const responseErrors = [];
  const requestEvents = [];
  page.on('console', message => projectConsole.push({
    type: message.type(),
    text: message.text(),
  }));
  page.on('response', response => {
    if (response.status() >= 400) {
      responseErrors.push({ status: response.status(), url: response.url() });
    }
  });
  page.on('request', request => {
    if (request.url().includes('/api/v2/')) {
      requestEvents.push({
        at: Date.now(),
        method: request.method(),
        url: request.url(),
      });
    }
  });

  await page.unroute('**/api/v2/**').catch(() => {});
  const iso = '2026-08-20T08:00:00Z';
  const requirements = {
    schema_version: '1.0',
    responsibilities: [
      '交付一个足够长的虚构招聘平台模块说明，用于验证文本换行、卡片高度与窄屏布局，不代表任何真实岗位或公司要求。',
    ],
    required_skills: ['React', 'TypeScript'],
    preferred_skills: ['可访问性'],
    minimum_work_years: 2,
    education_requirement: 'bachelor_or_above',
    required_experiences: ['复杂业务前端'],
    preferred_experiences: ['性能优化'],
    keywords: ['虚构验收'],
    additional_requirements: ['仅用于阶段 7 浏览器人工验收'],
  };
  const jobs = [1, 2, 3, 4].map(id => ({
    id,
    title: ['虚构前端工程师', '虚构数据分析师', '虚构测试工程师', '虚构关闭岗位'][id - 1],
    department: '验收测试部',
    location: '虚构地点',
    employment_type: 'full_time',
    headcount: 2,
    description: 'STAGE7_BROWSER_ACCEPTANCE_FIXTURE，仅用于前端展示验收。',
    requirements,
    status: id === 4 ? 'closed' : 'open',
    created_at: iso,
    updated_at: iso,
  }));
  const applicationIds = Array.from({ length: 23 }, (_, index) => 101 + index);
  const jobIdFor = id => id === 121 ? 2 : id === 112 ? 4 : 1;
  const applications = applicationIds.map((id, index) => ({
    id,
    candidate_id: 201 + index,
    job_id: jobIdFor(id),
    current_resume_id: 301 + index,
    source: 'hr_screening',
    lifecycle_status: 'active',
    recruitment_stage: 'hr_review',
    hr_decision: index % 3 === 0 ? 'passed' : index % 3 === 1 ? 'backup' : 'pending',
    applied_at: iso,
    created_at: iso,
    updated_at: iso,
  }));
  const candidates = applicationIds.map((id, index) => ({
    id: 201 + index,
    name: `虚构验收样本 A${String(index + 1).padStart(2, '0')}`,
    source: '阶段7浏览器验收',
    status: 'screening',
    applied_job_id: jobIdFor(id),
    current_title: '虚构岗位经历',
  }));

  const plan = (jobId, status) => ({
    id: 400 + jobId,
    job_id: jobId,
    jd_fingerprint: 'a'.repeat(64),
    status,
    is_current: status !== 'outdated',
    items: status === 'failed' ? [] : [
      {
        key: 'required_skill:react',
        title: 'React 与 TypeScript 复杂业务前端交付能力（这是用于验证长文本自动换行和布局稳定性的虚构超长评价事项，不代表真实岗位）',
        category: 'skill',
        priority: 'required',
        source_type: 'structured',
        source_field: 'requirements.required_skills',
        source_quote: null,
      },
      {
        key: 'preferred_accessibility',
        title: '基本可访问性实践',
        category: 'responsibility',
        priority: 'preferred',
        source_type: 'ai_extracted',
        source_field: null,
        source_quote: '需要支持键盘导航、清晰焦点和可理解的按钮名称；这是虚构 JD 原文。',
      },
      {
        key: 'general_collaboration',
        title: '跨角色协作',
        category: 'experience',
        priority: 'general',
        source_type: 'ai_extracted',
        source_field: null,
        source_quote: '与产品、后端和测试协作交付。',
      },
    ],
    structured_coverage: {
      source_schema_version: '1.0',
      fields: [{
        source_field: 'requirements.required_skills',
        source_value_count: 2,
        item_keys: ['required_skill:react'],
      }],
      all_covered: true,
    },
    warnings: jobId === 2 ? ['limited_basis'] : [],
    prompt_version: 'browser-fixture-plan-v1',
    model_version: 'fixture-not-deepseek',
    schema_version: '1.0',
    input_fingerprint: 'b'.repeat(64),
    input_snapshot: {
      job_id: jobId,
      title: jobs[jobId - 1].title,
      department: '验收测试部',
      description: '虚构',
      requirements,
    },
    error_code: status === 'failed' ? 'FIXTURE_PLAN_FAILED' : null,
    error_message: status === 'failed' ? '虚构安全错误：评价计划未通过内容校验。' : null,
    created_at: iso,
    completed_at: status === 'generating' ? null : iso,
    updated_at: iso,
  });
  const plans = {
    1: plan(1, 'ready'),
    2: plan(2, 'generating'),
    3: plan(3, 'failed'),
    4: plan(4, 'outdated'),
  };

  const run = (applicationId, status, runId = 500 + applicationId) => ({
    id: runId,
    application_id: applicationId,
    job_id: jobIdFor(applicationId),
    resume_id: 300 + applicationId - 100,
    job_evaluation_plan_id: 401,
    trigger_type: 'single_reassessment',
    status,
    input_fingerprint: 'c'.repeat(64),
    prompt_version: 'browser-fixture-screen-v1',
    model_version: 'fixture-not-deepseek',
    schema_version: '1.0',
    redaction_version: 'fixture-redact-v1',
    started_at: ['waiting_resume', 'waiting_plan', 'queued', 'paused'].includes(status) ? null : iso,
    completed_at: ['succeeded', 'failed'].includes(status) ? iso : null,
    error_code: status === 'failed' ? 'FIXTURE_SCREENING_FAILED' : null,
    error_message: status === 'failed' ? '虚构安全错误：输出未通过校验。' : null,
    input_tokens: null,
    output_tokens: null,
    duration_ms: null,
    attempt_count: 1,
    created_at: iso,
    updated_at: iso,
  });
  const report = (applicationId, outdated = false, zero = false) => ({
    id: 600 + applicationId,
    application_id: applicationId,
    job_id: jobIdFor(applicationId),
    resume_id: 300 + applicationId - 100,
    job_evaluation_plan_id: 401,
    overall_score: zero ? 72 : 78,
    display_label: '整体较匹配',
    overall_summary: '这是虚构且脱敏的浏览器验收报告。候选人展示了可核对的前端项目经历；AI 仅提供岗位匹配建议，HR 决策保持独立。',
    requirement_assessments: [
      {
        requirement_key: 'required_skill:react',
        score: zero ? 0 : 8,
        reason: zero
          ? '当前简历未体现 React 项目经历，不代表候选人不会 React。'
          : '有可核对的复杂业务前端项目。',
        calculation_note: null,
        evidence: zero ? [] : [{
          quote: '使用 React 与 TypeScript 交付复杂业务表单，并补充键盘导航。',
          section: '虚构项目经历',
        }],
      },
      {
        requirement_key: 'preferred_accessibility',
        score: 8,
        reason: '有键盘导航实践。',
        calculation_note: null,
        evidence: [{ quote: '补充键盘导航与 ARIA 标签。', section: '虚构项目经历' }],
      },
      {
        requirement_key: 'general_collaboration',
        score: 7,
        reason: '有跨角色协作记录。',
        calculation_note: null,
        evidence: [{ quote: '与产品、后端和测试协作交付。', section: '虚构项目经历' }],
      },
    ],
    bonus_highlights: zero ? [{
      title: '性能优化实践',
      score: 8,
      reason: '与岗位相关且有证据的额外亮点。',
      evidence: [{ quote: '将虚构页面首屏时间降低 30%。', section: '虚构项目经历' }],
    }] : [],
    tradeoff_reason: zero
      ? '必需项当前未体现，但其他工程实践支持较高综合判断；需要在面试中核实 React 实际经验。'
      : null,
    interview_questions: ['请说明你在虚构项目中的具体职责。', '请举例说明键盘可访问性如何验收。'],
    input_fingerprint: 'd'.repeat(64),
    jd_fingerprint: 'a'.repeat(64),
    plan_fingerprint: 'e'.repeat(64),
    resume_fingerprint: 'f'.repeat(64),
    prompt_version: 'browser-fixture-screen-v1',
    model_version: 'fixture-not-deepseek',
    schema_version: '1.0',
    redaction_version: 'fixture-redact-v1',
    is_outdated: outdated,
    outdated_reasons: outdated ? ['resume_changed'] : [],
    outdated_at: outdated ? iso : null,
    generated_at: iso,
    updated_at: iso,
  });
  const state = applicationId => {
    if (applicationId === 101) return { application_id: applicationId, report: null, latest_run: null };
    if (applicationId === 102) return { application_id: applicationId, report: null, latest_run: run(applicationId, 'waiting_resume') };
    if (applicationId === 103) return { application_id: applicationId, report: null, latest_run: run(applicationId, 'waiting_plan') };
    if (applicationId === 104) return { application_id: applicationId, report: null, latest_run: run(applicationId, 'queued') };
    if (applicationId === 105) return { application_id: applicationId, report: report(applicationId), latest_run: run(applicationId, 'running') };
    if (applicationId === 106) return { application_id: applicationId, report: report(applicationId), latest_run: run(applicationId, 'succeeded') };
    if (applicationId === 107) return { application_id: applicationId, report: null, latest_run: run(applicationId, 'failed') };
    if (applicationId === 108) return { application_id: applicationId, report: report(applicationId), latest_run: run(applicationId, 'failed') };
    if (applicationId === 109 || applicationId === 112) return { application_id: applicationId, report: null, latest_run: run(applicationId, 'paused') };
    if (applicationId === 110) return { application_id: applicationId, report: report(applicationId, true), latest_run: run(applicationId, 'succeeded') };
    if (applicationId === 111) return { application_id: applicationId, report: report(applicationId, false, true), latest_run: run(applicationId, 'succeeded') };
    return { application_id: applicationId, report: null, latest_run: null };
  };

  const routeCounts = {};
  const routeTimes = {};
  const batchBodies = [];
  let queuedPollingStartedAt = null;
  await page.route('**/api/v2/**', async route => {
    const request = route.request();
    const rawUrl = request.url();
    const afterPrefix = rawUrl.slice(rawUrl.indexOf('/api/v2') + 7);
    const path = afterPrefix.split('?')[0];
    const method = request.method();
    const key = `${method} ${path}`;
    routeCounts[key] = (routeCounts[key] || 0) + 1;
    routeTimes[key] = [...(routeTimes[key] || []), Date.now()];
    const json = value => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(value),
    });

    if (method === 'GET' && path === '/jobs') return json(jobs);
    if (method === 'GET' && path === '/candidates') return json(candidates);
    if (method === 'GET' && path === '/applications') return json(applications);

    let match = path.match(/^\/jobs\/(\d+)\/evaluation-plan$/);
    if (method === 'GET' && match) return json(plans[Number(match[1])]);

    match = path.match(/^\/applications\/(\d+)\/screening$/);
    if (method === 'GET' && match) {
      const applicationId = Number(match[1]);
      if (applicationId === 104) {
        const elapsed = queuedPollingStartedAt === null ? 0 : Date.now() - queuedPollingStartedAt;
        if (elapsed < 4000) return json(state(applicationId));
        if (elapsed < 8000) {
          return json({ application_id: applicationId, report: null, latest_run: run(applicationId, 'running') });
        }
        return json({
          application_id: applicationId,
          report: report(applicationId),
          latest_run: run(applicationId, 'succeeded'),
        });
      }
      return json(state(applicationId));
    }

    match = path.match(/^\/applications\/(\d+)\/screening\/re-evaluate$/);
    if (method === 'POST' && match) {
      const applicationId = Number(match[1]);
      return json({
        application_id: applicationId,
        run: run(applicationId, 'queued', 900 + applicationId),
        report: state(applicationId).report,
        reused_report: false,
        reused_run: false,
      });
    }

    match = path.match(/^\/applications\/(\d+)\/screening$/);
    if (method === 'POST' && match) {
      const applicationId = Number(match[1]);
      const reused = applicationId === 113;
      return json({
        application_id: applicationId,
        run: reused ? null : run(applicationId, 'queued', 900 + applicationId),
        report: reused ? report(applicationId) : null,
        reused_report: reused,
        reused_run: false,
      });
    }

    match = path.match(/^\/jobs\/(\d+)\/screening\/re-evaluate-batch$/);
    if (method === 'POST' && match) {
      const body = JSON.parse(request.postData() || '{}');
      batchBodies.push(body);
      return json({
        job_id: Number(match[1]),
        results: (body.application_ids || []).map(applicationId => ({
          application_id: applicationId,
          run: run(applicationId, 'queued', 1000 + applicationId),
          report: state(applicationId).report,
          reused_report: false,
          reused_run: false,
        })),
      });
    }

    if (method === 'POST' && /\/evaluation-plan\/(generate|regenerate)$/.test(path)) {
      const jobId = Number(path.split('/')[2]);
      return json(plans[jobId]);
    }

    return route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: { code: 'FIXTURE_NOT_FOUND', message: '验收夹具没有配置此请求' } }),
    });
  });

  const screenshot = async filename => {
    const path = `docs/stages/stage7/browser-acceptance-evidence/${filename}`;
    await page.screenshot({ path, fullPage: false, scale: 'css' });
    result.screenshots.push(path);
  };
  const waitDrawerClosed = async name => {
    await page.getByRole('dialog', { name }).waitFor({ state: 'detached' });
  };
  const jobRow = title => page.getByRole('row', { name: new RegExp(title) });
  const screeningCard = applicationId => page.locator('.recruitment-screening-card')
    .filter({ hasText: `Application #${applicationId}` });
  const openPlan = async title => {
    await jobRow(title).getByRole('button', { name: /评价计划/ }).click();
    const drawer = page.getByRole('dialog', { name: new RegExp(title) });
    await drawer.waitFor({ state: 'visible' });
    await page.waitForTimeout(450);
    return drawer;
  };
  const closeDrawer = async drawer => {
    const name = await drawer.getAttribute('aria-label');
    await drawer.getByRole('button', { name: '关闭', exact: true }).click();
    if (name) await waitDrawerClosed(name);
    else await drawer.waitFor({ state: 'detached' });
  };
  const openReport = async applicationId => {
    await screeningCard(applicationId).getByRole('button', { name: /查看 AI 报告/ }).click();
    const drawer = page.getByRole('dialog', { name: new RegExp(`Application #${applicationId}`) });
    await drawer.waitFor({ state: 'visible' });
    await page.waitForTimeout(450);
    return drawer;
  };
  const overflow = async locator => locator.evaluate(element => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
    horizontalOverflow: element.scrollWidth > element.clientWidth,
  }));

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://127.0.0.1:5173/app/jobs');
  await page.getByRole('table', { name: '新版岗位列表' }).waitFor();
  result.pages.push('/app/jobs');
  result.planStates.listOpened = await page.getByRole('table', { name: '新版岗位列表' }).isVisible();

  let drawer = await openPlan('虚构前端工程师');
  let text = await drawer.innerText();
  result.planStates.ready = {
    displayed: text.includes('已就绪'),
    required: text.includes('必需'),
    preferred: text.includes('优先'),
    structuredSource: text.includes('来自结构化 JD 字段'),
    quoteSource: text.includes('来自 JD 原文'),
    longContent: text.includes('这是用于验证长文本自动换行'),
    forbidden: ['API Key', '模型原始响应', '内部异常堆栈'].filter(value => text.includes(value)),
    overflow: await overflow(drawer.locator('.ant-drawer-body')),
  };
  await screenshot('jobs-plan-ready-desktop-1440x900.png');
  const readyTrigger = jobRow('虚构前端工程师').getByRole('button', { name: /评价计划/ });
  const focusOrder = [];
  let closeFocusVisible = false;
  for (let index = 0; index < 8; index += 1) {
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => {
      const element = document.activeElement;
      return {
        tag: element?.tagName || null,
        name: element?.getAttribute?.('aria-label') || element?.textContent?.trim() || null,
        focusVisible: Boolean(element?.matches?.(':focus-visible')),
      };
    });
    focusOrder.push(focused);
    if (focused.name === '关闭') {
      closeFocusVisible = focused.focusVisible;
      break;
    }
  }
  await page.keyboard.press('Escape');
  await drawer.waitFor({ state: 'detached' });
  result.accessibility.planDrawer = {
    focusOrder,
    closeFocusVisible,
    focusReturnedToTrigger: await readyTrigger.evaluate(element => element === document.activeElement),
  };

  drawer = await openPlan('虚构数据分析师');
  text = await drawer.innerText();
  result.planStates.generating = {
    displayed: text.includes('生成中'),
    limitedBasis: text.includes('评价依据有限'),
  };
  const generatingKey = 'GET /jobs/2/evaluation-plan';
  const generatingCountOpen = routeCounts[generatingKey] || 0;
  await page.waitForTimeout(8500);
  const generatingCountObserved = routeCounts[generatingKey] || 0;
  await closeDrawer(drawer);
  await page.waitForTimeout(8500);
  result.polling.planGenerating = {
    requestPath: '/api/v2/jobs/2/evaluation-plan',
    countAtOpen: generatingCountOpen,
    countAfterTwoScreeningIntervals: generatingCountObserved,
    countAfterClose: routeCounts[generatingKey] || 0,
    note: '评价计划生成中页面当前只在打开或手动刷新时请求，不自动轮询。',
  };

  drawer = await openPlan('虚构测试工程师');
  text = await drawer.innerText();
  result.planStates.failed = {
    displayed: text.includes('生成失败'),
    safeError: text.includes('虚构安全错误'),
    retryVisible: await drawer.getByRole('button', { name: '重新生成' }).isVisible(),
  };
  await screenshot('jobs-plan-failed-desktop-1440x900.png');
  await closeDrawer(drawer);

  drawer = await openPlan('虚构关闭岗位');
  text = await drawer.innerText();
  result.planStates.outdated = {
    displayed: text.includes('已过期') && text.includes('这份计划基于旧 JD'),
    overflow: await overflow(drawer.locator('.ant-drawer-body')),
  };
  await closeDrawer(drawer);

  await page.setViewportSize({ width: 820, height: 1180 });
  drawer = await openPlan('虚构前端工程师');
  result.responsive.planNarrow = {
    viewport: page.viewportSize(),
    drawerBox: await drawer.boundingBox(),
    body: await overflow(drawer.locator('.ant-drawer-body')),
    closeVisible: await drawer.getByRole('button', { name: '关闭', exact: true }).isVisible(),
  };
  await screenshot('jobs-plan-ready-narrow-820x1180.png');
  await closeDrawer(drawer);

  await page.setViewportSize({ width: 390, height: 844 });
  drawer = await openPlan('虚构前端工程师');
  result.responsive.planMobile = {
    viewport: page.viewportSize(),
    drawerBox: await drawer.boundingBox(),
    body: await overflow(drawer.locator('.ant-drawer-body')),
    closeVisible: await drawer.getByRole('button', { name: '关闭', exact: true }).isVisible(),
    refreshVisible: await drawer.getByRole('button', { name: '刷新评价计划' }).isVisible(),
  };
  await screenshot('jobs-plan-ready-mobile-390x844.png');
  await closeDrawer(drawer);

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole('link', { name: /AI 初筛/ }).click();
  await page.locator('.recruitment-screening-card').first().waitFor();
  result.pages.push('/app/screening');
  result.screeningStates.list = {
    cardCount: await page.locator('.recruitment-screening-card').count(),
    visibleStatuses: await page.locator('.recruitment-screening-card').allInnerTexts(),
  };
  await screenshot('screening-state-grid-desktop-1440x900.png');

  const checks = {
    101: ['尚无成功报告'],
    102: ['等待简历'],
    103: ['等待评价计划'],
    106: ['已完成'],
    107: ['运行失败', '当前没有可展示的成功报告'],
    108: ['运行失败', '旧成功报告仍然保留'],
    109: ['已暂停'],
    110: ['当前报告基于旧输入', '当前 Resume 已变化'],
  };
  for (const [idValue, expected] of Object.entries(checks)) {
    const applicationId = Number(idValue);
    drawer = await openReport(applicationId);
    text = await drawer.innerText();
    result.screeningStates[applicationId] = Object.fromEntries(
      expected.map(value => [value, text.includes(value)]),
    );
    if (applicationId === 108) await screenshot('screening-failed-old-report-desktop-1440x900.png');
    await closeDrawer(drawer);
  }

  drawer = await openReport(111);
  text = await drawer.innerText();
  const evidenceButtons = drawer.getByRole('button', { name: /查看简历证据/ });
  const evidenceBefore = await evidenceButtons.nth(1).getAttribute('aria-expanded');
  await evidenceButtons.nth(1).click();
  const evidenceAfter = await evidenceButtons.nth(1).getAttribute('aria-expanded');
  const desktopBody = await overflow(drawer.locator('.ant-drawer-body'));
  result.screeningStates.report = {
    zeroMeaning: text.includes('当前简历未体现 React 项目经历') && text.includes('不等同于候选人不会'),
    bonus: text.includes('性能优化实践'),
    tradeoff: text.includes('综合权衡'),
    interviewQuestions: text.includes('面试重点'),
    evidenceExpanded: evidenceBefore === 'false' && evidenceAfter === 'true',
    evidenceReadable: await drawer.getByText('“与产品、后端和测试协作交付。”').isVisible(),
    forbiddenDecisionText: ['建议通过', '建议淘汰', '建议录用', 'Offer'].filter(value => text.includes(value)),
    forbiddenLegacy: ['五维权重', '证据覆盖率', 'unknown', 'ScreeningResult'].filter(value => text.includes(value)),
    forbiddenSensitiveOrRaw: ['电话', '邮箱', '性别', '年龄', '婚育', '模型原始响应', 'API Key', '内部异常'].filter(value => text.includes(value)),
    body: desktopBody,
  };
  await screenshot('screening-report-zero-bonus-tradeoff-desktop-1440x900.png');
  const reportAria = typeof drawer.ariaSnapshot === 'function' ? await drawer.ariaSnapshot() : null;
  result.accessibility.reportAriaSnapshot = {
    supported: reportAria !== null,
    containsDialogTitle: reportAria?.includes('Application #111') || false,
    containsEvidenceButton: reportAria?.includes('查看简历证据') || false,
    containsReassessButton: reportAria?.includes('重新评估') || false,
  };

  await page.setViewportSize({ width: 820, height: 1180 });
  await page.waitForTimeout(350);
  result.responsive.screeningNarrow = {
    viewport: page.viewportSize(),
    drawerBox: await drawer.boundingBox(),
    body: await overflow(drawer.locator('.ant-drawer-body')),
    actionVisible: await drawer.getByRole('button', { name: '重新评估' }).isVisible(),
  };
  await screenshot('screening-report-narrow-820x1180.png');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(350);
  result.responsive.screeningMobile = {
    viewport: page.viewportSize(),
    drawerBox: await drawer.boundingBox(),
    body: await overflow(drawer.locator('.ant-drawer-body')),
    closeVisible: await drawer.getByRole('button', { name: '关闭', exact: true }).isVisible(),
    actionVisible: await drawer.getByRole('button', { name: '重新评估' }).isVisible(),
    evidenceVisible: await drawer.getByText('“与产品、后端和测试协作交付。”').isVisible(),
  };
  await screenshot('screening-report-mobile-390x844.png');
  await closeDrawer(drawer);

  await page.setViewportSize({ width: 1440, height: 900 });
  drawer = await openReport(112);
  result.actions.closedJob = {
    actionDisabled: await drawer.getByRole('button', { name: '开始初筛' }).first().isDisabled(),
    batchCheckboxDisabled: await screeningCard(112).getByRole('checkbox').isDisabled(),
  };
  await closeDrawer(drawer);

  drawer = await openReport(108);
  const hrDecisionBefore = await screeningCard(108).locator('.ant-tag').first().innerText();
  await drawer.getByRole('button', { name: '重新评估' }).click();
  const confirm = page.getByRole('dialog', { name: '确认重新评估？' });
  await confirm.waitFor({ state: 'visible' });
  result.actions.singleReassessmentConfirmation = await confirm.isVisible();
  await confirm.getByRole('button', { name: '重新评估' }).click();
  await page.waitForTimeout(450);
  text = await drawer.innerText();
  const hrDecisionAfter = await screeningCard(108).locator('.ant-tag').first().innerText();
  result.actions.singleReassessment = {
    queued: text.includes('已排队'),
    oldReportRetained: text.includes('旧成功报告仍然保留'),
    hrDecisionBefore,
    hrDecisionAfter,
    hrDecisionUnchanged: hrDecisionBefore === hrDecisionAfter,
  };
  await closeDrawer(drawer);

  drawer = await openReport(113);
  await drawer.getByRole('button', { name: '开始初筛' }).first().click();
  const reusedDialog = page.getByRole('dialog', { name: '已复用当前报告' });
  await reusedDialog.waitFor({ state: 'visible' });
  result.actions.idempotentReusePresented = await reusedDialog.isVisible();
  await reusedDialog.getByRole('button', { name: '知道了' }).click();
  await closeDrawer(drawer);

  const firstCheckbox = screeningCard(101).getByRole('checkbox');
  await firstCheckbox.click();
  await page.waitForTimeout(100);
  result.actions.crossJobRejected = await screeningCard(121).getByRole('checkbox').isDisabled();
  await firstCheckbox.click();

  const sameJobIds = applicationIds.filter(id => jobIdFor(id) === 1);
  for (const applicationId of sameJobIds.slice(0, 20)) {
    await screeningCard(applicationId).getByRole('checkbox').click();
  }
  result.actions.maxTwenty = {
    selectedText: await page.getByText('已选 20 / 20').innerText(),
    twentyFirstDisabled: await screeningCard(sameJobIds[20]).getByRole('checkbox').isDisabled(),
  };
  const checkedBoxes = page.getByRole('checkbox', { checked: true });
  while (await checkedBoxes.count()) {
    await checkedBoxes.first().click();
  }

  await screeningCard(101).getByRole('checkbox').click();
  await screeningCard(102).getByRole('checkbox').click();
  const batchHrBefore = [
    await screeningCard(101).locator('.ant-tag').first().innerText(),
    await screeningCard(102).locator('.ant-tag').first().innerText(),
  ];
  await page.getByRole('button', { name: '批量重新评估' }).click();
  const batchConfirm = page.getByRole('dialog', { name: /确认重新评估 2 人/ });
  await batchConfirm.waitFor({ state: 'visible' });
  await batchConfirm.getByRole('button', { name: '批量重新评估' }).click();
  await page.getByText('岗位 #1 已提交 2 个独立后台任务').waitFor({ state: 'visible' });
  const batchHrAfter = [
    await screeningCard(101).locator('.ant-tag').first().innerText(),
    await screeningCard(102).locator('.ant-tag').first().innerText(),
  ];
  result.actions.batch = {
    requestBody: batchBodies.at(-1),
    resultVisible: true,
    hrDecisionBefore: batchHrBefore,
    hrDecisionAfter: batchHrAfter,
    hrDecisionUnchanged: JSON.stringify(batchHrBefore) === JSON.stringify(batchHrAfter),
  };

  queuedPollingStartedAt = Date.now();
  drawer = await openReport(104);
  const queuedKey = 'GET /applications/104/screening';
  const queuedOpenCount = routeCounts[queuedKey] || 0;
  const queuedOpenText = await drawer.innerText();
  await page.waitForTimeout(4200);
  const queuedFirstPollCount = routeCounts[queuedKey] || 0;
  const firstPollText = await drawer.innerText();
  await page.waitForTimeout(4200);
  const queuedSecondPollCount = routeCounts[queuedKey] || 0;
  const secondPollText = await drawer.innerText();
  const queuedTimes = routeTimes[queuedKey] || [];
  await page.waitForTimeout(8500);
  const queuedTerminalCount = routeCounts[queuedKey] || 0;
  result.polling.queuedToSucceeded = {
    requestPath: '/api/v2/applications/104/screening',
    countAtOpen: queuedOpenCount,
    countAfterFirstPoll: queuedFirstPollCount,
    countAfterSecondPoll: queuedSecondPollCount,
    countAfterTwoMoreTerminalIntervals: queuedTerminalCount,
    showedQueued: queuedOpenText.includes('已排队'),
    showedRunning: firstPollText.includes('评估中'),
    showedSucceeded: secondPollText.includes('已完成'),
    intervalsMs: queuedTimes.slice(-3).map((time, index, values) => index === 0 ? null : time - values[index - 1]).slice(1),
  };
  await closeDrawer(drawer);

  drawer = await openReport(105);
  const runningKey = 'GET /applications/105/screening';
  await page.waitForTimeout(4200);
  const runningBeforeClose = routeCounts[runningKey] || 0;
  await closeDrawer(drawer);
  await page.waitForTimeout(8500);
  result.polling.closeDrawerStops = {
    requestPath: '/api/v2/applications/105/screening',
    countBeforeClose: runningBeforeClose,
    countAfterTwoIntervalsClosed: routeCounts[runningKey] || 0,
  };

  drawer = await openReport(105);
  await page.waitForTimeout(4200);
  const beforeRouteLeave = routeCounts[runningKey] || 0;
  await page.goto('http://127.0.0.1:5173/app/jobs');
  await page.getByRole('table', { name: '新版岗位列表' }).waitFor();
  await page.waitForTimeout(8500);
  result.polling.routeLeaveStops = {
    requestPath: '/api/v2/applications/105/screening',
    countBeforeLeave: beforeRouteLeave,
    countAfterTwoIntervalsAway: routeCounts[runningKey] || 0,
  };

  const apiEvents = requestEvents.filter(event => event.url.includes('/api/v2/'));
  result.network = {
    requestCount: apiEvents.length,
    responseErrorCount: responseErrors.length,
    responseErrors,
    batchPostCount: apiEvents.filter(event => event.method === 'POST' && event.url.includes('/screening/re-evaluate-batch')).length,
    singleReassessmentPostCount: apiEvents.filter(event => event.method === 'POST' && event.url.includes('/screening/re-evaluate')).length,
  };
  const ignoredWarnings = projectConsole.filter(entry =>
    entry.type === 'warning' && entry.text.includes('React Router Future Flag Warning'));
  const relevantConsole = projectConsole.filter(entry =>
    entry.type === 'error'
    || (entry.type === 'warning' && !entry.text.includes('React Router Future Flag Warning')));
  result.console = {
    totalCaptured: projectConsole.length,
    ignoredReactRouterFutureWarnings: ignoredWarnings.length,
    relevantProjectErrorOrWarningCount: relevantConsole.length,
    relevantProjectEntries: relevantConsole,
  };
  result.pages.push('/app/jobs (route-leave verification)');
  return result;
}
