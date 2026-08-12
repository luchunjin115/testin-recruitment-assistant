# 项目进度状态

> 最新更新：2026-08-12（架构重建阶段 4 已完成并完成人工验收；阶段 5 前两小步已完成：严格草稿 Schema 与 Resume 独立结构化状态迁移）

## 当前总状态：🚧 新架构重建已启动，旧版演示系统作为迁移资产保留

### 权威依据

- 项目指令：`CLAUDE.md`
- 权威设计文档：`docs/specs/2026-07-15-hr-agent-platform-design.md`
- 实施计划：`docs/implementation-plan.md`
- 迁移清单：`docs/migration-inventory.md`
- 阶段 5 换电脑交接手册：`docs/handoff/2026-08-12-stage5-development-handoff.md`

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

### 阶段 5 正式方案：大模型简历结构化提取与表单辅助填写（已定稿，前两小步已完成）

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
3. 实现可替换的 DeepSeek Adapter；自动化测试全部使用 Fake Adapter，不产生真实费用。
4. 实现 `ResumeStructureService` 的幂等、并发、失败和旧成功草稿保护。
5. 实现结构化 API，再接入新增候选人页面的进度、AI 标记、冲突提示和辅助填写。
6. 使用至少 15～20 份去隐私样本评估字段完整性、格式失败率、响应时间和费用，最后完成真实前后端人工验收。

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

#### 下一台电脑的恢复起点

- 继续工作前完整阅读 `AGENTS.md`、`CLAUDE.md`、本文件、`docs/implementation-plan.md`、权威设计文档和阶段 5 专项设计，并检查分支及未提交修改。2026-08-12 文档修改前工作区为干净状态；后续仍严禁 reset、clean、覆盖或丢弃用户修改。
- 阶段 5 前两小步已经完成；仍未调用 DeepSeek、未创建结构化解析 API。方案已经确认，不再重复讨论是否使用 LangGraph；下一小步只实现 DeepSeek Adapter。
- 当前本机人工验收进程使用临时环境变量关闭自动过期清理；正常配置默认 `RESUME_CLEANUP_ENABLED=true`。Resume 38 仍未绑定且已超过 24 小时，换电脑或正常启动后端前必须再次明确是否保留，否则运行满第一个清理周期后会符合自动删除条件。

优先任务：

1. 下一小步只实现 DeepSeek Adapter：单次 JSON Output 请求、禁用自动模型重试、稳定异常映射和 Fake/Mock 隔离测试；不得实现数据库状态流转或 API。
2. 之后再依次实现 `ResumeStructureService`、结构化解析 API、草稿持久化和新增候选人页自动填充，每个部分继续独立验证。
3. 实现依据为 `docs/specs/2026-08-12-stage5-resume-structure-design.md`；如需改变一次调用、不用 Agent/LangGraph、HR 最终确认等核心决定，必须先与用户重新确认并同步文档。
4. 阶段 5 只处理简历结构化草稿；岗位匹配、AI 初筛、报告生成、扫描件 OCR和自动重复候选人判定仍不提前进入。

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
