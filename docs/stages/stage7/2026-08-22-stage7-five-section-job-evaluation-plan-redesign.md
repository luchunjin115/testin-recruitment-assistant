# 阶段 7 五段式 JD 评价计划重设计补充

> 日期：2026-08-22
>
> 状态：业务合同与 7R-A—7R-H 实施顺序已完成讨论，文档草案待用户最终复核；最终确认前不得实施业务代码
>
> 上游权威文档：`../stage6/2026-08-21-stage6-five-section-jd-remediation-design.md`
>
> 上游验收记录：`../stage6/2026-08-22-stage6-five-section-jd-remediation-acceptance.md`
>
> 被补充文档：`2026-08-20-stage7-jd-driven-ai-screening-redesign.md`
>
> 历史质量资料：`2026-08-21-stage7-step9-jd-decomposition-quality-remediation-design.md`

## 1. 文档目的与权威边界

阶段 6 已将当前 Job 从旧 `description + JobRequirementsV1` 原子切换为五个普通多行文本字段：

- `job_background`
- `job_responsibilities`
- `candidate_requirements`
- `preferred_qualifications`
- `public_notes`

旧阶段 7 的 JobEvaluationPlan 仍依赖混合 `description`、结构化技能、最低年限、学历和经历字段，因此不能通过替换字段名继续使用。本设计重新规定五段式 JD 如何形成稳定、可追溯、不可直接编辑的评价计划，并规定 Application 与 Screening 恢复门禁、历史兼容、质量样本和实施顺序。

本文替代原阶段 7 设计中以下旧合同：

1. 第 1 节固定流程中“AI 自由文本拆解 + 程序补齐结构化要求”的上游部分。
2. 第 3.1 节第 2—3 项旧 B+C 生成方案。
3. 第 4.1 节对 `JobRequirements` 的依赖。
4. 第 5.1 节旧 JobEvaluationPlan 输入、coverage 和版本合同。
5. 第 6 节全部旧 JD 评价事项生成合同。
6. 第 13—14 节中由旧计划输入决定的状态、过期和指纹语义。
7. 第 17—18 节中与旧计划生成、错误和分层职责有关的内容。
8. 第 20.1、21.1、22 节中依赖旧 JD 样本的验收合同。
9. 第 23 节小步骤 9—13 的后续实施顺序。

原阶段 7 下列已经实现的能力继续有效，除本文明确收紧的恢复门禁外不重新设计：

- Candidate、Application 与当前 Resume 的关系；
- `Application.applied_at` 固定评价时间基准；
- Resume 可用性、脱敏和经历时间事实；
- 单次严格 AI 报告、证据定位和安全校验；
- ScreeningRun、幂等和当前成功报告事务替换；
- 新运行失败时保护旧成功报告；
- 单人和最多 20 人小批量重新评估；
- HR 通过、备选、淘汰、招聘阶段和生命周期不受 AI 自动修改。

发生冲突时，本文对五段式评价计划、计划恢复门禁、质量样本和 7R-A—7R-H 顺序拥有更高权威性。旧质量结果继续保留为历史基线，不作为新合同验收结果。

## 2. 当前事实与受控暂停

### 2.1 阶段 6 已完成事实

五段式 Job 已贯通：

```text
React 五段式岗位表单
        -> FastAPI Job API
        -> Pydantic Job Schema
        -> JobService
        -> SQLAlchemy Job Model
        -> PostgreSQL jobs 五段式列
```

草稿只要求标题；岗位开放时岗位职责和任职要求必填。五个字段保存普通文本，保留内部换行、编号和项目符号，不保存 HTML。

### 2.2 2026-08-22 设计前只读基线

```text
分支：2lcj
HEAD：c169c55d2e5a111b6422a8a88dcf857e7fe9388c
上游：origin/2lcj
ahead/behind：0/0
Alembic current/head：f2b8c6d1a940/f2b8c6d1a940

jobs=0
applications=0
candidates=2
resumes=2
job_evaluation_plans=0
screening_reports=0
screening_runs=0
stage_histories=0
```

阶段 6 验收曾记录 `resumes=9`，本次实时只读查询为 `resumes=2`，说明验收后数据库内容或连接环境发生过变化。本设计不修改、恢复或解释这些 Resume 行；进入任何实施批次前必须重新预检。

### 2.3 当前暂停方式

- Job 创建、编辑、开放、关闭和重新开放不触发旧评价计划。
- generate/regenerate 固定返回 HTTP 503 与 `JOB_EVALUATION_PLAN_CONTRACT_UPGRADE_IN_PROGRESS`。
- React 不展示旧生成或重新生成按钮。
- 历史计划只能只读查看。
- 五段式 Job 不交给旧 Adapter。
- Screening 对开放岗位保持 `waiting_plan`，关闭岗位为 `paused`。
- 新设计最终确认前不调用真实 DeepSeek。

## 3. 目标、包含与不包含

### 3.1 目标

1. 从五段式 Job 生成字段优先级明确、原文可追溯的 JobEvaluationPlan 3.0。
2. DeepSeek 负责语义审阅和最小事项拆分，程序负责确定性边界和安全校验。
3. 任职要求、加分项和岗位职责分别稳定形成 `required/preferred/general`。
4. 岗位背景只作上下文，候选人可见备注完全排除。
5. 评价计划失败不阻止岗位开放，也不得以降级计划冒充成功。
6. 只有当前 3.0 ready 计划可以恢复 Screening。
7. 保留旧计划、旧报告、异步运行和 HR 决策的历史解释能力。
8. 使用完整、复杂、虚构的五段式 JD 和 JD/Resume 样本完成真实质量验收。

### 3.2 包含

- JobEvaluationPlan 3.0 input snapshot、source unit、item、warning 和 review summary；
- 五段式切片、Prompt、AI 输出 Schema、Adapter、Service 和 API；
- 两层指纹、过期、幂等、自动生成与显式重试；
- Application/Screening 恢复门禁；
- React 计划查看、来源、警告和操作；
- 一条新的向前 migration 与历史计划只读共存；
- 自动化、真实 PostgreSQL/API、真实 DeepSeek 和浏览器验收。

### 3.3 不包含

- AI 生成、润色或自动填写 JD；
- HR 直接编辑评价计划或恢复 Rubric；
- 权重、淘汰阈值、Python 加权评分或 `unknown`；
- 按换行生成临时或降级计划；
- 修改既有 migration 或旧质量结果；
- 自动重评已有成功报告的全部 Application；
- 公开投递、面试、Offer、录取、登录/RBAC、Agent、RAG 或阶段 8 能力。

## 4. 固定业务流程

### 4.1 首次开放

```text
HR 保存并开放完整五段式 Job
        ↓
Job 事务先成功提交
        ↓
后台生成 JobEvaluationPlan 3.0
        ↓
程序切出三个评价字段的 source units
        ↓
DeepSeek 逐片段审阅并拆出最小评价事项
        ↓
程序验证来源、优先级、去重、数量和完整性
        ↓
保存 ready 或 failed 计划
        ↓
ready 后协调无成功报告的等待 Application 首次初筛
```

计划生成失败不回滚已经开放的 Job。

### 4.2 开放岗位编辑

1. JobService 先按阶段 6 合同保存合法 Job。
2. 若进入指纹的字段变化，旧当前计划标记 outdated。
3. 引用旧计划的当前成功报告标记过期，但不删除。
4. 不立即自动调用 DeepSeek，避免连续编辑产生无效成本。
5. HR 查看修改后显式点击“按当前 JD 生成”。

### 4.3 关闭与重新开放

- 关闭不使计划或报告过期，但暂停等待和新 Screening。
- 已发出的计划或筛选请求可以完成；保存前仍校验输入是否变化。
- 未修改指纹字段时重新开放，复用当前 ready 计划。
- 关闭期间修改过指纹字段时重新开放，自动开始生成新计划。
- 不自动批量重评已有成功报告的历史 Application。

## 5. 五段式 AI 输入边界

| Job 字段 | 是否进入计划 Prompt | 是否生成事项 | 固定优先级 |
| --- | --- | --- | --- |
| `title` | 是，只作上下文 | 否 | 无 |
| `department` | 是，只作上下文 | 否 | 无 |
| `job_background` | 是，只作上下文 | 否 | 无 |
| `job_responsibilities` | 是 | 是 | `general` |
| `candidate_requirements` | 是 | 是 | `required` |
| `preferred_qualifications` | 是 | 是 | `preferred` |
| `public_notes` | 完全排除 | 否 | 无 |
| `location` | 否 | 否 | 无 |
| `employment_type` | 否 | 否 | 无 |
| `headcount` | 否 | 否 | 无 |

`public_notes` 不得出现在 Prompt、input snapshot、source units、指纹、事项、报告或模型调用日志中。地点、用工类型和招聘人数属于 Job 业务事实，但不是评价计划生成输入；若出差、现场办公或合同性质确实是候选人条件，HR 必须将要求明确写入任职要求。

字段位置拥有最终优先级。字段内措辞冲突时，DeepSeek 不得移动字段或改变优先级，程序保留字段优先级并生成 `priority_signal_conflict` warning。

## 6. Source unit 确定性切片

### 6.1 定义

source unit 是程序从三个评价字段中按排版确定性生成的连续原文片段。程序切片只界定“模型必须审阅哪些原文”，不创建技能、年限、学历或其他评价事项。

### 6.2 生成规则

1. 空行分隔的自然段形成不同 source unit。
2. `1.`、`1、`、`（1）`、`-`、`*`、`•` 等列表项开始新 source unit。
3. 同一列表项下的缩进续行、冒号说明和同编号连续说明并入该 source unit。
4. 普通连续文字可按句号、问号、感叹号和分号形成候选片段。
5. 不按逗号、顿号、“和”“及”或 `and` 机械拆成事项。
6. 保留内部换行、空行、大小写、标点、编号和项目符号。
7. 不静默截断超长输入或过多片段，无法安全处理时受控失败。

稳定 ID 使用字段名和字段内序号：

```text
job_responsibilities:0001
candidate_requirements:0001
preferred_qualifications:0001
```

### 6.3 最小评价语义

DeepSeek 按“能否分别根据简历评分”判断拆分：

- 两部分可能得到不同分数时通常拆开；
- 拆开会破坏原意、制造重复或拆散固定组合概念时保留为一项；
- 一行可以形成多个事项；
- 同一事项可以引用包含换行的连续原文；
- 不允许用一个包含整段的 source quote 冒充多个要求已经分别识别。

例如“熟悉 Python、PostgreSQL，并具备跨部门沟通能力”通常拆为三项；“能够使用 Python 构建 FastAPI 服务”可以作为一个完整能力事项。

### 6.4 每段必须有结论

每个 source unit 必须恰好返回一次：

- `evaluation`：产生一个或多个评价事项；
- `non_evaluation`：公司介绍、福利、宣传、招聘流程、候选人说明或其他非评价内容。

明显岗位要求被标成 non-evaluation 时整次失败，但硬校验范围必须保持狭窄：

- 只检查三个评价来源字段；
- 只阻止无需推测即可确认的直接职责、强制要求或优先条件被整体丢弃；
- 不能只因出现“负责”“优先”等单个词就失败；
- 不能根据关键词自行生成事项。

“负责招聘平台后端开发”“必须具备三年以上 Python 经验”“RAG 经验优先”被丢弃属于硬冲突；“团队负责为员工提供培训”“我们提供五险一金”可以是 non-evaluation。

## 7. DeepSeek 与程序职责边界

### 7.1 DeepSeek 负责

- 审阅每一个 source unit；
- 判断 evaluation/non-evaluation；
- 拆分最小可评价语义；
- 选择支撑事项的最小连续原文；
- 生成简洁标题；
- 分类为 `skill/experience/responsibility/education/other`；
- 提出保守的语义重复关联；
- 识别宣传、福利和招聘流程。

### 7.2 程序负责

- source unit、稳定 ID 和不可变来源表；
- source unit 全量审阅校验；
- `source_unit_id/source_field/source_quote` 一致性和原文定位；
- 按字段固定 `required/preferred/general`；
- 完全相同或规范化后相同事项的确定性去重；
- 对模型提出的语义重复关系进行来源、类别和优先级验证；
- 事项数量、warning、版本、指纹、状态和事务；
- 决定 ready/failed，不保存可误用的部分成功结果。

### 7.3 程序禁止

- 根据 Python、本科、三年等关键词创建事项；
- 从 title、department 或 job_background 推测隐藏要求；
- 使用旧 JobRequirementsV1 补项；
- 为降低数量强行合并独立要求；
- 改变原文强弱语气或字段优先级；
- 在模型失败后按换行生成正式、临时或 degraded 计划。

旧方案是“AI 拆解 + 程序从结构化字段补项”；新方案固定为“AI 拆解 + 程序验证完整性”。

## 8. JobEvaluationPlan 3.0 合同

### 8.1 Input snapshot

```json
{
  "schema_version": "3.0",
  "job_context": {
    "title": "AI 应用工程师",
    "department": "技术研发部",
    "job_background": "建设面向企业客户的 AI 应用平台"
  },
  "evaluation_fields": {
    "job_responsibilities": "负责 AI 应用设计、开发和上线",
    "candidate_requirements": "具备 Python 后端开发经验",
    "preferred_qualifications": "有 RAG 项目经验者优先"
  },
  "source_units": [
    {
      "source_unit_id": "candidate_requirements:0001",
      "source_field": "candidate_requirements",
      "ordinal": 1,
      "source_text": "具备 Python 后端开发经验"
    }
  ]
}
```

input snapshot 不保存 `public_notes/location/employment_type/headcount/status/updated_at`，也不保存 Resume 或 Application。

### 8.2 Source unit

| 字段 | 规则 |
| --- | --- |
| `source_unit_id` | 当前快照唯一且稳定 |
| `source_field` | 只能是三个评价字段 |
| `ordinal` | 字段内原始顺序，从 1 开始 |
| `source_text` | 保留排版的完整连续原文 |

### 8.3 Evaluation item

```json
{
  "key": "item:0001",
  "title": "Python 后端开发经验",
  "category": "experience",
  "priority": "required",
  "sources": [
    {
      "source_field": "candidate_requirements",
      "source_unit_id": "candidate_requirements:0001",
      "source_quote": "具备 Python 后端开发经验"
    }
  ]
}
```

- `key` 在不可变计划内稳定唯一，ScreeningReport 按它关联单项评价。
- `title` 允许受控概括，但不得增加技能、程度、年限、经历类型或强制语气。
- `source_quote` 必须是对应 source unit 中未经翻译或改写的连续原文。
- 中英文混合保持原文；`LLM/RAG/SaaS/C++/C#/Node.js/A/B` 等写法不得擅改。
- `category` 只用于归类展示，不对应权重、上限或淘汰规则。
- `sources` 至少一项；去重后的事项保存全部有效来源。

### 8.4 多来源与 priority

字段固定映射：

```text
candidate_requirements       -> required
preferred_qualifications    -> preferred
job_responsibilities        -> general
```

重复事项的优先级按 `required > preferred > general` 取最高值，同时保留全部来源。DeepSeek 不输出最终 priority。

保守去重只合并能够确认的同一语义；“Python 开发”与“使用 Python 构建高并发服务”不因共享关键词自动合并。

### 8.5 Source review summary

新合同删除 `structured_coverage` 和 `source_type` 的运行语义，改用：

```json
{
  "rule_version": "five_section_source_units_v1",
  "total_units": 8,
  "reviewed_units": 8,
  "evaluation_units": 6,
  "non_evaluation_units": 2,
  "all_reviewed": true,
  "units": [
    {
      "source_unit_id": "candidate_requirements:0002",
      "disposition": "non_evaluation",
      "non_evaluation_reason": "recruitment_process",
      "item_keys": []
    }
  ]
}
```

`all_reviewed` 由程序比对输入和输出计算，不能信任模型声明。它证明每段已被处理，不能证明语义判断一定正确。

### 8.6 Warnings

3.0 warnings 使用受控对象：

```json
{
  "code": "limited_basis",
  "message": "当前计划只有 3 项评价事项，评价依据有限",
  "source_unit_ids": []
}
```

首版只允许：

- `limited_basis`：最终 1—4 项；
- `priority_signal_conflict`：字段位置与“必须/优先”等措辞冲突；
- `misplaced_non_evaluation_content`：评价字段中存在宣传、福利或流程内容。

来源缺失、明显要求遗漏、伪造 source ID、超过上限等危险问题必须失败，不能降级为 warning。

### 8.7 数量边界

| 最终事项数 | 行为 |
| ---: | --- |
| 0 | failed，`JOB_EVALUATION_PLAN_NO_ITEMS` |
| 1—4 | ready + `limited_basis` |
| 5—30 | 正常 ready |
| 31 及以上 | failed，`JOB_EVALUATION_PLAN_TOO_MANY_ITEMS` |

最多 30 项，不静默截断，不为通过上限而强行合并独立事项。limited 不是单独状态。

### 8.8 状态

```text
generating -> ready
           -> failed
ready -> outdated
generating -> outdated（生成期间输入变化）
```

- generating、failed、outdated 都不能进入 Screening。
- failed 可以保存输入快照、版本、调用诊断和安全错误，但不保存可被误用的部分成功事项。
- outdated 计划和引用它的历史报告不删除。

### 8.9 版本

| 合同 | 新版本 |
| --- | --- |
| Prompt | `job_evaluation_plan_v5` |
| AI 输出 Schema | `3.0` |
| 最终计划 Schema | `3.0` |
| input snapshot | `3.0` |
| source-unit 规则 | `five_section_source_units_v1` |
| 指纹规则 | `job_evaluation_input_v3` |
| 破坏性生成合同 | `five_section_plan_generation_v1` |

旧 1.0/2.0 计划只读，返回 `contract_outdated=true`，不能用于五段式 Job 的新 Application，不就地改写为 3.0。

## 9. 指纹、幂等与过期

### 9.1 两层指纹

`jd_fingerprint` 包含：

- title；
- department；
- job_background；
- job_responsibilities；
- candidate_requirements；
- preferred_qualifications。

`input_fingerprint` 包含：

- jd_fingerprint；
- input snapshot Schema；
- source-unit 规则；
- AI 输出 Schema；
- 最终计划 Schema；
- 破坏性生成合同版本。

`public_notes/location/employment_type/headcount/status/updated_at` 不进入指纹。

相同 Job、相同 input fingerprint 已有 current generating/ready/failed 时，普通请求幂等复用，不创建重复行或重复调用模型。

### 9.2 文本规范化

不改变指纹：

- 整段首尾空白；
- 每行末尾无意义空格；
- CRLF/LF/CR 的换行编码差异。

改变指纹：

- 正文内部换行、空行、顺序、大小写或标点变化；
- 拆分或合并列表项；
- `-`、`•`、`1.` 等项目符号变化；
- 中英文术语写法变化。

内部排版影响 source-unit 边界和 source quote，不能全部压平后复用旧计划。

### 9.3 合同升级

输入字段、切片、输出字段、追溯、优先级、去重或数量语义变化时升级破坏性生成合同并改变 input fingerprint。

普通 Prompt 措辞澄清、示例文字、模型返回别名、SDK 超时或连接配置变化只记录审计版本，不自动使全部计划过期。

### 9.4 Job 变化

- 进入 jd fingerprint 的字段变化：旧计划 outdated，旧报告增加 `job_evaluation_input_changed`。
- public_notes、地点、用工类型或人数变化：计划和报告不过期。
- 新计划 ready：已有成功报告继续只读并保持过期，不自动重评。
- 新计划失败：旧成功报告继续保留。
- Job 变化发生在生成或筛选运行中：返回后再次比较指纹，不允许旧输入结果成为当前成功结果。

## 10. 模型调用、重试与失败

### 10.1 自动重试

最多“首次调用 + 1 次 Service 显式自动重试”。只有以下基础设施错误重试：

- 网络连接失败；
- 请求超时；
- 限流；
- DeepSeek 服务端 5xx；
- 临时连接中断。

SDK 自动重试关闭，确保实际调用次数透明。

以下错误不自动重试：

- Key、鉴权或配置错误；
- JSON 或 Schema 不合法；
- source unit 遗漏、重复或伪造；
- source quote 无法定位；
- 明显岗位要求被丢弃；
- 数量、重复或其他业务校验失败。

内容失败直接进入 failed，由 HR 显式重试或修改 JD。不得通过多次碰运气选择较好响应。

### 10.2 失败边界

- Job 开放状态不受影响。
- Application 保持 waiting_plan，不记为筛选失败。
- 不生成 line-based、temporary 或 degraded 计划。
- 不回退使用旧合同计划。
- Fake/Mock 只用于自动化，不属于生产降级路径。
- 原始模型响应、API Key、调用栈、SQL、内部路径和环境变量不返回浏览器。

## 11. HR 页面与操作

### 11.1 入口与展示

沿用岗位列表的 JobEvaluationPlanDrawer。顶部展示状态、岗位、生成时间、事项数量、是否对应当前 JD、warning 和合同版本，不展示原始 JSON、Prompt 或模型响应。

事项按以下顺序分组：

1. 任职要求：required；
2. 加分项：preferred；
3. 岗位职责：general。

页面固定解释优先级来自 JD 字段，只用于解释原意，不代表固定权重或自动淘汰。

每项展示标题、类别、优先级、来源数量，并允许展开全部 source quotes。多来源用于解释去重和最终 priority。

### 11.2 状态与按钮

| Job/计划状态 | 页面行为 |
| --- | --- |
| draft，无计划 | 说明开放后生成；无生成按钮 |
| open，无计划 | `生成评价计划` |
| generating | 自动刷新；禁止重复生成 |
| ready 且当前 | 只读查看，不提供同输入抽卡式重生成 |
| ready + limited | 可用于 Screening，同时提示依据有限 |
| failed | `重试生成`、`修改 JD` |
| outdated | `按当前 JD 生成`、查看历史计划 |
| 旧 1.0/2.0 | 历史只读；可按五段式新规则生成 |
| closed | 历史只读；不允许生成或重试 |

generating 轮询在 ready/failed/outdated、关闭抽屉、离开页面或岗位关闭时停止。本阶段不增加取消已发送模型请求。

### 11.3 纠错

HR 不直接编辑计划。发现拆解错误时查看 source quote，回到 JD 修改职责、任职要求或加分项，再生成新计划。

允许直接编辑计划会造成候选人看到的 JD 与 AI 使用标准不一致，并重新形成已废弃的第二套 Rubric，故明确禁止。

### 11.4 Warning 文案

- limited：可用但评价依据有限，建议检查 JD 完整性；
- priority conflict：保留字段优先级，提示 HR 将内容移动到正确字段；
- misplaced content：说明宣传、福利或流程未生成事项，建议整理 JD。

危险失败只显示安全、可操作的信息和稳定错误码。

## 12. Application 与 Screening 恢复门禁

### 12.1 唯一可用计划

进入 Screening 的计划必须同时满足：

- status=ready；
- is_current=true；
- contract_outdated=false；
- schema/input snapshot 为五段式 3.0；
- jd/input fingerprint 与当前 Job 和合同一致；
- 1—30 项；
- source_review_summary.all_reviewed=true；
- Job=open。

旧合同、生成中、失败、过期、部分成功、Fake/Mock 或降级计划一律不可用。

### 12.2 等待原因

| 状态 | 原因码 |
| --- | --- |
| paused | `job_closed` |
| waiting_resume | 现有 Resume 处理原因 |
| waiting_plan | `plan_missing` |
| waiting_plan | `plan_generating` |
| waiting_plan | `plan_failed` |
| waiting_plan | `plan_outdated` |
| waiting_plan | `plan_contract_outdated` |
| queued | 条件齐全，等待运行 |
| running | 正在评价 |
| succeeded | 当前报告成功 |
| failed | 实际筛选运行失败 |

多个阻塞条件的主状态优先级为“岗位关闭 > Resume 不可用 > 计划不可用 > 正常排队”，后台可保留全部原因。

### 12.3 首次自动初筛

Application 第一次同时满足以下条件时自动排队：

- Job 开放；
- 当前 Resume 可用；
- 当前 3.0 计划 ready；
- 尚无当前成功报告；
- 没有相同输入 queued/running；
- Application 仍处于既有合同允许评价的生命周期。

触发可以来自新 Application、Resume 后来可用、计划后来 ready 或岗位重新开放。AI 只生成报告，不修改 HR 决策和招聘状态。

### 12.4 历史 Application

- 尚无成功报告：新计划 ready 后自动完成首次评价。
- 已有成功报告：旧报告标记过期，不自动重评；HR 单人或最多 20 人显式重新评估。
- 新报告成功后事务替换当前报告；失败时旧报告保留。
- Resume 变化继续使用原 Application.applied_at，不自动重评已有成功报告。

### 12.5 运行期间输入变化

已经发出的请求可以完成，但保存前重新比较 Job、Plan、Resume 和时间事实指纹。变化后本次结果不得替换当前成功报告，ScreeningRun 记录 `SCREENING_INPUT_OUTDATED_DURING_RUN`，Application 回到对应等待状态。

仅岗位关闭而输入未变化时，已运行任务可以完成保存；等待任务暂停。

## 13. Migration 与历史数据

### 13.1 当前表事实

现有表已具有 items、warnings、input snapshot、两种 fingerprint、版本、状态、is_current、structured_coverage 和 free_text_coverage；唯一约束已经是 `(job_id, input_fingerprint)`，状态和当前计划唯一性无需重建。

### 13.2 新 migration

新增一条接在 `f2b8c6d1a940` 后的向前 revision：

1. 新增 `source_review_summary JSONB NULL`。
2. 将 `structured_coverage` 改为允许 NULL，退出 3.0 运行合同。
3. `free_text_coverage` 保留为 2.0 legacy-only。
4. 增加 summary 为空或 JSON object 的约束。
5. 3.0 ready 必须具有 source_review_summary。
6. 3.0 不得写 structured_coverage/free_text_coverage。
7. 原 2.0 ready coverage 约束继续有效。

当前开发库 plan/report/run 均为 0，可以直接切换结构而无需内容迁移。

### 13.3 非空环境

- 不停止纯追加兼容 migration，除非发现未知结构。
- 不清空或删除旧计划。
- 不把旧计划转换成 3.0。
- 不修改历史报告或运行日志外键。
- 新列以 NULL 加入，旧行保持原值。
- 生成 3.0 时，同一事务将旧 current 设为 outdated/is_current=false，再插入新 current。
- 未知旧内容或约束外数据必须停止并单独讨论。

### 13.4 历史兼容

- API GET 按 schema_version 只读解析 1.0/2.0/3.0。
- generate/regenerate 恢复后只生成 3.0。
- 不提供旧生成参数，不双写旧、新 JSON。
- 不允许客户端指定 Prompt 或 Schema 版本。
- 兼容的是历史读取，不是旧生成能力。

### 13.5 Alembic 原则

- 不修改任何既有 revision。
- 临时 PostgreSQL 完成空表 upgrade→downgrade→upgrade。
- 使用旧计划和历史外键夹具验证升级无改写。
- 正式库只做确认后的向前升级。
- downgrade 发现 3.0 行时主动停止，不删除 3.0 数据冒充可回滚。
- 执行并记录 current/head/check 和业务表计数。

## 14. 五段式质量样本

### 14.1 总体原则

建立两个独立样本集：

1. 20 份 JobEvaluationPlan 五段式 JD；
2. 20 组可用五段式 JD + Resume 初筛样本。

除刻意设计的 limited 和 0 项边界外，正常 JD 均达到真实招聘 JD 复杂度，不使用一两句玩具文本。岗位由项目自行设计，全部使用虚构公司、业务和人员信息，不保留模板占位符。

完整正常样本通常包含：

- 1—2 段岗位背景；
- 3—5 个职责分组；
- 6—12 条包含复合句、跨行或项目符号的职责；
- 6—12 条技能、经历、学历或软性要求；
- 2—5 条加分项；
- 一段候选人可见但不参与 AI 的备注；
- 约 8—25 个最终事项，复杂样本允许接近 30。

岗位职责中的 `40%/30%/20%/10%` 等工作占比只作原文上下文，不转换为评分权重。

### 14.2 20 份计划样本矩阵

| ID | 岗位 | 核心覆盖 |
| --- | --- | --- |
| J5-01 | Python 后端工程师 | 标准中文分组、技能与工程经历 |
| J5-02 | React 前端工程师 | 一行多个独立要求、工具组合 |
| J5-03 | AI/RAG 应用工程师 | 中英混合、技术名词保留 |
| J5-04 | 数据分析师 | 纯英文职责与要求 |
| J5-05 | SaaS 产品经理 | 路线图、需求分析和跨部门协作 |
| J5-06 | 供应链产品运营 | 职责、能力和业务指标边界 |
| J5-07 | 新媒体运营专员 | 采用用户提供样式复杂度，含四组职责、比例、平台、活动、数据、KOC/KOL、软性要求和福利排除 |
| J5-08 | 企业客户成功经理 | SaaS、onboarding、renewal 中英混合 |
| J5-09 | 应届后端工程师 | 复杂背景但评价字段刻意只有 1—4 项，预期 limited |
| J5-10 | 应届产品助理 | 跨行说明，评价字段刻意只有 1—4 项，预期 limited |
| J5-11 | 高级分布式架构师 | 高级岗位、多组复杂职责 |
| J5-12 | 高级 AI 平台工程师 | 跨行要求、缩进续行和平台治理 |
| J5-13 | 电商内容运营 | 背景含宣传与技术栈但不得生成事项 |
| J5-14 | B2B 产品经理 | 三个评价字段存在语义重复 |
| J5-15 | 海外社媒运营 | 复杂编号、符号、嵌套续行和中英文平台名 |
| J5-16 | 雇主品牌运营 | public_notes 含技能与面试说明但完全排除 |
| J5-17 | 安全合规分析师 | 字段与必须/优先措辞冲突，验证 warning |
| J5-18 | AI 应用工程师 | JD 中包含类似模型指令的恶意文本 |
| J5-19 | 品牌推广协作岗位 | 职责和要求非空但全为宣传/流程，预期 0 项失败 |
| J5-20 | 商业化运营负责人 | 31 个清晰独立要求，预期超过上限失败 |

J5-01—J5-18 必须 ready，其中 J5-09/J5-10 必须 limited；J5-19 必须 no_items；J5-20 必须 too_many_items。所有人工标签在真实调用前冻结。

旧 JD18 永久保留为旧合同历史失败，不删除、不改写、不计入新合同；J5-20 独立承担五段式超过 30 项边界。

### 14.3 public_notes 样本

J5-16 在备注中写入技能和面试说明，自动化必须证明备注不进入 Prompt、快照、source units、指纹、事项或报告。另使用只有 public_notes 不同的成对 Job，证明复用同一评价输入且额外模型调用为 0。

## 15. 质量指标、调用和结果记录

### 15.1 计划质量

- 18/18 正常 JD ready；
- 2/2 边界结果正确；
- 明确 required 召回 100%；
- 全部人工标注主要语义召回不低于 95%；
- source unit 审阅率 100%；
- source 引用合法且可定位 100%；
- priority 与字段一致 100%；
- 擅自新增要求、明显重复、错误合并、背景/备注污染和宣传误识别均为 0；
- 预期 warning 命中 100%。

任一不可追溯事项、擅自新增 required 或背景/备注污染都会阻止计划质量门禁通过。

### 15.2 报告质量

- 20/20 样本至少一份合法报告，失败样本不得移出分母；
- 正分事项和额外亮点证据可定位 100%；
- 人工高/部分/低三档总体方向一致率不低于 80%；
- 明显高匹配不评为低，明显无关不评为高；
- 同岗位强样本整体排序高于弱样本。

该指标只能称为岗位匹配方向一致性，不能称为招聘准确率。

### 15.3 三次稳定性

同一 JD、计划、Resume、applied_at、时间事实、Prompt、Schema 和模型配置直接真实调用三次：

- 至少 18/20 三次全部合法；
- 三次全合法样本中至少 90% 的综合分最大差值不超过 5；
- 不跨越两个以上展示区间；
- 单项评分无明显方向反转。

### 15.4 安全硬门槛

以下必须为 0：

- 严重事实虚构；
- 敏感属性参与评分；
- 招聘决定建议；
- 投递后经历当作投递时事实；
- 年限结论与程序时间事实冲突；
- 把“未体现”写成“候选人不会”；
- 额外亮点与基础事项明显重复。

### 15.5 调用分层

1. Fake/Mock：验证程序合同，成本 0，不计质量。
2. 定向真实调试：独立记录，不挑选最好结果，不计正式门槛。
3. 正式计数：20 次计划生成 + 60 次报告评价，共 80 次业务调用。

7R-F 首轮最多 6 次定向 + 20 次正式；7R-G 首轮最多 6 次定向 + 60 次正式。基础设施自动重试单列。超过定向上限前重新取得用户确认。

每次记录样本、阶段、调用类型、实际模型、input/output/cache token、耗时、重试、Schema、业务结果、拒绝层和估算费用。执行前记录当时官方单价、币种、日期和来源；估算费用不冒充实际账单。

定向、正式计划、定向报告、正式报告和浏览器结果使用独立带日期文件，不覆盖旧 JSON/Markdown。

## 16. 自动化与人工验收范围

### 16.1 后端

- 3.0 Schema、旧计划只读和额外字段拒绝；
- source-unit 切片、稳定 ID、原文保留和全量审阅；
- 一行多要求、跨行要求、复杂项目符号和中英文；
- title 受控概括、source quote 连续原文；
- priority、sources、去重、warning 和 0—30 边界；
- 两层指纹、过期、幂等和慢响应防覆盖；
- 重试分类、失败不回滚 Job 和无降级计划；
- Application/Screening 状态、首次自动评价、报告保护和 HR 决策隔离；
- 旧 1.0/2.0 历史读取但禁止用于新 Screening。

### 16.2 Migration/PostgreSQL

- 新列、可空性和版本约束；
- 空表往返；
- 非空旧计划和报告/运行外键保持不变；
- 3.0 数据 downgrade 主动停止；
- current/head/check；
- 八张业务表前后计数；
- 正式库不使用用户数据测试 downgrade。

### 16.3 前端/浏览器

- 状态和按钮矩阵；
- 三组事项和多来源展开；
- limited、priority conflict、misplaced content；
- failed/outdated/旧合同和 waiting reason；
- 修改 JD 纠错，不出现计划编辑和同输入抽卡重生成；
- 报告过期、旧成功保护和 HR 决策隔离；
- 1440×900、820×1180、390×844；
- 键盘、焦点、轮询终止、普通文本安全和无整页横向溢出。

浏览器使用真实 API/PostgreSQL 与受控固定结果；真实模型质量由独立 7R-F/G 证明，浏览器验收不额外调用 DeepSeek。

## 17. 实施批次、依赖与停止点

每批开始前重新检查 git status、相关差异、分支/HEAD/上游、Alembic current/head、八张业务表计数和上一批结果。每轮只完成一个已确认批次，结束后报告实际修改、链路位置、验证、证明边界和风险，然后停止等待确认。

### 17.1 总体顺序

| 批次 | 唯一目标 | 依赖 | 停止点 |
| --- | --- | --- | --- |
| 7R-A | 自动化合同基线 | 本文最终确认 | 不改生产代码，等待 7R-B |
| 7R-B | 3.0 数据与持久化 | 7R-A 红灯分类 | 不调用模型，等待 7R-C |
| 7R-C | 五段式计划生成 | 7R-B 稳定 | 不恢复 Screening，等待 7R-D |
| 7R-D | Application/Screening 恢复 | 7R-C 计划稳定 | 不改 React，等待 7R-E |
| 7R-E | React 与无真实模型集成 | 7R-D 后端稳定 | 停在真实成本门禁前 |
| 7R-F | 计划真实质量 | 7R-E 全绿与成本授权 | 未通过不得进入 7R-G |
| 7R-G | 报告质量与稳定性 | 7R-F 通过 | 未通过不得进入 7R-H |
| 7R-H | 最终数据库、浏览器与收尾 | 7R-G 通过 | 阶段 7 结束，不进入阶段 8 |

### 17.2 7R-A：自动化合同基线

唯一目标：将本文合同转换为可重复测试，准确分类旧实现缺失能力。

通俗解释：先写考试题，不改答案，证明后续每个修改解决哪一个问题。

允许修改：JobEvaluationPlan Schema/Service/API/Model/migration 测试、Application/Screening 门禁测试、React 计划测试、五段式虚构夹具和本批状态文档。

链路位置：测试覆盖前端→API→Schema→Service→Model→PostgreSQL，不修改生产层。

禁止：生产代码、数据库结构和业务数据、真实 DeepSeek、skip/xfail、删除断言。

交付物：input snapshot、source unit、sources、priority、warning、状态、指纹、过期、数量、历史、Screening 和 UI 合同矩阵；每个预期红灯映射到 7R-B—7R-E。

验证：正常收集；既有无关测试无新增回归；DeepSeek 0 次、成本 0；git diff --check。

完成标志：合同测试和红灯责任完整。失败返回测试/夹具层。停止并等待 7R-B，唯一下一步是数据合同。

### 17.3 7R-B：3.0 数据与持久化

唯一目标：系统可以准确表达、保存和读取 3.0 与旧历史，但不生成真实事项。

通俗解释：先准备可靠的数据盒子，还不让 AI 往里面写内容。

允许修改：`backend/app/schemas/job_evaluation_plan.py`、`backend/app/models/job_evaluation_plan.py`、与版本/指纹/持久化直接相关的最小 Service、一条新 migration 和对应测试。

链路位置：Schema→Model→PostgreSQL。

禁止：Prompt、Adapter、生成工作流、Screening、React、真实 DeepSeek、既有 migration 和旧数据转换。

交付物：3.0 类型、source_review_summary、legacy-only coverage、版本约束、旧计划只读和新 migration。

业务与失败：3.0 ready 缺 summary 拒绝；旧行原样保留；未知历史内容停止；3.0 downgrade 不删数据。

验证：定向 Schema/Model/migration、临时 PostgreSQL 往返、旧计划/外键夹具、正式库确认后的向前升级、current/head/check、DeepSeek 0 次、成本 0。

完成标志：3.0 可持久化且历史不被改写。失败返回 Schema、Model 或 migration 层。停止等待 7R-C。

### 17.4 7R-C：五段式计划生成

唯一目标：从五段式 Job 生成安全、完整、可追溯的 3.0 计划。

通俗解释：让 AI 阅读三块真正用于评价的原文，程序守住来源、优先级和完整性。

允许修改：计划 Prompt、AI 中间 Schema、Adapter、Service、API、source-unit helper、Job 开放后的最小协调入口和对应后端测试。

链路位置：API→Schema→Service→Prompt/Adapter→Model→PostgreSQL。

禁止：Screening 恢复、报告评分合同、React、真实 DeepSeek、降级计划。

交付物：切片、逐段审阅、最小拆项、原文、多来源、priority、去重、warning、0—30、两层指纹、幂等、重试、自动/显式生成和 3.0 API。

失败语义：基础设施最多重试一次；内容失败不重试；Job 不回滚；无旧计划回退；慢响应不覆盖新输入。

验证：Fake/Mock Adapter、定向和后端全量、真实 PostgreSQL + Fake 集成、Job 开放隔离、调用次数断言；DeepSeek 0 次、成本 0。

完成标志：新计划链路可在 Fake 下完整 ready/failed。失败返回切片、Prompt、Schema、Adapter、Service 或 API。停止等待 7R-D。

### 17.5 7R-D：Application 与 Screening 恢复

唯一目标：只让当前 3.0 ready 计划进入初筛并保护旧成功报告。

通俗解释：评价依据没准备好就等待，准备好才筛；旧成功结果不会被失败运行覆盖。

允许修改：Application 协调 Service、ScreeningService、相关 API/Schema、必要状态与过期逻辑和测试。

链路位置：API→Schema→Service→Model→PostgreSQL。

禁止：React、计划 Prompt、报告核心评分/证据/时间原则、真实 DeepSeek。

交付物：waiting 原因、首次自动初筛、旧合同隔离、过期、输入变化拒绝替换、关闭/重开、Resume 变化、最多 20 人重评和 HR 决策隔离。

验证：状态矩阵、幂等、事务替换、失败保护、Application/Resume/时间事实/报告全量、真实 PostgreSQL + Fake；DeepSeek 0 次、成本 0。

完成标志：后端完整恢复且只有合法计划可筛。失败返回协调、ScreeningService 或报告事务层。停止等待 7R-E。

### 17.6 7R-E：React 与无真实模型集成

唯一目标：HR 可以理解并操作新版计划，在真实模型成本前完成程序和页面集成。

通俗解释：先把页面、接口、数据库和所有状态走通，再花钱测试模型质量。

允许修改：JobEvaluationPlanDrawer、岗位/初筛页面、前端 Service/类型/样式/测试、浏览器夹具，以及验收暴露的合同内最小后端缺陷。

链路位置：前端→API，并集成后端到 PostgreSQL。

禁止：真实 DeepSeek、核心业务合同变化、计划编辑、同输入 ready 重生成。

交付物：状态按钮、三组事项、多来源、warning、失败/过期/旧合同、修改 JD、waiting reason 和报告过期展示。

验证：前端定向/全量、TypeScript、Vite、后端全量、migration/PostgreSQL、三档浏览器、键盘/焦点/轮询/安全；受控 Fake，0 次 DeepSeek、成本 0。

完成标志：非 AI 集成门禁全绿。失败返回 React、API 映射或实际后端层。停止并单独等待 7R-F 成本授权。

### 17.7 7R-F：评价计划真实质量

唯一目标：证明 20 份复杂五段式 JD 在真实 DeepSeek 下达到计划门槛。

允许修改：20 份冻结 JD、计划质量脚本/统计/结果，以及定向暴露的本文合同内最小计划修复。

链路位置：Prompt/Adapter→Service→质量验收，不恢复新的产品功能。

禁止：Screening 质量整改、React、门槛放宽、覆盖旧结果、Fake 冒充真实质量。

调用：dry-run 0；首轮定向最多 6；通过后正式 20；基础设施重试单列。超过定向 6 次前重新确认。记录 token、单价和成本。

验证与完成：第 15.1 节全部通过。失败返回 7R-C 的具体责任层，不执行正式报告质量；无论结果均停止。唯一下一步在通过并确认后进入 7R-G。

### 17.8 7R-G：报告质量与三次稳定性

唯一目标：证明新版计划进入下游后的合法率、方向、安全和稳定性。

允许修改：20 组冻结 JD/Resume、报告验收脚本/统计/结果和既有报告合同内最小修复。

链路位置：筛选 Prompt/Adapter→ScreeningService→质量验收。

禁止：计划核心合同、证据/事实/安全门槛放宽、删样本、定向结果替代正式结果。

调用：dry-run 0；首轮定向最多 6；正式 20×3=60；基础设施重试单列。超过定向 6 次前重新确认。记录 token、单价和成本。

验证与完成：第 15.2—15.4 节全部通过。失败返回报告 Prompt、Schema、证据、时间事实、亮点或一致性层；无论结果均停止。通过并确认后进入 7R-H。

### 17.9 7R-H：最终数据库、浏览器与收尾

唯一目标：证明完整产品链真实可操作，并形成阶段 7 最终验收记录。

允许：全量回归、真实 PostgreSQL/API、浏览器、合同内最后最小缺陷、阶段 7 验收文档、PROJECT_STATE、实施计划和文档索引。

链路位置：前端→API→Schema→Service→Model→PostgreSQL 全链。

禁止：真实 DeepSeek 新调用、放宽质量门槛、进入阶段 8/Agent/RAG/登录。

交付物：current/head/check、八表计数、真实 API 主链、三档浏览器、HR 决策隔离、全量自动化和证明边界。浏览器使用 7R-F/G 已验证的固定结果和受控 Adapter，DeepSeek 0 次、成本 0。

完成标志：自动化、migration、计划质量、报告质量、数据库/API 和浏览器全部通过并获用户确认。失败返回实际责任批次。完成后停止，不进入阶段 8。

## 18. 设计门禁与最终停止点

1. 本文获得用户最终确认前，不得修改生产代码、测试、Prompt、Adapter、Schema、Model、API、React、migration 或 PostgreSQL 业务数据。
2. 最终确认只允许进入 7R-A；不等于授权连续执行 7R-B—7R-H。
3. 每批结束后必须停止并等待用户明确确认下一批。
4. 真实 DeepSeek 仅允许在 7R-F/G 且单独确认成本后调用。
5. 任何核心输入、优先级、来源、数量、状态、迁移、质量门槛或批次顺序变化，必须先更新本文并重新确认。
6. 不使用 reset、clean、checkout 覆盖阶段 6 累计工作区修改。
7. 不修改或删除旧 JD18、旧质量 JSON/Markdown 和既有 Alembic revision。
8. 阶段 7 完成前不进入阶段 8；阶段 7 完成后也必须停下等待新的阶段门禁。

本文最终确认后的唯一下一步是 7R-A 自动化合同基线。
