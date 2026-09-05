import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';


const appSource = await readFile(
  new URL('../src/App.tsx', import.meta.url),
  'utf8',
);
const viteSource = await readFile(
  new URL('../vite.config.ts', import.meta.url),
  'utf8',
);
const nginxSource = await readFile(
  new URL('../nginx.conf', import.meta.url),
  'utf8',
);
const startupSource = await readFile(
  new URL('../../scripts/start_project.ps1', import.meta.url),
  'utf8',
);
const indexSource = await readFile(
  new URL('../index.html', import.meta.url),
  'utf8',
);
const layoutSource = await readFile(
  new URL('../src/features/recruitment/RecruitmentLayout.tsx', import.meta.url),
  'utf8',
);
const publicApplicationSource = await readFile(
  new URL('../src/features/recruitment/RecruitmentApplicationForm.tsx', import.meta.url),
  'utf8',
);

const retiredFrontendFiles = [
  '../src/api/index.ts',
  '../src/types/index.ts',
  '../src/utils/constants.ts',
  '../src/components/AppLayout.tsx',
  '../src/components/ChannelPieChart.tsx',
  '../src/components/CopilotChat.tsx',
  '../src/components/DailySummary.tsx',
  '../src/components/FollowUpAlerts.tsx',
  '../src/components/FunnelChart.tsx',
  '../src/components/RecentLogs.tsx',
  '../src/components/StageTag.tsx',
  '../src/components/StatsCards.tsx',
  '../src/pages/AIScreeningCenter.tsx',
  '../src/pages/ApplyForm.css',
  '../src/pages/ApplyForm.tsx',
  '../src/pages/CandidateDetail.tsx',
  '../src/pages/CandidateForm.tsx',
  '../src/pages/CandidateList.tsx',
  '../src/pages/Dashboard.tsx',
  '../src/pages/JobManagement.tsx',
  '../src/pages/ResumeUpload.tsx',
  '../src/pages/Stage3Preview.tsx',
];

for (const retiredFile of retiredFrontendFiles) {
  await assert.rejects(
    access(new URL(retiredFile, import.meta.url)),
    { code: 'ENOENT' },
    `旧前端文件不应重新出现：${retiredFile}`,
  );
}

await assert.rejects(
  access(new URL('../src/stage3', import.meta.url)),
  { code: 'ENOENT' },
  '施工期 frontend/src/stage3 目录不应重新出现',
);

for (const retiredImport of [
  './components/AppLayout',
  './pages/Dashboard',
  './pages/CandidateForm',
  './pages/CandidateList',
  './pages/CandidateDetail',
  './pages/AIScreeningCenter',
  './pages/ApplyForm',
  './pages/JobManagement',
  './pages/Stage3Preview',
]) {
  assert.equal(
    appSource.includes(retiredImport),
    false,
    `运行入口仍加载旧前端模块：${retiredImport}`,
  );
}

assert.ok(
  appSource.includes('<Navigate to="/app/dashboard" replace />'),
  '根路径和未知路径必须进入新版工作台',
);
assert.ok(
  appSource.includes('path="/apply" element={withRouteLoading(<RecruitmentApplicationForm />)}'),
  '公开投递地址必须直接加载正式投递页',
);
assert.ok(appSource.includes('path="/app"'), '内部 HR 工作台必须使用 /app');
assert.equal(appSource.includes('/stage3'), false, '运行入口不应保留施工期 /stage3 路径');
assert.equal(appSource.includes('path="/stage3-preview"'), false);
assert.equal(viteSource.includes("'/uploads'"), false, 'Vite 不应代理旧公开上传目录');
assert.equal(nginxSource.includes('location /uploads/'), false, 'Nginx 不应代理旧公开上传目录');
assert.ok(
  startupSource.includes('http://localhost:5173/app/jobs'),
  '一键启动脚本必须打开正式岗位管理地址',
);
assert.equal(
  startupSource.includes('http://localhost:5173/stage3'),
  false,
  '一键启动脚本不应重新打开施工期地址',
);
assert.ok(
  indexSource.includes('<title>HR智聘｜AI 招聘全流程平台</title>'),
  '浏览器标签必须使用当前正式产品名称',
);
assert.equal(indexSource.includes('Testin云测招聘助手'), false, '浏览器标签不得恢复旧品牌');
for (const source of [layoutSource, publicApplicationSource]) {
  assert.ok(source.includes('<strong>HR智聘</strong>'), '内部工作台和公开投递必须使用统一短品牌');
  assert.equal(source.includes('HR Agent'), false, '当前页面不得恢复未实现的 Agent 品牌');
}
assert.ok(startupSource.includes('HR智聘 - Backend'));
assert.ok(startupSource.includes('HR智聘 - Frontend'));

console.log('NEW_RUNTIME_ENTRY_TEST_OK');
