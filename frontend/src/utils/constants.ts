export const STAGES = ['新投递', '待筛选', '待约面', '已约面', '面试中', '复试', 'offer', '入职', '淘汰'];

export const FORMAL_FLOW_STAGES = ['待约面', '已约面', '面试中', '复试', 'offer', '入职', '淘汰'];

export const ACTIVE_FORMAL_FLOW_STAGES = ['待约面', '已约面', '面试中', '复试', 'offer', '入职'];

export const STAGE_COLORS: Record<string, string> = {
  '新投递': '#1890ff',
  '待筛选': '#13c2c2',
  '待约面': '#faad14',
  '已约面': '#722ed1',
  '面试中': '#eb2f96',
  '复试': '#fa541c',
  'offer': '#52c41a',
  '入职': '#389e0d',
  '淘汰': '#8c8c8c',
};

export const CHANNELS = ['HR手动录入', '企业微信群', '内推', 'Boss直聘', '拉勾', '猎聘', '其他', '在线投递', '表单录入', '简历上传'];

export const DEGREES = ['大专', '本科', '硕士', '博士', '其他'];

export const CHANNEL_COLORS = ['#1890ff', '#52c41a', '#2f54eb', '#722ed1', '#faad14', '#eb2f96', '#fa541c', '#13c2c2'];

export const HR_ACTIONS: { key: string; label: string; description: string; needsTime?: boolean }[] = [
  { key: 'pass_screening', label: '通过初筛', description: '将候选人推进到待约面阶段并进入正式候选人列表' },
  { key: 'set_interview_time', label: '安排面试', description: '填写面试时间、方式、面试官并推进到已约面', needsTime: true },
  { key: 'advance_to_retest', label: '进入复试', description: '确认一面通过并推进到复试阶段' },
  { key: 'send_offer', label: '发放 Offer', description: '填写 Offer 信息并推进到 offer 阶段' },
  { key: 'mark_onboarded', label: '确认入职', description: '确认候选人入职并结束流程' },
  { key: 'mark_eliminated', label: '淘汰', description: '填写淘汰原因并结束流程' },
];

export const STAGE_SOURCE_LABELS: Record<string, string> = {
  'system_auto': '系统自动',
  'hr_action': 'HR操作',
  'manual': '人工修正',
};

export const PRIORITY_LEVELS = ['高优先级', '中优先级', '低优先级'];

export const PRIORITY_COLORS: Record<string, string> = {
  '高优先级': 'red',
  '中优先级': 'gold',
  '低优先级': 'default',
};
