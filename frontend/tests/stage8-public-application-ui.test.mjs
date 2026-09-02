import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';


const source = await readFile(
  new URL('../src/features/recruitment/RecruitmentApplicationForm.tsx', import.meta.url),
  'utf8',
);
const service = await readFile(
  new URL('../src/features/recruitment/services/application.ts', import.meta.url),
  'utf8',
);
const styles = await readFile(
  new URL('../src/features/recruitment/styles/application.css', import.meta.url),
  'utf8',
);

for (const expectedText of [
  '选择岗位，提交你的申请资料',
  '申请资料夹',
  '姓名',
  '手机号码',
  '电子邮箱',
  '应聘岗位',
  '简历文件',
  'PDF、DOCX、TXT',
  '隐私说明版本',
  '发送申请',
  '投递已收到',
  '投递凭证',
  '受理成功不等于 AI 完成或 HR 通过',
  '已填写内容和简历仍保留在本页',
  '只使用虚构或完整脱敏',
  '岗位背景',
  '岗位职责',
  '任职要求',
  '加分项',
  '补充说明',
  '以下内容按招聘信息原始顺序展示',
]) {
  assert.ok(source.includes(expectedText), `公开投递页缺少真实交互或说明：${expectedText}`);
}

for (const removedText of [
  '表单结构预览',
  '内容不会发送到服务器',
  '返回招聘工作台',
  '教育背景',
  '毕业院校',
  '最高学历',
  '所学专业',
  '技能关键词',
  '个人简介',
  '提交投递 · 后续开放',
  '仅本地选择，不会上传',
  'PDF、DOC、DOCX、TXT',
]) {
  assert.equal(source.includes(removedText), false, `公开投递页仍保留旧预览合同：${removedText}`);
}

assert.ok(source.includes('onFinish={handleSubmit}'), '表单必须有真实提交处理');
assert.ok(source.includes('htmlType="submit"'), '主按钮必须触发表单提交');
assert.ok(source.includes('submittingRef.current'), '重复点击必须由同步门闩拦截');
assert.ok(source.includes('crypto.randomUUID()'), '浏览器必须生成不可手填的幂等 UUID');
assert.match(
  source,
  /previousAttempt\.signature === signature[\s\S]*previousAttempt\.resume === resume[\s\S]*previousAttempt\.idempotencyKey/,
  '相同表单与文件的网络重试必须复用同一幂等键',
);
assert.match(
  source,
  /parsedError\.code === 'IDEMPOTENCY_KEY_REUSED'[\s\S]*attemptRef\.current = null/,
  '服务端明确报告幂等冲突后，下次人工重试必须生成新键',
);
assert.match(
  source,
  /parsedError\.code === 'JOB_NOT_OPEN'[\s\S]*setFieldValue\('jobId', undefined\)[\s\S]*getRecruitmentApplicationJobs/,
  '岗位关闭竞态必须清空失效选择并刷新公开岗位',
);
assert.ok(source.includes('role="alert"'), '失败反馈必须对辅助技术立即可见');
assert.ok(source.includes('tabIndex={-1}'), '文件错误和成功标题必须可被程序聚焦');
assert.equal(source.includes('dangerouslySetInnerHTML'), false, '岗位文本不得作为 HTML 渲染');
const jdSectionsStart = source.indexOf('const sections = [');
const jdSectionsEnd = source.indexOf('];', jdSectionsStart);
assert.ok(jdSectionsStart >= 0 && jdSectionsEnd > jdSectionsStart, '缺少五段公开 JD 定义');
const jdSectionsBlock = source.slice(jdSectionsStart, jdSectionsEnd);
let previousJdSectionPosition = -1;
for (const label of ['岗位背景', '岗位职责', '任职要求', '加分项', '补充说明']) {
  const position = jdSectionsBlock.indexOf(`label: '${label}'`);
  assert.ok(position > previousJdSectionPosition, `公开 JD 顺序错误：${label}`);
  previousJdSectionPosition = position;
}
assert.match(
  styles,
  /\.recruitment-apply-selected-job-copy li\s*\{[^}]*grid-template-columns:\s*38px minmax\(0, 1fr\)/s,
  '桌面端每段 JD 必须独占一行，不能再左右交错',
);
assert.doesNotMatch(
  styles,
  /\.recruitment-apply-selected-job-copy\s*\{[^}]*repeat\(2/s,
  '岗位 JD 不得恢复成双栏网格',
);

assert.ok(service.includes("'/public/jobs'"), '公开页面只能请求独立公开岗位 API');
assert.ok(service.includes("'/public/applications'"), '公开页面必须请求独立公开投递 API');
assert.equal(service.includes("'/jobs'"), false, '公开页面不能再请求内部岗位 API');
for (const field of [
  'name',
  'phone',
  'email',
  'job_id',
  'privacy_consent',
  'consent_version',
  'idempotency_key',
  'resume',
]) {
  assert.ok(service.includes(`formData.append('${field}'`), `multipart 缺少字段：${field}`);
}

assert.match(
  styles,
  /\.recruitment-apply-layout\s*\{[^}]*grid-template-columns:\s*286px minmax\(0, 1fr\)/s,
  '桌面布局必须约束主列允许收缩',
);
assert.match(
  styles,
  /@media\s*\(max-width:\s*900px\)[\s\S]*?\.recruitment-apply-layout\s*\{[^}]*grid-template-columns:\s*1fr/s,
  '820px 视口必须切换为单列',
);
assert.match(
  styles,
  /@media\s*\(max-width:\s*600px\)[\s\S]*?\.recruitment-apply-grid[\s\S]*?grid-template-columns:\s*1fr/s,
  '390px 视口必须使用单列表单',
);
assert.ok(styles.includes(':focus-visible'), '键盘操作必须有明确焦点样式');
assert.ok(styles.includes('@media (prefers-reduced-motion: reduce)'), '必须尊重减少动态效果偏好');
assert.ok(styles.includes('overflow-x: clip'), '公开页面必须主动防止横向溢出');

console.log('STAGE8_PUBLIC_APPLICATION_UI_TEST_OK');
