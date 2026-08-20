import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';


const source = await readFile(
  new URL('../src/features/recruitment/RecruitmentCandidateCreate.tsx', import.meta.url),
  'utf8',
);
const styles = await readFile(
  new URL('../src/features/recruitment/styles/candidate-create.css', import.meta.url),
  'utf8',
);

for (const expectedText of [
  '阶段 7 · HR 人工直通',
  '简历智能识别',
  '文件已上传',
  '内容已读取',
  '信息识别',
  '正在识别候选人信息',
  '简历识别完成，请核对后创建候选人',
  '本次识别耗时',
  '模型调用',
  '结果校验',
  '结果保存',
  '查看提取文本（核对用）',
  '仅用于核对',
]) {
  assert.ok(source.includes(expectedText), `缺少新版简历识别文案：${expectedText}`);
}

for (const removedText of [
  '正在生成 AI 草稿',
  'AI 草稿生成完成',
  '提取原文预览',
  '简历与 AI 草稿',
  '未识别的重要字段',
]) {
  assert.equal(source.includes(removedText), false, `仍存在旧版技术文案：${removedText}`);
}

assert.ok(source.includes('<Collapse'), '提取文本必须使用默认折叠区域');
assert.equal(source.includes('defaultActiveKey'), false, '提取文本不应默认展开');
assert.match(
  styles,
  /\.recruitment-candidate-create-aside\s*\{[^}]*height:\s*calc\(100vh\s*-\s*32px\);[^}]*overflow:\s*hidden;/s,
  '桌面端右侧栏必须具有明确的视口高度',
);
assert.match(
  styles,
  /\.recruitment-candidate-create-aside\s*>\s*\.recruitment-candidate-resume-card\s*\{[^}]*min-height:\s*0;[^}]*overflow-y:\s*scroll;/s,
  '简历智能识别卡片本身必须是强制纵向滚动容器',
);
assert.match(
  styles,
  /@media\s*\(max-width:\s*980px\)[\s\S]*?\.recruitment-candidate-create-aside\s*\{[^}]*height:\s*auto;[^}]*overflow:\s*visible;[\s\S]*?\.recruitment-candidate-create-aside\s*>\s*\.recruitment-candidate-resume-card\s*\{[^}]*overflow:\s*hidden;/s,
  '窄屏右侧识别栏必须恢复普通页面流，避免嵌套滚动',
);

console.log('RECRUITMENT_RESUME_INTAKE_UI_COPY_TEST_OK');
