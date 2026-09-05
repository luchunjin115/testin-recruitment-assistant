# 项目当前状态

> 最新更新：2026-09-05
>
> 本文件只记录当前结论、风险和下一步；详细过程由 Git 历史恢复。

## 当前结论

- 阶段 4—8 已完成。阶段 8 的 8A—8F、真实模型最小链路和项目负责人浏览器检查均已完成；项目负责人于 2026-09-02 明确确认阶段 8 最终验收通过并关闭。
- 阶段 9 的 9A—9F 已全部完成；产品流纠偏、自动化回归和浏览器复查均已完成，项目负责人于 2026-09-05 明确确认最终验收通过并关闭阶段 9。
- 项目负责人于 2026-09-05 确认当前秋招版本暂不开发阶段 10 首页综合 Agent 和阶段 11 RAG；两项保留为长期可选方向，不属于当前交付范围，也不作为阶段 9 完成条件。
- 阶段 7 已于 2026-09-01 通过项目负责人验收并关闭；功能链路已经完成，目前不是“等待继续开发才能交付”的状态。
- 阶段 7 当前生产合同：评价计划 `deepseek-v4-pro` / Prompt v4 / Service v5 / Schema 5.0；初筛报告 `deepseek-v4-pro` / 主 Prompt v10 / Repair Prompt v2 / Service v11 / Schema 5.0。
- `ScreeningRun` 最多保留 3 个 API attempts；当前 Alembic head 为 `b9e2f4a6c801`。
- 8A 已固定公开表单/响应、身份核对和 ProcessingRun Schema/枚举，新增 `PublicApplicationSubmission`、`ApplicationProcessingRun` ORM 与数据库约束；`Candidate.email` 已按确认结果扩展到 254 字符，初始审计已补充 `public_application_received` reason code。
- 8B 已提供独立公开 Job API 和单次 multipart 投递 API；后端已实现请求体上限、Redis 摘要限流、Candidate 解析、重复申请/幂等、私有文件 SHA-256 与 DOCX 安全检查、数据库事务和文件补偿，以及稳定公开错误。
- 新公开投递会一致创建 Candidate/Resume/Application/Submission/初始 ProcessingRun 和系统 StageHistory；既有内部 active Application 收到公开 Resume 时保留旧 `current_resume_id` 且不伪造阶段变化。初始 Run 只排队，不在 API 请求中解析简历或调用 AI。
- 8C 已新增 PostgreSQL Application Processing Worker：使用 `SKIP LOCKED` 和租约推进原文提取、结构化、阶段 7 触发与终态对账；成功步骤跳过，提取失败阻塞，结构化失败形成 warning 后继续，岗位关闭或内部 Application 未选择新简历时暂停。
- 自动编排最多 3 次，同一步基础设施重试最多 2 次；过期租约可恢复，达到上限安全失败。人工重试会新建 `manual_retry` Run、保留历史并写 ActivityLog，8E 已提供 HR API/UI 入口。
- 8D 已将 `/apply` 接入独立公开 Job 和 multipart 投递 API，删除预览文案、内部工作台入口、教育/技能/个人简介和旧 `.doc`；页面现在具备必填/文件/隐私校验、幂等重试、重复点击保护、安全错误、公开凭证成功页和三档响应式/键盘样式。
- 8E 已将公开投递直接并入现有 AI 初筛列表，没有新增页面、Tab 或独立工作区；统一列表支持来源、正常/异常和精确处理状态筛选，公开行显示凭证、文件和“受理 → 原文 → 结构化 → 初筛”轨迹。
- 8E 已新增安全工作台摘要/详情、身份核对、人工重试和只读结构化草稿 API；身份核对不合并 Candidate，人工重试保留旧 Run，切换简历/身份核对/重试均写 ActivityLog，只读草稿不会启动模型。
- 最终真实质量运行：35 个业务调用、35 个 API attempts、0 次基础设施重试、0 次 Repair；基础报告合法 `19/20`，合法报告方向一致 `14/19`，分数进入冻结区间 `7/19`，稳定性 `15/15`，费用估算 USD 0.52694268。
- 最终机器结果中的 `quality_gate_passed=null`、`quality_conclusion_allowed=false` 保持原样。阶段关闭来自项目负责人基于完整证据作出的产品验收，不表示每项机器质量指标都通过。

## 阶段 7 已完成能力

```text
HR 维护完整 JD
    → AI 生成轻量评价清单
    → HR 编辑并确认清单
    → 完整 JD + 已确认清单 + 当前 Application 简历进入 AI 初筛
    → AI 输出逐项评分、证据、总体分和报告
    → Schema / Service 校验结构、引用、安全与事务规则
    → 合同错误最多执行一次受控 Repair
    → HR 阅读报告并独立作出通过 / 备选 / 淘汰决定
```

- Python 不做加权评分，也不替代 HR 作招聘决定。
- 个人联系方式等隐私字段在进入模型前移除。
- 重新评估失败时保留最近一次成功报告；异步运行具备幂等、租约、重试和审计记录。
- API、PostgreSQL、React 初筛中心和当前产品回归测试均已落地。

## 已接受的非阻塞限制

- R12 中普通“手机号用户”的业务语境会被隐私规则保守拒绝。
- 模型评分整体偏保守；五个 high 稳定组均为 88 分。

这两项未在阶段 7 内继续修复。若未来调整隐私语义或 AI 评分原则，应另立专项并重新确认合同与验收标准。

## 当前权威入口

1. `CLAUDE.md`：长期架构与技术约束。
2. `docs/DOCUMENT_INDEX.md`：文档导航与按任务阅读规则。
3. `docs/stages/stage9/2026-09-02-stage9-interview-offer-hiring-pipeline-design.md`：阶段 9 已确认业务合同。
4. `docs/stages/stage9/2026-09-02-stage9-implementation-record.md`：阶段 9 唯一实施记录。
5. `docs/stages/stage8/2026-09-02-stage8-public-application-async-processing-design.md`：阶段 8 已确认业务合同与实施入口。
6. `docs/stages/stage8/2026-09-02-stage8-implementation-record.md`：阶段 8 各批次实际修改、验证、边界和风险。
7. `docs/stages/stage7/README.md`：阶段 7 单一入口。
8. `docs/stages/stage7/2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`：阶段 7 最终业务合同。
9. `docs/stages/stage7/2026-09-01-stage7-final-v10-v2-acceptance-review.md`：最终验收结论与已知限制。
10. `docs/planning/implementation-plan.md`：跨阶段实施顺序。

## 当前风险与工作区状态

- 阶段 7 收尾整理已完成：当前目录只保留单一入口、最终合同、最终验收和最终原始证据；一次性质量运行器与中间批次测试已删除。
- 整理前的完整恢复点是分支 `2lcj` 上的提交 `f2e77b0`；被删过程材料可从 Git 历史找回。
- 最终 raw 结果没有回算、覆盖或美化。
- 本地 PostgreSQL 已执行迁移到 `a8d4f2c7e901 (head)`；原有业务表行数未变，两个阶段 8 新表为空，`alembic check` 无待生成操作。
- 8A—8C 定向测试、完整后端回归、真实 PostgreSQL/API/Redis 和临时 PostgreSQL 并发已通过；完整回归为 `1365 passed, 460 subtests passed`，保留 2 个既有非阻塞 warning。
- 随机临时 PostgreSQL 中已验证 8B 相同并发提交只产生一个业务结果，以及 8C 多 Worker 不重复领取、过期租约恢复和真实 Worker 重启后进入阶段 7 `waiting_plan`；临时数据库均已删除且残留为 0。开发库仍为 `a8d4f2c7e901 (head)`、`alembic check` 无漂移，两张阶段 8 表仍为 0 行。
- 8E 完成后前端全部 `27` 个测试文件和 TypeScript/Vite production build 通过；完整后端回归为 `1377 passed, 467 subtests passed`，保留 2 个既有非阻塞 warning。
- 8B 请求体会在应用进程内最多缓冲约 10.25 MB，且限流使用直连客户端 IP；这满足当前本地作品集边界，正式公网部署仍需要反向代理限制、可信代理配置和恶意文件扫描评估。
- Codex 当前环境没有可连接的浏览器，因此阶段 8 浏览器验收由项目负责人手工完成。首次查看发现 `/apply` 五段 JD 双栏错位和字号过小；展示层改为固定顺序的单列 `01—05` 说明书结构后，全部 27 个前端测试文件和 production build 通过，项目负责人复查并接受当前结果。
- 阶段 8 HR 正常/异常筛选、身份核对、简历选择审计、只读草稿和人工重试已经实现；Worker 仍默认随应用生命周期启动。开发库当前没有 queued Run，本轮只使用前端假响应和只读/回滚测试，没有真实投递、DeepSeek 调用或阶段 8 模型费用。
- 8E 没有数据库结构变更；开发库仍为 `a8d4f2c7e901 (head)`，`alembic check` 无漂移，`public_application_submissions` 和 `application_processing_runs` 均为 0 行。
- 8F 开始时已重新核对 `current/head/check` 和开发库行数：Alembic 仍为 `a8d4f2c7e901 (head)`、无待生成迁移，两张阶段 8 表仍为 0 行；本轮没有创建投递或 queued Run。
- 8F 最小真实模型链路已按项目负责人单独授权完成：公开 API 返回 202，`deepseek-v4-flash` 结构化和 `deepseek-v4-pro` 初筛各 1 个 API request，合计 2 次、无重试/Repair；结构化 692/592、初筛 2659/319 input/output tokens，最终 ProcessingRun 为 `succeeded/completed`，非高峰保守估算费用 USD 0.00292952，低于 USD 0.25 上限。
- 8F 真实链路只使用虚构数据；随机临时 PostgreSQL 已删除，Redis 限流键为 0，隔离目录文件数为 0。开发库两张阶段 8 表仍为 0 行，Alembic 仍为 `a8d4f2c7e901 (head)` 且无漂移。执行环境只留下不含文件或业务数据的空目录骨架。
- `waiting_screening` 当前使用固定短周期数据库轮询，Worker 随 FastAPI 进程运行；这满足本地作品集边界，但生产级高流量需要另行评估退避/通知、独立进程监督、指标和告警。
- 阶段 8 定位为作品集和本地演示，只能使用虚构或完整脱敏数据；若改为真实公网招聘，必须先另行确认隐私保留/删除、恶意文件扫描和生产安全范围。
- 阶段 9 设计前已只读复核：Git 起始工作区干净，开发库为 `a8d4f2c7e901 (head)` 且 `alembic check` 无漂移；库内只有 1 条 `active / screening_passed / passed` Application，尚无 InterviewRecord 或 OfferRecord 表。设计过程未修改数据库，也未生成真实候选人或薪资数据。
- 9A 开始前重新只读复核了 Git、Alembic、PostgreSQL 结构和数据：没有无法解释的 `ended` Application。随机临时 PostgreSQL 已通过阻塞预检、upgrade → downgrade → upgrade、约束和部分唯一索引实测；临时库均已删除。
- 开发 PostgreSQL 已安全前向升级到 `b9e2f4a6c801 (head)`，`alembic check` 无漂移；原有 Application、StageHistory、ScreeningReport 等行数未变，新增 InterviewRecord 和 OfferRecord 表均为 0 行。
- 9B 已提供面试安排、改期、取消、未到场、首次反馈、反馈更正和统一安全时间线 API；Application/Interview 行锁、expected_version、幂等、StageHistory/ActivityLog 同事务和稳定错误均已落地。
- 9B 直接测试、真实 PostgreSQL/API 和多会话并发通过；完整后端回归为 `1412 passed, 502 subtests passed`。测试虚构数据已回滚或精确清理，开发库 InterviewRecord、OfferRecord、ActivityLog 均为 0 行，原 Application 状态和原有行数未变。
- 9C 的分页聚合 API 在 9F 增加 `view=screening|candidate|all` 业务视图：AI 初筛中心只列 `hr_decision != passed` 的待处理/备选/淘汰投递；HR 明确通过后的 Application 进入候选人页，并在统一详情继续面试、Offer、录取和入职。Candidate 身份记录可因去重先存在，但不等于已经进入候选人业务工作台。
- 9C 完整后端回归为 `1420 passed, 502 subtests passed`，前端 28 个测试文件和 production build 全部通过；开发 PostgreSQL 真实聚合 API 返回 200，Alembic 仍为 `b9e2f4a6c801 (head)` 且无漂移，原有 1 条 Application 及相关数据数量和状态未变。
- 9C 没有 migration、DeepSeek 调用、模型费用、新 Worker 或浏览器产品验收。当前主要未验风险是真实浏览器中的高密度列表/移动端手感，以及大数据量查询计划和生产级认证权限。
- 9D 开始时发现刚拉取代码后的开发 PostgreSQL 仍停在 `e7f9a1b3c545`；经项目负责人确认后只执行仓库既有 migration 到 `b9e2f4a6c801 (head)`。迁移和最终复核前后，Candidate 4、Job 2、Resume 5、Application 2、StageHistory 2、ScreeningRun 4 等原数据数量及两条 Application 状态保持不变。
- 9D 已完成 Offer 草稿/编辑/发送/接受/拒绝/撤回/过期、录取/入职、候选人退出、公司取消和受控重新打开；accepted 更正使用同一 Offer `accepted → sent`，终态 Offer 重开后允许创建递增版本的新 Offer，阶段 9 不改写 `hr_decision=passed`。
- 9D 的 Application/Offer/Interview 行锁、expected_version、重复请求幂等、部分唯一索引、单事务历史/审计和回滚已通过真实 PostgreSQL/API 与双会话并发测试。薪资保持 Decimal/NUMERIC，只在单 Application Offer 详情按需返回；列表、时间线、错误和 ActivityLog 未返回金额明文。
- 9D 完整后端回归为 `1439 passed, 525 subtests passed`，前端全部 `*.test.mjs` 文件和 production build 通过；Alembic 最终为 `b9e2f4a6c801 (head)` 且无漂移，测试数据已回滚或精确清理，InterviewRecord、OfferRecord、ActivityLog 最终均为 0。
- 9D 未做真实浏览器产品验收、生产认证/RBAC、字段级薪资权限、大数据量压测或生产日志隐私评审；没有调用 DeepSeek，没有新增 migration、Worker 或 9E 统计。
- 9E 已新增只读 `GET /api/v2/recruitment-statistics`：按 `Application.applied_at` 固定 cohort，用持久化历史计算 8 步漏斗、上一环节转化率、7 段耗时/样本数，并返回不受日期范围影响但尊重岗位筛选的 7 类实时待办；统计不返回 PII/薪资、不调用 AI、不写库。
- 9E 统计能力和口径保持不变；9F 产品流纠偏后，统计面板只保留在仪表盘，不再占用 AI 初筛中心。9D 状态操作后会刷新 Application 概览、Offer、时间线及候选人列表。
- 9E 最终 Alembic 仍为 `b9e2f4a6c801 (head)` 且无漂移；开发库 Candidate 4、Job 2、Resume 5、Application 2、StageHistory 2、ScreeningRun 4 等原数据数量和两条 Application 状态未变，面试、Offer、ActivityLog 等阶段 9 业务表仍为 0。
- 9F 已用全虚构页面数据实际检查 1440px 桌面高密度表格和 1024px 响应式卡片：初筛中心无统计面板、候选人表格能同屏显示主要业务信息，且窄屏没有横向溢出。检查中发现统一详情首次读取会触发父列表刷新并形成请求循环，现已改为“普通读取不通知父级、状态变化才通知”，前端 29 个测试文件和 production build 均已通过；项目负责人于 2026-09-05 完成复查并确认当前产品流和交互可验收。
- 9F 后端完整回归为 `1445 passed, 2 warnings, 525 subtests passed`；前端 29 个测试文件和 production build 通过。当前 Alembic 为 `b9e2f4a6c801 (head)` 且无漂移。本轮只读复核开发库为 Candidate 4、Job 2、Resume 4、Application 2、StageHistory 2、ScreeningRun 4，其余报告及阶段 8/9 业务表为 0；两条 Application 状态未变。该 Resume 数量与 9D/9E 当时记录的 5 不一致，本轮未修改、补造或删除开发数据。
- 9F 尚未完成生产认证/RBAC、字段级薪资权限、大数据量查询计划/压力测试、生产日志隐私评审和多浏览器验证。

## 唯一下一步

1. 保持阶段 8、阶段 9 的已关闭结论、现行业务合同和验收证据不被后续工作改写。
2. 阶段 10 首页 Agent 和阶段 11 RAG 已暂缓，不进入设计或实现；当前没有活动开发阶段。
3. 阶段 12 的登录/RBAC、审计、部署和交付是否继续，后续单独评审并确认，不因本次路线调整自动启动。

## 新对话恢复方式

先读 `CLAUDE.md`、本文件和 `docs/DOCUMENT_INDEX.md`；若修改已关闭阶段 9，完整阅读阶段 9 当前专项设计并按涉及范围读取阶段 4—8 当前合同和实际代码；若讨论后续阶段，读取现行路线图和总体架构；不默认阅读 Git 历史中的中间实验材料。
