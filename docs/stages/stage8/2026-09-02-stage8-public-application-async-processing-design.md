# 阶段 8：公开投递与异步自动处理设计

> 日期：2026-09-02
>
> 状态：已于 2026-09-02 由项目负责人确认；8E 统一初筛中心细化合同同日确认；8A—8F 已实施并于同日通过项目负责人最终验收
>
> 实施记录：`2026-09-02-stage8-implementation-record.md`
>
> 上游依赖：阶段 4—7 已完成
>
> 目标入口：候选人 `/apply`，HR `/app/*`，正式 API `/api/v2/*`

## 1. 这一步要解决什么

当前系统已经支持 HR 在内部创建岗位、上传简历、建立 Application、执行 AI 初筛并作出人工决定，但公开 `/apply` 仍是“只预览、不提交”的页面。

阶段 8 要把它变成真实入口：候选人提交开放岗位后，系统先可靠保存 Candidate、Resume 和 Application，再由后台任务完成原文提取、结构化草稿和阶段 7 初筛。任何文件、AI 或进程失败都不能让已经接受的投递消失。

大白话主线是：

```text
候选人提交姓名、联系方式、岗位和简历
        ↓
系统先把投递和原文件保存好
        ↓
页面立即返回“投递已收到”
        ↓
后台 Worker 读取简历、生成结构化草稿、触发 AI 初筛
        ↓
HR 在正常处理池或异常处理区继续处理
```

阶段 8 的成功标准不是“AI 每次都成功”，而是：有效投递不会丢，后台状态可解释，失败可以安全恢复，HR 始终保留最终决定权。

## 2. 当前可复用底座

阶段 8 不重新发明阶段 4—7 已经完成的能力：

- Job 已有 `draft / open / closed` 状态和五段式公开 JD；
- `/apply` 已有公开页面视觉原型和开放岗位展示；
- Resume 已支持 PDF、DOCX、TXT 私有保存、原文提取和独立解析状态；
- `ResumeStructureService` 已支持单次 DeepSeek 结构化、幂等、并发保护和旧成功草稿保留；
- Application 已按 Candidate + Job 隔离，并支持 `public_apply` 来源；
- 阶段 7 已有 PostgreSQL 持久 `ScreeningRun`、租约、Worker、当前/历史报告和 HR 决策；
- PostgreSQL、Redis 和 Chroma 已在基础设施中运行，但 Redis 尚未承担正式业务队列。

当前不能直接复用为公开合同的入口包括：

- 内部 `/api/v2/jobs` 返回的是 HR 工作台合同，不应直接作为长期公开合同；
- 内部 `/api/v2/resumes/upload` 与 `/api/v2/applications/intake` 是两个独立提交，无法保证一次公开投递的整体一致性；
- `ApplicationIntakeRequest` 只允许 HR 来源，公开浏览器不能自行声明 `source`、Candidate ID 或 HR 决策；
- 当前 `/apply` 不上传文件、不提交数据，并误展示了后端不支持的旧 `.doc` 格式；
- 当前阶段 7 Worker 只处理 ScreeningRun，尚未编排“原文提取 → 结构化 → 初筛”的完整公开投递链。

## 3. 项目负责人已确认的产品决定

项目负责人于 2026-09-02 逐项确认以下产品合同：

1. 阶段 8 当前定位为作品集和本地演示，只使用虚构或完整脱敏数据，不接收真实候选人个人信息，也不宣称已经具备正式公网招聘合规能力。
2. 公开表单只收集姓名、手机号、邮箱、目标岗位、简历和隐私同意；姓名、手机和邮箱均必填。文件只接受 PDF、DOCX、TXT，单文件最大 10 MB；不接受旧 `.doc`，第一版不做 OCR。
3. 同一候选人重复申请同一岗位时不静默覆盖旧简历：既有公开申请直接复用；既有内部申请保存本次公开提交和新简历，但在 HR 明确选择当前简历前暂停初筛。
4. 同一 Candidate + Job 只要存在任何已结束或作废的历史 Application，第一版都不自动创建再次申请；返回通用人工处理提示，由 HR 线下核对。未来放开重投必须另行修改合同。
5. 手机或邮箱只匹配到既有 Candidate 的一部分时，不自动合并或改写旧 Candidate；另建 Candidate，并标记 HR 人工核对。
6. 简历结构化草稿失败不阻塞阶段 7 初筛，因为初筛使用脱敏 `Resume.raw_text`，不使用 `parsed_snapshot`。
7. 持久业务队列使用 PostgreSQL并由独立 Worker 处理；Redis 只可用于短期限流等非权威状态，不作为投递事实或任务唯一来源。API 只受理请求，不等待文件解析或 DeepSeek。
8. 第一版不提供候选人账号、公开进度查询、邮件、短信、日历和验证码付费服务。
9. 公开岗位展示岗位名称、部门、地点、用工类型和五段式候选人可见 JD；不展示招聘人数、内部时间、计划/AI 状态或内部数据。
10. HR 处理入口扩展现有初筛中心，增加正常处理池和异常处理区，不另建一套重复后台。

同时固定以下安全边界：岗位在受理事务锁定时必须为 `open`；投递被接受后即使岗位关闭，投递和文件仍保留，未开始的阶段 7 初筛按现有合同暂停；公开端永远不返回 Candidate ID、Application ID、Resume ID、重复候选人 ID、内部错误或 AI 结果；公开 `source=public_apply` 只能由服务端设置。

## 4. 用户与决策边界

| 用户/组件 | 本阶段职责 | 不能做什么 |
| --- | --- | --- |
| 候选人 | 查看开放岗位、填写必要信息、上传简历、提交投递 | 不能选择内部来源、HR 决策、处理状态或 AI 参数 |
| HR | 查看正常/异常投递、查看简历和 AI 结果、人工重试、人工核对重复身份、独立决策 | 不能把 AI 分数当作自动淘汰或录用命令 |
| 公开 API | 校验请求、可靠受理、返回不透明凭证 | 不在请求中等待 DeepSeek，不暴露内部对象 |
| Worker | 领取持久任务、推进固定处理步骤、记录安全失败 | 不自动作招聘决定，不跳过成功事实重新收费 |
| DeepSeek | 简历结构化和阶段 7 语义评价 | 不创建/合并 Candidate，不改变岗位或招聘状态 |

AI 结构化结果继续只保存为 `Resume.parsed_snapshot` 草稿。它不得自动覆盖公开表单中由候选人主动填写的姓名、手机和邮箱，也不得自动写入正式教育、工作或项目经历。

## 5. 范围

### 5.1 本阶段包含

- 候选人公开岗位列表、岗位详情和真实投递；
- 独立公开 Job Schema 与只读 API；
- 单次 multipart 投递接口；
- Candidate、Resume、Application、公开提交事实和初始处理任务的可靠创建；
- 服务端幂等、重复申请和候选人身份疑点处理；
- PostgreSQL 持久处理任务、租约、独立 Worker 和进程恢复；
- 原文提取、结构化草稿和阶段 7 初筛编排；
- 正常处理池、异常处理区、人工重试和人工核对；
- 文件、隐私、日志、限流和安全错误边界；
- 自动化、真实 PostgreSQL/API/Worker 和浏览器验收。

### 5.2 本阶段不包含

- 使用真实候选人个人信息进行作品集演示，或直接部署成正式公网招聘入口；
- 候选人登录、账号、公开进度查询或撤回；
- 邮件、短信、日历、付费验证码或外部 ATS；
- 扫描件 OCR、旧 `.doc`、压缩包或多文件投递；
- 自动合并 Candidate 或复杂候选人主数据治理；
- AI 自动通过、淘汰、排序、发 Offer 或录用；
- 面试、Offer、录取和流程报告；
- 完整 RBAC、多租户、计费和互联网级恶意文件扫描平台；
- Redis 消息队列、Celery、LangGraph、Agent、RAG 或 MCP；
- 改写阶段 7 最终 Prompt、评分原则、已知限制或历史原始证据。

## 6. 公开候选人主流程

### 6.1 查看岗位

1. 候选人打开 `/apply`。
2. 页面只请求公开 Job API，只展示 `open` 岗位。
3. 候选人可以查看岗位名称、部门、地点、用工类型和五段式候选人可见 JD。
4. 页面不展示招聘人数、内部时间、计划状态、内部备注、Application 数量或 AI 信息。
5. 没有开放岗位时展示明确空状态，不显示无效提交表单。

### 6.2 填写与提交

公开表单字段固定为：

| 字段 | 必填 | 规则 |
| --- | --- | --- |
| `name` | 是 | 去除首尾空白，1—100 字符 |
| `phone` | 是 | 服务端标准化，7—15 位数字，可带合法国家前缀 |
| `email` | 是 | 去除首尾空白并转小写，最长 254 字符 |
| `job_id` | 是 | 必须指向事务锁定时仍为 `open` 的岗位 |
| `resume` | 是 | PDF、DOCX、TXT，最大 10 MB |
| `privacy_consent` | 是 | 必须为 `true` |
| `consent_version` | 是 | 必须等于页面展示的当前隐私说明版本 |
| `idempotency_key` | 是 | 浏览器为本次提交生成 UUID；不能由候选人手填 |

学校、学历、专业、技能和个人介绍不在第一版表单重复收集。候选人不得提交 `source`、`candidate_id`、`application_id`、招聘状态或 HR 决策字段。

### 6.3 受理与响应

有效请求按以下顺序处理：

```text
限流、Schema 和文件安全校验
        ↓
文件写入私有临时区并计算摘要
        ↓
锁定幂等键、联系方式和目标 Job
        ↓
解析 Candidate 复用/新建/人工核对语义
        ↓
按重复申请规则创建或复用 active Application
        ↓
需要记录本次公开事实时创建 Resume、PublicApplicationSubmission 和初始 ProcessingRun
        ↓
提升临时文件到正式私有路径
        ↓
提交 PostgreSQL 事务
        ↓
返回不透明投递凭证
```

接口成功只表示“投递事实和原文件已经可靠接受”，不表示解析、结构化、AI 初筛或 HR 审核已经完成。

## 7. 公开 API 合同

公开接口使用独立 Router、Schema 和 Service，仍位于正式 `/api/v2/*` 下：

```text
GET  /api/v2/public/jobs
GET  /api/v2/public/jobs/{job_id}
POST /api/v2/public/applications
```

### 7.1 公开岗位响应

概念响应只包含候选人需要的字段：

```json
{
  "id": 12,
  "title": "Python 后端工程师",
  "department": "技术研发部",
  "location": "长沙",
  "employment_type": "full_time",
  "job_background": "……",
  "job_responsibilities": "……",
  "candidate_requirements": "……",
  "preferred_qualifications": "……",
  "public_notes": "……"
}
```

- 列表和详情只读取 `status=open`；关闭、草稿或不存在统一返回公开安全语义。
- `public_notes` 继续是候选人可见普通文本，不进入阶段 7 计划或报告模型。
- 响应不复用内部 `JobRead`，避免未来新增内部字段后被公开接口自动泄露。

### 7.2 公开投递请求

`POST /api/v2/public/applications` 使用 `multipart/form-data`，一次携带表单和一份文件。服务端固定 `source=public_apply`。

### 7.3 成功响应

新投递返回 `202 Accepted`：

```json
{
  "submission_reference": "AP-7K9M2Q4X",
  "accepted_at": "2026-09-02T10:30:00+08:00",
  "message": "投递已收到，招聘团队会在审核后与合适的候选人联系。"
}
```

相同幂等请求或已有公开提交的同岗位重复申请返回原公开凭证。若既有 active Application 来自内部录入，本次公开投递会形成新的公开凭证并进入 HR 简历选择流程；公开端不说明 Candidate 或内部 Application 是否已存在，也不返回内部主键。

### 7.4 稳定失败语义

| HTTP | 公开错误码 | 场景 |
| --- | --- | --- |
| 400 | `PUBLIC_APPLICATION_INVALID` | 普通格式或组合错误 |
| 409 | `JOB_NOT_OPEN` | 岗位已关闭、为草稿或不存在 |
| 409 | `IDEMPOTENCY_KEY_REUSED` | 同一幂等键被用于不同请求内容 |
| 409 | `PUBLIC_APPLICATION_REVIEW_REQUIRED` | 已有结束/作废历史，第一版不自动重投 |
| 413 | `RESUME_FILE_TOO_LARGE` | 超过大小上限 |
| 415 | `RESUME_TYPE_UNSUPPORTED` | 文件类型不允许 |
| 422 | `PUBLIC_APPLICATION_VALIDATION_FAILED` | 字段未通过严格 Schema |
| 429 | `PUBLIC_APPLICATION_RATE_LIMITED` | 触发限流，并返回 `Retry-After` |
| 500 | `PUBLIC_APPLICATION_SAVE_FAILED` | 保存失败且已回滚 |
| 503 | `PUBLIC_APPLICATION_TEMPORARILY_UNAVAILABLE` | 必需基础设施暂时不可用 |

所有错误只返回安全中文说明和稳定错误码，不返回数据库约束名、文件路径、候选人匹配结果、堆栈或上游响应。

## 8. Candidate、重复申请与身份疑点

### 8.1 Candidate 解析

服务端先标准化手机号和邮箱，并使用 PostgreSQL advisory lock 避免并发创建：

1. 手机和邮箱都精确命中同一个 Candidate：复用该 Candidate。
2. 手机和邮箱都未命中：创建新 Candidate。
3. 只有手机或只有邮箱命中，或二者命中不同 Candidate：不自动改写、合并或暴露旧 Candidate；创建新 Candidate，并把公开提交标记为 `needs_review`。
4. 只有姓名相同：创建新 Candidate，并添加低风险 `same_name` 人工核对提示。

Candidate 的正式姓名、手机和邮箱来自候选人主动提交的表单；`source=public_apply`。AI 结构化不得覆盖这些字段。

### 8.2 同岗位重复申请

数据库继续保持“同一 Candidate + Job 最多一个 active Application”的约束。

- 相同幂等键且请求指纹相同：返回第一次结果，不重复保存文件或创建任务。
- 相同幂等键但请求内容不同：拒绝，不猜测候选人意图。
- 同一 Candidate 已有同岗位 active Application，且已有公开提交：返回原公开凭证，丢弃本次临时文件；不切换 `current_resume_id`，不重新初筛。
- 同一 Candidate 已有同岗位 active Application，但它来自 HR 内部录入且没有公开提交：保留本次新 Resume，创建 PublicApplicationSubmission 和 ProcessingRun；完成原文提取与结构化后，在初筛前以 `paused / existing_application_resume_choice` 等待 HR 明确选择是否把新 Resume 设为 `current_resume_id`。
- 同一 Candidate 申请不同岗位：创建新的独立 Application 和 Resume。
- 同一 Candidate + Job 存在已结束或作废 Application：第一版不自动创建新申请，丢弃本次临时文件并返回通用 `PUBLIC_APPLICATION_REVIEW_REQUIRED`；响应不说明具体历史状态，HR 线下核对。

重复申请响应不得让外部请求者确认某个手机号或邮箱是否已在系统中。

## 9. 文件与事务一致性

文件系统和 PostgreSQL 无法形成真正的单一数据库事务，因此使用“临时文件 + 数据库事务 + 补偿清理”：

1. 文件先进入服务端私有临时路径，不使用原文件名作为真实路径。
2. 完成扩展名、MIME、大小、ZIP 结构和安全路径校验，并计算 SHA-256。
3. PostgreSQL 事务中创建 Candidate、Resume、Application、PublicApplicationSubmission 和初始 ProcessingRun。
4. 事务提交前把临时文件提升到不可预测的正式私有路径。
5. 提升失败则回滚数据库；数据库提交失败则尝试删除已提升文件。
6. 补偿删除失败只记录安全文件标识，由定时清理器在保留窗口后处理。
7. 定时清理器只删除精确确认未被 Resume 引用的临时/孤儿文件，不扫描后直接删除未知用户数据。

有效投递一旦成功返回，Candidate、Resume、Application、提交事实和任务必须全部存在；不允许只留下其中一部分。

## 10. 新增持久对象

### 10.1 `PublicApplicationSubmission`

该对象保存公开受理事实，不保存完整表单副本：

| 字段 | 语义 |
| --- | --- |
| `id` | 内部主键，不公开 |
| `application_id` | 一对一关联 Application |
| `resume_id` | 本次公开提交的原 Resume |
| `submission_reference` | 随机、不连续、可供 HR 查询的公开凭证，唯一 |
| `idempotency_key_hash` | 幂等键摘要，唯一；不保存浏览器原值 |
| `request_fingerprint` | 标准化字段、Job、文件摘要和同意版本的指纹 |
| `consent_version` | 候选人确认的隐私说明版本 |
| `consented_at` | 服务端记录的同意时间 |
| `identity_review_status` | `clear / needs_review / reviewed` |
| `identity_review_reasons` | 受控枚举列表，如 `same_name / contact_conflict` |
| `created_at / updated_at` | 审计时间 |

公开凭证不是认证令牌，不提供公开查询能力。原始 IP、User-Agent、完整表单和幂等键不写入该表。

### 10.2 `ApplicationProcessingRun`

该对象负责阶段 8 固定流水线，每次人工重试形成新的 Run，历史不覆盖：

| 字段 | 语义 |
| --- | --- |
| `id` | 运行主键 |
| `submission_id` | 关联公开提交 |
| `application_id / resume_id` | 冻结处理对象 |
| `trigger_type` | `automatic / manual_retry` |
| `status` | `queued / running / waiting_screening / succeeded / succeeded_with_warnings / failed / paused` |
| `current_step` | `extract_text / structure_resume / trigger_screening / await_screening / completed` |
| `attempt_count` | 本 Run 的实际编排尝试次数，设置数据库上限 |
| `waiting_reason` | 暂停时的受控原因，如 `job_closed / existing_application_resume_choice` |
| `error_code / error_message` | 终态失败时必填的安全错误 |
| `warning_codes` | 不阻塞主链的受控 warning 列表 |
| `started_at / completed_at` | 运行时间 |
| `lease_owner / lease_expires_at` | Worker 认领和崩溃恢复 |
| `created_at / updated_at` | 审计时间 |

数据库使用部分唯一索引保证同一公开提交最多一个非终态 ProcessingRun。Run 不保存简历正文、完整 Prompt、模型原始响应或 API Key。

### 10.3 初始审计合同

- 新建公开 Application 时，初始 StageHistory 使用 `reason_code=public_application_received`、`actor_type=system`、`actor_label=候选人公开投递（系统受理）`，状态为 `applied / pending`。
- 公开投递不能复用当前内部入口的“本地 HR（未认证）”演员标签，也不能伪装成 HR 人工录入。
- 既有内部 Application 收到新的公开 Resume 时不伪造招聘阶段变化；公开提交事实由 PublicApplicationSubmission 记录，HR 选择当前 Resume 的操作进入 ActivityLog。
- 相同幂等请求或既有公开申请复用不重复写 StageHistory。

## 11. 后台处理流程

### 11.1 Worker 领取

独立 Worker 使用 PostgreSQL `FOR UPDATE SKIP LOCKED` 领取 `queued` 或租约已过期的运行：

- API 和 Worker 不共享内存任务状态；
- 多个 Worker 可以并发处理不同投递；
- 同一投递只能被一个有效租约处理；
- Worker 崩溃后，租约到期即可恢复；
- 每个外部调用前后使用短事务，等待 DeepSeek 时不长期持有数据库连接或行锁。

### 11.2 固定步骤

```text
extract_text
  成功：Resume.parse_status=parsed，保存 raw_text
  失败：ProcessingRun=failed，保留原文件和业务记录
        ↓
structure_resume
  成功：保存最近一次合法 parsed_snapshot
  失败：记录 warning，继续主链，不覆盖旧草稿
        ↓
trigger_screening
  调用阶段 7 ScreeningService，而不是直接调用模型
  既有内部 Application 尚未确认当前简历：paused / existing_application_resume_choice
        ↓
await_screening
  waiting_resume / waiting_plan / queued / running：继续等待
  paused / job_closed：ProcessingRun=paused
  succeeded：ProcessingRun=succeeded 或 succeeded_with_warnings
  failed：ProcessingRun=failed，保留所有成功事实
```

结构化与初筛在业务上独立。第一版 Worker 可以按上述顺序串行调用以降低并发和费用，但结构化失败只能形成 warning，不能阻止已有 `raw_text` 进入初筛。

### 11.3 复用与跳过

每次自动恢复或人工重试前重新读取数据库：

- `raw_text` 已成功且输入文件未变：跳过提取；
- 当前结构化草稿合法且文件未变：跳过结构化；
- 阶段 7 已有相同指纹的 current 报告或非终态运行：复用；
- 成功步骤不能为了“重跑整链”重复调用或覆盖；
- 输入变更、重新评估和历史报告继续遵守阶段 7 现有合同。

## 12. 状态展示

后台保存精确技术状态，候选人只看到提交是否被接受。HR 页面把状态翻译为易懂分组：

| HR 分组 | 典型后台状态 |
| --- | --- |
| 等待处理 | ProcessingRun `queued` |
| 正在处理 | `running`，步骤为读取或结构化 |
| 等待初筛 | `waiting_screening`，计划未确认或 ScreeningRun 正在排队 |
| 处理完成 | `succeeded` |
| 完成但需留意 | `succeeded_with_warnings` 或身份核对 `needs_review` |
| 处理失败 | `failed` |
| 等待 HR 处理 | `paused / job_closed` 或 `paused / existing_application_resume_choice` |

页面不得把“提交成功”“AI 成功”“HR 通过”混为一个状态。

## 13. 重试与失败隔离

### 13.1 自动重试

- 文件损坏、不支持格式、文本为空、Schema 内容错误等确定性问题不自动重试；
- 网络中断、临时存储错误、上游 5xx 等基础设施错误可有限重试；
- ProcessingRun 的自动尝试次数和退避时间必须通过配置设置上下限；
- 阶段 7 的模型 attempts 和一次 Repair 上限继续由阶段 7 合同负责，阶段 8 不增加隐藏调用；
- 达到上限后进入 `failed`，不无限循环、不静默吞错。

具体推荐默认值在实现前的测试合同中固定：编排自动尝试最多 3 次；同一步基础设施重试最多 2 次；内容错误 0 次自动重试。任何真实付费调用都记录实际模型、attempt、token 和费用。

### 13.2 人工重试

HR 只能对终态失败或暂停后恢复条件已满足的投递发起人工重试：

1. 页面明确显示将从哪个失败步骤继续；
2. HR 二次确认；
3. 创建新的 `manual_retry` ProcessingRun；
4. 复用所有仍有效的成功步骤；
5. 不删除旧 Run、旧成功草稿、旧 ScreeningReport 或原文件。

身份核对不自动合并 Candidate。第一版 HR 只能查看提示并标记“已核对”；真正的 Candidate 合并需要另立数据治理专项。

## 14. 关键异常流程

| 场景 | 固定行为 |
| --- | --- |
| 提交时岗位已关闭 | 不接受，不保存投递 |
| 提交已接受后岗位关闭 | 保留数据；解析/结构化可完成，未开始初筛暂停 |
| 评价清单缺失或待确认 | ScreeningRun `waiting_plan`，不是任务失败 |
| 文件保存成功、数据库失败 | 回滚并补偿删除文件 |
| 数据库成功响应前连接断开 | 相同幂等键重试返回同一凭证 |
| Worker 处理中崩溃 | 租约到期后重新领取，成功步骤跳过 |
| 原文提取失败 | 保留原文件和投递，进入异常区 |
| 结构化失败 | 保留原文；记录 warning；初筛继续 |
| 初筛失败 | 保留投递、简历、草稿和旧成功报告，进入异常区 |
| AI 返回敏感评价或招聘决定 | 按阶段 7 安全合同失败，不自动 Repair 高风险错误 |
| HR 已作出决定后迟到任务完成 | 不覆盖 HR 决定；报告和历史按阶段 7 事务保护处理 |
| 同一请求并发提交 | advisory lock + 唯一约束只产生一个业务结果 |
| 已有内部 active Application 又收到公开简历 | 保存公开提交与新 Resume；不静默切换，等待 HR 选择当前简历 |

## 15. HR 工作台

第一版优先在现有初筛中心扩展，而不是同时新建另一套候选人主页面。

### 15.1 正常处理池

- 显示公开凭证、候选人、岗位、提交时间和当前处理步骤；
- 支持等待处理、处理中、等待初筛和处理完成筛选；
- 复用现有简历查看、初筛报告和 HR 决策入口；
- queued/running 使用有上限的最小轮询，抽屉关闭或终态后停止。

### 15.2 异常处理区

- 原文提取失败；
- 结构化 warning；
- 初筛失败；
- 岗位关闭暂停；
- `same_name` 或 `contact_conflict` 身份核对；
- 安全错误只显示可行动说明，不展示内部异常。

HR 可执行查看原文件、查看成功原文/草稿/报告、重试失败步骤、标记身份已核对和进入人工决策。第一版不提供 Candidate 自动合并。

### 15.3 8E 统一初筛中心接口合同

> 本节是进入 8E 生产代码前补齐的最小实施合同，不改变前述十项已确认产品选择；项目负责人于 2026-09-02 确认按统一初筛中心实施。

8E 只扩展现有 `/app/screening` 初筛中心，不新建页面、Tab 或独立“公开投递工作区”。候选人在公开网站提交后，Application 立即进入现有统一初筛列表；公开来源只是列表中的来源和后台处理状态。所谓正常池和异常区只是同一列表的筛选结果，不是两套队列。归类固定如下：

- 正常池：身份状态为 `clear / reviewed`，且最新 ProcessingRun 为 `queued / running / waiting_screening / succeeded`；
- 异常区：身份状态为 `needs_review`，或最新 ProcessingRun 为 `failed / paused / succeeded_with_warnings`；
- 同一提交只出现一次；同时满足多个异常条件时仍只在异常区显示，并完整保留所有异常标签；
- `succeeded` 只代表阶段 8 自动处理完成，不代表 HR 已通过；HR 决策继续读取 Application 的独立字段。

#### 15.3.1 新增内部只读与动作接口

| 方法与路径 | 用途 | 固定边界 |
| --- | --- | --- |
| `GET /api/v2/public-application-submissions` | 读取公开投递工作台摘要 | 支持 `pool=all/normal/exception`、`job_id`、`processing_status`；默认 `all`，按提交时间倒序；仅内部工作台使用 |
| `GET /api/v2/public-application-submissions/{submission_id}` | 读取一条投递详情和全部 ProcessingRun 历史 | 不返回幂等键摘要、请求指纹、租约 owner、租约到期时间或文件路径 |
| `POST /api/v2/public-application-submissions/{submission_id}/identity-review` | 将 `needs_review` 标记为 `reviewed` | 请求固定为 `{ "confirmed": true }`；原因列表必须原样保留；不合并、不删除、不改写 Candidate |
| `POST /api/v2/public-application-submissions/{submission_id}/retry` | 对失败或恢复条件已满足的暂停任务人工重试 | 请求固定为 `{ "confirmed": true }`；创建新 `manual_retry` Run 并返回，不覆盖旧 Run |
| `GET /api/v2/resumes/{resume_id}/structure` | 只读返回当前已保存的结构化结果 | 只调用现有 `get_current_result()`；没有结果时返回 404，绝不启动模型调用 |

现有 `GET /api/v2/resumes/{resume_id}`、`GET /api/v2/resumes/{resume_id}/file`、`GET /api/v2/applications/{application_id}/screening`、报告历史和 HR 决策接口继续复用。现有 `PUT /api/v2/applications/{application_id}/current-resume` 继续负责既有内部 Application 的简历选择；8E 只补齐该操作的 ActivityLog，不新增平行切换接口。

#### 15.3.2 工作台 Schema

列表摘要固定只包含工作台需要的安全字段：

- 提交：`submission_id / submission_reference / submitted_at / identity_review_status / identity_review_reasons`；
- 关联对象：`application_id / candidate_id / resume_id / job_id`；
- 展示摘要：`candidate_name / job_title / job_status / resume_filename / resume_parse_status`；
- 最新 Run：`id / trigger_type / status / current_step / attempt_count / waiting_reason / error_code / error_message / warning_codes / started_at / completed_at / created_at / updated_at`；
- 独立 HR 结果：Application 的 `lifecycle_status / recruitment_stage / hr_decision`。

详情在列表摘要基础上增加：

- `processing_runs`：按创建时间倒序的完整安全历史，但仍排除租约字段；
- `identity_candidates`：只在身份核对时返回可能相关 Candidate 的 `id / name / phone / email / source / created_at / is_submission_candidate`，供 HR 人工比对；
- 不内嵌原文件、原文、结构化草稿或 ScreeningReport，页面按需调用上述既有/新增只读接口，避免列表批量暴露大文本和隐私数据。

列表和详情 Schema 不复用 `PublicApplicationSubmissionRead` 或 `ApplicationProcessingRunRead`，因为这两个内部持久化 Schema 含幂等摘要、请求指纹或租约字段，不属于 HR 页面合同。

#### 15.3.3 动作、审计和失败语义

- 身份核对仅允许 `needs_review → reviewed`；重复提交已完成的核对返回当前详情，不重复写审计；`clear` 状态不能伪造核对历史。
- 人工重试继续使用 8C 的 `create_manual_retry()`：存在非终态 Run 时拒绝；`failed` 可继续；`paused` 必须先满足岗位重新开放或已选择本次公开 Resume 的恢复条件。
- 身份核对写入 ActivityLog：`action=public_application_identity_reviewed`，目标为 Submission，记录受控原因和本地 HR actor，不保存自由文本。
- 人工重试写入 ActivityLog：`action=public_application_manual_retry`，记录旧 Run、新 Run 和继续步骤。
- 切换当前简历写入 ActivityLog：`action=application_current_resume_changed`，记录旧/新 Resume ID；不伪造 StageHistory。

接口只返回下列稳定错误，不把数据库约束、文件路径、模型原始错误或堆栈返回页面：

| HTTP | 错误码 | 说明 |
| --- | --- | --- |
| 404 | `PUBLIC_APPLICATION_SUBMISSION_NOT_FOUND` | 投递不存在 |
| 404 | `RESUME_STRUCTURE_RESULT_NOT_FOUND` | 尚无已保存结构化结果 |
| 409 | `PUBLIC_APPLICATION_IDENTITY_REVIEW_NOT_REQUIRED` | 当前身份状态不允许标记 |
| 409 | `APPLICATION_PROCESSING_ACTIVE_RUN` | 已有非终态 ProcessingRun |
| 409 | `APPLICATION_PROCESSING_RETRY_NOT_ALLOWED` | 当前任务不是可人工重试状态 |
| 409 | `APPLICATION_PROCESSING_PAUSE_NOT_RECOVERED` | 暂停原因尚未解除 |
| 422 | `HR_ACTION_CONFIRMATION_REQUIRED` | 身份核对或人工重试缺少二次确认 |
| 500 | `PUBLIC_APPLICATION_WORKBENCH_OPERATION_FAILED` | 未预期内部失败的安全退化 |

#### 15.3.4 前端交互和轮询边界

- 现有统一初筛表格继续以候选人和岗位为主要信息；公开来源行额外显示公开凭证和后台处理状态，步骤采用“受理 → 原文 → 结构化 → 初筛”的窄型处理轨迹，当前、完成、warning 和失败使用文字加图标，不只依赖颜色。
- 现有来源筛选增加公开投递选项；正常池/异常区通过统一状态筛选进入，不增加页面、Tab 或独立模块。HR 手工录入和公开投递继续共用同一份 Application 列表、详情抽屉、初筛报告和 HR 决策。
- 正常池提供等待处理、处理中、等待初筛、处理完成筛选；异常区按提取失败、结构化 warning、初筛失败、岗位关闭、简历待选择和身份核对筛选。
- 详情抽屉按需读取原文件、原文、已保存草稿和报告；没有成功事实时显示“尚未生成”，不能通过只读入口触发 AI。
- 只有详情抽屉打开且最新 Run 为 `queued / running / waiting_screening` 时，每 4 秒刷新一次，最多 30 次；关闭抽屉、进入终态或达到 30 次立即停止，之后由 HR 手动刷新。
- 身份核对和人工重试均使用二次确认；按钮提交期间禁用，成功后用接口响应更新当前行，失败时保留抽屉上下文并显示上述安全说明。
- 8E 自动化和浏览器假数据不得创建真实 queued Run；本批次不调用 DeepSeek、不产生费用。

## 16. 隐私与安全

### 16.1 数据最小化

- 公开表单不主动收集性别、年龄、民族、婚姻、生育、身份证、照片或详细住址；
- 候选人只提交招聘联络需要的姓名、手机、邮箱和简历；
- `consent_version` 与服务端时间可审计，但不保存无关浏览器画像；
- 测试、截图和文档不得使用真实个人简历或联系方式。

### 16.2 文件安全

- 文件存储在 Web 根目录之外，路径不可由用户控制；
- 只允许 PDF、DOCX、TXT，扩展名和实际 MIME 必须一致；
- DOCX 继续执行 ZIP 结构、解压体积和文本长度保护；
- 下载使用安全文件名、`private, no-store` 和 `nosniff`；
- 普通文本由 React 文本节点展示，不渲染候选人 HTML；
- 第一版不宣称具备互联网级恶意文件扫描能力；正式公网部署前需在阶段 12 再评估隔离区和恶意文件扫描。

### 16.3 接口保护

- 公开 Router 不复用内部写入 Schema；
- 使用请求体上限、IP/联系方式短期限流和 `Retry-After`；
- Redis 可以保存短 TTL 限流计数，但限流键不是业务事实；
- 限流基础设施不可用时返回安全 `503`，不无保护地放开无限提交；
- CORS 只控制浏览器来源，不被视为认证或防滥用机制；
- 不增加付费 CAPTCHA，除非未来真实滥用证据支持并重新获得授权。

### 16.4 模型输入

- 简历原文继续作为不可信数据，不能覆盖系统指令；
- 阶段 5 结构化只提取，不评价或猜测；
- 阶段 7 在调用前移除联系方式和敏感字段；
- 原始 Prompt、完整简历和完整模型响应不进入普通日志；
- API Key、`.env` 和内部路径不得出现在响应、提交或截图中。

## 17. 分层职责

```text
React /apply
  公开岗位、表单、文件选择、幂等键、提交反馈
        ↓
FastAPI Public API
  multipart、公开错误、限流入口、依赖注入
        ↓
Pydantic Public Schema
  字段、枚举、长度、同意和额外字段拒绝
        ↓
PublicApplicationService
  Candidate 解析、幂等、Job 锁、文件补偿、事务
        ↓
ApplicationProcessingService / Worker
  任务认领、步骤推进、重试、失败隔离
        ↓
既有 ResumeService / ResumeStructureService / ScreeningService
        ↓
SQLAlchemy Model + PostgreSQL + 私有文件存储
```

- React 不生成来源、状态或 HR 决策；
- API 不直接编排跨对象事务或调用模型；
- Schema 不查询数据库；
- PublicApplicationService 不复制文件解析或 AI 逻辑；
- Worker 只调用既有 Service，不直接写模型表或绕过阶段 7；
- Model/PostgreSQL 负责外键、唯一约束、状态 CHECK 和最终持久边界。

## 18. Migration 原则

阶段 8 会新增数据库合同，实施前必须先重新确认实际数据和 Alembic 状态：

- `alembic current/head/check`；
- Candidate、Resume、Application、Job、计划、报告和 Run 数量；
- 当前 active Application 和公开来源分布；
- 是否存在无法满足新外键或唯一约束的数据；
- 当前私有文件目录和孤儿清理风险。

Migration 必须：

1. 只新增向前 revision，不修改 `e7f9a1b3c545` 或其他既有 migration；
2. 新增 `public_application_submissions` 和 `application_processing_runs`；
3. 增加明确外键、唯一约束、CHECK、索引和非终态部分唯一索引；
4. 不删除或回算任何阶段 7 Application、ScreeningRun、报告或 raw 证据；
5. 对既有行使用可解释的可空/回填顺序，不伪造公开同意事实；
6. 在临时 PostgreSQL 执行 `upgrade -> downgrade -> upgrade`；
7. 在开发数据库只执行确认后的向前升级，不用用户数据测试 downgrade；
8. 最终 `current=head` 且 `alembic check` 无待生成操作。

## 19. 自动化与验收

### 19.1 Schema 与 Service

- 公开字段必填、长度、手机/邮箱归一、额外字段拒绝；
- 隐私同意版本和幂等键校验；
- PDF、DOCX、TXT 与大小、MIME、恶意路径边界；
- Job 必须 open，关闭竞态使用行锁；
- Candidate 精确复用、无匹配新建、部分冲突人工核对；
- 相同幂等请求复用、不同内容冲突、并发唯一；
- 同岗位重复不覆盖旧 Resume；
- 文件提升、数据库回滚和补偿清理。

### 19.2 Worker 与状态

- `SKIP LOCKED` 多 Worker 不重复领取；
- 租约过期恢复和进程重启；
- 成功步骤跳过，不重复模型调用；
- 提取失败阻塞、结构化失败不阻塞、初筛失败隔离；
- 计划缺失等待、岗位关闭暂停、重新开放恢复；
- 人工重试新建历史 Run；
- 失败不删除原文件、Application、草稿或旧报告。

### 19.3 真实 PostgreSQL 与 API

- multipart 真实上传和公开响应无内部 ID；
- 同一事务形成 Candidate、Resume、Application、Submission 和 Run；
- 约束和并发竞态真实生效；
- migration 往返、外键、索引和 `alembic check`；
- Worker 重启后继续处理队列；
- OpenAPI 路由无重复，公开/内部 Schema 隔离。

### 19.4 前端与浏览器

1. `/apply` 不再显示“预览、不会提交”或返回内部工作台链接。
2. 只展示 open 岗位和候选人可见字段。
3. 姓名、手机、邮箱、岗位、简历和隐私同意校验明确。
4. 只允许 PDF、DOCX、TXT，大小提示与后端一致。
5. 重复点击只提交一个逻辑请求，成功显示公开凭证。
6. 网络失败保留已填内容和已选文件；可安全重试。
7. HR 能区分提交、后台处理、AI 结果和 HR 决策。
8. 正常池、异常区、人工重试和身份核对可操作。
9. 1440×900、820×1180 和 390×844 无横向溢出，键盘和焦点可用。
10. 页面不渲染候选人 HTML，不显示内部错误、路径或未脱敏内容。

### 19.5 真实 DeepSeek

设计和普通自动化默认使用 Fake Adapter，不产生费用。阶段 8 最终真实链路需要同时覆盖一次结构化和一次阶段 7 初筛；开始前另行说明模型、调用次数、当前价格、费用上限、脱敏样本和结果写入位置，并取得授权。

阶段 7 的长期质量调用授权不能自动扩大为阶段 8 的新验收调用。任何真实结果只证明该样本链路工作，不证明招聘准确率、互联网规模或所有错误都能恢复。

## 20. 实施顺序与停止点

阶段 8 设计获得明确确认后，按紧密相关的小批次实施：

1. **8A：合同与 migration**：固定公开 Schema、Submission/ProcessingRun 状态、约束和迁移；完成临时 PostgreSQL 往返。
2. **8B：可靠公开受理**：实现公开 Job API、单次 multipart 投递、文件补偿、Candidate 解析、幂等和稳定错误；不启动 AI。
3. **8C：持久 Worker 与流水线**：实现任务领取、租约、原文提取、结构化 warning、阶段 7 触发与终态对账。
4. **8D：候选人 `/apply`**：把现有预览页面接入真实 API，删除无效字段、旧 `.doc` 和内部入口。
5. **8E：HR 正常池与异常区**：展示处理状态、失败、warning、身份核对和人工重试，复用现有报告与决策。
6. **8F：完整验收**：扩大到后端、migration、真实 PostgreSQL/API/Worker、前端构建和浏览器；经授权后执行最小真实模型链路。

每个批次先跑直接相关测试，再按影响扩大。若实施发现必须改变本文的核心流程、API、Schema、数据库状态、权限、重试或失败语义，立即停止，先更新本文并重新获得确认。

## 21. 完成标准与风险声明

只有同时满足以下条件才能宣布阶段 8 完成：

1. 有效公开投递能够可靠形成 Candidate、Resume、Application、Submission 和 ProcessingRun；
2. 重复和并发请求不会产生重复业务结果或重复收费；
3. API 不等待 DeepSeek，Worker 可以在进程重启后恢复；
4. 原文提取、结构化和阶段 7 初筛按既有合同衔接；
5. 任一步失败都不删除投递、原文件、人工输入或旧成功结果；
6. HR 能处理正常、warning、失败、暂停和身份疑点；
7. AI 不自动作招聘决定；
8. 自动化、migration、真实 PostgreSQL/API/Worker 和浏览器验收通过；
9. 所有真实模型调用均经过授权并记录 attempts、token 和费用；
10. 项目负责人完成最终产品验收。

本阶段验收不能证明：

- 系统已达到互联网大规模并发；
- 文件已通过企业级恶意软件扫描；
- Candidate 自动去重或合并完全准确；
- AI 初筛代表真实招聘准确率；
- 登录、RBAC、数据保留、合规和生产部署已经全部完成。

这些剩余边界在阶段 12 或新的独立专项中处理，不能用删除断言、隐藏失败或扩大 AI 决策权来换取阶段 8 通过。

## 22. 简历与面试表达

阶段完成后可以如实描述：

> 设计并实现公开招聘投递与异步处理链路，通过 PostgreSQL 持久任务、`SKIP LOCKED`、租约恢复、幂等键、文件补偿和分步骤失败隔离，保证 Candidate、Application、Resume 先可靠落库，再由独立 Worker 编排简历提取、DeepSeek 结构化和可解释 AI 初筛，并为 HR 提供正常处理池和异常恢复入口。

常见面试追问包括：

- 为什么先保存投递，再执行 AI？
- 为什么当前使用 PostgreSQL 队列而不是 Redis/Celery？
- 文件系统和数据库不能同事务时怎样补偿？
- 怎样保证网络重试不产生重复 Application？
- Worker 崩溃后怎样恢复，如何防止两个 Worker 重复处理？
- 为什么结构化失败仍可以继续初筛？
- 为什么公开 API 不能复用内部 ApplicationIntakeRequest？
- 怎样避免候选人联系方式和敏感属性进入评分？
- 为什么不自动合并 Candidate 或自动淘汰候选人？

## 23. 设计确认结果与实施门禁

项目负责人已于 2026-09-02 明确确认第 3 节全部十项产品决定。阶段 8 的业务设计门禁已经通过，实施顺序按第 20 节执行，当前进度统一见 `PROJECT_STATE.md`。

后续实施仍遵守以下停止条件：

- 发现必须改变公开表单、重复申请、身份解析、结构化/初筛依赖、队列、HR 入口、隐私或失败语义时，先修改本文并重新确认；
- 作品集演示不得使用真实候选人个人信息；若目标改为正式公网使用，必须先增加隐私保留/删除、恶意文件扫描和生产安全专项；
- 任何阶段 8 真实 DeepSeek 调用仍需单独说明模型、次数、价格、费用上限和证据位置并获得授权；
- 在正式开始 8A 前重新检查 Git、Alembic 和真实 PostgreSQL 数据状态。
