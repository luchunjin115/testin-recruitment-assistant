import React from 'react';
import { Card, List, Tag, Empty } from 'antd';
import { WarningOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { FollowUpAlert } from '../types';
import StageTag from './StageTag';

const FollowUpAlerts: React.FC<{ alerts: FollowUpAlert[] }> = ({ alerts }) => {
  const navigate = useNavigate();

  return (
    <Card
      title={<span><WarningOutlined style={{ color: '#faad14' }} /> 跟进预警 ({alerts.length})</span>}
      style={{ height: '100%' }}
      styles={{ body: { maxHeight: 280, overflow: 'auto' } }}
    >
      {alerts.length === 0 ? (
        <Empty description="暂无预警，所有候选人均已及时跟进" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          dataSource={alerts}
          renderItem={item => (
            <List.Item
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(`/candidates/${item.candidate_id}`)}
            >
              <List.Item.Meta
                title={<span>{item.name} - {item.target_role}</span>}
                description={
                  <div>
                    <StageTag stage={item.stage} />
                    <div style={{ marginTop: 4, color: '#666', fontSize: 12 }}>
                      {item.overdue_reason || item.followup_suggestion}
                    </div>
                  </div>
                }
              />
              <div style={{ textAlign: 'right' }}>
                <Tag color={item.followup_priority === '高' ? 'red' : item.followup_priority === '中' ? 'gold' : 'default'}>
                  {item.followup_priority}优先级
                </Tag>
                <Tag color="red">超时 {item.overdue_days}天</Tag>
              </div>
            </List.Item>
          )}
        />
      )}
    </Card>
  );
};

export default FollowUpAlerts;
