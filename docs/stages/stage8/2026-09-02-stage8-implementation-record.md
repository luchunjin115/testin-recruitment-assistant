# 阶段 8：公开投递与异步自动处理实施记录

> 建立日期：2026-09-02
>
> 当前状态：8A—8F 已完成；项目负责人于 2026-09-02 完成浏览器检查并确认阶段 8 最终验收通过
>
> 业务合同：[阶段 8 公开投递与异步处理设计](2026-09-02-stage8-public-application-async-processing-design.md)
>
> 当前进度与唯一下一步：`PROJECT_STATE.md`

## 1. 文档职责

本文是阶段 8 唯一实施记录，按 8A—8F 记录每个批次实际完成了什么、修改位于哪一层、验证结果能证明什么、不能证明什么以及遗留风险。

本文不重新定义公开表单、重复申请、身份解析、状态、失败语义、隐私或权限。业务规则发生变化时，必须先修改阶段 8 设计并重新确认；当前阶段和唯一下一步仍只在 `PROJECT_STATE.md` 维护。

后续每完成一个批次，直接更新本文对应章节，不另建并行流水、一次性运行器说明或第二份实施日志。详细命令和中间失败由 Git 历史恢复，只保留对理解实现和验收有用的最终事实。

## 2. 批次总览

| 批次 | 状态 | 完成日期 | 最终结果 |
| --- | --- | --- | --- |
| 8A 合同与 migration | 已完成 | 2026-09-02 | 固定公开 Schema/枚举，新增 Submission/ProcessingRun ORM 与 PostgreSQL 合同，迁移和回归通过 |
| 8B 可靠公开受理 | 已完成 | 2026-09-02 | 公开 Job/投递 API、限流、文件补偿、Candidate 解析、幂等与安全错误已实现并通过真实 PostgreSQL/API/Redis 验证 |
| 8C 持久 Worker 与流水线 | 已完成 | 2026-09-02 | PostgreSQL 任务领取、租约恢复、固定步骤、失败隔离和阶段 7 状态对账已实现并通过真实 Worker 验证 |
| 8D 候选人 `/apply` | 已完成 | 2026-09-02 | 公开岗位、真实 multipart 投递、幂等重试、成功/失败反馈和响应式样式已实现，并在 8F 完成项目负责人浏览器检查 |
| 8E HR 正常池与异常区 | 已完成 | 2026-09-02 | 公开投递直接进入现有统一初筛列表；安全摘要/详情、处理筛选、异常提示、身份核对、简历选择审计、只读草稿和人工重试已实现并通过完整回归 |
| 8F 完整验收 | 已完成 | 2026-09-02 | 自动化、migration、真实 PostgreSQL/API/Worker、前端构建、真实模型链路和项目负责人浏览器/最终产品验收全部完成 |

## 3. 8A：合同与 migration

### 3.1 本批次完成的事情

#### Schema 层

- 新增 `backend/app/schemas/public_application.py`，固定公开岗位响应、公开投递表单、成功响应和稳定公开错误码。
- 固定身份核对状态与原因、ProcessingRun trigger、状态、步骤、等待原因、warning code 和安全错误字段。
- 为 `PublicApplicationSubmission` 和 `ApplicationProcessingRun` 增加独立 Create/Read Schema，并在 Pydantic 层校验状态组合、终态错误、warning、租约和时间字段。
- 公开投递 Schema 拒绝 `source`、Candidate/Application ID、HR 决策等内部字段；`source=public_apply` 仍只能由未来 Service 设置。
- 新增 `StageHistoryReasonCode.PUBLIC_APPLICATION_RECEIVED`，供后续 8B 创建公开 Application 的初始审计使用；本批次没有写入 StageHistory。

预检发现阶段 8 设计允许 254 字符邮箱，而既有 `Candidate.email` Schema、ORM 和 PostgreSQL 只有 100 字符。项目负责人确认保留 254 字符公开合同后，本批次同步扩展 `CandidateCreate`、`CandidateUpdate`、ORM 和数据库列，避免请求通过 Schema 后在持久化层失败。

#### Model 层

- 新增 `PublicApplicationSubmission`，保存 Application/Resume 关联、公开凭证、幂等键摘要、请求指纹、隐私同意版本/时间和身份核对状态。
- Submission 不保存原始幂等键、IP、User-Agent、完整表单、简历正文、Prompt 或模型响应。
- 新增 `ApplicationProcessingRun`，保存阶段 8 固定流水线的 trigger、状态、当前步骤、编排尝试次数、等待原因、安全错误、warning、开始/完成时间和 Worker 租约。
- 补齐 Application、Resume、Submission 和 ProcessingRun 关系；复合外键冻结每个 Run 对应的 Application 和 Resume，不能与 Submission 身份错配。
- ORM mapper 在 warning-as-error 模式下完成配置，没有关系覆盖或歧义告警。

#### PostgreSQL 层

- 新增向前 migration `a8d4f2c7e901`，上游 revision 为阶段 7 head `e7f9a1b3c545`；没有修改任何既有 migration。
- 新增 `public_application_submissions` 和 `application_processing_runs` 两张表。
- Submission 增加 Application、Resume、公开凭证、幂等摘要唯一约束，以及引用格式、SHA-256、同意版本和身份核对一致性 CHECK。
- ProcessingRun 增加状态/步骤/trigger/尝试次数/等待原因/安全错误/warning/租约一致性 CHECK，以及 Worker 领取和 HR 查询所需索引。
- 部分唯一索引保证同一 Submission 最多存在一个 `queued / running / waiting_screening` Run；`paused / failed / succeeded / succeeded_with_warnings` 作为历史 Run 不占用 active 唯一位置，后续才能保留旧 Run 并创建人工重试。
- 所有新业务外键使用 `RESTRICT`；downgrade 在发现超过 100 字符的 Candidate 邮箱时会明确阻止有损收窄。

### 3.2 主要文件

| 文件 | 层次 | 职责 |
| --- | --- | --- |
| `backend/app/schemas/public_application.py` | Schema | 公开输入输出、持久对象和状态枚举合同 |
| `backend/app/schemas/candidate.py` | Schema | Candidate 邮箱上限同步到 254 |
| `backend/app/schemas/stage_history.py` | Schema/审计 | 增加公开投递初始 reason code |
| `backend/app/models/public_application_submission.py` | Model | 公开受理事实 ORM |
| `backend/app/models/application_processing_run.py` | Model | 阶段 8 持久流水线运行 ORM |
| `backend/app/models/application.py`、`resume.py` | Model | 补齐新对象关系 |
| `backend/app/models/candidate.py` | Model | Candidate 邮箱列映射扩展到 254 |
| `backend/migrations/versions/a8d4f2c7e901_add_public_application_processing_contract.py` | PostgreSQL | 两张新表、约束、索引和邮箱扩容 |
| `backend/tests/schemas/test_public_application.py` | 测试 | 公开合同、枚举和状态组合 |
| `backend/tests/models/test_stage8_public_application_models.py` | 测试 | ORM 列、外键、CHECK 和部分唯一索引 |
| `backend/tests/migrations/test_stage8_public_application_migration.py` | 测试 | revision、表结构和 downgrade 保护 |

### 3.3 验证结果

- 实施前开发 PostgreSQL 为 `e7f9a1b3c545 (head)`，`alembic check` 无漂移；Candidate、Resume、Application、Job、评价计划、报告、Run 和 StageHistory 各 1 行，既有外键孤儿为 0。
- 8A 定向测试：`25 passed, 43 subtests passed`。
- 完整后端回归：`1328 passed, 448 subtests passed`。
- 完整回归保留两个既有非阻塞 warning：PyPDF2 弃用提示，以及一处测试结束时的异步连接清理提示。
- 临时 PostgreSQL 从空库完整升级到 `a8d4f2c7e901`，然后执行 `downgrade e7f9a1b3c545 → upgrade head`；降级后两张新表消失且邮箱恢复 100，重新升级后结构恢复。
- 在临时 PostgreSQL 中用事务内虚构数据验证：254 字符邮箱可写入，第二个 active ProcessingRun 被部分唯一索引拒绝，Run 与 Submission 的 Resume 身份错配被复合外键拒绝；测试事务最终回滚。
- 临时数据库最终已删除，没有保留测试业务数据。
- 开发 PostgreSQL 只执行向前升级，最终 `current=head=a8d4f2c7e901`，`alembic check` 无待生成操作；原有 8 类业务表行数未变，两张阶段 8 新表均为 0 行。

### 3.4 这些结果能证明什么

- 阶段 8 公开数据合同、ORM metadata 和实际 PostgreSQL 结构一致。
- 新表可以从既有阶段 7 head 安全创建、撤销并重新创建。
- 数据库会实际拦截重复 active Run、非法状态组合和 Submission/Run 身份错配，而不只是在 Python 测试中声明约束。
- 新模型导入和 Candidate 邮箱扩容没有破坏当前后端回归。

### 3.5 这些结果不能证明什么

- 公开 Job/Application API 尚不存在，候选人还不能真实提交。
- Candidate 解析、重复申请、幂等锁、文件临时区/提升/补偿和事务编排尚未实现。
- Worker、`SKIP LOCKED`、租约恢复、结构化 warning 和阶段 7 初筛衔接尚未实现。
- `/apply`、HR 正常池/异常区、真实并发、浏览器体验和完整阶段 8 链路尚未验证。
- 没有调用 DeepSeek，也不能证明 AI 结果、招聘准确率、互联网规模或公网安全能力。

### 3.6 剩余风险和停止点

- 私有存储预检发现 1 个数据库有效引用文件和 2 个未引用文件；本批次没有移动或删除它们，后续文件清理仍必须先确认精确引用。
- 一旦未来写入超过 100 字符的 Candidate 邮箱，8A migration 的 downgrade 会按设计阻止有损收窄，需要先处理数据而不能强制降级。
- 8B 必须在一个可靠受理事务中实现 Candidate、Resume、Application、Submission 和初始 Run 的一致创建；8A 只提供持久边界，不代表这条业务链已经接通。
- 若 8B 发现必须改变已确认的公开字段、重复申请、身份解析、文件事务或错误语义，应停止实现并回到阶段 8 设计重新确认。

### 3.7 本批次明确没有做

- 没有实现 `/api/v2/public/jobs` 或 `/api/v2/public/applications`。
- 没有实现公开投递 Service、Candidate 解析、文件上传编排或 Redis 限流。
- 没有启动阶段 8 Worker，没有修改前端或 HR 工作台。
- 没有使用真实候选人数据，没有调用 DeepSeek，没有产生费用。
- 没有提交或推送 Git。

## 4. 8B：可靠公开受理

### 4.1 本批次完成的事情

#### API 与 Schema 边界

- 新增独立公开 Router，正式提供 `GET /api/v2/public/jobs`、`GET /api/v2/public/jobs/{job_id}` 和 `POST /api/v2/public/applications`。
- 公开岗位列表和详情只查询 `open` 岗位，并通过独立 `PublicJobRead` 输出候选人可见字段；`headcount`、岗位状态、内部时间和 AI/计划字段不会进入响应。
- 公开投递使用一次 multipart 请求，OpenAPI 明确把姓名、手机、邮箱、岗位、隐私同意、同意版本、幂等 UUID 和 Resume 列为必填。
- 公开投递校验会拒绝未知字段、重复字段、失效同意版本和缺失文件；所有已确认失败场景映射到稳定公开错误码，响应不包含数据库约束、内部路径、Candidate/Application/Resume ID 或异常原文。
- 增加只作用于公开投递路径的请求体上限；默认允许 10 MB 文件加 256 KiB multipart 开销，超限在进入路由依赖前返回安全 `413`。

#### Service 与文件层

- 新增 `PublicApplicationService`，在一个 PostgreSQL 事务中锁定幂等摘要、联系方式和 open Job，解析 Candidate 后一致创建 Resume、Application（需要时）、PublicApplicationSubmission、初始 ProcessingRun 和初始 StageHistory（只在新建公开 Application 时）。
- 手机和邮箱同时精确命中同一 Candidate 时复用；完全未命中时新建；部分命中、拆分命中或只有同名时新建 Candidate，并把受控人工核对原因写入 Submission。服务端固定 `source=public_apply`。
- 相同幂等键与相同请求指纹返回原凭证；同键不同内容安全拒绝。既有公开 active Application 返回原凭证且不保存第二份文件；既有内部 active Application 保存本次 Resume 和提交/任务，但不切换 `current_resume_id`、不伪造 StageHistory；存在 ended/voided 历史时不自动重投。
- Resume 文件继续复用现有私有存储实现；在暂存阶段完成扩展名、实际内容、大小、路径和 DOCX ZIP 安全检查，并新增 SHA-256 摘要。数据库提交前提升文件；提升失败回滚，提交失败补偿删除已提升文件；清理失败只记录文件摘要前缀，不把路径写入公开响应。
- 初始 ProcessingRun 只写入 `queued / extract_text / automatic`，本批次没有领取或执行任务，没有调用解析、结构化、阶段 7 初筛或 DeepSeek。

#### Redis 与配置

- 新增 Redis 固定窗口短期限流，对直连客户端 IP、标准化手机号和邮箱分别计数；Redis key 只包含 SHA-256 摘要，不保存原始联系方式或 IP。
- 默认窗口 60 秒，单 IP 10 次、单手机号/邮箱 3 次；命中时返回 `429` 和 `Retry-After`，Redis 不可用时 fail closed 返回安全 `503`，不会绕过保护继续接收。
- `.env.example` 增加隐私说明版本、限流和 multipart 开销配置。Redis 仍不是投递事实或业务队列，真实受理和初始任务只以 PostgreSQL 为准。

### 4.2 主要文件

| 文件 | 层次 | 职责 |
| --- | --- | --- |
| `backend/app/api/public.py` | API | 公开岗位/投递路由、multipart、请求体上限、限流入口和稳定错误 |
| `backend/app/services/public_job_service.py` | Service | 只读 open Job 查询 |
| `backend/app/services/public_application_service.py` | Service | Candidate 解析、幂等、重复申请、事务和文件补偿编排 |
| `backend/app/services/public_application_rate_limiter.py` | Service/Redis | IP 与联系方式摘要限流、`Retry-After` 和 fail-closed 语义 |
| `backend/app/services/resume_storage.py` | 文件层 | SHA-256、DOCX ZIP 安全、暂存/提升/补偿删除 |
| `backend/app/core/config.py`、`.env.example` | 配置 | 同意版本、限流阈值和请求开销上限 |
| `backend/app/main.py` | 应用装配 | 注册公开 Router、请求体 middleware 和公开校验错误处理 |
| `backend/tests/api/test_public.py` | 测试 | 公开字段白名单、multipart、错误、限流和请求体上限 |
| `backend/tests/services/test_public_application_rate_limiter.py` | 测试 | Redis 摘要键、超限和不可用语义 |
| `backend/tests/services/test_public_application_service_postgres.py` | PostgreSQL/API 测试 | 完整受理图、重复/身份分支、补偿回滚和真实 multipart |
| `backend/tests/services/test_resume_upload_service.py` | 文件测试 | SHA-256 与 DOCX 高压缩比拒绝 |

### 4.3 验证结果

- 8A/8B 与既有相关能力联合定向测试：`66 passed`。
- 完整后端 pytest 回归：`1353 passed, 454 subtests passed`；仍只有 PyPDF2 弃用提示和既有异步连接清理提示两个非阻塞 warning。
- 真实开发 PostgreSQL 测试通过：multipart 请求实际创建 Candidate、Resume、Application、Submission、ProcessingRun 和系统 StageHistory，测试使用外层事务回滚，运行前后各相关表行数一致。
- 真实 PostgreSQL 分支验证通过：同幂等重试、不同内容冲突、既有公开申请复用、既有内部 active Application 保留旧当前 Resume、ended/voided 历史拦截、联系方式冲突和同名人工核对，以及文件提升/数据库提交故障补偿。
- 随机临时 PostgreSQL 从空库迁移到 head 后，并发发送两次相同虚构提交：两次返回同一公开凭证，复用标记为一新一旧，最终 Candidate、Resume、Application、Submission、ProcessingRun 各 1 行且只有 1 个正式文件；临时数据库随后删除并确认残留为 0。
- 真实 Redis `PING` 和限流 Lua 脚本执行成功；使用随机虚构摘要键和 2 秒 TTL，没有写入业务事实或队列。
- 当前 Alembic `current=head=a8d4f2c7e901`，`alembic check` 输出 `No new upgrade operations detected`；开发库阶段 8 两张表仍为 0 行。
- `compileall`、OpenAPI multipart 注册和 `git diff --check` 通过；OpenAPI 中 8 个公开投递字段全部为 required。

### 4.4 这些结果能证明什么

- 后端现在能够可靠受理一份虚构公开投递，并保证数据库对象和正式文件要么一起成功，要么回滚并执行补偿清理。
- 公开岗位响应有独立白名单，公开错误不会泄露内部主键、约束名、文件路径或异常详情。
- 已确认的 Candidate 身份、重复申请和幂等语义在真实 PostgreSQL 中按合同执行；相同并发请求只留下一个业务结果。
- Redis 限流失效时不会无保护放行；限流键和数据库提交事实相互独立。
- 8B 没有触发原文解析、结构化、AI 初筛或任何模型费用。

### 4.5 这些结果不能证明什么

- 新 ProcessingRun 目前只停在 `queued / extract_text`；没有阶段 8 Worker，因此不能证明领取、租约恢复、步骤跳过、warning、暂停或阶段 7 初筛衔接。
- `/apply` 前端尚未接通，候选人目前只能通过 API 合同投递；没有完成浏览器交互、可访问性或移动端验收。
- HR 正常池、异常区、简历选择、身份核对和人工重试入口尚不存在。
- 没有使用真实候选人数据，没有调用 DeepSeek，也不能证明公网级容量、分布式拒绝服务防护或恶意文件扫描能力。

### 4.6 剩余风险和停止点

- 当前请求体上限 middleware 会在应用进程内最多缓冲约 10.25 MB multipart 内容，适合作品集和本地演示；正式公网部署仍需要反向代理层大小/并发限制和阶段 12 的恶意文件扫描评估。
- 限流使用直连客户端 IP。未来若部署在可信反向代理后，需要显式配置可信代理和真实客户端 IP 解析，不能直接信任任意 `X-Forwarded-For`。
- 本批次保留 8A 发现的既有私有存储文件，没有移动或删除；孤儿文件长期回收仍需精确引用核对。
- 若 8C 发现必须改变已确认的 Run 状态、步骤、等待原因或阶段 7 衔接语义，应停止并回到阶段 8 设计确认，不能在 Worker 内另造合同。

### 4.7 本批次明确没有做

- 没有启动阶段 8 Worker，没有消费 queued Run。
- 没有实现 Candidate 原文解析、结构化或初筛编排，没有调用 DeepSeek、没有产生费用。
- 没有修改 `/apply` 前端，没有实现 HR 正常池、异常区、身份核对或人工重试。
- 没有使用真实候选人数据，没有提交或推送 Git。

## 5. 8C：持久 Worker 与流水线

### 5.1 本批次完成的事情

#### Service 与 Worker 层

- 新增 `ApplicationProcessingService`，使用 PostgreSQL `FOR UPDATE SKIP LOCKED` 领取 `queued`、待对账和恢复条件已满足的暂停 Run；任务事实、当前步骤、尝试次数和租约全部保存在数据库，不建立内存权威队列。
- 实现 `extract_text → structure_resume → trigger_screening → await_screening → completed` 固定步骤。原文提取复用阶段 4 `ResumeService`，结构化复用阶段 5 `ResumeStructureService`，初筛只调用阶段 7 `ScreeningService`，没有在阶段 8 直接写模型表或直接调用初筛模型。
- 每个步骤前续租，外部结构化调用期间不持有 Run 行锁；成功原文和合法结构化草稿由既有 Service 自动复用，Worker 重启或人工重试不会为了重跑整链重复调用成功步骤。
- 原文提取的确定性失败进入 `failed` 并保留原文件和业务记录；结构化内容失败或有限基础设施重试耗尽只追加 `RESUME_STRUCTURE_FAILED` warning，仍继续触发初筛。
- 阶段 7 `waiting_resume / waiting_plan / queued / running` 映射为 `waiting_screening`，成功映射为 `succeeded` 或 `succeeded_with_warnings`，失败安全映射为 `failed`，岗位关闭和既有内部 Application 未选择新 Resume 映射为受控 `paused`。
- 岗位重新开放或 HR 已把公开 Resume 选为当前 Resume 后，暂停 Run 可自动重新领取；已有内部 Application 不会被 Worker 静默切换当前简历。
- 编排自动尝试上限固定为 3，同一步基础设施重试上限为 2，退避和租约均有配置边界；租约过期会重新排队，达到上限后安全失败，`await_screening` 对账不会消耗新的编排尝试。
- 实现人工重试的 Service 能力：只允许失败或恢复条件已满足的暂停任务创建新的 `manual_retry` Run，旧 Run、成功原文、草稿、报告和文件均保留。8C 没有增加 HR API 或页面入口。
- 新增独立 Application Processing Worker 循环并接入 FastAPI lifespan；启动和关闭与既有简历清理、阶段 7 Screening Worker 分开管理，多进程依靠数据库租约协调。

#### 配置与 PostgreSQL 行为

- `.env.example` 和 `Settings` 增加 Worker 开关、轮询间隔、租约、批量大小、编排尝试、步骤基础设施重试和退避配置。
- 配置校验保证 Worker 租约覆盖一次结构化调用及其有限重试的最坏超时时间，避免默认配置下调用尚未返回、租约却已过期。
- 8C 没有新增或修改 migration、表、字段、约束或状态枚举；继续使用 8A 已固定的 `ApplicationProcessingRun` PostgreSQL 合同。

### 5.2 主要文件

| 文件 | 层次 | 职责 |
| --- | --- | --- |
| `backend/app/services/application_processing_service.py` | Service/Worker | PostgreSQL 领取、租约、固定步骤、失败隔离、暂停恢复、人工重试和阶段 7 对账 |
| `backend/app/main.py` | 应用装配 | 启动和安全停止独立 Application Processing Worker |
| `backend/app/core/config.py`、`.env.example` | 配置 | Worker 上限、尝试次数、步骤重试、退避和租约安全校验 |
| `backend/tests/services/test_application_processing_service_postgres.py` | PostgreSQL 测试 | 完整非模型链路、步骤复用、warning、终态映射、暂停恢复、租约和历史 Run |
| `backend/tests/test_config.py` | 配置测试 | 8C 默认值、上下限和租约覆盖关系 |

### 5.3 验证结果

- 8C Service 真实 PostgreSQL 直接测试：`10 passed`。覆盖完整非 AI 步骤、成功事实跳过、阶段 7 成功/失败对账、结构化 warning、两次基础设施重试、岗位关闭/开放、租约耗尽、人工重试历史和内部 Application 简历选择。
- 阶段 4/5/7 被复用 Service 与 8C 联合回归：`93 passed, 34 subtests passed`。
- 完整后端回归：`1365 passed, 460 subtests passed`；仍只有 PyPDF2 弃用提示和既有异步连接清理提示两个非阻塞 warning。
- 随机临时 PostgreSQL 中让 3 个 Worker 并发领取 2 条 queued Run，最终恰好领取 2 条且 Run ID、租约所有者均不重复；租约过期后由新 Worker 以第 2 次编排尝试恢复。
- 另一随机临时 PostgreSQL 中启动真实 Worker 循环，成功恢复一条 `dead-worker` 遗留的过期 Run：ProcessingRun 进入 `waiting_screening`，复用的阶段 7 Service 创建 `waiting_plan` ScreeningRun，尝试次数从 1 变为 2；临时数据库均已删除，残留为 0。
- 当前开发 PostgreSQL 仍为 `current=head=a8d4f2c7e901`，`alembic check` 无待生成操作；两张阶段 8 表均为 0 行。`compileall` 和 `git diff --check` 通过。
- 所有结构化场景使用假适配器；真实 Worker 验证从 `trigger_screening` 开始并因评价计划缺失停在 `waiting_plan`。本批次没有调用 DeepSeek，没有产生模型费用。

### 5.4 这些结果能证明什么

- API 已受理的 queued Run 可以由独立 Worker 从 PostgreSQL 领取，进程失联后可以靠过期租约恢复，多 Worker 不会重复持有同一条任务。
- 阶段 8 只做流程编排，原文、结构化和初筛分别遵守阶段 4/5/7 的现有 Service 合同；成功事实可复用，结构化失败不阻塞初筛。
- 等待、暂停、失败、成功和带 warning 成功会落到 8A 固定的状态组合，达到自动尝试上限后不会无限循环。
- 人工重试可以保留历史 Run，但目前只存在后端 Service 能力，尚没有对 HR 暴露入口。

### 5.5 这些结果不能证明什么

- 没有执行真实 DeepSeek 结构化或初筛，不能证明真实模型响应、token、费用或 AI 质量；阶段 8 最小真实链路仍需在 8F 前单独授权。
- `/apply` 前端尚未接通，候选人还没有浏览器表单体验；这是 8D 范围。
- HR 正常池、异常区、身份核对、简历选择和人工重试 UI/API 尚未实现；这是 8E 范围。
- 当前验证适合作品集和本地演示，不证明公网高并发、恶意文件防护、生产监控告警或长期运行稳定性。

### 5.6 剩余风险和停止点

- `waiting_screening` 当前按固定短周期轮询 PostgreSQL，满足本地演示；若未来扩大为高流量部署，需要评估退避、通知或独立进程监控，不能在不更新设计的情况下另造队列事实。
- Worker 目前随 FastAPI lifespan 启动。数据库锁和租约支持多实例正确领取，但生产级进程监督、指标、告警和优雅部署仍未建设。
- 实际存在 queued Run 时，Worker 的结构化步骤会按阶段 5 配置调用模型；在执行阶段 8 真实链路验收前，仍必须先按项目门禁说明模型、次数、价格和费用上限并获得授权。

### 5.7 本批次明确没有做

- 没有修改阶段 8 Schema、Model 或 PostgreSQL migration 合同。
- 没有修改 `/apply` 前端，没有实现 HR 正常池、异常区或任何 HR API。
- 没有新增 Redis 业务队列，没有把内存或 Redis 作为任务事实。
- 没有使用真实候选人数据，没有调用 DeepSeek，没有产生费用。
- 没有提交或推送 Git。

## 6. 8D：候选人 `/apply`

### 6.1 当前状态

代码实现、前端自动化、生产构建和后端公开 API 回归已经完成。当前运行环境没有可连接的浏览器，因此 1440×900、820×1180、390×844 的实际渲染、键盘操作和焦点移动尚未形成浏览器证据。项目负责人已于 2026-09-02 明确接受该限制，将由其后续手工打开网页检查，并同意进入 8E；因此 8D 按负责人验收结论标记完成，但浏览器证据缺口仍如实保留。

### 6.2 已完成的事情

#### 前端 Service 层

- 将 `/apply` 从内部 `/jobs?status=open` 切换到独立 `GET /api/v2/public/jobs`，只映射候选人可见岗位字段，不读取 `status`、`headcount`、内部时间或计划/AI 字段。
- 新增 `POST /api/v2/public/applications` multipart 调用，严格只发送姓名、手机、邮箱、岗位、隐私同意、同意版本、浏览器生成的幂等 UUID 和一份 Resume。
- 新增公开错误白名单。只有 8B 固定的公开错误码和安全中文说明能进入页面；未知错误、内部约束或路径统一退化为普通网络失败文案。
- 支持读取 `Retry-After`；相同表单和同一个文件的失败重试复用幂等键，修改内容或更换文件时生成新键。服务端明确报告幂等冲突后，下次人工重试会生成新键。

#### React 页面与交互

- 删除“预览、不会提交”、内部工作台返回入口、教育背景、技能、个人简介和旧 `.doc`；页面只保留阶段 8 已确认的六类输入。
- 公开岗位下拉显示名称、部门和地点；选中后展示地点、用工类型及五段候选人可见 JD。岗位文本只通过 React 文本节点渲染，不注入 HTML。
- 姓名、手机号、邮箱和岗位使用明确必填/长度/格式校验；Resume 只允许 PDF、DOCX、TXT，最大 10 MB，文件缺失或不合法时将焦点移到上传区。
- 隐私同意为必选项，页面显示当前版本 `2026-09-02`，并明确作品集只能使用虚构或完整脱敏资料。
- 同步提交门闩阻止重复点击。网络或公开业务错误不会清空表单和文件；岗位关闭竞态会清除失效岗位并重新读取公开岗位。
- 成功页显示不透明公开凭证和受理时间，并明确“受理成功不等于 AI 完成或 HR 通过”；不提供内部 ID、AI 结果或虚假公开进度查询。

#### 视觉、响应式和可访问性

- 保留产品蓝色体系，以“申请资料夹”为页面视觉记忆点：顶部脊线分别反馈岗位、简历和隐私同意是否就绪；其余区域保持安静、偏文档式的信息层级。
- 桌面使用流程侧栏和申请资料双列布局；CSS 在 900px 以下切换单列，在 600px 以下把表单、岗位详情、收据和操作区改为单列，并主动阻止横向溢出。
- 增加 `:focus-visible`、上传错误/提交错误 `role=alert`、成功标题程序聚焦、语义化 `main/section/article/dl`，并尊重 `prefers-reduced-motion`。

### 6.3 主要文件

| 文件 | 层次 | 职责 |
| --- | --- | --- |
| `frontend/src/features/recruitment/services/application.ts` | 前端 Service | 公开 Job 映射、multipart 投递、幂等字段和安全错误解析 |
| `frontend/src/features/recruitment/RecruitmentApplicationForm.tsx` | React | 岗位选择、表单、文件、隐私、提交、重试和成功反馈 |
| `frontend/src/features/recruitment/styles/application.css` | UI/CSS | 申请资料夹视觉、三档响应式、焦点和 reduced-motion |
| `frontend/tests/stage8-public-application-service.test.mjs` | Service 测试 | 公开端点、字段白名单、multipart、响应和错误安全 |
| `frontend/tests/stage8-public-application-ui.test.mjs` | UI 合同测试 | 字段删改、幂等交互、错误保留、可访问性和响应式规则 |
| `frontend/tests/recruitment-job-read-boundaries.test.mjs` | 跨页面回归 | `/apply` 公开 Job 与内部工作台 Job 读取边界 |
| `frontend/package.json` | 测试入口 | 增加两个 8D 直接测试命令 |

### 6.4 已完成验证

- 8D Service、UI 和正式路由直接测试均通过。
- 前端全部 `26` 个 `.test.mjs` 测试文件通过。
- `npm run build` 通过：TypeScript 和 Vite production build 均成功。
- 后端公开 API 回归：`10 passed, 6 subtests passed`，只有既有 PyPDF2 弃用 warning。
- 开发 PostgreSQL 的 `public_application_submissions` 和 `application_processing_runs` 仍均为 0 行；8D 没有发送真实投递，没有触发 Worker 或 DeepSeek。

### 6.5 这些结果能证明什么

- 前端请求字段、公开端点、成功响应和安全错误与 8B 后端合同一致，页面不再依赖内部 Job API。
- TypeScript 能完整编译，现有阶段 5—7 前端合同没有被 8D 改坏。
- 旧无效字段、旧 `.doc`、内部入口和预览文案已退出运行代码；代码层存在桌面、平板、手机和键盘/减少动态效果保护。
- 普通失败会保留表单与文件，重复点击和网络重试具备前端幂等保护。

### 6.6 尚不能证明和剩余风险

- 浏览器连接返回“无可用浏览器”，因此尚不能证明三个目标视口真实无横向溢出，也不能证明真实浏览器中的拖拽、Tab 顺序、焦点移动、成功页和失败页视觉效果。静态 CSS 断言和 build 不能替代这项证据。
- 前端与后端当前分别固定隐私说明版本 `2026-09-02`；未来变更版本时必须同步发布，否则后端会按安全合同拒绝旧页面。
- 实际向开发 API 成功投递会创建 queued Run，而 8C Worker 默认启用并可能触发模型。浏览器验收必须使用受控假 API，或在明确关闭阶段 8/7 Worker 且完成测试数据补偿方案后进行，不能直接用真实联系方式试投。
- 真实浏览器视觉与键盘检查仍由项目负责人后续手工完成；这不再作为进入 8E 的停止点。

### 6.7 后续人工检查

项目负责人后续使用受控假 API 检查 1440×900、820×1180、390×844 三尺寸、键盘/焦点、成功、网络失败、岗位空状态和文件校验；不得直接向启用 Worker 的开发 API 写入真实联系方式或 queued Run。

## 7. 8E：HR 正常池与异常区

### 7.1 当前状态

已完成。项目负责人确认公开投递不进入独立工作区，而是直接进入现有 AI 初筛中心；正常池和异常区只作为统一列表的来源/处理状态筛选。阶段 8 设计 15.3 已按该确认修订，生产实现与合同一致。

### 7.2 已完成的事情

#### 后端 Schema 与 API

- 新增专用 HR 工作台摘要、详情、身份候选人、处理 Run 摘要和二次确认 Schema。没有复用包含幂等摘要、请求指纹和 Worker 租约的底层持久化 Schema。
- 新增内部公开投递列表、详情、身份核对和人工重试 API；支持按正常/异常、岗位和精确处理状态查询，错误统一映射为阶段 8 已确认的安全错误。
- 新增已保存结构化结果的只读 `GET` 入口，只调用现有 `get_current_result()`；没有结果返回稳定 404，不会启动结构化 Adapter 或模型调用。

#### 后端 Service 与审计

- 工作台查询一次关联 Submission、Application、Candidate、Job、Resume 和最新 ProcessingRun；详情按需读取安全 Run 历史和身份核对候选人。
- 身份核对只执行 `needs_review → reviewed` 并保留原因；重复核对幂等，不合并、不删除、不改写 Candidate，写入 `public_application_identity_reviewed` ActivityLog。
- 8C 人工重试继续新建 `manual_retry` Run、保留旧 Run 和成功事实，并补充 `public_application_manual_retry` ActivityLog；暂停原因未恢复时返回独立安全错误。
- 现有切换当前简历 Service 补充 `application_current_resume_changed` ActivityLog，记录旧/新 Resume，不伪造 StageHistory。
- 本批次没有新增 Model、数据库表、字段或 migration。

#### 统一初筛中心前端

- `getStage7ScreeningCenter()` 在读取现有 Application、Candidate、Job 和阶段 7 初筛状态时，同时关联公开投递安全摘要；公开投递和 HR 录入仍共用同一份列表。
- 现有列表新增来源和自动处理状态筛选；“公开投递 · 正常”和“公开投递 · 需人工处理”只是筛选条件，没有新增路由、页面、Tab 或独立工作区。
- 公开投递行显示公开凭证、文件名、身份提醒和“受理 → 原文 → 结构化 → 初筛”处理轨迹；颜色之外同时使用图标和文字。
- 现有 AI 报告抽屉顶部按公开来源显示处理详情，复用原文件、原文、报告和 HR 决策入口；新增已保存结构化结果查看、身份已核对、当前简历选择和人工重试。
- 只有抽屉打开且 Run 非终态时才每 4 秒刷新，累计最多 30 次；关闭抽屉、终态或达到上限后停止。人工重试会重新开始一轮有界刷新。
- 身份核对和人工重试均有二次确认，失败保留当前上下文并只显示安全说明；只读结构化结果明确提示不会启动 AI。

### 7.3 主要文件

| 文件 | 层次 | 职责 |
| --- | --- | --- |
| `backend/app/schemas/public_application_workbench.py` | Schema | 固定 HR 可见摘要/详情、处理 Run、身份候选人与确认请求，排除内部敏感字段 |
| `backend/app/services/public_application_workbench_service.py` | Service | 统一队列查询、正常/异常分池、详情、身份核对和安全映射 |
| `backend/app/api/public_application_workbench.py` | API | 内部列表/详情/身份核对/人工重试端点与稳定错误 |
| `backend/app/api/resumes.py` | API | 增加已保存结构化结果的只读 GET，不触发模型 |
| `backend/app/services/application_processing_service.py` | Service | 人工重试审计与暂停未恢复的独立错误 |
| `backend/app/services/screening_service.py` | Service | 切换当前简历写 ActivityLog |
| `frontend/src/features/recruitment/services/publicApplicationWorkbench.ts` | 前端 Service | 工作台 API 映射、安全错误和正常/异常判断 |
| `frontend/src/features/recruitment/services/screening.ts` | 前端聚合 | 将公开 Submission 摘要关联到现有 Application 队列 |
| `frontend/src/features/recruitment/RecruitmentScreeningCenter.tsx` | React | 统一列表的来源/处理筛选、公开凭证、状态和处理轨迹 |
| `frontend/src/features/recruitment/PublicApplicationProcessingPanel.tsx` | React | 原抽屉内的处理详情、轮询、原文/草稿、身份核对、简历选择和重试 |
| `frontend/src/features/recruitment/styles/screening.css` | UI/CSS | 处理轨迹、异常信息、身份候选人和响应式布局 |
| `backend/tests/api/test_public_application_workbench.py` | API 测试 | 安全字段、确认、错误和路由边界 |
| `backend/tests/services/test_public_application_workbench_service_postgres.py` | PostgreSQL 测试 | 统一查询、分池、身份不合并、历史保留和三类审计 |
| `frontend/tests/stage8-public-application-workbench.test.mjs` | 前端测试 | API 映射、统一列表、只读草稿、动作、轮询和错误安全 |

### 7.4 已完成验证

- 8E 后端 API、Resume API 和真实 PostgreSQL 直接验证：`59 passed, 28 subtests passed`；只有既有 PyPDF2 弃用 warning。
- 加入阶段 8 Worker 与阶段 7 初筛影响面的组合验证：`106 passed, 28 subtests passed`。
- 完整后端回归：`1377 passed, 467 subtests passed`；保留 PyPDF2 弃用和一个既有异步连接清理 RuntimeWarning。
- 前端全部 `27` 个 `.test.mjs` 测试文件通过；其中新增 8E Service/UI 合同测试，既有阶段 7 初筛中心测试已更新为统一队列合同。
- `npm run build` 通过：TypeScript 和 Vite production build 均成功。
- 开发 PostgreSQL 仍为 `a8d4f2c7e901 (head)`，`alembic check` 返回 `No new upgrade operations detected.`；8E 无数据库结构变更。
- 开发库 `public_application_submissions=0`、`application_processing_runs=0`；PostgreSQL 动作测试全部由外层事务回滚，没有留下 queued Run。

### 7.5 这些结果能证明什么

- 公开投递会通过 Application ID 进入现有初筛列表，不存在第二套页面或重复工作区；正常/异常只是统一队列筛选。
- HR 页面拿到的 Submission 和 ProcessingRun 数据不包含幂等摘要、请求指纹、租约、文件路径或内部异常。
- 身份核对不会合并 Candidate；人工重试保留旧 Run；切换简历、身份核对和人工重试都有真实 PostgreSQL ActivityLog 证据。
- 查看已保存结构化结果使用 GET 且不会调用写入 Service；没有结果时不会触发 DeepSeek。
- 完整 TypeScript 构建和阶段 4—8 后端回归没有发现被 8E 破坏的现有合同。

### 7.6 尚不能证明和剩余风险

- 按项目负责人的决定，本批次不由 Codex 执行浏览器视觉验收；实际列表密度、抽屉、确认框、三个视口、键盘和焦点体验仍由项目负责人后续手工检查。自动化和 build 不能替代真实浏览器观感。
- 没有创建真实公开投递或启动 Worker 消费，没有调用 DeepSeek，因此不能证明完整真实链路的模型响应、费用和端到端时序；这属于 8F 且需要单独费用授权。
- 当前内部 `/api/v2/*` 与项目其他 HR 接口一样尚未实现登录/RBAC，只适合本地作品集演示；正式公网部署前必须增加认证和权限。
- 统一初筛中心沿用阶段 7 的逐 Application 读取初筛状态方式，8E 另增一次公开投递摘要查询；当前本地数据量可接受，大规模数据需要分页和批量状态查询专项。
- 身份核对候选人根据当前 Candidate 姓名/联系方式生成参考，第一版只记录已核对，不提供 Candidate 合并或长期数据治理。

### 7.7 本批次明确没有做

- 没有新建独立公开投递页面、Tab 或工作区，没有修改候选人 `/apply` 合同。
- 没有新增 Model、migration、Redis 队列或 Worker 类型。
- 没有自动作出 HR 决策，没有自动合并 Candidate。
- 没有使用真实候选人数据，没有调用 DeepSeek，没有产生费用。
- 没有提交或推送 Git。

## 8. 8F：完整验收

### 8.1 当前状态

已完成。8A—8E 的自动化、migration、真实 PostgreSQL/API/Redis/Worker 和前端构建证据已经汇总；8F 新一轮非付费预检没有发现 migration、开发库数据或模型配置冲突。项目负责人随后单独授权的最小真实 DeepSeek 链路已经通过并完成数据清理。

项目负责人于 2026-09-02 手工检查页面，在反馈并复查五段 JD 双栏错位修正后，明确确认“目前阶段 8 可以验收通过”。阶段 8 据此完成最终产品验收并关闭。

### 8.2 已具备的自动化与基础设施证据

- 完整后端回归：`1377 passed, 467 subtests passed`；保留两个既有非阻塞 warning。
- 阶段 8 Worker 与阶段 7 初筛影响面组合：`106 passed, 28 subtests passed`。
- 前端全部 `27` 个 `.test.mjs` 测试文件通过；TypeScript/Vite production build 通过。
- 8A 临时 PostgreSQL 已完成 `upgrade → downgrade → upgrade`；8B/8C 已验证真实 multipart、事务、并发幂等、多 Worker 不重复领取、租约恢复和 Worker 重启。
- 8F 开始时重新核对：Alembic `current=head=a8d4f2c7e901`，`alembic check` 返回 `No new upgrade operations detected.`。
- 8F 开始时开发库 `public_application_submissions=0`、`application_processing_runs=0`，没有遗留公开投递、queued Run 或模型任务。
- 当前模型配置仍为 DeepSeek 官方 API：结构化 `deepseek-v4-flash`，初筛 `deepseek-v4-pro`；两个能力均启用。本轮只读取模型名和服务地址，没有读取或输出 Key。

这些证据能证明代码合同、数据库结构、并发/恢复边界和生产构建在自动化范围内一致；不能证明真实浏览器观感、真实模型响应质量或公网生产能力。

### 8.3 项目负责人手工浏览器检查清单

手工检查使用虚构或完整脱敏数据；真实模型链路另按 8.4 的单独授权和隔离方案执行。

- [x] `/apply` 不显示“预览、不会提交”，也没有返回内部工作台的链接。
- [x] 只显示 open 岗位和候选人可见字段，岗位文本没有被当作 HTML 渲染。
- [x] 姓名、手机、邮箱、岗位、简历和隐私同意的错误提示清楚，错误后焦点位置合理。
- [x] 只接受 PDF、DOCX、TXT，10 MB 大小提示与后端一致。
- [x] 重复点击只表现为一个逻辑提交；成功页显示公开凭证，并说明受理成功不等于 AI 完成或 HR 通过。
- [x] 模拟网络失败后，已填内容和已选文件仍保留，可以安全重试。
- [x] 统一 AI 初筛中心能区分“公开投递受理”“后台处理”“AI 结果”和“HR 决策”，没有新增公开投递独立工作区。
- [x] 统一列表的正常/异常筛选、处理轨迹、身份核对、简历选择和人工重试入口显示及确认交互合理。
- [x] `1440×900`、`820×1180`、`390×844` 三个视口无横向溢出；Tab 顺序、键盘操作和焦点提示可用。
- [x] 页面不显示内部 ID、路径、租约、堆栈、未脱敏内容或其他内部错误。

项目负责人已完成上述检查并确认阶段 8 验收通过。

#### 8F 浏览器检查发现与修正

项目负责人首次打开 `/apply` 后指出岗位 JD 排版错乱：原实现把五段 JD 放入桌面双栏网格，较长的“岗位职责”会单独撑高右列，后续“任职要求”和“加分项”在左右列交错出现；正文只有 11px，进一步削弱了段落边界。公开 API 和前端字段映射经核对没有串线，问题位于 React/CSS 展示层，不是 Schema、Model 或 PostgreSQL 合同错误。

- `RecruitmentApplicationForm.tsx` 将五段 JD 固定为“岗位背景 → 岗位职责 → 任职要求 → 加分项 → 补充说明”，按原始顺序逐段整行渲染，并增加与内容顺序对应的 `01—05` 标记和语义化 section 标题。
- `application.css` 删除 JD 双栏规则，改为单列说明书结构；保留原始换行，正文提升到 13px、1.9 行高，移动端只收窄编号栏，不改变段落顺序。
- `stage8-public-application-ui.test.mjs` 增加五段固定顺序、桌面每段独占一行和禁止恢复双栏网格的保护断言。
- 修正后 `/apply` Service/UI 直接测试通过，全部 `27` 个前端测试文件通过，TypeScript/Vite production build 通过。

上述自动化证明字段顺序和单列布局规则已进入代码并可构建；项目负责人随后完成实际浏览器复查并接受当前观感，该问题关闭。

### 8.4 最小真实 DeepSeek 链路结果

项目负责人已明确授权最多 5 个 API 请求、USD 0.25 硬上限。2026-09-02 使用完全虚构的 TXT 简历、虚构岗位和预置已确认评价计划，在随机临时 PostgreSQL、隔离文件目录和 Redis 短期限流键中执行；没有调用评价计划生成模型。

- 真实路径：`POST /api/v2/public/applications` 返回 `202`，同一事务形成 Candidate、Resume、Application、Submission、初始 ProcessingRun 和初始 StageHistory；随后按现有 Service 顺序推进 ProcessingRun、ScreeningRun 和最终对账。
- 结构化：`deepseek-v4-flash`，Prompt `resume_structure_v1`，Schema `1.0`；1 个 API request，692 input tokens、592 output tokens，`Resume.structure_status=succeeded`。
- 初筛：`deepseek-v4-pro`；1 个 API request，2659 input tokens、319 output tokens，`ScreeningRun.status=succeeded`、`attempt_count=1`、无安全错误，生成一份 current `ScreeningReport`。
- 最终编排：`ApplicationProcessingRun.status=succeeded`、`current_step=completed`，无 warning、无安全错误。
- 总计：2 个 API requests，没有基础设施重试或 Repair，低于授权的 5 次上限。
- 价格与费用：执行时为官方非高峰价，Flash 每百万输入/输出 token USD `0.22/0.66`，Pro 为 USD `0.66/1.98`；按全部输入 cache miss 保守估算 USD `0.00292952`，低于 USD 0.25 上限。价格入口为 [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)。
- 清理：随机临时 PostgreSQL 已删除并确认不存在；Redis 限流键在 60 秒 TTL 后扫描为 0；隔离目录中的简历文件已精确删除并确认文件数为 0。执行环境阻止删除空目录骨架，里面不含文件或业务数据。
- 开发环境复查：开发库 `public_application_submissions=0`、`application_processing_runs=0`；Alembic 仍为 `a8d4f2c7e901 (head)`，`alembic check` 无待生成操作。
- 证据边界：没有记录或输出 API Key、原始 Prompt、完整模型响应或可识别个人信息，也没有新建一次性运行器。

这次结果证明一个虚构样本能够穿过真实公开 API、持久任务、结构化和阶段 7 初筛并安全落库；不能证明所有简历都能正确解析、AI 代表招聘准确率或系统达到公网生产容量。浏览器结论来自项目负责人另行完成的手工检查，不由这次模型运行推出。

### 8.5 完成门禁

完成门禁已全部满足：

1. 自动化、migration、真实 PostgreSQL/API/Redis/Worker 和前端 production build 均有通过证据；
2. 经单独授权的最小真实模型链路通过，attempts、token、费用和清理结果已记录；
3. 项目负责人完成浏览器检查，并在修正首次发现的 JD 排版问题后复查接受；
4. 项目负责人基于完整证据确认阶段 8 最终验收通过。

阶段 8 于 2026-09-02 关闭。已知风险仍按设计第 21 节和本记录保留，不因产品验收而改写为“已达到公网生产级”。
