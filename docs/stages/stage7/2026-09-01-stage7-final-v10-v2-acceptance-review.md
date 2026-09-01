# 阶段 7 v10/v2 最终验收审核卡

> 日期：2026-09-01  
> 当前状态：真实 raw 与自动化已完成；原始结果继续保持 `quality_gate_passed=null`；项目负责人已接受下述已知限制，并于 2026-09-01 确认阶段 7 产品验收通过  
> 固定版本：`deepseek-v4-pro` / 主 Prompt v10 / Repair Prompt v2 / Service behavior v11 / Schema 5.0

## 1. 机器结果

- 固定执行 20 份基础报告和 15 次额外稳定性报告，共 35 个业务 case。
- 35 次 API attempts 全部获得供应商响应，基础设施失败和重试均为 0。
- 20 份基础报告中 19 份通过 JSON、Schema 与 Service，R12 被安全规则拒绝。
- 19 份合法报告中，14 份粗方向符合冻结人工标签，7 份分数进入冻结人工区间。
- 15 次稳定性报告全部合法；R01、R05、R09、R13、R17 五组均为 `88 / 88 / 88`，方向稳定且分差为 0。
- 35 份首次输出均没有白名单结构错误，因此本批 Repair 触发 0 次；Repair v2 的真实纠错能力以独立 R04 历史 raw 挑战成功结果为证据，不能把本批 0 次触发解释为 Repair 不工作。
- 成功响应合计 173,530 input tokens、75,223 output tokens；按 peak 全部 cache miss 保守估算 USD 0.52694268，低于 USD 2 硬上限。
- PostgreSQL 业务写入为 0；Key、堆栈和内部异常未写入证据。

与旧 P3 相比：基础 Service 合法率由 17/20 提升为 19/20；稳定性合法由 11/15 提升为 15/15，完整稳定组由 3/5 提升为 5/5。方向匹配绝对数量仍为 14，分数进入冻结区间由 10 降为 7，因此结构改善不能代替评分质量审核。

## 2. 当前唯一问题清单

### 问题 A：R12 隐私规则确定性误报

R12 的简历事实是转化率统计分母从“全部访问用户”改为“提交手机号用户”。模型在报告中复述了这里的业务分类词“手机号”，没有输出任何真实电话号码；Service 的 `_EXPLICIT_PRIVACY_OUTPUT_LABEL` 使用 `手机号码?`，会把“手机号”三个字本身当成敏感信息泄露，因此以 `SCREENING_EVALUATION_INVALID_MODEL_OUTPUT` 直接拒绝，且按高风险边界正确地没有进入 Repair。

这不是 LLM JSON/Schema 错误，而是 Service 安全匹配粒度过宽。是否允许“手机号用户、手机号登录、手机号渠道”等不含具体号码的业务语境，属于隐私边界调整，必须由项目负责人明确确认后才能修改；不能在验收中偷偷放宽。

### 问题 B：partial 样本存在系统性偏低

以下 5 份冻结人工方向为 partial 的简历被模型判成 low：

| Case | 模型分数 | 模型方向 | 冻结方向 | 冻结区间 |
| --- | ---: | --- | --- | --- |
| R04 | 35 | low | partial | 42—58 |
| R08 | 28 | low | partial | 38—54 |
| R16 | 18 | low | partial | 36—52 |
| R18 | 38 | low | partial | 50—64 |
| R20 | 35 | low | partial | 36—52 |

另有 R02、R06、R07、R11、R14、R15、R19 虽然粗方向符合标签，但分数仍低于冻结区间。合计 12/19 份合法报告不在原人工区间。报告摘要普遍采用“缺少核心经验”作为降分理由；需要项目负责人判断是冻结标签过于宽松，还是当前模型/Prompt 对“部分相关经验”的正向价值给得过低。没有这一人工判断，不能调整分数规则，也不能宣布质量通过。

五个 high 稳定性样本的 15 次结果全部固定为 88。这证明稳定，但也需要人工确认是否存在过强的分档锚定，而不是把“完全一致”自动视为语义质量优秀。

## 3. 项目负责人确认结果

项目负责人在查看问题解释后作出以下产品取舍：

1. R12 是不含真实号码的特殊业务语境误报，当前不修改隐私正则，接受它继续被安全侧保守拒绝。
2. partial 样本和其余区间偏低案例反映当前 LLM 评分可能偏严格；本轮不继续修改 Prompt、评分合同或人工标签，待整个平台主链完成后再专项优化。
3. 五个 high 稳定组固定为 88 的现象继续登记为“分档锚定待观察”，不在阶段 7 继续付费扩样。
4. 阶段 7 按当前产品范围验收通过并收尾，允许进入阶段 8 的需求确认门禁。

这是一项产品负责人对已知限制的接受决定，不是对原始质量数据的回算。R12 仍是 1 份 Service 拒绝，方向/区间统计仍为 `14/19` 和 `7/19`，原始 raw 的 `quality_gate_passed=null`、`quality_conclusion_allowed=false` 继续保持不可变；不得把它们改写成机器质量门槛全部通过，也不得声称隐私误报或评分偏保守已经修复。

## 4. 自动化与证据

- 最终验收专项：7 passed。
- 当前 API、Schema、Service、ScreeningRun、migration 与 PostgreSQL 专项：202 passed + 6 subtests passed。
- 后端全量：1557 passed + 425 subtests passed；8 个失败均为此前登记的 1 个旧月份断言和 7 个 I4/CLOSE-07 历史哈希基线，不是本批新增回归。
- 前端 20 个合同脚本、TypeScript 与 Vite production build 全部通过，构建转换 3121 modules。
- Alembic `current=head=e7f9a1b3c545`，`alembic check` 返回 `No new upgrade operations detected`。
- `py_compile`、证据哈希/敏感标记扫描和 `git diff --check` 以最终命令结果为准。

原始结果：`2026-09-01-stage7-final-v10-v2-raw-results.json`。  
逐 attempt raw journal：`2026-09-01-stage7-final-v10-v2-attempt-journal.jsonl`。  
零调用预检：`2026-09-01-stage7-final-v10-v2-zero-call-preflight.json`。

## 5. 阶段 7 最终结论

阶段 7 的 Application、HR 确认评价清单、AI 初筛、一次受控 Repair、ScreeningRun 审计、API/Schema/Service、React 报告和 PostgreSQL 合同已形成可继续复用的产品底座。结合既有自动化、真实 PostgreSQL/API、人工界面验收和最终 v10/v2 真实质量证据，项目负责人确认阶段 7 在上述已知限制下完成。

完成结论能证明当前范围可交付并可进入下一阶段，不能证明 LLM 评分具有普遍人工一致性、R12 隐私语境误报已经消失、Repair 对所有错误都能成功，或未来新简历无需 HR 审核。阶段 8 只能从需求确认和独立设计开始，不得把本结论当成阶段 8 业务实现授权。
