# 项目当前状态

> 最新更新：2026-08-26
>
> 本文件只记录“现在是什么状态、下一步做什么”。完整开发过程已归档到 `docs/archive/history/2026-08-20-project-history.md`，不再作为新对话的默认阅读材料。

## 1. 当前结论

- 项目正在建设新版招聘主链，旧 React + FastAPI + SQLite + Mock LLM 演示系统已经退役。
- 阶段 4“简历上传与原文提取”和阶段 5“AI 结构化草稿”已经完成；阶段 6 五段式 JD 整改的 6R-A—6R-D 已全部完成，自动化、真实 PostgreSQL/API 和 Microsoft Playwright 三档浏览器验收通过。
- 阶段 7”Application 与 AI 初筛底座”已有 Application、Resume 隔离、异步运行、幂等、当前成功报告、固定投递时间、React 报告和 HR 决策历史等可复用能力。4.0 正式 20 份计划质量只通过 `15/20`，因此 7R4-I/J 从未获准继续。用户随后重新确认产品目标，决定不再按 `RequirementFact + EvaluationCriterion` 做原子级 JD 拆解，改为 5.0”完整 JD + HR 可编辑轻量评价清单 + 独立简历报告”：通常约 5—12 个评价点、每项 0—10 分、AI 直接给总体 0—100 分、不采用权重、HR 保留最终决定。5.0 业务合同已经逐项确认并写入新权威设计；7R5-A—7R5-D 已逐批确认并完成。公开计划入口现已使用 5.0，HR 草稿编辑、新增/删除/合并、稳定 ID、warning 重算、乐观并发、确认和只读版本历史已接入 API 与 PostgreSQL；来源、安全、擅自新增和越权继续硬失败。当前 Alembic head 为 `b4c6d8e0f212`，最近全套为 1100 passed、32 xfailed（严格，属于 7R5-E/F）、419 subtests passed、0 failures。当前停止等待用户确认 7R5-E。
- 小步骤 9-I 已完成 20 次 JD 正式复验和 60 次下游真实诊断。18/18 正常 JD 可用、主要要求与结构化覆盖均为 100%，但 JD18 没有形成预期 `too_many_items`，因此 `step9_quality_gate_passed=false`，小步骤 9 仍未通过；下游诊断也仅有 9/20 至少一份合法报告、1/20 三次全部合法。
- Application、Resume 隔离、HR 内部录入和 HR 决策等公共能力继续保留。
- 旧 Rubric、五维权重、确定性评分、`unknown`、证据覆盖率、Python 加权总分和多报告历史方案已经废弃。
- 阶段 7 暂停前的公共业务方案已经确认并实现：旧 Rubric 删除、`JobEvaluationPlan`、严格单次评价、异步运行、幂等、当前成功报告替换、React 完整报告交互以及固定投递时间事实已经完成。SR05/SR15 最终 6 次真实 DeepSeek 定向复验的严重年限事实冲突为 0，但合法报告只有 3/6；原 Playwright 浏览器验收仍为 60 项中 57 通过、2 失败、1 未验证、0 阻塞。五段式计划 3.0 的程序生成链已在 Fake 下完成，不代表真实模型质量、Screening、React 或阶段 7 整体通过。

## 2. 当前权威文档

文档职责和按任务阅读规则统一见 `docs/DOCUMENT_INDEX.md`。

当前阶段的权威顺序是：

1. 阶段 7 轻量评价清单 5.0 当前设计：`docs/stages/stage7/2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`，负责当前产品目标、轻量清单、无权重评分、报告、状态、数据、安全、验收和待确认的 7R5-A—7R5-J 顺序
2. 阶段 7 评价计划 4.0 历史实现与失败证据：`docs/stages/stage7/2026-08-24-stage7-job-evaluation-plan-v4-redesign.md`，保留 RequirementFact、三/四次调用、HR2 `6/6` 和正式 20 份 `15/20` 的不可覆盖记录，不再授权新增实现
3. 阶段 7 五段式计划 3.0 记录：`docs/stages/stage7/2026-08-22-stage7-five-section-job-evaluation-plan-redesign.md`，只负责已完成实现事实和历史失败证据
4. 阶段 7 原设计：`docs/stages/stage7/2026-08-20-stage7-jd-driven-ai-screening-redesign.md`，其已实现的 Application、Resume、异步运行、报告、时间事实和 HR 决策底座继续有效
5. 阶段 6 五段式 JD 整改：`docs/stages/stage6/2026-08-21-stage6-five-section-jd-remediation-design.md`
6. 阶段 6 原设计：`docs/stages/stage6/2026-08-15-stage6-structured-job-management-design.md`，除被五段式补充替代的 JD 字段合同外继续有效
7. 本文件：只负责当前进度、工作区风险和下一步
8. `CLAUDE.md`：项目长期架构、技术栈和稳定约束
9. `docs/planning/implementation-plan.md`：跨阶段实施顺序
10. `docs/planning/2026-08-14-post-stage5-product-roadmap.md`：阶段 5 后产品路线
11. `docs/architecture/2026-07-15-hr-agent-platform-design.md`：总体架构背景

发生冲突时，当前阶段专项设计优先于旧总体示例和历史记录。归档文档不具有当前业务权威性。

## 3. 当前阶段 7 方案摘要

> 当前说明：5.0 是新增实现的目标合同，现有运行代码仍主要是 4.0。4.0 的正式质量失败和 1.0—4.0 历史数据继续保留，但不能继续按 4.0 扩展。下文第 4—9 节记录可复用的既有能力和历史实现基线；若与 5.0 设计冲突，以 5.0 为准。

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

- 新增 `ScreeningReport` 当前成功报告和 `ScreeningRun` 必要运行日志；每个 Application 由数据库唯一约束保护最多一份当前报告，运行日志不保存完整旧报告、原始模型响应或未脱敏 Resume。
- 使用稳定 JSON 序列化和 SHA-256 组合 Application、`Application.applied_at`、`Asia/Shanghai`、经历时间事实/规则版本、JD、当前 Resume、当前 ready 评价计划及 Prompt/模型/Schema/脱敏版本；普通请求复用相同报告或运行，主动“重新评估”即使输入相同也会建立新运行。
- 采用 PostgreSQL 持久运行表加 FastAPI 生命周期轮询器作为当前架构下的最小可靠后台机制；`FOR UPDATE SKIP LOCKED`、部分唯一索引和租约恢复共同保护多进程认领、并发重复及服务重启后的可解释状态，没有引入 Celery、RQ、Arq 或无持久状态的任务假象。
- Application 提交、Resume 解析完成、岗位重新开放和4.0计划确认会在相关业务提交后协调首次自动初筛或等待任务；HTTP 请求不等待筛选模型，触发失败不回滚已经提交的 Candidate、Resume、Application 或 Job。
- Resume/计划不可用分别保留 `waiting_resume/waiting_plan`；计划原因稳定区分缺失、生成中、失败、过期和合同过期，岗位关闭以 `job_closed` 暂停未开始任务且允许 `running` 完成；岗位重开按最新输入恢复仍然有效的自动任务和人工重新评估。
- 只有 active Application、开放 Job、可用 Resume 与当前合法4.0 ready计划能够 queued；1.0—3.0只读且阻止新筛选，`pending_confirmation`使用独立`plan_pending_confirmation`等待原因。运行中输入变化以 `SCREENING_INPUT_OUTDATED_DURING_RUN` 失败，不替换旧报告。revision `d6f4a2b8e913` 扩展 PostgreSQL 等待原因约束并提供有数据降级阻断。
- 成功响应会重新核对最新 Resume、JD 和计划，只在严格 Schema/业务校验通过后，以同一数据库事务替换当前报告并把运行标记成功；迟到响应、内容失败或数据库提交失败都保留旧报告。
- 网络、限流、超时和模型服务端故障最多额外重试 1 次；认证、配额、JSON、Schema、事项、证据、安全及业务内容错误不自动重试，SDK 自动重试仍关闭。
- Resume、JD 或当前计划变化只把旧报告标记过期，不删除、不自动批量重评；普通 Prompt、模型或 Schema 版本升级不会自动使历史报告过期。
- 当前 4.0 代码已有普通触发、单人重新评估、同岗位 1—20 人批量重新评估和切换当前 Resume 的最小 `/api/v2` 接口；5.0 将复用独立提交和部分失败语义，并把阶段 7 批量上限收紧为 5。
- AI 初筛链路不写 `hr_decision`、`recruitment_stage` 或 `lifecycle_status`。当前仍沿用内部开发接口边界，没有临时伪造登录/RBAC。
- `ScreeningReport` 额外审计评价基准、时区、事实规则版本和成功评价使用的完整时间事实快照；`ScreeningRun` 审计评价基准、时区、规则版本和时间事实指纹，不保存完整 Resume 或模型原始响应。
- 新迁移 `d9a1f4c7e820` 只向既有 `ScreeningReport`/`ScreeningRun` 增加上述审计字段。真实数据库没有历史行；migration 对假设存在的旧行也只从关联 `Application.applied_at` 回填基准，不伪造旧事实快照。

## 8. 已完成的 React 完整报告与交互

- 新增严格 TypeScript 合同和集中 `v2Http` Service，覆盖当前 JobEvaluationPlan、Screening 状态/报告/运行、普通初筛、单人重新评估、同岗位批量重新评估和切换当前 Resume；组件中不散落裸 `fetch`，也不使用 `any` 绕过合同。
- 岗位列表的评价计划抽屉已接入 4.0：按 `EvaluationCriterion` 组织、逐 `RequirementFact` 展示 ID/分类/priority/主原文和全部多来源，支持 `pending_confirmation` 无正文确认、五类 warning、coverage/audit、生成中/ready/failed/outdated/旧合同/关闭状态和历史只读。没有计划编辑、criterion 分数/权重、自动淘汰或同输入 ready 重生成；修正只能回到 JD 编辑。
- AI 初筛工作台读取每个 Application 当前 Screening 状态；报告抽屉展示建议分、程序标签、综合评价、逐项分数/理由/计算说明/折叠证据、额外亮点、综合权衡、面试问题、版本、生成时间和“按该申请 YYYY-MM-DD 的投递时间计算”的评价基准。旧报告缺字段时诚实显示“历史报告未记录评价基准”。
- 0 分固定解释为“当前简历未体现”，AI 分数和标签固定说明为辅助建议；查看、普通初筛、重新评估和批量操作均不调用 HR 决策接口，不修改 `hr_decision`、`recruitment_stage` 或 `lifecycle_status`。
- 报告过期时继续展示旧报告和 Resume/JD/评价计划变化原因；现有 4.0 页面在计划与报告一致时按 criterion 分组并逐 fact 展示，5.0 将改为直接逐评价点评分。旧计划不可读取或 ID 不一致时仍必须诚实回退，不能使用新计划内容冒充旧报告。
- `queued/running` 使用 4 秒最小轮询；终态、关闭抽屉或组件卸载后停止。请求序号阻止迟到响应覆盖新状态，递归 `setTimeout` 保证只保留一个定时器。
- 评价计划 `generating` 同样使用单个 4 秒递归轮询，在 ready/failed/outdated、关闭抽屉、关闭岗位或组件卸载时停止；前端只停止查询，不声称取消后台任务。
- 普通初筛明确允许复用报告或运行；单人“重新评估”需要确认，新运行期间及失败后继续展示旧成功报告；岗位关闭时禁用开始和重新评估。
- 现有 AI 初筛工作台支持同一开放岗位 1—20 个 Application 批量选择；这是 4.0 实现基线，不是 5.0 产品合同。7R5-F/G 必须把上限收紧为 5，并继续拒绝空选、重复、跨岗位和重复提交。
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

- 当前分支是 `2lcj`，本轮基线 HEAD 与 `origin/2lcj` 均为 `16ae835f50b9cd7f67f08ce2a8fbf12eaf2f3082`。开始 7R5-D 时工作区已有本对话中已完成但未提交的 7R5-C1 修改；当前未提交差异只包含 7R5-C1 与本轮 7R5-D 的 Prompt/配置、Schema、Service、API、Model、migration、专项测试和状态文档，没有发现范围外用户修改。没有实现 5.0 Screening 报告、React 或真实 DeepSeek 调用，也没有修改 4.0 历史质量结果文件。
- 项目由旧电脑压缩迁移后，旧 `.venv` 因保存 `C:\Users\GYAI\...Python311` 绝对路径而失效。本轮已用本机 Python 3.11.9 原地重建 `.venv`，安装 `backend/requirements.txt` 和本地测试依赖 pytest 9.1.1；`.venv` 继续由 Git 忽略，不提交、不再跨电脑复制。
- 本机 PostgreSQL Docker 卷原停在 `b4e8c2d7f913`，且保留 1 个 Job、2 个 Candidate、2 个 Resume 和 1 个 3.0 failed 计划。升级前已生成 `data/backups/pre_a3b5c7d9e101_20260826.dump`，SHA-256 为 `F8F8AD2EB6C3E6D399562D7DDC2146C262A87A4D9BDBC85FD858325C0D962C4C`。7R5-D 新增 revision `b4c6d8e0f212` 并完成真实 `b4 → a3 → b4` 往返；计划表保持 1 行，整行内容 MD5 往返前后均为 `0819ebafc4168daf6b99d8a848911221`，最终 `current=head` 且 `alembic check` 无待生成操作。
- 4.0 的 7R4-A—7R4-H2 均停在各自历史停止点；HR2 定向为 `6/6`，正式 H2 为 `15/20` 且失败。7R4-I/J 永久停止，不再通过追加 4.0 样本整改继续推进；所有既有结果只作历史证据。
- 用户已经逐项确认 5.0 的产品目标、轻量评价清单、无权重评分、单人/最多 5 人批量、状态、审计、隐私和验收标准。5.0 原权威设计和 7R5-A—7R5-J 顺序已获整体确认，7R5-A—7R5-D 已分别确认并完成；Schema、Model、PostgreSQL、纯单次生成 Prompt/Adapter/Service、importance warning、API、HR 编辑/确认与并发版本已具备 5.0 能力。5.0 Screening 报告与运行接线和 React 仍未实施。
- 用户已最终确认并完成小步骤 9 的 9-A—9-I。此前助手误解用户意图产生的独立 20 份 JD 结果继续保留为历史诊断；正式 9-I 已使用新路径独立落盘，没有复用或覆盖该记录。JD18 的正式边界失败和当时返回阶段 6 整改的决定均为历史事实；当前新增实现依据已经切换为 5.0 设计。
- 用户已最终确认五段式 JD 业务合同和 6R-A—6R-D 顺序；四个批次已经全部完成并通过 6R-D 验收。
- 用户明确授权无备份删除唯一 Job #19；该历史操作不能从当前数据库直接恢复。7R4-B开始时正式开发库revision为 `e4c7a1b9d632`，四张直接相关表计数均为0；7R4-E结束时`current=head=d6f4a2b8e913`、`alembic check`通过，相关业务表均为0。d6已在正式空库完成真实`downgrade c7 -> upgrade d6`往返，没有写入或删除业务行。
- 后续不得恢复旧 Rubric、旧 ScreeningResult 或嵌入 Application 的 AI 状态字段。
- 新功能应复用 Candidate、Application、Resume、Job、StageHistory、Report 和通用 DeepSeek/数据库基础设施。

## 11. 当前唯一下一步

5.0 权威设计已经写入 `docs/stages/stage7/2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`。它保留现有 Application、异步运行、报告历史、投递时间和 HR 决策底座，只替换过度精细的 4.0 计划生成与逐 fact 接线。核心合同是：

- 完整 JD 作为上下文，AI 一次生成通常约 5—12 个主要评价点；
- HR 可以编辑、新增、删除、合并并确认，JD 外新增项明确标为“HR 补充”；
- 每项 0—10 分，AI 直接给总体 0—100 分，不使用权重或 Python 加权总分；
- 同岗位每名候选人独立评价，阶段 7 小批量最多 5 人；
- HR 决策始终独立，敏感属性和自动招聘决定为零容忍；
- 真实验收为 10 份新鲜 JD、20 组新鲜 JD/Resume、其中 5 组各 3 次稳定性，以及真实 PostgreSQL/API/浏览器。

7R5-A”合同测试与离线基线”、7R5-B”计划 Schema / Model / migration”、7R5-C”单次计划生成链”、7R5-C1”importance 原文语义与 HR 复核 warning”和 7R5-D”计划编辑、确认、版本和 API”均已完成。数据库和代码迁移头为 `b4c6d8e0f212`；1.0—4.0 历史计划保持公开只读兼容，没有回填或改写旧行。公开 5.0 生成链继续只做一次业务模型调用；AI 成功草稿进入 pending，HR 可以原子编辑、新增/删除/合并、处理 warning 并用版本号确认，ready 后再次编辑形成新历史行。最近全量为 1100 passed、32 xfailed（严格，属于 7R5-E/F）、419 subtests passed、0 failures；真实 DeepSeek 调用和费用均为 0。

当前唯一下一步是等待用户明确确认权威设计第 28 节 7R5-E”5.0 初筛报告后端”。未经确认不得修改筛选报告 Schema/Prompt/Adapter/Service 或报告持久化，不得进入 7R5-F、React 或真实 DeepSeek。

## 12. 最近验证基线

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
