# GitHub 招聘项目对比与借鉴决策

> 日期：2026-08-15
>
> 状态：已完成讨论，作为阶段 6—12 的外部参考基线；具体字段、状态和验收标准仍须在每个阶段开始前单独确认
>
> 上游路线：`../specs/2026-08-14-post-stage5-product-roadmap.md`

## 1. 文档目的

本文整理当前项目与五个公开 GitHub 项目的区别，明确哪些能力值得借鉴、为什么借鉴，以及哪些内容不进入当前路线。外部项目只用于校准产品结构和技术边界，不替代本项目的阶段需求确认，也不直接复制受许可证约束的代码。

对比基于新版 PostgreSQL 重建主线，而不是旧版 SQLite 演示系统。旧版虽然已有投递、初筛、面试和 Offer 演示逻辑，但不能视为新版招聘闭环已经完成。

## 2. 当前项目的位置

当前阶段 5 已完成，已经具备：

- FastAPI、React、PostgreSQL、Alembic 的新版基础。
- PDF、DOCX、TXT 安全上传、私有存储和原文提取。
- `Resume.raw_text` 持久化、文件解析状态和稳定错误。
- 单次 DeepSeek 简历结构化、严格 Schema 校验和草稿持久化。
- HR 内部手动新增场景的草稿核对与 Candidate 创建。
- Job、Candidate、Resume、ScreeningResult 等新版模型和基础 API。

当前尚未正式完成：

- Candidate 与 Application 分离。
- 新版公开投递、异步自动处理和异常任务区。
- 可解释的正式初筛引擎、评分证据、快照和版本。
- 新版面试、Offer、录取、退出和完整阶段历史。
- 首页综合 Agent、业务 Tools、确认中断和会话审计。
- RAG 入库、分块、Embedding、召回、重排序和来源引用。
- 完整登录、RBAC、隐私、数据保留和生产交付。

最终产品不是其中某一个开源项目的复刻，而是：

```text
完整招聘业务链路
+ 可解释 AI 初筛
+ 首页综合 Agent
+ 简历语义搜索和公司知识库 RAG
```

## 3. 总体对比

| 参考项目 | 核心定位 | 它对当前项目最有价值的部分 | 明确不照搬的部分 |
| --- | --- | --- | --- |
| [Reqcore](https://github.com/reqcore-inc/reqcore) | 完整 ATS | Application、Pipeline、公开/后台边界、私有简历、历史保留 | Nuxt/Vue、早期多租户和计费、AGPL 代码 |
| [SAP Recruiting Agent](https://github.com/SAP-samples/smartrecruiters-ai-recruiting-custom-agent) | 现有 ATS 上的招聘 Agent | LLM、Tools、确定性 Python 业务逻辑分工和降级 | SmartRecruiters/SAP/Teams 集成、过早预测模型 |
| [HackerRank Hiring Agent](https://github.com/interviewstreet/hiring-agent) | 简历评价流水线 | Rubric、逐项证据、加分/扣分、Prompt/模型版本和缓存 | PDF 转 Markdown、每章节一次模型调用、默认 GitHub 评价 |
| [Resume Screening RAG Pipeline](https://github.com/Hungreeee/Resume-Screening-RAG-Pipeline) | 简历语义召回 POC | 查询分类、多查询、Small-to-Big、去重重排和命中片段 | Streamlit 上传、用向量相似度直接决定招聘结果 |
| [MCP Resume Screening](https://github.com/run-llama/mcp_resume_screening) | 对外暴露筛选工具的 MCP 示例 | 单一职责工具和清晰输入输出 | 当前阶段直接建设远程 MCP Server、AI 解析 JD 必经流程 |

## 4. Reqcore：校准招聘业务骨架

### 4.1 根本区别

Reqcore 已经是一套 ATS，岗位、候选人、Application、公开投递、Pipeline、简历解析和 AI Shortlist 已经连接起来。当前项目的新版主线主要完成到简历结构化底座，`Candidate` 仍直接保存 `applied_job_id` 和状态，还没有独立 Application。

### 4.2 借鉴项与原因

1. **Candidate 与 Application 分离**
   - Candidate 表示“这个人是谁”。
   - Application 表示“这个人对某个岗位的一次投递”。
   - 原因：同一个候选人可能投递多个岗位，每次投递必须拥有独立的初筛、面试、Offer 和最终结果。
2. **以 Application 为中心的 Pipeline/Kanban**
   - 原因：HR 需要按岗位观察待初筛、面试、Offer、录用等人数，不能把 Candidate 的单一状态当作所有投递的状态。
3. **公开路由与后台路由隔离**
   - 原因：候选人可以公开查看开放岗位和提交申请，但不能访问简历、评分、面试反馈和内部统计。
4. **简历私有存储并通过鉴权接口读取**
   - 原因：简历包含联系方式和工作经历，不能公开暴露底层文件地址。
5. **岗位关闭后保留历史 Application、数据保留与删除**
   - 原因：招聘记录需要追溯，也必须支持后续隐私和删除要求。

### 4.3 不借鉴项

- 保持 React + FastAPI + PostgreSQL 技术栈，不切换 Nuxt/Vue。
- 只研究产品结构和数据关系，不直接复制 AGPL-3.0 代码。
- 多租户、计费和商业套餐不进入早期 MVP。

## 5. SAP Recruiting Agent：校准综合 Agent 分工

### 5.1 根本区别

SAP 项目不是从零建设招聘系统，而是在已有 SmartRecruiters ATS 上增加智能助手。可以用“大白话”理解：SAP 项目是在已经运营的餐厅里增加智能店长；本项目需要先自己建设餐厅、厨房和订单系统，再增加智能店长。

因此 SAP 项目主要指导本项目的阶段 10，不能替代阶段 6—9 的招聘业务建设。

### 5.2 借鉴项与原因

采用以下职责分工：

```text
LLM：理解 HR 的自然语言、选择工具、组织回答
Tool：把 Agent 的意图转换成一个受控业务能力调用
Service：查询、计算、校验权限、改变状态
PostgreSQL/Chroma：保存事实数据和检索数据
```

例如“岗位 A 最匹配的 5 个人”不能由 LLM 临时阅读所有简历后自行排名，而应调用已验证的排名和证据 Service，再由 LLM 解释结果。

原因：

- 数据库和 API 是事实来源，避免模型编造业务数据。
- 统计、天数、规则得分等由 Python 计算，结果稳定且可测试。
- 更换大模型不会改变核心业务规则。
- LLM 不可用时，查询和分析 Service 仍然可以通过模板结果降级运行。

### 5.3 不借鉴项

- 不接入 SmartRecruiters、SAP AI Core 或 Teams 作为当前前提。
- 没有足够历史数据前，不建设候选人流失风险和招聘周期预测。

## 6. HackerRank Hiring Agent：校准初筛质量

### 6.1 根本区别

Hiring Agent 是“输入一份简历、输出评价结果”的流水线，不是完整招聘管理系统。当前项目在上传安全、数据库、API、状态和生命周期方面更完整，但在正式评分 Rubric、逐项证据和评估体系方面还没有实现。

### 6.2 借鉴项与原因

1. **岗位级 Rubric 和固定权重**：让同一岗位的候选人使用同一套标准，减少 Prompt 表述变化造成的漂移。
2. **每个评分项附带简历证据和岗位证据**：让 HR 能核对“为什么得分”，降低黑盒感。
3. **加分项、扣分项和风险分开保存**：避免把不同性质的信息混成一段自然语言。
4. **保存规则、Prompt、模型、岗位快照和简历快照版本**：支持重跑、历史解释和评分争议追溯。
5. **模型 Provider 抽象**：当前使用 DeepSeek，业务逻辑不应与单一模型写死。
6. **开发缓存和脱敏样本评估**：降低调试成本，并能够量化准确率、稳定性、耗时和费用。
7. **公平性约束**：性别、年龄、民族、婚姻状况不得进入招聘评分。

### 6.3 不借鉴项

- 当前 PDF/DOCX 原文提取已经满足结构化识别，不增加 PDF 转 Markdown。
- 不照搬“每个章节分别调用一次模型”，保持一次结构化调用，除非真实样本证明需要改变。
- 不默认使用 GitHub 活跃度评价所有岗位，避免对非研发岗位和没有公开代码的候选人形成偏差。

## 7. Resume Screening RAG：校准候选人召回

### 7.1 根本区别

该项目已完成研究型向量召回流程，但不是正式 ATS。当前项目有安全上传、结构化数据和业务模型，但 RAG 目前只有 Chroma 连接骨架。

### 7.2 借鉴项与原因

1. **查询分类**：数据库可以回答的精确统计不启动 RAG；只有语义搜索和知识问答才检索向量库，降低延迟和成本。
2. **结构化过滤 + 向量召回**：先按岗位、状态、年限等过滤，再做语义检索，避免不相关候选人进入结果。
3. **复杂问题拆成多个子查询并合并重排**：提高多条件岗位问题的召回完整度。
4. **Small-to-Big**：先检索小片段，再取回候选人完整结构化简历，让检索有效率、回答有上下文。
5. **返回命中片段和来源元数据**：HR 可以核对推荐依据。

RAG 只负责“找到可能相关的人”，不能用向量相似度直接代替正式岗位评分。正式顺序为：

```text
结构化过滤 -> 语义召回 -> 去重重排 -> 正式初筛 -> 证据解释
```

### 7.3 简历内容格式决策

不建设 PDF 转 Markdown 文件流程。简历 RAG 优先使用：

```text
Resume.raw_text + Resume.parsed_snapshot
        ↓
按基本信息、工作、项目、教育、技能生成检索片段
        ↓
附加 candidate_id、resume_id、section、时间等元数据
        ↓
Embedding 与 Chroma 索引
```

可以在内存中把结构化字段渲染为 Markdown 风格文本以增强片段可读性，但它只是索引文本的组织形式，不产生 `.md` 文件，也不替换 `raw_text`。

## 8. MCP Resume Screening：校准工具边界

### 8.1 Tools 与 MCP 的区别

- Tool 是 Agent 可以调用的一项能力。
- MCP 是把能力暴露给外部 Agent 或客户端的一种通信协议。

当前首页 Agent、FastAPI 和业务 Service 位于同一系统，优先使用内部结构化 Tools：

```text
首页 Agent -> Tool -> Service -> PostgreSQL/Chroma
```

### 8.2 借鉴项与原因

借鉴单一职责、强类型输入输出和清晰工具粒度，例如：

- `get_job`
- `list_ranked_applications`
- `get_screening_evidence`
- `search_candidates`
- `generate_job_draft`
- `search_company_knowledge`
- `transition_application_stage`

原因：工具越清晰，越容易测试、授权、审计、限流和处理失败。

### 8.3 MCP 决策

MCP 不作为阶段 10 或当前 MVP 的必选项。业务实现放在 Service，Tool 只包装 Service。未来确实需要让外部 Agent、IDE 或其他系统调用时，再增加薄的 MCP Adapter，不能把 MCP Server 作为核心业务层。

## 9. 统一落地路线

| 阶段 | 主要参考 | 落地内容 |
| --- | --- | --- |
| 阶段 6 | Reqcore | 结构化岗位、状态和开放/关闭边界 |
| 阶段 7 | Reqcore + Hiring Agent | Application、正式初筛、Rubric、证据、快照和版本 |
| 阶段 8 | Reqcore | 公开/后台隔离、可靠投递、异步自动处理和异常区 |
| 阶段 9 | Reqcore | Pipeline、面试、Offer、录取和阶段历史 |
| 阶段 10 | SAP Agent + MCP 示例 | 内部 Tools、确定性 Service、分级确认、降级和审计 |
| 阶段 11 | Resume Screening RAG | 查询分类、分块、召回、重排、来源引用和集合隔离 |
| 阶段 12 | Reqcore 等生产实践 | 登录、权限、隐私、保留、限流、测试和部署 |

## 10. 当前确认的技术边界

- 阶段 6 不把 AI 解析 JD 作为岗位创建前置步骤。
- 公开投递正常简历自动进入 AI 初筛池，不要求 HR 逐份确认结构化草稿。
- PDF/DOCX 继续提取纯文本并保留 `raw_text`，不增加 PDF 转 Markdown。
- 初筛使用“确定性规则 + LLM 语义判断”，RAG 相似度不直接作为录取依据。
- Agent 必须通过 Tools 和 Service 访问业务能力，不能直接执行任意 SQL。
- 查询可直接执行；草稿不产生正式业务结果；写入和高风险操作按级别确认并审计。
- Tools 是阶段 10 必选能力，MCP 是未来可选适配，不提前建设。
- 每个阶段仍需先讨论业务需求、范围、状态、权限、失败语义和验收标准，确认后才能开发。
