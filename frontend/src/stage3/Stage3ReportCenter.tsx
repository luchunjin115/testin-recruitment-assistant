import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowRightOutlined,
  ExportOutlined,
  EyeOutlined,
  FileAddOutlined,
  FileTextOutlined,
  LinkOutlined,
  ReloadOutlined,
  SearchOutlined,
  SolutionOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Alert, Button, Drawer, Empty, Input, Select, Skeleton, Tag, Tooltip } from 'antd';
import { Link } from 'react-router-dom';
import {
  getStage3Reports,
  ReportCenterSnapshot,
  Stage3Report,
} from './services/reports';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ReportCenterSnapshot };

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}).format(new Date(value));

const getReportTypeLabel = (value: string) => {
  if (value.toLowerCase() === 'screening') return '初筛报告';
  return value || '类型未记录';
};

const getFormatLabel = (value: string) => {
  if (value.toLowerCase() === 'markdown') return 'Markdown';
  return value ? value.toUpperCase() : '格式未记录';
};

const Stage3ReportCenter: React.FC = () => {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [keyword, setKeyword] = useState('');
  const [jobFilter, setJobFilter] = useState<number | 'all'>('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [selectedReport, setSelectedReport] = useState<Stage3Report | null>(null);

  const loadReports = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      setLoadState({ status: 'ready', data: await getStage3Reports() });
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : '无法连接新版报告接口',
      });
    }
  }, []);

  useEffect(() => {
    void loadReports();
  }, [loadReports]);

  const typeOptions = useMemo(() => {
    if (loadState.status !== 'ready') return [{ value: 'all', label: '全部报告类型' }];
    return [
      { value: 'all', label: '全部报告类型' },
      ...Array.from(new Set(loadState.data.items.map(item => item.reportType)))
        .sort()
        .map(value => ({ value, label: getReportTypeLabel(value) })),
    ];
  }, [loadState]);

  const filteredItems = useMemo(() => {
    if (loadState.status !== 'ready') return [];
    const normalizedKeyword = keyword.trim().toLowerCase();
    return loadState.data.items.filter(item => {
      const matchesJob = jobFilter === 'all' || item.jobId === jobFilter;
      const matchesType = typeFilter === 'all' || item.reportType === typeFilter;
      const matchesKeyword = !normalizedKeyword || [
        item.title,
        item.candidateName,
        item.jobTitle,
        item.content,
      ].some(value => value.toLowerCase().includes(normalizedKeyword));
      return matchesJob && matchesType && matchesKeyword;
    });
  }, [jobFilter, keyword, loadState, typeFilter]);

  const resetFilters = () => {
    setKeyword('');
    setJobFilter('all');
    setTypeFilter('all');
  };

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="初筛报告加载中" className="s3-main">
        <section className="s3-page-heading"><Skeleton active paragraph={{ rows: 2 }} /></section>
        <section className="s3-stat-grid">
          {[0, 1, 2, 3].map(item => <article className="s3-stat-card" key={item}><Skeleton active paragraph={false} /></article>)}
        </section>
        <section className="s3-state-panel"><Skeleton active paragraph={{ rows: 7 }} /></section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="s3-main">
        <section className="s3-page-heading">
          <div><span className="s3-section-kicker">新版报告库 · 只读</span><h2>初筛报告</h2><p>集中查看已经保存的报告，不在本页生成新内容。</p></div>
        </section>
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadReports()}>重新加载</Button>}
          className="s3-dashboard-alert s3-section-gap"
          description={`请确认 FastAPI 已启动，且 /api/v2/reports、/api/v2/candidates、/api/v2/jobs 与 /api/v2/screening-results 可访问。技术信息：${loadState.message}`}
          message="新版初筛报告数据加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const linkedScreeningCount = data.items.filter(item => item.screeningId !== null).length;
  const coveredCandidateCount = new Set(data.items.map(item => item.candidateId)).size;
  const coveredJobCount = new Set(data.items.map(item => item.jobId)).size;
  const stats = [
    { label: '初筛报告', value: data.totalReports, note: '新版 reports 表真实记录', icon: <FileTextOutlined />, tone: 'blue' },
    { label: '已关联初筛', value: linkedScreeningCount, note: `已有初筛结果 ${data.totalScreeningResults} 条`, icon: <LinkOutlined />, tone: 'green' },
    { label: '覆盖候选人', value: coveredCandidateCount, note: `候选人库共 ${data.totalCandidates} 人`, icon: <TeamOutlined />, tone: 'orange' },
    { label: '覆盖岗位', value: coveredJobCount, note: `岗位库共 ${data.totalJobs} 个`, icon: <SolutionOutlined />, tone: 'red' },
  ];

  return (
    <main className="s3-main">
      <section className="s3-page-heading">
        <div>
          <span className="s3-section-kicker">新版报告库 · 数据来源 /api/v2 · 只读</span>
          <h2>初筛报告</h2>
          <p>查看已保存的报告正文和业务关联；本页不会生成报告、调用 LLM 或导出文件。</p>
        </div>
        <Tooltip title="报告生成属于后续 report_gen 工作流，本步不开放">
          <Button disabled icon={<FileAddOutlined />} type="primary">生成报告 · 后续</Button>
        </Tooltip>
      </section>

      <section aria-label="初筛报告统计" className="s3-stat-grid">
        {stats.map(stat => (
          <article className="s3-stat-card" key={stat.label}>
            <div className={`s3-stat-icon is-${stat.tone}`}>{stat.icon}</div>
            <div className="s3-stat-content"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
          </article>
        ))}
      </section>

      <section className="s3-panel s3-report-panel">
        <div className="s3-report-toolbar">
          <div>
            <h3>报告列表</h3>
            <p>按更新时间倒序排列，共 {data.totalReports} 条真实报告记录</p>
          </div>
          <div className="s3-report-filter-controls">
            <Input
              allowClear
              aria-label="搜索初筛报告"
              onChange={event => setKeyword(event.target.value)}
              placeholder="搜索报告、候选人或岗位"
              prefix={<SearchOutlined />}
              value={keyword}
            />
            <Select
              aria-label="按岗位筛选报告"
              onChange={setJobFilter}
              options={[
                { value: 'all', label: '全部岗位' },
                ...data.jobs.map(job => ({ value: job.id, label: `${job.title}（${job.reportCount}）` })),
              ]}
              showSearch
              optionFilterProp="label"
              value={jobFilter}
            />
            <Select
              aria-label="按报告类型筛选"
              onChange={setTypeFilter}
              options={typeOptions}
              value={typeFilter}
            />
            <Button aria-label="刷新初筛报告" icon={<ReloadOutlined />} onClick={() => void loadReports()} />
          </div>
        </div>

        {data.totalReports === 0 ? (
          <Empty
            className="s3-panel-empty s3-report-empty"
            description={(
              <div className="s3-empty-copy">
                <strong>新版报告库目前没有初筛报告</strong>
                <span>页面已连接 /api/v2/reports；筛选结果与报告是不同记录，当前不会自动把结果转换成报告。</span>
              </div>
            )}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <div className="s3-report-data-boundary" aria-label="初筛结果和报告数量对比">
              <span>已有初筛结果 <strong>{data.totalScreeningResults}</strong> 条</span>
              <ArrowRightOutlined />
              <span>已生成报告 <strong>{data.totalReports}</strong> 条</span>
            </div>
            <Button disabled icon={<FileAddOutlined />}>报告生成能力 · 后续</Button>
          </Empty>
        ) : filteredItems.length === 0 ? (
          <Empty
            className="s3-panel-empty s3-report-empty"
            description={(
              <div className="s3-empty-copy">
                <strong>已有报告，但当前筛选条件没有匹配项</strong>
                <span>可以清除关键词、岗位和报告类型筛选，查看已有报告。</span>
              </div>
            )}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button onClick={resetFilters}>清除筛选</Button>
          </Empty>
        ) : (
          <div aria-label="新版初筛报告列表" className="s3-report-list" role="list">
            {filteredItems.map(item => (
              <article className="s3-report-item" key={item.id} role="listitem">
                <div className="s3-report-item-main">
                  <span className="s3-report-file-mark"><FileTextOutlined /></span>
                  <div className="s3-report-title">
                    <strong>{item.title}</strong>
                    <span>报告 #{item.id} · {item.candidateSource || '来源未填写'}</span>
                  </div>
                  <div className="s3-report-person">
                    <Link to={`/stage3/candidates/${item.candidateId}`}>{item.candidateName}</Link>
                    <span>{item.jobTitle}</span>
                  </div>
                  <div className="s3-report-tags">
                    <Tag bordered={false} className="s3-status-tag is-info">{getReportTypeLabel(item.reportType)}</Tag>
                    <Tag bordered={false}>{getFormatLabel(item.format)}</Tag>
                  </div>
                  <div className="s3-report-updated"><span>更新时间</span><strong>{formatDateTime(item.updatedAt)}</strong></div>
                  <Button icon={<EyeOutlined />} onClick={() => setSelectedReport(item)} size="small">查看报告</Button>
                </div>
                <div className="s3-report-preview">
                  <p>{item.content}</p>
                  <div>
                    <span>{item.screeningId === null ? '未关联筛选结果' : `关联筛选结果 #${item.screeningId}`}</span>
                    <span>匹配分 {item.screeningScore ?? '—'}</span>
                    <span>{item.screeningRecommendation || '推荐结果未记录'}</span>
                    <span>生成于 {formatDateTime(item.generatedAt)}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <Drawer
        className="s3-report-viewer-drawer"
        extra={(
          <div className="s3-report-viewer-actions">
            <Button onClick={() => setSelectedReport(null)}>关闭</Button>
            <Button disabled icon={<ExportOutlined />} type="primary">导出 · 后续</Button>
          </div>
        )}
        onClose={() => setSelectedReport(null)}
        open={selectedReport !== null}
        title={selectedReport?.title || '初筛报告'}
        width="min(720px, 100vw)"
      >
        {selectedReport && (
          <div className="s3-report-viewer">
            <Alert
              description="当前按数据库原文只读展示，不执行 Markdown 渲染、内容生成或文件导出。"
              message="报告查看骨架"
              showIcon
              type="info"
            />
            <div className="s3-report-viewer-meta">
              <div><span>候选人</span><Link to={`/stage3/candidates/${selectedReport.candidateId}`}>{selectedReport.candidateName}</Link></div>
              <div><span>应聘岗位</span><strong>{selectedReport.jobTitle}</strong></div>
              <div><span>报告类型</span><strong>{getReportTypeLabel(selectedReport.reportType)}</strong></div>
              <div><span>存储格式</span><strong>{getFormatLabel(selectedReport.format)}</strong></div>
              <div><span>关联筛选</span><strong>{selectedReport.screeningId === null ? '未关联' : `#${selectedReport.screeningId}`}</strong></div>
              <div><span>更新时间</span><strong>{formatDateTime(selectedReport.updatedAt)}</strong></div>
            </div>
            <article className="s3-report-content">
              <span>报告正文</span>
              <pre>{selectedReport.content}</pre>
            </article>
            <article className="s3-report-metadata">
              <span>报告元数据</span>
              <pre>{selectedReport.metadata ? JSON.stringify(selectedReport.metadata, null, 2) : '未记录报告元数据'}</pre>
            </article>
          </div>
        )}
      </Drawer>
    </main>
  );
};

export default Stage3ReportCenter;
