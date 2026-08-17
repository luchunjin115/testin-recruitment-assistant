# 阶段 7：Application 与 AI 初筛专项设计及执行计划

> 日期：2026-08-17
>
> 状态：评分方案变更确认中；小步骤 1—5 已完成并保留，步骤 6 暂停进入业务代码
>
> 上游依据：`2026-07-15-hr-agent-platform-design.md`、`2026-08-14-post-stage5-product-roadmap.md`、`../implementation-plan.md`
>
> 外部参考：`../research/2026-08-15-github-recruiting-project-comparison.md`
>
> 前置门禁：阶段 6 已于 2026-08-17 获用户确认完成；2026-08-17 用户决定采用 Reqcore 式“预设模板 + AI 根据岗位生成评分项”，该变更涉及 Rubric 数据模型、Prompt 和验收标准，重新打开评分子方案确认门禁，确认本文修订后才能继续步骤 6

## 1. 文档目的

本阶段把阶段 5 的结构化简历和阶段 6 的结构化岗位连接起来，建立以 `Application` 为中心的正式 AI 初筛底座。

大白话理解：`Candidate` 只说明“这个人是谁”，`Application` 才说明“这个人用哪份简历申请了哪个岗位、AI 怎么评价、HR 最后怎么决定”。同一个人可以申请多个岗位，每次申请都必须拥有独立的评分、决策和历史。

本设计已经吸收 2026-08-17 的逐项业务讨论结果。后续开发必须按第 22 节的小步骤推进；任何会改变字段、状态、评分、人工决策或验收标准的问题，都必须先暂停并更新本文档，不能只改代码。

### 1.1 2026-08-17 Rubric 方案变更

用户确认借鉴 Reqcore 的核心思路：系统提供预设 Rubric 模板，也允许 DeepSeek 根据当前岗位的结构化要求和 JD 默认生成 5—8 个岗位专用语义评分项，简单/复杂岗位允许 4—10 个。Python 确定性规则不计入该数量；生成结果只是一份待确认草稿，不能自动成为正式招聘标准。

本项目不直接照搬 Reqcore 的“所有评分都交给模型”方式，而是保留已经确认的混合边界：

```text
五个稳定大维度与 Python 确定性规则
                +
模板或 AI 生成的岗位专用语义评分项
                +
HR 审核确认与版本化发布
```

用户进一步确认两类规则使用两个明确入口，不让系统猜测执行者：结构化 JobRequirements 只产生 Python 可执行确定性规则；Rubric 编辑器中的模板项、AI 建议项和 HR 手动新增项都是语义规则，发布后由 Prompt Builder 注入 DeepSeek。Python 不解析 HR 自由文本规则，DeepSeek 不接管明确的字段比较。

本次变更替代第 12 节原先“固定 13 个内部子项 + 六档语义换算”的长期方案。小步骤 1—5 已完成的 Application、状态机、Rubric 版本、五维权重、确定性规则、并发和审计能力继续保留；固定子项和六档换算代码将在新的“小步骤 5A”中按确认后的设计调整，不能把旧实现描述为最终方案。

## 2. 当前事实与主要问题

当前已具备：

- 阶段 5 已能安全上传 PDF/DOCX/TXT、提取 `Resume.raw_text`、生成严格结构化草稿，并由 HR 确认后创建 Candidate。
- 阶段 6 已建立 `JobRequirements v1`、`draft/open/closed` 状态、真实岗位表单和开放岗位读取边界。
- PostgreSQL 已有 Candidate、Job、Resume、ScreeningResult、Report 和 ActivityLog 等基础模型。
- `/stage3/screening` 目前只能读取已有 ScreeningResult，不会启动新的 AI 评分。
- 当前 ScreeningResult 使用 `candidate_id + job_id` 唯一约束，只能保留一条结果，无法支持重跑历史。
- 当前 Candidate 使用 `applied_job_id` 和单一 `status` 表达岗位及流程，无法支持一个人独立申请多个岗位。
- 阶段 6 验收时 PostgreSQL 有 30 条 Candidate、8 条 Job、0 条 Resume 和29条ScreeningResult，旧数据必须无损迁移。

当前不足：

- 没有 Application 和 Application 阶段历史。
- AI 处理状态、HR 决策和招聘阶段混在 Candidate 状态中。
- 没有正式的规则 + 大模型评分流水线。
- 没有岗位级 Rubric、逐项证据、输入快照和版本。
- 没有当前有效结果、过期结果和失败重跑的稳定语义。
- 没有 HR 内部录入后的自动评分和正式通过/备选/淘汰动作。
- 没有旧 Candidate/ScreeningResult 到 Application 的确定性迁移。

## 3. 阶段目标与范围

### 3.1 本阶段包含

1. 新增 Application、StageHistory 和版本化岗位 ScreeningRubric。
2. Candidate 与一次具体岗位申请分离。
3. AI 状态、HR 决策、招聘阶段和记录生命周期分离。
4. 候选人页面“HR 直接新增”和 AI 初筛中心“录入新申请”两种内部入口。
5. 新 Application 必须具有有效手机号、邮箱、开放岗位和当前简历。
6. Candidate 去重、联系方式冲突提示和同岗位有效申请拦截。
7. 确定性规则 + 单次 DeepSeek 语义判断 + Service 统一计分。
8. 岗位级版本化 Rubric、预设模板、AI 生成岗位专用评分项、HR 确认发布、逐项证据和公平性约束。
9. 首次自动评分、手动重跑、输入指纹、历史结果和当前有效结果。
10. 同一开放岗位最多5个 Application 的小批量评分。
11. HR 通过、备选、淘汰、撤销和原因审计。
12. Application 作废、Candidate 归档和历史数据保护。
13. 旧 30 条 Candidate、29 条 ScreeningResult 的迁移预览和无损迁移。
14. 20份脱敏样本的真实 DeepSeek 质量评估。
15. `/stage3/screening`、候选人列表、候选人详情和岗位表单的阶段 7 交互。

### 3.2 本阶段不包含

- 不实现公开候选人投递；属于阶段 8。
- 不实现 Redis 持久化队列或后台 Worker；属于阶段 8。
- 不承诺超过5人的同步批量处理；大规模处理属于阶段 8。
- 不实现面试安排、面试反馈、Offer、录取和候选人退出；属于阶段 9。
- 不实现首页综合 Agent、LangGraph 或业务 Tools；属于阶段 10。
- 不实现 RAG、Embedding、Chroma 候选人召回或公司知识库；属于阶段 11。
- 不实现登录、RBAC、正式用户身份和最终隐私删除策略；属于阶段 12。
- 不实现 MCP Server、邮件、日历、ATS、多租户或计费。
- 不允许 AI 自动通过、自动备选、自动淘汰、自动录取或自动撤销 HR 决定。
- 不使用向量相似度代替正式初筛。
- 不增加 PDF 转 Markdown 文件流程。

## 4. 核心业务对象与关系

```text
Candidate 人员本人
    ↓ 一对多
Application 一次岗位申请
    ├── Job 目标岗位
    ├── Resume 当前简历
    ├── ScreeningRubric 当前岗位评分规则
    ├── ScreeningResult 多次评分历史
    └── StageHistory 招聘阶段与 HR 决策历史
```

### 4.1 Candidate

Candidate 保存相对稳定的人员资料。Candidate 可以在数据库中早于 HR 通过存在，但候选人页面不展示全部 Candidate。

候选人页面的业务展示条件是：

```text
Application.hr_decision == passed
```

页面每一行对应一个已通过的 Application。同一个 Candidate 通过两个岗位时显示两行；Candidate 详情页再按人聚合全部申请。

### 4.2 Application

建议字段：

| 字段 | 规则 |
| --- | --- |
| `id` | PostgreSQL 主键 |
| `candidate_id` | 必填，关联 Candidate |
| `job_id` | 必填，关联 Job |
| `current_resume_id` | 新记录必填；legacy 迁移允许为空 |
| `source` | `hr_direct/hr_screening/public_apply/legacy_migration` |
| `lifecycle_status` | `active/ended/voided` |
| `recruitment_stage` | 当前招聘阶段 |
| `ai_status` | 当前 AI 处理状态 |
| `hr_decision` | `pending/passed/backup/rejected` |
| `current_screening_result_id` | 当前最近成功结果，可空 |
| `applied_at` | 带时区申请时间 |
| `created_at/updated_at` | 服务端维护 |
| `legacy_stage` | 旧数据原状态，可空，只读 |

同一 Candidate、同一 Job 只能存在一个 `lifecycle_status=active` 且未作废的 Application。阶段 7 的 rejected 和 voided 会结束当前申请；阶段 9 增加 hired、withdrawn 等终态时同步扩展生命周期规则。

### 4.3 StageHistory

StageHistory 只追加、不更新、不删除，至少保存：

- `application_id`
- 原招聘阶段与新招聘阶段
- 原 HR 决策与新 HR 决策
- `reason_code` 与补充说明
- `actor_type/actor_id/actor_label`
- 关联的 ScreeningResult ID，可空
- 是否属于人工覆盖 AI 建议
- 操作时间

### 4.4 JobScreeningRubric

每个岗位拥有版本化 Rubric。建议使用独立表而不是把所有版本覆盖写入 Job：

- `job_id`
- `version`
- 五个维度权重
- `source_type`：`system_default/template/ai_generated/hr_adjustment/legacy_migration`
- `template_key`：`standard/technical/non_technical`，可空
- `status`：`draft/active/superseded`
- 岗位专用评分项列表及其维度、说明、评估方式、权重份额和评分锚点
- 生成所依据的 JobRequirements 指纹
- AI 生成时使用的 Prompt、模型和输出 Schema 版本
- HR 确认人、确认时间
- 推荐阈值版本
- 公平性规则版本
- `is_current`
- 创建人、创建时间和变更原因

新岗位仍在同一事务内自动获得合法的 `standard` 默认 Rubric，岗位创建不依赖 DeepSeek 成功。HR 可以改用技术/非技术模板，也可以主动请求 AI 根据岗位生成建议。模板预览或 AI 生成结果先保存为 draft；只有 HR 明确确认后才发布为 active/current 版本。岗位开放时必须存在合法且已确认的当前 Rubric。修改开放岗位 Rubric 会创建新版本，不覆盖旧版本。

### 4.5 ScreeningResult

ScreeningResult 从“候选人 + 岗位唯一结果”改为“Application 的一次不可覆盖评分执行”。建议字段：

- `application_id`
- `candidate_id/job_id/resume_id` 快速查询外键或快照标识
- `attempt_number`
- `execution_status`
- `input_fingerprint`
- 总分、推荐等级和证据覆盖率
- 硬性条件逐项检查
- 五个维度及子项得分
- 优势、风险、理由和待确认问题
- 简历证据与岗位证据
- Candidate 脱敏输入快照
- Resume、JobRequirements 和 Rubric 快照
- 规则、Prompt、模型、Job Schema、Resume Schema 版本
- 稳定错误码和安全错误说明
- 开始、结束、耗时、token 和估算费用
- 触发原因、是否强制重跑和操作人

已结束的 ScreeningResult 不允许普通更新或删除。Application 的 `current_screening_result_id` 只在新评分成功后切换；新评分失败时继续指向旧成功结果。

## 5. Application 创建入口

### 5.1 候选人页面“新增候选人”

该入口代表 HR 已人工判断通过初筛：

```text
选择开放岗位
→ 上传并识别简历
→ HR 检查和修改资料
→ HR 明确确认人工通过
→ 保存 Candidate + Resume + Application + StageHistory
→ 立即进入候选人页面
→ 自动启动一次 AI 岗位评分
```

创建后的固定语义：

- `source=hr_direct`
- `hr_decision=passed`
- `recruitment_stage=screening_passed`
- 首次评分必须尝试执行
- AI 低分、blocked 或 failed 都不能撤销 HR 通过

确认文案必须明确说明：该操作代表 HR 人工通过，AI 评分只作为补充参考。

### 5.2 AI 初筛中心“录入新申请”

```text
选择开放岗位
→ 上传或选择简历
→ 创建或复用 Candidate
→ 保存 Application
→ 自动启动 AI 评分
→ 进入等待 HR 决策
→ HR 通过后才进入候选人页面
```

固定语义：

- `source=hr_screening`
- `hr_decision=pending`
- 初始 `recruitment_stage=applied`
- AI 执行结束后进入 `hr_review`

### 5.3 已有候选人发起新岗位申请

候选人详情允许为已有 Candidate 选择另一个开放岗位，并选择已有简历或上传新简历。新 Application 必须重新评分和重新作出岗位级 HR 决策，不能继承其他岗位的通过状态。

### 5.4 强制联系方式和岗位

所有新 Application 必须同时具有：

- 非空姓名
- 有效手机号
- 有效邮箱
- 开放岗位
- 当前简历

缺少任一项不得创建正式 Application。阶段 4 的未绑定临时 Resume 可以暂存，取消或超时后继续按既有清理规则处理。

## 6. Candidate 去重与资料冲突

手机号统一去除空格、短横线和格式差异；邮箱去除首尾空白并使用不区分大小写的标准化值。

| 情况 | 行为 |
| --- | --- |
| 手机和邮箱都匹配同一 Candidate | 提示并复用 Candidate |
| 两者都没有匹配 | 创建新 Candidate |
| 手机匹配但邮箱不匹配 | 身份冲突，人工核对 |
| 邮箱匹配但手机不匹配 | 身份冲突，人工核对 |
| 手机和邮箱分别匹配不同 Candidate | 禁止自动合并，人工核对 |
| 只有姓名相同 | 只提示疑似重复，不自动合并 |

复用 Candidate 时，新简历识别结果不能静默覆盖已有正式资料。前端展示差异，由 HR 逐项选择保留旧值、采用新值或暂不更新。

如果同一 Candidate、同一 Job 已有未结束 Application，不创建重复记录；重复提交直接返回现有 Application，上一条结束后才允许创建新申请。手机号和邮箱已经共同识别到同一 Candidate 时，阶段 7 不允许强制另建重复人员。Candidate 合并不进入阶段 7。

## 7. 状态机与人类决策边界

### 7.1 AI 状态

阶段 7 使用：

```text
not_started -> screening -> completed
                         -> failed
not_started -> blocked
failed/blocked -> screening（HR 手动重试）
```

阶段 8 再增加 `queued/extracting/structuring`。`blocked` 表示前置资料不足、岗位关闭或关系错误且没有调用模型；`failed` 表示执行过程中发生模型、格式或持久化失败。

### 7.2 HR 决策

```text
pending -> passed
        -> backup
        -> rejected
backup  -> passed/rejected
passed  -> backup/rejected
rejected -> 撤销淘汰 -> pending
```

所有反转必须填写原因并追加历史。AI 不能执行任何迁移。

### 7.3 阶段 7 招聘阶段

```text
applied -> hr_review -> screening_passed
                     -> backup
                     -> rejected
```

HR 直接新增可以在创建时直接进入 `screening_passed`，但必须记录 `hr_direct_entry` 历史。旧数据的面试、Offer 和 hired 阶段只读保留，阶段 9 再接入正式动作。

### 7.4 候选人页面与初筛中心

- 候选人页面只展示 `hr_decision=passed` 的 Application。
- 备选留在 AI 初筛中心备选分类。
- 淘汰进入历史分类，不删除数据。
- AI 初筛中心录入的 Application 在 `screening` 期间不开放 HR 决策；进入 `completed/blocked/failed` 任一终态后转为 `hr_review`，再由 HR 结合现有资料决定通过、备选或淘汰。
- AI 重新评分不会自动改变页面归类。

## 8. Resume 绑定与评分输入

### 8.1 当前简历

每个新 Application 必须绑定一份当前 Resume。同一 Resume 可以被该 Candidate 的多个 Application 使用，不能绑定其他 Candidate 的 Resume。

第一次评分前允许切换 Resume。已有结果后更换 Resume：

1. 保留旧结果及旧 Resume 绑定。
2. 更新 Application 当前 Resume。
3. 旧结果标记为基于历史输入。
4. 当前评分标记过期。
5. HR 手动启动新评分。

HR 决策不会因更换简历自动撤销。

### 8.2 输入优先级

评分输入使用：

```text
HR 已确认 Candidate 结构化资料
+ 本次 Resume 原文和结构化快照
+ JobRequirements
+ 当前 JobScreeningRubric
```

信息优先级为 HR 已确认资料、简历原文证据、AI 结构化草稿。出现冲突时不得静默选择，结果必须列入待确认问题。

### 8.3 最低输入

满足下列任一条件即可评价：

- Resume 原文可读；或
- HR 已确认至少一类有效岗位相关资料，如技能、工作、项目、教育或证书。

部分字段缺少不阻止评分，使用 `unknown`。原文不可读且结构化资料基本为空时不调用模型、不返回0分，Application 标记 blocked。

## 9. Job 与 Rubric 生命周期

- 只有开放岗位允许创建 Application、首次评分和重跑。
- 创建 Job 时自动生成安全的 `standard` 默认 Rubric v1，不调用 DeepSeek，不要求 HR 从空白开始配置。
- HR 可在岗位草稿或开放状态下预览 `standard/technical/non_technical` 模板，或主动发起一次 AI 生成；AI 生成不是岗位创建或保存的必经步骤。
- AI 生成基于生成时的 JobRequirements/岗位描述指纹。生成后岗位评分输入发生变化时，proposal 标记 stale，禁止直接发布，必须重新生成或由 HR 明确重新编辑确认。
- AI 生成失败、超时、非法 JSON、偏见字段或不合规评分项时，只把本次 proposal 记为 failed；当前 active Rubric 和岗位数据保持不变。
- AI 生成或模板预览不会自动生效；HR 确认发布后才创建新的 active 版本。
- 岗位关闭后已有 Application、HR 决策和结果继续保留并可查看。
- 关闭前已经启动的评分使用启动时快照完成；关闭后不能新建下一次评分。
- 岗位重新开放后才恢复新申请和新评分。
- 修改职责、技能、年限、学历、经历、关键词、补充要求或参与评分的岗位描述，会改变评分输入指纹。
- 招聘人数或不参与评分的展示字段变化不使结果过期。
- 评分相关字段变化后旧结果保留但标记 outdated，HR 决定是否重跑。
- 岗位和 Rubric 修改不能自动改变 HR 决策。

## 10. AI 初筛工作流与技术选择

```text
Application
    ↓ 前置关系与岗位开放校验
读取 HR 已确认的当前 Rubric，并生成脱敏 Candidate/Resume/Job/Rubric 快照
    ↓
确定性规则检查
    ↓
Prompt Builder 注入岗位专用评分项
    ↓
单次 DeepSeek 严格 JSON 语义评价
    ↓
Pydantic 严格校验
    ↓
ScreeningService 按固定 Rubric 计算
    ↓
事务保存 ScreeningResult
    ↓
更新 Application AI 状态和当前结果
```

本阶段不使用 LangGraph。该流程顺序固定，不需要模型决定下一步、暂停等待确认或动态选择工具；普通 Service 更简单、更可测。阶段 10 的综合 Agent 才使用 LangGraph 编排多个强类型 Tool。

正常一次评分最多调用一次 DeepSeek。输出无效或调用失败后不自动连续重试，由 HR 决定是否重跑。模型 Provider 通过 Adapter 抽象，业务 Service 不直接写死 DeepSeek SDK。

Rubric AI 生成与候选人评分是两个不同调用：前者只在 HR 主动点击“AI 生成评分项”时发生，并生成待确认草稿；后者在 Application 评分时读取已确认 Rubric。两者分别记录 Prompt、模型、耗时、token、费用和失败信息，不能混成一次执行记录。

## 11. 脱敏与公平性

传给模型的数据必须排除：

- 姓名、手机号、邮箱
- 性别、年龄、出生日期
- 民族、婚姻、生育状况
- 照片、身份证号、详细地址
- 与岗位无关的个人身份信息

学历规则只比较学历层级，不让模型推断学校档次或 985/211。不得默认使用 GitHub 活跃度评价候选人。模型输入使用无真实身份的 Application 引用。

脱敏在后端 Service 完成并自动测试，不能依赖 Prompt 自觉忽略。禁止字段不得进入 Prompt、开发缓存、评分快照和模型调用日志。

## 12. Rubric 与权重

### 12.1 稳定五维外框

| 维度 | 默认 | HR 可调范围 |
| --- | ---: | ---: |
| 必备技能与硬性要求 | 40 | 30—50 |
| 工作经历与岗位职责相关性 | 25 | 15—35 |
| 项目、成果与能力深度 | 20 | 10—30 |
| 加分技能与加分经历 | 10 | 0—20 |
| 关键词及补充要求 | 5 | 0—10 |

权重必须是整数、总和为100并能一键恢复默认。推荐阈值、公平性规则和证据规则不允许岗位单独修改。

五个大维度继续作为稳定、公平、便于比较的外框，已完成的范围校验和总和 100 规则继续保留。岗位专用评分项必须映射到其中一个维度，不能由模型创建第六个隐藏维度。

### 12.2 预设模板

阶段 7 第一版内置三套模板：

| 模板 | 适用场景 | 行为 |
| --- | --- | --- |
| `standard` | 无法明确分类或通用岗位 | 新建岗位自动使用的安全默认值 |
| `technical` | 开发、测试、数据、AI 等技术岗位 | 提供技术栈、职责、项目、能力深度等建议项 |
| `non_technical` | 产品、运营、销售、HR 等非技术岗位 | 提供职责、业务经验、协作、成果等建议项 |

模板是后端版本化资产，不允许前端提交任意 Prompt。选择模板先生成预览，HR 确认后才发布新 Rubric 版本。阶段 7 不建设“公司自定义模板库”管理页面；后续真实复用需求明确后再单独设计。

### 12.3 AI 根据岗位生成评分项

HR 可主动要求 DeepSeek 读取岗位标题、职责、必备/加分技能、最低年限、学历、必备/加分经历、关键词、补充要求和参与评分的岗位描述，默认生成 5—8 个岗位专用**语义评分项建议**。简单岗位最低允许 4 个，复杂岗位最多允许 10 个；Schema 使用 4—10 个作为严格合法范围。

上述数量只统计需要大模型理解上下文的语义项。必备技能、明确工作年限、最低学历层级、明确加分技能和关键词等 Python 确定性规则按岗位要求自动产生，不占用 4—10 个名额。生成 Prompt、Schema 校验和 HR 审核都必须阻止语义项与确定性规则评价同一事实，避免同一段简历证据重复得分。

每个建议项至少包含：

| 字段 | 规则 |
| --- | --- |
| `key` | 岗位 Rubric 内唯一、稳定的小写标识 |
| `name` | HR 可读的评分项名称 |
| `description` | 只描述能从简历材料核对的岗位相关能力 |
| `dimension` | 必须属于固定五维之一 |
| `max_score` | 第一版固定为 10 |
| `suggested_share` | 该大维度内部的建议占比，由 Service 归一化 |
| `high_score_anchor` | 9—10 分需要什么证据 |
| `mid_score_anchor` | 4—8 分如何区分 |
| `low_score_anchor` | 0—3 分或缺少证据的边界 |

AI 只能生成语义项。必备技能、明确工作年限、最低学历层级、明确加分技能和关键词等可确定内容，由系统从 JobRequirements 自动生成确定性规则项，不能被 AI 删除、改写或降级为主观判断。

确定性规则不接受 HR 在 Rubric 编辑器中输入一段自然语言后交给 Python 猜测。HR 必须在结构化 JobRequirements 表单填写明确字段，Service 再编译为包含 `source_field`、`operator`、`expected_value` 和 `on_missing` 的可执行规则。例如最低 3 年工作经验编译为 `total_work_months >= 36`，最低本科学历编译为学历等级比较，必备技能编译为规范化技能集合包含判断。候选人材料缺少可比较值时返回 `unknown`，不能伪装为 `failed`。

Rubric 编辑器允许 HR 从零手动新增语义项，例如“支付系统故障排查能力”。手动项必须设置唯一 key、名称、说明、固定五维归属、0—10 分锚点和同维度建议占比；它与模板项、AI 生成项共同计入 4—10 条语义项总量，并接受相同的公平性、重复评价、证据和版本校验。发布后，ScreeningPromptBuilder 必须把手动项与其他已确认语义项一起注入 DeepSeek；未发布草稿不得进入候选人评分。

AI 不得生成年龄、性别、民族、婚姻、生育、照片、姓名、籍贯、学校声誉、985/211、与岗位无关的文化偏好等评分项。未配置到已确认 Rubric 的简历亮点直接忽略，不返回 `additional_signals`，不临时加分。

### 12.4 HR 审核与发布

AI 生成结果默认 `draft`。HR 可以：

- 修改名称、说明、评分锚点和同维度内部占比；
- 删除不相关建议项；
- 从模板补充一个合法评分项；
- 从零手动新增一个合法语义评分项；
- 放弃草稿并继续使用当前 Rubric；
- 确认发布为新的 active 版本。

HR 不能通过普通表单删除系统确定性规则、突破五维权重范围、把总权重改为非 100、加入公平性禁止项或直接编辑底层系统 Prompt。发布后若已有评分结果，旧结果保留并标记 outdated，不自动重跑、不改变 HR 决策。

### 12.5 候选人语义评分

DeepSeek 对每个已确认语义项返回 `0—10` 整数或 `unknown`，并必须返回 `confidence`、`evidence`、`reason`、`strengths` 和 `gaps`。不再使用 `full/strong/partial/weak/none` 六档作为最终语义合同。

```text
语义项贡献分 = AI 原始分 / 10 × 该项在总分中的实际权重
```

Python 负责确定性规则得分、同维度占比归一化、五维加权、证据覆盖率、推荐上限和最终四舍五入。`unknown` 表示证据不足，不等于 failed：该项不获得分数、不额外扣分，但降低证据覆盖率。非 unknown 分数没有可定位证据时拒绝计分。

学历第一版只比较大专、本科、硕士、博士层级，不判断 985/211、双一流或公司认可院校。院校名单和 RAG 方案后续单独设计。

## 13. unknown、证据覆盖率与推荐等级

### 13.1 unknown

`unknown` 表示没有足够证据，不等于 failed：

- 不获得该项分数。
- 不产生额外扣分。
- 降低证据覆盖率。
- 不能作为自动淘汰依据。
- 结果必须告诉 HR 缺少什么证据。

`failed` 表示存在明确不满足证据；两者即使得分相同，业务语义也必须分开。

### 13.2 证据覆盖率

```text
有明确证据的有效评分权重 / 全部有效评分权重
```

低于60%时，推荐等级最高为 `review_required`。资料严重不足则不生成分数，使用 blocked。

### 13.3 推荐等级

| 分数 | 推荐等级 |
| ---: | --- |
| 85—100 | `strong_recommend` |
| 70—84 | `recommend` |
| 50—69 | `review_required` |
| 0—49 | `low_match` |

存在任一硬性条件 failed、硬性条件 unknown 或证据覆盖率低于60%时，最高为 `review_required`。推荐等级只供 HR 参考，不触发招聘阶段变化。

## 14. 首次评分、重跑与幂等

### 14.1 首次评分

所有新 Application 在数据可靠保存后自动启动一次评分。保存 Candidate/Application 的成功不能依赖 DeepSeek 成功：模型失败时保留业务数据和稳定错误。

### 14.2 手动重跑

以下情况由 HR 手动触发：

- 上次 blocked/failed 后问题已修复
- 更换 Resume
- 候选人岗位相关资料变化
- JobRequirements 或 Rubric 变化
- 规则、Prompt 或模型版本发生重要变化
- HR 主动复核

### 14.3 输入指纹

指纹至少覆盖 Application、Resume、Candidate 脱敏输入、JobRequirements、Rubric 五维权重、已确认评分项与锚点、规则、Prompt 和模型配置版本。

相同输入已有成功结果时默认复用，不调用 DeepSeek。强制重跑必须二次确认并记录原因。同一 Application 同时只能有一个执行中的评分。

### 14.4 当前结果

- 新评分中：旧成功结果继续显示，并提示正在生成新版本。
- 新评分成功：切换当前结果，旧结果进入历史。
- 新评分失败：旧成功结果继续保留；若输入已变化，明确标记为 outdated。
- 任何新结果都不能自动改变 HR 决策。

## 15. HR 决策与原因

### 15.1 通过

- HR 直接新增自动记录 `hr_direct_entry`。
- AI 为 strong_recommend/recommend 时，通过可以使用默认 `meets_requirements`。
- AI 为 review_required/low_match、存在硬性 failed 或证据不足时仍通过，必须填写 `manual_override` 原因。

### 15.2 备选

备选必须选择岗位相关原因，可包括少量能力差距、等待比较、名额有限、信息待补充、薪资或到岗时间待确认等。备选不进入候选人页面，可后续改为通过或淘汰。

### 15.3 淘汰

淘汰必须二次确认并选择岗位相关原因。敏感和歧视性因素禁止进入标准选项和自由文本招聘依据。候选人主动放弃在阶段 9 建立独立 withdrawn 流程，不与普通淘汰长期混用。

### 15.4 决定反转

通过、备选、淘汰之间的任何反转都必须填写原因并追加 StageHistory。AI 只能展示证据，不能替 HR 选择原因。

## 16. 小批量评分

- 只能选择同一个开放岗位。
- 每批最多5个 Application。
- 预览岗位、Rubric、预计模型调用数、可复用结果、blocked 和正在执行项。
- 相同有效结果默认跳过并复用。
- 每项独立保存；一个失败不回滚其他成功项。
- failed 可以单独重试；blocked 必须先补资料。
- 批量评分不执行批量 HR 决策。
- 页面刷新后能够重新查询已保存的逐项状态。

阶段 7 不承诺服务器重启后继续未完成的同步批次；阶段 8 使用持久化 Redis 队列解决规模化、重试和恢复。

## 17. 作废、归档与数据保留

- Application 不提供普通硬删除。
- 误录、选错岗位或重复录入使用 voided，必须确认并填写原因。
- `ai_status=screening` 时暂不允许作废，等待本次同步评分进入终态后再操作，避免留下无法收敛的运行状态；步骤 7 保存评分结果时仍必须重新校验 Application 最新生命周期。
- rejected 表示真实招聘淘汰，不能与 voided 混用。
- 已开始评分后不能直接把 Application 从岗位 A 改到岗位 B；应作废并新建。
- ScreeningResult 不允许前端任意创建、修改或删除。
- 被 Application/ScreeningResult 使用的 Resume 不允许普通删除。
- 参与过招聘流程的 Candidate 只能归档；无任何关联的 Candidate 才允许安全删除。
- 最终隐私删除、匿名化和保留期限属于阶段 12。
- 自动化和验收隔离数据可以由严格限定的测试清理逻辑删除。

## 18. 旧数据迁移

### 18.1 只读预检

正式 migration 前输出并保存：

- Candidate、Job、Resume、ScreeningResult 数量
- Candidate 每种旧状态数量
- Candidate.applied_job_id 与 ScreeningResult.job_id 关系
- 缺少岗位、联系方式或 Resume 的数量
- 预计生成 Application 数量
- 预计进入候选人页、待审核、备选、淘汰和异常区数量
- 冲突和未识别状态明细
- 当前 Alembic revision 和关键关联哈希

用户确认预览后才能向正式开发数据库升级。

### 18.2 状态映射

| 旧 Candidate.status | 新 HR 决策 | 新招聘阶段 | 候选人页面 |
| --- | --- | --- | --- |
| `new` | pending | applied | 否 |
| `screening` | pending | hr_review | 否 |
| `passed/active` | passed | screening_passed | 是 |
| `interview_pending/interview_scheduled/interviewing/second_interview` | passed | 原阶段只读保留 | 是 |
| `offer/hired` | passed | 原阶段只读保留 | 是 |
| `backup` | backup | backup | 否 |
| `rejected` | rejected | rejected | 否 |
| `closed/未知` | pending 或迁移异常 | 人工核对 | 否 |

旧 AI 分数或 `screening_status` 不能推断新的 HR 决策。

### 18.3 Application 与旧结果

- 根据 Candidate.applied_job_id 和 ScreeningResult 的 candidate/job 关系生成 legacy Application。
- 同一 pair 只生成一条；冲突不静默选择，进入迁移异常。
- 旧 ScreeningResult 绑定对应 Application，作为 attempt 1 历史结果。
- 标记 `legacy_sqlite_import`、旧规则、证据不完整和历史输入。
- 不伪装成新版 Rubric，不自动调用 DeepSeek。
- legacy Application 允许 current_resume_id 为空；补齐/上传 Resume 后才允许新版评分。
- Candidate 旧字段先保留作兼容桥，不在同一 migration 中激进删除。

### 18.4 往返与保护

- 在专用临时 PostgreSQL 执行 upgrade -> downgrade -> upgrade。
- 核对数量、ID、时间、岗位关联、旧状态和原始结果 JSON。
- 正式数据库只执行确认后的向前升级。
- 旧 SQLite 和上传目录不修改、不清理。

## 19. API 契约方向

具体路径在实现前以 OpenAPI 冲突检查为准，推荐契约：

| 方法与路径 | 行为 |
| --- | --- |
| `POST /api/v2/applications/intake` | 统一处理 hr_direct/hr_screening 内部录入 |
| `GET /api/v2/applications` | 按岗位、阶段、AI 状态、HR 决策筛选 |
| `GET /api/v2/applications/{id}` | Application 详情 |
| `GET /api/v2/applications/{id}/history` | 阶段和决策历史 |
| `PUT /api/v2/applications/{id}/resume` | 切换当前 Resume 并使旧结果过期 |
| `POST /api/v2/applications/{id}/screenings` | 首次/重跑评分，支持 force 和 reason |
| `GET /api/v2/applications/{id}/screenings` | 全部评分历史 |
| `GET /api/v2/screening-results/{id}` | 单次评分详情和证据 |
| `POST /api/v2/jobs/{id}/screenings/batch` | 同岗位最多5个小批量评分 |
| `POST /api/v2/applications/{id}/pass` | HR 通过 |
| `POST /api/v2/applications/{id}/backup` | HR 备选 |
| `POST /api/v2/applications/{id}/reject` | HR 淘汰 |
| `POST /api/v2/applications/{id}/undo-rejection` | 撤销淘汰回到人工审核 |
| `POST /api/v2/applications/{id}/void` | 作废误录申请 |
| `GET/PUT /api/v2/jobs/{id}/screening-rubric` | 读取/创建新 Rubric 版本 |
| `POST /api/v2/jobs/{id}/screening-rubric/template-preview` | 预览内置模板，不直接生效 |
| `POST /api/v2/jobs/{id}/screening-rubric/generate` | 根据岗位默认生成 5—8 个待确认语义评分项，允许 4—10 个 |
| `POST /api/v2/jobs/{id}/screening-rubric/drafts/{draft_id}/publish` | HR 确认并发布新版本 |
| `DELETE /api/v2/jobs/{id}/screening-rubric/drafts/{draft_id}` | 放弃未发布草稿，不影响当前版本 |

正式 ScreeningResult 创建、更新和删除不能继续暴露为普通客户端 CRUD。

### 19.1 关键错误语义

| HTTP | code | 场景 |
| --- | --- | --- |
| 404 | `APPLICATION_NOT_FOUND` | Application 不存在 |
| 404 | `RESUME_NOT_FOUND` | Resume 不存在 |
| 409 | `ACTIVE_APPLICATION_EXISTS` | 同候选人同岗位已有有效申请 |
| 409 | `CONTACT_IDENTITY_CONFLICT` | 手机与邮箱匹配冲突 |
| 409 | `JOB_NOT_OPEN_FOR_SCREENING` | 岗位不是 open |
| 409 | `SCREENING_ALREADY_RUNNING` | 同一申请已有执行中任务 |
| 409 | `SCREENING_RESULT_CURRENT` | 相同输入已有有效结果且未 force |
| 409 | `INVALID_APPLICATION_TRANSITION` | 非法 HR 决策或阶段迁移 |
| 422 | `APPLICATION_CONTACT_REQUIRED` | 缺少有效手机号或邮箱 |
| 422 | `APPLICATION_RESUME_REQUIRED` | 缺少当前 Resume |
| 422 | `SCREENING_INPUT_BLOCKED` | 原文与结构化资料都不足 |
| 422 | `RUBRIC_WEIGHT_INVALID` | 权重越界或总和不为100 |
| 409 | `RUBRIC_DRAFT_STALE` | 生成后岗位评分输入已变化，草稿不能直接发布 |
| 422 | `RUBRIC_CRITERIA_INVALID` | 评分项数量、字段、维度、锚点或公平性规则不合法 |
| 503 | `RUBRIC_GENERATION_MODEL_UNAVAILABLE` | 生成建议失败，岗位和当前 Rubric 不受影响 |
| 503 | `SCREENING_MODEL_UNAVAILABLE` | 模型服务不可用，业务数据已保留 |
| 500 | `APPLICATION_OPERATION_FAILED` | 已 rollback 的未预期错误 |

错误响应不得泄露简历原文、Prompt、模型密钥、数据库地址、SQL、路径或调用栈。

## 20. Service、事务与并发边界

建议职责拆分：

- `ApplicationIntakeService`：联系方式校验、Candidate 去重、差异确认、Resume 绑定、Application 原子创建。
- `ApplicationService`：查询、状态迁移、作废、当前 Resume 和生命周期。
- `ScreeningInputService`：生成脱敏输入、快照和指纹。
- `ScreeningRuleService`：把结构化 JobRequirements 编译为字段比较规则，执行年限、学历层级、技能规范化、明确关键词和硬性检查；不解析 HR 自由文本。
- `RubricTemplateService`：加载版本化的 standard/technical/non_technical 模板并生成预览。
- `RubricGenerationAdapter`：单次 DeepSeek 默认生成 5—8 个岗位专用语义评分项草稿，严格 Schema 允许 4—10 个。
- `ScreeningPromptBuilder`：把固定系统约束、当前岗位、已确认 Rubric 和脱敏候选人材料组装为评分 Prompt。
- `ScreeningModelAdapter`：单次 DeepSeek 严格结构化调用。
- `ScreeningScoreService`：档位换算、证据覆盖率、总分和推荐等级。
- `ScreeningService`：执行编排、结果版本、幂等、失败隔离和当前结果切换。
- `ScreeningRubricService`：默认 Rubric、受限编辑、版本和过期判断。
- `ApplicationDecisionService`：HR 决策、原因、StageHistory 和 ActivityLog。

关键事务：

- Candidate/Resume/Application/初始 StageHistory 必须原子保存。
- 模型调用前先提交业务事实和评分执行记录，不在外部网络等待期间持有数据库事务或行锁。
- 结果落库时重新锁定 Application，校验执行仍是当前任务，再提交结果和状态。
- HR 决策、作废、切换简历和 Rubric 修改使用行锁与最新状态校验。
- 批量评分按 Application 独立事务执行，禁止整批大事务。
- 所有失败写操作 rollback；外部模型错误不能回滚已可靠保存的申请事实。

## 21. 前端交互设计

### 21.1 AI 初筛中心

- 主入口“录入新申请”。
- 按岗位、AI 状态、HR 决策和推荐等级筛选。
- 展示待评分、评分中、待 HR 决策、blocked、failed、备选和淘汰数量。
- 单个评分、最多5人批量评分、失败项重试和强制重跑确认。
- 结果详情展示 Rubric、硬性条件、证据覆盖率、优势、风险、理由和待确认问题。
- 历史抽屉展示每次评分版本、输入版本和分数变化。
- 通过、备选、淘汰动作遵循原因和确认规则。
- 关闭岗位历史可查看，但不提供新评分动作。

### 21.2 候选人页面

- 每行对应一个 `hr_decision=passed` 的 Application。
- 显示候选人、岗位、当前 AI 分数、推荐等级、招聘阶段和更新时间。
- HR 直接新增确认后立即出现，AI 评分中/failed/blocked 使用明确状态，不隐藏记录。
- 同一 Candidate 多岗位通过时允许多行。
- AI 新结果不能自动移出候选人。

### 21.3 新增与详情

- 候选人页面保留“新增候选人”，明确为 HR 人工直通。
- 初筛中心提供“录入新申请”，明确为先 AI 后 HR 决策。
- 手机、邮箱、开放岗位和简历前后端双重必填。
- Candidate 去重和资料差异必须由 HR 确认。
- Candidate 详情聚合全部 Application，并允许发起新岗位申请。

### 21.4 岗位 Rubric

- 岗位表单增加 AI 初筛 Rubric 区；新岗位先显示自动生成的 standard 默认版本。
- 岗位要求区维护 Python 确定性条件，Rubric 区只维护语义评分项；前端不提供“输入一段自然语言让 Python 执行”的入口。
- 支持选择 standard/technical/non_technical 模板并预览，也支持点击“AI 根据岗位生成评分项”。
- Rubric 草稿支持 HR 手动新增语义项，必须填写所属维度、说明和高/中/低分锚点；发布后才参与 DeepSeek 评分。
- AI 生成期间显示 loading；失败时保留当前版本并展示可重试错误，不阻塞岗位保存。
- 草稿页面展示默认 5—8 个、合法范围 4—10 个语义项及其所属维度、0—10 分锚点和建议占比，HR 可审核后发布或放弃。
- 默认五维 40/25/20/10/5 继续支持受限调整、总和提示和恢复默认。
- 修改已有结果岗位的 Rubric 必须确认会生成新版本并使旧结果过期。

### 21.5 当前身份提示

阶段 7 尚无登录，页面明确显示“本地 HR（未认证）”。二次确认只防误操作，不声称已经完成正式权限控制。

## 22. 开发顺序与小步骤

每个小步骤完成后必须单独解释、验证并等待用户理解，不提前跨步。

### 小步骤 1：Application、StageHistory 与 Rubric Schema

- 固定枚举、严格请求/响应 Schema、联系方式和权重校验。
- 只做纯 Schema 测试，不改数据库。
- 完成状态：✅ 2026-08-17 已新增 Application、StageHistory、HR 决策/作废/强制重跑请求和版本化 Rubric Schema；27 项定向测试及 71 项 Schema 回归测试通过，未修改数据库。

### 小步骤 2：Model 与 Alembic migration

- 新增 Application、StageHistory、JobScreeningRubric。
- 扩展 ScreeningResult 为多次版本。
- 生成 migration、只读预检和专用数据库往返验证。
- 不改前端，不调用 DeepSeek。
- 完成状态：✅ 2026-08-17 已新增三张 Model、扩展 ScreeningResult 多版本结构并生成 revision `e7b1c9d4a206`；独立 PostgreSQL 的 `upgrade -> downgrade -> upgrade`、约束验证、`alembic check` 和后端全量 455 项测试通过，正式开发库仍停留在阶段 6 revision。

### 小步骤 3：Application Service 与内部录入 API

- Candidate 去重、冲突、Application 唯一有效记录、Resume 绑定和原子创建。
- 接入 hr_direct/hr_screening 两种入口。
- 验证 rollback、并发和旧入口兼容。
- 完成状态：✅ 2026-08-17 已新增 `ApplicationIntakeService` 与 `POST /api/v2/applications/intake`；相同联系方式安全复用 Candidate，同 Candidate/Job 重复提交返回既有 active Application，冲突与失败使用稳定错误并完整回滚。隔离 PostgreSQL 真实并发、约束失败回滚、`alembic check`、34 项定向测试和后端全量 471 项测试通过；正式开发库未升级，未调用 DeepSeek、未修改前端。

### 小步骤 4：Application 状态、HR 决策与历史

- 实现 pass/backup/reject/undo/void。
- 固定原因、二次确认后端契约、StageHistory 和 ActivityLog。
- 尚不实现 AI 评分。
- 完成状态：✅ 2026-08-17 已新增行锁保护的 `ApplicationDecisionService`，实现五种 HR 操作、固定状态迁移、非法迁移拒绝、撤销淘汰时 active Application 冲突保护，以及 Application/StageHistory/ActivityLog 同事务提交；新增五个决策 API 和历史查询 API。隔离 PostgreSQL 并发与审计失败回滚、30 项联合定向测试、后端全量 487 项测试和 `alembic check` 通过；正式开发库未升级，未调用 DeepSeek、未修改前端。

### 小步骤 5：Rubric 与确定性评分规则

- 默认权重、受限岗位配置、内部子项和版本。
- 年限、学历、技能规范化、unknown、覆盖率和推荐等级纯规则测试。
- 不调用 DeepSeek。
- 完成状态：✅ 2026-08-17 已新增版本化 Rubric Service/API 和纯 `ScreeningRuleService`；新岗位同事务生成默认 Rubric，调整/恢复默认保留旧版本并记录 ActivityLog。技能别名、年限、学历层级、必备经历、六档换算、不适用重分配、证据覆盖率、blocked、推荐阈值和硬性条件封顶均已固定；69 项联合定向测试、后端全量 512 项测试、隔离 PostgreSQL 并发版本/失败回滚/删除生命周期验证及 `alembic check` 通过。正式开发库未升级，未调用 DeepSeek、未保存 ScreeningResult、未修改前端。

### 小步骤 5A：Reqcore 式 Rubric 方案调整（当前门禁）

- 用户已确认 AI 默认生成 5—8 个语义项、Schema 允许 4—10 个、Python 确定性规则不计入该数量，以及“结构化 JobRequirements 编译为 Python 规则、HR 手动语义项发布后注入 DeepSeek”的双入口；进入业务代码前仍需确认本文第 12 节其余权重分配、岗位变更、空维度、失败语义和验收场景。
- 确认后调整 Rubric Schema/Model/migration：保留五维权重与版本能力，增加 source、template、draft/active 状态、岗位专用评分项、岗位指纹和生成/确认审计。
- 新增三套版本化模板、RubricGenerationAdapter、生成 Prompt/输出 Schema 和 ScreeningPromptBuilder。
- 将语义合同从六档改为 `0—10/unknown + confidence/evidence/reason/strengths/gaps`；保留确定性规则、证据覆盖率、推荐上限和 HR 决策边界。
- 先使用 Fake Adapter 验证生成成功、非法输出、偏见字段、超时、stale 草稿、放弃草稿和发布新版本，再使用少量脱敏岗位样本验证真实 DeepSeek。
- 本步骤完成前不进入候选人语义评分 Adapter；已完成的小步骤 1—5 不伪装成新方案已实现。

### 小步骤 6：DeepSeek 语义评价 Adapter

- 读取已确认的岗位专用评分项，通过 ScreeningPromptBuilder 生成岗位专用 Prompt；实现脱敏输入、严格 `0—10/unknown` 输出 Schema 和 Provider Adapter。
- 单次调用、稳定错误、耗时/token/费用记录。
- 使用 Mock/Fake 完成异常和格式测试，再使用少量脱敏样本验证。

### 小步骤 7：ScreeningService、版本和幂等

- 组合规则与语义评价，计算总分。
- 输入指纹、首次自动、重跑、当前结果、outdated 和失败保留。
- 单 Application 真实 PostgreSQL + DeepSeek 链路。

### 小步骤 8：小批量评分 API

- 同岗位最多5项、逐项事务、部分失败、复用和仅重试失败项。
- 不引入 Redis，不实现批量 HR 决策。

### 小步骤 9：前端 Application 与 AI 初筛中心

- 录入、列表、状态、评分详情、证据、历史、批量和 HR 决策。
- 覆盖 loading、空状态、失败、blocked、outdated 和关闭岗位历史。

### 小步骤 10：候选人页面、详情和岗位 Rubric

- 候选人页面按已通过 Application 展示。
- 升级 HR 直接新增并自动评分。
- Candidate 详情聚合 Application。
- 接入岗位 Rubric 编辑和版本提示。

### 小步骤 11：旧数据正式迁移

- 先生成只读预览并等待用户确认。
- 临时数据库往返通过后，正式数据库只向前升级。
- 核对 30/8/0/29 基线或执行时最新实际基线，不硬编码假设。

### 小步骤 12：脱敏评估、全量回归与人工验收

- 20份样本评估。
- 全量后端、前端、migration 和生产构建。
- 真实 PostgreSQL、真实 DeepSeek 和浏览器人工场景。
- 验收通过后更新项目状态和交接文档。

## 23. 自动化测试标准

### 23.1 Schema

- 所有枚举、未知字段、空请求、长度和类型。
- 手机/邮箱必填、标准化和非法格式。
- Rubric 总和、范围、默认值和恢复默认。
- HR 决策原因和强制重跑原因。

### 23.2 Application Service

- 新建/复用 Candidate。
- 所有联系方式匹配与冲突组合。
- 同岗位有效 Application 并发拦截。
- Resume 所属关系。
- hr_direct/hr_screening 初始状态。
- Candidate/Resume/Application/History 原子 rollback。
- void、归档和删除保护。

### 23.3 状态与决策

- 所有合法/非法 AI 状态和招聘阶段迁移。
- 通过、备选、淘汰、撤销和反转原因。
- AI 结果不能改变 HR 决策。
- Candidate 页面展示条件。

### 23.4 规则与 Rubric

- 年限、学历、技能别名和必备经历。
- 三套模板预览、AI 默认生成 5—8 项且只接受 4—10 项、HR 编辑/发布/放弃和版本历史。
- JobRequirements 能稳定编译为 Python 规则；Rubric 自由文本不能伪装成 Python 规则，HR 手动语义项发布后必须出现在模型输入和逐项输出中。
- AI 生成非法 JSON、重复 key、越界数量、非法维度、偏见项和岗位指纹 stale。
- `0—10/unknown` 换算、同维度占比归一化和不适用项重新分配。
- 证据覆盖率、推荐阈值和硬性条件等级封顶。
- HR 权重变化和 Rubric 版本。

### 23.5 模型 Adapter 与 ScreeningService

- 禁止字段不进入模型输入。
- 合法/非法 JSON、超时、Provider 错误和严格 Schema。
- 一次正常执行最多一次调用。
- 相同指纹复用、force 重跑和并发幂等。
- 新成功切换当前结果；新失败保留旧成功。
- Job/Resume/Rubric 变化使旧结果过期。

### 23.6 批量

- 不同岗位拒绝、超过5项拒绝。
- 成功、failed、blocked、复用混合结果。
- 单项失败不回滚其他项。
- 仅重试失败项。

### 23.7 API 与前端

- 路由唯一、响应 Schema、稳定业务 code 和安全错误。
- 页面数据来源真实，不生成演示分数。
- HR 直接新增、AI 录入、候选人页过滤、详情聚合。
- 结果详情、历史、失败、blocked、outdated 和确认文案。
- TypeScript 严格检查、生产构建和窄屏布局。

### 23.8 migration

- 全部旧状态映射和未知状态隔离。
- Candidate/Job/ScreeningResult 数量、ID、时间和关系不丢失。
- 同 pair 去重、冲突、缺 Resume 和 legacy 结果。
- upgrade -> downgrade -> upgrade。
- `alembic check` 无待生成操作。

## 24. 脱敏样本评估

准备20份、覆盖测试开发、AI 应用和数据分析/其他岗位的脱敏样本：

- 高匹配4份
- 中等匹配4份
- 低匹配4份
- 明确硬性失败3份
- 资料缺失应 unknown 3份
- HR 资料与简历冲突2份

HR 在运行 AI 前记录硬性条件、主要技能、优势、风险、大致推荐等级和预期证据，不能用 AI 自己的答案作为基准。

验收指标：

| 指标 | 标准 |
| --- | --- |
| 禁止敏感字段进入模型 | 100% |
| 确定性硬规则测试 | 100% |
| 单次模型结构化成功率 | >=95% |
| 证据可核对率 | >=90% |
| 推荐方向与 HR 基准一致率 | >=80% |
| 严重虚构证据 | 0 |
| 5份重复样本推荐等级一致 | 至少4份 |
| 重复评分分数变化 | 建议不超过5分 |
| 单份中位耗时 | 目标 <=20秒 |
| 95% 单份耗时 | 目标 <=40秒 |

耗时目标受外部模型波动影响，必须记录但不在质量合格时机械冒充本地缺陷。真实脱敏文件不提交 Git；仓库测试只保存虚拟构造样本和不含个人信息的汇总指标。

## 25. 人工验收场景

1. 候选人页直接新增：手机号、邮箱、开放岗位、简历缺一不可；确认后立即进入候选人页并自动评分。
2. HR 直接新增的评分为 low_match/failed/blocked 时，人员仍保留，HR 决策不被撤销。
3. 初筛中心录入：自动评分后仍不进入候选人页；HR 通过后才进入。
4. HR 备选不进入候选人页；改为通过后进入。
5. HR 淘汰需要确认和原因，进入历史但数据不删除；撤销后回到审核。
6. 手机/邮箱匹配同一 Candidate 时复用；任一冲突进入人工核对。
7. 同 Candidate 同 Job 有有效 Application 时拒绝重复创建。
8. 同 Candidate 通过两个岗位时，候选人页出现两行，详情聚合两次申请。
9. 更换 Resume 后旧结果过期，重跑成功后保留两版结果。
10. 修改 JobRequirements/Rubric 后旧结果过期，不自动重跑或改变 HR 决策。
11. 新建岗位自动获得 standard Rubric，不调用模型；HR 可切换技术/非技术模板并先预览后发布。
12. AI 根据完整岗位默认生成 5—8 个语义评分项，简单/复杂岗位允许 4—10 个；Python 确定性规则不计入该数量且不得重复计分。生成结果不自动生效；HR 发布后才产生新 current 版本。
13. AI 生成失败、非法输出或包含公平性禁止项时，岗位与当前 Rubric 不变；岗位变化后旧草稿不能直接发布。
14. AI 只评价已确认 Rubric；未配置亮点不返回、不计分。
15. HR 在 JobRequirements 修改明确年限、学历、技能或关键词时生成 Python 规则；在 Rubric 手动新增语义项并发布后，DeepSeek 必须按该项返回分数和证据，旧评分不自动重跑。
16. 关闭岗位退出新申请/新评分选择，历史仍可查看；已启动评分按快照完成。
17. 相同输入普通重试复用；force 重跑记录原因并新增结果。
18. 5人批量含成功、blocked、failed 和复用，结果逐项保存且互不回滚。
19. unknown 与 failed 分开展示，资料严重不足不生成虚假0分。
20. 每个评分项可查看简历和岗位证据，敏感信息不进入模型调用。
21. Application 作废与淘汰分开展示；已关联记录不能硬删除。
22. 迁移预览获得确认后再执行；迁移前后旧记录、关系和 legacy 原始结果不丢失。
23. 1440 像素桌面和严格 390 像素窄屏完成新增、筛选、详情、历史、确认和错误状态检查，无整页横向溢出。

## 26. 阶段完成标准

只有以下全部满足，阶段 7 才能标记完成：

- Candidate 与 Application 已正式分离，旧单岗位字段不再驱动新流程。
- 两种 HR 内部入口、联系方式强校验和 Candidate 去重可用。
- 每个新 Application 可靠保存并尝试首次评分。
- 新岗位具备可用默认模板；模板或 AI 生成的岗位专用评分项必须经 HR 确认并版本化发布。
- 规则 + DeepSeek + Service 评分符合已确认的岗位专用 Rubric 和公平性边界。
- HR 能查看逐项证据并作出通过、备选、淘汰决定。
- 候选人页面只展示 HR 已通过 Application。
- 重跑、当前结果、过期、失败、blocked 和历史版本语义稳定。
- 5人小批量部分失败隔离可用。
- 旧数据迁移预览、往返和正式向前升级通过，无数据丢失。
- 20份脱敏样本达到第 24 节质量标准。
- 自动化、真实 PostgreSQL、真实 DeepSeek、生产构建和浏览器人工验收全部通过。
- 阶段 6 真实浏览器人工验收已经完成并获用户确认。
- `PROJECT_STATE.md`、实施计划和必要交接文档按实际结果更新。

## 27. 外部参考的取舍

阶段 7 借鉴：

- Reqcore 的 Candidate/Application 分离、以 Application 为流程主记录和历史保留。
- Reqcore 的预设评分模板、根据岗位生成 4—6 个可衡量评分项、逐项 0—10 分与程序加权；生成建议必须增加本项目的 HR 确认、版本和确定性规则边界。
- HackerRank Hiring Agent 的岗位级 Rubric、逐项证据、快照、版本、缓存、Provider 抽象和公平性约束。

明确不照搬：

- 不复制 AGPL 代码，不切换 Nuxt/Vue。
- 不增加 PDF 转 Markdown。
- 不按每个简历章节分别调用模型。
- 不默认用 GitHub 活跃度评分。
- 不建设 MCP Server。
- 不使用向量相似度决定初筛结论。

## 28. 完成后的简历表述与面试准备

完成后可以如实表述：

> 设计并实现以 Application 为中心的招聘初筛底座，将 Candidate 与岗位申请解耦，支持预设模板及 DeepSeek 根据岗位生成待确认评分项，使用确定性规则与 0—10 结构化语义评价构建版本化 Rubric 评分，保存逐项证据、输入快照和重跑历史，并通过 PostgreSQL 状态机、幂等指纹和人工确认保证 AI 不越过 HR 决策边界。

不能表述为：

- AI 可以自动淘汰、录取或推进招聘流程。
- 已实现公开投递、Redis 大规模队列或 LangGraph Agent。
- 已实现正式登录、RBAC 或完整隐私删除。
- AI 分数代表候选人真实能力的绝对评价。

面试官可能追问：

1. Candidate 和 Application 为什么必须分开？
2. 为什么候选人页面按 Application 展示？
3. 为什么 HR 直接新增后仍要 AI 评分？
4. 如何防止 AI 结果自动改变 HR 决策？
5. 规则和大模型分别负责什么？
6. 为什么 LLM 不直接输出最终总分？
7. unknown 和 failed 有什么区别？
8. 为什么要保存 Job/Resume/Rubric 快照？
9. 重跑失败时如何保留旧成功结果？
10. 输入指纹如何防止重复调用和重复扣费？
11. 为什么阶段 7 不使用 LangGraph 和 Redis？
12. 如何证明敏感信息没有进入模型？
13. 旧数据 migration 如何避免根据 AI 分数伪造 HR 决策？
14. 自动化测试、脱敏样本评估和真实浏览器验收分别能证明什么？
