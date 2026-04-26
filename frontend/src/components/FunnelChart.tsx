import React from 'react';
import { Card } from 'antd';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';
import type { FunnelStage } from '../types';
import { STAGE_COLORS } from '../utils/constants';

const FunnelChart: React.FC<{ data: FunnelStage[] }> = ({ data }) => {
  const filtered = data.filter(d => d.count > 0 || ['新投递', '初筛', '待约面', '面试中', 'offer'].includes(d.stage));

  return (
    <Card title="📊 招聘漏斗" style={{ height: '100%' }}>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={filtered} layout="vertical" margin={{ left: 20, right: 30, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis type="category" dataKey="stage" width={70} tick={{ fontSize: 13 }} />
          <Tooltip formatter={(value: number) => [`${value} 人`, '候选人数']} />
          <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={28}>
            {filtered.map((entry) => (
              <Cell key={entry.stage} fill={STAGE_COLORS[entry.stage] || '#1890ff'} />
            ))}
            <LabelList dataKey="count" position="right" style={{ fontSize: 12, fill: '#666' }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
};

export default FunnelChart;
