# 阶段 9 实施记录

> 日期：2026-09-02  
> 当前状态：9A—9F 已完成；项目负责人于 2026-09-05 确认最终验收通过，阶段 9 已关闭
> 业务合同：以 `2026-09-02-stage9-interview-offer-hiring-pipeline-design.md` 为唯一来源

本文只记录阶段 9 实际做过的修改、验证、证明边界、风险和下一步，不重新定义状态、字段语义、权限或验收标准。

## 9A：合同与 migration

### 实际修改

| 层级 | 文件 | 职责与本次效果 |
| --- | --- | --- |
| Schema | `backend/app/schemas/application.py`、`stage_history.py` | 扩展阶段枚举，新增最终结果合同、审计前后值、来源关联和受控 reason code；保留四组状态职责独立。 |
| Schema | `backend/app/schemas/interview.py`、`offer.py`、`__init__.py` | 新增面试与 Offer 输入/输出合同；薪资金额和月数使用 Decimal 校验，不接收 float。 |
| Model | `backend/app/models/application.py`、`stage_history.py` | 增加最终结果、生命周期/最终结果审计字段、来源外键、关系、CHECK 和索引。 |
| Model | `backend/app/models/interview_record.py`、`offer_record.py`、`__init__.py` | 新增 InterviewRecord、OfferRecord ORM、关系、唯一约束、普通索引和部分唯一索引；薪资落为 PostgreSQL NUMERIC。 |
| Service 兼容 | `backend/app/services/application_decision_service.py`、`application_intake_service.py`、`public_application_service.py` | 让既有创建、初筛决定、撤销和作废路径写入符合新合同的最终结果及 StageHistory 前后值；未新增阶段 9 Service 或 API。 |
| PostgreSQL | `backend/migrations/versions/b9e2f4a6c801_add_stage9_pipeline_contract.py` | 在既有 head 后新增一条向前 migration；预检无法解释的 ended 数据，创建新结构，只对明确的旧初筛淘汰组合回填，并提供带数据保护的 downgrade。 |
| 测试 | `backend/tests/schemas/test_stage9_pipeline.py`、`models/test_stage9_pipeline_models.py`、`migrations/test_stage9_pipeline_migration.py` | 直接覆盖枚举、Decimal、Schema、ORM、约束声明、migration 前置检查和升级/降级结构。 |
| 回归测试 | `backend/tests/services/test_application_decision_service.py`、`test_public_application_service_postgres.py`、`test_screening_plan_v3_gate_contract.py`、`test_screening_service.py`、`backend/tests/test_stage7_v5_hr_decision_contract.py` | 更新既有测试夹具和断言，使阶段 4—8 旧路径继续满足 9A 合同；没有删除断言或降低门槛。 |
| 文档 | 阶段 9 设计、本文、`docs/DOCUMENT_INDEX.md`、`PROJECT_STATE.md` 和 planning 文档 | 记录设计已确认、9A 实施结果和下一步；业务规则仍只维护在专项设计。 |

### Migration 与真实 PostgreSQL 验证

实施前重新只读核对：开发库 revision 为 `a8d4f2c7e901 (head)`，`alembic check` 无漂移；PostgreSQL 可连接；只有 1 条 `active / screening_passed / passed` Application，没有既有 ended 行，也没有 InterviewRecord/OfferRecord 表，因此不存在需要猜测的回填。

随机临时 PostgreSQL 实际完成：

- 用虚构数据证明无法解释的 ended Application 会让 migration 以 `STAGE9_UNEXPLAINED_ENDED_APPLICATIONS` 中止，revision 和旧结构保持不变；
- 完成 `upgrade` 到新 head、`downgrade` 回旧 head、再次 `upgrade`；旧 Application 和 StageHistory 行数在往返中保持；
- 实测同一 Application + 面试轮次唯一、同一 Application 最多一个 scheduled 面试、同一 Application + Offer version 唯一、同一 Application 最多一个 draft/sent/accepted Offer；
- 实测时长、薪资、薪资月数、StageHistory 来源外键、Application 生命周期/最终结果和 hired 组合 CHECK；
- 通过合法的取消/拒绝后再创建下一条，证明部分唯一索引只限制当前活动记录；
- 用 `pg_typeof` 确认薪资字段为 `numeric`；所有随机临时数据库最后均已删除。

开发 PostgreSQL 在安全预检通过后只执行前向升级到 `b9e2f4a6c801`。升级前后原有数据行数一致：Candidate 1、Job 1、Resume 1、Application 1、StageHistory 1、ScreeningReport 1、ScreeningRun 1，两个阶段 8 表为 0；新增 InterviewRecord 和 OfferRecord 表为 0。现有 Application 仍为 `active / screening_passed / passed / final_outcome=NULL`，没有写入真实候选人、面试或薪资数据。

### 自动化测试

- 9A 直接相关测试：`117 passed, 94 subtests passed`；
- 两个旧 ended 测试夹具修正后的定向复测：`2 passed`；
- 完整后端回归：`1395 passed, 486 subtests passed`，保留 2 个既有非阻塞 warning；
- 最终 `alembic current` 与 `alembic heads` 均为 `b9e2f4a6c801 (head)`，`alembic check` 无待生成操作。

### 能够证明

- 代码枚举、Schema、ORM 与 Alembic 结构对 9A 合同一致；
- migration 会阻止无法解释的历史 ended 数据，不会静默猜测；明确的旧初筛淘汰组合具备确定回填路径；
- 临时 PostgreSQL 上升级/降级可往返，关键 CHECK、外键、唯一约束和部分唯一索引由数据库真实执行；
- 开发库已到新 head，原有行数和状态组合未被改写；阶段 4—8 后端回归未发现破坏。

### 不能证明

- 截至 9A 结束时，9B 之后的面试 Service/API、事务并发、权限和审计流程尚未实现；
- Offer、录取、入职、前端收口、AI 标签和统计链路尚未实现或验收；
- 开发库没有旧 rejected 样本，因此这里只证明了临时库中的回填行为，没有在开发库实际回填业务行；
- 本批次没有浏览器验收、真实 Worker、DeepSeek 调用或生产高并发/大数据量验证。

### 遗留风险与下一步

- downgrade 会在存在阶段 9 表数据、阶段 9 新阶段/审计值或无法安全还原的数据时主动拒绝，不能把它当作无损生产回滚方案；
- 正式环境执行 migration 前仍需重复同一只读数据预检；
- 9A 完成时的下一步是 9B“面试后端”；9B 的实际结果见下节。

## 9B：面试后端

### 实际修改

| 层级 | 文件 | 职责与本次效果 |
| --- | --- | --- |
| Schema | `backend/app/schemas/interview.py`、`recruitment_timeline.py`、`__init__.py` | 新增安排、改期、取消、未到场、首次反馈、反馈更正和安全时间线合同；严格校验 version、确认、原因、数组、URL 和真实 IANA 时区。 |
| API | `backend/app/api/interviews.py`、`app/main.py` | 注册阶段 9 设计中的 7 个面试写/读路由和 1 个时间线路由；只负责 HTTP、严格请求、稳定错误及确认入口，不直接修改 ORM。 |
| Service | `backend/app/services/interview_service.py` | 锁定 Application 和 InterviewRecord，执行多轮面试状态转换、乐观并发、幂等、同事务 Application/面试/StageHistory/ActivityLog 写入和失败回滚。 |
| Query Service | `backend/app/services/recruitment_timeline_service.py` | 合并 StageHistory 与受控面试 ActivityLog，返回显式只读字段；过滤任意 JSONB、会议链接和反馈正文。 |
| 运行依赖 | `backend/requirements.txt` | 固定 `tzdata==2026.3`，使 Windows 环境也能用标准库验证真实 IANA 时区，而不是只检查字符串外形。 |
| 自动化 | `backend/tests/api/test_interviews.py`、`test_interviews_postgres.py`、`backend/tests/services/test_interview_service_postgres.py`、`test_interview_service_concurrency_postgres.py`、`backend/tests/schemas/test_stage9_pipeline.py` | 覆盖 Schema、路由、稳定错误、真实 API、多轮状态、事务回滚、时间线安全、幂等、数据库行锁和并发 version 冲突。 |

### 实际行为与分层结果

- 只有 `active / screening_passed / passed` 的 Application 能创建第一轮面试；首轮创建在同一事务把 Application 推进到 interview。
- 后续轮次必须连续；上一轮明确进入下一轮、取消或未到场后才允许安排下一轮。数据库部分唯一索引继续兜底同一 Application 最多一个 scheduled 面试。
- 普通改期只改当前 InterviewRecord，增加 version 并写受控 ActivityLog，不伪造 Application 阶段变化。
- 取消和未到场要求确认与原因，但不会自动淘汰；重复提交相同终态请求返回原结果，不重复写审计。
- 首次反馈把面试标记为 completed；pending 和 next_round 保持 Application 在 interview，proceed_offer 原子推进到 offer，rejected 或 candidate_withdrew 按设计结束流程，并始终保留原 `hr_decision=passed`。
- 已提交反馈的文字更正使用 PUT、expected_version、确认和更正原因；已生效的非 pending 决定不能靠普通反馈编辑改写，必须等待后续专用重新打开流程。
- 所有业务写入使用本地未认证 HR 标签；9B 没有虚构出生产级登录或权限能力。

### 自动化与真实 PostgreSQL 结果

- 9A + 9B 直接相关套件：`35 passed, 35 subtests passed`；
- 完整后端回归：`1412 passed, 502 subtests passed`，保留 PyPDF2 弃用和既有异步连接清理 2 个非阻塞 warning；
- 真实 API + PostgreSQL 已验证安排、改期、反馈、进入 Offer、列表、时间线和确认失败不写库；
- 独立 PostgreSQL 会话同时创建第一轮时只有一个成功，另一个稳定成为 `INTERVIEW_ROUND_CONFLICT`；
- 独立 PostgreSQL 会话同时用相同 expected_version 改期时只有一个成功，另一个稳定成为 `INTERVIEW_VERSION_CONFLICT`，最终只增加一次 version 和一条改期审计；
- 注入 ActivityLog 写入失败后，InterviewRecord、Application 和 StageHistory 同时回滚，没有半状态；
- 测试只使用虚构 Candidate、面试官、链接和反馈，事务测试回滚，并发测试按精确主键清理。最终开发库 InterviewRecord、OfferRecord、ActivityLog 均为 0 行，测试身份残留为 0。

最终 `alembic current` 与 `alembic heads` 仍为 `b9e2f4a6c801 (head)`，`alembic check` 无待生成操作。9B 不需要新 migration，也没有改写 9A 数据库合同。原开发数据仍为 1 条 `active / screening_passed / passed / final_outcome=NULL` Application、1 条 StageHistory、1 条 ScreeningReport 和 1 条 ScreeningRun。

### 能够证明

- 9B 面试 Schema、API、Service、ORM 和 PostgreSQL 约束能够组成真实可运行链路；
- Application 行锁、InterviewRecord 行锁、expected_version 和数据库唯一约束可以共同处理双击与两个 HR 并发；
- 面试反馈推进 Offer、面试淘汰和候选人退出时不会改写阶段 7 的 HR 初筛决定；
- 事务失败不会留下已推进但无审计的 Application，也不会留下孤立面试记录；
- 时间线只返回显式安全字段，不把 ActivityLog 任意 detail、会议链接或反馈正文原样交给前端解释；
- 阶段 4—8 与 9A 的完整后端回归没有发现破坏。

### 不能证明与遗留风险

- 当前内部应用仍没有登录认证，`本地 HR（未认证）` 只是作品集审计标签，不是生产权限控制；
- 9C 的 AI 初筛中心列表聚合、导航/详情前端和确定性 AI 标签尚未实现；
- Offer、录取、入职、阶段 9 重新打开和招聘统计仍属于 9D—9E；
- 第一版仍没有邮件、短信、日历、会议系统或独立面试官账号；
- 本批次没有浏览器验收、DeepSeek 调用、模型费用或新 Worker；
- 完整测试证明当前数据量和并发场景，不能代替正式生产压测、认证授权和隐私治理。

### 下一步入口

9B 完成时的下一步是 9C“AI 初筛中心收口”；实际结果见下节。

## 9C：AI 初筛中心收口

### 实际修改

| 层级 | 文件 | 职责与本次效果 |
| --- | --- | --- |
| Schema | `backend/app/schemas/screening_center.py`、`schemas/__init__.py` | 固定分页、筛选、排序、报告状态、处理池、能力标签、最小列表字段和允许操作的响应合同；无报告使用独立状态，分数保持空值。 |
| Query Service | `backend/app/services/screening_center_service.py` | 用固定两条 SELECT 完成总数和分页聚合，拼接 Application、Candidate、Job、当前 Resume、当前成功报告、最新初筛运行及最新公开投递处理运行；生成脱敏电话、业务更新时间、报告状态和保守的允许操作。 |
| 确定性标签 | 同上 | 只读取当前 Schema 5.0 报告中 strengths 引用的持久化评价点及非零、有证据的 assessment；按分数、重要性、strength 顺序和评价点顺序排序，名称归一化去重后最多返回 4 个；旧报告、坏引用或无可靠证据返回空数组。 |
| API | `backend/app/api/screening_center.py`、`app/main.py` | 新增 `GET /api/v2/screening-center/applications`；提供分页、Application 精确深链和已确认的业务筛选/排序，校验非法分数和日期区间，并把内部异常收口成稳定安全错误。 |
| 前端 Service | `frontend/src/features/recruitment/services/screeningCenter.ts`、`recruitmentPipeline.ts` | 映射聚合接口的小字段，并为统一详情只读获取现有面试和安全时间线；没有新增模型或 Offer 请求。 |
| 前端入口 | `frontend/src/App.tsx`、`RecruitmentLayout.tsx` | 主导航收为工作台、候选人、岗位管理、AI 初筛中心；旧 `/app/resumes` 和 `/app/reports` 使用 replace 跳转到统一中心。 |
| 前端列表 | `RecruitmentScreeningCenter.tsx`、`styles/screening.css` | 新增桌面证据台账和移动卡片布局；同屏展示人员/岗位、真实报告状态、最多 4 个能力标签、两条优势、两条风险、招聘阶段轨迹、异常、时间和允许操作；保留录入待审核申请、HR 决策和五人批量重评。 |
| 统一详情 | `ApplicationScreeningDrawer.tsx` | 在现有完整 `ScreeningReportView` 和公开投递处理组件上补齐申请概览、当前简历元数据/下载/已保存原文/结构草稿摘要、面试只读列表、Offer 未开放边界和安全时间线；所有读取都不会启动 AI。 |
| 深链接 | `RecruitmentCandidateList.tsx`、`RecruitmentCandidateDetail.tsx` | 候选人业务行携带准确 Application ID；“查看初筛报告”进入 `/app/screening?application_id=...`，聚合 API 精确返回并自动打开对应详情。 |
| 测试 | 后端 3 个新增测试文件、`frontend/tests/stage9-screening-center.test.mjs` 及 3 个既有前端合同测试 | 直接覆盖标签排序/去重/安全、无报告状态、允许操作、API 参数与安全失败、真实 PostgreSQL 固定查询数、小字段边界、路由跳转、导航、深链接、统一详情、响应式和旧能力回归。 |

### 实际验证结果

- 9C 直接后端测试共 `8 passed`；其中真实 PostgreSQL 事务测试监听 SQL，确认一个带 Schema 5 报告的分页请求只有 2 条业务 SELECT（总数 + 当前页），并在回滚后核对业务表数量未变。
- 完整后端回归为 `1420 passed, 502 subtests passed`；保留 PyPDF2 弃用和既有异步连接清理 2 个非阻塞 warning。
- 前端 28 个 `*.test.mjs` 文件全部通过，TypeScript + Vite production build 通过；既有简历录入、HR 决策、批量重评逐项失败、公开投递处理和阶段 7 Schema 5 报告合同继续通过。
- 直接调用开发 PostgreSQL 上的真实 HTTP API 返回 200、`total=1`，响应只含列表所需小字段；未返回 `raw_text`、完整 `parsed_snapshot`、完整 `v5_report`、联系方式原值、薪资或会议信息。
- 最终 `alembic current`、`heads` 均为 `b9e2f4a6c801 (head)`，`alembic check` 为无待生成操作。9C 没有数据库结构变化，也没有新增 migration。
- 开发库最终仍为 Candidate 1、Job 1、Resume 1、Application 1、StageHistory 1、ScreeningReport 1、ScreeningRun 1；PublicApplicationSubmission、ApplicationProcessingRun、InterviewRecord、OfferRecord、ActivityLog 均为 0。原 Application 仍是 `active / screening_passed / passed / final_outcome=NULL`。

### 能够证明

- 列表不再由前端对每条 Application 逐行请求；聚合查询数不会随当前页行数线性增加。
- “没有报告”“正在等待”“失败无报告”“旧报告保留”“报告过期”使用不同状态，列表不会把缺失报告显示成 0 分。
- 能力标签来自已保存的 Schema 5 证据链，旧 Schema、坏引用、零分、无证据和敏感标签不会被包装成可靠能力。
- 内部录入和公开投递共享同一列表；旧页面 URL、候选人 Application 深链及统一详情的读取边界已经接通。
- 9C 没有改写数据库数据、没有新增 Worker、没有调用 DeepSeek，也没有产生模型费用。

### 不能证明与遗留风险

- 本批次没有浏览器产品验收；自动化覆盖结构、映射、构建和响应式 CSS 合同，不能替代真实浏览器中的视觉密度、滚动、焦点顺序和小屏手感检查。
- 固定两条 SELECT 已在当前 PostgreSQL fixture 和开发库证明，但没有进行十万级 Application 的查询计划、索引命中或压力测试。
- 开发库没有公开投递、失败、过期和面试样本；这些组合由虚构/回滚测试覆盖，不代表开发库中实际走过每一种 UI 状态。
- 内部 HR 工作台仍没有登录和 RBAC；时间线和简历原文属于本地作品集边界，正式公网环境仍需权限、审计和隐私治理。
- Offer 区只显示 9D 边界，没有 Offer Service/API/页面、录取或入职操作；统计和最终浏览器验收仍属于 9D—9F。

### 下一步入口

当前唯一下一步是 9D“Offer 与最终结果”。开始前继续只读核对当前 Git、Alembic 和开发库；9D 必须沿用 9A 已固定的 `offer → offer_accepted → admitted → hired` 独立节点，不在 9C 页面或标签层推断业务状态。

## 9D：Offer 与最终结果

### 开工基线与确认补充

本轮接手的是刚从 GitHub 拉取的代码和未同步到最新 migration 的本地 PostgreSQL。只读核对发现代码、设计和 Alembic head 均为 `b9e2f4a6c801`，开发库实际停在 `e7f9a1b3c545`；库内 Candidate 4、Job 2、Resume 5、Application 2、StageHistory 2、ScreeningRun 4，其余报告和阶段 8/9 新表业务数据均为 0，两条 Application 都是 `active / screening_passed / passed / final_outcome=NULL`。项目负责人确认应同步数据库后，只执行仓库已有前向 migration 到 `b9e2f4a6c801`，没有新增 migration，也没有改写或伪造业务数据。

编码前还发现原设计没有唯一说明 accepted Offer 更正以及候选人退出/公司取消后重新打开时如何处理支撑记录。项目负责人于 2026-09-04 确认后，现行设计 6.6 固定为：误接受更正使用同一 Offer `accepted → sent`；候选人退出/公司取消恢复结束历史中的原阶段并保留原记录；Offer 终态重开允许创建下一 `version_number`；面试淘汰重开把触发决定改回 pending；no-show 只有显式 `end_application=true` 才结束流程。

### 实际修改

| 层级 | 文件 | 职责与本次效果 |
| --- | --- | --- |
| Schema | `backend/app/schemas/offer.py`、`interview.py`、`recruitment_timeline.py`、`screening_center.py`、`stage_history.py`、`__init__.py` | 提供 Offer 草稿/全量编辑、发送/接受/拒绝/撤回/过期、录取/入职、退出/取消/重开严格请求；金额只接受 Decimal 语义，确认、原因、日期和 version 都有显式合同；no-show 增加默认 false 的 `end_application`。 |
| API | `backend/app/api/offers.py`、`app/main.py` | 注册 13 个 9D 路由，统一调用 Service；高风险动作在进入 Service 前后都校验确认，并把校验、冲突和未知异常转换为不回显薪资或内部异常的稳定错误。 |
| Service | `backend/app/services/offer_service.py` | 使用 Application/Offer/Interview 行锁执行 Offer 状态机、最终结果、确认里程碑和受控重开；结合 expected_version、重复请求识别、部分唯一索引和单事务写入保持一致性。Offer 历史只追加，同一版本记录的内容修改使用对象 version，不覆盖历史 Offer 版本语义。 |
| 面试兼容 | `backend/app/services/interview_service.py` | no-show 默认只记录未到场；只有显式结束才在同一事务结束 Application，并支持已 no-show 后再次明确结束和重复请求幂等。 |
| 防回写 | `backend/app/services/application_decision_service.py` | 阶段 7 决策只允许在阶段 7 的 active 阶段执行，阻止旧接口改写 interview/offer/admitted 等阶段 9 Application；阶段 9 始终保留 `hr_decision=passed`。 |
| 查询与隐私 | `backend/app/services/recruitment_timeline_service.py`、`screening_center_service.py` | 时间线只映射受控 Offer/最终结果字段，不返回薪资；列表只连接最新 Offer 的 id/status/version/更新时间来计算操作和业务更新时间，不选择或返回任何薪资字段。 |
| 前端 Service | `frontend/src/features/recruitment/services/recruitmentPipeline.ts`、`screeningCenter.ts`、`applications.ts` 及相关类型 | 完整映射 9D API；薪资从输入到响应保持 string，不进入 JavaScript number/float；扩展阶段、最终结果和允许操作。 |
| 前端详情 | `OfferPipelinePanel.tsx`、`ApplicationScreeningDrawer.tsx`、`RecruitmentScreeningCenter.tsx`、`styles/screening.css` | 在统一 Application 详情按需读取并倒序展示全部 Offer 和具体薪资；提供全部 9D 操作、必要说明和二次确认；成功后重新读取 Offer、时间线、Application 概览、初筛状态和中心列表，不做乐观伪更新；时间线不再静默截断前 8 条。 |
| 测试 | `backend/tests/schemas/test_offer.py`、`api/test_offers*.py`、`services/test_offer_service*.py`、既有面试 PostgreSQL 测试和 `frontend/tests/stage9-screening-center.test.mjs` | 覆盖严格字段、真实 API/PostgreSQL、完整主链、异常转换、幂等、多版本、活动唯一性、并发胜者、回滚、no-show 与重开、薪资隐私、全前端回归和 production build。 |

### 实际行为

- `draft → sent → accepted` 由 OfferRecord 保存；接受时 Application 只到 `offer_accepted`。HR 另行确认后依次到 `admitted` 和终态 `hired`，三次动作各写独立 StageHistory/ActivityLog，`hr_decision` 全程保持 passed。
- `sent → declined/withdrawn/expired` 结束 Application 并写对应 final_outcome；过期只由 HR POST 明确标记，且 Service 核对 `valid_until` 已经过期，GET 不写库，也没有新增 Worker。
- 创建重复的相同草稿、重复编辑成相同内容以及重复提交相同目标状态/原因会返回当前结果，不重复增加对象版本、历史或审计；不同内容或过期 expected_version 返回冲突。
- Offer 内容编辑锁定 Application 后再锁定 Offer；draft 可普通编辑，sent 编辑还必须确认并填写更正原因。审计只记录变更字段名和版本，不记录金额、奖金或福利正文。
- Offer 拒绝、撤回或过期后重开时保留旧终态 Offer，可创建 version_number 递增的新 Offer；候选人退出/公司取消重开恢复真实原阶段，若仍有 draft/sent/accepted Offer 则不能创建新 Offer。
- accepted 误操作重开时原子把同一 Offer 改回 sent、清空 responded_at、保留 sent_at、增加 version，同时把 Application 从 offer_accepted 改回 offer；不会新建 Offer 或覆盖薪资。
- no-show 的默认请求不结束 Application；`end_application=true` 才写 `interview_no_show`，重开后原 no_show 面试记录保持不变。面试淘汰或由反馈触发的候选人退出重开时，相应 decision 更正为 pending 并增加 version。

### 验证结果

- 9D Schema、API 和真实 PostgreSQL 直接测试全部通过；真实 API 完成创建、发送、接受、确认录取和确认入职，响应中的 `18888.80` 保持十进制字符串，Application 最终为 `ended / hired / passed / hired`。
- 真实 PostgreSQL 主链覆盖草稿、编辑、发送、接受、录取、入职、逐级更正回退、拒绝后重开和创建第二版 Offer；证明 accepted、admitted、hired 是三个独立节点，旧 Offer 未删除。
- 两个独立 PostgreSQL 会话并发创建不同 Offer 时只有一个成功，另一个为活动 Offer 冲突；两个会话用同一 expected_version 修改时只有一个成功，另一个为 version 冲突，最终只增加一次 version。
- 注入 ActivityLog 写入失败后，Offer、Application、StageHistory 和 ActivityLog 全部回滚；活动 Offer 部分唯一索引和数据库 CHECK 继续由 9A migration 兜底。
- 审计和安全时间线断言未出现三个虚构金额，初筛中心 Schema/查询和前端列表不含薪资；只有单个 Application 的 Offer GET 与详情组件读取和展示具体金额。
- 完整后端回归：`1439 passed, 525 subtests passed`；保留 PyPDF2 弃用和既有异步连接清理 2 个非阻塞 warning。
- 前端全部 `*.test.mjs` 文件通过，TypeScript + Vite production build 通过；9D 测试确认薪资请求/响应使用字符串、所有 9D 操作入口存在、时间线不静默截断。
- 最终 `alembic current` 与 `heads` 均为 `b9e2f4a6c801 (head)`，`alembic check` 无待生成操作。最终开发库仍为 Candidate 4、Job 2、Resume 5、Application 2、StageHistory 2、ScreeningRun 4；ScreeningReport、PublicApplicationSubmission、ApplicationProcessingRun、InterviewRecord、OfferRecord、ActivityLog 均为 0。两条原 Application 的状态未变化。
- 本轮没有调用 DeepSeek、没有产生模型费用，没有新增 migration、Worker、统计接口或 9E 组件。

### 能够证明

- 当前 Schema、API、Service、Model 和 PostgreSQL 约束能组成真实 Offer/最终结果纵向链路，并在当前测试规模下处理并发、双击、冲突和事务失败。
- 数据库行锁负责串行化同一 Application 的竞争写入，expected_version 负责识别用户基于旧页面提交；数据库部分唯一索引在 Service 之外仍能阻止第二个活动 Offer。
- Application、OfferRecord、StageHistory 和 ActivityLog 不会在已测试失败点留下半状态；阶段 9 的结束和重新打开不会改写阶段 7 的 passed 历史事实。
- 薪资使用 Decimal/NUMERIC 且只通过单 Application Offer 详情返回；已测试的列表、时间线、API 错误和应用审计没有薪资明文。
- 9D 没有提前实现 9E 招聘统计或 9F 最终验收。

### 不能证明与遗留风险

- 本轮没有真实浏览器产品验收；静态 UI 合同、全部前端测试和 production build 不能替代鼠标/键盘焦点、弹窗滚动、窄屏表单、不同浏览器日期控件和真实操作手感检查。
- 当前工作台仍使用“本地 HR（未认证）”标签，没有登录、RBAC 或字段级薪资权限；只能作为本地作品集，不代表可直接部署真实招聘数据。
- 并发测试覆盖同一 Application 的两个会话，不是压力测试；没有十万级 Offer/时间线历史、查询计划、连接池容量、锁等待指标或生产故障恢复验证。
- “日志无薪资”证明范围是当前显式 ActivityLog、时间线、列表响应和稳定错误；不能替代生产反向代理、APM、数据库备份、运维日志和员工访问审计的专项隐私评审。
- 9E 招聘统计尚未实现；9F 浏览器与最终验收尚未开始。

### 下一步入口

当前唯一下一步是 9E“招聘流程统计”。继续沿用 9D 的状态、隐私和历史合同；统计只能读取 PostgreSQL 已保存事实，不读取具体薪资，不调用 DeepSeek，也不能把 accepted、admitted 和 hired 合并成一个节点。

## 9E：招聘流程统计

### 实际修改

| 层级 | 文件 | 职责与本次效果 |
| --- | --- | --- |
| Schema | `backend/app/schemas/recruitment_statistics.py`、`schemas/__init__.py` | 新增固定 cohort、8 步漏斗、7 段平均耗时与样本数、7 类实时待办的独立响应合同；不暴露 ORM、候选人字段或薪资。 |
| API | `backend/app/api/recruitment_statistics.py`、`app/main.py` | 新增只读 `GET /api/v2/recruitment-statistics`，支持 `job_id / applied_from / applied_to`；时间必须带时区，非法区间和内部失败返回稳定安全错误。 |
| Query Service | `backend/app/services/recruitment_statistics_service.py` | 用 `Application.applied_at` 固定 cohort，读取 StageHistory、InterviewRecord 和 OfferRecord 的必要非敏感列判断历史里程碑；按 Application 去重，多版本 Offer 不重复计数；缺少或逆序端点不进入平均值。 |
| 实时待办 | 同上 | 日期范围不裁剪当前待办，`job_id` 仍限定岗位；只统计 active Application 中真正等待处理的 scheduled、pending、next_round、draft、sent、accepted 和 admitted 状态，已进入后续节点的不重复算旧待办。 |
| 前端 Service | `frontend/src/features/recruitment/services/recruitmentStatistics.ts` | 映射统计请求/响应和安全错误；只发送三项已确认筛选，不拼接薪资、候选人或 AI 字段。 |
| 前端面板 | `RecruitmentStatisticsPanel.tsx`、`styles/statistics.css`、`styles/index.css` | 在一个复用面板中展示漏斗、上一环节转化率、耗时/样本数和实时待办；提供岗位、投递日期和刷新控件，并为桌面、平板、手机使用无横向滚动的自适应网格。 |
| 页面接入 | `RecruitmentDashboard.tsx`、`RecruitmentScreeningCenter.tsx`、相关 CSS | 9E 初次实现时统计面板位于仪表盘和 AI 初筛中心顶部；9F 产品流纠偏后，当前产品只在仪表盘保留统计，初筛中心回归投递处理职责。 |
| 测试 | `backend/tests/api/test_recruitment_statistics.py`、`services/test_recruitment_statistics_service_postgres.py`、`frontend/tests/stage9-recruitment-statistics.test.mjs`、既有 9D 前端合同 | 覆盖参数/错误、固定 cohort、历史漏斗、纯取消面试、多版本 Offer、转化率零分母、七段耗时与样本数、实时待办、岗位隔离、真实 API、敏感字段和双页面/刷新/响应式合同。 |

### 实际统计口径

- 时间和岗位筛选先用 `Application.applied_at` 选出一批固定 Application；之后的通过、面试、Offer、录取和入职都回看其持久化历史，因此已入职者仍保留在所有真实经过的前序漏斗中。
- 初筛通过、Offer 接受、录取等跨对象节点优先使用 StageHistory；面试进入/完成读取 InterviewRecord；Offer 已发送使用持久化 `sent_at`。同一 Application 无论有多少 Offer 版本，每个漏斗节点最多计一次。
- 每步转化率都以前一步为分母；前一步为 0 时返回 `null`，有真实分母但本步为 0 时返回 `0.0`，不把“无样本”和“转化为零”混为一谈。
- 七段耗时以小时返回，两端时间都存在且顺序合法才形成样本；平均值旁始终返回 sample_count，缺失端点的 Application 仍保留在漏斗中。
- 当前待办是查询时刻的 active 流程快照：投递日期筛选不影响它，但岗位筛选仍生效。接受 Offer 后已经 admitted 的 Application 只计入“待确认入职”，不继续计入“待确认录取”。

### 验证结果

- 9E API 与 PostgreSQL 直接测试 `5 passed`；扩大到初筛中心、9D Offer API/Service、真实 PostgreSQL 和并发套件为 `21 passed, 13 subtests passed`。
- 真实 PostgreSQL fixture 使用全虚构数据覆盖 3 人 cohort、两版 Offer 和 7 类日期范围外实时待办；漏斗得到 `3 → 2 → 2 → 2 → 2 → 1 → 1 → 1`，七段耗时及各自样本数与预设时间线一致。外层事务回滚后相关表行数与测试前一致。
- 同一 fixture 通过真实 ASGI HTTP 请求访问 `/api/v2/recruitment-statistics` 返回 200；开发 FastAPI 连接现有 PostgreSQL 的真实 GET 也返回 200，当前开发数据为 2 份 Application、2 份历史初筛通过、其余后续漏斗和待办均为 0，响应不含薪资或候选人身份字段。
- 完整后端回归为 `1444 passed, 525 subtests passed`，保留 PyPDF2 弃用和既有异步连接清理 2 个非阻塞 warning。
- 前端 29 个 `*.test.mjs` 文件全部通过，TypeScript + Vite production build 通过；既有 9D 断言升级为操作后同时刷新列表和统计，没有降低门槛。
- 最终 `alembic current`、`heads` 均为 `b9e2f4a6c801 (head)`，`alembic check` 无待生成操作。开发库仍为 Candidate 4、Job 2、Resume 5、Application 2、StageHistory 2、ScreeningRun 4；ScreeningReport、PublicApplicationSubmission、ApplicationProcessingRun、InterviewRecord、OfferRecord、ActivityLog 均为 0。两条 Application 仍为 `active / screening_passed / passed / final_outcome=NULL`。
- 本批次没有新增 migration、数据库写接口、Worker 或统计导航，没有调用 DeepSeek，也没有产生模型费用。

### 能够证明

- 9E 已形成“React 面板 → v2 API → Pydantic Schema → 只读 Query Service → ORM Model → PostgreSQL”的真实纵向切片，而不是静态演示数字。
- 固定 cohort 与历史里程碑能避免当前已到后续阶段的人从前序漏斗消失；多版本 Offer 和同一 Application 的多条事件不会重复增加人数。
- `null` 转化率、耗时 sample_count 和实时待办的日期独立性在 API、Service 和 PostgreSQL 层有直接证据。
- 统计查询只选择必要的业务 ID、状态和时间戳，响应和稳定错误中没有具体薪资、候选人身份或简历内容；GET 不提交事务、不推进状态。
- 阶段 7 的 AI 报告和 `hr_decision=passed` 没有被统计代码改写；9E 完全不调用模型。

### 不能证明与遗留风险

- 当前 Codex 环境没有可用浏览器实例，无法完成真实点击、焦点顺序、日期控件手感、桌面/平板/手机视觉密度和截图验收；静态 UI 合同、响应式 CSS 检查和 production build 不能替代这项证据。
- PostgreSQL 测试证明当前 fixture 下的口径和事务清理，不是十万级数据压测；当前查询条数不随 Application 数量线性增加，但仍会把 cohort 的必要事件行读入应用内存，正式大数据量前需要 `EXPLAIN ANALYZE`、索引命中、响应时间和内存压测。
- 本地工作台仍没有登录、RBAC 和字段级权限；虽然统计本身不返回 PII/薪资，正式生产还需验证租户/部门/岗位授权，防止用户看到不属于自己的聚合结果。
- 开发库没有真实面试或 Offer 业务行，真实 API 的非零复杂组合由事务回滚 fixture 证明；尚未在生产权限、连接池、反向代理/APM 和多浏览器环境下验证。
- 本节是 9E 当时的完成记录；9F 后续纠偏和验收状态见下节，阶段 9 尚未关闭。

### 下一步入口

当前唯一下一步是 9F“阶段 9 最终验收”。9F 应基于 9A—9E 的现有合同和证据执行完整主链、真实浏览器与最终验收，不新增 9E 统计口径，也不把自动化通过等同于项目负责人验收。

## 9F：最终验收（已完成）

### 产品流纠偏

项目负责人指出原页面把“Candidate 身份实体”和“已通过初筛的候选人工作台”混为一谈。现行业务入口已纠正为：

```text
公开投递 / HR 内部录入
    → AI 初筛中心（HR 尚未通过）
    → AI 只提供岗位匹配证据
    → HR 明确通过
    → 候选人工作台（已通过的 Application）
    → 面试 → Offer → 录取 → 入职
```

- AI 不自动决定通过；`hr_decision=passed` 仍只能由 HR 动作产生。
- Candidate 可为身份去重先存在，但只有其 Application 被 HR 通过后才进入候选人业务页。
- `/app/screening` 固定请求 `view=screening`，只显示 `hr_decision != passed` 的投递；`/app/candidates` 固定请求 `view=candidate`，只显示 `hr_decision=passed` 的后续流程。
- 招聘统计只保留在仪表盘，不再占用初筛列表；具体薪资仍只在单 Application 的 Offer 详情按需读取。

### 实际修改

| 层级 | 文件 | 职责与当前效果 |
| --- | --- | --- |
| Schema/API | `backend/app/schemas/screening_center.py`、`backend/app/api/screening_center.py` | 新增严格 `screening/candidate/all` 视图参数和关键词；补充公司、工作年限、学历等列表小字段，不增加薪资。 |
| Query Service | `backend/app/services/screening_center_service.py` | 在数据库 count 和分页之前应用业务视图；关键词做转义后匹配候选人、联系方式、公司、职位和岗位，并支持 Application ID 精确查找，避免前端过滤造成总数/分页错误。 |
| 面试详情 | `backend/app/api/interviews.py`、`backend/app/services/interview_service.py` | 增加单条面试私有详情读取；列表继续不返回 meeting_link 和 schedule_note，详情按需读取。 |
| 双工作台 | `RecruitmentScreeningCenter.tsx`、`RecruitmentCandidateList.tsx`、`ApplicationEvidenceTable.tsx` | 初筛与候选人共享高密度表格、移动卡片和一致字段语言，但各自请求不同业务视图；候选人页增加阶段筛选和统一详情，不再跳回初筛中心。 |
| 统一详情 | `ApplicationScreeningDrawer.tsx`、`InterviewPipelinePanel.tsx`、`OfferPipelinePanel.tsx` | 初筛详情只处理简历、AI 证据与 HR 决策；候选人详情继续面试、Offer、录取和入职。状态、简历解析结果与时间线改用业务中文；普通 GET 不再触发父列表刷新，只有状态变化才通知父级。 |
| 统计位置 | `RecruitmentDashboard.tsx`、`RecruitmentScreeningCenter.tsx` | 统计只位于仪表盘；没有修改 9E API、cohort 或漏斗口径。 |
| 测试 | 初筛中心后端/API/PostgreSQL 测试、`frontend/tests/stage9-screening-center.test.mjs` 及既有前端合同 | 覆盖两类视图的互斥、分页前过滤、小字段/薪资边界、面试私有详情、双页面入口、操作刷新和详情读取不循环的静态合同。 |

### 当前验证与证据边界

- 定向后端测试为 `20 passed, 1 warning, 14 subtests passed`；完整后端回归为 `1445 passed, 2 warnings, 525 subtests passed`。
- 前端 29 个 `*.test.mjs` 文件全部通过，TypeScript + Vite production build 通过。
- Alembic `current` 与 `heads` 均为 `b9e2f4a6c801 (head)`，`alembic check` 无待生成操作；没有新增 migration。
- 全虚构浏览器数据已检查 1440px 桌面高密度表格和 1024px 响应式卡片；初筛中心不再显示统计，窄屏没有横向溢出。浏览器检查发现的详情请求循环已完成代码修复和自动化回归；项目负责人于 2026-09-05 完成复查并确认当前业务分流、信息密度、详情请求和操作手感可验收。
- 本轮只读开发库基线为 Candidate 4、Job 2、Resume 4、Application 2、StageHistory 2、ScreeningRun 4，其余报告及阶段 8/9 业务表为 0，两条 Application 均保持 `active / screening_passed / passed / final_outcome=NULL`。Resume 数量与 9D/9E 当时记录的 5 不一致；本轮未修改、删除或补造任何开发数据。
- 自动化和数据库证据能证明当前代码的视图分流、类型检查、构建、数据库合同和已覆盖事务行为；项目负责人验收补足当前作品集范围内的产品判断，但不能证明生产 RBAC、字段级薪资权限、大数据量性能、多浏览器兼容和外部日志系统的隐私边界。
- 本轮没有调用 DeepSeek、没有模型费用、没有写入或伪造开发库业务数据。

### 最终验收结论

项目负责人于 2026-09-05 确认 `/app/screening`、`/app/candidates` 和候选人统一详情的业务分流、信息密度、详情请求行为及面试/Offer 操作手感达到阶段 9 作品集验收要求。9F 和阶段 9 据此关闭；生产认证/RBAC、字段级薪资权限、大数据量性能、生产日志隐私评审和多浏览器验证继续作为未扩大的后续边界，不因本次验收被视为已经完成。阶段 10—12 不自动启动，后续范围仍须重新评审并按阶段门禁确认。
