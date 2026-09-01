# 阶段 7：轻量评价清单驱动的 AI 初筛 5.0 最终设计

> 最终更新：2026-09-01
> 状态：已实现并完成产品验收
> 当前版本：计划 Prompt/Service/Schema `v4 / v5 / 5.0`；报告主 Prompt/Repair Prompt/Service/Schema `v10 / v2 / v11 / 5.0`

## 1. 产品目标

阶段 7 把岗位、候选人简历和 HR 决策连接成可运行、可恢复、可审计的 AI 初筛链路：

```text
HR 维护完整 JD
→ AI 生成轻量评价清单
→ HR 编辑并确认
→ Application 使用当前 Resume 发起异步初筛
→ AI 输出逐项评价和总体建议分
→ 程序校验结构、引用和安全
→ HR 阅读报告并独立决策
```

AI 只提供辅助建议，不自动通过、淘汰、发 Offer 或录用。固定输入、固定步骤和固定输出由普通 Service 编排，不使用 LangGraph。

## 2. 范围

### 2.1 包含

- Candidate、Application、Resume 的岗位级隔离；
- 根据完整五段式 JD 生成轻量评价清单；
- HR 编辑、新增、删除、合并、确认和创建新版本；
- 单人初筛、显式重新评估和同岗位最多 5 人批量重新评估；
- PostgreSQL 持久运行、租约恢复、幂等、并发和迟到响应保护；
- 当前成功报告、历史报告和过期状态；
- React 计划抽屉、初筛工作台、报告和 HR 决策交互；
- 一次受控 Repair 及 attempt/token 审计；
- 旧 1.0—4.0 计划和报告只读兼容。

### 2.2 不包含

- 自动招聘决定；
- Python 权重、加权总分或证据覆盖率评分；
- 用性别、年龄、民族、婚育等敏感属性评价候选人；
- AI 工作年限计算和达标判断；
- 阶段 8 的公开投递扩展、持久任务队列和后续招聘流程；
- 完整登录、RBAC 或多租户权限体系。

## 3. 核心对象

```text
Job
 └─ JobEvaluationPlan（评价清单及版本）

Candidate
 └─ Application（候选人申请某一岗位）
     ├─ current Resume
     ├─ ScreeningRun（异步运行和审计）
     ├─ ScreeningReport（当前及历史报告）
     └─ StageHistory（系统推进和 HR 决策历史）
```

正式评价对象是 Application。同一 Candidate 可以申请多个 Job，每个 Application 独立绑定 Resume、报告和 HR 决策，不能跨岗位复用评分。

## 4. 评价清单

### 4.1 输入

计划生成只读取 Job 的岗位基本信息、岗位背景、岗位职责、任职要求和加分项。候选人可见备注不进入模型、快照或指纹。

### 4.2 评价点

AI 通常生成约 5—12 项，技术上限为 30。每项包含：

- `criterion_id`：稳定 ID；
- `name`、`description`、`screening_focus`；
- `importance`：`required / preferred / general`；
- `origin`：`ai_from_jd / hr_added`；
- `sources`：AI 来源项必须能逐字定位到 JD；
- `hr_note`：HR 补充项必须填写，且不得伪造 JD 来源。

评价点不是权重项。程序不根据 importance 计算总分。

### 4.3 HR 编辑与版本

生成成功先进入待确认草稿。HR 可以整份原子保存、编辑、新增、删除和合并；保存使用 `edit_version` 做乐观并发保护。确认后版本只读，需要修改时创建新编辑版本。

JD 评价输入改变后，旧计划变为 outdated；非评价字段变化不得误伤计划。Screening 只消费当前、已确认、Schema 5.0 的 ready 计划。

### 4.4 最终语义规则

- 条件性要求必须保留适用条件，不能自动升格成对所有候选人无条件 required；
- 普通语义疑点通过 warning 交给 HR 复核，Service 不用关键词直接拒绝整份计划；
- 纯工作年限不生成评价点；“3 年 Java”等混合要求只保留 Java 能力主题；
- Service 只校验结构、来源、ID、安全、数量和明确禁止字段。

## 5. 初筛前置条件

只有以下条件同时成立才能 queued：

- Application 为 active；
- Job 为开放状态；
- 当前 Resume 已解析完成；
- 当前评价计划为已确认的 5.0 ready；
- 输入仍与运行快照一致。

等待状态包括 `waiting_resume` 和 `waiting_plan`；计划原因区分 missing、generating、pending_confirmation、failed、outdated 和 contract_outdated。关闭岗位使未开始任务进入 `paused / job_closed`，不强行取消已运行模型调用。

## 6. 模型输入与隐私

报告模型只接收：

- 完整 JD；
- HR 已确认的轻量评价清单；
- 当前 Application 的脱敏 Resume。

姓名、联系方式、身份证、详细地址、性别、出生日期、直接年龄、婚育、民族、籍贯、照片和外貌信息在调用前移除。学校、专业、公司、职责、项目和成果保留为能力语境，但不得只按学校或公司品牌评分。

Job、计划和 Resume 都作为不可信数据包裹，不能覆盖系统规则或诱导输出招聘决定。

AI 不计算、不比较、不判断工作年限；模型输入不再提供经历月份事实。任职日期可以作为经历定位信息保留，但不得因年限加分或扣分。

## 7. 报告合同

### 7.1 逐项评价

每个已确认评价点必须且只能出现一次：

- `criterion_id`；
- `score`：0—10 整数；
- `reason`；
- `evidence`：非零分至少一条 AI 判断依据；
- `experience_period_fact_keys=[]`；
- `calculation_note=null`。

0 分表示当前简历没有体现，不表示候选人事实上不会。程序不自动修改分数或补 evidence。

### 7.2 总体报告

DeepSeek 直接输出 0—100 总体建议分和综合说明，Python 不求和、平均或加权重算。程序只把分数映射为展示标签。

完整 5.0 报告包含：

- `strengths`；
- `gaps`；
- `risks_or_conflicts`；
- `missing_info`；
- `hr_follow_up_questions`。

五个字段必须存在；没有事实时允许诚实空列表，不为了完整性凑内容。前四类是 finding 对象，HR 问题必须是非空字符串。

### 7.3 Service 职责

Service 保留：

- 严格 JSON 和 Schema；
- criterion ID 全量交叉引用；
- 非零分 evidence 结构；
- 明确隐私泄露；
- 自动招聘决定；
- Prompt 注入；
- 输入快照、版本和事务一致性。

Service 不再按普通自然语言关键词判断候选人语义、分数方向、品牌表达或固定权衡模板。这些内容由 Prompt、人工审核和质量测试承担。

## 8. 一次受控 Repair

主报告使用 Prompt v10。首次输出只在白名单 LLM 输出合同错误时允许调用一次 Repair Prompt v2；Repair 必须返回完整报告，不能只返回补丁，也不能与旧输出拼接。

允许 Repair 的典型问题是非法 JSON、Schema 类型错误、缺字段、评价点交叉引用或低风险报告合同错误。以下情况禁止 Repair：

- 认证、配额、限流、网络和服务端故障；
- 输入、数据库、并发或运行状态错误；
- 明确隐私泄露、招聘决定或 Prompt 注入等高风险安全错误。

修正版从 JSON 开始重新通过 Schema 和 Service 全量验证；第二次仍非法则失败，不进行第二次 Repair。`ScreeningRun.attempt_count` 允许 0—3，记录实际 attempts 和 token，不保存 Key 或未脱敏输入。

## 9. 异步、幂等与并发

ScreeningRun 使用 PostgreSQL 持久化，FastAPI 生命周期轮询器通过 `FOR UPDATE SKIP LOCKED`、租约和唯一索引认领任务。

输入指纹组合 Application、JD、当前 Resume、确认计划及模型/Prompt/Schema/脱敏版本。普通触发复用相同 current 报告或非终态运行；显式重新评估即使输入相同也创建新运行。

成功时在同一事务内：

1. 复核最新输入；
2. 写入新 current 报告；
3. 把旧 current 变为历史；
4. 标记运行 succeeded。

失败、迟到响应或提交异常不得替换旧成功报告。Resume、JD 或计划变化只把旧报告标记过期，不删除历史。

## 10. HR 决策

AI 成功或失败只在 Application 仍未决时把招聘阶段推进到 `hr_review`，不得覆盖 HR 已有决定。HR 独立选择通过、备选或淘汰；决定及反转写入 StageHistory，并可关联当时的 ScreeningReport。

AI queued/running 时前端禁用 HR 决策，避免并发歧义；终态 AI 结果仍不能代替 HR 决策。

## 11. API 与前端

正式入口位于 `/api/v2/*`，React 工作台位于 `/app/*`。

评价计划界面支持草稿编辑、warning、确认、版本分叉和历史只读。初筛中心支持当前状态、当前/历史报告、过期原因、单人重新评估和最多 5 人批量重新评估；批量返回逐人成功或安全失败，不因部分失败抹掉已提交项。

报告页面展示总体建议分、逐项评分、AI 判断依据、五类辅助信息、版本和审计元数据，并明确说明 AI 仅供参考、0 分不等于不会。

## 12. 失败语义

- 基础设施错误最多按当前 Adapter/编排合同有限重试；
- 内容错误不做基础设施重试，只可能进入一次受控 Repair；
- 任何失败都不删除 Resume、Application、HR 输入或旧成功报告；
- API 只返回稳定安全错误，不暴露 Key、原始响应、堆栈或未脱敏简历；
- 旧计划合同只能只读，不能驱动新的 5.0 Screening。

## 13. 最终版本与验收

- 评价计划：`deepseek-v4-pro`、`job_evaluation_plan_lightweight_v4`、Service v5、Schema 5.0；
- 报告：`deepseek-v4-pro`、`screening_evaluation_lightweight_v10`、Repair v2、Service v11、Schema 5.0；
- Alembic：`e7f9a1b3c545`；
- 最终真实质量：20 份基础报告、15 次稳定性，共 35 次调用；报告合法 19/20，方向 14/19，分数区间 7/19，稳定性 15/15；
- 最终费用：peak 保守估算 USD 0.52694268；
- 后端、API/PostgreSQL、前端合同、TypeScript、Vite build 和人工界面验收完成。

完整机器数据和产品负责人取舍见 `2026-09-01-stage7-final-v10-v2-acceptance-review.md`。

## 14. 已知限制

1. R12 的普通“手机号用户”业务语境会被当前隐私规则保守拒绝；
2. 部分匹配及其他样本的 LLM 分数可能系统性偏低；
3. 五个 high 稳定组均为 88，存在分档锚定待观察；
4. 一次 Repair 只证明已知结构错误可以修复，不代表所有错误类型都能成功；
5. AI 结果仍需 HR 审核，不能视为招聘准确率证明。

项目负责人接受上述限制并确认阶段 7 完成。原始 raw 的 `quality_gate_passed=null` 和 `quality_conclusion_allowed=false` 保持不变；产品验收通过不等于机器门槛被改写为全绿。
