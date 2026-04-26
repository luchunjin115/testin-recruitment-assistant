import React, { useEffect, useState, useCallback } from 'react';
import { Table, Card, Input, Select, Tag, Button, Space, message, Row, Col, Popconfirm, Progress, Alert, Modal } from 'antd';
import { SearchOutlined, DownloadOutlined, SyncOutlined, DeleteOutlined, CheckCircleOutlined, StopOutlined, CalendarOutlined, FileExcelOutlined, RobotOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { Candidate } from '../types';
import { getCandidates, getCandidateFilterOptions, updateStage, triggerSync, downloadCSV, deleteCandidate, batchUpdateStatus, batchExportCandidates, batchGenerateFollowup, markCandidateBackup } from '../api';
import { ACTIVE_FORMAL_FLOW_STAGES, FORMAL_FLOW_STAGES, PRIORITY_COLORS } from '../utils/constants';

type CandidateScope = 'formal' | 'backup' | 'rejected';

const SCOPE_CONFIG: Record<CandidateScope, { label: string; title: string; description: string }> = {
  formal: {
    label: '正式流程候选人',
    title: '正式流程候选人',
    description: '展示已通过初筛并进入招聘流程的候选人。',
  },
  backup: {
    label: '备选候选人',
    title: '备选候选人',
    description: '展示暂不进入正式流程但保留观察的候选人。',
  },
  rejected: {
    label: '淘汰候选人',
    title: '淘汰候选人',
    description: '展示已淘汰但保留记录的候选人。',
  },
};

const CandidateList: React.FC = () => {
  const [data, setData] = useState<Candidate[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [filterRole, setFilterRole] = useState<string | undefined>();
  const [filterStage, setFilterStage] = useState<string | undefined>();
  const [filterChannel, setFilterChannel] = useState<string | undefined>();
  const [filterTodayNew, setFilterTodayNew] = useState(false);
  const [candidateScope, setCandidateScope] = useState<CandidateScope>('formal');
  const [roleOptions, setRoleOptions] = useState<string[]>([]);
  const [channelOptions, setChannelOptions] = useState<string[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchLoading, setBatchLoading] = useState<string | null>(null);
  const [eliminateModalOpen, setEliminateModalOpen] = useState(false);
  const [eliminateReason, setEliminateReason] = useState('');
  const navigate = useNavigate();

  const selectedIds = selectedRowKeys.map(key => Number(key));
  const selectedCount = selectedRowKeys.length;
  const scopeConfig = SCOPE_CONFIG[candidateScope];
  const showStageFilter = candidateScope === 'formal';
  const stageOptions = candidateScope === 'rejected' ? ['淘汰'] : candidateScope === 'formal' ? ACTIVE_FORMAL_FLOW_STAGES : [];

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 20 };
      if (keyword) params.keyword = keyword;
      if (filterRole) params.target_role = filterRole;
      if (filterStage) params.stage = filterStage;
      if (filterChannel) params.channel = filterChannel;
      if (filterTodayNew) params.is_today_new = 'true';
      params.candidate_scope = candidateScope;
      const result = await getCandidates(params);
      setData(result.items);
      setTotal(result.total);
    } catch {
      message.error('加载候选人列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, keyword, filterRole, filterStage, filterChannel, filterTodayNew, candidateScope]);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    const loadOptions = async () => {
      try {
        const options = await getCandidateFilterOptions();
        setRoleOptions(options.target_roles || []);
        setChannelOptions(options.source_channels || []);
      } catch {
        message.error('加载筛选选项失败');
      }
    };
    loadOptions();
  }, []);

  const resetFilters = () => {
    setKeyword('');
    setFilterRole(undefined);
    setFilterStage(undefined);
    setFilterChannel(undefined);
    setFilterTodayNew(false);
    setCandidateScope('formal');
    setPage(1);
    setSelectedRowKeys([]);
  };

  const formatDateTime = (value: string) => {
    if (!value) return '';
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const renderSourceTag = (source: string) => {
    if (source === '在线投递') return <Tag color="green">在线投递</Tag>;
    if (source === 'HR手动录入') return <Tag color="blue">HR录入</Tag>;
    return <Tag>{source || '未知来源'}</Tag>;
  };

  const handleStageChange = async (id: number, stage: string) => {
    try {
      await updateStage(id, stage);
      message.success('状态更新成功');
      loadData();
    } catch {
      message.error('状态更新失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteCandidate(id);
      message.success('删除成功');
      loadData();
    } catch {
      message.error('删除失败');
    }
  };

  const clearSelection = () => setSelectedRowKeys([]);

  const handleScopeChange = (value: CandidateScope) => {
    setCandidateScope(value);
    setFilterStage(undefined);
    setPage(1);
    clearSelection();
  };

  const handleBatchStatus = async (targetStage: string, reason: string, loadingKey: string) => {
    if (!selectedIds.length) return;
    setBatchLoading(loadingKey);
    try {
      const result = await batchUpdateStatus({
        candidate_ids: selectedIds,
        target_stage: targetStage,
        reason,
        source: 'hr_action',
      });
      if (result.failed_count > 0) {
        message.warning(`批量操作完成：成功 ${result.success_count} 人，失败 ${result.failed_count} 人`);
      } else {
        message.success(`批量操作成功：已处理 ${result.success_count} 人`);
      }
      clearSelection();
      loadData();
    } catch {
      message.error('批量操作失败');
    } finally {
      setBatchLoading(null);
    }
  };

  const handleBatchEliminate = async () => {
    const reason = eliminateReason.trim() ? `批量淘汰：${eliminateReason.trim()}` : '批量淘汰';
    setEliminateModalOpen(false);
    await handleBatchStatus('淘汰', reason, 'eliminate');
    setEliminateReason('');
  };

  const handleBatchBackup = async () => {
    if (!selectedIds.length) return;
    setBatchLoading('backup');
    try {
      await Promise.all(selectedIds.map(id => markCandidateBackup(id)));
      message.success(`已将 ${selectedIds.length} 名正式流程候选人标记为备选`);
      clearSelection();
      loadData();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || '批量标记备选失败');
    } finally {
      setBatchLoading(null);
    }
  };

  const handleBatchExport = async () => {
    if (!selectedIds.length) return;
    setBatchLoading('export');
    try {
      await batchExportCandidates(selectedIds);
      message.success(`已导出 ${selectedIds.length} 名候选人`);
    } catch {
      message.error('批量导出失败');
    } finally {
      setBatchLoading(null);
    }
  };

  const handleBatchFollowup = async () => {
    if (!selectedIds.length) return;
    setBatchLoading('followup');
    try {
      const result = await batchGenerateFollowup(selectedIds);
      if (result.failed_count > 0) {
        message.warning(`AI跟进建议生成完成：成功 ${result.success_count} 人，失败 ${result.failed_count} 人`);
      } else {
        message.success(`已为 ${result.success_count} 名候选人生成AI跟进建议`);
      }
      clearSelection();
      loadData();
    } catch {
      message.error('批量生成AI跟进建议失败');
    } finally {
      setBatchLoading(null);
    }
  };

  const columns = [
    {
      title: '姓名', dataIndex: 'name', width: 100,
      render: (name: string, record: Candidate) => (
        <a onClick={() => navigate(`/candidates/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: '新增标签',
      dataIndex: 'new_candidate_label',
      width: 105,
      render: (label: string) => label ? (
        <Tag color={label === '今日新增' ? 'green' : 'gold'}>{label}</Tag>
      ) : <span style={{ color: '#999' }}>-</span>,
    },
    { title: '手机号', dataIndex: 'phone', width: 130 },
    { title: '应聘岗位', dataIndex: 'target_role', width: 140 },
    { title: '学校', dataIndex: 'school', width: 130 },
    {
      title: '阶段', dataIndex: 'stage', width: 130,
      render: (stage: string, record: Candidate) => (
        <Select
          value={stage}
          size="small"
          style={{ width: 110 }}
          onChange={(v) => handleStageChange(record.id, v)}
          options={FORMAL_FLOW_STAGES.map(s => ({ label: s, value: s }))}
          dropdownStyle={{ minWidth: 110 }}
          disabled={candidateScope === 'rejected'}
        />
      ),
    },
    {
      title: '初筛状态',
      dataIndex: 'screening_status',
      width: 100,
      render: (status: Candidate['screening_status']) => {
        const map: Record<Candidate['screening_status'], { text: string; color: string }> = {
          pending: { text: '待初筛', color: 'gold' },
          passed: { text: '已通过', color: 'green' },
          backup: { text: '备选', color: 'blue' },
          rejected: { text: '初筛淘汰', color: 'red' },
        };
        const item = map[status || 'pending'];
        return <Tag color={item.color}>{item.text}</Tag>;
      },
    },
    {
      title: '来源渠道', dataIndex: 'source_channel', width: 110,
      render: renderSourceTag,
    },
    {
      title: '是否今日新增',
      dataIndex: 'is_today_new',
      width: 115,
      render: (isTodayNew: boolean) => isTodayNew ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: 'AI初筛',
      width: 180,
      render: (_: unknown, record: Candidate) => (
        record.match_score === null ? (
          <Tag>未初筛</Tag>
        ) : (
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Progress
              percent={record.match_score || 0}
              size="small"
              strokeColor={(record.match_score || 0) >= 80 ? '#f5222d' : (record.match_score || 0) >= 60 ? '#faad14' : '#8c8c8c'}
            />
            <Space size={4} wrap>
              <Tag color={PRIORITY_COLORS[record.priority_level]}>{record.priority_level}</Tag>
              {record.screening_result && <Tag color="blue">{record.screening_result}</Tag>}
            </Space>
          </Space>
        )
      ),
    },
    {
      title: 'AI标签', dataIndex: 'ai_tags', width: 200,
      render: (tags: string[]) => (
        <Space size={[2, 4]} wrap>
          {(tags || []).slice(0, 3).map(t => <Tag key={t} color="blue">{t}</Tag>)}
        </Space>
      ),
    },
    {
      title: 'AI跟进',
      width: 170,
      render: (_: unknown, record: Candidate) => (
        <Space direction="vertical" size={2}>
          {record.is_overdue && (
            <Space size={4} wrap>
              <Tag color="red">超时</Tag>
              <Tag color="volcano">{record.overdue_days}天</Tag>
            </Space>
          )}
          <Tag color={record.followup_priority === '高' ? 'red' : record.followup_priority === '中' ? 'gold' : 'default'}>
            {record.followup_priority || '低'}优先级
          </Tag>
          <span style={{ fontSize: 12, color: '#666' }}>
            {record.overdue_reason || record.followup_reason || record.followup_suggestion || '暂无建议'}
          </span>
        </Space>
      ),
    },
    {
      title: '重复', dataIndex: 'is_duplicate', width: 60,
      render: (dup: boolean) => dup ? <Tag color="red">重复</Tag> : null,
    },
    {
      title: '投递时间', dataIndex: 'created_at', width: 140,
      render: formatDateTime,
    },
    {
      title: '操作', width: 80, fixed: 'right' as const,
      render: (_: unknown, record: Candidate) => (
        <Popconfirm
          title="确认删除"
          description={`确定要删除候选人「${record.name}」吗？此操作不可恢复。`}
          onConfirm={() => handleDelete(record.id)}
          okText="确认删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button type="link" danger size="small" icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <Card
      title={`候选人管理 / ${scopeConfig.title} (共 ${total} 人)`}
      extra={
        <Space>
          <Button icon={<SyncOutlined />} onClick={async () => { try { await triggerSync(); message.success('同步成功'); } catch { message.error('同步失败'); } }}>同步CSV</Button>
          <Button icon={<DownloadOutlined />} onClick={downloadCSV}>导出</Button>
        </Space>
      }
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="当前页面用于查看已通过初筛、备选及淘汰候选人；新投递和待初筛候选人请在 AI 初筛中心处理。"
        description={scopeConfig.description}
      />
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={3}>
          <Select
            style={{ width: '100%' }}
            value={candidateScope}
            onChange={handleScopeChange}
            options={[
              { label: '正式流程候选人', value: 'formal' },
              { label: '备选候选人', value: 'backup' },
              { label: '淘汰候选人', value: 'rejected' },
            ]}
          />
        </Col>
        <Col span={4}>
          <Select
            placeholder="全部岗位"
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: '100%' }}
            value={filterRole}
            onChange={v => { setFilterRole(v); setPage(1); clearSelection(); }}
            options={roleOptions.map(role => ({ label: role, value: role }))}
          />
        </Col>
        <Col span={4}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索姓名/学校/专业/技能/邮箱/手机"
            value={keyword}
            onChange={e => { setKeyword(e.target.value); setPage(1); clearSelection(); }}
            onPressEnter={() => setPage(1)}
            allowClear
          />
        </Col>
        {showStageFilter && (
          <Col span={3}>
            <Select
              placeholder="全部阶段"
              allowClear
              style={{ width: '100%' }}
              value={filterStage}
              onChange={v => { setFilterStage(v); setPage(1); clearSelection(); }}
              options={stageOptions.map(s => ({ label: s, value: s }))}
            />
          </Col>
        )}
        <Col span={3}>
          <Select
            placeholder="全部来源"
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: '100%' }}
            value={filterChannel}
            onChange={v => { setFilterChannel(v); setPage(1); clearSelection(); }}
            options={channelOptions.map(channel => ({ label: channel, value: channel }))}
          />
        </Col>
        <Col span={3}>
          <Select
            placeholder="新增筛选"
            allowClear
            style={{ width: '100%' }}
            value={filterTodayNew ? 'today' : undefined}
            onChange={v => { setFilterTodayNew(v === 'today'); setPage(1); clearSelection(); }}
            options={[{ label: '今日新增', value: 'today' }]}
          />
        </Col>
        <Col span={2}>
          <Button type="primary" block onClick={() => setPage(1)}>搜索</Button>
        </Col>
        <Col span={2}>
          <Button block onClick={resetFilters}>重置</Button>
        </Col>
      </Row>

      <Alert
        type={selectedCount > 0 ? 'info' : 'warning'}
        showIcon
        style={{ marginBottom: 16 }}
        message={
          <Row align="middle" justify="space-between" gutter={12}>
            <Col>
              {selectedCount > 0 ? `已选择 ${selectedCount} 名候选人` : '请选择候选人后进行批量处理'}
            </Col>
            <Col>
              <Space wrap>
                {candidateScope === 'formal' && (
                  <>
                    <Button
                      size="small"
                      icon={<CheckCircleOutlined />}
                      disabled={!selectedCount}
                      loading={batchLoading === 'backup'}
                      onClick={handleBatchBackup}
                    >
                      批量标记备选
                    </Button>
                    <Button
                      size="small"
                      icon={<CalendarOutlined />}
                      disabled={!selectedCount}
                      loading={batchLoading === 'mark_interview'}
                      onClick={() => handleBatchStatus('待约面', '批量标记待约面', 'mark_interview')}
                    >
                      批量标记待约面
                    </Button>
                  </>
                )}
                {candidateScope !== 'rejected' && (
                  <Button
                    size="small"
                    danger
                    icon={<StopOutlined />}
                    disabled={!selectedCount}
                    loading={batchLoading === 'eliminate'}
                    onClick={() => setEliminateModalOpen(true)}
                  >
                    批量淘汰
                  </Button>
                )}
                <Button
                  size="small"
                  icon={<FileExcelOutlined />}
                  disabled={!selectedCount}
                  loading={batchLoading === 'export'}
                  onClick={handleBatchExport}
                >
                  批量导出CSV
                </Button>
                {candidateScope === 'formal' && (
                  <Button
                    size="small"
                    icon={<RobotOutlined />}
                    disabled={!selectedCount}
                    loading={batchLoading === 'followup'}
                    onClick={handleBatchFollowup}
                  >
                    批量生成AI跟进建议
                  </Button>
                )}
              </Space>
            </Col>
          </Row>
        }
      />

      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        loading={loading}
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: nextPage => { setPage(nextPage); clearSelection(); },
          showTotal: t => `共 ${t} 条`,
        }}
        size="middle"
        rowClassName={record => {
          if (record.is_today_new) return 'candidate-row-today-new';
          if (record.is_recent_3_days_new) return 'candidate-row-recent-new';
          return '';
        }}
        scroll={{ x: 1520 }}
        onRow={record => ({
          style: { cursor: 'pointer' },
          onDoubleClick: () => navigate(`/candidates/${record.id}`),
        })}
      />

      <Modal
        title="确认批量淘汰"
        open={eliminateModalOpen}
        onOk={handleBatchEliminate}
        onCancel={() => { setEliminateModalOpen(false); setEliminateReason(''); }}
        okText="确认淘汰"
        cancelText="取消"
        okButtonProps={{ danger: true, loading: batchLoading === 'eliminate' }}
      >
        <p>即将淘汰 {selectedCount} 名候选人，该操作会影响候选人状态、看板统计和最近操作日志。</p>
        <Input.TextArea
          rows={3}
          placeholder="填写淘汰原因（可选）"
          value={eliminateReason}
          onChange={event => setEliminateReason(event.target.value)}
        />
      </Modal>
    </Card>
  );
};

export default CandidateList;
