# 项目进度状态

> 最新更新：2026-08-18（阶段 7 评分详情、逐项证据与评分历史前端交互已完成；下一小步是强制重跑确认交互，暂不进入 HR 决策）

## 当前总状态：🚧 新版主链建设中，旧版演示系统已完成退役

### 权威依据

- 项目指令：`CLAUDE.md`
- 权威设计文档：`docs/specs/2026-07-15-hr-agent-platform-design.md`
- 阶段 5 后路线基线：`docs/specs/2026-08-14-post-stage5-product-roadmap.md`
- 阶段 7 专项设计与执行计划：`docs/specs/2026-08-17-stage7-application-ai-screening-design.md`
- 旧版系统退役决策：`docs/specs/2026-08-18-legacy-system-retirement-decision.md`
- 实施计划：`docs/implementation-plan.md`
- 历史迁移清单：`docs/migration-inventory.md`（已停止执行，由旧版退役决策替代）
- 阶段 5 历史实现与回归排查资料：`docs/handoff/2026-08-12-stage5-development-handoff.md`（阶段 6 日常开发无需读取）

### 2026-08-18 提交前文档一致性收口（已完成）

- 已把 `CLAUDE.md`、总体设计、阶段 5 后路线、实施计划和阶段 7 专项设计的当前口径统一为：评分详情、逐项证据与评分历史交互已完成，下一小步只做强制重跑确认，暂不进入 HR 决策前端交互。
- 当前唯一主链目录已统一为 `frontend/src/features/recruitment/` 和后端各正式 package，现行工作台路由为 `/app/*`；`stage3/`、`rebuilt/` 和 `/stage3/*` 只可作为历史记录出现，不得再被描述为当前入口。
- 正式开发库已重建为空库并升级到 `f8c2d0e5b317 (head)`；阶段 7 早期小步骤中的“当时未升级”保留为历史验证记录，不代表现状。
- 本次只修正文档当前事实和历史标注，没有修改前端、API、Schema、Service、Model、Alembic 或 PostgreSQL 数据。

### 2026-08-18 旧版退役决策

- 用户明确确认不再保留或维护旧 React + FastAPI + SQLite + Mock LLM 演示代码，也不再保留或迁移旧演示数据。
- 项目方式由“新旧并行、逐步迁移”改为“新版直接替代旧版”；Git 历史负责旧实现追溯，旧系统不再作为运行资产。
- 阶段 7 取消旧 30 条 Candidate、29 条 ScreeningResult 的无损迁移要求；`legacy_migration`、`legacy_stage`、无 Resume 例外和旧结果兼容响应已在第 3A 步移除。
- `frontend/src/stage3/` 和后端 `rebuilt/` 当前是新版主链，不能因名称误删；是否改为最终命名放在业务退役完成后单独处理。
- 第 1 步文档门禁、第 2 步运行入口切换、第 3 步 Schema/数据收口、第 4 步旧文件删除和第 5 步命名/交付收口均已完成；旧 SQLite、旧备份、旧演示附件、PostgreSQL 旧业务数据及 70 个旧代码/工具/说明文件已清理。新版数据库为空且位于 `f8c2d0e5b317`，旧系统不再是后续开发事项。

### 2026-08-18 旧版退役第 5A 步：最终命名与交付盘点（已完成）

- 已新增 `docs/specs/2026-08-18-final-naming-and-delivery-closure-plan.md`，只读核对 `stage3`、`rebuilt`、`/api/v2`、`V2_STORAGE_DIR`、四份根目录交付文档和启动脚本，没有移动运行代码或改变路由。
- 推荐把浏览器工作台 `/stage3/*` 改为 `/app/*`、公开投递直接使用 `/apply`，把 `frontend/src/stage3/` 改为 `frontend/src/features/recruitment/` 并移除 `Stage3*` 组件前缀。
- 推荐把后端各层 `rebuilt/` 内容移到对应父 package，并把 `V2_STORAGE_DIR` 改为 `STORAGE_DIR`；正式版本化业务接口 `/api/v2` 与 `v2Http` 继续保留。
- README、使用说明、HANDOFF、TODO 共 2391 行，仍包含已删除旧路径和演示数据脚本；推荐在命名完成后重写 README/使用说明并删除旧 HANDOFF/TODO，启动脚本本身继续保留。
- 下一小步是等待用户确认上述命名，再单独执行第 5B 步前端最终命名；本步未修改数据库、业务数据、API 合同、Schema、Service、Model 或现有测试。

### 2026-08-18 旧版退役第 5B 步：前端最终命名（已完成）

- `frontend/src/stage3/` 的 40 个文件已整体移动到 `frontend/src/features/recruitment/`；10 个页面/Layout 文件、组件符号、相关 TypeScript 类型和 Service 方法从 `Stage3*` 统一改为 `Recruitment*`。
- 浏览器内部 HR 工作台从 `/stage3/*` 改为 `/app/*`，公开投递页 `/apply` 直接加载投递表单；不保留 `/stage3/*` 兼容入口，根路径和未知路径统一进入 `/app/dashboard`。
- 9 个阶段命名测试文件及 npm scripts 已改为 `recruitment-*`；样式中 1446 处 `s3-`/`--s3` 前缀改为 `recruitment-`/`--recruitment`，运行源码中 `stage3`、`Stage3`、`s3-` 扫描结果均为 0。
- `frontend/tests/new-runtime-entry.test.mjs` 新增物理目录和路由防回流保护：`frontend/src/stage3/` 必须不存在，`App.tsx` 不得重新包含 `/stage3`，并验证 `/app` 与直接 `/apply` 入口。
- 验证结果：前端 14 个测试脚本全部通过；`tsc && vite build` 成功转换 3116 个模块。首次测试准确发现移动目录后 9 个 Service 到公共 `services/http.ts` 的相对路径少一级，修正后从头全量重跑通过。
- 本步只改变前端文件/import/符号/CSS 类名和浏览器 URL，不修改 `/api/v2` 请求、后端 API、Schema、Service、Model、Alembic 或 PostgreSQL 数据。下一小步是第 5C 步后端最终命名，必须单独移动并做后端全量回归。

### 2026-08-18 旧版退役第 5C 步：后端最终命名（已完成）

- 已移除 `backend/app/` 下 Adapter、Model、Prompt、Schema、Service 的 5 个 `rebuilt/` 目录，以及 `backend/tests/` 下 Adapter、API、Model、Schema、Service 的 5 个对应测试目录。
- 63 个正式源码文件与 55 个测试文件共 118 个文件已移动到对应父 package；129 个 Python 文件的 `app.*.rebuilt`、`tests.*.rebuilt` import 完成更新，正式 package 的 `__init__.py` 导出已经合并。
- `app/main.py` 已使用正式 Router 模块名，不再保留 `rebuilt_*` 临时别名；`V2_STORAGE_DIR` 已在 `.env.example`、Docker Compose、Settings、Resume API 和 lifespan 测试中统一改为 `STORAGE_DIR`。扫描确认无运行调用者的旧 `UPLOAD_DIR` 也已删除。
- `/api/v2` 作为正式版本化业务接口继续保留；PostgreSQL 表名、字段、约束、Alembic revision 和私有文件内部 `v2/resumes` 命名空间没有修改。
- 旧代码防回流测试新增两层语义：10 个 `rebuilt/` 目录不得重新出现；7 个与旧文件同名但被新版复用的最终路径必须包含 PostgreSQL Base、Pydantic v2 `ConfigDict` 或异步 `AsyncSession` 标记，而不能再用“文件必须不存在”判断。
- 验证结果：后端全量 595 项测试通过；OpenAPI 共 46 个 path，全部只属于 `/api/health` 或 `/api/v2/*`；`alembic current` 为 `f8c2d0e5b317 (head)`，`alembic check` 无结构差异。
- 数据边界复核：PostgreSQL 12 张业务表全部 0 行，Redis 0 个键、Chroma 0 个 collection、`backend/storage` 0 个文件，`sample_data/` 4 个受控样例保留。本步未改变数据库和业务数据。
- 本步完成 `API -> Schema -> Service -> Model -> PostgreSQL` 中间四层的 Python package 最终命名，但没有改变层间职责或 HTTP 合同。下一小步是第 5D 步重写现行 README/使用说明并处理旧 HANDOFF/TODO。

### 2026-08-18 旧版退役第 5D 步：交付文档收口（已完成）

- 已从当前代码重新编写根目录 `README.md` 和 `使用说明.md`：启动入口、页面地址、真实能力、AI 配置、空数据状态、当前工作流和未完成边界均以新版为准，不再把旧 SQLite、演示 seed、旧页面或已删除脚本写成现行功能。
- 已删除过时的 `HANDOFF.md` 和 `TODO_NEXT.md`；现行交接继续由本文件、`docs/implementation-plan.md` 与阶段专项设计承担，历史内容仍可通过 Git 追溯。
- `scripts/start_project.ps1` 默认打开地址已从失效的施工期岗位页改为 `http://localhost:5173/app/jobs`；`/api/v2` 作为正式版本化 API 保留。
- 新增 `docs/2026-08-18-legacy-retirement-summary.md`，集中记录五步退役范围、70 个旧文件与 23 个旧数据文件的处理、前后端最终命名、验证证据、不可恢复边界和简历/面试表达。
- 第 5D 步只修改交付材料和启动脚本默认页面，没有新增业务功能、修改 API/Schema/Service/Model、执行 migration、写入业务数据或删除 Docker volume。
- 启动环境检查、当前交付文档路径/链接与遗留引用扫描、Docker Compose 解析和 `git diff --check` 均通过；前端 14 个测试脚本已按 README 中的命令重新全量执行并通过。整次退役同时使用后端 595 项、3116 模块生产构建、OpenAPI 46 个 path 与 Alembic `f8c2d0e5b317` 的既有全量验证基线。
- 旧系统退役至此全部完成。下一小步回到阶段 7，只接入评分详情、逐项证据与历史交互，不提前扩展公开投递、权限、面试、Agent 或 RAG。

### 2026-08-18 旧版退役第 3A 步：Schema 合同收口（已完成）

- Application 的 `source` 只保留 `hr_direct`、`hr_screening`、`public_apply`；`current_resume_id` 在前端类型、Pydantic Schema、SQLAlchemy Model 和尚未部署的阶段 7 Alembic migration 中统一改为必填，`legacy_stage` 及旧 Resume 例外已删除。
- ScreeningResult 现在必须同时关联 Application 与 Resume。`GET /api/v2/screening-results` 和详情接口只返回阶段 7 Application 筛选结果；旧通用 `ScreeningResultCreate/Update/Read`、Service 增删改能力及 `POST/PUT/DELETE /api/v2/screening-results` 已移除。正式结果仍只能由 Application 筛选流程产生并作为审计历史保留。
- Rubric 和 StageHistory 中仅服务于旧数据迁移的枚举及数据库允许值已移除；新版前端映射、Dashboard、报告中心和初筛中心统一消费 Application ScreeningResult 合同，不再兼容无 Application 的结果。
- 本步没有执行 Alembic 升级、没有清空开发数据库、没有删除附件，也没有删除旧文件。第 3B-1 步随后确认实际 PostgreSQL 已执行到 `e7b1c9d4a206`，因此保留 `e7` 为不可改写历史，并新增待部署的 `f8c2d0e5b317` 收口 migration；现有旧数据会在第 3B-2 步按精确目标单独处理。
- 验证结果：直接相关的 32 项后端测试通过；后端全量 599 项测试通过；前端全部 14 个测试脚本通过；`tsc && vite build` 成功转换 3116 个模块；新版运行代码和待部署 `f8` 中没有 legacy 合同，已执行的 `e7` 只保留历史建库职责，负向 Schema 测试仍明确验证旧 source/字段会被拒绝。
- 本步位于 `前端类型/映射 -> FastAPI 只读结果 API -> Pydantic Schema -> Service 查询边界 -> SQLAlchemy Model -> 待部署 f8 PostgreSQL migration`。它证明代码合同不再接受或暴露 legacy 数据，但不能证明既存数据库和附件已经清理、Alembic 能在空库完整升级或真实 PostgreSQL 主链已经通过；这些属于第 3B-2 步及其后续验证。

### 2026-08-18 旧版退役第 3B-1 步：旧数据只读盘点（已完成）

- 实际 PostgreSQL 数据库为 `recruitment_assistant`，Alembic revision 是已部署的 `e7b1c9d4a206`，不是旧文档所写的“尚未进入阶段 7”。现有表结构仍允许 `legacy_migration`、`legacy_stage` 和空 Application/Resume 关联，因此不能改写 `e7`；已新增后续 `f8c2d0e5b317` migration，只有旧行清理后才允许升级，并用前置检查阻止带 legacy 行误升级。
- PostgreSQL 当前只有旧演示业务数据：Candidate 30 行（ID 1-30）、Education 30 行（ID 1-30）、WorkExperience 30 行（ID 1-30）、Job 8 行（ID 1-8）、ScreeningResult 29 行（ID 1-29，全部 `application_id` 与 `resume_id` 为空）、随 `e7` 生成的 JobScreeningRubric 8 行（ID 1-8）。Application、Resume、ProjectExperience、Report、StageHistory、ActivityLog 均为 0 行。
- 旧 SQLite `backend/recruit.db` 为 155,648 字节，包含 Candidate 30 行、Job 8 行、ActivityLog 77 行、StageChangeLog 26 行；`backend/data/recovery-backups/recruit-before-first-start-20260804-095513.db` 为 139,264 字节。两者均被 `.gitignore` 忽略，不可通过当前 Git 工作树恢复。
- `backend/uploads/` 下共有 21 个 `demo_resume_*` TXT 文件，总计 9,128 字节，恰好对应 SQLite Candidate 1-21 的旧绝对路径记录；这些文件被 `.gitignore` 忽略。新版 `backend/storage` 当前为 0 个文件，Docker 中也未创建 `resume-data` volume。
- Redis 当前为 0 个键，Chroma 当前为 0 个 collection；两者无需数据清理。受版本控制的 `sample_data/` 共 4 个文件、5,112 字节，仍被 Prompt 效果验证和演示文档引用，属于受控测试样例而不是运行时旧数据库，本轮保留。
- 第 3B-2 步建议精确执行：删除两个忽略的 SQLite 文件和 21 个旧上传附件；重建 PostgreSQL 中唯一的 `recruitment_assistant` 数据库并升级到 `f8c2d0e5b317`，以同时清除上述旧行、重置序列并完成真实空库 Alembic 验证。保留 Redis/Chroma volume、受控 `sample_data/`、空的新版私有存储和 Git 历史。
- 本步只有只读 SQL、SQLite `mode=ro`、文件枚举和 Docker 状态查询；没有执行 DELETE、TRUNCATE、DROP、Alembic upgrade、文件删除、容器停止或 volume 删除。

### 2026-08-18 旧版退役第 3B-2 步：旧数据清理与空库迁移（已完成）

- 删除前再次确认 PostgreSQL 仍位于 `e7b1c9d4a206`，Candidate 30 行、ScreeningResult 29 行、Application/Resume 0 行；两个 SQLite 文件和 21 份附件的数量、大小与盘点完全一致，且 `backend/uploads/` 没有混入非 `demo_resume_*.txt` 文件，backend 容器未运行。
- 已永久删除被 Git 忽略的 `backend/recruit.db`、`backend/data/recovery-backups/recruit-before-first-start-20260804-095513.db` 和 `backend/uploads/` 下全部 21 份旧演示附件，共 23 个文件。`backend/uploads/` 与 recovery-backups 目录保留为空，等待第 4 步随旧代码边界统一判断；这些数据不能通过 Git 恢复。
- 已只删除并重建 PostgreSQL 中唯一的 `recruitment_assistant` 业务数据库，没有删除 PostgreSQL 容器或 `postgres-data` volume；随后从真正空库依次执行全部 Alembic migration，并成功从基础 revision 经 `e7b1c9d4a206` 升级到 `f8c2d0e5b317`。
- 迁移后全部 12 张业务表均为 0 行，没有自动生成 seed 或演示数据；`applications.current_resume_id`、`screening_results.application_id`、`screening_results.resume_id` 均为数据库级 NOT NULL，`legacy_stage` 列不存在，Application/Rubric/StageHistory 的允许值中不再包含 legacy 或 migration 专用入口。
- `sample_data/` 的 4 个受控测试文件、空的新版 `backend/storage`、Redis/Chroma 数据卷和 Git 历史均按计划保留；Redis 仍为 0 个键，Chroma 仍为 0 个 collection，本步没有删除任何 Docker volume。
- 验证结果：`alembic current` 为 `f8c2d0e5b317 (head)`；`alembic check` 返回 `No new upgrade operations detected`，证明当前 SQLAlchemy Model 与真实 PostgreSQL Schema 一致；后端全量 600 项测试通过；`git diff --check` 通过。前端代码在本步未修改，继续沿用第 3A 步已经通过的 14 个脚本和 3116 模块生产构建结果。
- 本步位于 `旧运行数据 -> PostgreSQL 空库 -> Alembic 全历史 -> f8 最终约束 -> Model/Schema/API`。它证明旧演示数据已从当前运行环境清除、空库可完整升级且最终结构与代码一致；它不包含旧 Router、Model、Service、脚本、历史文档等代码文件删除，这属于第 4 步。

### 2026-08-18 旧版退役第 4A 步：旧代码只读引用扫描（已完成）

- 已从唯一前端入口 `App.tsx`、唯一后端入口 `app/main.py`、当前启动脚本和全量测试反向扫描调用链，确认旧前端与旧后端形成自包含旧系统簇，新版主链没有导入它们。
- 已形成 `docs/specs/2026-08-18-legacy-code-deletion-inventory.md`：第 4B 步待删除 70 个文件，其中旧后端运行模块 36 个、旧脚本/测试 7 个、旧前端 22 个、只描述旧 Prompt 系统的说明 5 个。
- 新版替代关系已经核对：旧 `file_parser.py` 由新版 TXT/PDF/DOCX extractor 与私有存储链替代；旧 `dedup_service.py` 由 Application intake 的身份解析与冲突语义替代；旧 `ai_service.py`、`mock_llm.py`、`screening.txt` 由新版 Rubric、输入快照、真实模型适配器和评分 Service 替代；一次性旧候选人导入在旧数据放弃后没有职责。
- `scripts/start_project.ps1`、三个 `launch/*.bat`、新版 live validation、`sample_data/`、全部 migration 和 `rebuilt` 主链均有当前职责，明确保留。父 package `models/__init__.py`、`schemas/__init__.py`、`services/__init__.py` 也必须保留，不能随旧同级文件误删。
- 本步只新增删除清单和更新状态文档，没有删除或修改运行代码、数据库、附件、Docker volume 或测试；下一小步是按清单执行第 4B 步，并同步移除旧前端专属依赖和增加“旧文件不得重新出现”的回归测试。

### 2026-08-18 旧版退役第 4B 步：旧代码物理删除（已完成）

- 已严格按 `docs/specs/2026-08-18-legacy-code-deletion-inventory.md` 删除全部 70 个目标：旧后端运行模块 36 个、旧脚本/测试 7 个、旧前端 22 个、旧 Prompt 说明 5 个；旧空目录和遗留 Python 字节码缓存也已清理，新版主链和 Git 历史保留。
- 已从前端直接依赖中移除仅由旧页面使用的 `dayjs` 和 `recharts` 并更新 lockfile；`dayjs` 仍可作为 Ant Design 的传递依赖存在，但不再是本项目直接声明。`.gitignore` 已移除只服务于旧 backend uploads/recovery data 的规则，继续保留新版 `backend/storage/` 和通用本地产物规则。
- 新增 `backend/tests/test_legacy_code_retirement.py`，固定 48 个旧后端、工具和 Prompt 路径不得重新出现；扩展 `frontend/tests/new-runtime-entry.test.mjs`，固定 22 个旧前端路径不得重新出现，并继续验证入口、Vite 和 Nginx 不暴露旧路由/上传目录。
- 验证结果：后端全量 593 项测试通过；前端 14 个测试脚本全部通过；`tsc && vite build` 成功转换 3116 个模块；OpenAPI 共 46 个 path，全部仅位于 `/api/health` 或 `/api/v2/*`；`alembic current` 为 `f8c2d0e5b317 (head)`，`alembic check` 无新结构差异。
- 数据边界复核：PostgreSQL 12 张业务表全部 0 行，Redis 0 个键、Chroma 0 个 collection、`backend/storage` 0 个文件；`sample_data/` 的 4 个受控样例保留。本步未删除数据库、Docker volume、新版存储或受控样例。
- 本步位于 `前端入口/API 调用 -> FastAPI API -> 新版 Schema -> 新版 Service -> rebuilt Model -> PostgreSQL` 整条链路之外的遗留旁路清理；全量验证证明主链不依赖已删文件，但不等同于已经完成第 5 步 `/stage3`、`rebuilt`、`/api/v2` 命名决策和最终 README/使用说明改写。

### 2026-08-18 旧版退役第 2 步：运行入口切换（已完成）

- 前端 `App.tsx` 已停止导入旧 `AppLayout`、旧 `pages/` 页面和 `/stage3-preview`；根路径及未知路径进入 `/stage3/dashboard`，旧 `/apply` 只跳转到新版 `/stage3/apply`。旧前端文件仍在工作树中，等待第 4 步删除。
- FastAPI `main.py` 已停止导入和挂载旧 `app.routers`，不再调用 `ensure_demo_data()`，不再公开挂载旧 `/uploads`；健康检查改由新版 `app.api.health` 提供，全部业务 API 只保留在 `/api/v2`。
- `app.models` 父包不再隐式导入旧 SQLite Model，因此导入新版 `app.models.rebuilt` 不会顺带创建旧同步 SQLite engine。旧 Model 文件尚未删除。
- 本地 `backend/run.py`、`.env.example`、Docker Compose 和 Dockerfile 已切到新版 `core.config`、PostgreSQL 与私有 `V2_STORAGE_DIR`；Vite 和 Nginx 已停止代理旧 `/uploads`。Compose 不再挂载旧 SQLite data volume 或旧上传目录，但本步没有删除宿主机文件或既存 Docker volume。
- 新增前端运行入口回归测试，固定“入口不得导入旧页面、旧投递地址只跳转新版、开发与容器代理不得公开旧上传目录”。
- 验证结果：后端全量 610 项测试通过；独立进程导入 FastAPI 后共有 73 个 `/api` 路由项，只有 `/api/health` 与 `/api/v2/*`，旧 Router、旧配置、旧 SQLite Model 均未加载；健康检查返回 200，旧 `/api/jobs` 与 `/uploads/*` 返回 404。
- 前端新增入口测试及既有 13 组回归测试全部通过；`tsc && vite build` 成功转换 3116 个模块，旧页面不再进入生产构建。Docker Compose 解析检查确认使用 PostgreSQL 与私有 `resume-data`，不再包含 SQLite、`recruit-data` 或 `/app/uploads`。
- 本步位于 `前端入口 -> FastAPI 路由入口 -> 新版 API/Service/Model -> PostgreSQL 配置`。它证明正常启动与生产构建不再加载旧系统，但不能证明 legacy Schema 已移除、旧演示数据已清理、Docker 镜像已真实重建运行或浏览器跳转视觉效果；这些属于后续小步骤。

### 阶段 0 已完成事项

- 已确认 `CLAUDE.md` 指向的权威设计文档存在。
- 已扫描当前项目结构，确认仓库内存在旧版 React + FastAPI + SQLite/Mock LLM 演示系统。
- 已识别可迁移资产：Prompt 模板、`file_parser.py`、`dedup_service.py`、候选人投递页、Mock 评分规则。
- 已识别需重写模块：`ai_service.py`、`mock_llm.py`、旧前端页面、旧 SQLite 模型、旧 API 分层。
- 已新增完整实施计划文档，后续按阶段推进。
- 已新增迁移清单文档，避免后续误删或盲目搬迁旧代码。

### 阶段 1 已完成事项

- 已更新后端依赖清单，加入新架构需要的 `asyncpg`、`alembic`、`redis`、`chromadb`、`langgraph`、`langchain-openai`。
- 已扩展 `.env.example`，补充 PostgreSQL、Redis、Chroma 配置项。
- 已新增后端新架构目录骨架：
  - `backend/app/api/`
  - `backend/app/core/`
  - `backend/app/agents/graphs/`
  - `backend/app/agents/nodes/`
  - `backend/app/agents/states/`
  - `backend/app/agents/prompts/`
  - `backend/app/rag/`
- 已新增基础设施模块：
  - `backend/app/core/config.py`
  - `backend/app/core/database.py`
  - `backend/app/core/redis.py`
  - `backend/app/core/llm.py`
  - `backend/app/rag/vector_store.py`
- 已新增 Alembic 骨架：`backend/alembic.ini`、`backend/migrations/`。
- 已更新 `docker-compose.yml`，加入 PostgreSQL 16、Redis 7、Chroma 服务。当前后端容器仍默认使用旧 SQLite 演示库，避免旧启动脚本被 PostgreSQL 迁移打断；新 `core/database.py` 已按 PostgreSQL 准备。
- 已新增前端基础目录入口：
  - `frontend/src/services/http.ts`
  - `frontend/src/theme/index.ts`
  - `frontend/src/stores/index.ts`
  - `frontend/src/hooks/index.ts`
- 已将 Ant Design 主题抽到 `frontend/src/theme/index.ts`。
- 已将前端 API 底层 axios 实例抽到 `frontend/src/services/http.ts`。

### 阶段 1 验证结果

- 前端构建通过：`npm.cmd run build`
- 新增后端骨架 Python 语法检查通过：`python -m compileall backend\app\core backend\app\api backend\app\agents backend\app\rag backend\migrations`

### 阶段 1 仍需完成

阶段 1 的第一批地基已经完成，但还没有把旧业务入口正式切到新架构。

剩余任务：

1. 根据阶段 2 的数据模型设计，补齐新 SQLAlchemy models。
2. 生成第一版 Alembic migration。
3. 在安全时机把 FastAPI 入口从旧 `routers/` 逐步迁移到新 `api/`。
4. 根据新页面规划继续整理前端页面目录。
5. 等新模型和迁移稳定后，再决定是否让 Docker 后端直接使用 PostgreSQL。

### 下一步：阶段 2 数据库模型和核心业务对象

阶段 2 的目标是把候选人、岗位、简历、筛选结果、报告等核心业务对象落成 PostgreSQL 模型。

### 阶段 2 当前进度

- 已开始第一批新版模型，暂放在 `backend/app/models/rebuilt/`，避免破坏旧 SQLite 演示系统。
- 已新增：
  - `backend/app/models/rebuilt/job.py`
  - `backend/app/models/rebuilt/candidate.py`
  - `backend/app/models/rebuilt/resume.py`
- 已新增第二批候选人画像模型：
  - `backend/app/models/rebuilt/education.py`
  - `backend/app/models/rebuilt/work_experience.py`
  - `backend/app/models/rebuilt/project_experience.py`
- 已在新版 `Candidate` 模型中建立教育经历、工作经历、项目经历关系。
- 已新增 AI 初筛结果模型：
  - `backend/app/models/rebuilt/screening_result.py`
- 已建立 `Candidate`、`Job` 与 `ScreeningResult` 的关系。
- 已新增初筛报告模型：
  - `backend/app/models/rebuilt/report.py`
- 已建立 `Candidate`、`Job`、`ScreeningResult` 与 `Report` 的关系。
- 已新增通用操作日志模型：
  - `backend/app/models/rebuilt/activity_log.py`
- 新版 `ActivityLog` 使用 `target_type + target_id` 标识候选人、岗位、报告等不同业务对象，并使用 JSONB 保存操作详情，不再只绑定候选人表。
- 阶段 2 规划的 9 类核心表模型已全部建立。
- 已安装 Python 3.11.9，并在项目根目录创建 `.venv` 作为后端开发虚拟环境。
- 已将后端依赖安装到 `.venv`，包括 `asyncpg`、`alembic`、`langgraph`、`chromadb` 等新架构依赖。
- 已将 `backend/app/core/database.py` 改为懒加载数据库 engine，避免仅导入模型时就要求数据库驱动或连接可用。
- 第一批模型语法检查通过：`python -m compileall backend\app\models\rebuilt`
- 第二批模型语法检查通过：`python -m compileall backend\app\models\rebuilt`
- 初筛结果模型语法检查通过：`python -m compileall backend\app\models\rebuilt`
- 初筛报告模型和全部 rebuilt 模型导入检查通过：`from app.models.rebuilt import ...`
- 操作日志模型语法、导入、SQLAlchemy mapper 和表元数据检查通过。
- Alembic 环境已显式加载 `app.models.rebuilt`，`Base.metadata` 能够识别阶段 2 的 9 张新版数据表。
- 已开始编写新版 Pydantic v2 schemas，并暂放在 `backend/app/schemas/rebuilt/`，避免影响旧版 API 使用的 schemas。
- 已完成第一组岗位 schemas：`JobCreate`、`JobUpdate`、`JobRead`；创建校验、局部更新和 SQLAlchemy ORM 对象转换检查通过。
- 已完成候选人及三类经历 schemas：Candidate、Education、WorkExperience、ProjectExperience 均提供 Create、Update、Read 类型。
- `CandidateCreate` 支持嵌套教育、工作和项目经历；`CandidateRead` 的 SQLAlchemy ORM 嵌套转换检查通过。
- 已完成 Resume、ScreeningResult、Report 的 Create、Update、Read schemas。
- 已完成追加式 ActivityLog 的 Create、Read schemas；操作日志不提供 Update，避免审计历史被普通更新接口改写。
- 9 类核心模型对应的新版 Pydantic schemas 已全部建立；请求校验、非法值拦截、局部更新、ORM 转换和统一导出检查通过。
- Alembic、应用配置与 Docker Compose 的数据库目标已核对一致，均指向本机 `localhost:5432/recruitment_assistant` PostgreSQL 数据库。
- 已安装并启动 Docker Desktop 4.82.0、Docker Engine 29.6.1 和 WSL 2.7.10；本地 PostgreSQL 16 容器运行健康。
- 后端依赖已改为 `sqlalchemy[asyncio]==2.0.35`，并在 `.venv` 中安装 greenlet 3.5.3，解决 Alembic 异步连接缺少 greenlet 的问题。
- 已为岗位、候选人、教育经历、简历和报告等非空业务字段补充 PostgreSQL `server_default`，同时保留 ORM `default`。
- Alembic revision `bbd627449743_create_rebuilt_core_tables.py` 已生成，包含 9 张业务表、34 组索引、11 个 JSONB 字段、11 个外键和 1 个唯一约束。
- migration 建表/回滚顺序、PostgreSQL dialect 导入、业务默认值、Python 语法和离线 SQL 编译检查通过。
- 已完成 `alembic upgrade head -> downgrade base -> upgrade head` 往返测试：第一次建表后 9 张业务表及 34 个索引、11 个外键、11 个 JSONB 字段、1 个唯一约束均存在；回滚后 9 张业务表全部删除；再次升级后结构完整恢复。
- PostgreSQL 当前停留在 Alembic revision `bbd627449743`，9 张业务表已经真实创建，数据库端默认值检查通过。
- 当前策略：旧 `backend/app/models/*.py` 暂时保留，等新主链路跑通后再进入旧系统清理阶段。
- 已新增新版异步岗位 CRUD Service：`backend/app/services/rebuilt/job_service.py`，与旧版同步 `backend/app/services/job_service.py` 隔离，未修改旧业务代码。
- 新版 `JobService` 已提供创建、按 ID 查询、列表查询、局部更新和删除 5 个基础方法；写操作失败时会回滚数据库事务。
- 已新增 8 个 `unittest` 单元测试，覆盖 Job 基础 CRUD、记录不存在和写入失败回滚；测试结果为 8 项全部通过。
- 已使用当前 PostgreSQL 完成 Job Service 真实往返验证：创建 -> 按 ID 查询 -> 列表查询 -> 更新 -> 删除 -> 确认不存在，输出 `POSTGRES_JOB_CRUD_OK`，临时验证数据已清理。
- 已新增隔离的新版 Job API 文件：`backend/app/api/jobs.py`，实现 `POST /jobs`、`GET /jobs`、`GET /jobs/{job_id}`、`PUT /jobs/{job_id}` 和 `DELETE /jobs/{job_id}` 完整基础 CRUD。
- 新版 Job API 使用 `JobCreate`、`JobUpdate` 校验请求，使用 `JobRead` 约束响应；岗位不存在时统一返回 `404`，删除成功返回无正文的 `204`。
- 新版 Job CRUD API 的语法、导入和路由结构检查通过，5 个请求方法与路径均已正确登记。
- 新版 Job API 最初保持隔离，完成兼容性核对后已按 `/api/v2/jobs` 正式挂载；旧版 `/api/jobs` 继续保留，避免影响旧前端。
- 已为新版 Job CRUD 增加隔离的 API 自动化测试：使用临时 FastAPI 应用、依赖覆盖和 Mock Service，不连接真实数据库。
- Job API 测试覆盖创建成功与非法标题、列表与空列表、详情成功与 `404`、更新成功/非法标题/`404`、删除成功与 `404`；11 项测试全部通过。
- 当前新版后端测试共 19 项全部通过：Job Service 8 项、Job CRUD API 11 项。
- 已使用临时 FastAPI 应用连接真实 PostgreSQL，完成 Job API 创建、列表、详情、更新、删除和删除后 `404` 的全链路往返验证，输出 `POSTGRES_JOB_API_CRUD_OK`，临时数据已清理。
- 首次集成验证因 Docker Engine 和 PostgreSQL 容器未运行而连接失败；启动项目 PostgreSQL 容器后重试通过。中间一次中文值断言失败定位为 PowerShell 管道编码问题，并非业务或数据库错误，改用无编码歧义的测试值后严格断言通过。
- 已核对旧前端仍依赖旧版 `GET /api/jobs/active`、`PATCH /api/jobs/{id}/status` 和旧删除响应，直接替换 `/api/jobs` 会破坏旧演示系统。
- 已采用版本化 API 安全迁移方案：旧版岗位 API 继续保留在 `/api/jobs`，新版 Job CRUD API 已在当前 `backend/app/main.py` 正式挂载为 `/api/v2/jobs`。
- 正式入口的 5 个新版 Job 路由均只登记一次，旧版岗位路由仍存在，OpenAPI 生成、Python 编译和全部 19 项回归测试通过。
- 已直接请求正式 `app.main:app` 的 `/api/v2/jobs` 并连接真实 PostgreSQL，再次完成完整 CRUD 往返，输出 `MOUNTED_POSTGRES_JOB_API_CRUD_OK`，临时数据已清理。
- 已新增新版异步 Candidate CRUD Service：`backend/app/services/rebuilt/candidate_service.py`，并通过 `backend/app/services/rebuilt/__init__.py` 统一导出；旧版候选人 Service 和 API 未修改。
- 新版 `CandidateService` 已提供创建、按 ID 查询、列表查询、局部更新和删除 5 个基础方法；创建时可在同一事务内保存教育、工作和项目经历，写操作失败时会回滚。
- Candidate 详情和列表查询使用 `selectinload` 预加载三类经历，返回 Candidate 时不依赖后续隐式数据库查询。
- Candidate 与教育、工作、项目经历的 ORM 关系已加入 `all, delete-orphan` 级联；删除 Candidate 时会同步删除三类直属经历，避免孤立记录。
- 已新增 11 个 Candidate Service 隔离测试，覆盖嵌套创建、空经历创建、详情、列表、局部更新、删除、不存在分支、失败回滚和直属经历级联配置；11 项全部通过。
- 当前新版后端回归测试共 30 项全部通过：Job Service 8 项、Job CRUD API 11 项、Candidate Service 11 项。
- 已使用当前 PostgreSQL 完成 Candidate Service 真实往返验证：创建 Candidate 及三类经历 -> 按 ID 查询 -> 列表查询 -> 更新 -> 删除 -> 确认主记录和三类经历均不存在，输出 `POSTGRES_CANDIDATE_SERVICE_CRUD_OK`，临时验证数据已清理。
- 已新增隔离的新版 Candidate API：`backend/app/api/candidates.py`，实现创建、列表、详情、局部更新和删除 5 个基础 CRUD 路由；请求和响应分别使用 `CandidateCreate`、`CandidateUpdate`、`CandidateRead`。
- 新版 Candidate API 创建和读取时支持教育、工作、项目三类嵌套经历；候选人不存在时统一返回 `404`，删除成功返回无正文的 `204`。
- 已新增 12 个 Candidate API 隔离测试，覆盖嵌套创建、空姓名和负年龄校验、列表和空列表、详情、局部更新、删除及各类不存在分支；12 项全部通过。
- 已核对旧前端仍依赖 `/api/candidates` 的招聘阶段、AI 初筛、面试、Offer 和批量操作等旧字段与专用接口，新版基础 CRUD 不能直接替换旧接口。
- 已采用版本化 API 安全迁移方案：旧版 Candidate API 继续保留在 `/api/candidates`，新版 Candidate CRUD API 已在 `backend/app/main.py` 正式挂载为 `/api/v2/candidates`。
- 正式入口的 5 个新版 Candidate 路由均只登记一次，旧版 Candidate 路由仍存在；OpenAPI 生成、Python 编译和当前全部 42 项回归测试通过。
- 已直接请求正式 `app.main:app` 的 `/api/v2/candidates` 并连接真实 PostgreSQL，完成 Candidate 及三类经历的创建、列表、详情、更新、删除和删除后 `404` 全链路往返，输出 `MOUNTED_POSTGRES_CANDIDATE_API_CRUD_OK`；主记录和三类经历临时数据均已清理。
- 正式 API 首次集成验证在中文 `404` 文本断言处受到 PowerShell 管道编码影响，CRUD 请求本身已经执行成功；确认临时记录为 0 后，改用 Unicode 转义进行相同严格断言，完整验证通过。
- 已新增新版异步 Resume CRUD Service：`backend/app/services/rebuilt/resume_service.py`，并通过 `backend/app/services/rebuilt/__init__.py` 统一导出；旧版简历上传与解析业务未修改。
- 新版 `ResumeService` 已提供创建、按 ID 查询、按上传时间倒序列表、局部更新和删除 5 个基础方法；写操作失败时会回滚数据库事务。
- 已新增 8 个 Resume Service 隔离测试，覆盖基础 CRUD、局部更新、不存在分支和失败回滚；8 项全部通过。
- 已新增隔离的新版 Resume API：`backend/app/api/resumes.py`，实现创建、列表、详情、局部更新和删除 5 个基础 CRUD 路由。
- Resume API 使用 `ResumeCreate`、`ResumeUpdate` 校验文件信息、解析状态和 JSONB 解析快照，使用 `ResumeRead` 约束响应；简历不存在时返回 `404`，删除成功返回无正文的 `204`。
- 已新增 14 个 Resume API 隔离测试，覆盖完整 CRUD、空文件名、空文件路径、负文件大小、非法解析状态和不存在分支；14 项全部通过。
- 已核对旧前端继续使用 `/api/resume/upload` 和 `/api/resume/parse-preview`；新版 CRUD 使用复数路径 `/api/v2/resumes`，两者职责和路径均不冲突。
- 新版 Resume CRUD API 已在 `backend/app/main.py` 正式挂载为 `/api/v2/resumes`；5 个新版路由均只登记一次，旧上传和解析预览路由仍存在，OpenAPI、Python 编译和当前全部 64 项回归测试通过。
- 已通过正式 Job、Candidate、Resume API 创建外键完整的临时数据，并连接真实 PostgreSQL 完成 Resume 创建、列表、详情、解析状态与 JSONB 快照更新、删除和删除后 `404` 全链路往返，输出 `MOUNTED_POSTGRES_RESUME_API_CRUD_OK`；临时 Resume、Candidate、Job 均已清理。
- 已新增 Education 独立异步 CRUD Service/API，正式挂载为 `/api/v2/education`；创建时校验 Candidate 存在，列表支持按 `candidate_id` 筛选，单条记录支持查询、局部更新和删除。
- Education 的 18 项隔离测试全部通过；当时全部 82 项回归通过。正式 PostgreSQL 创建、筛选、详情、更新、删除和删除后 `404` 验证输出 `MOUNTED_POSTGRES_EDUCATION_API_CRUD_OK`，临时数据已清理。
- 已新增 WorkExperience 独立异步 CRUD Service/API，正式挂载为 `/api/v2/work-experiences`；支持按候选人筛选，并验证 `tech_stack` JSONB 数组的创建、更新和读取。
- WorkExperience 的 15 项隔离测试全部通过；当时全部 97 项回归通过。正式 PostgreSQL 验证输出 `MOUNTED_POSTGRES_WORK_EXPERIENCE_API_CRUD_OK`，临时数据已清理。
- 已新增 ProjectExperience 独立异步 CRUD Service/API，正式挂载为 `/api/v2/project-experiences`；支持按候选人筛选，并覆盖 `tech_stack` 与 `achievements` 的独立维护。
- ProjectExperience 的 15 项隔离测试全部通过；当时全部 112 项回归通过。正式 PostgreSQL 验证输出 `MOUNTED_POSTGRES_PROJECT_EXPERIENCE_API_CRUD_OK`，临时数据已清理。
- 已新增 ScreeningResult 独立异步 CRUD Service/API，正式挂载为 `/api/v2/screening-results`；创建时校验 Candidate、Job，应用层预检候选人-岗位重复结果，并由 PostgreSQL 唯一约束兜底并发重复，重复创建统一返回 `409`。
- ScreeningResult 的 15 项隔离测试全部通过；当时全部 127 项回归通过。正式 PostgreSQL CRUD、JSONB 更新和重复创建 `409` 验证输出 `MOUNTED_POSTGRES_SCREENING_RESULT_API_CRUD_OK`，临时数据已清理。
- 已新增 Report 独立异步 CRUD Service/API，正式挂载为 `/api/v2/reports`；创建和更换 `screening_id` 时校验 ScreeningResult 与报告的 Candidate、Job 一致，不一致返回 `409`。
- Report 的 16 项隔离测试全部通过；当时全部 143 项回归通过。正式 PostgreSQL CRUD、JSONB 元数据和跨候选人错误关联 `409` 验证输出 `MOUNTED_POSTGRES_REPORT_API_CRUD_OK`，临时数据已清理。
- 已新增追加式 ActivityLog Service/API，正式挂载为 `/api/v2/activity-logs`；仅提供创建、列表和详情，不提供普通更新、删除，列表支持目标类型、目标 ID、动作、用户筛选及 1-500 条限制。
- ActivityLog 的 11 项隔离测试全部通过，包含路由层“不暴露 PUT/DELETE”的结构检查；正式 PostgreSQL 新增、组合筛选、详情和 PUT/DELETE `405` 验证输出 `MOUNTED_POSTGRES_ACTIVITY_LOG_APPEND_READ_OK`，临时验证日志已通过内部数据库会话精确清理。
- 当前新版后端回归测试共 154 项全部通过；正式应用中 43 个 `/api/v2`“HTTP 方法 + 路径”组合均唯一，检查输出 `MOUNTED_V2_METHOD_PATHS_UNIQUE_OK`。
- PostgreSQL 曾因 Docker Desktop 未运行而拒绝连接；后台恢复 Docker Desktop 和项目 PostgreSQL 容器后，同一真实数据库验证通过。Alembic 当前仍为 `bbd627449743 (head)`，本轮只新增 Service/API，不需要新 migration。
- 阶段 2 最低验收标准已经满足：岗位和候选人可创建、查询、更新，数据真实写入 PostgreSQL，Alembic 可正常建表和回滚。
- 阶段 2 完整任务清单已经收口：Job、Candidate、Resume、Education、WorkExperience、ProjectExperience、ScreeningResult、Report 均有独立基础 CRUD Service/API；ActivityLog 按审计设计提供只新增/查询 Service/API。
- 三类经历既支持随 Candidate 嵌套创建、查询和级联删除，也支持单条独立新增、筛选、修改和删除。

### 阶段 3 视觉样板进度

- 已新增隔离的新版 Dashboard 视觉样板：`frontend/src/pages/Stage3Preview.tsx` 与 `Stage3Preview.css`。
- 样板路由为 `/stage3-preview`，不替换旧版首页、Dashboard、候选人或岗位页面。
- 当前风格采用简约专业方向：浅灰背景、白色内容面、低饱和蓝色强调、弱边框、少阴影、清晰留白和克制的状态色。
- 样板已覆盖新版侧边栏、顶部搜索、今日概览、统计卡片、候选人列表、今日待办和 AI 助手入口，并加入桌面端与窄屏响应式布局。
- 前端生产构建已通过；现有旧项目仍有 JavaScript bundle 大于 500 kB 的 Vite 警告，后续阶段可通过页面级懒加载拆包优化，不影响本次样板运行。
- 当前页面使用演示数据，只用于确认阶段 3 的视觉方向；尚未接入 `/api/v2`，也不代表阶段 3 全部页面已经完成。

### 阶段 3 第一小步进度

- 已新增隔离的新版入口 `/stage3/dashboard`，旧版 `/`、`/dashboard`、旧公共布局和旧 `/api` 调用均保持不变。
- 已新增新版公共布局 `frontend/src/stage3/Stage3Layout.tsx`，延续 `Stage3Preview` 的浅灰背景、白色内容面、低饱和蓝、弱边框和克制状态色。
- 新版公共布局已提供桌面侧栏与窄屏抽屉导航；尚未开发的页面入口明确标记为“后续”并禁用，不伪装为可用功能。
- 已新增独立 `v2Http` 客户端，固定使用 `/api/v2`；旧版 `http` 客户端继续固定使用 `/api`，两套边界不混用。
- 新版 Dashboard 初版通过 `/api/v2` 组合只读数据；后经第四小步复核，已把统计口径和下方内容结构重新对齐获认可的 `Stage3Preview`，不再以简历解析指标替换待初筛、待跟进。
- 页面已覆盖 loading、真实空状态、接口错误与重试；当前 PostgreSQL 新版业务接口返回空数组，因此页面如实展示各区域独立空状态，不使用视觉样板中的演示数字。
- 前端生产构建通过；Vite `/stage3/dashboard`、新版模块加载和 `/api/v2/jobs` 代理请求均返回 HTTP 200。现有 JavaScript bundle 大于 500 kB 的警告仍存在，不影响本次骨架运行。

### 阶段 3 第二小步进度

- 已新增隔离的新版简历管理页 `/stage3/resumes`；新版侧栏“简历管理”已可点击，旧版 `/upload`、`/form`、旧简历页面和旧 `/api/resume` 均未修改。
- 页面通过 `/api/v2/resumes` 读取真实简历记录，并通过 `/api/v2/candidates`、`/api/v2/jobs` 补充候选人姓名和关联岗位；三个请求均为只读，不写入 PostgreSQL。
- 已展示简历总数、等待解析、正在解析、解析异常和已解析数量；列表预留文件、候选人、岗位、文件信息、解析状态、失败原因和上传时间等真实业务字段。
- 已提供文件名/候选人/岗位搜索、解析状态筛选和手动刷新；筛选只作用于接口返回的真实数据，不生成演示记录。
- 已覆盖 loading、接口错误与重试、数据库真实空状态、筛选无结果状态和窄屏单列布局；“上传简历”明确标注为阶段 4，当前禁用，未提前进入文件上传或 LangGraph 解析。
- 前端生产构建通过，共转换 3903 个模块；Vite `/stage3/resumes` 与页面模块返回 HTTP 200，Vite 代理下的 `/api/v2/resumes`、`/api/v2/candidates`、`/api/v2/jobs` 均返回 HTTP 200 和空数组。
- 后续协作规则：每完成一个小步骤，除记录本步实际成果和验证结果外，必须同步改写“优先任务”，明确下一小步的页面、接口边界和不进入的后续能力。

### 阶段 3 第三小步进度

- 已新增隔离的新版候选人列表页 `/stage3/candidates`；新版侧栏“候选人”已可点击，旧版 `/candidates`、旧候选人列表/详情和旧 `/api/candidates` 均未修改。
- 页面通过 `/api/v2/candidates` 读取真实候选人记录，并通过 `/api/v2/jobs` 把 `applied_job_id` 转换为岗位名称；两个请求均为只读，不写入 PostgreSQL。
- 已展示候选人总数、新候选人、已关联岗位和已含简历数量；列表预留身份与联系方式、应聘岗位、当前公司/职位、学历/工作年限、来源、状态和更新时间等真实业务字段。
- 已提供姓名、联系方式、公司、职位和岗位关键词搜索，并支持岗位、候选人真实状态筛选和手动刷新；筛选只作用于接口返回数据，不生成演示候选人。
- 已覆盖 loading、接口错误与重试、数据库真实空状态、筛选无结果状态和窄屏单列布局；“新增候选人”明确标注为后续能力，当前禁用，未接入旧版面试、淘汰、Offer 或 AI 初筛流程。
- 前端生产构建通过，共转换 3905 个模块；Vite `/stage3/candidates` 与页面模块返回 HTTP 200，Vite 代理下的 `/api/v2/candidates`、`/api/v2/jobs` 均返回 HTTP 200 和空数组；桌面与窄屏最终空状态已完成截图检查。

### 阶段 3 第四小步进度：Dashboard 样板对齐修正

- 在继续候选人详情前重新审计阶段 1-3：Docker 中 PostgreSQL 16 健康、Redis 与 Chroma 正常运行；FastAPI `/docs` 返回 HTTP 200；Alembic 为 `bbd627449743 (head)`；Service 75 项、API 79 项，共 154 项 `unittest` 全部通过；43 个 `/api/v2`“HTTP 方法 + 路径”组合保持唯一。
- 审计确认正式 `/stage3/dashboard` 初版虽然延续了视觉语言，但擅自把样板的“待初筛、待跟进”替换为“待解析简历、解析失败”，并在数据库全空时用一块总空状态替换“最新候选人、今日待办、AI 助手”，属于业务信息结构偏差。
- 已恢复样板四张核心卡片：开放岗位、候选人、待初筛、待跟进；开放岗位和候选人读取真实 `/api/v2` 数据，待初筛按“候选人没有任何筛选结果”从 `/api/v2/candidates` 与 `/api/v2/screening-results` 计算。
- 阶段 2 尚无完整新版跟进规则和待办模型，因此“待跟进”显示 `—` 并明确标注“新版跟进规则待接入”，不显示 0 或演示数字，不用其他指标替代。
- 已恢复并始终保留“最新候选人、今日待办、AI 招聘助手”三块结构；数据库为空时分别在区域内部展示真实空状态或待接入说明，不再让整个下半区坍缩为一块大空白。
- 最新候选人表格已恢复候选人、应聘岗位、AI 匹配、状态、更新时间等样板字段；存在真实筛选结果时展示分数和 recommendation，没有结果时显示“待初筛”。欢迎区按钮当前禁用并标注后续阶段，不伪装为可用写操作。
- 前端生产构建通过，共转换 3905 个模块；Vite `/stage3/dashboard` 和页面模块返回 HTTP 200，Vite 代理下的 `/api/v2/jobs`、`/api/v2/candidates`、`/api/v2/screening-results` 均返回 HTTP 200 和空数组；桌面与窄屏最终页面已完成截图检查。
- 本步只修改前端数据组合和展示结构，没有修改后端、Schema、Service、Model、PostgreSQL、旧 `/api`、旧 Dashboard 或 `/stage3-preview`。

### 阶段 3 第五小步进度：候选人详情页骨架

- 已新增隔离的新版候选人详情路由 `/stage3/candidates/:id`，候选人列表中的姓名可进入对应详情；旧版 `/candidates/:id`、旧候选人详情和旧 `/api/candidates/{id}` 均未修改。
- 页面通过 `/api/v2/candidates/{id}` 读取单个候选人的真实资料，并通过 `/api/v2/jobs` 把 `applied_job_id` 转换为岗位名称；两个请求均为只读，不写入 PostgreSQL。
- 已展示候选人基础资料、联系方式、当前公司与职位、学历和工作年限、来源、状态、标签、关联岗位，以及嵌套的教育经历、工作经历和项目经历；缺失字段统一如实显示“未填写”或对应空状态。
- 简历卡片只反映真实的文件路径、简历正文和结构化数据是否存在，AI 摘要只展示接口真实返回值；初筛报告和招聘流程操作明确标注为后续能力并保持禁用，没有填充演示结果或接入旧版写操作。
- 已覆盖 loading、真实 404、普通接口错误、各经历模块独立空状态和窄屏单列布局；真正的 390 像素设备模拟确认页面宽度与文档宽度均为 390 像素，无横向滚动，404 说明文字可完整换行。
- 前端生产构建通过，共转换 3907 个模块；Vite `/stage3/candidates/999999999` 与新增页面模块返回 HTTP 200，Vite 代理下的 `/api/v2/candidates/999999999` 返回真实 HTTP 404；桌面与窄屏 404 页面均完成截图检查。
- 本步只新增和调整前端页面、数据读取封装、路由、布局标题与样式，没有修改后端、Schema、Service、Model、PostgreSQL、旧 `/api` 或旧页面。

### 阶段 3 第六小步进度：旧版候选人数据安全接入

- 已新增一次性迁移工具 `scripts/import_legacy_candidates.py`：默认只预览，只有显式传入 `--apply` 才会写入；旧 `backend/recruit.db` 始终使用 SQLite `mode=ro` 只读连接。
- 工具在写入事务开始后会再次检查新版 PostgreSQL 的 8 张相关业务表；只要任意表已有记录就拒绝导入，整个过程不执行删除、清空、覆盖或 upsert，中途失败会整体回滚。
- 已从恢复的旧数据中安全复制 8 个岗位、30 名候选人、30 条教育经历、30 条工作经历和 29 条已有初筛结果到新版 PostgreSQL；旧岗位引用全部有效，旧岗位 `active` 映射为新版 `open`，旧招聘阶段映射为新版候选人状态。
- 已按恢复后的文件名确认 21 份简历原件均存在于 `backend/uploads/`，新版候选人只记录相对文件路径，不移动、不复制、不覆盖原文件；阶段 4 的新版简历记录和解析流程仍未提前执行。
- 旧版已有的学校、学历、专业、工作年限、工作描述、技能标签、AI 摘要和初筛分数均按字段含义迁移；旧模型没有当前公司、当前职位、城市、项目经历等字段，因此新版保持 `null` 或空列表，页面如实显示“未填写/0 条”。
- `/api/v2/jobs`、`/api/v2/candidates`、`/api/v2/screening-results` 已分别返回 8、30、29 条真实 PostgreSQL 记录；候选人详情接口返回关联岗位、1 条教育经历和1 条工作经历，Dashboard 显示 8 个开放岗位、30 名候选人和 1 名尚无新版初筛结果的候选人。
- 已完成 Dashboard、候选人列表和候选人详情的真实数据截图检查；列表显示 30 名候选人、30 人关联岗位、21 人含简历路径，详情页缺失字段和后续能力提示均保持真实。
- 新增 8 项旧数据迁移与安全映射测试；Service 83 项、API 79 项，共 162 项 `unittest` 全部通过。前端生产构建通过，共转换 3907 个模块；`git diff --check` 通过。
- 本步没有修改 Alembic revision、数据库表结构、旧 `/api`、旧页面、SQLite 原数据、`backend/uploads/`、`.env` 或 Docker volume，也没有调用 LLM。

### 阶段 3 第七小步进度：岗位管理页骨架

- 已新增隔离的新版岗位管理页 `/stage3/jobs`，新版侧栏“岗位管理”已可点击并显示独立页头；旧版 `/jobs`、旧岗位页面和旧 `/api/jobs` 均未修改。
- 页面通过 `/api/v2/jobs` 读取真实岗位，并通过 `/api/v2/candidates` 按 `applied_job_id` 汇总每个岗位的候选人数；两个请求均为只读，不写入 PostgreSQL。
- 已展示岗位总数、开放岗位、已关闭岗位和关联候选人数；岗位表格包含岗位、部门、岗位要求、必备技能、候选人数、状态、更新时间和表单入口，当前真实结果为 8 个岗位、8 个开放岗位、0 个关闭岗位和 30 名关联候选人。
- 已提供岗位/部门/职责/技能搜索、真实状态筛选和手动刷新；筛选只作用于接口返回数据，没有生成演示岗位。
- 已提供新增与编辑岗位的表单抽屉结构，覆盖岗位名称、部门、状态、岗位描述、任职要求摘要和必备技能；抽屉明确说明未连接 `/api/v2` 写接口，保存按钮保持禁用，不会修改数据库，也未提前实现 JD 解析或 AI 匹配。
- 已覆盖 loading、接口错误与重试、数据库真实空状态、筛选无结果状态和窄屏布局；真正的 390 像素设备模拟确认整页无横向溢出，多列表格仅在自身容器内横向滚动，表单抽屉和桌面表格均完成截图检查。
- 前端生产构建通过，共转换 3909 个模块；Vite `/stage3/jobs` 返回 HTTP 200，Vite 代理下的 `/api/v2/jobs`、`/api/v2/candidates` 均返回真实数据；`git diff --check` 通过。
- 本步只修改前端页面、数据读取封装、路由、公共布局和样式，没有修改后端、Schema、Service、Model、PostgreSQL、旧 `/api` 或旧页面。

### 阶段 3 第八小步进度：AI 筛选中心骨架

- 已新增隔离的新版 AI 筛选中心 `/stage3/screening`，新版侧栏“AI 初筛”已可点击并显示独立页头；旧版 `/ai-screening`、旧 AI 初筛页面及旧 `/api/screening` 写操作均未修改。
- 页面并行只读请求 `/api/v2/jobs`、`/api/v2/candidates` 和 `/api/v2/screening-results`，在前端按 ID 关联真实岗位、候选人与历史结果；当前页面如实显示 8 个岗位、30 名候选人和 29 条已迁入 PostgreSQL 的历史初筛结果。
- 已完成岗位筛选与推荐结果筛选；岗位下拉同时展示各岗位已有结果数，当前统计会随筛选结果同步更新，包含历史结果数、覆盖候选人数、有效分数平均值和含实际风险项的结果数。
- 初筛结果列表按更新时间倒序展示候选人、岗位、总分、推荐结果、优先级、筛选理由、优势项、风险项、技能/经验/项目维度分、硬性条件记录、数据来源和更新时间；历史数据未单独记录的优势与维度分统一显示“未单独记录”或 `—`，不补造内容。
- 已明确区分三类状态：全库没有筛选结果、选中岗位没有筛选结果、已有历史结果但当前筛选条件无匹配；同时覆盖 loading、接口错误与重试、清除筛选和窄屏布局。
- 页面明确标注“只读历史结果”，重新筛选按钮保持禁用；本步没有运行重新筛选，没有调用 LLM 或 LangGraph，没有生成新的 AI 业务结果，也没有修改 PostgreSQL。
- 前端生产构建通过，共转换 3911 个模块；Vite `/stage3/screening` 与三个 `/api/v2` 读取接口均返回 HTTP 200，页面真实统计为 29 条结果、29 名覆盖候选人、平均分 81、10 条含实际风险结果；`git diff --check` 通过。
- 已完成 1440 像素桌面截图检查；通过 Edge 设备指标把页面严格模拟为 390 像素，确认 `innerWidth`、`documentElement.scrollWidth` 和 `body.scrollWidth` 均为 390，越界元素为 0，筛选控件、刷新按钮和结果卡片均能在窄屏完整换行。
- 本步只新增和调整前端页面、只读数据组合、路由、公共布局与共享样式；后端 API、Schema、Service、Model、PostgreSQL、旧 SQLite、`backend/uploads/`、旧页面和旧 `/api` 均未修改，因此没有重复运行后端 unittest。

### 阶段 3 第九小步进度：候选人状态统一显示修正

- 已新增阶段 3 公共候选人状态字典，数据库和 `/api/v2` 继续保留稳定英文代码，前端统一翻译为中文业务名称；候选人列表和详情页不再各自维护不完整的映射。
- 已覆盖当前 PostgreSQL 实际存在的 9 种状态：`new`、`screening`、`interview_pending`、`interview_scheduled`、`interviewing`、`second_interview`、`offer`、`hired`、`rejected`，分别显示为新候选人、待筛选、待约面、已约面、面试中、复试、Offer 阶段、已入职、已淘汰。
- 状态筛选选项已按招聘流程顺序排列，不再按英文代码字母排序；筛选框与下拉弹层宽度调整为 156 像素，中文状态完整显示。未知的新状态会明确显示“未识别状态”并在筛选项保留原代码，避免被错误翻译。
- 截图检查时发现候选人 7 列布局被后置的公共 5 列表格规则覆盖，已提高候选人表格列规则的优先级；候选人、岗位、当前经历、学历/年限、来源、状态和更新时间现已各自对齐。
- 当前真实 9 种状态已逐项核对；下拉弹层实际宽度为 156 像素，表头与数据行均解析为 7 列；状态为 `hired` 的候选人详情页实际显示“已入职”。
- 前端生产构建通过，共转换 3912 个模块；候选人列表状态下拉和详情标签完成浏览器检查，`git diff --check` 通过。
- 本步只修正前端状态语义、筛选显示和表格布局，没有修改 API、Schema、Service、Model、PostgreSQL、旧 `/api` 或旧页面。

### 阶段 3 第十小步进度：初筛报告页骨架

- 已新增隔离的新版初筛报告页 `/stage3/reports`，新版侧栏“初筛报告”已可点击并显示独立页头；旧版路由、旧页面及旧 `/api` 均未修改。
- 页面只读请求 `/api/v2/reports`，并读取 `/api/v2/candidates`、`/api/v2/jobs` 和 `/api/v2/screening-results` 以准备报告与候选人、岗位、筛选结果的真实关联；当前四个接口分别返回 0 条报告、30 名候选人、8 个岗位和 29 条历史初筛结果。
- 已展示报告总数、已关联初筛、覆盖候选人和覆盖岗位四项统计；真实空状态明确展示“已有初筛结果 29 条 -> 已生成报告 0 条”，没有把筛选结果、候选人简历或其他数据伪装成报告。
- 已预留报告标题/候选人/岗位/正文关键词搜索、岗位筛选、报告类型筛选、刷新、报告列表和只读查看抽屉；未来存在报告时可展示标题、正文预览、类型、存储格式、关联筛选结果、匹配分、推荐结果、元数据和时间字段。
- 已覆盖 loading、接口错误与重试、数据库真实空状态、已有报告但筛选无结果、清除筛选和窄屏布局；生成报告与导出按钮保持禁用。
- 本步没有生成报告，没有调用 LLM、LangGraph 或 `report_gen`，没有进行 Markdown 渲染、PDF/Word 导出、发送给面试官或任何 PostgreSQL 写操作。
- 前端生产构建通过，共转换 3914 个模块；Vite `/stage3/reports` 与四个 `/api/v2` 读取接口均返回 HTTP 200；`git diff --check` 通过。
- 已完成 1440 像素桌面真实空状态截图检查；通过 Edge 设备指标严格模拟 390 像素，确认 `innerWidth`、`documentElement.scrollWidth` 和 `body.scrollWidth` 均为 390，越界元素为 0，筛选控件、刷新按钮、数据边界说明和空状态均完整显示。
- 本步只新增和调整前端页面、只读数据组合、路由、公共布局与共享样式；后端 API、Schema、Service、Model、PostgreSQL、旧 SQLite、`backend/uploads/`、旧页面和旧 `/api` 均未修改，因此没有重复运行后端 unittest。

### 阶段 3 第十一小步进度：候选人投递页骨架

- 已新增独立的候选人投递页 `/stage3/apply`，页面不套用 HR 后台侧栏，但继续使用阶段 3 的浅灰背景、白色卡片、克制蓝色和弱边框视觉语言；旧版公开 `/apply`、旧投递页面和旧 `/api/apply` 均未修改。
- 页面只读请求 `/api/v2/jobs` 并只展示状态为 `open` 或 `active` 的岗位；当前真实返回 8 个岗位且全部开放，岗位选择项展示岗位名称和部门，选中后可查看已有岗位说明与任职要求，不生成演示岗位。
- 已完成基本信息、教育背景、求职信息和简历文件四组表单结构，覆盖姓名、手机号、邮箱、院校、学历、专业、应聘岗位、技能关键词、个人简介和简历选择；表单刷新后不会保留。
- 简历选择仅使用浏览器本地文件列表，限制为 PDF、DOC、DOCX、TXT 且不超过 10MB，并在上传区域明确标注“仅本地选择，不会上传”；没有调用新版或旧版上传、解析、候选人写入接口。
- 页面头部、投递说明和表单底部均明确标注当前为结构预览；提交按钮保持禁用，本步不会创建候选人、简历、初筛或报告记录，不调用 LLM、LangGraph，也不修改 PostgreSQL。
- 已覆盖 loading、岗位接口错误与重试、真实开放岗位为空和窄屏单列布局；接口异常和没有开放岗位是两种独立状态，不会把接口失败误报为空数据。
- 前端生产构建通过，共转换 3916 个模块；Vite `/stage3/apply` 返回 HTTP 200，`/api/v2/jobs` 返回 8 个真实开放岗位，新建的数据服务不包含 POST、PUT、PATCH 或 DELETE 写方法；`git diff --check` 通过，仅保留原有换行符提示。
- 已完成 1440 像素桌面截图检查；通过 Edge 设备指标严格模拟 390 像素，确认 `innerWidth`、`documentElement.scrollWidth` 和 `body.scrollWidth` 均为 390，越界元素为 0，开放岗位数和禁用提交状态均在真实 DOM 中确认。
- 本步只新增和调整前端页面、岗位只读封装、路由和共享样式；后端 API、Schema、Service、Model、PostgreSQL、旧 SQLite、`backend/uploads/`、旧页面和旧 `/api` 均未修改，因此没有重复运行后端 unittest。

### 阶段 3 第十二小步进度：页面骨架收口复核

- 已逐项核对阶段 3 路由、侧栏导航、候选人公开投递入口和数据服务：`/stage3/dashboard`、`/stage3/resumes`、`/stage3/candidates`、候选人详情、`/stage3/jobs`、`/stage3/screening`、`/stage3/reports`、`/stage3/apply` 均返回 HTTP 200；侧栏活动页面标识正确，公开投递页继续与 HR 后台布局隔离。
- 已确认 `frontend/src/stage3/services/` 中所有阶段 3 数据请求均为 `GET`；新增候选人、上传简历、岗位保存、重新筛选、报告生成/导出、招聘流程操作和投递提交仍保持禁用，没有 POST、PUT、PATCH 或 DELETE 写请求。
- 已重新核对真实 PostgreSQL 只读结果：8 个岗位且全部开放、30 名候选人、29 条历史初筛结果、0 条新版简历、0 条报告；1 名候选人尚无初筛结果。候选人关联岗位和初筛结果关联候选人/岗位均没有孤立引用，30 对 29 是真实业务状态而不是关联错误。
- 已修复阶段完成后遗留的过期入口：Dashboard 的“查看全部候选人”和最近候选人姓名现可进入真实列表/详情；候选人详情可进入岗位列表、AI 初筛和初筛报告，并如实说明单个岗位详情及招聘流程写操作尚未开放。
- 窄屏审查发现 Dashboard 多列表格虽然设置了局部横向滚动，但 CSS Grid 子项的固有最小宽度仍把整页撑到 780 像素；已把窄屏内容网格改为 `minmax(0, 1fr)` 并允许子项收缩，表格继续在自身容器中滚动而不再造成整页横向溢出。
- 已逐页检查 1440 像素桌面布局和严格 390 像素窄屏布局：后台页面显示正确活动导航或移动菜单，公开投递页保持独立页头；修复后 Dashboard 直接首次加载的 `innerWidth`、`clientWidth`、`documentElement.scrollWidth` 和 `body.scrollWidth` 均为 390，其余阶段 3 页面也均保持 390 像素文档宽度。
- 前端生产构建通过，共转换 3916 个模块；阶段 3 与旧版 `/apply`、`/dashboard`、`/candidates`、`/jobs`、`/ai-screening` 均返回 HTTP 200；`git diff --check` 通过，仅保留原有换行符提示。
- 本步只修正前端导航、说明文案和窄屏布局，没有修改后端 API、Schema、Service、Model、PostgreSQL、旧 SQLite、`backend/uploads/`、`.env`、Docker volume、旧页面或旧 `/api`，因此没有重复运行后端 unittest。

### 阶段 3 第十三小步进度：投递页岗位要求修复与样式模块化

- 已修复候选人投递页岗位要求的数据类型错误：`/api/v2/jobs` 的 `requirements` 按真实 JSON 对象读取，前端只提取字符串摘要和字符串技能数组，不再把整个对象直接交给 React 渲染。
- 已在真实 390 像素浏览器中打开岗位下拉并选择“测试工程师”，页面成功展示岗位说明、任职要求和 4 个必备技能标签；未出现 React 对象渲染错误，提交按钮仍保持禁用，没有产生候选人、简历或其他写入。
- 原 `frontend/src/pages/Stage3Preview.css` 已安全迁移到 `frontend/src/stage3/styles/`；`Stage3Layout`、`Stage3ApplicationForm` 和保留的 `/stage3-preview` 页面均改为引用正式阶段 3 样式入口，旧位置不再保留重复样式内容。
- 阶段 3 样式已按职责拆分为 `tokens.css`、`layout.css`、`shared.css`、`dashboard.css`、`resumes.css`、`candidates.css`、`jobs.css`、`screening.css`、`reports.css` 和 `application.css`；`index.css` 只按固定顺序导入这些模块。
- 拆分前后共 180 个 `.s3-*` 类选择器，完整性检查确认缺失 0、意外新增 0；公共视觉 token、选择器名称和页面业务结构保持不变，避免样式归档演变成重新设计。
- 已对 Dashboard、简历、候选人列表/详情、岗位、AI 初筛、初筛报告、视觉样板和候选人投递页逐页执行 1440 像素与严格 390 像素浏览器检查；所有页面均无错误提示，桌面宽度保持 1440，窄屏的 `innerWidth`、文档和 body 宽度均为 390。
- 已对拆分前后的 Dashboard、候选人窄屏和候选人投递桌面截图进行对比，页面层级、颜色、间距和布局未发生可见偏移；`/stage3-preview` 视觉样板在桌面和窄屏下继续正常显示。
- CSS 原样搬迁后的中间生产构建和最终模块化后的生产构建均通过，共转换 3916 个模块；`git diff --check` 通过，仅保留原有换行符提示。
- 本步只调整前端岗位要求适配、样式归属、模块拆分和导入路径，没有修改后端 API、Schema、Service、Model、PostgreSQL、旧 SQLite、`backend/uploads/`、旧页面路由或旧 `/api`，因此没有重复运行后端 unittest。

### 阶段 3 第十四小步进度：新旧页面路由级懒加载与前端拆包收尾

- 已把 `frontend/src/App.tsx` 中旧版布局/页面、阶段 3 布局/页面和视觉样板共 18 个同步导入改为 `React.lazy` 动态导入；路由路径、嵌套关系、旧版入口与 `/stage3/*` 入口均保持不变。
- 已为每个懒加载路由增加统一 `Suspense` 加载状态；加载提示包含 `role="status"` 与 `aria-live="polite"`，并在用户启用减少动态效果时停止旋转动画。
- 前端生产构建通过，共转换 3917 个模块；原单一入口 JavaScript 为 1955.98 kB（gzip 594.91 kB），拆包后入口为 263.65 kB（gzip 89.66 kB），最大页面块为 422.01 kB（gzip 116.49 kB），Vite 的 500 kB 大块警告已消失。
- 已确认构建产物包含独立的阶段 3 Dashboard、简历、候选人列表/详情、岗位、AI 初筛、初筛报告、候选人投递和布局代码块；后端全量 162 项 `unittest` 通过；`git diff --check` 通过，仅保留工作区既有换行符提示。
- 本步只调整前端模块加载方式与加载状态样式，没有修改页面业务逻辑、API、Schema、Service、Model、PostgreSQL、旧 SQLite、文件目录或路由地址。

### 阶段 4 第一小步进度：新版简历安全接收、元数据与 uploaded 状态

- 已完成旧 `/api/resume/upload` 审计：旧接口只按扩展名判断格式，把文件完整读入内存并先写入 `backend/uploads/`，随后同步解析和创建旧候选人；解析失败或数据库失败时可能遗留文件，且没有按文件内容校验实际类型。本步没有修改该旧路由或旧 `file_parser.py`。
- 已完成新版 Resume Model、Schema、Service、`/api/v2/resumes` 与文件目录审计：当前 `Resume.candidate_id` 必填，因此第一小步要求上传时关联已存在的新版候选人；不创建候选人，不把旧候选人的 `resume_file_path` 伪装为新版 Resume。
- 已新增 `POST /api/v2/resumes/upload`，使用 `multipart/form-data` 接收 `file`、必填 `candidate_id` 和可选 `job_id`；候选人或岗位不存在返回 `404`，不支持的扩展名返回 `415`，空文件/内容类型不符返回 `400`，超过 10 MB 返回 `413`。
- 旧 `UPLOAD_DIR` 当前被 `/uploads` 静态公开，因此新版不复用其子目录；已新增私有 `V2_STORAGE_DIR`，本地默认 `backend/storage`、Docker 使用独立 `resume-data` volume，且不挂载静态路由。新版文件写入 `<V2_STORAGE_DIR>/v2/resumes/YYYY/MM/<UUID>.<ext>`；数据库 `filename` 只保存剥离目录成分后的原始展示名，磁盘路径只由服务端 UUID、UTC 年月和已验证扩展名生成。同名或相同内容允许形成独立 Resume 版本，不覆盖旧文件，也不在本步执行候选人或内容去重。
- 上传不信任客户端声明的 MIME：服务端按 `%PDF-` 文件头识别 PDF，按 ZIP 结构中的 `[Content_Types].xml` 与 `word/document.xml` 识别 DOCX，并对 TXT 做严格解码和控制字符比例检查；扩展名必须与实际内容一致。数据库保存服务端识别的标准 MIME。
- 由于 DOCX 标准 MIME 长 71 字符，已新增 Alembic revision `8a9c4d2e1f01`，只把 `resumes.file_type` 从 `VARCHAR(30)` 扩为 `VARCHAR(100)`；真实 PostgreSQL 已升级到该 head，字段长度查询返回 100。
- 事务顺序为：先确认 Candidate/Job 外键 -> 分块写入 `v2/resumes/.staging` 并限制大小 -> 校验真实内容 -> PostgreSQL `flush`（未提交）-> 原子移动到最终路径 -> PostgreSQL `commit`。文件落盘失败会回滚未提交记录；数据库 `flush/commit` 失败会回滚并删除临时文件与最终文件。
- PostgreSQL 与本地文件系统不能组成真正的跨系统原子事务，进程在“文件移动成功、数据库提交之前”被强制终止仍存在极小崩溃窗口。后续孤立文件对账只能扫描 `v2/resumes`，必须用数据库 `file_path` 反查并设置宽限期；不得扫描删除 `backend/uploads/` 根层旧文件。本小步先覆盖所有可捕获异常的即时清理，不提前实现定时清理任务。
- 新增 20 项上传隔离测试；Resume 相关 42 项测试全部通过，后端全量回归共 182 项全部通过。测试使用 `TemporaryDirectory`，覆盖 PDF/DOCX/TXT、安全文件名、同名不覆盖、非法扩展名、空文件、超限、内容伪装、关联对象不存在、文件失败、数据库 flush/commit 失败和清理回滚。
- 真实 PostgreSQL + 真实私有临时目录验证通过：正式新版路由最终生成 Resume ID 7，写入候选人 46、岗位 11、原始名 `final.pdf`、MIME `application/pdf`、14 字节、`uploaded` 状态，`raw_text` 保持 `null`；实际文件位于系统临时目录的 `v2/resumes/2026/08/<UUID>.pdf`，未经过旧 `/uploads` 静态挂载。非法文件、文件落盘失败、数据库 commit 失败均验证数据库计数不变且孤立文件为 0；临时 Resume、Candidate、Job 和临时目录均已清理。
- 本轮启动 Docker 前各服务均不可用；恢复 Docker Desktop 后 PostgreSQL 16 容器健康，Redis、Chroma、后端和前端未启动。当前真实 PostgreSQL 在验证前的 `candidates/jobs/resumes` 计数均为 0，与阶段 3 曾记录的 30/8/0 不一致；本轮没有清空、重建或覆盖数据库，只如实记录当前所连接 volume 的状态。
- `backend/uploads/` 仍为原有 21 个 TXT 文件、共 9,128 字节，根层文件未移动、覆盖或删除；所有新增自动化和真实验证文件都位于临时目录。

### 阶段 4 第二小步进度：TXT 原文提取与解析状态流转

- 已新增 `POST /api/v2/resumes/{resume_id}/extract-text`，只处理第一小步安全上传生成的 `text/plain` Resume；Resume 不存在返回 `404`，正在解析返回 `409`，PDF/DOCX 等本步未支持类型返回 `415`，文件读取或完整性校验失败返回 `422`。
- 已新增独立 `ResumeTextExtractor`：只允许解析 `V2_STORAGE_DIR/v2/resumes/` 内的 `.txt` 最终文件，拒绝绝对路径、`..` 越界、`.staging` 临时文件、非 TXT 后缀、缺失文件和缺少文件大小元数据的记录。
- 提取前会对比磁盘实际字节数与 Resume `file_size`；上传后被替换或追加内容的文件不会进入 `raw_text`。TXT 解码复用上传阶段同一套 `chardet + utf-8 + gb18030` 严格规则，并拒绝二进制控制字符过多或只有空白的文本。
- 同步接口在单个数据库事务内执行 `uploaded/failed -> parsing（flush，未提交）-> parsed/failed（commit）`。`parsing` 是本次同步事务中的中间态：成功时保存完整 `raw_text`、清空 `parse_error` 并写入 `parsed_at`；提取失败时保存 `failed + parse_error`，但保留原文件供人工检查和重试。
- 采用“中间态只 flush、不提前 commit”的原因是避免数据库最终提交失败后永久遗留 `parsing`。真实 commit 失败验证中，PostgreSQL 回滚到原 `uploaded` 状态，`raw_text/parse_error/parsed_at` 仍为空，原始 TXT 文件继续存在。
- 已支持幂等和重试：已经 `parsed` 且有 `raw_text` 的 Resume 再次调用直接返回现有结果，不重复读文件；`failed` Resume 修复文件后可以重新进入提取流程。
- 本步新增 26 项隔离测试；Extractor、Service 与 Resume API 相关隔离测试共 47 项全部通过，后端全量回归从 182 增至 208 项全部通过。覆盖 UTF-8、GB18030、完整原文保留、路径穿越、绝对路径、临时目录、文件缺失、大小篡改、空白/二进制文本、状态冲突、幂等、失败重试和数据库 flush/commit 回滚。
- 真实 PostgreSQL + 真实私有临时目录验证通过：Resume ID 10 从 `uploaded` 变为 `parsed`，完整写入 24 个字符的中文原文，`parsed_at` 非空且原 TXT 文件保持原字节；Resume ID 11 为 PDF，调用提取接口返回 `415` 并保持 `uploaded`；篡改 TXT Resume ID 13 返回 `422`，数据库保存 `failed + 简历文件大小与上传记录不一致` 且篡改文件仍保留；强制数据库 commit 失败的 Resume ID 14 回滚为 `uploaded` 且文件保留。所有临时 Candidate、Job、Resume 和系统临时目录均已清理。
- 本步没有修改 Model、Schema、Alembic、旧 `file_parser.py`、旧 `/api/resume/*`、前端、旧 SQLite、`backend/uploads/` 或 Docker volume，也没有调用 LLM、LangGraph、AI 初筛或报告生成。

### 阶段 4 第三小步进度：PDF 文字层提取与质量边界

- 统一接口 `POST /api/v2/resumes/{resume_id}/extract-text` 已扩展支持服务端识别 MIME `application/pdf`；ResumeService 根据 MIME 分派 TXT 或 PDF 提取器，DOCX 仍明确返回 `415`，前端后续无需为不同文件类型维护不同提取接口。
- 已新增通用 `ResumeFileAccess`，集中处理 TXT/PDF 共用的私有命名空间、路径穿越、绝对路径、`.staging`、文件存在、扩展名和数据库 `file_size` 一致性校验；TXT 提取器已改为复用该组件，原有 TXT 行为和测试保持通过。
- 已新增独立 `ResumePdfExtractor`，使用项目现有 PyPDF2 3.0.1 的 `PdfReader(strict=False)` 按原页码逐页读取文字层，跳过空白页，并用两个换行连接非空页面；不调用 AI 改写、总结或补全原文。
- PDF 专有失败边界已明确：无页面、损坏/无法读取、密码加密、页级提取异常、全部页面无文字、有效文字过少和字体编码异常均保存稳定 `parse_error`；无文字层统一提示“可能是扫描件，需要 OCR”，但本步不接 OCR。
- 已增加资源安全上限：单份 PDF 最多 100 页，提取文本最多 1,000,000 字符；超过限制进入 `failed`，避免小体积恶意 PDF 长时间占用 CPU 或异常展开内存。
- PDF 继续复用 TXT 已验证的单事务状态流：`uploaded/failed -> parsing（flush，未提交）-> parsed/failed（commit）`。数据库最终 commit 失败会回滚到原 `uploaded`，不会永久卡在 `parsing`；无论提取成功还是失败，原始 PDF 均保留。
- 本步新增 16 项隔离测试；PDF、TXT、Service 与 Resume API 相关隔离测试共 63 项全部通过，后端全量回归从 208 增至 224 项全部通过。覆盖单页、多页顺序、空白页、无页面、扫描件边界、低质量、损坏、加密、100 页限制、输出长度限制、路径穿越、临时目录、文件缺失、大小篡改、MIME 分派和失败状态持久化。
- 真实 PostgreSQL + 真实私有临时目录验证通过：Resume ID 15 的三页 PDF（含空白页）按页序提取并保存 111 个字符，状态为 `parsed`、`parsed_at` 非空且原文件字节不变；Resume ID 16 的无文字层 PDF 保存 `failed + 需要 OCR` 且文件保留；Resume ID 18 的损坏 PDF 返回 `422` 并保存 `failed + PDF 文件损坏或无法读取`；强制数据库 commit 失败的 Resume ID 19 回滚为 `uploaded`，原 PDF 保留且 `raw_text/parse_error/parsed_at` 均为空。所有临时 Candidate、Job、Resume 和系统临时目录均已清理。
- 本步没有修改 API 路径、Model、Schema、Alembic、旧 `file_parser.py`、旧 `/api/resume/*`、前端、旧 SQLite、`backend/uploads/` 或 Docker volume，也没有调用 OCR、LLM、LangGraph、AI 初筛或报告生成。

### 阶段 4 第四小步进度：DOCX 正文与表格文本提取

- 统一接口 `POST /api/v2/resumes/{resume_id}/extract-text` 已扩展支持服务端识别的 DOCX 标准 MIME；ResumeService 现在按 MIME 分派 TXT、PDF 或 DOCX 提取器，前端不需要维护不同格式的提取接口，未知 MIME 仍返回 `415`。
- 已新增独立 `ResumeDocxExtractor`，使用项目既有 `python-docx 1.1.2`，通过 `Document.iter_inner_content()` 按正文中的真实出现顺序读取普通段落和表格；表格按行输出、单元格以制表符分隔，并避免合并单元格文字重复。页眉、页脚、图片、文本框和批注不在本小步范围内。
- DOCX 继续复用 `ResumeFileAccess`，提取前校验私有 `v2/resumes` 命名空间、`.docx` 后缀、文件存在性和数据库 `file_size`；解析过程只读取 ZIP 包，不把任何成员解压到文件系统，因此不会由压缩包内部路径产生目录穿越写入。
- 已增加压缩包资源边界：最多 2,000 个 ZIP 成员、解压后总大小最多 50 MiB、提取文本最多 1,000,000 字符，并拒绝 ZIP 加密标志；损坏包、空文档、结构过于复杂、解压规模超限和文本超限均返回稳定 `422`，数据库保存 `failed + parse_error`。
- DOCX 完全复用既有单事务状态流：`uploaded/failed -> parsing（flush，未提交）-> parsed/failed（commit）`。成功保存完整 `raw_text` 和 `parsed_at`；文件读取失败不创建其他文件，数据库最终提交失败由统一服务回滚，不会遗留永久 `parsing` 状态。
- 本步新增 11 项隔离测试；DOCX 提取器与统一状态服务的定向测试共 23 项全部通过，后端全量回归从 224 增至 235 项全部通过。覆盖正文/表格顺序、合并单元格、空文档、损坏包、ZIP 成员数、解压大小、文本长度、路径越界、大小不一致、MIME 分派、失败状态和数据库回滚。
- 真实 FastAPI + PostgreSQL + 私有临时目录验证通过：DOCX 上传返回 `201`，原始中文文件名和标准 MIME 正确保存，文件实际写入系统临时目录的 `v2/resumes/2026/08/<UUID>.docx`；提取返回 `200`，中文段落、表格与后续段落共 43 个字符逐字写入 `raw_text`，状态为 `parsed` 且 `parsed_at` 非空。伪造 DOCX 上传返回 `400` 且无文件/数据库残留；删除临时原文件后提取返回 `422`，PostgreSQL 保存 `failed + 原始简历文件不存在` 且 `raw_text` 为空。所有临时 Candidate、Resume 和临时目录均已清理。
- 本步没有新增 API 路径，没有修改 Model、Schema、Alembic、旧 `file_parser.py`、旧 `/api/resume/*`、前端、旧 SQLite、`backend/uploads/` 或 Docker volume，也没有调用 OCR、LLM、LangGraph、AI 初筛或报告生成。

#### 阶段 4 DOCX 文本框兼容补强

- 真实 Resume #66 是有效 DOCX，但正文几乎全部位于 Word/VML 文本框；`python-docx` 能打开文件，却只能看到 60 个空正文段落，因此原提取器返回“没有可提取的有效文本”。这不是 DeepSeek 故障，也不是文件损坏。
- 新增 `mammoth==1.12.1` 作为文本框文档的原文提取依赖。提取器先执行既有私有路径、文件大小、ZIP 成员数、解压体积、加密标志和文本长度校验；普通段落/表格 DOCX 继续使用原 `python-docx` 顺序提取，检测到 `txbxContent` 或普通正文为空时才使用 Mammoth，Mammoth 失败且普通正文可用时自动回退。
- 未调用 DeepSeek、未修改 Resume #66 数据库记录的隔离实测中，正式提取器读取 2,125 个字符、36 个非空文本段，重复段落数为 0，耗时约 169 毫秒；说明文件转原文已可落地，仍不能替代后续 AI 结构化质量验收。
- DOCX 提取器新增文本框与 Mammoth 失败回退测试，专项测试 11 项、后端全量回归 370 项全部通过。纯图片 DOCX 仍不在本步做 OCR，继续返回无有效文本并允许 HR 保留文件后手工填写。

### 阶段 4 第五小步进度：新版候选人创建入口与上传流程校正

- 前端联调审计发现，当前新版 `Resume.candidate_id` 和 `POST /api/v2/resumes/upload` 都要求简历必须关联已存在候选人；在 PostgreSQL 为空时直接从简历列表选择候选人的方案无法成立，也不能在未调用 AI 的情况下根据客户端文件名伪造候选人身份。根据实际接口和产品操作习惯，流程已明确为“新增候选人 -> 进入候选人详情 -> 上传简历 -> 提取原文”。
- 已启用阶段 3 候选人列表的“新增候选人”入口，使用现有 `POST /api/v2/candidates` 创建基础记录；姓名必填，电话、邮箱、应聘岗位和来源可选，默认状态为 `new`、默认来源为 `HR手动录入`。创建成功后直接跳转 `/stage3/candidates/{id}`，不在本步上传文件或写入简历原文。
- 已在 `frontend/src/stage3/services/candidates.ts` 增加独立创建方法，继续使用 `v2Http`，未混用旧 `/api` 客户端；前端弹窗显示本步边界并在提交期间禁止重复关闭或重复提交，空姓名和邮箱格式先由表单拦截，后端 Pydantic 继续作为最终校验。
- 前端生产构建通过，共转换 3917 个模块；入口 JavaScript 为 263.68 kB（gzip 89.69 kB），最大块仍为 422.01 kB（gzip 116.50 kB），没有重新出现 Vite 500 kB 大块警告。后端全量 235 项 `unittest` 全部通过。
- 真实 FastAPI + PostgreSQL 验证通过：临时候选人 ID 57 返回 `201`，姓名、电话、邮箱、来源和 `new` 状态真实写入 PostgreSQL，`resume_file_path`、`resume_text` 均为空且没有结构化解析数据；详情接口返回 `200`，空姓名创建返回 `422`。随后通过 `DELETE /api/v2/candidates/57` 精确删除，详情再次查询为 `404`，没有清空或重建数据库。
- 本地 Uvicorn 使用 `--lifespan off` 启动，因此没有执行旧版 Demo 种子逻辑；Vite 与后端测试进程及临时日志已停止并清理。当前环境没有可用的内置浏览器实例，未声称完成点击或截图视觉验收；页面代码已通过 TypeScript 和生产构建，真实接口与数据库链路已单独验证。
- 本步没有修改 Candidate/Resume Model、Schema、Alembic、后端业务代码、旧页面、旧 API、`backend/uploads/` 或文件存储，也没有调用 OCR、LLM、LangGraph、AI 初筛或报告生成。

### 阶段 4 第六小步进度：候选人确认前的待绑定简历边界

- 根据最终确认的产品流程，阶段 4 的目标流程调整为“在统一新增候选人页面手动填写字段或上传简历 -> 提取原文 -> 识别字段并只补充空字段 -> HR 检查并确认创建候选人 -> 绑定简历”。第五小步曾采用的“先创建候选人再进入详情上传”保留为可用的手动创建能力，但不再作为目标主流程。
- 已新增 Alembic revision `d3f6a8c1b204`，把新版 `resumes.candidate_id` 从 `NOT NULL` 改为可空，同时继续保留到 `candidates.id` 的外键约束；已有已绑定 Resume 不变，有候选人 ID 时仍必须引用真实候选人，不创建占位候选人，也不把旧候选人的文件路径伪装为新版 Resume。
- 现有 `POST /api/v2/resumes/upload` 的 `candidate_id` 已改为可选：省略时创建 `candidate_id = NULL` 的待绑定 Resume，传入时继续执行原有候选人存在性校验；接口路径、文件校验、私有命名空间、UUID 文件名、原始文件名保存、大小限制及事务顺序均未改变。
- 上传事务继续为“可选 Candidate/Job 校验 -> 临时分块写入并校验 -> PostgreSQL flush -> 原子移动文件 -> PostgreSQL commit”。待绑定分支已直接覆盖文件移动失败、数据库 flush 失败和数据库 commit 失败，失败后均回滚数据库并清除临时/最终文件；非法文件和不存在的显式候选人仍在落库前失败。
- Resume 响应 Schema 与前端阶段 3 简历列表已兼容 `candidate_id = null`；待绑定记录显示“待确认候选人 / 尚未创建候选人”，不会显示“候选人 #null”。本步没有提前增加绑定接口、结构化字段识别或自动填表逻辑。
- 本步新增 2 项隔离测试；新版上传 Service/API 定向 41 项全部通过，后端全量回归从 235 增至 237 项全部通过。新增分支及既有测试共同覆盖成功上传、非法文件、显式候选人不存在、文件移动失败、数据库 flush/commit 失败、回滚和孤立文件清理。
- 真实 FastAPI + PostgreSQL + 私有临时目录验证通过：未传 `candidate_id` 上传 TXT 返回 `201` 并生成 Resume ID 24，PostgreSQL 读取确认 `candidate_id = NULL`、状态从 `uploaded` 成功流转为 `parsed`、`raw_text` 保存 33 个字符；文件实际写入系统临时目录的 `v2/resumes/2026/08/<UUID>.txt`，原始展示名中的目录成分已移除。非法 EXE 返回 `415`、显式不存在候选人返回 `404`，两种失败后数据库和文件计数均未增加。
- 临时 Resume 已精确删除，临时目录已清理；最终 PostgreSQL `candidates/jobs/resumes` 计数均为 0。迁移已完成 `d3f6a8c1b204 -> 8a9c4d2e1f01 -> d3f6a8c1b204` 真实降级/升级往返，当前 head 为 `d3f6a8c1b204`，`information_schema` 确认 `candidate_id` 可空。
- 前端生产构建通过，共转换 3917 个模块；入口 JavaScript 为 263.68 kB（gzip 89.68 kB），最大块为 422.01 kB（gzip 116.50 kB），无 Vite 500 kB 大块警告。旧 `/api/resume/upload` 和新版 `/api/v2/resumes/upload` 继续并存；`backend/uploads/` 未移动、覆盖或删除。

### 阶段 4 第七小步进度：确认候选人与待绑定简历的单事务保存

- 已新增 `POST /api/v2/candidates/from-resume`，请求体为 `{ resume_id, candidate }`；`candidate` 复用现有 `CandidateCreate`，支持候选人主字段及教育、工作、项目三类嵌套经历。现有 `POST /api/v2/candidates` 继续用于无简历的普通手动创建，旧版候选人和简历接口均未修改。
- CandidateService 使用 PostgreSQL `SELECT ... FOR UPDATE` 锁定目标 Resume；Resume 不存在返回 `404`，已绑定 Candidate 返回 `409`。同一 Resume 在并发或重复请求中只能成功绑定一次，但本步不按电话、邮箱或姓名自动判定重复候选人。
- 岗位一致性边界已明确：Candidate 与 Resume 都有岗位且不一致时返回 `409`；只有一侧有岗位时同步到另一侧；最终岗位不存在返回 `404`。Resume 可处于 `uploaded`、`parsed` 或 `failed`，解析失败不会阻止 HR 使用手填字段确认候选人。
- 客户端提交的 `resume_file_path`、`resume_text` 和 `parsed_data` 不作为可信来源；确认时统一从被锁定的 Resume 复制服务端 `file_path`、`raw_text` 和 `parsed_snapshot`，防止客户端伪造路径、原文或解析快照。
- 事务顺序为“锁定并校验 Resume/Job -> 构造 Candidate 与三类嵌套经历 -> flush 获得 Candidate ID -> 写入 Resume.candidate_id/job_id -> 再次 flush -> 事务内刷新响应数据 -> 最后 commit”。任何数据库写入、刷新或 commit 失败都会 rollback，Candidate 与 Resume 绑定不会只成功一半。
- 本步新增 12 项隔离测试；Candidate Service/API 定向 35 项全部通过，后端全量回归从 237 增至 249 项全部通过。覆盖成功确认、三类嵌套经历、服务端字段覆盖、Resume 岗位继承、Resume 不存在、重复绑定、岗位冲突、岗位不存在、请求校验和 commit 回滚。
- 真实 FastAPI + PostgreSQL + 私有临时目录验证通过：Resume ID 29 提取 19 个字符后，通过新接口创建 Candidate ID 61 并绑定岗位 ID 17；PostgreSQL 读取确认 Resume 的 `candidate_id=61`、`job_id=17`，Candidate 保存服务端文件路径和原文，并创建教育/工作/项目记录各 1 条。相同请求再次提交返回 `409`，Candidate 数量不增加；真实岗位冲突请求也返回 `409` 且 Resume 保持未绑定。
- 使用真实 PostgreSQL 事务并强制模拟 commit 失败验证 Resume ID 30：Candidate 数量保持 `0 -> 0`，Resume `candidate_id` 仍为 `NULL`。所有临时 Resume、Candidate、Job、三类经历和临时文件目录均已精确清理，最终 `jobs/candidates/resumes` 计数恢复为 0。
- 本步没有新增迁移，没有修改文件上传、TXT/PDF/DOCX 提取器、前端、旧 SQLite 或 `backend/uploads/`，也没有调用 OCR、LLM、LangGraph、AI 初筛或报告生成。

### 阶段 4 第八小步进度：统一新增候选人页面与真实链路接入

- 已新增正式路由 `/stage3/candidates/new`，候选人列表的“新增候选人”按钮和空状态入口都进入该页面；原有小型弹窗已移除，候选人详情和其他新旧路由保持不变。`App.tsx` 继续使用路由级懒加载，新页面形成独立构建块。
- 页面把手动录入和简历处理放在同一个确认流程中：姓名、联系方式、性别、年龄、所在地、应聘岗位、来源、当前公司/职位、工作年限、学历层次及教育/工作/项目经历均可手填，三类经历支持增删多条记录。
- 无简历时继续调用 `POST /api/v2/candidates` 普通创建候选人；有简历时依次调用 `POST /api/v2/resumes/upload` 创建待绑定 Resume、`POST /api/v2/resumes/{resume_id}/extract-text` 提取原文，最终调用 `POST /api/v2/candidates/from-resume` 在单个数据库事务内创建 Candidate 并绑定 Resume。
- 上传控件只接受 PDF、DOCX、TXT，前端先执行 10 MiB 大小和扩展名提示性校验，后端继续执行权威的文件内容、MIME、大小、路径和事务校验。页面展示上传中、提取中、成功或失败状态及服务端失败原因；提取失败可重试，也允许 HR 保留手填内容并确认绑定原文件。
- 页面提供只读原文预览，但没有把原文假装成结构化识别结果。当前不会自动改写姓名、联系方式或经历字段；后续结构化识别必须单独定义草稿契约，并遵守“只填空字段、不覆盖 HR 已填内容”。
- Resume 一旦安全接收成功，页面不提供只删本地状态的“移除文件”操作，避免数据库中已经存在待绑定 Resume 却让用户误以为文件被删除；离开页面时该记录仍如实保留为“待确认候选人”，后续孤立文件/待确认记录处置需作为独立模块实现。
- 已新增独立响应式样式：桌面端为主表单加粘性简历侧栏，中窄屏自动改为单列；阶段 3 顶部标题会把该路由显示为“新增候选人”。未修改旧版页面样式和路由。
- 前端生产构建通过，共转换 3918 个模块；入口 JavaScript 为 264.15 kB（gzip 89.81 kB），新页面独立块为 16.19 kB（gzip 5.38 kB），最大页面块为 422.01 kB（gzip 116.50 kB），没有 Vite 500 kB 大块警告。后端全量 249 项 `unittest` 继续全部通过；`git diff --check` 通过，仅有既有换行符提示。
- 真实 Vite 代理 + FastAPI + PostgreSQL + 私有临时目录验证通过：`/stage3/candidates/new` 返回 HTTP 200；岗位 ID 18 下上传生成待绑定 Resume ID 31，TXT 原文提取并保存 76 个字符，最终确认生成 Candidate ID 63，教育/工作/项目经历各 1 条且 Resume 成功绑定；重复确认返回 `409`，没有新增第二名候选人。文件实际写入临时目录的 `v2/resumes/2026/08/<UUID>.txt`。
- 上述临时 Job、Candidate、Resume、三类经历、输入文件、私有存储目录及日志均已精确清理，验证进程均已停止。当前没有可用的内置浏览器实例，因此本步不声称完成点击或截图视觉验收；页面已通过 TypeScript/生产构建和真实 HTTP 代理数据流验证。
- 本步没有修改后端 Model、Schema、Service、API、Alembic、TXT/PDF/DOCX 提取器、旧 SQLite、旧 `/api/resume/upload` 或 `backend/uploads/`，也没有调用 OCR、LLM、LangGraph、AI 初筛或报告生成。

### 阶段 4 第九小步进度：PDF 视觉阅读顺序修复

- 真实页面验收发现 Resume ID 32 的文字虽然完整，但当前 PyPDF2 直接沿用 PDF 内容流顺序，导致“综合评价”正文出现在“教育背景/技能证书/项目经历/综合评价”标题之前；这类 PDF 的内部文字对象保存顺序不等于页面视觉顺序，不能继续把内容流顺序当作阅读顺序。
- 已在 `backend/requirements.txt` 固定增加 `pdfplumber==0.11.10`。该依赖使用 MIT 许可证，适合读取机器生成 PDF 中字符、词和页面坐标；不提供 OCR，扫描件边界保持不变。
- `ResumePdfExtractor` 继续使用 PyPDF2 完成损坏、加密、页数和 100 页上限检查；文字提取改由 pdfplumber 按页面坐标排序，显式禁用内容流顺序，并保持原页码顺序、空白页跳过、1,000,000 字符上限、低质量检测和稳定错误文案。
- 已用 pdfplumber/PDFium 把真实 PDF 渲染为图片并检查页面布局；临时 PNG 和浏览器失败时生成的空白截图均已删除，不提交或保留包含候选人隐私的测试产物。
- 真实样本只读提取后四个主要区块位置恢复为 `教育背景=60 < 技能证书=173 < 项目经历=398 < 综合评价=1915`，总原文 2,063 字符；标题和正文顺序与视觉页面一致。顶部姓名、地点等横向信息仍按实际坐标排序，不承诺把所有复杂双栏 PDF 自动还原为唯一的语义阅读顺序。
- 本步新增 2 项隔离测试，专门覆盖“内部内容流先保存第二部分，但视觉位置第一部分在上”和“同一视觉行内部先保存右侧文字”两种错序；PDF 提取器 16 项、PDF/状态 Service/Resume API 定向 57 项全部通过，后端全量回归从 249 增至 251 项全部通过。
- 真实 FastAPI + PostgreSQL + 私有临时目录验证通过：真实 PDF 上传生成 Resume ID 35，文件写入临时目录的 `v2/resumes/2026/08/<UUID>.pdf`，提取保存 2,063 字符且四区块顺序断言成功；伪造 PDF 返回 `400`；删除临时原文件后提取返回 `422` 并保存 `failed + 原始简历文件不存在`；真实事务强制 commit 失败后 Resume 回滚为 `uploaded` 且 `raw_text` 为空。
- 验证开始和清理后的 Resume 总数均为 1，只保留用户已创建的 Resume ID 32/Candidate ID 64；临时 Resume 35 及其他失败场景记录、文件、进程、日志和系统临时目录均已精确清理。已有 Resume 32 的旧 `raw_text` 和 Candidate 64 未被后台改写，因为已解析 Resume 的接口保持幂等；需要重新上传该 PDF 才会在页面看到新版顺序。
- 本步没有新增或修改 API、Model、Schema、Alembic、数据库字段、上传事务、TXT/DOCX、前端、旧 SQLite、旧 `/api/resume/upload` 或 `backend/uploads/`，也没有调用 OCR、LLM、LangGraph、AI 初筛或报告生成。

### 阶段 4 第十小步进度：候选人详情安全查看与下载原始简历

- 已新增 `GET /api/v2/resumes/{resume_id}/file`；默认对 PDF/TXT 返回 `Content-Disposition: inline`，传入 `?download=true` 时返回 `attachment`，DOCX 因浏览器通常无法直接预览而始终返回 `attachment`。响应使用数据库保存的服务端 MIME 和原始展示文件名，中文文件名通过 RFC 5987 `filename*=utf-8''...` 返回。
- 文件响应不会公开或接受客户端磁盘路径。ResumeService 根据 ID读取 Resume，再次通过 `ResumeFileAccess` 校验文件必须位于私有 `V2_STORAGE_DIR/v2/resumes`、不得进入 `.staging`、扩展名必须与服务端 MIME一致、文件必须存在且实际大小等于数据库元数据；未知 MIME返回 `415`，路径越界、缺失或大小变化返回 `422`。
- 响应增加 `Cache-Control: private, no-store` 与 `X-Content-Type-Options: nosniff`，避免浏览器缓存候选人隐私文件和进行 MIME嗅探。项目当前仍没有登录/权限系统，因此本步只能保证私有路径和安全文件读取，不能声称已经实现按 HR账号授权。
- `GET /api/v2/resumes` 新增可选 `candidate_id`过滤；不传参数时原列表行为保持不变。候选人详情页使用过滤结果列出该候选人绑定的全部新版 Resume，展示原文件名、格式、大小和解析状态；PDF/TXT显示“查看、下载”，DOCX显示“下载”。前端不读取或展示 Resume的服务端 `file_path`。
- 对于只有 Candidate历史路径、没有新版 Resume记录的候选人，页面明确提示“没有可安全读取的新版 Resume记录”，不会把旧候选人路径伪装为新版文件；无简历候选人显示未绑定提示。
- 本步新增 11项 Resume Service/API隔离测试，Resume定向测试共46项全部通过；覆盖候选人过滤、私有PDF、中文文件名、同一格式内联/下载、DOCX强制下载、记录不存在、未知MIME、路径穿越、缺失、大小变化和安全下载名。后端全量回归从251增至262项全部通过。
- 前端生产构建通过，共转换3918个模块；入口JavaScript为264.23 kB（gzip 89.84 kB），候选人详情块为13.87 kB（gzip 4.97 kB），最大页面块仍为422.01 kB（gzip 116.50 kB），没有Vite 500 kB大块警告。
- 已通过真实 Vite代理、FastAPI、PostgreSQL和用户现有 Resume ID 32验证：`candidate_id=64`过滤只返回绑定记录；PDF查看和下载均返回200及327,781字节，分别使用 `inline`/`attachment`，服务端 MIME为 `application/pdf`，中文原文件名、`private, no-store`和`nosniff`均正确。
- 真实临时目录验证通过：TXT Resume ID 39内联和下载字节均与源文件一致，DOCX Resume ID 40返回附件且字节一致；删除文件、改变文件大小、伪造 `../outside.pdf`和未知 MIME分别返回422/422/422/415，没有返回文件内容。所有临时记录、输入、私有存储、日志和8002进程均已精确清理，验证前后 Resume总数均为2。
- 当前真实 PostgreSQL保留用户数据：Candidate ID 64绑定 Resume ID 32；用户重新上传但未确认创建候选人的 Resume ID 38保持 `candidate_id=NULL + parsed`，本步没有把它当测试数据删除。内置浏览器没有可连接实例，因此不声称完成按钮点击或截图验收；真实页面、过滤接口和文件响应均已通过HTTP验证。
- 本步没有新增迁移，没有修改 Model/Schema、上传/提取事务、TXT/PDF/DOCX提取器、旧 SQLite、旧 `/api/resume/upload`、旧 `/uploads`或 `backend/uploads/`，也没有调用 OCR、LLM、LangGraph、AI初筛或报告生成。读取接口不写数据库或文件，因此不存在本步新增的数据库回滚或孤立文件场景。

### 阶段 4 第十一小步进度：取消创建时安全放弃未绑定简历

- 新版 `DELETE /api/v2/resumes/{resume_id}` 已收紧为“放弃未绑定 Resume”语义：使用 PostgreSQL `SELECT ... FOR UPDATE` 锁定目标记录，只允许 `candidate_id IS NULL` 的 Resume 删除；已绑定候选人的 Resume 返回 `409`，不存在返回 `404`。旧 `/api/resume/upload`、新版 `/api/v2/resumes/upload` 和新版读取接口继续并存。
- 新增独立 `ResumeFileCleanup`：先通过服务端 MIME、扩展名、大小和私有命名空间校验原文件，再使用同一文件系统内的原子移动把文件送入 `V2_STORAGE_DIR/v2/resumes/.trash/<UUID>.<ext>`。数据库删除提交失败时 rollback 并把文件恢复原位；文件隔离失败时不执行数据库删除；数据库已经提交但最终清除 `.trash` 失败时，实时文件和数据库记录保持已删除状态，私有垃圾文件留给下一小步的清扫器重试。
- `ResumeFileAccess` 已明确拒绝读取 `.trash`，因此待清理文件无法通过查看、下载或提取接口暴露。文件恢复时拒绝覆盖原位置出现的新文件，避免补偿操作造成同名覆盖。
- 新增候选人页已接入主动清理：原文提取成功或失败后均可点击“放弃这份简历”；左上角返回和底部取消会弹出确认框，确认后调用新版 DELETE，成功才离开页面。上传、提取、候选人提交或清理进行中会禁用相关入口，避免异步上传结束后留下未知 Resume。直接关闭浏览器无法可靠等待异步 DELETE，因此页面如实提示超时自动清理将在下一小步实现。
- 本步新增/调整的 Resume 文件清理、Service 和 API 定向测试共 62 项全部通过；后端全量回归从 262 增至 278 项全部通过。覆盖成功隔离/恢复/清除、路径穿越、未知 MIME、文件移动失败、数据库提交失败恢复、恢复失败告警、最终垃圾清除延迟、已绑定冲突、404/409/415/422/500 映射和绝对路径信息隐藏。
- 真实 PostgreSQL `recruitment_assistant` + 系统临时目录验证通过：成功场景测试 Resume 45 删除后数据库行和文件均不存在；测试 Resume 46 强制 PostgreSQL commit 失败后数据库行仍在且文件恢复；Resume 47 强制文件移动失败、Resume 48 制造大小元数据不一致后，数据库和原文件都保持不变。45–48 最终均精确清理，验证后只保留原有用户数据。
- 真实 HTTP + 独立 `tmp/stage4-http-storage` 验证通过：未绑定 Resume 49 删除返回 `204`，数据库和实际文件同时消失；绑定 Candidate 64 的专用 Resume 50 返回 `409` 且数据库和文件保持，解除专用测试绑定后返回 `204` 并清理；不存在 ID 返回 `404`。临时存储最终文件数为 0，测试进程、日志和临时目录均已停止并删除。
- 一次验收曾误连仍运行旧代码的后端，旧版数据库-only DELETE 意外删除 Resume 32 数据库行，但原始 PDF、Candidate 64 和 Candidate 中保存的 1,939 字原文均未丢失。已立即按原 ID 32、Candidate 64、原路径 `v2/resumes/2026/08/c838a5123e734768ab7fa9937414f012.pdf`、327,781 字节、`parsed` 状态及原文恢复；上传/解析时间使用原文件修改时间恢复。最终核对 Resume 32 文件读取返回 `200/327781`，Resume 38 仍为 `candidate_id=NULL + parsed`，两条用户记录都存在。后续删除验收统一使用专用临时 Resume，不再用用户记录测试破坏性边界。
- 前端生产构建通过，共转换 3918 个模块；入口 JavaScript 为 264.24 kB（gzip 89.85 kB），新增候选人页块为 17.16 kB（gzip 5.84 kB），最大块仍为 422.01 kB（gzip 116.50 kB），没有 Vite 500 kB 大块警告。`git diff --check` 通过，仅有既有换行符提示。内置浏览器仍无可连接实例，因此不声称完成确认弹窗的实际点击或截图验收。
- 本步没有新增迁移，没有修改 Resume Model/Schema、上传/提取器、旧版业务、旧 SQLite 或 `backend/uploads/`，也没有调用 OCR、LLM、LangGraph、AI 初筛或报告生成。

### 阶段 4 第十二小步进度：24 小时未绑定 Resume 自动清理

- 新增 `ResumeRetentionService`，默认把 `candidate_id IS NULL` 且 `uploaded_at <= 当前时间 - 24小时` 的 Resume 视为过期。每次先按最早上传时间查询最多 50 个 ID，再逐条使用 `SELECT ... FOR UPDATE SKIP LOCKED` 重新确认“仍未绑定且仍已过期”；候选人绑定事务和清理事务竞争同一行锁，已经绑定、尚未过期、正被其他事务处理或已经删除的记录都会跳过。
- 自动清理复用第十一小步的文件隔离与数据库补偿逻辑，不另写一套删除代码：文件进入 `.trash` 失败时数据库不删除；PostgreSQL delete/commit 失败时 rollback 并把文件恢复原位；单条 Resume 失败会记录失败并继续下一条，不会让整批任务停止。
- `.trash` 文件名从随机 UUID 收紧为 `resume-{resume_id}-{uuid}.{pdf|docx|txt}`。垃圾清扫只识别位于新版私有 `.trash` 根目录、符合严格命名规则且不是符号链接的普通文件；只有 PostgreSQL 已经不存在对应 Resume ID 时才删除，数据库仍有记录时保守保留，避免进程崩溃或数据库回滚后误删唯一可恢复文件。未知名称、嵌套目录和路径越界均忽略或拒绝。
- FastAPI 生命周期已启动轻量异步定时任务：默认启动后先等待 60 分钟，再每 60 分钟执行一批；应用关闭时主动 cancel 并等待任务结束，不遗留后台协程。配置项为 `RESUME_CLEANUP_ENABLED`、`RESUME_UNBOUND_RETENTION_HOURS`、`RESUME_CLEANUP_INTERVAL_MINUTES`、`RESUME_CLEANUP_BATCH_SIZE`，Pydantic 对数值范围进行校验，`.env.example` 和 Docker Compose 已同步透传。
- 由于正式规则默认启用，现有 Resume 38 已超过 24 小时且仍未绑定；正式后端连续运行到第一次定时检查时，它将符合自动清理条件。本步真实验证没有启动正式库的全量定时扫描，而是使用比 Resume 38 更早的专用测试时间和 `batch_size=1`，因此没有删除或改写 Resume 38。
- 本步新增 15 项隔离测试，文件清理、Resume Service、Retention Service、配置和 FastAPI 生命周期定向共 41 项全部通过；后端全量回归从 278 增至 293 项全部通过。覆盖严格垃圾命名/批次/路径校验、锁内过期复核、绑定/新鲜/锁定跳过、单条失败继续、垃圾有无数据库记录分流、目录扫描失败、时区与参数校验、首次等待、循环执行、关闭取消和禁用配置。
- 真实 PostgreSQL `recruitment_assistant` + 系统临时目录验证通过：过期 Resume 51 自动删除后数据库与文件均不存在；Resume 52 强制 PostgreSQL commit 失败后报告失败、数据库行保留且文件恢复；Resume 53 强制文件移动失败后数据库和文件均保留；绑定 Candidate 64 的 Resume 54 被锁内条件跳过；无数据库记录的垃圾文件被清除，有数据库记录的垃圾文件被保留。所有 51–54、辅助记录和临时文件最终精确清理，临时文件数和测试数据库残留均为 0。
- 最终 PostgreSQL 核对仍只保留用户数据：Resume 32 为 `candidate_id=64 + parsed` 且原文件存在，Resume 38 为 `candidate_id=NULL + parsed` 且原文件存在。短时启动后端并显式关闭自动清理后，健康接口返回 `ok`，OpenAPI 确认旧 `/api/resume/upload`、新版 `/api/v2/resumes/upload` 和新版 Resume DELETE 继续并存；进程和日志随后精确清理。`git diff --check` 通过；本步没有修改前端，因此未重复运行前端构建，继续沿用第十一小步已通过的 3918 模块生产构建结果。
- 本步没有新增或修改 API、Model、Schema、Alembic、上传/提取器、旧版业务、旧 SQLite 或 `backend/uploads/`，也没有调用 OCR、LLM、LangGraph、AI 初筛或报告生成。

### 阶段 4 最终人工验收与收尾状态

- 用户已在真实前端页面完成人工操作并反馈测试完成。随后执行只读核对：PostgreSQL 当前保留 Candidate 64、绑定的 Resume 32 和未绑定的 Resume 38；两份数据库文件大小均为 327,781 字节并与实际文件一致，新版私有存储中实时文件 2 个、`.trash` 0 个、`.staging` 0 个，没有孤立测试文件。
- 后端日志没有业务异常；前端日志只有前后端启动先后造成的瞬时 `/api/v2/jobs ECONNREFUSED`，服务就绪后 Vite 代理返回 `200`。本轮人工验收进程以 `RESUME_CLEANUP_ENABLED=false` 启动，因此没有把已超过 24 小时的 Resume 38 当成自动清理对象。
- 阶段 4 至此明确完成：新版安全上传、PDF/DOCX/TXT 原文提取、PDF 视觉顺序优化、待绑定 Resume、候选人单事务确认绑定、原文件查看/下载、主动放弃和 24 小时自动清理均已实现并验证。结构化字段识别、自动填表、LLM 和 LangGraph 不属于阶段 4，尚未实现。

### 阶段 5：大模型简历结构化提取与表单辅助填写（✅ 2026-08-14 已完成）

#### 已明确的需求和阶段边界

- 用户期望的最终前端流程是：“新增候选人”页面既可手动填写，也可上传简历；上传后先复用阶段 4 得到 `Resume.raw_text`，再识别姓名、电话、邮箱、城市、学历、当前公司/职位、教育经历、工作经历、项目经历和技能等结构化字段，自动补充表单，最后由 HR 检查、修改并确认创建候选人。
- 阶段 4 的“解析”准确含义是文件转原文，不等于结构化理解。阶段 5 才负责 `Resume.raw_text -> 结构化候选人草稿`。
- AI 结果必须是“草稿”而不是正式 Candidate：建议先进入 `Resume.parsed_snapshot` 或等价草稿存储；不得直接创建或改写 Candidate、Education、WorkExperience、ProjectExperience。前端只补充空字段，不覆盖 HR 已填写内容；无法确定的字段保持 `null`，禁止编造。
- 性别、年龄即使作为基础资料提取，也不得用于后续岗位匹配、评分或淘汰决策。

#### 已确认的技术决定

- 阶段 5 第一版采用普通 `ResumeStructureService` 和模型 Adapter，不使用 Agent 或 LangGraph，也不把一个 Prompt 包装成 Agent。
- 一次正常识别只调用一次 DeepSeek：完整 `Resume.raw_text -> ResumeParseDraft`。服务超时、限流、返回空内容或校验失败时不自动连续调用；页面展示失败，由 HR 决定是否发起一次新的“重新识别”。
- 使用 DeepSeek JSON Output 约束合法 JSON，但模型响应仍必须通过 `json.loads`、Pydantic 严格 Schema（`extra='forbid'`）和日期、重复项、长度、空记录等业务校验。
- 后端和前端只依赖稳定的 Service/API/草稿契约。未来只有真实去隐私样本证明存在稳定的局部遗漏、局部重试或多步骤编排需求后，才重新评估 LangGraph；当前不为尚未出现的复杂度预先设计。

#### JSON 和数据安全原则

- 不能保证模型每次都返回正确内容，但必须保证错误输出无法进入数据库或自动填表。防线顺序为：DeepSeek JSON Output → JSON 解析 → Pydantic 严格 Schema → 业务校验。
- 非 JSON、合法 JSON 但类型错误、额外字段、日期矛盾或业务规则不通过时，不写入新的成功草稿、不创建 Candidate、不覆盖表单；显示稳定失败原因，保留原文件和 `raw_text`，允许 HR 手填和人工重新识别。
- “合法 JSON”不等于“事实正确”。仍需要求只引用原文、不确定返回 `null`，必要时保存字段证据或警告，并由 HR 最终确认。

#### 草稿、状态和前端合并规则

- 合法结果先保存为版本化 `ResumeParseDraft`，成功草稿进入 `Resume.parsed_snapshot`，不直接创建或改写 Candidate、Education、WorkExperience、ProjectExperience。
- 新增独立的结构化识别状态、错误、开始/完成时间和 Schema 版本，不能复用阶段 4 的文件 `parse_status/parse_error/parsed_at`。
- API 采用 `POST /api/v2/resumes/{resume_id}/structure`。已有成功草稿时默认直接返回，避免重复收费；只有 HR 明确重新识别才调用一次新请求，同一 Resume 正在处理时返回 `409`。
- 前端普通字段只补充空值，不覆盖 HR 已填写内容；经历列表为空时可导入 AI 草稿，已经有人工作记录时不自动覆盖或拼接，展示差异并由 HR 选择。
- 应聘岗位、来源和招聘状态不从简历猜测。性别和年龄只在原文明确出现时提取，且不得用于后续匹配、评分或淘汰。
- 阶段 5 只忠实提取学校名称，不由大模型推断 985/211。后续初筛确有需要时，通过标准化学校名称和可追溯院校目录取得 985/211/双一流标签，再结合岗位要求生成可解释结论，不依赖模型记忆，也不据此自动淘汰。

#### 已确认的实现顺序

1. ✅ 已定义和测试 `ResumeParseDraft` Schema、字段映射、日期/空值/额外字段/去重规则及前端合并契约，未调用 DeepSeek。
2. ✅ 已增加结构化状态数据库字段，并完成 Alembic 隔离数据库往返和正式开发数据库向前升级。
3. ✅ 已实现可替换的 DeepSeek Adapter；自动化测试全部使用 Fake Adapter，不产生真实费用。
4. ✅ 已实现 `ResumeStructureService` 的幂等、并发、失败和旧成功草稿保护，并让阶段 4 清理器跳过有效租约内的识别任务。
5. ✅ 已实现结构化 API、请求/响应契约、稳定异常映射和旧草稿恢复响应。
6. ✅ 已接入新增候选人页面的进度、AI 标记、冲突提示、普通字段辅助填写、三类经历和技能人工确认导入。
7. ✅ 已用真实 PDF、DOCX 简历完成 DeepSeek、FastAPI、PostgreSQL、Vite 页面链路和人工操作验收，用户反馈当前测试无问题。原计划 15～20 份脱敏样本统计评估未执行，转为后续质量增强项，不记录为已完成。

#### 阶段 5 第一小步进度：`ResumeParseDraft` Schema 和业务校验

- 已新增隔离的 `backend/app/schemas/rebuilt/resume_parse.py`，定义 `ResumeBasicInfoDraft`、`ResumeEducationDraft`、`ResumeWorkExperienceDraft`、`ResumeProjectExperienceDraft` 和 `ResumeParseDraft` 五类 Pydantic v2 Schema，并通过 `backend/app/schemas/rebuilt/__init__.py` 统一导出，供后续 Service/API 复用。
- 草稿 Schema 版本固定为 `1.0`；五类 Schema 均使用严格类型和 `extra="forbid"`。所有契约字段都必须出现：无法确定的普通字段使用 `null`，无内容的列表使用 `[]`，列表本身不能为 `null`，未知字段不能静默进入草稿。
- 基本资料长度上限已与现有 `CandidateCreate` 对齐；教育、工作和项目的短字段上限已与现有正式经历 Schema 对齐。由于正式描述字段使用 PostgreSQL `TEXT`，草稿额外设置了明确服务端安全上限：工作/项目描述 10,000 字符，项目成果/自我评价 5,000 字符，避免异常超长模型输出进入后续链路。
- `age` 限制为 `0..120`，`work_years` 限制为 `0..80`；电话保留国际区号、空格、括号、点和连字符等合理格式，但要求 6～15 位数字且总长不超过 20；邮箱保留原值并检查基本 local/domain 边界，不擅自改写联系方式。
- 日期只允许 `YYYY`、`YYYY-MM`，结束时间额外允许 `至今`；月份必须为 `01..12`，`至今` 不能作为开始时间。开始年份晚于结束年份、或同年月精度下开始月份晚于结束月份时拒绝；同年但一侧只有年份时不武断推断月份顺序。
- 完全空白的教育、工作或项目对象采用明确拒绝策略，不静默删除模型返回内容；技能、工作/项目技术栈和证书会去除首尾空白、空项和完全重复项，保持首次出现顺序及原有大小写。
- 教育草稿只包含 `school/degree/major/start_date/end_date`，没有 `is_985/is_211`。字段映射已记录在 `docs/specs/2026-08-12-stage5-resume-draft-field-mapping.md`：应聘岗位、来源、招聘状态没有 AI 映射；证书、自我评价、警告和缺失字段当前保留在草稿；性别和年龄不得用于后续筛选决策。
- 新增 22 项纯 Schema 隔离测试，覆盖完整草稿、大量 `null`、空数组、缺失键、额外字段、错误类型、Schema 版本、年龄/工作年限、日期格式/顺序、`至今`、空经历、列表清理去重、超长字符串、邮箱/电话边界、学校标签边界、统一导出和 JSON Schema 导出；22 项全部通过。
- 后端全量回归从 293 项增至 315 项，315 项全部通过；新增 Schema Python 编译通过，导出的 JSON Schema 确认顶层 `additionalProperties=false`、10 个顶层字段全部必填、教育结构只有 5 个允许字段。
- 本步没有调用 DeepSeek，没有新增或修改 API、Service、Adapter、数据库 Model、Alembic migration、前端或 PostgreSQL 数据，也没有启动正式 FastAPI 生命周期及自动清理任务；Resume 38 未被读取、修改或删除。

#### 阶段 5 第二小步进度：Resume 独立结构化状态及 Alembic 迁移

- 已在新版 `Resume` SQLAlchemy Model 增加 `structure_status`、`structure_error`、`structure_attempt_id`、`structure_started_at`、`structured_at`、`structure_schema_version` 六个字段；它们与阶段 4 的 `parse_status/parse_error/parsed_at` 完全独立。
- `structure_status` 使用 `VARCHAR(30) NOT NULL`，ORM 与 PostgreSQL 默认值均为 `not_started`，并建立独立索引；其余字段按设计允许为空。`structure_attempt_id` 为 36 字符，供后续服务端 UUID 尝试编号使用；两个时间字段使用带时区时间；Schema 版本字段为 20 字符。
- `ResumeRead` 已增加四种合法结构化状态：`not_started/processing/succeeded/failed` 及六个状态字段。通用 `ResumeCreate/ResumeUpdate` 故意不开放这些字段，避免客户端通过普通 CRUD 伪造 AI 处理状态；后续由专用 `ResumeStructureService` 控制写入。
- 已新增 Alembic revision `f5a7c9e2d104_add_resume_structure_state.py`，上游为 `d3f6a8c1b204`。升级只增加六个字段和一个索引；降级只移除本步新增索引和字段，不修改阶段 4 字段、原文、草稿或绑定关系。
- 新增 8 项 Model/Schema/migration 隔离测试，覆盖字段类型、长度、默认值、可空规则、独立索引、读取状态限制、普通 CRUD 写入边界和升级/降级操作范围；Resume API 定向共 44 项全部通过，后端全量回归从 315 项增至 323 项，323 项全部通过。
- Python 编译和 Alembic PostgreSQL 离线 SQL 生成通过；离线 SQL 确认本 revision 只包含六次 `ADD COLUMN` 和一次 `CREATE INDEX`。
- 使用专用临时数据库 `recruitment_assistant_stage5_migration_test` 完成真实 PostgreSQL `upgrade -> downgrade d3f6a8c1b204 -> upgrade`：首次升级后测试 Resume 默认 `not_started`；降级后测试 Resume 及原 `parse_status=parsed` 保持存在，而六个新字段和索引计数均为 0；再次升级后同一既有 Resume 自动恢复六个字段并获得 `not_started`。验证结束后专用数据库已精确删除，存在数量确认为 0。
- 正式开发数据库只执行安全的向前升级，没有执行 downgrade，当前 Alembic head 为 `f5a7c9e2d104`。升级前后 Resume 32 仍绑定 Candidate 64、`parse_status=parsed`、原文和旧快照存在；Resume 38 仍未绑定、`parse_status=parsed`、原文存在。两条记录均只新增 `structure_status=not_started`，其余五个新字段为空。
- `alembic check` 输出 `No new upgrade operations detected`，证明当前 SQLAlchemy Model 与正式 PostgreSQL 表结构一致。本步没有启动 FastAPI，因此 24 小时自动清理任务未运行；没有调用 DeepSeek，没有实现 Adapter、Service、结构化 API或前端。

#### 阶段 5 第三小步进度：DeepSeek Adapter、版本化 Prompt 与稳定异常

- 已新增阶段 5 专用 `DeepSeekResumeStructureAdapter`，通过项目现有 OpenAI 兼容异步客户端发送一次非流式 DeepSeek Chat Completions 请求；请求固定启用 JSON Output、关闭 DeepSeek V4 默认思考模式，并由专用客户端显式设置 `max_retries=0`，保证一次 Adapter 方法调用最多发出一次上游请求。
- 已按 2026-08-13 DeepSeek 官方文档重新核对：OpenAI 格式 Base URL 仍为 `https://api.deepseek.com`，JSON Output 仍使用 `response_format={"type":"json_object"}`；旧 `deepseek-chat` 已在 2026-07-24 进入停用边界，因此阶段 5 独立默认模型使用当前支持 JSON Output、成本更低的 `deepseek-v4-flash`，旧演示系统的 `DEEPSEEK_MODEL` 未改动。
- 已新增版本化 Prompt `resume_structure_v1`，包含完整 `ResumeParseDraft v1` JSON 示例、简历原文不可信数据边界、只引用原文、无法确定返回 `null`/`[]`、不猜岗位/来源/状态/院校标签以及不进行评分淘汰等规则。配置中的 Prompt/Schema 版本必须与代码实际版本一致，漂移时在调用模型前失败。
- Adapter 在本地拒绝空白或超过配置字符上限的原文，不静默截断；返回内部结果只包含原始响应文本、实际模型名、完成原因和可空 token 用量。本步按既定边界不执行 `json.loads` 或 Pydantic 草稿校验，二者留给下一小步 Service。
- 已建立稳定异常：配置、输入、认证、余额/配额、限流、超时、服务不可用、空响应、非正常结束/截断及其他上游错误。异常文案不包含 API Key、简历原文、联系方式或上游响应正文，并抑制可能泄露正文的 SDK 异常上下文。
- 新增 12 项 Prompt、客户端与 Adapter Fake/Mock 隔离测试，另新增 2 项配置测试；与既有配置测试合计定向 16 项全部通过。覆盖单次调用、JSON Output、模型/token参数、非流式、禁用思考模式、SDK 零重试、版本漂移、超长输入零调用、认证/余额/限流/超时/服务错误映射、空内容、空 choices、截断及脱敏边界。
- 后端全量回归从 323 项增至 337 项，337 项全部通过；Python compileall 和 `git diff --check` 通过。首次全量回归因新电脑虚拟环境缺少 `requirements.txt` 已声明的 `pdfplumber==0.11.10` 出现阶段 4 导入错误，补齐该既有依赖后相同全量命令通过；未改动依赖清单。
- 本步没有真实调用 DeepSeek，不产生模型费用；没有启动 FastAPI，因此未触发 24 小时 Resume 自动清理；没有修改数据库、Model、Schema、Alembic、Resume 状态流转、Service、API、前端、Candidate 创建或阶段 4 自动清理逻辑。Fake 测试能证明请求构造、单次调用和异常边界，不能证明真实 API 连通性或简历提取质量。

#### 阶段 5 第四小步进度：`ResumeStructureService` 与并发保护

- 已新增 `backend/app/services/rebuilt/resume_structure_service.py`，把“读取原文、判断缓存、占用任务、调用 Adapter、校验草稿、保存结果”收口到业务层；本步没有创建 API 或修改前端。
- 默认识别会复用版本、状态和 attempt ID 均有效的旧成功草稿，不再调用 Adapter；`force=true` 才开启新识别。重新识别失败只更新失败状态和稳定错误，保留上一次成功的 `parsed_snapshot`、`structured_at` 和 Schema 版本。
- 使用两段 `SELECT ... FOR UPDATE` 短事务：第一段写入 `processing + attempt ID + started_at` 后立即提交，等待模型期间不占用数据库事务；第二段保存前再次锁行并核对 attempt ID，过期响应不能覆盖新任务。
- 处理租约默认为 180 秒。租约内重复请求返回冲突，租约过期后允许新任务接管；阶段 4 的主动/自动清理同时跳过租约内 `processing` Resume，超过租约后恢复原有 24 小时清理规则。
- Service 在调用前检查功能开关、Prompt/Schema 版本、文件解析状态、非空原文和最大字符数；响应依次通过 `json.loads` 和严格 `ResumeParseDraft` 校验。快照由服务端包装草稿、模型、版本、时间、字符/token 数和 attempt ID，客户端或模型不能伪造这些元数据。
- 新增 19 项 Service 测试，并补充清理器、Resume Service 和应用生命周期测试。47 项相关测试全部通过；后端全量回归从 337 项增至 356 项，356 项全部通过，`compileall` 和 `git diff --check` 通过。
- 当前电脑的 PostgreSQL 数据卷最初停留在旧 revision `bbd627449743`，已只执行安全向前升级到 `f5a7c9e2d104 (head)`，`alembic check` 无待生成操作；未在该数据库执行 downgrade。
- 已用 Fake Adapter 在真实 PostgreSQL 完成“临时 Resume 入库 → 第一次结构化保存 → 第二次命中缓存且 Adapter 总计只调用一次 → 精确清理”闭环，输出 `POSTGRES_SERVICE_OK`，验证记录残留为 0。该验证证明 Service 与 PostgreSQL 的真实写入和缓存闭环，不证明真实 DeepSeek 连通性、提取质量或 HTTP API 行为。
- 已进一步用两个真实 PostgreSQL 会话模拟并发接管：旧任务先占用并等待，新任务在租约过期后接管成功，旧结果返回时因数据库最新 attempt ID 不匹配而被拒绝；最终快照只保留新任务结果，输出 `POSTGRES_CONCURRENCY_OK`，验证记录残留为 0。

#### 阶段 5 第五小步进度：结构化 API 与稳定异常映射

- 已新增隔离的 `ResumeStructureRequest` 和 `ResumeStructureResponse`，客户端只允许提交 `force`；未知字段会被拒绝，响应只公开前端需要的状态、缓存标记、旧草稿标记和严格草稿，不公开模型调用 metadata。
- 已在新版 Resume Router 增加 `POST /api/v2/resumes/{resume_id}/structure` 并复用现有 `ResumeStructureService`。`force=false` 默认复用成功草稿，`force=true` 才表示 HR 明确重新识别；API 层没有重复实现缓存、并发、事务或模型调用逻辑。
- 已按异常类型稳定映射 HTTP 状态：不存在 `404`，原文尚未准备好或正在处理 `409`，本地输入超限 `422`，限流 `429`，空响应/截断/非法草稿 `502`，功能、配置、认证、余额或服务不可用 `503`，超时 `504`，脱敏后的未预期错误 `500`。为避免依赖中文文案判断状态码，Service 单独增加输入超限异常。
- `force=true` 重识别失败时，API 会只读恢复仍有效的旧草稿，在错误响应中同时返回最近失败状态、稳定错误和 `has_previous_draft=true`；旧草稿查询自身失败时降级为安全错误，不暴露数据库连接或内部路径。
- 新增 12 项 API/Service 自动化测试；结构化 API 与 Service 定向 67 项全部通过，后端全量回归从 356 项增至 368 项全部通过。OpenAPI 检查确认正式路由只挂载一次，且请求/成功响应分别引用正确 Schema，输出 `MOUNTED_STRUCTURE_API_OK`；Python `compileall` 和 `git diff --check` 通过。
- 已通过正式 `app.main:app`、Fake Adapter 和真实 PostgreSQL 完成“临时 Resume 入库 → 第一次 HTTP 结构化保存 → 第二次 HTTP 请求命中缓存且 Adapter 总计只调用一次 → 精确清理”闭环，输出 `POSTGRES_MOUNTED_STRUCTURE_API_OK` 和 `POSTGRES_MOUNTED_STRUCTURE_API_CLEANUP_OK`。本步没有真实调用 DeepSeek、没有修改前端、Candidate 创建逻辑、Model、Alembic 或数据库表结构；该验证不能证明真实模型连通性、提取质量或前端合并体验。

#### 阶段 5 第六步第一小步进度：前端类型与结构化 API 调用函数

- 已新增 `frontend/src/stage3/types/resumeStructure.ts`，以 TypeScript 类型完整表达后端 `ResumeParseDraft v1`、结构化请求/响应以及“失败但旧草稿可用”的错误详情；字段继续使用后端 JSON 契约的 snake_case，避免在尚未进入表单合并前引入第二套字段映射。
- 已在现有新版 `frontend/src/stage3/services/resumes.ts` 增加 `structureStage3Resume(resumeId, force=false)`，继续复用 `/api/v2` 专用 `v2Http`。默认发送 `{force:false}`，只有显式传入 `true` 才请求重新识别；调用层原样返回后端草稿并向页面透传失败，不在 Service 中自动填表、吞掉异常或覆盖人工内容。
- 在不新增测试依赖的前提下，新增 Vite + Fake Axios Adapter 隔离测试和 npm 脚本；验证真实函数使用 `POST /resumes/{id}/structure`、默认/强制请求体、响应返回与失败透传，输出 `STAGE3_RESUME_STRUCTURE_SERVICE_TEST_OK`。TypeScript 严格检查通过，前端生产构建通过并完成 3918 个模块转换。
- 本小步没有修改页面、样式、表单值、Candidate 创建逻辑、后端、数据库或 DeepSeek，也没有产生模型费用。验证证明前端数据通道可以编译、打包并生成正确请求，不能证明页面状态、字段合并、视觉效果或真实模型质量。

#### 阶段 5 第六步第二小步进度：新增候选人页面识别状态展示

- 新版新增候选人页面在阶段 4 原文提取成功后自动调用现有 `structureStage3Resume`，展示“文件已上传 → 原文已提取 → AI 草稿”的处理轨道，以及首次识别、重新识别、成功、命中缓存、普通失败、`409` 处理中冲突和“最近失败但旧草稿可用”状态。成功后只显示基本信息/教育/工作/项目/技能数量，不把任何 AI 内容写入表单。
- 已新增独立 `resumeStructureState.ts`，把 Axios 错误解析、HTTP 状态和旧草稿恢复从 JSX 中分离，并提供草稿数量统计；旧草稿使用琥珀色提醒，明确不是本次新结果。重新识别必须二次确认，文案说明会产生一次新 AI 请求；识别期间禁止创建候选人、主动删除 Resume 或离开页面，避免异步识别与绑定/清理竞态。
- 结构化请求使用独立 100 秒前端超时，比后端 90 秒模型超时多留返回余量，避免通用 30 秒超时造成“后端仍处理、前端先失败”的假超时；其他新版 API 继续使用原 30 秒默认值。
- 新增 Vite 隔离状态测试，覆盖草稿计数、`409`、普通错误、客户端超时和失败后旧草稿恢复，输出 `STAGE3_RESUME_STRUCTURE_STATE_TEST_OK`；既有请求测试继续输出 `STAGE3_RESUME_STRUCTURE_SERVICE_TEST_OK`。TypeScript 严格检查、`git diff --check` 和前端生产构建通过，构建转换 3919 个模块。
- 本小步未真实调用 DeepSeek，未修改表单值、Candidate 创建、经历列表、后端或数据库。自动化与构建能证明状态解析、互斥操作和打包正确，不能证明真实模型等待过程、提取质量或浏览器视觉效果；当前没有完成浏览器人工视觉验收。

#### 阶段 5 第六步第三小步进度：普通字段只补空值与人工冲突提示

- 已新增独立 `resumeDraftMerge.ts`，只映射姓名、电话、邮箱、性别、年龄、城市、当前公司、当前职位、工作年限和最高学历 10 个普通字段；`undefined/null/空白字符串` 才视为空值，数字 `0` 明确保留。
- AI 草稿成功返回时，页面读取当时最新表单值，只填充空字段；人工已有内容与 AI 不同时保留人工值，在对应字段旁显示“AI 识别到另一结果”和具体 AI 值，HR 可单独点击“采用 AI 结果”。
- AI 自动补充的字段显示轻量“AI 补充”标记；HR 手动修改该字段后标记消失，表示内容已由人工调整。重新识别时继续以最新表单为准，不批量覆盖已有内容。
- 映射表不包含应聘岗位、来源、招聘状态，也不包含教育、工作和项目经历；三类经历本小步没有自动导入、覆盖或拼接。
- 新增 Vite 隔离合并测试，覆盖空值、空白字符串、数字 `0`、相同值、人工冲突、`null` AI 值以及岗位/来源排除边界，输出 `STAGE3_RESUME_DRAFT_MERGE_TEST_OK`；既有结构化请求与状态测试继续通过，TypeScript 严格检查和前端生产构建通过，构建转换 3920 个模块。
- 本小步未修改后端、Schema、Service、Model、PostgreSQL 或 DeepSeek 调用，也没有创建 Candidate；后端全量 368 项回归继续全部通过。自动化测试能证明纯合并规则、类型边界和既有后端契约未回归，不能证明真实 DeepSeek 提取质量或浏览器中的最终视觉与人工操作体验。

#### 阶段 5 第六步第四小步进度：三类经历候选与人工确认导入

- 已新增独立 `resumeExperienceImport.ts`，把 AI 教育、工作和项目草稿转换成现有 `Form.List` 使用的前端表单格式；技术栈数组转换为表单的分隔文本，教育经历明确不写未经标准数据验证的 `is985/is211`。
- 三类经历卡片均新增“AI 识别候选”托盘。对应表单列表为空时，HR 可以明确导入全部或先勾选部分；已有任何人工记录时，导入按钮默认禁用，必须先逐条勾选，不自动覆盖、删除或静默拼接。
- 每条候选使用完整草稿内容生成稳定前端标识。导入后显示“已导入”并禁用重复选择，正式表单记录显示“AI 导入”；HR 删除该记录后会解除标识，允许重新选择导入。
- 前端来源标识 `aiCandidateKey` 只用于页面状态；既有 `buildCandidatePayload` 仍显式构造后端字段，不会把该标识发送给 API 或写入 PostgreSQL。AI 候选只有通过 HR 点击导入才进入可编辑表单，仍需最终点击创建候选人才正式入库。
- 新增 Vite 隔离转换测试，覆盖三类字段映射、稳定标识、技术栈转换、空值和教育院校标签边界，输出 `STAGE3_RESUME_EXPERIENCE_IMPORT_TEST_OK`；四项阶段 5 前端定向测试、TypeScript 严格检查、`git diff --check` 和生产构建全部通过，构建转换 3921 个模块；后端全量 368 项回归继续通过。
- 本小步未调用真实 DeepSeek，未修改后端、Schema、Service、Model 或 PostgreSQL。尝试启动本地 Vite 并使用浏览器检查真实交互，但当前浏览器运行环境没有可用实例，因此浏览器点击、截图和最终视觉验收仍未完成；自动测试和构建不能替代这项人工验收。

#### 阶段 5 第六步第五小步进度：技能候选与未建模内容安全展示

- 已新增独立 `resumeSupplementaryInfo.ts`，把 AI `skills` 转换为带稳定标识的技能候选，并提供“保留人工标签、只合并 HR 已勾选技能、去除空值和完全重复项”的纯函数；大小写不同的技能不会被模糊合并。
- 新增候选人页面已增加正式技能标签表单并接入既有 `Candidate.tags`：人工标签直接保留，AI 技能必须逐项勾选或全选后点击导入；表单已有、待确认和已导入状态分开展示，删除已导入技能后可重新选择。
- `Stage3CandidateCreateInput` 和 `buildCandidatePayload` 已显式发送清理后的 `tags`；证书、自我评价、`warnings`、`missing_fields` 不进入候选人请求，也没有被塞入 `ai_summary`、`parsed_data` 或其他无关字段。
- 草稿侧栏新增只读补充信息区：警告使用醒目提示，证书和自我评价分类展示；为保持 HR 界面简洁，模型返回的 `missing_fields` 只保留在服务端可信 `Resume.parsed_snapshot` 中用于质量评估，不在页面显示。所有可见模型文本都通过 React 普通文本节点渲染，不使用 `dangerouslySetInnerHTML` 或 Markdown/HTML 解释。
- 新增 Vite 隔离测试输出 `STAGE3_RESUME_SUPPLEMENTARY_INFO_TEST_OK`，覆盖技能清理、稳定标识、人工标签保留、显式选中合并、大小写边界、补充信息整理和 Candidate 请求白名单。五项阶段 5 前端定向测试全部通过；TypeScript 严格检查和生产构建通过，共转换 3922 个模块；后端全量 368 项回归通过，`git diff --check` 通过。
- 已启动 PostgreSQL、正式 FastAPI（关闭 lifespan）和 Vite，确认 `/api/v2/jobs` 与 `/stage3/candidates/new` 均返回 HTTP 200，随后精确停止本次临时进程和容器并关闭本次启动的 Docker Desktop。浏览器控制运行时因缺少所需路径无法建立连接，因此本步仍不声称完成点击、截图或最终视觉验收；也未上传简历、创建候选人或调用真实 DeepSeek。

#### 阶段 5 前端交互语义优化：从技术流水线改为业务流程

- 新增候选人页面不再把“AI 草稿”作为主流程名称，统一改为“简历智能识别”；处理轨道改为“文件已上传 → 内容已读取 → 信息识别”，处理中明确说明系统正在整理基本信息、三类经历和技能。
- 识别完成提示改为“简历识别完成，请核对后创建候选人”，保留现有数量摘要、普通字段只补空值、人工冲突提示、三类经历与技能人工确认规则；没有修改 API、Schema、Service、Model、PostgreSQL 或 DeepSeek 调用。
- 原先始终展开的“提取原文预览”改为默认收起的“查看提取文本（核对用）”，并明确原始文字只用于追溯核对，正式表单使用结构化识别结果。
- 新增 `STAGE3_RESUME_INTAKE_UI_COPY_TEST_OK` 界面契约测试；结构化请求、状态、普通字段合并、三类经历、技能/补充信息和界面文案共六项定向测试全部通过，TypeScript 严格检查与 3922 模块生产构建通过，`git diff --check` 通过。
- 正式 Vite 页面和 FastAPI 岗位接口均返回 HTTP 200；浏览器控制技能仍因运行环境缺少所需路径无法连接，因此本步不声称完成点击、截图或最终视觉布局验收。

#### 阶段 5 结构化识别耗时监控

- `ResumeStructureService` 使用单调时钟记录本次请求的总耗时，以及数据准备、模型调用、结果校验、结果保存四个阶段；模型调用耗时包含访问 DeepSeek 的网络等待和模型生成时间。
- 结构化 API 在成功响应中新增可选 `performance` 对象，单位统一为毫秒；该对象只描述当前请求，不写入 `parsed_snapshot` 或数据库，因此不需要新增 migration，也不改变已有草稿格式。
- 命中已保存草稿时只记录缓存查询耗时，`model_ms/validation_ms/persistence_ms` 为 `0`；必须上传新简历或由 HR 确认“重新识别”，才可观察一次真实模型请求的分阶段耗时。
- 新增候选人页面在识别完成卡片中展示总耗时和四阶段明细；缓存命中则明确展示“缓存读取耗时”，避免把缓存速度误认为 AI 识别速度。
- 修复识别结果增长后右侧粘性栏无法查看底部内容：桌面端右栏限制在当前视口内并启用独立纵向滚动，鼠标位于右栏时可查看耗时、补充信息、原文核对和创建按钮；`980px` 以下恢复普通页面流，避免移动端嵌套滚动。
- 后端全量 370 项、前端六项阶段 5 定向测试、TypeScript 严格检查、3922 模块生产构建和 `git diff --check` 均通过；本步没有主动发起真实 DeepSeek 调用，后续由人工测试数据决定具体优化点。

#### 阶段 5 最终人工验收与收口状态

- 用户已在真实页面上传并识别 PDF、DOCX 简历，完成原文核对、DeepSeek 信息识别、普通字段补充、三类经历与技能人工确认以及右侧结果区域滚动检查，并反馈当前测试无问题。
- 一次 DOCX 结构化识别总耗时约 11.96 秒，其中模型调用约 9.99 秒。项目方决定当前接受单份简历约 10～12 秒的响应速度，暂不继续优化 DeepSeek 调用、切换轻量模型或接入 OCR。
- 原计划 15～20 份脱敏样本的字段完整性、格式失败率、token 和费用统计没有执行，已转为后续质量增强项，不记录为已完成，也不阻塞当前 MVP 进入阶段 6。
- 阶段 5 于 2026-08-14 正式完成。后续阶段日常开发只需按 `AGENTS.md` 阅读通用权威文档，不必重复阅读阶段 5 专项设计或交接手册；只有修改简历上传、原文提取、结构化识别、辅助填表或排查相关回归时再读取。

### 阶段 6：结构化岗位管理（已完成）

#### 需求确认与专项设计

- 用户已确认阶段 6 的范围、基础字段、`JobRequirements v1`、草稿/开放完整性、`draft/open/closed` 状态机、开放岗位编辑、关闭后重新开放、安全删除、旧数据迁移、薪资暂缓、API/前端失败语义以及自动化和人工验收标准。
- 已新增并获用户确认专项设计 `docs/specs/2026-08-15-stage6-structured-job-management-design.md`；后续严格按其中第 14 节逐个小步骤开发，出现会改变字段、状态、流程或验收的新问题时先暂停讨论。

#### 第一小步进度：JobRequirements v1 与 Job Schema

- 已在 `backend/app/schemas/rebuilt/job.py` 固定 `JobStatus`、`EmploymentType`、`EducationRequirement` 三组枚举和 `JobRequirementsV1`；Schema 版本为 `1.0`，10 个要求字段全部必须出现，未知字段禁止进入。
- 岗位要求列表已固定数量和单项长度上限，统一去除首尾空白、空项和完全重复项；最低工作年限只接受 `0—80` 严格整数。岗位基础输入已增加地点、用工类型、招聘人数和描述约束，标题会去除首尾空白且不能只含空格。
- `JobCreate` 默认创建 `draft` 和完整空 v1，只允许初始状态 `draft/open`；`JobUpdate` 不允许普通更新状态，拒绝未知字段、空请求、`title=null` 和 `requirements=null`，要求 requirements 更新时提交完整 v1。
- 第一步曾为 migration 前旧 PostgreSQL 数据保留临时读取兼容，并在默认空值时避免向尚无新列的 Model 传参；第二步数据库迁移完成后，两处临时桥均已删除，`JobRead` 已收紧为严格 v1 和三种正式状态。
- 新增 22 项纯 Job Schema 测试，覆盖完整/空 v1、字段缺失和额外字段、版本、类型、长度、数量、列表清理、严格整数、枚举、草稿默认值、空白标题、创建关闭状态、人数边界、未知字段、局部更新和旧数据读取兼容。
- Job Schema、既有 Job Service/API 定向共 41 项测试全部通过；后端全量回归从 370 项增至 392 项，392 项全部通过。验证使用 Mock/Fake 和纯 Schema，不连接正式 PostgreSQL，因此能证明校验契约和现有后端回归稳定，不能证明新数据库列、旧数据迁移、开放完整性 Service 或前端交互已经完成。
- 第一步没有修改 Job Model、Service、API 路由、Alembic migration、PostgreSQL 或前端，没有调用 DeepSeek。

#### 第二小步进度：Job Model 与 Alembic migration

- `backend/app/models/rebuilt/job.py` 已增加 `location`、`employment_type`、`headcount` 和内部旧要求快照 `legacy_requirements`；`requirements` 改为非空，岗位默认状态改为 `draft`，数据库增加合法状态和招聘人数 CHECK。
- 新 migration `c8e1a6f4d205_structure_jobs_for_stage6.py` 会把 `active/open/inactive/closed/未知` 确定性映射到正式状态，把 null、合法 v1、已知旧格式和未知 JSON 转成完整 v1；旧/未知非空 JSON 会完整保存在 `legacy_requirements`，原岗位 ID、标题、description、时间和外键不改写。
- 迁移前真实开发 PostgreSQL 位于 `f5a7c9e2d104`，新版 `jobs` 表为 0 条；旧 SQLite 的 8 条演示岗位未导入、未修改，也未被当成 PostgreSQL 主链路数据。
- 专用临时 PostgreSQL 使用 4 种旧岗位和 1 条 Candidate 外键执行 `upgrade -> downgrade -> upgrade`。验证发现并修复 JSONB 的 Python `None` 被存为 JSON `null` 的差异，最终旧 JSON 可恢复、合法 v1 不被降级覆盖，岗位身份哈希 `1a2a2dad7384853eabd388f76395d0a0` 和外键数量全程不变。
- 开发 PostgreSQL 已只向前升级到 `c8e1a6f4d205`，升级后仍为 0 条岗位；12 列、`requirements NOT NULL`、`draft` 默认值和两条 CHECK 已真实查询确认，`alembic check` 返回无待生成操作。
- 新增 Model/migration 测试后，Schema/Model/migration 定向 32 项、既有 Job Service/API 19 项和后端全量 402 项全部通过；`git diff --check` 通过，仅有仓库既存的 LF/CRLF 提示。
- 本步位于 `Schema -> Model -> PostgreSQL`，没有修改 Job Service、API 路由或前端，没有实现开放校验、状态动作、行锁、安全删除，也没有调用 DeepSeek。

#### 第三小步进度：Job Service 业务规则

- `backend/app/services/rebuilt/job_service.py` 已实现创建并开放前校验、开放岗位合并后编辑校验、`draft -> open`、`open -> closed`、`closed -> open` 三种合法迁移，以及全部非法迁移拒绝。
- 编辑、状态动作和删除均通过 PostgreSQL `SELECT ... FOR UPDATE` 读取最新 Job；开放失败会一次返回全部缺失字段，并在修改 ORM 对象前完成校验，避免失败数据留在 Session 中等待误提交。
- 安全删除只允许无关联的 `draft/closed` 岗位；`open` 岗位必须先关闭，Candidate、Resume、ScreeningResult、Report 任一关联都会阻止删除，并保留四类关联数量。
- 所有预期业务失败、查询失败和提交失败都会 rollback；新增 `JobOpenValidationError`、`InvalidJobStatusTransitionError`、`JobMustBeClosedBeforeDeleteError`、`JobHasReferencesError` 和 `JobReferenceCounts`，供下一小步 API 映射稳定错误码。
- Service 定向 19 项、既有 Job API 回归 11 项和后端全量 413 项测试全部通过；Python 全量语法编译和 `git diff --check` 通过，仅有仓库既存 LF/CRLF 提示。
- 专用真实 PostgreSQL 已验证不完整开放、失败编辑不落库、关闭/重新开放、有关联删除拒绝和双会话行锁等待；验证结束时岗位与候选人均清到 0 条，临时数据库随后删除。
- 本步位于 `Schema -> Service -> Model -> PostgreSQL`；没有新增 API 状态动作或错误映射，没有修改前端，也没有调用 DeepSeek。当前 Service 异常尚不能代表最终 HTTP 响应，必须完成下一小步 API 契约后才可从接口正式验收。

#### 第四小步进度：Job API 与错误契约

- `backend/app/api/jobs.py` 已增加严格单状态筛选 `GET /api/v2/jobs?status=draft|open|closed`，以及 `POST /{id}/open`、`POST /{id}/close`、`POST /{id}/reopen` 三个专用状态动作；普通 PUT 仍不能修改状态。
- Job 不存在统一返回 `404 JOB_NOT_FOUND`；非法迁移、开放岗位删除、有关联删除分别返回设计确认的 `409` code；创建并开放、开放、重新开放或编辑开放岗位不完整时返回 `422 JOB_OPEN_VALIDATION_FAILED` 和全部字段路径。
- 空更新 `{}` 通过只匹配新版 Job PUT 路径的请求校验处理器返回 `422 JOB_UPDATE_EMPTY`；其他字段类型、枚举、长度、未知字段和非法查询状态继续使用 FastAPI 默认 422，不改变项目其他接口的验证格式。
- 所有未预期 Service/数据库异常统一隐藏为 `500 JOB_OPERATION_FAILED`，不会向前端返回数据库地址、SQL、文件路径、环境变量或调用栈。
- 主 FastAPI 应用已安装 Job 空更新处理器；OpenAPI 确认 `/api/v2/jobs` 列表/创建、详情/更新/删除和三个状态动作各挂载一次，operationId 不重复。
- API 定向 16 项、Service/API 联合 34 项和后端全量 418 项测试全部通过；Python 全量语法编译和 `git diff --check` 通过，`ruff` 因项目虚拟环境未安装而未执行，没有为本步临时增加依赖。
- 专用真实 PostgreSQL + FastAPI ASGI 已完成创建草稿、开放失败、空更新、补齐开放、状态筛选、失败编辑不落库、重复开放、关闭、重新开放、两类删除冲突和最终删除；结束时岗位与候选人均为 0 条，临时数据库随后删除。
- 本步位于 `API -> Schema -> Service -> Model -> PostgreSQL`；没有修改前端页面和下游岗位读取，也没有调用 DeepSeek。

#### 第五小步进度：岗位前端真实表单

- `/stage3/jobs` 已从只读骨架升级为真实岗位管理页：HR 可以创建草稿、创建并开放、编辑基础字段与完整 `JobRequirements v1`，并通过专用操作开放、关闭、重新开放和安全删除岗位；状态不再使用普通表单下拉框修改。
- 新版前端 API Service 已固定 `draft/open/closed`、用工类型、学历要求和完整 v1 类型，接入 `POST /jobs`、`PUT /jobs/{id}`、三个状态动作与 DELETE；列表增加草稿统计，并继续兼容展示现有 Candidate 岗位关联数量。
- 表单按基础信息、岗位职责、必备要求、加分与补充四区展示。草稿只由前端要求岗位名称；创建并开放、重新开放和开放岗位编辑由后端统一校验，失败时保留输入、标出全部缺失项并滚动到第一项。
- 关闭、重新开放和删除提供二次确认；关闭明确提示不会删除历史候选人和初筛结果。开放岗位不展示删除入口；有关联删除失败会显示服务端返回的候选人、简历、初筛结果和报告数量。写请求期间禁用关闭和重复操作，有未保存内容时关闭抽屉需要再次确认。
- 新增岗位 Service 与 UI 两项前端测试，失败基线分别捕获了缺少草稿统计/写接口和缺少真实保存操作；实现后两项均通过。阶段 5 既有 6 项前端测试全部回归通过，`tsc && vite build` 成功构建 3922 个模块，`git diff --check` 通过。
- 第一次生产构建因工作区沙箱拒绝 Vite 读取配置目录而失败；在获准的构建环境中使用同一命令重跑后成功，因此这不是代码或 Vite 配置缺陷。本步没有启动真实浏览器，也没有对真实 PostgreSQL 执行页面写入，自动化结果能证明类型、请求映射、关键交互源码和生产打包正确，不能替代第七小步的真实页面与数据库人工验收。
- 本步位于 `前端 -> API`，复用第四小步及其后的 `Schema -> Service -> Model -> PostgreSQL`，没有修改下游初筛、投递、Dashboard 或候选人岗位选择，也没有调用 DeepSeek。

#### 第六小步进度：下游开放岗位读取边界

- 投递骨架 `getStage3ApplicationJobs` 和内部新增候选人 `getStage3CandidateJobs` 现在都直接请求 `GET /api/v2/jobs?status=open`，并在前端再次只接受严格 `status=open`；不再把全部岗位下载到浏览器后兼容过滤 `active`。投递页同时改为读取 `JobRequirements v1.responsibilities` 和 `required_skills`，不再读取旧 `requirements.summary`。
- Dashboard 用独立开放岗位请求计算“开放岗位”数量，不再把旧 `active` 当成新版状态；它仍保留一次全部岗位读取，为历史候选人显示已关闭岗位名称，避免统计收紧后破坏历史展示。
- AI 初筛页把“可选岗位”限制为开放岗位，同时继续读取全部岗位为已有初筛结果补齐历史名称与状态；关闭岗位不会出现在新选择中，但其历史结果仍显示，并明确标记“岗位已关闭”。若刷新后当前筛选岗位已关闭，页面自动回到“全部岗位”。
- 候选人列表、候选人详情、简历和报告等历史展示读取没有被改成只读开放岗位，因此已有候选人关联关闭岗位时仍可显示原岗位名称。阶段 8 才建立真正的公开岗位 API；当前投递页仍是明确标注“不提交”的内部预览骨架。
- 新增 1 项下游读取边界测试，先证明旧实现请求没有 `status=open`，再覆盖四个开放岗位请求、三个历史全岗位请求、v1 职责映射、Dashboard 精确计数、关闭岗位历史候选人名称和历史初筛状态。连同阶段 5 的 6 项及岗位管理 2 项，前端共 9 项测试全部通过；`tsc && vite build` 成功构建 3922 个模块。
- 本步只修改 `前端 -> API` 的读取参数、结果映射和提示，不修改 API、Schema、Service、Model、PostgreSQL，不创建 Application，不运行 AI 初筛，也不调用 DeepSeek。自动测试与构建证明请求边界、历史映射和编译打包正确，不能替代第七小步的真实页面与 PostgreSQL 人工验收。

#### 第七小步验收准备：Windows 一键启动脚本修复

- 已定位 `scripts/start_project.ps1` 在 Docker Desktop 未运行时提前退出的原因：脚本全局使用 `$ErrorActionPreference = "Stop"`，`docker info` 写入标准错误后被 Windows PowerShell 转成终止性的 `NativeCommandError`，因此尚未执行 `$LASTEXITCODE` 判断和自动启动 Docker Desktop 分支。
- 已新增统一原生命令执行与就绪检查：需要展示输出的命令按退出码转换为稳定错误；Docker Engine 和 PostgreSQL 等预期会暂时失败的就绪检查返回布尔值，不再中断等待循环。
- Docker Engine 未就绪时会检查标准 Docker Desktop 安装路径；进程未启动则自动启动，进程已存在则继续等待，最长等待约 120 秒。Docker Desktop 不存在或等待超时会返回明确提示。
- PostgreSQL `pg_isready` 已复用同一安全检查；后端依赖预检已加入 `mammoth`，新电脑缺少 DOCX 文本框解析依赖时会按 `backend/requirements.txt` 自动补齐。
- PowerShell 语法解析、PowerShell `-CheckOnly` 和 `launch/start_project.bat -CheckOnly` 均通过；在 Docker Engine 关闭时正确输出 `Docker engine ready: False` 和“完整启动将自动打开 Docker Desktop”，没有再次出现 `NativeCommandError`。后端依赖检查输出 `True`，Docker Desktop 标准程序路径存在，`git diff --check` 通过。
- 本步只修改启动编排和项目状态文档，没有启动 Docker、容器、PostgreSQL、FastAPI 或 Vite，没有执行 migration 或页面写入。因此当前结果证明脚本可以安全识别“Docker 未运行”并进入后续自动启动路径，不能代替第七小步的真实完整启动、数据库和浏览器人工验收。

#### 第七小步进度：技术集成验收通过，用户已确认阶段完成

- 已通过修复后的 `scripts/start_project.ps1 -NoBrowser` 完成真实完整启动：Docker Desktop、PostgreSQL、Redis、Chroma、FastAPI 和 Vite 均就绪；`/api/health` 成功，`/stage3/jobs` 返回 HTTP 200。当前 `/api/v2/jobs` 及 open/close/reopen 动作均存在于运行中的 OpenAPI。
- Alembic 当前 revision 为 `c8e1a6f4d205 (head)`，自动迁移检查输出 `No new upgrade operations detected`；岗位表保留 8 条旧数据，ID 仍为 1—8，候选人和初筛结果的岗位关联分别为 30、29 条，8 条旧岗位快照及描述均存在，阶段 6 两个 CHECK 约束均存在。
- 后端全量 418 项测试通过；前端 9 项脚本测试全部通过；`npm run build` 成功构建 3922 个模块。结果覆盖 Schema、Service、API、状态机、安全删除、下游开放岗位读取边界和生产编译，但自动化测试不能替代真实页面视觉与点击验收。
- 已在真实 FastAPI + PostgreSQL 上使用隔离的 `S6-Acceptance-*` 数据完成 API 集成验收：不完整草稿开放失败并返回 9 个缺失字段；完整岗位可开放；开放岗位非法编辑会回滚、合法编辑会持久化；关闭后退出开放列表；关闭岗位不完整时无法重新开放，补齐后可重新开放；开放岗位删除返回 `409`；无关联草稿/关闭岗位可删除；Candidate、Resume、ScreeningResult 和 Report 的关联计数都会阻止删除并返回准确数量。
- 验收脚本在 `finally` 中清理全部隔离数据；验收前后 Candidate、Job、Resume、ScreeningResult、Report 计数完全一致，数据库中没有残留 `S6-Acceptance-*` 记录。详细证据见 `docs/handoff/2026-08-17-stage6-acceptance.md`。
- `/stage3/jobs`、`/stage3/screening`、`/stage3/apply` 和 `/stage3/candidates/new` 均可访问，但受控浏览器运行时没有任何可用浏览器实例，因此本次没有执行真实点击、刷新后的视觉确认、1440 像素桌面截图或严格 390 像素窄屏验收。HTTP 200 和源码测试不冒充这部分人工验收。

#### 下一小步恢复起点

- 当前分支为 `1lcj`。阶段 5 已形成本地提交 `3e832fa`；新对话仍必须先检查 `git status`、`git log` 和 `git diff`，严禁 reset、clean、checkout 覆盖或丢弃现有修改。
- 用户已同意将 `docs/specs/2026-08-14-post-stage5-product-roadmap.md` 作为当前方向基线；该路线允许在每个阶段的业务讨论后继续修订。
- 阶段 6 的自动化、真实 PostgreSQL 和真实 API 技术集成验收已经通过；用户于 2026-08-17 明确确认阶段 6 已完成，阶段 7 前置门禁据此关闭。此前 Codex 受控浏览器没有可用实例的事实仍保留在上方记录中，本次用户确认不伪装成新增的 Codex 截图证据。
- 阶段 6 由 HR 直接填写结构化岗位表单，不把 AI 解析 JD 作为必经步骤，也不在本阶段调用 DeepSeek。综合 Agent 后续可以按 HR 明确要求生成 JD 草稿，并在 HR 确认后保存。
- 阶段 6 业务方案、专项设计、技术集成验收和用户最终确认均已完成，已允许进入阶段 7。
- 阶段 7 小步骤 1—8、Rubric 修订小步骤 5A，以及步骤 9 的后端支撑契约、前端类型/API 调用层、Application 工作队列、单人评分、同岗位最多 5 人批量评分、评分详情、逐项证据和评分历史交互已完成。当前已具备 Application、HR 决策后端能力、版本化岗位 Rubric、确定性规则、脱敏候选人输入、DeepSeek 逐项语义评价、单 Application 正式评分、同岗位最多 5 项的批量 API，以及可查看真实状态、安全发起评分并追溯证据和历史的初筛中心；下一步只做强制重跑确认，暂不进入 HR 决策前端交互。
- 后续路线暂定为：阶段 7 Application 与 AI 初筛底座；阶段 8 公开投递和自动初筛；阶段 9 面试、Offer、录取和报告；阶段 10 首页综合 Agent；阶段 11 知识库 RAG 与语义搜索；阶段 12 质量、权限、部署和交付。
- 已新增 `docs/research/2026-08-15-github-recruiting-project-comparison.md`，对比 Reqcore、SAP Recruiting Agent、HackerRank Hiring Agent、Resume Screening RAG Pipeline 和 MCP Resume Screening，记录当前差距、借鉴原因和明确不借鉴项。
- Reqcore 只用于校准 Application、招聘 Pipeline、公开/后台接口、私有简历和数据保留；不切换其 Nuxt/Vue 技术栈，不直接复制 AGPL 代码，也不提前建设多租户和计费。
- 初筛借鉴 HackerRank Hiring Agent 的 Rubric、逐项证据、加分/扣分、版本、缓存和公平性约束，但不增加 PDF 转 Markdown，不照搬每个章节一次模型调用或默认 GitHub 评价。
- 阶段 10 借鉴 SAP Recruiting Agent 的职责分工，固定方向为 `Agent -> Tool -> Service -> PostgreSQL/Chroma`；Tools 必须强类型、可测试、可授权和可审计，MCP 仅作为未来外部调用适配，不是当前 MVP 必选项。
- 阶段 11 使用 `Resume.raw_text` 和 `Resume.parsed_snapshot` 生成带来源元数据的检索片段，支持查询分类、结构化过滤、Small-to-Big、去重重排和引用；RAG 负责召回，不替代正式初筛评分，也不生成 `.md` 文件。

### 阶段 7：Application 与 AI 初筛底座（进行中：步骤 9 批量评分交互已完成）

#### 已确认的业务边界

- `Candidate` 表示人员，`Application` 表示其对一个具体岗位的一次申请；同一人员可以有多个岗位申请，每个申请独立评分、独立决策、独立保留历史。
- 候选人页面按“HR 已通过的 Application”展示，不把 AI 完成评分等同于候选人通过；同一人员的不同岗位申请可以分别出现，人员详情聚合其全部申请。
- 候选人页面“新增候选人”是 HR 直通入口，确认后立即形成 `passed/screening_passed` 的 Application，但仍必须自动执行 AI 岗位匹配；AI 结果不能撤销 HR 已作出的通过决定。
- AI 初筛中心“录入新申请”创建 `pending` Application，评分结果只供 HR 参考；只有 HR 明确通过后才进入候选人页面。阶段 7 同时实现通过、备选、淘汰、决定反转和误录作废，阶段 9 不再承担首次初筛决定。
- 所有新 Application 都必须选择开放岗位、绑定当前 Resume，并填写姓名、手机号和邮箱；手机号或邮箱缺少任意一项都拒绝正式创建。手机号与邮箱共同命中同一 Candidate 才自动复用，冲突时进入人工处理，复用不会静默覆盖原资料。
- 同一 Candidate 与同一 Job 同时只允许一个未结束 Application；上一条结束后可重新申请。关闭岗位不允许新申请或新评分，但已开始的评分可按已捕获快照完成，历史流程仍可查看和推进。

#### 已确认的 AI 与评分边界

- 阶段 7 是固定 AI 工作流，由可测试的 Service 编排确定性规则与 DeepSeek 语义判断，不使用 LangGraph；LangGraph 留到阶段 10 综合 Agent 的意图路由、工具选择、确认中断和多步骤恢复。
- 默认五维权重仍为硬性/必备条件 40、经验与职责 25、项目/成果/深度 20、加分项 10、关键词/补充要求 5，作为稳定外框；HR 继续只能在受限区间内调整且总和必须为 100。
- 新方案内置 `standard/technical/non_technical` 模板，并允许 HR 主动让 DeepSeek 根据结构化岗位要求和 JD 默认生成 5—8 个岗位专用语义评分项，简单/复杂岗位允许 4—10 个。Python 确定性规则不计入该数量；生成结果只是一份 draft，必须由 HR 确认发布；岗位创建自动获得 standard 默认 Rubric，不依赖模型成功。
- 候选人语义评分合同改为逐项 `0—10/unknown`，并返回证据、原因、置信度、优势和缺口；固定 `full/strong/partial/weak/none` 六档只属于已完成步骤 5 的历史实现，不再作为最终合同。Python 继续负责确定性规则、五维加权、证据覆盖率和推荐上限。
- 推荐等级为 85—100 `strong_recommend`、70—84 `recommend`、50—69 `review_required`、0—49 `low_match`；存在硬性失败、硬性 unknown 或证据覆盖率低于 60% 时，推荐上限为 `review_required`，但绝不自动淘汰。
- 每次评分生成不可变 ScreeningResult，保存输入快照、指纹、证据和规则/Prompt/模型/Rubric/岗位版本；失败重跑保留上一次成功结果。首次评分在 Application 可靠保存后自动触发，后续重试和重评由 HR 手动触发。
- 阶段 7 只支持同一开放岗位最多 5 份的小批量评分，单份失败互不影响；阶段 8 才接入公开投递、Redis 持久化队列、Worker 和更大批量自动处理。

#### 已确认的质量与开发门禁

- 使用 20 份脱敏样本覆盖高匹配 4、中匹配 4、低匹配 4、硬性失败 3、信息未知 3、资料冲突 2；敏感信息隔离率和确定性规则正确率必须 100%，Schema 成功率至少 95%，证据可定位率至少 90%，推荐方向与 HR 复核一致率至少 80%，关键事实幻觉为 0。
- 完成 Schema、Model/migration、Application Service/API、HR 决策、Rubric、DeepSeek Adapter、ScreeningService、小批量、前端、旧数据迁移和综合验收共 12 个小步骤；每次只推进一个可理解、可验证的小步骤。
- 阶段 6 已获用户最终确认；阶段 7 Application/状态和 Rubric 业务门禁继续有效。用户已理解步骤 8 的范围并确认开始步骤 9；步骤 9 的后端支撑契约、前端类型/API 调用层、Application 工作队列、单人/小批量评分，以及评分详情、逐项证据与运行历史交互均已完成。下一段只做强制重跑确认，暂不进入 HR 决策交互。

#### 小步骤 1：Application、StageHistory 与 Rubric Schema（已完成）

- 新增 `backend/app/schemas/rebuilt/application.py`：固定 Application 来源、生命周期、招聘阶段、AI 状态和 HR 决策枚举；定义内部录入、持久化输入、读取响应和评分重跑请求合同。
- 内部录入请求强制姓名、手机号、邮箱、开放岗位 ID 和当前 Resume ID；手机号去除空格、短横线和括号差异，邮箱去除首尾空白并转小写。`hr_direct` 必须明确确认人工通过，`hr_screening` 禁止伪装为已通过。
- 新增 `backend/app/schemas/rebuilt/stage_history.py`：固定岗位相关的通过、备选、淘汰、决定反转和作废原因；人工覆盖必须写说明，淘汰和作废必须提交严格布尔二次确认；StageHistory 请求/响应采用固定阶段、决策、操作者和原因枚举。
- 新增 `backend/app/schemas/rebuilt/screening_rubric.py`：固定版本化 Rubric 合同、默认 40/25/20/10/5、五维可调范围、整数与总和 100 校验，并定义“提交新权重”和“恢复默认”二选一的更新请求。
- 新增 27 项阶段 7 纯 Schema 单元测试；阶段 7 定向测试 27/27 通过，包含既有阶段 5/6 Schema 的回归测试 71/71 通过，后端全量测试 445/445 通过，`compileall`、导入冒烟检查和 `git diff --check` 通过。
- 本步只位于 `前端 -> API -> Schema` 链路的 Schema 边界，未新增 API、Service、Model 或 PostgreSQL 表，未执行 migration，也未调用 DeepSeek。测试证明非法输入会在进入业务层前被拒绝，不能证明数据库状态机、并发、事务或 AI 评分已经可用。
- 用户理解并确认后已进入小步骤 2。

#### 小步骤 2：Model 与 Alembic migration（已完成）

- 新增 `Application`、`StageHistory`、`JobScreeningRubric` SQLAlchemy Model，并在 Candidate、Job、Resume、ScreeningResult 上建立明确的双向关系；SQLAlchemy 全部 mapper 配置检查通过。
- `applications` 使用数据库 CHECK 固定来源、生命周期、招聘阶段、AI 状态和 HR 决策；使用 PostgreSQL 部分唯一索引保证同一 Candidate 与 Job 同时最多一个 active Application；非 legacy Application 必须绑定当前 Resume。
- `job_screening_rubrics` 保存五个独立权重、四类规则版本、版本号和变更审计；数据库约束再次保证各项范围、总和 100、同一 Job 版本唯一且最多一个当前 Rubric。
- `stage_histories` 保存阶段与 HR 决策前后值、固定原因、操作者、关联评分和人工覆盖标记，表结构只提供追加记录所需字段，不提供普通更新时间字段。
- 扩展 `screening_results`：增加 Application/Resume 关联、attempt、执行状态、输入指纹、证据覆盖率、硬性检查、维度分数、证据与输入快照、规则/Prompt/模型版本、稳定错误、耗时/token/费用、重跑、outdated 和操作者字段；移除旧 `candidate_id + job_id` 唯一约束，改为 `application_id + attempt_number` 唯一，并用部分唯一索引限制同一 Application 同时只有一个 `screening` 执行。
- migration `e7b1c9d4a206_add_stage7_application_foundation.py` 正确接在阶段 6 revision `c8e1a6f4d205` 后；升级时为既有岗位补默认 40/25/20/10/5 Rubric。既有 ScreeningResult 保留原 ID、分数与关系，暂时允许 `application_id=NULL`，等待小步骤 11 的正式旧数据迁移，不根据 AI 分数猜测 HR 决策。
- 只读核对正式开发库仍为 `c8e1a6f4d205`，基线仍是 Candidate 30、Job 8、Resume 0、ScreeningResult 29；本步没有升级或写入正式开发库。
- 独立临时 PostgreSQL 已完成 `base -> c8 -> e7 -> c8 -> e7` 往返：三张新表、默认 Rubric、旧结果兼容、多 attempt、当前结果指针、active Application 并发约束、单一运行任务约束和 Rubric 总和约束均通过；`alembic check` 输出 `No new upgrade operations detected`，临时数据库已删除。
- 新增 10 项 Model/migration 测试，后端全量测试 455/455 通过，`compileall` 与 `git diff --check` 通过。
- 本步位于 `Schema -> Service -> Model -> PostgreSQL` 链路中的 Model 和数据库结构层；当时尚未实现 Application Service/API，尚未向正式开发库执行 migration，也未修改前端或调用 DeepSeek。用户理解并确认后已进入小步骤 3。

#### 小步骤 3：Application Service 与内部录入 API（已完成）

- 新增 `ApplicationIntakeService`，把开放岗位检查、当前 Resume 锁定、Candidate 安全识别或创建、Resume 绑定、Application 创建和首条 StageHistory 写入放在同一个数据库事务中；任一环节失败都会 rollback，不留下“有人但没申请”或“简历绑了一半”的中间状态。
- 手机号与邮箱共同且唯一命中同一 Candidate 时复用；只命中一项、两项分别命中不同人员、指定 Candidate 与联系方式不一致时返回稳定冲突。仅姓名相同不会自动合并，只在成功响应中返回疑似重复 ID 供后续人工提示。
- 同一 Candidate 与 Job 已有 active Application 时不重复创建，API 返回原记录并以 `existing_application_reused=true` 明确说明；PostgreSQL 部分唯一索引继续作为最后一道并发保护。
- 新增 `POST /api/v2/applications/intake`：新建返回 201，幂等复用返回 200；缺少联系方式或 Resume、岗位未开放、Resume 归属冲突和身份冲突使用稳定错误码，未知异常隐藏数据库细节。Application 的校验异常处理会委托给既有 Job 处理器，未改变旧入口的 422 合同。
- `hr_screening` 固定创建 `active/applied/not_started/pending` 和 `application_created` 历史；`hr_direct` 需要明确人工确认，固定创建 `active/screening_passed/not_started/passed` 和 `hr_direct_entry` 历史。本步只建立申请事实，不触发 DeepSeek 或 AI 评分。
- 新增 8 项 Service、6 项 API 及 2 项 Schema 增量测试；步骤 3 定向相关测试 34/34、后端全量测试 471/471、`compileall` 和 `git diff --check` 通过。
- 独立临时 PostgreSQL 真实并发验证中，两次相同提交得到同一 Application，结果为一条 Candidate、一条 Application、一条 StageHistory；联系方式冲突和故意制造的数据库约束失败均完整回滚，HR 直通初始状态正确；`alembic check` 无漂移，临时数据库已删除。
- 正式开发库仍停留在阶段 6 revision `c8e1a6f4d205`，本步没有升级或写入正式库，也没有修改前端。用户理解并确认后已进入小步骤 4。

#### 小步骤 4：Application 状态、HR 决策与历史（已完成）

- 新增 `ApplicationDecisionService`，实现 pass、backup、reject、undo-rejection 和 void 五种操作，并使用 `SELECT ... FOR UPDATE` 锁定 Application 后校验最新状态，避免并发请求静默覆盖。
- HR 初筛申请只有在 AI 状态进入 `completed/blocked/failed` 且招聘阶段进入 `hr_review` 后才能作决定；`screening` 期间禁止决策和作废。通过、备选、淘汰、撤销及作废均拒绝非法状态跳转。
- 通过固定落到 `active/screening_passed/passed`，备选固定落到 `active/backup/backup`，淘汰固定落到 `ended/rejected/rejected`；撤销淘汰回到 `active/hr_review/pending`，但同 Candidate/Job 已有其他 active Application 时拒绝恢复；作废只改变生命周期为 `voided`，不伪装成淘汰。
- 每次成功操作都会在同一个事务中更新 Application、追加 StageHistory 并追加 ActivityLog；人工覆盖 AI 建议会明确记录 `overrides_ai_recommendation=true`。审计写入失败时 Application 更新也会完整 rollback。
- 新增 `POST /api/v2/applications/{id}/pass|backup|reject|undo-rejection|void` 与 `GET /api/v2/applications/{id}/history`；不存在返回稳定 `APPLICATION_NOT_FOUND`，非法迁移返回 `INVALID_APPLICATION_TRANSITION`，未知错误不泄露数据库细节。
- 新增 10 项 Service 和 6 项 API 测试；步骤 4 联合定向测试 30/30、后端全量测试 487/487、`compileall` 和 `git diff --check` 通过。
- 独立临时 PostgreSQL 验证中，并发两次“通过”只有一次成功，另一次读取最新状态后拒绝；通过→备选→淘汰→撤销淘汰→作废留下 5 条 ActivityLog 和完整 StageHistory，故意制造审计约束失败后业务状态未改变；`alembic check` 无漂移，临时数据库已删除。
- 本步位于 `API -> Schema -> ApplicationDecisionService -> Application/StageHistory/ActivityLog Model -> PostgreSQL`；没有调用 DeepSeek、没有实现评分、没有修改前端，也没有升级正式开发库。用户理解并确认后已进入小步骤 5。

#### 小步骤 5：Rubric 与确定性评分规则（已完成）

- 新增严格 `screening_rules` Schema 和纯 `ScreeningRuleService`，固定 13 个内部评分子项、五个大维度、`full/strong/partial/weak/none/unknown = 100%/80%/50%/20%/0%/0%` 换算与最终四舍五入规则。
- 实现技能规范化和受控别名（如 Node.js/node、PostgreSQL/postgres、Kubernetes/k8s），明确 Java 不会误匹配 JavaScript；技能清单未被 HR 确认为完整时，缺少必备技能只记为 unknown，不能假设 failed。
- 工作年限使用已确认整数比较；学历只比较大专/本科/硕士/博士层级，不使用学校名称、985/211 或其他声誉信息；必备经历必须提交 passed/failed/unknown 和可核对证据，不用关键词猜测语义结论。
- 岗位未配置的子项不扣分，同一维度内按固定比例重新分配；整个维度不适用时从有效总权重中排除。非 unknown 档位必须提供证据；全部有效项均 unknown 时返回 blocked 和 `overall_score=None`，不制造虚假 0 分。
- 实现证据覆盖率与 `strong_recommend/recommend/review_required/low_match` 阈值；存在硬性 failed、硬性 unknown 或覆盖率低于 60% 时推荐最高为 review_required，但规则结果不修改 HR 决策或招聘阶段。
- 新增 `ScreeningRubricService` 和 `GET/PUT /api/v2/jobs/{id}/screening-rubric`。HR 调整或恢复默认都会保留旧版本、创建新 current 版本并写 ActivityLog；权重越界或总和不为 100 返回稳定 `RUBRIC_WEIGHT_INVALID`。
- 新岗位现在会在同一事务内自动创建版本 1 的默认 40/25/20/10/5 Rubric；无业务引用的草稿/关闭岗位删除时同步清理其内部 Rubric，失败时岗位与 Rubric 一起 rollback。
- 新增 13 项纯规则、6 项 Rubric Service 和 6 项 Rubric API 测试；步骤 5 联合定向测试 69/69、后端全量测试 512/512、`compileall`、`alembic check` 和 `git diff --check` 通过。
- 独立临时 PostgreSQL 验证中，新岗位自动获得版本 1；两个并发调整安全生成版本 2、3 且只有版本 3 为 current；故意制造版本约束失败后版本 3 保持 current；无引用草稿岗位与 Rubric 均可清理，临时数据库已删除。
- 本步位于 `API -> Schema -> ScreeningRubricService/ScreeningRuleService -> JobScreeningRubric/ActivityLog -> PostgreSQL`。它已经能管理评分尺子并进行纯规则计算，但还没有生成真实语义档位、没有调用 DeepSeek、没有保存 ScreeningResult、没有修改前端或升级正式开发库。下一小步是 DeepSeek 语义评价 Adapter。

#### Rubric 方案变更检查点（需求已全部确认，下一步执行小步骤 5A）

- 用户明确选择借鉴 Reqcore 的“预设模板 + AI 根据 JD/岗位生成评分项”思路；本项目保留五维外框、Python 确定性规则、HR 决策边界和不可变版本历史，不直接照搬其全部模型评分方式。
- 新岗位仍自动创建 `standard` 默认 Rubric，不在创建事务中调用 DeepSeek；HR 可预览技术/非技术模板，或主动默认生成 5—8 个岗位专用语义项，简单/复杂岗位允许 4—10 个。Python 确定性规则不计入该数量，语义项不得与确定性规则重复计分。
- 用户确认规则采用两个明确入口：最低年限、最低学历、必备/加分技能和明确关键词在结构化 JobRequirements 表单维护，由 Service 编译为 `字段 + 操作符 + 目标值` 的 Python 规则；Rubric 编辑器允许 HR 手动新增语义项，设置维度、说明和高/中/低分锚点，发布后由 ScreeningPromptBuilder 注入 DeepSeek。Python 不理解 HR 自由文本，大模型不接管明确结构化比较。
- HR 手动语义项与模板/AI 生成项使用相同的 4—10 条总量、公平性、去重、证据和版本约束。新增规则只影响新评分；旧结果保留并标记 outdated，不自动重跑。
- AI 生成结果不得自动生效。HR 审核名称、说明、维度、0—10 分锚点和占比后发布新版本；生成失败、非法输出、偏见项或岗位输入已变化时，当前 Rubric 和岗位保持不变。
- 语义评分由六档改为 `0—10/unknown + confidence/evidence/reason/strengths/gaps`；未配置亮点忽略，学历阶段 7 只比较学历层级，不判断 985/211 或公司院校名单。
- 五维内部由确定性规则与语义项共同分配 100% 占比；系统提供安全初值，AI 可以生成或优化占比并说明理由，但只能进入草稿。空维度按其他有效维度原权重比例重分配，已配置但缺证据必须保持 unknown。
- 影响评分的岗位字段变化会使 Rubric 待重新确认、旧结果 outdated 并暂停新评分；AI 失败、非法输出或生成期间岗位变化不影响当前正式版本。每个岗位最多一个编辑草稿，发布生成不可变新版本，放弃和替换留审计。
- HR 可以让 AI 生成整份评分标准，也可以用 AI 完善手动评分项的说明和高/中/低分锚点；所有结果均须后端校验和 HR 发布。
- 小步骤 5A 的验收覆盖技术/非技术岗位生成、手动项 AI 辅助、重复/偏见拦截、草稿隔离、发布与历史版本、岗位过期、失败不破坏和生成并发变化；先用 Fake Adapter 完整验证，再用少量脱敏岗位验证真实 DeepSeek。
- 该变化会调整 `screening_rubric.py`、JobScreeningRubric Model/migration、Rubric Service/API、固定子项与六档规则测试，并新增模板、RubricGenerationAdapter 和 ScreeningPromptBuilder。当前已完成权威文档对齐，尚未修改上述业务代码；下一步执行小步骤 5A，步骤 6 继续暂停。

#### 小步骤 5A 第一小段：Rubric v2 合同、模板与 Prompt Builder（已完成）

- 已在 `backend/app/schemas/rebuilt/screening_rubric.py` 增加 Rubric 来源、模板、生命周期、评分项来源和固定五维枚举；新增严格语义评分项合同，固定 `max_score=10`、内部占比 1—100、稳定 key、高/中/低分锚点及公平性禁止内容。
- 已明确区分“允许暂时不完整的编辑草稿”和“必须包含 4—10 个语义项的可发布内容”；AI 生成输出固定为 4—10 项、`source=ai_generated`、拒绝额外字段、重复 key、重复名称和非法维度。HR 手动新增只填写名称、维度、说明、占比和三档锚点，不暴露内部 key、source、max_score 或 Prompt。
- 已在 `backend/app/prompts/rebuilt/screening_rubric_templates.py` 新增 `standard/technical/non_technical` 三套后端版本化模板，分别提供 5、6、6 个可从简历核对的语义评分项；模板返回深拷贝，调用方修改草稿不会污染全局模板资产。
- 已新增版本化 `ScreeningRubricPromptBuilder`，分别构建整份 Rubric 生成和单项 AI 辅助消息；岗位输入使用标题、部门、描述和结构化要求白名单，额外传入的候选人手机号等字段不会进入 Prompt。Prompt 明确阻止确定性规则重复评分、公平性禁止项、岗位内容指令注入和非 JSON 输出。
- 新旧 Rubric 合同定向 18 项、全部新版 Schema 82 项，以及既有 ScreeningRule/Rubric Service/API 25 项测试全部通过；相关模块 `compileall` 和 `git diff --check` 通过。
- 本段位于 `Schema/模板/Prompt -> 后续 Adapter/Service` 的合同层，没有修改 JobScreeningRubric Model、Alembic migration、Rubric Service/API、正式 PostgreSQL 或前端，也没有调用真实 DeepSeek。下一段才进入 Model/migration 和草稿/发布持久化能力；小步骤 5A 尚未整体完成，步骤 6 继续暂停。

#### 小步骤 5A 第二小段：Rubric v2 Model 与 migration（已完成）

- `JobScreeningRubric` 已从旧权重版本扩展为 v2 持久化结构，新增 source、template_key、draft/active/archived/abandoned 状态、semantic_items JSONB、job_fingerprint、generation_metadata、确认/放弃审计和更新时间；五维权重、岗位版本号和既有关系继续保留。
- 数据库新增来源、状态、模板、JSON 数组、正式版本 4—10 项和 `status/is_current` 一致性 CHECK；保留“每岗位一个当前 active”部分唯一索引，并新增“每岗位最多一个 draft”部分唯一索引。active 版本不可原地伪装成草稿，archived/abandoned 也不能继续被标成 current。
- 尚未进入正式开发库的 migration `e7b1c9d4a206` 已同步 v2 表结构，并为既有岗位回填自包含的 standard 模板 5 个语义项、active 状态和确认审计；migration 内置模板与运行时代码模板的严格相等测试通过。既有岗位的指纹在正式迁移/重新确认流程中生成，本段不根据旧数据猜测。
- 新岗位创建时仍在同一事务中生成默认 Rubric，但现在会带 standard 模板 5 项和由标题、参与评分的描述及 JobRequirements 计算的 64 位 SHA-256 岗位指纹；旧权重更新兼容逻辑会把旧 current 标为 archived，并保留语义项和岗位指纹。
- Model/migration/Job Service/Rubric Service/API 等定向 60 项首次通过；修复模板放在 Service 包导致的循环导入后，后端全量 523 项测试全部通过，Python `compileall` 通过。Alembic 离线 SQL 被阶段 6 既有 migration 的数据库读取逻辑阻断，因此本段用 migration 操作结构测试验证 e7 声明，尚未把离线输出或真实 PostgreSQL 往返冒充为已通过。
- 本段位于 `Schema -> Model/migration -> PostgreSQL` 的结构层，尚未实现一个草稿的创建/编辑/发布/放弃 Service/API、岗位修改后的暂停评分、AI 生成 Adapter 或前端，也没有升级正式开发库。下一段继续完成 Service/API 和岗位过期事务语义；小步骤 5A 仍未整体完成。

#### 小步骤 5A 第三小段：Rubric 草稿生命周期、发布 API 与岗位过期语义（已完成）

- `ScreeningRubricService` 已实现每岗位单草稿的查询、模板创建、编辑、发布、放弃和替换；草稿永远不是 current，只有 HR 显式发布后才归档旧 active 并把草稿切为新的 active。创建、更新、发布、放弃和重确认均记录 ActivityLog，失败统一 rollback。
- 新增草稿查询、模板草稿创建、草稿更新、发布、放弃和 current 重确认 API；旧的 `PUT /jobs/{job_id}/screening-rubric` 直接生效入口已移除，避免绕过草稿和 HR 发布门禁。不存在、重复草稿、岗位输入过期、发布内容不完整和未知失败分别使用稳定且不泄密的错误码。
- 草稿保存和发布都要求客户端提交岗位指纹，并同时核对草稿生成时指纹与当前岗位指纹；生成或编辑期间岗位标题、描述或结构化要求发生变化时返回 `RUBRIC_STALE`，旧 active 不被破坏。
- 岗位标题、描述或 JobRequirements 变化会在同一岗位更新事务中把 current Rubric 标记为 stale，并把该岗位旧 ScreeningResult 标记为 outdated；部门、地点、人数等不参与评分的字段变化不会误触发。当前 stale 版本必须由 HR 重新确认并产生新 active 版本，后续评分 Service 应拒绝使用 stale current。
- JobScreeningRubric Model 和尚未进入正式库的 `e7b1c9d4a206` migration 已增加 `is_stale/stale_at/stale_reason` 与索引；发布内容仍由严格 Schema 校验 4—10 个语义项、权重、公平性和重复项。
- 本段定向 71 项测试和 64 组子场景通过；后端全量 533 项测试和 261 组子场景通过，`compileall` 与 `git diff --check` 通过。Docker Hub 拉取基础镜像超时，因此没有在本段重复执行真实 PostgreSQL migration 往返；正式开发库仍保持阶段 6 revision，未升级或写入。
- 本段位于 `API -> Schema -> ScreeningRubricService/JobService -> JobScreeningRubric/ScreeningResult/ActivityLog -> PostgreSQL`。尚未实现 AI 生成 Adapter、Fake 生成异常测试、真实 DeepSeek 或前端；下一段接入 RubricGenerationAdapter，小步骤 5A 仍为进行中。

#### 小步骤 5A 第四小段：RubricGenerationAdapter 与 Fake AI 生成闭环（已完成）

- 新增 `DeepSeekRubricGenerationAdapter` 和独立客户端工厂，整份 Rubric 生成与 HR 单项辅助都固定单次非流式 JSON Output 调用、90 秒有界超时、SDK 隐式重试关闭，并把认证、配额、限流、超时、连接、空响应和截断响应转换为不泄露岗位内容或上游响应的稳定错误。
- 新增生成配置、严格请求/响应 Schema 和 `POST /jobs/{job_id}/screening-rubric/generate`、`POST /jobs/{job_id}/screening-rubric/draft/assist-item`。整份生成保存 `ai_generated` 草稿及模型、Prompt/Schema 版本、token 和生成理由；单项辅助只返回已校验的 HR 可编辑字段，不自动修改草稿或正式版本。
- `ScreeningRubricService.generate_draft` 在模型调用前读取岗位快照并主动结束数据库读事务，不在外部网络等待期间持有行锁；模型返回后重新锁定岗位，复核岗位指纹、当前 Rubric 和单草稿约束，全部通过才原子保存草稿与 ActivityLog。
- Fake Adapter 已覆盖成功、已有草稿调用前拒绝、超时、非法 JSON、公平性禁止项、生成期间岗位变化以及单项辅助；任何失败都不会写入新草稿、替换旧草稿或改变当前 active。API 对非法标准、stale 和模型不可用分别返回 `RUBRIC_CRITERIA_INVALID`、`RUBRIC_DRAFT_STALE` 和 `RUBRIC_GENERATION_MODEL_UNAVAILABLE`。
- Adapter/Fake Service/API/Prompt 定向 41 项测试和 38 组子场景通过；后端全量 545 项测试和 269 组子场景通过，`compileall` 与 `git diff --check` 通过。真实 DeepSeek 未调用，正式开发库未升级或写入。
- 本段完成 `Prompt -> Adapter -> ScreeningRubricService -> draft Model` 的 Fake 闭环。小步骤 5A 尚余隔离 PostgreSQL 往返、少量脱敏岗位真实 DeepSeek 验证及最终文档收口；完成前不进入候选人语义评分 Adapter。

#### 小步骤 5A 第五小段：真实 PostgreSQL、真实 DeepSeek 与最终收口（已完成）

- 在独立临时库 `recruitment_assistant_stage7_rubric_test` 首次执行真实 `c8 -> e7` 时发现 migration 把内嵌 JSON 中的 `:10/:50` 误识别为 SQLAlchemy bind 参数；PostgreSQL 事务完整回滚并保持 c8。已改为 `CAST(:semantic_items AS jsonb)` 参数绑定，并增加结构回归断言，避免模型模板内容参与 SQL 字符串拼接。
- 修复后真实完成 `空库 -> c8 -> e7 -> c8 -> e7`。迁移前脱敏岗位 700001 在 e7 自动获得 standard、active、v2、5项语义标准；降级后岗位保留且三张阶段 7 表移除，再升级后默认 Rubric 正确重建。单 active、单 draft、stale 索引和 16 项 Rubric 约束均存在，`alembic check` 输出 `No new upgrade operations detected`。
- 第一次真实 DeepSeek 技术模板验证发现模型受系统 JSON 示例影响返回错误 `template_key`；后端严格校验正确拒绝该结果。生成 Prompt 随即升级为 `rubric_generation_v2`，在用户消息中明确要求返回模板必须与请求严格一致，并新增自动化断言。
- Prompt v2 下真实 DeepSeek `deepseek-v4-flash` 验证通过：脱敏技术岗位生成 6 项、非技术岗位生成 7 项，均在默认 5—8 项范围并通过严格 Schema/公平性校验；单项辅助保留名称、维度和占比并返回合法锚点。本次三次成功调用共 3355 input tokens、2392 output tokens，只使用虚构岗位，不包含候选人或联系方式。
- 最终后端全量 545 项测试和 269 组子场景通过，`compileall`、`git diff --check` 和 migration 4 项定向测试通过。正式开发库只读确认仍为 `c8e1a6f4d205`，没有升级或写入；临时数据库已精确删除，存在计数为 0。
- 小步骤 5A 至此完成：岗位级 Rubric 已具备模板、AI 整份生成、HR 单项辅助、严格校验、草稿/发布/放弃、版本、岗位过期、失败保护、Fake 异常、真实 PostgreSQL 和真实 DeepSeek 证据。下一步进入小步骤 6，只评价候选人材料，不再改变 Rubric 生成合同。

#### 小步骤 6：DeepSeek 候选人语义评价 Adapter（已完成）

- 新增 `backend/app/schemas/rebuilt/screening_evaluation.py`，固定候选人模型输入和 `ScreeningSemanticEvaluation v1` 输出合同。每个已发布语义项按原顺序恰好返回一次，分数只能是严格整数 `0—10` 或 `unknown`；置信度固定为 `low/medium/high`，每项返回 evidence、reason、strengths 和 gaps。数字分必须有证据，`unknown` 必须无证据、置信度为 low 并说明缺少材料；重复、漏项、额外项、越界/浮点/字符串分数和额外字段均拒绝。
- evidence 固定为 `source/locator/quote`，来源只能是 `confirmed_profile/resume_text/structured_resume`。`validate_against` 会核对 Rubric key 的完整顺序，并要求每条 quote 能在对应脱敏来源中逐字定位；模型拼接数组、改写或虚构证据不能进入后续计分。
- 新增纯 `ScreeningInputService`，只输出无真实身份的 `application-*` 引用和岗位相关字段。姓名、手机号、邮箱、性别、年龄、出生/民族/婚姻/地址/证件/照片/个人链接等字段不进入结构化模型输入；原文中的身份标签行、已知身份值、邮箱、手机号、身份证和 URL 在后端确定性移除。学校名称不进入结构化评分材料；脱敏后只剩身份信息时在模型调用前判定材料不足。
- 新增 `ScreeningPromptBuilder` 和 `screening_evaluation_v3`。Prompt 把岗位白名单、4—10 个已发布语义项和三类脱敏候选人来源分区注入，禁止岗位/简历指令注入、未配置亮点、总体分数、推荐等级和 HR 决策。HR 已确认资料优先于原文，原文优先于 AI 结构化快照；数组证据必须逐元素引用，0 分也必须有明确负面证据，无证据必须返回 unknown。
- 新增 `DeepSeekScreeningModelAdapter` 和独立客户端工厂，固定一次非流式 JSON Output、90 秒有界超时、SDK 隐式重试关闭、输入/输出长度上限，并把认证、余额、限流、超时、连接、服务异常、空响应和截断响应映射为不泄露岗位、简历或上游正文的稳定错误。成功结果记录模型、完成原因、耗时、input/output token；部署方配置每百万 token 单价时才计算费用，未配置时明确为 unknown，不伪造为 0。
- 新增步骤 6 Schema/Prompt/Input Service/Adapter 与配置测试；本步新增 21 项测试、Rubric 联合 77 项、后端全量 566 项测试均通过，`compileall` 和 `git diff --check` 通过。测试覆盖 PII 脱敏、只含身份信息阻断、严格分数、unknown、证据定位、公平性、一次调用、输入上限、Prompt/Schema 版本漂移、超时、鉴权、余额、限流、连接、5xx、空响应、截断和可选费用估算。
- 真实 DeepSeek `deepseek-v4-flash` 首次证据充分样本把技能数组拼成新字符串，证据定位校验正确拒绝；Prompt v2 明确逐元素引用后，第二次又发现模型对无材料项返回无证据数字低分，严格 Schema 再次拒绝。Prompt v3 增加机械自检后验证通过：证据充分虚构样本返回 6 项分数 `[8,8,7,8,8,6]`、6 条可定位证据，2047/893 tokens、约 5.4 秒；证据稀疏虚构样本 6 项全部 `unknown + low`、0 条证据，1830/506 tokens、约 3.5 秒。所有样本均为虚构材料，联系方式在调用前自动移除。
- 本步位于 `Schema/ScreeningInputService -> Prompt -> ScreeningModelAdapter -> DeepSeek`，没有新增 API、没有编排确定性规则和语义结果、没有创建或保存 ScreeningResult、没有改变 Application AI 状态、没有修改前端，也没有升级正式开发库。下一步小步骤 7 才实现 `ScreeningService`、输入指纹、首次/重跑、结果版本、失败保留和当前结果切换。

#### 小步骤 7：ScreeningService、结果版本和幂等（已完成）

- 新增 `backend/app/schemas/rebuilt/screening_score.py` 与纯 Python `ScreeningScoreService`。确定性规则和岗位专用语义项在五维内部按建议占比归一化，空维度按其他有效维度重分配；`unknown` 不等于 failed，但降低证据覆盖率。Python 统一计算总分、推荐等级、硬性条件/低覆盖率封顶、优势、风险和待确认问题，DeepSeek 不接管总分。
- 新增事务化 `ScreeningService`。开始时锁定 Application，核对 active、开放岗位、当前 Resume、唯一 active Rubric、stale 和岗位指纹；生成只含脱敏数据的 64 位输入指纹与快照，创建并提交 `screening` attempt 后才调用模型，结束时用短事务写回。支持相同成功指纹复用、二次确认 force 重跑、attempt 递增、同 Application 单运行、输入变化 outdated、新成功切换当前结果和新失败保留旧成功结果；AI 结构化快照不能单独满足最低输入。
- 每条结果保存 Application/Resume/Rubric 绑定、规则/计分/Prompt/Schema/模型版本、脱敏候选人快照、岗位要求与 Rubric 快照、硬性检查、逐项证据、维度分、总分、覆盖率、推荐、耗时、token、可选费用和稳定错误。模型非法输出只保存安全错误，不保存未校验原文；任何结果都不改变 HR 决策。
- 新增可重复执行的 `backend/scripts/validate_screening_service_live.py`。本步新增/扩展 16 项计分、编排与结果不可变保护测试，评分相关 57 项联合测试、后端全量 582 项、`compileall` 和 `git diff --check` 均通过。
- 随机临时 PostgreSQL 从空库迁移到 `e7b1c9d4a206` 后，以完全虚构 Application 完成真实 `deepseek-v4-flash` 链路：首次结果 86 分、证据覆盖率 100%、`strong_recommend`、1793/566 tokens；相同输入第二次复用，真实模型调用仍为 1。修改 Resume 后模拟超时，新 attempt 为 failed，旧成功结果继续作为当前结果并标记 outdated；数据库唯一索引拒绝第二个并发 screening。真实模型另有一次非法输出被严格校验拒绝并安全保存 failed，未放宽 Schema。
- 验证用临时数据库 `recruitment_step7_a0288aed` 已精确删除；正式开发库仍停留在阶段 6 revision，没有升级或写入。本步没有新增批量 API、没有接前端、没有自动改变 HR 决策。下一步小步骤 8 实现同岗位最多 5 份的小批量评分、逐项事务、部分失败、复用和仅重试失败项。

#### 小步骤 8：最多 5 人的小批量评分 API（已完成）

- 新增严格 `ScreeningBatchRunRequest/Response`：一次只能提交 1—5 个不重复 Application，支持普通执行、带二次确认和原因的 force 重跑，以及 `retry_failed_only`；仅重试失败项不能与 force 同时使用。逐项响应固定为 `completed/failed/blocked/reused/skipped`，并返回结果 ID、attempt、是否调用模型、安全错误和批次汇总。
- 新增 `ScreeningBatchService` 与 `POST /api/v2/jobs/{job_id}/screenings/batch`。执行前整体校验岗位存在且 open、全部 Application 存在且属于路径岗位；随后按请求顺序复用步骤 7 的 `ScreeningService`。每项由单人工作流独立提交，单项异常只回滚该项当前事务并继续下一项；相同成功结果复用，正在运行和不允许启动的项安全跳过，批量操作不改变 HR 决策。
- `retry_failed_only=true` 只执行当前 `ai_status=failed` 的 Application，completed、blocked、not_started 和 screening 均不被误重跑。blocked 必须先补资料后再发起普通评分；本步未引入 Redis、后台队列或批量 HR 通过/淘汰。
- 新增 13 项 Schema、Service 和 API 测试；批量/单人评分/岗位 API 联合 37 项与后端全量 595 项测试通过，`compileall`、OpenAPI 路由导入和 `git diff --check` 通过。
- 随机临时 PostgreSQL `recruitment_step8_6f91c2` 从空库迁移到 `e7b1c9d4a206`，使用完全虚构数据和可控模型适配器验证 5 项依次得到 `completed/failed/blocked/reused/completed`；随后仅第 2 个 failed 被重试并完成，数据库审计历史为 `[completed] / [failed, completed] / [blocked] / [completed] / [completed]`，证明前项成功未被后项失败回滚且复用项未新增 attempt。临时库已删除并确认计数为 0，正式开发库仍未升级、未写入；本次未调用真实 DeepSeek，不产生模型费用。
- 本步位于 `前端（尚未接入） -> Batch API -> Batch Schema -> ScreeningBatchService -> ScreeningService -> Model -> PostgreSQL`。下一步小步骤 9 接入 Application 录入、列表、状态、评分详情/历史/证据、批量操作和 HR 决策前端；开始前先向用户解释本步范围并等待确认。

#### 小步骤 9 第一小段：前端所需 Application 查询与单人评分契约（已完成）

- 新增只读 `ApplicationService`，提供 Application 列表和详情；列表支持岗位、招聘阶段、AI 状态、HR 决策和生命周期筛选，并按申请时间与 ID 稳定倒序。
- `GET /api/v2/applications`、`GET /api/v2/applications/{id}`、`POST /api/v2/applications/{id}/screenings` 和 `GET /api/v2/applications/{id}/screenings` 已接入正式 FastAPI 路由。单人评分复用步骤 7 的 `ScreeningService`，记录“本地 HR（未认证）”，不会复制评分逻辑。
- 新版结果响应分为轻量摘要和完整详情：摘要供列表/历史读取 Application、attempt、状态、分数、推荐、覆盖率、错误和 outdated；`GET /api/v2/screening-results/{id}` 对 Application 结果额外返回硬性检查、维度分、证据、待确认问题、脱敏快照、版本、耗时、token 和费用字段。旧 legacy ScreeningResult 继续使用兼容响应，不要求一次迁移全部旧字段。
- 单人评分稳定区分 `APPLICATION_NOT_FOUND`、`SCREENING_ALREADY_RUNNING`、`APPLICATION_RESUME_REQUIRED`、`JOB_NOT_OPEN_FOR_SCREENING`、`RUBRIC_CRITERIA_INVALID`、`RUBRIC_DRAFT_STALE` 和通用不允许/未知失败；响应不回传 Service 私有异常、数据库地址或调用栈。
- 新增 13 项 Schema、Application 查询 Service 与 API 测试；相关 59 项定向测试、后端全量 608 项、全量 Python 编译、正式 OpenAPI 路由检查和 `git diff --check` 通过。正式开发库仍停留在阶段 6 revision，本段未升级 PostgreSQL、未调用真实 DeepSeek、未修改 React 页面。
- 本段位于 `前端（下一段接入） -> API -> Schema -> ApplicationService/ScreeningService -> Model -> PostgreSQL`。它证明页面已有稳定可调用的后端合同，但不能证明前端交互、真实阶段 7 数据库或浏览器视觉效果；下一段只新增前端类型与 API 调用函数。

#### 小步骤 9 第二小段：前端类型与 API 调用层（已完成）

- 新增 `frontend/src/stage3/types/applicationScreening.ts`，用 TypeScript 表达 Application、AI 状态、HR 决策、评分摘要/详情、批量结果、阶段历史和全部写操作输入；前端领域对象统一使用 camelCase，并保留只在网络边界出现的 snake_case 原始响应类型。
- 新增 `frontend/src/stage3/services/applications.ts`，集中封装 Application 录入/查询、单人评分、评分历史/详情、同岗位批量评分、通过/备选/淘汰/撤销/作废和阶段历史调用。Service 负责 URL、查询参数、请求体、字段映射、Decimal 字符串转数值和稳定错误解析，后续页面不需要直接拼接后端路径。
- 新增 1 项阶段 7 前端 Service 测试，覆盖筛选参数、请求方法/路径/载荷、响应映射、证据详情、批量、5 种 HR 动作、阶段历史与错误详情；本项和 9 项既有前端回归测试全部通过。`tsc && vite build` 成功构建 3922 个模块，`git diff --check` 通过。
- 本段位于 `前端页面（下一段接入） -> TypeScript API Service -> FastAPI -> Schema -> Service -> Model -> PostgreSQL`。它证明前端调用契约可编译且请求/映射稳定，但尚不能证明页面交互、真实阶段 7 数据库、浏览器视觉效果或真实 DeepSeek 调用；下一段只建设页面数据读取与 loading/空/失败/blocked/outdated 等状态骨架。

#### 小步骤 9 第三小段：Application 只读工作队列与状态骨架（已完成）

- `/stage3/screening` 已从 legacy ScreeningResult 历史页改为阶段 7 Application 工作队列。新增前端聚合读取同时取得 Application、候选人、全部岗位和新版评分摘要，只把 `current_screening_result_id` 指向的当前结果拼入列表；旧 legacy 结果通过运行时类型守卫排除，不会误当 Application 评分。
- 页面新增可点击的招聘阶段轨道，以及岗位、AI 状态、HR 决策和生命周期筛选；展示候选人/岗位、关闭岗位、AI 状态、当前分数、attempt、推荐方向、HR 决策、未绑定简历、failed、blocked 和 outdated。覆盖首次 loading、API 失败与重试、数据库空状态、筛选无结果和清除筛选；页面明确保持只读，没有提前发起评分或修改 HR 决策。
- 新增 1 项聚合 Service/页面状态测试；与阶段 7 API Service 测试及 9 项既有前端回归合计 11 组全部通过。`tsc && vite build` 成功构建 3923 个模块，`git diff --check` 通过。当前环境没有可连接的受控浏览器实例，因此未完成真实点击、1440 像素桌面和 390 像素窄屏截图验收，源码响应式检查不能冒充视觉验收。
- 本段位于 `React 只读页面 -> 前端聚合 Service/API Service -> FastAPI -> Schema -> Service -> Model -> PostgreSQL`。它证明页面已接入阶段 7 的真实读取合同并能区分关键状态，但正式开发库尚未升级，不能证明真实阶段 7 数据展示、浏览器视觉效果或 DeepSeek 调用；下一段只接入单 Application 评分、运行中保护和完成后的队列刷新。

#### 小步骤 9 第四小段：单 Application 评分交互（已完成）

- 初筛中心每条 Application 已按真实状态显示单人操作：`not_started` 可开始、`failed` 可重新尝试、当前成功结果 outdated 可更新；本地或服务端 `screening`、ended/voided、岗位关闭/未知、缺简历、blocked 和最新成功结果均禁用，并在按钮下直接说明原因。AI 评分结果不会自动改变 HR 决策。
- 页面复用 `runStage7ApplicationScreening` 调用正式单人评分 API。同步 `Set` 守卫在 React 重新渲染前就登记 Application ID，连续双击只允许第一请求进入；不同 Application 仍各自独立。completed/reused、blocked/failed 和 HTTP 稳定错误分别反馈，成功或服务端已运行时重新读取工作队列。
- 新增纯状态策略、同步重复提交守卫、错误指引和页面接线测试；与阶段 7 既有 2 组及阶段 3—5 的 9 组前端回归合计 12 组全部通过。`tsc && vite build` 成功构建 3924 个模块，`git diff --check` 通过。
- 本段位于 `React 单人操作 -> applications.ts -> POST /applications/{id}/screenings -> Schema -> ScreeningService -> Model -> PostgreSQL/DeepSeek`。它证明前端会按状态安全发起一次请求、解释失败并刷新结果，但正式开发库未升级、本次测试没有真实调用 DeepSeek，且当前无受控浏览器实例，不能证明真实数据点击和视觉效果；下一段只接入同岗位选择 1—5 人、批量结果汇总和仅重试失败项。

#### 小步骤 9 第五小段：同岗位最多 5 人批量评分交互（已完成）

- `/app/screening` 已支持按行选择同一岗位的 1—5 个 Application。首个选择会锁定批次岗位；异岗位、第 6 人、非 active、关闭岗位、缺简历、blocked 和正在运行的申请会在前端禁用并解释原因，已有最新成功结果仍允许选择并由后端安全复用。
- 批量操作调用 `runStage7ScreeningBatch`，同步守卫阻止双击产生重复 POST；运行期间锁定筛选器和相关行操作。结果抽屉逐项展示 `completed/failed/blocked/reused/skipped`、attempt 和安全错误信息，汇总各状态数量，并可仅把 failed Application 重新提交。批量评分不会自动通过、备选或淘汰候选人。
- 新增 `screeningBatchAction.ts` 纯策略/同步守卫和 1 组批量 UI 测试；阶段 7 的 4 组与简历、岗位相关 9 组前端回归合计 13 组全部通过。`tsc && vite build` 成功构建 3925 个模块。
- 本段位于 `React 批量交互 -> applications.ts -> POST /jobs/{job_id}/screenings/batch -> Batch Schema -> ScreeningBatchService -> ScreeningService -> Model -> PostgreSQL/DeepSeek`。它证明前端选择边界、请求接线、逐项反馈和失败项重试可编译且受自动化保护，但正式开发库未升级、本次没有真实调用 DeepSeek，且当前无受控浏览器实例，不能证明真实数据库点击和视觉效果；下一段只接入评分详情、逐项证据和运行历史。

#### 小步骤 9 第六小段：评分详情、逐项证据与评分历史交互（已完成）

- `/app/screening` 每条 Application 新增“评分记录”入口，详情抽屉左侧按 attempt 展示全部不可变评分历史，并标识当前、已过期、失败、资料不足和强制重跑记录；打开时优先选中 Application 当前结果，没有当前结果时选中最近一次运行。
- 抽屉右侧复用现有评分详情接口，展示总分、推荐方向、证据覆盖率、五维分数、确定性硬性条件、Rubric 语义逐项 `0—10/unknown`、原因、置信度、可定位证据、优势/缺口，以及 Rubric/规则/Prompt/模型版本、耗时和 token。新增纯 TypeScript 转换层安全读取后端 JSON 快照，并在逐项证据缺失时回退到已保存的扁平证据，不伪造分数或证据。
- 历史列表和详情分别覆盖 loading、空、失败与重新读取；请求版本守卫会忽略切换记录后迟到的旧响应。该抽屉保持只读，没有新增强制重跑、HR 通过/备选/淘汰、公开投递或其他阶段功能。
- 新增 1 组详情 UI/数据转换测试；Application Service、工作队列、单人评分、批量评分和详情共 5 组阶段 7 相关测试全部通过。`tsc && vite build` 成功转换 3118 个模块，`git diff --check` 通过。当前没有使用真实阶段 7 数据执行浏览器点击或截图，因此不能把源码响应式检查和生产构建当作视觉验收。
- 本段位于 `React 只读详情 -> applications.ts -> GET /applications/{id}/screenings 与 GET /screening-results/{id} -> 既有 Schema -> ApplicationService/ScreeningResultService -> ScreeningResult Model -> PostgreSQL`。本次没有修改 API、Schema、后端 Service、Model、Alembic 或 PostgreSQL；下一小步只做已有评分接口的强制重跑确认交互，继续不进入 HR 决策。

### 重要说明

下面的历史内容记录的是旧版演示系统完成度，不能等同于新架构完成度。后续开发以 `docs/specs/2026-07-15-hr-agent-platform-design.md` 和 `docs/implementation-plan.md` 为准。

---

## 历史状态：旧版演示系统

> 最后更新：2026-04-26（第二十七轮，新电脑交付启动与演示数据自动兜底）

## 项目状态：✅ 全部完成 + 新电脑解压后可按脚本/Vite 启动看到演示数据 + AI 初筛中心移除备选逻辑 + 候选人列表正式流程备选 + 岗位一致 Demo 数据重置脚本 + 招聘漏斗初筛流转改造 + Dashboard 初筛状态统计 + TypeScript 构建通过，可运行、可演示、可答辩

---

## 一、已实现功能

### 后端功能
- **候选人 CRUD**：完整的增删改查 + 分页 + 组合筛选（岗位/阶段/渠道/关键词）+ 排序
- **动态筛选选项**：`/api/candidates/filter-options` 从真实候选人数据生成岗位和来源选项，不写死岗位名称
- **候选人批量处理**：支持批量标记备选、批量标记待约面、批量淘汰、批量导出 CSV、批量生成 AI 跟进建议
- **批量操作日志同步**：批量阶段变更复用 StageChangeLog + ActivityLog，Dashboard 最近操作日志可见，阶段统计自动更新
- **候选人删除**：列表页可删除候选人，带确认弹窗，删除后关联日志级联清理
- **HR 决策触发阶段流转**：6 种 HR 操作（通过筛选/安排面试/进入复试/发放offer/确认入职/淘汰）自动推进阶段
- **自动阶段推进**：简历上传自动进入「待筛选」；面试时间到达自动进入「面试中」
- **三种触发源追踪**：system_auto（系统自动）、hr_action（HR操作）、manual（人工修正），人工修正具有最高优先级
- **阶段变更审计日志**：StageChangeLog 记录每次变更的来源、原因、前后状态
- **Dashboard 最近操作日志同步**：状态变更后统一展示最新阶段日志，包含原阶段/新阶段/触发原因/触发来源/更新时间
- **简历解析**：上传 PDF/DOCX/TXT，AI 自动提取 11 个结构化字段
- **AI 候选人摘要**：一键生成 2-3 句专业摘要
- **AI 自动标签**：生成 3-6 个多维度分类标签（学历/经验/技能/岗位/特殊）
- **AI 跟进建议**：基于招聘阶段生成具体下一步行动建议
- **面试反馈 AI 总结**：HR 在候选人详情页录入面试反馈后，可生成技术能力、沟通表达、岗位匹配度、风险点、推荐结论和下一步建议，并保存到候选人记录
- **AI 批量初筛**：支持对未初筛候选人批量生成岗位匹配度、推荐等级、初筛建议、初筛理由、风险提示和初筛时间
- **AI 初筛结果查询**：`/api/screening/results` 支持按岗位、推荐等级筛选，并按匹配度或更新时间排序
- **招聘漏斗初筛流转**：候选人主表新增 `screening_status`（pending/passed/backup/rejected）；/apply 与 HR 新增默认进入 pending，新投递候选人先进入 AI 初筛中心，通过初筛后进入候选人列表正式流程
- **岗位一致 Demo 数据重置**：新增 `scripts/reset_demo_data.py`，保留岗位管理数据，补齐 8 个 active Demo 岗位及岗位要求，清空候选人相关测试数据并重建 30 条候选人、21 份 TXT 简历附件；所有候选人 `job_id/target_role` 均来自岗位库
- **启动时演示数据兜底**：新增 `scripts/ensure_demo_data.py`，后端启动时自动创建数据库、上传目录和默认岗位；只有候选人表为空时才复用 `reset_demo_data.py` 生成完整演示数据，已有候选人时不清空、不重复导入
- **统一本地 SQLite 路径**：默认数据库明确为 `backend/recruit.db`，默认上传目录为 `backend/uploads`；相对 `DATABASE_URL` / `UPLOAD_DIR` 会解析到 `backend/`，避免脚本写一个库、后端读另一个库
- **Windows 一键启动**：新增根目录 `start_backend.bat` 和 `start_frontend.bat`；前端必须通过 Vite `npm run dev` / `npm.cmd run dev` 启动，使用 `frontend/vite.config.ts` 代理 `/api -> http://localhost:8000`
- **AI 初筛 HR 决策接口**：新增 `POST /api/candidates/{id}/screening/pass`、`/backup`、`/reject`；通过初筛写入 passed 并推进到「待约面」，`/backup` 仅允许已通过初筛的正式流程候选人进入备选视图，初筛淘汰写入原因并推进到「淘汰」
- **候选人列表范围简化**：`GET /api/candidates` 仅支持 `candidate_scope=formal|backup|rejected` 三类视图；正式流程默认展示 `screening_status=passed` 且阶段未淘汰的候选人，备选展示 `backup`，淘汰展示 `rejected` 或阶段为「淘汰」的候选人
- **Dashboard 初筛状态统计**：区分总投递人数、待初筛、通过初筛、正式流程备选、初筛淘汰、正式流程候选人数，避免候选人列表默认人数与总投递人数混淆
- **AI 初筛统计口径统一**：候选人列表、Dashboard、AI 初筛中心均以候选人主表全部记录作为总候选人数；缺少岗位、简历或未初筛结果不会从总数中排除；AI 初筛中心当前筛选统计直接由当前表格数据计算
- **单人重新初筛**：支持对候选人重新执行 AI 初筛，不自动淘汰候选人，最终决策仍由 HR 确认
- **HR Copilot**：自然语言对话查询招聘数据
- **三级去重**：手机号 → 邮箱 → 姓名+学校+岗位
- **招聘看板统计**：漏斗数据、渠道分布、岗位分布、今日新增、最近 3 天新增、今日新增候选人列表、跟进预警、今日建议跟进
- **最近新增规则**：候选人响应统一返回 `new_candidate_label`、`is_today_new`、`is_recent_3_days_new`；列表默认按投递时间倒序排列，并支持今日新增筛选
- **数据同步**：CSV 导出 + 腾讯文档 Adapter 预留接口
- **操作日志**：全操作记录（创建/阶段变更/AI处理等）
- **在线投递**：投递者自助填写表单 + 简历上传，自动入库（source_channel="在线投递"），手机号去重
- **HR 统一新增候选人**：`/form` 同时支持手动录入 + 可选简历上传，默认阶段为「新投递」，默认来源为「HR手动录入」
- **简历附件元数据**：候选人记录关联保存简历文件名、文件类型、文件大小、上传时间，并返回下载/查看地址
- **种子数据**：启动时自动导入 14 条候选人数据
- **演示数据增强**：已有库启动时会补充 5 条在线投递候选人，并补全默认岗位描述/要求，候选人详情展示更完整的投递、简历和 AI 初筛信息

### 前端功能
- **Dashboard 看板**：统计卡片 + 最近新增候选人（今日新增、最近 3 天新增、今日新增 Top 5）+ 招聘漏斗图 + 渠道饼图 + 岗位分布 + 今日建议跟进 + 跟进预警 + 今日摘要 + 最近操作日志
- **新增候选人统一页**：手动录入 + 可选简历上传 + AI 补全空字段 + 自动去重 + 创建后跳转详情
- **候选人列表**：范围筛选只保留正式流程候选人、备选候选人、淘汰候选人；新投递/待初筛候选人只在 AI 初筛中心处理；正式流程阶段筛选保留「待约面、已约面、面试中、复试、offer、入职」
- **AI 初筛中心**：`/ai-screening` 默认只展示待初筛候选人，展示 AI 匹配度、推荐等级、初筛建议、风险提示、投递时间、应聘岗位，并提供通过初筛/初筛淘汰/重新初筛/查看详情；备选移至候选人列表正式流程管理
- **候选人列表初筛展示**：列表中用紧凑列展示 AI 匹配度、推荐等级和初筛建议
- **候选人详情**：完整信息 + AI 摘要/标签/跟进建议（按需生成） + HR 决策按钮 + 阶段变更记录（含触发来源） + 人工修正下拉框 + 面试时间设置弹窗 + 操作日志
- **候选人详情面试反馈**：详情页支持录入面试原始反馈、面试官、面试轮次、反馈时间，并生成/重新生成 AI 面试总结
- **候选人详情简历附件区**：展示文件名/类型/大小/上传时间，并提供查看、下载按钮；未上传时显示占位提示
- **HR Copilot 聊天**：嵌入式对话组件
- **投递者在线填写页**：独立全屏表单页（/apply），无需登录，支持基本信息/教育背景/求职信息/简历上传，提交后自动入库
- **兼容路由保留**：`/upload` 仍可访问，但会自动跳转到 `/form`，避免 HR 端存在两个分散入口

### AI 特性
- **双模架构**：Mock LLM（零成本）/ 真实 LLM（OpenAI/DeepSeek/智谱）
- **自动回退**：任何 LLM 调用失败自动回退到 Mock 模式
- **5 套 Prompt 模板**：简历提取、摘要生成、标签生成、跟进建议、Copilot 系统指令
- **AI 初筛规则**：基于岗位、学校、学历、专业、技能、工作经历、自我介绍和简历文本进行岗位匹配度评分；不使用性别、年龄、民族、婚育等敏感信息作为筛选依据

---

## 二、项目目录结构

```
testin云测面试题/
├── .gitignore
├── .env.example                # 环境变量模板
├── docker-compose.yml          # Docker 编排
├── README.md                   # 项目说明
├── PROJECT_STATE.md            # 本文件
├── TODO_NEXT.md                # 后续优化建议
├── HANDOFF.md                  # 交接说明
├── 项目.txt                    # 原始面试题目
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py                  # 启动入口
│   ├── uploads/.gitkeep
│   └── app/
│       ├── __init__.py
│       ├── main.py             # FastAPI app（lifespan + CORS + 路由挂载）
│       ├── config.py           # pydantic-settings 配置
│       ├── database.py         # SQLAlchemy engine + init_db()
│       ├── seed_data.py        # 14 条种子数据
│       ├── models/
│       │   ├── candidate.py    # Candidate ORM（35 列）
│       │   └── activity_log.py # ActivityLog ORM（5 列）
│       ├── schemas/
│       │   ├── candidate.py    # 请求/响应 Pydantic 模型
│       │   └── dashboard.py    # 看板数据模型
│       ├── routers/
│       │   ├── candidates.py   # 候选人 CRUD
│       │   ├── resume.py       # 简历上传
│       │   ├── ai.py           # AI 功能
│       │   ├── screening.py    # AI 批量初筛
│       │   ├── dashboard.py    # 看板统计
│       │   ├── sync.py         # 数据同步
│       │   └── apply.py        # 在线投递（投递者表单提交）
│       ├── services/
│       │   ├── ai_service.py       # 统一 AI 网关（双模）
│       │   ├── mock_llm.py         # Mock LLM（正则+模板+规则引擎）
│       │   ├── candidate_service.py # 候选人业务逻辑
│       │   ├── followup_service.py  # AI 跟进建议与 Dashboard 跟进统计
│       │   ├── file_parser.py      # 文件解析（PDF/DOCX/TXT）
│       │   ├── dedup_service.py    # 三级去重
│       │   └── sync_adapter.py     # 数据同步 Adapter
│       └── prompts/
│           ├── resume_extraction.txt
│           ├── candidate_summary.txt
│           ├── auto_tagging.txt
│           ├── followup_suggestion.txt
│           └── copilot_system.txt
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts          # 代理 /api → localhost:8000
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx            # React 入口
│       ├── App.tsx             # 路由配置
│       ├── App.css
│       ├── index.css
│       ├── api/index.ts        # Axios API 封装
│       ├── types/index.ts      # TypeScript 类型定义
│       ├── utils/constants.ts  # 常量定义
│       ├── components/
│       │   ├── AppLayout.tsx       # 侧边栏布局
│       │   ├── StatsCards.tsx      # 统计卡片
│       │   ├── FunnelChart.tsx     # 招聘漏斗图
│       │   ├── ChannelPieChart.tsx # 渠道饼图
│       │   ├── FollowUpAlerts.tsx  # 跟进预警
│       │   ├── RecentLogs.tsx      # 操作日志
│       │   ├── DailySummary.tsx    # 今日摘要
│       │   ├── StageTag.tsx        # 阶段标签
│       │   └── CopilotChat.tsx     # Copilot 聊天
│       └── pages/
│           ├── Dashboard.tsx       # 主看板
│           ├── CandidateForm.tsx   # HR 统一新增候选人（手动录入 + 简历上传）
│           ├── ResumeUpload.tsx    # 旧简历上传页逻辑保留（当前路由已跳转 /form）
│           ├── CandidateList.tsx   # 候选人列表
│           ├── AIScreeningCenter.tsx # AI 初筛中心
│           ├── CandidateDetail.tsx # 候选人详情
│           ├── ApplyForm.tsx      # 投递者在线填写页
│           └── ApplyForm.css      # 投递页样式
│
├── docs/
│   ├── 业务方案.md
│   ├── Prompt工程与效果验证.md
│   ├── 系统架构说明.md
│   ├── 演示脚本.md
│   └── 答辩讲稿.md
│
├── prompts/                    # Prompt 设计文档（5 个 .md）
├── scripts/
│   ├── init_db.py              # 数据库初始化
│   ├── ensure_demo_data.py     # 后端启动时按需补齐演示数据
│   ├── reset_demo_data.py      # 手动重置演示数据
│   └── export_csv.py           # CSV 导出
├── start_backend.bat           # Windows 后端一键启动
├── start_frontend.bat          # Windows 前端 Vite 一键启动
│
└── sample_data/
    ├── sample_resume_1.txt
    ├── sample_resume_2.txt
    ├── sample_resume_3.txt
    └── sample_candidates.json
```

---

## 三、启动方式

### 方式 A：手动启动（开发模式）

```bash
# 终端 1 - 后端（先启动）
cd backend
pip install -r requirements.txt
python run.py
# → http://localhost:8000/docs (Swagger API 文档)

# 终端 2 - 前端
cd frontend
npm install
npm run dev
# → http://localhost:5173 (前端页面)
```

前端必须使用 Vite 开发服务器启动，不要使用 `python -m http.server` 打开 `frontend` 静态文件。`frontend/vite.config.ts` 已配置 `/api` 代理到 `http://localhost:8000`，否则页面无法访问后端演示数据。

### 方式 A-1：Windows 双击脚本

```bash
start_backend.bat
start_frontend.bat
# 前端：http://localhost:5173
# 后端 API：http://localhost:8000/docs
```

首次启动后端时，如果 `backend/recruit.db` 不存在或候选人表为空，系统会自动生成完整演示数据；已有候选人时不会清空数据库。

### 方式 B：Docker

```bash
docker-compose up --build
# 前端：http://localhost:3000
# 后端 API：http://localhost:8000/docs
```

### 独立脚本

```bash
python scripts/init_db.py        # 初始化数据库 + 种子数据
python scripts/export_csv.py     # 导出候选人 CSV
```

---

## 四、可访问页面和入口

| 页面 | 手动模式地址 | Docker 地址 | 说明 |
|------|-------------|-------------|------|
| Dashboard 看板 | http://localhost:5173/ 或 /dashboard | http://localhost:3000/ 或 /dashboard | 首页，统计+漏斗+预警 |
| 新增候选人 | http://localhost:5173/form | http://localhost:3000/form | HR 统一录入页，支持手动填写 + 简历上传 |
| /upload 兼容跳转 | http://localhost:5173/upload | http://localhost:3000/upload | 自动跳转到 `/form` |
| AI 初筛中心 | http://localhost:5173/ai-screening | http://localhost:3000/ai-screening | 批量初筛、推荐等级筛选、匹配度排序 |
| 候选人列表 | http://localhost:5173/candidates | http://localhost:3000/candidates | 岗位/阶段/来源/关键词组合筛选、分页 |
| 候选人详情 | http://localhost:5173/candidates/:id | http://localhost:3000/candidates/:id | AI 摘要/标签/建议 |
| 投递者在线填写 | http://localhost:5173/apply | http://localhost:3000/apply | 投递者自助填写表单 |
| Swagger API | http://localhost:8000/docs | http://localhost:8000/docs | 后端 API 文档 |

---

## 五、已修复的问题

### 第一轮：Python 3.9 兼容 + Docker 修复

1. **docker-compose.yml DATABASE_URL 路径错误**：`sqlite:///./recruit.db`（相对路径）改为 `sqlite:////app/data/recruit.db`（绝对路径），确保数据库在 Docker 持久卷内
2. **Python 3.9 兼容性**：将全部 `dict | None`、`list[str]`、`tuple[list[...], int]` 等 Python 3.10+ 语法改为 `Optional[dict]`、`List[str]`、`Tuple[List[...], int]`（使用 `typing` 模块），涉及 7 个文件

### 第二轮：前端 UI 联调 + Bug 修复

3. **[HIGH] 简历上传手机号空值导致 422**：mock LLM 提取不到手机号时返回空字符串 `""`，`.get("phone", "13800000000")` 拿到 `""` 而非默认值，正则校验失败。修复：改用 `or` 运算符 `.get("phone") or "13800000000"`
4. **[HIGH] CandidateList 搜索双重请求**：`setPage(1); loadData()` 中 setState 异步导致 loadData 用旧 page 值发请求，然后 useEffect 又发一次。修复：移除显式 `loadData()` 调用
5. **[HIGH] triggerSync 未 await**：`triggerSync()` 返回 Promise 但未 await，立即显示"同步成功"。修复：await + try/catch + 失败提示
6. **[MEDIUM] AI 重新生成无 catch**：`handleRegenSummary` 和 `handleRegenTags` 使用 try/finally 无 catch，API 失败时无用户反馈。修复：增加 catch + message.error
7. **[MEDIUM] getFollowup 每次加载时调用**：每次进入详情页都 POST AI 跟进建议，阻塞页面加载。修复：改为按需调用（"生成建议"按钮）
8. **[MEDIUM] Antd Spin tip 不显示**：antd v5 standalone Spin 不渲染 tip 文字。修复：移除 tip prop
9. **[LOW] 废弃的 bodyStyle 属性（3 处）**：antd v5 中 bodyStyle 已废弃。修复：改为 `styles={{ body: {...} }}`
10. **[LOW] 未使用的 imports（2 处）**：CandidateForm 中 Upload/UploadOutlined 未使用，CandidateList 中 STAGE_COLORS/StageTag 未使用。修复：删除

### 第三轮：Dashboard 统计刷新 + 候选人删除功能

11. **[HIGH] Dashboard 统计数据不随新增候选人更新**：`useEffect` 依赖数组为 `[]`，仅在组件首次挂载时拉取数据。当用户从其他页面导航回 Dashboard 时，某些场景下组件未重新挂载导致数据不刷新。修复：引入 `useLocation`，将 `location.key` 作为 `useEffect` 依赖，确保每次导航到 Dashboard 都重新拉取全部看板数据
12. **[MEDIUM] 候选人列表无删除功能**：后端 `DELETE /candidates/{id}` 接口和 `deleteCandidate` API 已存在，但前端列表页未提供删除按钮。修复：在列表增加「操作」列，含 `Popconfirm` 确认弹窗 + 删除按钮，删除成功后自动刷新列表

### 第四轮：TypeScript 构建修复 + HR 决策自动阶段流转

13. **[HIGH] TypeScript 构建失败**：`tsconfig.node.json` 缺少 `composite: true` 且 `noEmit: true` 与 composite 引用冲突。修复：添加 `composite: true`，将 `noEmit` 改为 `emitDeclarationOnly`
14. **[HIGH] 前后端阶段常量不一致**：后端用 `"待筛选"`、前端用 `"初筛"`，前端多了 `"待定"` 后端会返回 400。修复：前端 STAGES 统一为后端 VALID_STAGES，移除 `"待定"`
15. **[HIGH] HR 操作无法从前端触发**：`stage_service.execute_hr_action()` 和 `HR_ACTION_MAP` 已实现但无 HTTP 端点暴露。修复：添加 `POST /candidates/{id}/hr-action/{action_name}` 路由 + `candidate_service.execute_hr_action()` 方法
16. **[HIGH] `_to_read` 未返回 `stage_source` 和 `interview_time`**：前端无法显示阶段触发来源和面试时间。修复：在 `_to_read` 中补充这两个字段
17. **[MEDIUM] 简历上传后阶段停留在「新投递」**：上传解析完成后应自动推进到「待筛选」。修复：在 `create_from_resume` 末尾调用 `stage_service.change_stage` 自动推进
18. **[MEDIUM] 候选人详情页缺少 HR 决策入口**：只有手动下拉框选择阶段，没有语义化的 HR 操作按钮。修复：添加 6 个 HR 决策按钮 + 面试时间设置弹窗 + 阶段变更记录展示 + 触发来源标签
19. **[MEDIUM] 无阶段变更记录展示**：StageChangeLog 表已记录数据但前端无展示入口。修复：添加 `GET /candidates/{id}/stage-logs` 端点 + 前端阶段变更记录卡片

### 第五轮：Dashboard 最近操作日志同步修复

20. **[HIGH] 改状态后 Dashboard 最近操作日志不同步**：看板最近日志读的是 `ActivityLog`，阶段审计读的是 `StageChangeLog`，两条链路未统一；同时旧种子日志存在未来时间戳，导致新状态日志可能排不到最前。修复：Dashboard 最近日志改为统一合并 `StageChangeLog + 非阶段类 ActivityLog`，阶段变更统一返回结构化字段；启动时执行日志迁移，回填历史阶段日志、修正旧阶段名并清理未来时间戳
21. **[HIGH] 系统自动阶段更新只在详情页触发**：`check_auto_interview_start()` 仅在 `get_candidate()` 执行，导致列表页和 Dashboard 访问时看不到最新自动阶段和对应日志。修复：在候选人列表、Dashboard 统计、跟进预警、最近日志、今日摘要查询前统一补跑待执行的自动阶段更新
22. **[MEDIUM] 新状态日志在同秒内可能被旧日志压住**：SQLite 默认时间戳为秒级，新日志和旧日志同秒时排序不稳定。修复：阶段变更与普通操作日志统一改为写入 Python 精确时间戳，保证最新状态变更在 Dashboard 置顶
23. **[MEDIUM] 种子数据阶段名和阶段日志不完全一致**：seed 中仍有 `"初筛"`/`"待定"` 旧值，且当天种子日志可能写到未来时间。修复：种子数据阶段名统一为当前常量，同时补充 StageChangeLog 种子记录并将日志时间钳制到当前时间

### 第六轮：在线投递简历附件详情可见

24. **[HIGH] /apply 上传的简历在候选人详情页不可见**：在线投递虽然已保存文件并写入 `resume_path`，但候选人详情接口未返回原始文件名、文件类型、文件大小、查看/下载地址，前端也没有附件展示区。修复：候选人模型新增 `resume_filename`、`resume_file_type`、`resume_file_size`、`resume_uploaded_at` 字段，详情接口统一返回 `resume_url`
25. **[MEDIUM] 简历上传与在线投递两条入口附件元数据不一致**：`/resume/upload` 和 `/apply` 原先都只保留存储路径。修复：新增 `candidate_service.attach_resume()`，统一写入简历路径、原始文件名、类型、大小、上传时间，复用现有 `/uploads` 静态访问
26. **[MEDIUM] 候选人详情页缺少附件查看/下载入口**：HR 无法在详情页直观看到简历。修复：新增“简历附件”区域，支持 PDF/TXT 新标签页查看，PDF/DOCX/TXT 下载；未上传简历时显示“未上传简历”

### 第七轮：修复 /apply 简历未实际上传

27. **[HIGH] 投递页选择了简历但提交时未真正上传文件**：`ApplyForm` 在 `beforeUpload` 中把原始 `RcFile` 直接强转成 `UploadFile` 放入 `fileList`，导致 `originFileObj` 丢失；提交时 `FormData` 判断 `fileList[0].originFileObj` 为 `undefined`，后端实际收不到文件。修复：在 `beforeUpload` 中显式构造带 `originFileObj` 的 `UploadFile`，提交时稳定从该字段追加到 `FormData`

### 第八轮：HR 端统一新增候选人页

28. **[HIGH] HR 端存在“候选人录入”和“简历上传”两个分散入口**：容易造成流程分裂，也无法保证文件与候选人记录统一关联。修复：将 `/form` 改为“新增候选人”统一页，支持手动录入 + 可选简历上传；侧边栏合并为单一菜单项“新增候选人”
29. **[HIGH] HR 后台上传简历时无法同时提交手动字段并关联附件**：旧 `/upload` 仅做 AI 预览确认，不会复用手动录入字段，也不保证简历文件与最终候选人记录绑定。修复：新增 `POST /api/candidates/hr-create` 多部分表单接口，统一创建候选人、保存简历附件并返回详情字段
30. **[MEDIUM] AI 简历解析会与 HR 手填内容冲突**：合并录入页后需要避免覆盖 HR 已填信息。修复：前后端都改为“AI 只补全空字段”，保留已填写内容不被覆盖
31. **[MEDIUM] HR 新增候选人日志不够直观**：Dashboard 最近日志中难以区分后台手动新增。修复：HR 后台新增统一写入 `HR新增候选人：姓名（渠道：xxx）`，创建后 Dashboard / 列表 / 详情数据保持一致

### 第十轮：AI 批量初筛中心

32. **[HIGH] HR 无法批量处理大量简历初筛**：新增候选人初筛字段 `match_score`、`priority_level`、`screening_result`、`screening_reason`、`risk_flags`、`screening_updated_at`，启动迁移自动补齐旧库字段
33. **[HIGH] 缺少岗位匹配度评分能力**：新增 Mock/LLM 初筛服务，基于岗位、学校、学历、专业、技能、工作经历、自我介绍和简历文本生成 0-100 分匹配度；80+ 为高优先级，60-79 为中优先级，60 以下为低优先级
34. **[HIGH] 缺少批量初筛 API 和结果查询 API**：新增 `POST /api/screening/run`、`POST /api/screening/run/{candidate_id}`、`GET /api/screening/results`
35. **[MEDIUM] HR 缺少高匹配候选人处理入口**：新增 `/ai-screening` 页面，支持批量初筛、单人重新初筛、按推荐等级筛选、按匹配度排序、跳转候选人详情，高优先级候选人突出展示
36. **[MEDIUM] 主列表和看板缺少初筛信息**：候选人列表增加紧凑 AI 初筛列；Dashboard 增加高/中/低优先级、平均匹配度和尚未初筛统计

### 第十一轮：候选人列表岗位筛选增强

37. **[HIGH] 候选人列表无法按岗位分类查看**：后端候选人列表接口新增 `target_role` 查询参数，支持与阶段、来源、关键词组合筛选，筛选后分页总数正确
38. **[MEDIUM] 岗位筛选选项不能写死**：新增 `GET /api/candidates/filter-options`，从当前候选人数据动态返回岗位和来源选项
39. **[MEDIUM] 关键词搜索覆盖字段不足**：关键词搜索扩展为姓名、手机号、邮箱、学校、专业、应聘岗位、技能关键词
40. **[MEDIUM] Dashboard 缺少岗位维度视图**：Dashboard 新增“岗位分布”模块，展示每个岗位候选人数、高优先级人数和待跟进人数；新增“今日建议跟进”轻量模块

### 第十二轮：候选人批量处理

41. **[HIGH] HR 无法一次处理多个候选人**：候选人列表新增行复选框、表头全选/取消全选、已选择人数和批量操作栏
42. **[HIGH] 缺少批量阶段处理接口**：新增 `POST /api/candidates/batch/status`，支持批量通过初筛、批量标记待约面、批量淘汰，操作来源为 `hr_action`
43. **[HIGH] 批量淘汰需要高风险确认**：前端新增批量淘汰二次确认弹窗，可填写淘汰原因，取消后不会修改数据
44. **[MEDIUM] 缺少选中候选人导出能力**：新增 `POST /api/candidates/batch/export`，只导出当前选中候选人 CSV，字段包含基础信息、阶段、来源、AI 摘要、AI 跟进建议和创建时间
45. **[MEDIUM] 批量生成跟进建议缺少操作入口**：新增 `POST /api/candidates/batch/followup`，对选中候选人生成最新跟进建议并写入操作日志

### 第十三轮：招聘岗位管理与投递岗位标准化

46. **[HIGH] /apply 应聘岗位自由输入导致数据失真**：新增 `jobs` 岗位表和 `job_id` 候选人字段；投递者端 `/apply` 改为从 `GET /api/jobs/active` 实时加载启用岗位下拉，提交时必须传 `job_id`，后端校验岗位存在且为 `active`
47. **[HIGH] 缺少 HR 岗位选项统一维护入口**：新增 `/jobs` 岗位管理页，支持查看、新增、编辑、启用/停用、谨慎删除；所有操作写入后端数据库并刷新列表
48. **[HIGH] 岗位改名可能影响历史候选人展示**：候选人提交时同时保存 `job_id` 和当时岗位名称快照 `target_role`；岗位后续改名/停用不回写历史候选人的 `target_role`
49. **[MEDIUM] HR 新增候选人仍可随意输入岗位**：HR 统一新增候选人页默认优先从岗位库选择岗位，特殊情况保留“其他/手动输入”；选岗位时同样保存 `job_id + target_role`
50. **[MEDIUM] 筛选和看板需兼容岗位库与历史数据**：候选人列表岗位筛选选项合并岗位库标题和真实候选人历史岗位，Dashboard 岗位分布继续基于候选人 `target_role` 快照统计，停用岗位不影响历史显示和筛选

### 第十四轮：HR 决策操作业务化

51. **[HIGH] HR 决策按钮过于简单，缺少业务表单**：候选人详情页的安排面试、进入复试、发放 Offer、确认入职、淘汰均改为弹窗提交；安排面试必填面试时间，淘汰必填淘汰原因
52. **[HIGH] 关键招聘动作缺少结构化数据落库**：候选人模型新增面试方式/面试官/面试备注、复试反馈/复试时间/复试面试官、Offer 岗位/薪资/预计入职/Offer 备注、实际入职时间/入职备注、淘汰原因/淘汰备注等字段，并通过启动迁移补齐旧库
53. **[HIGH] 终态候选人仍可继续推进流程**：后端禁止对「入职」「淘汰」候选人继续执行 HR 流程推进；前端同步禁用全部流程推进按钮，只保留阶段人工修正和日志查看
54. **[MEDIUM] 当前阶段可执行动作缺少限制**：前后端均按阶段限制 HR 动作：新投递/待筛选可通过筛选或淘汰，待约面可安排面试，已约面/面试中可进入复试或淘汰，复试可发 Offer 或淘汰，offer 可确认入职或淘汰
55. **[MEDIUM] 详情页缺少面试/Offer/入职/淘汰信息展示**：候选人详情页新增“招聘流程信息”区域，仅在存在对应数据时展示，避免空表格
56. **[MEDIUM] CSV 同步未包含关键流程字段**：LocalSheetAdapter 和导出脚本增加面试、Offer、入职、淘汰关键字段，HR 动作后同步数据更完整

### 第十五轮：AI 初筛中心投递时间筛选

57. **[HIGH] AI 初筛中心缺少投递时间信息**：初筛结果接口和前端列表新增候选人 `created_at`，页面展示“投递时间”列，格式为 `YYYY-MM-DD HH:mm`
58. **[HIGH] 无法按投递时间处理候选人**：`GET /api/screening/results` 支持 `date_range`、`start_date`、`end_date`、`sort_by=created_at`、`sort_order=desc|asc`；前端新增“全部时间 / 今日投递 / 本周投递 / 最近 7 天 / 最近 30 天”筛选
59. **[MEDIUM] 初筛排序只偏向匹配度**：AI 初筛中心排序下拉新增“最新投递优先”和“最早投递优先”，默认改为最新投递优先，同时保留匹配度从高到低、匹配度从低到高、最近初筛优先
60. **[HIGH] 批量初筛未联动筛选范围**：`POST /api/screening/run` 支持与结果列表相同的岗位、推荐等级和投递时间筛选参数；前端批量初筛只处理当前筛选范围内未初筛候选人，并在执行前二次确认

### 第十六轮：岗位要求配置驱动 AI 初筛

61. **[HIGH] AI 初筛缺少岗位要求依据**：`jobs` 表新增必备技能、加分技能、学历要求、经验要求、岗位关键词、风险提示关键词字段；岗位管理页可维护这些字段并写入后端数据库
62. **[HIGH] 初筛评分未优先参考岗位标准**：AI 初筛时通过候选人 `job_id` 读取对应岗位配置，历史数据无 `job_id` 时按岗位名称兜底匹配；Mock/回退评分逻辑基于必备技能命中率、加分技能、学历/经验要求、岗位关键词和风险关键词计算分数
63. **[MEDIUM] 初筛理由不够可追溯**：初筛理由增加岗位要求来源、必备技能命中、加分技能命中和岗位关键词命中说明；风险提示会标记必备技能不足、学历/经验未达标、风险关键词命中等
64. **[MEDIUM] AI 初筛中心无法查看岗位标准**：初筛列表新增“匹配依据”列，并提供“查看岗位标准”弹窗，展示当前岗位的必备技能、加分技能、学历/经验要求、岗位关键词、风险关键词、岗位描述和岗位要求

### 第十七轮：超时未跟进提醒

65. **[HIGH] HR 容易遗漏长期未处理候选人**：`followup_service` 新增统一超时规则，按候选人当前阶段和最近动作时间计算 `is_overdue`、`overdue_days`、`overdue_reason`、`last_action_at`
66. **[HIGH] Dashboard 缺少超时跟进概览**：Dashboard 今日建议跟进模块新增“超时未跟进”“今日待跟进”“高优先级跟进”“超过3天未跟进”统计；跟进预警模块改为展示真实超时候选人
67. **[MEDIUM] 候选人列表无法快速识别超时项**：候选人列表 AI 跟进列新增“超时”标签、超时天数、跟进优先级和超时原因
68. **[MEDIUM] 候选人详情缺少当前超时说明**：详情页 AI 跟进建议卡片新增超时提醒，展示超时天数、超时原因和系统跟进建议
69. **[MEDIUM] 终态候选人仍可能误提醒**：入职/淘汰阶段统一不再触发超时提醒；状态变化、备注更新、安排面试、HR 决策操作后通过 `updated_at`/阶段日志自动重新计算

### 第十八轮：最近新增候选人高亮

70. **[HIGH] HR 难以从大量候选人中快速识别新投递**：候选人列表新增“今日新增 / 新投递”标签，最近新增行轻微高亮，并保留表格可读性
71. **[HIGH] 列表缺少今日新增筛选与明确投递时间**：候选人列表新增“今日新增”筛选，明确展示投递时间、来源渠道和是否今日新增；默认继续按投递时间倒序排列
72. **[MEDIUM] Dashboard 缺少最近新增入口**：Dashboard 新增“最近新增候选人”模块，展示今日新增人数、最近 3 天新增人数和今日新增候选人列表（最多 5 条）
73. **[MEDIUM] 在线投递/HR录入来源识别不够直观**：来源列对 `在线投递` 显示绿色“在线投递”标签，对 `HR手动录入` 显示蓝色“HR录入”标签

### 第十九轮：面试反馈 AI 总结

74. **[HIGH] 面试后反馈零散，HR 需要手动整理结论**：候选人详情页新增“面试反馈 AI 总结”区域，可录入原始反馈、面试官、面试轮次和反馈时间
75. **[HIGH] 缺少结构化面试反馈总结能力**：新增 AI/mock 面试反馈总结，输出技术能力总结、沟通表达总结、岗位匹配度判断、风险点、推荐结论和下一步建议
76. **[MEDIUM] AI 总结需要可追溯保存**：候选人模型新增面试反馈与 AI 总结字段，生成结果保存到候选人记录；重新进入详情页仍可查看
77. **[MEDIUM] 生成 AI 面试总结缺少日志**：生成后写入操作日志 `ai_interview_summary`，详情页操作日志和 Dashboard 最近操作日志可见

### 第二十轮：演示数据与详情信息增强

78. **[MEDIUM] 演示候选人详情信息偏少**：新增 5 条在线投递候选人，补充更完整的工作经历、自我介绍、技能、AI 摘要和 HR 备注
79. **[MEDIUM] 默认岗位缺少业务描述**：默认岗位补充岗位描述和任职要求；已有数据库启动时会自动补齐空缺描述
80. **[LOW] AI 初筛中心匹配依据命名优化**：前端列名统一为“匹配依据”，弹窗入口改为“查看岗位标准”
81. **[LOW] 候选人详情可读信息密度不足**：详情页新增“投递与 AI 初筛信息”卡片，集中展示匹配度、推荐等级、初筛理由、风险提示、跟进日期和最近动作时间

### 第二十一轮：AI 初筛统计口径统一

82. **[HIGH] Dashboard 与 AI 初筛中心人数不一致**：根因是 AI 初筛列表和统计过滤了 `is_duplicate == False`，而 Dashboard 候选人总数按候选人主表全部记录统计；修复后 AI 初筛不再排除重复标记候选人
83. **[HIGH] AI 初筛统计缺少总人数与已初筛人数**：后端 `get_screening_stats()` 统一返回总候选人数、已初筛人数、尚未初筛人数、高/中/低优先级人数和平均匹配度
84. **[MEDIUM] 前端 AI 初筛统计由当前列表临时计算，容易与后端口径不一致**：`/api/screening/results` 返回 `overall_stats` 与 `stats`；前端顶部展示全部统计，筛选后单独展示当前筛选结果统计
85. **[MEDIUM] 未初筛候选人口径不稳定**：统一按 `总候选人数 - 高优先级 - 中优先级 - 低优先级` 计算尚未初筛，确保四类加总等于总候选人数

### 第二十二轮：AI 初筛中心当前筛选统计彻底统一

86. **[HIGH] 表格有候选人但蓝色统计框显示 0 人**：前端不再依赖后端 `stats` 渲染当前筛选统计，而是直接基于当前表格 `items` 计算，保证“当前 X 人”和蓝色统计框同源
87. **[HIGH] 批量初筛范围与当前筛选结果可能不一致**：批量初筛提示和执行参数改为当前筛选结果范围；当前结果 14 人时提示处理 14 人，已初筛候选人会重新生成结果
88. **[MEDIUM] 缺少初筛状态筛选**：AI 初筛中心新增“已初筛 / 尚未初筛”筛选；后端 `/api/screening/results` 和 `/api/screening/run` 支持 `screening_status`
89. **[MEDIUM] screened/unscreened 判定不统一**：统一为有 `match_score` 或非空 `priority_level` 算已初筛；两者都为空算尚未初筛；有分数但无等级时计入低优先级，确保加总闭合

### 第二十三轮：招聘漏斗初筛流转改造

90. **[HIGH] 新投递候选人直接进入候选人列表，业务漏斗不真实**：新增 `screening_status` 主状态，/apply 与 HR 新增默认 `pending` + 「新投递」，候选人先进入 AI 初筛中心；候选人列表默认只展示 `passed`
91. **[HIGH] AI 初筛中心缺少 HR 最终初筛动作**：新增通过初筛、初筛淘汰接口和前端按钮；通过初筛后 `screening_status=passed`、阶段进入「待约面」，初筛淘汰要求填写原因并保留主记录
92. **[HIGH] Dashboard 总投递人数和候选人列表人数容易混淆**：Dashboard 新增待初筛、通过初筛、正式流程备选、初筛淘汰、正式流程候选人数；总投递人数继续按候选人主表全部记录统计
93. **[MEDIUM] 候选人列表阶段筛选包含新投递/待筛选**：候选人列表阶段筛选改为正式流程阶段：待约面、已约面、面试中、复试、offer、入职、淘汰
94. **[MEDIUM] 历史数据缺少初筛流转状态**：启动迁移自动补齐 `screening_status`；新投递/待筛选回填 pending，正式流程阶段回填 passed，淘汰回填 rejected

### 第二十四轮：岗位一致的 Demo 数据重置脚本

95. **[HIGH] 演示候选人岗位可能与岗位管理不一致**：新增 `scripts/reset_demo_data.py`，候选人只从 active 岗位库选择岗位，并同时写入 `job_id` 与岗位标题快照 `target_role`
96. **[HIGH] Demo 前缺少一键恢复干净数据能力**：脚本会清空候选人主表、阶段日志、操作日志和旧上传附件，保留岗位表与系统配置，然后生成 30 条候选人和 21 份 TXT 简历附件
97. **[MEDIUM] 岗位库 Demo 覆盖不足**：脚本按同名不重复规则补齐并激活测试工程师、自动化测试工程师、AI应用实习生、数据分析师、前端开发工程师、后端开发工程师、产品助理、UI设计师，并补充岗位要求字段
98. **[MEDIUM] Demo 数据不能展示招聘漏斗差异**：脚本生成 pending 11 人、formal backup 3 人、rejected 1 人、passed 15 人；AI 初筛中心默认只显示 11 名 pending，候选人列表正式流程默认展示 14 人，备选视图 3 人，淘汰视图展示初筛淘汰和正式流程淘汰共 2 人
99. **[MEDIUM] 最近新增、投递时间筛选、超时未跟进缺少演示数据**：脚本生成今日新增 5 人、最近 3 天 10 人、本周 20 人、历史 10 人，并构造新投递/待约面/已约面/offer 超时提醒场景

### 第二十五轮：候选人列表范围筛选简化

100. **[MEDIUM] 候选人列表范围筛选包含全部/待初筛，容易与 AI 初筛中心职责混淆**：前端范围筛选只保留正式流程候选人、备选候选人、淘汰候选人，移除全部候选人和待初筛候选人
101. **[MEDIUM] 正式流程默认视图混入淘汰候选人**：后端 `candidate_scope=formal` 改为 `screening_status=passed AND stage != 淘汰`；淘汰视图统一展示 `screening_status=rejected OR stage=淘汰`
102. **[LOW] 阶段筛选仍出现不属于候选人列表的初筛阶段**：候选人列表正式流程阶段筛选只保留待约面、已约面、面试中、复试、offer、入职；备选/淘汰视图隐藏阶段筛选
103. **[LOW] 批量操作与当前视图不匹配**：正式流程视图保留批量标记备选、批量标记待约面、批量淘汰、导出、生成跟进建议；备选视图保留批量淘汰、导出；淘汰视图仅保留导出

### 第二十六轮：AI 初筛中心移除备选逻辑

104. **[MEDIUM] AI 初筛中心出现备选统计和标记备选按钮，职责边界不清**：AI 初筛中心移除备选统计、备选筛选项和每行“标记备选”按钮，默认查询改为 `decision_status=pending`，只处理新投递/待初筛候选人
105. **[MEDIUM] 备选应属于正式流程管理**：`/api/candidates/{id}/screening/backup` 改为仅允许 `screening_status=passed` 且未淘汰候选人调用；候选人列表正式流程视图新增批量标记备选，备选视图展示正式流程备选候选人
106. **[LOW] Demo 数据仍把 backup 放在 AI 初筛池**：`scripts/reset_demo_data.py` 改为生成 11 名 pending 待初筛、3 名已通过后标记的正式流程备选；AI 初筛默认池不再包含 backup

### 第二十七轮：新电脑交付启动与演示数据自动兜底

107. **[HIGH] 前端用 Python http.server 无法代理 API**：明确交付启动方式必须使用 Vite；`frontend/vite.config.ts` 已配置 `/api -> http://localhost:8000`，README 新增禁止使用 `python -m http.server` 的说明
108. **[HIGH] 新电脑空库启动看不到演示数据**：新增 `scripts/ensure_demo_data.py`，后端 lifespan 调用该脚本；候选人表为空时复用 `reset_demo_data.py` 生成 30 条候选人和简历附件，已有候选人时跳过
109. **[HIGH] SQLite 相对路径可能读写不一致**：`backend/app/config.py` 将默认数据库固定到 `backend/recruit.db`，并把相对 `DATABASE_URL` / `UPLOAD_DIR` 解析到 `backend/`
110. **[MEDIUM] 缺少 Windows 交付启动入口**：新增 `start_backend.bat` 与 `start_frontend.bat`，分别安装依赖并启动 `python run.py`、`npm.cmd run dev`

---

## 六、当前已知问题

1. ~~**TypeScript 生产构建未验证**~~：✅ 已修复并验证通过（第四轮）
2. **Docker 端到端部署未验证**：`docker-compose up --build` 未实际执行过（本机未安装 Docker，配置已审查无问题）
3. **根目录多余的 package-lock.json**：项目根目录存在一个 `package-lock.json`，应该只在 `frontend/` 下才对，可能是误生成的
4. **种子数据日期固定**：seed_data 中的日期按 `days_ago` 计算，每次重新初始化时日期会变化
5. **后端部分代码质量问题**（不影响功能）：
   - Dashboard 路由未使用 response_model，OpenAPI 文档不显示响应模型
   - `_run_ai` 和 `_sync` 中 bare `except Exception: pass` 吞掉所有异常
   - StageUpdate.validate_stage() 是死代码（普通方法而非 Pydantic validator）

---

## 七、适合演示的页面

按推荐演示顺序：

1. **Dashboard 看板**（/ 或 /dashboard）— 最直观，一眼看到全局数据
2. **新增候选人**（/form）— 演示 HR 手动录入和上传简历补全空字段
3. **候选人详情**（/candidates/1）— 展示 AI 摘要、标签、跟进建议、简历附件
4. **岗位管理**（/jobs）— 展示 HR 维护岗位库，并联动投递者岗位下拉
5. **候选人列表**（/candidates）— 展示筛选、最近新增高亮、分页、内联编辑
6. **Copilot 聊天** — 在任意页面底部展示自然语言问答
7. **投递者在线填写**（/apply）— 独立页面，模拟投递者视角自助填写

详细演示流程见 `docs/演示脚本.md`。
