# 项目当前状态

> 最新更新：2026-08-21
>
> 本文件只记录“现在是什么状态、下一步做什么”。完整开发过程已归档到 `docs/archive/history/2026-08-20-project-history.md`，不再作为新对话的默认阅读材料。

## 1. 当前结论

- 项目正在建设新版招聘主链，旧 React + FastAPI + SQLite + Mock LLM 演示系统已经退役。
- 阶段 4“简历上传与原文提取”和阶段 5“AI 结构化草稿”已经完成；阶段 6 原 `description + JobRequirementsV1` 岗位合同曾完成，但 2026-08-21 已决定返回阶段 6 进行五段式 JD 整改。
- 阶段 7“Application 与 AI 初筛底座”已完成小步骤 8 的投递时间基准与年限事实整改，但完整真实 AI 质量与浏览器验收仍未达到完成标准；当前因上游五段式 JD 变更暂停，不继续修补旧 JD 输入合同。
- 小步骤 9-I 已完成 20 次 JD 正式复验和 60 次下游真实诊断。18/18 正常 JD 可用、主要要求与结构化覆盖均为 100%，但 JD18 没有形成预期 `too_many_items`，因此 `step9_quality_gate_passed=false`，小步骤 9 仍未通过；下游诊断也仅有 9/20 至少一份合法报告、1/20 三次全部合法。
- Application、Resume 隔离、HR 内部录入和 HR 决策等公共能力继续保留。
- 旧 Rubric、五维权重、确定性评分、`unknown`、证据覆盖率、Python 加权总分和多报告历史方案已经废弃。
- 阶段 7 当前业务方案已经确认；旧 Rubric 删除、`JobEvaluationPlan`、严格单次评价、异步运行、幂等、当前成功报告替换、React 完整报告交互以及固定投递时间事实已经完成。SR05/SR15 最终 6 次真实 DeepSeek 定向复验的严重年限事实冲突为 0，但合法报告只有 3/6；原 Playwright 浏览器验收仍为 60 项中 57 通过、2 失败、1 未验证、0 阻塞。因此这次缺陷已修复，不代表阶段 7 整体通过。

## 2. 当前权威文档

文档职责和按任务阅读规则统一见 `docs/DOCUMENT_INDEX.md`。

当前阶段的权威顺序是：

1. 阶段 6 五段式 JD 整改：`docs/stages/stage6/2026-08-21-stage6-five-section-jd-remediation-design.md`
2. 阶段 6 原设计：`docs/stages/stage6/2026-08-15-stage6-structured-job-management-design.md`，除被新补充替代的 JD 字段合同外继续有效
3. 阶段 7 当前设计：`docs/stages/stage7/2026-08-20-stage7-jd-driven-ai-screening-redesign.md`，当前处于上游整改暂停状态
4. 本文件：只负责当前进度、工作区风险和下一步
5. `CLAUDE.md`：项目长期架构、技术栈和稳定约束
6. `docs/planning/implementation-plan.md`：跨阶段实施顺序
7. `docs/planning/2026-08-14-post-stage5-product-roadmap.md`：阶段 5 后产品路线
8. `docs/architecture/2026-07-15-hr-agent-platform-design.md`：总体架构背景

发生冲突时，当前阶段专项设计优先于旧总体示例和历史记录。归档文档不具有当前业务权威性。

## 3. 当前阶段 7 方案摘要

> 暂停说明：以下内容记录阶段 7 在五段式 JD 决定前已经实现的合同。阶段 6 将把 Job 改为岗位背景、岗位职责、任职要求、加分项和候选人可见备注五个独立字段；阶段 6 验收和新的阶段 7 输入设计确认前，旧 JobEvaluationPlan 不得继续生成。

### 3.1 固定流程

```text
HR 填写并发布 JD
        ↓
DeepSeek 拆解自由文本 + 程序补齐结构化 JobRequirements
        ↓
生成同一 JD 版本下稳定、只读的基础评价事项
        ↓
读取当前 Application 绑定的当前 Resume
        ↓
DeepSeek 单次综合评价
        ↓
后端严格校验结构、事项、证据和安全边界
        ↓
保存一份当前 AI 初筛报告
        ↓
React 渲染完整报告，HR 独立决定通过、备选或淘汰
```

本流程是固定的 Service 工作流，不是自然语言 Agent，也不使用 LangGraph。

### 3.2 评分与报告边界

- 基础事项按 `required/preferred/general` 标记，逐项使用 `0—10` 整数，不使用 `unknown`。
- 0 分表示当前简历没有体现，不代表候选人事实上不会。
- 1—10 分必须有可定位的简历证据。
- 每份简历可以有 0—5 个有证据、7—10 分、只产生正向影响的额外亮点。
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
- 该合同已于 2026-08-21 完成代码、Schema、Model、API、React、向前 migration、自动化和真实 DeepSeek 定向复验。事实规则版本为 `experience_period_facts_v1`，筛选 Prompt 为 `screening_evaluation_v3`，输出 Schema 为 `2.0`；该合同对应 migration 为 `d9a1f4c7e820`，当前数据库 head 已随小步骤 9-E 前进至 `e4c7a1b9d632`。

完整字段、状态、失败语义、验收场景和实施顺序以阶段 7 当前设计为准，本文件不重复维护第二套详细合同。

## 4. 已完成且继续保留的能力

- 新版唯一前端业务目录：`frontend/src/features/recruitment/`
- 新版工作台路由：`/app/*`；公开投递入口：`/apply`
- 正式后端接口：`/api/v2/*`
- PostgreSQL + SQLAlchemy 2.0 + Pydantic v2 + Alembic 主链
- PDF、DOCX、TXT 安全上传、私有存储和原文提取
- `Resume.raw_text` 与 `Resume.parsed_snapshot`
- DeepSeek 简历结构化草稿、严格校验和 HR 确认创建
- 结构化 JobRequirements、岗位草稿/开放/关闭状态
- Candidate 稳定身份与去重
- Application 按岗位独立绑定 Resume、独立 HR 决策和阶段历史
- HR 直通录入与 AI 初筛中心待审核录入

## 5. 已完成的 JobEvaluationPlan 能力

- 新增独立 `JobEvaluationPlan` Schema、SQLAlchemy Model 与 PostgreSQL 表，不复用旧 `JobScreeningRubric`，也不把 AI 字段塞回 Application。
- 当前 JD 使用包含 Job 标题、部门、描述和完整 `JobRequirementsV1` 的 SHA-256 稳定指纹；同一指纹幂等复用，每个 Job 只有一个当前计划。
- DeepSeek/Fake Adapter 拆解完整 JD，自有程序补齐职责、技能、年限、学历、经历、关键词和补充要求，再执行优先级修正、宣传过滤、语义去重、完整性与 0—30 项边界校验。
- 评价计划保存 `generating/ready/failed/outdated` 状态、结构化覆盖结果、Prompt/模型/Schema 版本、输入快照与指纹、稳定错误码、安全错误说明和时间字段。
- 网络、限流和模型服务端错误只自动重试 1 次；JSON、Schema 和业务内容错误不重试。1—4 项返回“评价依据有限”警告，0 项或去重后超过 30 项失败。
- 岗位创建即开放、开放、重新开放和开放状态修改后，在岗位事务提交后触发当前计划生成；失败不回滚岗位发布，JD 变化会使旧计划过期。
- 新增 `/api/v2/jobs/{job_id}/evaluation-plan` 的只读查询、幂等生成和失败重新生成接口。React 预览仍留到小步骤 7。
- 迁移 `a6d4e8f2c713` 只新增评价计划表、索引、外键和约束；该步已完成 `upgrade -> downgrade -> upgrade`，当前数据库继续由后续阶段 7 migration 向前演进至 `e4c7a1b9d632`。

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

- 新增 `ScreeningReport` 当前成功报告和 `ScreeningRun` 必要运行日志；每个 Application 由数据库唯一约束保护最多一份当前报告，运行日志不保存完整旧报告、原始模型响应或未脱敏 Resume。
- 使用稳定 JSON 序列化和 SHA-256 组合 Application、`Application.applied_at`、`Asia/Shanghai`、经历时间事实/规则版本、JD、当前 Resume、当前 ready 评价计划及 Prompt/模型/Schema/脱敏版本；普通请求复用相同报告或运行，主动“重新评估”即使输入相同也会建立新运行。
- 采用 PostgreSQL 持久运行表加 FastAPI 生命周期轮询器作为当前架构下的最小可靠后台机制；`FOR UPDATE SKIP LOCKED`、部分唯一索引和租约恢复共同保护多进程认领、并发重复及服务重启后的可解释状态，没有引入 Celery、RQ、Arq 或无持久状态的任务假象。
- Application 提交、Resume 解析完成、当前评价计划 ready 和岗位重新开放会在相关业务提交后协调首次自动初筛或等待任务；HTTP 请求不等待模型，触发失败不回滚已经提交的 Candidate、Resume、Application 或 Job。
- Resume/计划不可用分别保留 `waiting_resume/waiting_plan`，岗位关闭暂停未开始任务且允许 `running` 完成；岗位重开恢复仍然有效的自动任务和人工重新评估。
- 成功响应会重新核对最新 Resume、JD 和计划，只在严格 Schema/业务校验通过后，以同一数据库事务替换当前报告并把运行标记成功；迟到响应、内容失败或数据库提交失败都保留旧报告。
- 网络、限流、超时和模型服务端故障最多额外重试 1 次；认证、配额、JSON、Schema、事项、证据、安全及业务内容错误不自动重试，SDK 自动重试仍关闭。
- Resume、JD 或当前计划变化只把旧报告标记过期，不删除、不自动批量重评；普通 Prompt、模型或 Schema 版本升级不会自动使历史报告过期。
- 新增当前状态、普通触发、单人重新评估、同岗位 1—20 人批量重新评估和切换当前 Resume 的最小 `/api/v2` 接口；批量成员独立提交，单项失败不回滚其他人。
- AI 初筛链路不写 `hr_decision`、`recruitment_stage` 或 `lifecycle_status`。当前仍沿用内部开发接口边界，没有临时伪造登录/RBAC。
- `ScreeningReport` 额外审计评价基准、时区、事实规则版本和成功评价使用的完整时间事实快照；`ScreeningRun` 审计评价基准、时区、规则版本和时间事实指纹，不保存完整 Resume 或模型原始响应。
- 新迁移 `d9a1f4c7e820` 只向既有 `ScreeningReport`/`ScreeningRun` 增加上述审计字段。真实数据库没有历史行；migration 对假设存在的旧行也只从关联 `Application.applied_at` 回填基准，不伪造旧事实快照。

## 8. 已完成的 React 完整报告与交互

- 新增严格 TypeScript 合同和集中 `v2Http` Service，覆盖当前 JobEvaluationPlan、Screening 状态/报告/运行、普通初筛、单人重新评估、同岗位批量重新评估和切换当前 Resume；组件中不散落裸 `fetch`，也不使用 `any` 绕过合同。
- 岗位列表新增只读“评价计划”抽屉，稳定展示 `generating/ready/failed/outdated`、事项标题、category、priority、来源、警告、版本和安全错误；只在合法状态提供幂等生成或失败重新生成，不恢复旧 Rubric 编辑、权重或发布流程。
- AI 初筛工作台读取每个 Application 当前 Screening 状态；报告抽屉展示建议分、程序标签、综合评价、逐项分数/理由/计算说明/折叠证据、额外亮点、综合权衡、面试问题、版本、生成时间和“按该申请 YYYY-MM-DD 的投递时间计算”的评价基准。旧报告缺字段时诚实显示“历史报告未记录评价基准”。
- 0 分固定解释为“当前简历未体现”，AI 分数和标签固定说明为辅助建议；查看、普通初筛、重新评估和批量操作均不调用 HR 决策接口，不修改 `hr_decision`、`recruitment_stage` 或 `lifecycle_status`。
- 报告过期时继续展示旧报告和 Resume/JD/评价计划变化原因；当前计划与报告计划一致时补充事项标题和优先级，旧计划不可读取时诚实显示原事项 key，不使用新计划内容冒充旧报告。
- `queued/running` 使用 4 秒最小轮询；终态、关闭抽屉或组件卸载后停止。请求序号阻止迟到响应覆盖新状态，递归 `setTimeout` 保证只保留一个定时器。
- 普通初筛明确允许复用报告或运行；单人“重新评估”需要确认，新运行期间及失败后继续展示旧成功报告；岗位关闭时禁用开始和重新评估。
- AI 初筛工作台支持同一开放岗位 1—20 个 Application 批量选择，请求前拒绝空选、超过 20 人、重复和跨岗位选择，阻止重复提交，并按 Application 独立显示返回运行状态。
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

- 当前分支是 `2lcj`，HEAD 为 `37f4035`，与 `origin/2lcj` 同步。小步骤 4—8 已包含在当前 HEAD，不得回退或重做。
- 当前工作区正在同步小步骤 9 独立设计补充及关联状态文档，修改尚未提交；禁止使用 `git reset --hard`、`git clean`、`git checkout --` 或其他方式覆盖。
- 用户已最终确认并完成小步骤 9 的 9-A—9-I。此前助手误解用户意图产生的独立 20 份 JD 结果继续保留为历史诊断；正式 9-I 已使用新路径独立落盘，没有复用或覆盖该记录。JD18 的正式边界失败是暂停前事实；当前先回到阶段 6 整改上游 JD，不得直接进入阶段 7 步骤 10。
- 用户已确认五段式 JD 的业务规则，并授权开始文档修改。新增设计补充已形成，但按实施顺序门禁仍需用户最终复核 6R-A—6R-D 后才能修改测试或业务代码。
- 当前数据库只读核对时 Job、Application、Candidate、Resume、评价计划、筛选报告/运行和阶段历史均为 0 行；这不保证实施时仍为空，6R-B 前必须重新预检，发现 Job 行时禁止自动删除或迁移。
- 后续不得恢复旧 Rubric、旧 ScreeningResult 或嵌入 Application 的 AI 状态字段。
- 新功能应复用 Candidate、Application、Resume、Job、StageHistory、Report 和通用 DeepSeek/数据库基础设施。

## 11. 当前唯一下一步

当前唯一下一步是请用户最终复核 `docs/stages/stage6/2026-08-21-stage6-five-section-jd-remediation-design.md` 中的完整合同与 6R-A—6R-D 实施顺序。获得明确确认后，每轮只执行一个批次；第一批 6R-A 只建立自动化合同基线，不修改生产代码或调用真实模型。

五段式合同已经确认：基础信息不变；新增 `job_background/job_responsibilities/candidate_requirements/preferred_qualifications/public_notes` 五个独立普通文本字段；开放岗位只强制职责和任职要求；备注候选人可见且不参与 AI；旧 `description/requirements/legacy_requirements` 与 `JobRequirementsV1` 退出运行边界；当前不迁移旧 JD 内容、不双写、不实现 AI 生成 JD。未来 Agent 可以生成同一合同的草稿，但必须由 HR 修改、确认并独立开放。

阶段 7 现受控暂停。6R-B 后端切换时必须阻止旧 JobEvaluationPlan 读取新 Job 继续生成计划，但不在阶段 6 提前实现新 Prompt、Schema、拆解 Service 或调用 DeepSeek。阶段 6 通过后，唯一下一步才是讨论并确认新的阶段 7 五段式评价计划设计。

以下保留阶段 7 暂停前的小步骤 9 实施与验收事实，作为历史诊断和未来对比基线：

小步骤 9 的业务选择和实施顺序已写入 `docs/stages/stage7/2026-08-21-stage7-step9-jd-decomposition-quality-remediation-design.md`，并已获得用户最终确认。9-A—9-F 已完成新合同、持久化和 HR 显式升级链路。9-G 已让验收脚本使用 Schema 2.0 的 `input_snapshot/source_units/structured_candidates`，增加独立 `step9-jd` 模式、6 份定向调试与 20 份正式计数的分离路径，并统计正常、边界、limited、42 项召回、“激活”额外断言、结构化覆盖、required、重复、追溯和宣传误识别。离线统计测试即使全绿也不允许产生真实质量结论；只有 20 份冻结样本各一次实际调用的 `final_count` 才能判定门槛。42 项 step9 合同、139 项 JobEvaluationPlan/Screening/验收器定向、140 项岗位与业务隔离、32 项 migration、677 项后端 pytest 全量、19 个前端 Node 脚本及生产构建均通过。PostgreSQL current/head 均为 `e4c7a1b9d632`，`alembic check` 无新操作。9-G 没有新增或修改 migration，两种 dry-run 均为 0 次模型调用、0 次结果写入，没有调用真实 DeepSeek。

9-H 已先完成零调用、零写入的定向 dry-run，再对 JD04/JD08/JD11/JD13/JD18/JD19 各执行一次真实 DeepSeek 调用。六份 expected/actual outcome 全部一致：三份 ready、一份 `limited_basis`、一份 `too_many_items`、一份 `no_items`；11/11 个定向自由文本重点命中，JD08“激活”命中，结构化覆盖 13/13，擅自 required、明显重复、不可追溯和宣传福利误识别均为 0。实际响应模型名均为 `deepseek-v4-flash`，input/output token 为 7,764/1,209。独立 debug 记录保存原始结构化响应且不允许形成质量结论；42 项合同与 10 项验收器测试通过。本轮没有修改生产业务代码、前端或 migration。

此前误执行的 20 份 JD 真实调用无人工重跑，实际模型名均为 `deepseek-v4-flash`，input/output token 为 `23,761/5,212`。18/18 正常 JD 全部可用，自由文本主要要求 42/42，JD08“激活”命中，结构化明确要求 63/63，擅自 required、明显重复、不可追溯和宣传福利误识别均为 0。JD19 正确 `no_items`，但 JD18 把明确岗位要求误判为 `non_requirement/context` 后被 Service 提前拒绝，没有形成预期 `too_many_items`，所以边界仅 1/2 正确；JD16 形成可用 `limited_basis`，与冻结逐样本 `ready` 元数据存在记录差异。独立结果 `docs/stages/stage7/2026-08-21-stage7-step9-jd-decomposition-results.json` 保持原样，只作为历史审计，不替代重新授权的 9-I。

整理后的 9-I 详细合同统一写在 `docs/stages/stage7/2026-08-21-stage7-step9-jd-decomposition-quality-remediation-design.md` 第 14.10 节。它先运行零调用 dry-run，再产生新的 JD revalidation 结果；随后对有本轮可用计划的筛选样本各评价 3 次，缺少计划的样本标记上游阻塞并留在总体分母。JD 指标正式判定小步骤 9；合法报告率、方向、稳定性、安全、证据和幻觉只形成诊断值，不能标记步骤 10—12 完成。

9-I 已按该合同执行：dry-run 为 0 次调用、0 次写入；正式调用为 20 次 JD + 60 次筛选，80/80 均收到 `deepseek-v4-flash` 完整响应，input/output token 合计 `144,127/66,881`，没有额外基础设施调用。18/18 正常 JD 全部可用，主要要求 42/42、结构化覆盖 63/63，required/重复/追溯/宣传四类错误均为 0；JD19 正确 `no_items`，但 JD18 再次被提前拒绝为 `JOB_EVALUATION_PLAN_BUSINESS_VALIDATION_FAILED`，未形成 `too_many_items`，因此小步骤 9 门禁失败。JD16 的实际 3 项计划正确 `limited_basis`，但与冻结逐样本 `ready` 记录不同，后续也需要先确认记录口径。

下游 20 组均有本轮可用计划，上游阻塞 0，每组恰好评价 3 次。至少一份合法报告 9/20，低于旧基线 10/20；总体方向一致 9/20（45%），低于旧基线 50%；三次全部合法 1/20，低于旧基线 5/20。45 次拒绝主要来自 evidence 25、experience_fact 11、bonus 5、tradeoff 3 和其他模型不服从 1。最终 15 份合法报告的正分/亮点证据均可定位，严重事实、敏感属性评分、招聘决定、投递后事实误用均为 0；被拒绝响应仍暴露 33 次事实 grounding/年限类严重问题、1 项亮点重复和 4 项亮点无关。该数据只标记为 `diagnostic`，不代表步骤 10—12 完成。

阶段 6 整改和新的阶段 7 设计通过后，才重新确定小步骤 9—13 的样本与执行口径；合法报告率、方向一致性、三次稳定性和浏览器完整复验仍不能跳过。原稳定性门槛与质量数据保留为设计参考，但不得直接拿旧 `description + JobRequirementsV1` 样本冒充新合同验收。阶段 7 通过前不得进入产品阶段 8。

## 12. 最近验证基线

- 阶段 7 AI 前端 3 个专项脚本通过；前端全部 19 个 Node 测试脚本通过；TypeScript 严格检查通过；Vite 5.4.21 生产构建通过，共转换 3124 个模块。
- 小步骤 9-G 的 42 项 step9 合同、139 项 JobEvaluationPlan/Screening/验收器定向、140 项岗位及业务隔离和 32 项 migration 测试通过；后端全量 677 项 `pytest` 在 33.52 秒内通过，另有 1 条既有 PyPDF2 弃用 warning。
- 小步骤 9-H 定向 dry-run 为 0 次调用、0 次写入；真实定向调用 6/6 完成且合同满足 6/6，验收器 10/10 与冻结 step9 合同 42/42 通过。独立结果为 `docs/stages/stage7/2026-08-21-stage7-step9-jd-decomposition-debug-results.json`，不能作为 9-I 正式质量结论。
- 此前误执行的 20 次 JD 调用形成 18/18 正常 JD 可用、主要要求 42/42、结构化覆盖 63/63，安全追溯类错误均为 0；JD18 边界失败层不符合预期。独立结果保留为历史诊断，不作为整理后 9-I 的正式结论。
- Alembic 代码 head 与 PostgreSQL current 均为 `e4c7a1b9d632`；9-E 已完成真实数据库 migration 往返，9-F 真实 PostgreSQL 服务回归验证了新旧计划并存和历史报告外键，9-G 重跑实际 PostgreSQL 服务与 migration 回归。`alembic check` 返回 `No new upgrade operations detected`；9-G 没有新增或修改 migration。
- 合并 9-I dry-run 固定选中 20 份 JD、20 组 JD/Resume、high 8/partial 6/low 6 人工标签和每组 3 次计划，记录 0 次模型调用、0 次结果写入；真实计数严格执行 20 次 JD 和 60 次筛选，额外调用 0。新增验收器 19/19、受影响专项 122/122、后端全量 687/687 通过，另有 1 条既有 PyPDF2 弃用 warning。
- 9-I 正式 JD 结果为 18/18 正常 JD 可用、主要要求 42/42、JD08“激活”通过、结构化覆盖 63/63，required/重复/追溯/宣传错误均为 0；JD18 未形成预期 `too_many_items`，所以边界 1/2、`step9_quality_gate_passed=false`。JD 结果为 `2026-08-21-stage7-step9-jd-decomposition-revalidation-results.json`。
- 9-I 下游诊断为：上游阻塞 0，20 组各 3 次；至少一份合法报告 9/20，合法次数分布 0/3=11、1/3=4、2/3=4、3/3=1；总体方向 9/20，三次全部合法 1/20 且其分差 ≤5。结果为 `2026-08-21-stage7-step9-full-chain-diagnostic-results.json/.md`，状态仅为 `diagnostic`。
- PostgreSQL、Redis、Chroma 均运行；PostgreSQL healthy 并接受连接，Redis 返回 `PONG`，Chroma heartbeat 返回 HTTP 200。
- OpenAPI 共 64 条 method+path，重复为 0；当前计划、Application 与筛选路由没有重复注册。
- 运行时扫描没有恢复旧 Rubric、ScreeningResult、五维权重、证据覆盖率或 Python 加权评分；阶段 7 AI UI 没有 `dangerouslySetInnerHTML`、Resume 原文、原始模型响应、API Key、内部异常或敏感属性展示；Git 跟踪文件没有疑似真实 Key。
- 最终计分轮对 20 份虚构 JD 真实调用 DeepSeek 20 次：16 份形成 ready/limited 计划，0 项和 >30 项边界各 1 份正确失败，另 2 份中英文岗位内容失败；全部样本自由文本主要要求识别 35/42（83.33%），结构化覆盖在成功计划中为 100%，擅自新增 required、明显重复和宣传福利误识别均为 0。
- 20 组人工标签在调用前固定；17 组进入三次评价，共 51 次真实 DeepSeek 调用。10/20 至少形成一份合法且方向一致的报告，总体方向一致率 50%，低于 80%。仅 5 组连续三次通过严格校验，其中 4/5 最大分差不超过 5，低于 90%。
- 原正式质量验收的 23 份合法报告中，115 个正分基础事项均有可定位证据，敏感属性评分和招聘决定建议为 0；当时 2 个样本出现严重年限事实错误，额外亮点与基础事项重复至少涉及 2 个样本，因此原安全验收直接失败。整改后的 SR05/SR15 最终计数轮各 3 次真实 DeepSeek 调用共 6 次，模型响应 6/6，严重年限事实冲突 0；SR15 合法报告 3/3，SR05 因模型仍把年限放进综合摘要而 0/3，总体合法报告 3/6。
- Playwright MCP 实际打开 `/app/jobs` 和 `/app/screening`，使用虚构脱敏夹具覆盖计划四状态、筛选状态矩阵、报告、单人/批量动作、约 4 秒轮询、1440×900/820×1180/390×844 布局及键盘检查。60 项中 57 通过、2 失败、1 未验证、0 阻塞；完整脚本观察到 103 个 API 请求、HTTP 错误 0，终态/关闭/离开后轮询均停止。
- 浏览器最小修复包括计划抽屉关闭回焦、静态 Modal 改为上下文实例、空 `tradeoff_reason` 不再渲染空壳。修复后 Modal 警告为 0、回焦与空壳场景通过；仍有 1 条 Drawer 焦点哨兵 `aria-hidden` 警告，普通初筛真实数据库持久化幂等未在浏览器中验证。
- 本轮全部最小修复还包括 required 单字误判、JD 逐字/英文约束 Prompt v3、筛选嵌套 evidence/bonus Prompt v2，以及固定投递时间整改后的筛选 Prompt v3 / Schema 2.0。完整证据见 `docs/stages/stage7/2026-08-20-stage7-quality-acceptance.md`、原质量验收 JSON、`2026-08-21-stage7-time-fact-revalidation-results.json` 与 `browser-acceptance-evidence/`。
- `git diff --check` 通过。上述结果证明自动化、迁移、固定投递时间链路和年限事实防线稳定，并证明大部分前端状态与交互按合同工作；9-I 还证明新 JD 追溯/召回合同在 18 份正常样本上可用，但 JD18 边界、总体报告成功率和三次稳定性仍失败。它明确不能证明阶段 7 AI 质量合格、招聘准确、真实数据库端到端幂等或浏览器子验收全通过；本次没有重新执行浏览器验收。
- 后续顺序已调整为：最终确认阶段 6 五段式设计 → 6R-A—6R-D 逐批实施与验收 → 重新设计并确认阶段 7 五段式评价计划 → 重新安排 JD、合法报告率、方向、稳定性和浏览器完整复验。原质量结果及误执行结果保持不变，只作历史对比，不作为新合同计数。

开始下一步前仍须重新检查实际 Git 状态、测试数量、Alembic revision 和数据库状态，不能只依赖这里的历史基线。

## 13. 新对话恢复方式

1. 阅读 `CLAUDE.md`。
2. 阅读本文件。
3. 根据 `docs/DOCUMENT_INDEX.md` 判断任务需要哪些补充文档。
4. 修改阶段 7 业务代码前，完整阅读阶段 7 当前设计。
5. 执行任何修改前检查 `git status` 和相关差异，保护现有工作区修改。
