# HR智聘 — AI 招聘全流程平台

一个面向公司内部 HR 团队的 AI 招聘全流程工作台。项目使用 React、FastAPI、PostgreSQL 和 DeepSeek，打通岗位创建、候选人投递、简历处理、AI 初筛、HR 决策、面试、Offer、录取和入职，并通过严格 Schema、持久化 Worker、事务、幂等和审计保护业务事实。

> 当前状态：阶段 4—9 已完成并通过项目负责人验收。当前秋招版本以招聘业务闭环为功能终点；首页综合 Agent 和 RAG 暂缓，登录/RBAC 与生产部署尚未完成。

## 核心业务流程

```text
HR 创建并开放岗位
        ↓
候选人公开投递 / HR 内部录入
        ↓
可靠保存 Candidate / Resume / Application
        ↓
后台提取原文 → AI 结构化 → JD 驱动 AI 初筛
        ↓
HR 独立决定通过 / 备选 / 淘汰
        ↓
多轮面试 → Offer → 接受 → 录取 → 正式入职
        ↓
统一时间线、审计记录与招聘流程统计
```

AI 只负责提取、评价、解释和生成辅助信息，不会自动通过、淘汰、发 Offer、录取或确认入职。

## 已完成功能

| 能力 | 当前状态 | 说明 |
| --- | --- | --- |
| 岗位管理 | 已完成 | 五段式 JD，支持创建、编辑、开放、关闭、重新开放、安全删除和只读评价计划 |
| 简历处理 | 已完成 | PDF、DOCX、TXT 私有上传，原文提取、DeepSeek 结构化草稿和人工核对 |
| 公开投递 | 已完成 | `/apply` 提供开放岗位查询、隐私确认、文件校验、限流、幂等提交和公开凭证 |
| 异步自动处理 | 已完成 | PostgreSQL 持久任务推进原文、结构化和初筛，支持租约、重试、恢复和人工重试 |
| AI 初筛 | 已完成 | JD 评价计划、逐项证据、严格输出校验、报告替换、失败保留、过期提示和批量重评 |
| HR 决策 | 已完成 | AI 不替代人工决定；通过、备选、淘汰及更正写入持久历史 |
| 候选人工作台 | 已完成 | 初筛通过的 Application 独立进入候选人视图，并复用统一详情继续后半程流程 |
| 面试流程 | 已完成 | 多轮安排、改期、取消、未到场、反馈、进入下一轮/Offer、淘汰和受控更正 |
| Offer 与录取 | 已完成 | 草稿、编辑、发送、接受、拒绝、撤回、过期、录取、入职、退出和重新打开 |
| 招聘统计 | 已完成 | 固定 cohort 的 8 步漏斗、7 段耗时/样本数和 7 类实时待办 |
| Agent / RAG | 暂缓 | 保留为长期可选方向，不属于当前秋招版本 |
| 登录 / RBAC | 未完成 | 当前是本地作品集工作台，不能直接承载真实招聘数据 |

## 工程亮点

- 使用 `Candidate → Application → Resume` 边界隔离不同岗位申请，避免跨岗位简历和 AI 结果互相污染。
- 模型输出经过 JSON、Pydantic Schema、业务规则和安全校验后才能持久化。
- 简历和 JD 按不可信数据处理；进入模型前移除联系方式等隐私字段，并禁止用敏感属性评价候选人。
- AI 运行失败不会删除原简历、人工输入或最近一次成功报告。
- 公开投递先提交数据库事务，再由后台 Worker 处理文件和 AI，避免 HTTP 超时导致投递事实丢失。
- PostgreSQL Worker 使用租约与 `SKIP LOCKED` 支持多 Worker 安全领取、过期恢复和有限重试。
- 面试、Offer 与录取状态使用行锁、乐观版本、数据库约束和同事务审计保护并发一致性。
- Offer 金额保持 Decimal/NUMERIC 语义，只在单个 Application 的 Offer 详情按需返回，不进入列表、统计或普通审计。

## 技术架构

```text
React 18 + TypeScript + Ant Design
                ↓ HTTP
FastAPI API：协议、依赖注入、错误映射
                ↓
Pydantic Schema：请求、响应和模型输出合同
                ↓
Service：业务规则、AI 编排、事务、幂等和并发
                ↓
SQLAlchemy Model + Alembic
                ↓
PostgreSQL 16

AI 子链路：Prompt → DeepSeek Adapter → 严格校验 → 持久化 → HR 决策
异步子链路：公开投递 → PostgreSQL ProcessingRun → Worker → 结构化/初筛
```

| 层级 | 技术 |
| --- | --- |
| 前端 | React 18、TypeScript、Ant Design 5、Vite 5、Axios |
| 后端 | FastAPI、Pydantic v2、SQLAlchemy 2.0 Async |
| 数据 | PostgreSQL 16、Alembic、Redis 7 |
| AI | DeepSeek API（OpenAI 兼容接口）、版本化 Prompt 与 Schema |
| 文件 | 私有存储、SHA-256、PDF/DOCX/TXT 提取和 DOCX 安全检查 |
| 测试 | Python unittest/pytest、真实 PostgreSQL/API、Node 前端合同测试、TypeScript/Vite build |

Chroma 基础设施仍保留在 Docker Compose 中，但当前没有交付 RAG 业务能力。

## 快速启动

### 环境要求

- Windows 10/11
- Python 3.11
- Node.js 18 或更高版本
- Docker Desktop 与 Docker Compose
- Git

### 1. 可选：配置真实 AI

如果需要运行真实简历结构化或 AI 初筛，复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

然后在 `.env` 中配置有效的 DeepSeek Key：

```dotenv
DEEPSEEK_API_KEY=你的密钥
```

`.env` 不得提交到 Git。没有有效配置时仍可查看不依赖模型的页面和接口，但不能把模型失败或 Mock 输出当作真实 AI 结果。

### 2. Windows 一键启动

双击：

```text
launch\start_project.bat
```

启动器会检查环境、启动 PostgreSQL/Redis/Chroma、安装缺失依赖、执行 Alembic migration，并启动 FastAPI 与 Vite。默认打开岗位管理页。

只检查环境：

```powershell
launch\start_project.bat -CheckOnly
```

启动但不自动打开浏览器：

```powershell
launch\start_project.bat -NoBrowser
```

### 3. 手动启动

首次创建 Python 环境：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest==9.1.1
```

启动基础设施：

```powershell
docker compose up -d postgres redis chroma
```

启动后端：

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另开一个 PowerShell 启动前端：

```powershell
Set-Location frontend
npm install
npm run dev -- --host 127.0.0.1
```

## 页面入口

| 地址 | 用途 |
| --- | --- |
| `http://localhost:5173/app/dashboard` | 工作台与招聘流程统计 |
| `http://localhost:5173/app/jobs` | 岗位管理与 JD 评价计划 |
| `http://localhost:5173/app/screening` | 待决策、备选和初筛淘汰 Application |
| `http://localhost:5173/app/candidates` | HR 已通过候选人的面试、Offer 与录取流程 |
| `http://localhost:5173/app/candidates/new` | HR 内部录入候选人和简历 |
| `http://localhost:5173/apply` | 候选人公开投递 |
| `http://localhost:8000/docs` | FastAPI Swagger 文档 |
| `http://localhost:8000/api/health` | 后端健康检查 |

旧 `/app/resumes` 和 `/app/reports` 会安全跳转到 AI 初筛中心，不再作为独立业务入口。

## 数据与安全边界

- 正式业务数据只使用 PostgreSQL，不使用 SQLite 或自动 seed。
- 新数据库启动后业务表为空属于正常现象；请只使用虚构或完整脱敏数据演示。
- 简历原文件保存在 `STORAGE_DIR` 指向的私有目录，不通过静态目录公开。
- 数据库结构由 Alembic 管理；当前 head 为 `b9e2f4a6c801`。
- 公开投递具有请求体上限、Redis 摘要限流、文件校验、幂等和数据库/文件补偿。
- 当前没有登录、RBAC、字段级薪资授权和多租户隔离，只适合作品集与本地演示。
- 当前没有生产级恶意文件扫描、可信代理配置、压力测试、告警体系或完整日志隐私评审。
- 首页综合 Agent 和 RAG 已暂缓，不能在简历或演示中描述为已交付。

## 验证

后端完整回归：

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests
```

前端全部测试脚本：

```powershell
Set-Location frontend
$package = Get-Content -Raw package.json | ConvertFrom-Json
$tests = $package.scripts.PSObject.Properties | Where-Object { $_.Name -like 'test:*' }
foreach ($test in $tests) {
    npm run $($test.Name)
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

前端生产构建：

```powershell
Set-Location frontend
npm run build
```

数据库一致性：

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic check
```

阶段 9 封版证据：后端 `1445 passed, 2 warnings, 525 subtests passed`；前端 29 个测试文件和 production build 通过；Alembic 为 `b9e2f4a6c801 (head)` 且无待生成迁移。测试证明当前覆盖的合同、事务和并发行为，不代表已经完成生产压力、权限、多浏览器或安全审计。

## 目录结构

```text
backend/
  app/
    adapters/       # 外部模型适配器
    api/            # FastAPI /api/v2 路由
    core/           # 配置、数据库、Redis、文件和 LLM 基础设施
    models/         # SQLAlchemy ORM
    prompts/        # 版本化 Prompt
    schemas/        # HTTP 与模型输出合同
    services/       # 业务规则、事务和 AI 编排
  migrations/       # Alembic 向前迁移
  tests/            # 后端自动化和 PostgreSQL 集成测试

frontend/
  src/features/recruitment/  # 当前招聘工作台
  tests/                     # 前端合同测试

docs/
  DOCUMENT_INDEX.md          # 文档导航入口
  planning/                  # 路线与实施顺序
  architecture/              # 总体架构
  stages/                    # 阶段设计、实施和验收证据
  archive/                   # 只用于历史追溯
```

## 权威文档

- [项目当前状态](PROJECT_STATE.md)
- [文档索引](docs/DOCUMENT_INDEX.md)
- [总体架构](docs/architecture/2026-07-15-hr-agent-platform-design.md)
- [实施计划](docs/planning/implementation-plan.md)
- [阶段 7 AI 初筛入口](docs/stages/stage7/README.md)
- [阶段 8 公开投递与异步处理设计](docs/stages/stage8/2026-09-02-stage8-public-application-async-processing-design.md)
- [阶段 9 面试、Offer 与录取设计](docs/stages/stage9/2026-09-02-stage9-interview-offer-hiring-pipeline-design.md)
- [阶段 9 实施与最终验收](docs/stages/stage9/2026-09-02-stage9-implementation-record.md)

## 停止服务

在前端和后端窗口分别按 `Ctrl+C`。停止基础设施但保留数据卷：

```powershell
docker compose stop postgres redis chroma
```

不要把 `docker compose down -v` 当作普通停止命令；`-v` 会删除持久化数据卷。
