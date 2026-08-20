# 阶段 6：结构化岗位管理专项设计

> 日期：2026-08-15
>
> 状态：✅ 阶段 6 已于 2026-08-17 获用户确认完成；技术集成验收已通过，受控浏览器当时无可用实例的证据边界保留在同阶段验收记录中
>
> 上游依据：`../../architecture/2026-07-15-hr-agent-platform-design.md`、`../../planning/2026-08-14-post-stage5-product-roadmap.md`、`../../planning/implementation-plan.md`
>
> 当前进度：新版 Job 的严格 Schema、迁移、Service、API、真实管理表单和下游开放岗位读取边界已完成；详细验收证据见同目录 `2026-08-17-stage6-acceptance.md`

## 1. 文档目的

本阶段把当前“能保存一条 Job 记录”的基础 CRUD，升级为 HR 可以正式使用的岗位管理能力。完成后，HR 能创建草稿、补齐结构化要求、开放招聘、关闭岗位和重新开放；阶段 7 的 Application 与 AI 初筛可以依赖同一套稳定岗位标准。

这里的“结构化”是指岗位要求使用固定字段和固定类型保存。例如最低工作年限必须是整数，必备技能必须是字符串列表，不能再允许任意形状的 JSON 随意写入。

本设计已经吸收 2026-08-15 的业务讨论结果。用户再次明确确认本文档后，才允许按第 14 节顺序开始开发。

## 2. 当前事实与问题

当前新版链路为：

```text
/stage3/jobs
    ↓ GET（写入按钮禁用）
/api/v2/jobs
    ↓
JobCreate / JobUpdate / JobRead
    ↓
JobService 基础 CRUD
    ↓
Job SQLAlchemy Model
    ↓
PostgreSQL jobs 表
```

当前真实能力：

- PostgreSQL `jobs` 表已有 `title/department/description/requirements/status/created_at/updated_at`。
- `/api/v2/jobs` 已有创建、列表、详情、局部更新和删除。
- Service 写入失败会 rollback。
- 阶段 3 岗位页能够读取真实岗位并按候选人的 `applied_job_id` 统计关联人数。

当前不足：

- `requirements` 是任意 JSONB，没有版本和严格字段。
- `status` 是任意字符串，新岗位默认直接 `open`。
- 全空格标题也能通过当前 Schema。
- 没有地点、用工类型和招聘人数。
- 没有开放完整性校验和状态迁移规则。
- 普通更新可以直接修改状态。
- 删除没有业务级关联检查和稳定冲突语义。
- 岗位前端不能写入。
- AI 初筛中心仍读取所有状态的岗位。
- 旧 SQLite 的岗位管理、`active/inactive`、启停和安全删除属于旧演示逻辑，不能当作本阶段已完成。

## 3. 阶段目标与范围

### 3.1 本阶段包含

1. 严格、版本化的 `JobRequirements v1`。
2. 岗位基础字段：名称、部门、地点、用工类型、招聘人数和岗位描述。
3. `draft/open/closed` 三种状态。
4. 创建草稿、创建并开放、编辑、开放、关闭、重新开放和安全删除。
5. 开放岗位完整性校验。
6. 旧 PostgreSQL Job 数据和旧要求 JSONB 的无损迁移。
7. `/api/v2/jobs` 的状态筛选、状态动作和稳定错误语义。
8. `/stage3/jobs` 的真实写入表单和状态操作。
9. AI 初筛的新岗位选择只读取开放岗位。
10. 阶段 3 公开投递骨架改为从服务端请求开放岗位；真正的公开/后台权限隔离仍属于阶段 8、12。

### 3.2 本阶段不包含

- 不调用 DeepSeek，不解析粘贴的 JD，不生成 AI 岗位内容。
- 不新增 Candidate/Application 分离；Application 属于阶段 7。
- 不实现正式 AI 初筛、评分、证据和重跑；属于阶段 7。
- 不实现公开投递写入、Redis 队列和异步自动处理；属于阶段 8。
- 不实现面试、Offer、录取或报告；属于阶段 9。
- 不实现首页 Agent 或岗位 Tool；属于阶段 10。
- 不实现 RAG、MCP、多租户、计费、邮件或日历。
- 不实现登录、RBAC 和完整审计；属于阶段 12。
- 不建设岗位审批流、岗位历史版本表或乐观锁。
- 不实现薪资范围；阶段 8 设计公开岗位展示时再确认币种、周期、可见性和保密规则。

## 4. 核心业务概念

### 4.1 Job 基础信息

Job 基础信息描述“这是一个什么岗位、在哪里、招多少人”。

| 字段 | 类型与限制 | 草稿要求 | 开放要求 |
| --- | --- | --- | --- |
| `title` | 去除首尾空白后的字符串，1—200 字符 | 必填 | 必填 |
| `department` | 可空字符串，最长 100 字符 | 可空 | 必填 |
| `location` | 可空字符串，最长 100 字符，可填写“远程” | 可空 | 必填 |
| `employment_type` | 可空枚举 | 可空 | 必填 |
| `headcount` | 可空整数，1—999 | 可空 | 必填 |
| `description` | 可空字符串，最长 20,000 字符 | 可空 | 必填 |
| `status` | `draft/open/closed` | 服务端控制 | 服务端控制 |
| `created_at` | 带时区时间 | 服务端生成 | 服务端生成 |
| `updated_at` | 带时区时间 | 服务端更新 | 服务端更新 |

用工类型使用稳定英文代码，前端显示中文：

| 代码 | 中文 |
| --- | --- |
| `full_time` | 全职 |
| `part_time` | 兼职 |
| `internship` | 实习 |
| `contract` | 合同制 |

`description` 保存岗位整体介绍和原始描述；`responsibilities` 保存逐条结构化职责。迁移和编辑不得删除或覆盖旧 `description`。

### 4.2 JobRequirements v1

JSON 中的 Schema 版本固定为字符串 `"1.0"`。所有字段名都必须出现，未知字段一律拒绝。

```json
{
  "schema_version": "1.0",
  "responsibilities": [],
  "required_skills": [],
  "preferred_skills": [],
  "minimum_work_years": null,
  "education_requirement": null,
  "required_experiences": [],
  "preferred_experiences": [],
  "keywords": [],
  "additional_requirements": []
}
```

字段规则：

| 字段 | 类型与限制 | 开放要求 |
| --- | --- | --- |
| `schema_version` | 只能是 `"1.0"` | 必须 |
| `responsibilities` | 最多 50 条，每条最长 1,000 字符 | 至少 1 条 |
| `required_skills` | 最多 100 条，每条最长 100 字符 | 至少 1 条 |
| `preferred_skills` | 最多 100 条，每条最长 100 字符 | 可为空数组 |
| `minimum_work_years` | `0—80` 整数或 `null` | 必须是整数；`0` 表示不限经验 |
| `education_requirement` | 学历枚举或 `null` | 必须选择 |
| `required_experiences` | 最多 50 条，每条最长 1,000 字符 | 可为空数组 |
| `preferred_experiences` | 最多 50 条，每条最长 1,000 字符 | 可为空数组 |
| `keywords` | 最多 100 条，每条最长 100 字符 | 可为空数组 |
| `additional_requirements` | 最多 50 条，每条最长 1,000 字符 | 可为空数组 |

学历代码：

| 代码 | 中文 |
| --- | --- |
| `none` | 不限学历 |
| `associate_or_above` | 大专及以上 |
| `bachelor_or_above` | 本科及以上 |
| `master_or_above` | 硕士及以上 |
| `doctorate` | 博士 |

列表统一执行：去除首尾空白、删除空项、完全相同项去重，并保持第一次出现顺序。大小写不同的技能不做模糊合并，避免把不同技术名称误判成同一项。

新草稿如果没有提交 `requirements`，服务端创建上面的空 v1 对象。如果客户端显式提交 `requirements`，必须提交完整 v1，不能只提交其中一个嵌套字段。后续修改要求时同样使用完整对象替换，避免深层局部更新产生不确定结果。

## 5. 草稿与开放完整性

### 5.1 草稿可为空的内容

草稿只强制要求非空 `title`。以下内容允许暂时为空：

- `department`
- `location`
- `employment_type`
- `headcount`
- `description`
- 所有要求列表
- `minimum_work_years`
- `education_requirement`

草稿中的 `requirements` 仍必须符合 v1 的类型和字段结构，只是内容可以为空。

### 5.2 开放时必须满足

基础字段：

- `title` 非空。
- `department` 非空。
- `location` 非空。
- `employment_type` 是合法枚举。
- `headcount` 是 `1—999` 整数。
- `description` 非空。

结构化要求：

- `schema_version == "1.0"`。
- `responsibilities` 至少 1 条。
- `required_skills` 至少 1 条。
- `minimum_work_years` 是 `0—80` 整数。
- `education_requirement` 是合法枚举。
- 其余列表可以为空，但必须是合法列表。

开放校验失败时返回全部缺失或错误字段，不只返回第一个问题。失败不得写入部分数据或改变岗位状态。

## 6. 状态机

### 6.1 合法迁移

```text
创建草稿:          无记录 -> draft
创建并开放:        无记录 -> open（必须完整）
开放草稿:          draft -> open（必须完整）
关闭岗位:          open -> closed
重新开放:          closed -> open（必须完整）
```

### 6.2 非法迁移

- `open -> draft`
- `closed -> draft`
- `draft -> closed`
- 已开放岗位再次执行开放
- 已关闭岗位再次执行关闭
- 对非 `closed` 岗位执行重新开放
- 通过普通更新接口修改 `status`
- 使用任何枚举外的状态

非法迁移统一返回 HTTP `409` 和 `INVALID_JOB_STATUS_TRANSITION`。状态动作不采用“重复调用也返回成功”的幂等假象，前端需要明确告诉 HR 当前状态已经不符合该操作。

### 6.3 状态动作并发保护

Service 在编辑、状态动作和删除时使用 PostgreSQL 行锁读取目标 Job。大白话理解：同一时刻如果两名 HR 同时修改同一个岗位，数据库会让写操作排队，后进入的操作必须基于最新状态重新校验，避免开放和关闭互相覆盖。

## 7. 编辑规则

### 7.1 普通更新

- 沿用当前 `PUT /api/v2/jobs/{id}` 的局部更新语义，减少已有 API 破坏。
- `JobUpdate` 不包含 `status/created_at/updated_at/legacy_requirements`。
- 请求不得包含未知字段。
- 空更新请求返回 `422 JOB_UPDATE_EMPTY`。
- 客户端显式传 `null` 可以清空允许为空的基础字段。
- `title` 不能为 `null` 或空白。

### 7.2 编辑草稿和关闭岗位

草稿和关闭岗位允许保存不完整内容，但每个已提交字段本身必须满足类型、长度和枚举约束。关闭岗位修改后不会自动重新开放。

### 7.3 编辑开放岗位

允许编辑开放岗位，但必须：

1. 锁定并读取数据库最新岗位。
2. 把本次局部修改与旧值合并。
3. 对合并后的完整岗位执行全部开放校验。
4. 校验通过后一次提交。
5. 校验失败返回 `422 JOB_OPEN_VALIDATION_FAILED`，数据库保持原值。

开放岗位的合法修改只影响后续投递和后续初筛。已有 `ScreeningResult` 不自动删除、不自动重跑、不改写；阶段 7 会保存岗位要求快照来解释历史结果。

## 8. 关闭、重新开放和历史结果

- 关闭不会删除或改写 Candidate、Resume、ScreeningResult、Report。
- 关闭岗位不能出现在新投递和新初筛的岗位选择中。
- 关闭岗位已有的历史初筛结果仍允许 HR 只读查看。
- 关闭岗位可以编辑；重新开放时按当前 v1 规则重新校验。
- 重新开放成功后再次进入开放岗位列表。

阶段 6 的 AI 初筛中心仍只是历史结果骨架，不实现正式重新筛选按钮。岗位筛选控件只提供开放岗位；如果历史结果属于关闭岗位，结果卡片仍显示保存的岗位标题和“岗位已关闭”提示，不提供新筛选动作。

## 9. 删除规则

### 9.1 允许删除

岗位同时满足以下条件才允许硬删除：

- 状态是 `draft` 或 `closed`。
- 没有关联 Candidate。
- 没有关联 Resume。
- 没有关联 ScreeningResult。
- 没有关联 Report。
- 阶段 7 增加 Application 后，还必须没有关联 Application。

### 9.2 禁止删除

- `open` 岗位返回 `409 JOB_MUST_BE_CLOSED_BEFORE_DELETE`。
- 存在任一关联记录返回 `409 JOB_HAS_REFERENCES`。
- 不级联删除，不把“删除岗位”悄悄转换成“关闭岗位”。
- PostgreSQL 外键继续作为最后一道保护，Service 必须先给出可理解的业务错误。

删除冲突响应包含非零关联数量，便于前端解释：

```json
{
  "detail": {
    "code": "JOB_HAS_REFERENCES",
    "message": "岗位已有历史业务数据，不能删除",
    "references": {
      "candidates": 2,
      "resumes": 1,
      "screening_results": 2,
      "reports": 0
    }
  }
}
```

## 10. 数据库和旧数据迁移

### 10.1 Model 变化

`jobs` 新增：

- `location VARCHAR(100) NULL`
- `employment_type VARCHAR(30) NULL`
- `headcount INTEGER NULL`
- `legacy_requirements JSONB NULL`

调整：

- `requirements` 在数据回填后改为 `NOT NULL`。
- `status` 默认值从 `open` 改为 `draft`。
- 增加状态 CHECK：只允许 `draft/open/closed`。
- 增加人数 CHECK：`headcount IS NULL OR headcount BETWEEN 1 AND 999`。
- `title/department/description/created_at/updated_at` 原值保留。

`legacy_requirements` 只用于保存迁移前的旧要求 JSON，不允许 Job 创建、编辑 API 写入，也不出现在标准 `JobRead` 中。

### 10.2 迁移前只读预检

正式执行 migration 前必须查询并记录：

- Job 总数和每种状态数量。
- Job ID、标题和 `description` 摘要哈希。
- `requirements` 为 `null`、合法 v1、已知旧格式、未知格式的数量。
- Candidate、Resume、ScreeningResult、Report 的岗位关联数量。
- 当前 Alembic revision。

预检只读，不修改数据。若实际数据出现本文未覆盖的新格式，暂停开发并与用户讨论，不能自行丢弃或猜测。

### 10.3 状态迁移

| 旧状态 | 新状态 |
| --- | --- |
| `active` | `open` 候选值 |
| `open` | `open` 候选值 |
| `inactive` | `closed` |
| `closed` | `closed` |
| 空值或未知值 | `draft` |

完成字段和要求转换后，所有 `open` 候选记录都执行开放完整性检查。旧岗位没有可靠地点、用工类型或招聘人数时不得编造；任何不完整的旧开放岗位最终转为 `draft`，由 HR 补齐后重新开放。岗位记录本身、ID、描述和历史关联全部保留。

### 10.4 requirements 迁移

1. 已经严格符合 v1 的对象保持不变。
2. 其他非空旧 JSONB 先完整复制到 `legacy_requirements`。
3. 使用确定性映射生成 v1：
   - 旧 `responsibilities` 字符串列表继续使用；没有时，如果 `description` 非空，复制原描述作为第一条职责，但不改写 `description`。
   - `required_skills -> required_skills`。
   - `bonus_skills/preferred_skills -> preferred_skills`。
   - `job_keywords/keywords -> keywords`。
   - 已存在的 `required_experiences/preferred_experiences` 按列表迁移。
   - `experience_requirement` 中可明确解析的“0年以上/1年以上/3年以上”等转换为整数。
   - `education_requirement` 中明确的“不限/大专/本科/硕士/博士”转换为学历枚举。
   - 旧 `summary` 作为一条 `additional_requirements` 保留。
   - 无法可靠转换的年限或学历原文追加到 `additional_requirements`。
   - `risk_keywords` 和未知键不强行改变语义，只保留在 `legacy_requirements`。
4. `null` 或空对象生成空 v1。
5. 所有生成结果再次通过代码中的 `JobRequirementsV1` 校验后才写入。

### 10.5 migration 往返原则

- 先在专用临时 PostgreSQL 数据库执行 `upgrade -> downgrade -> upgrade`。
- 升级后核对记录数、ID、描述、时间、外键和旧要求快照。
- 降级时，有 `legacy_requirements` 的旧岗位恢复其原始 requirements；阶段 6 新建岗位保留 v1 JSON，因为旧基础模型能够保存 JSONB。
- 降级不删除岗位，不把 `draft` 自动改成 `open`，避免伪造业务状态。
- 正式开发数据库只执行确认后的向前升级，不使用用户数据测试 downgrade。
- 旧 SQLite `backend/recruit.db` 和 `backend/uploads/` 不修改、不重新导入、不清理。

实现说明：`legacy_requirements` 使用 JSONB 的 `none_as_null=True`，明确让 Python `None` 保存为 SQL `NULL`。否则 JSON 自身的 `null` 会被数据库视为“快照列有值”，降级时可能错误覆盖原本合法的 v1。该差异已通过专用 PostgreSQL 往返测试发现并修复。

## 11. API 契约

### 11.1 请求与响应 Schema

`JobCreate`：

- 接收全部可编辑基础字段和完整 `requirements`。
- `status` 只允许 `draft/open`，默认 `draft`；不允许创建即 `closed`。
- `status=open` 时在插入前执行完整开放校验，失败时数据库不生成 Job。

`JobUpdate`：

- 所有可编辑字段为可选，表示局部更新。
- 不接收 `status`。
- 更新 `requirements` 时提交完整 v1。
- 拒绝未知字段和空请求。

`JobRead`：

```json
{
  "id": 1,
  "title": "高级后端工程师",
  "department": "研发部",
  "location": "上海",
  "employment_type": "full_time",
  "headcount": 2,
  "description": "负责招聘平台后端研发",
  "requirements": {
    "schema_version": "1.0",
    "responsibilities": ["负责核心服务设计与开发"],
    "required_skills": ["Python", "PostgreSQL"],
    "preferred_skills": ["Docker"],
    "minimum_work_years": 3,
    "education_requirement": "bachelor_or_above",
    "required_experiences": [],
    "preferred_experiences": [],
    "keywords": ["后端", "异步服务"],
    "additional_requirements": []
  },
  "status": "open",
  "created_at": "2026-08-15T10:00:00+08:00",
  "updated_at": "2026-08-15T10:00:00+08:00"
}
```

### 11.2 路由

| 方法与路径 | 行为 | 成功状态 |
| --- | --- | --- |
| `POST /api/v2/jobs` | 创建草稿或创建并开放 | `201` |
| `GET /api/v2/jobs` | 返回全部岗位，按更新时间倒序 | `200` |
| `GET /api/v2/jobs?status=open` | 严格按单个状态筛选 | `200` |
| `GET /api/v2/jobs/{id}` | 岗位详情 | `200` |
| `PUT /api/v2/jobs/{id}` | 局部更新，不允许改状态 | `200` |
| `POST /api/v2/jobs/{id}/open` | `draft -> open` | `200` |
| `POST /api/v2/jobs/{id}/close` | `open -> closed` | `200` |
| `POST /api/v2/jobs/{id}/reopen` | `closed -> open` | `200` |
| `DELETE /api/v2/jobs/{id}` | 安全硬删除 | `204` |

`GET /api/v2/jobs?status=其他值` 由严格查询 Schema 返回 `422`。

### 11.3 错误格式

岗位业务错误统一使用：

```json
{
  "detail": {
    "code": "JOB_OPEN_VALIDATION_FAILED",
    "message": "岗位信息不完整，暂时不能开放",
    "fields": ["location", "requirements.required_skills"]
  }
}
```

| HTTP | code | 场景 |
| --- | --- | --- |
| `404` | `JOB_NOT_FOUND` | Job 不存在 |
| `409` | `INVALID_JOB_STATUS_TRANSITION` | 非法状态迁移 |
| `409` | `JOB_MUST_BE_CLOSED_BEFORE_DELETE` | 开放岗位删除 |
| `409` | `JOB_HAS_REFERENCES` | 岗位已有历史关联 |
| `422` | `JOB_OPEN_VALIDATION_FAILED` | 创建并开放、开放、重新开放或编辑开放岗位时不完整 |
| `422` | `JOB_UPDATE_EMPTY` | 空更新请求 |
| `422` | FastAPI/Pydantic 默认校验详情 | 类型、长度、枚举或未知字段错误 |
| `500` | `JOB_OPERATION_FAILED` | 已 rollback 的未预期数据库错误 |

数据库错误、SQL、磁盘路径、环境变量和调用栈不得返回前端。所有失败写操作必须 rollback。

## 12. Service 与数据库事务

业务规则集中在 `JobService`，API 只负责请求/响应和异常到 HTTP 的映射。

建议 Service 职责：

- `create_job`
- `get_job`
- `list_jobs(status=None)`
- `update_job`
- `open_job`
- `close_job`
- `reopen_job`
- `delete_job`
- `validate_open_job`
- `get_reference_counts`

创建并开放必须在插入前校验。编辑、状态动作和删除在同一事务中锁定 Job、校验、写入并提交。任何异常 rollback，不允许出现“字段已改但状态没改”或“状态已改但响应失败”的半成功状态。

删除关联检查只是友好提示，数据库外键仍保留并且不配置岗位级联删除。

本阶段不新增 Job 操作历史表，也不写入完整审计链；只维护 `updated_at`。阶段 7、10、12 增加流程历史、Agent 操作和权限审计时复用本阶段 Service，不把审计规则塞回前端。

## 13. 前端交互设计

### 13.1 岗位列表

- 保留总数、草稿数、开放数、关闭数和关联候选人数。
- 支持标题、部门、地点、职责和技能搜索。
- 支持 `draft/open/closed` 状态筛选。
- 状态使用稳定中文标签：草稿、开放招聘、已关闭。
- 不再兼容显示 `active/inactive`；数据库 migration 负责统一状态。
- 每行根据当前状态展示合法动作，不展示无法执行的按钮。

### 13.2 表单

继续使用宽抽屉，但按业务分区：

1. 基础信息：名称、部门、地点、用工类型、人数、描述。
2. 岗位职责：职责列表。
3. 必备要求：必备技能、最低年限、学历、必备经历。
4. 加分与补充：加分技能、加分经历、关键词、补充要求。

创建时提供：

- `保存草稿`
- `保存并开放`

编辑时提供：

- `保存修改`
- 草稿岗位另有 `开放岗位`
- 开放岗位另有 `关闭岗位`
- 关闭岗位另有 `重新开放`

状态不使用普通下拉框编辑，防止绕过状态迁移规则。

### 13.3 失败和确认

- 保存失败时抽屉保持打开，已填内容不清空。
- 开放校验失败时显示全部缺失项，并滚动或聚焦第一个错误字段。
- 写请求进行中禁用关闭、重复提交和其他状态动作。
- 关闭、重新开放、删除必须二次确认。
- 关闭提示“不会删除历史候选人和初筛结果”。
- 删除冲突显示服务端返回的关联数量。
- 请求成功后再刷新列表，不做可能回滚的乐观状态修改。
- 表单有未保存改动时，关闭抽屉需要确认。
- loading、接口失败、数据库空状态和筛选无结果继续保持独立展示。

### 13.4 下游岗位读取

- `/stage3/screening` 的“新初筛岗位选择”请求 `GET /api/v2/jobs?status=open`。
- `/stage3/apply` 骨架请求 `GET /api/v2/jobs?status=open`，不再先取得全部岗位再在浏览器过滤。
- Dashboard 的开放岗位数量只认 `status=open`。
- 候选人详情和历史结果为了显示旧关联岗位名称，可以继续读取全部岗位。
- HR 内部新增候选人的岗位下拉是否只允许开放岗位：阶段 6 统一改为只选择开放岗位；已有候选人关联关闭岗位时仍正常显示历史名称。

当前没有登录权限，`/api/v2/jobs` 仍是内部开发接口，不能声称已经实现真正的公开数据隔离。阶段 8 建立公开岗位 API，阶段 12 增加后台鉴权。

## 14. 开发顺序与小步骤

用户确认本文后，按以下小步骤实施。每一步完成后单独解释、测试和等待用户理解，不提前跳到下一步。

### 小步骤 1：JobRequirements v1 与 Job 请求/响应 Schema

- 新增严格枚举和 Schema。
- 固定清理、去重、长度、空草稿和开放校验输入契约。
- 只做纯 Schema 测试，不改数据库。

### 小步骤 2：Job Model 与 Alembic migration

- 增加基础字段、旧要求快照、CHECK 和默认值。
- 实现确定性旧数据转换。
- 在专用 PostgreSQL 数据库往返验证。
- 正式数据库只在确认预检结果后向前升级。

### 小步骤 3：Job Service 业务规则

- 增加行锁、开放校验、状态迁移、关联计数和安全删除。
- 验证失败回滚和并发边界。

### 小步骤 4：Job API 与错误契约

- 接入状态筛选和三个状态动作。
- 固定业务异常到 HTTP 的映射。
- 运行 OpenAPI 路由唯一性和 API 自动化测试。

### 小步骤 5：岗位前端真实表单

- 扩展 TypeScript 类型和 API 调用。
- 接入创建、编辑、开放、关闭、重新开放和删除。
- 完成表单失败保留和确认交互。
- 完成状态：✅ 2026-08-15 已完成；岗位前端 2 项专项测试、阶段 5 前端 6 项回归和生产构建通过，真实浏览器/PostgreSQL 人工验收留在小步骤 7。

### 小步骤 6：下游只读边界

- AI 初筛新选择、公开投递骨架、Dashboard 和内部新增候选人按本设计读取岗位。
- 保留关闭岗位历史结果和历史名称显示。
- 完成状态：✅ 2026-08-15 已完成；新选择直接请求 `status=open`，历史展示继续读取全部岗位，新增边界测试连同既有前端回归共 9 项通过，生产构建通过。

### 小步骤 7：集成与人工验收

- 全量后端回归、前端定向测试、TypeScript 和生产构建。
- 临时 PostgreSQL 全链路验证。
- 用户在真实页面完成第 16 节人工验收。
- 验收后更新 `PROJECT_STATE.md`、实施计划和必要交接说明。

## 15. 自动化测试标准

### 15.1 Schema 测试

- v1 完整对象和空草稿对象。
- 缺字段、额外字段、错误 Schema 版本。
- 错误列表类型、错误整数、非法枚举。
- 字符串去空格、空项清理、完全重复项去重。
- 每个长度、数量、年限和人数边界。
- 创建 `closed`、空白标题和空更新拒绝。

### 15.2 Service 测试

- 创建草稿和默认空 v1。
- 创建并开放成功/失败。
- 所有合法和非法状态迁移。
- 开放岗位合法编辑和清空必填字段失败。
- 草稿/关闭岗位保存不完整内容。
- 重新开放重新执行校验。
- 每一种关联对象阻止删除。
- 无关联草稿/关闭岗位删除成功。
- commit/refresh/查询失败 rollback。
- 状态筛选和更新时间排序。
- 行锁读取和并发后最新状态校验。

### 15.3 API 测试

- 所有路由成功状态、响应 Schema 和 OpenAPI 挂载唯一。
- `404/409/422/500` 稳定 code 和安全文案。
- 查询状态枚举。
- 未知字段和普通更新改状态被拒绝。
- 删除冲突关联数量。

### 15.4 migration 测试

- 旧状态映射。
- 已知旧 requirements 映射。
- 未知字段完整进入 `legacy_requirements`。
- Job 数量、ID、标题、描述、时间和外键不变。
- 不完整旧开放岗位转草稿。
- `upgrade -> downgrade -> upgrade` 往返。
- `alembic check` 无待生成操作。

### 15.5 前端测试

- 请求路径和请求体转换。
- 完整 v1 表单映射和列表清理。
- 状态对应的按钮和确认文案。
- 开放失败字段映射。
- 保存失败不清空表单。
- AI 初筛、投递骨架和内部新增候选人只请求开放岗位。
- 关闭岗位历史结果仍可显示。
- TypeScript 严格检查和生产构建。

自动化测试不能证明真实 PostgreSQL migration、浏览器视觉和人工操作体验，因此必须继续完成真实数据库和人工验收。

## 16. 人工验收场景

1. 创建只有标题的不完整草稿；刷新页面后记录和空 v1 仍存在。
2. 点击开放；页面展示全部缺失字段，岗位保持草稿。
3. 补齐基础信息、职责、必备技能、年限和学历并开放；刷新后状态为开放。
4. 开放岗位出现在 AI 初筛、公开投递骨架和内部新增候选人的岗位选择中。
5. 尝试清空开放岗位必填字段；保存失败，页面输入仍在，数据库旧值和开放状态不变。
6. 合法编辑开放岗位；刷新后字段和 `updated_at` 更新，历史初筛结果不被改写。
7. 关闭岗位；它从所有新业务选择中消失，但历史候选人名称和历史初筛结果仍能查看。
8. 编辑关闭岗位并重新开放；完整时成功，不完整时列出缺失字段。
9. 删除无关联草稿和无关联关闭岗位成功；开放岗位删除失败。
10. 删除有关联 Candidate/Resume/ScreeningResult/Report 的岗位返回关联数量，历史数据不变。
11. 模拟后端或数据库失败；前端保留表单，数据库没有半写入。
12. 在 1440 像素桌面和严格 390 像素窄屏下完成列表、抽屉、确认框和错误定位检查，无整页横向溢出。
13. migration 前后旧岗位数量、ID、标题、原始 description、时间和关联数量一致；旧 requirements 快照可追溯。

## 17. 阶段完成标准

只有以下条件全部满足，阶段 6 才能标记完成：

- HR 能在新版页面创建草稿和完整开放岗位。
- HR 能编辑、关闭和重新开放岗位。
- 草稿和关闭岗位不能进入新投递或新初筛选择。
- 开放岗位始终满足固定 v1 和基础字段完整性。
- 删除不会破坏任何历史关联。
- 旧岗位、ID、原始描述和旧要求快照没有丢失。
- PostgreSQL、API、前端和 migration 验证全部通过。
- 用户完成真实页面人工验收并明确确认无问题。
- `PROJECT_STATE.md` 和实施计划按实际结果更新，不把未执行验证写成已完成。

## 18. 阶段结束后的简历表述与面试准备

完成后可以如实表述：

> 设计并实现结构化岗位管理模块，使用 Pydantic 严格版本化岗位要求、FastAPI/SQLAlchemy 状态机和 PostgreSQL 约束，支持岗位草稿、开放、关闭、重新开放、安全删除及旧 JSONB 数据无损迁移，并接入 React/Ant Design 岗位表单与开放岗位下游过滤。

不能表述为：

- 已实现 AI 自动生成或解析 JD。
- 已实现正式 AI 初筛或 Application 流程。
- 已实现完整权限、审批或审计系统。

面试官可能追问：

1. 为什么不能继续使用任意 JSONB？
2. Schema 版本和岗位内容版本有什么区别？
3. 为什么状态变更要用专用动作，而不是普通 PUT？
4. 开放岗位编辑如何保证不会变残缺？
5. 为什么关闭岗位不直接删除？
6. 如何防止删除破坏候选人和筛选结果？
7. Alembic 如何做到旧数据不丢失和可回滚？
8. 为什么不在阶段 6 使用 DeepSeek 解析 JD？
9. 为什么历史初筛结果不能随着岗位修改自动改写？
10. 自动化测试和真实 PostgreSQL 验证分别能证明什么？
