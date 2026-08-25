# 阶段 7：岗位事实与评价维度双层计划 4.0 重设计

> 日期：2026-08-24
>
> 状态：业务规则与 7R4-A—7R4-J 实施顺序已获用户最终确认；7R4-A—7R4-F 已于 2026-08-24 完成。当前停止等待用户确认 7R4-G，不得提前进入 7R4-H—J，真实 DeepSeek 调用必须为 0
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
