# 阶段 6 五段式 JD 整改设计补充

> 日期：2026-08-21
>
> 状态：业务需求与 6R-A—6R-D 顺序已获用户最终确认；6R-A—6R-D 已于 2026-08-22 完成并通过验收，阶段 7 继续受控暂停
>
> 上游权威文档：`2026-08-15-stage6-structured-job-management-design.md`
>
> 下游依赖：`../stage7/2026-08-20-stage7-jd-driven-ai-screening-redesign.md`

## 1. 文档目的与权威边界

原阶段 6 使用 `description + JobRequirementsV1` 保存岗位内容，前端把技能、最低年限、学历、经历、关键词和补充要求拆成多个细碎控件。阶段 7 又需要从混合的 `description` 和结构化要求中重新判断哪些内容是背景、职责、必备条件或加分条件。

本次整改把岗位 JD 改为 HR 更容易填写、语义边界更明确的五个独立多行文本字段：岗位背景、岗位职责、任职要求、加分项和备注。

本文只替代原阶段 6 设计中与以下内容有关的合同：

- `description` 与 `JobRequirementsV1` 数据结构；
- 岗位开放完整性中的 JD 要求；
- Job API、Schema、Model、Service 和 React 表单中的 JD 字段；
- 旧 JD 数据迁移策略；
- 阶段 7 在新合同落地前的安全暂停边界。

原设计中的 `draft/open/closed` 状态机、基础信息、行锁、事务、安全删除、关联保护和开放岗位下游过滤继续有效。发生冲突时，本文对 JD 字段及其实施顺序拥有更高权威性。

## 2. 已确认的业务决定

1. 岗位名称、所属部门、工作地点、用工类型和招聘人数保持不变。
2. 后续表单依次使用岗位背景、岗位职责、任职要求、加分项和备注五个大型多行文本框。
3. 岗位职责和任职要求在岗位开放时必填；岗位背景、加分项和备注选填。
4. 草稿继续只强制岗位名称，五个 JD 字段均允许暂时为空。
5. 五个字段直接保存普通文本，保留内部换行、编号和项目符号；不保存 HTML，不使用富文本编辑器。
6. 不再向 HR 展示技能标签、最低年限数字框、学历下拉框、经历列表、关键词和“其他要求”等旧控件。
7. 五个字段是五个独立数据库列和 API 字段，不包装进新的混合 JSONB。
8. 备注是候选人可见的公开说明，不是 HR 内部备注，不参与 AI 评价。
9. 当前只实现 HR 手工填写。未来综合 Agent 可以生成同一五字段合同的岗位草稿，但不能自动开放岗位；本次不实现 Agent、Prompt 或 AI 生成 JD。
10. 当前开发数据库没有 Job 或关联业务行，用户确认不迁移旧 JD 内容，直接建立新合同；若实施时发现任何 Job 行，自动迁移必须停止，不得删除或猜测转换。
11. 旧 `description`、`requirements`、`legacy_requirements` 和 `JobRequirementsV1` 退出当前运行边界，不做双写、不提供旧 API 兼容。
12. 阶段 7 暂停在现有小步骤 9，不再继续修补 JD18；阶段 6 新合同完成后，先重新设计五段式 JD 如何生成评价计划，再恢复阶段 7。

## 3. 用户场景与主流程

### 3.1 创建草稿

```text
HR 打开新增岗位
        ↓
填写岗位名称，可选填写基础信息和五段式 JD
        ↓
点击“保存草稿”
        ↓
后端校验已提交字段的类型和长度
        ↓
事务保存 status=draft
```

草稿只要求岗位名称非空。岗位职责和任职要求在草稿阶段可以为空，方便 HR 分次补充。

### 3.2 创建并开放

```text
HR 填写岗位基础信息和五段式 JD
        ↓
点击“保存并开放”
        ↓
校验基础信息 + 岗位职责 + 任职要求
        ↓
同一事务创建 status=open 的岗位
        ↓
阶段 7 新五段式合同尚未就绪时，不调用旧评价计划生成逻辑
```

岗位开放是确定性业务操作，不依赖 DeepSeek。AI 不可用或阶段 7 暂停都不能回滚已经成功保存的岗位。

### 3.3 编辑开放岗位

1. Service 使用行锁读取数据库中的最新岗位。
2. 将局部修改与旧值合并。
3. 对合并后的完整岗位重新执行开放校验。
4. 岗位职责或任职要求为空时拒绝整次保存，数据库保持旧值和 `open` 状态。
5. 合法修改一次提交，岗位继续保持 `open`。
6. 会影响 AI 评价语义的字段变化，未来应使旧评价计划过期；在新阶段 7 合同完成前，不允许旧计划生成逻辑继续运行。

### 3.4 关闭与重新开放

- 关闭、重新开放和删除继续使用原阶段 6 的专用状态动作。
- 关闭岗位允许保存不完整 JD，但重新开放时必须重新满足当前合同。
- 关闭不删除 Job、Application、Resume、报告或招聘历史。

## 4. 五段式 JD 数据合同

### 4.1 字段定义

| 页面名称 | API / Model 字段 | 类型与最大长度 | 草稿 | 开放 | 候选人可见 | AI 边界 |
| --- | --- | --- | --- | --- | --- | --- |
| 岗位背景 | `job_background` | `TEXT`，5,000 字符 | 选填 | 选填 | 是 | 只作岗位上下文 |
| 岗位职责 | `job_responsibilities` | `TEXT`，10,000 字符 | 选填 | 必填 | 是 | 拆为 `general` 事项 |
| 任职要求 | `candidate_requirements` | `TEXT`，10,000 字符 | 选填 | 必填 | 是 | 拆为 `required` 事项 |
| 加分项 | `preferred_qualifications` | `TEXT`，5,000 字符 | 选填 | 选填 | 是 | 拆为 `preferred` 事项 |
| 备注 | `public_notes` | `TEXT`，5,000 字符 | 选填 | 选填 | 是 | 不发送给筛选模型 |

字段命名说明：

- `candidate_requirements` 表示岗位预先声明的任职要求。
- `preferred_qualifications` 表示岗位预先声明的加分条件。
- 阶段 7 的 `bonus_highlights` 仍表示某份简历中超出 JD 基础事项的候选人额外亮点，不能与 `preferred_qualifications` 混为一谈。
- `public_notes` 是公开说明。当前阶段没有正式候选人岗位详情页，但字段从本次开始进入 Job 正式合同，阶段 8 的公开岗位读取将直接复用。

### 4.2 普通文本规则

五个字段统一遵守：

1. 输入不是字符串或 `null` 时拒绝。
2. 去除整段首尾空白；去除后为空的内容归一为 `null`。
3. 保留正文内部的换行、空行、编号、项目符号、大小写和标点。
4. 不强制“一行一项”，不限制自然段数量，也不由阶段 6 解析技能、学历或年限。
5. 不接收或渲染 HTML 语义；字符串中的尖括号只按普通文本显示。
6. 超过字段最大长度时拒绝整次请求，并定位具体字段。
7. 前端、API 和数据库均不得静默截断。

### 4.3 基础信息与开放完整性

基础信息继续使用原合同：

- `title`：必填，1—200 字符；
- `department`：开放时必填；
- `location`：开放时必填；
- `employment_type`：开放时必填且必须是合法枚举；
- `headcount`：开放时必填且为 1—999 整数。

新的开放完整性只额外要求：

- `job_responsibilities` 非空；
- `candidate_requirements` 非空。

不再要求：

- `description`；
- `required_skills`；
- `minimum_work_years`；
- `education_requirement`；
- `requirements.schema_version` 或任何 `JobRequirementsV1` 子字段。

## 5. 页面交互合同

### 5.1 表单顺序

```text
岗位名称
所属部门 / 工作地点
用工类型 / 招聘人数
岗位背景
岗位职责 *
任职要求 *
加分项
备注
```

- 基础信息区域保持现有两列表单布局。
- 五个 JD 字段纵向排列，全部使用大型 `Input.TextArea`。
- 岗位职责和任职要求显示必填标记；其他字段显示选填语义。
- 每个文本框默认约 6 行，内容增加时自动增高，到受控最大高度后内部滚动。
- 备注下方固定提示“候选人可见，请勿填写内部招聘信息”。
- 页面底部继续固定显示“取消、保存草稿、保存并开放”或对应编辑操作。

### 5.2 保存与错误反馈

- 保存失败时抽屉保持打开，HR 已输入内容不清空。
- 开放校验返回全部问题字段，前端滚动并聚焦第一个错误字段。
- 写请求执行中禁止重复提交和关闭抽屉。
- 表单有未保存修改时，关闭抽屉继续二次确认。
- 成功响应后再刷新列表，不做可能回滚的乐观更新。

### 5.3 岗位列表与下游读取

- 岗位列表不再读取旧职责数组或必备技能标签。
- 列表摘要优先显示 `job_responsibilities` 的第一段非空文本；没有时显示“岗位职责未填写”。
- 搜索范围至少覆盖岗位名称、部门、地点、岗位背景、岗位职责、任职要求和加分项；`public_notes` 可以用于普通文字搜索，但不影响 AI。
- 现有下游组件不得继续引用 `description` 或 `requirements.*`。
- 阶段 8 的正式公开岗位页面尚不在本次范围；未来候选人端只读取允许公开的基础字段和五段式 JD。

## 6. API、Schema、Service、Model 与 PostgreSQL

### 6.1 正式 Job 响应

概念响应如下：

```json
{
  "id": 1,
  "title": "AI 应用工程师",
  "department": "技术研发部",
  "location": "长沙",
  "employment_type": "full_time",
  "headcount": 5,
  "job_background": "我们正在建设面向业务场景的 AI 应用平台。",
  "job_responsibilities": "负责 AI 应用设计、开发和上线。",
  "candidate_requirements": "具备后端开发经验，能够独立完成应用交付。",
  "preferred_qualifications": "有 RAG 或 Agent 项目经验者优先。",
  "public_notes": "面试共三轮，候选人可提前准备项目介绍。",
  "status": "open",
  "created_at": "2026-08-21T10:00:00+08:00",
  "updated_at": "2026-08-21T10:00:00+08:00"
}
```

`JobCreate` 和 `JobUpdate` 不接收 `description`、`requirements`、`legacy_requirements` 或任何旧嵌套字段；Pydantic 的 `extra="forbid"` 必须拒绝它们。`JobRead` 也不返回旧字段。

### 6.2 分层职责

```text
React 五段式岗位表单
        ↓
FastAPI Job API：请求、响应和安全错误映射
        ↓
Pydantic Job Schema：五字段类型、长度和空白归一
        ↓
JobService：开放校验、状态、行锁和事务
        ↓
SQLAlchemy Job Model：五个独立 TEXT 列
        ↓
PostgreSQL jobs 表
```

- React 不自行创造第二套必填规则，只把后端字段错误映射到对应文本框。
- Schema 负责字段形状、长度、未知字段和普通文本归一。
- Service 负责草稿/开放语义、状态迁移、行锁和事务。
- Model/PostgreSQL 负责持久化和基础约束，不解析自然语言。
- Agent 未来只能通过强类型 Tool 调用现有 Job Service，不能直接写数据库。

### 6.3 数据库合同

`jobs` 新增五个可空 `TEXT` 列：

- `job_background`
- `job_responsibilities`
- `candidate_requirements`
- `preferred_qualifications`
- `public_notes`

`jobs` 删除：

- `description`
- `requirements`
- `legacy_requirements`

字段在数据库层允许 `NULL`，因为草稿和关闭岗位可以不完整。开放完整性由同一事务中的 Service 校验，而不是使用无法区分状态的简单 `NOT NULL` 约束。

## 7. 旧数据与 migration 策略

### 7.1 当前只读事实

2026-08-21 讨论期间，实际 PostgreSQL 只读计数为：

```text
jobs=0
applications=0
candidates=0
resumes=0
job_evaluation_plans=0
screening_reports=0
screening_runs=0
stage_histories=0
```

该结果只能证明当时的当前开发数据库为空，不能证明未来执行时或其他环境仍为空。

### 7.2 不迁移旧 JD 内容

- 不把旧 `description` 搬到岗位背景。
- 不把旧职责列表搬到岗位职责。
- 不把技能、年限、学历、经历或其他要求拼接成任职要求。
- 不把旧加分技能或经历搬到加分项。
- 不把关键词转换为任何评价标准。
- 不生成兼容快照或双写旧字段。

### 7.3 强制预检与失败语义

新增向前 migration 前必须再次记录：

- 当前 Alembic revision；
- `jobs` 总数和状态分布；
- JobEvaluationPlan、Application、Resume、ScreeningRun、ScreeningReport 和其他 Job 关联数量；
- `jobs` 旧列是否符合预期结构。

只要 `jobs` 不是 0 行，实施立即停止，不能自动删除、覆盖或转换。需要用户重新确认该环境的数据处理方案后，才能另写迁移补充。

### 7.4 migration 原则

- 只新增一条向前 Alembic revision，不修改任何既有 migration。
- 在空表前提下新增五列并删除三个旧列。
- migration 内增加防误执行保护；发现 Job 行时主动失败，不产生部分结构变化。
- 先在专用临时 PostgreSQL 数据库完成空表 `upgrade -> downgrade -> upgrade`。
- 正式开发数据库只执行确认后的 `upgrade head`，不使用用户数据测试 downgrade。
- downgrade 只保证空表结构往返，不能宣称恢复已经不存在的旧 JD 内容。
- `alembic check` 必须返回无待生成操作。

## 8. 阶段 7 安全暂停与后续衔接

### 8.1 为什么必须暂停

当前 JobEvaluationPlan 读取 `title/department/description/requirements`，并通过 AI 自由文本拆解与结构化字段补齐生成事项。五段式合同上线后，这些输入不再存在；继续调用旧逻辑会产生错误评价计划或运行异常。

因此阶段 6 后端合同切换必须同时提供受控暂停：

- 岗位保存、开放、关闭和重新开放继续正常工作；
- 不再触发旧 JobEvaluationPlan 自动生成；
- 旧评价计划生成/重新生成入口不得读取新 Job 后假装成功；
- 依赖评价计划的初筛保持可解释的 `waiting_plan` 或稳定“合同升级中”语义；
- 不删除或改写既有阶段 7 历史结果文件与已执行 migration；
- 当前数据库为空，不需要处理现存计划或报告行；实施前仍须再次预检。

受控暂停只阻止使用错误合同，不属于新五段式 AI 拆解实现。具体稳定错误码、入口行为和最小测试在 6R-B 前写入测试合同，不向浏览器泄露内部异常。

### 8.2 后续阶段 7 的固定输入边界

阶段 6 验收完成后，阶段 7 必须先更新专项设计并获得用户确认，再实现：

```text
title / department     → 岗位上下文
job_background         → 岗位上下文，不直接产生事项
job_responsibilities   → general 事项来源
candidate_requirements → required 事项来源
preferred_qualifications → preferred 事项来源
public_notes           → 不进入 Prompt，不参与指纹和评价
```

新的评价计划不再需要模型猜测区块优先级：事项所在字段决定 `general/required/preferred`。DeepSeek 只负责在各自字段内审阅完整文本、拆分最小可评价事项、识别语义重复并保留原文追溯。

`public_notes` 的修改不得使评价计划或报告过期。其他四个 JD 字段以及阶段 7 最终确认的上下文字段是否进入指纹，以后续阶段 7 设计为准。

## 9. 异常流程与失败语义

| 场景 | 行为 |
| --- | --- |
| 五字段只有空格或空行 | 归一为 `null` |
| 草稿缺职责或任职要求 | 允许保存 |
| 创建并开放缺职责或任职要求 | `422 JOB_OPEN_VALIDATION_FAILED`，不插入 Job |
| 开放岗位被编辑成缺职责或任职要求 | 拒绝整次保存，旧数据和状态不变 |
| 文本超过最大长度 | Pydantic `422`，定位字段，不截断 |
| 请求包含旧 `description/requirements` | 作为未知字段拒绝，不兼容写入 |
| 数据库写入失败 | rollback，不留下半份 JD |
| 阶段 7 暂停 | 岗位仍可开放；旧评价计划逻辑不运行，初筛等待新合同 |
| migration 发现 Job 行 | 主动失败并停止，不删除、不转换 |
| 备注包含内部信息 | 系统无法判断语义；前端明确提示候选人可见，责任由 HR 确认 |

## 10. 包含与不包含

### 10.1 本次包含

- 五个独立 Job 文本字段；
- Job Schema、Model、Service、API 和 PostgreSQL 合同切换；
- 岗位创建、编辑、列表和现有下游读取的字段更新；
- 草稿、开放、编辑开放岗位与重新开放校验；
- 旧 JD 字段和 `JobRequirementsV1` 退出运行边界；
- 空库前提下的向前 migration；
- 阶段 7 旧 JD 生成逻辑的受控暂停；
- 自动化、真实 PostgreSQL、前端构建和浏览器验收；
- 权威文档、项目状态和跨阶段顺序同步。

### 10.2 本次不包含

- 旧 JD 内容转换、兼容读取或双写；
- AI 生成、润色、改写或自动填写 JD；
- 新五段式 JobEvaluationPlan Prompt、Schema、拆解 Service 或真实 DeepSeek 调用；
- AI 自动开放岗位；
- 正式候选人公开岗位详情页；
- 薪资、岗位审批、历史版本、登录、RBAC 或完整审计；
- Application、Resume、HR 决策、面试、Offer、Agent 或 RAG 新功能。

## 11. 自动化与人工验收

### 11.1 后端自动化

- 五字段合法、`null`、空白归一和长度边界；
- 旧字段和额外字段拒绝；
- 草稿只要求标题；
- 开放与重新开放要求职责和任职要求；
- 开放岗位非法编辑事务回滚；
- 状态机、安全删除和行锁既有回归；
- Job API 请求/响应不含旧字段；
- 阶段 7 旧生成入口受控暂停，不调用 Adapter；
- HR 决策、Application、Resume 和报告数据不被岗位操作修改。

### 11.2 PostgreSQL 与 migration

- 预检记录当前表计数和 revision；
- 非空 `jobs` 保护测试；
- 空表 `upgrade -> downgrade -> upgrade`；
- 五列类型与可空性正确，旧三列删除；
- Job 以外表、外键和 Alembic 历史不被删除；
- `alembic current/head/check` 一致。

### 11.3 前端自动化

- 五个大型文本框顺序、标签和提示；
- 旧技能、年限、学历、经历、关键词和其他要求控件消失；
- 保存请求和读取映射使用五字段；
- 开放错误映射到职责和任职要求；
- 保存失败保留输入，成功后刷新；
- 岗位列表摘要与搜索不依赖旧数组；
- TypeScript 严格检查、全部 Node 测试和 Vite 生产构建。

### 11.4 人工与浏览器验收

1. 只填写标题并保存草稿，刷新后内容存在。
2. 缺职责或任职要求时不能保存并开放，页面定位全部错误。
3. 只填写必需基础信息、职责和任职要求即可开放；背景、加分项和备注可以为空。
4. 五个字段保存并恢复换行、编号和项目符号。
5. 备注显示候选人可见提示，页面不把普通文本渲染为 HTML。
6. 开放岗位非法编辑不覆盖数据库旧值；合法编辑后仍为开放。
7. 关闭、编辑和重新开放继续遵守状态规则。
8. 岗位列表不显示旧技能标签，摘要来自岗位职责。
9. 阶段 7 旧评价计划没有被调用，页面得到可理解的等待/暂停状态。
10. 1440×900、820×1180 和 390×844 下无整页横向溢出，文本框和固定底部操作可用。

验证能够证明五段式 Job 合同在当前代码、数据库和页面中一致工作，并证明旧 AI 合同不会误用新字段；不能证明新阶段 7 拆解质量、真实招聘准确率、未来 Agent 生成 JD 或阶段 8 公开岗位页已经完成。

## 12. 实施批次、依赖与停止点

本整改固定分为 6R-A—6R-D 四个批次。每批开始前重新检查 `git status`、相关差异、当前 Alembic revision、PostgreSQL 表计数和上一批验证结果。每轮只能完成一个已经由用户确认的批次，结束后停止等待确认。

### 12.1 总体顺序

| 批次 | 唯一目标 | 依赖 | 完成后停止点 |
| --- | --- | --- | --- |
| 6R-A | 用测试固定五段式合同和旧 AI 暂停边界 | 本文获用户最终确认 | 不改生产代码，等待 6R-B |
| 6R-B | 原子切换后端与 PostgreSQL 合同，并安全暂停阶段 7 旧输入 | 6R-A 红灯分类完成 | 不改 React，等待 6R-C |
| 6R-C | 将岗位页面和现有读取方切换到五段式字段 | 6R-B 后端合同稳定 | 不恢复阶段 7 AI，等待 6R-D |
| 6R-D | 完成全量、真实数据库与浏览器验收并交接阶段 7 | 6R-C 完成 | 阶段 6 整改结束，等待阶段 7 新设计确认 |

### 12.2 6R-A：自动化合同基线

唯一目标：先用自动化准确证明旧实现缺少哪些五段式能力，以及阶段 7 哪些旧入口必须暂停。

允许修改：

- Job Schema、Service、API、Model、migration 和前端相关测试；
- 阶段 7 与岗位输入边界直接相关的测试；
- 测试专用虚构数据和本批状态文档。

禁止修改：

- 任何生产 Schema、Service、Model、API、React、Prompt 或 Adapter；
- 数据库结构和真实业务数据；
- 真实 DeepSeek 调用。

必须交付：

- 五字段形状、长度、归一、开放校验和旧字段拒绝测试；
- 空库/非空库 migration 保护测试；
- Job API 响应、事务回滚和状态机回归；
- 前端五文本框、旧控件退出和字段映射测试；
- 阶段 7 旧入口不调用 Adapter 的暂停合同测试；
- 每个预期红灯到 6R-B 或 6R-C 的明确归属。

验证：测试必须被正常收集，不能使用 `skip/xfail`、删断言或导入错误冒充红灯。完成标志是合同矩阵完整、既有无关测试没有新增回归。失败时留在测试层修正夹具或需求映射。停止并等待用户确认 6R-B。

实施结果（2026-08-21）：

- 修改前确认分支 `2lcj`、HEAD 与 `origin/2lcj` 均为 `c169c55`，工作树没有已有差异或未跟踪文件；本批未覆盖用户修改。
- 代码 Alembic head 为 `e4c7a1b9d632`，但当前开发 PostgreSQL 仍在 `c8e1a6f4d205`。只读计数为 `jobs=1`、`candidates=2`、`resumes=9`；`applications/job_evaluation_plans/screening_reports/screening_runs/stage_histories` 因数据库尚未升级而不存在。现有 Job 状态为 `open`。本批没有升级数据库、执行 migration 或修改这些业务数据。
- 新增 6 个后端合同测试文件和 2 个前端合同测试文件。后端 23 个测试方法被正常收集，无导入、语法或夹具错误，产生 42 个断言红灯；前端 13 项正常收集，2 项通过、11 项红灯。未使用 `skip/xfail`，没有删除旧断言。
- 42 个后端红灯全部归 6R-B：14 个 Schema 字段/归一/长度/旧字段红灯，8 个 Model 列红灯，7 个 Service 创建并开放、开放草稿、重新开放、开放完整性与原子保存红灯，3 个 API 请求响应红灯，4 个 migration 空表保护红灯，以及 6 个阶段 7 受控暂停红灯。阶段 7 暂停错误固定为 HTTP `503` + `JOB_EVALUATION_PLAN_CONTRACT_UPGRADE_IN_PROGRESS`，岗位开放仍成功，旧评价计划 Service 和 Adapter 均不得调用。
- 11 个前端红灯全部归 6R-C：1 个响应映射红灯和 10 个五文本框、错误定位、旧控件退出、列表摘要、搜索及现有读取方红灯。已通过的 2 项只证明现有 HTTP 封装会原样发送五字段请求、错误解析器会保留新字段名，不证明前端合同已切换。
- 修改前旧 Job 合同 69 项、旧 JobEvaluationPlan 28 项通过。完成合同测试后，Job/计划既有回归 97 项、Application/HR 决策 43 项、Resume/报告 76 项和前端全部 19 个既有 Node 脚本均通过，证明本批新增测试没有制造无关回归。
- 当前数据库落后代码且已有 1 条 Job；依据第 7.3 节，6R-B 的正式 migration 不得在该库执行。进入 6R-B 前必须重新预检，并由用户明确决定这条开发数据的处理方式；不得自动删除、覆盖或转换。
- 本批没有修改任何生产 Schema、Service、Model、API、React、Prompt 或 Adapter，没有新增 migration，没有调用真实 DeepSeek。完成后停在 6R-A，等待用户明确确认是否进入 6R-B。

### 12.3 6R-B：后端与 PostgreSQL 原子合同切换

唯一目标：让“API → Schema → Service → Model → PostgreSQL”同时切换到五字段，并确保阶段 7 旧逻辑不会误用新 Job。

允许修改：

- `backend/app/schemas/job.py`
- `backend/app/models/job.py`
- `backend/app/services/job_service.py`
- `backend/app/api/jobs.py`
- 一条新的向前 Alembic migration；
- 阶段 7 计划协调/入口中实现受控暂停所需的最小代码，禁止触碰新拆解逻辑；
- 对应后端测试和本批状态文档。

禁止修改：

- JobEvaluationPlan Prompt、AI 输出 Schema、Adapter 或新五段式拆解 Service；
- Screening 评分合同；
- React 页面；
- 任何既有 migration；
- 自动删除非空 Job 数据。

必须交付：

- Job 五字段 Pydantic、SQLAlchemy 和 API 合同；
- 新开放校验、空白归一、事务与错误字段；
- 旧 `JobRequirementsV1` 和三个旧 Job 字段退出后端运行边界；
- 非空表保护的向前 migration；
- 旧评价计划入口受控暂停且 Adapter 调用为 0；
- 原 Job 状态机、安全删除、关联保护继续通过。

验证：定向和后端全量 pytest、真实 PostgreSQL 预检、临时库 migration 往返、正式开发库向前升级、`alembic check`、OpenAPI 路由唯一性和 `git diff --check`。完成标志是后端只接受/返回五字段、数据库只保留五段式 JD 列、阶段 7 旧调用被明确阻止。失败分别返回 Schema、Service、migration 或暂停门禁层，不进入前端。停止并等待用户确认 6R-C。

实施结果（2026-08-22）：

- 用户明确确认开发库唯一 Job #19 无需备份、可以直接删除。删除前再次核对 `id=19/title=AI招聘平台全栈工程师/status=open` 且 Candidate、Resume、Report 引用均为 0；随后精确删除 1 行并确认 `jobs=0`。该 Job 没有备份，不能从当前数据库直接恢复；Candidate 和 Resume 数据未删除。
- `JobCreate/JobUpdate/JobRead`、Job Model、Job Service 与 Job API 已同时切换为 `job_background/job_responsibilities/candidate_requirements/preferred_qualifications/public_notes`。五字段外层空白裁剪、纯空白归一为 null、长度限制、草稿只要求标题、开放时职责和任职要求必填、开放岗位编辑原子失败、旧字段和未知字段拒绝均由 6R-A 合同测试覆盖。
- 新增唯一 revision `f2b8c6d1a940`，在任何 DDL 前检查 `jobs` 行数。临时 PostgreSQL 空库完成 `upgrade -> downgrade e4c7a1b9d632 -> upgrade`；升级态只有五个可空 TEXT JD 列，降级态恢复旧三列。临时库插入一条虚构 Job 后，升级以 `STAGE6_FIVE_SECTION_JD_REQUIRES_EMPTY_JOBS` 主动失败，旧列仍在、新列未出现、行数仍为 1，证明事务没有留下部分结构；清空夹具后恢复 head，并删除临时库。
- 正式开发 PostgreSQL 只做向前 `upgrade head`，由 `c8e1a6f4d205` 升至 `f2b8c6d1a940`。最终 `current=head=f2b8c6d1a940`，`alembic check` 返回 `No new upgrade operations detected`；`jobs=0/applications=0/candidates=2/resumes=9/job_evaluation_plans=0/screening_reports=0/screening_runs=0/stage_histories=0`，jobs 只保留五个新 JD 列。
- Job 创建、更新、开放和重新开放不再触发旧 JobEvaluationPlan；显式 generate/regenerate 固定返回 HTTP 503 + `JOB_EVALUATION_PLAN_CONTRACT_UPGRADE_IN_PROGRESS`。Screening 对真实五段式 Job 只形成 `waiting_plan`（关闭岗位为 `paused`）上下文，`job_snapshot/evaluation_plan/sanitized_resume` 均为空，不会调用 Adapter。旧 Prompt、Adapter 和新五段式拆解逻辑均未修改，也没有调用真实 DeepSeek。
- 6R-A 后端合同 23/23 通过；旧 Job 核心回归 45/45、历史 JobEvaluationPlan Service 22/22、历史 ScreeningService 27/27 通过。后端全量为 694 passed、411 subtests passed，只有 1 条既有 PyPDF2 弃用 warning；OpenAPI 唯一路由测试包含在全量中。
- 为运行完整 pytest，仅在本地 `.venv` 安装 pytest 9.1.1，没有修改依赖清单。10 个只含 `__pycache__/*.pyc` 的退休 `rebuilt` 缓存目录被可恢复地移动到忽略目录 `tmp/6rb-retired-rebuilt-cache/`，没有删除源码或业务数据。
- 本批没有修改 React、JobEvaluationPlan Prompt、Adapter 或真实 AI 合同；6R-A 的 2 个前端合同通过项和 11 个 6R-C 预期红灯继续保留。`git diff --check` 通过。6R-B 到此停止，唯一下一步是等待用户明确确认 6R-C。

### 12.4 6R-C：React 五段式岗位体验

唯一目标：把岗位创建、编辑、列表和现有读取方全部切换到五个大型文本框和新 API。

允许修改：

- `frontend/src/features/recruitment/RecruitmentJobList.tsx`
- `frontend/src/features/recruitment/services/jobs.ts`
- 岗位样式和相关现有读取组件；
- 前端定向测试和本批状态文档。

禁止修改：

- 后端业务合同或 migration；
- 阶段 7 Prompt、Adapter、拆解、评分或真实模型调用；
- 正式阶段 8 公开岗位详情页；
- AI 生成 JD 按钮。

必须交付：

- 五文本框顺序、尺寸、必填/选填提示和备注公开提示；
- 旧细分控件和旧字段映射全部删除；
- 创建、编辑、错误定位、输入保留和列表摘要；
- 现有读取方不再引用 `description/requirements.*`；
- 普通文本安全展示和窄屏布局。

验证：前端定向测试、全部 Node 测试、TypeScript 严格检查、Vite 生产构建和 `git diff --check`。完成标志是前端运行边界不含旧 JobRequirements，所有请求与新后端一致。失败返回组件、Service 类型或样式层，不修改后端合同。停止并等待用户确认 6R-D。

实施结果（2026-08-22）：

- `jobs.ts` 的响应、页面模型和写请求只保留五段式字段；岗位页面的创建、编辑、搜索、列表摘要和后端字段错误定位全部切换到新合同。五个字段按“岗位背景 → 岗位职责 → 任职要求 → 加分项 → 备注”排列，均使用大型普通多行文本框并声明 5000/10000/10000/5000/5000 字符上限；职责和任职要求明确提示开放时必填，备注明确提示候选人可见且不参与 AI。
- 岗位页面已删除岗位描述、技能标签、工作年限、学历、经历、关键词和其他要求等旧控件。申请岗位读取 Service 和申请页预览改用五段式字段，通过 React 文本插值和 `white-space: pre-wrap` 保留换行，不引入 HTML 渲染。
- 阶段 7 历史评价计划快照仍需只读解释旧数据，因此其旧结构被收口为阶段 7 自有的 `LegacyJobEvaluationPlanRequirements`，不再从当前 Job Service 导入或进入新 Job 请求边界；本批没有恢复计划生成、修改 Prompt/Adapter 或调用真实模型。
- 6R-A 的前端五段式合同由原 2 项通过、11 项预期红灯转为 13/13 通过。更新 3 个既有前端测试的虚构 Job 夹具和断言后，定向测试 16/16、前端全量 32/32 通过；TypeScript 严格检查和 Vite 5.4.21 生产构建通过，共转换 3121 个模块。
- 本批没有修改后端 Schema、Service、Model、API、migration 或 PostgreSQL 业务数据，也没有执行 migration。正式库沿用 6R-B 基线：`current=head=f2b8c6d1a940`，`jobs=0/applications=0/candidates=2/resumes=9/job_evaluation_plans=0/screening_reports=0/screening_runs=0/stage_histories=0`。`git diff --check` 通过。
- 自动化结果证明前端编译边界、请求映射和静态交互合同已与五段式后端一致，且简历、申请、HR 决策及阶段 7 既有前端测试没有新增回归；尚不能证明真实浏览器尺寸、真实 PostgreSQL 页面操作或前后端完整人工主链，这些留给 6R-D。6R-C 到此停止，唯一下一步是等待用户明确确认 6R-D。

### 12.5 6R-D：完整验收与阶段 7 交接

唯一目标：证明五段式岗位管理可真实操作、旧 AI 合同安全暂停，并形成恢复阶段 7 所需的准确交接。

允许操作：

- 修复本步骤验收暴露的、已确认合同范围内的最小缺陷；
- 自动化、真实 PostgreSQL、浏览器人工验收；
- 更新阶段 6 验收记录、`PROJECT_STATE.md`、实施计划和阶段 7 依赖说明。

禁止操作：

- 真实 DeepSeek JD 拆解或筛选调用；
- 实现新阶段 7 五段式 Prompt/Schema/Service；
- 开始阶段 8、Agent 或 RAG；
- 为通过验收放宽开放必填、事务或 migration 防误删规则。

必须完成：

- 第 11 节全部自动化、数据库和浏览器场景；
- 后端与前端全量回归；
- PostgreSQL current/head/check 和业务表计数记录；
- 旧 JobRequirements 运行时扫描为 0；
- 阶段 7 旧 Adapter 实际调用为 0；
- 验收能证明与不能证明的书面记录。

完成标志：阶段 6 五段式整改通过，岗位主链可用，阶段 7 保持受控暂停。失败回到实际责任层修复并重验，不提前恢复 AI。结束后停止，唯一下一步是讨论并编写阶段 7 五段式 JD 评价计划整改设计，获得用户确认后才能编码。

实施结果（2026-08-22）：

- 后端全量 694 passed（411 个子用例通过），五段式定向 19 passed（48 个参数化子用例通过），migration 合同 4 passed；前端 6R-D 定向 12/12、全量 32/32、TypeScript 与 Vite 生产构建均通过，转换 3121 个模块。
- 正式 PostgreSQL `current=head=f2b8c6d1a940`，`alembic check` 无待生成操作。真实 API 和 Microsoft Playwright 页面完成草稿、开放校验、五段保存、非法开放编辑回滚、关闭、关闭态编辑、重新开放与删除；验收后八张业务表恢复到原计数。
- 1440×900、820×1180、390×844 三档页面均无整页横向溢出，底部操作区可见；五段普通文本保留换行和项目符号，HTML-like 文本只按字面显示。截图和完整矩阵见 `2026-08-22-stage6-five-section-jd-remediation-acceptance.md`。
- 验收修复了成功通知上下文、静态 Modal、未挂载 Form reset 三个 React/Ant Design 警告，并把评价计划页面改为直接暂停、移除旧生成/重新生成写入口；历史计划仍只读。阶段 7 Adapter 调用为 0，未调用真实 DeepSeek。
- 阶段 6 五段式整改至此完成。唯一下一步是讨论并编写阶段 7 五段式 JD 评价计划整改设计；获得用户确认前不得实现新 Prompt、Schema、Service、Adapter 或调用真实模型。

## 13. 未来 Agent 边界

未来综合 Agent 可以帮助 HR 生成 JD，但必须复用本次五字段合同：

```text
HR 描述招聘需求
        ↓
Agent 调用强类型 JD 草稿 Tool
        ↓
Tool 调用 Job Service 创建或更新 draft
        ↓
HR 查看、修改并明确确认
        ↓
HR 独立执行开放岗位
```

AI 只能生成草稿，不能自动开放、关闭、删除岗位，也不能绕过开放校验。五个字段保持来源中立，不记录“只允许人工填写”的限制；本次不提前建设 Agent 能力。

## 14. 实施总门禁

1. 用户最终确认本文及 6R-A—6R-D 顺序前，不得修改业务代码、测试、Prompt、Schema、Model、数据库或前端。
2. 每轮只完成一个已确认批次，报告修改文件、链路位置、验证结果、证明边界和剩余风险后停止。
3. 任何核心字段、必填规则、迁移保护、阶段 7 暂停方式或批次顺序变化，必须先更新本文并重新获得用户确认。
4. 不修改既有 migration，不删除历史质量结果，不使用 reset/clean 覆盖当前工作区修改。
5. 阶段 6 验收完成前不恢复阶段 7；阶段 7 新设计确认前不实现新五段式拆解。
