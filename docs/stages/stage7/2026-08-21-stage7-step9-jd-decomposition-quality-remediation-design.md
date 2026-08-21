# 阶段 7 小步骤 9：JD 拆解质量整改设计补充

> 日期：2026-08-21
>
> 状态：用户已最终确认 9-A—9-I 实施顺序，9-A—9-I 已执行完成。正式 9-I 严格执行 20 次 JD 拆解和 60 次筛选调用；JD18 未形成预期 `too_many_items`，所以小步骤 9 JD 门禁未通过。下游结果保持 `diagnostic`，不得据此宣布步骤 10—12 完成。此前误执行结果继续作为不可改写历史审计记录保留
>
> 上游权威文档：`2026-08-20-stage7-jd-driven-ai-screening-redesign.md`
>
> 历史质量基线：`2026-08-20-stage7-quality-acceptance.md` 与 `2026-08-20-stage7-quality-acceptance-results.json`

## 1. 文档目的

本文只设计阶段 7 小步骤 9“JD 拆解质量整改”，解决三类已有真实 DeepSeek 验收缺陷：

1. JD04 和 JD11 的英文或中英混合要求被翻译或改写为中文标题，因无法确定性证明标题来自 JD 原文而使计划失败。
2. JD08 的自由文本第一句被整句漏读，预先标注的“拉新”和“留存实验”没有形成独立事项。
3. 当前后端只能证明 `source_quote` 在聚合 JD 文本中出现，不能精确证明它来自哪个字段，也不能证明每段自由文本都已被模型审阅。

大白话理解：后端先把 JD 原文分成带编号的原文片段，DeepSeek 必须对每一段表态“这是岗位要求”或“这不是岗位要求”。对于岗位要求，模型只能从该片段中选取连续原文作为事项标题；后端再根据片段编号回填真实来源，不信任模型自己填写的来源。

## 2. 已确认的方案方向

用户已确认采用“版本化来源片段逐段审阅”方案，本文将其固化为以下原则：

1. 这不是 RAG：不生成 Embedding，不建立向量索引，不检索“最相关片段”，而是要求完整 JD 的所有候选片段都被审阅。
2. DeepSeek 负责自由文本语义理解、要求/非要求分类、最小可评价语义拆分和事项类别判断。
3. 后端程序负责原文片段编号、来源回填、连续原文验证、优先级修正、结构化 `JobRequirements` 补齐、去重、完整性和 0—30 项边界。
4. 模型不再自由填写 `source_field` 或 `source_quote`；它只引用后端提供的 `source_id`。
5. 内容校验失败不自动重试，不使用“多调几次总会成功”规避合同问题。
6. 不放宽 required、原文追溯、宣传过滤、0 项失败和超过 30 项失败边界。
7. 最终 `JobEvaluationItem` 继续使用已有 `title/category/priority/source_type/source_field/source_quote`，不在小步骤 9 扩展为多来源 `sources[]`。
8. AI 自由文本事项只允许来自 `description`；`title` 和 `department` 只提供岗位上下文，不直接产生评价事项；`requirements.*` 继续由程序补齐。
9. 非要求分类采用平衡方案：允许公司介绍、福利、宣传和上下文片段被判为非要求，但带明确职责、required 或 preferred 信号的片段不得标为非要求。
10. `负责拉新、激活和留存实验` 必须拆成“拉新”“激活”“留存实验”三个可独立评价事项；历史 42 项基线不改写，“激活”作为额外强制回归项记录。
11. 模型可通过受控的 `equivalent_structured_item_key` 表达“该自由文本事项与某个既有结构化事项语义等价”，后端验证后再合并；该字段不能创建事项或升级 priority。
12. `free_text_coverage` 只作为后端持久化审计数据，不在前端展示来源片段或逐段审阅结果。
13. 旧 `ready` 计划不自动批量升级；后端识别旧合同，HR 通过最小的“按新规则重新生成”操作显式触发。
14. 本步骤使用 Prompt v4、AI 提取 Schema 2.0、最终计划 Schema 2.0 和 source-unit 规则 v1，并通过向前 migration 支持新旧合同共存。
15. 实现完成后，小步骤 9 使用原有完整 20 份虚构脱敏 JD 做独立正式计数；小步骤 13 仍需再次执行阶段 7 完整复验。

## 3. 当前失败的证据结论

### 3.1 JD04

模型成功返回并通过现有 AI 输出 Schema 的事项包括：

- `设计 LLM 应用` ← `Design LLM applications and evaluation pipelines.`
- `设计评估流水线` ← 同一英文原句
- `理解 prompt injection 防护`
- `RAG 项目经历优先`

`source_quote` 存在于 JD，所以来源存在性检查通过。第二个标题与英文引用没有可验证的词面关系，Service 因此以 `JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED` 拒绝。

当前校验器也存在不一致：`设计 LLM 应用` 可能因为保留 `LLM` 而被放行，完全翻译的标题则被拒绝。因此当前规则不是稳定的“禁止翻译”合同。

### 3.2 JD11

模型返回：

- `负责企业客户的上线与续约` ← `Own onboarding and renewal for enterprise customers.`
- `英语沟通能力` ← `必须可使用 English 进行客户会议`
- `SaaS 实施经验` ← `SaaS implementation experience preferred`

第一项为全中文翻译标题和全英文来源，在第一项标题支持检查即失败。

### 3.3 JD08

原文为：

```text
负责拉新、激活和留存实验。必须能独立设计活动并复盘数据，有社群裂变经验优先。
```

原验收预标为“拉新”、“留存实验”和“独立设计活动”。模型只返回了后一句中的“独立设计活动”、“复盘数据”和“社群裂变经验”，第一句没有任何拆解事项。

“拉新”和“留存实验”不存在于结构化 `JobRequirements`，所以程序兜底无法补回。这是模型召回问题，不是优先级修正、来源定位或去重删掉了事项。

## 4. 目标链路与分层职责

```text
Job title / department 作为岗位上下文
Job description
        ↓
后端确定性生成 source units
        ↓
DeepSeek 逐段标记 requirement / non_requirement
        ↓
DeepSeek 从 requirement 片段拆出连续原文标题
        ↓
后端回填 source_field / source_quote，重算 priority
        ↓
程序补齐结构化 JobRequirements
        ↓
来源验证 → 合并去重 → 0—30 项与完整性校验
        ↓
保存当前 JobEvaluationPlan
```

### 4.1 Prompt Builder

- 将 title、department、完整 description、结构化 requirements 作为不可信 JD 快照。
- title 和 department 只作为语义上下文，不单独产生 `ai_extracted` 事项。这与 JD19 的 0 项边界保持一致：不能仅因岗位标题存在就强行产生评价项。
- 传入后端生成的 source units 及其编号。
- 传入结构化候选事项作为去重上下文，但模型不得从 requirements 重复创建事项。
- 提供纯中文、纯英文、中英混合、同句多要求、宣传福利和结构化重复的正反例。

### 4.2 Adapter

- 正常拆解仍只调用一次 DeepSeek。
- 仍使用严格 JSON 对象输出、低温度、关闭 SDK 自动重试和关闭 Mock/Fake 回退。
- 只返回原始响应和模型元数据，不做业务拆分、来源修复或优先级判断。

### 4.3 AI 提取 Schema

- 提取阶段输出合同从 `1.0` 升级为 `2.0`。
- 提取 Schema 与最终 `JobEvaluationPlanRead/JobEvaluationItem` 持久化形状分开版本化，避免为了模型中间合同迫使前端和历史计划整体换形。
- 每个 AI 候选事项只返回原文 `title`、`category` 和可空的 `equivalent_structured_item_key`；不返回 `priority/source_field/source_quote`。
- 禁止额外字段；每个 source unit 必须恰好出现一次。

### 4.4 Service

- 生成 source units 和稳定编号。
- 校验模型没有遗漏、重复或伪造 source ID。
- 从服务端映射回填 `source_field` 和 `source_quote`。
- 校验 `title` 是对应原文片段中的连续子串。
- 不使用模型返回的 priority，继续按 JD 原文语气重算。
- 校验 `equivalent_structured_item_key` 只能引用本次输入中同 category 的真实结构化事项，并在来源验证后按受控关联合并。
- 完成结构化补齐、语义去重、覆盖审计和数量边界。

### 4.5 Model / PostgreSQL

- 最终事项仍保存在 `job_evaluation_plans.items` JSONB，事项核心字段不变。
- 新增可空 `free_text_coverage` JSONB：旧 `1.0` 计划为 `null`，新 `2.0` 成功计划必须保存完整审阅审计；不伪造旧计划历史。该字段只进入后端持久化/内部校验 Schema，不进入常规前端读取合同。
- 不就地改写已被 ScreeningReport/ScreeningRun 引用的成功计划内容。
- 需要新增一条向前 migration，不修改既有 migration：新增上述可空审计列，并将同一岗位的计划唯一性从 `(job_id, jd_fingerprint)` 调整为 `(job_id, input_fingerprint)`。
- `jd_fingerprint` 继续只表示 JD 内容；`input_fingerprint` 改为 JD 快照与破坏性提取合同版本的稳定组合指纹。
- 相同 JD + 相同提取合同继续幂等复用；提取合同版本变化时允许创建新计划行，旧计划标记 outdated，历史报告继续引用原计划。

### 4.6 API / React

- 既有计划读取、生成和失败重新生成 API 路径不变。
- 最终事项形状不变，前端不展示 source units 或 `free_text_coverage`，也不增加编辑或权重能力。
- 读取接口为旧合同计划返回后端计算的 `contract_outdated`；HR 只新增最小的“按新规则重新生成”提示和操作，不新增 JD 片段可视化。
- 新计划的 AI 事项将稳定带有 `source_field=description` 和可定位 `source_quote`；旧 `1.0` 计划仍可读。

## 5. 来源片段合同

### 5.1 Source unit 生成

`source unit` 是后端从 `description` 中确定性切出的连续原文片段。

分段只处理排版和明确句子/子句边界，不直接代替 DeepSeek 做语义拆分：

- 按换行、列表项、句号、问号、感叹号和分号分段；
- 当同句后续子句引入新的“必须/要求/优先/required/preferred”语气时，在该优先级边界再分段；
- 不机械按 `、`、`and`、`和`、`及` 拆成事项，这些连接的内容是一个整体概念还是多个独立要求，由 DeepSeek 判断；
- 保留片段的原始大小写、缩写、技术名词和标点；
- 不静默截断过长或过多的片段，超过安全输入上限时使用受控失败。

`source_id` 使用后端稳定序号，例如 `description:0001`。模型只能引用已提供 ID，不能创建新 ID。

### 5.2 AI 输出概念结构

```json
{
  "schema_version": "2.0",
  "source_reviews": [
    {
      "source_id": "description:0001",
      "disposition": "requirements",
      "non_requirement_reason": null,
      "items": [
        {
          "title": "Design LLM applications",
          "category": "responsibility",
          "equivalent_structured_item_key": null
        },
        {
          "title": "evaluation pipelines",
          "category": "responsibility",
          "equivalent_structured_item_key": "responsibility:0002"
        }
      ]
    },
    {
      "source_id": "description:0002",
      "disposition": "non_requirement",
      "non_requirement_reason": "benefit",
      "items": []
    }
  ]
}
```

受控值：

- `disposition`: `requirements/non_requirement`
- `non_requirement_reason`: `company_info/benefit/promotion/context`
- `category`: 继续使用 `skill/experience/responsibility/education/other`
- `equivalent_structured_item_key`: 本次 Prompt 中提供的同 category 结构化事项 key，或 `null`

规则：

- `requirements` 必须至少有一个 item 且 `non_requirement_reason=null`；`non_requirement` 必须 `items=[]` 且包含一个受控 reason。
- 每个 source unit 必须恰好被审阅一次。
- 包含明确 required/preferred 语气或明确岗位职责表达的片段，不得标记为 `non_requirement`；这类明显信号由后端确定性复核。
- 公司介绍、福利、团建、办公环境和宣传文案必须为 `non_requirement`，后端仍保留确定性过滤。
- `equivalent_structured_item_key` 只能表达语义等价：后端必须验证 key 存在、category 相同、自由文本标题已通过原文追溯，随后只保留结构化事项的来源和 priority。
- 关联字段为 `null` 时，该候选项按新的自由文本事项处理；非空关联不得使不存在的结构化事项出现，也不得把 general/preferred 升级为 required。

### 5.3 后端自由文本覆盖审计

新 `2.0` 成功计划持久化最小 `free_text_coverage`，概念结构如下：

```json
{
  "rule_version": "jd_source_units_v1",
  "all_reviewed": true,
  "units": [
    {
      "source_id": "description:0001",
      "disposition": "requirements",
      "item_keys": ["ai:0001", "responsibility:0002"],
      "equivalent_structured_item_keys": ["responsibility:0002"]
    }
  ]
}
```

规则：

- 审计数据用于证明每个 source unit 都被审阅，以及最终事项或结构化等价项如何覆盖该片段。
- 它不保存完整模型原始响应，不替代 `input_snapshot`、最终事项的 `source_quote` 或运行日志。
- `all_reviewed=true` 必须由后端根据请求 source ID 与响应逐一比对后生成，不能直接信任模型声明。
- 旧 `1.0` 计划允许 `free_text_coverage=null`；新 `2.0` 成功计划缺失或不一致时拒绝保存。
- 常规 `JobEvaluationPlanRead` API 不返回该字段；仅后端内部审计、运维诊断和自动化测试读取，React 不接收也不展示它。

## 6. 原文可追溯规则

### 6.1 定义

对于新提取合同产生的 `ai_extracted` 事项，只有同时满足以下条件才叫“原文可追溯”：

1. `source_id` 来自后端本次请求的不可变来源表。
2. `source_field` 由后端回填为 `description`。
3. `source_quote` 由后端从输入快照原样回填，不使用模型重述文本。
4. `title` 必须是该 `source_quote` 中的连续原文子串。
5. 事项不能增加原文不存在的技能、程度、年限、经历类型或强制语气。

### 6.2 标题允许的处理

允许：

- 从来源片段中选择较短的连续原文子串作为标题；
- 选择子串时排除片段外围的列表符号、序号、首尾空白和包裹标点；
- 去重比较使用独立 canonical text，可忽略大小写、首尾空白和无语义标点，但不改写最终展示标题。

禁止：

- 中英文互译；
- 同义改写、概括、语法润色或动词时态改写；
- 展开或改写缩写；
- 修改原文中 `LLM`、`RAG`、`SaaS`、`C++`、`C#`、`Node.js`、`A/B` 等技术名词的大小写、标点或写法；
- 把两段不连续原文拼接成一个标题。

### 6.3 中英混合示例

```text
原文：必须可使用 English 进行客户会议
合法标题：English 进行客户会议
不合法标题：英语沟通能力
```

```text
原文：Design LLM applications and evaluation pipelines.
合法标题：Design LLM applications
合法标题：evaluation pipelines
不合法标题：设计 LLM 应用
不合法标题：设计评估流水线
```

## 7. 自由文本召回与结构化补齐

### 7.1 DeepSeek 责任

- 审阅每一个 description source unit，不得只挑代表性句子。
- 判断片段是岗位要求还是宣传/背景/福利。
- 将一句中可独立评价的要求分成多个事项，但不机械拆解固定组合概念。
- 标题使用连续原文，不做翻译或同义改写。
- 不从结构化 requirements 重复生成事项。

### 7.2 程序责任

- 继续 100% 补齐 `responsibilities/required_skills/preferred_skills/minimum_work_years/education_requirement/required_experiences/preferred_experiences/keywords/additional_requirements`。
- 不从 description 凭规则自行创建新语义要求，避免恢复旧 Python 规则评分思路。
- 结构化 priority 始终优先；AI 事项 priority 从原文语气重算。
- 对结构化和自由文本语义重复事项只保留一个最终事项；优先使用模型返回且经后端验证的 `equivalent_structured_item_key`，保留结构化来源和其 required/preferred 语义。
- “数据复盘/复盘数据”一类语序变化由 DeepSeek 做语义等价判断，但模型的判断不能直接删项：后端还要验证被引用 key、category、原文追溯和结构化候选表；无法证明等价时不强行合并。
- 去重必须在每个 AI 候选项已通过来源验证之后执行，不允许不可追溯事项通过“被结构化项合并”洗白。

### 7.3 JD08 拆分决定

对于 `负责拉新、激活和留存实验`，按“可独立评价的最小语义单元”应产生：

- `拉新`
- `激活`
- `留存实验`

原 42 项人工预标只把“拉新”和“留存实验”列为 JD08 的门槛要求。本次不修改原 JSON、不把分母从 42 改为 43；“激活”作为新自动化拆分回归与定向人工复核项单独记录。

## 8. 优先级、去重与边界

### 8.1 Priority

- `required`：只能来自结构化必需字段，或对应原文片段的明确强制语气。
- `preferred`：只能来自结构化优先字段，或对应原文片段的明确优先/加分语气。
- `general`：已明确写入的职责或要求，但没有强制或优先语气。
- 模型输出 Schema 2.0 不再返回 priority，从数据合同上消除模型擅自升级 required 的入口。

### 8.2 Deduplication

去重顺序固定为：

1. AI 输出 Schema 校验。
2. source unit 完整性校验。
3. 每项标题与原文连续子串校验。
4. 结构化事项程序补齐。
5. priority 修正。
6. 校验 `equivalent_structured_item_key` 并先合并结构化/自由文本等价事项。
7. 对仍未关联的同类别事项做保守语义去重。
8. 生成 `free_text_coverage`，再执行结构化覆盖和 0—30 项校验。

去重不能：

- 跨 category 随意合并；
- 为了降低项数而合并两个可独立评价的要求；
- 通过删掉一项规避不可追溯、重复或超过 30 项的失败。

### 8.3 Item count

- 去重后 0 项：失败。
- 1—4 项：生成 ready 计划并保留 `limited_basis` 警告。
- 5—30 项：正常 ready。
- 去重后超过 30 项：失败，不静默截断。

## 9. 旧计划、过期和幂等

`ready` 表示：计划已成功完成、至少有一项合法评价事项、没有错误信息，并且可作为后续 Resume 初筛的当前评价依据。`limited` 不是单独状态，而是 `status=ready` 且携带 `limited_basis` 警告，表示只有 1—4 项、依据偏少但仍可使用。

### 9.1 旧 failed 计划

JD04/JD11 类旧 failed 计划可通过已有失败重新生成入口使用新提取合同。旧失败错误记录不修改为成功历史。

### 9.2 旧 ready 计划

JD08 类已 ready 但质量不足的计划不就地改写，否则已有 ScreeningReport 会在不改变外键的情况下被新事项冒充历史评价基础。

后端根据计划的 `prompt_version/schema_version/input_fingerprint` 计算 `contract_outdated`，不依赖 HR 人工判断。部署新合同不会自动扫描岗位、调用 DeepSeek 或批量写库；旧计划仍可读，HR 会看到最小升级提示，但不展示来源片段。

HR 点击“按新规则重新生成”后：

1. 旧 ready 计划标记 outdated 且 `is_current=false`。
2. 使用新 `input_fingerprint` 创建新计划行。
3. 新计划生成期间，依赖当前计划的新初筛继续等待，不回退使用已过期计划。
4. 旧报告继续引用旧计划，不删除、不改写。
5. 新计划 ready 后，相关当前报告按已有“评价计划变化”语义标记过期，不自动批量重评。
6. 新计划失败时保留可审计的失败行和旧历史报告，但旧计划不重新冒充新合同计划；HR 可使用既有失败重试入口处理失败。

### 9.3 普通幂等

- 同一 Job、JD 快照和提取合同版本已有当前 generating/ready/failed 计划时，普通生成不创建重复计划。
- 新 Prompt 文字微调不自动触发全量重生成；只有显式标记为破坏性的提取合同版本变化才改变 `input_fingerprint`。
- 模型服务别名或供应商运行时返回名变化，不单独使旧计划过期。

### 9.4 版本合同

| 合同 | 当前版本 | 小步骤 9 版本 | 变化语义 |
| --- | --- | --- | --- |
| JobEvaluationPlan Prompt | `job_evaluation_plan_v3` | `job_evaluation_plan_v4` | source units、逐段审阅、原文标题、结构化等价关联 |
| AI 提取输出 Schema | `1.0` | `2.0` | `source_reviews[]` 与 `equivalent_structured_item_key` |
| 最终计划读写 Schema | `1.0` | `2.0` | 事项核心字段不变，新增可空后端审计和合同过期语义 |
| source-unit 规则 | 无独立版本 | `jd_source_units_v1` | 确定性分段和覆盖审计 |

`input_fingerprint` 必须包含 JD 快照和上述破坏性合同组合的稳定标识。普通 Prompt 措辞修订若不改变输出或分段语义，不提升破坏性合同版本；任何字段、分段、追溯或合并语义变化都必须显式升级，不能悄悄复用旧指纹。

## 10. 自动化验收设计

### 10.1 Prompt / Adapter

- Prompt 版本和 AI 提取 Schema 版本与配置一致。
- Prompt 包含逐段审阅、原文标题、禁止翻译、禁止 required 升级、宣传过滤和同句多事项正反例。
- Adapter 仍为单次严格 JSON 调用，SDK 重试为 0，不添加 Mock/Fake 质量回退。

### 10.2 Schema

- source unit 缺失、重复、未知 ID、未知 disposition/reason/category 和额外字段拒绝。
- `requirements` 无 item 和 `non_requirement` 带 item 拒绝。
- AI 不再输出 `priority/source_field/source_quote`。
- `equivalent_structured_item_key` 的 null、合法引用、未知 key、跨 category 引用和借关联升级 required 回归。
- 旧 `1.0` 计划允许无审计数据；新 `2.0` ready 计划必须具有合法 `free_text_coverage`。

### 10.3 原文追溯

- JD04：`Design LLM applications` 和 `evaluation pipelines` 分别形成英文原文事项；中文翻译标题拒绝。
- JD11：`onboarding`、`renewal`、`English 进行客户会议`、`SaaS implementation experience` 均可回到对应原文。
- 纯中文、纯英文和中英混合回归。
- 大小写、缩写、`C++/C#/Node.js/A/B`、全角/半角标点和列表符号回归。
- 标题首尾格式选取合法，内部改写、翻译、拼接和新增要求拒绝。

### 10.4 召回、拆分和去重

- JD08 “拉新”和“留存实验”必须形成不同最终事项；“激活”作为额外拆分回归。
- 一句包含多个独立要求时，不能用一个包含整句的 `source_quote` 冒充多个要求都已独立识别。
- 结构化和自由文本重复只保留一项。
- `数据复盘/复盘数据` 等语序变化由模型关联、后端受控验证后只保留一项；不相等或无法证明时不得误合并。
- 公司介绍、福利、宣传、办公环境和团建不形成事项。
- 自由文本模糊要求不得升级 required。

### 10.5 边界和计划版本

- 0 项正确失败。
- 1—4 项正确 ready + `limited_basis`。
- 去重后超过 30 项正确失败且不截断。
- 普通相同输入复用，不调用模型。
- 旧合同 ready 计划返回 `contract_outdated=true`，但部署本身不自动调用模型、不批量写库。
- HR 显式升级时，旧计划 outdated、新计划使用新行；生成期间下游等待，新计划失败也不把旧计划重新当作新合同当前计划，旧报告外键不变。
- migration 只新增可空 `free_text_coverage` 并调整本步骤所需唯一性，完成 `upgrade -> downgrade -> upgrade` 与 `alembic check`。

### 10.6 下游隔离回归

- 岗位发布不因计划失败回滚。
- 计划未 ready 时继续 `waiting_plan`，ready 后才协调后续初筛。
- 不修改 HR 决策、Application、Resume、ScreeningReport 内容合同或评分规则。
- 前端只增加旧合同提示和 HR 显式升级操作，不展示审计片段；不修改后续初筛 Prompt/Schema。

## 11. 真实 DeepSeek 定向调试与 9-I 完整链路复验

只使用现有虚构脱敏 JD/Resume，并始终关闭 Mock/Fake 回退。真实调用分成三类，必须分开统计：

1. 定向调试：优先使用 JD04、JD08、JD11、JD13、JD18、JD19 定位根因；调用数按实际发生次数单独记录，不计入最终 20 份结果。
2. 9-I JD 正式复验：重新对原有完整 20 份 JD 各执行一次新合同拆解，预期业务调用 20 次；不得复用此前误执行结果冒充本轮调用。
3. 9-I 下游诊断：直接使用本轮第 2 类调用形成的可用计划，对原冻结 20 组 JD/Resume 各评价 3 次，最多 60 次筛选调用。某组缺少本轮可用计划时记为“上游阻塞”并保留在 20 组分母，不回退旧计划、不调用 Fake/Mock，也不删除样本。

每次真实调用记录：

- 实际模型调用次数；
- 模型实际返回名；
- input/output token；
- 模型结构化输出；
- 后端最终计划或稳定失败码；
- 原文追溯、主要要求、required、重复、宣传和数量边界复核。
- 筛选轮次、合法报告或稳定失败码、拒绝层、失败分类、综合分、方向、证据、事实、安全和亮点复核。

定向调试、JD 正式复验和下游诊断分开记录。9-I 新结果使用独立路径，不覆盖 `2026-08-20-stage7-quality-acceptance-results.json`、9-H debug、此前误执行的 `2026-08-21-stage7-step9-jd-decomposition-results.json` 或时间事实结果。原 35/42 保留为历史基线；新 JD 结果仍用原冻结 42 项计算可比召回率，并把“激活”作为额外必须通过的拆分断言单列。

9-I 对两类结论分开处理：20 份 JD 指标正式判定小步骤 9；20 组下游指标只诊断步骤 9 的上游整改是否连带改善合法报告率、方向、三次稳定性、安全、证据和幻觉。下游即使达到既有门槛，也不能标记步骤 10—12 完成，更不能冒充阶段 7 整体通过。小步骤 13 仍会独立重跑整条链路和浏览器，验证后续整改完成后没有回归。

## 12. 小步骤 9 的完成语义

小步骤 9 自动化和完整 20 份 JD 真实复验必须同时满足：

1. 除预设 0 项和超过 30 项边界外，其余 18 份正常 JD 全部形成可用 ready/limited 计划。
2. JD04/JD11 的英文和中英混合标题保留连续原文，翻译/改写事项为 0。
3. 原冻结 42 项自由文本主要要求识别率不低于 95%；JD08 的“拉新”“激活”“留存实验”均形成独立事项，其中“激活”作为分母外额外强制回归。
4. 结构化明确要求覆盖保持 100%。
5. 擅自新增 required、明显重复、不可追溯事项和宣传/福利误识别均为 0。
6. JD18/JD19 继续正确失败，所有 1—4 项样本继续正确 ready + limited。
7. 实际模型调用次数、模型名和 token 有记录；原 20 份 JD 结果未被覆盖，失败样本未删除，Fake/Mock 未作为质量指标。
8. 既有 HR 决策、Application、Resume 和后续初筛链路只做隔离回归，没有提前修改其业务合同。

满足以上条件只能写为“小步骤 9 JD 拆解质量门禁通过”：它能证明固定 20 份 JD 在新合同下达到本步骤标准，不能证明阶段 7 整体完成。9-I 同轮产生的 20 组 JD/Resume、报告质量、三次稳定性和安全数据仅为诊断值，不替代步骤 10—12 的正式整改与验收；小步骤 13 仍会再次执行最终整体验收。

## 13. 包含与不包含

### 13.1 包含

- JD 自由文本 source units 与逐段审阅。
- AI 提取 Schema 2.0 和对应 Prompt 版本升级。
- 中英文原文标题和来源定位。
- JD08 明确主要要求召回。
- 结构化补齐、优先级、宣传过滤和去重顺序。
- 受控 `equivalent_structured_item_key`、仅后端 `free_text_coverage` 审计和保守语义去重。
- 计划合同版本化、HR 手动升级旧 ready 计划和普通幂等。
- 与上述目标直接相关的 Prompt、Schema、Service、Adapter、Model、最小 API/React 升级提示、向前 migration、自动化和完整 20 份 JD 真实 DeepSeek 复验。
- 9-I 中使用本轮可用计划执行的 20 组 JD/Resume 三次评价，以及合法报告率、方向、稳定性、安全、证据和幻觉诊断。

### 13.2 不包含

- 合法报告成功率、Resume 初筛评分方向和三次稳定性的业务整改或正式完成认定；9-I 只采集诊断值。
- 额外亮点语义去重。
- 浏览器焦点警告和真实数据库幂等收尾。
- 来源片段或 `free_text_coverage` 的前端可视化。
- HR 决策规则、Application/Resume 核心数据合同和后续初筛报告内容合同。
- 公开投递、面试、Offer、录取、登录/RBAC、Agent、RAG 或任何产品阶段 8 能力。

## 14. 实施批次、交付物与停止点

小步骤 9 固定拆成 9-A—9-I 九个实施批次。每一批开始前都必须重新检查 `git status`、相关差异、当前分支/HEAD/远端关系和未跟踪文件；每一批结束后都必须报告实际修改、验证结果、能证明什么、不能证明什么和下一批风险，然后停止等待用户确认。不得因为后续批次内容已经明确，就在同一轮提前实现。

### 14.1 总体顺序

| 批次 | 本批唯一目标 | 主要交付物 | 完成后停止点 |
| --- | --- | --- | --- |
| 9-A | 自动化合同基线 | 测试夹具、合同测试和预期红灯分类 | 不改生产代码，等待确认进入 9-B |
| 9-B | description source-unit 确定性切片 | 分段器、稳定 ID、来源表和单元测试 | 不改 Prompt/AI Schema，等待确认进入 9-C |
| 9-C | AI 输入输出合同升级 | Prompt v4、AI 提取 Schema 2.0、Adapter 严格解析 | 不组装最终计划，等待确认进入 9-D |
| 9-D | Service 质量规则闭环 | 追溯、priority、补齐、关联去重、覆盖审计和边界 | 不落新数据库合同，等待确认进入 9-E |
| 9-E | 持久化与版本化 | Model、内部/读取 Schema、指纹、向前 migration | 不做 HR 前端入口，等待确认进入 9-F |
| 9-F | 旧计划显式升级 | `contract_outdated`、API 语义、HR 最小提示和按钮 | 不展示审计片段，等待确认进入 9-G |
| 9-G | 自动化总回归与正式验收器准备 | 全量自动化、PostgreSQL/migration、20 份 JD 统计器 | 不调用真实模型，等待确认进入 9-H |
| 9-H | 真实 DeepSeek 定向调试 | 受影响样本的真实调用与独立诊断记录 | 不产生正式 20 份结论，等待确认进入 9-I |
| 9-I | 20 份 JD 正式复验与下游完整诊断 | JD 正式结果、20 组×3 次筛选诊断、对比说明和状态文档 | 分开判定 JD 门禁与下游诊断，停止等待确认 |

### 14.2 9-A：自动化合同基线

目标：把本设计已经确认的业务规则转换为可重复的测试输入、预期输出和失败断言，先证明旧实现具体缺少什么。9-A 是测试先行的临时红灯阶段，不负责让新合同通过。

允许修改：

- `backend/tests` 中 JobEvaluationPlan 相关测试；
- 测试专用的虚构脱敏夹具、builder 和断言辅助函数；
- 本设计文档的确认状态与 `PROJECT_STATE.md` 的当前批次说明。

必须完成：

1. 固化 JD04、JD08、JD11 和纯中文/纯英文/中英混合的测试输入，不修改原质量结果 JSON。
2. 建立连续原文、禁止翻译/改写/拼接、大小写/缩写/技术名词/标点的合同断言。
3. 建立同句多要求、结构化/自由文本重复、`数据复盘/复盘数据`、宣传福利过滤和 required 不升级的合同断言。
4. 建立 source ID 缺失/重复/伪造、非法 disposition/reason/items 组合、结构化等价 key 合法/非法引用的合同矩阵。
5. 建立旧 `1.0` 无审计可读、新 `2.0` ready 必须有审计、普通幂等和破坏性合同版本变化的预期矩阵。
6. 建立 0 项、1—4 项和超过 30 项边界断言。

验证与完成标志：

- 新测试必须能够被 pytest 正常收集；不得用 import error、语法错误或夹具错误冒充红灯。
- 现有合同测试不得出现无关回归。
- 每个预期失败必须能映射到 9-B、9-C、9-D、9-E 或 9-F 的一个待实现能力。
- 不使用 `skip/xfail`、删断言或放宽规则伪造通过。
- 本批不修改任何生产代码，不调用 DeepSeek；报告红灯分类后停止。

### 14.3 9-B：description source-unit 确定性切片

目标：先把“模型需要审阅哪些原文”变成后端可重复、与模型无关的确定性输入。

允许修改：

- JobEvaluationPlan Service 内与输入准备直接相关的代码，或新增同职责的最小内部 helper；
- 对应单元测试和测试夹具；
- 当前批次状态文档。

必须完成：

1. AI 自由文本来源只读取 `description`；`title/department` 只保留为 Prompt 上下文，`requirements.*` 不进入自由文本切片。
2. 按换行、列表项、句号、问号、感叹号、分号和明确 priority 边界生成连续原文片段。
3. 不机械按照 `、/和/及/and` 拆成评价事项。
4. 保留原始大小写、缩写、技术名词和内部标点；只分离外围列表符号、序号和空白定位信息。
5. 生成稳定、无重复的 `description:0001` 形式 source ID，并建立不可变 source ID → 原文字段/片段映射。
6. 空 description、超长输入、过多片段和无法安全处理的输入使用稳定失败，不静默截断。

验证与完成标志：

- 纯中文、纯英文、中英混合、CRLF/LF、列表、连续标点和优先级边界测试通过。
- 同一 description 重复生成得到完全相同的 source units 和 ID。
- 9-A 中只依赖切片能力的红灯转绿，其余红灯保持原因明确。
- 不修改 Prompt、AI 输出 Schema、Adapter、Model、数据库、API 或前端；停止等待 9-C。

### 14.4 9-C：Prompt v4、AI 提取 Schema 2.0 与 Adapter

目标：让 DeepSeek 按 source unit 逐段作答，并从数据合同上移除模型伪造来源和擅自决定 priority 的入口。

允许修改：

- `backend/app/prompts/job_evaluation_plan.py`；
- `backend/app/schemas/job_evaluation_plan.py` 中 AI 中间输出合同；
- `backend/app/adapters/job_evaluation_plan.py`；
- 与版本配置直接相关的最小配置代码；
- 对应 Prompt、Schema、Adapter 测试。

必须完成：

1. Prompt 升级为 `job_evaluation_plan_v4`，输入包含岗位上下文、完整 source units 和可引用的结构化候选 key。
2. Prompt 明确逐段审阅、连续原文标题、禁止翻译/改写、同句多事项、非要求平衡规则、结构化等价关联和禁止 priority 升级。
3. AI 提取 Schema 2.0 使用 `source_reviews[]`；每项只允许 `title/category/equivalent_structured_item_key`。
4. `requirements` 必须有 items 且 reason 为空；`non_requirement` 必须无 items 且 reason 为受控值。
5. 禁止模型返回 `priority/source_field/source_quote` 和任何额外字段。
6. Adapter 继续只做单次严格 JSON 调用和响应转换，SDK 自动重试为 0，不能加入业务修复或 Mock/Fake 质量回退。

验证与完成标志：

- Prompt 版本、配置版本和 Schema 版本一致。
- 合法响应通过；缺 source review、额外字段、非法枚举、非法 item/reason 组合和旧 1.0 响应被稳定拒绝。
- Adapter 错误映射和单次调用既有测试继续通过。
- 本批不把 AI 响应组装成最终计划，不修改数据库/API/React；停止等待 9-D。

### 14.5 9-D：Service 原文追溯、补齐、关联去重与覆盖审计

目标：把通过 Schema 的模型响应转换成安全、完整、可追溯的最终事项，并在保存前完成所有业务校验。

允许修改：

- `backend/app/services/job_evaluation_plan_service.py` 及其最小内部 helper；
- JobEvaluationPlan 相关 Service 测试和夹具；
- 当前批次状态文档。

必须按顺序完成：

1. 校验请求中的每个 source ID 在响应中恰好出现一次，拒绝遗漏、重复和未知 ID。
2. 根据 source map 回填 `source_field=description` 和原样 `source_quote`。
3. 校验每个 AI title 是对应 source quote 的连续原文子串；翻译、改写、内部标点/大小写变化和跨片段拼接均拒绝。
4. 根据结构化字段或原文明确语气计算 `required/preferred/general`，不信任模型 priority。
5. 程序 100% 补齐全部结构化 `JobRequirements` 事项。
6. 校验 `equivalent_structured_item_key` 存在、category 相同、来源先合法；合法时保留结构化来源和 priority，非法时拒绝。
7. 对未显式关联的同 category 候选做保守去重；无法证明等价时不合并，两个独立要求不得为了降项数被合并。
8. 生成后端内部 `free_text_coverage`，由后端计算 `all_reviewed`，不能相信模型声明。
9. 最后执行结构化覆盖、明显重复、宣传过滤和 0—30 项边界。

验证与完成标志：

- JD04/JD11 的原文追溯 Service 测试通过。
- JD08 形成“拉新、激活、留存实验”三个独立事项。
- `数据复盘/复盘数据` 合法等价时只保留结构化事项；未知/跨 category/不确定关联不得误删。
- 擅自 required、不可追溯、明显重复和宣传福利事项为 0；0 项和 >30 项继续失败，1—4 项 ready + limited。
- 9-A 中属于 Service 的红灯全部转绿。
- 本批不新增数据库列、不改变唯一约束、不修改前端；停止等待 9-E。

### 14.6 9-E：Model、PostgreSQL、Schema 版本与输入指纹

目标：让新合同可以与旧计划并存、可审计并保持普通幂等，且不改写历史报告引用。

允许修改：

- `backend/app/models/job_evaluation_plan.py`；
- 最终计划的内部持久化/读取 Schema；
- JobEvaluationPlan Service 中与版本、指纹、持久化直接相关的代码；
- 新增一条向前 Alembic migration；
- Model、Schema、Repository/Service 和 migration 测试。

必须完成：

1. 新增可空 `free_text_coverage` JSONB；旧 1.0 行保持 null，新 2.0 ready 行必须保存合法审计。
2. 最终计划 Schema 支持旧 1.0 读取和新 2.0 合同；`JobEvaluationItem` 核心字段保持不变。
3. `jd_fingerprint` 继续只表示 JD 内容；`input_fingerprint` 纳入 JD 快照和破坏性合同版本。
4. 唯一约束从 `(job_id, jd_fingerprint)` 调整为 `(job_id, input_fingerprint)`，允许同一 JD 的新旧合同计划使用不同行。
5. 同一 JD + 同一合同普通生成继续复用，不重复调用模型；仅非破坏性 Prompt 措辞变化不制造新指纹。
6. 不就地改写被 ScreeningReport/ScreeningRun 引用的旧 ready 计划。
7. 只新增 migration，不修改任何既有 migration。

验证与完成标志：

- 新旧 Schema 读取、审计必填/可空、相同输入幂等和合同升级新行测试通过。
- 在真实 PostgreSQL 上完成 `upgrade -> downgrade -> upgrade` 和 `alembic check`。
- 旧报告外键保持原计划，数据未被批量重写。
- 本批不增加 HR 操作或审计前端展示；停止等待 9-F。

### 14.7 9-F：旧计划识别与 HR 手动升级

目标：让 HR 能看到旧合同计划需要升级，并显式生成新合同计划；部署本身不得自动产生模型调用或批量写库。

允许修改：

- JobEvaluationPlan Service/API 中合同过期计算和显式升级所需的最小代码；
- JobEvaluationPlan 相关 React 类型、状态、提示和操作；
- 对应 API、协调、前端组件测试。

必须完成：

1. 后端根据 `prompt_version/schema_version/input_fingerprint` 计算并返回 `contract_outdated`，不新增需要人工维护的持久化布尔值。
2. 复用现有普通生成入口完成旧 ready 计划升级；既有 failed 重试入口仍只负责 failed 计划，不混淆两种动作。
3. HR 只看到最小的“当前计划使用旧规则”和“按新规则重新生成”，不展示 source units 或 `free_text_coverage`。
4. HR 触发后旧计划变为 outdated、新合同计划使用新行；生成期间新初筛等待，不回退旧计划。
5. 新计划 ready 后沿用现有“计划变化”语义处理当前报告过期，不自动批量重评。
6. 新计划失败时保留失败行和旧历史报告，但不把旧计划重新冒充新合同当前计划。

验证与完成标志：

- 部署/读取旧计划不会自动调用模型或写库。
- API 的旧计划提示、手动升级、并发幂等、成功/失败状态和历史报告引用测试通过。
- React 只出现升级提示/按钮，既有计划事项展示不变，审计数据不可见。
- HR 决策、Application、Resume 和后续评分合同未修改；停止等待 9-G。

实施结果（2026-08-21）：

- `contract_outdated` 由 Service 使用当前 Prompt、最终 Schema 和合同感知指纹动态计算，未进入 SQLAlchemy Model 或 PostgreSQL 列；旧 1.0 与旧合同计划返回 true，当前合同返回 false。
- GET 读取和 FastAPI lifespan 启动测试均证明不会调用评价计划生成、写库或扫描岗位；React 只显示“当前评价计划使用旧规则”和“按新规则重新生成”，不接收或展示 `free_text_coverage/source_units`。
- 旧 ready 升级复用普通 `generate`：旧行转为 outdated，新行经历 generating 后独立 ready 或 failed；并发操作复用同一 generating 行，failed `regenerate` 仍拒绝 ready 计划。
- 真实 PostgreSQL 回归证明历史 ScreeningReport 的 `job_evaluation_plan_id` 不被改写，当前报告按 `evaluation_plan_changed` 标记过期且没有自动新增 ScreeningRun。生成中覆盖审计使用 SQL `NULL` 满足 9-E 已有 JSONB 约束，没有修改 Model 或 migration。
- 42 项 step9 合同、129 项 JobEvaluationPlan/Screening 定向、43 项岗位与部署隔离、668 项后端全量、19 个前端 Node 测试脚本、TypeScript 和 Vite 生产构建均通过；`alembic check` 无新操作。本批仅使用 Fake/Mock 模型边界，不构成真实 AI 质量结论。

### 14.8 9-G：完整自动化回归与正式验收器准备

目标：在产生真实模型成本前，证明代码、数据库、前端和统计工具都按小步骤 9 合同工作。

允许修改：

- 为修复小步骤 9 范围内自动化回归所必需的最小代码和测试；
- `scripts/run_stage7_quality_acceptance.py` 中小步骤 9 独立模式、统计和新输出路径；
- 小步骤 9 自动化验收说明和当前状态文档。

必须完成：

1. 运行全部 JobEvaluationPlan 定向测试和 backend 全量测试。
2. 运行 migration 测试、真实 PostgreSQL 相关测试和 `alembic check`。
3. 运行 frontend 单元测试和生产构建。
4. 回归岗位发布、waiting_plan、旧报告引用、HR 决策、Application、Resume 和 ScreeningReport 隔离。
5. 验收脚本继续使用原有 20 份虚构脱敏 `JD_CASES` 和冻结 42 项主要要求；增加“激活”分母外强制断言。
6. 验收器能分别统计正常计划、边界失败、limited、召回率、结构化覆盖、required、重复、不可追溯和宣传误识别。
7. 验收器使用新的独立输出路径，绝不覆盖原结果 JSON；调试调用和正式调用分开计数。

验证与完成标志：

- 所有自动化、migration 和前端构建通过，`git diff --check` 通过。
- 统计器使用离线夹具可以验证计算逻辑，但离线/Fake 结果不得被写成真实质量结论。
- 本批不得调用真实 DeepSeek；停止等待用户授权 9-H 的真实调用成本。

实施结果（2026-08-21）：

- `run_stage7_quality_acceptance.py` 新增独立 `step9-jd` 模式；`directed_debug` 固定只选 JD04/JD08/JD11/JD13/JD18/JD19，`final_count` 固定选全部 20 份 JD，两者使用不同新输出路径，并禁止覆盖历史 Stage 7 结果。
- 验收器已改用 `input_snapshot/source_units/structured_candidates` 新输入合同；召回只检查最终事项标题和模型审阅标题，不再用整段 `source_quote` 制造命中。
- 统计器独立计算 18 份正常计划、JD18/JD19 边界、4 份 limited、42 项召回、JD08“激活”额外断言、结构化覆盖、擅自 required、明显重复、不可追溯和宣传/福利误识别。只有冻结 20 份样本各恰好一次真实调用的 `final_count` 才允许形成通过/失败结论。
- 新增 9 项验收器测试；42 项 step9 合同、139 项 JobEvaluationPlan/Screening/验收器定向、140 项岗位与业务隔离、32 项 migration 以及 677 项 pytest 后端全量均通过；19 个前端 Node 脚本和 TypeScript/Vite 生产构建通过。
- PostgreSQL current/head 均是 `e4c7a1b9d632`，`alembic check` 无新操作，`git diff --check` 通过。定向/正式 dry-run 均为 0 次模型调用、0 次结果写入，独立结果 JSON 均未生成。本批没有调用真实 DeepSeek，离线/Fake 结果不构成 AI 质量结论。

### 14.9 9-H：真实 DeepSeek 定向调试

目标：用最少但覆盖关键根因的真实调用检查新 Prompt/Schema/Service 组合，不把调试结果冒充正式统计。

允许操作：

- 只使用现有虚构脱敏 JD04、JD08、JD11、JD13、JD18、JD19；
- 关闭 Mock/Fake 回退并调用当前配置的真实 DeepSeek；
- 写入独立诊断记录；
- 对暴露出的、小步骤 9 合同范围内缺陷补最小测试和修复。

必须完成：

1. 记录每次实际模型调用、实际模型名、input/output token、响应、最终计划或失败码。
2. JD04/JD11 检查英文/中英混合原文追溯；JD08 检查三项拆分和结构化重复；JD13/JD18/JD19 检查 limited、>30 和 0 项/宣传边界。
3. 调试失败必须分类为 Prompt、Schema、Adapter、Service 或模型不服从，不得直接重复多次挑选好结果。
4. 如果需要改变已确认的核心合同，立即停止并先更新设计、重新获得确认。
5. 如果只需按既有合同修复代码，回到对应 9-B—9-G 层补测试、修复并重跑自动化，然后重新申请定向调用；所有额外调用如实记录。

验证与完成标志：

- 六类定向样本均达到各自合同目标，调用记录完整，Mock/Fake 调用为 0。
- 调试记录与正式计数文件分开，不修改原质量结果。
- 不能据此宣布小步骤 9 或阶段 7 通过；停止等待用户授权 9-I 最多 80 次真实业务调用。

实施结果（2026-08-21）：

- 定向 dry-run 固定选中 JD04/JD08/JD11/JD13/JD18/JD19，`actual_model_call_count=0`、`writes_result_file=false`、`quality_conclusion_allowed=false`；没有生成或覆盖任何结果文件。
- 真实配置为 `LLM_PROVIDER=deepseek`、Mock/Fake 回退关闭、SDK 自动重试 0；Prompt 为 `job_evaluation_plan_v4`，AI 提取与最终计划 Schema 均为 `2.0`。API Key 只检查非空，没有打印或写入记录。
- 六份虚构脱敏 JD 各调用一次，实际调用 6 次且没有第 7 次调用。响应实际模型名均为 `deepseek-v4-flash`；input token 7,764、output token 1,209，合计 8,973。
- JD04/JD08/JD11 分别形成 ready，JD13 形成 `limited_basis`，JD18/JD19 分别保持 `too_many_items`/`no_items`；6/6 的 expected/actual outcome 一致且 `contract_satisfied=true`。
- JD04/JD11 的英文与中英混合标题均为对应 source quote 的连续原文；JD08 独立识别“拉新/激活/留存实验”，并通过受控 structured key 合并“复盘数据/社群裂变经验”；成功计划结构化覆盖完整、无擅自 required、明显重复、不可追溯或宣传福利误识别。
- 验收器补充保存模型原始结构化响应、失败时的模型名/token、逐样本合同结论、拒绝层和失败分类，并新增 1 项 Schema 拒绝证据回归；验收器 10 项、step9 合同 42 项均通过。
- 独立结果保存为 `2026-08-21-stage7-step9-jd-decomposition-debug-results.json`。原质量结果和 9-I 正式结果路径未覆盖；没有新增或修改 migration，没有影响前端。
- 本结果只证明六份关键定向样本在本次单次真实响应中遵守 Prompt/Schema/Adapter/Service 合同，不能证明正式 20 份 JD 门槛、小步骤 9 或阶段 7 通过。当前停止在 9-I 门禁前。

### 14.10 9-I：20 份 JD 正式复验与下游完整诊断

目标：在同一批次中先用固定 20 份 JD 正式判定小步骤 9，再使用本轮形成的可用评价计划观察上游整改对后续完整 AI 质量链路的连锁影响。

允许操作：

- 对原有完整 20 份虚构脱敏 JD 各执行一次真实 DeepSeek 拆解；
- 对原冻结 20 组 JD/Resume 各尝试 3 次真实筛选评价；
- 为新增合并 9-I 模式、独立结果路径、统计和 dry-run 所必需，最小修改 `scripts/run_stage7_quality_acceptance.py`、验收器测试和虚构脱敏夹具；
- 写入新的 JD 正式结果、下游诊断结果、对比说明和完成后的项目状态文档。

禁止修改生产 Prompt、Schema、Service、Adapter、Model、API、React 或 migration。业务质量失败只能记录和分类，不得在本批顺手修复。

#### 14.10.1 零调用预检

1. dry-run 固定选中 20 份 JD、20 组 JD/Resume、原人工标签和每组 3 次评价轮次。
2. 预期 JD 调用 20 次、筛选调用最多 60 次，dry-run 实际调用必须为 0，且不写正式结果。
3. 验收器必须证明新结果路径不会覆盖原质量结果、9-H debug、此前误执行结果或时间事实结果。
4. Mock/Fake 回退关闭、SDK 自动重试为 0；API Key 只检查存在，不打印或写入。
5. dry-run 或验收器测试失败时停止，不得调用真实 DeepSeek。

#### 14.10.2 JD 正式复验

1. 20 份 JD 各调用一次，预期业务调用 20 次；不得复用此前误执行响应，也不得人工重跑挑选较好结果。
2. 18 份正常 JD 全部 ready/limited；JD18/JD19 按预设边界失败；全部实际 1—4 项计划正确 limited。
3. 原冻结 42 项主要要求识别率 ≥95%，JD08“激活”额外强制通过，结构化明确要求覆盖 100%。
4. 擅自 required、明显重复、不可追溯和宣传/福利误识别均为 0。
5. 结果保存到新的 `docs/stages/stage7/2026-08-21-stage7-step9-jd-decomposition-revalidation-results.json`，不得覆盖此前误执行的 `2026-08-21-stage7-step9-jd-decomposition-results.json`。

#### 14.10.3 下游完整 AI 质量诊断

1. 只使用本轮 14.10.2 生成的可用计划；不得使用此前误执行结果、9-H 计划、旧 1.0 计划或 Fake/Mock 计划补齐。
2. 对原冻结 20 组 JD/Resume 各计划 3 次真实筛选评价。缺少本轮可用计划的样本记为上游阻塞，执行 0 次筛选，但仍留在合法报告率、方向和稳定性的 20 组总体分母中；其余样本各执行 3 次。
3. 记录每组 0/3、1/3、2/3、3/3 合法报告分布，以及 Prompt、Schema、Adapter、Service、模型不服从、证据、事实、亮点和一致性失败分类。
4. 按全部 20 组计算人工三档方向一致率；单列合法报告样本内部诊断值、极端方向错误和同岗位排序，不能用内部值替代总体指标。
5. 统计三次全部合法样本数、这些样本中最大分差 ≤5 的比例、跨两个以上区间和单项明显方向反转。
6. 统计证据可定位、严重事实虚构、敏感属性评分、招聘决定、年限事实冲突、投递后经历误用、亮点重复/无关、“未体现”写成“不会”等安全指标。
7. 与 2026-08-20 旧基线 `10/20` 至少一份合法报告、方向 `10/20=50%`、稳定样本 `5/20` 且其中 `4/5` 分差 ≤5 逐项比较。
8. 诊断 JSON 保存为 `docs/stages/stage7/2026-08-21-stage7-step9-full-chain-diagnostic-results.json`，说明保存为同名 `.md`；不得覆盖任何既有结果。

#### 14.10.4 调用、结果语义与停止点

1. 预计最多 80 次业务调用：20 次 JD 拆解 + 最多 60 次筛选；实际模型名、input/output token、完成响应和调用数全部如实记录。
2. 基础设施故障造成的额外调用单列原因和次数，不能选择较好结果替换首次有效结果。
3. JD 指标独立产生 `step9_quality_gate_passed`；下游指标标记为 `diagnostic`，即使达到既有门槛也不能宣布步骤 10—12 完成。
4. 自动化仍须全绿，`git diff --check` 通过，历史结果未改写，HR 决策、Application、Resume 和 PostgreSQL 业务表未被测试脚本修改。
5. 任一 JD 硬门槛失败，小步骤 9 保持未通过；下游诊断可以为有本轮可用计划的样本继续完成，但不能借此进入步骤 10。
6. 本批结束后更新 `PROJECT_STATE.md` 并停止，不修改业务代码、不进入步骤 10，等待用户确认下一步。

历史说明：此前 `2026-08-21-stage7-step9-jd-decomposition-results.json` 来自助手误解用户意图后执行的 20 次真实调用。该文件及 18/18 正常 JD 可用、42/42 主要要求、63/63 结构化覆盖、JD18 边界未按预期失败等事实继续保留用于审计，但不冒充本轮重新授权的正式 9-I，也不得被删除或覆盖。

实施结果（2026-08-21）：

- 新增独立 `step9-combined` 模式。零调用 dry-run 固定选择 JD01—JD20 和 SR01—SR20，人工标签保持 high 8、partial 6、low 6，每个非阻塞样本固定 3 次；预期 20 次 JD、最多 60 次筛选，实际调用 0、结果写入 0。运行时确认 `LLM_PROVIDER=deepseek`、Mock/Fake 回退关闭、JD/筛选 SDK `max_retries=0`，API Key 只检查存在且未输出或写入。
- 验收器新增历史路径独占保护、本轮计划 provenance、上游阻塞、20 组总体分母、非阻塞三次调用、合法报告/方向/稳定性分母、模型调用/token 以及安全/证据/失败分类测试。正式执行前 141 项受影响定向测试通过；执行后新增验收器 19 项、其余受影响专项 122 项和后端全量 687 项均通过，只有 1 条既有 PyPDF2 弃用 warning。
- JD 正式复验严格调用 20 次且 20/20 收到完整响应，没有重跑或额外基础设施调用；实际模型名全部为 `deepseek-v4-flash`，input/output token 为 `23,761/5,230`。18/18 正常 JD 均形成 ready/limited 可用计划；JD16 实际只有 3 项并正确携带 `limited_basis`，但与冻结逐样本 `ready` 记录存在差异。JD19 正确 `no_items`；JD18 再次把明确岗位要求误判为 `non_requirement/context`，在 Service 形成 `JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED`，没有到达预期 `too_many_items`，边界仅 1/2 正确。
- JD 其余正式指标为：冻结主要要求 42/42（100%）、JD08“激活”通过、结构化明确要求 63/63（100%），擅自新增 required、明显重复、不可追溯和宣传/福利误识别均为 0。由于 JD18 边界失败层不符合合同，`step9_quality_gate_passed=false`，小步骤 9 保持未通过。
- 下游所需 JD01/JD02/JD03/JD04/JD06/JD08/JD10 均有本轮可用计划，因此上游阻塞为 0，20 个样本各恰好调用 3 次，共 60 次且 60/60 收到完整响应；没有使用历史、9-H、旧 1.0 或 Fake/Mock 计划。实际模型名全部为 `deepseek-v4-flash`，input/output token 为 `120,366/61,651`。
- 20 组中至少一份合法报告为 9/20，低于旧基线 10/20；0/3、1/3、2/3、3/3 分布为 11/4/4/1。共 15 份合法报告、45 次被 Service 拒绝；主要失败分类为 evidence 25、experience_fact 11、bonus 5、tradeoff 3、其他模型不服从 1。
- 总体人工三档方向一致为 9/20（45%），低于旧基线 10/20（50%）；在至少有一份合法报告的 9 个样本内部为 9/9，但该内部值不替代总体分母。明显高匹配评低和明显无关评高均为 0；仅有合法结果的同岗位可比较对为 4 对，排序违反为 0，不能代表全部岗位排序已验证。
- 三次全部合法仅 1/20，低于旧基线 5/20；该唯一稳定样本最大分差为 0，因此分差不超过 5 为 1/1。三次全合法样本中跨两个以上展示区间和单项明显方向反转均为 0，但稳定样本覆盖过低，不能解释为稳定性改善。
- 60 次 Schema 合法响应的自动审计中，正分基础事项证据 329/329 可定位，额外亮点证据 41/41 可定位；15 份最终合法报告中的确定性严重事实/grounding 问题为 0。全部模型响应中另有 33 次因事实 grounding 或年限事实问题被严格校验拒绝，其中年限事实冲突/缺少事实 key 等命中 22 项；投递后事实误用、敏感属性评分、招聘决定建议均为 0。亮点与基础事项重复 1 项、与岗位无关 4 项；“未体现”写成“不会”和“缺少量化成果”写成经历无效均为 0。这些被拒绝输出没有形成合法报告或业务持久化。
- JD 与筛选合计 80 次业务调用，input/output token 为 `144,127/66,881`，总计 `211,008`；额外基础设施调用为 0。正式 JD 结果保存为 `2026-08-21-stage7-step9-jd-decomposition-revalidation-results.json`，下游诊断保存为 `2026-08-21-stage7-step9-full-chain-diagnostic-results.json/.md`，均未覆盖历史结果。
- 本模式直接测试 Pydantic Schema、纯 Service 与真实 DeepSeek Adapter，不经过 React、普通 FastAPI 幂等入口、SQLAlchemy Model、PostgreSQL 业务持久化或浏览器。执行前后 PostgreSQL 的 Job、Plan、Application、Resume、ScreeningRun、ScreeningReport 均为 0 行；HR 决策、招聘阶段和生命周期状态没有修改。四个历史 JSON 的 SHA-256 在 dry-run、真实调用和结果写入后保持不变；本批没有新增或修改 migration。
- 结论与停止点：小步骤 9 未通过，建议返回 JobEvaluationPlan 的模型不服从/Prompt 表达与 Service 边界分类层，重点处理 JD18 明确要求被判为 context 的根因；JD16 的冻结 outcome 记录差异也应在下一轮先确认口径。下游诊断显示合法报告率和稳定性未改善，后续分别返回筛选 evidence、experience_fact、bonus、tradeoff 对应层，但本批不修复、不进入步骤 10，并在此停止等待用户确认。

## 15. 实施总门禁

1. 用户明确确认本设计补充前，不得修改业务代码、测试、Prompt、Schema、Model、数据库或验收结果。
2. 实施时必须按第 14 节逐批执行，每轮只完成一个批次；不得跳序、合并批次或并行进入小步骤 10—13。
3. 任何 migration 只能新增向前 revision，不修改既有 migration。
4. 不输出 DeepSeek API Key，不使用 Mock/Fake 冒充真实质量结果。
5. 定向调试或合并 9-I 失败时停留在小步骤 9 继续分类；下游阻塞样本保留在 20 组分母，不通过删样本、改分母、放宽 required/追溯/安全校验或反复重试宣称通过。
