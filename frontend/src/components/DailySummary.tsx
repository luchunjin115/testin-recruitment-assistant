import React from 'react';
import { Card, Statistic, Row, Col, Typography } from 'antd';
import { CalendarOutlined, RiseOutlined } from '@ant-design/icons';
import type { DailySummary as DailySummaryType } from '../types';

const { Paragraph } = Typography;

const DailySummary: React.FC<{ summary: DailySummaryType | null }> = ({ summary }) => {
  if (!summary) return null;

  return (
    <Card title="📋 今日招聘总结">
      <Row gutter={24}>
        <Col span={4}>
          <Statistic title="日期" value={summary.date} prefix={<CalendarOutlined />} valueStyle={{ fontSize: 16 }} />
        </Col>
        <Col span={4}>
          <Statistic title="新增候选人" value={summary.new_count} suffix="位" valueStyle={{ color: '#52c41a' }} />
        </Col>
        <Col span={4}>
          <Statistic title="状态变更" value={summary.stage_changes} suffix="次" prefix={<RiseOutlined />} valueStyle={{ color: '#1677ff' }} />
        </Col>
        <Col span={12}>
          <div style={{ paddingTop: 8 }}>
            <strong>AI总结：</strong>
            <Paragraph style={{ marginTop: 4, color: '#555' }}>{summary.summary_text}</Paragraph>
          </div>
        </Col>
      </Row>
    </Card>
  );
};

export default DailySummary;
