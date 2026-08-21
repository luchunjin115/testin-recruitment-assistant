# HR Agent 招聘提效平台

一个面向公司内部 HR 团队的 AI 招聘工作台。项目使用 React、FastAPI 和 PostgreSQL 构建招聘业务主链，并在简历结构化和 JD 驱动的 AI 初筛中接入可审计的 AI 能力。

> 当前状态：阶段 4—6 已完成；阶段 7 的旧 Rubric、权重评分和 ScreeningResult 体系已删除，JobEvaluationPlan、严格 AI 评价、持久运行、幂等、当前报告替换和 React 完整报告交互已完成。下一步等待专项质量验收。旧 React + FastAPI + SQLite + Mock LLM 演示系统及其演示数据已于 2026-08-18 完成退役。

## 当前能做什么

| 能力 | 当前状态 | 说明 |
| --- | --- | --- |
| 岗位管理 | 可用 | 创建、编辑、开放、关闭、重新开放、安全删除，并只读预览当前 JD 评价计划 |
| 候选人管理 | 可用 | 列表、创建、详情和基础资料维护 |
| 简历处理 | 可用 | PDF、DOCX、TXT 私有上传、原文提取、AI 结构化、人工核对后绑定候选人 |
| Application 申请合同 | 可用 | 录入、身份解析、简历隔离、状态、历史和独立 HR 决策 |
| AI 初筛 | 可用 | 支持运行状态、完整报告、证据展开、过期提示、普通复用、单人/最多 20 人重新评估和失败保留旧报告 |
| Dashboard | 可用 | 读取 PostgreSQL 中的岗位、候选人和待处理 Application 统计 |
| 报告中心 | 只读 | `/app/reports` 继续查看通用 Report；Application 的当前 AI 报告在 `/app/screening` 查看 |
| 公开投递 | 页面预览 | `/apply` 可读取开放岗位，提交按钮尚未开放 |
| 权限、面试、Offer、Agent、RAG | 未完成 | 属于后续阶段，不在当前完成范围内 |

AI 结论只用于辅助 HR，不会自动通过或淘汰候选人。

## 技术栈

- 前端：React 18、TypeScript、Ant Design 5、Vite、Axios
- 后端：FastAPI、SQLAlchemy 2.0 Async、Pydantic v2、Alembic
- 数据：PostgreSQL 16、Redis 7、Chroma
- AI：DeepSeek/OpenAI 兼容接口，Prompt 与输出 Schema 版本化
- 基础设施：Docker Compose
- 测试：Python `unittest`、Node/Vite 模块测试、TypeScript 生产构建

## 当前架构

```text
React 页面
  -> /api/v2
FastAPI Router
  -> Pydantic Schema
  -> Application Service
  -> SQLAlchemy Model
  -> PostgreSQL

当前 AI 子链路
  -> Prompt Builder
  -> Provider Adapter
  -> DeepSeek JSON Output
  -> 严格 Schema 校验
  -> Resume 结构化草稿
```

Redis 和 Chroma 已完成基础设施接入，但综合 Agent 与 RAG 业务仍属于后续阶段。

## 环境要求

- Windows 10/11
- Python 3.11（项目当前验证版本）
- Node.js 18 或更高版本
- Docker Desktop 与 Docker Compose
- Git

## 快速启动

### 1. 可选：准备环境变量

如果只查看不需要 AI 调用的页面，可以直接使用默认配置启动。需要验证真实简历结构化或 JD 评价计划生成时，复制环境变量模板并配置自己的 DeepSeek Key：

```powershell
Copy-Item .env.example .env
```

在 `.env` 中配置：

```dotenv
DEEPSEEK_API_KEY=你的密钥
```

`.env` 不得提交到 Git。

### 2. Windows 一键启动（推荐）

双击：

```text
launch\start_project.bat
```

脚本会依次：

1. 检查 Docker、Python、Node 和 npm。
2. 启动 PostgreSQL、Redis、Chroma。
3. 安装缺失的后端依赖。
4. 执行 `alembic upgrade head`。
5. 安装缺失的前端依赖。
6. 启动 FastAPI 与 Vite。
7. 打开 `http://localhost:5173/app/jobs`。

只检查环境、不启动服务：

```powershell
launch\start_project.bat -CheckOnly
```

启动但不自动打开浏览器：

```powershell
launch\start_project.bat -NoBrowser
```

### 3. 手动启动

首次准备 Python 虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

启动基础设施：

```powershell
docker compose up -d postgres redis chroma
```

升级数据库并启动后端：

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

## 本地地址

| 地址 | 用途 |
| --- | --- |
| `http://localhost:5173/` | 自动进入 HR 工作台 |
| `http://localhost:5173/app/dashboard` | Dashboard |
| `http://localhost:5173/app/resumes` | 简历管理 |
| `http://localhost:5173/app/candidates` | 候选人管理 |
| `http://localhost:5173/app/candidates/new` | 新增候选人和简历智能识别 |
| `http://localhost:5173/app/jobs` | 岗位管理与只读评价计划预览 |
| `http://localhost:5173/app/screening` | Application、AI 完整报告、重新评估与 HR 独立决策 |
| `http://localhost:5173/app/reports` | 通用报告中心 |
| `http://localhost:5173/apply` | 公开投递页预览 |
| `http://localhost:8000/docs` | FastAPI Swagger 文档 |
| `http://localhost:8000/api/health` | 后端健康检查 |

## 初始数据状态

项目不会自动创建候选人、岗位、简历或初筛演示数据。一个新数据库启动后，业务表为空是正常现象。

- 不存在 SQLite 运行数据库。
- 不存在自动 seed 或重置演示数据脚本。
- 简历文件使用 `STORAGE_DIR` 指向的私有目录。
- 文件不会通过 `/uploads` 静态公开。
- 数据库结构由 Alembic 管理。

请通过当前 UI 或 `/docs` 中的 `/api/v2` 接口创建自己的开发数据。

## AI 配置说明

`.env.example` 中的 `RESUME_STRUCTURE_*` 用于简历结构化，`JOB_EVALUATION_PLAN_*` 用于 JD 评价计划生成，`SCREENING_EVALUATION_*` 与 `SCREENING_WORKER_*` 用于候选人评价和 PostgreSQL 持久任务工人。AI SDK 自动重试保持关闭；评价计划和候选人评价 Service 只对网络、限流、超时和模型服务端错误额外重试 1 次。

平台可以在没有 Key 的情况下启动，但真实 AI 请求需要有效的 DeepSeek 配置。配置缺失或模型调用失败时，相关业务接口会返回明确错误，不应把失败结果当作真实 AI 结论。

`LLM_PROVIDER=mock` 是通用 LLM 配置，不代表阶段 5 的专用简历结构化链路一定会生成模拟成功结果。

## JobEvaluationPlan API

岗位创建即开放、开放、重新开放或开放状态下修改后，后端会在岗位事务提交后尝试生成当前 JD 指纹对应的评价计划。生成失败不会回滚岗位发布。React 岗位列表中的“评价计划”入口会展示状态、事项、来源、警告和版本；这里只读，不提供旧 Rubric 式编辑、权重或发布流程。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/v2/jobs/{job_id}/evaluation-plan` | 查询当前 JD 的只读评价计划 |
| `POST` | `/api/v2/jobs/{job_id}/evaluation-plan/generate` | 幂等触发当前 JD 计划生成 |
| `POST` | `/api/v2/jobs/{job_id}/evaluation-plan/regenerate` | 重新生成失败的当前计划 |

当前项目尚未实现登录与 RBAC，这些接口继承现有 `/api/v2/jobs` 的内部开发接口边界。

## AI 初筛运行 API

Application 创建后，系统只在数据库事务提交成功后创建持久 `ScreeningRun`；HTTP 请求不会等待 DeepSeek。FastAPI 生命周期中的 worker 从 PostgreSQL 领取任务，成功后在一个事务中替换该 Application 唯一的当前 `ScreeningReport`，失败时保留旧报告。任务状态和租约都在数据库中，进程重启后可继续解释和恢复，不依赖内存任务状态。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/v2/applications/{application_id}/screening` | 查询当前报告和最近运行 |
| `POST` | `/api/v2/applications/{application_id}/screening` | 幂等触发普通初筛 |
| `POST` | `/api/v2/applications/{application_id}/screening/re-evaluate` | 单人重新评估 |
| `POST` | `/api/v2/jobs/{job_id}/screening/re-evaluate-batch` | 同一岗位下 1—20 人重新评估 |
| `PUT` | `/api/v2/applications/{application_id}/current-resume` | 切换当前 Resume 并使旧报告过期，不自动重评 |

这些接口同样沿用当前内部开发边界；项目尚未实现登录/RBAC，不能把它们当作已经具备生产权限控制。

在 `/app/screening` 中，“查看 AI 报告”会展示当前成功报告和最近运行；`queued/running` 时页面每 4 秒最小轮询，终态或关闭抽屉后停止。普通“开始初筛”可能复用相同报告或运行；“重新评估”会二次确认并创建主动运行。新运行期间或失败后旧成功报告继续显示，过期报告不会自动调用 AI。批量重新评估只允许同一岗位 1—20 个 Application。

## 项目目录

```text
backend/
  app/
    adapters/       # 外部模型适配器
    agents/         # 后续 Agent 骨架
    api/            # FastAPI Router
    core/           # 配置、数据库、Redis、LLM
    models/         # SQLAlchemy PostgreSQL Model
    prompts/        # 版本化 Prompt Builder
    rag/            # 后续 RAG 骨架
    schemas/        # Pydantic v2 合同
    services/       # 招聘业务与 AI 编排
  migrations/       # Alembic 历史
  tests/            # 后端自动化测试

frontend/
  src/
    features/recruitment/  # 招聘工作台功能模块
    services/http.ts       # API 客户端
    theme/                 # Ant Design 主题
  tests/                   # 前端模块与边界测试

docs/
  DOCUMENT_INDEX.md  # 文档总入口
  planning/          # 路线与实施顺序
  architecture/      # 总体架构
  stages/            # 阶段 4—7 专项设计与验收
  research/          # 外部项目研究
  archive/           # 历史、旧系统与被替代方案

launch/             # Windows 启动入口
sample_data/        # 受控 Prompt/测试样例，不是运行时 seed
scripts/            # 当前项目启动脚本
```

## 验证命令

后端全量测试：

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

当前验证基线：后端 573 项测试、前端 16 个测试脚本、Vite 生产构建 3116 个模块、Alembic revision `b7f2c9d4e816`。

## 停止服务

在后端和前端窗口分别按 `Ctrl+C`。如需停止基础设施容器：

```powershell
docker compose stop postgres redis chroma
```

该命令不会删除 Docker volume。

## 当前开发边界

以下能力尚未完成，不应在演示或简历中描述为已交付：

- 公开投递表单正式提交
- 真实 DeepSeek 的 20 份 JD 与 20 组 JD/Resume 专项质量验收
- 面试、Offer、录取闭环
- 登录、角色与权限
- 综合 Agent 与 RAG 知识库
- 经过验收的生产部署

当前进度、下一小步和验证证据以 [PROJECT_STATE.md](PROJECT_STATE.md) 为准。

## 权威文档

- [项目状态](PROJECT_STATE.md)
- [实施计划](docs/planning/implementation-plan.md)
- [总体设计](docs/architecture/2026-07-15-hr-agent-platform-design.md)
- [阶段 5 后路线图](docs/planning/2026-08-14-post-stage5-product-roadmap.md)
- [阶段 7 当前设计](docs/stages/stage7/2026-08-20-stage7-jd-driven-ai-screening-redesign.md)
- [项目文档索引](docs/DOCUMENT_INDEX.md)
- [旧系统退役决策](docs/archive/legacy-system/retirement/2026-08-18-legacy-system-retirement-decision.md)
- [最终命名与交付计划](docs/archive/legacy-system/retirement/2026-08-18-final-naming-and-delivery-closure-plan.md)
- [旧系统退役总修改说明](docs/archive/legacy-system/retirement/2026-08-18-legacy-retirement-summary.md)
