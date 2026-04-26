import React from 'react';
import { Card } from 'antd';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { ChannelDistribution } from '../types';
import { CHANNEL_COLORS } from '../utils/constants';

const ChannelPieChart: React.FC<{ data: ChannelDistribution[] }> = ({ data }) => {
  const filtered = data.filter(d => d.count > 0);

  return (
    <Card title="📌 渠道来源分布" style={{ height: '100%' }}>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={filtered}
            dataKey="count"
            nameKey="channel"
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={({ channel, count, percent }) =>
              `${channel}: ${count} (${(percent * 100).toFixed(0)}%)`
            }
            labelLine={{ strokeWidth: 1 }}
          >
            {filtered.map((_, i) => (
              <Cell key={i} fill={CHANNEL_COLORS[i % CHANNEL_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
};

export default ChannelPieChart;
