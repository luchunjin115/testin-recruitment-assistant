# 阶段 9：面试、Offer、录取与招聘流程统计设计

> 日期：2026-09-02
>
> 状态：已由项目负责人确认，可以开始 9A
>
> 上游依赖：阶段 4—8 已完成并关闭
>
> 目标入口：HR `/app/screening`（页面名称固定为“AI 初筛中心”），正式 API `/api/v2/*`

## 1. 这一步要解决什么

当前系统已经能够完成岗位开放、公开投递、简历处理、AI 初筛和 HR 初筛决定，但 HR 通过一名候选人后，Application 仍停在 `screening_passed`。面试安排、反馈、Offer、候选人回复、录取、正式入职和流程统计尚未形成正式业务合同。

阶段 9 要补齐招聘后半程，同时收拢当前重复的前端入口：

```text
候选人投递
→ 简历原文与结构化草稿
→ AI 初筛报告
→ HR 初筛通过
→ 多轮面试与人工反馈
→ Offer 与候选人回复
→ 已录取、正式入职或流程结束
→ 可追溯时间线与招聘流程统计
```

大白话目标是：HR 不再只看到“这个人初筛通过了”，而是能够在同一个 Application 详情中继续安排面试、填写反馈、记录 Offer 和最终结果；列表本身也要直接展示 AI 分数、标签、优点和风险，不必逐条点开才能判断。

阶段 9 仍然坚持：AI 只提供岗位匹配信息和核实方向，不能自动通过、淘汰、发 Offer、录取或确认入职。

## 2. 设计时实际基线

2026-09-02 创建本文前完成了只读核对：

- Git 分支为 `2lcj`，工作区无未提交修改；
- Alembic `current=head=a8d4f2c7e901`；
- `alembic check` 返回 `No new upgrade operations detected`；
- 开发库有 1 条 Application，状态为 `active / screening_passed / passed`；
- `stage_histories`、`screening_reports`、`resumes` 各 1 行；
- `public_application_submissions` 和 `application_processing_runs` 均为 0 行；
- 当前没有 `InterviewRecord`、`OfferRecord` ORM 或对应数据库表；
- 当前 Application 正式阶段只有 `applied / hr_review / screening_passed / backup / rejected`；
- 当前前端 `/app/screening` 为卡片列表，并为每条 Application 单独请求初筛状态；
- `/app/resumes` 和 `/app/reports` 仍是独立页面，候选人详情仍会跳转到旧报告页。

这只是设计基线，不是实施授权。开始 9A 前必须重新检查 Git、Alembic、PostgreSQL 数据和约束；若实际状态变化或出现无法安全回填的数据，应停止 migration 实施并报告冲突。

## 3. 项目负责人已确认的产品选择

阶段 9 讨论已固定以下方向；本文把它们转换为可实施合同：

1. 阶段 9 从 HR 已通过且仍有效的 Application 开始，完成多轮面试、汇总反馈、Offer、候选人回复、录取、正式入职和结束流程。
2. 左侧“AI 初筛”改名为“AI 初筛中心”；删除“简历管理”和“初筛报告”两个独立导航入口。
3. 简历和报告数据不删除；原文件、原文、结构化草稿、当前/历史 AI 报告都进入 Application 统一详情。
4. AI 初筛中心桌面端改为紧凑数据表，移动端使用信息卡；每条记录直接显示 AI 分数、匹配标签、能力标签、综合评价、主要优点、主要风险、HR 决定和招聘阶段。
5. AI 能力标签不额外调用 DeepSeek，而是从已经保存的当前报告、HR 已确认评价点和简历证据中确定性提取。
6. 只有 `active / screening_passed / passed` 的 Application 可以开始面试；备选必须先由 HR 调整为通过。
7. 面试使用不限固定数量的轮次结构，不把数据库写死为一面、二面；第一版每轮只有一份汇总反馈。
8. 面试结果支持待决定、进入下一轮、进入 Offer、淘汰、候选人退出、取消和未到场；重要结束操作必须确认并说明原因。
9. Offer 保存具体薪资；薪资只在 Offer 详情显示，不进入列表或招聘流程统计。
10. Offer 状态为草稿、已人工发送、已接受、已拒绝、已撤回和已过期；第一版不自动发送邮件、短信或文件。
11. “接受 Offer”“已录取、等待入职”和“正式入职”是三个独立节点；接受 Offer 后仍须由 HR 明确确认录取，录取后仍须另行确认实际入职。
12. 面试、Offer 和最终结果不能直接删除；更正、撤销和重新打开必须保留原状态、原因、操作人和时间。
13. 阶段 7 的 `hr_decision=passed` 是“曾通过初筛”的历史事实。阶段 9 后续淘汰或退出不能把它改写成 `rejected`。
14. “流程报告”正式改名为“招聘流程统计”，放在工作台和 AI 初筛中心顶部，不新增左侧菜单。
15. 招聘流程统计只根据 PostgreSQL 真实业务数据计算，不调用 AI，不生成叙事，不提供 Excel 导出。
16. 第一版不接邮件、短信、日历、电子签约、外部 ATS、候选人进度页或 AI 面试官。
17. 当前继续使用“本地 HR（未认证）”边界；完整登录、RBAC 和薪资字段授权留到阶段 12。

## 4. 用户与决策边界

| 用户/组件 | 本阶段职责 | 不能做什么 |
| --- | --- | --- |
| HR | 安排面试、填写汇总反馈、记录候选人回复、创建和维护 Offer、确认录取/入职、查看统计 | 不能删除历史、绕过确认、把 AI 标签当成人工决定 |
| 面试官 | 第一版只作为 HR 填写的姓名出现在面试记录中 | 没有独立账号、登录或单独提交入口 |
| 候选人 | 通过线下沟通参加面试并回复 Offer | 第一版没有账号、进度查询或在线接受 Offer 页面 |
| API | 提供严格合同、稳定错误和权限入口 | 不在 Router 中复制状态机或事务 |
| Service | 锁定 Application、校验转换、写记录和审计、保证并发一致性 | 不调用 DeepSeek 决定招聘结果 |
| PostgreSQL | 保存最终状态、约束、历史和精确薪资 | 不接受前端绕过 Service 写入非法组合 |
| DeepSeek | 继续只负责阶段 5/7 已确认的结构化和初筛能力 | 阶段 9 不新增模型调用、标签调用或自动决策 |

当前内部页面没有登录认证。所有人工动作继续记录 `actor_type=hr`、`actor_id=null`、`actor_label=本地 HR（未认证）`；这只是作品集边界，不代表已完成生产权限保护。

## 5. 范围

### 5.1 包含

- Application 招聘阶段与最终结果扩展；
- 多轮面试安排、改期、取消、未到场和一轮一份汇总反馈；
- 面试进入下一轮、进入 Offer、淘汰和候选人退出；
- Offer 草稿、具体薪资、人工发送、接受、拒绝、撤回和过期；
- 已录取等待入职、正式入职和高风险更正/重新打开；
- InterviewRecord、OfferRecord、Application 最终结果和 StageHistory 扩展；
- AI 初筛中心列表聚合 API、稳定分页/筛选/排序和 N+1 请求收口；
- AI 分数、匹配标签、能力标签、优点、风险和状态的列表级直观展示；
- Application 统一详情中的简历、报告、面试、Offer 和流程时间线；
- 删除独立前端导航和页面入口，旧前端 URL 安全跳转；
- 招聘漏斗、阶段耗时和当前待办统计；
- Schema、Service、API、Model、migration、直接测试、真实 PostgreSQL 和浏览器验收设计。

### 5.2 不包含

- 修改阶段 5 简历结构化 Prompt、Schema 或自动填表规则；
- 修改阶段 7 AI 评分原则、展示分档、Prompt、Repair、已知限制或历史 raw；
- 为 AI 标签再次调用 DeepSeek 或新增标签 Prompt；
- AI 自动排序、通过、淘汰、发 Offer、录取或确认入职；
- 多面试官分别评分和自动汇总；
- 视频面试、会议室、飞书、钉钉、企业微信或日历集成；
- 自动发送邮件、短信、Offer 文件或电子签约；
- 候选人账号、公开进度页或在线回复 Offer；
- 背景调查、入职材料、员工档案和入职后 HR 系统；
- 外部 ATS、完整 RBAC、多租户、薪资字段级授权和生产合规；
- Excel/PDF 导出、AI 生成流程总结、Agent、RAG 或 MCP；
- 使用真实候选人或真实薪资进行作品集演示。

## 6. Application 状态合同

### 6.1 三类状态继续分工

Application 继续使用三个不同概念，不把它们混成一个字符串：

| 字段 | 责任 |
| --- | --- |
| `hr_decision` | 只记录阶段 7 HR 初筛决定：`pending / passed / backup / rejected` |
| `recruitment_stage` | 当前所处业务阶段 |
| `lifecycle_status` | Application 是否仍可继续：`active / ended / voided` |

阶段 9 新增 `final_outcome`，只记录已结束 Application 的最终结果。它不覆盖 `hr_decision`。

### 6.2 RecruitmentStage

保留现有值：

```text
applied
hr_review
screening_passed
backup
rejected
```

新增：

```text
interview
offer
offer_accepted
admitted
hired
```

- `interview`：至少已经创建第一轮面试，或处于轮次间待安排状态；
- `offer`：面试已决定进入 Offer，或已经存在 Offer；
- `offer_accepted`：候选人已经接受 Offer，但 HR 尚未确认进入“已录取、等待入职”；
- `admitted`：HR 已明确确认录取，候选人正在等待实际入职；
- `hired`：HR 已确认实际入职，是终态。

候选人退出、Offer 拒绝或公司取消不需要伪造新的“阶段”；Application 保留退出前所在阶段，再通过 `final_outcome` 表明为何结束。

### 6.3 FinalOutcome

`final_outcome` 可空枚举固定为：

```text
screening_rejected
interview_rejected
interview_no_show
offer_declined
offer_withdrawn
offer_expired
candidate_withdrew
company_canceled
hired
```

一致性规则：

- `lifecycle_status=active` 时 `final_outcome` 必须为 null；
- `lifecycle_status=ended` 时 `final_outcome` 必须非空；
- `lifecycle_status=voided` 时 `final_outcome` 必须为 null，作废继续表示数据录入本身无效；
- `final_outcome=hired` 时 `recruitment_stage=hired`、`hr_decision=passed`；
- `screening_rejected` 时保持阶段 7 的 `recruitment_stage=rejected / hr_decision=rejected`；
- 阶段 9 的 `interview_rejected` 不改变 `hr_decision=passed`；
- Offer 或候选人退出类结果保留结束前的阶段，页面优先展示最终结果。

阶段 9 migration 对既有 `ended / rejected / rejected` 行解释性回填 `screening_rejected`；不得为其他既有行猜测最终结果。实现前若发现不能解释的 `ended` 组合，立即停止并报告。

### 6.4 主转换

| 当前状态 | 动作 | 结果 |
| --- | --- | --- |
| `active / screening_passed / passed` | 创建第一轮面试 | `active / interview / passed` |
| `active / interview / passed` | 本轮通过、安排下一轮 | 仍为 `active / interview / passed` |
| `active / interview / passed` | 面试通过、进入 Offer | `active / offer / passed` |
| `active / interview / passed` | 面试淘汰 | `ended / rejected / passed + interview_rejected` |
| `active / interview / passed` | 未到场并由 HR 结束 | `ended / rejected / passed + interview_no_show` |
| `active / offer / passed` | 候选人接受 Offer | `active / offer_accepted / passed` |
| `active / offer / passed` | 候选人拒绝 | `ended / offer / passed + offer_declined` |
| `active / offer / passed` | 公司撤回 | `ended / offer / passed + offer_withdrawn` |
| `active / offer / passed` | Offer 过期并结束 | `ended / offer / passed + offer_expired` |
| `active / offer_accepted / passed` | HR 确认录取 | `active / admitted / passed` |
| `active / admitted / passed` | HR 确认实际入职 | `ended / hired / passed + hired` |
| `active / screening_passed/interview/offer/offer_accepted/admitted` | 候选人退出 | 保留当前阶段，`ended + candidate_withdrew` |
| 上述 active 阶段 | 公司取消流程 | 保留当前阶段，`ended + company_canceled` |

Job 在候选人进入阶段 9 后关闭，不自动取消已经存在的面试或 Offer。关闭岗位仍阻止新投递和新的阶段 7 初筛；后续 Application 必须由 HR 明确结束，不能由 Job 状态静默改写。

### 6.5 更正与重新打开

- 阶段 7 淘汰继续使用既有 `undo-rejection`，回到 `active / hr_review / pending` 并清除 `screening_rejected`；
- 面试终态更正可以回到 `active / interview / passed`；
- Offer 拒绝、撤回、过期或候选人退出的更正可以回到 `active / offer / passed`；
- 已接受 Offer 的误操作可以回到 `active / offer / passed`；
- 错误“已录取”可以回到 `active / offer_accepted / passed`；
- 错误“已入职”可以回到 `active / admitted / passed`；
- 重新打开必须二次确认、选择受控原因并填写具体说明；
- Service 必须核对支撑记录存在，前端不能自由指定任意目标阶段；
- 重新打开只追加历史，不删除面试、Offer 或旧终态。

## 7. InterviewRecord 合同

### 7.1 责任

InterviewRecord 保存某个 Application 的一轮面试安排和汇总反馈。它不是候选人跨岗位画像；同一 Candidate 在不同 Job 的面试必须分别记录。

### 7.2 字段

| 字段 | 语义 |
| --- | --- |
| `id` | 主键 |
| `application_id` | 所属 Application，外键且不可空 |
| `round_number` | 从 1 开始的轮次，同一 Application 唯一 |
| `interview_type` | `onsite / video / phone` |
| `status` | `scheduled / completed / canceled / no_show` |
| `scheduled_start_at` | 带时区的计划开始时间 |
| `duration_minutes` | 15—480 分钟 |
| `timezone` | IANA 时区，第一版默认 `Asia/Shanghai` |
| `interviewer_names` | 1—10 个非空姓名字符串 |
| `location` | 现场地点，可空 |
| `meeting_link` | 视频会议链接，可空，不在普通列表展示 |
| `schedule_note` | 安排备注，可空，最长 2000 字符 |
| `decision` | `pending / next_round / proceed_offer / rejected / candidate_withdrew` |
| `feedback_summary` | 汇总反馈，可空，最长 5000 字符 |
| `strengths` | 人工面试优点字符串数组 |
| `concerns` | 人工风险/不足字符串数组 |
| `follow_up_questions` | 后续核实问题字符串数组 |
| `feedback_submitted_by_label` | 第一版固定本地 HR 标签 |
| `feedback_submitted_at` | 首次提交反馈时间 |
| `version` | 乐观并发版本，从 1 开始 |
| `created_at / updated_at` | 审计时间 |

面试反馈是人工事实，不复制 AI `strengths/gaps`，也不让 AI 自动生成。数组必须是 JSONB 数组且每项经过长度、空白和额外字段校验。

### 7.3 状态和一致性

- `scheduled` 可以改期或取消；改期更新同一记录并写旧/新时间审计，不删除旧事实；
- `completed` 表示面试已发生；`decision` 可以暂时为 `pending`，形成“面试完成、待反馈/待决定”待办；
- `canceled` 必须填写取消原因，不自动结束 Application；HR 可以另建下一轮或更正；
- `no_show` 必须填写原因，不自动淘汰；HR 明确选择结束时才写 `interview_no_show`；
- `next_round` 不自动创建下一轮，只允许 HR 创建 `round_number+1`；
- `proceed_offer` 原子把 Application 推进到 `offer`，但不自动发 Offer；
- `rejected` 和 `candidate_withdrew` 是高风险结束动作，必须确认；
- 同一 Application + `round_number` 唯一；
- 同一 Application 最多一个 `status=scheduled` 的未来/待进行面试，使用部分唯一索引保护；
- 已提交反馈再次修改时必须提供 `expected_version`、确认和更正原因。

## 8. OfferRecord 合同

### 8.1 责任与版本

OfferRecord 保存一次具体 Offer。一个 Application 可以保留多个历史 Offer 版本，但同一时间最多一个非终态 Offer。旧 Offer 不覆盖、不删除；重新发放使用新的 `version_number`。

### 8.2 状态

```text
draft
sent
accepted
declined
withdrawn
expired
```

- `draft`：内部草稿，尚未对外发送；
- `sent`：HR 明确确认已通过线下渠道发送；
- `accepted / declined`：HR 根据候选人真实回复人工记录；
- `withdrawn`：公司撤回；
- `expired`：超过有效期后由 HR 明确标记，第一版不新增定时 Worker；
- `accepted` 只表示候选人已接受 Offer，Application 仍为 active，但尚不能显示为“已录取”；
- HR 必须另行确认录取后，Application 才进入 `admitted`（已录取、等待入职）；
- 正式入职由 Application 独立高风险动作确认，Offer 继续保留 accepted 事实。

### 8.3 字段

| 字段 | 语义 |
| --- | --- |
| `id` | 主键 |
| `application_id` | 所属 Application |
| `version_number` | 同一 Application 从 1 递增，唯一 |
| `status` | 上述 Offer 状态 |
| `position_title` | 本次 Offer 岗位名称快照 |
| `currency` | 三位大写币种代码，例如 `CNY` |
| `salary_period` | `monthly / annual` |
| `base_salary_amount` | `NUMERIC(14,2)` 精确正数，不使用 float |
| `salary_months` | 月薪制必填，`NUMERIC(4,1)`，范围 1—24；年薪制为空 |
| `bonus_note` | 奖金/提成说明，可空 |
| `benefits_note` | 其他待遇说明，可空 |
| `valid_until` | Offer 有效截止日期 |
| `expected_start_date` | 预计入职日期 |
| `note` | HR 内部备注，可空 |
| `sent_at` | 标记已发送时间 |
| `responded_at` | 接受或拒绝时间 |
| `closed_at` | 撤回或过期时间 |
| `version` | 乐观并发版本 |
| `created_at / updated_at` | 审计时间 |

薪资字段是敏感业务数据：只在 Offer 详情返回和展示，不进入 AI 初筛中心列表、招聘流程统计、普通日志或 AI 输入。测试、截图和演示只能使用虚构金额。

### 8.4 转换与修改

- 创建 draft 不需要二次确认，但必须满足 Application 已在 `offer` 且 active；
- draft 可以普通编辑；
- `draft → sent` 必须二次确认；
- sent 后修改薪资、有效期或预计入职日期必须发送 `expected_version`、二次确认和更正原因；
- `sent → accepted/declined/withdrawn/expired` 必须二次确认并写原因或回复说明；
- accepted 后不能直接改回 draft；更正通过 Application/Offer 专用重新打开 Service 完成；
- 同一 Application + `version_number` 唯一；
- 部分唯一索引保证最多一个 `draft / sent / accepted` Offer；
- 重复提交同一目标状态和相同业务内容时返回当前结果，不重复写历史；
- 任何失败不得删除旧 Offer 或改变 Application。

## 9. StageHistory 与 ActivityLog

### 9.1 StageHistory 扩展

StageHistory 继续作为 Application 阶段变化的追加历史。阶段 9 增加：

- `from_lifecycle_status / to_lifecycle_status`；
- `from_final_outcome / to_final_outcome`；
- 可空 `interview_record_id`；
- 可空 `offer_record_id`。

既有历史行允许这些新字段为空；阶段 9 实施后的新转换必须填写生命周期字段。StageHistory 继续保留 from/to `recruitment_stage` 和 `hr_decision`，从而明确证明阶段 9 淘汰时 `hr_decision=passed` 没有被改写。

新增受控 reason code 至少包括：

```text
interview_scheduled
interview_rescheduled
interview_canceled
interview_no_show
interview_round_completed
interview_next_round
interview_proceed_offer
interview_rejected
candidate_withdrew
offer_created
offer_sent
offer_accepted
offer_declined
offer_withdrawn
offer_expired
application_admitted
application_hired
company_canceled
stage9_correction
stage9_reopened
```

仅真正改变 Application 状态的动作写 StageHistory；纯备注或不改变阶段的改期写 ActivityLog，避免伪造阶段变化。

### 9.2 ActivityLog

所有面试和 Offer 创建、修改、反馈、更正和高风险动作写 ActivityLog。detail 只保存必要结构化差异、对象 ID、受控 reason code 和本地 HR 标签；不保存完整简历、完整薪资备注或会议私密内容。

时间线 Service 按 Application 聚合 StageHistory 和受控 ActivityLog，返回统一只读 `RecruitmentTimelineItem`。前端不直接解释任意 JSONB，也不根据按钮点击伪造历史。

## 10. AI 初筛中心信息架构

### 10.1 导航收口

左侧导航固定为：

```text
工作台
候选人
岗位管理
AI 初筛中心
```

- `/app/screening` 路径保留，页面标题改为“AI 初筛中心”；
- 删除“简历管理”和“初筛报告”导航；
- `/app/resumes` 和 `/app/reports` 使用 `<Navigate replace>` 跳到 `/app/screening`，不返回空白或 404；
- 独立 `RecruitmentResumeList`、`RecruitmentReportCenter` 页面退出运行入口；
- 后端 Resume、ScreeningReport 和通用 Report 数据、Model、migration 不因删除前端入口而删除；
- 候选人详情的“查看初筛报告”改为带 `application_id` 的 `/app/screening` 深链接，并自动打开对应详情；
- 阶段 8 公开投递继续与内部录入共用同一 Application 列表，不新增公开投递工作区。

### 10.2 桌面表格与移动卡片

桌面端每条 Application 至少展示：

| 区域 | 内容 |
| --- | --- |
| 候选人 | 姓名、脱敏手机号、当前职位；完整联系方式只在详情查看 |
| 岗位/来源 | 应聘岗位、公开投递/HR 录入、公开凭证（如有） |
| AI 初筛 | 0—100 分、匹配标签、报告状态/过期状态 |
| AI 标签 | 最多 4 个可追溯能力标签 |
| AI 评价 | 综合说明最多两行，完整内容在详情 |
| 优点 | 最多 2 条 `strengths` 摘要 |
| 风险 | 最多 2 条 `gaps/risks_or_conflicts` 摘要 |
| HR/流程 | HR 初筛决定、当前阶段、最终结果、公开处理异常 |
| 时间 | 申请时间和最近业务更新时间 |
| 操作 | 查看统一详情、当前允许的 HR 动作 |

不能把无报告显示为 0 分：

- 尚未生成：显示等待简历、等待计划、排队中或运行中；
- 失败且无旧报告：显示初筛失败；
- 失败但有旧成功报告：继续显示旧分数，并标记“旧报告保留”；
- 报告过期：继续显示历史分数和标签，但明显标记“已过期”；
- 状态读取失败：显示安全错误和重试，不展示伪造数据。

移动端保留相同业务信息，但折叠为卡片；不能通过隐藏 AI 评价、风险或当前阶段换取窄屏通过。

### 10.3 AI 匹配标签

继续直接使用阶段 7 已保存 `display_label`：

```text
关联较弱
存在明显差距
部分匹配
整体较匹配
高度匹配
```

它只是总体分的程序展示分档，不是招聘决定。

### 10.4 AI 能力标签确定性提取

AI 能力标签不新增数据库列、不修改阶段 7 Prompt，也不产生新的模型调用。聚合 Service 从当前 ScreeningReport 计算：

1. 只读取当前报告；Schema 5.0 报告才支持能力标签。
2. 按报告 `strengths` 顺序解析它引用的 `criterion_ids`。
3. 评价点必须存在于持久化 criterion 快照中。
4. 对应 assessment 必须 `score > 0` 且至少有一条 evidence。
5. 标签文字直接使用 HR 已确认的 `criterion.name`，不截取模型长句重新命名。
6. 候选标签按 assessment 分数降序；同分按 `required > preferred > general`，再按 strength 和评价点原顺序。
7. 对标准化后的名称去重，最多返回 4 个；不足时不凑数。
8. 返回 `criterion_id / label / score / importance / evidence_count / is_outdated`，列表只显示 label，详情可以定位评价点和证据。
9. 当前报告过期时仍可展示旧标签，但每个标签和整行都标记过期。
10. 旧 1.0—4.0 报告、没有 strengths、交叉引用失败或证据不足时返回空数组并显示“暂无可靠标签”。

学校、公司可以结合真实职责和项目作为证据语境，但不生成“985 高校”“双一流”“名企”等品牌能力标签；年龄、性别、民族、婚育、照片等敏感信息永远不能成为标签。

### 10.5 列表聚合 API

新增内部只读接口：

```http
GET /api/v2/screening-center/applications
```

它在后端一次性返回分页摘要，替代当前前端为每条 Application 分别请求 screening 的 N+1 组合。支持：

- `page`，从 1 开始；
- `page_size`，默认 30，最大 100；
- `job_id`；
- `source`；
- `hr_decision`；
- `recruitment_stage`；
- `lifecycle_status`；
- `final_outcome`；
- `processing_pool / processing_status`；
- `display_label`；
- `score_min / score_max`；
- `applied_from / applied_to`；
- `sort=applied_desc / updated_desc / score_desc / score_asc`。

摘要响应只包含列表所需的小字段、最多 4 个标签、2 个优点和 2 个风险；不内嵌 raw_text、完整 parsed_snapshot、完整报告、完整联系方式、具体薪资或会议链接。

后端同时返回基于真实状态计算的 `allowed_actions`，前端用于解释按钮，但 Service 仍必须在写入时重新校验，不能把前端 capability 当授权。

## 11. Application 统一详情

点击列表行或从候选人详情深链接进入同一个抽屉/详情容器，内容固定为：

```text
概览
简历
AI 初筛报告
面试
Offer
流程时间线
```

### 11.1 概览

- Candidate、Job、来源、Application ID；
- HR 初筛决定、招聘阶段、生命周期和最终结果；
- 公开投递凭证、处理步骤和身份核对状态（如有）；
- 当前允许动作和安全说明。

### 11.2 简历

- 当前 Resume 文件名、类型、大小和处理状态；
- 查看/下载原文件；
- 查看成功 `raw_text`；
- 查看最近一次成功 `parsed_snapshot`；
- 显示结构化最近失败但旧草稿保留的真实状态；
- 内部录入和公开投递使用同一入口；
- 只读查看不得触发结构化或 DeepSeek；
- 未绑定的临时 Resume 不是正式业务工作区，由既有保留/清理规则处理。

### 11.3 AI 初筛报告

- 当前和历史成功报告；
- 总体分、匹配标签、综合说明；
- 逐项分数、理由和证据；
- strengths、gaps、risks、missing_info、HR 核实问题；
- 报告过期、旧报告保留、运行失败和版本信息；
- 继续复用阶段 7 既有接口与 `ScreeningReportView`，不复制报告合同。

### 11.4 面试、Offer、时间线

- 面试按 round_number 顺序展示，历史状态只读可追溯；
- Offer 按 version_number 倒序展示，具体薪资只在该区出现；
- 时间线使用统一 Schema 显示系统推进、HR 决策、改期、反馈、Offer 和更正；
- 候选人文本、反馈和备注都通过 React 文本节点渲染，不信任 HTML。

详情可以按需并发调用单个 Application 的既有 Resume/Screening 接口和阶段 9 新接口；列表不批量下载大文本。

## 12. 招聘流程统计

### 12.1 定位

“招聘流程统计”是 PostgreSQL 业务统计，不是 AI 初筛报告，也不是 LLM 生成的文字。它在工作台和 AI 初筛中心顶部显示，不增加左侧入口。

新增只读接口：

```http
GET /api/v2/recruitment-statistics
```

支持 `job_id / applied_from / applied_to`。时间范围采用 Application `applied_at` 形成固定申请 cohort；后续是否到达某一步按历史记录判断，不能只看当前 stage，否则进入后续阶段的人会从前一阶段统计中消失。

### 12.2 漏斗定义

| 指标 | 定义 |
| --- | --- |
| 申请人数 | cohort 中不同 Application 数 |
| 初筛通过人数 | 曾有 StageHistory 到达 `screening_passed`，包括 HR 直接录入初始通过 |
| 进入面试人数 | 至少一条非纯取消的 InterviewRecord |
| 完成面试人数 | 至少一条 `completed` InterviewRecord |
| Offer 人数 | 至少一条曾到达 `sent` 的 OfferRecord；只有 draft 不计入 |
| Offer 接受人数 | Offer 曾到达 `accepted`，或 Application 曾到达 `offer_accepted / admitted / hired` |
| 录取人数 | StageHistory 曾到达 `admitted`，或 Application 最终 hired |
| 正式入职人数 | `final_outcome=hired` |

转化率以前一漏斗层为分母；分母为 0 时返回 null，不返回 0% 伪装为可计算。

### 12.3 耗时与待办

耗时使用服务端时间戳计算平均值，同时返回样本数：

- 申请到 HR 初筛通过；
- HR 初筛通过到第一轮面试创建；
- 第一轮面试创建到最后一轮面试完成；
- 进入 Offer 到标记 sent；
- Offer sent 到 accepted/declined；
- Offer accepted 到 HR 确认录取；
- HR 确认录取到正式入职。

没有完整起止事件的 Application 不进入该项平均值，但仍保留在漏斗中。

当前待办是实时快照，不被 cohort 时间范围伪装成历史事实：

- 已安排、待进行面试；
- 面试已完成但 decision 仍 pending；
- 已决定下一轮但尚未创建下一轮；
- Offer draft 待发送；
- Offer sent 待回复；
- Offer accepted 待 HR 确认录取；
- 已录取待确认实际入职。

报告不统计薪资，不输出候选人个人信息，不调用 AI，不提供 Excel/PDF 导出。

## 13. API 合同

### 13.1 面试

```text
GET  /api/v2/applications/{application_id}/interviews
POST /api/v2/applications/{application_id}/interviews
PUT  /api/v2/interviews/{interview_id}/schedule
POST /api/v2/interviews/{interview_id}/cancel
POST /api/v2/interviews/{interview_id}/no-show
POST /api/v2/interviews/{interview_id}/feedback
PUT  /api/v2/interviews/{interview_id}/feedback
```

- 创建和普通改期使用严格 Schema 与 `expected_version`；
- cancel/no-show、淘汰、退出和更正请求带受控 reason code、必要说明与 `confirmed`；
- feedback 首次提交可以 decision=pending；再次修改必须使用 PUT、expected_version、confirmed 和 correction_reason；
- Service 负责根据 decision 原子更新 Application，API 只映射错误。

### 13.2 Offer 与最终结果

```text
GET  /api/v2/applications/{application_id}/offers
POST /api/v2/applications/{application_id}/offers
PUT  /api/v2/offers/{offer_id}
POST /api/v2/offers/{offer_id}/send
POST /api/v2/offers/{offer_id}/accept
POST /api/v2/offers/{offer_id}/decline
POST /api/v2/offers/{offer_id}/withdraw
POST /api/v2/offers/{offer_id}/expire
POST /api/v2/applications/{application_id}/confirm-admission
POST /api/v2/applications/{application_id}/confirm-hire
POST /api/v2/applications/{application_id}/withdraw
POST /api/v2/applications/{application_id}/cancel-process
POST /api/v2/applications/{application_id}/reopen-stage9
```

所有高风险动作都要求 `confirmed=true`；缺少确认在 API 层返回稳定 422，不能依赖前端弹窗证明确认。

### 13.3 时间线与统计

```text
GET /api/v2/applications/{application_id}/timeline
GET /api/v2/screening-center/applications
GET /api/v2/recruitment-statistics
```

### 13.4 稳定错误

| HTTP | 错误码 | 场景 |
| --- | --- | --- |
| 404 | `APPLICATION_NOT_FOUND` | Application 不存在 |
| 404 | `INTERVIEW_NOT_FOUND` | 面试记录不存在 |
| 404 | `OFFER_NOT_FOUND` | Offer 不存在 |
| 409 | `APPLICATION_NOT_READY_FOR_INTERVIEW` | 未达到 HR 初筛通过条件 |
| 409 | `APPLICATION_PIPELINE_ENDED` | 流程已结束或作废 |
| 409 | `INTERVIEW_ROUND_CONFLICT` | 轮次重复或已有待进行面试 |
| 409 | `INTERVIEW_TRANSITION_INVALID` | 当前面试状态不允许该动作 |
| 409 | `INTERVIEW_VERSION_CONFLICT` | 面试记录已被其他操作修改 |
| 409 | `OFFER_ACTIVE_CONFLICT` | 已有非终态 Offer |
| 409 | `OFFER_TRANSITION_INVALID` | 当前 Offer 状态不允许该动作 |
| 409 | `OFFER_VERSION_CONFLICT` | Offer 已被其他操作修改 |
| 409 | `APPLICATION_REOPEN_INVALID` | 当前结果或支撑记录不允许重新打开 |
| 422 | `HR_ACTION_CONFIRMATION_REQUIRED` | 高风险动作缺少确认 |
| 422 | `HR_ACTION_REASON_REQUIRED` | 必填原因缺失或非法 |
| 422 | `OFFER_COMPENSATION_INVALID` | 薪资字段组合无效 |
| 500 | `RECRUITMENT_PIPELINE_OPERATION_FAILED` | 未预期失败且事务已回滚 |

错误响应不返回数据库约束名、薪资、反馈正文、会议链接、内部堆栈或 Key。

## 14. Schema 原则

- 所有写入 Schema `extra="forbid"`；
- ID 使用严格正整数；金额使用 Decimal 并限制位数，不接受 float 的隐式误差；
- `confirmed` 使用 StrictBool；
- reason code 使用受控枚举，自由说明去空白并限制长度；
- URL、时区、日期、数组长度和字符串长度全部固定；
- `expected_version` 使用严格正整数；
- 读取 Schema 与 ORM 解耦，不把 ActivityLog 任意 detail、文件路径或内部薪资暴露到列表；
- 列表、详情、动作和统计使用不同响应 Schema，不能为省事返回 ORM 全字段；
- AI 标签属于列表派生 Schema，不写回 ScreeningReport 或 parsed_snapshot。

## 15. Service、事务与并发

- Application 状态变化前使用 `SELECT ... FOR UPDATE` 锁定 Application；
- 面试和 Offer 修改同时锁定目标记录，并校验 `expected_version`；
- Application、Interview/Offer、StageHistory 和 ActivityLog 在同一事务提交；
- 外部 DeepSeek 不属于阶段 9 事务，阶段 9 Service 不调用模型；
- 创建轮次/Offer 依靠唯一约束和部分唯一索引兜底；
- 前端提交期间禁用按钮，但数据库约束和 Service 才是最终保护；
- 重复提交相同终态动作返回当前结果，不重复写 StageHistory；不同内容或过期 version 返回 409；
- 事务失败回滚本次状态、记录和审计，不留下半个 Offer 或已推进但无历史的 Application；
- 统计只读查询不修改状态；Offer 过期必须由明确动作记录，不在 GET 时偷偷写库。

## 16. Model 与 PostgreSQL

### 16.1 新对象

新增：

```text
InterviewRecord
OfferRecord
```

Application 增加 `final_outcome`；StageHistory 增加生命周期、最终结果和可选来源对象外键。Application 增加与 interview_records、offer_records 的关系。

### 16.2 数据库约束

InterviewRecord 至少包含：

- Application 外键；
- Application + round_number 唯一约束；
- 状态、类型、decision CHECK；
- JSONB 数组类型 CHECK；
- duration、version 和时间一致性 CHECK；
- 同一 Application 最多一个 scheduled 的部分唯一索引；
- application/status/scheduled_start_at 索引。

OfferRecord 至少包含：

- Application 外键；
- Application + version_number 唯一约束；
- 状态、周期、币种、Decimal 金额和时间一致性 CHECK；
- 月薪/年薪与 salary_months 组合 CHECK；
- 同一 Application 最多一个 `draft/sent/accepted` 的部分唯一索引；
- application/status/valid_until 索引。

Application 和 StageHistory 的现有 stage CHECK 通过新 migration 向前扩展，不修改既有 migration。`final_outcome` 建立 CHECK 和索引。

### 16.3 Migration 原则

9A 使用一条新的向前 Alembic revision：

1. 不修改 `a8d4f2c7e901` 或更早 revision；
2. 先增加可空 `final_outcome` 和 StageHistory 兼容字段；
3. 对可解释的既有阶段 7 rejected 行回填 `screening_rejected`；
4. 创建 Interview/Offer 表、外键、唯一约束、CHECK 和索引；
5. 最后增加 Application 生命周期/结果一致性 CHECK；
6. 不创建虚构面试、Offer、录取或入职记录；
7. 在随机临时 PostgreSQL 验证 `upgrade → downgrade → upgrade`；
8. 开发数据库只执行确认后的向前升级；
9. 最终 `current=head` 且 `alembic check` 无漂移。

## 17. 前端交互与安全

- AI 初筛中心不能仅靠颜色表达分数、状态或错误；标签必须有文字；
- 表头、筛选、排序、行操作、抽屉和确认弹窗支持键盘与焦点；
- AI 综合评价、优点和风险使用行数限制加 tooltip/详情，不用 CSS 截断后丢失可访问名称；
- 具体薪资只在 Offer 区加载，不进入列表 DOM、统计响应或全局搜索；
- 完整手机号/邮箱只在详情按需展示，列表手机号脱敏；
- 候选人简历、反馈、备注和 AI 内容都当作不可信普通文本；
- 过期、失败、无报告、旧报告保留必须使用不同文案；
- HR 弹窗只是交互提示，后端仍校验 confirmed、version、状态和原因；
- 1440×900、820×1180 和 390×844 必须无横向溢出；桌面信息密度不能靠极小字号实现；
- 前端自动化使用假响应，不创建真实业务数据，不触发 DeepSeek。

## 18. 关键异常流程

| 场景 | 固定行为 |
| --- | --- |
| 备选候选人尝试安排面试 | 拒绝，先由 HR 明确调整为通过 |
| Application 已结束/作废 | 拒绝新面试和新 Offer |
| 两个 HR 同时改同一面试/Offer | 一个成功，另一个因 version 冲突刷新 |
| 双击创建同轮面试 | 唯一约束只产生一条，返回稳定冲突 |
| 面试取消或未到场 | 不自动淘汰；保留记录，由 HR 决定重排或结束 |
| 面试反馈保存失败 | Application 不推进，旧反馈和状态保留 |
| Offer draft 保存失败 | 不推进或改变 Application |
| Offer 标记 sent 失败 | 保留 draft，不伪造已发送 |
| 候选人接受后尚未确认录取 | 保持 offer_accepted，不显示 admitted 或 hired |
| 已确认录取但尚未实际入职 | 保持 admitted，不显示 hired |
| Offer 已过有效期 | 页面显示逾期提示；HR 明确标记 expired，GET 不写库 |
| 已结束流程需要更正 | 使用专用 reopen，确认并追加历史 |
| 当前 AI 报告过期 | 列表显示旧分数/标签并明确过期，不重新调用模型 |
| AI 初筛失败 | 不影响已存在的面试/Offer历史，也不自动改变阶段 9 决定 |
| 岗位关闭 | 不静默取消已存在阶段 9 流程，由 HR 明确结束 |
| 统计缺少完整起止时间 | 排除该耗时样本并返回样本数，不编造 0 |

## 19. 分层职责

```text
React AI 初筛中心
  列表、筛选、统一详情、表单、确认和统计展示
        ↓
FastAPI API
  HTTP 合同、依赖注入、稳定错误和确认入口
        ↓
Pydantic Schema
  枚举、字段、金额、版本、原因和响应边界
        ↓
RecruitmentPipelineService
  Application 状态机、事务、并发和审计
  ├─ InterviewService
  ├─ OfferService
  ├─ ScreeningCenterQueryService
  └─ RecruitmentStatisticsService
        ↓
SQLAlchemy Model
  Application / StageHistory / InterviewRecord / OfferRecord
        ↓
PostgreSQL
  外键、唯一约束、CHECK、索引和真实业务数据
```

- 前端不计算允许的状态转换或招聘统计真值；
- API 不直接改 ORM；
- Schema 不访问数据库；
- Query Service 不调用 DeepSeek 或改变业务状态；
- Interview/Offer Service 不复制阶段 7 AI 逻辑；
- Model/PostgreSQL 不保存前端派生 HTML 或列表截断文本。

## 20. 自动化与验收

### 20.1 Schema 与 Model

- 全部枚举、长度、金额、日期、时区、数组和额外字段拒绝；
- Application lifecycle/stage/final_outcome 合法和非法组合；
- 面试状态/decision/反馈一致性；
- Offer 状态/薪资/时间一致性；
- StageHistory 新字段和旧行兼容；
- ORM 关系、唯一约束、CHECK 和部分唯一索引。

### 20.2 Service 与 API

- 只有 HR 已通过 active Application 能进入面试；
- 多轮、改期、取消、未到场、反馈和下一轮；
- 面试进入 Offer、淘汰和退出不改写 hr_decision；
- Offer draft、精确薪资、sent、accepted、declined、withdrawn、expired；
- accepted、admitted 与 hired 三段分离；
- 高风险确认、reason、version 冲突、重复请求幂等；
- 事务失败不留下半状态；
- timeline 顺序和安全字段；
- 列表聚合无 N+1、分页/筛选/排序和 AI 标签提取；
- 报告过期、失败、旧报告和无报告状态；
- 统计 cohort、漏斗、转化率、耗时样本数和实时待办；
- OpenAPI 路由唯一、稳定错误不泄密。

### 20.3 Migration 与真实 PostgreSQL

- 开始前重新检查 current/head/check 和实际数据；
- 临时 PostgreSQL `upgrade → downgrade → upgrade`；
- 既有 rejected 可解释回填，其他行不伪造；
- 并发创建同轮面试和 active Offer 的唯一约束真实生效；
- version 冲突和 `FOR UPDATE` 状态转换真实生效；
- 开发库向前升级后原 Application/Resume/报告数量不丢失；
- 最终 Alembic current=head 且 check 无漂移。

### 20.4 前端与浏览器

1. 左侧只有工作台、候选人、岗位管理和 AI 初筛中心。
2. 旧 `/app/resumes`、`/app/reports` 自动跳转。
3. 列表无需点开即可看到分数、匹配标签、能力标签、评价、优点、风险、HR 决定和阶段。
4. 无报告不显示 0 分；过期和旧报告有明确标记。
5. 内部和公开 Application 都能在统一详情查看简历与报告。
6. 候选人详情深链接可以定位并打开正确 Application。
7. 多轮面试、反馈、Offer 和时间线可操作并刷新真实响应。
8. 具体薪资只在 Offer 详情出现。
9. 招聘流程统计与 PostgreSQL fixture 一致。
10. 桌面、平板、手机和键盘无阻塞。

### 20.5 DeepSeek 与费用

阶段 9 不新增 DeepSeek 调用。AI 标签、列表和统计只读取已有成功报告及业务数据；普通自动化和浏览器验收不得因展示标签而产生模型费用。

如实施发现必须新增模型生成标签、面试总结或 Offer 文案，属于新的 AI 合同和付费范围，必须先停止、修改本文并单独获得确认。

## 21. 实施顺序

本文获得项目负责人最终确认后，按以下批次实施：

1. **9A：合同与 migration**：Application/StageHistory 扩展、InterviewRecord、OfferRecord、枚举、约束和临时 PostgreSQL 往返；不接前端。
2. **9B：面试后端**：面试 Schema、Service、API、事务、并发、审计和时间线。
3. **9C：AI 初筛中心收口**：列表聚合 API、AI 标签、导航精简、桌面表格/移动卡片、简历与报告统一详情和深链接。
4. **9D：Offer 与最终结果**：精确薪资、Offer 状态、接受/拒绝/撤回/过期、录取、入职和重新打开。
5. **9E：招聘流程统计**：cohort 漏斗、耗时、待办、工作台和初筛中心统计展示。
6. **9F：完整验收**：后端回归、migration、真实 PostgreSQL/API、前端测试/build、浏览器和项目负责人验收。

每批先跑直接相关测试，再按影响扩大。任何必须改变状态、薪资、确认、AI 标签、页面收口、API、migration 或统计口径的情况，都必须先更新本文并重新确认。

## 22. 完成标准与不能证明的内容

只有同时满足以下条件才能宣布阶段 9 完成：

1. HR 已通过的 Application 能进入多轮面试并保留安排和反馈；
2. 面试可以安全进入下一轮、Offer、淘汰或退出；
3. Offer 保存精确薪资并区分 draft、sent、accepted、declined、withdrawn、expired；
4. 接受 Offer、已录取等待入职和正式入职明确分开，并各自需要真实人工动作；
5. 阶段 9 后续结果不改写阶段 7 HR 初筛决定；
6. 所有高风险动作、撤销和更正可追溯；
7. AI 初筛中心完成导航、列表和统一详情收口；
8. AI 分数、匹配标签、能力标签、优点和风险在列表中真实可见；
9. 招聘流程统计只根据数据库事实计算；
10. migration、自动化、真实 PostgreSQL/API、前端构建和浏览器验收通过；
11. 项目负责人完成最终产品验收。

阶段 9 验收不能证明：

- AI 初筛代表真实招聘准确率；
- 面试反馈具有跨面试官一致性；
- 系统已自动发送或签署 Offer；
- 薪资数据已有生产级字段权限和加密治理；
- 系统已经接入真实日历、邮件、ATS 或候选人账号；
- 登录、RBAC、多租户、数据保留和生产部署已经完成；
- 作品集演示可以使用真实候选人或真实薪资。

这些剩余边界由阶段 12 或新专项处理，不能通过隐藏风险或扩大 AI 决策权换取阶段 9 通过。

## 23. 简历与面试表达

阶段完成后可以如实描述：

> 在 Application 主链上设计并实现多轮面试、Offer 与录取状态机，通过 PostgreSQL CHECK/部分唯一索引、乐观并发、行锁、追加审计和可恢复更正确保高风险招聘状态一致；同时将简历、AI 报告、面试、Offer 和流程统计收口到统一 AI 初筛中心，并从既有可解释报告中确定性提取可追溯能力标签。

常见面试追问包括：

- 为什么阶段 9 淘汰不能把阶段 7 hr_decision 改成 rejected？
- Application stage、lifecycle 和 final_outcome 为什么要分开？
- 怎样保证双击或两个 HR 不会创建重复面试/Offer？
- 为什么接受 Offer 不等于正式入职？
- 具体薪资为什么使用 Decimal/NUMERIC？
- AI 标签怎样做到不再调用模型且仍可追溯？
- 为什么招聘漏斗要使用历史事件而不是当前状态？
- 为什么 Offer 过期不能在 GET 请求中偷偷写库？
- 为什么删掉独立页面但不删除 Resume 和报告数据？

## 24. 设计确认门禁

本文当前只代表已经讨论的产品选择被整理成正式设计草案。项目负责人必须完整审核并明确确认本文后，才能开始 9A。

确认前明确禁止：

- 修改 Application/StageHistory Schema 或 ORM；
- 新增 Interview/Offer Model 或 migration；
- 修改 `/app/screening` 导航、列表或详情；
- 删除独立前端页面或改变旧 URL；
- 新增面试、Offer、统计 API；
- 写入开发数据库或创建演示面试/薪资数据；
- 调用 DeepSeek 或产生费用。

如果项目负责人要求调整本文任何核心状态、字段、权限、薪资、统计、AI 标签或验收标准，应先修改本文，再重新确认，不得让实现先行。
