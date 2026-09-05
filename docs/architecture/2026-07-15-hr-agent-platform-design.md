# HR智聘 — AI 招聘全流程平台总体架构设计

> 初版日期：2026-07-15
>
> 当前修订：2026-08-20
>
> 角色：定义长期产品边界、系统分层和跨模块技术原则。当前进度见 `../../PROJECT_STATE.md`，阶段顺序见 `../planning/implementation-plan.md`，具体业务合同见当前阶段专项设计。
>
> 详细 v1 设计已归档到 `../archive/superseded/2026-07-15-hr-agent-platform-design-v1.md`。

## 1. 产品定位

本项目是面向公司内部 HR 团队的 AI 招聘平台。核心价值不是提供一个脱离业务的聊天机器人，而是让岗位、投递、简历、初筛、HR 决策、面试、Offer 和录取形成可靠数据链路，再通过 AI 降低阅读、整理和检索成本。

产品长期由三条主线组成：

1. 招聘业务全流程。
2. 首页综合 Agent 与受控业务工具。
3. 公司知识库 RAG 与简历语义搜索。

## 2. 用户与决策边界

| 用户 | 主要任务 |
| --- | --- |
| HR 招聘专员 | 创建岗位、处理申请、查看 AI 报告、推进招聘流程 |
| HR 负责人 | 查看招聘进度、统计和异常任务 |
| 候选人 | 查看开放岗位并提交申请 |

AI 只能提取、整理、评价、生成草稿和解释依据。通过、备选、淘汰、发 Offer 和录用等招聘决定必须由授权人员作出。

## 3. 产品主链

```text
HR 创建并开放岗位
        ↓
HR 内部录入或候选人公开投递
        ↓
可靠保存 Candidate / Application / Resume
        ↓
文件原文提取与结构化
        ↓
按当前 Job + Application + Resume 执行 AI 初筛
        ↓
HR 通过 / 备选 / 淘汰
        ↓
面试 -> Offer -> 录取或结束
```

公开投递阶段必须先保存投递事实，再异步处理文件和 AI。模型失败不能让投递、原简历或旧成功结果消失。

## 4. 技术架构

```text
React + TypeScript + Ant Design
                ↓ HTTP
FastAPI API / Pydantic Schema
                ↓
业务 Service / 固定 AI Service
                ↓
SQLAlchemy Model
                ↓
PostgreSQL

未来复杂编排：LangGraph Agent -> Tool -> 既有 Service
未来语义检索：Service / Tool -> Chroma
未来队列与缓存：Service / Worker -> Redis
```

### 4.1 技术选型

| 层 | 技术 | 职责 |
| --- | --- | --- |
| 前端 | React 18、TypeScript、Ant Design 5、Vite、zustand | 页面、交互和客户端状态 |
| API | FastAPI | HTTP 合同、依赖注入、错误映射 |
| Schema | Pydantic v2 | 严格输入输出边界 |
| Service | Python 异步 Service | 业务规则、事务和 AI 工作流 |
| ORM/迁移 | SQLAlchemy 2.0、Alembic | 数据映射和向前 Schema 演进 |
| 数据库 | PostgreSQL 16 | 正式业务数据和约束 |
| 模型 | DeepSeek API | 结构化提取、语义评价和生成 |
| 后续编排 | LangGraph | 多工具、条件路由、确认和恢复 |
| 后续检索 | Chroma | 公司知识与简历向量检索 |
| 后续队列 | Redis | 异步任务和短期协调状态 |

## 5. 分层职责

### 5.1 React 前端

- 展示真实业务状态，不用演示数据伪装成功。
- 调用受控 API，不在浏览器复制后端核心评分和状态规则。
- 对 loading、空状态、失败、过期和重试提供明确反馈。
- AI 报告由结构化数据渲染，不直接信任任意模型 HTML。

### 5.2 FastAPI API

- 接收和返回稳定 HTTP 合同。
- 完成认证入口、依赖注入和稳定错误映射。
- 不直接编写跨对象事务或模型 Prompt。

### 5.3 Pydantic Schema

- 限制字段、枚举、长度、类型和嵌套结构。
- 拒绝未知或非法模型输出，不能静默吞掉错误字段。
- HTTP Schema 与模型输出 Schema 可以分开，但职责必须明确。

### 5.4 Service

- 承担业务校验、事务、并发、幂等和状态变化。
- 通过 Adapter 调用 DeepSeek，不让路由或 ORM Model 直接依赖模型 SDK。
- 固定 AI 流程继续使用 Service；只有真实需要多步骤自主选择时才使用 LangGraph。

### 5.5 Model 与 PostgreSQL

- Model 负责 ORM 映射和关系。
- PostgreSQL 通过外键、唯一约束、CHECK 和事务守住最终数据边界。
- 已执行的 Alembic revision 不改写；删除旧表或字段使用新的向前 migration。

## 6. 核心业务对象

| 对象 | 责任 |
| --- | --- |
| Job | 岗位事实和结构化要求 |
| Candidate | 稳定身份与去重，不作为跨岗位职业画像 |
| Resume | 某次申请使用的文件、原文和结构化快照 |
| Application | 候选人对一个岗位的一次独立申请和流程主记录 |
| ScreeningReport | 当前 Application 的 AI 初筛报告 |
| ScreeningRun | AI 运行状态、失败和必要审计信息 |
| StageHistory | HR 决策与招聘阶段变更历史 |
| InterviewRecord | 面试安排和反馈 |
| OfferRecord | Offer 与最终结果 |
| ActivityLog | 系统和人工操作审计 |
| KnowledgeDocument | 内部知识文件及索引状态 |
| AgentSession / AgentAction | Agent 会话、工具调用和确认记录 |

具体字段和状态由所属阶段专项设计确认，本文不维护第二套 Schema。

## 7. Candidate、Application 与 Resume 边界

- Candidate 只负责姓名、标准化联系方式等稳定身份和去重。
- Application 表示一次岗位申请，同一个人申请不同岗位时分别处理。
- 每个 Application 绑定自己的当前 Resume、AI 结果、HR 决策和招聘阶段。
- 不同岗位的简历经历、技能和项目不能互相污染评分。
- 前端可以按 Application 展示候选记录，不要求提供跨岗位人员聚合页面。

## 8. AI 能力边界

### 8.1 简历结构化

```text
Resume.raw_text -> 单次 DeepSeek -> 严格校验
                -> Resume.parsed_snapshot -> HR 核对
```

AI 只生成草稿，不直接创建或覆盖正式候选人资料。

### 8.2 JD 驱动初筛

当前阶段使用固定 Service 工作流：从 Job/JD 生成稳定评价计划，再结合当前 Resume 生成结构化报告。详细评分、证据、状态和替换规则只在阶段 7 当前设计中维护。

### 8.3 综合 Agent

```text
自然语言 -> Agent -> 强类型 Tool -> 既有 Service -> 数据库/检索层
```

Agent 不执行任意 SQL，不复制业务规则。查询可以直接执行；草稿、普通写入和高风险操作按权限与风险分级确认。

### 8.4 RAG

- 公司知识和简历使用隔离集合。
- 检索结果返回来源文件和片段。
- 简历索引复用 `raw_text/parsed_snapshot`，不新增 PDF 转 Markdown 主链。
- RAG 用于召回和检索，不代替正式初筛、淘汰或录用判断。

## 9. AI 安全与可靠性

- 简历、JD 和内部文档是不可信输入，Prompt 必须防止提示注入。
- 模型输出先经过 JSON、Schema、业务和安全校验，再进入数据库。
- 敏感信息不能用于招聘评价。
- 模型超时、限流、空响应或非法输出必须转成稳定失败语义。
- 失败不能覆盖人工输入、原文件或旧成功结果。
- 关键写操作必须具备事务、幂等、并发保护和审计。
- AI 质量需要自动化测试、真实模型、脱敏样本和人工复核共同验证。

## 10. 当前运行目录

```text
frontend/src/features/recruitment/  当前 React 招聘工作台
backend/app/api/                    FastAPI /api/v2 路由
backend/app/schemas/                Pydantic 合同
backend/app/services/               业务与固定 AI Service
backend/app/models/                 SQLAlchemy Model
backend/app/prompts/                版本化 Prompt
backend/app/adapters/               DeepSeek Adapter
backend/app/core/                   配置、数据库、文件和 LLM 基础设施
backend/migrations/                 Alembic 历史与向前迁移
```

旧 React/FastAPI/SQLite/Mock LLM 系统已经退役。当前正式入口是 `/app/*`、`/apply` 和 `/api/v2/*`。

## 11. 架构决策摘要

| 决策 | 当前选择 |
| --- | --- |
| 项目演进 | 新版直接替代旧演示系统，不维护双主链 |
| 普通 AI 功能 | Service + Adapter + 严格 Schema |
| 复杂 Agent | LangGraph + 强类型 Tools + 人工确认 |
| 业务数据库 | PostgreSQL + Alembic 向前迁移 |
| 招聘流程主对象 | Candidate 身份与 Application 申请分离 |
| 简历隔离 | 每个 Application 使用自己的当前 Resume |
| AI 决策权 | 只提供参考，人类保留最终招聘决定 |
| MCP | 暂不作为内部 MVP 必选项，未来按外部调用需求适配 |
| RAG | 负责召回、重排和来源，不替代正式评分 |

## 12. 相关文档

- 文档导航：`../DOCUMENT_INDEX.md`
- 当前状态：`../../PROJECT_STATE.md`
- 实施计划：`../planning/implementation-plan.md`
- 产品路线：`../planning/2026-08-14-post-stage5-product-roadmap.md`
- 阶段 7 单一入口：`../stages/stage7/README.md`
- 旧系统退役：`../archive/legacy-system/retirement/2026-08-18-legacy-system-retirement-decision.md`
