import React from 'react';
import { Row, Col, Card, Statistic } from 'antd';
import { TeamOutlined, UserAddOutlined, FunnelPlotOutlined, TrophyOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { DashboardStats } from '../types';

const StatsCards: React.FC<{ stats: DashboardStats | null }> = ({ stats }) => {
  if (!stats) return null;

  const items = [
    { title: '总投递人数', value: stats.total_candidates, icon: <TeamOutlined />, color: '#1677ff' },
    { title: '今日新增', value: stats.new_today, icon: <UserAddOutlined />, color: '#52c41a' },
    { title: '最近3天新增', value: stats.new_last_3_days, icon: <ClockCircleOutlined />, color: '#fa8c16' },
    { title: '正式流程候选人', value: stats.formal_candidate_count ?? stats.in_pipeline, icon: <FunnelPlotOutlined />, color: '#722ed1' },
    { title: 'Offer数', value: stats.offer_count, icon: <TrophyOutlined />, color: '#faad14' },
  ];

  return (
    <Row gutter={16}>
      {items.map(item => (
        <Col flex="1 1 180px" key={item.title}>
          <Card hoverable>
            <Statistic
              title={item.title}
              value={item.value}
              prefix={React.cloneElement(item.icon, { style: { color: item.color } })}
              valueStyle={{ color: item.color }}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};

export default StatsCards;
