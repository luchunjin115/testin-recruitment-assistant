import React, { useCallback, useEffect, useState } from 'react';
import { FileSearchOutlined, FilterOutlined, ReloadOutlined, SearchOutlined, UserAddOutlined } from '@ant-design/icons';
import { Alert, Button, Empty, Input, Pagination, Select, Skeleton } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ApplicationEvidenceTable from './ApplicationEvidenceTable';
import ApplicationScreeningDrawer from './ApplicationScreeningDrawer';
import { getRecruitmentJobs, type RecruitmentJob } from './services/jobs';
import { getPublicApplicationSubmission, type PublicApplicationWorkbenchSummary } from './services/publicApplicationWorkbench';
import { getScreeningCenterError, listScreeningCenterApplications, type ScreeningCenterItem, type ScreeningCenterPage, type ScreeningCenterSort, type ScreeningCenterSource, type ScreeningCenterStage } from './services/screeningCenter';

type LoadState = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: ScreeningCenterPage };
type CandidateStage = Extract<ScreeningCenterStage, 'screening_passed' | 'interview' | 'offer' | 'offer_accepted' | 'admitted' | 'hired'> | 'all';
type FilterState = {
  keyword: string;
  jobId: number | 'all';
  source: ScreeningCenterSource | 'all';
  stage: CandidateStage;
  sort: ScreeningCenterSort;
};

const INITIAL_FILTERS: FilterState = { keyword: '', jobId: 'all', source: 'all', stage: 'all', sort: 'updated_desc' };
const SOURCE_LABELS: Record<ScreeningCenterSource, string> = { hr_direct: 'HR 直通', hr_screening: '内部初筛通过', public_apply: '公开投递通过' };
const STAGE_OPTIONS: Array<{ value: CandidateStage; label: string }> = [
  { value: 'all', label: '全部招聘阶段' },
  { value: 'screening_passed', label: '待安排面试' },
  { value: 'interview', label: '面试中' },
  { value: 'offer', label: 'Offer 沟通' },
  { value: 'offer_accepted', label: 'Offer 已接受' },
  { value: 'admitted', label: '已录取待入职' },
  { value: 'hired', label: '已正式入职' },
];

const RecruitmentCandidateList: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLinkedApplicationId = Number(searchParams.get('application_id'));
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [jobs, setJobs] = useState<RecruitmentJob[]>([]);
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [keywordInput, setKeywordInput] = useState('');
  const [page, setPage] = useState(1);
  const [selectedItem, setSelectedItem] = useState<ScreeningCenterItem | null>(null);
  const [publicSubmission, setPublicSubmission] = useState<PublicApplicationWorkbenchSummary | null>(null);

  const load = useCallback(async () => {
    setLoadState({ status: 'loading' });
    try {
      const hasDeepLink = Number.isInteger(deepLinkedApplicationId) && deepLinkedApplicationId > 0;
      const data = await listScreeningCenterApplications({
        view: 'candidate',
        page,
        pageSize: 30,
        applicationId: hasDeepLink ? deepLinkedApplicationId : undefined,
        keyword: hasDeepLink ? undefined : filters.keyword || undefined,
        jobId: hasDeepLink || filters.jobId === 'all' ? undefined : filters.jobId,
        source: hasDeepLink || filters.source === 'all' ? undefined : filters.source,
        stage: hasDeepLink || filters.stage === 'all' ? undefined : filters.stage,
        sort: filters.sort,
      });
      setLoadState({ status: 'ready', data });
      if (hasDeepLink) setSelectedItem(data.items[0] ?? null);
    } catch (error) {
      setLoadState({ status: 'error', message: getScreeningCenterError(error) });
    }
  }, [deepLinkedApplicationId, filters, page]);

  const refreshApplicationSummary = useCallback(() => {
    void load();
  }, [load]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void getRecruitmentJobs().then(value => setJobs(value.items)).catch(() => setJobs([])); }, []);
  useEffect(() => {
    if (!selectedItem?.submissionId) { setPublicSubmission(null); return undefined; }
    let cancelled = false;
    void getPublicApplicationSubmission(selectedItem.submissionId)
      .then(value => { if (!cancelled) setPublicSubmission(value); })
      .catch(() => { if (!cancelled) setPublicSubmission(null); });
    return () => { cancelled = true; };
  }, [selectedItem?.submissionId]);

  const openDetail = (item: ScreeningCenterItem) => {
    setSelectedItem(item);
    setPublicSubmission(null);
    setSearchParams({ application_id: String(item.applicationId) }, { replace: true });
  };
  const closeDetail = () => { setSelectedItem(null); setPublicSubmission(null); setSearchParams({}, { replace: true }); };
  const applySearch = () => { setPage(1); setFilters(value => ({ ...value, keyword: keywordInput.trim() })); };
  const clearFilters = () => { setKeywordInput(''); setFilters(INITIAL_FILTERS); setPage(1); };
  const items = loadState.status === 'ready' ? loadState.data.items : [];
  const hasFilters = JSON.stringify(filters) !== JSON.stringify(INITIAL_FILTERS);

  return (
    <main className="recruitment-main recruitment-candidate-pipeline-page">
      <section className="recruitment-page-heading">
        <div><span className="recruitment-section-kicker">HR 初筛通过 → 面试 → Offer → 入职</span><h2>候选人</h2><p>每一行代表候选人对一个岗位的招聘进程，面试、Offer 和入职均从详情中推进。</p></div>
        <Button icon={<UserAddOutlined />} onClick={() => navigate('/app/candidates/new')} type="primary">新增直通候选人</Button>
      </section>
      <section aria-label="候选人页面准入规则" className="recruitment-candidate-entry-rule is-compact">
        <strong>准入规则</strong><span>只有 HR 明确通过初筛的岗位申请显示在这里</span><i />
        <span>AI 报告仍是辅助证据</span><i /><span>面试、Offer、录取和入职在详情中操作</span>
      </section>
      <section className="recruitment-panel recruitment-candidate-pipeline-panel">
        <div className="recruitment-screening-toolbar is-table-toolbar">
          <div className="recruitment-screening-toolbar-heading"><h3>候选人列表</h3><p>{loadState.status === 'ready' ? `共 ${loadState.data.total} 份已通过的岗位申请` : '正在读取候选人'}</p></div>
          <div className="recruitment-screening-quick-filters">
            <Input allowClear aria-label="搜索候选人岗位申请" onChange={event => setKeywordInput(event.target.value)} onPressEnter={applySearch} placeholder="姓名 / 联系方式 / 岗位 / 申请编号" prefix={<SearchOutlined />} value={keywordInput} />
            <Select aria-label="按岗位筛选候选人" value={filters.jobId} onChange={jobId => { setPage(1); setFilters(value => ({ ...value, jobId })); }} options={[{ value: 'all', label: '全部岗位' }, ...jobs.map(job => ({ value: job.id, label: job.title }))]} />
            <Select aria-label="按招聘阶段筛选候选人" value={filters.stage} onChange={stage => { setPage(1); setFilters(value => ({ ...value, stage })); }} options={STAGE_OPTIONS} />
            <Button icon={<SearchOutlined />} onClick={applySearch} type="primary">搜索</Button>
            <Button aria-label="刷新候选人列表" icon={<ReloadOutlined />} onClick={() => void load()} />
          </div>
        </div>
        <details className="recruitment-screening-advanced-filters">
          <summary><FilterOutlined /> 更多筛选</summary>
          <div className="recruitment-screening-filter-controls">
            <Select aria-label="按来源筛选候选人" value={filters.source} onChange={source => { setPage(1); setFilters(value => ({ ...value, source })); }} options={[{ value: 'all', label: '全部来源' }, ...Object.entries(SOURCE_LABELS).map(([value, label]) => ({ value, label }))]} />
            <Select aria-label="候选人排序方式" value={filters.sort} onChange={sort => setFilters(value => ({ ...value, sort }))} options={[{ value: 'updated_desc', label: '最近进展' }, { value: 'applied_desc', label: '最近通过' }, { value: 'score_desc', label: 'AI 分数从高到低' }, { value: 'score_asc', label: 'AI 分数从低到高' }]} />
            {hasFilters && <Button onClick={clearFilters}>清除全部筛选</Button>}
          </div>
        </details>
        {loadState.status === 'loading' && <div className="recruitment-screening-loading"><Skeleton active paragraph={{ rows: 10 }} /></div>}
        {loadState.status === 'error' && <Alert className="recruitment-screening-inline-alert" action={<Button onClick={() => void load()}>重试</Button>} description={loadState.message} message="候选人列表读取失败" showIcon type="error" />}
        {loadState.status === 'ready' && items.length === 0 && <Empty className="recruitment-screening-empty" image={<FileSearchOutlined />} description="当前没有符合条件的已通过候选人" />}
        {loadState.status === 'ready' && items.length > 0 && <ApplicationEvidenceTable items={items} mode="candidate" onOpen={openDetail} />}
        {loadState.status === 'ready' && loadState.data.total > loadState.data.pageSize && <Pagination className="recruitment-application-pagination" current={loadState.data.page} pageSize={loadState.data.pageSize} total={loadState.data.total} showSizeChanger={false} onChange={setPage} />}
      </section>
      <ApplicationScreeningDrawer applicationId={selectedItem?.applicationId ?? null} candidateName={selectedItem?.candidateName ?? ''} currentResumeId={selectedItem?.resumeId ?? null} initialState={null} jobId={selectedItem?.jobId ?? null} jobStatus={selectedItem?.jobStatus ?? null} jobTitle={selectedItem?.jobTitle ?? ''} open={selectedItem !== null} onClose={closeDetail} onStateChange={refreshApplicationSummary} onPipelineChange={load} onPublicSubmissionChange={setPublicSubmission} onCurrentResumeChange={refreshApplicationSummary} publicSubmission={publicSubmission} summary={selectedItem} workspace="candidate" />
    </main>
  );
};

export default RecruitmentCandidateList;
