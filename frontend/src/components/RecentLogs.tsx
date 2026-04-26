import React from 'react';
import { Card, Timeline, Empty, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import type { RecentLog } from '../types';
import { STAGE_SOURCE_LABELS } from '../utils/constants';
import StageTag from './StageTag';

const ACTION_COLORS: Record<string, string> = {
  created: 'green',
  stage_changed: 'blue',
  ai_processed: 'purple',
  ai_interview_summary: 'purple',
  updated: 'orange',
  duplicate_found: 'red',
};

const RecentLogs: React.FC<{ logs: RecentLog[] }> = ({ logs }) => {
  const navigate = useNavigate();

  return (
    <Card
      title="🕐 最近操作日志"
      style={{ height: '100%' }}
      styles={{ body: { maxHeight: 280, overflow: 'auto' } }}
    >
      {logs.length === 0 ? (
        <Empty description="暂无操作记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Timeline
          items={logs.map(log => ({
            color: ACTION_COLORS[log.action] || 'gray',
            children: (
              <div>
                <div style={{ marginBottom: 4 }}>
                  <Tag
                    color="blue"
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/candidates/${log.candidate_id}`)}
                  >
                    {log.candidate_name}
                  </Tag>
                  {log.action === 'stage_changed' && log.from_stage && log.to_stage ? (
                    <>
                      <StageTag stage={log.from_stage} />
                      <span style={{ margin: '0 4px', color: '#999' }}>&rarr;</span>
                      <StageTag stage={log.to_stage} />
                      {log.trigger_source && (
                        <Tag
                          color={log.trigger_source === 'manual' ? 'orange' : log.trigger_source === 'hr_action' ? 'blue' : 'default'}
                          style={{ marginLeft: 4 }}
                        >
                          {STAGE_SOURCE_LABELS[log.trigger_source] || log.trigger_source}
                        </Tag>
                      )}
                    </>
                  ) : (
                    <span style={{ fontSize: 13 }}>{log.detail}</span>
                  )}
                </div>
                {log.action === 'stage_changed' && log.trigger_reason ? (
                  <div style={{ fontSize: 13, color: '#555', marginBottom: 4 }}>
                    {log.trigger_reason}
                  </div>
                ) : null}
                {log.action !== 'stage_changed' ? null : (
                  <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>
                    候选人 ID: {log.candidate_id}
                  </div>
                )}
                <span style={{ color: '#999', fontSize: 12 }}>
                  {log.updated_at ? dayjs(log.updated_at).format('MM-DD HH:mm') : log.created_at ? dayjs(log.created_at).format('MM-DD HH:mm') : ''}
                </span>
              </div>
            ),
          }))}
        />
      )}
    </Card>
  );
};

export default RecentLogs;
