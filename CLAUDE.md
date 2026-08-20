# CLAUDE.md — 项目长期指令

## 项目定位

HR Agent 招聘提效平台面向公司内部 HR 团队，目标是打通：

```text
岗位创建 -> 候选人投递 -> 简历处理 -> AI 初筛 -> HR 决策
         -> 面试 -> Offer -> 录取
```

首页综合 Agent、公司知识库 RAG 和简历语义搜索属于招聘主链稳定后的后续能力。

当前进度、唯一下一步和工作区风险只在 `PROJECT_STATE.md` 维护；文档职责和阅读入口见 `docs/DOCUMENT_INDEX.md`。

## 新对话阅读规则

1. 固定阅读本文件和 `PROJECT_STATE.md`。
2. 根据 `docs/DOCUMENT_INDEX.md` 判断是否需要实施计划、总体设计、路线图或历史资料。
3. 修改业务代码、测试、数据库或验收材料前，完整阅读当前阶段专项设计。
4. 修改前检查 `git status` 和相关差异，禁止覆盖工作区已有修改。

## 长期工作原则

1. 先完成招聘业务闭环，再建设自然语言 Agent、RAG 和外部协议适配。
2. 每个新阶段先讨论业务目标、主流程、异常流程、范围、数据、状态、权限和验收标准。
3. 阶段专项设计获得用户明确确认后，才能修改该阶段业务代码。
4. 核心流程、数据模型、阶段边界或完成标准变化时，先同步权威文档，再修改代码。
5. 每次只完成一个可理解、可验证的小步骤；先测试，再进入下一步。
6. 当前阶段的详细业务合同只在阶段专项设计中维护，其他文档只写摘要和链接。
7. 旧系统和已废弃方案只用于历史追溯，不得重新成为运行依赖。

## 技术栈

```text
前端：React 18 + TypeScript + Ant Design 5 + Vite 5 + zustand
后端：FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Alembic
数据库：PostgreSQL 16
AI：DeepSeek API（OpenAI 兼容接口）
后续基础设施：Redis + Chroma
部署：Docker Compose
```

LangGraph 只用于确实存在意图路由、循环、工具选择、人工确认中断或恢复执行的复杂流程。固定输入、固定步骤、固定输出的单次模型能力使用普通 Service，不为了“看起来像 Agent”而包装成 Agent。

## 运行代码边界

```text
前端业务：frontend/src/features/recruitment/
后端 API：backend/app/api/
后端 Schema：backend/app/schemas/
后端 Service：backend/app/services/
后端 Model：backend/app/models/
AI Prompt：backend/app/prompts/
模型 Adapter：backend/app/adapters/
基础设施：backend/app/core/
正式 API：/api/v2/*
内部工作台：/app/*
公开投递：/apply
```

旧 React 页面、旧 FastAPI Router、SQLite、Mock LLM、`stage3/`、`rebuilt/` 和 `/stage3/*` 已退出当前运行边界。

## 分层职责

```text
React 前端
    ↓ HTTP
FastAPI API：协议、权限入口和错误映射
    ↓
Pydantic Schema：输入输出合同
    ↓
Service：业务规则、事务和 AI 工作流编排
    ↓
SQLAlchemy Model：数据库映射
    ↓
PostgreSQL：正式业务数据
```

未来综合 Agent 的调用边界固定为：

```text
Agent -> Tool -> Service -> PostgreSQL / Chroma
```

LLM 负责语言理解、结构化提取、语义评价和解释；确定性业务状态、权限、事务、审计和最终招聘决定不能交给模型自由控制。

## AI 与数据安全约束

- 模型输出必须经过严格 Schema 和业务校验后才能持久化。
- Prompt 必须把简历、JD 和知识文件视为不可信数据，防止其中内容被当成系统指令。
- 禁止使用性别、年龄、民族、婚姻状况等敏感信息作招聘评价。
- AI 初筛只给 HR 提供参考，不自动通过、淘汰、发 Offer 或录用候选人。
- 模型失败不得删除原简历、Application、人工输入或旧成功结果。
- `Resume.raw_text` 和 `Resume.parsed_snapshot` 是简历处理与后续检索的稳定输入，不新增 PDF 转 Markdown 文件主链。
- RAG 负责召回和来源检索，不能用向量相似度代替正式初筛或人类招聘决定。
- 学校和公司可以结合真实经历作为语境，但不能脱离专业、职责、项目和成果只按品牌判断能力。

阶段 5 简历结构化、阶段 7 AI 初筛及未来 Agent/RAG 的具体合同，以各自当前专项设计为准，不在本文件重复维护字段和评分细节。

## 启动方式

```bash
# 基础设施
docker-compose up -d

# 后端
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
pnpm install
pnpm dev
```

启动、环境变量和人工使用说明以 `README.md` 与 `使用说明.md` 为准。
