import React from 'react';
import { Tag } from 'antd';
import { STAGE_COLORS } from '../utils/constants';

const StageTag: React.FC<{ stage: string }> = ({ stage }) => (
  <Tag color={STAGE_COLORS[stage] || '#1890ff'}>{stage}</Tag>
);

export default StageTag;
