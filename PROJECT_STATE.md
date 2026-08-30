# 项目当前状态

> 最新更新：2026-08-30
>
> 本文件只记录“现在是什么状态、下一步做什么”。完整开发过程已归档到 `docs/archive/history/2026-08-20-project-history.md`，不再作为新对话的默认阅读材料。

## 1. 当前结论

- 项目正在建设新版招聘主链，旧 React + FastAPI + SQLite + Mock LLM 演示系统已经退役。
- 阶段 4“简历上传与原文提取”和阶段 5“AI 结构化草稿”已经完成；阶段 6 五段式 JD 整改的 6R-A—6R-D 已全部完成，自动化、真实 PostgreSQL/API 和 Microsoft Playwright 三档浏览器验收通过。
- 阶段 7 的 5.0 产品主链已实现，但真实质量和最终收尾尚未通过。I2-E 在 USD 2 上限下完成 45/45 次调用，费用 `$0.09143638`；计划 `10/10`，报告仅 `17/20`，稳定性达标组仅 `2/5`。CLOSE-03A/B 已完成唯一正式 human audit 和 final，19 项门槛通过 13 项、失败 6 项，`quality_gate_passed=false`，生命周期为 `i2_final_complete`；raw/human/final 均不可覆盖。CLOSE-04R 已按用户确认把后续修订为验收合同、计划 Service、计划 Prompt、报告 Service、报告 Prompt 五批，并明确 Service 只硬判结构/真实引用/时间身份/安全，“至今”只按 `Application.applied_at`；当前停止并等待单独确认 CLOSE-05A，不得自动整改、执行 I3 或进入 7R5-J。本机 Alembic 为 current=head=`d6e8f0a2b434`。
- 小步骤 9-I 已完成 20 次 JD 正式复验和 60 次下游真实诊断。18/18 正常 JD 可用、主要要求与结构化覆盖均为 100%，但 JD18 没有形成预期 `too_many_items`，因此 `step9_quality_gate_passed=false`，小步骤 9 仍未通过；下游诊断也仅有 9/20 至少一份合法报告、1/20 三次全部合法。
- Application、Resume 隔离、HR 内部录入和 HR 决策等公共能力继续保留。
- 旧 Rubric、五维权重、确定性评分、`unknown`、证据覆盖率和 Python 加权总分已经废弃。
- 阶段 7 暂停前的公共业务方案已经确认并实现：旧 Rubric 删除、`JobEvaluationPlan`、严格单次评价、异步运行、幂等、当前成功报告替换、React 完整报告交互以及固定投递时间事实已经完成。SR05/SR15 最终 6 次真实 DeepSeek 定向复验的严重年限事实冲突为 0，但合法报告只有 3/6；原 Playwright 浏览器验收仍为 60 项中 57 通过、2 失败、1 未验证、0 阻塞。五段式计划 3.0 的程序生成链已在 Fake 下完成，不代表真实模型质量、Screening、React 或阶段 7 整体通过。

## 2. 当前权威文档

文档职责和按任务阅读规则统一见 `docs/DOCUMENT_INDEX.md`。

当前阶段的权威顺序是：

1. 阶段 7 轻量评价清单 5.0 当前设计：`docs/stages/stage7/2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`，负责产品目标、业务合同、状态、数据、安全、验收标准和完整历史证据
2. 阶段 7 剩余工作与收尾计划：`docs/stages/stage7/2026-08-30-stage7-remaining-work-plan.md`，只负责从当前状态到阶段完成评审的执行看板、依赖、逐批边界和停止点；用户已整体确认，CLOSE-02、CLOSE-03A、CLOSE-03B、CLOSE-04、CLOSE-04R 已完成，当前等待单独确认 CLOSE-05A
3. 阶段 7 评价计划 4.0 历史实现与失败证据：`docs/stages/stage7/2026-08-24-stage7-job-evaluation-plan-v4-redesign.md`，保留 RequirementFact、三/四次调用、HR2 `6/6` 和正式 20 份 `15/20` 的不可覆盖记录，不再授权新增实现
4. 阶段 7 五段式计划 3.0 记录：`docs/stages/stage7/2026-08-22-stage7-five-section-job-evaluation-plan-redesign.md`，只负责已完成实现事实和历史失败证据
5. 阶段 7 原设计：`docs/stages/stage7/2026-08-20-stage7-jd-driven-ai-screening-redesign.md`，其已实现的 Application、Resume、异步运行、报告、时间事实和 HR 决策底座继续有效
6. 阶段 6 五段式 JD 整改：`docs/stages/stage6/2026-08-21-stage6-five-section-jd-remediation-design.md`
7. 阶段 6 原设计：`docs/stages/stage6/2026-08-15-stage6-structured-job-management-design.md`，除被五段式补充替代的 JD 字段合同外继续有效
8. 本文件：只负责当前进度、工作区风险和下一步
9. `CLAUDE.md`：项目长期架构、技术栈和稳定约束
10. `docs/planning/implementation-plan.md`：跨阶段实施顺序
11. `docs/planning/2026-08-14-post-stage5-product-roadmap.md`：阶段 5 后产品路线
12. `docs/architecture/2026-07-15-hr-agent-platform-design.md`：总体架构背景

发生冲突时，当前阶段专项设计优先于旧总体示例和历史记录。归档文档不具有当前业务权威性。

## 3. 当前阶段 7 方案摘要

> 当前说明：5.0 已完成从 Schema、生成、编辑确认、报告、运行接线到 React 的 7R5-A—7R5-G 非付费实现，7R5-H 门禁和 I2 real raw 已执行。I2-E 自动结果为计划 `10/10`、报告 `17/20`、稳定性 `9/15`，稳定性达标组 `2/5`，费用 `$0.09143638`。CLOSE-03A/B 已基于封存 raw 完成人工审计与正式 final，19 项门槛通过 13 项、失败 6 项，生命周期为 `i2_final_complete`；CLOSE-04/04R 已完成综合归因和五批整改设计。真实 5.0 最终质量、真实 PostgreSQL/API/浏览器完整收尾仍未验收。当前只等待用户单独确认 CLOSE-05A，不自动修改质量工具、Service、Prompt 或进入 I3；下文第 4—9 节同时记录可复用能力和历史基线，若与 5.0 设计冲突，以 5.0 为准。

### 3.1 固定流程

```text
HR 维护完整 JD
        ↓
AI 一次生成约 5—12 个主要评价点
        ↓
HR 编辑、新增、删除、合并并确认轻量评价清单
        ↓
完整 JD + 已确认清单 + 当前 Application 简历进入独立 AI 初筛
        ↓
AI 对每项给 0—10 分并直接给总体 0—100 分
        ↓
程序校验证据、安全和明显方向矛盾
        ↓
HR 阅读报告并独立作出通过 / 备选 / 淘汰决定
```

本流程是固定的 Service 工作流，不是自然语言 Agent，也不使用 LangGraph。轻量评价点不是权重项，程序不计算加权总分。

### 3.2 评分与报告边界

- 评价点按 `required/preferred/general` 标记，逐项使用 `0—10` 整数，不使用 `unknown`。
- 0 分表示当前简历没有体现，不代表候选人事实上不会。
- 1—10 分必须有可定位的简历证据。
- 完整报告必须分别展示优势、差距、风险/冲突、缺失信息和 HR 跟进问题。
- DeepSeek 直接给出 `0—100` AI 岗位匹配建议分；Python 不按固定权重重新计算。
- 程序只根据综合分生成五档展示标签，不生成通过、淘汰或录用建议。
- 每个 Application 只保留最近一次成功报告和必要运行日志；重新评估失败时保留旧成功报告。
- 姓名、联系方式、性别、出生日期、婚育、民族、籍贯和照片等内容在模型输入前移除。
- 学校和公司名称可以结合真实专业、职责、项目和成果作为语境，不能只按品牌判断能力。

### 3.3 已实现的投递时间基准

- AI 初筛的 `evaluation_reference_at` 固定取当前 `Application.applied_at`，不取 Resume 上传时间、模型调用时间或当前系统时间。
- 阶段 7 的 `evaluation_timezone` 固定为 `Asia/Shanghai` 并随 Run/Report 审计保存，不依赖服务器本地时区。
- 首次评价、普通幂等请求、单人/批量重新评估和切换 Resume 后的重新评估，都继续使用原 Application 的同一投递时间。
- 后端负责生成版本化、可复核的经历时间事实；DeepSeek 负责相关性和匹配评分，Python 不恢复固定权重、总分公式或自动招聘决定。
- 评价基准、时间事实及规则版本必须进入 Prompt、输入指纹、ScreeningRun/ScreeningReport 审计元数据；报告页面展示评价基准日期。
- 该合同已于 2026-08-21 完成代码、Schema、Model、API、React、向前 migration、自动化和真实 DeepSeek 定向复验。事实规则版本为 `experience_period_facts_v1`，输出 Schema 保持 `2.0`；筛选 Prompt 已在7R4-E切换为 `screening_evaluation_v4`，当前数据库 head 为 `d6f4a2b8e913`。

完整字段、状态、失败语义、验收场景和实施顺序以阶段 7 当前设计为准，本文件不重复维护第二套详细合同。

## 4. 已完成且继续保留的能力

- 新版唯一前端业务目录：`frontend/src/features/recruitment/`
- 新版工作台路由：`/app/*`；公开投递入口：`/apply`
- 正式后端接口：`/api/v2/*`
- PostgreSQL + SQLAlchemy 2.0 + Pydantic v2 + Alembic 主链
- PDF、DOCX、TXT 安全上传、私有存储和原文提取
- `Resume.raw_text` 与 `Resume.parsed_snapshot`
- DeepSeek 简历结构化草稿、严格校验和 HR 确认创建
- 五段式 Job 普通文本合同、岗位草稿/开放/关闭状态
- Candidate 稳定身份与去重
- Application 按岗位独立绑定 Resume、独立 HR 决策和阶段历史
- HR 直通录入与 AI 初筛中心待审核录入

## 5. 已完成但已被 4.0 运行入口替代的 JobEvaluationPlan 3.0 能力

以下内容只描述历史验证事实和为旧数据保留的只读兼容，不表示它满足 4.0，也不允许继续用于新的生成或正式质量结论：

- 独立 `JobEvaluationPlan` Schema、SQLAlchemy Model 与 PostgreSQL 表继续保留；revision `a9e7d3c5b821` 让 3.0 与历史 1.0/2.0 只读数据共存，不改写旧计划或报告/运行外键。
- 历史 3.0 输入只包含 Job 基础上下文、岗位背景、岗位职责、任职要求和加分项；候选人可见备注不进入模型、快照或指纹。程序稳定切分三块评价原文，AI 逐段审阅，程序负责原文追溯、固定字段优先级、多来源合并、warning 和 0—30 项边界。
- 历史版本为 Prompt `job_evaluation_plan_v5`、AI Schema `3.0`、计划 Schema `3.0`。旧计划保存 `generating/ready/failed/outdated`、source review summary、事项多来源、受控 warning、输入快照、两层指纹、稳定错误和完成时间。
- 同输入 ready 幂等复用，仅候选人可见备注变化也不调用 Adapter；评价输入变化会让旧计划过期并生成新计划。普通 failed 不自动重试，显式 regenerate 可以重试；基础设施最多额外重试一次，内容错误不重试。
- Job 创建即开放、开放和重新开放在 Job 提交后使用独立数据库会话协调计划生成；开放 Job 编辑只做输入变化失效判断，不立即调用模型。计划失败不会回滚 Job，慢响应不会覆盖新输入。
- `/api/v2/jobs/{job_id}/evaluation-plan` 的生成和失败重试已切换为 4.0，成功先 `pending_confirmation`；新增无正文的 `/confirm`，事务复核后才 `ready`。展示 GET 继续允许旧 1.0—3.0 历史只读；Screening 只消费合法当前 4.0 ready，旧合同统一等待重新生成并确认。

## 6. 已完成的 AI 报告与单次评价能力

- 新增严格 `AIScreeningEvaluationOutput` Pydantic 合同，限定综合分、逐项评价、证据、0—5 个额外亮点、可空权衡说明和最多 5 个面试问题；禁止额外字段、旧 `strengths/gaps/risks`、`display_label` 和招聘决定字段。
- 基础事项必须与当前 `JobEvaluationPlan` 的 key 完整且一一对应；1—10 分必须有可定位证据，0 分必须表达“当前简历未体现”，不得写成候选人不会。
- 额外亮点只允许 7—10 分、正向、岗位相关、有证据且不与基础事项重复；DeepSeek 直接给综合分，Python 只生成五档展示标签，不求和、平均或加权重。
- 任意低分 `required` 与 70 分以上综合分并存时，必须同时解释支持高分的优势和待确认短板；明显的分数、理由、摘要、证据和权衡矛盾会被拒绝。
- 新增最小、可测试的 Resume 脱敏边界，移除姓名标签行、联系方式、身份证、详细住址、性别、出生、直接年龄、婚育、民族、籍贯、照片和外貌信息，保留学校、公司、专业、职责、项目与成果。
- 版本化 Prompt 把 JD、JobEvaluationPlan 和 Resume 都声明为不可信数据，只允许评价当前 Application 的当前 Resume，明确证据、公平性、Prompt 注入和禁止招聘决定规则。
- DeepSeek/Fake Adapter 只负责一次模型调用及原始响应/元数据转换，SDK 自动重试关闭；认证、配额、限流、网络、服务端、超时和非法响应映射为稳定安全错误。
- 纯评价 Service 严格解析 JSON，校验事项、证据、安全、事实支撑、亮点、权衡和一致性，并返回报告、程序展示标签以及 Prompt/模型/Schema/脱敏版本元数据。
- 小步骤 5 当时只完成纯评价能力，没有新增持久运行和报告替换；这些能力已由下述小步骤 6 衔接完成。

## 7. 已完成的异步运行、幂等与当前报告能力

- `ScreeningReport.is_current` 部分唯一索引保护每个 Application 最多一份 current 成功报告，旧成功行作为只读历史保留；`ScreeningRun` 保存必要运行日志，不保存原始模型响应或未脱敏 Resume。
- 使用稳定 JSON 序列化和 SHA-256 组合 Application、`Application.applied_at`、`Asia/Shanghai`、经历时间事实/规则版本、JD、当前 Resume、当前 ready 评价计划及 Prompt/模型/Schema/脱敏版本；普通请求复用相同报告或运行，主动“重新评估”即使输入相同也会建立新运行。
- 采用 PostgreSQL 持久运行表加 FastAPI 生命周期轮询器作为当前架构下的最小可靠后台机制；`FOR UPDATE SKIP LOCKED`、部分唯一索引和租约恢复共同保护多进程认领、并发重复及服务重启后的可解释状态，没有引入 Celery、RQ、Arq 或无持久状态的任务假象。
- Application 提交、Resume 解析完成、岗位重新开放和4.0计划确认会在相关业务提交后协调首次自动初筛或等待任务；HTTP 请求不等待筛选模型，触发失败不回滚已经提交的 Candidate、Resume、Application 或 Job。
- Resume/计划不可用分别保留 `waiting_resume/waiting_plan`；计划原因稳定区分缺失、生成中、失败、过期和合同过期，岗位关闭以 `job_closed` 暂停未开始任务且允许 `running` 完成；岗位重开按最新输入恢复仍然有效的自动任务和人工重新评估。
- 只有 active Application、开放 Job、可用 Resume 与当前合法 5.0 ready 计划能够 queued；1.0—4.0 只读且阻止新筛选，`pending_confirmation` 使用独立 `plan_pending_confirmation` 等待原因。运行中输入变化以 `SCREENING_INPUT_OUTDATED_DURING_RUN` 失败，不替换旧报告。
- 成功响应会重新核对最新 Resume、JD 和计划，只在严格 Schema/业务校验通过后，以同一数据库事务替换当前报告并把运行标记成功；迟到响应、内容失败或数据库提交失败都保留旧报告。
- 网络、限流、超时和模型服务端故障最多额外重试 1 次；认证、配额、JSON、Schema、事项、证据、安全及业务内容错误不自动重试，SDK 自动重试仍关闭。
- Resume、JD 或当前计划变化只把旧报告标记过期，不删除、不自动批量重评；普通 Prompt、模型或 Schema 版本升级不会自动使历史报告过期。
- 当前 5.0 代码已有普通触发、显式确认的单人重新评估、同岗位 1—5 人批量重新评估、逐人稳定失败结果、current/历史报告读取和切换当前 Resume 的最小 `/api/v2` 接口。
- AI 初筛链路不写 HR 通过/备选/淘汰决定；成功或失败只把仍处于 `pending + applied + active` 的 Application 推进到 `hr_review` 并追加 system StageHistory，HR 已先行决策时不倒退或覆盖。当前仍沿用内部开发接口边界，没有临时伪造登录/RBAC。
- `ScreeningReport` 额外审计评价基准、时区、事实规则版本和成功评价使用的完整时间事实快照；`ScreeningRun` 审计评价基准、时区、规则版本和时间事实指纹，不保存完整 Resume 或模型原始响应。
- 新迁移 `d9a1f4c7e820` 只向既有 `ScreeningReport`/`ScreeningRun` 增加上述审计字段。真实数据库没有历史行；migration 对假设存在的旧行也只从关联 `Application.applied_at` 回填基准，不伪造旧事实快照。

## 8. 已完成的 React 完整报告与交互

- 严格 TypeScript 合同和集中 `v2Http` Service 已扩展到 5.0 评价点、草稿保存、乐观并发版本、确认/分叉、计划历史、完整报告、报告历史和五人批量逐项结果；组件中不散落裸 `fetch`，也不使用 `any` 绕过合同。
- 岗位列表的评价计划抽屉已接入 5.0：HR 可编辑重要程度、名称、说明、初筛重点和备注，可新增、删除、合并后整份保存；AI 来源与 HR 补充、JD 原文和稳定 ID 明确区分，warning 指向具体评价点/原文/复核原因。未保存编辑时禁止确认；确认后当前版本只读，只能创建新编辑版本，旧 1.0—4.0 计划继续历史只读。
- AI 初筛工作台读取每个 Application 当前 Screening 状态；5.0 报告抽屉展示 AI 直接建议分、程序标签、综合说明、每项 0—10 分、评价点快照、JD 原文和 Resume 证据，以及优势、差距、风险/事实冲突、缺失信息、HR 后续问题和审计元数据。0 分固定说明“当前简历未发现相关证据，不等同于不会”；旧 1.0—4.0 报告可在成功历史中切换并保持只读。
- 0 分固定解释为“当前简历未体现”，AI 分数和标签固定说明为辅助建议；查看、普通初筛、重新评估和批量操作均不调用 HR 决策接口，不修改 `hr_decision`、`recruitment_stage` 或 `lifecycle_status`。
- 报告过期时继续展示旧报告和 Resume/JD/评价计划变化原因；现有 4.0 页面在计划与报告一致时按 criterion 分组并逐 fact 展示，5.0 将改为直接逐评价点评分。旧计划不可读取或 ID 不一致时仍必须诚实回退，不能使用新计划内容冒充旧报告。
- `queued/running` 使用 4 秒最小轮询；终态、关闭抽屉或组件卸载后停止。请求序号阻止迟到响应覆盖新状态，递归 `setTimeout` 保证只保留一个定时器。
- 评价计划 `generating` 同样使用单个 4 秒递归轮询，在 ready/failed/outdated、关闭抽屉、关闭岗位或组件卸载时停止；前端只停止查询，不声称取消后台任务。
- 普通初筛明确允许复用报告或运行；单人“重新评估”需要危险确认，新运行期间及失败后继续展示旧成功报告；岗位关闭时禁用开始和重新评估。AI queued/running 时 HR 决策按钮明确禁用，但终态 AI 结果不会替代或自动改写 HR 决定。
- AI 初筛工作台只允许同一开放岗位选择 1—5 个 Application，达到 5 个后第 6 个选择被禁用；批量结果分别展示总计、复用、排队、失败及每个 Application 的状态/安全错误，部分失败不抹掉已提交项。
- 计划和报告抽屉在移动端占满可用宽度且无页面横向溢出；关闭计划抽屉后焦点回到原“评价计划”按钮。危险确认、表单可访问名称、键盘焦点和迟到请求保护继续保留。
- `/app/reports` 继续保持通用 Report 只读中心；Application 当前 AI 报告从 `/app/screening` 进入，避免混淆两类数据模型。

## 9. 已完成删除的旧阶段 7 能力

- `JobScreeningRubric` 及模板、草稿、编辑、生成、发布和版本流程
- `standard/technical/non_technical` Rubric 模板
- 五维权重、维度内部占比和 AI 占比优化
- HR 手动维护 Rubric 语义项及 AI 单项辅助
- Python 年限、学历、技能和关键词确定性评分
- `unknown`、证据覆盖率、推荐上限和 Python 加权总分
- 同一 Application 多份完整 ScreeningResult 历史
- 旧 Rubric 页面、API、Schema、Service、Prompt、Adapter、Model 字段和相关测试

已执行的 Alembic 历史保持不变；新迁移 `c4a9d8e7f621` 已向前删除旧表、字段、索引和约束。它的 downgrade 只恢复空结构，不能恢复已删除的数据。

旧设计已经归档到 `docs/archive/superseded/2026-08-17-stage7-application-ai-screening-design.md`，只在盘点旧 Rubric 或追溯历史时阅读。

## 10. 当前工作区状态与风险

- 当前分支是 `2lcj`，当前基线包含提交 `44b7626191d82b11760c7e56588f7799ea7629ba`。工作区已有的 `PROJECT_STATE.md`、当前阶段 7 权威设计、7R5-I 价格快照、raw 和人工审核辅助目录均为用户工作成果，必须完整保护；本次只在两份既有权威文档上追加 Service 整改门禁，没有覆盖 raw、人工记录、前几批代码或历史 4.0 质量结果。
- 项目由旧电脑压缩迁移后，旧 `.venv` 因保存 `C:\Users\GYAI\...Python311` 绝对路径而失效。本轮已用本机 Python 3.11.9 原地重建 `.venv`，安装 `backend/requirements.txt` 和本地测试依赖 pytest 9.1.1；`.venv` 继续由 Git 忽略，不提交、不再跨电脑复制。
- 本机 PostgreSQL Docker 卷原停在 `b4e8c2d7f913`，且保留 1 个 Job、2 个 Candidate、2 个 Resume 和 1 个 3.0 failed 计划。升级前已生成 `data/backups/pre_a3b5c7d9e101_20260826.dump`；2026-08-29 再次核对大小为 87,224 bytes，SHA-256 仍为 `F8F8AD2EB6C3E6D399562D7DDC2146C262A87A4D9BDBC85FD858325C0D962C4C`。7R5-D 曾新增 revision `b4c6d8e0f212` 并完成真实 `b4 → a3 → b4` 往返；HASH-B 全量回归前发现本机仍停在 `b4c6d8e0f212`，经用户单独明确授权执行 `b4c6d8e0f212 → c5d7e9f1a323 → d6e8f0a2b434`，现为 `current=head=d6e8f0a2b434`，`alembic check` 无待生成操作。
- 4.0 的 7R4-A—7R4-H2 均停在各自历史停止点；HR2 定向为 `6/6`，正式 H2 为 `15/20` 且失败。7R4-I/J 永久停止，不再通过追加 4.0 样本整改继续推进；所有既有结果只作历史证据。
- 用户已经逐项确认 5.0 的产品目标、轻量评价清单、无权重评分、单人/最多 5 人批量、状态、审计、隐私和验收标准。7R5-A—7R5-H 已分别确认并完成，7R5-I raw 已按独立金额授权执行。用户于 2026-08-28 完成 10 份计划的引导式审核后，确认相关缩写、符号和非排他举例可以作为 HR 可编辑草稿，但不得变成新增硬门槛；并明确暂停其余人工审核，先处理 Service 逐词支持性误拒绝。`7R5-IR-A/B` 已分别确认并完成；I2 独立复验实施顺序已写入权威设计，但当前未授权 I2-A 测试、质量运行器生命周期调整或任何真实调用。
- 用户已最终确认并完成小步骤 9 的 9-A—9-I。此前助手误解用户意图产生的独立 20 份 JD 结果继续保留为历史诊断；正式 9-I 已使用新路径独立落盘，没有复用或覆盖该记录。JD18 的正式边界失败和当时返回阶段 6 整改的决定均为历史事实；当前新增实现依据已经切换为 5.0 设计。
- 用户已最终确认五段式 JD 业务合同和 6R-A—6R-D 顺序；四个批次已经全部完成并通过 6R-D 验收。
- 用户明确授权无备份删除唯一 Job #19；该历史操作不能从当前数据库直接恢复。7R4-B开始时正式开发库revision为 `e4c7a1b9d632`，四张直接相关表计数均为0；7R4-E结束时`current=head=d6f4a2b8e913`、`alembic check`通过，相关业务表均为0。d6已在正式空库完成真实`downgrade c7 -> upgrade d6`往返，没有写入或删除业务行。
- 后续不得恢复旧 Rubric、旧 ScreeningResult 或嵌入 Application 的 AI 状态字段。
- 新功能应复用 Candidate、Application、Resume、Job、StageHistory、Report 和通用 DeepSeek/数据库基础设施。

## 11. 当前唯一下一步

2026-08-30 已把阶段 7 的剩余工作从完整历史中拆分为 `docs/stages/stage7/2026-08-30-stage7-remaining-work-plan.md`。当前状态应统一理解为：5.0 产品主链已实现，CLOSE-02 已恢复 post-raw 全绿基线，CLOSE-03A/B 已完成 I2 正式人工审计与 final，CLOSE-04/04R 已完成综合整改设计和 Service 职责修订；final 真实判定失败，整改尚未实现，7R5-J 未开始，因此阶段 7 仍未完成。

用户已于 2026-08-30 整体确认收尾计划并逐批授权。`7R5-CLOSE-02` 已完成：专项 `65 passed`、阶段 7 扩大回归 `149 passed`、后端全量 `1321 passed + 425 subtests passed`，9 个旧状态失败全部消失且没有新失败。I2 raw 身份与大小不变，模型调用、费用和 PostgreSQL 写入新增均为 0。

`7R5-CLOSE-03A/B` 已完成并停止。问题总账和正式 human audit 已覆盖 107/107 个 required 标签、15/15 次稳定性和 12 项人工指标；final 合并后 19 项门槛通过 13 项、失败 6 项，`quality_gate_passed=false`。验证确认 raw/human 指纹不变、生命周期为 `i2_final_complete`，第二次 finalize 被拒绝；质量专项 `66 passed`，后端全量 `1322 passed + 425 subtests passed + 2 warnings`、0 failures，本批新增模型调用、费用和 PostgreSQL 写入均为 0。

`7R5-CLOSE-04` 已完成初次归因；用户随后确认 Service 应只硬判确定性结构、真实引用、时间身份与明确安全边界，普通语义和分数合理性交由 HR，并重申“至今”只按投递时间。`7R5-CLOSE-04R` 已据此完成文档修订并停止：CLOSE-05A 纠正 I3 质量合同、重要发现标签、逐案 `application_applied_at` 与 HR 确认计划快照；CLOSE-05B 把计划 Service 目标升级为 `lightweight_plan_generation_v4`，语义支持启发式改为 HR warning；CLOSE-05C 把计划 Prompt 升级为 `job_evaluation_plan_lightweight_v3` 并保留条件；CLOSE-05D 把报告 Service 升级为 `lightweight_report_generation_v8`，退出普通语义裁判；CLOSE-05E 把报告 Prompt 升级为 `screening_evaluation_lightweight_v5`。计划与报告 Schema 版本均保持 5.0，质量合同目标为 `stage7_v5_quality_contract_v2`，I3 继续使用 19 项门槛。

CLOSE-04R 只修改三份权威文档，没有修改或执行质量工具、Service、Prompt、Schema、API、Model、React、数据库或正式证据；模型调用、费用、PostgreSQL 写入和 I2/I3 结果写入均为 0。

当前唯一下一步是等待用户另行确认 CLOSE-05A。不得提前修改质量工具、Service 或 Prompt，不得连续进入 CLOSE-05B—05E、I3、7R5-J 或阶段完成评审。

以下内容保留为 5.0 业务合同和历史上下文，不再承担“当前下一步”职责。

5.0 权威设计已经写入 `docs/stages/stage7/2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`。它保留现有 Application、异步运行、报告历史、投递时间和 HR 决策底座，只替换过度精细的 4.0 计划生成与逐 fact 接线。核心合同是：

- 完整 JD 作为上下文，AI 一次生成通常约 5—12 个主要评价点；
- HR 可以编辑、新增、删除、合并并确认，JD 外新增项明确标为“HR 补充”；
- 每项 0—10 分，AI 直接给总体 0—100 分，不使用权重或 Python 加权总分；
- 同岗位每名候选人独立评价，阶段 7 小批量最多 5 人；
- HR 决策始终独立，敏感属性和自动招聘决定为零容忍；
- 真实验收为 10 份新鲜 JD、20 组新鲜 JD/Resume、其中 5 组各 3 次稳定性，以及真实 PostgreSQL/API/浏览器。

7R5-A—7R5-H 均已完成。7R5-H 已实现冻结质量合同、零调用运行器、人工审计/费用/不可覆盖保护；应用内自动测试浏览器当时不可用，但用户于 2026-08-28 亲自完成浏览器手工测试并明确确认验收成功，因此 H 的非付费门槛已完成。数据库和代码迁移头为 `d6e8f0a2b434`；1.0—4.0 历史计划和报告保持只读兼容，没有回填、覆盖或改写旧行。5.0 报告已接入异步运行、最多 5 人批量、current/历史切换和 HR 审计移交；React 已接入清单编辑确认、完整报告、历史切换、批量部分失败和独立决策。内容错误不重试、不保存部分报告，失败不替换旧成功。7R5-I 唯一 real raw 已执行：29 次业务调用/API attempt、0 技术重试、估算 `$0.11033604`；自动结构门槛为计划 `6/10`、报告 `1/20`、稳定性合法运行 `0/15`。用户暂停后续人工审核后完成 `7R5-IR-A/B`；Service 合同与 10 份 raw 只读回放通过，后端全量除 6 个 post-raw 生命周期旧断言外为 `1200 passed + 425 subtests passed`，尚未 finalize、重跑或调用模型。

7R5-E Prompt 已按用户确认的结构化分区、输入隔离、严格 JSON Schema、4 个虚构脱敏且类别平衡的 Few-shot、静默完整性检查及 Prompt 版本/Bad Case 回归六项方法实现。Prompt 不要求或保存完整思维链；正式质量样本未用于反向调 Prompt。该结论只由静态合同和 Fake/Mock 行为验证支持，不能证明真实模型语言质量。

`7R5-I2-A—C` 和问题 1 的 `7R5-I2-R1-A—C` 已完成并停止。六例旧结构响应均被当前 Schema 接受，证明辅助列表数量问题解决；R1-C 当时的 Service 继续拒绝全部六例：4 个年限时间事实冲突、1 个高分/无证据方向矛盾、1 个无直接证据结论。隔离诊断不含原始响应。

用户已确认逐个解决 I2-E 问题。第一项时间事实 key 误用的 R7-A—D 已完成：生产为 Prompt v4 / Service v7；六份 I2-E 旧响应的原关键词门禁全部消失，但都进入非空 key 缺少 calculation_note 的确定性门禁。新隔离诊断不含 raw response，真实调用和费用为 0；这只能证明 Service 职责修正和旧响应的下一错误，不能证明 Prompt v4 改善真实模型输出或旧响应内容正确。

2026-08-30 简历提取 500 回归的 `7R5-RESUME-R1-A/B` 已完成并停止。新增 API 组合测试准确模拟 `after_resume_ready` 使 ORM 属性失效，生产修改前精确返回 500；Resume API 随后只在协调前创建并返回现有 `ResumeRead` 快照，协调器及其 `rollback`、Resume Service、Schema 字段、Model、migration、React 和提取器均未改。新测试转为 200，Resume 定向为 `77 passed + 21 subtests passed`；Docker/PostgreSQL healthy 后后端全量为 `1312 passed + 425 subtests passed`，仅剩已登记的 9 个 post-raw 生命周期旧失败。真实 Resume `#2301` 接口从历史 500 恢复为 200，调用前后 PostgreSQL 均为 `parsed`、原文 2060 字符、`not_started`、错误为空；其 Application 绑定数为 0，没有调用 DeepSeek 或产生费用。临时 Uvicorn 已关闭，Docker/PostgreSQL 当前保持运行。

R1-B 完成时的停止点恢复为讨论并登记 post-raw 生命周期测试整改顺序。该顺序现已写入 2026-08-30 收尾计划草案；在计划整体确认且 CLOSE-02 另行确认前，不得修改那 9 个测试。Resume 修复能证明“成功响应不再被协调回滚连带失效”，不能证明所有文件都可提取、AI 结构化正确或初筛质量达标。

### 11.1 2026-08-29 跨电脑交接清单

用户计划在当前电脑提交并推送，然后在另一台电脑拉取后继续。交接时必须以本文件和 5.0 权威设计为准，不依赖聊天记忆。

当前完成点：

- 计划 Service 的 JD 支持性机械误拒绝已由 `7R5-IR-A/B` 解决；原 raw 计划 10/10 已零调用回放通过。
- 报告辅助列表数量问题已由 `7R5-I2-R1-A—C` 解决；Prompt 要求通常只保留 1—5 条最高价值内容，Schema 技术上限为 20。
- 报告自然语言年限机械判断已由 `7R5-I2-R2-A—E` 取消；后端月份事实和 fact key 硬校验保留，Prompt v3 负责年限表达。
- 报告无 evidence 结论的同义词裁判已由 `7R5-I2-R3-A—D` 取消并完成六例回放；旧门禁 6/6 消失，Service 接受不等于内容正确，证据、事实、数字、ID、结构和安全硬门禁保留。
- 剩余 Service 总盘点/红灯/实现/回放 `7R5-I2-R5-A—D` 已完成：旧门禁 11/11 消失，9 份接受，R16/S00-3 两份进入下一来源表示门禁；另有 7 份报告和 9 次稳定性无响应。
- 自由文本来源裁判退出的 `7R5-I2-R6-A—D` 已完成：不为 R16/S00-3 增加编号或日期特例；R6-C 删除整类扫描并升级行为 v6，R6-D 将全部 19 份已有响应统一回放为 Service 接受 `19/19`、旧门禁消失 `2/2`。R5-D 固定为历史 v5 诊断，R6-D 固定为 v6 独占诊断，均只读且禁止覆盖；全部 19 例仍待未来人工质量判断。
- 文件字节 hash 阻塞已经由 `7R5-HASH-A/B` 取消；CRLF 副本能通过，缺文件、损坏 JSON、错误身份、case 分母/ID 不完整、生命周期越级和覆盖仍会失败。CLOSE-02 已将质量运行器/I2 预检专项恢复为 `65 passed`、阶段 7 扩大回归 `149 passed`、后端全量 `1321 passed + 425 subtests passed`。本机 PostgreSQL 为 `current=head=d6e8f0a2b434`。I2 raw 与 human 已完成且不可覆盖，final 不存在；生命周期合同验证为 `i2_human_complete`。

2026-08-29 当时的停止点是先讨论 post-raw 生命周期测试为什么仍硬编码 `i2_preflight_complete`。该问题已在 CLOSE-02 修复并全绿，CLOSE-03A 也已完成唯一正式 human audit。I2 raw、human、既有诊断和历史证据继续只读且禁止覆盖；当前停止点是等待用户另行确认 CLOSE-03B。

新一轮真实复验后需要重点核对的模型内容与验收队列：

1. 敏感属性门禁：R4-A—C 已完成；R07/R00/S00-2 的旧敏感拒绝 `3/3` 消失，当前 Service `3/3` 接受且没有下一程序错误。该项机械误拒绝已解决，但三例仍待未来人工质量审核，不能宣布内容或敏感属性语义正确。
2. Resume 不支持的普通事实：R06/R15/R18 已被 Service v5 接受；R06/R15 年限内容风险仍保留。R16 已在 v6 越过合法 criterion ID 尾号来源门禁，但能力迁移推断仍需人工审核；程序接受不代表事实正确。
3. Resume 不支持的非时间数字：R04/R17/S04-1/S04-3 已被 Service v5 接受；完全无来源数字硬保护继续保留。
4. 理由与证据联系不足：S00-1 的旧二字词门禁消失并被 Service v5 接受；内容正确性仍待人工审核。
5. 高分与无证据方向矛盾：R09 已被 Service v5 接受；S00-3 的旧方向门禁和后续自由文本来源门禁均已在 v6 消失，当前被 Service 接受，但实际分数与表述方向仍留给质量审核。
6. 报告五分区完整性：R14 虽是原 I2-C 中唯一通过 Service 的报告，但 `strengths` 为空，因此仍不满足每份报告必须包含优势、差距、风险/冲突、缺失信息和 HR 问题的人工质量门槛。
7. 旧 raw 缺少模型回答：R01、R02、R03、R08、R11、R12、R13 共 7 份报告，以及 S01-1—3、S02-1—3、S03-1—3 共 9 次稳定性响应，当时因上游计划被拒而没有调用模型；零调用回放不能补出这些内容。
8. 稳定性当前不可计算：没有任何一组获得 3 份合法报告，因此不能说“已经证明不稳定”，只能说旧 raw 无法测量稳定性门槛。
9. Service 机械门禁整改和 19 份总回放已经结束。下一步必须先由用户决定：是先人工阅读已有 19 份内容风险、先基于风险设计 Prompt 改进，还是直接按 I2-D/E 获取完整新 raw 后统一人工审核。任何选择都要先写入权威设计并逐批确认，不能从 Service `19/19` 自动跳到付费运行或 finalize。

提交/拉取保护：提交前应检查 `git status` 和 `git diff`，逐项确认预检、价格、raw、诊断和人工审核辅助材料都被纳入预期提交；不得提交 `.env`、API Key 或本机秘密。拉取后不再因质量证据文件的 LF/CRLF 或字节 hash 差异停止；若证据缺失、JSON 无法解析、`stage/run_id/batch/mode` 身份错误、case 分母/ID 不完整、既有结果被覆盖或 I2 正式路径意外出现，仍必须停止。

## 12. 最近验证基线

- 2026-08-29，`7R5-I2-R6-D：十九份已有响应零调用总回放` 已完成并停止。预检脚本和测试新增行为 v6 的 19 例固定顺序、R1-C/R2-E/R3-D/R4-C/R5-D 只读身份与最近来源追溯、七份报告/九次稳定性缺失回答清单、R06/R14/R15/R16/R19 五项内容风险和独占写入保护。预检专项从修改前 `32 passed`，经过诊断缺失的精确 `33 passed + 4 failed`，写入唯一诊断后转为 `37 passed`；19 份已有响应全部被 Service 接受，R16/S00-3 的旧自由文本来源门禁 `2/2` 消失，没有下一程序错误。独占诊断 `2026-08-29-stage7-7r5i2-r6d-service-v6-full-replay.json` 为 26,250 bytes，不含完整响应、Prompt、Key、堆栈或思维链。R6 直接合同 `173 passed`，扩大回归 `228 passed + 43 subtests passed`，后端全量 `1312 passed + 425 subtests passed`、0 failures；`py_compile` 和精确敏感字段扫描通过。生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、fixture、旧 raw/诊断、PostgreSQL 和 I2 正式路径未改，模型调用/API attempt/token/费用为 0。Service 接受不证明内容正确，全部 19 例仍待人工质量判断；`pricing_gate_allowed=false`，唯一下一步是讨论 Prompt/人工/独立真实复验顺序。
- 2026-08-29，`7R5-I2-R6-C：删除 5.0 自由文本来源扫描` 已完成并停止。assessment reason 与 finding summary 不再调用 `_validate_v5_explicit_sources`，相关评价点/fact/assessment 来源拼接和正则 helper 已删除，没有增加白名单、日期归一化、词典、模糊匹配或 Judge；结构化 evidence/criterion ID/fact key/required 双面说明和明确安全规则保留，旧 1.0—4.0 逻辑未改。报告行为升级为 v6，Prompt 正文/版本仍为 v3，活动质量合同同步。R6-B 直接合同转为 `168 passed`；首次运行的 4 个 R5-D 失败只因旧测试尝试用活动 v6 动态重建历史 v5 结果，现已改为只读封存诊断并新增动态重建拒绝合同。扩大回归 `243 passed + 43 subtests passed`，后端全量 `1307 passed + 425 subtests passed`、0 failures；`py_compile`、静态扫描、`git diff --check`、历史诊断大小、I2 空路径和 Alembic `current=head=d6e8f0a2b434` 通过。Schema/Adapter/API/Model/migration/React、Prompt 正文、fixture、旧 raw/诊断、PostgreSQL 和 `.gitattributes` 未改，真实调用/费用为 0。该结果不能证明 19 份旧响应已完成 v6 回放或内容正确；`pricing_gate_allowed=false`，唯一下一步是等待用户明确确认 R6-D。
- 2026-08-29，`7R5-I2-R6-B：Service v6 职责合同红灯` 已完成并停止。五份允许测试修改前为 `160 passed + 1 warning`；实际只修改三份测试，形成精确 `11 failed + 156 passed + 1 warning`，没有额外失败、skip 或 xfail。11 个红灯为 assessment 数字/英文词/日期、finding 程序 ID/英文词+数字共 5 个通用自由文本样本，两条主解析路径停止调用、旧 helper 删除共 3 个扫描退出合同，以及 Service/Prompt/质量执行合同 3 个行为 v6 元数据。结构化非零分 evidence/零分形状、finding/criterion ID、优势 evidence、无法定位 evidence、隐私泄露、招聘决定、Prompt 注入、required 双面说明、经历 fact key 和重复 JSON key 定向为 `17 passed + 51 deselected + 1 warning`。测试 `py_compile` 与 `git diff --check` 通过；生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、质量脚本/合同、fixture、历史证据、I2 正式路径和 PostgreSQL 未改，真实调用/费用为 0。生产行为仍为 v5；该红灯不能证明 R6-C 已实现或内容正确。`pricing_gate_allowed=false`，唯一下一步是等待用户明确确认 R6-C。
- 2026-08-29，`7R5-I2-R6-A：自由文本来源裁判退出职责文档门禁` 已完成并停止。用户确认不为 R16/S00-3 增加编号白名单、日期归一化或其他场景特例，而让 5.0 Service 整体退出 reason/finding 自由文本数字和英文词来源判断。只读代码核对确认行为 v5 的 `_validate_v5_explicit_sources` 位于 assessment 与 finding 两条主解析路径；第 32I 节已登记确定性结构/evidence/ID/fact/明确安全规则继续保留，同时主动接受 Oracle/99 等疑似自由文本编造不再由 Service 兜底的风险，并固定 R6-B 红灯、R6-C 实现、R6-D 19 份零调用回放顺序。本批只修改两份权威文档，没有修改或执行生产代码、测试、fixture、质量脚本/合同、诊断、结果或 PostgreSQL，没有创建 I2 raw/human/final，没有读取 Key、实例化真实 Adapter、调用 DeepSeek 或产生费用。该结果不能证明 Service v6 已实现或任何报告内容正确；`pricing_gate_allowed=false`，唯一下一步是等待用户明确确认 R6-B。
- 2026-08-29，`7R5-I2-R5-D：十一份旧拒绝零调用总回放` 已完成并停止。固定 11 例和 P00/P04/P06/P07/P09 五份支持计划只读回放，旧五类门禁 11/11 消失；9 份被 Service v5 接受，R16/S00-3 进入程序 ID 数字及合法截止月日期分隔符的下一来源门禁。R06/R15 年限和 R16 推断风险继续保留，11 例全部仍需未来人工质量审核。新增不可覆盖诊断 `v5-quality-results/7r5i2-diagnostics/2026-08-29-stage7-7r5i2-r5d-service-v5-replay.json`，18,833 bytes，不含完整响应、Prompt、Key、堆栈或思维链。预检 `31 passed`、R5 直接相关 `154 passed`、扩大回归 `313 passed + 43 subtests passed`、后端全量 `1299 passed + 425 subtests passed`、0 failures；`py_compile`、诊断身份/字段、既有诊断大小、不可覆盖、I2 空路径、Alembic `current=head=d6e8f0a2b434` 和 `git diff --check` 通过。生产代码、fixture、旧 raw/诊断和 PostgreSQL 未改，真实调用/费用为 0。`pricing_gate_allowed=false`；唯一下一步是先讨论 R16/S00-3，不得直接实现或进入 I2-D/E。
- 2026-08-29，`7R5-I2-R5-C：Service v5 职责收口实现` 已完成并停止。assessment/finding 明确数字和英文词来源扩展到 Resume、当前评价点及合法 fact/calculation note；5.0 主解析停止调用 reason/evidence、overall/evidence 二字词裁判和四个高低分方向词表裁判，旧 1.0—4.0 共用逻辑未改。无来源 Oracle/99、证据、ID、fact key、明确隐私/决定/注入等硬门禁继续保留。报告行为升级为 `lightweight_report_generation_v5`，Prompt 正文/版本仍为 v3，活动质量合同同步 v5；R4-C 动态构建已退休，`--r4c` 只读既有 10,385-byte 诊断且文件未改变。直接合同 `149 passed`，扩大回归 `308 passed + 43 subtests passed`，后端全量 `1294 passed + 425 subtests passed`、0 failures；`py_compile`、静态扫描、`git diff --check`、I2 空路径和 Alembic `current=head=d6e8f0a2b434` 通过。Schema/Adapter/API/Model/migration/React、fixture、旧结果/诊断、PostgreSQL 业务数据和 `.gitattributes` 未改；Key/真实 Adapter/DeepSeek/API attempt/token/费用/正式结果写入为 0。该结果不能证明旧 11 份响应已经回放或内容正确。`pricing_gate_allowed=false`；唯一下一步是等待用户明确确认 R5-D。
- 2026-08-29，`7R5-I2-R5-B：Service v5 新职责合同红灯` 已完成并停止。五份允许测试修改前为 `138 passed + 1 warning`；新增/调整合同后精确为 `13 failed + 136 passed + 1 warning`，没有额外失败、skip 或 xfail。13 个红灯包括 9 个 Service 自然语言职责、3 个报告行为 v5 元数据接线和 1 个 R4-C 动态重建退休合同；无来源英文词/数字、证据定位、明确隐私泄露、重复/未知/不可用 fact key 定向为 `6 passed + 55 deselected + 1 warning`。测试文件 `py_compile`、`git diff --check` 和 I2 raw/human/final 空路径检查通过。生产 Prompt/Schema/Service、质量脚本/合同、fixture、历史结果/诊断、PostgreSQL 和 `.gitattributes` 均未在本批修改；没有读取 Key、实例化真实 Adapter、调用 DeepSeek、产生 API attempt/token/费用或写正式结果。生产报告行为仍为 v4，Prompt 正文/版本仍为 v3；红灯只证明 R5-C 目标被准确捕获，不能证明问题已修复或旧响应内容正确。`pricing_gate_allowed=false`；唯一下一步是等待用户明确确认 R5-C。
- 2026-08-29，`7R5-I2-R5-A：剩余 Service 总盘点与职责文档门禁` 已完成并停止。只读重建当前报告行为 v4 的全部封存去向：13 份有响应报告为 6 接受、7 拒绝，6 份有响应稳定性为 2 接受、4 拒绝，合计 8/19 接受、11/19 拒绝；另有 7 份报告和 9 次稳定性无封存响应。11 份拒绝完整归为数字来源 R04/R17/S04-1/S04-3、英文词来源 R06/R15、综合说明重合 R16/R18、理由/证据重合 S00-1、分数方向关键词 R09/S00-3，并只读核实 ROI、Spring Cloud/Dubbo、0 到 50 万及年限数字的评价点/fact 来源。第 32H 节已登记 Service 硬规则、自然语言职责边界和 R5-B—D 独立实施顺序；本批只修改两份权威文档，没有修改 Prompt/Schema/Service、测试、fixture、质量脚本、诊断、结果或 PostgreSQL，没有创建 I2 raw/human/final，没有读取 Key、实例化 Adapter、调用 DeepSeek、产生 API attempt/token/费用。当前生产报告行为仍为 v4，Prompt 仍为 v3；该结果不能证明 Service v5 已实现或 11 份内容正确。`pricing_gate_allowed=false`；唯一下一步是等待用户明确确认 R5-B。
- 2026-08-29，`7R5-I2-R4-C：R07/R00/S00-2 零调用回放` 已完成并停止。回放只读取封存 raw、R2-E/R3-D 来源诊断及 P00/P07 支持计划，固定报告行为 `lightweight_report_generation_v4`；旧“5.0 AI 初筛输出包含不得参与评价的敏感个人属性”门禁 `3/3` 消失，R07、R00、S00-2 当前均被 Service 接受，没有下一程序错误。三例全部标记为未来人工质量审核，Service 接受没有被写成内容正确、敏感属性语义安全或真实质量通过。新增独占诊断 `v5-quality-results/7r5i2-diagnostics/2026-08-29-stage7-7r5i2-r4c-sensitive-replay.json`，大小 10,385 bytes，不含完整原始响应、Key、Prompt、堆栈或思维链。预检专项由 `21 passed` 增至 `25 passed`；R4 直接相关 `118 passed`，扩大阶段 7 回归 `170 passed + 43 subtests passed`，后端全量 `1283 passed + 425 subtests passed`、0 failures；`py_compile`、诊断字段扫描、静态检查和 `git diff --check` 通过。生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、fixture、旧诊断和 PostgreSQL 均未改；I2 raw/human/final 与 `.gitattributes` 不存在，Key/真实 Adapter/DeepSeek/API attempt/token/费用/PostgreSQL/正式结果写入均为 0。`pricing_gate_allowed=false`；唯一下一步是先讨论 R06/R15/R16/R18 的 Resume 不支持普通事实门禁，不得直接整改。
- 2026-08-29，第二次修正后的 `7R5-I2-R4-B：缩小 5.0 Service 敏感扫描职责` 已完成并停止。5.0 Service 不再扫描整份 JSON 或用受保护属性通用关键词裁决自然语言，只提取 HR 可见文字并检查明确隐私标识、邮箱、电话和身份证；程序 ID、结构键和合法 fact key 不参与，明确隐私泄露、招聘决定、Prompt 注入及事实/证据/结构门禁继续保留，旧 1.0—4.0 行为不变。报告行为版本递增为 `lightweight_report_generation_v4`，Prompt 正文、Schema、Adapter、API、Model、migration、React 和 PostgreSQL 均未改。R1-C、R2-E、R3-D 已改为只读取并验证各自既有诊断，三个动态构建入口均会直接拒绝；只读命令成功，历史文件未覆盖。R4-B 相关为 `114 passed`，扩大阶段 7 回归为 `166 passed + 43 subtests passed`，后端全量为 `1279 passed + 425 subtests passed`、0 failures；`py_compile`、静态扫描和 `git diff --check` 通过。I2 raw/human/final 与 `.gitattributes` 均不存在；未读取 Key、实例化真实 Adapter、调用 DeepSeek、产生 API attempt/token/费用或写 PostgreSQL。结果证明误报职责和历史回放隔离已修复，不能证明 R07/R00/S00-2 当前整份报告通过或内容正确。`pricing_gate_allowed=false`；唯一下一步是等待用户确认 R4-C。
- 2026-08-29，`7R5-I2-R4-A：敏感属性职责红灯合同` 已完成并停止。三份允许测试修改前为 `89 passed + 1 warning`，新增合同后为 `7 failed + 86 passed + 1 warning`；红灯固定为“用户增长相关”子串误报、合法 fact key 数字误报、受保护属性语义仍由 Service 关键词裁决、整份 `model_dump_json()` 扫描，以及 Service/Prompt/质量合同三个报告行为 v4 接线。明确邮箱泄露、招聘决定、Prompt 注入、重复/不存在 fact key 定向为 `5 passed + 1 warning`；测试 `py_compile` 和 `git diff --check` 通过。生产代码、质量脚本/合同、fixture、历史证据、数据库和正式路径均未改，真实调用与费用为 0。该红灯不能证明问题已修复；`pricing_gate_allowed=false`，唯一下一步是等待用户确认 R4-B。
- 2026-08-29，`7R5-I2-R3-D：六个旧拒绝零调用回放` 已完成并停止。只读取封存 raw 与 I2-C/R1-C/R2-E 三层结构证据，固定回放 R07/R10/R16/R18/R19/S04-2 及 P00/P04/P05/P06/P07 五份必要支持计划；旧“无直接证据结论只能表达缺口、风险或待核实信息”门禁 6/6 消失。R10/R19/S04-2 当前被 Service 接受；R07 转入敏感属性门禁；R16/R18 转入综合说明含 Resume 不支持事实门禁。六例均保留未来人工审核，Service 接受没有被写成内容正确。新增独占诊断 `v5-quality-results/7r5i2-diagnostics/2026-08-29-stage7-7r5i2-r3d-no-evidence-replay.json`，大小 13,452 bytes，完整原始响应字段为 0。预检专项 `19 passed`，六份直接相关回归 `136 passed + 20 subtests passed`；第一次全量因 Docker/PostgreSQL 在运行期间非正常重启而为 `1259 passed + 14 connection failures`，容器自动恢复后失败两份合同 `25 passed`、数据库 `current=head=d6e8f0a2b434` 且 `alembic check` 无差异，稳定全量重跑为 `1273 passed + 425 subtests passed`、0 failures。`py_compile`、JSON 字段扫描和 `git diff --check` 通过；生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、fixture、旧证据和 PostgreSQL 业务数据未改，I2 raw/human/final 未创建，Key/Adapter/DeepSeek/API attempt/token/费用新增为 0。`pricing_gate_allowed=false`；唯一下一步是先讨论 R07 及同类 R00/S00-2 的敏感属性门禁，不得直接整改。
- 2026-08-29，`7R5-HASH-B：移除文件字节 hash 阻塞并保留结构保护` 已完成并停止。旧 4.0/当前 5.0 质量合同、运行器和 I2 预检不再以历史结果、raw、preflight/诊断或后续正式结果的整文件 SHA 决定通过；改为校验文件存在/可读、JSON 身份、固定 case 分母与唯一 ID、来源关系、write-once 和 I2 生命周期。CRLF 副本通过，损坏 JSON、错误 stage 和缺少分母仍失败；规范化 fixture、业务输入和数据库备份指纹保留。相关四份测试 `78 passed + 1 warning`，后端全量 `1269 passed + 425 subtests passed + 2 warnings`，0 failures；`py_compile`、删除门禁静态扫描和 `git diff --check` 通过。全量回归最初因本机数据库缺少 5.0 列产生同源 48 个失败；经用户单独明确授权、并在复核 87,224 bytes 备份及 SHA-256 后，已执行 `b4c6d8e0f212 → c5d7e9f1a323 → d6e8f0a2b434`，最终 `current=head` 且 `alembic check` 无差异。历史证据/诊断、fixture、产品 Prompt/Schema/Service/API/Model/migration/React、`.gitattributes` 和 Git 配置未改，I2 raw/human/final 未创建；Key/真实 Adapter/DeepSeek/API attempt/token/费用新增为 0。该结果不能证明六例内容正确或真实质量通过；`pricing_gate_allowed=false`，唯一下一步是等待用户按新合同重新确认 `7R5-I2-R3-D`。
- 2026-08-28，`7R5-HASH-A：文件 hash 职责与实施顺序文档门禁` 已完成并停止。触发原因是跨电脑拉取后 Windows LF/CRLF 转换使 `2026-08-20-stage7-quality-acceptance-results.json` 的字节 SHA 与旧常量不同，I2 专项基线为 `13 failed + 1 passed`，13 个失败均在同一历史证据 hash 前置检查停止，R3-D 业务回放尚未运行；这不证明证据内容被修改，也不证明 R3-D 失败。新合同取消旧 4.0/当前 5.0 质量证据文件 SHA 的阻塞职责，保留 Git 差异、文件存在、JSON 身份、case 分母/ID、来源关系、生命周期和不可覆盖保护；规范化 fixture 指纹、业务输入指纹和数据库备份校验不在取消范围。本批只修改两份权威文档，`git diff --check` 通过，`.gitattributes` 和 I2 raw/human/final 均不存在；代码、测试、证据、Git 配置和数据库未改，未执行 R3-D、读取 Key 或调用 DeepSeek。`pricing_gate_allowed=false`；唯一下一步是等待用户确认 `7R5-HASH-B`，R3-D 必须在 HASH-B 完成后重新确认。
- 2026-08-28，完成跨电脑交接范围纠正并停止。重新以受保护 I2-C preflight 为总账，确认已知无 evidence 关键词旧拒绝的完整分母为 R10（I2-C）、R16（R1-C）和 R07/R18/R19/S04-2（R2-E），因此 R3-D 从四例更正为六例；同时补回待讨论的 R04/S04-1 数字事实、R06 普通事实、R14 五分区不完整、7 份报告/9 次稳定性无旧响应和稳定性不可计算状态。本次只修改 5.0 权威设计与 `PROJECT_STATE.md`；没有修改代码、测试、Prompt、Schema、Service、质量脚本或结果，没有执行 R3-D、读取 Key、调用 DeepSeek、写 PostgreSQL 或产生费用。原四例版确认不得沿用，`pricing_gate_allowed=false`；唯一下一步是等待用户在六例范围下确认 R3-D。
- 2026-08-28，`7R5-I2-R3-C：删除无证据结论关键词裁判` 已完成并停止。5.0 报告 Service 删除 `_NO_EVIDENCE_FINDING_TERMS` 和对应固定词拒绝分支，保留合法评价点关联、strengths/非零分证据、证据定位、事实/数字、时间 fact key、结构和安全门禁；报告行为版本递增为 `lightweight_report_generation_v3`，Prompt 正文/Prompt v3/Schema 5.0 不变。R3-B 8 个红灯全部转绿，五份直接相关 `126 passed`，后端全量 `1268 passed + 425 subtests passed`；`py_compile`、静态扫描、`git diff --check`、受保护证据 hash 和 I2 空路径检查通过。测试态旧响应显示 R19/S04-2 当前 Service 接受，R07/R18/R16 进入其他门禁；没有创建诊断或追认质量。Key/Adapter/DeepSeek/API attempt/token/费用/正式结果/PostgreSQL 业务写入新增为 0。该结果不能证明真实模型质量；`pricing_gate_allowed=false`，唯一下一步是等待用户确认 R3-D。
- 2026-08-28，`7R5-I2-R3-B：Service 新职责合同红灯` 已完成并停止。五份相关测试修改前为 `118 passed`，新增合同后为 `8 failed + 118 passed`：四个正常措辞误拒绝、一个关键词表静态删除、两个行为版本 v3 元数据和一个质量执行合同元数据红灯，全部只指向 R3-C 尚未实现的职责。合法评价点关联、strengths/非零分证据、证据定位、事实/非时间数字、敏感属性、自动招聘决定、Prompt 注入、内容错误不重试和 13 份历史 hash 定向 `13 passed`；五份测试 `py_compile`、`git diff --check` 通过。生产代码、配置、fixture、质量脚本、结果和 PostgreSQL 未改，Key/Adapter/DeepSeek/API attempt/token/费用新增为 0。该结果不能证明修复或真实质量；`pricing_gate_allowed=false`，唯一下一步是等待用户确认 R3-C。
- 2026-08-28，`7R5-I2-R3-A：无证据结论职责与实施顺序文档门禁` 已完成并停止。用户确认取消 5.0 报告 Service 对无 evidence gap/risk/missing 的关键词同义词裁判，不取消整个 Service；合法评价点关联、strengths/非零分证据、证据定位、事实/非时间数字、时间 fact key、ID、结构和安全硬门禁继续保留。权威设计当时初始登记 R3-B 合同红灯、R3-C 最小删除与行为版本 v3、R3-D R07/R18/R19/S04-2 四例零调用回放；后续交接复核已补入 R10/R16，当前权威范围为六例。本批只修改权威设计和 `PROJECT_STATE.md`；生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、配置、测试、fixture、质量脚本、结果和 PostgreSQL 均未改，真实 DeepSeek 调用/API attempt/token/费用新增为 0。该历史结果不能证明 Service 已修复、相关旧响应内容正确或真实质量通过；`pricing_gate_allowed=false`，当时唯一下一步是等待用户确认 R3-B。
- 2026-08-28，`7R5-I2-R2-E：十二个旧年限拒绝零调用回放` 已完成并触发停止门禁。脚本同时以受保护 I2-C preflight 和 R1-C 诊断建立 12 个旧年限拒绝基线，避免把 R00/S00-1—3 的先前数量失败错记为 preflight 年限失败。12/12 不再命中旧年限门禁；R05 完整通过当前 Service，11 份进入其他门禁：无直接证据 4、敏感属性 2、Resume 不支持的非时间数值 2、普通事实不支持 1、理由/证据联系不足 1、高分/无证据方向矛盾 1；R15/R19 仍等待人工质量审核。新增隔离诊断 `v5-quality-results/7r5i2-diagnostics/2026-08-28-stage7-7r5i2-r2e-duration-replay.json`，大小 21,567 bytes、SHA-256 `dff95720113a9eaf7cfc115a1a29fd89482a57b009e8dcaa66b85c9c0d8d10ac`，不含完整原始响应。专项 `14 passed`、相关回归 `118 passed`、后端全量 `1260 passed + 425 subtests passed`；Key/Adapter/DeepSeek/API attempt/token/费用/PostgreSQL/正式结果写入为 0，诊断写入 1。`pricing_gate_allowed=false`，唯一下一步是讨论 4 个无直接证据结论拒绝，不得直接实现或进入 I2-D/E。
- 2026-08-28，`7R5-I2-R2-D：报告 Prompt v3 年限约束` 已完成并停止。报告 Prompt 升级为 `screening_evaluation_lightweight_v3`，明确使用可用后端月份事实，区分日期/时长、JD 门槛/候选人实际、总工作/岗位相关、单段/合计，统一把门槛换算为月份，禁止重叠累计和把全部日历跨度默认视为岗位相关；证据不足时必须写“无法确认达到”，不得写成“未达到”，输出前静默核对门槛方向且不输出草稿或思维链。行为版本仍为 `lightweight_report_generation_v2`，Schema 仍为 `5.0`。配置、`.env.example`、活动 I2 质量合同和元数据测试同步为 v3；Service、Schema、Adapter、API、Model、migration、React、fixture 和结果未改。定向为 `93 passed + 16 subtests passed`，后端全量为 `1255 passed + 425 subtests passed`；真实调用/API attempt/token/费用/PostgreSQL/正式结果写入新增为 0。该结果不能证明真实模型必然遵守 Prompt 或质量通过；`pricing_gate_allowed=false`，唯一下一步是等待用户确认 R2-E。
- 2026-08-28，`7R5-I2-R2-C：删除 Service 自然语言年限判断` 已完成并停止。5.0 报告 Service 不再扫描报告文字判断日期、时长、约数、JD 门槛或满足方向；后端月份事实、fact key 唯一/存在/可用、非时间评价项误引、引用后的计算说明、证据、非时间数字、结构和安全门禁继续保留，旧 4.0 共用年限规则未删除。报告行为版本从 `lightweight_report_generation_v1` 递增为 `lightweight_report_generation_v2`，Prompt 正文和 Prompt 版本仍为 v2。R2-B 的 5 个 Service 红灯全部转绿；定向为 `52 passed + 8 expected failed + 1 warning`，8 个失败仅为 R2-D 的 Prompt v3 版本和 7 条指令；排除它们后的后端全量为 `1247 passed + 425 subtests passed + 8 deselected`。未读取 Key、调用 DeepSeek、产生 API attempt/token/费用、写 PostgreSQL 或正式结果。该结果不能证明 DeepSeek 年限结论正确、R15/R19 正确或真实质量通过；`pricing_gate_allowed=false`，唯一下一步是等待用户确认 R2-D。
- 2026-08-28，`7R5-I2-R2-B：Service/Prompt 新职责合同红灯` 已完成并停止。本批只修改报告 Service 与 Prompt 两份测试和两份状态文档。修改前两份测试为 `42 passed + 1 warning`；新增合同后为 `13 failed + 45 passed + 1 warning`，其中 5 个 Service 红灯分别锁定日历日期片段、JD 年限门槛、单段/合计月份、精确月份对应约数和综合报告年限文字，8 个 Prompt 红灯锁定 `screening_evaluation_lightweight_v3` 及 7 条年限比较/不确定性指令。新旧保护定向为 `15 passed + 25 deselected + 1 warning`，覆盖 fact key、证据、非时间数字、ID、安全、方向、重复 JSON 和内容不重试；两份测试 `py_compile` 通过。生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、配置、fixture、质量脚本、结果和 PostgreSQL 均未改，真实 DeepSeek 调用/API attempt/token/费用新增为 0。红灯只定位 R2-C/D 责任，不能证明修复或真实质量；`pricing_gate_allowed=false`，唯一下一步是等待用户确认 R2-C。
- 2026-08-28，`7R5-I2-R2-A：年限职责与实施顺序文档门禁` 已完成并停止。用户确认保留后端按 `Application.applied_at` 生成的 `experience_period_facts`、固定月份/上下界、fact key 和指纹；取消报告 Service 对自然语言日期、年限、JD 门槛、单段/合计、约数和达到方向的机械裁判；DeepSeek 通过未来 Prompt v3 使用月份事实，HR 与真实质量验收承担最终内容判断。权威设计登记 R2-B 合同红灯、R2-C Service 最小删除、R2-D Prompt v3、R2-E 十二个旧拒绝零调用回放，每批独立确认和停止。R15/R19 的模型风险继续保留，不能因未来 Service 放行追认为正确。本批只修改权威设计与 `PROJECT_STATE.md`；生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、配置、测试、fixture、质量脚本、结果和 PostgreSQL 均未改，真实 DeepSeek 调用/API attempt/token/费用新增为 0。`pricing_gate_allowed=false`；唯一下一步是等待用户明确确认 R2-B。
- 2026-08-28，`7R5-I2-R1-C：六个旧结构失败零调用回放` 已完成并停止。只回放 R00、R09、R16、S00-1—3 六个报告响应及 P00/P06/P09 三个必要支持计划；6/6 被当前 Schema 接受，列表最大 7—12 条，数量门禁已经解决；0/6 完整通过，R00/S00-1—3 为年限时间事实冲突，R09 为高分与无证据方向矛盾，R16 为无直接证据结论。新增隔离、独占写入诊断 `v5-quality-results/7r5i2-diagnostics/2026-08-28-stage7-7r5i2-r1c-structure-replay.json`，大小 16,101 bytes、SHA-256 `f89426b3aa03b005cb533d6305590d17751dbada076dda526295b8a31b9ad3f3`；不复制原始响应、Prompt、Key、堆栈或思维链。专项 `9 passed`、相关合同 `97 passed`、后端全量 `1239 passed + 425 subtests passed`，`py_compile`、`git diff --check`、13 份历史 hash 保护通过。旧 raw/preflight hash 不变，I2 raw/human/final 仍空；Key/Adapter/DeepSeek 调用/API attempt/token/费用/PostgreSQL/正式结果写入为 0，诊断写入 1。`pricing_gate_allowed=false`；下一步只讨论年限冲突，不得直接实施。
- 2026-08-28，`7R5-I2-R1-B：Prompt v2 与 Schema 容忍实现` 已完成并停止。`backend/app/prompts/screening_evaluation.py` 升级为 `screening_evaluation_lightweight_v2` 并要求五类辅助列表通常只保留 1—5 条最高价值、按影响选择、合并重复、不得穷举、每类最多 20 条；`backend/app/schemas/screening_evaluation.py` 让 AI 输出和持久化报告共用 20 条技术上限，6—20 条完整保留、21 条拒绝，Schema 版本仍为 5.0。配置默认值、`.env.example`、质量合同和相关元数据测试同步为 v2；没有修改报告事实/年限/证据/安全 Service、Adapter、API、Model、migration、React 或 fixture。R1-A 为 `66 passed`，扩大回归为 `192 passed + 59 subtests passed`，后端全量为 `1234 passed + 425 subtests passed`；`py_compile`、`git diff --check`、13 份历史 hash 保护通过。旧 raw/preflight 大小和 SHA-256 不变，I2 raw/human/final 仍空；未读取 Key、调用 DeepSeek、产生 API attempt/token/费用或写入正式业务结果。该结果证明离线数量合同修复，不能证明六个旧响应已完整通过或真实模型质量；唯一下一步是等待用户确认 R1-C。
- 2026-08-28，`7R5-I2-R1-A：辅助列表数量合同红灯` 已完成并停止。本批只修改 `backend/tests/prompts/test_screening_evaluation_v5_prompt.py`、`backend/tests/services/test_screening_evaluation_v5_service.py` 和 `backend/tests/test_stage7_7r5_quality_runner.py`：固定报告 Prompt v2 的“通常 1—5、最高价值、合并重复、不穷举、最多 20”要求；固定 HR 问题 6/7/10/20、gaps/missing 12 和五类列表 20 条均应合法且原样保留；固定任一列表 21 条仍拒绝。修改前相关基线为 `46 passed + 1 warning`，新合同结果为 `17 failed + 49 passed + 1 warning`，17 个失败均是下一批尚未实现的职责；21 条上限、评价项 ID、证据/数字、安全、敏感属性、自动招聘决定、Prompt 注入、重复 JSON 键、内容错误不重试和 13 份历史 hash 定向为 `19 passed + 1 warning`。三份测试 `py_compile`、`git diff --check` 通过。旧 raw/preflight 大小和 SHA-256 不变，I2 raw/human/final 仍空；生产 Prompt/Schema/Service/Adapter、fixture、结果和 PostgreSQL 未改，Key/真实调用/API attempt/token/费用新增为 0。该结果只能证明新业务规则已有精确红灯，不能证明问题已修复；唯一下一步是等待用户确认 R1-B。
- 2026-08-28，只完成 I2 报告整改问题 1 的业务与实施顺序文档门禁。用户确认 DeepSeek 可以生成超过 5 条的辅助信息，但必须优先最重要、最需要 HR 核实且互不重复的部分，不得全盘穷举。第 32C 节据此固定：通常 1—5 条是 Prompt 质量推荐值，五类辅助列表 6—20 条 Schema 合法且不得静默截断，21 条为技术安全硬失败；评价项、分数、证据、数字/年限、安全和敏感属性门禁不变。实施顺序为 R1-A 测试红灯、R1-B `screening_evaluation_lightweight_v2` 与 Schema 容忍实现、R1-C 六个旧结构响应零调用回放，每批单独确认和停止。本批只修改权威设计与 `PROJECT_STATE.md`，没有修改生产 Prompt/Schema/Service/Adapter/fixture、测试或结果；没有读取 Key、调用模型、写 PostgreSQL 或产生费用。唯一下一步是等待用户确认 R1-A。
- 2026-08-28，`7R5-I2-C：旧 raw 全类别零调用预检` 已完成并触发停止门禁。新增只读预检脚本/测试，直接用当前解析/校验函数重放封存 raw 的 29 个已有模型响应；不实例化 Adapter、不读 Key、不联网、不写 PostgreSQL。计划 10/10 当前通过；报告 13 个有响应 case 为 1 通过/12 拒绝、7 个无响应不可回放；稳定性 6 个有响应 case 全部拒绝、9 个无响应不可回放。18 个拒绝分为严格结构 6、Resume 不支持的数字事实 2、年限时间事实冲突 8、普通事实不受支持 1、无直接证据结论 1；无法自动判断模型错误与 Service 误拒绝，`pricing_gate_allowed=false`，不得进入 I2-D/E。唯一 preflight 大小 33,887 bytes，SHA-256 `185b42d7c55d6654cedfa251f340d89469470800336aa17be192ae3d1c28b6b2`；不复制原始响应，仅记录 hash/长度和安全诊断。专项 `50 passed`，后端全量 `1214 passed + 425 subtests passed`，`py_compile`、`git diff --check` 通过。旧 raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`，13 份历史 hash 不变；I2 raw/human/final/价格路径仍空。新增真实调用/API attempt/token/费用均为 0，正式写入只有 preflight 1 份。下一步只能先讨论并登记报告 Service/内容诊断批次。
- 2026-08-28，`7R5-I2-B：独立路径与生命周期实现` 已完成并停止。`scripts/stage7_7r5_quality_contract.py` 登记封存 run `7R5-I`、活动 run `7R5-I2`、四条新证据路径和五态生命周期，固定旧 raw SHA-256，允许已登记旧 raw/helper 合法共存，拒绝未知 JSON、路径重叠、状态跳跃、未登记 run、旧入口和跨轮补写/覆盖；write-once 只允许按 preflight/raw/human/final 顺序写下一条路径。`scripts/run_stage7_7r5_quality.py` 的 dry-run/Fake/real 使用显式 I2 上下文，执行合同新增 Service 行为版本 v3。质量合同/静态扫描为 `46 passed`，与计划 Service/HR 编辑合跑 `103 passed`，后端全量为 `1210 passed + 425 subtests passed`；dry-run 为 `i2_not_started`、0 调用、0 写入、不读 Key、不加载 Adapter，`py_compile` 和 `git diff --check` 通过。旧 raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`；原 human/final、I2 preflight/raw/human/final/价格路径仍空，13 份历史 hash 不变。产品前端/API/Schema/Service/Model/PostgreSQL、Prompt、Adapter、fixture 和结果文件未改；真实 DeepSeek 调用/API attempt/token/费用新增均为 0。唯一下一步是等待用户确认 I2-C。
- 2026-08-28，`7R5-I2-A：生命周期合同红灯` 已完成并停止。修改前复现 6/6 旧失败，均因旧 raw/人工辅助目录合法存在但旧测试要求结果路径或整个目录为空。只修改 `backend/tests/test_stage7_7r5_quality_runner.py`、`backend/tests/test_stage7_v5_static_scan_contract.py` 和状态文档：删除空目录假设，新增 I2 run identity/四条证据路径/五态生命周期、旧 raw 封存 hash、未知 JSON 拒绝、helper 不得冒充正式人工审计、跨轮不可覆盖、Service 行为 v3，以及 dry-run/Fake/real 显式 I2 上下文合同。两份测试当前为 `35 passed + 10 failed`，10 个失败分别指向 I2-B 尚未实现的合同/运行器职责，没有删除断言或标记 xfail；既有 fixture/hash/写入拒绝/价格/费用守卫定向 `6 passed`，两份测试 `py_compile` 和 `git diff --check` 通过。旧 raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`，I2 preflight/raw/human/final/价格五条路径仍不存在，13 份历史 hash 不变；质量合同、运行器、产品代码、fixture、数据库和结果文件未改，API Key/Adapter/DeepSeek 调用/API attempt/token/费用新增均为 0。用户提出未来 DeepSeek 调用“无上限”，但本批未把它当成金额授权；I2-D 仍须查当时官方价格并取得明确美元上限，完成后另行确认 I2-E。唯一下一步是等待用户确认 I2-B。
- 2026-08-28，只完成整改后独立真实复验 `7R5-I2` 的权威文档门禁。第 32B 节固定旧 I raw/hash 与原 human/final 空路径，登记 I2 preflight/raw/human/final/价格五条独立路径和五态生命周期；冻结原 10/20/5×3 样本、模型/Prompt/Schema/行为 v3、45/90 调用、内容 0 重试、金额守卫和第 20.1 节门槛。顺序固定为 I2-A 生命周期红灯、I2-B 运行器实现、I2-C 旧 raw 全类别零调用预检、I2-D 官方价格/金额门禁、I2-E 唯一真实 raw、I2-F 用户人工审计、I2-G final；C 发现报告 Service/内容/人工判断问题必须先停止，不能直接花钱。本批只修改 5.0 权威设计和 `PROJECT_STATE.md`；未修改测试、质量合同/运行器、产品代码、fixture 或结果，未读取 Key、调用模型或产生费用。唯一下一步是等待用户确认 I2-A。
- 2026-08-28，7R5-IR-B“Service 最小整改与零调用回放”已完成并停止。Service 行为合同升级到 `lightweight_plan_generation_v3`；移除全量英文 token 逐字包含硬拒绝，统一技术词标点归一，并把普通缩写、符号和相关非排他举例交给粗粒度主题锚点与 HR 确认；新增量化门槛、学历/学位/证书/认证、排他措辞、伪造来源和安全越界仍硬失败。IR-A 新合同 `11 passed`，生成/编辑完整合同 `57 passed`，原 7R5-I P00—P09 raw response 直接解析回放 `10/10`；未调用 Adapter。扩大回归为 `140 passed + 3 subtests passed + 6 failed`；不排除测试的后端全量为 `1200 passed + 425 subtests passed + 6 failed`，排除六个已确认 post-raw 生命周期旧断言后为 `1200 passed + 425 subtests passed`。六个失败只因当前合法 raw/人工辅助目录存在，而测试仍要求正式路径或整个目录为空；删除受保护证据不是修复，本批也未修改质量运行器。`py_compile`、其余静态合同和 `git diff --check` 通过。raw 仍为 344,355 bytes、SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`，human/final 仍空，13 份历史 hash 全部不变；真实 DeepSeek 调用/API attempt/token/费用新增为 0，没有持久化正式业务数据。该结果证明计划 Service 误拒绝已修复，不能追认旧 raw 通过或证明报告质量；下一步只能先设计独立真实复验及测试生命周期调整。
- 2026-08-28，7R5-IR-A“支持性校验合同红灯”已完成并停止。修改前相关两份合同为 `46 passed`；新增 11 个参数用例后，正常表达定向结果为 5 个预期失败：`Node.js`、`UX/UI`、`PRD`、`Hive/Presto` 四个生成路径和 `Kubernetes/K8s` HR 编辑路径，均落在当前 `JOB_EVALUATION_PLAN_V5_UNSUPPORTED_CRITERION`；新增年限、学历、学位、证书、认证和排他技术 6 个保护用例全部通过。来源/安全/>30/非法 JSON/内容不重试定向为 `14 passed`；排除新增合同后的既有回归仍为 `46 passed`；两份测试 `py_compile` 和 `git diff --check` 通过。API 编辑用例的临时测试事务已回滚，没有持久化正式业务数据；生产 Prompt/Schema/Adapter/Service/API/Model/migration/React、冻结样本、质量运行器和结果文件均未修改，真实 DeepSeek 调用/API attempt/token/费用新增为 0。该红灯证明 IR-B 的责任位于计划 Service 支持性检查，不能证明修复已完成；唯一下一步是等待用户确认 IR-B。
- 2026-08-28，用户在完成 10 份计划引导式人工审核后，明确暂停 7R5-I 后续报告/稳定性审核，先解决 `JOB_EVALUATION_PLAN_V5_UNSUPPORTED_CRITERION` 的 Service 误拒绝。只读同规则回放确认 P01 `Node.js`、P02 `Hive/Presto` 相关举例、P03 `PRD` 和 P08 `UX/UI` 分别是四份计划的首个拒绝点；四例此前均已通过 JSON/Schema、原文来源定位和安全检查。用户确认普通缩写、符号、同义表达和非排他举例可以进入 HR 待确认草稿，但不得变成新增硬门槛。该文档门禁批次只修改 5.0 权威设计和 `PROJECT_STATE.md`，登记 `7R5-IR-A` 测试红灯、`7R5-IR-B` Service 最小整改与零调用 raw 回放顺序；当时未修改测试或生产 Prompt/Schema/Adapter/Service/API/Model/migration/React/数据库，未读取 API Key、未调用 DeepSeek、未创建 human/final、未重算或覆盖 raw；其停止点随后由上方 IR-A 完成记录接续。
- 2026-08-28，7R5-I 唯一真实 raw 已在 USD 10 上限下执行并停止。官方价格查询时间 `2026-08-28T09:08:45.432+08:00`，当时为 peak，单价 `$0.014/$0.44/$1.32`（cache-hit input/cache-miss input/output，USD/1M tokens）；独立快照 24 小时有效。Key 前置门禁为 H 专项 `20 passed`、dry-run `0/0/无 Adapter/不读 Key`、fixture/模型/Prompt/Schema/参数/`45/90` 预算未漂移、三个正式路径全空、13 份历史 hash 不变、`git diff --check` 通过。实际 29 次业务调用/API attempt、0 技术重试；计划 6/10 合法，报告 1/20 合法且完整五分区 0/20，稳定性合法运行 0/15；其余为 4 份计划内容失败、18 次报告内容失败和 16 个上游阻塞，均无内容重试或补跑。input/output token `120,360/48,425`；cache hit `15,360`、保守 cache miss `105,000`；估算 `$0.11033604`，剩余 `$9.88966396`。raw 文件大小 `344,355` bytes，SHA-256 `de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`；human/final 路径仍空，raw 的质量结论仍为 null，唯一下一步是等待用户人工审阅，不得自动 finalize、补跑、整改或进入 7R5-J。
- 2026-08-27 至 2026-08-28，7R5-H“零调用质量运行器与非付费预检”已完成并停止。新增 `scripts/stage7_7r5_quality_contract.py`、`scripts/run_stage7_7r5_quality.py`、`backend/tests/test_stage7_7r5_quality_runner.py` 和非授权价格快照；冻结 10 JD、20 对、5×3、5 组独立样本/标签 hash、13 份历史结果 hash、三个不可覆盖新结果路径、45 次业务调用/90 次 API attempt、正常/重试输出 token 上界 500,000/1,000,000、内容错误 0 重试、逐 attempt 原始响应/token/cache/费用审计、失败 attempt 保守费用预留和人工审计后二次 final gate。修改前 4.0 基线为 42 passed；H 专项 20 passed；真实 PostgreSQL Fake API/migration/H 合跑 23 passed；后端全量 1195 passed、425 subtests passed、0 failures；前端全部 20 组 Node、TypeScript strict、Vite build（3121 modules）通过；真实 PostgreSQL `d6 → c5 → d6` 后 `current=head`、`alembic check` 通过且 8 张核心表均从 0 恢复到 0；`py_compile`、`git diff --check`、dry-run、Fake normal/failure、正式结果不存在和历史 hash 均通过。本机 HTTP fixture 的根页/5.0 plan/5.0 report 返回正常；Codex 应用内浏览器当时两次发现均为空，没有自动交互/控制台/网络日志，但用户于 2026-08-28 明确确认亲自完成浏览器手工测试且验收成功，本批据此接受浏览器非模型路径通过，不将其伪写为自动浏览器证据。2026-08-28 08:35（北京时间）重新查询 DeepSeek 官方页，当时属于 off-peak，`deepseek-v4-flash` off_peak/peak 单价仍为 `$0.007/$0.22/$0.66` 与 `$0.014/$0.44/$1.32`（cache-hit input/cache-miss input/output，USD/1M tokens）；快照仅 24 小时有效。开发中第一次 Fake 调试在离线 Settings 修复前可能加载过 `.env` 配置字符串，但没有输出秘密、实例化真实 Adapter、联网或产生费用；最终 Fake/dry-run 已显式 `_env_file=None`、空 Key，并由测试锁死。真实 DeepSeek 调用和费用仍为 0；唯一下一步是等待用户确认 7R5-I 美元金额上限或明确不设上限。
- 2026-08-27 7R5-G“React 评价清单与初筛报告”已完成并停止。阶段 7 TypeScript/集中 Service 已接入 5.0 清单草稿保存、乐观并发、确认/分叉、计划/报告历史、强制确认重评和五人批量逐项结果；计划抽屉支持编辑、新增、删除、合并、来源/原文/warning、未保存禁止确认和确认后只读；报告视图展示 AI 直接总分、逐项 0—10、JD/Resume 证据、0 分语义、优势/差距/风险/缺失/HR 问题及审计，旧 1.0—4.0 只读兼容。修改前 19 组前端 Node 基线与生产构建通过；修改后 20 组前端 Node 测试全部通过，`npm run build` 完成 TypeScript strict 与 Vite production build（3121 modules）；受影响后端回归为 61 passed、17 subtests passed。静态扫描未发现生产目录裸 `fetch`、`any` 或危险 HTML，`git diff --check` 通过。Fake 浏览器在 1440×1000 验证待确认编辑、HR 新增保存（edit version 3→4）、编辑中禁止确认、确认后只读/新版本入口、完整 5.0 报告、0 分语义、旧 4.0 历史报告、五人上限、4 排队+1 失败、AI 运行中决策禁用和关闭抽屉焦点恢复；390×844 下抽屉宽 390、无横向溢出，当前页面控制台无新错误。浏览器网络仅访问 `127.0.0.1` Fake API，真实 DeepSeek/API Key/费用均为 0。该结果证明 Fake 前端合同、交互和响应式边界，不能证明真实模型质量、真实 PostgreSQL/API 完整链路或最终真实浏览器验收；唯一下一步是等待用户确认 7R5-H。
- 2026-08-27 7R5-F“单人、小批量、状态与决策接线”已完成并停止。5.0 ready gate 已接入 `ScreeningRun`；单人/批量重评强制 `confirmed=true`，批量上限 5 并返回逐人部分失败；运行和报告按 Application 分别由部分唯一索引保护唯一非终态与唯一 current。成功重评新增 current 并冻结旧成功历史，失败/迟到/提交异常保留旧 current；旧 1.0—4.0 只读且不再驱动新评分。AI 成功或失败只把未决 `applied` 推进 `hr_review`，不覆盖 HR 决策；`StageHistory.report_id` 保存当时报告关联。revision `d6e8f0a2b434` 已完成真实 PostgreSQL `c5 → d6 → c5 → d6`，最终 `current=head` 且 `alembic check` 无差异。修改前直接相关基线为 182 passed、12 xfailed、36 subtests passed；7R5-F 核心专项为 181 passed、54 subtests passed；后端全量为 1175 passed、425 subtests passed、0 failures；`py_compile` 和 `git diff --check` 通过。全部 AI 行为使用 Fake/Mock，真实 DeepSeek 调用、API Key 读取和费用均为 0；未修改 React、阶段 8/9 或历史质量结果。这能证明本地 Fake/PostgreSQL 下的运行/事务/审计合同，不能证明真实模型质量、React 体验或完整端到端验收；唯一下一步是等待用户确认 7R5-G。
- 2026-08-27 7R5-E“5.0 初筛报告后端”已完成并停止。新增严格 5.0 报告输入/输出/持久化 Schema、十段式 Prompt 与 4 个虚构脱敏平衡 Few-shot、单次 Adapter 兼容、纯 Service 确定性校验、`ScreeningReport.v5_report` JSONB 合同及 revision `c5d7e9f1a323`；保留 1.0—4.0 报告只读兼容，不回填、不覆盖历史证据。专项合跑 183 passed、12 xfailed、52 subtests passed；受影响回归 154 passed、55 subtests passed；后端全量 1149 passed、12 xfailed、419 subtests passed、0 failures。真实 PostgreSQL 完成 `a3 → b4 → c5 → b4 → c5`，最终 `current=head=c5d7e9f1a323`、`alembic check` 无待生成操作，关键业务表往返前后均为 0 行；`py_compile` 和 `git diff --check` 通过。全部报告行为使用 Fake/Mock，真实 DeepSeek 调用、API Key 读取和费用均为 0。该结果证明离线 Schema/Prompt/Adapter/Service/Model/migration 合同和既有后端回归稳定，不能证明真实模型质量、React 体验、异步运行接线或完整端到端验收；唯一下一步是等待用户确认 7R5-F。
- 2026-08-27 用户确认 7R5-E Prompt 采用六项工程方法：结构化分区、输入隔离、严格 JSON Schema、3—5 个虚构脱敏且与正式样本隔离的平衡 Few-shot、输出前静默完整性检查，以及 Prompt 版本与 Bad Case 回归。权威设计同时固定不采用输出思维链、普通流程多次投票、内容错误 Self-Refine、动态 RAG/Few-shot 检索或 LLM-as-Judge 单独代替人工/程序校验。本轮只修改阶段设计与状态文档，没有修改生产代码、测试、Schema、Prompt、Adapter、Service、Model、migration、API、React 或数据库，真实 DeepSeek 调用和费用为 0；该记录不能证明 7R5-E 已实现或 Prompt 真实质量，唯一下一步仍是等待用户明确确认实施 7R5-E。
- 2026-08-26 7R5-D 计划编辑、确认、版本和 API 已完成并停止。公开生成/失败重生入口切换到 5.0；新增整份草稿原子保存、确认、ready 分叉和历史列表 API，Service 落地 HR 编辑/新增/删除/合并、`hr_added`、全历史稳定 ID、warning 重算、乐观并发、JD 过期、非评价字段不误伤和迟到响应保护。Model/migration 用两套部分唯一索引分别保护旧 1.0—4.0 输入唯一与 5.0 编辑版本唯一，并增加完整草稿/失败无部分 payload/确认时间约束。真实 PostgreSQL `b4 → a3 → b4` 往返保持计划表 1 行及整行 MD5 `0819ebafc4168daf6b99d8a848911221` 不变；最终 `current=head=b4c6d8e0f212`、`alembic check` 通过。专项 PostgreSQL/API/迁移合同 15 passed；D 与静态合同 56 passed、4 xfailed；受影响回归 119 passed、2 xfailed、12 subtests passed；后端全量 1100 passed、32 xfailed、419 subtests passed、0 failures，用时 102.07 秒。`py_compile`、`git diff --check` 通过。全部 AI 行为使用 Fake/Mock，真实 DeepSeek 调用和费用为 0；没有实现 5.0 Screening 报告或 React，没有修改 4.0 历史质量结果。当前结果不能证明真实模型质量、前端 HR 体验或 5.0 筛选报告链；唯一下一步是等待用户确认 7R5-E。
- 2026-08-26 7R5-C1 importance 原文语义与 HR 复核 warning 已完成并停止。Prompt 升级为 `job_evaluation_plan_lightweight_v2`，按七段固定结构组织，加入 5 个虚构、去标识化且类别平衡的边界 Few-shot，并以静态合同保护业务输出字段、正式冻结样本隔离和禁止输出思维链；行为合同升级为 `lightweight_plan_generation_v2`。新增受控 warning code、稳定 criterion ID 引用及 7 类复核原因；Service 保留模型 importance/origin，只在来源、安全、擅自新增和结构硬门禁通过后生成 warning，warning 成功返回、不内容重试。纯生成专项 36 passed；专项与配置合跑 47 passed、16 subtests passed；受影响回归 274 passed、2 xfailed、59 subtests passed；后端全量 1075 passed、42 xfailed、419 subtests passed、0 failures，用时 97.88 秒；静态扫描 20 passed、2 xfailed，`py_compile` 与 `git diff --check` 通过。全部 AI 路径使用 Fake/AsyncMock，真实 DeepSeek 调用和费用为 0；Alembic `current=head=a3b5c7d9e101`。没有 API、持久化 Model、migration、HR 编辑确认、Screening、React、正式业务数据或 4.0 历史质量结果改动。该结果证明 Prompt 静态结构及离线 warning/硬失败/重试合同，不能证明 Few-shot 已改善真实模型语言质量或 HR 页面体验；唯一下一步是等待用户确认 7R5-D。
- 2026-08-26 用户确认 importance 业务方向后，只完成权威设计第 5.3/5.5/6/7/18/19 节合同补充、新增第 26A 节 7R5-C1 书面实施顺序并同步本状态文件；没有修改 Prompt、Schema、Adapter、Service、测试、API、Model、migration、Screening、React 或数据库。当前仅证明实施门禁和停止点已经写清，不能证明 warning 行为已实现；唯一下一步是等待用户确认 7R5-C1。
- 2026-08-26 7R5-C 单次计划生成链已完成并停止。新增 5.0 Prompt、Adapter 单请求边界、Service 纯生成与确定性校验、独立版本配置和 17 个专项合同用例；覆盖正常、少量、复杂、超过 30 项、稳定 ID、程序版本字段、完整允许 JD、Prompt 污染、敏感信息、自动招聘决定、擅自新增、来源错误、超时成功重试、第二次超时停止、非法 JSON 和内容不重试。专项与配置合跑为 28 passed、16 subtests passed；受影响回归为 213 passed、6 xfailed、59 subtests passed；全量后端为 1056 passed、42 xfailed、419 subtests passed、0 failures，用时 96.91 秒。静态扫描单跑为 20 passed、2 xfailed；`py_compile` 与 `git diff --check` 通过。全部模型路径使用 Fake 或 `AsyncMock`，真实 DeepSeek 调用 0；没有 API、Model、migration、Screening、React、PostgreSQL 业务数据或 4.0 历史质量结果改动。这证明离线程序合同和既有回归稳定，不能证明真实模型质量、费用、API/数据库、HR 编辑确认、并发、初筛或浏览器链路。
- 2026-08-26 跨电脑开发环境恢复完成：旧 `.venv` 的绝对路径指向旧用户，已用本机 Python 3.11.9 重建，`pip check` 为 `No broken requirements found`，FastAPI/SQLAlchemy/Pydantic/asyncpg/Alembic 核心导入和版本检查通过，本地测试依赖为 pytest 9.1.1。本机 Docker Desktop 已恢复，PostgreSQL/Redis/Chroma 运行；开发库在备份后由 `b4e8c2d7f913` 向前升级至 `a3b5c7d9e101`，`alembic current=head`、`alembic check` 通过，升级前后业务表计数不变。后端全量为 1039 passed、42 xfailed、419 subtests passed、2 warnings、0 failures，用时 94.73 秒；前端 19 个 Node 测试脚本、TypeScript 和 Vite 生产构建通过。Docker Hub IPv6 拉取前后端基础镜像失败，不影响本机 `.venv`、已有基础设施容器和本轮测试，但尚未重新验证全量 Docker 镜像构建。
- 2026-08-26 7R5-B 计划 Schema/Model/migration 已完成并停止。新增 revision `a3b5c7d9e101`（`down_revision=d6f4a2b8e913`），让 1.0—5.0 计划并存，新增 `v5_criteria`、`edit_version`、`confirmed_at` 和对应约束，不回填、不改写旧 1.0—4.0 行。批次完成时全套测试为 1039 passed、42 xfailed（strict=True，属于 7R5-D/E/F）、0 failures，真实 DeepSeek 调用 0。
- 2026-08-26 7R5-A 合同测试与离线基线已完成并停止。新增 7 个测试文件和 1 个 fixture 文件，共 127 个 v5.0 合同测试：70 passed、57 xfailed（strict=True）、0 failures、0 errors。所有 xfail 红灯均来自缺少 5.0 生产能力，0 来自 import 错误、测试语法或 fixture 路径。既有 4.0 回归 954 passed、0 failures。`py_compile` 全部新文件通过，`git diff --check` 通过。历史 H2 正式 SHA-256 `b416809973ef0013a125736d8acafc024b610882608967f42c6ab10fc8a20b50`、HR2 定向 SHA-256 `4b7c44d4874f3ece189b50d4488d305a1161dbbcdf291277de45945844030ce9` 均不变。真实 DeepSeek 调用 0、生产代码修改 0、Alembic `current=head=d6f4a2b8e913`。
  - 新增文件：`backend/tests/fixtures/v5_quality_samples.py`（10 JD + 20 JD-Resume 对 + 5×3 稳定性标签，fixture hash `2ecc2da188f09883c1b6acaa40d0ca25f2306f2894e7f060a3a26aefb2fa9643`）
  - `backend/tests/test_stage7_v5_schema_model_contract.py`（16 tests：16 xfail → 7R5-B/E）
  - `backend/tests/test_stage7_v5_plan_edit_contract.py`（23 tests：8 passed + 15 xfail → 7R5-D/F）
  - `backend/tests/test_stage7_v5_report_scoring_contract.py`（26 tests：12 passed + 14 xfail → 7R5-E）
  - `backend/tests/test_stage7_v5_screening_ops_contract.py`（23 tests：19 passed + 4 xfail → 7R5-F）
  - `backend/tests/test_stage7_v5_hr_decision_contract.py`（17 tests：11 passed + 6 xfail → 7R5-F）
  - `backend/tests/test_stage7_v5_static_scan_contract.py`（22 tests：20 passed + 2 xfail → 7R5-B/D）
  - 红灯按批次分布：7R5-B 14 个（Schema/Model/migration）、7R5-D 16 个（计划编辑/版本/并发）、7R5-E 14 个（报告/评分/证据/矛盾）、7R5-F 13 个（筛选门/批量/HR 决策/移交）
  - 70 个 passed 证明：无权重（9）、显示标签（6）、JD 过期（3）、计划只读（4）、安全（3）、4.0 筛选门（1）、状态枚举/方法/并发（19）、HR 决策/历史（11）、历史结果保护（3）、RequirementFact 现状（2）、质量常量（5）、无加权总分（4）
- 2026-08-26 7R4-H2 唯一正式 20 份已执行并停止，结果未通过。运行前 HR2 validator、正式空路径、官方实时 peak 价格、API Key 存在性、工作区和历史 hash 均通过。正式结果为 `docs/stages/stage7/2026-08-25-stage7-7r4h-plan-quality-formal-results.json`，大小 `1,550,704` bytes，SHA-256 `b416809973ef0013a125736d8acafc024b610882608967f42c6ab10fc8a20b50`。58 次业务调用/API attempt、0 repair、0重试，token 为 input/cache hit/cache miss/output `105,874/43,776/62,098/35,182`，估算 `$0.074376224`。质量统计为 `15/20`、facts `214/245`、明确必测 `97/97`、source units `222/255`、warning `3/5`、错误合并 4、边界 `1/2`，所以正式门禁为 false。结果写入和历史 hash 后置检查完成后，终端打印因 GBK 无法编码 `•` 返回 `UnicodeEncodeError`；UTF-8 JSON 完整可读，不重跑。PostgreSQL healthy、`current=head=d6f4a2b8e913`、九表全 0，历史与 HR2 hash 不变，`git diff --check` 通过。本轮未改生产代码、测试、Prompt、Schema、数据库或前端。
- 2026-08-26 7R4-H2P 已完成并停止。唯一代码修改是移除质量运行器静态路径测试中的 HR2 执行前存在性断言；质量合同和运行器生产逻辑未改。Adapter/Service/质量运行器专项分别为 `12 passed + 18 subtests`、`68 passed`、`20 passed`，三组同跑 `100 passed + 18 subtests`，扩大回归 `286 passed + 59 subtests`；Fake normal/repair 为 3/4 次业务调用和 0/1 repair，dry-run 真实调用/写入/Adapter/Key 前提均为 0/0/否/否，`py_compile`、`git diff --check`、九份证据 hash、正式 validator、Alembic `current=head=d6f4a2b8e913` 和九表全 0 均通过。官方价格检查时间为 `2026-08-26T14:55:42.413+08:00`，当时属于工作日 peak；`deepseek-v4-flash` off_peak 为 `$0.007/$0.22/$0.66`，peak 为 `$0.014/$0.44/$1.32`，依次对应 cache-hit input/cache-miss input/output，单位 USD / 1M tokens。正式边界为 58/77/80 次业务调用、160 次 API attempt、每次 max output tokens 16,000。该批完成时停在用户金额确认门禁，随后已按独立授权执行 H2。
- 2026-08-26 正式轮首次零调用预检因质量运行器测试生命周期过期而停止：Adapter 专项 `12 passed + 18 subtests`、Service 4.0 专项 `68 passed`、质量运行器专项 `19 passed, 1 failed`。失败仅为测试断言 HR2 路径必须不存在；实际 HR2 文件大小/hash 正确、正式 validator 只读通过，正式结果路径不存在，九份证据 hash 全部匹配，`git diff --check` 通过。没有读取 API Key、实例化真实 Adapter、调用 DeepSeek、查询价格或修改生产链。第 32 节只完成 `7R4-H2P` 实施顺序文档门禁，尚未授权或修改测试。
- 2026-08-26 7R4-HR2 已完成并停止。运行前直接专项 `100 passed + 18 subtests`，扩大受影响回归 `286 passed + 59 subtests`，`py_compile`、`git diff --check`、Fake normal/repair、dry-run 和只读 PostgreSQL 基线均通过；金额确认前真实调用 0。HR2 六份结果 `6/6`，全部质量硬门槛通过，16 次业务调用/API attempt、0 repair、0 基础设施重试，逐 attempt model/Prompt/finish/token/cache/raw response/费用完整；估算总费用 `$0.028416576`。结果文件 `docs/stages/stage7/2026-08-26-stage7-7r4hr2-plan-quality-targeted-revalidation-results.json` 大小 `510,921` bytes，SHA-256 `4b7c44d4874f3ece189b50d4488d305a1161dbbcdf291277de45945844030ce9`。正式门禁只读验证通过但正式结果未创建；H1、HR1 和其余历史 hash 不变，PostgreSQL revision 与九表计数不变。该结果只证明六份定向计划质量门禁通过，不能证明正式 20 份、报告质量、浏览器验收或阶段 7 完成。
- 2026-08-26 7R4-HR0b 已完成。修改前直接相关基线为 `73 passed + 7 subtests`；修改后 Adapter/Service 4.0/质量运行器专项分别为 `12 passed + 18 subtests`、`68 passed`、`20 passed`，三组同跑为 `100 passed + 18 subtests`，受影响 Adapter/Schema/Service/source units/step9/容量/质量合同回归为 `275 passed + 43 subtests`；仅有既有 PyPDF2 弃用 warning。Fake normal/repair 严格为 3/4 次业务调用，repair 路径只有 1 次内容修复，基础设施重试均为 0；dry-run 为真实调用 0、结果写入 0、真实 Adapter 未实例化、API Key 非前提。`py_compile`、`git diff --check` 通过，四个 AI Output Schema 无修改。H1/HR1 hash 仍为 `ada6cbc91c21e7f4f341eee587259676579c9c2770af3a220277ff32a5e47a6f` / `f1de3930c16e628617d4213ad0f85bf3a25fa0272945e5806e00c69a5d0df4d4`，其余历史质量结果 hash 也与固定值一致；HR2 与正式 20 份结果不存在；PostgreSQL `current=head=d6f4a2b8e913` 且九张业务表全为 0。该验证证明版本责任迁移和严格结构门禁按合同工作，不能证明真实模型质量或 HR2 六份会达到 `6/6`。
- 2026-08-26 只完成第 30 节方案替换和 `PROJECT_STATE.md` 同步，没有修改 Prompt、Adapter、Service、Schema、测试、质量合同或数据库，也没有调用 DeepSeek。H1/HR1 SHA-256 仍分别为 `ada6cbc91c21e7f4f341eee587259676579c9c2770af3a220277ff32a5e47a6f`、`f1de3930c16e628617d4213ad0f85bf3a25fa0272945e5806e00c69a5d0df4d4`；HR2 候选结果路径不存在，`git diff --check` 通过。这只能证明文档方案和历史证据边界已同步，不能证明 HR0b 代码已实现或真实模型问题已修复。
- 7R4-HR1 结果文件为 `docs/stages/stage7/2026-08-25-stage7-7r4hr1-plan-quality-targeted-revalidation-results.json`，大小 `315,076` bytes，SHA-256 为 `f1de3930c16e628617d4213ad0f85bf3a25fa0272945e5806e00c69a5d0df4d4`。逐样本 `3/6`、人工 facts `23/80`、明确必测 `12/23`、source units `31/90`、正常/边界 `2/4、1/2`、warnings `0/2`；已形成的 23 条 facts 的来源追溯、priority 和 criterion 覆盖均为 100%，六类污染/合并错误均为 0。10 次调用的 input/cache hit/cache miss/output 为 `20,441/3,584/16,857/10,556`，按峰值价重算为 `$0.021401176`。旧 H1 和全部历史结果 hash 不变，正式结果未创建；运行前后 PostgreSQL `current=head=d6f4a2b8e913` 且九张业务表全为 0。
- 7R4-HR0 Prompt/Service 专项 `44 passed`，质量运行器专项 `19 passed`，配置专项 `11 passed + 16 subtests`；受影响后端回归 `262 passed + 48 subtests`，覆盖配置、计划 Adapter、1.0—4.0 计划 Service/Schema、source units、step9 与 4.0 Screening gate。dry-run、Fake normal 和 Fake local repair 均通过，分别证明 0、3、4 次 Fake/业务路径，真实 DeepSeek 调用 0、正式结果写入 0、真实 Adapter 未实例化。定向/正式审计基线和合法修复上界为 `16/21、58/77`，安全硬上限保持 `24/48、80/160`；少跑、乱序、no_facts 后继续、repair 错位、第三次技术尝试和汇总不一致会被拒绝。HR0 完成当时 H1 SHA-256 为 `ada6cbc91c21e7f4f341eee587259676579c9c2770af3a220277ff32a5e47a6f`、HR1 文件尚不存在，历史 hash 不变；PostgreSQL `current=head=d6f4a2b8e913` 且九张业务表全为 0。
- 7R4-H1 新定向结果 SHA-256 为 `ada6cbc91c21e7f4f341eee587259676579c9c2770af3a220277ff32a5e47a6f`，`targeted_gate_passed=false`、逐样本 `4/6`。80/80 人工 facts、23/23 明确必测、90/90 source units 均为 100%；83 facts 的追溯、priority 和 criterion 覆盖均为 100%，正常/边界为 4/4、2/2，六类污染/错误中只有 `source_merge_failure_count=1`。预期 warning 命中 1/2。16 次真实 attempt 均为 `deepseek-v4-flash + stop`，逐次费用可重算，历史 hash 和空数据库基线不变；正式结果未创建。
- 7R4-H0 专项为 26 passed + 7 subtests；配置、Adapter、4.0 纯生成和质量运行器受影响回归为 60 passed + 23 subtests；`py_compile`、`git diff --check` 通过。计划 dry-run/Fake 均为真实调用 0、正式结果写入 0，新 4.0 定向/正式结果文件不存在，历史结果 hash 不变。H0 没有修改 Prompt、Schema、Service、Model、migration、API、React 或 PostgreSQL；这些结果只证明审计与调用门禁已就绪，不能证明六份真实定向质量。
- 7R4-G 计划 dry-run 固定 J5-01—J5-20、定向 J5-03/07/14/17/19/20、SHA-256 `23651a92bb68602f096cf30519d5c11cd2ce6e724950f158587ba201e41fdfe0`、245 条人工 facts、97 条明确必测、定向 80/23，以及 255/90 source units；报告 dry-run 固定 SR01—SR20、high/partial/low=8/6/6 和每组 3 次。两侧均为真实模型 0 次、正式结果写入 0 次、真实 Adapter 未实例化、API Key 非前提，既有历史结果 hash 不变。
- 7R4-G 计划预算为定向正常/局部修复/含基础设施重试最大尝试 `18/24/48`，正式为 `60/80/160`；候选模型已从退役兼容别名 `deepseek-chat` 明确改为官方模型 ID `deepseek-v4-flash`，保持 `thinking disabled`，模型档位与官方单价仍须在 7R4-H 前另行确认，费用字段没有伪造数值。Fake 实际审计得到正常 3 次业务调用、0 内容修复、0 基础设施重试；局部修复 4 次、1 内容修复、0 基础设施重试；另有超时 4 次尝试但仍为 3 次业务调用和 1 次基础设施重试。认证、非法 JSON、Schema、事实、证据和安全错误均只尝试 1 次。
- 2026-08-25 模型别名兼容修正后，配置、计划/筛选 Adapter 与 7R4-G 门禁定向为 36 passed + 29 subtests；后端全量仍为 896 passed + 408 subtests。dry-run 为 `deepseek-v4-flash / thinking disabled / 0 次真实调用 / 0 次正式写入`；门禁会拒绝模型、thinking、temperature/JSON/token/SDK 重试或 Prompt 版本与定向轮不一致的正式轮。
- 7R4-G 新合同测试为 11 passed；受控 API/PostgreSQL Fake 集成 1 passed。受影响计划、Screening、API、migration 定向回归为 129 passed + 22 subtests；后端全量为 896 passed + 408 subtests，另有既有 PyPDF2 弃用 warning 与旧 API 测试清理阶段的 asyncpg cancel RuntimeWarning。正式开发库最终 `current=head=d6f4a2b8e913`，`jobs/candidates/resumes/applications/job_evaluation_plans/screening_runs/screening_reports/stage_histories/reports` 均为 0。由于没有修改前端，本批未重复浏览器、TypeScript 或 Vite 验收。
- 7R4-A—E核心后端合同82/82 passed；旧1.0/2.0/3.0运行时拦截、31条容量、513条上限、fact来源追溯、criterion完整归组和Adapter调用前失败均有专项回归。7R4-F前端4.0合同由2 passed、10 failed转为12/12 passed。
- PostgreSQL上的7R4-E后端全量884 passed、408 subtests passed；7R4-F受影响后端回归51 passed + 5 subtests，前端全量56/56，TypeScript与Vite 5.4.21生产构建通过（3121模块）。正式开发库`current=head=d6f4a2b8e913`，相关业务表均为0；真实DeepSeek调用0。
- 7R4-A 新增合同测试共 63 条：8 passed、55 expected failed、0 skip、0 xfail、0 收集/导入/夹具错误；红灯责任为 7R4-B 19、7R4-C 14、7R4-D 6、7R4-E 6、7R4-F 10。既有前端 44/44、TypeScript 与 Vite 5.4.21 构建通过（3121 模块）；既有受影响后端非数据库回归 89 passed + 7 subtests。后端全量在进入 PostgreSQL 测试后因本机端口拒绝连接而不能形成有效结论，Docker Desktop Linux engine 同样未运行；这不是 4.0 红灯，也不能冒充全量通过。
- 7R4-A 离线容量为 20 份 JD、255 source units、245 人工 facts、93 个容量估算 criteria；各样本最大值依次为 33、31、11。input snapshot/facts/criteria/合并输出最大为 5045/5944/1099/7088 字符。脚本不实例化 Adapter、不读取 API Key、不写结果文件，DeepSeek 真实调用 0。候选安全口径随后已获确认；7R4-B只实现其数据层责任，其余仍留在7R4-C/G。
- 7R-F dry-run 以 0 次真实调用完成 20 份冻结 JD、245 条主要语义、97 条明确必测、`public_notes` 排除、Prompt 与费用门检查；首轮定向真实验证随后执行 6 次、0 重试。source unit review、来源追溯、优先级一致与预期 warning 均为 100%，五类污染/错误计数为 0；但逐样本合同仅 3/6，主要语义召回 91.25%、明确必测召回约 86.96%，边界正确 1/2，所以正式 20 份被门禁阻止，7R-F 未通过。
- 7R-E 前端合同 12/12、前端全量 44/44、TypeScript 严格检查和 Vite 5.4.21 生产构建通过（3121 模块）；后端展示/API/Service 定向 33 passed + 8 subtests，全量 793 passed + 408 subtests。`alembic check` 无待生成操作，`git diff --check` 通过。
- 7R-E 真实 PostgreSQL/API 固定夹具覆盖 ready、missing、failed、outdated、legacy、generating、closed、draft；验收读取成功且 DeepSeek 调用 0。夹具和独立 8010/5174 服务均已清理/停止，正式库八表计数恢复原值。
- 7R-E 应用内 Browser 首次初始化被本机 `failed to write kernel assets: 系统找不到指定的路径 (os error 3)` 阻断；重启后初始化已恢复，但没有挂载任何可控制浏览器实例。没有使用独立 Playwright 替代。因此三档尺寸、八种状态、键盘/焦点、实际轮询停止、整页溢出和危险文本浏览器验收当时仍未验证；3.0/4.0 的浏览器欠账现在统一由未来获准后的 7R5-J 重新验收，不能声明通过。

- 6R-D 验收结论为通过，完整记录见 `docs/stages/stage6/2026-08-22-stage6-five-section-jd-remediation-acceptance.md`。真实 API 与 Microsoft Playwright 完成标题-only 草稿、缺字段开放失败、五段持久化、非法开放编辑回滚、关闭、关闭态编辑、非法/合法重新开放和安全删除；验收 Job #326/#327 已清理。
- 6R-D 三档视口 1440×900、820×1180、390×844 均无整页横向溢出，底部操作区可见；HTML-like JD 只按普通文本显示。浏览器负向 422 后重新导航为 0 个 console error、2 条既有 React Router future warning。截图保存在 `docs/stages/stage6/browser-acceptance-evidence/`。
- 6R-D 修复成功通知上下文、静态 Modal、未挂载 Form reset 和评价计划旧写入口四个最小问题。前端定向 12/12、全量 32/32、TypeScript/Vite 构建通过（3121 模块）；后端沿用本轮已执行的全量 694 passed、411 个子用例通过和 1 条既有 PyPDF2 warning。
- PostgreSQL `current=head=f2b8c6d1a940`，`alembic check` 无待生成操作；最终计数为 `jobs=0/applications=0/candidates=2/resumes=9/job_evaluation_plans=0/screening_reports=0/screening_runs=0/stage_histories=0`。阶段 7 Adapter 调用为 0，没有调用真实 DeepSeek。

- 6R-B 后端合同测试 23/23、旧 Job 核心回归 45/45、历史 JobEvaluationPlan Service 22/22、历史 ScreeningService 27/27 通过；后端全量 694 passed、411 subtests passed，另有 1 条既有 PyPDF2 弃用 warning。OpenAPI 唯一路由包含在全量中，`git diff --check` 通过。
- 6R-B 临时 PostgreSQL 已完成空表 `upgrade -> downgrade -> upgrade`，并实证非空 jobs 表以 `STAGE6_FIVE_SECTION_JD_REQUIRES_EMPTY_JOBS` 失败且无部分 DDL。正式库只做向前升级，`current=head=f2b8c6d1a940`，`alembic check` 无待生成操作；最终业务计数为 `jobs=0/applications=0/candidates=2/resumes=9/job_evaluation_plans=0/screening_reports=0/screening_runs=0/stage_histories=0`。
- 6R-C 已把岗位创建、编辑、搜索、列表摘要、错误定位和申请岗位读取方切换到五段式字段；五个大型普通文本框及长度/公开提示合同已落地，旧细分 JD 控件和当前 Job Service 的 `JobRequirementsV1` 已退出运行边界。阶段 7 历史计划快照旧结构只保留在阶段 7 自有的历史读取类型中。
- 6R-A 的前端合同已由 2 项通过、11 项预期红灯转为 13/13 通过；包含 3 个既有 Job 前端脚本的定向结果为 16/16，前端全量为 32/32。TypeScript 严格检查和 Vite 生产构建通过，共转换 3121 个模块。
- 6R-C 本身没有修改后端合同或 migration；其当时未覆盖的真实浏览器尺寸和完整 PostgreSQL 页面主链已由 6R-D 验收通过。
- 6R-A 新增后端合同测试 23 个方法，正常收集且无 ERROR，形成 42 个预期断言红灯：Schema 14、Model 8、Service 7、API 3、migration 4、阶段 7 暂停 6；全部映射到 6R-B。新增前端合同 13 项中 2 项通过、11 项预期红灯，全部映射到 6R-C。
- 6R-A 修改前旧 Job 合同 69 项、旧 JobEvaluationPlan 28 项通过；新增测试后，Job/计划 97 项、Application/HR 决策 43 项、Resume/报告 76 项和前端全部 19 个既有 Node 脚本通过。阶段 7 ScreeningService 的 27 项在修改前即因开发库缺少阶段 7 表而报错，属于数据库 revision 落后代码的既有环境基线，未冒充本批红灯或回归结果。
- 6R-A 没有修改生产代码、Prompt、Adapter 或既有 migration，没有执行 migration、修改 PostgreSQL 业务数据或调用 DeepSeek。当前代码 head `e4c7a1b9d632`，开发库 current `c8e1a6f4d205`；`jobs=1/candidates=2/resumes=9`，其余所列阶段 7 表不存在。
- 阶段 7 AI 前端 3 个专项脚本通过；前端全部 19 个 Node 测试脚本通过；TypeScript 严格检查通过；Vite 5.4.21 生产构建通过，共转换 3124 个模块。
- 小步骤 9-G 的 42 项 step9 合同、139 项 JobEvaluationPlan/Screening/验收器定向、140 项岗位及业务隔离和 32 项 migration 测试通过；后端全量 677 项 `pytest` 在 33.52 秒内通过，另有 1 条既有 PyPDF2 弃用 warning。
- 小步骤 9-H 定向 dry-run 为 0 次调用、0 次写入；真实定向调用 6/6 完成且合同满足 6/6，验收器 10/10 与冻结 step9 合同 42/42 通过。独立结果为 `docs/stages/stage7/2026-08-21-stage7-step9-jd-decomposition-debug-results.json`，不能作为 9-I 正式质量结论。
- 此前误执行的 20 次 JD 调用形成 18/18 正常 JD 可用、主要要求 42/42、结构化覆盖 63/63，安全追溯类错误均为 0；JD18 边界失败层不符合预期。独立结果保留为历史诊断，不作为整理后 9-I 的正式结论。
- Alembic 代码 head 与 PostgreSQL current 均为 `e4c7a1b9d632`；9-E 已完成真实数据库 migration 往返，9-F 真实 PostgreSQL 服务回归验证了新旧计划并存和历史报告外键，9-G 重跑实际 PostgreSQL 服务与 migration 回归。`alembic check` 返回 `No new upgrade operations detected`；9-G 没有新增或修改 migration。
- 合并 9-I dry-run 固定选中 20 份 JD、20 组 JD/Resume、high 8/partial 6/low 6 人工标签和每组 3 次计划，记录 0 次模型调用、0 次结果写入；真实计数严格执行 20 次 JD 和 60 次筛选，额外调用 0。新增验收器 19/19、受影响专项 122/122、后端全量 687/687 通过，另有 1 条既有 PyPDF2 弃用 warning。
- 9-I 正式 JD 结果为 18/18 正常 JD 可用、主要要求 42/42、JD08“激活”通过、结构化覆盖 63/63，required/重复/追溯/宣传错误均为 0；JD18 未形成预期 `too_many_items`，所以边界 1/2、`step9_quality_gate_passed=false`。JD 结果为 `2026-08-21-stage7-step9-jd-decomposition-revalidation-results.json`。
- 9-I 下游诊断为：上游阻塞 0，20 组各 3 次；至少一份合法报告 9/20，合法次数分布 0/3=11、1/3=4、2/3=4、3/3=1；总体方向 9/20，三次全部合法 1/20 且其分差 ≤5。结果为 `2026-08-21-stage7-step9-full-chain-diagnostic-results.json/.md`，状态仅为 `diagnostic`。
- PostgreSQL、Redis、Chroma 均运行；PostgreSQL healthy 并接受连接，Redis 返回 `PONG`，Chroma heartbeat 返回 HTTP 200。
- OpenAPI 共 65 条 method+path，重复为 0；新增的 4.0 确认路由与当前计划、Application、筛选路由均没有重复注册。
- 运行时扫描没有恢复旧 Rubric、ScreeningResult、五维权重、证据覆盖率或 Python 加权评分；阶段 7 AI UI 没有 `dangerouslySetInnerHTML`、Resume 原文、原始模型响应、API Key、内部异常或敏感属性展示；Git 跟踪文件没有疑似真实 Key。
- 最终计分轮对 20 份虚构 JD 真实调用 DeepSeek 20 次：16 份形成 ready/limited 计划，0 项和 >30 项边界各 1 份正确失败，另 2 份中英文岗位内容失败；全部样本自由文本主要要求识别 35/42（83.33%），结构化覆盖在成功计划中为 100%，擅自新增 required、明显重复和宣传福利误识别均为 0。
- 20 组人工标签在调用前固定；17 组进入三次评价，共 51 次真实 DeepSeek 调用。10/20 至少形成一份合法且方向一致的报告，总体方向一致率 50%，低于 80%。仅 5 组连续三次通过严格校验，其中 4/5 最大分差不超过 5，低于 90%。
- 原正式质量验收的 23 份合法报告中，115 个正分基础事项均有可定位证据，敏感属性评分和招聘决定建议为 0；当时 2 个样本出现严重年限事实错误，额外亮点与基础事项重复至少涉及 2 个样本，因此原安全验收直接失败。整改后的 SR05/SR15 最终计数轮各 3 次真实 DeepSeek 调用共 6 次，模型响应 6/6，严重年限事实冲突 0；SR15 合法报告 3/3，SR05 因模型仍把年限放进综合摘要而 0/3，总体合法报告 3/6。
- Playwright MCP 实际打开 `/app/jobs` 和 `/app/screening`，使用虚构脱敏夹具覆盖计划四状态、筛选状态矩阵、报告、单人/批量动作、约 4 秒轮询、1440×900/820×1180/390×844 布局及键盘检查。60 项中 57 通过、2 失败、1 未验证、0 阻塞；完整脚本观察到 103 个 API 请求、HTTP 错误 0，终态/关闭/离开后轮询均停止。
- 浏览器最小修复包括计划抽屉关闭回焦、静态 Modal 改为上下文实例、空 `tradeoff_reason` 不再渲染空壳。修复后 Modal 警告为 0、回焦与空壳场景通过；仍有 1 条 Drawer 焦点哨兵 `aria-hidden` 警告，普通初筛真实数据库持久化幂等未在浏览器中验证。
- 本轮全部最小修复还包括 required 单字误判、JD 逐字/英文约束 Prompt v3、筛选嵌套 evidence/bonus Prompt v2，以及固定投递时间整改后的筛选 Prompt v3 / Schema 2.0。完整证据见 `docs/stages/stage7/2026-08-20-stage7-quality-acceptance.md`、原质量验收 JSON、`2026-08-21-stage7-time-fact-revalidation-results.json` 与 `browser-acceptance-evidence/`。
- `git diff --check` 通过。上述结果证明自动化、迁移、固定投递时间链路和年限事实防线稳定，并证明大部分前端状态与交互按合同工作；9-I 还证明新 JD 追溯/召回合同在 18 份正常样本上可用，但 JD18 边界、总体报告成功率和三次稳定性仍失败。它明确不能证明阶段 7 AI 质量合格、招聘准确、真实数据库端到端幂等或浏览器子验收全通过；本次没有重新执行浏览器验收。
- 当前后续顺序为：7R4-HR2 已以 `6/6` 通过 → 7R4-H2 正式 20 份已以 `15/20` 失败并停止 → 先由用户决定是否登记新的质量整改设计 → 只有未来整改与独立复验使正式计划质量通过、且再次获得授权后，才能进入 7R4-I 报告质量与稳定性 → 7R4-J 数据库/API/浏览器收尾。H1、HR1、HR2 和本次 H2 正式结果都是不可覆盖的历史证据；3.0 和更早质量结果只作历史对比，不计入未来复验。

开始下一步前仍须重新检查实际 Git 状态、测试数量、Alembic revision 和数据库状态，不能只依赖这里的历史基线。

## 13. 新对话恢复方式

1. 阅读 `CLAUDE.md`。
2. 阅读本文件。
3. 根据 `docs/DOCUMENT_INDEX.md` 判断任务需要哪些补充文档。
4. 修改阶段 7 业务代码前，完整阅读阶段 7 当前设计。
5. 执行任何修改前检查 `git status` 和相关差异，保护现有工作区修改。
