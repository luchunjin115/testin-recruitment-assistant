# 阶段 7：岗位事实与评价维度双层计划 4.0 重设计

> 日期：2026-08-24
>
> 状态：业务规则与 7R4-A—7R4-J 实施顺序已获用户最终确认；7R4-A—7R4-G、7R4-H0 已完成，7R4-H1 六份定向真实验证已执行并以 `4/6` 失败。用户已认可整改方向，第 29 节已写入 7R4-HR0/HR1 固定顺序并等待明确确认；确认前不得修改 Prompt/Service、补跑或进入正式 20 份及 7R4-I—J
>
> 直接上游：`../stage6/2026-08-21-stage6-five-section-jd-remediation-design.md`
>
> 3.0 实施与失败记录：`2026-08-22-stage7-five-section-job-evaluation-plan-redesign.md`
>
> 阶段 7 保留能力：`2026-08-20-stage7-jd-driven-ai-screening-redesign.md`

## 1. 为什么需要 4.0

JobEvaluationPlan 3.0 让一次 DeepSeek 调用同时承担：逐段审阅、判断是否可评价、拆分最小语义、生成标题、分类、发现语义重复和多来源合并。Service 随后只能检查结构、原文定位和少量明显冲突，无法可靠判断模型是否漏掉了某项 JD 语义。

7R-F 首轮 6 份定向真实验证因此只有 3/6 满足完整合同：

- 主要语义召回 73/80（91.25%），低于 95%；
- 明确必测项召回 20/23（约 86.96%），低于 100%；
- J5-07 的模型标题增加了原文没有的要求；
- J5-14 漏项且没有完成多来源合并；
- J5-20 在数量判断前被另一项内容校验拒绝，边界结果不符合预期；
- `targeted_gate_passed=false`，因此正式 20 份验证没有执行。

根因不是“Prompt 再写长一点”就能稳定解决，而是 3.0 把岗位原文事实、展示标题、评价事项和语义分组压在同一层，并让同一次模型调用既生成答案又承担完整性责任。

4.0 将岗位解析拆成两层：

```text
RequirementFact：JD 原文中可以独立评价的事实
EvaluationCriterion：组织相关事实的展示章节
```

事实层只保存原文和来源，不生成事实标题；评价维度只负责组织，不替代事实，也不成为额外评分标准。

## 2. 权威边界

本文替代 3.0 文档中以下当前运行合同：

1. JobEvaluationPlan 的当前 Schema、状态和持久化形状；
2. 逐段单次生成 Prompt 与 Adapter 调用方式；
3. `EvaluationItem.title/category/priority/sources` 单层事项合同；
4. 0—30 项数量边界和 31 项以上直接失败语义；
5. 3.0 ready 直接进入 Screening 的门禁；
6. 当前计划页面的三组事项展示；
7. 7R-F 之后的实施和质量验证顺序。

以下既有能力继续有效，除本文明确收紧外不重新设计：

- 五段式 Job 字段、普通文本和开放校验；
- Candidate、Application、Resume 与 `Application.applied_at`；
- Resume 脱敏、经历时间事实和证据定位；
- ScreeningRun、当前成功报告替换和失败保护；
- AI 不修改 HR 决策、招聘阶段或生命周期；
- 旧计划、旧报告和旧运行记录只读保留；
- 前端不使用 HTML 解释模型或 JD 文本；
- 固定 Service 工作流，不引入 LangGraph、Agent 或运行时 Skill。

3.0 文档继续保存已经完成的 7R-A—7R-F 实施事实和失败证据，不得改写成 4.0 已经实现。

## 3. 已确认的核心业务决定

1. `RequirementFact` 不生成标题；事实展示和业务依据来自一个或多个原文 `source_quote`。
2. `EvaluationCriterion` 只是组织章节；每条事实以后仍被独立评价，不按维度合并成一个分数。
3. 评价维度不设置 5—12 个硬目标。一个维度可以只含一条事实，维度数量也可以等于事实数量。
4. 每条事实必须且只能进入一个评价维度；不得遗漏或重复归组。
5. 计划生成完成后进入 `pending_confirmation`，只有 HR 确认后才成为 `ready` 并允许初筛。
6. HR 不直接编辑事实或评价维度；发现错误时修改 JD 并重新生成。
7. 正常流程使用同一个 DeepSeek 模型完成三次独立调用：事实提取、完整性复核、评价维度归组；三次使用不同 Prompt 和严格输出 Schema。
8. 内容问题最多允许一轮局部修复，只发送有问题的 source units；仍失败则整份计划 failed，不保存可用于初筛的部分计划。
9. 技术失败与内容修复分开：每次模型调用遇到网络、超时、限流或 5xx 时最多额外重试一次，不占用内容修复次数。
10. 首版事实分类只允许 `skill/experience/responsibility/education/other`；证书、语言等暂归 `other`。
11. 31 条及以上事实不再直接失败，改为 `overly_broad_jd` warning；业务层不静默截断。技术安全上限先通过冻结样本离线分析，再单独确认。
12. JD 内部冲突时保留所有原文来源，标记 `conflicting_requirements`；同一语义同时来自 required/preferred/general 时，程序按 required > preferred > general 计算最终 priority。
13. 模糊要求保留原文，标记 `ambiguous_requirement`；模型不得自行补充年限、数量、等级或技能，后续不能把它当作明确硬淘汰条件。
14. 福利、公司介绍、招聘流程等不生成事实，标记 `non_evaluation_content`；混合句只截取连续的候选人要求原文。
15. 计划未 ready 时岗位仍可开放并接收申请，申请保存为等待计划，不启动 AI 初筛。
16. JD 变化后旧计划 outdated；旧筛选结果保留计划版本，旧输入的迟到响应不得成为当前有效结果。
17. 普通生产数据库只保存通过校验的结构化计划和必要调用审计，不长期保存或向 HR 展示模型完整原始响应；质量验证文件可以受控保存原始响应。
18. 新计划格式为 4.0；1.0/2.0/3.0 与旧筛选结果只读保留。仍在招聘的旧职位必须重新生成并确认 4.0，才能继续新的 AI 初筛。

## 4. 目标、包含与不包含

### 4.1 目标

1. 将“忠实提取 JD 原文事实”和“组织评价展示”分离。
2. 使用独立复核调用发现漏项、错项和缺少的多来源合并。
3. 让 Service 对 ID、来源、字段优先级、状态、事务和覆盖关系作确定性校验。
4. 让 HR 在任何候选人被 AI 初筛前确认评价计划。
5. 复用现有 6 个定向样本和 20 份冻结 JD，证明问题确实被解决。

### 4.2 本次包含

- 4.0 input snapshot、RequirementFact、EvaluationCriterion、review、warning 和调用审计；
- 三类 Prompt、可选局部修复 Prompt、严格 Schema 和 Adapter 接口；
- Service 固定工作流、内容校验、状态、指纹、幂等和迟到响应保护；
- PostgreSQL 向前兼容 migration；
- HR 确认 API、计划页面和 Screening 4.0 门禁；
- 以事实为基本单元的下游初筛接线；
- 自动化、真实 PostgreSQL/API、真实 DeepSeek、浏览器和质量验收。

### 4.3 本次不包含

- AI 生成或润色 JD；
- HR 直接编辑计划、权重、阈值或 Rubric；
- LangChain、LangGraph、Agent、RAG 或 Codex Skill 作为生产运行依赖；
- 自动通过、淘汰、发 Offer 或录用；
- 自动重评全部历史候选人；
- 阶段 8 公开投递新功能、登录/RBAC、面试、Offer 或录取；
- 在离线分析前拍脑袋固定新的技术数量上限。

## 5. 固定输入与 source unit

五段式字段边界保持不变：

| Job 字段 | 进入 Prompt | 产生事实 | 程序 priority |
| --- | --- | --- | --- |
| `title` | 是，仅上下文 | 否 | 无 |
| `department` | 是，仅上下文 | 否 | 无 |
| `job_background` | 是，仅上下文 | 否 | 无 |
| `job_responsibilities` | 是 | 是 | `general` |
| `candidate_requirements` | 是 | 是 | `required` |
| `preferred_qualifications` | 是 | 是 | `preferred` |
| `public_notes` | 完全排除 | 否 | 无 |
| `location/employment_type/headcount` | 否 | 否 | 无 |

程序继续按排版稳定切分 source unit：自然段、列表项和必要的完整句形成连续片段；不按逗号、顿号、“和”或 `and` 机械生成事实。稳定 ID 继续使用：

```text
job_responsibilities:0001
candidate_requirements:0001
preferred_qualifications:0001
```

程序切片只决定模型必须审阅哪些原文，不预填技能、学历、年限或事实分类。一段可以产生多个事实，一个事实也可以保存多个字段或片段中的同义来源。

## 6. JobEvaluationPlan 4.0 数据合同

### 6.1 RequirementFact

概念结构：

```json
{
  "fact_id": "fact:0001",
  "category": "experience",
  "priority": "required",
  "sources": [
    {
      "source_field": "candidate_requirements",
      "source_unit_id": "candidate_requirements:0001",
      "source_quote": "具备 Python 后端开发经验"
    },
    {
      "source_field": "preferred_qualifications",
      "source_unit_id": "preferred_qualifications:0002",
      "source_quote": "有 Python 服务端项目经验者优先"
    }
  ]
}
```

规则：

- `fact_id` 由 Service 在最终不可变计划中稳定生成，模型不决定数据库主键。
- 不存在 `title`、`statement` 或模型改写后的事实文本。
- `category` 只能取五个受控值，不参与权重或淘汰。
- `priority` 由所有来源字段按 required > preferred > general 计算，模型不得输出最终值。
- `sources` 至少一项，每个 `source_quote` 必须能在对应 source unit 中连续、逐字定位。
- 多来源事实的主展示取最高 priority 下最早出现的原文，其余来源可展开；所有来源共同构成事实依据。
- 两段只是主题相关但可以分别评分时，必须保留为两条事实，不得为了减少数量强行合并。

### 6.2 EvaluationCriterion

概念结构：

```json
{
  "criterion_id": "criterion:0001",
  "name": "Python 后端工程经验",
  "fact_ids": ["fact:0001", "fact:0004"]
}
```

规则：

- `name` 是 HR 页面和报告中的展示章节名称，可以概括成员事实，但不能替代原文事实。
- 初筛 Prompt、逐项评分、证据校验和报告关联均以 `fact_id` 为准，不以 criterion name 创造新要求。
- 每条 RequirementFact 必须且只能出现在一个 criterion 的 `fact_ids` 中。
- `fact_ids` 内不得重复、伪造或引用不存在的事实。
- 不设置业务数量目标或强制合并；criterion 数量最少 1 个，最多等于 fact 数量。
- Criterion 不配置权重、分数、淘汰线或 required/preferred 属性。

### 6.3 Source review

每个 source unit 必须恰好有一个最终处理记录：

```json
{
  "source_unit_id": "job_responsibilities:0002",
  "disposition": "evaluation",
  "fact_ids": ["fact:0003", "fact:0004"],
  "non_evaluation_reason": null
}
```

`evaluation` 必须关联至少一个 fact；`non_evaluation` 必须使用受控原因且不关联 fact。Service 根据输入和最终 facts 重算 review summary，不信任模型自报的 `all_reviewed`。

### 6.4 Coverage review

第二次 DeepSeek 调用只返回审计结论，不直接改写事实：

```json
{
  "status": "needs_repair",
  "findings": [
    {
      "code": "missing_fact",
      "source_unit_ids": ["candidate_requirements:0003"],
      "fact_ids": [],
      "message": "该片段中的证书要求尚未形成独立事实"
    }
  ]
}
```

首版 finding code 只允许：

- `missing_fact`：原文中的可评价语义被遗漏；
- `unsupported_fact`：事实来源不能支撑该事实关系；
- `wrong_disposition`：明显要求被当作非评价内容，或反向误判；
- `invalid_atomicity`：应分别评价的语义被错误捆绑，或同一语义被无意义拆散；
- `missing_source_merge`：同一事实的其他原文来源没有合并；
- `category_mismatch`：五分类与事实含义明显不一致。

Reviewer 不生成最终 fact、criterion、priority 或计划状态。Service 校验 finding 引用的 ID、范围和文本长度。

### 6.5 Warnings

4.0 首版允许：

| code | 含义 | 是否阻止 HR 确认 |
| --- | --- | --- |
| `limited_basis` | 只有 1—4 条事实，评价依据较少 | 否 |
| `overly_broad_jd` | 最终事实达到 31 条及以上 | 否 |
| `conflicting_requirements` | 同一语义存在优先级或内容冲突 | 否 |
| `ambiguous_requirement` | 原文无法形成明确、客观的判断标准 | 否 |
| `non_evaluation_content` | 评价字段中混入福利、宣传或流程 | 否 |

Warning 必须引用相关 source unit，必要时引用 fact。Warning 只提醒 HR，不修改原文事实，也不允许模型借 warning 增加具体要求。

### 6.6 状态

```text
generating -> pending_confirmation -> ready
           -> failed

generating/pending_confirmation/ready -> outdated
```

- 三次正常调用和全部 Service 校验通过后进入 `pending_confirmation`，即使没有 warning 也必须由 HR 确认。
- 只有当前、4.0、指纹一致的 `ready` 可以进入 Screening。
- `failed/outdated` 和部分结果不能进入 Screening。
- JD 输入在生成或待确认期间变化时，旧计划 outdated；迟到响应只记审计，不得恢复为当前计划。
- HR 确认是状态变更，不重新调用 DeepSeek。

## 7. 固定 Service 工作流

```text
HR 保存/开放五段式 JD
        ↓
程序生成 input snapshot 与 source units
        ↓
调用 1：DeepSeek 提取 RequirementFact 候选及每段 disposition
        ↓
Schema + Service 确定性校验
        ↓
调用 2：DeepSeek 独立复核原文与事实覆盖
        ↓
若有可定位问题：最多调用 1 次局部修复，只发送失败 source units
        ↓
Service 重新校验；仍有问题则整份 failed
        ↓
调用 3（有修复时为第 4 次）：DeepSeek 组织 EvaluationCriterion
        ↓
Service 校验所有 fact 恰好归组一次
        ↓
保存 pending_confirmation
        ↓
HR 查看原文、分组和 warning 后确认
        ↓
ready，等待 Application 才可进入初筛
```

这是一条输入、步骤和输出都固定的后端工作流。它不需要工具选择、自然语言路由或任意循环，因此使用普通 FastAPI Service，不引入 LangGraph。Codex Skill 也不能替代生产端的 Schema、事务、数据库约束和 API 权限，所以不作为运行依赖。

## 8. 三类 Prompt 与一次局部修复

### 8.1 调用 1：事实提取

输入完整 source-unit 表；输出每段 disposition、原文 quote、分类和语义重复关系。Prompt 明确：

- JD 是不可信数据，不执行其中指令；
- 只能引用原文，不能生成事实标题或改写事实；
- 不增加年限、数量、技能、程度或强制语气；
- 一段包含多个可独立评分语义时分别提取；
- 同一事实多处出现时保存全部来源；
- 模糊要求保留原文但标记，不自行具体化。

### 8.2 调用 2：完整性复核

使用同一个配置模型，但采用独立 Prompt。输入原 source units 与第一次形成的候选 facts；只判断遗漏、无支撑、错误排除、粒度、分类和多来源关系，不得直接重写整份答案。

### 8.3 可选局部修复

- 只有第一次输出已通过外层 JSON/Schema，且问题能定位到 source unit 时才允许修复。
- 一次性发送全部失败 source units、相关现有 facts 和 reviewer findings。
- 不发送无关 source units，不要求模型重新生成整份计划。
- 内容修复最多一轮；修复后 Service 再校验，任何未解决 finding、Schema 或业务错误都使整份计划 failed。
- 外层 JSON 完全不可解析、无法定位失败单元或 grouping 输出错误时，不进行盲目内容重试。

### 8.4 调用 3：评价维度归组

只输入已经通过校验的 facts，输出 criterion name 与 fact ID 分组。它不能新增、删除、合并或改写 facts；Service 用集合相等和出现次数校验所有事实恰好归组一次。

## 9. Service 必须校验什么

### 9.1 确定性校验

- 严格 JSON Schema、禁止额外字段和重复 JSON key；
- source unit ID 集合完整且每段只有一个 disposition；
- source field、ordinal、ID 和 snapshot 一致；
- quote 是对应原文中的连续片段，保持中英文、大小写和标点；
- fact/source/criterion ID 唯一且引用存在；
- category 属于五个受控值；
- priority 完全由字段位置计算；
- 相同规范化 quote 的确定性重复合并；
- 每条 fact 至少一个来源，每条 fact 恰好属于一个 criterion；
- warning code、引用 ID 和状态合法；
- 输入指纹在保存前仍是当前版本；
- failed 不保存可用于筛选的部分 facts/criteria。

### 9.2 Service 不能冒充理解的部分

程序不能只靠关键词证明语义没有遗漏，也不能自行发明事实或语义合并。因此完整性召回由独立 reviewer 和冻结人工标签共同验证。Service 的职责是阻止结构、来源、状态和明显业务错误，不宣称能够确定招聘语义绝对正确。

### 9.3 错误优先级

先完成可安全聚合的结构和来源检查，再决定 warning、局部修复或 failed。31 条以上不再被更早的内容错误伪装成 `too_many_items`；它只在事实通过校验后形成 `overly_broad_jd`。如果同一响应同时存在危险内容错误和数量 warning，危险错误进入修复或 failed，数量 warning 不冒充成功结果。

## 10. 特殊内容处理

### 10.1 冲突

- 保留全部原文来源，不替 HR 删除任一句；
- 同一语义可形成一个多来源 fact；
- priority 取 required > preferred > general；
- 生成 `conflicting_requirements` 并指出来源；
- HR 可以确认，也可以修改 JD 后重生成。

### 10.2 模糊要求

- “技术能力优秀”“沟通能力较强”等仍形成原文 fact；
- 不补成年限、项目数量、熟练等级或具体技术；
- 生成 `ambiguous_requirement`；
- 下游只能依据简历相关证据保守评价，不作为明确硬淘汰条件。

### 10.3 非评价内容

- 福利、公司介绍、团队宣传、工作流程和面试安排不形成 fact；
- 评价字段中出现时生成 `non_evaluation_content`；
- 混合句可以只引用其中连续的候选人要求原文；
- 该 warning 不阻止 HR 确认。

### 10.4 数量

- 0 条事实：failed，`JOB_EVALUATION_PLAN_NO_FACTS`；
- 1—4 条：pending confirmation + `limited_basis`；
- 5—30 条：正常 pending confirmation；
- 31 条及以上：pending confirmation + `overly_broad_jd`；
- 不为通过数量边界而截断或错误合并。

业务合同不在本文固定技术最大值。7R4-A 必须离线统计现有 20 份冻结 JD 的 source units、事实标签和序列化大小，并提出输入、source unit、fact、criterion 和 token 的技术安全值。如果该值会让合法 JD 业务失败，必须先更新本文并再次获得用户确认，不能在代码中偷偷保留 3.0 的 30 项上限。

## 11. HR、Job、Application 与 Screening

### 11.1 HR 操作

- 计划抽屉展示状态、事实数量、维度数量、全部 warning、每个维度和其中事实原文；
- 多来源 fact 展示主原文并可展开其他来源；
- `pending_confirmation` 提供“确认评价计划”和“修改 JD”操作；
- 不提供事实、维度、priority、分类、权重或阈值编辑；
- HR 确认时后端必须重新核对岗位状态、当前计划、4.0 合同和指纹；过期确认返回稳定 409。

### 11.2 岗位与申请

- Job 可以在计划 missing/generating/pending_confirmation/failed/outdated 时保持 open；
- Application 和 Resume 正常保存，不因计划失败丢失；
- AI 初筛显示等待计划的具体原因；
- 当前 4.0 ready 后，尚无成功报告且满足原有条件的申请按既有协调逻辑进入队列；
- 已有成功报告不自动重评。

### 11.3 以事实为初筛单位

- Screening 的 `requirement_key` 改为 4.0 的 `fact_id`；
- 每条 RequirementFact 独立得到 0—10 分、理由和证据；
- Criterion 只用于页面分组，不计算维度分、不设置权重；
- 原来的总体分、展示标签、证据、安全、时间事实和 HR 决策边界继续有效；
- 模糊 fact 的低分不能在文案中冒充明确不满足硬条件；
- 报告保存 `job_evaluation_plan_id` 和 4.0 fact 快照关系，历史报告继续按旧计划解释。

## 12. 指纹、幂等、版本与历史

### 12.1 4.0 版本

计划使用独立版本：

| 合同 | 版本起点 |
| --- | --- |
| 最终计划 Schema | `4.0` |
| input snapshot | `4.0` |
| 事实提取 Prompt | `job_requirement_fact_extraction_v1` |
| 完整性复核 Prompt | `job_requirement_coverage_review_v1` |
| 局部修复 Prompt | `job_requirement_local_repair_v1` |
| 维度归组 Prompt | `job_evaluation_criterion_grouping_v1` |
| source-unit 规则 | 保持版本化，若算法未变可沿用并显式记录 |
| 指纹规则 | `job_evaluation_input_v4` |
| 破坏性生成合同 | `fact_criterion_plan_generation_v1` |

同一模型配置用于三类调用，但每次保存具体 prompt role/version、实际 model、token、耗时、基础设施重试次数和业务结果。

### 12.2 输入与过期

`jd_fingerprint` 继续包含 title、department、job_background 和三个评价字段；`public_notes/location/employment_type/headcount/status/updated_at` 不进入。

进入指纹的字段变化时：

- 当前 generating/pending_confirmation/ready 计划 outdated；
- 引用旧计划的成功报告保留并标记过期；
- 等待或正在运行的旧输入结果不能成为当前成功结果；
- 不自动批量重评历史 Application。

### 12.3 历史兼容

- 1.0/2.0/3.0 计划和旧报告只读保留；
- 不把旧 `items` 猜测转换成 facts/criteria；
- 新生成入口只生成 4.0；
- 升级后仍开放的旧职位必须生成并确认 4.0，旧计划不能继续用于新的 AI 初筛；
- 前端明确显示格式版本和历史只读状态。

## 13. PostgreSQL 与审计

4.0 使用明确的新字段，不把 facts 和 criteria 再塞回 legacy `items`：

- `requirement_facts JSONB NULL`；
- `evaluation_criteria JSONB NULL`；
- `coverage_review_summary JSONB NULL`；
- `generation_audit JSONB NULL`；
- 状态约束加入 `pending_confirmation`；
- Schema 约束加入 `4.0`；
- 4.0 pending/ready 必须同时具有合法 facts、criteria、source review 和 coverage review；
- 4.0 不写 legacy `items/structured_coverage/free_text_coverage`；
- 旧行、旧外键和既有 migration 不改写。

普通数据库与页面不保存或展示完整原始模型响应。`generation_audit` 只保存调用角色、版本、实际模型、token、耗时、重试、成功/错误码等结构化元数据。失败计划不保存可被误用的部分 facts/criteria。

质量运行器可以在受控的、带日期的新结果文件中保存原始响应，用于复核模型行为；不得覆盖 3.0 定向结果或把质量文件当作生产数据库。

## 14. 错误与重试语义

每一次实际模型业务调用最多“首次尝试 + 1 次基础设施重试”。可重试范围仅包括网络、超时、限流、临时连接中断和 DeepSeek 5xx；认证、配置、余额、JSON、Schema、内容、来源、覆盖、归组和业务错误不做原样重试。

正常路径是 3 次业务调用；发生一次局部内容修复时是 4 次业务调用。每次调用的基础设施重试独立计算并单列审计。SDK 自动重试保持关闭。

任一最终失败：

- Job 不回滚、不自动关闭；
- Application 保持等待计划；
- 不使用旧计划、按行生成计划或 Fake 计划降级；
- 不删除旧成功报告；
- HR 可以修改 JD 或显式重新生成整份 4.0 计划。

## 15. 质量样本与门槛

### 15.1 样本不换

继续使用 3.0 已冻结的 20 份五段式 JD 和首轮 6 个定向样本：J5-03、J5-07、J5-14、J5-17、J5-19、J5-20。旧结果保持不变，4.0 新结果写入新文件。

4.0 调整后的边界预期：

- J5-01—J5-18：生成合法 `pending_confirmation`；
- J5-19：0 facts，`JOB_EVALUATION_PLAN_NO_FACTS`；
- J5-20：31 条及以上独立 facts，生成 `pending_confirmation + overly_broad_jd`，不再预期 `too_many_items`。

### 15.2 计划质量硬门槛

- 6 个定向样本必须 6/6 满足完整逐样本合同；
- 定向 `targeted_gate_passed=true` 后才允许正式 20 份；
- J5-01—J5-18 全部形成合法待确认计划，两个边界结果符合 4.0 新预期；
- 明确必测项召回 100%；
- 人工标注主要语义召回不低于 95%；
- source unit 最终处理率、quote 定位和 priority 一致率均为 100%；
- 每条 fact 恰好进入一个 criterion，覆盖率 100%；
- 擅自新增要求、错误合并、明显重复、错误多来源合并、背景/备注污染均为 0；
- 预期 warning 命中 100%；
- 任一不可追溯事实或新增硬要求都会阻止门禁通过。

不降低门槛、不删除失败样本、不挑选最好响应，也不把 Fake/Mock 结果计入真实质量。

### 15.3 调用与成本

4.0 一份正常 JD 至少 3 次模型调用，有局部修复时最多 4 次业务调用：

- 6 份定向：基线 18 次，最多 24 次业务调用；
- 正式 20 份：基线 60 次，最多 80 次业务调用；
- 基础设施重试单列，不冒充业务调用；
- dry-run 必须为 0 次模型调用、0 次结果写入；
- 每一轮真实调用前重新确认模型、官方单价、估算上限和授权。

正式 20 份只能在定向门禁通过后执行。计划质量通过后，才允许进入报告质量和三次稳定性验证。

## 16. 自动化与人工验收

### 16.1 后端与数据库

- 4.0 Schema、五分类、facts、criteria、review、warnings 和额外字段拒绝；
- source-unit 稳定切片、事实多来源、原文连续定位和程序 priority；
- 三次调用顺序、独立 Prompt、同模型配置和调用次数；
- 一次局部修复、失败单元范围、无盲目整单重试；
- 基础设施重试与内容修复独立计数；
- criterion 对 fact 的集合相等和恰好一次覆盖；
- pending confirmation、确认、过期、迟到响应和并发确认；
- 31+ warning、0 facts 失败、冲突、模糊和非评价内容；
- 1.0/2.0/3.0 历史只读与 4.0 migration；
- Screening 只接受当前 4.0 ready，并逐 fact 评价。

### 16.2 前端与浏览器

- generating/pending_confirmation/ready/failed/outdated/legacy/closed 状态；
- 按 criterion 展示事实，展开多来源和 warning；
- 确认计划、修改 JD、禁止直接编辑计划；
- 等待计划原因与旧报告过期；
- 报告按 criterion 分组但逐 fact 显示分数、理由和证据；
- 1440×900、820×1180、390×844；
- 键盘、焦点、轮询终止、普通文本安全和无整页横向溢出；
- 继续补回 3.0 阶段延期的全部 7R-H 浏览器欠账。

### 16.3 人工场景

1. HR 开放岗位，计划生成完成后必须确认，确认前申请只等待不评分。
2. 同一要求在职责、必需和加分字段重复时形成一个多来源 fact，priority 为 required，并提示冲突。
3. 一段包含三个可独立评价要求时形成三条 facts，并全部只归入一个 criterion。
4. 模糊要求保留原文且不被模型补成年限或数量。
5. 福利混入要求字段时不形成 fact，但页面显示 warning。
6. 31 条以上 facts 不截断、不直接失败，HR 可以看 warning 后确认。
7. JD 在生成或待确认期间变化时旧计划过期，迟到结果不能覆盖。
8. HR 无法编辑计划；修改 JD 后重新生成新版本。
9. 旧 3.0 计划和旧报告可查看，但旧职位必须确认 4.0 后才能新筛选。
10. 4.0 报告逐 fact 评价，criterion 只分组，不出现维度权重或维度分。

## 17. 实施批次、依赖与停止点

以下顺序已于 2026-08-24 获得用户最终确认。每批开始前重新检查 git status、相关差异、分支/HEAD/上游、Alembic current/head、业务表计数和上一批结果。每轮只执行一个已确认批次，结束后停止。

### 17.1 总体顺序

| 批次 | 唯一目标 | 依赖 | 停止点 |
| --- | --- | --- | --- |
| 7R4-A | 4.0 自动化合同与离线容量基线 | 本文最终确认 | 不改生产代码，等待 7R4-B |
| 7R4-B | 4.0 Schema、Model 与 migration | 7R4-A 红灯分类 | 不改 Prompt/Service，等待 7R4-C |
| 7R4-C | facts/review/repair/criteria 纯生成工作流 | 7R4-B 数据稳定 | 不恢复 API/Screening，等待 7R4-D |
| 7R4-D | 计划持久化、状态、确认 API 与 Job 协调 | 7R4-C 生成稳定 | Screening 仍按旧合同等待，等待 7R4-E |
| 7R4-E | Screening 后端切换为 4.0 facts | 7R4-D 可确认 ready | 不改 React，等待 7R4-F |
| 7R4-F | React 计划与报告交互切换 4.0 | 7R4-E 后端稳定 | 不调用真实模型，等待 7R4-G |
| 7R4-G | 质量运行器、dry-run 与无真实模型全链 | 7R4-F 程序稳定 | 0 次 DeepSeek，等待成本确认 |
| 7R4-H | 6 份定向与正式 20 份计划真实质量 | 7R4-G + 单独成本授权 | 未通过不得进入 7R4-I |
| 7R4-I | 报告合法率、方向与三次稳定性 | 7R4-H 通过 + 成本授权 | 未通过不得收尾 |
| 7R4-J | PostgreSQL/API/浏览器与阶段收尾 | 7R4-I 通过 | 阶段 7 结束，停止等待阶段 8 |

### 17.2 7R4-A：合同测试与离线容量基线

- 唯一目标：把本文规则变成可重复的红灯测试，并用现有冻结样本统计 source units、人工 facts、criteria 候选和序列化大小。
- 通俗解释：先出考试题并测量真实题量，不先猜技术上限。
- 允许：新增 4.0 后端/前端合同测试、虚构夹具、离线统计脚本和本设计结果小节。
- 链路：测试覆盖前端→API→Schema→Service→Model→PostgreSQL，但不修改生产层。
- 禁止：生产代码、migration、数据库业务写入、真实 DeepSeek、修改旧结果、skip/xfail。
- 交付：字段、状态、三/四次调用、修复、warning、历史、Screening 和 UI 红灯矩阵；技术容量统计与建议。若建议会引入新的业务失败边界，先更新本文并重新确认。
- 验证：测试正常收集、既有无关回归无新增失败、dry-run 0 调用、git diff --check。
- 完成/失败/下一步：红灯责任完整才完成；失败留在测试或夹具层；停止等待 7R4-B。

### 17.3 7R4-B：4.0 数据与持久化

- 唯一目标：Schema、Model 和 PostgreSQL 能准确保存 4.0 与只读历史。
- 通俗解释：先做能区分事实和章节的数据盒子。
- 允许：`backend/app/schemas/job_evaluation_plan.py`、`backend/app/models/job_evaluation_plan.py`、一条新 `backend/migrations/versions/` revision、直接相关测试。
- 链路：Schema→Model→PostgreSQL。
- 禁止：Prompt、Adapter、生成 Service、API 行为、Screening、React、真实模型、修改既有 migration。
- 交付：facts/criteria/review/audit、pending_confirmation、4.0 约束和 1.0—3.0 历史读取。
- 验证：定向测试、临时 PostgreSQL upgrade→downgrade→upgrade、旧计划与报告外键夹具、正式库确认后的单向升级、current/head/check、表计数；DeepSeek 0 次。
- 完成/失败/下一步：4.0 可持久化且旧行不改写才完成；失败返回 Schema/Model/migration；停止等待 7R4-C。

### 17.4 7R4-C：纯计划生成工作流

- 唯一目标：在不接业务 API 的情况下完成 facts→review→可选 repair→criteria 的严格工作流。
- 通俗解释：先把三位“整理员、检查员、归组员”接好，再接岗位状态。
- 允许：`backend/app/prompts/job_evaluation_plan.py`、`backend/app/adapters/job_evaluation_plan.py`、`backend/app/services/job_evaluation_plan_service.py` 中的纯生成边界、source-unit helper、4.0 AI Schema 和测试。
- 链路：Schema→Service→Prompt/Adapter。
- 禁止：Job/API 状态持久化、Screening、React、migration、真实 DeepSeek、降级计划。
- 交付：三类 Prompt、一类局部修复 Prompt、同模型分角色调用、严格顺序、调用计数、Service 校验和 Fake Adapter。
- 验证：正常 3 次、修复 4 次、每次基础设施重试、外层 JSON 失败、局部失败、归组失败、迟到输入检查的定向及后端回归；DeepSeek 0 次。
- 完成/失败/下一步：Fake 下完整生成或受控失败才完成；失败返回切片/Prompt/Schema/Adapter/Service；停止等待 7R4-D。

### 17.5 7R4-D：计划状态、确认 API 与 Job 协调

- 唯一目标：把纯生成结果安全持久化，并由 HR 将 pending 计划确认成 ready。
- 通俗解释：评价标准先放到待确认区，HR 点确认后才生效。
- 允许：`backend/app/services/job_evaluation_plan_service.py`、`backend/app/api/job_evaluation_plans.py`、Job 提交后的最小协调、相关 Schema/测试。
- 链路：API→Schema→Service→Model→PostgreSQL。
- 禁止：Screening 评价、React、真实 DeepSeek、自动确认、直接编辑计划。
- 交付：生成/重生成/读取/确认、指纹、幂等、outdated、迟到响应、Job 不回滚和安全错误。
- 验证：Fake API、并发确认、JD 变化、仅 public_notes 变化、失败保护、真实 PostgreSQL 事务和调用次数；DeepSeek 0 次。
- 完成/失败/下一步：只有当前 4.0 pending 可确认且 ready 不会被旧响应覆盖才完成；失败返回 API/Service/事务；停止等待 7R4-E。

### 17.6 7R4-E：Screening 后端切换 4.0

- 唯一目标：只让当前 4.0 ready 计划按 fact 进入初筛。
- 通俗解释：评分器逐条评价 JD 原文事实，章节只负责排版。
- 允许：`backend/app/services/screening_service.py`、`screening_evaluation_service.py`、Screening Prompt/Adapter/Schema/API 和直接相关测试、必要向前 migration。
- 链路：API→Schema→Service→Prompt/Adapter→Model→PostgreSQL。
- 禁止：React、计划生成合同、权重、维度分、真实 DeepSeek、自动重评历史报告。
- 交付：waiting 原因、fact key 完整一一对应、criterion 展示关系、旧计划阻止新筛选、迟到结果和旧成功报告保护。
- 验证：Fake 单次评价、证据/时间事实/安全回归、状态矩阵、最多 20 人重评和真实 PostgreSQL 事务；DeepSeek 0 次。
- 完成/失败/下一步：4.0 ready 可筛且 1.0—3.0 只读不可新筛才完成；失败返回 Screening Schema/Service/事务；停止等待 7R4-F。

### 17.7 7R4-F：React 4.0 交互

- 唯一目标：HR 能理解、确认并查看 4.0 计划和逐 fact 报告。
- 通俗解释：页面按章节摆放事实，但每条事实仍有自己的评价和证据。
- 允许：`JobEvaluationPlanDrawer.tsx`、Screening 抽屉/报告、前端 Service/类型/样式/测试，以及暴露的合同内最小 API 映射缺陷。
- 链路：前端→API。
- 禁止：真实 DeepSeek、核心后端合同、计划编辑、同输入抽卡重生成、维度分。
- 交付：pending 确认、warnings、多来源、criteria/facts、等待原因、历史版本和逐 fact 报告。
- 验证：前端定向/全量、TypeScript、Vite、后端受影响回归、受控 API/PostgreSQL 夹具；DeepSeek 0 次。
- 完成/失败/下一步：程序与页面合同一致才完成；失败返回 React/类型/API 映射；停止等待 7R4-G。

### 17.8 7R4-G：质量运行器与零调用全链

- 唯一目标：在花费真实模型费用前证明样本、统计、调用预算和程序链可重复。
- 通俗解释：先演练考试流程，确认不会多调用或写错结果。
- 允许：20 份冻结 JD 的 4.0 期望、计划/报告质量运行器、统计测试、Fake 全链和新的结果路径约定。
- 链路：质量夹具→Prompt/Adapter→Service→统计；并覆盖 API/PostgreSQL 的受控 Fake 集成。
- 禁止：真实 DeepSeek、放宽门槛、修改样本文本以迁就模型、覆盖旧结果。
- 交付：6 份定向和 20 份正式选择、每阶段 3/4 次调用预算、旧结果隔离、dry-run 门和费用估算输入。
- 验证：dry-run 0 调用、0 结果写入；Fake 三/四调用分支、定向/全量回归、git diff --check。
- 完成/失败/下一步：运行器能阻止定向未通过时的正式调用才完成；失败返回夹具/统计/调用门；停止并向用户申请 7R4-H 模型与成本授权。

### 17.9 7R4-H：计划真实质量

- 唯一目标：证明 4.0 在真实 DeepSeek 下稳定生成合格计划。
- 通俗解释：先复考原来失败的 6 题，通过后再考完整 20 题。
- 允许：真实质量结果、新发现的本文合同内最小 Prompt/Service 修复；任何修复后必须重新走 7R4-C/G 相关门禁。
- 链路：Prompt/Adapter→Service→质量统计。
- 禁止：Screening 质量整改、React、降门槛、删样本、挑最好结果、覆盖 3.0 结果。
- 交付：6 份定向新结果；6/6 通过后才产生 20 份正式新结果；逐调用 token、费用、重试和原始响应受控记录。
- 验证：第 15.2 节全部门槛；定向最多 24 次、正式最多 80 次业务调用，实际基础设施重试单列。
- 完成/失败/下一步：正式门槛全部通过才完成；失败返回具体 Prompt/Schema/Service 层并停止；通过后等待 7R4-I 成本授权。

### 17.10 7R4-I：报告质量与稳定性

- 唯一目标：证明 4.0 facts 进入下游后的合法率、方向、安全和三次稳定性。
- 通俗解释：岗位标准先可靠，再验证简历评分是否可靠。
- 允许：冻结 20 组 JD/Resume、报告质量运行器、结果，以及既有报告合同内最小修复。
- 链路：Screening Prompt/Adapter→Service→质量统计。
- 禁止：计划核心合同、证据/事实/安全门槛放宽、失败样本移出分母、React。
- 交付：20/20 至少一份合法报告、方向一致性、20×3 稳定性和安全硬门槛结果。
- 验证：沿用阶段 7 已确认的报告质量、方向、证据、时间事实和稳定性门槛；真实调用前单独确认成本。
- 完成/失败/下一步：全部通过才完成；失败返回报告 Prompt/Schema/证据/事实层；停止等待 7R4-J。

### 17.11 7R4-J：最终数据库、API、浏览器与收尾

- 唯一目标：证明 4.0 全链真实可操作并完成阶段 7。
- 通俗解释：最后从 HR 页面一路走到数据库和报告，补完所有浏览器欠账。
- 允许：全量回归、真实 PostgreSQL/API、浏览器、合同内最后最小缺陷、验收文档、PROJECT_STATE、实施计划和文档索引。
- 链路：前端→API→Schema→Service→Model→PostgreSQL 全链。
- 禁止：新的真实 DeepSeek 调用、放宽质量门槛、进入阶段 8/Agent/RAG/登录。
- 交付：migration current/head/check、业务表计数、真实 API 主链、HR 决策隔离、三档浏览器、全部状态、键盘/焦点/轮询/溢出/普通文本安全，以及 3.0 延期浏览器清单逐项结论。
- 验证：后端/前端全量、真实数据库/API、浏览器人工矩阵；使用 7R4-H/I 已验证的固定结果，DeepSeek 0 次。
- 完成/失败/下一步：自动化、数据库、API、计划质量、报告质量和浏览器全部通过并获用户确认才完成；失败返回实际责任批次；完成后停止，不进入阶段 8。

## 18. 最终门禁

1. 用户确认本文业务规则只代表需求已定，不代表 4.0 已实现。
2. 第 17 节实施顺序确认后，每轮仍只允许执行用户当轮明确授权的一个批次。
3. 每批结束后必须报告修改文件、链路位置、验证结果、能证明什么、不能证明什么和剩余风险，然后停止等待下一批确认。
4. 真实 DeepSeek 只允许在 7R4-H/I，且每轮都要单独确认模型、费用和调用上限。
5. 核心字段、状态、修复次数、数量语义、历史策略、质量门槛或批次顺序变化时，必须先更新本文并重新确认。
6. 不修改既有 migration，不覆盖 3.0 结果，不使用 reset/clean/checkout/restore 覆盖工作区。
7. 4.0 完成前不得把 3.0、Fake、部分计划或未确认计划用于新的 AI 初筛。
8. 阶段 7 完成前不得进入阶段 8；阶段 7 完成后也必须停下等待新的阶段门禁。

当前停止点：4.0 业务决定和 7R4-A—7R4-J 顺序已确认，7R4-A—7R4-F 已完成。唯一下一步是等待用户明确确认 7R4-G；未经确认不得进入 7R4-G，更不得提前进入 7R4-H—J 或调用真实 DeepSeek。

## 19. 7R4-A 实施结果（2026-08-24）

### 19.1 修改边界与测试结论

本批只新增 4.0 专用后端合同测试、前端合同测试、测试夹具和离线容量脚本，并更新本文与 `PROJECT_STATE.md`。没有修改生产 Prompt、Adapter、Schema、Service、Model、API、React 组件、migration、PostgreSQL 业务数据、3.0 质量结果、冻结样本文本或质量门槛。

4.0 新测试共正常收集 63 条：8 条通过，55 条按预期失败，0 条 skip、0 条 xfail、0 条导入/收集/夹具错误。55 条红灯唯一归属如下：

| 责任批次 | 红灯数 | 当前 3.0 缺少的 4.0 能力 |
| --- | ---: | --- |
| 7R4-B | 19 | 4.0 版本、`pending_confirmation`、RequirementFact/EvaluationCriterion/coverage/audit Schema、`public_notes` 排除、四个 JSONB 列、约束与向前 migration |
| 7R4-C | 14 | 三类正常 Prompt、一次局部修复 Prompt、Prompt 排除 `public_notes`、三/四次业务调用、技术重试与内容修复独立计数、程序 priority、0/31+ 语义和失败无部分内容 |
| 7R4-D | 6 | 生成成功先 pending、HR 确认 API、确认时重核当前合同/指纹、确认不调用 Adapter且不能编辑计划 |
| 7R4-E | 6 | Screening 只接受当前 4.0 ready、逐 `fact_id` 评价、criterion 只展示分组、1.0—3.0 阻止新筛选 |
| 7R4-F | 10 | 前端 4.0 类型/映射、pending 确认、五类 warning、criteria/facts 展示、逐 fact 报告和确认请求 |

8 条绿灯不是把 3.0 冒充 4.0：其中 6 条固定离线样本、245 条人工事实、`public_notes` 排除、旧 30 条上限冲突和零调用门；另外 2 条只证明现有前端已经具备多来源原文展开与 1.0—3.0 历史只读基础。

### 19.2 离线容量口径

- 样本文本严格复用冻结 J5-01—J5-20，SHA-256 为 `23651a92bb68602f096cf30519d5c11cd2ce6e724950f158587ba201e41fdfe0`；定向样本仍为 J5-03、J5-07、J5-14、J5-17、J5-19、J5-20。
- “人工事实数”复用现有 245 条人工主要语义 expectation，每条作为 4.0 至少一条独立 fact；J5-14 的客户访谈 expectation 按多来源 fact 估算。它是已有人工标签的容量下界，不表示真实模型最终只能提取 245 条。
- “预计 criterion 数”只为序列化容量估算，按原顺序每 3 条 facts 临时分一组；不是业务数量目标。正式 criterion 仍允许从 1 到 fact 数量，由 7R4-C 的归组调用决定。
- facts 容量估算使用完整 source unit 作为 quote，通常比生产所需的最小连续 quote 更保守；category 暂以固定占位值计算 JSON 大小，不作为人工分类质量结论。
- 脚本不实例化 Adapter、不读取 API Key、不写结果文件；真实模型调用 0 次。

### 19.3 每份冻结 JD 容量

| 样本 | source units | 人工 facts | 预计 criteria | input snapshot 字符 | facts 字符 | criteria 字符 | 合并输出字符 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| J5-01 | 13 | 13 | 5 | 2491 | 2714 | 487 | 3246 |
| J5-02 | 13 | 13 | 5 | 2430 | 2690 | 487 | 3222 |
| J5-03 | 13 | 13 | 5 | 2688 | 2811 | 487 | 3343 |
| J5-04 | 13 | 13 | 5 | 3611 | 3220 | 487 | 3752 |
| J5-05 | 13 | 13 | 5 | 2393 | 2671 | 487 | 3203 |
| J5-06 | 13 | 13 | 5 | 2388 | 2665 | 487 | 3197 |
| J5-07 | 13 | 13 | 5 | 2521 | 2736 | 487 | 3268 |
| J5-08 | 13 | 13 | 5 | 2422 | 2681 | 487 | 3213 |
| J5-09 | 3 | 3 | 1 | 754 | 618 | 103 | 766 |
| J5-10 | 4 | 4 | 2 | 866 | 793 | 181 | 1019 |
| J5-11 | 14 | 14 | 5 | 2558 | 2869 | 499 | 3413 |
| J5-12 | 13 | 14 | 5 | 2553 | 2977 | 499 | 3521 |
| J5-13 | 14 | 13 | 5 | 2481 | 2635 | 487 | 3167 |
| J5-14 | 13 | 10 | 4 | 2275 | 2388 | 385 | 2818 |
| J5-15 | 13 | 13 | 5 | 3638 | 3285 | 487 | 3817 |
| J5-16 | 13 | 13 | 5 | 2316 | 2632 | 487 | 3164 |
| J5-17 | 13 | 13 | 5 | 2329 | 2639 | 487 | 3171 |
| J5-18 | 13 | 13 | 5 | 2420 | 2670 | 487 | 3202 |
| J5-19 | 5 | 0 | 0 | 1074 | 2 | 2 | 49 |
| J5-20 | 33 | 31 | 11 | 5045 | 5944 | 1099 | 7088 |

汇总结果：source units 为 3—33、总计 255、中位数 13、P95 14；人工 facts 为 0—31、总计 245、中位数 13、P95 14；预计 criteria 为 0—11、总计 93、中位数/P95 均为 5。input snapshot 最大 5045 字符；facts 最大 5944 字符；criteria 最大 1099 字符；合并输出最大 7088 字符、P95 3817 字符。

### 19.4 现有 3.0 上限判断与建议门禁

- `JOB_EVALUATION_PLAN_MAX_ITEMS=30` 会把合法 J5-20 的 31 facts 错误拒绝，明确不能带入 4.0；4.0 必须得到 `pending_confirmation + overly_broad_jd`，不失败、不截断。
- `JOB_EVALUATION_PLAN_MAX_SOURCE_UNITS=100` 没有限制当前冻结集（最大 33），但会拒绝当前字段长度内“极端碎片化但仍合法”的 JD，不能未经确认直接沿用为 4.0 业务失败边界。
- 当前 Adapter 的 100000 input chars 与 8000 output tokens 对冻结样本尚未观察到直接限制；但 source-unit JSON 会重复字段名、ID 和原文，极端碎片化可能让合法文本超过 100000。8000 token 也不能由“7088 JSON 字符”直接证明一定安全，因为不同调用的 Schema、review finding 和 token 化不同。

离线脚本提出的技术候选值如下。用户已于 2026-08-24 确认：这些数值是防止异常资源消耗的技术安全边界，不是业务质量边界；达到边界时必须返回明确错误，禁止静默截断；31 条只产生 warning；7R4-G 可以根据 Fake/dry-run 结果向上调整，未经重新确认不得向下收紧。各数值仍只能在其责任批次实现：7R4-B 只负责数据 Schema 容量，模型输入/输出与 token 参数留在 7R4-C/G：

| 对象 | 候选值 | 结论 |
| --- | ---: | --- |
| input snapshot / 单次输入序列化 | 1,000,000 字符 | 已确认为技术安全边界；7R4-C/G 仍需用极端碎片夹具验证成本和模型上下文 |
| 单个 source unit | 10,000 字符 | 与单个评价字段当前最大长度一致，不截断合法字段 |
| source unit 数量 | 512 | 已确认为技术安全边界，不得当作业务质量失败 |
| fact 数量 | 512 | 移除 30 条业务失败；已确认为技术安全边界，不得静默截断 |
| criterion 数量 | 512 | 允许等于 fact 数量；已确认为技术安全边界 |
| facts JSON | 262,144 字符 | 已确认为技术安全边界；仍须通过 7R4-C/G 夹具验证 |
| criteria JSON | 131,072 字符 | 已确认为技术安全边界；仍须通过 7R4-C/G 夹具验证 |
| facts + criteria 结构化输出 | 393,216 字符 | 已确认超限受控失败且不允许静默截断；实现留在 7R4-C/G |
| 单次模型输出 | 16,000 tokens | 已确认为候选技术边界；需在 7R4-C/G 验证，并在真实调用前重新确认模型能力和成本 |

这些有限上限仍可能让字段长度合法但极端碎片化的 JD 技术失败。用户已确认接受这一点，但要求它们只作为明确、可观测、禁止截断的技术保护：7R4-B 可把 source unit/fact/criterion 的 512 容量写入数据 Schema；输入序列化、JSON 总尺寸和 token 边界不得提前越过 7R4-C/G 实现。

### 19.5 验证结果与证明边界

- 4.0 后端合同：51 条正常收集，6 passed、45 expected failed；其中红灯按 7R4-B/C/D/E 分别为 19/14/6/6。
- 4.0 前端合同：12 条正常收集，2 passed、10 expected failed，红灯全部归 7R4-F。
- 既有前端测试：44/44 通过；TypeScript 严格检查和 Vite 5.4.21 生产构建通过，转换 3121 个模块。
- 既有受影响后端非数据库回归：89 passed，另有 7 个 unittest subtests passed 和 1 条既有 PyPDF2 弃用 warning。
- 后端全量在 79% 后进入 PostgreSQL 测试时失败；定向 `test_screening_plan_v3_gate_contract.py -x` 证明原因是本机 PostgreSQL 端口拒绝连接，`docker-compose ps` 又证明 Docker Desktop Linux engine 未运行。该失败不是 4.0 合同红灯，也不能写成全量回归通过。
- `git diff --check`、新增文件语法和最终工作区边界在本批结束前再次执行。

这些结果证明：4.0 合同测试可以正常收集；当前 3.0 缺口已被稳定暴露并唯一归责；冻结样本容量、J5-20 的 30 条错误边界和 `public_notes` 排除可离线复现；本批没有调用真实模型。它们不能证明：4.0 已实现、候选技术上限已获批准、真实 PostgreSQL 全量回归通过、真实模型质量合格、Screening/React 4.0 可用或阶段 7 已完成。

7R4-A 已停止；用户随后确认第 19.4 节技术上限处理口径并明确授权 7R4-B。7R4-B 完成后必须重新停止等待 7R4-C，不得连续实施。

## 20. 7R4-B 实施结果（2026-08-24）

### 20.1 修改边界与数据职责

本批只修改 `backend/app/schemas/job_evaluation_plan.py`、`backend/app/models/job_evaluation_plan.py`、新增 revision `c7d9e2f4a681`，并增强直接相关 Schema/Model/migration 测试；同步更新本文和 `PROJECT_STATE.md`。没有修改 Prompt、Adapter、生成 Service、API 业务行为、Screening、React、冻结样本或旧质量结果，真实 DeepSeek 调用为 0。

Schema 新增独立 4.0 数据版本常量、`pending_confirmation`、RequirementFact、EvaluationCriterion、4.0 source review、coverage review、五类 warning 和 generation audit。RequirementFact 没有 AI 生成 title/statement/text；priority 只能与来源字段的 required > preferred > general 一致；每个 quote 必须在对应 source unit 中连续定位；同一 fact 可保存多个来源；每条 fact 必须且只能属于一个 criterion。4.0 source unit/fact/criterion 数量技术边界均为 512，单个 source unit 与 fact quote 均支持 10,000 字符；31 facts 可完整通过 Schema，不再复用 3.0 的 30 items 上限。

3.0 Service 当前直接依赖原有“当前运行版本”常量。为避免 7R4-B 在未修改 Service 的情况下意外启动半成品 4.0，本批新增 `JOB_EVALUATION_PLAN_V4_*` 数据常量，同时保留 3.0 运行常量；4.0 Prompt/Adapter/生成链的版本切换仍唯一属于 7R4-C。这不改变 4.0 最终版本合同，只隔离批次激活时机。

Model 和 PostgreSQL 新增四个可空 JSONB 列：`requirement_facts`、`evaluation_criteria`、`coverage_review_summary`、`generation_audit`。legacy `items` 改为可空，使 4.0 可以明确保存 NULL；数据库约束要求 4.0 不写 legacy payload，1.0—3.0 不写 4.0 payload，4.0 pending/ready 同时具备完整顶层 payload，4.0 generating/failed 不保存部分结果。旧计划、旧报告外键和既有 migration 不改写。

### 20.2 自动化与剩余红灯

- 7R4-B 专项为 29/29 passed：7R4-A 分配给本批的原19条红灯全部变绿，另新增10条防回归测试，覆盖 migration 操作/阻断、31 facts、10,000字符来源、程序 priority、连续 quote、失败无部分结果和3.0序列化隔离。
- 当前4.0后端专项共61条：35 passed，26 expected failed；剩余红灯唯一归属为 7R4-C 14、7R4-D 6、7R4-E 6。
- 4.0前端仍为2 passed、10 expected failed，10条全部保留给7R4-F；既有前端44/44通过。
- 排除尚未授权的7R4-C—E三组预期红灯后，后端全量为828 passed、408 subtests passed；只有既有 PyPDF2 弃用 warning 和一条异步连接取消 RuntimeWarning。

### 20.3 PostgreSQL 验证

独立临时 PostgreSQL 使用端口55432，不挂正式 volume。先升级到 `b4e8c2d7f913`，写入1.0/2.0/3.0三条计划和引用3.0计划的一条旧报告，再完成：

1. `b4e8c2d7f913 -> c7d9e2f4a681`，旧三行内容与旧报告外键不变，新四列均为NULL；
2. 插入4.0 `pending_confirmation` 行，验证 legacy items 为NULL且facts/criteria新列可持久化；
3. 4.0行存在时，downgrade以 `STAGE7_PLAN_V4_DOWNGRADE_BLOCKED` 在DDL前受控停止；
4. 删除临时4.0行后，`downgrade b4e8c2d7f913 -> upgrade head` 成功，旧三行和报告外键仍不变；
5. 最终 `current=head=c7d9e2f4a681`，`alembic check` 返回 `No new upgrade operations detected`。

正式开发库升级前 revision 为 `e4c7a1b9d632`，`jobs/job_evaluation_plans/screening_reports/screening_runs` 均为0；单向执行既有f2/a9/b4与本批c7后，`current=head=c7d9e2f4a681`、`alembic check`通过，最终八张相关业务表计数均为0。没有写入或删除业务行。临时容器在本批结束前删除。

### 20.4 证明边界、风险与停止点

这些结果证明4.0数据合同可以严格解析并持久化，31 facts和10,000字符连续来源不会被3.0边界误拒绝，旧1.0—3.0行与报告外键可跨migration往返保留，失败计划不能形成可筛选的顶层部分payload。PostgreSQL约束负责顶层JSON类型、版本隔离、状态和NULL关系；嵌套fact来源、priority、归组完整性仍由Pydantic Schema与后续Service校验，直接绕过应用写任意JSON不是受支持业务入口。

这些结果不能证明Prompt、Adapter或三/四次生成工作流已经实现，不能证明HR确认、Screening或React 4.0可用，也不能证明真实模型质量。输入序列化、facts/criteria总JSON尺寸和16,000 tokens边界仍按已确认顺序留给7R4-C/G验证。

7R4-B 到此停止。唯一下一步是等待用户明确确认7R4-C；不得自动进入7R4-C。

## 21. 7R4-C 实施结果（2026-08-24）

### 21.1 修改边界与纯生成职责

本批只修改 4.0 AI Schema、`backend/app/prompts/job_evaluation_plan.py`、`backend/app/adapters/job_evaluation_plan.py`、`backend/app/services/job_evaluation_plan_service.py` 的纯生成边界和直接测试，并同步本文与 `PROJECT_STATE.md`。没有修改 API、Job 状态持久化、Screening、React、Model 或 migration，也没有写入数据库或调用真实 DeepSeek。

纯生成链现为 `facts 提取 → coverage review → 可选一次局部 repair → criteria 归组`。四个 Prompt 角色分离，所有 JD 文本按不可信数据处理，`public_notes` 不进入任何角色输入。AI 只返回临时候选 ID、五分类和连续原文来源；最终 `fact_id`、`criterion_id` 以及 required > preferred > general 的 priority 均由 Service 稳定计算。

正常路径恰好 3 次业务调用；coverage 失败时只向 repair 提供失败 source units、相关 facts 和 findings，最多修复 1 次，因此恰好 4 次。基础设施短暂错误只在当前角色内最多重试 1 次，与内容修复分开计数；认证、非法 JSON 和确定性合同错误不重试。任何终端失败只返回安全错误与完整审计，不暴露部分 facts/criteria。

Service 会重新验证 source unit ID、逐字连续 quote、candidate/review 双向引用、coverage finding 引用、repair 范围、每个 fact 恰好归属一个 criterion，并在进入下一角色前执行迟到输入检查。0 facts 受控失败；1—4 facts 生成 `limited_basis`；31 条及以上完整保留并生成 `overly_broad_jd`，不截断。已实现 1,000,000 输入字符、262,144 facts JSON、131,072 criteria JSON、393,216 合并输出字符和 16,000 output tokens 技术保护。

### 21.2 自动化、数据库与调用结果

- 7R4-C 文件 24/24 passed：原 14 条红灯全部转绿，并增加 10 条 Fake 行为回归。正常路径业务调用/实际 attempt 为 3/3，局部修复为 4/4，一次技术重试为 3/4，且 `infrastructure_retry_count=1`、`content_repair_count=0`。
- 7R4-B + 7R4-C 定向为 53/53 passed；当前 4.0 后端合同共 71 条，59 passed、12 expected failed，剩余红灯仅属 7R4-D 6 条和 7R4-E 6 条。
- 3.0 Adapter/Schema/生成 Service 相容回归为 157 passed + 32 subtests passed；排除后续 D/E 预期红灯后，后端全量为 852 passed + 408 subtests passed。仅有既有 PyPDF2 弃用 warning 和一条异步连接取消 RuntimeWarning。
- 7R4-F 前端合同保持 2 passed、10 expected failed；既有前端 44/44 passed。这是后续边界仍被锁定的证据，不是 C 的失败。
- 新增/受影响 Python 文件 `py_compile` 通过，`git diff --check` 通过。
- 正式开发库只读复核为 `current=head=c7d9e2f4a681`，`alembic check` 返回 `No new upgrade operations detected`；8 张相关业务表计数均为 0。本批没有执行 migration，没有写入或删除业务行。
- 所有生成验证均使用 Fake Adapter；真实 DeepSeek 调用 0 次。

### 21.3 证明边界、风险与停止点

这些结果证明：4.0 纯生成引擎在 Fake 下能以固定三/四次业务调用完成生成或安全失败；局部修复不接收无关 JD；来源、priority、覆盖和归组由程序二次守住；0/31+ 边界、安全错误、审计计数和 3.0 隔离按合同工作。

它们不能证明：真实 DeepSeek 会稳定遵守四个 Prompt，16,000 tokens 的真实模型成本/上下文足够，API 能持久化 `pending_confirmation`，HR 确认、Screening 或 React 4.0 可用，也不能证明阶段 7 已完成。真实模型质量与极端容量成本仍属 7R4-G/H；API 事务、并发确认和迟到响应落库仍属 7R4-D。

7R4-C 到此停止。唯一下一步是等待用户明确确认 7R4-D；不得自动进入 7R4-D。

## 22. 7R4-D 实施结果（2026-08-24）

### 22.1 修改边界与链路职责

本批只接通“API → Schema → Service → Model → PostgreSQL”的 4.0 计划落库与 HR 确认链路。公开生成入口现在固定使用 7R4-C 的 4.0 纯生成工作流：成功结果先保存为 `pending_confirmation`，确认接口在数据库事务中重新锁定 Job 与当前计划、复核岗位开放状态、4.0 合同和两层指纹，完整性通过后才转为 `ready`。确认请求没有计划正文，HR 不能借确认接口编辑 AI 提取的事实。

同输入的 pending 生成与 ready 确认均幂等；`public_notes` 不进入快照或指纹，因此修改候选人可见备注不会错误淘汰计划。JD 在生成或待确认期间变化时，旧计划转 `outdated`；迟到成功或失败都不能覆盖已经 ready 的计划。非法 JSON、确定性业务失败和意外异常只保存稳定错误码与安全消息，failed 行清空全部 3.0/4.0 业务载荷，不落部分 facts、criteria 或审计残片。旧 1.0—3.0 读取与既有 Screening 兼容判断暂时保留，只为隔离 7R4-D 与 7R4-E；生产 API 已没有新的 3.0 生成入口。

本批没有修改 Screening 的 fact 评价合同、React、旧 migration、冻结 JD 或真实质量结果。计划确认后对既有 Screening 协调器仍明确发送“计划尚不可供旧合同筛选”的信号，避免在 7R4-E 前把 4.0 ready 错送进 3.0 Screening。

### 22.2 自动化、并发、数据库与调用结果

- 7R4-D 专项 14/14 passed：原 6 条合同红灯全部转绿，并新增 8 条 PostgreSQL/Fake/API 回归，覆盖 pending 落库、恰好 3 次正常业务调用、同输入幂等、公开备注排除、确认幂等、JD 变化、关闭岗位、非法 JSON 失败后重试、迟到响应和新输入失败保护。
- 独立 PostgreSQL 并发测试使用两个 `AsyncSession` 同时确认同一计划；两个调用都得到 `ready`，数据库最终只有一条 current ready 行。该测试同时验证 `FOR UPDATE` 串行化与确认幂等，不代表任意跨机故障都已覆盖。
- 7R4-A—7R4-D 后端合同为 73 passed；剩余 6 条失败全部属于尚未授权的 7R4-E。排除这 6 条预期红灯后，后端全量为 866 passed、408 subtests passed；3.0 计划读取与旧 Screening 隔离定向为 39 passed、5 subtests passed。
- 既有前端 44/44 passed；7R4-F 合同保持 2 passed、10 expected failed。Python 编译检查与 `git diff --check` 通过。
- 正常 4.0 生成恰好调用 Fake Adapter 3 次，确认调用 0 次 Adapter；本批真实 DeepSeek 调用为 0。
- 正式开发库保持 `current=head=c7d9e2f4a681`，`alembic check` 为 “No new upgrade operations detected”；本批没有新 migration。验证结束后 `jobs/applications/candidates/resumes/job_evaluation_plans/reports/screening_reports/screening_runs/stage_histories` 均为 0，测试没有遗留业务数据。

### 22.3 证明边界、风险与停止点

这些结果证明：4.0 纯生成结果可以安全进入 pending，HR 确认会重新核对当前 Job/合同/指纹并在事务中转 ready；并发确认、同输入重试、JD 变化、关闭岗位、迟到响应和生成失败都有可复现的数据库保护；公开备注不影响计划有效性；确认不会再次调用模型或修改事实。

它们不能证明：4.0 ready 已能进入 Screening、Screening 会逐 `fact_id` 评价、1.0—3.0 已被禁止新筛选、React 已提供确认交互、真实 DeepSeek 质量或阶段 7 已完成。当前主要风险正是既有 Screening 仍理解 3.0 items；若现在放行 4.0，会把 facts/criteria 当成旧事项，因此该切换必须留给 7R4-E 的 Schema/Service/事务测试一起完成。

7R4-D 已按门禁停止并在用户明确确认后进入 7R4-E；7R4-E 的实际结果记录在下一节。

## 23. 7R4-E 实施结果（2026-08-24）

### 23.1 修改边界与逐 fact 评价职责

本批把 Screening 后端从历史 3.0 `items` 切换到当前 4.0 `requirement_facts + evaluation_criteria`。只有当前、指纹一致且 HR 已确认的 4.0 `ready` 计划能进入队列；1.0—3.0 继续允许历史只读，但统一以 `plan_contract_outdated` 阻止新的 AI 初筛。`generating`、`pending_confirmation`、`failed`、`outdated` 分别保留独立等待原因，其中新增 `plan_pending_confirmation`，不会把待确认计划误当成可筛选计划。

筛选 Prompt 升级为 `screening_evaluation_v4`。模型逐条返回 `requirement_key=fact_id`；每个 fact 的原文来源、source unit、来源字段和 priority 在模型调用前再次由 Service 核对。`EvaluationCriterion` 只作为展示分组发送给模型，不产生 criterion 分数、权重或阈值，也不参与 Python 求和。逐项输出和报告读取容量从旧 30 条放宽到 512 条技术上限，31 条事实可完整通过，513 条才在 Schema 层拒绝。

报告仍绑定实际 `job_evaluation_plan_id` 并保存逐 `fact_id` 评价。运行完成前会重新核对当前 Resume、4.0 JD 快照和计划指纹；迟到响应不能替换当前成功报告。旧报告不会删除或自动重评：如果它绑定旧计划，只增加 `evaluation_plan_changed`，不会因 3.0/4.0 指纹算法不同而误加 `jd_changed`。

本批修改范围位于 `API 协调 → Screening Schema → Screening Service → Prompt/Adapter → ScreeningRun Model → PostgreSQL`；没有修改 React、JobEvaluationPlan 4.0 生成合同、事实/维度内容、冻结样本、旧 migration 或历史质量结果，也没有调用真实 DeepSeek。

### 23.2 migration、自动化与调用结果

- 新 revision `d6f4a2b8e913` 只替换 `screening_runs` 等待原因检查约束，使 PostgreSQL 接受 `plan_pending_confirmation`。downgrade 会先检查是否已有该状态，存在时以 `STAGE7_SCREENING_V4_DOWNGRADE_BLOCKED` 在 DDL 前受控阻止。
- 正式开发库在业务表为空时完成真实 `d6f4a2b8e913 -> c7d9e2f4a681 -> d6f4a2b8e913` 往返；最终 `current=head=d6f4a2b8e913`，`alembic check` 返回 `No new upgrade operations detected`，`jobs/applications/job_evaluation_plans/screening_runs/screening_reports` 均为 0。
- 7R4-A—E 核心后端合同为 82/82 passed；筛选相关定向修正后全部通过。新增运行时测试明确覆盖旧 1.0/2.0/3.0 拦截、31 条逐 fact 容量、513 条上限、不完整 criterion 归组和不可追溯 fact 在 Adapter 调用前失败。
- 后端全量为 884 passed、408 subtests passed；另有既有 PyPDF2 弃用 warning 和一次测试清理阶段的 asyncpg cancel RuntimeWarning，没有断言失败。
- 既有前端为 44/44 passed；TypeScript 严格检查和 Vite 5.4.21 生产构建通过，转换 3121 个模块。7R4-F 合同保持 2 passed、10 expected failed，证明 React 批次没有被提前实施。
- Python 全量编译与 `git diff --check` 通过；筛选 Prompt/Service 扫描没有 criterion weight/score/threshold 或 Python 加权逻辑。全部 AI 行为验证使用 Fake Adapter，真实 DeepSeek 调用 0 次。

### 23.3 证明边界、风险与停止点

这些结果证明：后端只会消费合法当前 4.0 ready 计划；待确认和旧合同不会误入队列；模型输入、输出键、报告持久化与过期判断已经转为逐 fact；31+ 不再被旧 30 条上限拒绝；等待原因约束可以在真实 PostgreSQL 安全往返；失败、迟到响应和历史报告继续受保护。

这些结果不能证明：React 已展示 criteria/facts 或提供确认按钮，真实 DeepSeek 能稳定生成合格报告，4.0 质量门槛已经通过，或真实浏览器端到端流程已经验收。当前剩余风险是前端仍使用 3.0 类型和展示结构；在 7R4-F 完成前，用户界面不能完整操作 4.0 计划。

7R4-E 已按门禁停止并在用户明确确认后进入 7R4-F；7R4-F 的实际结果记录在下一节。

## 24. 7R4-F 实施结果（2026-08-24）

### 24.1 修改边界与前端职责

本批只接通“React 页面 → 前端 Service → 既有 `/api/v2` 计划读取/确认与报告读取接口”的 4.0 交互。前端类型和 API 映射现可完整读取 `pending_confirmation`、五类 warning、`RequirementFact`、`EvaluationCriterion`、coverage review 和 generation audit；确认按钮只向 `/jobs/{job_id}/evaluation-plan/confirm` 发送无正文 POST，不允许从浏览器提交或修改事实、维度和分数。

评价计划抽屉按 criterion 组织展示，但每条 fact 保持独立：HR 可以看到 fact ID、分类、程序计算的 priority、主原文和全部多来源原文。`pending_confirmation` 显示受控确认动作和等待说明；`ready` 与 1.0—3.0 历史计划保持只读；JD 合同过期时只能按五段式新规则生成 4.0。视觉上沿用现有 Ant Design 蓝灰体系，只新增一条聚焦的“事实证据轨道”，帮助 HR 从展示维度回到原始 JD 证据，没有扩展为全站重设计。

报告抽屉在报告绑定的 4.0 计划可读取且 ID 一致时，按 criterion 分组、逐 fact 展示单项分数、理由、简历证据和原始 JD 来源；criterion 本身没有分数、权重或阈值。历史报告或旧计划不可读取时继续诚实使用原有扁平回退，不拿当前新计划冒充旧报告。

本批链路止于前端到既有 API。没有修改后端生产 Schema、Service、Model、migration 或 PostgreSQL 数据，没有新增计划编辑、同输入随机重生成、criterion 评分、自动筛选决策或真实 DeepSeek 调用。

### 24.2 自动化、构建、数据库与调用结果

- 7R4-F 前端合同由基线 2 passed、10 failed 转为 12/12 passed；包含 Service 映射、无正文确认请求、待确认状态、五类 warning、criteria/facts、多来源、历史只读和逐 fact 报告。
- 前端全部 Node 合同为 56/56 passed；TypeScript 严格检查和 Vite 5.4.21 生产构建通过，转换 3121 个模块。
- 受影响后端 PostgreSQL/API/Service 回归为 51 passed，另有 5 个 unittest subtests passed 和 1 条既有 PyPDF2 弃用 warning。本批未修改后端，因此没有重复冒充执行 7R4-E 已完成的后端全量 884 passed。
- 正式开发库只读复核为 `current=head=d6f4a2b8e913`；验证结束后 `jobs/applications/job_evaluation_plans/screening_runs/screening_reports` 均为 0，没有写入或遗留业务夹具。
- `git diff --check` 通过；静态扫描未发现 `criterionScore`、`criterionWeight`、`publicNotes`、计划编辑入口或 `dangerouslySetInnerHTML`。
- 所有页面合同和后端协调验证都使用固定夹具或 Fake Adapter；真实 DeepSeek 调用 0 次。

### 24.3 证明边界、风险与停止点

这些结果证明：程序层面的前端类型、API 映射、确认请求、待确认状态、五类 warning、criteria/facts、多来源原文、历史只读和逐 fact 报告已经与 4.0 后端合同一致；确认动作不会把计划正文发回服务端；criterion 只负责展示分组，不会被误当成评分项。

这些结果不能证明：三档真实浏览器下的尺寸、焦点、键盘、滚动、轮询停止和整页溢出已经验收，也不能证明真实 API 页面主链或真实 DeepSeek 的计划/报告质量。浏览器与真实 PostgreSQL/API 全链仍属于 7R4-J；真实模型质量只允许在后续单独授权的 7R4-H/I 中验证。

当前剩余风险主要是历史计划与报告组合很多：若报告绑定的计划不可读取或 ID 不一致，页面会有意回退到旧的逐项显示；这能避免错误关联，但仍需 7R4-J 用真实浏览器状态矩阵确认交互细节。若待确认按钮返回冲突，应首先检查岗位是否关闭、JD 或计划指纹是否已变化，而不是在前端绕过后端门禁。

7R4-F 到此停止。唯一下一步是等待用户明确确认 7R4-G 零调用门禁；不得自动进入 7R4-G，更不得进入 7R4-H—J、调用真实 DeepSeek 或进入阶段 8。

## 25. 7R4-G 实施结果（2026-08-25）

### 25.1 修改边界与运行器职责

本批补齐的是“质量夹具 → Prompt/Adapter 合同 → 4.0 Service 实际审计 → 统计与硬门禁”，并用 Fake 把该链延伸到 API/PostgreSQL；没有修改生产 Prompt、Schema、Service、Model、API、migration 或 React。冻结 JD 原文和人工标签文件没有修改，计划质量继续复用既有 20 份 J5 夹具及其 SHA-256。

- `scripts/stage7_7r4_quality_contract.py` 统一保存冻结样本 ID、分母、调用预算、候选模型/费用输入、历史结果清单、新 4.0 结果路径、只写新文件规则和定向硬门禁。
- `scripts/run_stage7_7r4_plan_quality.py` 提供计划 dry-run、Fake 正常/局部修复以及后续 7R4-H 才可授权的定向/正式入口。正式模式先读取并完整校验固定路径下的新 4.0 定向结果，之后才允许创建 Adapter；没有 `skip gate` 或自定义定向结果路径参数。
- `scripts/run_stage7_7r4_report_quality.py` 只实现本批允许的报告零调用准备，固定报告样本、人工标签分母、三次稳定性预算和 7R4-H 正式计划结果前提，不产生报告质量结论。
- `backend/tests/test_stage7_7r4g_quality_runner.py` 验证冻结分母、dry-run、预算、三/四调用、基础设施重试与内容错误分离、硬门禁和历史路径隔离。
- `backend/tests/api/test_stage7_7r4g_fake_api_postgres.py` 使用真实 AsyncSession/API/Service/PostgreSQL 和 Fake Adapter 验证等待计划、`pending_confirmation → ready`、逐 `fact_id` 报告、内容错误不重试及事务回滚后零夹具。

独立新路径固定为：

- `2026-08-25-stage7-7r4h-plan-quality-targeted-results.json`
- `2026-08-25-stage7-7r4h-plan-quality-formal-results.json`
- `2026-08-25-stage7-7r4i-report-quality-targeted-results.json`
- `2026-08-25-stage7-7r4i-report-quality-formal-results.json`
- `2026-08-25-stage7-7r4i-report-quality-formal-results.md`

写入函数只接受上述登记路径且拒绝覆盖已存在文件。dry-run 只读校验 3.0 的 7R-F、step9 和既有质量 JSON/Markdown 的 hash，不写这些文件，也不创建新的正式结果文件。

### 25.2 冻结样本、预算与 dry-run 结果

计划 dry-run 实际固定正式样本 J5-01—J5-20，定向样本 J5-03/J5-07/J5-14/J5-17/J5-19/J5-20，冻结 SHA-256 为 `23651a92bb68602f096cf30519d5c11cd2ce6e724950f158587ba201e41fdfe0`。统计分母为 245 条人工 facts、97 条明确必测；定向分母为 80/23；正式与定向 source units 分别为 255/90。`public_notes` 在全部输入中继续排除，4.0 Schema、指纹、破坏性合同、四角色 Prompt 版本和 16,000 output tokens 边界均完成检查。

每份正常计划固定 3 次业务调用，每份最多一次局部修复后为 4 次；每个业务调用遇到基础设施瞬时错误最多额外尝试 1 次。因此：

| 轮次 | 正常业务调用 | 含局部修复最大业务调用 | 含基础设施重试最大 API 尝试 |
| --- | ---: | ---: | ---: |
| 6 份定向 | 18 | 24 | 48 |
| 20 份正式 | 60 | 80 | 160 |
| 两轮合计（均另行授权时） | 78 | 104 | 208 |

当前配置候选模型记录为 `deepseek-v4-flash`，temperature=0.1、JSON object、thinking disabled、SDK 自动重试 0、单次最大输出 16,000 tokens。2026-08-25 根据 DeepSeek 当前官方 API 名称，将已退役、此前指向 V4 Flash 非思考模式的兼容别名 `deepseek-chat` 明确改为正式模型 ID `deepseek-v4-flash`；这不改变原模型档位或思考模式。它仍只是 7R4-H 费用估算输入，不是本批对真实模型的授权；官方 cache hit/cache miss/output 单价保持空值，并明确要求 7R4-H 前重新查询和由用户确认。

计划与报告 dry-run 的共同结果为：真实模型调用 0、正式质量结果写入 0、真实 Adapter 未实例化、真实 API Key 不是运行前提、历史结果 hash 前后不变、新正式路径当前均不存在。报告侧另固定 SR01—SR20、high/partial/low 人工标签分母 8/6/6、每组 3 次和正式 60 次业务调用（含基础设施重试最大 120 次尝试）；失败样本继续留在统计分母中。

### 25.3 Fake 调用、硬门禁与 API/PostgreSQL 全链

Fake 正常分支从生产 Service 的 `generation_audit` 实际得到 3 次 Adapter 尝试、3 次业务调用、0 次内容修复、0 次基础设施重试，角色顺序为 fact extraction → coverage review → criterion grouping。Fake 局部修复分支实际得到 4/4/1/0，角色顺序在 coverage review 后只增加一次 local repair。基础设施超时样例实际为 4 次 Adapter 尝试、3 次业务调用、0 次内容修复、1 次基础设施重试。

认证、非法 JSON、Schema 版本和非法 fact 原文引用在计划侧均只尝试 1 次，审计为 1 次业务调用、0 次内容修复、0 次基础设施重试；报告侧不可定位证据和敏感属性安全错误也各只尝试 1 次。它们不会被错误当成网络抖动重复请求。

正式 20 份门禁只接受固定新路径上的 `stage=7R4-H`、`result_kind=plan_quality_targeted`、`status=formal`、Schema 4.0、冻结 SHA、完整且有序的 6 个定向 ID、6/6 样本合同、80/23 与 90 source units 分母，以及两个明确 `true` 的通过标记。定向与正式还必须保持同一个 `deepseek-v4-flash`、`thinking disabled`、temperature/JSON/16,000 tokens/SDK 重试配置和四个 Prompt 版本；切换 Pro、thinking 或 Prompt 后，旧定向结果不能放行新配置。门禁还会从实际分子/分母重新计算主要语义召回、明确必测召回、source review、来源追溯、priority、criterion 覆盖和 warning 命中率，并逐项检查新增要求、缺失多来源、错误合并、明显重复、背景/公开备注污染、宣传福利误识别都为 0；结果文件只写一个伪造的 `1.0` 或 `targeted_gate_passed=true` 无法绕过。定向结果缺失、失败、3.0 版本、模型/参数/Prompt 版本、样本不一致、分母/分子异常或历史路径均受控拒绝；测试把 Adapter factory 设为一旦调用即失败的哨兵，证明阻断发生在任何模型实例化/调用之前。J5-19 即使预期为 0 facts，也必须从事实提取原始响应证明全部 source units 已审阅；发生技术重试时只取成功的 fact extraction 尝试。

受控 PostgreSQL 测试从 API 触发缺计划的 `waiting_plan/plan_missing`，Fake 计划经过 3 次实际调用落为 `pending_confirmation`，筛选等待原因转为 `plan_pending_confirmation`；无正文确认后计划转为 `ready`，原运行入队并生成逐 `fact:0001` 报告。计划确认没有增加 Adapter 调用，Screening 使用 1 次 Fake 调用，Application 的 `recruitment_stage=applied` 与 `hr_decision=pending` 未被 AI 修改。整个夹具位于外层事务，结束后另开连接确认九张相关业务表计数与测试前完全一致。

### 25.4 自动化、数据库、证明边界与停止点

- 7R4-G 运行器合同：11 passed；API/PostgreSQL Fake 集成：1 passed。
- 2026-08-25 模型别名兼容修正后，配置、计划/筛选 Adapter 与 7R4-G 门禁定向为 36 passed、29 subtests passed；dry-run 为 `deepseek-v4-flash / thinking disabled / 0 次真实调用 / 0 次正式写入`。
- 计划生成、Screening、API 和 migration 受影响定向：129 passed、22 subtests passed，1 条既有 PyPDF2 弃用 warning。
- 后端全量：896 passed、408 subtests passed，模型别名修正后最终重跑用时 49.63 秒；另有既有 PyPDF2 弃用 warning和旧 API 测试清理阶段的 asyncpg cancel RuntimeWarning，没有断言失败。
- Alembic 代码 head 与正式 PostgreSQL current 均为 `d6f4a2b8e913`；最终 `jobs/candidates/resumes/applications/job_evaluation_plans/screening_runs/screening_reports/stage_histories/reports` 均为 0，没有遗留业务夹具。
- `git diff --check` 通过。冻结夹具文本未修改，历史结果未覆盖、未重命名、未删除，新正式结果文件未创建。
- 本批没有修改前端，因此没有重复浏览器、TypeScript 或 Vite 验收；7R4-F 的前端历史基线只作为上游证据，不冒充本轮重跑。
- 真实 DeepSeek 调用最终为 0。

这些结果能证明：4.0 样本选择和统计分母不会静默漂移；dry-run 可以在无 Key、无真实 Adapter、无结果写入下完成配置/版本/预算/路径预检；业务调用、内容修复和基础设施重试是三套独立实际计数；定向失败或不属于新 4.0 的结果不能通过参数绕过并启动正式调用；Fake 能衔接现有 API/Service/PostgreSQL 的待确认、确认和逐 fact 链路；3.0、step9 与既有结果继续隔离。

这些结果不能证明：`deepseek-v4-flash + thinking disabled` 已经通过 7R4-H 真实定向质量，V4 Pro 或 thinking 模式一定不需要，当前官方单价或费用上限已经确认，真实 DeepSeek 能在 6/20 份 JD 上满足质量门槛，报告 20 组三次稳定性合格，或真实浏览器/API 端到端验收完成。若后续门禁异常，先检查定向结果路径、版本、冻结 SHA、样本顺序和统计分母；若调用数异常，分别检查 generation audit 的 business/content repair/infrastructure retry；若数据库状态异常，检查外层事务、计划确认通知和 Screening waiting reason，不得通过放宽门槛或改样本文本解决。

7R4-G 到此完成并停止。唯一下一步是等待用户单独确认 7R4-H 的真实模型、官方费用和定向/正式调用上限；未经确认不得执行 7R4-H，不得进入 7R4-I—J，不得调用真实 DeepSeek，也不得进入阶段 8。

## 26. 7R4-H 付费预检与审计补充顺序（2026-08-25，已确认）

### 26.1 为什么不能直接开始付费调用

7R4-H 首次付费预检完成了官方价格、模型配置、dry-run、冻结样本、结果路径、历史 hash、Alembic 和业务表计数检查，没有发起真实调用。预检发现两个必须先处理的事实：

1. DeepSeek 官方已经启用工作日峰谷价；`deepseek-v4-flash` 的高峰单价是空闲时段的 2 倍。原 7R4-G 只保留空价格输入，不能冒充本轮最新官方价格。
2. 当前计划质量运行器只保存总 input/output tokens 和成功内容，没有完整保存 `finish_reason`、cache hit/cache miss tokens、逐 attempt 费用；非法 JSON/Schema 等响应在 Adapter 抛错后也没有原始内容可供复核。因此当前结果文件不能满足本轮已经确认的逐调用审计和失败证据合同。

用户随后明确提出“先补齐审计，再开始测试”，并取消本次 6 份定向轮的金额上限。金额上限取消不取消调用次数、样本、模型、参数、内容错误不重试和失败后停止等安全边界，也不授权正式 20 份。

### 26.2 修订后的固定子批次

7R4-H 拆成三个不能连续越过的子批次：

| 子批次 | 唯一目标 | DeepSeek | 完成后停止点 |
| --- | --- | --- | --- |
| 7R4-H0 | 补齐质量运行器逐 attempt 审计与费用记录 | 0 次 | 报告自动化结果，等待 7R4-H1 确认 |
| 7R4-H1 | 只执行 J5-03/07/14/17/19/20 六份定向真实质量 | 允许，最多 24 次业务调用、48 次 API 尝试 | 无论通过或失败都停止，不执行正式 20 份 |
| 7R4-H2 | 正式 20 份计划质量 | 本轮不授权 | 只有 H1 门禁通过且用户另行授权后才可讨论 |

### 26.3 7R4-H0：逐 attempt 审计补齐

- 唯一目标：确保每一笔真实请求都有可核对的“调用小票”，内容失败也保留原始证据。
- 通俗解释：先补齐第几次调用、为什么停止、哪些 token 走缓存、花费多少以及失败时模型原话，再允许付费考试。
- 允许修改：`scripts/run_stage7_7r4_plan_quality.py`、`scripts/stage7_7r4_quality_contract.py`、`backend/tests/test_stage7_7r4g_quality_runner.py`，以及仅在无法通过客户端记录层取得元数据时才允许的最小 `backend/app/adapters/job_evaluation_plan.py` 审计字段；同步本文和 `PROJECT_STATE.md`。
- 链路位置：Prompt/Adapter 响应元数据 → 质量运行器 → 结果 JSON；不进入前端、API、业务 Schema、Service、Model 或 PostgreSQL。
- 禁止修改：四个生产 Prompt、4.0 AI/业务 Schema、生成 Service、事实/criterion 规则、质量门槛、冻结 JD/人工标签、Model、migration、API、React 和历史结果。
- 每个实际 attempt 必须记录：`case_id`、role、attempt number、实际 model、thinking、temperature、JSON 模式、max tokens、Prompt version、input tokens、cache-hit input tokens、cache-miss input tokens、output tokens、finish reason、duration、是否基础设施重试、错误码、原始响应和按本轮官方单价计算的费用估算。
- 原始响应规则：API 已返回响应时，即使非法 JSON、Schema 或业务内容失败也必须保留原始内容；网络/超时等未收到响应时明确记录 `raw_response=null`，不得伪造。
- 价格规则：真实调用前仍须重新查询官方 cache hit/cache miss/output 的空闲与高峰单价、检查时间和适用时段，并写入结果。7R4-H1 不设金额硬上限，但费用必须逐 attempt 和汇总记录。
- 调用门禁：H0 的所有测试、Fake 和 dry-run 必须是 0 次真实调用、0 个正式结果写入、0 个真实 Adapter 实例化；不得以 API Key 是否存在作为 dry-run 前提。
- 自动化：新增成功、`finish_reason=length`、cache hit/miss 混合、非法 JSON、Schema 失败、内容错误不重试、一次基础设施重试、费用汇总、48 尝试硬停止、旧结果隔离和拒绝覆盖测试；运行配置/Adapter/质量运行器定向、受影响后端回归和 `git diff --check`。
- 完成标志：Fake 响应能证明所有字段来自实际响应/异常记录而不是写死；失败原始证据可读取；费用分项与汇总可重算；0 调用/0 写入门禁保持有效。
- 失败处理：缺口仍在客户端记录层就返回 H0，不修改 Prompt/Schema/Service，也不开始付费测试。
- 停止点：H0 验证完成后必须停止并报告；不得在同一小步自动执行 H1。

### 26.4 7R4-H1：六份定向真实质量

- 唯一目标：使用 `deepseek-v4-flash + thinking disabled` 对固定六份样本执行一次新的 4.0 定向真实验证。
- 固定模型参数：temperature `0.1`、`response_format=json_object`、单次 max tokens `16,000`、SDK 自动重试 `0`。
- 固定样本与顺序：J5-03、J5-07、J5-14、J5-17、J5-19、J5-20；冻结 SHA、80 条人工 facts、23 条明确必测和 90 个 source units 分母保持不变。
- 调用上限：正常 18 次业务调用；有局部修复最多 24 次业务调用；每个业务调用最多额外 1 次基础设施重试；全部最多 48 次 API 尝试。达到任一上限立即停止。
- 费用边界：本次定向不设置美元或人民币金额硬上限；仍必须在调用前记录官方峰谷价，并按实际 cache hit/cache miss/output tokens 逐次计算和汇总费用。
- 禁止：内容错误重试、额外试跑、A/B、补跑、挑选最好响应、删除失败样本、修改冻结样本/Prompt/Schema/Service/门槛，以及创建正式 20 份结果。
- 结果：只允许创建固定的新 4.0 定向结果文件且拒绝覆盖；6/6 和聚合门槛按第 15.2 节从实际分子/分母重算。
- 完成/失败/停止：无论 `targeted_gate_passed` 为 true 或 false，都保留全部样本和证据并停止。通过只允许后续讨论 H2，不等于 H2 已获授权；失败则返回具体责任层讨论。

### 26.5 本补充的确认门禁

用户已于 2026-08-25 明确确认 7R4-H0，并且本轮只能实施 H0；完成并报告后再次停止。未经用户对 H1 的独立确认，不得调用真实 DeepSeek。正式 20 份、7R4-I、7R4-J 和阶段 8 均不在本次授权内。

## 27. 7R4-H0 实施结果（2026-08-25）

### 27.1 实际修改与链路位置

- `backend/app/adapters/job_evaluation_plan.py` 只补充响应审计元数据：成功或已经收到响应后再失败时，均保留实际 model、`finish_reason`、总 input、cache hit、cache miss、output tokens 和原始内容。非法 JSON、Schema 错误与 `length` 中断不再因抛错丢失模型原话。
- `scripts/run_stage7_7r4_plan_quality.py` 增加跨六份样本共享的逐 attempt ledger（审计账本）。每次 Adapter 尝试统一登记样本、角色、全局/样本内/业务调用编号、模型参数、Prompt 版本、耗时、重试属性、错误、原始响应和费用；24 次业务调用、48 次 API 尝试以及每个业务调用最多一次基础设施重试都在下一次调用前阻断。
- `scripts/stage7_7r4_quality_contract.py` 增加官方价格快照、cache hit/cache miss/output 分项费用重算与定向结果逐 attempt 门禁。真实模式必须显式确认没有金额上限，并拒绝缺字段、超过 1 小时或明显来自未来的价格检查时间；历史结果回放只校验当轮已保存快照，不用今天的价格篡改过去费用。
- `backend/tests/adapters/test_job_evaluation_plan_adapter.py` 与 `backend/tests/test_stage7_7r4g_quality_runner.py` 覆盖成功、`length`、非法 JSON、4.0 Schema 失败、cache 分账、费用重算、一次技术重试、第三次重试阻断、24/48 上限、审计篡改拒绝、旧结果隔离和拒绝覆盖。
- 本批链路仍是“Prompt/Adapter 响应元数据 → 质量运行器 → 新结果 JSON”。没有修改四个 Prompt、4.0 Schema、Service、Model、migration、API、React 或 PostgreSQL，也没有创建任何质量结果文件。

### 27.2 实际验证

- Adapter 与质量运行器专项：`26 passed + 7 subtests`；受影响配置、Adapter、4.0 纯生成和质量运行器回归：`60 passed + 23 subtests`。只有既有 PyPDF2 弃用 warning，没有失败。
- `py_compile` 覆盖 Adapter、质量合同、计划质量运行器及其测试；`git diff --check` 通过。
- 计划 CLI dry-run：真实模型调用 `0`、正式结果写入 `0`、真实 Adapter 未实例化、API Key 不是前提。Fake normal/repair 分别实际走 3/4 次 Fake attempt，真实调用均为 `0`。
- 新 4.0 定向与正式计划质量结果路径均不存在；测试确认历史结果 hash 不变、旧路径不可写、新路径存在时不可覆盖。

### 27.3 能证明、不能证明与停止点

这些结果证明 H1 运行器已经能为每次真实 API 尝试开出可重算的“调用小票”，模型返回非法 JSON/Schema 或被 token 上限截断时也能保存原始证据；调用次数和重试上限不依赖金额上限。它也证明 H0 没有花费模型费用、没有污染正式结果和历史结果。

这些结果不能证明 DeepSeek 真实响应一定包含完整 cache 分账，不能证明六份定向质量合格，也不能证明本轮官方价格在 H1 开始时仍未变化。若真实响应缺少计费字段，逐 attempt 会明确标为不可完整计价且定向门禁不通过；若价格快照过期，真实 Adapter 创建前就会停止；若模型内容质量失败，保留原始响应并返回 Prompt/Schema/Service 对应责任层讨论，不允许偷偷补跑。

7R4-H0 到此完成并停止。唯一下一步是等待用户独立确认 7R4-H1；H1 只允许六份固定定向样本，无论通过或失败都停止，不执行正式 20 份。

## 28. 7R4-H1 六份定向真实质量结果（2026-08-25）

### 28.1 调用、费用与不可变证据

用户于 2026-08-25 独立确认 7R4-H1。运行前重新核对 DeepSeek 官方价格页、模型列表、工作区、新结果路径、历史结果 hash、Alembic 和业务表基线；北京时间 12:23 属于空闲时段，官方 `deepseek-v4-flash` 每百万 token 美元单价记录为 cache hit `$0.007`、cache miss `$0.22`、output `$0.66`，高峰单价为 `$0.014/$0.44/$1.32`。API Key 认证和模型可用性检查通过，未输出 Key。

- 只执行 J5-03、J5-07、J5-14、J5-17、J5-19、J5-20，模型 `deepseek-v4-flash`、thinking disabled、temperature `0.1`、JSON object、max tokens `16,000`、SDK 自动重试 `0` 均未改变。
- 实际 Adapter/API attempt 为 `16`：fact extraction 6 次、coverage review 5 次、criterion grouping 5 次。J5-19 按预期得到 `no_facts`，第一次事实提取后合法结束，因此没有继续进行无意义的 review/grouping；其余五份各 3 次。没有局部修复和基础设施重试，16 次全部 `finish_reason=stop`，全部有原始响应和完整计费 token。
- 实际总 input tokens `31,946`，其中 cache hit `3,584`、cache miss `28,362`；output tokens `13,233`。逐 attempt 分项和总费用均从保存的官方价格快照重算一致，估算总费用 `$0.014998508`；它是 API token 估算，不冒充最终账单。
- 新结果只创建 `docs/stages/stage7/2026-08-25-stage7-7r4h-plan-quality-targeted-results.json`，大小 `522,918` bytes，SHA-256 `ada6cbc91c21e7f4f341eee587259676579c9c2770af3a220277ff32a5e47a6f`。历史结果 hash 不变，正式 4.0 结果未创建，数据库九张业务表运行前后均为 0。

### 28.2 质量结论

`targeted_gate_passed=false`、`quality_conclusion_allowed=false`，逐样本合同只有 `4/6`：J5-03、J5-07、J5-19、J5-20 通过；J5-14、J5-17 失败。因此正式 20 份严格阻断。

通过项同样必须保留：人工主要事实召回 `80/80 = 100%`，明确必测事实 `23/23 = 100%`，source unit 审阅 `90/90 = 100%`；83 个生成 facts 的原文追溯、priority 一致和 criterion 唯一覆盖均为 `100%`。正常输出 `4/4`、边界结果 `2/2` 正确；擅自新增、错误合并、明显重复、背景/public notes 污染和宣传福利误识别均为 0。

两个失败责任不同：

1. J5-14 的“客户访谈”分别出现在两条职责、必备要求和加分项。模型抽成了四条单来源事实，coverage review 仍返回 passed，没有形成合同要求的至少两来源事实，因此 `source_merge_failure_count=1`。这是 fact extraction/coverage review 的跨 source unit 语义合并缺口。
2. J5-17 在 `candidate_requirements` 中写“SQL 数据核查经验优先”，在 `preferred_qualifications` 中写“必须具备审计项目经验”。实际 warnings 为空，没有命中预期 `conflicting_requirements`，所以 warning 命中为 `1/2 = 50%`。这暴露当前确定性 warning 只在同一 fact 已经合并了不同优先级来源时触发，尚不能独立识别字段内“必须/优先”信号与字段语义冲突。

### 28.3 新发现的审计合同缺口与停止点

H0 把定向 attempt 下界写成 18，但 J5-19 是事先固定的 `no_facts` 边界，按 Service 合同只允许第一次提取后停止，因此本轮合法基线实际是 16。结果文件本身完整保存了 16 次真实证据、费用和停止原因，质量失败也无需作为正式门禁输入；但 `validate_plan_attempt_audit()` 的 `18—48` 下界不能正确审计这种预期边界结果，后续复用前必须通过新的已确认整改批次修正，不能靠补两次无意义调用凑数。

这些结果不能证明正式 20 份质量，也不授权立即修改 Prompt/Service、覆盖结果或重跑六份。7R4-H1 到此失败并停止。下一步必须先和用户讨论整改范围、实施顺序和验收方式；未经新的明确确认，不得进入正式 20 份、7R4-I、7R4-J 或阶段 8。

## 29. 7R4-H1 失败后的整改与复验顺序（2026-08-25，HR0 已完成）

### 29.1 已确认的业务含义与整改原则

用户已认可以下整改方向，但本节写入前尚未授权直接修改代码：

1. “合并”不是把意思接近的 JD 内容改写成一段，也不是把相关 facts 合成一个大项；只有多个 source units 重复表达同一条、可以独立评价的能力/经验/职责，而且能够由同一类简历证据证明、合并后不损失独立评价价值时，才把它们放进同一条 `RequirementFact.sources`。
2. `EvaluationCriterion` 继续只是展示文件夹：相关但可分别评价的 facts 可以归入同一 criterion，每条 fact 仍必须且只能出现一次，criterion 不打分、不加权、不合并或改写 facts。
3. 跨 source unit 的语义等价由模型按明确合同判断；程序不得仅因出现“数据、项目、客户”等相同词就自动合并。原文定位、字段 priority、措辞/字段冲突、角色顺序、次数和上限由程序确定性校验。
4. J5-14 的合同不是强制四处“客户访谈”全部合并，而是至少形成一条由两个及以上真实来源共同支持的客户访谈 fact；不同结果如问题定义、版本计划如果仍有独立评价价值可以保留为其他 facts。
5. J5-17 的 SQL 数据核查与审计项目经验不是同一事实，不得为了产生 warning 而合并。warning 来自字段固定 priority 与原文“必须/优先”等强弱信号冲突，程序只提醒 HR，不改 JD、字段、fact 或 priority。
6. 当前 H1 结果文件、冻结六份 JD、80/23 人工标签、90 source units 和质量门槛都是不可变证据。整改不得覆盖、删除、改写或把 `4/6` 伪造成通过。

本轮只新增两个不能连续越过的子批次：

| 子批次 | 依赖 | 唯一目标 | 真实 DeepSeek | 完成后停止点 |
| --- | --- | --- | ---: | --- |
| 7R4-HR0 | 本节获用户确认 | 修复同事实多来源复核、优先级信号 warning 和逐样本调用审计 | 0 次 | 报告代码/Fake/回归结果，等待 HR1 单独确认 |
| 7R4-HR1 | HR0 完成且用户另行确认模型、价格和调用边界 | 用新 Prompt 对完整六份重新做一次定向真实验证 | 允许，受本节上限约束 | 无论通过或失败都停止；不执行正式 20 份 |

### 29.2 7R4-HR0：零调用整改

#### 29.2.1 唯一目标与通俗解释

- 唯一目标：让模型先看完整份 JD，再合并同一事实的多处原文；让独立 reviewer 必须检查“该合并的是否被拆开”；让程序稳定识别字段与“必须/优先”措辞冲突；让调用审计按每份样本实际业务结果判断，而不是靠错误的全局 18 次下限。
- 通俗解释：模型负责判断“是不是同一件事”，程序负责判断“字段和必须/优先有没有写反”，复核模型负责找漏合并，审计器负责检查每份样本有没有走对步骤。

#### 29.2.2 允许修改的文件与链路位置

- 允许修改 `backend/app/prompts/job_evaluation_plan.py`：只把 fact extraction 和 coverage review Prompt 升为 v2；local repair 与 criterion grouping Prompt 保持原版本，除非实现证明现有输入无法消费合法 `missing_source_merge`，此时必须返回本文重新讨论，不能自行扩展。
- 允许修改 `backend/app/services/job_evaluation_plan_service.py`：增加 4.0 字段/措辞冲突 warning，并复用现有一次局部修复链；不得加入关键词自动语义合并。
- 允许修改 `scripts/stage7_7r4_quality_contract.py`、`scripts/run_stage7_7r4_plan_quality.py`：更新 Prompt 版本、16/58 正常基线、逐样本角色顺序、合法短路、费用/重试核对和新的 HR1 结果路径。
- 允许修改 `backend/tests/services/test_job_evaluation_plan_v4_generation_contract.py`、`backend/tests/services/test_job_evaluation_plan_service.py`、`backend/tests/test_stage7_7r4g_quality_runner.py` 及仅与上述文件直接相关的既有 Adapter/配置测试；同步本文与 `PROJECT_STATE.md`。
- 允许修改 `.env.example`：只把 `DEEPSEEK_MODEL`、`JOB_EVALUATION_PLAN_MODEL`、`SCREENING_EVALUATION_MODEL` 等仍残留的 `deepseek-chat` 示例同步为当前已确认默认值 `deepseek-v4-flash`，并允许增加直接相关配置测试，防止实际默认配置与示例配置再次分叉。该同步不得扩大到其他模型、其他业务功能或 Adapter 调用参数。
- 链路位置是“Prompt → Adapter 原样传递 → Service 事实/warning/局部修复 → 质量运行器”。在“前端 → API → Schema → Service → Model → PostgreSQL”主链中只进入 Prompt、Service 和链外质量工具；不修改前端、API、Pydantic 业务/AI Schema、SQLAlchemy Model、migration 或 PostgreSQL。

#### 29.2.3 Fact extraction v2 合同

模型输出前必须按固定步骤完成：

1. 先阅读全部 source units，不得按字段顺序看到一段就立即建立一条孤立 fact。
2. 找出重复表达同一能力、经验或职责的来源；判断它们是否可以由同一类简历证据证明，以及合并后是否仍保留所有独立评价价值。
3. 三项都成立时只生成一个 candidate，并把全部已确认来源放进 `sources`；仅主题相关、普通词相同、用途/结果/条件不同或可以分别满足时必须保留为不同 facts。
4. 输出前再次扫描是否存在表达同一事实的多个单来源 candidates；不得为了减少数量强行合并。
5. Prompt 使用通用正反例说明规则，不写死 J5-14 的完整答案，不改变“无 AI 标题、无改写 statement、只保存连续原文”的 4.0 合同。

#### 29.2.4 Coverage review v2 与局部修复合同

- reviewer 除现有漏事实、错误事实、disposition、原子性和分类检查外，必须逐 source unit/fact 检查：同一事实是否跨职责、必备、加分项重复出现；是否因字段不同被错误拆开；是否有来源没有挂到已有 fact；合并后是否会损失独立评价价值。
- 发现漏合并必须返回 `status=needs_repair`、`code=missing_source_merge`，引用全部相关 `source_unit_ids` 和 `fact_ids`；没有完成该检查不得返回 passed。
- 继续复用现有 `merge_into_fact_id`，只把 finding 涉及的来源并入已有 fact；最多一次局部修复，不重生成整份计划，不处理无关 source units，不无限重试。
- 修复后仍存在 unresolved finding、来源不存在、错误合并、重复来源或覆盖不完整时，使用现有稳定内容错误失败，不进入 criterion grouping，不通过改门槛继续。

#### 29.2.5 4.0 优先级信号 warning 合同

- 程序比较每个 source unit 的固定字段 priority 与原文显式强弱信号。`candidate_requirements` 中的“优先/加分/preferred/plus”、`preferred_qualifications` 中的“必须/至少/required/must”，以及其他字段/信号明确不一致时，产生受控 `conflicting_requirements` warning。
- warning 必须保存可定位 `source_unit_ids` 和相关 `fact_ids`，相同证据不得重复；继续按来源字段计算 fact priority，不按措辞擅自改 priority。
- 程序不得把不同事实合并来制造 warning，不修改 JD，不作招聘决定。必须覆盖中文、英文、大小写、正常同向表达和否定/非强度语境，防止简单子串误报。

#### 29.2.6 调用预算与逐样本审计合同

- 对门禁可通过的六份定向：五份正常计划各为 fact extraction → coverage review → 可选 local repair → criterion grouping；J5-19 `no_facts` 只能是 fact extraction → 合法停止。因此无内容修复基线是 `5×3+1=16`，每份正常计划最多一次修复时业务调用最多 `5×4+1=21`。
- 对未来正式 20 份：19 份正常计划加 J5-19，基线为 `19×3+1=58`，门禁可通过结果含内容修复最多 `19×4+1=77`。
- 安全硬上限不下调：定向仍为 24 次业务调用/48 次 API 尝试，正式仍为 80/160；每个业务调用最多额外一次相邻基础设施重试，内容错误不重试。
- validator 必须从 `cases.actual_outcome`、generation audit 和逐 attempt 角色顺序重算合法业务调用，不得只把全局下限机械改成 16。任何少跑 review/grouping、`no_facts` 后继续调用、repair 位置错误、第三次技术尝试、汇总与明细不一致都必须失败。

#### 29.2.7 结果路径、自动化和禁止范围

- 当前 `2026-08-25-stage7-7r4h-plan-quality-targeted-results.json` 永久保持原样。HR0 只登记新的复验路径 `docs/stages/stage7/2026-08-25-stage7-7r4hr1-plan-quality-targeted-revalidation-results.json`，write helper 必须拒绝历史路径、当前失败路径和已存在新路径。
- 必测正例：同一客户访谈经验在必备/加分来源中形成一个多来源 fact；reviewer 能返回 `missing_source_merge`，local repair 能并入已有 fact。
- 必测反例：客户访谈/PRD/版本复盘、普通“数据/项目”词、SQL 数据核查/审计项目经验保持独立；criterion 可以归组但不得替代 fact 合并。
- 必测 warning：J5-17 中文冲突、英文 required/preferred 冲突、正常同向表达、否定或非强度语境、去重和可定位证据。
- 必测审计：16 次正常定向、J5-19 单次合法停止、五份可选 repair 后最多 21 次、24/48 硬停止、基础设施单次重试，以及删减/乱序/伪造角色与汇总均被拒绝。
- 运行 Prompt/Service/质量运行器专项、受影响后端回归、dry-run/Fake、`py_compile` 和 `git diff --check`。HR0 必须为真实模型调用 0、新复验结果写入 0、真实 Adapter 未实例化、历史 hash 和当前 H1 SHA-256 不变。
- 配置测试必须核对 `backend/app/core/config.py` 的实际默认值、`.env.example` 的模型调用示例和质量合同的计划模型一致为 `deepseek-v4-flash`。历史真实结果文件中的 `deepseek-chat` 不得修改；仅作为普通 Schema 字符串样本、不参与模型调用的历史测试值可以保留，并在 HR0 报告中解释。
- 禁止修改冻结 JD、人工标签、质量门槛、4.0 Pydantic Schema、Adapter 调用参数、criterion 业务、Model、migration、API、React、PostgreSQL、当前/历史结果；禁止提前调用真实模型、只改测试期待值、按关键词自动合并或进入 7R4-I—J。

#### 29.2.8 HR0 完成、失败与停止点

- 完成标志：上述正反例和 warning/审计合同全部由实际测试通过；Prompt 版本与 dry-run/门禁同步；0 调用、0 复验结果写入和不可变证据 hash 被实际验证。
- 若 Prompt 合同仍不能让 reviewer 表达 `missing_source_merge`、现有 Schema/repair 无法安全处理、确定性 warning 存在无法排除的误报，返回 HR0 讨论是否需要扩 Coverage Schema；不得自行扩大到 Schema/数据库或付费试错。
- HR0 完成后立即停止并报告“修改、链路位置、验证、能证明/不能证明、剩余风险”。唯一下一步是等待用户独立确认 HR1。

### 29.3 7R4-HR1：完整六份重新真实验证

- 前置门禁：HR0 必须完成；用户必须另行明确确认 `deepseek-v4-flash + thinking disabled`、当时官方峰谷价格、不设置或设置何种金额上限，以及 24/48 安全硬上限。当前对第 29 节或 HR0 的确认不等于 HR1 付费授权。
- 固定样本/顺序仍为 J5-03、J5-07、J5-14、J5-17、J5-19、J5-20；冻结 SHA、80/23 人工标签、90 source units 和第 15.2 节门槛不变。不得只跑失败两份、改样本、改标签或删除失败分母。
- 固定实现为 fact extraction v2、coverage review v2、local repair v1、criterion grouping v1，以及 HR0 完成后的同一 Service/Schema；任何 Prompt/参数/模型再变化都使本次授权失效并返回预检。
- 只允许创建登记的新 revalidation 文件且拒绝覆盖；调用前记录最新官方价格/时段，逐 attempt 保存请求配置、model、token/cache、finish reason、耗时、重试、原始响应和费用。
- 预期无修复业务调用 16，门禁可通过结果含修复最多 21；安全硬上限仍是 24/48。达到硬上限、认证/配额/配置错误或结果路径异常立即停止；内容错误不重试，不额外试跑、A/B、补跑或挑最好响应。
- 通过必须同时满足：6/6；80/80、23/23、90/90；正常 4/4、边界 2/2；追溯、priority、criterion 覆盖和两个预期 warning 均为 100%；新增要求、漏多来源、错误合并、明显重复、背景/public notes 污染、宣传福利误识别均为 0。J5-14 至少一条客户访谈 fact 有两个及以上合法来源，J5-17 命中可定位 `conflicting_requirements`。
- 验证新结果可从原始明细重算全部分子/分母、角色顺序和费用；历史/current H1 hash、正式结果路径和数据库基线不变。无论通过或失败都同步证据并停止。
- HR1 通过只允许讨论原 7R4-H2 正式 20 份，不等于 H2 已授权；失败则返回具体 Prompt/Service/审计责任层。不得自动进入 H2、7R4-I、7R4-J 或阶段 8。

### 29.4 本节确认门禁

用户“按照方案来”的回复授权本轮把讨论结果落为第 29 节实施顺序，不视为已经授权修改代码或付费复验。用户明确确认本节或 `7R4-HR0` 后，下一轮只能实施零调用 HR0；完成并报告后再次停止。HR1、正式 20 份、7R4-I—J 和阶段 8 均需要各自后续授权。

### 29.5 7R4-HR0 实际完成记录（2026-08-25）

#### 29.5.1 实际修改与链路位置

- fact extraction 与 coverage review Prompt 已升为 v2：提取模型必须先阅读全部 source units，再用“同一条可独立评价事实、同一类简历证据、合并不损失独立评价价值”三项条件判断多来源；reviewer 必须复核 `missing_source_merge` 并同时返回全部相关来源和 facts。local repair v1 与 criterion grouping v1 保持原合同。
- 4.0 Service 增加字段/措辞确定性 warning：`candidate_requirements` 中的弱化信号和 `preferred_qualifications` 中的强化信号会生成一条去重后的 `conflicting_requirements`，保留相关 `source_unit_ids/fact_ids`。正常同向、否定和“优先处理、加分规则、PLUS operator、preferred name、required field”等非强度语境被排除；程序没有按普通关键词自动合并 facts，也没有改变 JD 或 fact priority。
- 计划质量合同和运行器改为逐样本审计：五份正常样本必须按 extraction → review → 可选 repair → grouping，J5-19 只能 extraction 后 `no_facts` 停止；定向合法业务调用为 16—21、正式为 58—77，安全硬上限仍为 24/48 和 80/160。少跑、乱序、no_facts 后继续、repair 错位、同一业务调用第三次技术尝试、逐 attempt/generation/质量汇总不一致都会被拒绝。
- 新 HR1 复验路径已登记为 `docs/stages/stage7/2026-08-25-stage7-7r4hr1-plan-quality-targeted-revalidation-results.json`，但 HR0 没有创建它。当前 H1 失败结果被加入不可变历史集合并固定校验 SHA-256。
- `.env.example` 中三个实际参与模型调用的示例已与 `backend/app/core/config.py` 和质量合同同步为 `deepseek-v4-flash`；直接配置测试防止三处再次分叉。历史真实结果没有改动；普通 Schema 测试里仅作为字符串样本、不触发调用的旧 `deepseek-chat` 值保留。
- 主链位置仅为 Prompt 与 Service，另有链外质量运行器和非业务配置示例；没有修改前端、API、Pydantic Schema、Adapter 参数、EvaluationCriterion 合同、SQLAlchemy Model、migration、React 或 PostgreSQL。

#### 29.5.2 实际验证与不可变证据

- Prompt/Service 专项 `44 passed`；质量运行器专项 `19 passed`；配置专项 `11 passed + 16 subtests`。受影响后端回归覆盖配置、计划 Adapter、1.0—4.0 计划 Service/Schema、source units、step9 和 4.0 Screening gate，为 `262 passed + 48 subtests`。只有既有 PyPDF2 弃用 warning，没有失败。
- CLI dry-run、Fake normal、Fake local repair 均通过。Fake normal 实际为 3 次业务调用，Fake repair 为 4 次且只有 1 次 local repair；三种模式真实 DeepSeek 调用均为 0、正式结果写入为 0，dry-run 测试使用哨兵证明真实 Adapter 未实例化且 API Key 不是前提。
- `py_compile` 与 `git diff --check` 通过。dry-run 前后历史结果 hash 一致；当前 H1 结果 SHA-256 仍为 `ada6cbc91c21e7f4f341eee587259676579c9c2770af3a220277ff32a5e47a6f`，新 HR1 复验结果文件不存在。
- PostgreSQL 只读复核仍为 `current=head=d6f4a2b8e913`，`jobs/candidates/resumes/applications/job_evaluation_plans/screening_runs/screening_reports/stage_histories/reports` 全为 0。本批没有运行 migration、数据库写入或 PostgreSQL 测试夹具。

#### 29.5.3 能证明、不能证明、风险与停止点

这些验证能证明 v2 Prompt 明确表达多来源合同、现有一次 local repair 能消费可定位的 `missing_source_merge`、确定性 warning 的中英文正反例和证据去重按当前测试成立，也能证明审计器按每份样本的真实角色序列而不是全局数字放行。它还证明 HR0 没有付费调用、没有创建复验结果、没有改变历史证据或数据库基线。

这些验证不能证明真实 DeepSeek 一定按 v2 Prompt 正确合并 J5-14，也不能证明未枚举的所有自然语言都不会使确定性信号检查误报或漏报，更不能证明六份真实质量已从 4/6 提升。最终模型质量只能由完整六份 HR1 新结果判断；出现新语言边界时应回到 Prompt/Service 测试层，不得靠额外真实调用碰运气。

7R4-HR0 到此完成并立即停止。唯一下一步是等待用户单独确认 7R4-HR1 的模型、当时价格、金额边界和 24/48 安全上限；当前授权不允许真实 DeepSeek、正式 20 份、7R4-I、7R4-J 或阶段 8。
