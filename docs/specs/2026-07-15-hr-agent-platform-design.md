# HR Agent 招聘提效平台 — 设计文档

> **版本**: v1.0  
> **日期**: 2026-07-15  
> **状态**: 设计评审通过，待实施  
> **文档目的**: 本文档是完整的项目设计规范，任何 AI agent 或开发者都应能仅凭此文档理解全部设计意图并执行实施

---

## 1. 项目概述

### 1.1 定位

面向公司内部 HR 团队的**招聘提效工具**，以 AI 能力为核心，帮助 HR 在简历处理阶段大幅提升效率。

### 1.2 核心问题

HR 每天面对大量简历（来自招聘网站、邮件内推、自建投递页），人工筛选耗时、容易遗漏优质候选人。需要 AI 自动完成：简历结构化解析、JD 匹配打分、初筛报告生成。

### 1.3 项目方式

在现有 `testin-recruitment-assistant` 项目基础上**架构重建**：重新规划项目结构，迁移有价值的代码（Prompt 模板、候选人投递页面、业务逻辑），用全新的分层架构承载。

### 1.4 MVP 范围与迭代计划

| 阶段 | 范围 | 优先级 |
|------|------|--------|
| **MVP（当前）** | 简历处理：解析 + 匹配打分 + 初筛报告 | P0 |
| 迭代 2 | 面试协调：跨部门排面、时间协调、进度追踪 | P1 |
| 迭代 3 | 知识沉淀：招聘标准统一、JD 模板库、面试题库 | P2 |
| 迭代 4 | 全流程自动化：从 JD 发布到入职跟踪 | P3 |

---

## 2. 用户与场景

### 2.1 用户角色

| 角色 | 描述 | 核心诉求 |
|------|------|---------|
| HR 招聘专员 | 日常操作者，处理简历、安排面试 | 减少重复劳动，快速找到匹配候选人 |
| HR 负责人 | 管理整体招聘进度 | 数据看板，了解全局 |
| 候选人 | 通过投递页面提交简历 | 简单易用的投递体验 |

### 2.2 MVP 核心用户故事

**US-01**: 作为 HR，我上传一份简历（PDF/Word/TXT），系统自动提取全部结构化信息（姓名、手机、邮箱、教育、工作经历、项目经历、技能、期望薪资等），我不需要回头翻原始简历。

**US-02**: 作为 HR，我选择一个岗位 JD，系统自动对候选人进行匹配打分（0-100），给出匹配度、优势、劣势、风险点，并按分数排序，我只需关注 Top N。

**US-03**: 作为 HR，我可以一键生成初筛报告（包含候选人基本信息、匹配分析、推荐/待定/不推荐结论），可以直接发给用人部门/面试官。

**US-04**: 作为 HR，我在工作台输入自然语言（如"帮我看看最近有没有匹配Java高级工程师的简历"），系统理解意图并返回结果。

**US-05**: 作为候选人，我通过投递页面填写信息并上传简历，操作简单直观。

---

## 3. 技术架构

### 3.1 技术选型

| 层 | 技术 | 选择理由 |
|----|------|---------|
| **前端框架** | React 18 + TypeScript | 现有经验，生态成熟 |
| **UI 组件库** | Ant Design 5（Design Token 深度定制主题） | B 端组件最完整，定制主题实现高颜值 |
| **构建工具** | Vite 5 | 开发体验好，HMR 快 |
| **后端框架** | FastAPI + SQLAlchemy 2.0 | 现有经验，异步原生，自动文档 |
| **数据库** | PostgreSQL 16 | 生产级，支持 JSONB、全文搜索 |
| **向量数据库** | Chroma | 轻量级，Python 原生，MVP 够用 |
| **缓存** | Redis | 会话缓存、频率限制、任务队列 |
| **AI 模型** | DeepSeek（通过 API） | 性价比高，中文能力强 |
| **AI 编排** | LangGraph | 图结构工作流，支持条件路由和循环，可渐进演进到多 Agent |
| **容器化** | Docker Compose | 一键启动所有服务 |

### 3.2 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (React + Ant Design 5)         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │  工作台   │ │ 简历管理  │ │ AI筛选   │ │ 候选人投递  │  │
│  │(智能助手) │ │(上传/列表)│ │(匹配/报告)│ │  (公开页)   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘  │
└───────┼────────────┼────────────┼──────────────┼─────────┘
        ▼            ▼            ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                 API 网关 (FastAPI Router)                 │
│  /api/chat  /api/resume  /api/screening  /api/apply      │
│  /api/jobs  /api/candidates  /api/dashboard              │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Service 业务逻辑层                           │
│  ResumeService │ ScreenService │ CandidateService        │
│  JobService    │ ReportService │ DashboardService         │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph Agent 层 ★                        │
│  ┌──────────────────────────────────────────────────┐    │
│  │               Orchestrator (编排器)                │    │
│  │   理解意图 → 路由到对应工作流 → 汇总返回           │    │
│  └────────┬──────────────┬───────────────┬──────────┘    │
│  ┌────────▼──────┐ ┌─────▼───────┐ ┌────▼──────────┐    │
│  │ 简历解析 Graph │ │ JD匹配 Graph │ │ 报告生成 Graph │    │
│  │ parse_resume  │ │  jd_match   │ │  report_gen   │    │
│  └───────────────┘ └─────────────┘ └───────────────┘    │
│  共享资源: Prompt 模板 / State 定义 / 可复用 Nodes        │
└────────────┬─────────────────────────┬───────────────────┘
     ┌───────▼───────┐         ┌───────▼───────┐
     │   DeepSeek    │         │    Chroma     │
     │   API 调用    │         │   向量检索    │
     └───────────────┘         └───────────────┘
     ┌──────────────────────────────────────────┐
     │            数据存储层                      │
     │  PostgreSQL     Redis     文件存储         │
     │  (业务数据)    (缓存/队列)  (简历原件)      │
     └──────────────────────────────────────────┘
```

### 3.3 项目目录结构

```
testin-recruitment-assistant/

├── frontend/
│   ├── src/
│   │   ├── assets/              # 图标、图片
│   │   ├── components/
│   │   │   ├── SmartAssistant/  # 智能助手对话组件
│   │   │   ├── ResumeUpload/    # 简历上传组件（支持拖拽、批量）
│   │   │   ├── ScoreCard/       # 匹配分数卡片
│   │   │   ├── ReportViewer/    # 初筛报告展示/导出
│   │   │   └── StatsPanel/      # 统计面板组件
│   │   ├── pages/
│   │   │   ├── Dashboard/       # 工作台（智能助手 + 快捷操作 + 数据概览）
│   │   │   ├── Resume/
│   │   │   │   ├── List/        # 简历列表（搜索、筛选、批量操作）
│   │   │   │   ├── Detail/      # 简历详情（结构化展示 + 原件预览）
│   │   │   │   └── Upload/      # 简历上传页
│   │   │   ├── Screening/
│   │   │   │   ├── Center/      # 筛选配置 + 结果展示
│   │   │   │   └── Report/      # 初筛报告生成与导出
│   │   │   ├── Jobs/            # 岗位管理
│   │   │   └── Apply/           # 候选人投递页（迁移现有）
│   │   ├── services/            # API 调用封装
│   │   ├── hooks/               # 自定义 React Hooks
│   │   ├── stores/              # 状态管理（zustand）
│   │   ├── theme/               # Ant Design 5 主题定制 Token
│   │   ├── utils/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── vite.config.ts
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI 路由
│   │   │   ├── chat.py          # 智能助手对话
│   │   │   ├── resume.py        # 简历上传/解析
│   │   │   ├── screening.py     # AI 筛选
│   │   │   ├── candidates.py    # 候选人 CRUD
│   │   │   ├── jobs.py          # 岗位管理
│   │   │   ├── reports.py       # 初筛报告
│   │   │   ├── dashboard.py     # 数据看板
│   │   │   └── apply.py         # 候选人投递
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── resume_service.py
│   │   │   ├── screening_service.py
│   │   │   ├── candidate_service.py
│   │   │   ├── job_service.py
│   │   │   ├── report_service.py
│   │   │   └── dashboard_service.py
│   │   ├── agents/              # ★ LangGraph 工作流层
│   │   │   ├── graphs/
│   │   │   │   ├── resume_parse.py      # 简历解析工作流
│   │   │   │   ├── jd_match.py          # JD 匹配打分工作流
│   │   │   │   ├── report_gen.py        # 初筛报告生成工作流
│   │   │   │   ├── smart_assistant.py   # 智能助手意图路由
│   │   │   │   └── orchestrator.py      # 总编排器
│   │   │   ├── nodes/           # 可复用的图节点
│   │   │   │   ├── extract_basic_info.py
│   │   │   │   ├── extract_education.py
│   │   │   │   ├── extract_experience.py
│   │   │   │   ├── extract_skills.py
│   │   │   │   ├── score_match.py
│   │   │   │   ├── analyze_strengths.py
│   │   │   │   ├── analyze_risks.py
│   │   │   │   └── format_report.py
│   │   │   ├── states/          # LangGraph State 类型定义
│   │   │   │   ├── resume_state.py
│   │   │   │   ├── match_state.py
│   │   │   │   └── report_state.py
│   │   │   └── prompts/         # Prompt 模板
│   │   │       ├── resume_extraction.py
│   │   │       ├── jd_matching.py
│   │   │       ├── report_generation.py
│   │   │       ├── smart_assistant.py
│   │   │       └── candidate_summary.py
│   │   ├── rag/                 # RAG 检索层
│   │   │   ├── embeddings.py
│   │   │   ├── vector_store.py
│   │   │   └── retriever.py
│   │   ├── models/              # SQLAlchemy 数据模型
│   │   │   ├── candidate.py
│   │   │   ├── job.py
│   │   │   ├── resume.py
│   │   │   ├── screening_result.py
│   │   │   ├── report.py
│   │   │   └── activity_log.py
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   │   ├── candidate.py
│   │   │   ├── job.py
│   │   │   ├── resume.py
│   │   │   ├── screening.py
│   │   │   └── report.py
│   │   ├── core/                # 基础设施
│   │   │   ├── config.py        # 环境变量配置
│   │   │   ├── database.py      # PostgreSQL 连接
│   │   │   ├── redis.py         # Redis 连接
│   │   │   ├── security.py      # 认证与权限
│   │   │   ├── llm.py           # DeepSeek 客户端封装
│   │   │   └── file_parser.py   # PDF/Word/TXT 解析器
│   │   └── main.py
│   ├── migrations/              # Alembic 数据库迁移
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── CLAUDE.md
└── README.md
```

---

## 4. LangGraph 工作流设计（核心）

### 4.1 简历解析工作流 (resume_parse)

**输入**: 简历文件（PDF/Word/TXT）

```
file_to_text ──→ extract_basic ──→ extract_education ──→ extract_work_exp
                                                              │
extract_skills ←── extract_projects ←─────────────────────────┘
      │
      ▼
validate & quality_check
      │
   完整？──→ 是 ──→ merge & save_to_db ──→ 输出结构化 JSON
      │
      └──→ 否 ──→ 条件路由回缺失的提取节点
```

**设计要点**:
- 分步提取而非一次性提取全部，每个节点的 Prompt 更聚焦，准确率更高
- 校验节点实现自我纠错：如果技能字段为空，回退到 extract_skills 重新提取
- 每个节点可独立测试和优化
- 全量信息提取，不遗漏任何简历内容

### 4.2 JD 匹配打分工作流 (jd_match)

**输入**: 候选人结构化数据 + 岗位 JD

```
parse_jd_require ──→ hard_require_check
                          │
                     通过？──→ 是 ──→ skill_match ──→ experience_match ──→ overall_score
                          │
                          └──→ 否 ──→ 标记原因（不丢弃）──→ skill_match ──→ ...
```

**输出**: `{score: 85, level: "推荐", strengths: [...], risks: [...], reason: "..."}`

**设计要点**:
- 硬性条件先筛，但不直接淘汰——标记原因，让 HR 有最终决策权
- 多维度分开评估再综合，比一次性打分更准确、更可解释
- 输出结构化的评分理由，HR 能看到"为什么给这个分"

### 4.3 初筛报告生成工作流 (report_gen)

**输入**: 候选人数据 + 匹配结果 + 岗位信息

```
compile_data ──→ generate_summary ──→ generate_analysis ──→ generate_verdict ──→ format_report
```

**报告模板结构**:

```
# 初筛报告
## 基本信息:     姓名 | 手机 | 邮箱 | 当前公司 | 当前职位
## 应聘岗位:     岗位名称 | 匹配度评分
## 候选人概要:   一句话总结
## 教育背景:     学校 | 学历 | 专业 | 毕业时间
## 核心技能:     技能列表 + 熟练度评估
## 匹配分析:     优势 + 风险/关注点
## AI 评估结论:  推荐等级 | 推荐理由 | 建议面试方向
## 附注:         报告生成时间 | 数据来源 | 免责声明
```

### 4.4 智能助手工作流 (smart_assistant)

**输入**: HR 的自然语言输入

```
intent_classify ──→ 意图路由:
  ├── "筛选简历"   → 触发 jd_match 工作流
  ├── "查看候选人" → 查询数据库返回
  ├── "生成报告"   → 触发 report_gen 工作流
  ├── "数据统计"   → 查询 dashboard 数据
  └── "通用问答"   → 直接 LLM 回答
```

---

## 5. 数据模型设计

### 5.1 核心表结构

```sql
-- 候选人表
CREATE TABLE candidates (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    phone           VARCHAR(20),
    email           VARCHAR(100),
    gender          VARCHAR(10),
    age             INTEGER,
    location        VARCHAR(100),
    current_company VARCHAR(200),
    current_title   VARCHAR(200),
    work_years      INTEGER,
    education_level VARCHAR(50),
    source          VARCHAR(50),       -- boss/lagou/email/referral/apply
    status          VARCHAR(50) DEFAULT 'new',
    applied_job_id  INTEGER REFERENCES jobs(id),
    resume_file_path VARCHAR(500),
    resume_text     TEXT,
    parsed_data     JSONB,
    ai_summary      TEXT,
    tags            JSONB,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- 岗位表
CREATE TABLE jobs (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    department      VARCHAR(100),
    description     TEXT,
    requirements    JSONB,
    status          VARCHAR(20) DEFAULT 'open',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- 筛选结果表
CREATE TABLE screening_results (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER REFERENCES candidates(id),
    job_id          INTEGER REFERENCES jobs(id),
    overall_score   INTEGER,
    hard_pass       BOOLEAN,
    skill_score     INTEGER,
    experience_score INTEGER,
    strengths       JSONB,
    risks           JSONB,
    recommendation  VARCHAR(20),
    reason          TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(candidate_id, job_id)
);

-- 初筛报告表
CREATE TABLE reports (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER REFERENCES candidates(id),
    job_id          INTEGER REFERENCES jobs(id),
    screening_id    INTEGER REFERENCES screening_results(id),
    content         TEXT,
    report_type     VARCHAR(20) DEFAULT 'screening',
    generated_at    TIMESTAMP DEFAULT NOW()
);

-- 教育经历表
CREATE TABLE education (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER REFERENCES candidates(id),
    school          VARCHAR(200),
    degree          VARCHAR(50),
    major           VARCHAR(200),
    start_date      VARCHAR(20),
    end_date        VARCHAR(20),
    is_985          BOOLEAN DEFAULT FALSE,
    is_211          BOOLEAN DEFAULT FALSE
);

-- 工作经历表
CREATE TABLE work_experience (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER REFERENCES candidates(id),
    company         VARCHAR(200),
    title           VARCHAR(200),
    start_date      VARCHAR(20),
    end_date        VARCHAR(20),
    description     TEXT,
    tech_stack      JSONB
);

-- 项目经历表
CREATE TABLE project_experience (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER REFERENCES candidates(id),
    project_name    VARCHAR(200),
    role            VARCHAR(100),
    start_date      VARCHAR(20),
    end_date        VARCHAR(20),
    description     TEXT,
    tech_stack      JSONB,
    achievements    TEXT
);

-- 操作日志表
CREATE TABLE activity_logs (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(50),
    action          VARCHAR(100),
    target_type     VARCHAR(50),
    target_id       INTEGER,
    detail          JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### 5.2 Chroma 向量集合

```
Collection: resumes
- document: 简历全文文本（分段存储）
- metadata: {candidate_id, name, skills, education_level, work_years, source}
- embedding: BGE 嵌入向量
- 用途: 语义搜索候选人（"有微服务架构经验的 Java 开发"）
```

---

## 6. 界面设计

### 6.1 交互模式

**混合模式**: 工作台首页有智能助手入口 + 快捷操作卡片，左侧菜单导航到各功能页面。

### 6.2 主题设计方向

基于 Ant Design 5 Design Token 定制:
- **主色调**: 科技蓝渐变（类似截图中的蓝紫渐变风格）
- **卡片风格**: 大圆角 (12-16px) + 轻阴影 + 充足留白
- **数据展示**: 大字号统计数字 + 趋势标记 + 彩色图标
- **整体感觉**: 专业、现代、清爽，不花哨

### 6.3 页面规划

**工作台 Dashboard（首页）**:
```
┌───────────────────────────────────────────────────┐
│  顶部导航栏                              用户头像  │
├───────┬───────────────────────────────────────────┤
│       │  ┌─────────────────────────────────────┐  │
│ 左侧  │  │     渐变 Banner                      │  │
│ 菜单  │  │     智能工作助手                      │  │
│       │  │     [   输入你的需求...   ] [智能识别] │  │
│ 工作台 │  │     快速示例: [生成JD] [筛选简历] ... │  │
│ 简历  │  └─────────────────────────────────────┘  │
│ 岗位  │                                           │
│ 筛选  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │
│       │  │ 15   │ │ 42   │ │ 8    │ │ 23   │    │
│       │  │招聘职位│ │候选人 │ │今日新增│ │AI处理 │    │
│       │  └──────┘ └──────┘ └──────┘ └──────┘    │
│       │                                           │
│       │  ┌──── 快捷操作 ────┐  ┌── 最近活动 ──┐  │
│       │  │ 上传简历          │  │ xx 2小时前   │  │
│       │  │ 批量筛选          │  │ xx 1天前     │  │
│       │  │ 生成报告          │  │ xx 2天前     │  │
│       │  └─────────────────┘  └──────────────┘  │
└───────┴───────────────────────────────────────────┘
```

**简历管理页**:
- 顶部: 上传区（拖拽 + 点击，支持批量）
- 中部: 表格列表 — 姓名 | 应聘岗位 | 学历 | 工作年限 | 来源 | 状态 | AI摘要 | 匹配分 | 操作
- 详情: 左侧结构化信息展示，右侧原始简历预览

**AI 筛选中心**:
- 顶部: 选择岗位 + 开始筛选按钮
- 主体: 候选人按匹配度排序，显示分数 + 推荐等级 + 关键理由
- 侧栏/弹窗: 各维度得分、优劣势分析
- 底部: 批量生成初筛报告

**初筛报告页**:
- Markdown 渲染展示
- 导出 PDF / Word
- 发送给面试官

---

## 7. API 设计

### 7.1 核心 API

```
简历管理:
  POST   /api/resume/upload          上传简历（单个/批量）
  POST   /api/resume/parse/{id}      触发 AI 解析
  GET    /api/resume/{id}/parsed     获取解析结果

候选人:
  GET    /api/candidates             列表（分页/筛选/搜索）
  GET    /api/candidates/{id}        详情
  PUT    /api/candidates/{id}        更新
  DELETE /api/candidates/{id}        删除

岗位管理:
  POST   /api/jobs                   创建
  GET    /api/jobs                   列表
  GET    /api/jobs/{id}              详情
  PUT    /api/jobs/{id}              更新

AI 筛选:
  POST   /api/screening/run          运行筛选（流式 SSE）
  POST   /api/screening/batch        批量筛选
  GET    /api/screening/results      结果列表
  GET    /api/screening/{id}         单个结果

初筛报告:
  POST   /api/reports/generate       生成报告
  GET    /api/reports/{id}           获取报告
  GET    /api/reports/{id}/export    导出（PDF/Word）

智能助手:
  POST   /api/chat                   对话（流式 SSE）
  GET    /api/chat/history           对话历史

数据看板:
  GET    /api/dashboard/stats        统计数据
  GET    /api/dashboard/activities   最近活动

候选人投递（公开）:
  POST   /api/apply                  提交申请
  GET    /api/apply/jobs             开放岗位列表
```

### 7.2 关键 API 详细设计

**POST /api/resume/upload**:
```json
// Request: multipart/form-data
// files: File[], job_id?: int, source: string, auto_parse: bool

// Response:
{
  "uploaded": [
    {"candidate_id": 1, "filename": "张三.pdf", "status": "parsing"}
  ],
  "errors": []
}
```

**POST /api/screening/run** (流式 SSE):
```
Request: {"candidate_ids": [1, 2, 3], "job_id": 1}

data: {"candidate_id": 1, "status": "scoring", "progress": "技能匹配中..."}
data: {"candidate_id": 1, "status": "done", "result": {"score": 85, "recommendation": "推荐", ...}}
```

**POST /api/chat** (流式 SSE):
```
Request: {"message": "帮我看看最近有没有匹配Java高级工程师的简历", "session_id": "xxx"}

data: {"type": "thinking", "content": "正在搜索匹配的候选人..."}
data: {"type": "result", "content": "找到 3 位匹配的候选人..."}
data: {"type": "action", "content": {"action": "show_candidates", "ids": [1, 2, 3]}}
```

---

## 8. Prompt 设计规范

### 8.1 总体原则

1. **角色设定**: 每个 Prompt 以专业 HR 技术招聘专家身份开头
2. **结构化输出**: 所有需要后处理的 Prompt 强制 JSON 输出
3. **全量提取**: 简历信息不遗漏，宁多勿少
4. **无偏见**: 禁止在评估中使用性别、年龄、民族、婚姻状况
5. **可解释**: 每个评分都要有具体理由
6. **约束清晰**: 明确禁止虚构信息、禁止过度推断

### 8.2 Prompt 模板示例（简历解析）

```python
RESUME_EXTRACTION_PROMPT = """
你是一位专业的技术招聘 HR 助手。请从以下简历文本中提取全部结构化信息。

## 提取要求
- 提取所有可识别的信息，不遗漏
- 无法识别的字段填 null，不要猜测或虚构
- 技能列表尽可能完整，包括编程语言、框架、工具、平台
- 工作经历和项目经历按时间倒序排列
- 保留原文中的关键描述，不要过度概括

## 输出格式（严格 JSON）
{{
    "basic_info": {{
        "name": "姓名",
        "phone": "手机号",
        "email": "邮箱",
        "gender": "性别 (仅在简历明确标注时提取)",
        "age": "年龄/出生年月",
        "location": "所在城市",
        "current_company": "当前公司",
        "current_title": "当前职位",
        "work_years": "工作年限（数字）",
        "expected_salary": "期望薪资",
        "availability": "到岗时间"
    }},
    "education": [{{
        "school": "学校名称",
        "degree": "学历",
        "major": "专业",
        "start_date": "入学时间",
        "end_date": "毕业时间"
    }}],
    "work_experience": [{{
        "company": "公司名称",
        "title": "职位",
        "start_date": "开始时间",
        "end_date": "结束时间",
        "description": "工作职责和成就（保留原文关键内容）",
        "tech_stack": ["使用的技术"]
    }}],
    "project_experience": [{{
        "project_name": "项目名称",
        "role": "担任角色",
        "start_date": "开始时间",
        "end_date": "结束时间",
        "description": "项目描述",
        "tech_stack": ["使用的技术"],
        "achievements": "项目成果"
    }}],
    "skills": ["技能1", "技能2"],
    "certifications": ["证书1"],
    "self_evaluation": "自我评价原文"
}}

## 简历文本
{resume_text}
"""
```

---

## 9. 从现有项目迁移

### 9.1 可复用

| 现有文件/模块 | 迁移方式 | 目标位置 |
|--------------|---------|---------|
| `prompts/*.md` (5个) | 优化后迁移 | `backend/app/agents/prompts/` |
| `ApplyForm` 页面 | 迁移 + UI 升级 | `frontend/src/pages/Apply/` |
| `file_parser.py` | 迁移 | `backend/app/core/file_parser.py` |
| `dedup_service.py` | 迁移 | `backend/app/services/` |
| Mock LLM 评分规则 | 提取作为 fallback | `backend/app/services/` |
| 业务常量（985院校等） | 迁移 | `backend/app/core/constants.py` |

### 9.2 需重写

| 现有模块 | 原因 | 新实现 |
|---------|------|-------|
| `ai_service.py` | 直接调 API，无编排 | LangGraph 工作流 |
| `mock_llm.py` (577行) | 职责不清 | 拆分到各 graph fallback |
| 前端所有页面 | UI 需全面升级 | Ant Design 5 定制主题重写 |
| SQLite 数据模型 | 需优化字段 | PostgreSQL 新 schema |

---

## 10. 开发计划

### 第 1 周: 项目骨架 + 基础设施

- [ ] 初始化前后端项目结构
- [ ] Docker Compose（PostgreSQL + Redis + Chroma）
- [ ] FastAPI 骨架（路由、DB 连接、配置管理）
- [ ] React + Ant Design 5 骨架 + 主题定制
- [ ] Alembic 初始化 + 建表
- [ ] DeepSeek API 客户端封装

### 第 2 周: LangGraph 核心工作流

- [ ] 简历解析工作流 (resume_parse graph)
- [ ] JD 匹配打分工作流 (jd_match graph)
- [ ] 初筛报告生成工作流 (report_gen graph)
- [ ] Prompt 模板编写与测试
- [ ] 简历文件解析器 (PDF/Word/TXT)

### 第 3 周: 前端核心页面

- [ ] 工作台 Dashboard（智能助手 + 统计面板 + 快捷操作）
- [ ] 简历管理页（上传 + 列表 + 详情）
- [ ] AI 筛选中心（岗位选择 + 结果展示）
- [ ] 初筛报告页（展示 + 导出）
- [ ] 候选人投递页（迁移 + 升级）

### 第 4 周: 智能助手 + 打磨

- [ ] 智能助手工作流（意图识别 + 路由）
- [ ] RAG 接入（简历向量化 + 语义搜索）
- [ ] 岗位管理页面
- [ ] 界面动效和细节打磨
- [ ] 演示数据准备
- [ ] 端到端测试

---

## 11. 关键技术决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端框架 | React + Ant Design 5 定制主题 | B 端组件完整，定制主题高颜值，现有经验 |
| 后端框架 | FastAPI | 异步原生，AI 应用首选，现有经验 |
| AI 编排 | LangGraph | 图结构支持条件路由，可渐进演进到多 Agent |
| 数据库 | PostgreSQL | 生产级，JSONB 支持 |
| 向量库 | Chroma | 轻量 Python 原生，MVP 够用 |
| AI 模型 | DeepSeek | 中文强，性价比高 |
| 项目方式 | 架构重建 | 分层清晰，LangGraph 独立层，可演进 |
| 交互模式 | 混合（助手 + 页面） | 兼顾效率和灵活性 |

---

## 12. 给下一个 Agent 的执行指南

### 12.1 阅读顺序

1. **先读本文档**，理解全局设计
2. 读 `CLAUDE.md` 了解项目上下文
3. 读现有 `backend/app/prompts/` 下的 5 个 Prompt 模板，理解业务逻辑
4. 读现有 `backend/app/services/mock_llm.py`，理解评分规则引擎（577行，包含完整的规则引擎逻辑，可作为 fallback 参考）

### 12.2 实施原则

1. **严格按照第 10 节开发计划的顺序执行**
2. 每完成一个模块，先测试再继续
3. LangGraph 图的每个节点要能独立运行和测试
4. 前端每个页面先搭结构，再填充交互和样式
5. Prompt 模板是核心资产，要认真编写和测试
6. 迁移现有代码时，参考第 9 节的迁移指南

### 12.3 环境要求

```
后端: Python 3.11+, PostgreSQL 16, Redis 7, Chroma 0.4+
前端: Node.js 18+, pnpm (推荐) 或 npm
AI:   DeepSeek API Key（配置在 .env 文件中）
```

### 12.4 关键依赖

```
后端:
  fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic,
  pydantic>=2.0, langgraph, langchain-openai, chromadb, redis,
  python-multipart, pdfplumber, python-docx

前端:
  react, react-dom, react-router-dom, antd, @ant-design/icons,
  @ant-design/plots, axios, dayjs, zustand
```

### 12.5 现有项目关键文件索引

```
现有 Prompt 模板（迁移参考）:
  backend/app/prompts/resume_extraction.md   - 简历提取
  backend/app/prompts/candidate_summary.md   - 候选人摘要
  backend/app/prompts/auto_tagging.md        - 自动标签
  backend/app/prompts/followup_suggestion.md - 跟进建议
  backend/app/prompts/copilot_system.md      - Copilot 系统提示

现有核心逻辑（迁移参考）:
  backend/app/services/mock_llm.py           - 规则引擎（577行）
  backend/app/services/ai_service.py         - AI 服务层
  backend/app/services/file_parser.py        - 文件解析
  backend/app/services/dedup_service.py      - 去重逻辑

现有前端（UI 参考）:
  frontend/src/pages/ApplyForm.tsx           - 候选人投递页
  frontend/src/pages/Dashboard.tsx           - 工作台
  frontend/src/pages/AIScreeningCenter.tsx   - AI 筛选中心
```
