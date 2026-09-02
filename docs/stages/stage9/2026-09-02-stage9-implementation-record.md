# 阶段 9 实施记录

> 日期：2026-09-02  
> 当前状态：9A“合同与 migration”和 9B“面试后端”已完成；9C—9F 未开始  
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

当前唯一下一步是 9C“AI 初筛中心收口”。开始前重新核对工作区、Alembic、开发库和本节结果；9C 只做列表聚合 API、确定性标签、导航精简、桌面/移动列表与简历/报告统一详情，不提前进入 Offer 或最终结果操作。
