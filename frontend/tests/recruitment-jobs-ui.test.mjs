import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';


const source = await readFile(
  new URL('../src/features/recruitment/RecruitmentJobList.tsx', import.meta.url),
  'utf8',
);
const styles = await readFile(
  new URL('../src/features/recruitment/styles/jobs.css', import.meta.url),
  'utf8',
);

for (const expectedText of [
  '新增岗位',
  '保存草稿',
  '保存并开放',
  '保存修改',
  '开放岗位',
  '关闭岗位',
  '重新开放',
  '删除岗位',
  '岗位名称',
  '所属部门',
  '工作地点',
  '用工类型',
  '招聘人数',
  '岗位背景',
  '岗位职责',
  '任职要求',
  '加分项',
  '备注',
  '候选人可见，请勿填写内部招聘信息',
  '不会删除历史候选人和初筛结果',
  '岗位已有历史业务数据，不能删除',
]) {
  assert.ok(source.includes(expectedText), `岗位页面缺少真实交互或字段：${expectedText}`);
}

for (const removedText of [
  '新增岗位 · 表单预览',
  '查看新增表单结构',
  '保存岗位 · 后续',
  '当前不会保存',
  '不会修改 PostgreSQL',
  '岗位描述',
  '必备技能',
  '加分技能',
  '最低工作年限',
  '学历要求',
  '必备经历',
  '加分经历',
  '岗位关键词',
  '其他要求',
]) {
  assert.equal(source.includes(removedText), false, `岗位页面仍存在骨架文案：${removedText}`);
}

assert.ok(source.includes('Modal.useModal'), '确认框必须使用可消费 React 上下文的 Modal 实例');
assert.ok(source.includes('modalApi.confirm'), '关闭、重新开放和删除必须提供二次确认');
assert.equal(source.includes('Modal.confirm'), false, '岗位页面不能使用丢失主题上下文的静态确认框');
assert.ok(source.includes('isFieldsTouched'), '关闭抽屉前必须检查未保存修改');
assert.ok(source.includes('scrollToField'), '开放校验失败后必须定位第一个字段');
assert.ok(
  source.includes("loadState.status !== 'ready' || !pendingSuccessMessage"),
  '成功通知必须等待岗位列表重新挂载后再显示，避免 React 渲染期调用 Ant Design message',
);
assert.equal(
  /await loadJobs\(\);\s*messageApi\.success/.test(source),
  false,
  '刷新列表后不能同步调用已卸载上下文中的成功通知',
);
assert.equal(
  /const closeFormNow[\s\S]*?form\.resetFields\(\);[\s\S]*?};/.test(source),
  false,
  '列表状态操作关闭未挂载表单时不能调用 resetFields',
);
assert.match(
  styles,
  /\.recruitment-job-form-footer\s*\{[^}]*display:\s*flex;/s,
  '岗位表单底部操作区必须使用可换行布局',
);
assert.match(
  styles,
  /\.recruitment-job-form-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\);/s,
  '岗位表单两列必须允许收缩，不能被长文本挤坏',
);
assert.match(
  styles,
  /\.recruitment-job-form-grid\s*>\s*\.ant-form-item[^{]*\{[^}]*min-width:\s*0;/s,
  '网格内的表单项必须允许收缩',
);
assert.match(
  styles,
  /@media\s*\(max-width:\s*560px\)[\s\S]*?\.recruitment-job-form-footer\s*\{[^}]*flex-direction:\s*column;/s,
  '390px 窄屏下表单操作按钮必须纵向排列',
);

console.log('RECRUITMENT_JOBS_UI_TEST_OK');
