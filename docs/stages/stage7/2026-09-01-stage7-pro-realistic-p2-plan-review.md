# Stage 7 Pro P2 评价计划人工复核卡

> 状态：用户已于 2026-09-01 确认全部五份当前计划；confirmed snapshots 已冻结，P3 报告调用尚未单独授权。  
> 模型：`deepseek-v4-pro`；当前只展示通过 Schema/Service 硬校验的计划草稿。  
> 复核重点：必备项是否正确、是否遗漏核心要求、是否擅自新增、粒度是否合适、来源是否支持。

## 快速复核建议

- `JD-01`：14 项超过产品建议的 12 项，结构合法但偏细。可重点考虑合并 `0001/0006/0007` 的 Java 服务与 Spring Boot 主题、`0003/0009` 的 SQL 性能主题，以及 `0004/0014` 的测试/文档/复盘主题。
- `JD-02`：`0002` API 测试与 `0004` API 自动化存在一定重叠；`0009` SQL/Linux 被模型列为 required，但原文没有“必须”等强语气，需由你确认是否保留 required。
- `JD-03`：12 项、无 warning，必备与加分层次相对清楚，可重点检查实验分析和 BI 是否需要调整重要性。
- `JD-04`：`0001` 的 warning 很可能是“优先级判断”中的“优先”被程序当成弱语气信号；评价点本身是职责类 general，建议重点确认是否直接保留 general。
- `JD-05`：12 项、无 warning；`0008` ERP/MRP 和 `0009` 跨部门推进当前为 general，需要你确认它们是否应提升为 required。

## JD-01：交易平台 Java 后端工程师

- 运行状态：`succeeded`
- 评价点数量：14
- 全部来源可追溯：是
- Warning 数量：5

| ID | 名称 | 重要性 | 说明 | 初筛重点 | JD 来源 |
| --- | --- | --- | --- | --- | --- |
| criterion:0001 | 订单、库存预占或履约服务开发 | general | 判断是否能够负责订单、库存预占或履约相关 Java 服务的需求分析、接口设计、开发和维护。 | 寻找订单、库存预占或履约相关 Java 服务开发职责和成果证据。 | job_responsibilities: 负责订单、库存预占或履约相关 Java 服务的需求分析、接口设计、开发和维护 |
| criterion:0002 | REST API、异常码、幂等和数据一致性方案定义 | general | 判断是否能够与产品、前端、测试及上下游团队共同定义 REST API、异常码、幂等和数据一致性方案。 | 寻找参与定义 REST API、异常码、幂等和数据一致性方案的证据。 | job_responsibilities: 与产品、前端、测试及上下游团队共同定义 REST API、异常码、幂等和数据一致性方案 |
| criterion:0003 | 慢 SQL、缓存热点、消息堆积和线上告警分析 | general | 判断是否能够分析慢 SQL、缓存热点、消息堆积和线上告警，推动性能优化及问题复盘。 | 寻找分析慢 SQL、缓存热点、消息堆积和线上告警并推动优化的证据。 | job_responsibilities: 分析慢 SQL、缓存热点、消息堆积和线上告警，推动性能优化及问题复盘 |
| criterion:0004 | 单元测试、集成测试、代码评审与文档维护 | general | 判断是否能够编写单元测试和必要的集成测试，参与代码评审、发布检查与技术文档维护。 | 寻找编写测试、参与代码评审、发布检查和技术文档维护的证据。 | job_responsibilities: 编写单元测试和必要的集成测试，参与代码评审、发布检查与技术文档维护 |
| criterion:0005 | 服务拆分、容量评估和可观测性建设参与 | general | 判断是否能够根据业务增长参与服务拆分、容量评估和可观测性建设，但不要求入职后立即承担整体架构负责人职责。 | 寻找参与服务拆分、容量评估和可观测性建设的证据。 | job_responsibilities: 根据业务增长参与服务拆分、容量评估和可观测性建设，但不要求入职后立即承担整体架构负责人职责 |
| criterion:0006 | Java 项目开发经验 | required | 判断是否具备 Java 项目开发经验。 | 寻找 Java 项目开发职责和成果证据。 | candidate_requirements: 必须具备 Java 项目开发经验 |
| criterion:0007 | Spring Boot REST API 设计与实现 | required | 判断是否能够使用 Spring Boot 完成 REST API 的设计与实现。 | 寻找使用 Spring Boot 设计并实现 REST API 的项目证据。 | candidate_requirements: 能够使用 Spring Boot 完成 REST API 的设计与实现 |
| criterion:0008 | MySQL 表设计、事务和索引理解 | required | 判断是否理解 MySQL 表设计、事务和索引。 | 寻找 MySQL 表设计、事务和索引相关实践证据。 | candidate_requirements: 必须理解 MySQL 表设计、事务和索引 |
| criterion:0009 | SQL 性能问题定位 | required | 判断是否能够结合执行计划定位常见 SQL 性能问题。 | 寻找结合执行计划定位 SQL 性能问题的实践证据。 | candidate_requirements: 能够结合执行计划定位常见 SQL 性能问题 |
| criterion:0010 | Redis 或消息队列实际使用经验 | required | 判断是否具备 Redis 或主流消息队列的实际使用经验，并能说明使用场景及异常处理方式。 | 寻找 Redis 或消息队列使用场景、异常处理实践证据。 | candidate_requirements: 需要具备 Redis 或主流消息队列的实际使用经验，并能说明使用场景及异常处理方式 |
| criterion:0011 | 线上问题定位与沟通 | required | 判断是否能够阅读日志、定位线上问题，并与测试和业务同事清晰沟通处理过程。 | 寻找阅读日志、定位线上问题及沟通处理过程的证据。 | candidate_requirements: 能够阅读日志、定位线上问题，并与测试和业务同事清晰沟通处理过程 |
| criterion:0012 | 订单、支付、库存或履约系统经验 | preferred | 判断是否有订单、支付、库存或履约系统经验。 | 寻找订单、支付、库存或履约系统相关项目经验证据。 | preferred_qualifications: 有订单、支付、库存或履约系统经验优先 |
| criterion:0013 | 高并发压测、限流降级、容器化部署或 Kubernetes 实践 | preferred | 判断是否有高并发压测、限流降级、容器化部署或 Kubernetes 实践。 | 寻找高并发压测、限流降级、容器化部署或 Kubernetes 实践证据。 | preferred_qualifications: 有高并发压测、限流降级、容器化部署或 Kubernetes 实践者优先 |
| criterion:0014 | 技术方案文档或线上事故复盘经验 | preferred | 判断是否有技术方案文档或线上事故复盘经验。 | 寻找技术方案文档或线上事故复盘经验证据。 | preferred_qualifications: 有技术方案文档或线上事故复盘经验者优先 |

请重点复核的 warning：
- `many_criteria` / `整份计划` / `-`：当前轻量评价清单多于 12 项，请 HR 检查是否需要合并
- `importance_review_required` / `criterion:0005` / `complex_qualification_language`：评价点 importance 与原文语气或字段信号存在需要 HR 复核的不确定性
- `importance_review_required` / `criterion:0007` / `no_explicit_signal_non_general`：评价点 importance 与原文语气或字段信号存在需要 HR 复核的不确定性
- `importance_review_required` / `criterion:0009` / `no_explicit_signal_non_general`：评价点 importance 与原文语气或字段信号存在需要 HR 复核的不确定性
- `importance_review_required` / `criterion:0011` / `no_explicit_signal_non_general`：评价点 importance 与原文语气或字段信号存在需要 HR 复核的不确定性

- [ ] required / preferred / general 判断正确
- [ ] 没有遗漏影响初筛的核心要求
- [ ] 没有新增 JD 不存在的门槛
- [ ] 评价点粒度适合 HR 阅读和后续评分
- [ ] 来源能够支持名称、说明和初筛重点
- 用户结论：按当前计划确认

## JD-02：测试开发工程师

- 运行状态：`succeeded`
- 评价点数量：12
- 全部来源可追溯：是
- Warning 数量：1

| ID | 名称 | 重要性 | 说明 | 初筛重点 | JD 来源 |
| --- | --- | --- | --- | --- | --- |
| criterion:0001 | 需求和技术方案评审 | general | 判断是否参与需求和技术方案评审，识别接口、权限、状态流转、异常与兼容性风险。 | 寻找参与需求或技术方案评审并识别风险的证据。 | job_responsibilities: 参与需求和技术方案评审，识别接口、权限、状态流转、异常与兼容性风险 |
| criterion:0002 | API 测试经验 | required | 判断是否具备 API 测试经验，理解 HTTP、鉴权、幂等、数据库校验和异常场景。 | 寻找 API 测试职责、覆盖场景和结果证据。 | candidate_requirements: 必须具备 API 测试经验，理解 HTTP、鉴权、幂等、数据库校验和异常场景<br>job_responsibilities: 使用 Python 或 Java 建设和维护 API 自动化测试 |
| criterion:0003 | Python 或 Java 编程能力 | required | 判断是否具备 Python 或 Java 编程能力，能独立编写和调试测试代码。 | 寻找使用 Python 或 Java 编写和调试测试代码的职责、项目或成果证据。 | candidate_requirements: 必须具备 Python 或 Java 编程能力，能独立编写和调试测试代码<br>job_responsibilities: 使用 Python 或 Java 建设和维护 API 自动化测试 |
| criterion:0004 | API 自动化测试建设与维护 | general | 判断是否能建设和维护 API 自动化测试，保证数据隔离、断言质量和失败可定位。 | 寻找建设和维护 API 自动化测试并保证数据隔离、断言质量和失败可定位的证据。 | job_responsibilities: 使用 Python 或 Java 建设和维护 API 自动化测试，保证数据隔离、断言质量和失败可定位 |
| criterion:0005 | Web UI 自动化建设 | general | 判断是否能为关键业务流程建设必要的 Web UI 自动化，并控制脆弱用例和维护成本。 | 寻找建设 Web UI 自动化并控制脆弱用例和维护成本的证据。 | job_responsibilities: 为关键业务流程建设必要的 Web UI 自动化，并控制脆弱用例和维护成本 |
| criterion:0006 | CI 流水线集成与质量跟踪 | general | 判断是否能将自动化测试接入 CI 流水线，跟踪失败、缺陷逃逸率和关键链路覆盖情况。 | 寻找将自动化测试接入 CI 流水线并跟踪失败、缺陷逃逸率和关键链路覆盖情况的证据。 | job_responsibilities: 把自动化测试接入 CI 流水线，跟踪失败、缺陷逃逸率和关键链路覆盖情况 |
| criterion:0007 | 性能测试、线上问题复盘或测试工具开发 | general | 判断是否参与性能测试、线上问题复盘或测试工具开发，推动可重复的质量改进。 | 寻找参与性能测试、线上问题复盘或测试工具开发并推动质量改进的证据。 | job_responsibilities: 参与性能测试、线上问题复盘或测试工具开发，推动可重复的质量改进 |
| criterion:0008 | 自动化测试框架使用 | required | 判断是否熟悉 pytest、JUnit/TestNG 或同类自动化框架中的至少一种。 | 寻找使用 pytest、JUnit/TestNG 或同类框架的测试项目证据。 | candidate_requirements: 熟悉 pytest、JUnit/TestNG 或同类自动化框架中的至少一种 |
| criterion:0009 | SQL 和 Linux 问题定位 | required | 判断是否能使用 SQL 和 Linux 命令辅助定位问题，并清楚记录复现步骤和结论。 | 寻找使用 SQL 和 Linux 命令定位问题并记录复现步骤和结论的证据。 | candidate_requirements: 能使用 SQL 和 Linux 命令辅助定位问题，并清楚记录复现步骤和结论 |
| criterion:0010 | 可维护 UI 自动化经验 | preferred | 判断是否有 Playwright、Cypress 或 Selenium 的可维护 UI 自动化经验。 | 寻找使用 Playwright、Cypress 或 Selenium 进行可维护 UI 自动化的证据。 | preferred_qualifications: 有 Playwright、Cypress 或 Selenium 的可维护 UI 自动化经验优先 |
| criterion:0011 | CI/CD、性能测试、容器或质量平台开发经验 | preferred | 判断是否有 Jenkins/GitLab CI、性能测试、Docker/Kubernetes 或质量平台开发经验。 | 寻找 Jenkins/GitLab CI、性能测试、Docker/Kubernetes 或质量平台开发经验证据。 | preferred_qualifications: 有 Jenkins/GitLab CI、性能测试、Docker/Kubernetes 或质量平台开发经验优先 |
| criterion:0012 | 通过质量数据推动流程改进 | preferred | 判断是否有通过质量数据推动流程改进的案例。 | 寻找通过质量数据推动流程改进的案例证据。 | preferred_qualifications: 有通过质量数据推动流程改进的案例优先 |

请重点复核的 warning：
- `importance_review_required` / `criterion:0009` / `no_explicit_signal_non_general`：评价点 importance 与原文语气或字段信号存在需要 HR 复核的不确定性

- [ ] required / preferred / general 判断正确
- [ ] 没有遗漏影响初筛的核心要求
- [ ] 没有新增 JD 不存在的门槛
- [ ] 评价点粒度适合 HR 阅读和后续评分
- [ ] 来源能够支持名称、说明和初筛重点
- 用户结论：按当前计划确认

## JD-03：商业数据分析师

- 运行状态：`succeeded`
- 评价点数量：12
- 全部来源可追溯：是
- Warning 数量：0

| ID | 名称 | 重要性 | 说明 | 初筛重点 | JD 来源 |
| --- | --- | --- | --- | --- | --- |
| criterion:0001 | 核心指标口径建设与维护 | general | 判断是否能够建设并维护获客、转化、活跃、留存和续费等核心指标口径。 | 寻找建设或维护获客、转化、活跃、留存、续费等核心指标口径的证据。 | job_responsibilities: 建设并维护获客、转化、活跃、留存和续费等核心指标口径 |
| criterion:0002 | SQL 数据提取与清洗 | general | 判断是否能够使用 SQL 完成多表数据提取、清洗和分析，建立可复用查询或数据集。 | 寻找使用 SQL 进行多表数据提取、清洗、分析，建立可复用查询或数据集的证据。 | job_responsibilities: 使用 SQL 完成多表数据提取、清洗和分析，建立可复用查询或数据集 |
| criterion:0003 | 经营看板建设与异常监控 | general | 判断是否能够使用 BI 工具建设经营看板，监控异常并解释指标变化。 | 寻找使用 BI 工具建设经营看板、监控异常并解释指标变化的证据。 | job_responsibilities: 使用 BI 工具建设经营看板，监控异常并解释指标变化 |
| criterion:0004 | 专题分析能力 | general | 判断是否能够针对活动、产品功能或客户分层开展专题分析，形成结论、限制和业务建议。 | 寻找针对活动、产品功能或客户分层开展专题分析并形成结论、限制和业务建议的证据。 | job_responsibilities: 针对活动、产品功能或客户分层开展专题分析，形成结论、限制和业务建议 |
| criterion:0005 | A/B 实验或准实验分析 | general | 判断是否能够参与 A/B 实验或准实验分析，清楚说明样本、指标、显著性和可能偏差。 | 寻找参与 A/B 实验或准实验分析，并说明样本、指标、显著性和可能偏差的证据。 | job_responsibilities: 参与 A/B 实验或准实验分析，清楚说明样本、指标、显著性和可能偏差 |
| criterion:0006 | SQL 熟练使用 | required | 判断是否能够熟练使用 SQL，完成多表关联、窗口函数、分组聚合和数据质量检查。 | 寻找 SQL 多表关联、窗口函数、分组聚合和数据质量检查的实践证据。 | candidate_requirements: 必须能够熟练使用 SQL，完成多表关联、窗口函数、分组聚合和数据质量检查 |
| criterion:0007 | 指标体系或经营分析经验 | required | 判断是否有指标体系或经营分析经验，能说明指标定义和口径变化。 | 寻找指标体系或经营分析经验，以及说明指标定义和口径变化的证据。 | candidate_requirements: 必须有指标体系或经营分析经验，能说明指标定义和口径变化 |
| criterion:0008 | BI 工具看板制作与维护 | general | 判断是否能使用 Tableau、Power BI、FineBI 或同类工具制作并维护业务看板。 | 寻找使用 Tableau、Power BI、FineBI 或同类工具制作和维护业务看板的证据。 | candidate_requirements: 能使用 Tableau、Power BI、FineBI 或同类工具制作并维护业务看板 |
| criterion:0009 | 结构化表达能力 | general | 判断是否具备结构化表达能力，能够区分数据事实、分析推断和待验证假设。 | 寻找结构化表达、区分数据事实、分析推断和待验证假设的证据。 | candidate_requirements: 具备结构化表达能力，能够区分数据事实、分析推断和待验证假设 |
| criterion:0010 | SaaS、订阅业务、销售漏斗或客户留存分析经验 | preferred | 判断是否有 SaaS、订阅业务、销售漏斗或客户留存分析经验。 | 寻找 SaaS、订阅业务、销售漏斗或客户留存分析经验证据。 | preferred_qualifications: 有 SaaS、订阅业务、销售漏斗或客户留存分析经验优先 |
| criterion:0011 | Python/pandas、统计检验或实验设计 | preferred | 判断是否熟悉 Python/pandas、统计检验或实验设计。 | 寻找 Python/pandas、统计检验或实验设计相关技能或项目证据。 | preferred_qualifications: 熟悉 Python/pandas、统计检验或实验设计者优先 |
| criterion:0012 | 推动统一指标口径经验 | preferred | 判断是否有推动业务团队采用统一指标口径的经验。 | 寻找推动业务团队采用统一指标口径的经验证据。 | preferred_qualifications: 有推动业务团队采用统一指标口径的经验优先 |

- [ ] required / preferred / general 判断正确
- [ ] 没有遗漏影响初筛的核心要求
- [ ] 没有新增 JD 不存在的门槛
- [ ] 评价点粒度适合 HR 阅读和后续评分
- [ ] 来源能够支持名称、说明和初筛重点
- 用户结论：按当前计划确认

## JD-04：B2B SaaS 产品经理

- 运行状态：`succeeded`
- 评价点数量：12
- 全部来源可追溯：是
- Warning 数量：1

| ID | 名称 | 重要性 | 说明 | 初筛重点 | JD 来源 |
| --- | --- | --- | --- | --- | --- |
| criterion:0001 | 共性问题识别与优先级判断 | general | 判断是否能够通过客户访谈、工单、销售反馈和产品数据识别共性问题，形成问题定义和优先级判断。 | 寻找通过客户访谈、工单、销售反馈和产品数据识别共性问题并判断优先级的证据。 | job_responsibilities: 通过客户访谈、工单、销售反馈和产品数据识别共性问题，形成问题定义和优先级判断 |
| criterion:0002 | 产品文档输出与跨团队协作 | general | 判断是否能够输出 PRD、流程图、原型、验收标准和上线说明，并推动研发、设计、测试和交付协作。 | 寻找输出 PRD、流程图、原型、验收标准、上线说明及推动跨团队协作的证据。 | job_responsibilities: 输出 PRD、流程图、原型、验收标准和上线说明，推动研发、设计、测试和交付协作 |
| criterion:0003 | 权限、审批或企业配置类功能方案设计 | general | 判断是否能够负责权限、审批或企业配置类功能的方案设计，处理角色、状态、异常和兼容性边界。 | 寻找权限、审批或企业配置类功能方案设计及处理角色、状态、异常和兼容性边界的证据。 | job_responsibilities: 负责权限、审批或企业配置类功能的方案设计，处理角色、状态、异常和兼容性边界 |
| criterion:0004 | 功能采用率与客户反馈跟踪 | general | 判断是否能够跟踪功能采用率、任务完成率和客户反馈，并根据数据与研究结果持续迭代。 | 寻找跟踪功能采用率、任务完成率、客户反馈并持续迭代的证据。 | job_responsibilities: 跟踪功能采用率、任务完成率和客户反馈，根据数据与研究结果持续迭代 |
| criterion:0005 | 需求池与版本范围管理 | general | 判断是否能够管理需求池和版本范围，明确标准产品、配置能力与定制需求的边界。 | 寻找管理需求池、版本范围及明确标准产品、配置能力与定制需求边界的证据。 | job_responsibilities: 管理需求池和版本范围，明确标准产品、配置能力与定制需求的边界 |
| criterion:0006 | 完整产品交付经验 | required | 判断是否具备从问题发现推进到方案、研发、验收和上线复盘的完整产品交付经验。 | 寻找完整产品交付周期中问题发现、方案、研发、验收和上线复盘的职责与成果证据。 | candidate_requirements: 必须具备完整产品交付经验，能够从问题发现推进到方案、研发、验收和上线复盘 |
| criterion:0007 | PRD、业务流程和验收标准编写 | required | 判断是否能够独立编写 PRD、业务流程和验收标准，并清楚表达异常流程。 | 寻找独立编写 PRD、业务流程、验收标准及异常流程说明的证据。 | candidate_requirements: 必须能够独立编写 PRD、业务流程和验收标准，并清楚表达异常流程 |
| criterion:0008 | 企业客户需求调研或 B2B 产品经验 | general | 判断是否具有企业客户需求调研或 B2B 产品经验，并能区分单一客户诉求和可复用产品能力。 | 寻找企业客户需求调研、B2B 产品经验及区分单一诉求与可复用能力的证据。 | candidate_requirements: 有企业客户需求调研或 B2B 产品经验，能够区分单一客户诉求和可复用产品能力 |
| criterion:0009 | 数据意识与功能指标定义 | general | 判断是否具备数据意识，能够定义功能指标并用数据或用户反馈判断效果。 | 寻找定义功能指标、使用数据或用户反馈判断效果的证据。 | candidate_requirements: 具备数据意识，能够定义功能指标并用数据或用户反馈判断效果 |
| criterion:0010 | RBAC 权限、审批流、订阅计费或多租户产品经验 | preferred | 判断是否具有 RBAC 权限、审批流、订阅计费或多租户产品经验。 | 寻找 RBAC 权限、审批流、订阅计费或多租户产品相关经验证据。 | preferred_qualifications: 有 RBAC 权限、审批流、订阅计费或多租户产品经验优先 |
| criterion:0011 | AI 辅助功能、开放 API 或平台型产品经验 | preferred | 判断是否具有 AI 辅助功能、开放 API 或平台型产品经验。 | 寻找 AI 辅助功能、开放 API 或平台型产品相关经验证据。 | preferred_qualifications: 有 AI 辅助功能、开放 API 或平台型产品经验优先 |
| criterion:0012 | 客户实施或售前协作经验 | preferred | 判断是否具有客户实施或售前协作经验。 | 寻找客户实施或售前协作相关经验证据。 | preferred_qualifications: 有客户实施或售前协作经验者优先 |

请重点复核的 warning：
- `importance_review_required` / `criterion:0001` / `explicit_weak_signal_mismatch, source_field_signal_mismatch`：评价点 importance 与原文语气或字段信号存在需要 HR 复核的不确定性

- [ ] required / preferred / general 判断正确
- [ ] 没有遗漏影响初筛的核心要求
- [ ] 没有新增 JD 不存在的门槛
- [ ] 评价点粒度适合 HR 阅读和后续评分
- [ ] 来源能够支持名称、说明和初筛重点
- 用户结论：按当前计划确认

## JD-05：制造供应链计划专员

- 运行状态：`succeeded`
- 评价点数量：12
- 全部来源可追溯：是
- Warning 数量：0

| ID | 名称 | 重要性 | 说明 | 初筛重点 | JD 来源 |
| --- | --- | --- | --- | --- | --- |
| criterion:0001 | 生产计划编制与滚动更新 | general | 判断是否能够汇总销售预测、在手订单、库存和产能信息，编制并滚动更新月度及周度生产计划。 | 寻找编制和滚动更新生产计划的职责、流程和成果证据。 | job_responsibilities: 汇总销售预测、在手订单、库存和产能信息，编制并滚动更新月度及周度生产计划 |
| criterion:0002 | 物料齐套与延期风险闭环 | general | 判断是否能够跟踪关键物料齐套、供应商交期和工单进度，识别缺料与延期风险并推动闭环。 | 寻找跟踪物料齐套、供应商交期和工单进度，识别风险并推动闭环的证据。 | job_responsibilities: 跟踪关键物料齐套、供应商交期和工单进度，识别缺料与延期风险并推动闭环 |
| criterion:0003 | 产销协同组织与记录 | general | 判断是否能够组织销售、采购、生产和仓储进行产销协同，记录决策、责任人和计划变更原因。 | 寻找组织跨部门产销协同会议、记录决策和计划变更的证据。 | job_responsibilities: 组织销售、采购、生产和仓储进行产销协同，记录决策、责任人和计划变更原因 |
| criterion:0004 | 供应链指标分析与改善建议 | general | 判断是否能够分析预测准确率、准时交付率、库存周转和呆滞料，提出可执行的改善建议。 | 寻找分析供应链指标并提出改善建议的职责和成果证据。 | job_responsibilities: 分析预测准确率、准时交付率、库存周转和呆滞料，提出可执行的改善建议 |
| criterion:0005 | ERP计划参数与基础数据维护 | general | 判断是否能够维护 ERP 中的计划参数和基础数据，保证报表口径与实际业务一致。 | 寻找维护 ERP 计划参数和基础数据、保证报表口径一致的证据。 | job_responsibilities: 维护 ERP 中的计划参数和基础数据，保证报表口径与实际业务一致 |
| criterion:0006 | 生产计划或供应链交付经验 | required | 判断是否具备生产计划、物料计划或供应链交付相关经验，能够说明完整计划流程。 | 寻找生产计划、物料计划或供应链交付相关经验及完整计划流程说明。 | candidate_requirements: 必须具备生产计划、物料计划或供应链交付相关经验，能够说明完整计划流程 |
| criterion:0007 | Excel数据整理与分析能力 | required | 判断是否能够使用 Excel 进行数据整理和分析，熟悉常用查找、透视和条件计算。 | 寻找使用 Excel 进行数据整理、透视和条件计算的实践证据。 | candidate_requirements: 必须能够使用 Excel 进行数据整理和分析，熟悉常用查找、透视和条件计算 |
| criterion:0008 | ERP/MRP实际使用经验 | general | 判断是否有 ERP/MRP 实际使用经验，理解订单、BOM、库存、采购和工单之间的基本关系。 | 寻找 ERP/MRP 实际使用经验及对订单、BOM、库存、采购和工单关系的理解证据。 | candidate_requirements: 有 ERP/MRP 实际使用经验，理解订单、BOM、库存、采购和工单之间的基本关系 |
| criterion:0009 | 跨部门推进与风险记录能力 | general | 判断是否具备跨部门推进能力，能清楚记录风险、责任人、承诺日期和处理结果。 | 寻找跨部门推进和记录风险、责任人、承诺日期及处理结果的证据。 | candidate_requirements: 具备跨部门推进能力，能清楚记录风险、责任人、承诺日期和处理结果 |
| criterion:0010 | 离散制造或电子元器件生产经验 | preferred | 判断是否有离散制造、电子元器件或多品种小批量生产经验。 | 寻找离散制造、电子元器件或多品种小批量生产经验证据。 | preferred_qualifications: 有离散制造、电子元器件或多品种小批量生产经验优先 |
| criterion:0011 | 数据分析与预测优化工具经验 | preferred | 判断是否有 Power BI、SQL、需求预测模型或安全库存优化经验。 | 寻找 Power BI、SQL、需求预测模型或安全库存优化经验证据。 | preferred_qualifications: 有 Power BI、SQL、需求预测模型或安全库存优化经验优先 |
| criterion:0012 | 供应链改善量化案例 | preferred | 判断是否有降低呆滞库存、改善准时交付或缩短计划周期的量化案例。 | 寻找降低呆滞库存、改善准时交付或缩短计划周期的量化案例证据。 | preferred_qualifications: 有降低呆滞库存、改善准时交付或缩短计划周期的量化案例优先 |

- [ ] required / preferred / general 判断正确
- [ ] 没有遗漏影响初筛的核心要求
- [ ] 没有新增 JD 不存在的门槛
- [ ] 评价点粒度适合 HR 阅读和后续评分
- [ ] 来源能够支持名称、说明和初筛重点
- 用户结论：按当前计划确认

