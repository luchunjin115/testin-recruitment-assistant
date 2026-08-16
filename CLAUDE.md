# CLAUDE.md — 项目指令

## 项目概览

HR Agent 招聘提效平台 — 面向公司内部 HR 团队的 AI 招聘助手。
基于现有 testin-recruitment-assistant 项目进行**架构重建**。

**总体架构设计**: `docs/specs/2026-07-15-hr-agent-platform-design.md`

**阶段 5 后产品路线基线**: `docs/specs/2026-08-14-post-stage5-product-roadmap.md`

**GitHub 招聘项目对比与借鉴决策**: `docs/research/2026-08-15-github-recruiting-project-comparison.md`

**新 agent 必须先读设计文档和路线基线，再开始任何工作。**

## 当前状态

项目处于**架构重建阶段**。现有代码是旧版本（React + FastAPI + SQLite + Mock LLM），
新版本将升级为: React + Ant Design 5 定制主题 + FastAPI + PostgreSQL + Chroma + Redis + DeepSeek API；LangGraph 只在后续确有多步骤编排价值的工作流中使用，不作为所有 AI 能力的强制包装。

阶段 4“简历上传与文件解析”和阶段 5“大模型简历结构化提取与表单辅助填写”已于 2026-08-14 完成，当前准备进入阶段 6“结构化岗位管理”。阶段 6 日常开发无需阅读阶段 5 专项文档；只有修改阶段 5 功能或排查其回归时才重新读取。

阶段 5 后的当前产品方向是：先完成结构化岗位、Application 与 AI 初筛底座，再打通公开投递、自动初筛、HR 决策、面试、Offer 和录取；随后建设首页综合 Agent、公司知识库 RAG、权限与交付能力。详细边界见阶段 5 后路线基线。

## 工作原则

1. **先读总体设计和路线基线**，理解全局架构与当前阶段顺序
2. 按实施计划顺序推进，但每个阶段开始前必须先完成业务需求、范围和验收标准讨论，并获得用户明确确认
3. 迁移现有代码时，参考设计文档第 9 节的迁移指南
4. 每完成一个模块，先测试再继续
5. 完成工作后同步更新 PROJECT_STATE.md
6. 采用小步骤协作：每次操作前说明要做什么、技术上如何做以及为什么这样做；操作后说明验证方法和结果，并同时使用大白话与必要的技术术语
7. 当前路线允许后续讨论修订；核心流程、数据模型、阶段边界或验收标准发生变化时，先更新阶段设计和权威文档，再修改业务代码

## 技术栈

```
前端: React 18 + TypeScript + Ant Design 5 (Design Token 定制) + Vite 5 + zustand
后端: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Alembic
数据库: PostgreSQL 16 + Chroma (向量) + Redis (缓存)
AI: DeepSeek API + 按需使用 LangGraph（复杂工作流编排）
部署: Docker Compose
```

## 启动方式

```bash
# 基础设施（首次需要）
docker-compose up -d  # PostgreSQL + Redis + Chroma

# 后端
cd backend && pip install -r requirements.txt
alembic upgrade head  # 数据库迁移
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && pnpm install
pnpm dev  # → http://localhost:5173
```

## 项目结构（新架构）

```
frontend/src/
  components/    通用 UI 组件
  pages/         页面（Dashboard, Resume, Screening, Jobs, Apply）
  services/      API 调用
  stores/        zustand 状态管理
  theme/         Ant Design 5 主题 Token
  types/         TypeScript 类型

backend/app/
  api/           FastAPI 路由
  services/      普通业务与 AI 服务（阶段 5 简历结构化提取位于此层）
  agents/        LangGraph 工作流（仅用于确有多步骤编排需求的模块）
  rag/           RAG 检索层（Chroma）
  models/        SQLAlchemy 数据模型
  schemas/       Pydantic 请求/响应
  core/          基础设施（config, database, llm, file_parser）
```

## 核心 AI 能力

1. **resume_structure** — 阶段 5 普通 AI Service：`Resume.raw_text` → 单次 DeepSeek 结构化提取 → 严格校验 → 草稿持久化 → 表单辅助填写；不使用 Agent/LangGraph，不直接创建 Candidate
2. **jd_match** — JD 匹配: 解析 JD → 硬性条件检查 → 多维度评分 → 综合推荐；实现时再依据真实分支复杂度决定是否使用 LangGraph
3. **report_gen** — 报告生成: 汇总数据 → 摘要 → 分析 → 结论 → 格式化
4. **smart_assistant** — 智能助手: 意图识别 → 路由到对应工作流

## 现有代码关键文件索引（迁移参考）

```
可复用:
  backend/app/prompts/*.md          5 个 Prompt 模板
  backend/app/services/file_parser.py   文件解析
  backend/app/services/dedup_service.py 去重逻辑
  frontend/src/pages/ApplyForm.tsx      候选人投递页

参考但需重写:
  backend/app/services/mock_llm.py      规则引擎（577行，含评分逻辑）
  backend/app/services/ai_service.py    AI 服务层
```

## 关键约束

- AI 模型: DeepSeek（通过 OpenAI 兼容接口）
- Prompt 设计: 禁止使用性别/年龄/民族/婚姻状况进行评估
- 简历解析: 全量信息提取，不遗漏
- 阶段 5 的一次识别正常只调用一次 DeepSeek；失败不自动连续重试，由 HR 决定是否重新识别
- 阶段 5 只保存结构化草稿并补充前端空字段，正式 Candidate 必须由 HR 检查并确认后创建
- 阶段 5 只忠实提取学校名称，不让模型推断 985/211；后续初筛如需院校标签，使用可追溯的标准院校数据，不依赖模型记忆
- 匹配打分: 不通过硬性条件的候选人不直接淘汰，标记原因让 HR 决策
- 简历内容格式: 保留 `Resume.raw_text` 与 `Resume.parsed_snapshot`，不增加 PDF 转 Markdown 文件流程；RAG 阶段从两者生成带来源元数据的检索片段
- Agent 工具边界: `Agent -> Tool -> Service -> PostgreSQL/Chroma`；Tools 是阶段 10 必选能力，MCP 仅作为未来外部调用适配
- RAG 职责: 负责候选人召回和知识检索，不以向量相似度代替正式初筛、淘汰或录取判断
