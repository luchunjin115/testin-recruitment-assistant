# 阶段 7 剩余工作与收尾计划

> 日期：2026-08-30
> 状态：用户已于 2026-08-30 整体确认；`7R5-CLOSE-02`、`7R5-CLOSE-03A`、`7R5-CLOSE-03B`、`7R5-CLOSE-04`、`7R5-CLOSE-04R` 已完成，I2 final 正式判定失败且修订后的五批整改顺序已冻结，当前停止并等待单独确认 `7R5-CLOSE-05A`
> 职责：只维护阶段 7 从当前状态到“完成评审”的唯一剩余顺序；已完成业务合同和历史证据仍以 5.0 主设计为准

## 1. 为什么单独建立这份计划

阶段 7 的业务主链已经基本实现，但进度记录混入了 1.0—5.0 历史方案、两轮真实质量结果、七组 Service 职责整改、跨电脑交接、质量工具生命周期问题和一个简历提取回归。继续从 5.0 主设计的两千多行记录中寻找“下一步”，很容易把历史失败、当前阻塞和未来收尾混为一谈。

从本文件开始，阶段 7 采用两个入口：

- `2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`：业务合同、字段、状态、安全、验收标准和完整历史证据；
- 本文件：当前进度、剩余依赖、每批边界、停止点和唯一下一步。

若旧文档中的“唯一下一步”与本文件冲突，以本文件更新日期更晚的剩余顺序为准；旧实施结果本身仍是真实历史，不删除、不改写。

## 2. 当前结论

阶段 7 现在应表述为：**产品主链已实现，真实质量验收未通过，收尾尚未完成。**

| 模块 | 当前状态 | 能证明什么 | 还不能证明什么 |
| --- | --- | --- | --- |
| 5.0 数据、API、Service、异步运行、React | 已完成 | Fake/自动化和既有 PostgreSQL 合同下主链成立 | 最终真实质量和完整端到端收尾通过 |
| 7R5-H 非付费质量门禁 | 已完成 | 冻结样本、调用/费用、write-once 和 dry-run 合同成立 | 真实模型输出一定合格 |
| 7R5-I2-E 真实 raw | 已完成但失败 | 45/45 次调用成功，费用 `$0.09143638`，计划 `10/10` | 报告 `17/20`、稳定性 `2/5` 未达到硬门槛 |
| I2 Service R1—R7 | 已完成离线整改 | Prompt v4 / Service v7 职责和旧响应回放可复核 | 新 Prompt/Service 在新真实调用中已改善质量 |
| I2 human/final | 已完成，final 判定失败 | 12 项人工指标与自动结果已合并，19 项门槛通过 13 项、失败 6 项，生命周期已正式关闭 | I2 不满足真实质量验收，不能进入 7R5-J |
| CLOSE-04/CLOSE-04R 综合整改设计 | 已完成 | 6 个失败门槛已归因，并按用户确认修订为验收合同、计划 Service、计划 Prompt、报告 Service、报告 Prompt 五批 | 尚未实施任何整改，不能证明 I3 会通过 |
| post-raw 自动化 | 已恢复 | 旧状态断言已修复，只读诊断兼容 raw/human/final，正式结果继续 write-once | 不能证明模型输出质量合格 |
| 简历提取 500 回归 | 已完成 | R1-B 已完成红灯→绿灯、定向/全量和 Resume `#2301` 真实 API 200 复验 | 不能证明所有简历格式、AI 结构化或初筛质量正确 |
| 7R5-J 真实全链收尾 | 未开始 | 已有历史局部浏览器/数据库证据 | 当前 5.0 完整 PostgreSQL/API/浏览器链尚未最终验收 |

阶段 7 不能标记完成，也不能进入阶段 8。I2 raw、既有诊断和历史结果继续只读，不能通过补写、覆盖或降低门槛把失败改成通过。

## 3. 唯一剩余主线

```text
7R5-CLOSE-00  本收尾计划确认
    ↓
7R5-CLOSE-02  post-raw 生命周期测试恢复
    ↓
7R5-CLOSE-03A I2 用户人工审计
    ↓
7R5-CLOSE-03B I2 final 与失败总账
    ↓
7R5-CLOSE-04  一次性综合整改设计
    ↓
7R5-CLOSE-04R 按用户确认修订 Service 边界与整改顺序
    ↓
7R5-CLOSE-05-* 按综合设计执行有限整改批次
    ↓
7R5-CLOSE-06A—E 独立 I3 真实质量复验
    ↓
7R5-CLOSE-07  7R5-J 真实 PostgreSQL/API/浏览器收尾
    ↓
7R5-CLOSE-08  阶段 7 完成评审
```

固定纪律：

1. 每轮只执行一个已经确认的批次，完成后立即停止。
2. 不再按模型回答逐个增加 Service 关键词、白名单、正则或样本特例。
3. I2 先形成完整人工/final 总账，再一次性决定整改范围；不得在审计过程中边看边改代码。
4. 任何生产整改完成后都不得补跑或覆盖 I2；必须使用独立 I3 路径、版本、价格和金额授权。
5. I3 未全部通过前不得进入 7R5-J；7R5-J 完成后也不得自动进入阶段 8。

## 4. 7R5-CLOSE-00：收尾计划确认

当前状态：用户已于 2026-08-30 明确表示“按照计划开始实施”，CLOSE-00 已完成。

唯一目标：把阶段 7 的剩余顺序从历史记录中分离出来，停止“发现一项、修一项、再发现下一项”的循环。

允许范围：本文件、5.0 主设计的入口说明、`PROJECT_STATE.md`、`docs/DOCUMENT_INDEX.md` 和跨阶段 `implementation-plan.md`。链路位置是文档治理，不进入“前端 → API → Schema → Service → Model → PostgreSQL”。

禁止范围：不得借整理计划继续修改已完成的 Resume 回归、修改 9 个生命周期失败、创建 I2 human/final、处理 R12/R17/S03-2、调用 DeepSeek、写 PostgreSQL 或进入 7R5-J。

交付与验证：五份文档口径一致，明确当前完成/失败/阻塞状态、唯一主线、逐批停止点和历史证据保护；执行链接/标题扫描、`git diff --check` 和工作区差异复核。

实施结果：用户已经确认本计划并授权从第一个可执行批次开始。本次确认没有授权连续执行 CLOSE-03A 及以后范围；当前只实施 CLOSE-02，完成后立即停止。

## 5. 已完成前置项：7R5-RESUME-R1-B

本计划形成期间，工作区中的 R1-B 已完成并由权威状态登记：Resume API 在调用初筛协调器前创建现有 `ResumeRead` 快照；组合测试先复现 500 红灯，再以同一合同得到 200 绿灯；Resume 定向为 `77 passed + 21 subtests passed`，后端全量为 `1312 passed + 425 subtests passed`，只保留 9 个已登记 post-raw 生命周期旧失败；真实 Resume `#2301` API 返回 200，PostgreSQL 保持 `parsed`、原文 2060 字符、`not_started`。DeepSeek 调用、token 和费用为 0。

该结果位于“前端 → **API → Schema** → Service → Model → PostgreSQL”的 API 响应边界，能证明已提交的提取成功响应不再被后续协调回滚连带失效；不能证明所有简历格式、AI 结构化或初筛质量正确。它是 CLOSE-02 的已完成依赖，不需要再次执行，也不得在后续批次顺手扩大。

## 6. 7R5-CLOSE-02：post-raw 生命周期测试恢复

依赖：R1-B 已完成、CLOSE-00 获得用户整体确认，且用户另行确认本批。

唯一目标与通俗解释：让质量工具知道“试卷已经考完并封存 raw”，历史诊断可以在 `i2_raw_complete` 状态只读运行，同时保留真正付费运行前只能处于 `i2_preflight_complete` 的门禁。

允许修改与链路：只允许 `scripts/run_stage7_7r5_quality.py`、`scripts/run_stage7_7r5i2_preflight.py`、`scripts/stage7_7r5_quality_contract.py` 中经测试证明与状态判断直接相关的最小位置，以及 `backend/tests/test_stage7_7r5_quality_runner.py`、`backend/tests/test_stage7_7r5i2_preflight.py` 和三份状态文档。该批位于离线质量工具/测试，不改变产品全链。

禁止：不得把所有 `i2_preflight_complete` 机械替换成 `i2_raw_complete`；真实 raw 入口、价格门禁和 write-once 前置状态仍必须保持 preflight-only。不得修改生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、fixture、raw/human/final、诊断或 PostgreSQL，不得调用模型。

交付与异常语义：

- 先固定 9 个失败的精确 test ID、调用路径和共同根因；
- post-raw 只读诊断在 `i2_raw_complete` 通过；pre-raw dry-run/real 入口在错误状态继续失败；
- 缺文件、损坏 JSON、错误身份/分母、生命周期越级和覆盖既有结果继续硬失败；
- 不通过删断言、skip、xfail 或删除 raw 换取绿色。

验证：生命周期矩阵、质量运行器/I2 预检专项、阶段 7 扩大回归和后端全量必须恢复零断言失败；执行 `py_compile`、静态扫描和 `git diff --check`。I2 raw/诊断身份不变，Key/Adapter/DeepSeek/API attempt/token/费用/PostgreSQL/正式结果写入均为 0。

完成标志：9 个旧状态失败全部消失且前置保护没有放宽。失败返回质量生命周期合同层。完成后停止；唯一下一步是等待确认 CLOSE-03A。

实施结果（2026-08-30）：CLOSE-02 已完成并停止。先精确复现 `9 failed, 56 passed`，确认 9 个失败都是质量工具/测试仍把已封存的 I2 当成 `i2_preflight_complete`，不是新的 AI 评分失败。`build_preflight_payload` 现允许在 `i2_raw_complete` 下只读复核；历史 R5-D/R6-D 动态重建先校验当前 raw 生命周期，再因当前 Service v7 不是历史 v5/v6 而明确拒绝。对应测试已改为断言 `i2_raw_complete`、raw 不可再写，以及下一个可写目标只能是 human audit；测试本身没有创建 human 文件。真实付费 raw 入口的 preflight-only 检查、价格门禁和 write-once 保护未改。

验证结果：质量运行器/I2 预检专项 `65 passed`；阶段 7 扩大回归 `149 passed`；后端全量 `1321 passed + 425 subtests passed + 2 warnings`，0 failures。`py_compile`、`git diff --check` 通过；两个 warning 仍是 PyPDF2 弃用提示和测试连接取消协程提示。I2 raw 仍为 943,247 bytes，SHA-256 仍为 `6583fe1b5b8219b49989166fcfbfd1c676d7b482b513b87ea3669dac6b6a0d27`，生命周期仍为 `i2_raw_complete`，human/final 均不存在；Key、Adapter、DeepSeek、API attempt、token、费用、PostgreSQL 写入和正式结果写入新增均为 0。这能证明 post-raw 离线生命周期与当前真实状态一致，不能证明 I2 内容质量已通过。

## 7. 7R5-CLOSE-03A：I2 用户人工审计

依赖：CLOSE-02 全绿，用户另行确认开始 I2-F。

唯一目标：基于封存 I2 raw 完成一次完整语义审计，得到全部问题，而不是继续只看首个程序错误。

允许范围与链路：只读 I2 raw、冻结 fixture/标签和既有诊断；Codex 可以生成逐案展示清单，并根据用户逐项明确判断写入唯一 I2 human audit 路径。链路属于质量验收，不写产品数据库。

禁止：Codex 不冒充人工审阅者，不使用 LLM-as-Judge，不替用户推断语义结论，不修改 Prompt/Schema/Service/标签/raw，不调用模型。

交付与验证：覆盖固定分母、case ID 和 12 个审计指标；至少把 R00/S00-1—3/S04-2/3 时间 key、R12 证据定位、R17 required 高分权衡、S03-2 结构、R06/R14/R15/R16/R19 已登记内容风险纳入同一问题总账。human 文件绑定 run 身份、审阅人、带时区时间和用户确认，且 write-once。

完成标志：用户完成全部必要判断，human 文件结构合法。缺少用户判断时停在人工审计层，不猜测。完成后停止；唯一下一步是等待确认 CLOSE-03B。

实施结果（2026-08-30）：用户确认问题总账，指定审阅人标识为“项目负责人（Codex辅助整理证据）”，并授权完成 107 个 required 标签、15 次稳定性计数和唯一正式 human audit。正式文件 `v5-quality-results/2026-08-28-stage7-7r5i2-quality-human-audit.json` 已创建并绑定 I2 raw 身份、raw SHA-256、冻结 fixture SHA-256 和带时区审计时间。12 项人工指标为：计划 required `55/55`、禁止新增 `0/22`、敏感评价点 `0`、非评价误纳 `0/26`；报告编造事实 `0/20`、严重事实错误 `5/20`、敏感评分 `0/20`、自动决定 `0/20`、总体方向一致 `19/20`；required 方向一致 `105/107`；稳定性严重事实错误 `5/15`、敏感评分 `0/15`。

逐项证据保留在 `v5-quality-results/7r5i2-human-review-helper/2026-08-30-stage7-7r5i2-issue-ledger.md`。校验确认 JSON 合法、12 个指标字段与冻结合同严格一致、107/107 和 15/15 分母完整、raw SHA-256 不变、生命周期为 `i2_human_complete`、I2 final 不存在；`git diff --check` 通过。CLOSE-03A 到此完成并停止，没有调用模型、写 PostgreSQL 或修改产品链。唯一下一步是等待用户另行确认 CLOSE-03B。

## 8. 7R5-CLOSE-03B：I2 final 与失败总账

依赖：CLOSE-03A 完成，用户另行确认 finalize。

唯一目标：零模型调用合并 raw 与 human，正式关闭 I2 生命周期，并把自动失败和人工问题形成一个不可覆盖的 final 总账。

允许范围：质量合同/运行器中既有 finalize 入口、必要测试和三份状态文档；只允许创建唯一 I2 final 文件，不修改 raw/human。

禁止：不得为了通过而降低第 20 节门槛、改分母、补跑、改标签或修业务代码。由于已知报告 `17/20`、稳定性达标组 `2/5`，final 必须如实计算，不能提前写成通过。

验证与完成标志：raw/human 身份、分母、人工签署、全部自动/人工门槛、费用和 write-once 校验通过；final 给出明确 `passed/failed` 及失败清单。失败的质量结论是本批可以接受的正确交付，不等于批次执行失败。完成后停止；唯一下一步是等待确认 CLOSE-04。

实施结果（2026-08-30）：CLOSE-03B 已完成并停止。质量运行器按 I2 当时真实执行合同合并封存 raw 与正式 human audit，创建唯一 `v5-quality-results/2026-08-28-stage7-7r5i2-quality-final-results.json`。19 项冻结门槛中 13 项通过、6 项失败，`quality_gate_passed=false`；失败项为报告 `20/20` 合法、报告严重事实错误为零、报告五分区 `20/20` 完整、稳定性方向至少 `4/5`、稳定性分差至少 `4/5`、稳定性严重事实错误与敏感评分均为零。费用总账保持 45 次 API attempt、`$0.09143638`，本批新增模型调用和费用均为 0。

验证确认 raw SHA-256 仍为 `6583fe1b5b8219b49989166fcfbfd1c676d7b482b513b87ea3669dac6b6a0d27`，human SHA-256 仍为 `2d89a6bee06b29b0b3c1280db78a6e4cb5e8785c4f86b5a99553a29385912430`；final SHA-256 为 `2862f18cc39c0ea5a0a8a76efdb3dd4dbe6aaccd08cae49e4e75d5bb587af988`，生命周期为 `i2_final_complete`。质量运行器/I2 预检专项为 `66 passed`，后端全量为 `1322 passed + 425 subtests passed + 2 warnings`、0 failures，`py_compile` 与 `git diff --check` 通过；两个 warning 是既有 PyPDF2 弃用提示和测试连接取消协程提示。第二次 finalize 被生命周期门禁按预期拒绝，证明 final 不可覆盖。本批位于离线质量工具层，没有修改前端、API、Schema、生产 Service、Model 或 PostgreSQL。唯一下一步是等待用户另行确认 CLOSE-04，不自动整改、执行 I3 或进入 7R5-J。

## 9. 7R5-CLOSE-04：一次性综合整改设计

依赖：I2 final 已形成，用户另行确认本批。

唯一目标与通俗解释：先把整张失败答卷看完，再决定有限的维修清单；不再修完一个首错才发现下一个。

允许范围：只修改本文件、5.0 主设计和 `PROJECT_STATE.md`，必要时新建一份独立整改补充。链路位置是设计层。

固定交付：

1. 以 I2 final 为唯一总账，逐项归属 Prompt、Schema、Service、测试/质量工具、人工标签或明确接受的产品限制；
2. 合并同一根因，禁止按 case ID 写生产特例；
3. 为每个真正需要实现的子批次写明依赖、唯一目标、允许文件和链路位置、禁止范围、业务/异常语义、自动化/真实验证、费用、完成标志、失败返回层、停止点和唯一下一步；
4. 冻结整改后的 Prompt/Service/Schema 目标版本和 I3 进入条件；
5. 用户逐批确认前不修改实现。

验证与完成标志：问题总账没有遗漏 I2 final 失败，所有实现项都有可验证合同，所有“接受风险”都有产品影响说明。若仍无法判断责任，返回人工/只读诊断层，不进入代码。完成后停止；唯一下一步是等待确认首个 `7R5-CLOSE-05-*` 子批次。

实施结果（2026-08-30）：CLOSE-04 已完成并停止。本批把 I2 final 的 6 个失败门槛以及虽未直接形成 final 失败、但会污染下一轮判断的计划扫描误报、冻结标签漂移和条件性要求问题一起归因，结论如下：

| I2 现象 | 直接原因 | 责任层与后续处理 |
| --- | --- | --- |
| 报告仅 `17/20` 合法 | R00 时间 fact key 职责误用、R12 拼接了非连续“原文”、R17 required 低分与高总分缺少可信权衡；Service 的拒绝本身正确 | 报告 Prompt/模型输出可靠性，进入 CLOSE-05C；保留 Service v7 硬保护 |
| 报告严重事实错误 `5/20` | R00/R06/R17 的事实或时间理解错误；R15/R19 同时包含模型算术矛盾和冻结标签时间漂移 | 标签合同进入 CLOSE-05A，报告 Prompt 进入 CLOSE-05C；I2 历史计数不改 |
| 五分区仅 `8/20` 全非空 | 6 例合理空优势/风险被错误判失败，3 例只遗漏微弱优势；“所有列表非空”把诚实空值和真实遗漏混在一起 | 验收合同进入 CLOSE-05A；CLOSE-05C 只改善有事实却漏报的内容，不强迫编造 |
| 稳定性方向与分差均仅 `2/5` | S00、S03、S04 多次输出先被合法性门禁拒绝，无法组成完整三次样本；不是已有证据证明分数随机大幅波动 | 先由 CLOSE-05C 提高合法输出率，再由独立 I3 重测；方向/分差门槛不降低 |
| 稳定性“严重错误与敏感评分均为零”失败 | 实际为严重事实错误 `5/15`、敏感评分 `0/15`，一个组合门槛掩盖了责任 | CLOSE-05A 将两项拆开，二者仍各自保持零容忍；严重错误由 CLOSE-05C 整改 |
| 计划粗扫描曾报 `3/26` 与 `11/22` | 中文按单字 55% 重合的近似算法把“前端开发经验/Java 后端开发经验”等无关短语误判成命中 | CLOSE-05A 把粗扫描降为诊断提示，正式语义门槛使用调用前冻结的人审标签 |
| R07 required 方向冲突 | “有某行业经验者，需……”是满足前置条件后才生效，却被计划生成为无条件 required | 计划 Prompt 条件语义进入 CLOSE-05B；I3 报告改用 HR 确认后的冻结计划快照，避免未确认草稿错误级联 |

上述归因是 CLOSE-04 当时的正式结果；其中“Service v7 全部硬保护不动、三个整改子批、I3 拆为 20 个门槛”的施工结论已被下述 CLOSE-04R 修订，历史问题证据和 I2 失败结论不变。

## 9A. 7R5-CLOSE-04R：Service 职责与整改顺序修订

依赖：CLOSE-04 完成；用户进一步确认“AI 生成内容只要结构合法、引用真实且不越过安全边界，就应交给 HR 判断，不应由 Service 继续裁判普通自然语言语义”，并明确“至今”以 `Application.applied_at` 为唯一节点；用户于 2026-08-30 授权开始实施修订后的完整方案。

唯一目标与通俗解释：把新产品原则先写成施工合同——程序负责查格式、查引用、守安全，HR 负责判断引用是否足以支持能力和分数；不让旧的 Service 硬拒绝规则继续支配后续整改。

允许范围与链路：只修改本文件、5.0 主设计和 `PROJECT_STATE.md`。链路位置是设计治理，不进入“前端 → API → Schema → Service → Model → PostgreSQL”。

禁止：不得修改或执行质量脚本、Prompt、Schema、Service、Adapter、API、Model、migration、React、fixture 或 PostgreSQL；不得读取 Key、调用模型、创建 I3 文件或覆盖 I2 raw/human/final/诊断。

固定决策：

1. Service 继续硬拒绝确定性错误：非法 JSON/Schema/ID/范围、引用不存在、非零分无引用、时间事实 key 非法、明确敏感属性、自动招聘决定、Prompt 注入、版本/生命周期/并发错误。
2. Service 退出普通语义裁判：引用是否充分证明能力、分数是否最合理、required 低分与总体高分如何权衡、某段经历是否岗位相关、普通自然语言方向与“不会/未发现”措辞不再导致整单失败；计划语义支持启发式改为 HR warning，报告直接保留引用供 HR 判断，不为此新增报告 warning Schema。
3. “至今”的唯一业务节点始终是 `Application.applied_at`；`evaluation_reference_at` 只是运行和报告中保存的同一时间副本。I3 fixture 必须逐案冻结 `application_applied_at`，并证明两者相等后再按它计算月份；R15/R19 是 I2 人工标签与既定测试投递时间不一致，不是生产代码改用了当前日期。
4. 稳定性 final 保持 19 个门槛；严重事实错误和敏感评分继续作为一个组合零容忍门槛，但结果中必须分别显示两个计数，不因展示优化增加第 20 项。
5. 计划侧 I2 六项门槛已经全部通过；后续只整改过重的 Service 语义裁判和条件性要求，不把阶段 7 整体失败误写成 JD 清单核心能力未通过。
6. 条件性要求暂不新增 `conditional/not_applicable` 结构，由 Prompt 保留完整条件并由 HR 确认；若离线合同证明三档 importance 无法诚实表达，返回设计层再决定 Schema，不得写 case 特例。

目标版本修订为：质量合同 `stage7_v5_quality_contract_v2`；计划 Prompt/Service/Schema 为 `job_evaluation_plan_lightweight_v3` / `lightweight_plan_generation_v4` / `5.0`；报告 Prompt/Service/Schema 为 `screening_evaluation_lightweight_v5` / `lightweight_report_generation_v8` / `5.0`。Schema 版本保持 5.0 不等于禁止最小受控 warning 枚举补充，但不得改变核心持久化形状或引入条件适用性字段。

验证与完成标志：三份权威文档完整写入上述边界，后续拆成 05A—05E 五个可单独确认批次；I2 六个 final 失败项没有遗漏，raw/human/final 指纹不变，`git diff --check` 通过。该结果只能证明施工合同已修订，不能证明任何代码或真实模型质量已经改善。完成后立即停止；唯一下一步是等待用户单独确认 CLOSE-05A。

## 10. 7R5-CLOSE-05-*：有限整改批次

本编号是容器，不是当前实现授权。CLOSE-04R 已把它修订为下列五个子批次；A—E 必须按顺序分别获得用户确认，不能合并授权或连续实施。

所有子批共同规则：先红灯、后最小实现、再定向/扩大/全量回归；每批只解决一个已归类根因；不得修改 I2 证据、不得真实调用、不得边实现边改变质量标签。完成全部已确认子批后停止，唯一下一步是设计并确认 CLOSE-06A。

### 10.1 7R5-CLOSE-05A：纠正 I3 验收尺子与标签合同

依赖：CLOSE-04 完成，用户另行确认本批。

唯一目标与通俗解释：先修“判卷规则”，保证下一轮既不会因合理空列表冤枉模型，也不会因粗糙中文重合或与投递时间不一致的人工标签得出假结论。

允许修改与链路：只允许离线质量合同、质量运行器、I3 合同/夹具结构与对应测试，以及三份状态文档；预期文件为 `scripts/stage7_7r5_quality_contract.py`、`scripts/run_stage7_7r5_quality.py`、必要的新 I3 零调用合同/测试、`backend/tests/test_stage7_7r5_quality_runner.py` 和直接相关质量测试。链路位置是产品全链之外的离线验收工具。

禁止：不得修改生产 Prompt、Schema、Service、Adapter、API、Model、migration、React 或 PostgreSQL；不得创建 I3 正式 raw/human/final，不得读取 Key、调用模型、修改或重算 I2。

固定交付与异常语义：

1. 质量合同升级为 `stage7_v5_quality_contract_v2`；I2 仍按其冻结 v1 合同只读解释，不回算。
2. 中文粗扫描只输出诊断候选，不再直接形成语义失败；计划的 required、禁止新增、非评价误纳和敏感项继续使用调用前冻结的人审标签计数。
3. 报告五个字段必须存在、类型正确，但优势、风险等确无事实时允许空；每个 I3 case 在调用前冻结 `material_findings[]`（必须出现的重要优势/差距/风险），正式门槛改为“重要发现遗漏为 0”。微弱、非关键观察另记诊断，不逼模型编造。
4. 每个 case 必须冻结 `application_applied_at`、`evaluation_reference_at`、实际月数和门槛月数；后二者中的参考时间必须等于投递时间，实际月数必须按该投递时间计算。任一不一致时预检直接失败，不允许开始付费调用，不得使用当前日期修补。
5. 计划生成质量仍独立使用 10 份 JD；20 份报告和 5 组稳定性使用调用前冻结且经 HR 确认的 `confirmed_plan_snapshot`，不让同轮未审核的计划草稿错误级联到报告。
6. 稳定性方向至少 `4/5`、分差不超过 10 至少 `4/5` 和极端翻转 0 保持不变；非法输出所在组仍失败。“严重事实错误和敏感评分均为 0”继续保留为一个组合门槛，同时 final 分别展示两个计数。因此 I3 final 仍为 19 项门槛。

验证与费用：先用测试精确复现旧误判红灯，再验证合理空列表、真实重要遗漏、投递时间/标签矛盾、HR 确认快照、非法稳定性组和组合门槛的两个独立计数；运行质量专项、阶段 7 扩大回归、后端全量、`py_compile`、静态扫描和 `git diff --check`。真实调用、API attempt、token、费用和 PostgreSQL 写入固定为 0。

完成标志：v2 合同能稳定区分结构错误、重要内容遗漏、诊断提示和标签错误，旧 I2 指纹与内容不变，全部自动化零失败。失败返回质量合同/冻结标签层。完成后立即停止；唯一下一步是等待用户确认 CLOSE-05B。

### 10.2 7R5-CLOSE-05B：收缩计划 Service 的语义裁判

依赖：CLOSE-05A 完成，用户另行确认本批。

唯一目标与通俗解释：让计划 Service 只确认“格式对、引用真、安全”，不再因为程序觉得生成文字和 JD 原文“不够像”而拒绝整份 HR 草稿。

允许修改与链路：以 `backend/app/services/job_evaluation_plan_service.py` 及其专项测试为核心；允许最小修改 `backend/app/schemas/job_evaluation_plan.py` 的受控 warning code、API 序列化测试、前端计划 warning 类型/文案/组件测试、配置/运行元数据和三份状态文档。链路位置为前端 → API → Schema → Service 的 warning 展示边界，不进入 Model/PostgreSQL；Schema 版本保持 5.0，计划行为版本升级为 `lightweight_plan_generation_v4`。

禁止：不得修改计划 Prompt、Adapter、API 业务流程、Model、migration、报告链、React 计划 warning 展示之外的页面、核心持久化形状、I2/I3 正式证据或 PostgreSQL；不得调用模型。不得取消来源逐字定位、敏感属性、招聘决定、Prompt 注入、JSON/Schema、数量、版本、生命周期和并发硬门禁。

固定交付与异常语义：

1. 合法 JSON、严格字段、1—30 项、稳定 ID、去重排序、真实 `source_field/source_quote`、明确安全和运行状态继续硬失败。
2. `_v5_candidate_is_supported` 一类数字/关键词/英文 token/中文连续双字语义启发式不得再造成整单失败；疑似语义扩大只生成关联评价点的 `semantic_support_review_required` warning，HR 对照引用决定是否修改或确认。
3. warning 是合法草稿，不触发内容重试；AI 原始 importance 和来源保留，程序不静默改写内容。
4. 计划 I2 已通过的 required 覆盖、禁止新增、非评价内容、敏感项与追溯门槛继续作为 I3 人工质量标准；Service 放行不等于内容自动合格。

验证与费用：先固定合法同义表达被旧启发式拒绝的红灯，以及真实引用不存在、敏感、决定、注入、非法结构仍失败的保护基线；最小实现后运行计划 Service/Schema/API 专项、warning 前端组件/类型测试、TypeScript strict、生产构建、阶段 7 扩大回归、后端全量、`py_compile` 和 `git diff --check`。真实调用、费用和 PostgreSQL 写入为 0。

完成标志：普通语义不再被程序硬拒绝，疑似扩大可由 HR warning 复核，所有确定性硬门禁全绿，行为版本为 v4。若 warning 需要改变核心持久化形状，停止并返回 CLOSE-04R，不得顺手扩表。完成后停止；唯一下一步是等待用户确认 CLOSE-05C。

### 10.3 7R5-CLOSE-05C：计划 Prompt 保留条件性要求

依赖：CLOSE-05B 完成，用户另行确认本批。

唯一目标与通俗解释：让 AI 看懂“只有满足前提才检查”的要求，不再把它偷换成对所有候选人都生效的硬门槛。

允许修改与链路：以 `backend/app/prompts/job_evaluation_plan.py` 为核心，只允许直接相关配置/版本元数据、通用 Fake/静态测试和三份状态文档。链路位置为 Schema → Service → Model 中的计划 Prompt 输入边界；计划 Service 保持 v4，Schema 保持 5.0。

禁止：不得修改计划 Service、Schema/数据库结构、API、Model、migration、报告链、React、I2/I3 正式证据或 PostgreSQL；不得调用模型。不得把 R07、P07 或任何正式冻结样本文字写进 Prompt/Few-shot。

固定交付与异常语义：计划 Prompt 升级到 `job_evaluation_plan_lightweight_v3`；通用规则与虚构 Few-shot 必须要求保留“若/当/仅在……时”等触发条件，条件性子要求不得被表述成无条件 `required`。在现有三档 importance 下，只有在前置条件成立才有意义的子要求通常作为带完整条件说明的 `general` 草稿交给 HR 复核；模型不得删掉触发条件，也不得把不存在前置条件写入清单。HR 编辑确认权、来源追溯、安全和语义 warning 不变。

验证与费用：先建立条件成立、条件不成立、无条件 required、preferred、否定/转折和多来源的通用红灯合同，再最小修改 Prompt；运行 Prompt/计划专项、正式样本隔离扫描、阶段 7 扩大回归、后端全量、`py_compile` 和 `git diff --check`。真实调用与费用为 0。

完成标志：Prompt v3 的条件保留和不升格规则被离线合同固定，Service v4/Schema 5.0 与既有确定性保护全绿。若三档 importance 无法在不扭曲业务含义的情况下满足合同，停止并返回 CLOSE-04R 设计结构化适用性字段；不得强行通过测试。完成后停止；唯一下一步是等待用户确认 CLOSE-05D。

### 10.4 7R5-CLOSE-05D：收缩报告 Service 的语义裁判

依赖：CLOSE-05C 完成，用户另行确认本批。

唯一目标与通俗解释：报告只要格式合法、引用确实在简历里、没有越过安全边界，就交给 HR 阅读；Service 不再替 HR 判断“这段引用够不够证明能力、这个分数合不合理”。

允许修改与链路：以 `backend/app/services/screening_evaluation_service.py` 和报告 Service 专项测试为核心，允许直接相关行为版本/运行元数据和三份状态文档。链路位置为 Schema → Service；报告行为版本升级为 `lightweight_report_generation_v8`，Schema 版本保持 5.0。

禁止：不得修改报告 Prompt、核心报告 Schema/Model/API/React、数据库结构、质量标签、I2/I3 证据或 PostgreSQL；不得调用模型。不得取消严格 JSON/Schema、评价点完整交叉引用、分数范围、非零分至少一条 evidence、quote 在脱敏简历中逐字定位、时间 fact key 有效且参考时间等于 `Application.applied_at`、明确敏感属性、招聘决定和 Prompt 注入硬门禁。

固定交付与异常语义：required 低分与总体高分的权衡、0 分固定措辞、“未发现”与“不会”的普通语言差别、品牌表达、普通方向词和经历是否岗位相关不再造成整单失败；它们由 Prompt 约束并在质量验收/HR 阅读中判断。报告不新增 warning Schema，HR 直接查看逐项分数、理由和原文引用；Service 放行不等于内容正确。时间 Service 继续按投递时间生成事实，报告 Service 只校验所引用 fact key 的身份、可用性和计算说明存在，不判断自然语言月份结论或岗位相关性。

验证与费用：先建立普通语义响应被旧规则拒绝的红灯，同时锁定伪造引用、非零分无证据、非法 key、敏感属性、自动决定、注入和结构错误继续失败；最小实现后运行报告 Service/Schema/API 相关专项、阶段 7 扩大回归、后端全量、`py_compile` 和 `git diff --check`。真实调用、费用和 PostgreSQL 写入为 0。

完成标志：报告语义判断交回 HR，确定性引用/安全硬保护无降级，行为版本为 v8，I2 文件未改。若发现某项被移除规则其实属于明确安全或可百分百确定的引用真实性检查，停止并返回 CLOSE-04R 重新归类。完成后停止；唯一下一步是等待用户确认 CLOSE-05E。

### 10.5 7R5-CLOSE-05E：报告 Prompt 可靠性整改

依赖：CLOSE-05D 完成，用户另行确认本批。

唯一目标与通俗解释：Service 不再替模型理解语义以后，由 Prompt 明确要求模型自己把时间、原文引用、非零分证据和总分逻辑检查清楚，尽量减少需要 HR 纠正的内容。

允许修改与链路：以 `backend/app/prompts/screening_evaluation.py` 为核心，只允许直接相关配置/版本元数据、通用 Fake/静态测试和三份状态文档。链路位置为 Schema → Service → Model 的报告 Prompt 边界；报告 Service 保持 v8，Schema 保持 5.0。

禁止：不得恢复已退出的 Service 语义硬拒绝，不得改 API、Model、migration、React、质量标签或 I2 证据，不得调用模型。不得把 R00/R06/R12/R15/R17/R19/S00/S02/S03 的正式文本复制进 Prompt/Few-shot。

固定交付与异常语义：报告 Prompt 升级到 `screening_evaluation_lightweight_v5`，使用通用规则、虚构平衡 Few-shot 和静默自检固定以下能力：`evaluation_reference_at` 等于投递时间且只使用后端月份事实；实际月数与门槛月数先比较再下结论；Resume quote 必须连续可定位而非跨段拼接；每个非零分都有证据；required 低分与高总体分应给出可信权衡；声称“没有/无法确认”前重查明显教育、行业与工作经历；有真实弱优势时不遗漏，确实没有时允许空；时间 fact key 只作计算引用、不能冒充 Resume 来源。

验证与费用：先用完全虚构的通用 bad case 建立红灯，再做 Prompt 最小实现；运行报告 Prompt、Service v8 确定性保护、Schema、质量元数据、阶段 7 扩大回归、后端全量、`py_compile`、正式样本隔离扫描和 `git diff --check`。所有模型行为使用 Fake/Mock，真实调用、API attempt、token、费用和 PostgreSQL 写入为 0。

完成标志：Prompt v5 合同全绿，Service v8/Schema 5.0 确定性硬保护无降级，I2 文件未改。真实语义改善仍只能由 I3 证明。完成后立即停止；唯一下一步是等待用户确认 CLOSE-06A。

五个子批全部完成且自动化为零失败后，才满足 I3 设计入口条件。CLOSE-06A 还必须另行冻结全新未参与 Prompt 调整的 10 份 JD、20 组 JD/Resume、其中 5 组稳定性、逐案 `application_applied_at`、v2 标签、`material_findings[]`、HR 确认计划快照和实际版本，并由用户审核后才能进入 06B 价格门禁；任何真实调用仍需 06C 的独立金额授权。

## 11. 7R5-CLOSE-06A—E：独立 I3 真实质量复验

I3 必须是新 run，不能继续、补跑、覆盖或 finalize I2。目标版本已由 CLOSE-04R 冻结；CLOSE-05 完成后由 CLOSE-06A 核对实际实现版本并冻结全新路径、未参与 Prompt 调整的新鲜样本、投递时间、标签与 HR 确认计划快照，预算再由 CLOSE-06B 单独查询和授权。I3 final 继续使用 19 项门槛。

| 批次 | 唯一目标 | 费用与停止点 |
| --- | --- | --- |
| CLOSE-06A | 新路径/生命周期、冻结样本/标签/版本、dry-run/Fake/全量非付费预检 | 0 调用；完成后等价格门禁确认 |
| CLOSE-06B | 查询 DeepSeek 官方实时价格、记录 24 小时快照和请求美元上限 | 不读 Key、不调用；完成后等 real 授权 |
| CLOSE-06C | 唯一一轮 I3 real raw | 只写 raw；失败或成功都停止，不补跑 |
| CLOSE-06D | 用户完成人工审计 | 0 调用；只写 human，Codex 不代审 |
| CLOSE-06E | final 合并全部门槛 | 0 调用；只有明确全部通过才可进入 CLOSE-07 |

五批必须分别确认。任一质量硬门槛失败，返回 CLOSE-04 重新评估总账和产品取舍，不得直接进入 7R5-J。

## 12. 7R5-CLOSE-07：7R5-J 真实全链收尾

依赖：I3 final 全部门槛通过，用户另行确认。

唯一目标：用真实 PostgreSQL、真实 `/api/v2` 和真实浏览器证明 5.0 可操作、可恢复、可审计。

允许范围与链路：覆盖“前端 → API → Schema → Service → Model → PostgreSQL”全链；只允许修复验收发现且不改变已确认合同的最小缺陷。若核心合同、数据或完成标准需要变化，返回 CLOSE-04/专项设计并重新确认。

固定验证：5.0 计划生成/编辑/确认/过期/历史，Application/Resume 隔离，单人/最多 5 人批量，幂等/并发/失败/迟到/current 历史，HR 决策/反转/StageHistory，migration 往返/current=head/check，数据库前后计数，桌面/平板/手机、键盘/焦点/危险确认、控制台/网络和敏感信息检查。

完成标志：第 21 节全部项目通过，自动化和 I3 证据仍有效。完成后停止；唯一下一步是等待确认 CLOSE-08。

## 13. 7R5-CLOSE-08：阶段 7 完成评审

依赖：CLOSE-07 完成，用户另行确认评审。

唯一目标：逐项核对 5.0 主设计第 34 节完成标准，更新阶段状态、实施总计划、文档索引和交接说明。

完成条件：产品主链、自动化、I3 真实质量、PostgreSQL/API/浏览器、费用、证据、隐私和 HR 决策边界全部通过；明确记录能证明与不能证明的范围。完成后阶段 7 才可标记完成，并立即停止；阶段 8 仍须重新完成自己的需求确认门禁。

## 14. 当前停止点

当前 CLOSE-00、CLOSE-02、CLOSE-03A、CLOSE-03B、CLOSE-04 和 CLOSE-04R 均已完成。I2 生命周期保持 `i2_final_complete`；修订后的综合整改已写成 05A—05E，但尚未实施。当前停止在 CLOSE-05A 单独授权门禁：

- 不重复修改或复验已完成的 Resume R1-B；
- 不再执行 CLOSE-02 测试、真实 API、数据库或模型调用；
- 不覆盖、重算或重新 finalize I2 raw/human/final；
- 不提前修改 Prompt、Schema、Service 或质量工具；
- 不连续进入 CLOSE-05B—05E、I3、7R5-J 或阶段 8。

CLOSE-05A 只有在用户另行明确确认后才能先修 I3 验收尺子与标签合同；当前文档设计完成不等于实现授权。
