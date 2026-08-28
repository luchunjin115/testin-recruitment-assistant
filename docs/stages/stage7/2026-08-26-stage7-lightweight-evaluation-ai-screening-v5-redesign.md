# 阶段 7：轻量评价清单驱动的 AI 初筛 5.0 重设计

> 日期：2026-08-26  
> 状态：7R5-A—7R5-H 与 7R5-I 唯一真实 raw 已完成；报告/稳定性人工审核暂停。`7R5-IR-A/B`、`7R5-I2-A—C`、`7R5-I2-R1-A—C`、`7R5-I2-R2-A—E` 和 `7R5-I2-R3-A—C` 已完成。计划支持性、报告数量、自然语言年限和无 evidence 同义词机械误拒绝均已按独立批次处理，报告 Service 行为版本为 `lightweight_report_generation_v3`。交接复核发现原 R3-D 只登记最近四例，遗漏 I2-C 的 R10 与 R1-C 的 R16，现已把 R3-D 文档范围纠正为六例；尚未执行 R3-D。`pricing_gate_allowed=false`，禁止进入 I2-D/E、读取 Key、调用模型、恢复人工审核、补跑旧 I、finalize 或进入 7R5-J。Alembic head=`d6e8f0a2b434`。
> 当前权威性：本文件替代 4.0 作为阶段 7 新增实现的唯一业务合同。4.0、3.0 和更早资料只保留历史实现与质量证据，不得继续指导新开发。  
> 一句话目标：不再追求把 JD 拆成大量“原子事实”，而是让 AI 基于完整 JD 生成一份 HR 可编辑、可追溯的轻量评价清单，再用同一把尺子独立评价每份简历。

## 1. 为什么重新设计

阶段 7 的最终目标一直是帮助 HR 做候选人初筛，不是把“岗位 JD 拆解”本身做成产品。

4.0 为了获得极高的事实召回率，采用 `RequirementFact + EvaluationCriterion` 双层合同：先把 JD 拆成大量原子事实，再完整性复核、必要时局部修复，最后归组。正式 20 份真实 JD 只通过 15 份，暴露出事实粒度、warning 和归组稳定性问题。继续沿这个方向整改，容易变成“换一批 JD、修一批特例”，却没有直接提升 HR 的初筛体验。

本次重新确认后的判断是：

- 需要稳定、可解释、可供同岗位候选人复用的评价标准；
- 不需要把 JD 的每一句话都拆成独立事实；
- 完整 JD 可以直接作为模型上下文；
- HR 需要能够修改 AI 建议，最终确认同一岗位的评价清单；
- 评分仍应直观，但不能恢复已经废弃的固定维度和加权公式。

因此 5.0 不是“放弃结构化”，而是把结构化控制在初筛真正需要的层级。

## 2. 5.0 的产品定位

阶段 7 提供的是“AI 初筛辅助意见”，不是自动招聘系统。

固定主流程：

```text
HR 维护完整岗位 JD
→ AI 生成约 5—12 个主要评价点
→ HR 编辑并确认轻量评价清单
→ 系统把完整 JD + 已确认清单 + 当前 Application 的简历交给 AI
→ AI 对每个评价点给 0—10 分并直接给总体 0—100 分
→ 程序校验结构、证据、安全边界和明显矛盾
→ HR 阅读报告并独立作出通过 / 备选 / 淘汰决定
```

系统必须始终明确：

- 分数是“当前简历与当前 JD 的证据匹配建议分”，不是候选人的综合能力分；
- 分数不是录用概率；
- AI 不得自动通过、备选或淘汰候选人；
- 最终招聘决定只属于 HR；
- 阶段 7 不承诺对所有行业和岗位绝对准确。

## 3. 5.0 与 4.0 的关系

### 3.1 保留的能力

以下现有能力继续保留并作为 5.0 基础：

- Candidate、Application、Resume、Job 和 StageHistory 的对象边界；
- 同一个候选人对不同岗位分别形成 Application；
- 每个 Application 只读取自己绑定的当前 Resume；
- `Application.applied_at` 作为不可变评价时间基准；
- 异步 `ScreeningRun`、幂等、并发保护、租约恢复和稳定失败语义；
- 当前成功报告替换与旧成功报告历史保留；
- 迟到响应不能覆盖新输入；
- HR 决策与 AI 运行状态相互独立；
- 敏感属性禁用、原始模型响应不进入正常报告、错误信息脱敏；
- 旧 1.0—4.0 计划和旧报告只读，不改写历史结果。

### 3.2 被替换的能力

5.0 新生成链不再使用：

- `RequirementFact` 原子事实层；
- “每条 fact 必须且只能归入一个 criterion”的归组合同；
- 事实提取 → 完整性复核 → 可选局部修复 → 归组的三至四次模型调用；
- 以 245 条人工 facts、255 个 source units 为核心的 4.0 质量门槛；
- HR 只能无正文确认、不能编辑评价点的限制；
- 逐 fact 评分、criterion 只展示不评分的报告接线。

这些内容继续保留在 4.0 设计和结果文件中作为历史证据，不删除、不覆盖，也不冒充 5.0 验收结果。

### 3.3 明确不恢复的旧 Rubric 能力

5.0 也不得恢复更早已经废弃的：

- 固定五个评分维度；
- 维度权重或评价点权重；
- Python 按技能、年限、学历等规则确定性打分；
- `unknown`、证据覆盖率和阈值封顶公式；
- Python 加权计算总分；
- AI 分数直接改变 HR 决策。

## 4. 岗位输入边界

### 4.1 可进入 AI 上下文的 Job 内容

- `title`：岗位名称，只作上下文；
- `department`：部门，只作上下文；
- `job_background`：岗位背景，只作上下文，不直接评分；
- `job_responsibilities`：岗位职责，可形成评价点；
- `candidate_requirements`：任职要求，可形成评价点；
- `preferred_qualifications`：加分项，可形成评价点。

### 4.2 不得成为评分依据的内容

- `public_notes` 或候选人可见备注；
- 公司宣传、品牌口号、团队氛围；
- 薪酬福利、晋升宣传和办公环境；
- 招聘流程、投递方式、联系人和截止时间；
- 仅用于介绍背景、没有对候选人提出要求的文字。

程序和 Prompt 都要把这些内容标为“非评价内容”。它们不能因为出现在 JD 中就被用于扣分。

## 5. 轻量评价清单合同

### 5.1 数量口径

- AI 通常生成约 5—12 个主要评价点；
- 5—12 是产品建议，不是硬失败边界；
- 简单岗位少于 5 个，只要覆盖主要判断点，可以接受并提示依据较少；
- 复杂岗位多于 12 个，不截断、不直接失败，显示“评价点较多，请 HR 检查是否需要合并”的 warning；
- 技术安全上限暂定 30 个，超过时按内容错误失败，防止异常输出拖垮页面和报告；安全上限不是业务目标。

### 5.2 每个评价点的最小字段

```text
criterion_id          稳定 ID，由程序生成
name                  简短名称
importance            required / preferred / general
description           HR 能看懂的简短说明
screening_focus       初筛时重点寻找什么证据
origin                ai_from_jd / hr_added
sources[]             JD 来源；AI 生成项至少一条
hr_note               HR 补充说明；HR 自增项可填写
```

每条 `source` 至少包含：

```text
source_field           只允许职责 / 任职要求 / 加分项
source_quote           可在冻结 JD 原文中定位的短引用
```

不再要求先创建 `RequirementFact`，也不要求每个句子或数字成为一个独立评价点。一个评价点可以引用多处 JD 原文，但名称、描述和初筛重点必须围绕同一个主要判断主题。

### 5.3 importance 的含义

- `required`：完整 JD 原文明确定义为必须、至少、需要具备、硬性要求、不可缺少或同等强约束；任职要求或岗位职责中的明确强约束都属于 `required`；
- `preferred`：完整 JD 原文明确定义为优先、加分、熟悉更佳、非必须、有则更好或同等弱约束；
- `general`：职责匹配、通用能力或完整原文没有明确强弱信号的主要判断点。

importance 只帮助 AI 和 HR理解重要程度，不是权重，不参与数学加权。

importance 的首要判断依据是评价点全部来源及完整 JD 上下文中的真实语义，不允许只根据关键词或 `source_field` 机械决定。模型负责提出 importance；程序负责校验枚举、来源和明显一致性信号，但不得把简单词表冒充完整语义理解，也不得静默覆盖模型建议。

五段式字段继续提供一致性信号：岗位职责通常对应 `general`、任职要求通常对应 `required`、加分项通常对应 `preferred`。如果原文明确语气与字段位置不一致、同一评价点同时包含强弱信号、包含否定/转折/可放宽语义，或模型建议与程序可识别的明确信号冲突，内容在来源、安全和结构均合法时不得整单失败；程序保留模型建议并为该稳定 `criterion_id` 生成 `importance_review_required` warning，交由 HR 对照原文修改或明确确认。

`importance_review_required` 是业务复核提示，不是安全放行：来源不存在、擅自新增要求、敏感内容、Prompt 污染、招聘决定越界、非法 JSON/Schema 和超过技术安全上限仍按内容错误整单失败，不能借 HR 审核绕过。

### 5.4 来源和 HR 补充规则

- `ai_from_jd` 必须至少有一条可定位 JD 原文；
- AI 不得凭常识补充 JD 没写的学历、年限、证书、行业、指定技术或其他硬性门槛；
- AI 可以在名称、描述或 `screening_focus` 中使用与原评价主题直接相关的常见缩写、同义表达、符号写法和非排他举例，例如“产品需求文档（PRD）”或“常见 OLAP 引擎（如 Hive、Presto）”；这些扩展只能帮助 HR 理解或寻找同类证据，不能把举例中的品牌、工具或术语变成 JD 未规定的必备条件，也不能排除等价经验；
- Service 对 `ai_from_jd` 继续要求 `source_quote` 可在对应冻结 JD 字段中原样定位，但不得要求评价点名称、描述和初筛重点与原文逐词一致；`Node.js/Nodejs`、`UX/UI/UXUI`、常见缩写和相关非排他举例不得仅因字符不同而整单失败；
- Service 只对可确定的新增硬门槛和明显无关主题执行内容硬失败：模型新增原文没有的年限、学历、学位、证书、认证或其他明确排他要求必须拒绝；普通语义不确定性由 HR 在 `pending_confirmation` 中对照来源审核，程序不得冒充完整语义理解；
- HR 可以新增 JD 没写的评价点，但必须标记为 `hr_added`；
- `hr_added` 在界面和报告中始终显示“HR 补充”，不得伪装成 JD 原文；
- HR 补充项没有 JD 来源时，`sources` 为空，`hr_note` 应说明补充内容；
- HR 把 AI 项修改到已不再受原引用支持时，必须转为 `hr_added`，或重新绑定真实 JD 来源；
- 程序必须验证 AI 来源引用可在对应冻结字段中定位。

### 5.5 HR 编辑权限

只有 HR 可以：

- 生成或重新生成清单；
- 修改名称、重要程度、描述和初筛重点；
- 新增、删除和合并评价点；
- 确认清单可用于初筛。

AI 只提供建议，不自动确认，不在 HR 不知情时修改 ready 清单。

HR 审核 `pending_confirmation` 时必须能够同时看到 importance、对应五段式字段、JD 原文和 `importance_review_required`。HR 可以修改 importance，也可以在读过提示后明确保留当前建议；整份计划确认本身即表示 HR 已审核当前版本的全部 warning。仅修改 importance 且评价主题仍受原引用支持时可以保持 `ai_from_jd`，由编辑版本审计记录 HR 修改；只有修改后不再受原引用支持时才必须转为 `hr_added` 或重新绑定真实来源。

## 6. 评价计划状态和版本

当前状态沿用并明确为：

```text
缺失
→ generating
→ pending_confirmation
→ ready

任一步内容或基础设施失败 → failed
JD 评价输入改变或被新版本替代 → outdated
```

固定规则：

1. 只有当前 `ready` 且 JD 指纹仍匹配的 5.0 计划可以启动新初筛。
2. `pending_confirmation` 可以编辑，不能用于初筛。
3. HR 每次保存编辑都必须带当前版本或并发标识；版本过期的请求返回冲突，不能覆盖别人的新编辑。
4. HR 确认后生成只读版本快照；后续再次编辑必须形成新版本并重新确认，不原地改写已被报告引用的版本。
5. JD 的评价输入变化后，旧计划标记 `outdated` 且不再是 current；旧报告和旧计划仍可读取。
6. 仅修改非评价内容不得让计划过期。
7. 同一 Job 最多一个 current 计划；历史版本不可删除或篡改。
8. 正在生成时发生 JD 变化，迟到结果只能成为失败或历史记录，不能成为 current。
9. `pending_confirmation` 可以携带 `importance_review_required`；保存编辑后按当前内容重新计算 warning。HR 可以消除 warning，也可以在仍有 warning 时明确确认当前版本，确认动作表示对当前版本全部 warning 的整体审核，不设置隐蔽的自动确认。

## 7. 计划生成模型边界

5.0 的正常计划生成只做一次业务模型调用：完整允许范围内的 JD → 轻量评价清单候选。

调用责任：

- 模型负责理解完整原文语义、聚合主要判断点、给出 importance 建议、名称/描述/初筛重点和原文引用；
- Service 负责版本字段、稳定 ID、来源定位、去重、安全上限、可确定的新增硬门槛、明显 importance 一致性 warning、指纹、状态、事务和迟到保护；Service 不得静默改写模型 importance，不得把合法的 importance 模糊项当作整单内容失败，也不得用英文 token 全量包含或中文连续双字等机械规则冒充语义等价判断；
- Adapter 只负责模型 API、严格 JSON 解析、重复键、finish reason、token/费用和基础设施错误分类；
- 固定 `schema_version` 等程序合同由程序补充，不能要求模型随机背诵。

支持性校验固定分为两层。第一层是来源和安全硬门禁：`source_quote` 必须真实存在；敏感属性、Prompt 污染、招聘决定越界、非法 JSON/Schema、超过 30 项，以及原文没有的明确年限/学历/学位/证书/认证等硬门槛直接失败。第二层是普通语义草稿：缩写、标点、同义表达、相关非排他举例、清单粒度和 importance 不确定性不得按逐词不一致整单失败；合法结果进入 `pending_confirmation`，由 HR 查看来源后编辑、删除、合并或确认。完全无关主题可以使用最小、可解释的粗粒度相关性保护拦截，但程序不得声称该启发式能够证明自然语言语义绝对正确。

Prompt 结构固定按“唯一任务 → 输入数据边界 → 评价点生成规则 → importance 判断规则 → 来源与安全硬约束 → 输出格式 → 输出前静默自检”组织，避免把所有规则堆成一段连续文字。输出前静默自检只要求模型在形成最终 JSON 前核对来源、擅自新增、importance、敏感信息、招聘决定、数量上限和额外字段；不得要求或保存完整思维链、分析草稿或内部推理过程。

5.0 可以使用少量 Few-shot（少样本输入/输出示例）帮助模型理解 importance 边界，但必须遵守：

- 示例总量保持精简，目标为 3—5 个虚构、脱敏且与正式验收样本分离的开发示例；
- 示例至少覆盖“职责中的明确强约束”“任职要求中的明确弱约束”“无明确强弱信号”“否定/转折/可放宽”和“多来源强弱混合”，不能只展示 `required`；
- 示例只演示如何基于完整原文语义生成合法业务候选字段，不得引入 JD 外知识、模型版本字段、稳定 ID、warning、分数或招聘决定；
- 后续第 20 节的 10 份新鲜 JD 和正式人工标签不得进入 Prompt 或 Few-shot，防止验收样本污染；
- Few-shot 不能代替 Schema/Service 校验。模型建议仍可能出错，程序继续负责来源、安全、技术上限和 `importance_review_required` 最小兜底。

重试规则：

- 网络超时、限流和模型 5xx 最多额外技术重试一次；
- 认证、配额、非法 JSON、Schema、来源、敏感内容和业务内容错误不自动重试；合法的 importance 模糊或冲突只产生 warning，不触发重试；
- 内容失败保存稳定错误，HR 可显式重新生成；
- 不引入 4.0 的隐藏完整性复核、局部修复和归组调用。

## 8. 简历输入与隐私边界

每次只读取当前 Application 绑定的当前 Resume，不得读取：

- 同候选人的其他 Resume；
- 其他岗位的 Application 或报告；
- 其他候选人的简历；
- Candidate 全局资料中不属于当前简历的职业信息。

送给 AI 前必须去除或禁止用于判断：

- 姓名、手机号、邮箱、身份证号、照片；
- 性别、年龄、出生日期；
- 婚育情况；
- 民族、籍贯等敏感属性。

教育、专业、工作经历、项目经历、技能和证书可以在 JD 确有相关要求时用于匹配，但不得根据学校名气、公司名气或其他社会标签推断能力。

## 9. AI 初筛评分合同

### 9.1 单项分

AI 对每个已确认评价点给 `0—10` 整数分，并提供：

- 判断理由；
- 一条或多条当前简历证据；
- 没有证据时的明确说明；
- 必要时引用固定经历时间事实。

`0` 分允许没有简历引用，但必须写成“当前简历未发现相关证据”。不得把“没写”表述成“候选人肯定不会”。非零分必须至少有一条可在当前简历中定位的证据。

### 9.2 总分

- AI 直接输出总体 `0—100` 整数建议分；
- Python 不按评价点平均、不加权、不重算总分；
- Prompt 要求 AI 综合全部评价点、importance、证据强弱、明显缺口和冲突作出整体判断；
- 程序只验证范围、证据和明显方向矛盾；
- 例如存在明确必备项严重不满足却给极高总分，或全部单项较高却给极低总分，应作为内容错误拒绝，具体粗矛盾规则在 7R5-A 由测试先固定；
- 不要求总分能够从单项分用公式精确复算，因为本方案明确不采用权重。

程序依据总分生成五档展示标签，沿用已经实现且 HR 容易理解的固定区间：

| 分数 | 展示标签 |
| ---: | --- |
| 0—29 | 关联较弱 |
| 30—49 | 存在明显差距 |
| 50—69 | 部分匹配 |
| 70—84 | 整体较匹配 |
| 85—100 | 高度匹配 |

标签只是界面摘要，不改变 HR 决策，也不能由模型自由输出。

5.0 的“明显方向矛盾”先固定最低保护线，不引入数学加权：单项 `7—10` 分却写“未发现证据”，或单项 `0—3` 分却写“完全满足”，必须拒绝；总体 `70—100` 分却在综合说明中判定明显不匹配，或总体 `0—49` 分却判定高度匹配，必须拒绝；任何 `required` 项 `0—3` 分而总体仍达到 70 分时，报告必须在风险/权衡中同时说明该必备缺口和支撑总体分的其他证据，否则拒绝。7R5-A 可以把这些语义写成受控测试词表，但不得把它扩展成权重公式或自动招聘阈值。

## 10. 报告合同

一份成功报告至少包含：

- 总体 0—100 分、程序展示标签和综合说明；
- 每个已确认评价点的 0—10 分、判断理由、简历证据和对应 JD/HR 补充来源；
- 主要优势；
- 主要差距；
- 风险或事实冲突；
- 简历中缺失、需要 HR 补充确认的信息；
- 面试或后续核实问题；
- Application、Job、Resume、评价计划和模型版本元数据；
- 生成时间与固定评价基准时间。

报告不得包含：

- 自动通过、自动备选或自动淘汰指令；
- 对受保护或敏感属性的评分；
- 其他候选人的相对比较；
- 原始模型响应、内部 Prompt、API Key 或堆栈信息；
- 没有证据却写成已确认事实的简历内容。

## 11. 单人和小批量初筛

### 11.1 调用方式

- 每名候选人独立评价，正常情况一名候选人一次报告模型调用；
- 每次调用发送完整允许范围 JD、当前 ready 清单和当前脱敏简历；
- 多名候选人不得放进同一个 Prompt，也不得让 AI 做相对排名；
- 批量页面可以按分数排序，但只是独立报告的界面排序。

### 11.2 阶段 7 批量边界

- 单次小批量最多 5 个同岗位 Application；
- 成功和失败按候选人分别结算，部分失败不回滚成功项；
- 返回总数、复用数、排队数、失败数、每项稳定原因和可重试项；
- 大批量导入、跨岗位调度和完整持久队列产品能力留给阶段 8。

现有 20 人批量重新评估上限必须在 5.0 收紧为 5，不能因为旧实现已经支持 20 就继续沿用。

### 11.3 调用前检查

每名候选人都必须独立确认：

- Application 存在且 `lifecycle_status=active`；
- Job 仍为开放状态；
- 当前 Resume 存在、属于该 Application 对应候选人且已可读取；
- 当前评价计划为合法 5.0 `ready` 且没有过期；
- 同一 Application 没有另一个活动运行；
- Job、Application、Candidate、Resume 和计划关系没有串线。

## 12. 幂等、重新评估和并发

- 相同 Application、JD、计划版本、Resume、评价时间、Prompt、模型、Schema 和脱敏规则形成相同输入指纹；
- 已有成功报告时，普通触发默认复用，不再次收费；
- 已有排队或运行任务时，重复点击返回同一运行；
- 同一 Application 最多一个非终态运行，由数据库约束保护；
- 强制重新评估必须由 HR 明确二次确认；
- 新成功报告成为 current，旧成功报告转为不可变历史；
- 新运行失败时保留旧 current 成功报告；
- Resume、JD 或评价计划变化让旧报告变成历史/过期，不删除；
- 迟到响应如果绑定旧输入，必须失败并且不能替换 current 报告。

## 13. 运行状态和失败语义

面向 HR 的状态含义：

```text
not_started     尚未开始
waiting_resume  等待可用简历
waiting_plan    等待生成、编辑或确认评价清单
queued          已排队
running         AI 正在初筛
succeeded       已完成
failed          本次运行失败
paused          岗位关闭等原因暂停
outdated        页面语义；旧报告输入已变化
```

稳定失败至少区分：

- 配置 / 认证 / 配额；
- 网络 / 限流 / 模型服务端；
- 非法 JSON / Schema；
- 评价点遗漏、重复或出现未知 ID；
- 非零分没有简历证据；
- 敏感属性或招聘决定越界；
- 总分与单项/必备缺口严重矛盾；
- 运行期间输入已变化；
- 数据库提交失败。

失败尝试只保存稳定错误码、阶段、时间、模型版本、attempt/token/必要费用，不向 HR 展示部分报告。

## 14. AI 状态、HR 决策和招聘阶段分离

三套状态不得混成一个字段：

1. AI 运行状态：等待、排队、运行、成功、失败、暂停；
2. HR 决策：`pending / passed / backup / rejected`；
3. 招聘阶段：`applied / hr_review / screening_passed / backup / rejected`。

阶段 7 不进入面试、Offer 或 hired；这些属于阶段 9。

固定交互：

- HR 从“AI 初筛中心”录入时，Application 从 `pending + applied` 开始；
- AI 到达成功、失败或阻塞终态后，系统把仍处于 `applied` 的 Application 推进到 `hr_review` 并追加 system StageHistory；如果 HR 已经先行决策，则不得倒退或覆盖 HR 状态；
- AI 运行期间建议暂时禁用决策按钮，防止 HR 误以为报告已经完成；
- AI 失败或阻塞不得阻止 HR 手工决策；
- HR 直接录入并明确确认通过时，Application 直接成为 `passed + screening_passed`；后续 AI 报告只作补充，低分或失败都不能撤销 HR 通过；
- 候选人管理页只展示已经通过的 Application；初筛中心负责 pending、运行、失败、备选和淘汰视图。

## 15. HR 决策审计

每次状态变更必须追加 StageHistory，至少记录：

- 变更前后招聘阶段；
- 变更前后 HR 决策；
- 操作时间；
- 关联的当前报告 ID，可为空；
- actor/source；
- 受控原因码和必要的补充说明。

初次通过可以不要求自由文本；备选、淘汰和任何反转必须说明原因。历史只追加，不覆盖。

## 16. 数据与版本审计

每次运行和成功报告至少固化：

- Application ID、Job ID；
- JD 指纹和必要快照；
- JobEvaluationPlan ID、5.0 版本和指纹；
- Resume ID 和脱敏输入指纹；
- `Application.applied_at`、`Asia/Shanghai` 和经历时间事实规则版本；
- Prompt、模型、输出 Schema、脱敏规则版本；
- started/completed/generated 时间；
- attempt 数、input/output/cache token 和必要费用估算；
- 输入总指纹。

`applied_at` 固定后，“至今”的经历年限在重新评估时不能继续增长。

## 17. 权限和安全边界

当前项目尚未实现完整登录/RBAC 时，API 仍必须按“只有 HR 内部用户可调用”的业务边界设计，不得因为开发环境没有身份系统就把生成、编辑、确认、重新评估或决策开放给候选人端。

5.0 不新增：

- 自动招聘决定；
- 跨候选人比较；
- 敏感属性推断；
- 学校或公司声望推断；
- 原始模型响应长期生产存储；
- 通用 Agent 自主改写计划或决策；
- 阶段 8 的大批量队列；
- 阶段 9 的面试、Offer 和录用状态。

## 18. 前端产品要求

### 18.1 评价清单抽屉

必须支持：

- 生成、生成中轮询、失败和显式重新生成；
- `pending_confirmation` 的编辑；
- 新增、删除、合并、调整 importance；
- AI 来源和“HR 补充”的明显区分；
- 可展开查看 JD 原文引用；
- `importance_review_required` 必须同时展示当前 importance、来源字段、原文和受控冲突原因，不能只显示笼统“请检查”；
- 约 5—12 个的提示和多于 12 个的 warning；
- 保存冲突、过期和迟到响应提示；
- 明确确认后才变为 ready；
- 历史 1.0—4.0 只读展示，不提供旧合同编辑。

### 18.2 初筛中心和报告

必须支持：

- 单人开始、普通复用和二次确认后的重新评估；
- 同岗位最多 5 人小批量；
- 每名候选人独立状态与部分失败结果；
- 总体 0—100 分和每项 0—10 分；
- JD 来源、HR 补充标识和简历证据；
- 优势、差距、风险、缺失信息和跟进问题；
- 旧报告、过期原因和历史版本；
- AI 状态与 HR 决策分区展示；
- 键盘、焦点、危险操作确认和桌面/平板/手机布局。

## 19. 自动化验收合同

7R5 的 Fake/自动化至少覆盖：

1. 轻量清单 Schema、约 5—12 提示、30 安全上限和来源定位；
2. 原文强/弱/无信号、任职要求与职责中的明确强约束、字段/语气冲突、否定/转折/可放宽、混合来源和模型 importance 偏差；合法模糊项形成稳定 warning 而不整单失败、不重试、不被程序静默改写；
3. `Node.js` 标点、`UX/UI` 斜杠、产品需求文档/`PRD` 缩写、OLAP 引擎及 Hive/Presto 非排他举例均可形成待 HR 确认草稿；模型新增原文没有的年限、学历、学位、证书、认证、明确排他技术门槛、明显无关主题和伪造来源仍稳定失败；
4. HR 新增、修改、删除、合并、保存、保留或消除 importance warning、确认、版本冲突和 `hr_added` 来源语义；AI 来源项经 HR 编辑后继续使用同一来源/硬门槛边界，不因普通同义改写再次被误拒；
5. JD 改动使计划/报告过期，非评价内容变化不误伤；
6. 旧 1.0—4.0 只读和 5.0 新生成隔离；
7. 单人普通幂等、强制重评确认、并发唯一运行和迟到响应保护；
8. 同岗位最多 5 人、跨岗位/重复/超量拒绝和批量部分失败；
9. 每个评价点恰好一条 assessment、0—10 范围、总体 0—100 范围；
10. 所有非零分有当前简历证据，0 分使用“未发现证据”语义；
11. 敏感属性、自动招聘决定、未知评价点和严重方向矛盾被拒绝；
12. current 成功替换、失败保留旧成功、输入变化和历史只读；
13. HR 决策、反转、原因和 StageHistory；
14. 明确扫描 5.0 运行路径中没有固定权重、权重字段和 Python 加权总分。

Prompt 专项还必须静态验证结构化分区、3—5 个边界 Few-shot、示例类别平衡、正式质量样本未进入 Prompt、只允许输出业务候选字段，以及输出前自检不要求模型返回思维链。Fake/Mock 可以证明消息构造、Schema、重试和程序 warning/硬失败边界，不能证明 Few-shot 已提高真实模型语义质量；该效果只能由第 20 节的新鲜样本真实验收证明，不能用静态检查或固定 Fake 输出冒充。

## 20. 真实 AI 质量验收

所有真实样本必须是未参与 Prompt 调整的新鲜、虚构或脱敏样本；人工标签在调用前冻结，运行后不得按模型答案改标签。

### 20.1 评价清单：10 份新鲜 JD

人工预先标注：

- 关键必备要求；
- 明显非评价内容；
- 禁止擅自新增的门槛。

硬门槛：

- 10/10 生成可供 HR 编辑的清单；
- 关键必备要求全部覆盖；
- 擅自新增的全新评价主题或硬门槛 0；与 JD 原主题直接相关的常见缩写、同义表达、符号写法和非排他工具举例不计为擅自新增，但举例不得被标成原文没有的必备条件，也不得排除等价经验；
- 敏感要求 0；
- 每个 AI 评价点都可追溯到 JD；
- 宣传、福利和招聘流程不得成为扣分项；
- 数量通常约 5—12，复杂岗位超过 12 只 warning、不失败。

上述放宽后的“擅自新增”定义只用于未来另行设计、冻结和授权的独立复验，不回写、不重算、不覆盖 2026-08-28 已执行的 7R5-I raw、调用审计、冻结标签或正式路径。

### 20.2 初筛报告：20 组新鲜 JD + Resume

人工预先标注：

- 总体匹配方向和大致合理分数区间；
- 主要差距与事实冲突；
- 必备要求应出现的证据或缺证据结论；
- 禁止使用的敏感信息。

硬门槛：

- 20/20 报告结构合法；
- 非零分有证据率 100%；
- 编造简历事实 0；
- 严重事实错误 0；
- 敏感属性参与评分 0；
- 自动招聘决定 0；
- 总体方向一致率至少 80%；
- 明确必备要求方向一致率至少 90%；
- 总分与单项/必备结论的粗矛盾 0；
- 每份都具有优势、差距、风险、缺失信息和跟进问题。

### 20.3 稳定性：5 组各独立运行 3 次

- 5 组从上述 20 组中在运行前冻结；
- 标签方向一致至少 4/5；
- 同组最大分差不超过 10 分至少 4/5；
- 极端方向翻转 0；
- 严重事实错误和敏感评分仍为 0。

这些门槛证明新方案在冻结样本上达到当前产品可接受线，不证明对所有岗位、所有简历或真实录用效果普遍准确。

## 21. 真实 PostgreSQL、API 和浏览器验收

### 21.1 PostgreSQL / API

必须真实验证：

- 计划生成、编辑、确认、版本、过期和历史；
- Application 创建与 Resume 隔离；
- 单人、小批量、幂等、并发、失败、重试和迟到保护；
- current 报告切换和旧报告历史；
- HR 决策、反转和 StageHistory；
- migration `upgrade / downgrade / upgrade`、`current=head` 和 `alembic check`；
- 夹具运行前后关键业务表计数恢复。

### 21.2 浏览器

必须真实验证：

- 评价清单生成、编辑、确认和 JD 改动后过期；
- 单人、小批量和逐人进度；
- 0—100 总分、0—10 单项、JD/HR 补充来源和简历证据；
- 失败、重试、旧成功保留和历史；
- HR 通过、备选、淘汰和反转；
- 键盘操作、焦点恢复、危险确认；
- 桌面、平板和手机布局；
- 无新增严重控制台错误、无敏感内容泄漏。

## 22. 真实调用和金额门禁

任何付费真实模型调用前必须依次完成：

1. Fake/自动化、构建、静态安全扫描通过；
2. 真实 PostgreSQL/API 和无需模型的浏览器预检通过；
3. 冻结模型、thinking、temperature、response format、max tokens、样本、人工标签、调用次数和独立结果路径；
4. 查询并记录 DeepSeek 官方实时价格、当前计价时段和估算方法；
5. 向用户展示基线调用次数、一次技术重试后的上限和结果不可覆盖规则；
6. 获得用户对本轮明确的金额上限或“不设置金额上限”确认；
7. 只执行被确认的一轮，达到通过或失败门槛后立即停止，不自动补跑。

计划 10 份、报告 20 份和稳定性 15 次是不同验收目的。实施时必须在质量运行器中精确记录每次业务调用、API attempt、token、cache、费用估算和原始响应审计；是否合并为一次金额授权，必须在当轮运行前由用户决定。

## 23. 5.0 实施批次总览

> 原实施顺序已获用户整体确认，7R5-A—7R5-H 已分别确认并完成，7R5-I 唯一 raw 已执行。10 份计划人工审核发现 Service 支持性误拒绝后，用户于 2026-08-28 明确暂停其余报告/稳定性人工审核，先解决 Service。新增插入的 `7R5-IR-A/B` 两个批次已分别确认并完成；每一轮仍只能执行一个另行确认的批次并停止。当前不能恢复旧 7R5-I，下一步只能先设计独立真实复验及其结果路径生命周期调整。

```text
7R5-A 合同测试与离线基线
→ 7R5-B 计划 5.0 Schema / Model / migration
→ 7R5-C 单次计划生成 Prompt / Adapter / Service
→ 7R5-C1 importance 原文语义与 HR 复核 warning 补充
→ 7R5-D 计划编辑、确认、版本和 API
→ 7R5-E 5.0 报告 Schema / Prompt / Service
→ 7R5-F 单人、小批量、状态与 HR 决策接线
→ 7R5-G React 评价清单与初筛报告
→ 7R5-H 零调用质量运行器和全量非付费预检
→ 金额确认门禁
→ 7R5-I 真实 AI raw（已执行；后续人工审核在计划部分后暂停）
→ 7R5-IR-A 支持性校验合同红灯
→ 7R5-IR-B Service 最小整改与零调用历史 raw 回放
→ 另行设计并授权独立真实复验（不得复用或覆盖原 7R5-I raw）
→ 7R5-J 真实 PostgreSQL / API / 浏览器收尾
→ 阶段 7 完成评审
```

## 24. 7R5-A：合同测试与离线基线

依赖：用户确认本文件全部实施顺序。

唯一目标：先用失败测试固定 5.0 新合同，证明当前 4.0 实现具体缺少什么，不先写生产实现。

通俗解释：先把“新尺子的刻度”刻清楚，再改机器。

允许修改：

- 新增 5.0 Schema/Model/Service/API/Screening 合同测试与 fixture；
- 新增静态扫描，证明 5.0 无权重和无 4.0 fact 依赖；
- 新增离线 10 JD、20 JD/Resume 和 5×3 稳定性样本合同及人工标签结构；
- 本文和 `PROJECT_STATE.md` 记录实际红灯。

链路位置：测试层，覆盖未来的 API → Schema → Service → Model → PostgreSQL 和前端合同；生产链不修改。

禁止：生产代码、Prompt、Adapter、Schema、Model、migration、API、React、数据库写入、真实 DeepSeek、结果文件和旧质量证据。

交付与验证：定向测试必须因缺少 5.0 能力而红，不得因测试语法或夹具错误而红；现有回归保持原状态；样本/标签 hash、数量、分母、调用预算和新结果路径冻结；`git diff --check` 通过。

完成标志：红灯逐条对应本文合同，且 0 次真实调用。失败返回测试设计层。完成后停止，唯一下一步是等待确认 7R5-B。

### 7R5-A 实际结果（2026-08-26 执行）

127 个 v5.0 合同测试全部收集成功：70 passed、57 xfailed（strict=True）、0 failures、0 errors。

红灯按责任批次分布：

| 批次 | xfail 数 | 覆盖范围 |
| --- | ---: | --- |
| 7R5-B | 14 | schema_version "5.0"、轻量 criterion 字段、DB 列和约束 |
| 7R5-D | 16 | 计划编辑/删除/合并方法、版本/并发、PlanEditConflictError、版本分叉 |
| 7R5-E | 14 | 报告 strengths/gaps/risks/missing_info、方向矛盾检测、证据校验器 |
| 7R5-F | 13 | v5 筛选门、批量上限 5、force 重评确认、HR 移交和 StageHistory report_id |

70 个 passed 证明既有能力不受影响：无权重字段（9）、展示标签正确（6）、JD 过期/非评价内容隔离（3）、1.0—3.0 计划只读（4）、安全禁字段（3）、4.0 筛选门（1）、批量/并发/幂等/状态（19）、HR 决策/历史/边界（11）、历史结果文件存在（3）、RequirementFact 现状（2）、质量常量（5）、无加权总分（4）。

fixture 摘要：10 JD（2 极简 + 2 丰富 + 1 混合 + 1 优先级冲突）、20 对（8 high + 6 partial + 6 low）、5×3 稳定性、SHA-256 `2ecc2da188f09883c1b6acaa40d0ca25f2306f2894e7f060a3a26aefb2fa9643`。调用预算：计划 10 + 报告 20 + 稳定性 15 = 45。

验证：既有 954 个 4.0 回归 passed；`py_compile` 全部新文件通过；`git diff --check` 通过；历史 H2 SHA-256 `b416809973ef...`、HR2 SHA-256 `4b7c44d4874f...` 不变；Alembic `current=head=d6f4a2b8e913`；真实 DeepSeek 调用 0；生产代码修改 0。

## 25. 7R5-B：计划 Schema、Model 与 migration

依赖：7R5-A 完成且用户另行确认。

唯一目标：让 PostgreSQL 能安全并存 1.0—5.0 计划，保存轻量评价点和编辑/确认版本审计。

通俗解释：先把新的“表格格式和存放位置”准备好，旧档案不动。

允许修改：

- `backend/app/schemas/job_evaluation_plan.py`；
- `backend/app/models/job_evaluation_plan.py`；
- 一份新的向前 Alembic revision；
- 对应 schema/model/migration 测试、本文和状态文档。

链路位置：Schema → Model → PostgreSQL。

固定交付：5.0 criteria、origin/sources/hr_note、状态、版本/确认审计、JSONB 约束、旧 1.0—4.0 只读并存；不得回填或改写旧行。

禁止：Prompt、Adapter、生成 Service、API、Screening、React、真实模型调用。

验证：测试库 migration 往返、正式开发库先只读基线再经单独确认迁移、`current=head`、`alembic check`、旧行兼容和表计数。失败返回 Schema/Model/migration 层。完成后停止，唯一下一步是 7R5-C。

### 7R5-B 实际结果（2026-08-26 执行）

Alembic migration `a3b5c7d9e101`（`down_revision=d6f4a2b8e913`）已应用至正式开发库：新增 `v5_criteria JSONB`、`edit_version INTEGER`、`confirmed_at TIMESTAMPTZ` 三列，更新 5 条 CheckConstraint（含 `'5.0'` 加入允许值、v5 payload 隔离和 `v5_criteria` 数组约束）。`alembic check` 通过，`current=head=a3b5c7d9e101`。

全套测试：1039 passed、42 xfailed（strict=True，属于 7R5-D/E/F 范围）、0 failures。12 个来自 `TestSchemaVersion50NotSupported`、`TestV5CriterionFieldsMissing`、`TestModelConstraints` 的 xfail 标记已移除（对应测试现在通过）；`test_stage7_v5_plan_edit_contract.py` 中 3 个因 7R5-B 变为 XPASS 的标记同步移除。

验证：`alembic check` 通过；历史 H2 SHA-256 `b416809973ef...`、HR2 SHA-256 `4b7c44d4874f...` 不变；真实 DeepSeek 调用 0；旧 1.0—4.0 行兼容无回填。

## 26. 7R5-C：单次计划生成链

依赖：7R5-B 完成且用户另行确认。

唯一目标：用一次业务模型调用生成轻量清单候选，并由程序完成来源、ID、版本和安全校验。

通俗解释：把过去“拆事实、复核、修补、归组”的流水线，换成一次直接生成 HR 可读清单。

允许修改：计划 Prompt、计划 Adapter 的必要兼容、计划 Service 纯生成部分、配置/版本常量和专项测试。

链路位置：Schema → Service → AI Adapter；不落正式业务数据。

固定交付：单次调用、程序版本字段、稳定 ID、JD 来源定位、importance、5—12 提示、30 安全上限、敏感/擅增拒绝、一次技术重试和内容不重试。

禁止：API 落库接线、HR 编辑、Screening、React、真实模型调用、修改 4.0 结果。

验证：Fake 正常/少量/复杂/>30/污染/来源错误/超时重试/内容不重试；现有回归和静态扫描。失败返回 Prompt/Adapter/Service 层。完成后停止，唯一下一步是 7R5-D。

### 7R5-C 实际结果（2026-08-26 执行）

5.0 单次计划生成链已在纯生成边界完成：Prompt 把完整允许范围 JD 声明为不可信数据并要求通常 5—12 项、最多 30 项；Adapter 每次 attempt 只发出一个 JSON 请求并保留严格 JSON/重复键/finish reason/基础设施错误分类；Service 在一次业务调用内完成版本字段、确定性排序与 `criterion:0001` 起的稳定 ID、逐字来源定位、`required/preferred/general` 复核、去重和安全拒绝。模型无权输出版本、ID、origin 或 HR 字段；简单岗位少于 5 项返回 `limited_basis`，复杂岗位多于 12 项返回 `many_criteria` 而不截断，原始输出超过 30 项直接按内容错误失败。

重试边界已固定：网络超时、限流和服务端错误最多额外技术重试一次，仍计为一次业务调用；非法 JSON、未知字段、来源错误、importance 冲突、Prompt 污染、敏感信息、自动招聘决定和 JD 无法支持的新增要求不重试。5.0 独立配置版本为 Prompt `job_evaluation_plan_lightweight_v1`、AI Schema `5.0`、计划 Schema `5.0`，没有切换现有 4.0 API 入口。

专项 5.0 生成合同为 17 passed；连同配置为 28 passed、16 subtests passed。受影响 Adapter/Service/3.0/4.0/Schema/静态扫描回归为 213 passed、6 xfailed、59 subtests passed；后端全量为 1056 passed、42 xfailed（strict=True，仍属于 7R5-D/E/F）、419 subtests passed、0 failures。静态扫描单跑为 20 passed、2 xfailed；`py_compile` 和 `git diff --check` 通过。全部模型路径只使用 Fake 或 `AsyncMock`，真实 DeepSeek 调用 0；未修改 API、Model、migration、Screening、React、PostgreSQL 业务数据或 4.0 历史质量结果。

这些结果证明单次计划候选的程序合同、确定性校验和重试边界在离线输入下成立，也证明既有后端回归未被破坏；不能证明真实 DeepSeek 对 10 份冻结 JD 的语义聚合质量、稳定性、费用、API 落库、HR 编辑确认、并发版本、Screening、React 或真实端到端链路。上述未验证范围分别留给 7R5-D—7R5-J，当前必须停止。

完成后的教学复盘进一步发现：本批实现会在模型 importance 与程序词表/字段回退不一致时整单失败，并把无明确语气的 `candidate_requirements` 机械回退为 `required`。这与第 5.3 节现已确认的“完整原文语义为主、HR 最终审核”不一致。该结果作为真实实现事实保留，不改写为已满足新合同；必须先完成下述 7R5-C1，才能进入 7R5-D。

## 26A. 7R5-C1：importance 原文语义与 HR 复核 warning 补充

依赖：7R5-C 已完成；用户已确认业务规则为“任职要求或岗位职责中的明确强约束是 `required`，明确弱约束是 `preferred`，无明确信号是 `general`，模型基于完整原文提出建议，HR 最终审核”；本节书面实施顺序另行获得明确确认。

唯一目标：主要通过结构化 Prompt 和少量边界 Few-shot 提高模型对 importance 原文语义的判断质量，并把剩余合法不确定性从“整单失败”改为“保留模型建议并生成稳定 HR 复核 warning”，同时保持来源、安全和擅自新增硬门禁不退让。

通俗解释：AI 负责读懂原文并打草稿；程序不再用简单词表替 AI 武断改答案，只把看得见的矛盾圈出来；HR 对照原文修改或签字。

允许修改：以计划 Prompt 为主；另允许修改 5.0 importance/review warning 所需的最小 Schema、计划 Adapter 的版本兼容、计划 Service 纯生成部分、配置/版本常量、7R5-C/C1 专项测试、本文和 `PROJECT_STATE.md`。Schema/Service 修改只能服务于 warning 表达、稳定关联和既有硬门禁，不得扩展为新的评分或确定性 importance 决策。链路位置为 Schema → Service → AI Adapter；不接 API，不落正式业务数据。

禁止修改：JobEvaluationPlan 持久化 Model、migration、API 路由和事务、HR 编辑/确认实现、Screening、React、正式 PostgreSQL 业务数据、真实 DeepSeek、4.0 历史质量结果及 7R5-D 以后范围。

固定交付：

1. Prompt 按第 7 节固定结构重新组织，明确要求模型结合评价点全部来源和完整 JD 上下文判断 importance，正确处理否定、转折、非必须、可放宽和混合语气；字段位置只作上下文和一致性信号。
2. Prompt 内加入 3—5 个精简、虚构且类别平衡的边界 Few-shot，覆盖职责强约束、任职要求弱约束、无信号、否定/转折/可放宽和多来源强弱混合；不得复用第 20 节正式新鲜样本或把程序 warning 冒充模型输出字段。
3. `required/preferred/general` 模型建议原样保留；程序不得静默改写。明确单向语气与模型建议不一致、强弱混合/否定/可放宽、明显字段/语气错位时，生成关联稳定 `criterion_id` 的受控 `importance_review_required` warning。
4. 无明确强弱信号时 Prompt 目标为 `general`；模型给出其他值时生成 warning，不整单失败。
5. importance warning 属于合法草稿的软问题：业务调用成功、内容不重试，可进入未来 `pending_confirmation`；warning 不代表自动确认，也不改变 `origin`。
6. 来源不存在、来源字段错误、擅自新增、敏感信息、Prompt 污染、招聘决定、非法 JSON/Schema、模型越权字段和超过 30 项继续整单失败且内容不重试。
7. Prompt/行为合同版本递增，旧 7R5-C 结果和 1.0—4.0 历史数据不改写；单次业务调用、基础设施最多额外重试一次、稳定 ID、5—12 提示和 30 上限保持不变。

验证：只使用 Fake/Mock，静态检查 Prompt 分区、Few-shot 数量/平衡/字段边界、正式样本隔离和禁止输出思维链；行为测试至少覆盖任职要求强约束、岗位职责强约束、明确弱约束、无信号、否定/转折/可放宽、强弱混合、多来源、模型建议偏差、字段/语气错位、warning 稳定 criterion ID、软问题不失败/不重试，以及全部既有来源/敏感/擅增/>30 硬失败回归；再执行受影响回归、全量后端、静态扫描、`py_compile` 和 `git diff --check`。真实模型调用和费用固定为 0，结果只记录在本文和状态文档，不创建或覆盖质量结果 JSON。本批只能证明 Prompt 结构、示例边界和程序兜底已按合同实现，不能证明 Few-shot 改善了真实 DeepSeek 质量；真实效果留给 7R5-I 的新鲜样本验收。

完成标志：新语义专项全绿，旧硬门禁没有降级，42 个后续严格 xfail 不因本批扩大，0 次真实调用；报告能证明离线 warning 和失败边界，不能证明真实模型语气判断质量或 HR 编辑体验。失败返回 Prompt/Schema/Service 责任层。本批完成后停止，唯一下一步是等待用户确认 7R5-D。

### 26A.1 7R5-C1 实际完成记录（2026-08-26）

本批已按授权完成。5.0 计划 Prompt 从 `job_evaluation_plan_lightweight_v1` 升级为 `job_evaluation_plan_lightweight_v2`，并按“唯一任务 → 输入数据边界 → 评价点生成规则 → importance 判断规则 → 来源与安全硬约束 → 输出格式 → 输出前静默自检”七段固定结构组织。Prompt 明确要求模型结合评价点全部来源和完整 JD 上下文判断 importance，原文强约束对应 `required`、弱约束对应 `preferred`、无明确信号对应 `general`，并处理否定、转折、非必须、可放宽和混合语气；岗位职责/任职要求/加分项只作为上下文和一致性信号，不能机械覆盖原文语义。输出前只要求内部静默核对最终 JSON，明确禁止输出、保存或复述分析步骤、思维链、草稿和自检过程。

Prompt 内固定 5 个虚构、去标识化边界 Few-shot，分别覆盖岗位职责明确强约束、任职要求明确弱约束、无明确强弱信号、否定/转折/可放宽及多来源强弱混合。示例输出只包含 `criteria` 及 `name/importance/description/screening_focus/sources` 业务候选字段，不包含版本、稳定 ID、origin、warning、HR 字段、分数或招聘决定；静态测试同时保护第 20 节 10 份冻结正式 JD 及其人工标签不被复制进 Prompt。配置默认值与 `.env.example` 已同步，Adapter 既有版本一致性检查会自动拒绝仍冒用 v1 的配置，因此不需要修改 Adapter 调用参数或请求次数。

最小 Schema 新增受控 5.0 warning code、importance 复核原因枚举和 warning detail。`importance_review_required` 必须关联稳定 `criterion_id` 和至少一个受控原因；数量 warning 不得伪造 criterion 引用或复核原因。Service 的行为合同从 `lightweight_plan_generation_v1` 升级为 `lightweight_plan_generation_v2`：来源、结构、安全和擅自新增校验继续先执行；通过硬门禁后，程序在稳定排序并生成 criterion ID 以后检查明确强/弱/无信号、复杂限定语气、字段/语气错位和多来源强弱冲突。模型给出的 `required/preferred/general` 与 `origin=ai_from_jd` 原样保留，程序不再用字段回退或词表结果覆盖模型，也不再因合法 importance 差异整单失败。

warning 原因固定为：`explicit_strong_signal_mismatch`、`explicit_weak_signal_mismatch`、`no_explicit_signal_non_general`、`mixed_strength_signals`、`complex_qualification_language`、`source_field_signal_mismatch` 和 `multi_source_signal_conflict`。同一个 criterion 可以携带多个原因，顺序由程序枚举固定；模型换序后 criterion 与 warning 关联仍保持稳定。少于 5 项和多于 12 项的原字符串 warning 同步升级为受控对象，30 项技术上限、单次业务调用和最多一次基础设施重试不变。

实际修改位于 `Schema → Service → AI Adapter` 的纯生成边界和链外配置/测试：`backend/app/schemas/job_evaluation_plan.py` 定义 warning 数据盒子，`backend/app/prompts/job_evaluation_plan.py` 规定模型语义责任，`backend/app/services/job_evaluation_plan_service.py` 在硬门禁后生成 warning，`backend/app/core/config.py` 与 `.env.example` 固定 v2 Prompt，两个专项测试文件固定行为与版本。没有修改 JobEvaluationPlan 持久化 Model、migration、API、事务、HR 编辑/确认、Screening、React、PostgreSQL 业务数据、4.0 历史质量结果或任何质量结果 JSON。

自动化结果：7R5-C/C1 纯生成专项 `36 passed`；专项与配置合跑最终为 `47 passed、16 subtests passed`；受影响的 Adapter、1.0—4.0 Schema/Service、source units、5.0 生成和静态扫描回归为 `274 passed、2 xfailed、59 subtests passed`；后端全量为 `1075 passed、42 xfailed、419 subtests passed、0 failures`，用时 `97.88` 秒。42 个严格 xfail 数量与责任批次保持不变，属于后续 7R5-D/E/F。静态扫描单跑为 `20 passed、2 xfailed`；受影响文件 `py_compile` 与 `git diff --check` 通过。全部模型行为只使用 Fake 或 `AsyncMock`，真实 DeepSeek 调用和费用均为 0；Alembic `current=head=a3b5c7d9e101`，本批没有 migration 或数据库写入。

这些结果能证明：Prompt 的七段结构、5 个边界 Few-shot、输出字段边界、正式样本隔离和禁止输出思维链已被静态合同固定；在离线可控响应下，明确语气目标、复杂语气提示、模型建议保留、稳定 warning 关联、软问题不重试，以及来源错误、错误字段、敏感信息、Prompt 污染、擅自新增、招聘决定、非法 JSON/Schema、模型越权字段和超过 30 项继续硬失败的程序合同成立；既有后端回归没有新增断言失败。它们不能证明 Few-shot 已改善真实 DeepSeek 对自然语言的判断质量，也不能证明未枚举表达不会产生 warning 误报/漏报，更不能证明 API 落库、HR 编辑确认、Screening 或 React 已可用。若模型普遍选错语义，先回到 Prompt；若 warning 形状或原因不足，回到 Schema；若错误地失败、漏提示、ID 不稳或发生重试，回到 Service。7R5-C1 到此完成并停止，唯一下一步是等待用户明确确认 7R5-D。

## 27. 7R5-D：计划编辑、确认、版本和 API

依赖：7R5-C1 完成且用户另行确认。

唯一目标：把 5.0 清单可靠落库，让 HR 能编辑并确认同一岗位的正式尺子。

通俗解释：AI 先打草稿，HR 真正拥有修改和签字权。

允许修改：计划 Service 持久化部分、API、请求/响应 Schema、Job 变更协调、必要 migration 补充、专项测试和 API 映射测试。

链路位置：API → Schema → Service → Model → PostgreSQL。

固定交付：生成/失败重生、编辑、新增/删除/合并、HR 补充、乐观并发、确认、历史版本、JD 过期、非评价内容不误伤、迟到保护。

禁止：Screening 评分、React 页面、真实模型质量验收。

验证：Fake API、事务、并发、真实 PostgreSQL 受控夹具和回滚；旧 1.0—4.0 只读。失败返回对应链路层。完成后停止，唯一下一步是 7R5-E。

### 7R5-D 实际结果（2026-08-26）

本批已按 `API → Schema → Service → Model → PostgreSQL` 完成。公开生成与失败重生入口切换到 5.0；新增整份草稿保存、确认、从已确认版本分叉和历史列表 API。请求必须携带当前 `edit_version`，Service 在事务内锁定 Job 与当前计划并执行乐观并发检查；过期版本返回稳定 `409 JOB_EVALUATION_PLAN_EDIT_CONFLICT`。HR 可以通过一次原子草稿保存完成编辑、新增、删除和合并：现有评价点保留稳定 ID，新增项由程序分配全岗位历史不复用的 ID，并强制 `origin=hr_added`、无伪造 JD 来源且填写 `hr_note`。来源、安全、Prompt 污染、擅自新增和招聘决定仍在保存前硬拒绝；importance warning 按保存后的完整清单重新计算，warning 可以由 HR 明确确认，但不能绕过硬门禁。

5.0 生成成功只进入 `pending_confirmation`；确认记录 `confirmed_at` 并变为只读 `ready`。再次编辑 ready 计划不会原地覆盖，而是复制成新的 pending 历史行，旧 ready 行继续可读且不再是 current。JD 评价字段变化会令当前计划 `outdated`，`public_notes` 等非评价内容变化不误伤；模型返回前再次核对当前 JD、指纹、状态和 current 标记，迟到成功或失败响应不能覆盖新输入。公开 5.0 写接口不能修改 1.0—4.0 历史行；内部 4.0 服务只保留用于历史回归和旧数据读取，不再作为公开生成入口。本批没有实现 5.0 Screening 评分或报告，也没有修改 React。

新增 migration `b4c6d8e0f212`（`down_revision=a3b5c7d9e101`）。数据库使用两套部分唯一索引分别保护旧 1.0—4.0 的 `(job_id, input_fingerprint)` 和 5.0 的 `(job_id, input_fingerprint, edit_version)`，避免 PostgreSQL 的 NULL 唯一语义削弱旧合同；另新增 5.0 正编辑版本、完整草稿、失败无部分 payload 和 ready 确认时间约束。真实开发库完成 `b4 → a3 → b4` 往返，计划表始终为 1 行，整行内容 MD5 往返前后均为 `0819ebafc4168daf6b99d8a848911221`；最终 `current=head=b4c6d8e0f212`，`alembic check` 为 `No new upgrade operations detected`。

专项真实 PostgreSQL/API/迁移合同为 `15 passed`；D 合同与静态扫描合跑为 `56 passed、4 xfailed`；受影响 API、Model、Service 与历史回归为 `119 passed、2 xfailed、12 subtests passed`。后端全量为 `1100 passed、32 xfailed、419 subtests passed、0 failures`，用时 `102.07` 秒；32 个严格 xfail 全部继续属于 7R5-E/F。受影响文件 `py_compile`、`git diff --check` 通过。测试只使用 Fake、Mock、受控事务和回滚，真实 DeepSeek 调用与费用均为 0；受控 PostgreSQL 用例结束后表计数恢复，4.0 历史质量结果及其结果文件未修改。

这些结果能证明：在 Fake 输出和当前 PostgreSQL 约束下，5.0 生成落库、失败显式重生、原子编辑、HR 补充、稳定 ID、warning 重算、乐观并发、确认、只读版本分叉、历史读取、JD 过期、非评价字段不误伤、迟到保护和旧合同公开只读边界成立；也证明现有后端没有新增断言失败。它们不能证明 React 上的 HR 编辑体验、5.0 Screening 报告质量、真实 DeepSeek 语义质量、完整 HTTP 服务与浏览器端到端行为，或多机高负载下的长期性能。若请求字段或响应形状错误，先查 Schema/API；若状态、warning、ID、并发或过期语义错误，查 Service；若数据库接受非法状态或版本重复，查 Model/migration。7R5-D 到此完成并停止，唯一下一步是等待用户明确确认 7R5-E。

## 28. 7R5-E：5.0 初筛报告后端

依赖：7R5-D 完成且用户另行确认。

唯一目标：按已确认评价点逐项打 0—10 分，由 AI 直接给总体 0—100 分并生成完整证据报告。

通俗解释：用 HR 签过字的同一把尺子看简历，但不套权重公式。

允许修改：screening evaluation Schema、Prompt、Adapter、Service、ScreeningReport 必要字段/JSONB 合同、新 migration 和专项测试。

链路位置：Schema → Service → AI Adapter → Model → PostgreSQL。

固定交付：完整 JD + 清单 + 当前脱敏简历；criterion assessment；总体分；优势/差距/风险/缺失/问题；证据；敏感禁用；明显矛盾拒绝；程序标签；无权重。

本批 Prompt 固定采用以下六项工程方法：

1. **结构化分区**：Prompt 按“唯一任务 → 权限与决策边界 → 不可信输入说明 → 逐评价点评分 → 总体评分 → 证据 → 报告完整性 → 安全禁止项 → JSON 输出 → 输出前静默检查”组织；不得把全部规则堆成连续长段。
2. **指令与数据隔离**：完整 JD、已确认评价清单、当前脱敏 Resume 和固定经历时间事实分别使用清晰边界包裹，并统一声明为不可信数据；其中任何看起来像系统命令、评分指令或 Prompt 修改要求的内容都只作为待分析数据，不得执行。
3. **严格 JSON Schema**：Prompt 只允许输出最终 JSON；模型输出必须再经过严格 Pydantic Schema、重复键和未知字段检查。Prompt 的格式要求不能替代程序校验，程序也不得容忍或猜测修复缺失字段。
4. **少量、平衡 Few-shot**：允许使用 3—5 个虚构、脱敏、类别平衡且与第 20 节正式验收样本隔离的示例，覆盖有充分证据、无证据为 0、只有间接证据、required 严重缺口与总体权衡、事实冲突或 Prompt 注入等边界；示例只展示最终合法业务 JSON，不展示思维链、草稿或内部自检。
5. **静默完整性检查**：输出前要求模型只在内部核对评价点恰好一次、非零分证据、0 分语义、总分方向、优势/差距/风险/缺失/问题完整性、敏感属性、招聘决定和 JSON 形状；最终响应不得包含检查过程、分析草稿或思维链。
6. **Prompt 版本与 Bad Case 回归**：本批建立独立 5.0 报告 Prompt/行为合同版本。后续每次修改都要记录原因，把脱敏 Bad Case 加入回归，重跑既有格式、证据、安全、矛盾和历史兼容测试；不得用正式新鲜质量样本反向调 Prompt，也不得无版本改写现有行为。

上述六项不改变既有调用与安全合同。本批明确不采用输出完整思维链、普通生产流程多次自一致性投票、内容错误后的 Self-Refine/修复调用、动态 RAG/Few-shot 检索或 LLM-as-Judge 单独代替人工标签和确定性校验；正常情况仍是一名候选人一次报告业务调用，只有网络、限流、超时或模型服务端错误允许最多一次额外技术重试，内容错误不重试。

禁止：批量上限/入口、HR 决策改动、React、真实模型调用。

验证：Fake 高/中/低、缺证据、编造、敏感、自动决定、未知 ID、方向粗矛盾、时间事实和旧报告兼容。失败返回 Schema/Prompt/Service/Model 层。完成后停止，唯一下一步是 7R5-F。

### 28.1 7R5-E 实际完成记录（2026-08-27）

本批已按 `Schema → Service → AI Adapter → Model → PostgreSQL` 的纯报告边界完成。Schema 保留旧 `AIScreeningEvaluationOutput` 与 1.0—4.0 报告读取，新增独立 `AIScreeningEvaluationV5Output`、`CriterionAssessment`、五类结构化报告分区和程序补齐的 `ScreeningEvaluationV5ReportPayload`。模型只返回 criterion ID、0—10 分、理由、经历时间事实 key、当前 Resume 证据、AI 直接 0—100 总分、综合说明、优势、差距、风险/事实冲突、缺失信息和 HR 核实问题；程序生成五档标签，并把 HR 已确认 criterion 的 importance、origin、JD 来源和 hr_note 快照与 assessment 一一绑定后，才形成可安全持久化 payload。Python 没有平均、加权或重算总分，也没有恢复 RequirementFact 评分。

5.0 报告 Prompt 版本为 `screening_evaluation_lightweight_v1`，行为合同为 `lightweight_report_generation_v1`，输出 Schema 为 `5.0`。Prompt 按“唯一任务 → 权限与决策边界 → 不可信输入说明 → 逐评价点评分 → 总体评分 → 证据与时间事实 → 报告完整性 → 安全禁止项 → 严格 JSON Schema → 输出前静默完整性检查”十段组织；Job、已确认清单、脱敏 Resume、评价基准和经历时间事实使用五组独立不可信数据边界。固定 4 个虚构、脱敏、类别平衡且可由同一 Pydantic Schema 验证的完整 JSON Few-shot，覆盖充分证据、0 分无证据、间接证据以及 required 严重缺口与 Prompt 注入；冻结正式质量样本内容未进入 Prompt。最终响应明确禁止思维链、草稿或自检过程；没有多次 Self-Consistency、内容 Self-Refine、动态 RAG/Few-shot 或 LLM-as-Judge。

Adapter 新增独立 `evaluate_v5` 单请求合同，继续使用 JSON object、thinking disabled、temperature 0.1、SDK 自动重试 0 和现有安全错误分类；不改变旧 4.0 调用。纯 Service 的 `evaluate_v5/parse_and_validate_v5_output` 在持久化前拒绝重复 JSON key、未知/遗漏/重复 criterion ID、非零分无证据、0 分错误语义、证据无法定位、编造数字或综合事实、敏感属性、学校/公司品牌推断、自动招聘决定、Prompt 注入复述、未知经历时间事实、时间冲突和明显分数文字矛盾。required 项 0—3 分而总体达到 70 时，必须同时存在引用该 criterion 的风险/缺口说明和有 Resume 证据的优势；内容错误一次调用后直接失败，不返回部分报告。基础设施最多一次额外重试继续由既有运行底座负责，本批没有提前接入 5.0 `ScreeningRun`。

`ScreeningReport` 新增隔离的可空 `v5_report JSONB`，数据库约束要求只有 `schema_version='5.0'` 才能携带完整对象，旧版本必须为 `NULL`；旧 `requirement_assessments/bonus_highlights` 等列不删除、不回填、不改写。Pydantic 读取还会复核 JSONB 内的总分、程序标签和综合说明与索引列一致。新 migration `c5d7e9f1a323`（`down_revision=b4c6d8e0f212`）只增加该列和约束；downgrade 在存在任何 5.0 报告时以 `STAGE7_SCREENING_V5_DOWNGRADE_BLOCKED` 阻止有损删除。

修改前直接基线为 `62 passed、18 xfailed、43 subtests passed`。完成后 5.0 专项与合同为 `183 passed、12 xfailed、52 subtests passed`，12 个严格 xfail 全部仍属于 7R5-F；受影响的 4.0 Screening、运行底座、API、5.0 计划及历史 migration 回归为 `154 passed、55 subtests passed`。后端全量为 `1149 passed、12 xfailed、419 subtests passed、0 failures`，用时 `53.00` 秒；仅有既有 PyPDF2 弃用 warning 和一次既有 asyncpg cancel RuntimeWarning。受影响 Python 文件 `py_compile` 与 `git diff --check` 通过。

本机 PostgreSQL 启动后确认原开发库为 `current=a3b5c7d9e101` 且 `jobs/applications/job_evaluation_plans/screening_reports/screening_runs` 全为 0；实际执行 `a3 → b4 → c5 → b4 → c5`，最终 `current=head=c5d7e9f1a323`，`alembic check` 为 `No new upgrade operations detected`，`v5_report` 为可空 JSONB 且约束存在，关键表计数前后仍全为 0。全部 AI 行为使用 Fake/Mock，未读取真实 API Key，真实 DeepSeek 调用和费用均为 0；没有修改 Screening 运行入口、批量上限、HR 决策、API 主流程、React 或 4.0 历史质量结果。

这些结果能证明 5.0 报告的离线结构、Prompt 工程方法、一次业务调用边界、确定性证据/安全/方向/时间校验、程序标签、旧报告兼容和 PostgreSQL JSONB 合同按当前 Fake 与冻结测试工作；不能证明真实 DeepSeek 报告质量、真实 token/费用、5.0 异步运行与 current 报告替换、最多 5 人批量、HR 页面体验或完整端到端验收。若模型 JSON 形状或必填字段错误，返回 Schema；若模型普遍误判或遗漏报告内容，返回 Prompt；若 ID、证据、安全、事实或方向校验误报/漏报，返回 Service；若外部响应、finish reason 或基础设施分类错误，返回 Adapter；若 JSONB/版本隔离或往返失败，返回 Model/migration。7R5-E 到此完成并停止，唯一下一步是等待用户另行确认 7R5-F。

## 29. 7R5-F：单人、小批量、状态与决策接线

依赖：7R5-E 完成且用户另行确认。

唯一目标：把 5.0 报告接入现有可靠运行底座，并把批量上限收紧为 5。

通俗解释：新报告引擎接上已有排队、复用、失败保护和 HR 决策流程。

允许修改：screening Service/API/Schema、Application 协调和 HR 决策/历史的必要接线、数据库约束、专项测试。

链路位置：API → Schema → Service → Model → PostgreSQL。

固定交付：5.0 ready gate、普通复用、强制重评确认、唯一活动运行、每人独立、最多 5 人、部分失败、current 替换、旧成功保留、迟到保护、AI/HR/招聘阶段分离。

禁止：React、真实模型质量调用、阶段 8 大队列。

验证：Fake API/PostgreSQL 幂等、并发、重启恢复、跨关系隔离、批量部分失败、HR 决策和审计。失败返回运行/事务/决策层。完成后停止，唯一下一步是 7R5-G。

### 7R5-F 实际结果（2026-08-27 执行）

5.0 报告已接入既有 `ScreeningRun`：新运行只接受当前合法 5.0 `ready` 计划，按 Application 原投递时间、当前 Resume、计划编辑版本、Prompt/模型/Schema/脱敏版本形成输入指纹，并调用 7R5-E 的单次 `evaluate_v5`。普通触发复用相同 current 报告或唯一非终态运行；单人和批量强制重评都要求显式 `confirmed=true`；同岗位批量上限由 20 收紧为 5，返回总数、复用数、排队数、失败数和逐 Application 的安全失败原因/可重试标记，逐项失败不回滚已成功提交项。内容错误仍不重试，基础设施错误最多额外技术重试一次，迟到响应和数据库提交失败不会切换 current。

`ScreeningReport` 由“每个 Application 只能一行”调整为“每个 Application 只能一行 `is_current=true`”：成功重评先在同一事务中冻结旧 current，再新建 5.0 current；失败则整笔回滚并保留旧 current。历史 1.0—4.0 行不改写，新 `/applications/{id}/screening/reports` 只读接口按 current 优先、时间倒序返回全部成功历史。`ScreeningRun` 的部分唯一索引覆盖 `waiting_resume / waiting_plan / queued / running / paused`，数据库保证每个 Application 最多一个非终态运行。

AI 运行、HR 决策和招聘阶段继续使用三套字段。AI 成功或失败只会把仍处于 `pending + applied + active` 的 Application 推进到 `hr_review`，不写通过/备选/淘汰；如果 HR 已先行决策，AI 结果不得回退或覆盖。HR 直接通过使用显式覆盖入口；备选、淘汰和反转要求岗位相关说明。每次系统移交或 HR 决策都追加 `StageHistory`，可关联当时 current `report_id`；历史只追加。revision `d6e8f0a2b434` 新增报告 current 部分唯一索引、全非终态运行唯一索引和 `StageHistory.report_id` 外键，并在既有冲突数据或有损 downgrade 时给出稳定阻断码。

修改前直接相关基线为 `182 passed、12 xfailed、36 subtests passed`。完成后 7R5-F 核心专项为 `181 passed、54 subtests passed`，后端全量为 `1175 passed、425 subtests passed、0 failures`；原 12 个 7R5-F 严格 xfail 已全部转为通过合同。真实 PostgreSQL 已执行 `c5 → d6 → c5 → d6`，最终 `current=head=d6e8f0a2b434`，`alembic check` 为 `No new upgrade operations detected`；本批 Python 文件 `py_compile` 与 `git diff --check` 通过。全部 AI 行为使用 Fake/Mock，没有读取真实 API Key，真实 DeepSeek 调用和费用为 0；未修改 React、批量阶段 8、真实质量结果或历史 4.0 证据。

这些结果证明 Fake/本地 PostgreSQL 下的 5.0 gate、幂等、唯一非终态运行、强制确认、五人批量/部分失败、current/历史切换、失败回滚、迟到保护、HR 状态隔离和审计合同成立；不能证明真实 DeepSeek 质量、真实费用、React 体验、浏览器交互或完整端到端验收。若请求形状、确认或批量计数错误，返回 Schema/API；若复用、逐项失败、迟到或事务错误，返回 Screening Service；若 HR 状态被覆盖或审计缺失，返回决策 Service；若 current/唯一索引/外键或往返失败，返回 Model/migration。7R5-F 到此完成并停止，唯一下一步是等待用户另行确认 7R5-G。

## 30. 7R5-G：React 评价清单与报告

依赖：7R5-F 完成且用户另行确认。

唯一目标：让 HR 在页面上完成计划编辑、确认、单人/小批量初筛、报告阅读和独立决策。

通俗解释：后端能力变成 HR 真能操作和看懂的产品。

允许修改：阶段 7 TypeScript 类型、集中 Service、计划抽屉、初筛中心、报告视图、决策交互、样式和前端测试。

链路位置：前端 → API。

固定交付：第 18 节全部页面要求、历史 1.0—4.0 只读、5.0 可编辑、5 人上限、危险确认、轮询/迟到 UI 保护、响应式和可访问性。

禁止：后端合同扩展、真实模型调用、阶段 8/9 页面。

验证：Node 测试、TypeScript strict、生产构建、无裸 `fetch`/`any`/危险 HTML，Fake 浏览器状态矩阵。失败返回组件/类型/API 映射层。完成后停止，唯一下一步是 7R5-H。

### 7R5-G 实际结果（2026-08-27 执行）

React 的 5.0 合同已落地到集中 TypeScript 类型和 `v2Http` Service。岗位评价计划抽屉现在读取/保存整份 5.0 草稿，支持修改 importance、名称、说明、初筛重点和 HR 备注，以及新增、删除、合并；AI 来源、HR 补充、稳定 criterion ID、JD 原文和 warning 复核原因分开展示。未保存编辑期间不能误确认数据库旧版本；保存使用 `edit_version` 乐观并发；确认需要危险操作确认，确认后当前版本只读，只能创建新编辑版本。历史 1.0—4.0 计划继续只读，不用新结构覆盖旧解释。

初筛工作台把批量选择固定为同一开放岗位最多 5 人，展示总计、复用、排队、失败及逐 Application 安全结果；部分失败不隐藏已提交项。普通复用、单人重新评估确认、轮询和迟到响应保护继续保留。AI queued/running 时 HR 决策入口禁用；终态 AI 结果和 HR 决策仍是两套独立状态。报告抽屉支持当前/历史成功报告切换：5.0 页面明确总体分由 AI 直接给出，程序不平均、不加权、不重算，并逐评价点展示 0—10 分、确认时评价点快照、JD 原文、Resume 证据、0 分边界、优势、差距、风险/事实冲突、缺失信息、HR 后续问题及 Prompt/模型/Schema/脱敏/时间事实审计；旧 1.0—4.0 报告保持历史只读。

修改前 19 组前端 Node 基线和生产构建通过。完成后 20 组前端 Node 测试全部通过；`npm run build` 完成 TypeScript strict 与 Vite production build（3121 modules）；受影响后端回归为 `61 passed、17 subtests passed`。静态扫描未发现生产目录裸 `fetch`、显式 `any` 或 `dangerouslySetInnerHTML`，`git diff --check` 通过。Fake 浏览器在 1440×1000 下实际完成清单编辑、HR 新增、保存（edit version `3 → 4`）、编辑中确认禁用、确认后只读、5.0 报告、旧 4.0 历史、五人上限、`4 queued + 1 failed` 部分失败和焦点返回；390×844 下报告抽屉宽度为 390、页面无横向溢出，最后一轮控制台无新错误。Fake 网络只访问本机 `127.0.0.1`，没有读取真实 API Key，真实 DeepSeek 调用和费用为 0；没有修改后端合同、migration、阶段 8/9 页面或历史质量结果。

这些结果证明 Fake/本地静态构建下的 React 类型映射、主要 HR 交互、只读历史、批量部分失败、可访问性焦点和响应式边界成立；不能证明真实 DeepSeek 质量、真实 PostgreSQL/API 全链、真实费用或最终完整端到端验收。若字段映射、请求体或兼容默认值错误，返回 TypeScript/API 映射层；若局部状态、确认、选择、轮询、迟到或焦点错误，返回 React 组件层；若布局溢出或证据层级不清，返回样式/组件层；若后端响应本身违反已确认合同，不在 G 中扩展前端绕过，返回 Schema/API/Service 责任层。7R5-G 到此完成并停止，唯一下一步是等待用户另行确认 7R5-H。

## 31. 7R5-H：零调用质量运行器与非付费预检

依赖：7R5-G 完成且用户另行确认。

唯一目标：冻结真实验收输入、门槛、预算和不可覆盖结果路径，在不读取 API Key 的情况下证明付费运行不会因程序问题浪费调用。

通俗解释：付费考试前先检查试卷、计分器、保存路径和整条非付费链路。

允许修改：独立 7R5 质量合同/运行器、冻结 fixture/人工标签、质量测试、Fake API/PostgreSQL、浏览器夹具和验收文档。

链路位置：质量门禁，覆盖全链但不调用真实模型。

固定交付：10 JD、20 对、5×3；样本与标签 hash；计划/报告/稳定性统计；调用与 attempt 上限；独立新结果路径；历史结果 hash；dry-run/Fake；价格查询前置条件。

禁止：改 Prompt/业务合同来迎合样本、读取 API Key、真实调用、创建正式结果、覆盖 4.0 结果。

验证：后端/前端全量、构建、migration、真实 PostgreSQL/API 非付费链、浏览器非模型路径、Fake 正常与失败、dry-run 0 调用、历史 hash、`git diff --check`。任何红灯都返回责任层，不能带病付费。完成后展示官方价格和调用边界，停止等待金额确认。

2026-08-27 至 2026-08-28 实施记录（**7R5-H 已完成并停止**）：已新增独立 5.0 质量合同、运行器、20 个专项测试和仅用于价格预检的官方价格快照。冻结 fixture 仍为 10 JD、20 对、5 组各 3 次，完整 SHA-256 为 `2ecc2da188f09883c1b6acaa40d0ca25f2306f2894e7f060a3a26aefb2fa9643`；计划样本/标签、报告样本/标签和稳定性选择另有独立 hash，人工分母固定为 55 个计划必备标签、26 个非评价标签、22 个禁止新增标签、107 个报告 required 方向标签。正常业务调用固定为计划 10 + 报告 20 + 稳定性 15 = 45；只有网络、限流、超时或服务端错误可各多 1 次，API attempt 硬上限 90，内容错误重试 0。输出 token 安全上界为正常 500,000、全部发生一次技术重试时 1,000,000。raw、人工审计和 final 使用 `v5-quality-results/` 下三个独立、不可覆盖且当前不存在的 7R5-I 路径；13 份 4.0/历史质量证据 hash 前后完全一致。

运行器只在显式 `real` 模式、官方价格快照 24 小时内有效且用户给出美元上限或明确不设上限后，才加载真实 Settings 和 Adapter；`dry-run`/Fake 使用 `_env_file=None` 且显式空 `DEEPSEEK_API_KEY`。逐 attempt 记录业务样本、attempt 编号、请求/返回模型、finish reason、token/cache、耗时、原始响应和费用；成功按实际 token 计费，超时等无 usage 的失败 attempt 保留调用前最坏费用预留，避免连续失败低估金额。raw 结果无权直接宣布质量通过；必须再绑定 raw hash、fixture hash、人工审阅人/时间以及 12 个固定人工指标，最终程序才合并人工语义门槛与确定性结构门槛。正式新结果路径当前均不存在，真实 DeepSeek Adapter 未实例化，真实模型调用和费用均为 0。

已通过：修改前 4.0 质量合同/运行器基线 `42 passed`；7R5-H 专项 `20 passed`；真实 PostgreSQL Fake API、两份 migration 合同与 H 专项合跑 `23 passed`；后端全量 `1195 passed + 425 subtests passed`、0 failures（只有既有 PyPDF2 弃用 warning 和一次异步连接清理 RuntimeWarning）；前端全部 20 组 Node 测试、TypeScript strict 和 Vite production build（3121 modules）；真实 PostgreSQL `d6e8f0a2b434 → c5d7e9f1a323 → d6e8f0a2b434`，最终 `current=head`、`alembic check` 无差异，8 张核心表往返前后均为 0；dry-run 为 0 调用/0 写入/无 Adapter/无质量结论，Fake normal 为计划 `10/10`、报告 `20/20`、稳定性 `15/15` 结构合法，Fake failure 能拒绝非法来源和缺证据内容且不重试、不写部分结果；`py_compile` 与 `git diff --check` 通过。本机 fixture HTTP 根页面、5.0 plan 和 5.0 report 均返回 200/合法固定响应。

浏览器补充验收：Codex 应用内测试浏览器当时两次发现结果均为空，因此没有生成自动点击、控制台或网络日志证据；2026-08-28 用户已明确确认亲自完成浏览器手工测试且验收成功，本批据此接受浏览器非模型路径通过。该结论的证据类型是“用户手工验收确认”，不能改写成 Codex 自动浏览器验收，也不能替代 7R5-J 仍需执行的真实 PostgreSQL/API/浏览器最终全链验收。开发中第一次 Fake 调试调用在显式离线 Settings 修复前曾走 Service 默认配置加载器，因此可能读取过本机 `.env` 配置字符串；没有输出秘密、没有实例化真实 Adapter、没有网络请求或费用，随后已改成显式空 Key并由测试锁死，但这段中间过程不能倒推成“从未读取配置”。至此 7R5-H 的非付费门槛全部完成，真实 DeepSeek 调用和费用仍为 0；本批立即停止，唯一下一步是等待用户另行确认 7R5-I 的美元金额上限或明确“不设上限”。

## 32. 7R5-I：真实 AI 质量验收

依赖：7R5-H 全绿、官方价格已重新查询、用户明确确认本轮金额上限或不设上限。

唯一目标：执行第 20 节冻结的真实计划、报告和稳定性质量验收。

允许修改：只允许新建独立不可覆盖结果文件，并在运行后追加本文和状态记录；质量失败不得当场改 Prompt 或代码。

链路位置：真实 AI Adapter 质量验证。

固定交付：逐调用原始响应审计、模型/参数/Prompt/Schema、token/cache/费用、逐样本和汇总门槛、人工分母、结果 hash。

禁止：覆盖历史、自动补跑、边跑边改标签、失败后直接整改、数据库业务写入、进入 7R5-J。

验证与停止：按第 20、22 节重算。通过或失败都立即停止。失败先登记新整改设计并重新确认；通过后唯一下一步是等待确认 7R5-J。

### 32.1 真实 raw 执行记录（2026-08-28）

用户明确授权 7R5-I 并给出本轮 USD 10 金额上限。运行前重新查询 DeepSeek 官方价格页；查询时间为 `2026-08-28T09:08:45.432+08:00`，当时为工作日 peak，`deepseek-v4-flash` 的 cache-hit input、cache-miss input、output 单价依次为 `$0.014 / $0.44 / $1.32`（USD / 1M tokens）。独立价格快照为 `2026-08-28-stage7-7r5i-pricing-snapshot.json`，24 小时有效，没有覆盖 7R5-H 快照。

读取真实 API Key 前，7R5-H 专项 `20 passed`；dry-run 为真实调用 0、正式写入 0、真实 Adapter 未实例化且 API Key 未读取；冻结 fixture hash `2ecc2da188f09883c1b6acaa40d0ca25f2306f2894e7f060a3a26aefb2fa9643`、模型、Prompt、Schema、参数和 `45/90` 调用预算均未漂移；13 份历史质量证据 hash 全部匹配；raw/human/final 三个正式路径全空；`git diff --check` 通过。随后只执行唯一一轮 real raw，没有修改 Prompt、Schema、Adapter、Service、Model、migration、API、React、冻结样本或 PostgreSQL 业务数据。

本轮计划 45 次业务调用，实际发出 29 次业务调用和 29 个 API attempt，所有 attempt 均获得模型响应；基础设施失败 0、技术重试 0、失败 attempt 费用预留 0。10 次计划调用中，Service 接受 6 份，4 份以 `JOB_EVALUATION_PLAN_V5_UNSUPPORTED_CRITERION` 拒绝；20 份正式报告中 13 份实际调用、7 份因上游计划不合法而未调用，实际调用结果只有 1 份通过 Service，12 份以 `SCREENING_EVALUATION_INVALID_MODEL_OUTPUT` 拒绝；15 次稳定性中 6 次实际调用、9 次因上游计划不合法而未调用，6 次均被严格内容校验拒绝。内容错误和上游阻塞均没有重试、修复调用或补跑。

token 汇总为 input `120,360`、output `48,425`。计划 input 的 cache hit/miss 为 `15,360 / 11,603`；报告 Adapter 没有返回 cache 拆分，正式报告与稳定性共 `93,397` input tokens 按全部 cache miss 保守计费，因此费用重算口径为 cache hit `15,360`、cache miss `105,000`、output `48,425`。峰值价格下估算费用为 `$0.11033604`，USD 10 上限剩余 `$9.88966396`。

raw 结果为 `v5-quality-results/2026-08-27-stage7-7r5i-quality-raw-results.json`，大小 `344,355` bytes，SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`。自动汇总已经确定计划结构合法 `6/10`、报告结构合法 `1/20`、报告必备五分区 `0/20`、稳定性合法运行 `0/15`，因此这些自动硬门槛没有达到；raw 仍按合同保持 `quality_gate_passed=null`、`quality_conclusion_allowed=false`，无权代替人工给出最终质量结论。13 份历史证据 hash 在运行前后完全一致；人工审计和 final 正式路径仍不存在。

当前必须停止等待用户根据冻结标签人工审阅 raw，并提交绑定 raw hash、fixture hash、审阅人、带时区审阅时间及 12 个固定人工指标的审计文件。Codex 不冒充人工审阅者，不创建审计结论，不执行 finalize，不补跑失败样本，不整改生产代码，也不进入 7R5-J。

### 32.2 计划人工审核事实与暂停决定（2026-08-28）

用户在 Codex 展示完整 JD、冻结标签和 DeepSeek 评价项后，逐份确认 P00—P09 的计划语义记录。辅助 CSV 当前记录 55/55 个冻结关键要求为覆盖、22 个调用前冻结的禁止新增标签均未出现、26 个非评价标签均未误分类、10 份计划敏感项合计 0；这些是引导式人工审核辅助记录，不是绑定审阅人/时间和 12 个固定指标的正式 `human-audit.json`，不能据此 finalize。

程序仍只有 6/10 成功。4 个失败全部为 `JOB_EVALUATION_PLAN_V5_UNSUPPORTED_CRITERION`，同规则只读回放确定首个拒绝点分别为：P01 的 `Node.js/SSR`（原文同样包含 `Node.js/SSR`，标点归一后比较不一致）、P02 的 OLAP 相关非排他举例 `Hive/Presto`、P03 的“产品需求文档（PRD）”常见缩写，以及 P08 的 `UX/UI`（原文同样包含 `UX/UI`，斜杠归一后比较不一致）。这 4 份均已通过 JSON/Schema、原文 `source_quote` 定位、敏感内容、Prompt 污染和招聘决定检查；失败集中在 Service 将评价点名称、描述和 `screening_focus` 与来源做机械 token/连续双字支持性比较的硬拒绝层。

用户确认的产品判断是：DeepSeek 生成的是必须经 HR 编辑确认的草稿；与 JD 主题直接相关的缩写、同义表达、符号写法和非排他举例可以接受，只要它们不被提升为 JD 未规定的硬门槛，也不排除等价经验。用户据此明确暂停 20 份报告和 5×3 稳定性的后续人工审核，先解决 Service 误拒绝。原 7R5-I raw 的大小、SHA-256、调用/token/cache/费用、自动 6/10、1/20、0/15 统计、冻结标签和三个正式路径状态均不得修改；当前也不得用新业务判断把旧 raw 追认为通过。

## 32A. 7R5-IR：计划 Service 支持性校验整改

### 32A.1 整改目标、范围和共同边界

唯一业务目标：取消“评价点普通语义必须与 JD 原文逐词对应”的整单硬拒绝，只让 Service 拦截伪造来源、安全越界、可确定的新增硬门槛和明显无关主题；缩写、标点、同义表达、相关非排他举例和清单粒度交给 `pending_confirmation` 中的 HR 审核。

通俗解释：门卫继续拦危险品和明显拿错的包，但不再因为包装上的点号、斜杠、缩写或相关举例不同，就把整份草稿扔掉。

本整改只处理 `JobEvaluationPlan` 5.0 的 Service 支持性校验，不处理报告 Service 的 18 次内容失败，不修改 DeepSeek Prompt、输出 Schema、Adapter、API、Model、migration、React、PostgreSQL 业务数据、冻结 fixture、质量运行器或历史结果。链路位置固定为：

```text
DeepSeek 已返回结构化评价清单
        ↓
Schema 已通过
        ↓
JobEvaluationPlan Service 来源 / 安全 / 支持性校验  ← 本整改
        ↓
pending_confirmation
        ↓
HR 编辑并确认后才可进入 Screening
```

共同保护：

1. 7R5-I raw SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`、人工辅助记录、human/final 空路径和 13 份历史质量证据只读；不得覆盖、回填或改写。
2. 不读取真实 API Key、不实例化真实 Adapter、不调用 DeepSeek，费用固定为 USD 0。
3. 不用正式质量样本反向修改 Prompt，不更换模型、Schema、temperature、thinking 或报告合同。
4. 不把 Service 放宽解释成自动放行：计划仍只能进入 `pending_confirmation`，只有 HR 保存并确认后的当前 5.0 `ready` 才能用于初筛。
5. 不自动恢复 7R5-I 报告/稳定性人工审核，不自动补齐当时因上游阻塞而未调用的样本，不自动进入 7R5-J。

固定顺序：

```text
7R5-IR-A 支持性校验合同红灯
→ 停止，等待用户确认
→ 7R5-IR-B Service 最小整改与零调用回放
→ 停止，另行设计独立真实复验
```

### 32A.2 7R5-IR-A：支持性校验合同红灯

依赖：本节书面顺序获得用户明确确认；开始前重新检查分支、基线提交、`git status`、相关差异、raw/human/final 路径和历史 hash。

唯一目标：先用自动化准确证明当前 Service 对正常缩写、符号和相关举例的误拒绝，以及放宽后仍必须保留的硬门槛，不修改生产实现。

允许修改：新增一个最小 5.0 支持性校验专项测试文件，或在 `backend/tests/services/test_job_evaluation_plan_v5_generation_contract.py` 和 `backend/tests/api/test_job_evaluation_plan_v5_edit_contract.py` 中增加对应合同；只允许同步本文和 `PROJECT_STATE.md` 的实际红灯记录。

链路位置：测试层，覆盖未来的 Schema → Service → `pending_confirmation`，生产链不修改。

固定红灯合同：

1. `Node.js` 点号、`UX/UI` 斜杠、产品需求文档/`PRD` 缩写、OLAP 与 `Hive/Presto` 非排他举例必须可形成合法 AI 草稿；这些表达不得被提升为新增 required 门槛。
2. 原文没有的更高年限、学历、学位、证书、认证和明确排他技术要求继续稳定失败。
3. “负责项目交付”被改成“Python 开发能力”等没有可解释主题锚点的明显无关内容继续失败。
4. 错误 `source_field/source_quote`、非法 JSON/Schema、Prompt 污染、敏感属性、招聘决定和超过 30 项继续失败，内容错误不重试。
5. `ai_from_jd` 项经 HR 做普通同义改写后使用同一边界；真正超出来源的 HR 新增项仍必须转为 `hr_added`。
6. 一个合法语义差异不能再使整份清单 failed；成功草稿仍只能是 `pending_confirmation`，不能自动 ready 或启动 Screening。

禁止：修改任何生产 Prompt、Schema、Adapter、Service、API、Model、migration、React、数据库、质量运行器、冻结样本或结果文件；禁止真实模型调用、通过删断言/改预期把现状冒充通过。

验证：新测试必须正常收集，并只因当前 Service 行为与新合同不一致而红；既有来源、安全和硬门槛测试保持通过；执行相关既有回归、`py_compile` 和 `git diff --check`。完成标志是每个红灯都有明确的 IR-B 责任，0 次真实调用、0 写入。失败返回测试/夹具设计层。本批结束后停止，唯一下一步是等待用户确认 7R5-IR-B。

#### 32A.2.1 7R5-IR-A 实施结果（2026-08-28）

本批只修改 `backend/tests/services/test_job_evaluation_plan_v5_generation_contract.py` 和 `backend/tests/api/test_job_evaluation_plan_v5_edit_contract.py`，没有修改生产 Service、Prompt、Schema、Adapter、API、Model、migration、React、质量运行器、冻结样本或结果文件。

修改前两份相关合同为 `46 passed`。新增 11 个合同参数用例后，定向运行结果为 `5 failed, 6 passed, 46 deselected`：`Node.js`、`UX/UI`、`PRD`、`Hive/Presto` 非排他举例四个生成用例，以及 `Kubernetes/K8s` 的 `ai_from_jd` HR 编辑用例，均只因当前 `JOB_EVALUATION_PLAN_V5_UNSUPPORTED_CRITERION` 机械支持性检查而红；新增年限、学历、学位、证书、认证和排他技术六个保护用例全部通过。来源、安全、超过 30 项、非法 JSON 和内容不重试定向回归为 `14 passed`；排除 11 个新增合同后的既有两文件回归仍为 `46 passed`。两份测试 `py_compile` 和 `git diff --check` 通过。

API 编辑用例仅在测试事务中创建临时数据并由外层事务回滚，没有持久化正式业务数据；真实 DeepSeek 调用、API attempt、token 和新增费用均为 0。红灯只能证明待修改责任位于 Service 的支持性校验，不能证明 IR-B 已实现或真实质量已通过。本批完成后停止，唯一下一步是等待用户明确确认 7R5-IR-B。

### 32A.3 7R5-IR-B：Service 最小整改与零调用回放

依赖：7R5-IR-A 红灯责任完整且用户另行确认。

唯一目标：用最小 Service 修改让 IR-A 红灯转绿，同时保持来源、安全、明确新增硬门槛、状态和 HR 确认门禁不退让。

允许修改：`backend/app/services/job_evaluation_plan_service.py` 中 5.0 评价点支持性校验和行为合同版本；IR-A/既有 5.0 生成与编辑测试；本文和 `PROJECT_STATE.md` 的实施结果。行为合同从 `lightweight_plan_generation_v2` 递增为 `lightweight_plan_generation_v3`，Prompt 仍为 `job_evaluation_plan_lightweight_v2`，AI/计划 Schema 仍为 `5.0`。

链路位置：Service；不修改前端、API、Schema、Adapter、Model 或 PostgreSQL。

固定实现语义：

1. 保留 `source_quote` 在对应冻结 JD 字段中的原样定位，模型不能伪造来源。
2. 删除“每个非通用英文 token 都必须出现在归一化来源中”的全量包含硬拒绝，避免 `Node.js/Nodejs`、`UX/UI/UXUI` 和 `PRD` 误判；比较双方必须使用一致的归一化口径。
3. 不再使用“名称中的某个中文连续双字”冒充完整语义证明；如保留粗粒度主题锚点，只能用于拦截明显无关内容，必须对中英文和符号采用对称、可解释规则，不能要求逐词一致。
4. 相关非排他举例允许进入草稿；Service 不把 `Hive/Presto` 等例子自动改成 required，也不排除 ClickHouse 等同类经验。当前批次不新增 warning Schema；HR 通过现有来源展示、草稿编辑和确认门禁负责最终取舍。
5. 原文没有的数字年限、学历、学位、证书、认证和明确排他要求继续硬失败；安全、结构、来源、30 项上限、内容不重试和失败无部分计划保持不变。
6. 生成路径和 `ai_from_jd` 的 HR 保存路径使用同一规则；HR 真正新增 JD 外主题仍使用 `hr_added`。
7. 放宽后的 AI 计划只到 `pending_confirmation`；不得自动确认、自动启动报告或改变 HR 决策。

禁止：Prompt/Schema/Adapter/API/Model/migration/React/Screening 报告整改，真实 PostgreSQL 业务写入，真实 DeepSeek，修改冻结 fixture/标签、质量运行器和任何 7R5-I/历史结果；禁止顺手处理报告 Service 的其他失败。

验证：IR-A 全部转绿；既有 5.0 生成、编辑/API 映射、来源/敏感/污染/招聘决定/>30/内容不重试回归通过；受影响后端回归和后端全量通过；`py_compile`、静态扫描和 `git diff --check` 通过。另用只读脚本把原 7R5-I raw 中 P00—P09 的 10 个计划响应送入修改后的解析/校验函数，目标为 10/10 可形成草稿；该回放不写原 raw、不创建正式结果、不调用 Adapter，只证明新 Service 能接收这些既有响应，不能冒充新的真实质量复验。验证前后复核 raw SHA-256、三个正式路径和 13 份历史 hash 不变，真实调用/attempt/token/费用新增均为 0。

完成标志：正常语义差异不再误拒，明确硬门槛和安全防线未降级，行为版本为 v3，全部验证通过且证据未改。若正常表达仍失败，返回 Service 归一/主题锚点；若危险新增被放行，返回 Service 硬门槛；若请求/数据形状需改变，立即停止并返回设计层，不在本批扩展 Schema/API。本批完成后停止，不能恢复旧 7R5-I 或进入 7R5-J；唯一下一步是另写独立真实复验的样本、路径、金额和不可覆盖方案，重新获得用户确认。

#### 32A.3.1 7R5-IR-B 实施结果（2026-08-28）

本批只修改 `backend/app/services/job_evaluation_plan_service.py`、IR-A 两份测试和本文/`PROJECT_STATE.md`。行为合同升级为 `lightweight_plan_generation_v3`；Prompt 仍为 `job_evaluation_plan_lightweight_v2`，AI/计划 Schema 仍为 `5.0`。Service 删除了“每个英文 token 必须逐字存在”的硬拒绝，技术词在双方采用同一标点归一口径；普通缩写、符号和相关非排他举例使用粗粒度主题锚点进入 HR 草稿。数字或中文数字年限/人数等量化门槛、学历/学位/证书/认证，以及原文没有的排他措辞继续硬失败；原文定位、安全、30 项上限、内容不重试和 `pending_confirmation → HR 确认 → ready` 状态门禁保持不变。

IR-A 新合同从 5 个预期红灯变为 `11 passed`；生成与 HR 编辑两份完整合同为 `57 passed`。包含 API 映射、Schema、静态扫描和质量合同的扩大回归中，Service/API 相关部分为 `140 passed + 3 subtests passed`，另有 6 个与 Service 无关的结果目录生命周期失败。排除这 6 个已确认旧断言后的后端全量为 `1200 passed + 425 subtests passed`；不排除任何测试的真实全量为 `1200 passed + 425 subtests passed + 6 failed`。六个失败固定为：质量运行器 5 个仍以“raw 路径必须为空”为前提的 pre-run 测试，以及静态扫描 1 个“整个 v5-quality-results 目录必须为空”的 pre-run 测试。当前 raw 和人工辅助目录是受保护证据，不能删除来换取绿灯；本批也禁止修改质量运行器，因此该例外返回下一次独立复验的测试生命周期设计层，不归因于 Service。

只读回放直接把原 7R5-I attempt audit 中 P00—P09 的 raw response 送入修改后的解析/校验函数，没有调用 Adapter，结果为 `10/10` 可形成草稿；各份评价点数量依次为 `17/11/12/10/6/7/13/11/11/18`。该结果只能证明修改后的 Service 能接收既有模型响应，不能追认旧 raw 通过，也不能代替新的真实质量复验。`py_compile`、其余静态合同和 `git diff --check` 通过；真实 DeepSeek 调用/API attempt/token/费用新增均为 0，没有持久化正式 PostgreSQL 业务数据。

验证后原 raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`，human/final 路径仍空，13 份历史结果 hash 全部不变。Service 整改目标已完成，但后端“所有测试零失败”不能在当前受保护 raw 存在且禁止改质量运行器的边界内成立；下一次独立真实复验设计必须先把 pre-run、post-raw 和新一轮独立路径的测试前提拆开，再重新确认样本、路径、金额和停止点。当前停止，不自动进入该设计、真实调用、7R5-J 或其他整改。

## 32B. 7R5-I2：整改后的独立真实质量复验

### 32B.1 目标、身份和不可覆盖边界

`7R5-I2` 是 Service 整改后的独立复验，不是继续、补跑、覆盖或 finalize 原 `7R5-I`。原 I 永久保留整改前事实：raw 存在且 `quality_gate_passed=null`，原 human/final 继续为空；原人工辅助目录只作诊断材料，不能被新 finalizer 当成正式人工审计。

通俗解释：旧答卷封存，新开一张答卷。新答卷可以使用同一套冻结题目来比较整改前后，但文件、费用、调用记录、人工审核和结论必须完全独立。

本序列只处理质量验收基础设施、零调用诊断、独立真实 raw、人工审核和 final。它不授权修改 Prompt、Schema、计划/报告 Service、Adapter、API、Model、migration、React、PostgreSQL 业务数据或冻结样本；如果零调用诊断发现报告 Service、Prompt 或标签问题，必须停止并另写对应整改顺序，不能在 I2 中边验收边修。

链路位置：

```text
冻结样本
  ↓
质量合同 / 结果生命周期 / 费用门禁  ← I2-A/B
  ↓
旧 raw 直接解析诊断                  ← I2-C，0 调用
  ↓
官方价格与用户金额授权               ← I2-D，不读 Key
  ↓
真实 Adapter → Model → 新 raw         ← I2-E
  ↓
用户人工审核 → final                  ← I2-F/G
```

### 32B.2 固定结果路径和生命周期

旧证据继续固定：

- 原 raw：`docs/stages/stage7/v5-quality-results/2026-08-27-stage7-7r5i-quality-raw-results.json`，SHA-256 必须始终为 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`；
- 原 human：`docs/stages/stage7/v5-quality-results/2026-08-27-stage7-7r5i-quality-human-audit.json`，继续为空；
- 原 final：`docs/stages/stage7/v5-quality-results/2026-08-27-stage7-7r5i-quality-final-results.json`，继续为空；
- 原 `7r5i-human-review-helper/` 只读保留，但不是正式结果路径。

I2 新证据固定为：

- 零调用预检：`docs/stages/stage7/v5-quality-results/2026-08-28-stage7-7r5i2-zero-call-preflight.json`；
- 新 raw：`docs/stages/stage7/v5-quality-results/2026-08-28-stage7-7r5i2-quality-raw-results.json`；
- 新 human：`docs/stages/stage7/v5-quality-results/2026-08-28-stage7-7r5i2-quality-human-audit.json`；
- 新 final：`docs/stages/stage7/v5-quality-results/2026-08-28-stage7-7r5i2-quality-final-results.json`；
- 新价格快照：`docs/stages/stage7/2026-08-28-stage7-7r5i2-pricing-snapshot.json`。

生命周期测试不再要求整个目录为空，而是按精确路径判断：

| 状态 | 旧 raw | I2 preflight | I2 raw | I2 human | I2 final |
| --- | --- | --- | --- | --- | --- |
| `i2_not_started` | 必须存在且 hash 固定 | 空 | 空 | 空 | 空 |
| `i2_preflight_complete` | 不变 | 存在且不可覆盖 | 空 | 空 | 空 |
| `i2_raw_complete` | 不变 | 不变 | 存在且不可覆盖 | 空 | 空 |
| `i2_human_complete` | 不变 | 不变 | 不变 | 存在且不可覆盖 | 空 |
| `i2_final_complete` | 不变 | 不变 | 不变 | 不变 | 存在且不可覆盖 |

任何状态都必须保持 13 份旧质量证据 hash 不变；未知正式 JSON、跨轮路径重叠、已有文件覆盖、跳过前置状态或把 helper 当 human audit 都必须失败。

### 32B.3 冻结质量、调用和费用合同

I2 继续使用原冻结 10 份 JD、20 组 JD/Resume、5 组 × 3 次稳定性及其全部样本/标签 hash，不修改标签来迎合整改结果。模型、Prompt、Schema 和推理参数保持：

- 模型：`deepseek-v4-flash`；
- thinking：disabled；temperature：0.1；JSON object；SDK 自动重试：0；
- 计划 Prompt：`job_evaluation_plan_lightweight_v2`；报告 Prompt：`screening_evaluation_lightweight_v1`；
- 计划/报告 Schema：5.0；计划 Service 行为合同：`lightweight_plan_generation_v3`；
- 计划 max output tokens：8000；报告：12000。

调用合同仍为计划 10、报告 20、稳定性 15，正常最多 45 次业务调用；每次业务调用仅允许一次网络/限流/超时/服务端技术重试，API attempt 硬上限 90。JSON、Schema、证据、安全、未知/遗漏/重复 ID、方向矛盾等内容错误 0 重试；不得补跑失败样本、Self-Consistency、Self-Refine、模型修复或 Judge 调用。上游失败可以阻塞下游并减少实际调用，但不能自动追加调用补足 45。

I2-D 前不得读取真实 API Key。实际运行必须重新查询 DeepSeek 官方价格并生成独立快照，24 小时有效；用户必须在同一轮明确给出美元金额上限，金额为空、占位、含糊或无法换算时立即停止。费用守卫在每个 attempt 前按最坏输出预留，失败无 token 时保留预留；下一 attempt 可能超额时先停止。

自动和人工质量门槛仍使用第 20.1 节，不因第一次 raw 失败或 Service 整改而降低。新 raw 无权宣布通过，只有 I2-F 用户人工审计合法且 I2-G final 全部门槛通过才允许形成 I2 质量结论。

### 32B.4 固定实施顺序

```text
7R5-I2-A  生命周期合同红灯
→ 停止，等待确认
→ 7R5-I2-B  质量运行器独立路径与生命周期实现
→ 停止，等待确认
→ 7R5-I2-C  旧 raw 全类别零调用预检
→ 停止并处理诊断结论
→ 7R5-I2-D  官方价格与金额授权门禁
→ 停止，等待真实运行明确授权
→ 7R5-I2-E  唯一一轮独立真实 raw
→ 停止，等待用户人工审核
→ 7R5-I2-F  用户人工审计文件
→ 停止，等待 finalize 确认
→ 7R5-I2-G  final 校验与结论
→ 停止；只有全部通过才可讨论 7R5-J
```

### 32B.5 7R5-I2-A：生命周期合同红灯

依赖：本节书面顺序获得用户明确确认。

唯一目标：先用测试准确描述“旧 raw 合法存在、新一轮路径必须为空、各状态不可跳跃”，不修改质量合同或运行器实现。

允许修改：`backend/tests/test_stage7_7r5_quality_runner.py`、`backend/tests/test_stage7_v5_static_scan_contract.py`，以及本文和 `PROJECT_STATE.md` 的实施记录。链路位置是测试层和验收基础设施边界。

固定红灯：旧 raw/hash 和 13 份历史证据必须通过；目录非空本身不再失败；I2 四个证据路径互不重叠且初始为空；状态矩阵、未知 JSON、helper 隔离、跨轮覆盖、行为合同 v3、dry-run/Fake 0 Key/0 调用/0 正式写入都必须有合同。当前 6 个旧生命周期失败应被新合同替换为责任清晰的 I2-B 红灯，不能删断言、删除 raw 或把失败标成 xfail。

禁止：修改 `scripts/`、任何生产代码、结果文件、fixture 或数据库；禁止读取 Key、调用模型。验证新测试正常收集，既有历史 hash/写入拒绝/费用守卫合同保持通过，`py_compile` 和 `git diff --check` 通过。完成后停止，唯一下一步是等待 I2-B 确认。

实施结果（2026-08-28）：I2-A 已完成。修改前精确复现 6 个旧生命周期失败；修改后两份合同测试为 `35 passed + 10 failed`，10 个红灯分别锁定行为版本 v3、I2 run identity/四条路径/五态生命周期、旧 raw 与 helper 合法共存、未知 JSON 拒绝、跨轮覆盖拒绝，以及 dry-run/Fake/real 接受 I2 上下文。既有 fixture、13 份历史 hash、write-once、价格与费用守卫定向 `6 passed`；`py_compile`、`git diff --check` 通过。旧 raw 大小仍为 344,355 bytes，SHA-256 仍为 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`；I2 preflight/raw/human/final/价格五条路径均未创建。未修改 `scripts/`、产品代码、fixture、数据库或结果，未读取 Key、实例化真实 Adapter、调用 DeepSeek 或产生费用。用户表达的未来“调用无上限”不替代 I2-D 的最新价格与明确美元上限门禁。当前停止，唯一下一步是等待用户另行确认 I2-B。

### 32B.6 7R5-I2-B：独立路径与生命周期实现

依赖：I2-A 红灯责任完整且用户另行确认。

唯一目标：让质量合同和运行器按 I2 精确路径及状态工作，使合法旧 raw 存在时 dry-run/Fake/全量测试恢复通过，同时任何旧证据和新证据都不可覆盖。

允许修改：`scripts/stage7_7r5_quality_contract.py`、`scripts/run_stage7_7r5_quality.py`、I2-A 两份测试和两份状态文档。可以新增受测的 run identity/result lifecycle 数据结构，但不得修改产品 Service、Prompt、Schema、Adapter 或 fixture。

交付：注册 `7R5-I` 只读证据和 `7R5-I2` 新路径；显式校验上表五种状态；write-once 只接受当前 run 已登记且在当前状态允许写入的路径；dry-run/Fake 使用 I2 上下文，不因旧 raw 存在而失败；静态扫描从“目录必须为空”改成“已登记证据合法、未知正式 JSON 失败”；执行合同新增 Service 行为版本 v3。旧 I real/finalize 入口必须保持不可再次执行。

验证：I2-A 转绿，原 6 个生命周期失败消失；H/质量运行器专项、Fake normal/failure、dry-run、受影响回归和后端全量通过；真实调用、API attempt、token、费用和正式写入为 0；raw/hash、原 human/final 空路径和 13 份历史证据不变。失败返回质量合同/运行器层。完成后停止，唯一下一步是等待 I2-C 确认。

实施结果（2026-08-28）：I2-B 已完成并停止。质量合同登记封存 run `7R5-I`、活动 run `7R5-I2`、四条 I2 证据路径和五态生命周期；旧 raw 固定 SHA-256 并禁止旧 real 入口、补写或覆盖旧 human/final。目录非空不再失败，已登记旧 raw 与 helper 合法共存；未知 JSON、路径重叠、状态跳跃、未登记 run 和跨轮写入继续硬失败。write-once 只允许按 `preflight → raw → human → final` 的下一路径写一次。dry-run/Fake/real 接受显式 I2 run identity，执行合同新增 Service 行为版本 `lightweight_plan_generation_v3`。A 的两份测试从 `35 passed + 10 failed` 转为 `46 passed`；计划 Service、HR 编辑与质量合同合跑 `103 passed`；后端全量 `1210 passed + 425 subtests passed`，只有既有 PyPDF2 弃用和异步连接清理 warning。dry-run 实测为 `i2_not_started`、0 调用、0 写入、不读 Key、不实例化 Adapter；四份脚本/测试 `py_compile` 和 `git diff --check` 通过。旧 raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`；原 human/final 与 I2 preflight/raw/human/final/价格路径仍不存在，13 份历史 hash 不变。未修改产品前端/API/Schema/Service/Model/PostgreSQL、Prompt、Adapter 或 fixture；DeepSeek 调用/API attempt/token/费用新增均为 0。唯一下一步是等待用户另行确认 I2-C。

### 32B.7 7R5-I2-C：旧 raw 全类别零调用预检

依赖：I2-B 全部通过且用户另行确认。

唯一目标：在花钱前直接重放旧 raw 中所有可取得的计划、报告和稳定性原始响应，判断当前 Service 是否还存在已知误拒绝，不重新请求模型。

允许修改：新增只读预检脚本及其测试，写入唯一 I2 preflight 路径，并同步状态文档。脚本只能读取冻结 fixture、原 raw 和当前解析/校验函数；不得实例化 Adapter、读取 Key、写 PostgreSQL、修改 raw 或生成质量结论。

预检必须记录每个旧 attempt 的 case ID、原状态、当前解析状态、当前错误码、自动可确定的结构/来源/安全结果和需要人工判断的项目；不得复制 API Key、内部 Prompt、堆栈或完整思维链。计划目标为 P00—P09 `10/10`；报告和稳定性不预设通过数字，必须如实分类。

停止门禁：只要发现疑似报告 Service 误拒绝、无法区分模型事实错误与校验误判、或任何安全防线回退，就停止。疑似 Service 问题返回独立报告 Service 设计；内容质量问题返回 Prompt/模型质量讨论；人工标签不明确返回人工审阅层。只有不存在已知 Service 缺陷、用户看过预检并明确同意继续，才可进入 I2-D。完成后停止。

实施结果（2026-08-28）：I2-C 已完成并触发停止门禁。新增 `scripts/run_stage7_7r5i2_preflight.py` 与 `backend/tests/test_stage7_7r5i2_preflight.py`，不实例化 Adapter、不读配置/Key、不联网、不写 PostgreSQL，直接以当前计划与报告解析/校验函数回放封存 raw 中全部 29 个可取得响应；另外 7 个报告和 9 个稳定性 case 因原计划阻塞而没有模型响应，明确记为不可回放，没有伪造补齐。计划 10/10 当前通过；报告 13 个有响应 case 中 1 个通过、12 个拒绝；稳定性 6 个有响应 case 全部拒绝。18 个拒绝按当前安全消息分为严格结构 6、Resume 不支持的数字事实 2、年限与后端时间事实冲突 8、普通事实不受 Resume 支持 1、无直接证据结论 1；自动回放不能可靠判定这些是模型内容错误还是报告 Service 误拒绝，因此 `human_or_service_adjudication_required=true`、`pricing_gate_allowed=false`，不得进入 I2-D/E。preflight 路径为 `docs/stages/stage7/v5-quality-results/2026-08-28-stage7-7r5i2-zero-call-preflight.json`，大小 33,887 bytes，SHA-256 `185b42d7c55d6654cedfa251f340d89469470800336aa17be192ae3d1c28b6b2`；文件不复制原始响应，只保存响应 hash/长度、逐 case 原状态、当前状态、错误码和安全消息。专项为 `50 passed`，后端全量为 `1214 passed + 425 subtests passed`，`py_compile`、`git diff --check` 通过。旧 raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`，13 份历史 hash 不变；I2 raw/human/final/价格路径仍空。新增 DeepSeek 业务调用/API attempt/token/费用均为 0，正式写入只有唯一 preflight 1 份。当前停止，下一步只能先讨论并写入独立报告 Service/内容诊断批次，获得确认后再实施；不得直接进入 I2-D。

### 32B.8 7R5-I2-D：官方价格与金额授权门禁

依赖：I2-C 没有未解决的 Service/人工判断阻塞，且用户另行确认。

唯一目标：零调用完成真实运行的最后门禁。重新查询 DeepSeek 官方价格，记录北京时间/时区、peak/off-peak、三项单价、来源和 24 小时有效期；生成 I2 独立价格快照。

Key 前必须验证：I2-B/H 专项通过；dry-run 0 调用、0 写入、不加载真实 Adapter；fixture/标签/模型/Prompt/Schema/参数/行为版本/45/90 预算不漂移；旧 raw/hash、原 human/final、I2 preflight、I2 三个正式空路径和 13 份历史证据符合状态；`git diff --check` 通过。用户必须明确给出本轮美元上限。本批不读取 Key、不调用模型，完成后停止，等待 I2-E 的真实运行授权。

### 32B.9 7R5-I2-E：唯一一轮独立真实 raw

依赖：I2-D 快照仍在 24 小时内、金额明确且用户在同一轮授权真实运行。

唯一目标：使用冻结运行器执行一次 I2 raw。只允许写新 raw；每个 attempt 继续记录 case、attempt、请求/返回模型、Prompt/Schema/参数/行为版本、finish reason、token/cache、耗时、费用和原始响应，并执行金额/90 attempts/内容不重试门禁。

任何质量失败、金额停止或服务异常都只记录并停止；不得补跑、修代码、改标签、创建 human/final 或进入 J。结束必须报告实际业务调用/attempt、失败与技术重试、token/cache/费用/剩余额度、新 raw 路径/大小/hash、全部旧证据状态、自动已确定门槛和待人工门槛。完成后停止等待用户人工审核。

### 32B.10 7R5-I2-F：用户人工审计

依赖：I2-E raw 完整且用户另行确认开始审核。

Codex 只生成逐案清单、展示 JD/简历/模型内容、解释固定指标并记录用户明确判断；不得冒充人工审阅者、用 LLM-as-Judge、替用户推断结论或改变冻结标签。新输出必须重新审核，旧 helper 判断不能自动复制成 I2 标签。用户完成后写唯一 I2 human 路径，校验分母、case ID、枚举和签署信息，停止等待 finalize 确认。

### 32B.11 7R5-I2-G：final 校验与结论

依赖：I2 human 文件由用户完成并明确授权 finalize。

唯一目标：0 模型调用校验 raw/human、计算第 20.1 节全部门槛并 write-once 生成 I2 final。不得修改 raw/human、补跑失败样本或用代码替代人工判断。质量通过或失败都记录并停止；只有 I2 final 明确全部通过、全部 hash/路径/费用可复核且用户另行确认，才允许讨论 7R5-J。

## 32C. I2 报告整改问题 1：辅助列表数量过严

### 32C.1 已确认的业务规则

用户于 2026-08-28 明确确认：DeepSeek 可以生成超过 5 条的辅助信息，但必须优先选择最重要、最需要 HR 核实且互不重复的内容，不能把全部简历细节穷举成报告或问题。`strengths`、`gaps`、`risks_or_conflicts`、`missing_info` 和 `hr_follow_up_questions` 都是给 HR 的辅助材料，不是自动招聘决定；普通数量超出推荐值不能让整份报告作废。

冻结规则如下：

- Prompt 要求每类通常只保留 1—5 条最高价值内容；允许 `strengths` 或 `risks_or_conflicts` 在确无事实时为空，现有必填/可空语义不变；
- 必须合并同义或重复问题，优先核实会影响岗位匹配判断、证据真实性、个人职责和关键缺口的信息；不得全盘枚举简历细节；
- 1—5 条是质量推荐值，不是 Schema 合法性硬上限；五类列表统一使用 20 条技术安全硬上限；
- 6—20 条不得因数量本身被拒绝，也不得静默截断、排序或删除，完整保留给 HR 编辑；超过 20 条仍以结构异常硬失败；
- 不改变评价项 ID 完整性、0—10/0—100 分数、非零证据、来源、数字/年限事实、安全、敏感属性和禁止自动招聘决定等门禁；
- AI 输出 Schema 仍为 `5.0`，字段和持久化形状不变，本次是向后兼容的数量容忍放宽；报告 Prompt 升级为 `screening_evaluation_lightweight_v2`，旧报告继续只读，不回填或重写。

链路位置：`前端 → API → Schema（本问题主要位置）→ Service → Model`。前端只展示完整结果供 HR 取舍；本问题不修改数据库表、业务状态或 HR 决策。

### 32C.2 有序实施批次

```text
7R5-I2-R1-A  辅助列表数量合同红灯
→ 停止，等待实现确认
→ 7R5-I2-R1-B  Prompt v2 与 Schema 容忍实现
→ 停止，等待回放确认
→ 7R5-I2-R1-C  六个旧结构失败零调用回放
→ 停止，只讨论下一个问题
```

#### 7R5-I2-R1-A：数量合同红灯

唯一目标：只用测试固定“推荐少而精、6—20 合法、21 硬失败、不静默截断、其他安全门禁不放松”。

允许修改：报告 Prompt、Schema、Service 相关测试，质量合同测试，以及本文和 `PROJECT_STATE.md` 的实施记录。优先文件为 `backend/tests/prompts/test_screening_evaluation_v5_prompt.py`、`backend/tests/schemas/test_screening_evaluation.py`、`backend/tests/services/test_screening_evaluation_v5_service.py`、`backend/tests/test_stage7_7r5_quality_runner.py`；可新增一个只针对 R00/R09/R16/S00-1—3 的零调用回放测试文件。不得修改生产 Prompt/Schema/Service、fixture 或结果文件。

红灯合同：6、7、10 条 HR 问题以及 12 条 gaps/missing 必须合法并原样保留；任一辅助列表 21 条必须非法；Prompt 版本和“通常 1—5、最高价值、去重、不穷举”指令先红；评价项 ID、证据、数字/年限、安全和敏感属性既有保护继续通过。验证测试正常收集、既有回归不退步、`py_compile` 与 `git diff --check` 通过。真实调用、Key、Adapter、token、费用和正式写入均为 0。完成后停止，等待 R1-B 明确确认。

实施结果（2026-08-28）：本批只修改三份测试。修改前相关基线为 `46 passed + 1 warning`；新增合同后为 `17 failed + 49 passed + 1 warning`，17 个失败全部对应尚未实现的 Prompt v2、6—20 条合法且原样保留和质量运行合同版本，没有使用 xfail 或删除旧断言。任一五类列表 21 条拒绝，以及评价项 ID、证据/数字、安全、敏感属性、自动招聘决定、Prompt 注入、重复 JSON 键、内容错误不重试和 13 份历史 hash 保护定向为 `19 passed + 1 warning`。三份测试 `py_compile`、`git diff --check` 通过；旧 raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`，唯一 preflight 仍为 33,887 bytes、SHA-256 `185b42d7c55d6654cedfa251f340d89469470800336aa17be192ae3d1c28b6b2`，I2 raw/human/final 仍为空。生产 Prompt/Schema/Service/Adapter、fixture、结果和 PostgreSQL 均未修改，Key/真实调用/API attempt/token/费用新增为 0。本批只能证明下一批的修改责任被清楚锁定，不能证明数量问题已经修复；唯一下一步是等待用户确认 R1-B。

#### 7R5-I2-R1-B：Prompt v2 与 Schema 容忍实现

依赖：R1-A 红灯责任完整且用户另行确认。

唯一目标：让 DeepSeek 优先生成少量高价值内容，同时让后端接受 6—20 条而不把整份报告作废。

允许修改：`backend/app/prompts/screening_evaluation.py`、`backend/app/schemas/screening_evaluation.py`、`backend/app/core/config.py`、相关配置样例、质量合同/运行器中的冻结报告 Prompt 版本、R1-A 测试和两份状态文档。只在确有直接依赖时调整 Adapter 的版本检查测试；不得修改报告事实/年限/证据 Service 规则、Model、migration、API、React、fixture、旧 raw/preflight 或任何正式结果。

交付：Prompt 版本升级为 `screening_evaluation_lightweight_v2`，明确通常 1—5 条、按影响排序、合并重复、禁止穷举；AI 输出与持久化报告的五类辅助列表技术上限统一为 20，6—20 原样保留，21 拒绝，不做自动删减或二次模型修复。配置、执行合同、元数据与测试版本同步。验证 R1-A 转绿、Prompt/Schema/Service/质量专项和后端全量通过，旧 1.0—4.0 兼容、raw/preflight/hash 不变；真实调用和费用为 0。失败返回 Prompt/Schema 层。完成后停止，等待 R1-C 确认。

实施结果（2026-08-28）：R1-B 已完成并停止。报告 Prompt 升级为 `screening_evaluation_lightweight_v2`，新增“通常只保留 1—5 条最高价值内容、按岗位影响选择、合并同义或重复、不得穷举、每类最多 20 条”的明确指令。AI 原始输出 `AIScreeningEvaluationV5Output` 与可持久化 `ScreeningEvaluationV5ReportPayload` 共用 20 条常量，6—20 条不因数量本身失败且由现有 Service 原样传递，21 条继续由 Schema 硬拒绝；Schema 版本仍为 `5.0`，数据库字段和 JSON 形状不变。配置默认值、`.env.example`、Service 元数据测试和 I2 质量执行合同同步为 Prompt v2；报告 Service 事实/年限/证据/安全规则、Adapter、API、Model、migration、React 和 fixture 均未修改。

R1-A 三份合同由 `17 failed + 49 passed` 转为 `66 passed`；扩大 Prompt/Schema/配置/Adapter/Service/运行/质量回归为 `192 passed + 59 subtests passed`；后端全量为 `1234 passed + 425 subtests passed`，只有既有 PyPDF2 弃用和异步连接测试清理 warning。相关 Python 文件 `py_compile`、`git diff --check` 通过，13 份历史 hash 保护通过。旧 raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`；唯一 preflight 仍为 33,887 bytes、SHA-256 `185b42d7c55d6654cedfa251f340d89469470800336aa17be192ae3d1c28b6b2`；I2 raw/human/final 仍为空。未读取 Key、实例化真实 Adapter、调用 DeepSeek、产生 API attempt/token/费用或写入正式业务结果。本批证明离线数量合同和后端兼容已修复，不能证明六个旧响应能通过后续事实/证据门禁，也不能证明真实模型质量；唯一下一步是等待用户确认 R1-C。

#### 7R5-I2-R1-C：六个旧结构失败零调用回放

依赖：R1-B 全部通过且用户另行确认。

唯一目标：只重放 R00、R09、R16、S00-1、S00-2、S00-3 的旧响应，证明它们不再仅因 6—12 条辅助列表被结构拒绝，并如实记录随后出现的下一道 Service 门禁。

允许修改：I2-C 预检脚本/测试和状态文档；可以在 `v5-quality-results/7r5i2-diagnostics/` 新建一份不可覆盖的非正式诊断 JSON，但不得覆盖唯一 preflight、修改正式生命周期或复制完整原始响应。不得修改任何生产代码、Prompt、Schema、Service 或 fixture。

验证：6 个响应必须越过列表长度校验；若随后被事实、年限、证据或安全规则拒绝，只记录下一错误并停止，不能把“越过结构校验”写成整份报告通过。真实调用、Key、Adapter、PostgreSQL、token、费用均为 0；旧 raw/preflight 和 13 份历史证据 hash 不变。完成后停止，只与用户讨论下一个单独问题，`pricing_gate_allowed` 继续为 false，不进入 I2-D/E。

实施结果（2026-08-28）：R1-C 已完成并停止。扩展 `scripts/run_stage7_7r5i2_preflight.py` 和 `backend/tests/test_stage7_7r5i2_preflight.py`，只读取封存 raw 中 R00、R09、R16、S00-1、S00-2、S00-3 六个报告响应，并只为重建其确认清单回放 P00、P06、P09 三个支持计划；没有重放其他报告或稳定性响应。诊断先用当前 `AIScreeningEvaluationV5Output` 单独确认数量/Schema，再调用当前报告 Service 记录下一稳定门禁，禁止把 Schema 通过冒充整份报告通过。

结果为：六例 `current_schema_accepted=true`，辅助列表最大数量均在 7—12 条，`quantity_gate_crossed_count=6/6`、`current_schema_rejected_count=0/6`，证明问题 1 的数量门禁已解决；但 `full_report_accepted_count=0/6`、`next_service_gate_rejected_count=6/6`。R00 与 S00-1—3 共 4 例进入“AI 年限结论与后端经历时间事实冲突”，R09 进入“单项高分与未发现证据说明方向明显矛盾”，R16 进入“无直接证据的报告结论只能表达缺口、风险或待核实信息”。这些结果只定位下一道门禁，尚未判定是模型内容错误、Service 过严还是两者共同作用，必须分问题继续讨论。

唯一隔离诊断为 `docs/stages/stage7/v5-quality-results/7r5i2-diagnostics/2026-08-28-stage7-7r5i2-r1c-structure-replay.json`，大小 16,101 bytes，SHA-256 `f89426b3aa03b005cb533d6305590d17751dbada076dda526295b8a31b9ad3f3`；采用独占创建、拒绝覆盖，不复制原始响应、Prompt、Key、堆栈或思维链，仅保存响应 hash/长度、列表数量和稳定错误。R1-C 专项 `9 passed`，R1/质量/静态相关合同 `97 passed`，后端全量 `1239 passed + 425 subtests passed`；`py_compile`、`git diff --check`、13 份历史 hash 保护通过。旧 raw/preflight 大小和 SHA-256 不变，I2 raw/human/final 仍为空；Key、Adapter、DeepSeek 业务调用、API attempt、token、费用、PostgreSQL 写入和正式结果写入均为 0，诊断写入 1。`pricing_gate_allowed=false`，当前停止；唯一下一步是先与用户讨论数量最多的“年限结论与后端时间事实冲突”，未登记并确认新批次前不得修改 Prompt/Schema/Service 或继续回放。

## 32D. I2 报告整改问题 2：年限判断责任调整

### 32D.1 已确认的业务规则

用户于 2026-08-28 明确确认：后端继续按 `Application.applied_at` 从当前脱敏 Resume 中提取每段经历的起止日期，生成 `experience_period_facts`，并把原始日期、标准化月份、确定月份或上下界、可用状态和稳定 fact key 一并提供给 DeepSeek。后端是“日历计算器”，只负责可靠算出每段经历持续多久；DeepSeek 负责结合岗位语义判断哪些经历属于当前岗位相关经验，HR 负责最终审核 AI 报告。

当前报告 Service 使用正则表达式扫描 `reason` 和 `calculation_note` 中的“年/月”文字，再把抓到的数字与所引用事实的合并总月份机械比较。只读诊断已确认它会把日历日期、JD 年限门槛、各段经历、合计经历和“约 N 年”混为同一种候选人年限断言。现有 12 个年限拒绝中，10 个主要是这种 Service 误拒绝；R15、R19 同时存在模型结论或表述风险。该技术诊断不是正式人工质量标签，不能替代未来 I2 人工审计，也不能把 R15、R19 追认为正确。

新的职责边界固定如下：

1. 保留 `experience_period_service.build`、固定投递时间、`experience_period_facts` 快照、指纹和向 DeepSeek 传递事实的现有能力；不得改用当前时间或模型调用时间。
2. 保留 `experience_period_fact_keys` 字段。Service 继续确定性校验 key 不重复、真实存在且 `usable_for_reference=true`；不存在、重复、投递后或日期冲突的 fact key 仍硬失败。
3. Service 不再扫描报告自然语言来判断其中的年数、月份、日期、JD 门槛、分段时长、合计时长、约数或“达到/未达到”结论是否与后端月份一致，也不再因为报告正文出现未被它正确理解的年限文字而整份失败。
4. Service 不负责判断某段日历经历是否属于 Java、财务分析、运营、HRBP 等岗位相关经验；这属于 DeepSeek 的语义评价和 HR 的最终审核。Service 放行只代表结构、引用和其他硬门禁合法，不代表年限内容正确。
5. 报告 Prompt 必须要求 DeepSeek 优先使用后端提供的确定月份或上下界，区分 JD 门槛与候选人实际经历、总工作年限与岗位相关年限、单段与合计；统一用月份比较，并在证据不足时写“无法确认达到”，不得把未知写成“未达到”。
6. Prompt 约束不是百分之百保证。DeepSeek 把 37 个月错误判断为不满足 24 个月等真实内容错误，将不再由 Service 自然语言规则自动拒绝，必须在真实质量验收的“严重事实错误/方向一致性”和 HR 人工审核中如实失败。
7. 继续保留严格 JSON/Schema、评价项 ID 完整性、0—10/0—100 范围、非零分证据、Resume 引用定位、普通数字编造保护、敏感属性、Prompt 污染、品牌推断、自动招聘决定和明显非年限方向矛盾等门禁。不得借本整改删除安全或证据保护。
8. AI 报告始终是 HR 审核草稿，不得因为取消该 Service 判断而直接改变 Application、HR 决策或招聘阶段；HR 最终确认仍是业务前提。

链路位置为：

```text
当前脱敏 Resume + Application.applied_at
        ↓
ExperiencePeriodService 生成确定性月份事实（保留）
        ↓
Prompt 把完整 JD、已确认清单、Resume 和月份事实交给 DeepSeek
        ↓
Schema 严格解析
        ↓
ScreeningEvaluationService（取消自然语言年限裁判，保留事实 key/证据/安全硬门禁）
        ↓
Model / PostgreSQL 保存 HR 待审核报告
```

本问题不改变前端字段、API 请求/响应、报告 Schema 5.0、数据库表、Model、migration、异步状态、幂等、current/历史切换或 HR 决策合同。

### 32D.2 有序实施批次

```text
7R5-I2-R2-A  年限职责与实施顺序文档门禁
→ 停止，等待红灯确认
→ 7R5-I2-R2-B  Service/Prompt 新职责合同红灯
→ 停止，等待 Service 实现确认
→ 7R5-I2-R2-C  删除 Service 自然语言年限判断
→ 停止，等待 Prompt 实现确认
→ 7R5-I2-R2-D  报告 Prompt v3 年限约束
→ 停止，等待零调用回放确认
→ 7R5-I2-R2-E  十二个旧年限拒绝零调用回放
→ 停止，只讨论下一个问题
```

每批必须单独获得用户明确确认，完成后立即停止。R2-A—R2-E 均不得读取真实 API Key、实例化真实 Adapter、调用 DeepSeek、写 PostgreSQL 业务数据、创建 I2 raw/human/final、恢复人工审核或进入 I2-D/E；新增业务调用、API attempt、token 和费用必须为 0。

#### 7R5-I2-R2-A：年限职责与实施顺序文档门禁

唯一目标：把第 32D.1 节的新职责边界、后续四个实施批次、验证方法、失败返回层和停止点写入权威设计与 `PROJECT_STATE.md`，不修改任何实现或测试。

通俗解释：先写清楚“后端算时间、DeepSeek 判断相关性、Service 不读作文判年限、HR 最后审核”，防止后续为了消除误拒绝把全部事实或安全检查一起删掉。

允许修改：本文和 `PROJECT_STATE.md`。链路位置是设计/状态文档，生产链不修改。

禁止：生产 Prompt、Schema、Service、Adapter、API、Model、migration、React、配置、测试、fixture、质量脚本、结果文件和 PostgreSQL；禁止任何真实模型调用。

验证与完成标志：检查 Git 分支/基线/已有修改，确认文档明确保留月份事实和 fact key 硬校验、明确取消的自然语言判断、R15/R19 不能被追认为正确、R2-B—R2-E 的依赖/文件/链路/禁止范围/交付/验证/失败返回层/停止点；执行 `git diff --check`。失败返回设计层。本批结束后停止，唯一下一步是等待用户明确确认 R2-B。

实施结果（2026-08-28）：R2-A 已完成并停止。本批只修改本文与 `PROJECT_STATE.md`，登记上述业务合同和 R2-B—R2-E 顺序；未修改生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、配置、测试、fixture、质量脚本、结果或 PostgreSQL。真实 DeepSeek 调用、API attempt、token 和费用新增均为 0，`pricing_gate_allowed=false`。该结果只能证明实施边界已经写清楚，不能证明 Service 误拒绝已修复、DeepSeek 年限质量提高或任何旧报告已经通过。唯一下一步是等待用户明确确认 R2-B。

#### 7R5-I2-R2-B：Service/Prompt 新职责合同红灯

依赖：R2-A 完成且用户另行确认。

唯一目标：先用失败测试准确固定“Service 不再裁判自然语言年限、Prompt 必须约束 DeepSeek、其他硬门禁不退让”，不修改生产实现。

通俗解释：先做一组会报警的样例，证明现在的门卫确实会把日期和岗位门槛错当成候选人年限，同时确保坏 fact key、无证据和安全越界仍会被拦住。

允许修改：`backend/tests/services/test_screening_evaluation_v5_service.py`、`backend/tests/prompts/test_screening_evaluation_v5_prompt.py`、必要的质量合同/静态扫描测试，以及本文和 `PROJECT_STATE.md` 的实施记录；可以新增一个只含脱敏构造数据的 R2 专项测试文件。链路位置是测试层，覆盖 Prompt → Schema → Service。

固定红灯：日历日期 `2020年7月至今`、JD 门槛 `至少3年`、89/7/96 个月单段与合计、73 个月写作约 6 年均不得因自然语言年限比较整份失败；报告正文即使出现年限也不由 Service 自动判断“达到/未达到”。重复、不存在、不可用 fact key，以及非零分无证据、未知 ID、编造的非时间数字、敏感属性、自动招聘决定和其他既有安全门禁继续失败。Prompt v3 必须新增第 32D.1 节第 5 项的明确规则并先形成红灯。

禁止：修改生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、配置、fixture、质量脚本实现、结果或数据库；禁止删除旧保护断言、使用 xfail 掩盖责任或调用模型。

验证与完成标志：新测试正常收集，预期红灯只指向当前 Service 自然语言年限判断和尚未实现的 Prompt v3；保留门禁测试继续通过；执行相关既有回归、`py_compile` 和 `git diff --check`。失败返回测试/夹具设计层。完成后停止，唯一下一步是等待用户确认 R2-C。

实施结果（2026-08-28）：R2-B 已完成并停止。本批只修改 `backend/tests/services/test_screening_evaluation_v5_service.py`、`backend/tests/prompts/test_screening_evaluation_v5_prompt.py` 和两份状态文档，没有修改生产 Prompt、Schema、Service、Adapter、API、Model、migration、React、配置、fixture、质量脚本、结果或 PostgreSQL。

修改前两份测试基线为 `42 passed + 1 warning`。新增合同后为 `13 failed + 45 passed + 1 warning`：5 个 Service 红灯分别证明日历日期片段、JD 年限门槛、单段/合计月份、精确月份对应约数和综合报告年限文字仍会被当前自然语言规则拒绝；8 个 Prompt 红灯分别锁定 `screening_evaluation_lightweight_v3` 版本和 7 条年限比较/不确定性指令。首次样例中“55 个月满足 3 年”被当前 Service 正确接受，因此测试没有制造假红灯，而是改成旧 R18 类型的“4 个月、未达到 3 年”，确认 JD 门槛会被误当作候选人实际时长。

新旧保护定向为 `15 passed + 25 deselected + 1 warning`，覆盖非零分证据、评价项 ID、Resume 证据与非时间数字、敏感属性、招聘决定、Prompt 污染、方向矛盾、重复/不存在/不可用 fact key、重复 JSON key 和内容错误不重试；两份测试 `py_compile` 通过。红灯只证明待实现责任已经准确锁定，不能证明 R2-C Service 已修改、R2-D Prompt v3 已实现、DeepSeek 真实质量提高或任何旧报告通过。真实 DeepSeek 调用、API attempt、token、费用和 PostgreSQL/正式结果写入新增均为 0；`pricing_gate_allowed=false`。唯一下一步是等待用户明确确认 R2-C。

#### 7R5-I2-R2-C：删除 Service 自然语言年限判断

依赖：R2-B 红灯责任清楚且用户另行确认。

唯一目标：删除报告 Service 对自然语言年限数字和门槛方向的机械判断，让 R2-B 的 Service 红灯转绿，同时保留经历事实 key、证据、结构和安全硬门禁。

通俗解释：后端继续把每段经历的月份算好并提供给 AI，但不再把 AI 写的整段中文拆成数字后自己猜它在说日期、门槛还是实际年限。

允许修改：`backend/app/services/screening_evaluation_service.py` 中 5.0 报告年限自然语言校验的最小范围、必要的报告行为版本/配置/质量合同常量、R2-B 和既有报告 Service 测试，以及本文和 `PROJECT_STATE.md`。链路位置是 Service；不得改变请求或持久化 JSON 形状。

固定实现：停止扫描 `reason`、`calculation_note` 和报告其他正文中的 duration/date/threshold 文字，不再执行自然语言时长与合并月份的等值比较、约数比较、门槛满足方向判断或 unscoped duration 拒绝；保留 facts 的生成/传入/指纹，保留 fact key 唯一、存在和可用校验。非年限的 Resume 事实、证据、数字、安全和方向校验保持不变。报告行为版本应明确递增，旧报告和原 raw 只读，不回填、不重算。

禁止：修改 Prompt、Schema、Adapter、API、Model、migration、React、经历时间事实生成算法、fixture、正式结果或 PostgreSQL；禁止顺手解决高分/无证据和无直接证据问题，也禁止把 R15/R19 写成模型内容正确。

验证与完成标志：R2-B 的 Service 红灯转绿，fact key/证据/安全保护全部通过；受影响报告、运行、质量和后端全量回归通过；`py_compile`、静态扫描和 `git diff --check` 通过；历史 hash 和 I2 路径状态不变。若 fact key 保护退化，返回 Service 结构校验层；若必须改变输出字段，停止并返回设计/Schema 层。完成后停止，唯一下一步是等待用户确认 R2-D。

实施结果（2026-08-28）：R2-C 已完成并停止。5.0 报告 Service 已停止扫描 `reason`、`calculation_note` 和综合报告正文中的日期、时长、约数及门槛方向，也不再把自然语言数字与后端月份做机械等值判断；报告行为版本从 `lightweight_report_generation_v1` 递增为 `lightweight_report_generation_v2`。后端经历月份事实的生成、传入和指纹没有改变，fact key 重复、不存在、不可用、非时间评价项误引和引用后缺少 `calculation_note` 仍会拒绝；证据、非时间数字、敏感属性、招聘决定、Prompt 注入、方向和结构门禁保持不变。旧 4.0 共用的年限校验未删除。

R2-B 的 5 个 Service 红灯已全部转绿；Service/Prompt 定向结果为 `50 passed + 8 expected failed + 1 warning`，8 个失败仅对应尚未实施的 Prompt v3 版本和 7 条年限规则。更新两个旧合同后定向为 `52 passed + 8 expected failed + 1 warning`：旧运行测试现在证明自然语言年限分歧不会被 Service 拒绝，R1-C 零调用重放测试则如实固定取消年限门禁后遇到的下一道证据/安全/方向门禁。排除这 8 个 R2-D 红灯后的后端全量为 `1247 passed + 425 subtests passed + 8 deselected`，仅有既有 PyPDF2 弃用和异步连接清理 warning。

本批没有修改 Prompt 正文或 Prompt 版本、Schema、Adapter、API、Model、migration、React、经历时间事实算法、fixture、质量结果或 PostgreSQL；没有读取 Key、实例化真实 Adapter、调用 DeepSeek、产生 API attempt/token/费用或写正式结果。该结果能证明 Service 机械误拒绝已取消且确定性保护未回归，不能证明 DeepSeek 的年限结论正确、R15/R19 已变正确、旧报告整体验收通过或真实质量提高。`pricing_gate_allowed=false`；唯一下一步是等待用户明确确认 R2-D。

#### 7R5-I2-R2-D：报告 Prompt v3 年限约束

依赖：R2-C 完成且用户另行确认。

唯一目标：升级报告 Prompt，让 DeepSeek 更稳定地使用后端月份事实比较 JD 年限门槛，不通过新增模型调用修复内容。

通俗解释：程序不再读作文判年限后，要把“怎么算、怎么说、证据不足时怎么表达”更明确地告诉 DeepSeek。

允许修改：`backend/app/prompts/screening_evaluation.py`、报告 Prompt 版本配置、质量合同/运行器中的活动 I2 Prompt 版本、Prompt/配置/元数据测试，以及本文和 `PROJECT_STATE.md`。Prompt 版本目标为 `screening_evaluation_lightweight_v3`，AI/持久化 Schema 仍为 `5.0`。链路位置是 Prompt → Adapter 输入；Adapter 请求行为不改。

固定 Prompt 规则：只能使用 `EXPERIENCE_PERIOD_FACTS` 中可用事实；优先直接写确定月份或上下界；区分日期与时长、JD 门槛与候选人实际值、总经历与岗位相关经历、单段与合计；比较时统一换算为月份；不得把重叠经历重复累计；不得自行把日历跨度全部认定为岗位相关；证据不足时写“无法确认达到”，只有后端事实和岗位相关性都明确时才能写“达到/未达到”；输出前静默核对门槛方向，不输出计算草稿或思维链。

禁止：修改 Service、Schema、Adapter、API、Model、migration、React、fixture、Few-shot 正式样本污染、Self-Refine、额外 Judge 或真实调用。不得承诺 Prompt 能百分之百消除模型错误。

验证与完成标志：R2-B Prompt 红灯转绿；版本、结构化分区、正式样本隔离、无思维链、单次调用和内容 0 重试合同通过；相关回归、`py_compile` 和 `git diff --check` 通过。若 JSON 形状必须改变，返回设计/Schema；若真实效果仍未知，留给未来独立真实 raw，不能用 Fake 冒充。完成后停止，唯一下一步是等待用户确认 R2-E。

实施结果（2026-08-28）：R2-D 已完成并停止。5.0 报告 Prompt 版本从 `screening_evaluation_lightweight_v2` 升级为 `screening_evaluation_lightweight_v3`，报告行为版本仍为 `lightweight_report_generation_v2`，Schema 仍为 `5.0`。Prompt 现在明确要求只使用 `EXPERIENCE_PERIOD_FACTS` 中可用事实，优先使用确定月份或上下界；区分日期与时长、JD 门槛与候选人实际经历、总工作年限与岗位相关年限、单段与合计；把 JD 年数门槛统一换算为月份后比较，不重复累计重叠经历，也不把全部日历跨度默认视为岗位相关经历。

不确定性规则也已固定：只有后端月份事实可用且 Resume 证据足以确认岗位相关性时才能写“达到/未达到”；证据、相关性或日期精度不足时必须写“无法确认达到”，不得写成“未达到”。输出前只做静默门槛方向核对，不输出换算草稿、核对过程或思维链。配置默认值、`.env.example`、活动 I2 质量合同和元数据测试同步为 v3；没有修改 Service、Schema、Adapter、API、Model、migration、React、fixture、Few-shot 正式样本或结果文件。

R2-B 留下的 8 个 Prompt 红灯全部转绿；Prompt/配置/Service 元数据/质量合同定向为 `93 passed + 16 subtests passed + 1 warning`，后端全量为 `1255 passed + 425 subtests passed + 2 warnings`，没有排除测试。相关 Python 文件 `py_compile` 通过。未读取 Key、实例化真实 Adapter、调用 DeepSeek、产生 API attempt/token/费用、写 PostgreSQL 或正式结果。该结果能证明静态 Prompt 合同和后端版本接线完成，不能证明 DeepSeek 会始终正确执行规则或真实年限质量已经通过。`pricing_gate_allowed=false`；唯一下一步是等待用户明确确认 R2-E。

#### 7R5-I2-R2-E：十二个旧年限拒绝零调用回放

依赖：R2-C/D 全部通过且用户另行确认。

唯一目标：只读重放当前已知的 12 个旧年限拒绝响应，确认它们不再被已取消的 Service 自然语言年限规则误拒绝，并如实记录随后遇到的下一门禁和已知模型风险。

允许修改：I2-C 预检脚本/测试和状态文档；可以在 `v5-quality-results/7r5i2-diagnostics/` 新建一份不可覆盖、非正式且不复制完整原始响应的 R2 诊断 JSON。链路位置是离线质量诊断，不进入产品写入链。

固定样本：R00、R05、R07、R15、R17、R18、R19、S00-1、S00-2、S00-3、S04-2、S04-3。每例只能使用封存 raw 中已有响应和必要支持计划；不得补齐当时未调用样本。目标只是不再出现旧“AI 年限结论与后端经历时间事实冲突”Service 错误，不预设 12/12 整份报告通过。R15、R19 的模型结论风险必须单独保留为“等待未来人工质量审计”，不得因为 Service 接受而记为内容正确。

验证与完成标志：0 Key、0 Adapter、0 DeepSeek 业务调用、0 API attempt、0 token、USD 0、0 PostgreSQL 和 0 正式结果写入；旧 raw/preflight、I2 raw/human/final 和 13 份历史证据 hash 不变；专项、相关回归、`py_compile`、静态扫描和 `git diff --check` 通过。若仍命中年限自然语言规则，返回 R2-C Service；若 Prompt 静态合同不满足，返回 R2-D；若出现其他事实/证据/方向门禁，只记录并停止，另行讨论。完成后停止，`pricing_gate_allowed=false`，不得进入 I2-D/E。

实施结果（2026-08-28）：R2-E 已完成并触发停止门禁。只读回放固定的 12 个旧年限拒绝响应以及 P00、P04、P05、P07 四份必要支持计划；R05、R07、R15、R17、R18、R19、S04-2、S04-3 的旧年限拒绝基线来自受保护 I2-C preflight，R00、S00-1、S00-2、S00-3 则因当时先被数量 Schema 拒绝，其年限拒绝基线来自受保护 R1-C 诊断。脚本同时校验两份来源的固定 SHA-256，没有把不同生命周期证据混为一份。

12/12 当前均不再命中“AI 年限结论与后端经历时间事实冲突”，证明 R2-C 取消的旧机械门禁没有残留；其中只有 R05 整份报告通过当前 Service，另外 11 份进入其他独立门禁：无直接证据结论 4 份（R07、R18、R19、S04-2），敏感属性 2 份（R00、S00-2），Resume 不支持的非时间数值 2 份（R17、S04-3），Resume 不支持的普通事实 1 份（R15），理由与证据缺少可核对联系 1 份（S00-1），高分与未发现证据方向矛盾 1 份（S00-3）。R15、R19 继续明确标记为等待未来人工质量审核；Service 接受或年限门禁消失均未被写成模型内容正确。

新增隔离、不可覆盖诊断 `docs/stages/stage7/v5-quality-results/7r5i2-diagnostics/2026-08-28-stage7-7r5i2-r2e-duration-replay.json`，大小 21,567 bytes、SHA-256 `dff95720113a9eaf7cfc115a1a29fd89482a57b009e8dcaa66b85c9c0d8d10ac`；不复制完整原始响应、Prompt、Key、堆栈或思维链。专项 `14 passed`，质量/静态/Prompt/Service 相关回归 `118 passed`，后端全量 `1260 passed + 425 subtests passed`，相关文件 `py_compile` 通过。Key、Adapter、DeepSeek 业务调用、API attempt、token、费用、PostgreSQL 和正式结果写入均为 0，诊断写入 1；`pricing_gate_allowed=false`。该结果不能验证 Prompt v3 的真实模型行为或宣布报告质量通过。当前停止，唯一下一步是先与用户讨论数量最多的 4 个“无直接证据的报告结论”门禁；未登记并确认独立整改批次前不得修改代码或进入 I2-D/E。

## 32E. I2 报告整改问题 3：取消无证据结论的关键词裁判

### 32E.1 已确认的业务规则

1. 本问题只调整 5.0 报告 Service 对 `gaps`、`risks_or_conflicts` 和 `missing_info` 中“没有直接 Resume 证据的结论”的自然语言审核，不取消整个报告 Service，也不降低证据、安全或数据结构硬门槛。
2. 当前 `_NO_EVIDENCE_FINDING_TERMS` 只能识别“缺少、缺失、未发现、未体现、不足、无法确认、待核实、仍需、风险、冲突、缺口、尚未”等固定词。R07 的“未提供”、R18 的“缺乏”、R19 的“未提及”和 S04-2 的“未量化”语义正常，却因没有命中词表被整份拒绝。自然语言表达无法靠不断补充同义词穷举完整，因此不再由 Service 通过关键词判断一条结论是不是缺口、风险或待核实信息。
3. 没有直接证据的辅助结论仍必须关联当前计划中存在的 `criterion_ids`；未知、重复或跨计划 ID 继续拒绝。这个关联只能证明结论属于哪个评价点，不能证明结论文字本身正确。
4. `strengths` 仍必须提供可定位到 Resume 原文的证据；评价项非零分仍必须有证据；一旦 `gaps`、`risks_or_conflicts` 或 `missing_info` 主动提供 evidence，该证据仍必须能在 Resume 中精确定位，结论也仍需与所引证据有可核对关系。
5. Service 继续负责适合程序确定判断的硬规则：JSON/Schema、列表技术上限、评价项和事实 ID、分数范围、非零分证据、证据原文定位、Resume 不支持的普通事实与非时间数字、后端时间 fact key、敏感属性、自动招聘决定、Prompt 注入及其他既有安全门禁。
6. Service 不再负责判断无证据辅助结论用了哪个中文同义词，也不因“未提供、缺乏、未提及、未量化”等自然表达拒绝整份报告。此类语言是否准确、是否过度绝对、是否把正向事实伪装成缺口，由 Prompt 约束、真实质量验收和 HR 人工复核负责。
7. Service 放行只表示“数据结构和确定性硬门槛合格”，不表示 DeepSeek 内容正确，更不能把 R07、R10、R16、R18、R19 或 S04-2 追认为质量通过。特别是把没有依据的正向断言错误塞进缺口分区，未来可能越过该关键词门禁；这是取消机械自然语言裁判后明确接受的剩余风险，必须由真实质量和 HR 复核发现。
8. 本轮不修改 Prompt。Prompt v3 已要求区分证据、缺口和待核实信息；是否需要进一步改善措辞，只能在后续真实 raw 或人工审核得到证据后另行立项，不能与本 Service 职责整改混做一批。

在“前端 → API → Schema → Service → Model → PostgreSQL”链路中，本整改仅位于 **Service**：前端和 API 的输入输出不变，Schema 5.0 不变，DeepSeek 请求 Prompt v3 不变，Model/migration/PostgreSQL 不变。

### 32E.2 有序实施批次

```text
7R5-I2-R3-A  无证据结论职责与实施顺序文档门禁
    ↓
7R5-I2-R3-B  Service 新职责合同红灯
    ↓
7R5-I2-R3-C  删除无证据结论关键词裁判
    ↓
7R5-I2-R3-D  六个旧拒绝零调用回放
```

每批必须单独获得用户明确确认，完成后立即停止。R3-A—R3-D 均不得读取真实 API Key、实例化真实 Adapter、调用 DeepSeek、写 PostgreSQL 业务数据、创建 I2 raw/human/final、恢复人工审核或进入 I2-D/E；新增业务调用、API attempt、token 和费用必须为 0。

#### 7R5-I2-R3-A：无证据结论职责与实施顺序文档门禁

唯一目标与通俗解释：先把“程序不再靠同义词表判断缺口，但其他硬门禁继续工作”写成正式合同，避免后续误删整个 Service 或顺手降低证据和安全保护。

允许修改：仅本文和 `PROJECT_STATE.md`。链路位置为 Service 职责设计，不改变运行代码。

禁止：修改生产 Prompt、Schema、Service、Adapter、API、Model、migration、React、配置、测试、fixture、质量脚本、结果文件或 PostgreSQL；禁止读取 Key、调用模型或恢复人工审核。

交付物：本节业务规则、R3-B—R3-D 的依赖顺序、允许/禁止范围、验证、失败返回层、停止点和唯一下一步，以及项目状态同步。

验证与完成标志：检查 Git 分支/基线/已有修改，确认本节只取消关键词语义裁判而保留第 32E.1 节第 3—5 项硬门槛；执行 `git diff --check`，确认受保护 raw/preflight/诊断 hash 与 I2 raw/human/final 空路径不变。失败返回设计层。本批结束后停止，唯一下一步是等待用户明确确认 R3-B。

实施结果（2026-08-28）：R3-A 已完成并停止。本批只修改本文和 `PROJECT_STATE.md`，把取消无证据结论关键词裁判、保留确定性硬门槛和 R3-B—R3-D 独立批次写入权威合同；生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、配置、测试、fixture、质量脚本、结果文件和 PostgreSQL 均未修改。真实 DeepSeek 业务调用、API attempt、token 和费用新增均为 0，`pricing_gate_allowed=false`。当时初始 R3-D 只登记了 R2-E 新暴露的四例；交接复核后由第 32E.3 节补入更早的 R10、R16，纠正为六例。该结果只能证明职责和实施边界已经写清楚，不能证明 Service 已经放行六例、六例内容正确或真实质量通过。唯一下一步是等待用户明确确认 R3-B。

#### 7R5-I2-R3-B：Service 新职责合同红灯

依赖：R3-A 完成并由用户另行明确确认本批。

唯一目标与通俗解释：先用测试证明当前程序确实会把四种正常说法误判，同时锁住不能随本整改一起消失的证据和安全保护。

允许修改：`backend/tests/services/test_screening_evaluation_v5_service.py`、`backend/tests/test_stage7_7r5i2_preflight.py`、必要的质量/静态合同测试，以及本文和 `PROJECT_STATE.md`；链路位置为 Service 测试合同。

禁止：修改任何生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、配置、fixture、质量脚本、正式或诊断结果、PostgreSQL；禁止通过删断言、`skip` 或 `xfail` 冒充红灯。

交付与规则：固定无直接 evidence 且关联合法评价点的“未提供、缺乏、未提及、未量化”应可通过该语义门禁；固定无 `criterion_ids`、未知 ID、strength 无 evidence、非零分无 evidence、伪造证据、普通事实/非时间数字不受支持、敏感属性、自动招聘决定和 Prompt 注入继续拒绝；固定报告行为版本下一批递增为 `lightweight_report_generation_v3`。

验证与完成标志：新红灯只指向 `_NO_EVIDENCE_FINDING_TERMS` 及对应分支，保留门禁全部为绿；执行相关既有回归、`py_compile` 和 `git diff --check`。失败返回测试/夹具设计层。完成后停止，唯一下一步是等待用户确认 R3-C。

实施结果（2026-08-28）：R3-B 已完成并停止。修改前五份相关测试为 `118 passed + 1 warning`；新增合同后为 `8 failed + 118 passed + 1 warning`，没有使用 `skip` 或 `xfail`。8 个红灯职责清楚：4 个分别证明“未提供、缺乏、未提及、未量化”仍被 `_NO_EVIDENCE_FINDING_TERMS` 误拒绝；1 个静态红灯要求删除词表和对应错误分支；2 个行为元数据红灯要求 `lightweight_report_generation_v3`；1 个质量执行合同红灯要求登记同一报告 Service 行为版本。合法评价点关联、strengths/非零分证据、证据定位、普通事实/非时间数字、敏感属性、自动招聘决定、Prompt 注入、内容错误不重试和 13 份历史 hash 定向为 `13 passed + 1 warning`；五份测试 `py_compile` 和 `git diff --check` 通过。生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、配置、fixture、质量脚本、结果和 PostgreSQL 均未修改，真实 DeepSeek 业务调用、API attempt、token 和费用新增为 0。红灯只能证明 R3-C 的修改责任已经锁定，不能证明问题已修复、四份旧报告内容正确或真实质量通过。`pricing_gate_allowed=false`；唯一下一步是等待用户明确确认 R3-C。

#### 7R5-I2-R3-C：删除无证据结论关键词裁判

依赖：R3-B 精确红灯完成并由用户另行明确确认本批。

唯一目标与通俗解释：只删除“找固定关键词”这一步，让正常的缺口表达不再拖垮整份报告；保留程序真正能可靠判断的结构、证据和安全规则。

允许修改：`backend/app/services/screening_evaluation_service.py`、仅用于递增行为版本且不改变正文的 `backend/app/prompts/screening_evaluation.py`、直接相关测试、活动 I2 质量元数据合同，以及本文和 `PROJECT_STATE.md`；链路位置仅为 Service，行为版本递增为 `lightweight_report_generation_v3`，Prompt 版本仍为 `screening_evaluation_lightweight_v3`，Schema 仍为 5.0。

禁止：删除整个 `_validate_v5_findings`、取消无 evidence 时的合法 `criterion_ids` 要求、放松 strengths/非零分证据和证据定位、修改 Prompt 正文/Schema/Adapter/API/Model/migration/React/fixture、调用模型、写 PostgreSQL 或结果文件。

交付与异常语义：删除 `_NO_EVIDENCE_FINDING_TERMS` 及“摘要必须命中固定词”的拒绝分支；无 evidence 且评价点关联合法的 gap/risk/missing 交给后续质量与 HR 判断；缺失或非法关联、伪造 evidence、硬事实/数字、安全问题仍按原稳定错误拒绝。Service 接受不得写成内容正确。

验证与完成标志：R3-B 新红灯转绿，保留门禁和历史回归全部通过；执行相关 Service/运行/质量测试、后端全量、`py_compile`、静态扫描和 `git diff --check`，历史证据及 I2 正式路径状态不变。若保留门禁退化，返回 Service；若需要改变字段，停止并返回设计/Schema；若真实语言质量未知，留给未来 raw。完成后停止，唯一下一步是等待用户确认 R3-D。

实施结果（2026-08-28）：R3-C 已完成并停止。5.0 报告 Service 删除 `_NO_EVIDENCE_FINDING_TERMS` 及“无 evidence 摘要必须命中固定词”的拒绝分支；`_validate_v5_findings` 继续要求无 evidence 结论关联合法评价点，strengths 必须有 Resume 可定位证据，主动提供的 finding evidence 仍需定位和内容关联，其他评价项证据、事实/数字、时间 fact key、结构和安全门禁均未改变。报告行为版本从 `lightweight_report_generation_v2` 递增为 `lightweight_report_generation_v3`，活动 I2 质量执行合同同步记录该版本；Prompt 正文和 Prompt 版本 `screening_evaluation_lightweight_v3`、Schema 5.0 均未改变。

R3-B 的 8 个红灯全部转绿，五份直接相关测试为 `126 passed + 1 warning`；后端全量为 `1268 passed + 425 subtests passed + 2 warnings`。相关文件 `py_compile`、静态扫描和 `git diff --check` 通过。测试态旧响应显示：R19、S04-2 当前整份被 Service 接受，R07 进入敏感属性门禁，R18 和 R16 进入综合说明含 Resume 不支持事实门禁；这些只是用于保持直接相关回归一致，没有创建或覆盖任何诊断。交接复核又确认 R10 在 I2-C、R16 在 R1-C 曾命中同一关键词门禁，因此正式 R07/R10/R16/R18/R19/S04-2 六例记录属于修正后的 R3-D。Service 接受没有被写成内容正确，R19 仍保留未来人工质量审核标记。

本批没有修改 Prompt 正文、Schema、Adapter、API、Model、migration、React、fixture、正式质量结果或 PostgreSQL 业务数据；没有读取 Key、实例化真实 Adapter、调用 DeepSeek、产生 API attempt/token/费用。旧 raw/preflight/R1-C/R2-E 证据 hash 不变，I2 raw/human/final 仍为空，`pricing_gate_allowed=false`。该结果能证明关键词机械拒绝已取消且离线回归稳定，不能证明六例内容正确、真实模型遵守规则、真实报告质量或稳定性通过。唯一下一步是等待用户明确确认 R3-D。

### 32E.3 交接复核后的 R3-D 范围纠正

交接复核重新以受保护 I2-C preflight 为总账，确认历史上共有六个已知 case 曾命中“无直接证据的报告结论只能表达缺口、风险或待核实信息”：R10 在 I2-C 中直接命中；R16 在数量门禁解决后的 R1-C 中命中；R07、R18、R19、S04-2 在年限门禁解决后的 R2-E 中命中。原 R3-D 只登记最后四例，会遗漏两个更早生命周期中的同类拒绝，因此验证分母从 4 更正为 6。

本次范围纠正只修改本文与 `PROJECT_STATE.md`，不修改代码、测试、Prompt、Schema、Service、质量脚本或结果，不执行回放，不读取 Key，不调用 DeepSeek。由于 R3-D 的核心样本分母从 4 变为 6，原四例版确认不得沿用；必须以本文六例合同重新取得用户明确确认后才能执行。

#### 7R5-I2-R3-D：六个旧拒绝零调用回放

依赖：R3-C 通过全部离线回归并由用户另行明确确认本批。

唯一目标与通俗解释：不用 DeepSeek 花钱，只拿封存的 R07、R10、R16、R18、R19、S04-2 六份旧响应重新过当前 Service，证明所有已知同类拒绝都不再因为自然语言没有命中固定词表而被机械拒绝，并如实记录每例下一道门禁。旧门禁来源分别固定为 I2-C 的 R10、R1-C 的 R16，以及 R2-E 的 R07/R18/R19/S04-2；不得只依赖最新诊断而漏掉较早生命周期。

允许修改：`scripts/run_stage7_7r5i2_preflight.py`、`backend/tests/test_stage7_7r5i2_preflight.py`、一份位于 `v5-quality-results/7r5i2-diagnostics/` 的独占诊断，以及本文和 `PROJECT_STATE.md`；链路位置为离线 Service 回放，不经过 Model 或 PostgreSQL。

禁止：补齐无旧响应 case、修改或覆盖旧 raw/preflight/R1-C/R2-E 诊断、复制完整原始响应、Prompt、Key、堆栈或思维链、创建 I2 raw/human/final、把 Service 接受记为质量通过、恢复人工审核或进入真实调用。

交付与验证：固定六例旧响应 hash，以及 I2-C preflight、R1-C、R2-E 三份来源证据 hash；记录旧门禁是否 6/6 消失、每例当前完整接受或下一稳定错误；执行专项、相关回归、后端全量、`py_compile`、静态扫描、`git diff --check`、13 份历史 hash 和 I2 路径检查。必须为 0 Key、0 Adapter、0 DeepSeek 业务调用、0 API attempt、0 token、USD 0、0 PostgreSQL、0 正式结果写入，仅允许 1 份不可覆盖诊断。

完成标志与停止点：若仍命中关键词规则，返回 R3-C Service；若保留门禁回归，返回 R3-C；若出现其他内容/证据/安全门禁，只记录并停止，另行讨论。R3-D 完成后仍为 `pricing_gate_allowed=false`，不得自动进入 I2-D/E；唯一下一步由回放发现的下一门禁决定。

## 33. 7R5-J：真实数据库、API、浏览器收尾

依赖：7R5-IR-A/B 完成，7R5-I2-A—G 依次完成且 I2 final 全部真实质量硬门槛通过，用户另行确认；原 7R5-I raw 或任何零调用回放不能满足本依赖。

唯一目标：用真实 PostgreSQL/API 和真实浏览器证明 5.0 是可操作、可恢复、可审计的完整产品链。

允许修改：仅修复验收发现且不改变已确认合同的最小缺陷；若需要改变核心合同、数据或门槛，必须先回到本文更新并重新确认。

链路位置：前端 → API → Schema → Service → Model → PostgreSQL 全链。

交付与验证：第 21 节全部项目、截图/可访问性/控制台证据、数据库前后计数、migration/current/head、API 结果、浏览器三档尺寸和最终回归。

完成标志：所有自动化、真实 AI、PostgreSQL/API 和浏览器门槛通过，历史证据未改，风险和不能证明的边界如实记录。完成后停止，单独进行阶段 7 完成评审，不自动进入阶段 8。

## 34. 阶段 7 完成标准

阶段 7 只有同时满足以下条件才可标记完成：

- 5.0 轻量评价清单和 HR 编辑/确认链可用；
- 0—10 单项和 AI 直接 0—100 总分报告可用，且没有权重；
- 单人和最多 5 人小批量可靠；
- 幂等、并发、失败、旧成功保留、过期和迟到保护通过；
- HR 决策与 AI 状态分离，历史可审计；
- 敏感属性、编造事实和自动招聘决定硬门槛为 0；
- 第 19—21 节全部自动化、真实 AI、数据库/API 和浏览器验收通过；
- 真实费用和结果文件可复核且不可覆盖；
- 没有用 Fake、旧 4.0 结果或部分样本冒充 5.0 完成。

即使完成，也只能表述为“在冻结测试集和当前产品边界内达到辅助初筛验收标准”。不能宣称替代 HR、法律专家或岗位专家，也不能宣称对所有真实招聘场景普遍准确。

## 35. 当前停止点

7R5-A—7R5-H 已分别获得授权并完成；7R5-I 唯一 real raw 已在 USD 10 上限下执行。实际 29 次业务调用/API attempt、0 技术重试，估算费用 `$0.11033604`；自动结构门槛为计划 `6/10`、报告 `1/20`、稳定性合法运行 `0/15`。用户已完成 10 份计划的引导式人工审核，确认核心要求覆盖和安全边界可接受，同时识别 4 份计划均被 Service 支持性硬门禁拒绝；随后明确暂停报告/稳定性人工审核，先解决 Service。raw 仍保持 `quality_gate_passed=null`，human audit 与 final 路径仍为空，不能用当前业务决定追认为通过。Alembic head 为 `d6e8f0a2b434`，旧 1.0—4.0 计划/报告及 13 份历史证据保持不变；尚未执行 7R5-J。

`7R5-IR-A/B` 已完成并停止。计划 Service 行为合同为 `lightweight_plan_generation_v3`，IR-A 11/11、相关合同 57/57 和原 raw 计划 10/10 只读回放通过；Prompt/Schema/Adapter/API/Model/migration/React 均未改。原 6 个旧生命周期失败已经由 I2-A/B 正确替换和修复，不再需要删除任何证据。

`7R5-I2-A—C` 以及问题 1 的 `7R5-I2-R1-A—C` 已完成并停止。Prompt v2 与 Schema 数量容忍已经实现，六例旧结构响应也全部越过数量门禁，但 0/6 完整通过：R00/S00-1—3 为年限时间事实冲突，R09 为高分与无证据说明方向矛盾，R16 为无直接证据结论。隔离诊断大小 16,101 bytes、SHA-256 `f89426b3aa03b005cb533d6305590d17751dbada076dda526295b8a31b9ad3f3`，不含原始响应。

报告整改问题 2 的 `7R5-I2-R2-A—E` 已完成并停止：后端经历月份事实和 fact key 硬校验继续保留，Service 已取消自然语言年限机械裁判，Prompt 已升级为 `screening_evaluation_lightweight_v3`；12/12 旧年限拒绝均不再命中旧规则。仅 R05 整份通过当前 Service，其他 11 份进入证据、安全、普通事实/数字或方向门禁；R15/R19 继续等待未来人工质量审核。

报告整改问题 3 的 `7R5-I2-R3-A—C` 已完成并停止：Service 已删除无 evidence gap/risk/missing 的同义词表和对应拒绝分支，合法评价点关联、strengths/非零分证据、证据定位、事实/数字、时间 fact key、ID、结构和安全硬门禁继续保留；报告行为版本为 `lightweight_report_generation_v3`。R3-B 的 8 个红灯全部转绿，直接相关 `126 passed`，后端全量 `1268 passed + 425 subtests passed`。交接复核确认已知同类旧拒绝完整分母为 R07/R10/R16/R18/R19/S04-2 六例，原四例 R3-D 范围已在第 32E.3 节纠正；尚未创建 R3-D 正式隔离诊断，也不能宣布内容正确。`pricing_gate_allowed=false`，不得进入 I2-D/E。唯一下一步是等待用户以六例合同明确确认 `7R5-I2-R3-D`；不得读取 API Key、调用 DeepSeek、恢复人工审核、创建新 raw、补跑原 I、进入 7R5-J 或阶段 8/9。

跨电脑交接说明（2026-08-28）：用户将在当前电脑提交并推送，再在另一台电脑拉取继续。拉取后必须先读取 `CLAUDE.md`、`PROJECT_STATE.md`、`docs/DOCUMENT_INDEX.md` 和本文，确认分支 `2lcj`、工作区状态、受保护 raw/preflight/R1-C/R2-E hash 及 I2 raw/human/final 空路径。唯一获准的后续仍是另行确认六例版 R3-D；敏感属性、Resume 不支持的普通事实/数字、理由与证据联系、高分方向矛盾、R14 五分区完整性、缺失模型响应和稳定性不可计算只是 R3-D 之后的待讨论队列，尚未获得业务合同或实施授权，不得在新电脑上连续整改。提交与拉取不得遗漏当前未跟踪的 I2 preflight 测试/脚本、价格快照和 `v5-quality-results/` 证据目录，也不得提交 `.env` 或 API Key。
