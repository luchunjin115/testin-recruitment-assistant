import React, { useCallback, useEffect, useState } from 'react';
import {
  ArrowLeftOutlined,
  BankOutlined,
  BookOutlined,
  FileTextOutlined,
  MailOutlined,
  ProjectOutlined,
  ReloadOutlined,
  RobotOutlined,
  SolutionOutlined,
  UserOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { Alert, Avatar, Button, Empty, Result, Skeleton, Tag } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { getCandidateStatusMeta } from './candidateStatus';
import {
  CandidateDetailData,
  getStage3CandidateDetail,
} from './services/candidateDetail';

type LoadState =
  | { status: 'loading' }
  | { status: 'notFound' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: CandidateDetailData };

const formatDateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
}).format(new Date(value));

const formatPeriod = (start: string | null, end: string | null) => {
  if (!start && !end) return '时间未填写';
  return `${start || '开始时间未填写'} — ${end || '至今'}`;
};

const InfoItem: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="s3-detail-info-item"><span>{label}</span><strong>{value || '未填写'}</strong></div>
);

const Stage3CandidateDetail: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const candidateId = Number(id);
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });

  const loadCandidate = useCallback(async () => {
    if (!Number.isInteger(candidateId) || candidateId <= 0) {
      setLoadState({ status: 'notFound' });
      return;
    }
    setLoadState({ status: 'loading' });
    try {
      const data = await getStage3CandidateDetail(candidateId);
      setLoadState({ status: 'ready', data });
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        setLoadState({ status: 'notFound' });
        return;
      }
      setLoadState({ status: 'error', message: error instanceof Error ? error.message : '无法连接新版候选人详情接口' });
    }
  }, [candidateId]);

  useEffect(() => { void loadCandidate(); }, [loadCandidate]);

  if (loadState.status === 'loading') {
    return (
      <main aria-busy="true" aria-label="候选人详情加载中" className="s3-main">
        <section className="s3-detail-hero"><Skeleton active avatar paragraph={{ rows: 2 }} /></section>
        <section className="s3-detail-layout">
          <div className="s3-detail-main"><article className="s3-detail-card"><Skeleton active paragraph={{ rows: 8 }} /></article></div>
          <aside className="s3-detail-aside"><article className="s3-detail-card"><Skeleton active paragraph={{ rows: 4 }} /></article></aside>
        </section>
      </main>
    );
  }

  if (loadState.status === 'notFound') {
    return (
      <main className="s3-main">
        <section className="s3-state-panel s3-detail-not-found">
          <Result
            extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/stage3/candidates')}>返回候选人列表</Button>}
            status="404"
            subTitle="该编号在新版候选人库中不存在，可能尚未创建或已经被移除。"
            title="未找到候选人"
          />
        </section>
      </main>
    );
  }

  if (loadState.status === 'error') {
    return (
      <main className="s3-main">
        <Alert
          action={<Button icon={<ReloadOutlined />} onClick={() => void loadCandidate()}>重新加载</Button>}
          className="s3-dashboard-alert"
          description={`请确认 FastAPI 已启动，且 /api/v2/candidates/${candidateId} 可访问。技术信息：${loadState.message}`}
          message="候选人详情加载失败"
          showIcon
          type="error"
        />
      </main>
    );
  }

  const { data } = loadState;
  const statusMeta = getCandidateStatusMeta(data.status);

  return (
    <main className="s3-main">
      <section className="s3-detail-hero">
        <Button aria-label="返回候选人列表" className="s3-detail-back" icon={<ArrowLeftOutlined />} onClick={() => navigate('/stage3/candidates')} />
        <Avatar className="s3-detail-avatar" size={56}>{data.name.slice(0, 1)}</Avatar>
        <div className="s3-detail-identity">
          <span className="s3-section-kicker">候选人 #{data.id} · 数据来源 /api/v2</span>
          <h2>{data.name}</h2>
          <p>{data.appliedJobTitle} · {data.currentTitle || '当前职位未填写'}</p>
          <div className="s3-detail-tags">
            <Tag bordered={false} className={`s3-status-tag is-${statusMeta.tone}`}>{statusMeta.label}</Tag>
            {data.source && <Tag bordered={false}>{data.source}</Tag>}
            {data.tags.map(tag => <Tag bordered={false} key={tag}>{tag}</Tag>)}
          </div>
        </div>
        <div className="s3-detail-updated"><span>最近更新</span><strong>{formatDateTime(data.updatedAt)}</strong></div>
      </section>

      <section className="s3-detail-layout">
        <div className="s3-detail-main">
          <article className="s3-detail-card">
            <div className="s3-detail-card-header"><div><UserOutlined /><h3>基础资料</h3></div><span>创建于 {formatDateTime(data.createdAt)}</span></div>
            <div className="s3-detail-info-grid">
              <InfoItem label="联系电话" value={data.phone} />
              <InfoItem label="电子邮箱" value={data.email} />
              <InfoItem label="所在城市" value={data.location} />
              <InfoItem label="来源渠道" value={data.source} />
              <InfoItem label="当前公司" value={data.currentCompany} />
              <InfoItem label="当前职位" value={data.currentTitle} />
              <InfoItem label="工作年限" value={data.workYears === null ? null : `${data.workYears} 年`} />
              <InfoItem label="最高学历" value={data.educationLevel} />
            </div>
          </article>

          <article className="s3-detail-card">
            <div className="s3-detail-card-header"><div><BookOutlined /><h3>教育经历</h3></div><span>{data.educationRecords.length} 条记录</span></div>
            {data.educationRecords.length === 0 ? <Empty className="s3-detail-empty" description="暂无教育经历" image={Empty.PRESENTED_IMAGE_SIMPLE} /> : (
              <div className="s3-experience-list">{data.educationRecords.map(record => (
                <div className="s3-experience-item" key={record.id}>
                  <span className="s3-experience-mark"><BookOutlined /></span>
                  <div>
                    <div className="s3-experience-title"><h4>{record.school || '学校未填写'}</h4><span>{formatPeriod(record.startDate, record.endDate)}</span></div>
                    <p>{record.degree || '学历未填写'} · {record.major || '专业未填写'}</p>
                    <div>{record.is985 && <Tag bordered={false}>985</Tag>}{record.is211 && <Tag bordered={false}>211</Tag>}</div>
                  </div>
                </div>
              ))}</div>
            )}
          </article>

          <article className="s3-detail-card">
            <div className="s3-detail-card-header"><div><BankOutlined /><h3>工作经历</h3></div><span>{data.workExperiences.length} 条记录</span></div>
            {data.workExperiences.length === 0 ? <Empty className="s3-detail-empty" description="暂无工作经历" image={Empty.PRESENTED_IMAGE_SIMPLE} /> : (
              <div className="s3-experience-list">{data.workExperiences.map(experience => (
                <div className="s3-experience-item" key={experience.id}>
                  <span className="s3-experience-mark"><BankOutlined /></span>
                  <div>
                    <div className="s3-experience-title"><h4>{experience.company || '公司未填写'}</h4><span>{formatPeriod(experience.startDate, experience.endDate)}</span></div>
                    <p className="s3-experience-role">{experience.title || '职位未填写'}</p>
                    {experience.description && <p>{experience.description}</p>}
                    <div className="s3-detail-tags">{experience.techStack.map(tech => <Tag bordered={false} key={tech}>{tech}</Tag>)}</div>
                  </div>
                </div>
              ))}</div>
            )}
          </article>

          <article className="s3-detail-card">
            <div className="s3-detail-card-header"><div><ProjectOutlined /><h3>项目经历</h3></div><span>{data.projectExperiences.length} 条记录</span></div>
            {data.projectExperiences.length === 0 ? <Empty className="s3-detail-empty" description="暂无项目经历" image={Empty.PRESENTED_IMAGE_SIMPLE} /> : (
              <div className="s3-experience-list">{data.projectExperiences.map(project => (
                <div className="s3-experience-item" key={project.id}>
                  <span className="s3-experience-mark"><ProjectOutlined /></span>
                  <div>
                    <div className="s3-experience-title"><h4>{project.projectName || '项目名称未填写'}</h4><span>{formatPeriod(project.startDate, project.endDate)}</span></div>
                    <p className="s3-experience-role">{project.role || '项目角色未填写'}</p>
                    {project.description && <p>{project.description}</p>}
                    {project.achievements && <p><strong>项目成果：</strong>{project.achievements}</p>}
                    <div className="s3-detail-tags">{project.techStack.map(tech => <Tag bordered={false} key={tech}>{tech}</Tag>)}</div>
                  </div>
                </div>
              ))}</div>
            )}
          </article>
        </div>

        <aside className="s3-detail-aside">
          <article className="s3-detail-card">
            <div className="s3-detail-card-header"><div><SolutionOutlined /><h3>应聘岗位</h3></div></div>
            <div className="s3-detail-side-value">
              <strong>{data.appliedJobTitle}</strong>
              <span>岗位来自新版岗位库；单个岗位详情尚未开放。</span>
              <Button onClick={() => navigate('/stage3/jobs')} size="small">查看岗位列表</Button>
            </div>
          </article>
          <article className="s3-detail-card">
            <div className="s3-detail-card-header"><div><FileTextOutlined /><h3>简历资料</h3></div></div>
            <div className="s3-detail-check-list">
              <span className={data.hasResume ? 'is-ready' : ''}>简历文件 {data.hasResume ? '已记录' : '未记录'}</span>
              <span className={data.hasResumeText ? 'is-ready' : ''}>简历文本 {data.hasResumeText ? '已保存' : '未保存'}</span>
              <span className={data.hasParsedData ? 'is-ready' : ''}>解析快照 {data.hasParsedData ? '已保存' : '未生成'}</span>
            </div>
          </article>
          <article className="s3-detail-card">
            <div className="s3-detail-card-header"><div><RobotOutlined /><h3>AI 摘要</h3></div></div>
            <p className="s3-detail-summary">{data.aiSummary || '尚未生成 AI 摘要；当前不展示模拟结论。'}</p>
          </article>
          <article className="s3-detail-card s3-detail-future-card">
            <div className="s3-detail-card-header"><div><MailOutlined /><h3>筛选与报告</h3></div></div>
            <p>历史初筛结果和已保存报告可在对应的只读中心查看；本页不运行筛选或生成报告。</p>
            <div className="s3-detail-related-links">
              <Button onClick={() => navigate('/stage3/screening')} size="small">查看 AI 初筛</Button>
              <Button onClick={() => navigate('/stage3/reports')} size="small">查看初筛报告</Button>
            </div>
            <Button disabled>招聘流程操作 · 后续</Button>
          </article>
        </aside>
      </section>
    </main>
  );
};

export default Stage3CandidateDetail;
