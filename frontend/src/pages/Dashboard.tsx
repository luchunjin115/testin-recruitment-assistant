import React, { useEffect, useState } from 'react';
import { Row, Col, Spin, Card, Statistic, List, Tag, Space } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import StatsCards from '../components/StatsCards';
import FunnelChart from '../components/FunnelChart';
import ChannelPieChart from '../components/ChannelPieChart';
import FollowUpAlerts from '../components/FollowUpAlerts';
import RecentLogs from '../components/RecentLogs';
import DailySummary from '../components/DailySummary';
import type { DashboardStats, FollowUpAlert, RecentLog, DailySummary as DailySummaryType } from '../types';
import { getDashboardStats, getFollowUpAlerts, getRecentLogs, getDailySummary } from '../api';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [alerts, setAlerts] = useState<FollowUpAlert[]>([]);
  const [logs, setLogs] = useState<RecentLog[]>([]);
  const [summary, setSummary] = useState<DailySummaryType | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    const load = async () => {
      try {
        const [s, a, l, sm] = await Promise.all([
          getDashboardStats(),
          getFollowUpAlerts(),
          getRecentLogs(),
          getDailySummary(),
        ]);
        setStats(s);
        setAlerts(a);
        setLogs(l);
        setSummary(sm);
      } catch (err) {
        console.error('加载看板数据失败', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [location.key]);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>;
  }

  const formatDateTime = (value: string) => {
    if (!value) return '';
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div>
      <StatsCards stats={stats} />
      <Card title="最近新增候选人" style={{ marginTop: 16 }} styles={{ body: { paddingBottom: 8 } }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic title="今日新增人数" value={stats?.new_today || 0} valueStyle={{ color: '#52c41a' }} />
          </Col>
          <Col span={6}>
            <Statistic title="最近3天新增人数" value={stats?.new_last_3_days || 0} valueStyle={{ color: '#fa8c16' }} />
          </Col>
          <Col span={12}>
            <List
              size="small"
              dataSource={stats?.today_new_candidates || []}
              locale={{ emptyText: '今日暂无新增候选人' }}
              renderItem={item => (
                <List.Item style={{ cursor: 'pointer' }} onClick={() => navigate(`/candidates/${item.candidate_id}`)}>
                  <List.Item.Meta
                    title={<span>{item.name} - {item.target_role || '未填写岗位'}</span>}
                    description={`投递时间：${formatDateTime(item.created_at)}`}
                  />
                  <Space>
                    <Tag color="green">{item.new_candidate_label}</Tag>
                    <Tag color={item.source_channel === '在线投递' ? 'green' : item.source_channel === 'HR手动录入' ? 'blue' : 'default'}>
                      {item.source_channel === 'HR手动录入' ? 'HR录入' : item.source_channel || '未知来源'}
                    </Tag>
                  </Space>
                </List.Item>
              )}
            />
          </Col>
        </Row>
      </Card>
      {stats?.screening_stats && (
        <Card title="初筛流转统计" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Statistic title="总投递人数" value={stats.total_candidates} valueStyle={{ color: '#1677ff' }} />
            </Col>
            <Col span={4}>
              <Statistic title="待初筛人数" value={stats.pending_screening_count} valueStyle={{ color: '#d48806' }} />
            </Col>
            <Col span={4}>
              <Statistic title="通过初筛人数" value={stats.passed_screening_count} valueStyle={{ color: '#389e0d' }} />
            </Col>
            <Col span={4}>
              <Statistic title="正式流程备选人数" value={stats.backup_screening_count} valueStyle={{ color: '#1677ff' }} />
            </Col>
            <Col span={4}>
              <Statistic title="淘汰人数" value={stats.rejected_screening_count} valueStyle={{ color: '#cf1322' }} />
            </Col>
            <Col span={4}>
              <Statistic title="正式流程候选人" value={stats.formal_candidate_count} valueStyle={{ color: '#722ed1' }} />
            </Col>
          </Row>
        </Card>
      )}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={14}>
          <FunnelChart data={stats?.funnel || []} />
        </Col>
        <Col span={10}>
          <ChannelPieChart data={stats?.channels || []} />
        </Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <FollowUpAlerts alerts={alerts} />
        </Col>
        <Col span={12}>
          <RecentLogs logs={logs} />
        </Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="今日建议跟进" style={{ height: '100%' }} styles={{ body: { maxHeight: 320, overflow: 'auto' } }}>
            <Row gutter={16} style={{ marginBottom: 12 }}>
              <Col span={6}>
                <Statistic title="超时未跟进" value={stats?.followup_summary?.overdue_count || 0} valueStyle={{ color: '#cf1322' }} />
              </Col>
              <Col span={6}>
                <Statistic title="今日待跟进" value={stats?.followup_summary?.today_followup_count || 0} valueStyle={{ color: '#1677ff' }} />
              </Col>
              <Col span={6}>
                <Statistic title="高优先级跟进" value={stats?.followup_summary?.high_priority_count || 0} valueStyle={{ color: '#cf1322' }} />
              </Col>
              <Col span={6}>
                <Statistic title="超过3天未跟进" value={stats?.followup_summary?.stale_count || 0} valueStyle={{ color: '#d48806' }} />
              </Col>
            </Row>
            <List
              size="small"
              dataSource={stats?.followup_summary?.items || []}
              locale={{ emptyText: '暂无需要重点跟进的候选人' }}
              renderItem={item => (
                <List.Item style={{ cursor: 'pointer' }} onClick={() => navigate(`/candidates/${item.candidate_id}`)}>
                  <List.Item.Meta
                    title={<span>{item.name} - {item.target_role || '未填写岗位'}</span>}
                    description={item.is_overdue ? item.overdue_reason : item.followup_reason}
                  />
                  <Space>
                    {item.is_overdue && <Tag color="red">超时 {item.overdue_days}天</Tag>}
                    <Tag color={item.followup_priority === '高' ? 'red' : item.followup_priority === '中' ? 'gold' : 'default'}>
                      {item.followup_priority}
                    </Tag>
                    {item.followup_days_since_update >= 3 && <Tag color="orange">{item.followup_days_since_update}天未更新</Tag>}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="岗位分布" style={{ height: '100%' }} styles={{ body: { maxHeight: 320, overflow: 'auto' } }}>
            <List
              size="small"
              dataSource={stats?.role_distribution || []}
              locale={{ emptyText: '暂无岗位数据' }}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta title={item.target_role} />
                  <Space>
                    <Tag color="blue">{item.count}人</Tag>
                    <Tag color="red">高优先级 {item.high_priority_count}</Tag>
                    <Tag color="orange">待跟进 {item.followup_count}</Tag>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
      <div style={{ marginTop: 16 }}>
        <DailySummary summary={summary} />
      </div>
    </div>
  );
};

export default Dashboard;
