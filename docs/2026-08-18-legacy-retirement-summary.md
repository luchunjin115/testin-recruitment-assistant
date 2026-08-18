# 旧系统退役总修改说明

> 日期：2026-08-18
>
> 结论：旧 React + FastAPI + SQLite + Mock LLM 演示系统及其演示数据已经退役；当前仓库只维护 React + FastAPI + PostgreSQL + DeepSeek 新版主链。

## 1. 为什么这样处理

项目早期同时保留旧演示系统和新版系统，导致前端路由、后端模块、数据库、测试和文档长期存在两套含义。用户已经明确决定不要旧代码，也不要迁移旧演示数据，因此本次没有继续做兼容迁移，而是让新版直接成为唯一产品入口，由 Git 历史承担旧实现的追溯职责。

大白话来说：不是把旧房子的家具一件件搬进新房，而是确认新房主结构可用后，把旧房对应的入口、假数据和重复代码清掉，今后只装修新房。

## 2. 退役前后对比

| 项目 | 退役前 | 退役后 |
| --- | --- | --- |
| 前端入口 | 旧页面与施工期新版入口并存 | 只保留 `/app/*` 工作台与 `/apply` 公开页 |
| 后端入口 | 旧 `/api` Router 与新版 `/api/v2` 边界并存 | 业务接口只保留 `/api/v2`，另保留 `/api/health` |
| 数据库 | 旧 SQLite、由旧系统导入的 PostgreSQL 演示数据 | 只使用 PostgreSQL，业务表为空且由 Alembic 管理 |
| 文件 | 旧演示简历附件与新版私有存储并存 | 旧附件删除，只保留 `STORAGE_DIR` 私有存储 |
| AI | 旧 Mock LLM 与新版专用 AI 链路并存 | 简历、Rubric、初筛使用新版可审计链路 |
| 代码命名 | `stage3`、`Stage3*`、`rebuilt`、`V2_STORAGE_DIR` | `features/recruitment`、`Recruitment*`、正式后端 package、`STORAGE_DIR` |
| 演示数据 | 启动/重置脚本可以自动造旧数据 | 不自动 seed，空数据是正常初始状态 |
| 交付文档 | README、使用说明、HANDOFF、TODO 同时描述不同年代 | README、使用说明、项目状态、实施计划和阶段设计各司其职 |

## 3. 分步完成内容

### 第 1 步：先确定退役规则

- 新增旧系统退役决策文档。
- 明确“不维护、不迁移、不兼容旧演示数据”。
- 同步总体设计、路线图、阶段 7 设计、实施计划和项目状态，先改变合同再改代码。

这一步解决的是“到底删什么、保留什么”的问题，避免把新版中仍有职责的代码误当旧代码删除。

### 第 2 步：把运行入口切到新版

- 前端入口停止加载旧 Layout、旧页面和旧预览路由。
- FastAPI 停止挂载旧 Router、停止连接旧 SQLite、停止启动时自动造数据。
- 取消旧 `/uploads` 静态公开入口。
- Docker、Vite、Nginx 和本地启动方式统一指向新版主链。

这一步以后，正常启动和生产构建已经不会再运行旧系统，但旧文件和旧数据当时仍保留，便于后续逐项核对。

### 第 3 步：收紧 Schema 并清理旧数据

- 删除 Application 的 `legacy_migration` 来源、`legacy_stage` 字段和无 Resume 兼容例外。
- 新增 Alembic revision `f8c2d0e5b317`，把最终约束落实到 PostgreSQL。
- 永久删除两个被 Git 忽略的 SQLite 文件和 21 份旧演示附件，共 23 个文件。
- 重建唯一的 `recruitment_assistant` 开发数据库，并从空库完整升级到 `f8c2d0e5b317`。
- 清除旧 PostgreSQL 演示记录，包括 30 个 Candidate、30 条 Education、30 条 WorkExperience、8 个 Job、29 条旧 ScreeningResult 和 8 个随阶段 7 建立的 Rubric。
- 保留 Redis、Chroma 的数据卷、空的新版存储、Git 历史和 `sample_data/` 中 4 个受控 Prompt/测试样例。

被 Git 忽略的 23 个旧数据文件已经不可通过当前仓库恢复，这是用户明确放弃旧演示数据后的预期结果。

### 第 4 步：删除旧代码

- 先建立精确删除清单，再物理删除 70 个旧文件。
- 其中包括旧后端 Router、同步 Model/Schema/Service、Mock LLM、自动造数与旧导入工具、旧前端页面和只描述旧 Prompt 系统的文档。
- 移除只由旧前端直接使用的 `dayjs` 和 `recharts` 声明，并更新 lockfile。
- 新增防回流测试，固定旧文件、旧 Router、旧上传入口和旧前端页面不得重新出现。

这里删除的是已经不在新版调用链中的旁路，不是把同名业务能力一并删除。文件解析、身份解析、岗位、候选人和评分等仍由新版实现继续承担。

### 第 5A—5C 步：去掉施工期命名

- 前端 40 个文件从 `frontend/src/stage3/` 移到 `frontend/src/features/recruitment/`。
- 10 个页面/Layout 等符号从 `Stage3*` 改为 `Recruitment*`。
- 浏览器工作台改为 `/app/*`，公开页面直接使用 `/apply`，不保留 `/stage3/*` 兼容路由。
- 9 个阶段命名测试脚本改为招聘业务命名；CSS 中 1446 处施工期前缀同步收口。
- 后端 63 个源码文件和 55 个测试文件，共 118 个文件移出 10 个 `rebuilt/` 目录。
- 129 个 Python 文件的 import 路径更新到正式 package。
- `V2_STORAGE_DIR` 改为 `STORAGE_DIR`，无调用者的 `UPLOAD_DIR` 删除。
- `/api/v2` 保留，因为它是正式 API 版本号，不是旧系统名称。

仓库中仍可看到历史 Alembic 文件 `bbd627449743_create_rebuilt_core_tables.py`。migration 是已经执行过的数据库历史，不能为了改名而重写；它不代表运行代码仍有 `rebuilt` 分层。

### 第 5D 步：交付文档收口

- 按当前代码重新编写 `README.md`，说明产品能力、架构、启动、地址、AI 配置、验证和未完成边界。
- 按当前 UI 与 API 重新编写 `使用说明.md`，不再描述旧页面、SQLite、演示 seed 或已经删除的脚本。
- 删除过时的根目录 `HANDOFF.md` 和 `TODO_NEXT.md`；现行交接由 `PROJECT_STATE.md`、实施计划和专项设计承担，历史内容仍可从 Git 查看。
- 修正一键启动脚本的默认浏览器地址，从已失效的施工期岗位页改为 `/app/jobs`。
- 新增本总修改说明，集中记录退役范围、验证结果、数据可恢复边界和简历表达。

## 4. 当前真实调用链

```text
React 页面
  -> /api/v2 FastAPI Router
  -> Pydantic Schema（请求/响应合同）
  -> Application Service（业务规则与事务）
  -> SQLAlchemy Model（数据库映射）
  -> PostgreSQL（正式业务数据）
```

AI 初筛在 Service 中继续经过 Prompt Builder、模型 Adapter、确定性规则和语义评价，再把可审计结果保存到 PostgreSQL。旧 Mock LLM 不再位于这条链路中。

## 5. 验证证据

| 验证项 | 结果 | 能证明什么 |
| --- | --- | --- |
| 后端全量测试 | 595 项通过 | 当前 API、Schema、Service、Model 和退役防回流测试没有因清理被破坏 |
| 前端测试 | 14 个 npm 测试脚本通过 | 当前页面、Service、路由和施工期命名保护符合预期 |
| 前端生产构建 | 3116 个模块转换成功 | TypeScript 与 Vite 能生成当前生产包 |
| OpenAPI | 46 个 path，全部属于 `/api/health` 或 `/api/v2/*` | 旧业务 Router 不再对外暴露 |
| Alembic | `f8c2d0e5b317 (head)`，无 Schema 差异 | 真实 PostgreSQL 结构与当前 Model 一致 |
| 数据状态 | PostgreSQL 12 张业务表 0 行；Redis 0 键；Chroma 0 collection；新版存储 0 文件 | 旧演示运行数据已经清空，没有自动 seed 回流 |
| 启动检查 | `start_project.ps1 -CheckOnly` 通过 | 当前机器具备启动脚本要求的 Docker、Python、Node/npm 和项目文件 |
| 文档/工作树检查 | 当前交付文档链接与命令核对通过，`git diff --check` 通过 | 文档引用存在，修改没有明显空白或补丁格式问题 |

这些验证不能证明生产环境权限、安全加固、真实公网部署、所有浏览器视觉效果或完整招聘闭环已经完成；那些仍属于后续阶段。

## 6. 当前产品边界

已经可用的主要能力是岗位管理、候选人管理、私有简历上传/提取/AI 结构化、Dashboard，以及 Application/Rubric/AI 初筛的后端主链和部分初筛前端。

当前仍未完成：

- 正式公开投递提交；
- Rubric 完整前端编辑和发布；
- 初筛详情、证据、历史与 HR 决策完整前端交互；
- 面试、Offer、录取闭环；
- 登录、角色与权限；
- 综合 Agent、RAG 和生产部署验收。

因此旧系统退役完成，不等于整个产品完成。它代表的是：从现在开始只有一套值得继续开发的新架构。

## 7. 如何写进简历

可以如实表达为：

> 主导招聘系统遗留架构退役，将新旧并行的 React/FastAPI/SQLite 与 React/FastAPI/PostgreSQL 双链路收口为单一 PostgreSQL 主链；分阶段完成入口切换、Schema 约束、旧数据清理、70 个遗留文件删除、前后端正式命名与防回流测试，并以 595 项后端测试、14 组前端测试、生产构建、OpenAPI 和 Alembic 校验保障重构安全。

不要写成“完成生产系统迁移”或“完成全部招聘平台”，因为当前没有生产发布、权限体系和完整投递到录取闭环。

## 8. 面试官可能追问

- 为什么选择直接退役，而不是继续迁移旧数据？
- 如何证明删除的 70 个文件没有被新版依赖？
- 为什么 Alembic 历史文件不能跟着 `rebuilt` 一起改名？
- 为什么 `/api/v2` 要保留，而 `/stage3` 要删除？
- Schema、Service、Model 和 migration 分别负责什么？
- 数据清理前如何确认目标范围，如何避免误删 Docker volume？
- 测试通过能证明什么，又不能证明什么？
- 如果未来要恢复兼容旧数据，会在哪一层增加适配，而不是污染核心合同？

回答这些问题时，应围绕“先定边界、再切入口、再收合同和数据、最后删文件与改名”的顺序说明，而不是只说做了批量重命名。
