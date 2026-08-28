# 阶段 7：轻量评价清单驱动的 AI 初筛 5.0 重设计

> 日期：2026-08-26  
> 状态：7R5-A—7R5-E 已分别确认并完成；Alembic head=`c5d7e9f1a323`；最近全套 1149 passed、12 xfailed（严格，全部属于 7R5-F）、419 subtests passed、0 failures。5.0 报告 Schema、六项方法 Prompt、Adapter 兼容、纯报告 Service、隔离 JSONB 持久化合同和 migration 已落地；当前停止等待用户另行确认 7R5-F，不得进入运行接线、React 或真实 DeepSeek
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
- AI 不得凭常识补充 JD 没写的学历、年限、证书、行业、技术或其他门槛；
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
- Service 负责版本字段、稳定 ID、来源定位、去重、安全上限、明显 importance 一致性 warning、指纹、状态、事务和迟到保护；Service 不得静默改写模型 importance，也不得把合法的 importance 模糊项当作整单内容失败；
- Adapter 只负责模型 API、严格 JSON 解析、重复键、finish reason、token/费用和基础设施错误分类；
- 固定 `schema_version` 等程序合同由程序补充，不能要求模型随机背诵。

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
3. HR 新增、修改、删除、合并、保存、保留或消除 importance warning、确认、版本冲突和 `hr_added` 来源语义；
4. JD 改动使计划/报告过期，非评价内容变化不误伤；
5. 旧 1.0—4.0 只读和 5.0 新生成隔离；
6. 单人普通幂等、强制重评确认、并发唯一运行和迟到响应保护；
7. 同岗位最多 5 人、跨岗位/重复/超量拒绝和批量部分失败；
8. 每个评价点恰好一条 assessment、0—10 范围、总体 0—100 范围；
9. 所有非零分有当前简历证据，0 分使用“未发现证据”语义；
10. 敏感属性、自动招聘决定、未知评价点和严重方向矛盾被拒绝；
11. current 成功替换、失败保留旧成功、输入变化和历史只读；
12. HR 决策、反转、原因和 StageHistory；
13. 明确扫描 5.0 运行路径中没有固定权重、权重字段和 Python 加权总分。

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
- 擅自新增要求 0；
- 敏感要求 0；
- 每个 AI 评价点都可追溯到 JD；
- 宣传、福利和招聘流程不得成为扣分项；
- 数量通常约 5—12，复杂岗位超过 12 只 warning、不失败。

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

> 原实施顺序已获用户整体确认，7R5-A、7R5-B、7R5-C、7R5-C1、7R5-D 与 7R5-E 已分别确认并完成。每一轮仍只能执行一个另行确认的批次并停止；当前必须先获得 7R5-F 实施确认，不得直接修改运行接线、批量、HR 决策或进入 React。

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
→ 7R5-I 真实 AI 计划、报告和稳定性验收
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

## 33. 7R5-J：真实数据库、API、浏览器收尾

依赖：7R5-I 全部真实质量硬门槛通过且用户另行确认。

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

7R5-A、7R5-B、7R5-C、7R5-C1、7R5-D、7R5-E、7R5-F、7R5-G 与 7R5-H 已分别获得授权并完成；H 的浏览器非模型路径由用户于 2026-08-28 手工测试并明确确认通过，证据类型不是 Codex 自动浏览器日志。5.0 评价计划、纯报告引擎、单人/最多 5 人运行、current/历史报告、AI→HR 移交、审计后端、React 清单/报告产品交互和真实质量运行前门禁均已落地，Alembic head 为 `d6e8f0a2b434`。新运行只接受当前合法 5.0 ready 计划；旧 1.0—4.0 计划/报告继续只读兼容，不再驱动新评分。真实 DeepSeek 调用和费用为 0；尚未证明真实模型质量或 7R5-J 最终完整端到端验收。

当前唯一下一步是停止并等待用户另行确认 7R5-I 的美元金额上限，或明确确认本轮“不设金额上限”。未经金额确认不得执行真实质量运行、读取真实 API Key、调用 DeepSeek、创建三个正式结果文件、进入 7R5-J 或阶段 8/9。
