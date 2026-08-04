import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  InboxOutlined,
  ReloadOutlined,
  SearchOutlined,
  SyncOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { Alert, Button, Empty, Input, Select, Skeleton, Tag, Tooltip } from 'antd';
import {
  getStage3Resumes,
  ResumeListSnapshot,
  ResumeParseStatus,
} from './services/resumes';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ResumeListSnapshot };

const statusMeta: Record<ResumeParseStatus, { label: string; tone: string }> = {
  uploaded: { label: '已上传', tone: 'neutral' },
  parsing: { label: '解析中', tone: 'info' },
  parsed: { label: '已解析', tone: 'success' },
  failed: { label: '解析失败', tone: 'warning' },
};

const formatFileSize = (size: number | null) => {
  if (size === null) return '大小未记录';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
};

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}).format(new Date(value));

const Stage3ResumeList: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [keyword, setKeyword] = useState('');
  const [parseStatus, setParseStatus] = useState<ResumeParseStatus | 'all'>('all');

  const loadResumes = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      const data = await getStage3Resumes();
      setLoadState({ status: 'ready', data });
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法连接新版简历接口',
      });
    }
  }, []);

  useEffect(() => {
    void loadResumes();
  }, [loadResumes]);

  const filteredItems = useMemo(() => {
    if (loadState.status !== 'ready') return [];
    const normalizedKeyword = keyword.trim().toLowerCase();

    return loadState.data.items.filter(item => {
      const matchesStatus = parseStatus === 'all' || item.parseStatus === parseStatus;
      const matchesKeyword = !normalizedKeyword || [item.filename, item.candidateName, item.jobTitle]
        .some(value => value.toLowerCase().includes(normalizedKeyword));
      return matchesStatus && matchesKeyword;
    });
  }, [keyword, loadState, parseStatus]);

  const resetFilters = () => {
    setKeyword('');
    setParseStatus('all');
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="简历列表加载中" className="s3-main">
        <section className="s3-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="s3-stat-grid">
          {[0, 1, 2, 3].map(item => <article className="s3-stat-card" key={item}><Skeleton active paragraph={false} /></article>)}
        </section>
        <section className="s3-state-panel"><Skeleton active paragraph={{ rows: 6 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="s3-main">
        <section className="s3-page-heading">
          <div><span className="s3-section-kicker">新版简历库 · 数据来源 /api/v2</span><h2>简历管理</h2><p>集中查看简历文件和解析状态。</p></div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadResumes()}>重新加载</Button>}
          className="s3-dashboard-alert s3-section-gap"
          description={`请确认 FastAPI 已启动，且 /api/v2/resumes 可访问。技术信息：${loadState.message}`}
          message="新版简历数据加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const stats = [
    { label: '简历总数', value: data.total, note: '新版简历表真实记录', icon: <FileTextOutlined />, tone: 'blue' },
    { label: '等待解析', value: data.uploaded, note: '状态：uploaded', icon: <InboxOutlined />, tone: 'orange' },
    { label: '正在解析', value: data.parsing, note: '状态：parsing', icon: <SyncOutlined />, tone: 'blue' },
    { label: '解析异常', value: data.failed, note: `已解析 ${data.parsed} 份`, icon: <CloseCircleOutlined />, tone: 'red' },
  ];

  return (
    <main className="s3-main">
      <section className="s3-page-heading">
        <div>
          <span className="s3-section-kicker">新版简历库 · 数据来源 /api/v2</span>
          <h2>简历管理</h2>
          <p>查看简历文件、关联候选人和解析状态；上传与解析能力将在后续阶段接入。</p>
        </div>
        <Tooltip title="简历上传属于阶段 4，本页暂不提供写入操作">
          <Button disabled icon={<UploadOutlined />} type="primary">上传简历 · 阶段 4</Button>
        </Tooltip>
      </section>

      <section aria-label="简历状态统计" className="s3-stat-grid">
        {stats.map(stat => (
          <article className="s3-stat-card" key={stat.label}>
            <div className={`s3-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="s3-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      <section className="s3-panel s3-resume-panel">
        <div className="s3-resume-toolbar">
          <div>
            <h3>简历列表</h3>
            <p>按上传时间倒序排列，共 {data.total} 份真实记录</p>
          </div>
          <div className="s3-filter-controls">
            <Input
              allowClear
              aria-label="搜索简历"
              onChange={event => setKeyword(event.target.value)}
              placeholder="搜索文件、候选人或岗位"
              prefix={<SearchOutlined />}
              value={keyword}
            />
            <Select
              aria-label="按解析状态筛选"
              onChange={setParseStatus}
              options={[
                { value: 'all', label: '全部状态' },
                { value: 'uploaded', label: '已上传' },
                { value: 'parsing', label: '解析中' },
                { value: 'parsed', label: '已解析' },
                { value: 'failed', label: '解析失败' },
              ]}
              value={parseStatus}
            />
            <Button aria-label="刷新简历列表" icon={<ReloadOutlined />} onClick={() => void loadResumes()} />
          </div>
        </div>

        {data.total === 0 ? (
          <Empty
            className="s3-panel-empty s3-resume-empty"
            description={
              <div className="s3-empty-copy">
                <strong>新版简历库目前没有简历</strong>
                <span>页面已成功连接 /api/v2/resumes；阶段 4 接入上传后，新简历会显示在这里。</span>
              </div>
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : filteredItems.length === 0 ? (
          <Empty
            className="s3-panel-empty s3-resume-empty"
            description="没有符合当前搜索和状态条件的简历"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button onClick={resetFilters}>清除筛选</Button>
          </Empty>
        ) : (
          <div aria-label="新版简历列表" className="s3-table" role="table">
            <div className="s3-table-head s3-resume-table-columns" role="row">
              <span>简历文件</span><span>候选人</span><span>关联岗位</span><span>文件信息</span><span>解析状态</span><span>上传时间</span>
            </div>
            {filteredItems.map(item => (
              <div className="s3-table-row s3-resume-table-columns" key={item.id} role="row">
                <div className="s3-resume-file-cell">
                  <span className="s3-file-icon"><FileTextOutlined /></span>
                  <div><strong title={item.filename}>{item.filename}</strong><span>简历 #{item.id}</span></div>
                </div>
                <div className="s3-resume-secondary"><strong>{item.candidateName}</strong><span>候选人 #{item.candidateId}</span></div>
                <span className="s3-role-cell">{item.jobTitle}</span>
                <div className="s3-resume-secondary"><strong>{item.fileType?.toUpperCase() || '类型未记录'}</strong><span>{formatFileSize(item.fileSize)}</span></div>
                <div>
                  <Tag bordered={false} className={`s3-status-tag is-${statusMeta[item.parseStatus].tone}`}>
                    {item.parseStatus === 'parsed' && <CheckCircleOutlined />} {statusMeta[item.parseStatus].label}
                  </Tag>
                  {item.parseError && <span className="s3-parse-error" title={item.parseError}>查看失败原因</span>}
                </div>
                <span className="s3-time-cell">{formatDateTime(item.uploadedAt)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
};

export default Stage3ResumeList;
