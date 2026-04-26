import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Input, message, Modal, Progress, Row, Select, Space, Statistic, Table, Tag, Typography } from 'antd';
import { CheckCircleOutlined, ReloadOutlined, RobotOutlined, StopOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import type { ColumnsType } from 'antd/es/table';
import type { ScreeningResult, ScreeningStats } from '../types';
import { getScreeningResults, passCandidateScreening, rejectCandidateScreening, runBatchScreening, runSingleScreening } from '../api';
import { PRIORITY_COLORS, PRIORITY_LEVELS } from '../utils/constants';

const { Text } = Typography;

const DATE_RANGE_OPTIONS = [
  { label: '全部时间', value: 'all' },
  { label: '今日投递', value: 'today' },
  { label: '本周投递', value: 'this_week' },
  { label: '最近 7 天', value: 'last_7_days' },
  { label: '最近 30 天', value: 'last_30_days' },
];

const EMPTY_STATS: ScreeningStats = {
  total_candidates: 0,
  screened_count: 0,
  high_priority_count: 0,
  medium_priority_count: 0,
  low_priority_count: 0,
  average_match_score: 0,
  unscreened_count: 0,
  pending_count: 0,
  passed_count: 0,
  backup_count: 0,
  rejected_count: 0,
  formal_candidate_count: 0,
};

const AIScreeningCenter: React.FC = () => {
  const [data, setData] = useState<ScreeningResult[]>([]);
  const [total, setTotal] = useState(0);
  const [currentStats, setCurrentStats] = useState<ScreeningStats>(EMPTY_STATS);
  const [overallStats, setOverallStats] = useState<ScreeningStats>(EMPTY_STATS);
  const [priority, setPriority] = useState<string | undefined>();
  const [screeningStatus, setScreeningStatus] = useState<string | undefined>();
  const [decisionStatus, setDecisionStatus] = useState('pending');
  const [sortBy, setSortBy] = useState('created_desc');
  const [dateRange, setDateRange] = useState('all');
  const [targetRole, setTargetRole] = useState('');
  const [loading, setLoading] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [actionId, setActionId] = useState<number | null>(null);
  const [rejectCandidate, setRejectCandidate] = useState<ScreeningResult | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [jobProfileCandidate, setJobProfileCandidate] = useState<ScreeningResult | null>(null);
  const navigate = useNavigate();

  const buildQueryParams = useCallback(() => {
    const params: Record<string, string> = {};
    if (sortBy === 'created_desc') {
      params.sort_by = 'created_at';
      params.sort_order = 'desc';
    } else if (sortBy === 'created_asc') {
      params.sort_by = 'created_at';
      params.sort_order = 'asc';
    } else {
      params.sort_by = sortBy;
    }
    if (priority) params.priority_level = priority;
    if (screeningStatus) params.screening_status = screeningStatus;
    params.decision_status = decisionStatus;
    if (targetRole.trim()) params.target_role = targetRole.trim();
    if (dateRange !== 'all') params.date_range = dateRange;
    return params;
  }, [dateRange, priority, screeningStatus, decisionStatus, sortBy, targetRole]);

  const calculateStatsFromRows = (rows: ScreeningResult[]): ScreeningStats => {
    let high = 0;
    let medium = 0;
    let low = 0;
    let unscreened = 0;
    const scores: number[] = [];
    rows.forEach(item => {
      const priorityLevel = (item.priority_level || '').trim();
      const isScreened = item.match_score !== null || Boolean(priorityLevel);
      if (item.match_score !== null) scores.push(item.match_score);
      if (!isScreened) {
        unscreened += 1;
      } else if (priorityLevel === '高优先级') {
        high += 1;
      } else if (priorityLevel === '中优先级') {
        medium += 1;
      } else {
        low += 1;
      }
    });
    const screened = high + medium + low;
    return {
      total_candidates: rows.length,
      screened_count: screened,
      high_priority_count: high,
      medium_priority_count: medium,
      low_priority_count: low,
      average_match_score: scores.length ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length) : 0,
      unscreened_count: unscreened,
      pending_count: rows.filter(item => item.screening_status === 'pending').length,
      passed_count: rows.filter(item => item.screening_status === 'passed').length,
      backup_count: rows.filter(item => item.screening_status === 'backup').length,
      rejected_count: rows.filter(item => item.screening_status === 'rejected').length,
      formal_candidate_count: rows.filter(item => item.screening_status === 'passed').length,
    };
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getScreeningResults(buildQueryParams());
      setData(result.items);
      setTotal(result.total ?? (result.items || []).length);
      setCurrentStats(calculateStatsFromRows(result.items || []));
      setOverallStats(result.overall_stats || result.stats || EMPTY_STATS);
    } catch {
      message.error('加载初筛结果失败');
    } finally {
      setLoading(false);
    }
  }, [buildQueryParams]);

  useEffect(() => { loadData(); }, [loadData]);

  const hasFilters = Boolean(priority || screeningStatus || decisionStatus !== 'pending' || targetRole.trim() || dateRange !== 'all');
  const currentTotalCheck = currentStats.high_priority_count
    + currentStats.medium_priority_count
    + currentStats.low_priority_count
    + currentStats.unscreened_count;

  const handleBatchRun = async () => {
    const currentCount = data.length;
    if (currentCount === 0) {
      message.info('当前筛选范围内暂无候选人');
      return;
    }
    Modal.confirm({
      title: '确认开始批量初筛',
      content: `将对当前筛选结果中的 ${currentCount} 名候选人执行 AI 初筛；已初筛候选人会重新生成结果。`,
      okText: '开始初筛',
      cancelText: '取消',
      onOk: async () => {
        setBatchLoading(true);
        try {
          const params = buildQueryParams();
          delete params.sort_by;
          delete params.sort_order;
          const result = await runBatchScreening(params);
          message.success(`批量初筛完成，本次处理 ${result.processed_count} 人`);
          await loadData();
        } catch {
          message.error('批量初筛失败');
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  const handleSingleRun = async (candidate: ScreeningResult) => {
    setRunningId(candidate.id);
    try {
      await runSingleScreening(candidate.id);
      message.success(`已重新初筛 ${candidate.name}`);
      await loadData();
    } catch {
      message.error('重新初筛失败');
    } finally {
      setRunningId(null);
    }
  };

  const handlePass = async (candidate: ScreeningResult) => {
    setActionId(candidate.id);
    try {
      await passCandidateScreening(candidate.id);
      message.success(`${candidate.name} 已通过初筛，进入候选人列表`);
      await loadData();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '通过初筛失败');
    } finally {
      setActionId(null);
    }
  };

  const handleReject = async () => {
    if (!rejectCandidate) return;
    const reason = rejectReason.trim();
    if (!reason) {
      message.warning('请填写淘汰原因');
      return;
    }
    setActionId(rejectCandidate.id);
    try {
      await rejectCandidateScreening(rejectCandidate.id, { reject_reason: reason });
      message.success(`${rejectCandidate.name} 已初筛淘汰`);
      setRejectCandidate(null);
      setRejectReason('');
      await loadData();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '初筛淘汰失败');
    } finally {
      setActionId(null);
    }
  };

  const columns: ColumnsType<ScreeningResult> = [
    {
      title: '姓名',
      dataIndex: 'name',
      width: 100,
      fixed: 'left',
      render: (name: string, record) => (
        <a onClick={() => navigate(`/candidates/${record.id}`)}>{name}</a>
      ),
    },
    { title: '应聘岗位', dataIndex: 'target_role', width: 130, render: (text: string) => text || '-' },
    {
      title: '匹配依据',
      dataIndex: 'job_match_summary',
      width: 180,
      render: (summary: string, record) => (
        <Space direction="vertical" size={2}>
          <span>{summary || '暂无岗位标准匹配信息'}</span>
          <Button size="small" type="link" onClick={() => setJobProfileCandidate(record)}>
            查看岗位标准
          </Button>
        </Space>
      ),
    },
    {
      title: '投递时间',
      dataIndex: 'created_at',
      width: 150,
      sorter: (a, b) => new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime(),
      render: (time: string) => time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-',
    },
    { title: '学校', dataIndex: 'school', width: 130, render: (text: string) => text || '-' },
    {
      title: '技能标签',
      dataIndex: 'skills',
      width: 220,
      render: (skills: string[]) => (
        <Space size={[2, 4]} wrap>
          {(skills || []).slice(0, 4).map(skill => <Tag key={skill}>{skill}</Tag>)}
        </Space>
      ),
    },
    {
      title: 'AI匹配度',
      dataIndex: 'match_score',
      width: 140,
      sorter: (a, b) => (a.match_score || 0) - (b.match_score || 0),
      render: (score: number | null) => (
        score === null
          ? <Tag>未初筛</Tag>
          : <Progress percent={score} size="small" strokeColor={score >= 80 ? '#f5222d' : score >= 60 ? '#faad14' : '#8c8c8c'} />
      ),
    },
    {
      title: '推荐等级',
      dataIndex: 'priority_level',
      width: 110,
      render: (level: string) => level ? <Tag color={PRIORITY_COLORS[level]}>{level}</Tag> : <Tag>未初筛</Tag>,
    },
    {
      title: '初筛建议',
      dataIndex: 'screening_result',
      width: 100,
      render: (result: string) => {
        if (!result) return '-';
        const displayText = result === '备选' ? '待HR复核' : result;
        return <Tag color={result === '建议初筛' ? 'green' : 'default'}>{displayText}</Tag>;
      },
    },
    {
      title: '处理状态',
      dataIndex: 'screening_status',
      width: 105,
      render: (status: ScreeningResult['screening_status']) => {
        const map: Partial<Record<ScreeningResult['screening_status'], { text: string; color: string }>> = {
          pending: { text: '待初筛', color: 'gold' },
          passed: { text: '已通过', color: 'green' },
          rejected: { text: '初筛淘汰', color: 'red' },
        };
        const item = map[status || 'pending'] || { text: '正式流程', color: 'default' };
        return <Tag color={item.color}>{item.text}</Tag>;
      },
    },
    {
      title: '风险提示',
      dataIndex: 'risk_flags',
      width: 220,
      render: (flags: string[]) => (
        <Space size={[2, 4]} wrap>
          {(flags || []).map(flag => (
            <Tag key={flag} color={flag === '暂无明显风险' ? 'green' : 'orange'}>{flag}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'AI理由',
      dataIndex: 'screening_reason',
      ellipsis: true,
      width: 260,
      render: (reason: string) => reason || '-',
    },
    {
      title: '操作',
      width: 280,
      fixed: 'right',
      render: (_, record) => (
        <Space wrap>
          <Button
            size="small"
            type="primary"
            icon={<CheckCircleOutlined />}
            loading={actionId === record.id}
            disabled={record.screening_status === 'passed'}
            onClick={() => handlePass(record)}
          >
            通过初筛
          </Button>
          <Button
            size="small"
            danger
            icon={<StopOutlined />}
            disabled={record.screening_status === 'passed'}
            onClick={() => { setRejectCandidate(record); setRejectReason(''); }}
          >
            初筛淘汰
          </Button>
          <Button size="small" onClick={() => navigate(`/candidates/${record.id}`)}>详情</Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={runningId === record.id}
            onClick={() => handleSingleRun(record)}
          >
            重新初筛
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Space align="center">
            <RobotOutlined style={{ fontSize: 24, color: '#1677ff' }} />
            <div>
              <h2 style={{ margin: 0 }}>AI 初筛中心</h2>
              <Text type="secondary">批量评分、推荐等级和风险提示仅作为 HR 辅助参考</Text>
            </div>
          </Space>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={batchLoading}
            onClick={handleBatchRun}
          >
            开始批量初筛
          </Button>
        </Col>
      </Row>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="AI 初筛中心只处理新投递和待初筛候选人。AI 只提供匹配度和风险提示，最终通过或初筛淘汰由 HR 确认。"
      />

      <Card title="招聘漏斗初筛统计" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={5}><Statistic title="总投递人数" value={overallStats.total_candidates} valueStyle={{ color: '#1677ff' }} /></Col>
          <Col span={5}><Statistic title="待初筛" value={overallStats.pending_count} valueStyle={{ color: '#d48806' }} /></Col>
          <Col span={5}><Statistic title="已通过初筛" value={overallStats.passed_count} valueStyle={{ color: '#389e0d' }} /></Col>
          <Col span={5}><Statistic title="初筛淘汰" value={overallStats.rejected_count} valueStyle={{ color: '#cf1322' }} /></Col>
          <Col span={4}><Statistic title="AI已评分" value={overallStats.screened_count} /></Col>
        </Row>
      </Card>

      <Card>
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={`当前处理池：${currentStats.total_candidates} 人，待初筛 ${currentStats.pending_count} 人`}
          description={`AI 已评分 ${currentStats.screened_count} 人，尚未评分 ${currentStats.unscreened_count} 人；高优先级 ${currentStats.high_priority_count} 人 / 中优先级 ${currentStats.medium_priority_count} 人 / 低优先级 ${currentStats.low_priority_count} 人。四类加总：${currentTotalCheck} 人。${hasFilters ? '当前已应用筛选条件。' : '当前为待初筛默认视图。'}`}
        />
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Input
              placeholder="按岗位搜索"
              value={targetRole}
              onChange={event => setTargetRole(event.target.value)}
              allowClear
            />
          </Col>
          <Col span={3}>
            <Select
              style={{ width: '100%' }}
              value={dateRange}
              onChange={setDateRange}
              options={DATE_RANGE_OPTIONS}
            />
          </Col>
          <Col span={3}>
            <Select
              placeholder="推荐等级"
              allowClear
              style={{ width: '100%' }}
              value={priority}
              onChange={setPriority}
              options={PRIORITY_LEVELS.map(level => ({ label: level, value: level }))}
            />
          </Col>
          <Col span={3}>
            <Select
              placeholder="处理状态"
              style={{ width: '100%' }}
              value={decisionStatus}
              onChange={setDecisionStatus}
              options={[
                { label: '待初筛', value: 'pending' },
                { label: '初筛淘汰', value: 'rejected' },
              ]}
            />
          </Col>
          <Col span={3}>
            <Select
              placeholder="初筛状态"
              allowClear
              style={{ width: '100%' }}
              value={screeningStatus}
              onChange={setScreeningStatus}
              options={[
                { label: '已初筛', value: 'screened' },
                { label: '尚未初筛', value: 'unscreened' },
              ]}
            />
          </Col>
          <Col span={4}>
            <Select
              style={{ width: '100%' }}
              value={sortBy}
              onChange={setSortBy}
              options={[
                { label: '最新投递优先', value: 'created_desc' },
                { label: '最早投递优先', value: 'created_asc' },
                { label: '匹配度从高到低', value: 'score_desc' },
                { label: '匹配度从低到高', value: 'score_asc' },
                { label: '最近初筛优先', value: 'updated_desc' },
              ]}
            />
          </Col>
          <Col span={2}>
            <Button onClick={loadData}>刷新</Button>
          </Col>
          <Col span={1} style={{ textAlign: 'right', lineHeight: '32px' }}>
            <Text type="secondary">当前 {total} 人</Text>
          </Col>
        </Row>

        <Table
          dataSource={data}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="middle"
          scroll={{ x: 1900 }}
          rowClassName={record => record.priority_level === '高优先级' ? 'screening-high-priority-row' : ''}
          pagination={{ pageSize: 10, showTotal: count => `共 ${count} 条` }}
        />
      </Card>

      <Modal
        title={jobProfileCandidate ? `${jobProfileCandidate.target_role || '岗位'}标准` : '岗位标准'}
        open={!!jobProfileCandidate}
        footer={null}
        onCancel={() => setJobProfileCandidate(null)}
      >
        {jobProfileCandidate?.job_requirement_profile && Object.keys(jobProfileCandidate.job_requirement_profile).length > 0 ? (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text type="secondary">必备技能</Text>
              <div>{jobProfileCandidate.job_requirement_profile.required_skills || '未配置'}</div>
            </div>
            <div>
              <Text type="secondary">加分技能</Text>
              <div>{jobProfileCandidate.job_requirement_profile.bonus_skills || '未配置'}</div>
            </div>
            <div>
              <Text type="secondary">学历 / 经验要求</Text>
              <div>
                {jobProfileCandidate.job_requirement_profile.education_requirement || '未配置'}
                {' / '}
                {jobProfileCandidate.job_requirement_profile.experience_requirement || '未配置'}
              </div>
            </div>
            <div>
              <Text type="secondary">岗位关键词</Text>
              <div>{jobProfileCandidate.job_requirement_profile.job_keywords || '未配置'}</div>
            </div>
            <div>
              <Text type="secondary">风险提示关键词</Text>
              <div>{jobProfileCandidate.job_requirement_profile.risk_keywords || '未配置'}</div>
            </div>
            <div>
              <Text type="secondary">岗位描述 / 要求</Text>
              <div style={{ whiteSpace: 'pre-wrap' }}>
                {[jobProfileCandidate.job_requirement_profile.description, jobProfileCandidate.job_requirement_profile.requirements]
                  .filter(Boolean)
                  .join('\n\n') || '未配置'}
              </div>
            </div>
          </Space>
        ) : (
          <Alert type="warning" showIcon message="该候选人的应聘岗位尚未配置岗位要求" />
        )}
      </Modal>

      <Modal
        title={rejectCandidate ? `初筛淘汰：${rejectCandidate.name}` : '初筛淘汰'}
        open={!!rejectCandidate}
        onOk={handleReject}
        onCancel={() => { setRejectCandidate(null); setRejectReason(''); }}
        okText="确认淘汰"
        cancelText="取消"
        okButtonProps={{ danger: true, loading: !!rejectCandidate && actionId === rejectCandidate.id }}
      >
        <Alert
          type="warning"
          showIcon
          message="请填写淘汰原因，候选人数据会保留但不会进入正式候选人列表。"
          style={{ marginBottom: 12 }}
        />
        <Input.TextArea
          rows={4}
          placeholder="请输入初筛淘汰原因"
          value={rejectReason}
          onChange={event => setRejectReason(event.target.value)}
        />
      </Modal>
    </div>
  );
};

export default AIScreeningCenter;
