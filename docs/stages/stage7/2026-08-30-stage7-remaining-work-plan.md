# 阶段 7 剩余工作与收尾计划

> 日期：2026-08-30
> 状态：阶段 7 已于 2026-09-01 完成产品验收并关闭。CLOSE-07 的未封存记录、I2 final 失败以及 I3-R1/I4/final-v10-v2 raw 均按原结论保留；项目负责人明确接受 R12 安全侧误报和评分偏保守为非阻塞已知限制。阶段 8 仅允许进入需求确认与独立设计门禁
> 职责：只维护阶段 7 从当前状态到“完成评审”的唯一剩余顺序；已完成业务合同和历史证据仍以 5.0 主设计为准

## 1. 为什么单独建立这份计划

阶段 7 的业务主链已经基本实现，但进度记录混入了 1.0—5.0 历史方案、两轮真实质量结果、七组 Service 职责整改、跨电脑交接、质量工具生命周期问题和一个简历提取回归。继续从 5.0 主设计的两千多行记录中寻找“下一步”，很容易把历史失败、当前阻塞和未来收尾混为一谈。

从本文件开始，阶段 7 采用两个入口：

- `2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`：业务合同、字段、状态、安全、验收标准和完整历史证据；
- 本文件：当前进度、剩余依赖、每批边界、停止点和唯一下一步。

若旧文档中的“唯一下一步”与本文件冲突，以本文件更新日期更晚的剩余顺序为准；旧实施结果本身仍是真实历史，不删除、不改写。

## 2. 当前结论

阶段 7 现在应表述为：**产品主链已实现，项目负责人在保留真实失败数据和两项已知限制的前提下完成产品验收，阶段已关闭。**

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
| 工作年限退出 AI 初筛 | 已完成产品决定，尚未实现 | 已明确纯年限退出、混合要求保留能力、稳定性方向/分差只作诊断 | 代码、v3 质量合同和新真实质量尚未验证 |
| 7R5-J 真实全链收尾 | 未开始 | 已有历史局部浏览器/数据库证据 | 当前 5.0 完整 PostgreSQL/API/浏览器链尚未最终验收 |

阶段 7 已允许进入阶段 8 的需求确认门禁，但 I2 raw、既有诊断和全部历史结果继续只读；不得通过补写、覆盖或回算把失败改成机器通过。阶段 8 生产实现仍须完成自己的独立设计和用户确认。

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
7R5-CLOSE-05A—F 已完成的有限整改
    ↓
7R5-CLOSE-06A—C I3-R1 已封存 raw；因产品边界变化不再继续 final
    ↓
7R5-CLOSE-04R2 工作年限退出 AI 初筛的合同修订
    ↓
7R5-CLOSE-05G—I 新合同、计划链、报告链逐批整改
    ↓
7R5-CLOSE-06R2-A—E 独立 I4 真实质量复验
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

实施结果（2026-08-31）：CLOSE-05A 已完成并停止。离线合同新增 `stage7_v5_quality_contract_v2`，同时把 I2 明确登记为冻结 v1、禁止回算；中文粗略重合只返回诊断候选，报告五分区字段必须存在且为列表但允许合理为空，正式内容门槛改为调用前 `material_findings[]` 的遗漏数为 0。时间案例固定投递/评价参考时间、计算区间、实际月数和门槛月数，参考时间不等于投递时间或实际月数算错时直接预检失败；报告/稳定性只接受带确认人、确认时间和内容指纹的 HR `confirmed_plan_snapshot`。稳定性 `4/5`、分差 10 的 `4/5`、极端翻转 0、非法输出组失败均未降低；严重事实错误与敏感评分保持一个稳定性组合门槛，两个计数分别展示，final 仍为 19 项。

测试先得到精确 `12 failed` 红灯，再转为质量专项 `39 passed`；阶段 7 扩大回归 `263 passed + 3 subtests passed`，后端全量 `1336 passed + 425 subtests passed + 2 warnings`、0 failures，静态专项 `23 passed`，`py_compile` 与差异检查通过。两条 warning 为既有 PyPDF2 弃用和异步连接取消提示。I2 三份正式文件无 Git 差异、生命周期仍为 `i2_final_complete`；按用户后续指示不再把本机换行符导致的字节 SHA 差异作为阻塞。生产 Prompt/Schema/Service/Adapter/API/Model/migration/React、PostgreSQL 均未修改；I3 正式 raw/human/final 未创建；Key 读取、模型调用、API attempt、输入/输出 token、费用和 PostgreSQL 写入均为 0。该结果能证明下一轮验收尺子已离线固定，不能证明生产 AI 已整改或真实质量会通过。唯一下一步是等待用户另行确认 CLOSE-05B。

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

实施结果（2026-08-31）：CLOSE-05B 已完成并停止。计划 Service 行为版本升级到 `lightweight_plan_generation_v4`，删除 `_v5_candidate_is_supported` 对整份计划抛出 `JOB_EVALUATION_PLAN_V5_UNSUPPORTED_CRITERION` 的路径；原数字、显式要求、排他表达、英文 token 和中文连续双字启发式只用于生成关联稳定 `criterion_id` 的 `semantic_support_review_required` warning。warning 是合法 `pending_confirmation` 草稿，不触发内容重试，AI 名称、importance 与逐字来源均未改写；HR 可对照来源后编辑或确认。Schema 5.0 只新增受控 warning 枚举与引用规则，既有 JSON 持久化形状和 API 业务流程不变，前端增加对应类型和可操作文案。

真实 `source_field/source_quote` 定位、严格 JSON/Schema、1—30 项、稳定 ID、去重排序、Prompt 污染、敏感属性和招聘决定继续硬失败。精确红灯为后端 `10 failed + 61 passed`、从正确前端目录执行为 `1 failed + 1 passed`；最小实现后计划 Service/质量元数据 `71 passed`、计划 Schema/API/编辑扩大专项 `102 passed`、前端全量 `58 passed`，TypeScript 严格检查和 Vite 生产构建通过（3121 模块）。阶段 7/计划扩大回归 `627 passed + 52 subtests passed`，后端全量 `1336 passed + 425 subtests passed + 2 warnings`、0 failures，静态专项 `23 passed`，`py_compile`、旧硬拒绝符号扫描和 `git diff --check` 通过。两条 warning 仍为既有 PyPDF2 弃用和异步连接取消提示。

本批没有修改计划 Prompt、Adapter、API 业务流程、Model、migration、报告链、核心持久化形状、I2/I3 正式证据或 PostgreSQL；没有读取 Key、调用模型、产生 API attempt/token/费用或 PostgreSQL 写入。它能证明普通语义疑点不再让整份草稿失败且 HR 可看到提醒，不能证明被放行内容正确、计划 Prompt 已能保留条件或真实模型质量改善。唯一下一步是等待用户另行确认 CLOSE-05C。

### 10.3 7R5-CLOSE-05C：计划 Prompt 保留条件性要求

依赖：CLOSE-05B 完成，用户另行确认本批。

唯一目标与通俗解释：让 AI 看懂“只有满足前提才检查”的要求，不再把它偷换成对所有候选人都生效的硬门槛。

允许修改与链路：以 `backend/app/prompts/job_evaluation_plan.py` 为核心，只允许直接相关配置/版本元数据、通用 Fake/静态测试和三份状态文档。链路位置为 Schema → Service → Model 中的计划 Prompt 输入边界；计划 Service 保持 v4，Schema 保持 5.0。

禁止：不得修改计划 Service、Schema/数据库结构、API、Model、migration、报告链、React、I2/I3 正式证据或 PostgreSQL；不得调用模型。不得把 R07、P07 或任何正式冻结样本文字写进 Prompt/Few-shot。

固定交付与异常语义：计划 Prompt 升级到 `job_evaluation_plan_lightweight_v3`；通用规则与虚构 Few-shot 必须要求保留“若/当/仅在……时”等触发条件，条件性子要求不得被表述成无条件 `required`。在现有三档 importance 下，只有在前置条件成立才有意义的子要求通常作为带完整条件说明的 `general` 草稿交给 HR 复核；模型不得删掉触发条件，也不得把不存在前置条件写入清单。HR 编辑确认权、来源追溯、安全和语义 warning 不变。

验证与费用：先建立条件成立、条件不成立、无条件 required、preferred、否定/转折和多来源的通用红灯合同，再最小修改 Prompt；运行 Prompt/计划专项、正式样本隔离扫描、阶段 7 扩大回归、后端全量、`py_compile` 和 `git diff --check`。真实调用与费用为 0。

完成标志：Prompt v3 的条件保留和不升格规则被离线合同固定，Service v4/Schema 5.0 与既有确定性保护全绿。若三档 importance 无法在不扭曲业务含义的情况下满足合同，停止并返回 CLOSE-04R 设计结构化适用性字段；不得强行通过测试。完成后停止；唯一下一步是等待用户确认 CLOSE-05D。

实施结果（2026-08-31）：CLOSE-05C 已完成并停止。计划 Prompt 升级到 `job_evaluation_plan_lightweight_v3`。Prompt 现在先判断“若/当/仅在……时”的触发条件是否已经由完整 JD 明确成立：已经成立时仍保留适用场景，再按条件内部强弱判断 importance；尚未明确成立时不得自行假定，只有满足前提才有意义的子要求通常保留完整条件并作为 `general` 草稿交给 HR，不能升格成对所有候选人无条件生效的 required。无条件要求仍按真实强弱判断，模型不得凭空编造前置条件。

新增两组完全虚构、去标识化 Few-shot，分别覆盖条件已成立和条件未确认；连同原有无条件 required、preferred、普通 general、否定/转折/放宽和多来源示例形成七组通用语义矩阵。精确红灯为 `4 failed + 6 passed`，失败点是旧 Prompt 仍为 v2 且缺少两组条件合同；实现后 Prompt/计划/配置/质量专项 `87 passed + 16 subtests passed`，阶段 7/计划扩大回归 `632 passed + 52 subtests passed`，后端全量 `1341 passed + 425 subtests passed + 2 warnings`、0 failures，静态专项 `23 passed`，`py_compile`、正式冻结样本隔离和 `git diff --check` 通过。

本批只修改计划 Prompt、直接关联的配置/当前质量版本、通用测试和三份状态文档。计划 Service 保持 `lightweight_plan_generation_v4`，Schema 保持 5.0；I2 冻结执行合同中的计划 Prompt 仍为 v2。没有修改报告链、API、Model、migration、React、PostgreSQL 或 I2 正式结果，没有创建 I3 正式文件；Key 读取、真实模型调用、API attempt、token、费用与 PostgreSQL 写入均为 0。该结果能证明离线 Prompt 合同和回归成立，不能证明真实模型每次都遵守条件、真实计划质量已改善或 I3 会通过。唯一下一步是等待用户另行确认 CLOSE-05D。

### 10.4 7R5-CLOSE-05D：收缩报告 Service 的语义裁判

依赖：CLOSE-05C 完成，用户另行确认本批。

唯一目标与通俗解释：报告只要格式合法、引用确实在简历里、没有越过安全边界，就交给 HR 阅读；Service 不再替 HR 判断“这段引用够不够证明能力、这个分数合不合理”。

允许修改与链路：以 `backend/app/services/screening_evaluation_service.py` 和报告 Service 专项测试为核心，允许直接相关行为版本/运行元数据和三份状态文档。另允许在 `backend/app/schemas/screening_evaluation.py` 的 `CriterionAssessment.validate_score_evidence_shape` 中只删除“0 分 reason 必须逐字包含固定句式”的语义分支，并修改直接对应的 Schema 测试；不得借此改变字段、类型、长度、数量、版本或持久化形状。链路位置为 Schema → Service；报告行为版本升级为 `lightweight_report_generation_v8`，Schema 版本保持 5.0。

禁止：除上一段明确允许删除的单个零分固定措辞语义分支外，不得修改报告 Prompt、核心报告 Schema/Model/API/React、数据库结构、质量标签、I2/I3 证据或 PostgreSQL；不得调用模型。不得取消 `reason` 必填与合法非空文本、严格 JSON/Schema、0 分不得附带正向 evidence、评价点完整交叉引用、分数范围、非零分至少一条 evidence、quote 在脱敏简历中逐字定位、时间 fact key 有效且参考时间等于 `Application.applied_at`、明确敏感属性、招聘决定和 Prompt 注入硬门禁。

固定交付与异常语义：每个分数仍必须提供 `reason`，Schema 只判断它是合法非空文本，不判断必须出现哪句话，也不维护“未发现”的同义词白名单。0 分仍不得附带正向 evidence，非零分仍必须有真实可定位 evidence。required 低分与总体高分的权衡、0 分固定措辞、“未发现”与“不会”的普通语言差别、品牌表达、普通方向词和经历是否岗位相关不再造成整单失败；它们由 Prompt 约束并在质量验收/HR 阅读中判断。报告不新增 warning Schema，HR 直接查看逐项分数、理由和原文引用；Service/Schema 放行不等于内容正确。时间 Service 继续按投递时间生成事实，报告 Service 只校验所引用 fact key 的身份、可用性和计算说明存在，不判断自然语言月份结论或岗位相关性。

验证与费用：先建立“0 分有非空 reason 但没有固定口令”以及其他普通语义响应被旧规则拒绝的红灯，同时锁定 reason 缺失/空文本、0 分附带正向证据、伪造引用、非零分无证据、非法 key、敏感属性、自动决定、注入和结构错误继续失败；最小实现后运行报告 Service/Schema/API 相关专项、阶段 7 扩大回归、后端全量、`py_compile` 和 `git diff --check`。真实调用、费用和 PostgreSQL 写入为 0。

完成标志：报告语义判断交回 HR，确定性引用/安全硬保护无降级，行为版本为 v8，I2 文件未改。若发现某项被移除规则其实属于明确安全或可百分百确定的引用真实性检查，停止并返回 CLOSE-04R 重新归类。完成后停止；唯一下一步是等待用户确认 CLOSE-05E。

实施前合同修订（2026-08-31）：只读检查发现解析顺序是先由 `AIScreeningEvaluationV5Output` 完成 Schema 校验，再进入报告 Service；当前 `CriterionAssessment` Schema 与 Service 同时要求 0 分 reason 逐字包含“当前简历未发现相关证据”。因此只删除 Service 重复入口仍会被 Schema 提前拒绝，无法兑现本批已经确认的“0 分固定措辞不再整单失败”。用户确认采用“reason 继续必填，但 Schema/Service 不裁判其自然语言内容”的边界，本节据此增加上述唯一 Schema 例外；Schema 版本和数据形状保持 5.0。该轮只修订三份权威文档，没有修改代码、测试或证据；修订后的 05D 仍须再次获得明确实施确认。

实施结果（2026-08-31）：修订后的 CLOSE-05D 已完成并停止。`CriterionAssessment` 仍要求非空 `reason`，0 分仍禁止正向 evidence，非零分仍要求至少一条 evidence；唯一 Schema 变化是删除 0 分 reason 必须逐字包含固定句式的语义分支，版本、字段和持久化形状保持 5.0。报告 5.0 Service 主路径删除固定零分措辞、“未发现/不会”、品牌表达、普通分数方向和 required 低分/高总体分固定权衡模板的拒绝入口；报告不新增 warning，AI 原分数、理由、分区和真实引用直接交给 HR。行为版本升级为 `lightweight_report_generation_v8`，Prompt 正文和版本保持 `screening_evaluation_lightweight_v4`。

精确红灯为 `10 failed + 111 passed`；最小实现后报告专项 `121 passed`，报告 Schema/Service/Adapter/API/migration 扩大专项 `187 passed + 49 subtests passed`，阶段 7/报告扩大回归 `398 passed + 49 subtests passed`，后端全量 `1348 passed + 425 subtests passed + 2 warnings`、0 failures，静态专项 `23 passed`，`py_compile` 与 `git diff --check` 通过。扩大回归期间同步纠正旧测试：封存 R7-D v7 诊断继续只读验证，当前 v8 明确拒绝跨版本动态重建，不修改或重新生成历史诊断。

严格 JSON/Schema、reason 必填、0 分无正向 evidence、非零分有 evidence、评价点 ID 全量交叉引用、quote 在脱敏 Resume 中逐字定位、时间 fact key 存在/唯一/可用及非空 key 的 calculation_note、明确隐私泄露、招聘决定和 Prompt 注入保护均保持全绿。I2 冻结执行合同仍记录报告 Service v6，正式结果无 Git 差异且生命周期仍为 `i2_final_complete`；没有 I3 正式文件。报告 Prompt 正文、API、Model、migration、React、PostgreSQL 均未修改；Key、真实模型调用、API attempt、token、费用和 PostgreSQL 写入均为 0。本批能证明 Service/Schema 不再按普通语义拒绝整单且确定性保护未降级，不能证明放行内容正确、真实模型质量改善或 I3 会通过。唯一下一步是等待用户另行确认 CLOSE-05E。

### 10.5 7R5-CLOSE-05E：报告 Prompt 可靠性整改

依赖：CLOSE-05D 完成，用户另行确认本批。

唯一目标与通俗解释：Service 不再替模型理解语义以后，由 Prompt 明确要求模型自己把时间、原文引用、非零分证据和总分逻辑检查清楚，尽量减少需要 HR 纠正的内容。

允许修改与链路：以 `backend/app/prompts/screening_evaluation.py` 为核心，只允许直接相关配置/版本元数据、通用 Fake/静态测试和三份状态文档。链路位置为 Schema → Service → Model 的报告 Prompt 边界；报告 Service 保持 v8，Schema 保持 5.0。

禁止：不得恢复已退出的 Service 语义硬拒绝，不得改 API、Model、migration、React、质量标签或 I2 证据，不得调用模型。不得把 R00/R06/R12/R15/R17/R19/S00/S02/S03 的正式文本复制进 Prompt/Few-shot。

固定交付与异常语义：报告 Prompt 升级到 `screening_evaluation_lightweight_v5`，使用通用规则、虚构平衡 Few-shot 和静默自检固定以下能力：`evaluation_reference_at` 等于投递时间且只使用后端月份事实；实际月数与门槛月数先比较再下结论；Resume quote 必须连续可定位而非跨段拼接；每个非零分都有证据；required 低分与高总体分应给出可信权衡；声称“没有/无法确认”前重查明显教育、行业与工作经历；有真实弱优势时不遗漏，确实没有时允许空；时间 fact key 只作计算引用、不能冒充 Resume 来源。

验证与费用：先用完全虚构的通用 bad case 建立红灯，再做 Prompt 最小实现；运行报告 Prompt、Service v8 确定性保护、Schema、质量元数据、阶段 7 扩大回归、后端全量、`py_compile`、正式样本隔离扫描和 `git diff --check`。所有模型行为使用 Fake/Mock，真实调用、API attempt、token、费用和 PostgreSQL 写入为 0。

完成标志：Prompt v5 合同全绿，Service v8/Schema 5.0 确定性硬保护无降级，I2 文件未改。真实语义改善仍只能由 I3 证明。完成后立即停止；唯一下一步是等待用户确认 CLOSE-06A。

实施结果（2026-08-31）：本批先建立 `19 failed + 125 passed + 16 subtests passed` 的精确红灯，覆盖 Prompt v5 版本、投递时间副本、`actual_months`/`threshold_months` 比较、连续 quote、非零分证据、required 低分/高总体分权衡、明显教育/行业/工作经历重查、弱优势防遗漏、时间 key 只作计算引用、自然 0 分措辞、静默自检和含时间事实的虚构 Few-shot。最小实现后报告 Prompt 升级为 `screening_evaluation_lightweight_v5`，报告 Service 保持 `lightweight_report_generation_v8`，Schema 保持 5.0；固定结构仍为 10 节、Few-shot 仍为 4 个，没有复制 R00/R06/R12/R15/R17/R19/S00/S02/S03 正式文本。生产 Schema 当前要求 gaps、missing_info、hr_follow_up_questions 非空，因此 Prompt 只允许 Schema 已支持的 strengths/risks 合理为空，本批未越界修改 Schema。

实现后专项为 `144 passed + 16 subtests passed`，阶段 7 扩大回归 `372 passed + 3 subtests passed`，后端全量 `1360 passed + 425 subtests passed + 2 warnings`、0 failures，静态/Prompt 扫描 `55 passed`；`py_compile`、正式样本隔离扫描和 `git diff --check` 通过。I2 正式目录无 Git 差异，没有 I3 正式文件；API、Schema、Service 业务逻辑、Model、migration、React、PostgreSQL 均未修改，Key、真实模型调用、API attempt、token、费用与 PostgreSQL 写入均为 0。本批能证明 Prompt v5 的离线文字合同、版本接线和现有确定性回归成立，不能证明真实模型必然遵守、语义质量已经改善或 I3 会通过。唯一下一步是等待用户另行确认 CLOSE-06A。

### 10.6 7R5-CLOSE-05F：报告五分区诚实空列表合同对齐

依赖：CLOSE-05E 完成；用户已确认产品方向，但新增实施顺序写入本文后仍须再次确认本批，才能修改代码。

唯一目标与通俗解释：报告的五个栏目必须一直存在，但确实没有真实内容时可以留空，不能为了通过程序检查而强迫模型编造一条差距、缺失信息或追问。

允许修改与链路：以 `backend/app/schemas/screening_evaluation.py` 的 `AIScreeningEvaluationV5Output` 和 `ScreeningEvaluationV5ReportPayload` 为核心，删除 gaps、missing_info、hr_follow_up_questions 的最小长度限制；同步 `backend/app/prompts/screening_evaluation.py` 的分区规则、合法虚构 Few-shot 和版本元数据，以及直接相关的 Schema、Prompt、Service、Adapter/API 序列化、持久化兼容、配置、静态测试和三份状态文档。链路位置为 API → Schema → Service → Model 的报告输出合同；Prompt 目标递增为 `screening_evaluation_lightweight_v6`，Service 保持 `lightweight_report_generation_v8`，Schema 版本保持 5.0。数据库 JSON 形状和字段名不变，不需要 migration。

禁止：不得让五个字段变成可缺失或 null，不得修改字段类型、名称、单项结构、最大 20 条限制、评价点/证据/时间/安全硬保护或 I3 的 19 项门槛；不得恢复 Service 普通语义裁判，不得改 SQLAlchemy Model、migration、React 业务代码、质量标签或 I2 证据，不得创建 I3 正式 raw/human/final，不得读取 Key、调用真实模型或写 PostgreSQL。若现有 React 不能安全展示空列表，只报告并返回文档层扩展范围，不在本批偷改前端。

固定交付与异常语义：strengths、gaps、risks_or_conflicts、missing_info、hr_follow_up_questions 五个字段仍全部必填且必须为列表，每个列表允许 0—20 项；缺字段、null、错误类型、超过上限或单项结构非法仍由 Schema 拒绝。Prompt 必须说明“有真实重要内容就写，没有就返回 []，不得凑数”，并继续要求明显经历重查和弱优势防遗漏。空列表只表示当前材料和本次评价没有形成该类真实内容，不表示候选人事实层面不存在问题；重要内容遗漏继续由调用前冻结的 `material_findings`、I3 人工审计和 HR 处理。

红灯与最小实现：先建立精确红灯，分别证明当前输入 Schema、持久化 Schema 和 Service 解析会拒绝后三类空列表，并锁定字段缺失/null/错误类型/超过上限仍失败、已有确定性保护继续为绿；再只删除六处 `min_length=1`，更新 Prompt 分区说明与必要示例并把 Prompt 版本递增到 v6，不增加新的 Service 语义判断。

验证与费用：运行报告 Schema/Prompt/Service 精确专项、Adapter/API/持久化兼容测试、阶段 7 扩大回归、后端全量、现有前端合同测试、`py_compile`、静态扫描、正式样本隔离、I2 正式目录差异和 `git diff --check`。所有模型行为使用 Fake/Mock；真实调用、API attempt、token、费用和 PostgreSQL 写入均为 0。

完成标志与失败返回层：五类列表全空的结构化报告可以通过输入与持久化 Schema/Service，缺字段和非法类型仍失败，Prompt v6 不再要求凑满后三类，Service v8/Schema 5.0 其他保护无降级，I2 文件未改。若空列表无法进入 Schema，返回 Schema；若 Prompt 仍强迫凑数或遗漏真实内容，返回 Prompt/I3 质量标签；若 API/持久化不能往返，返回 Schema/序列化边界；若前端无法显示，停止并返回文档层另行授权 React。完成后立即停止，唯一下一步是等待用户确认 CLOSE-06A。

实施结果（2026-08-31）：精确红灯为 `10 failed + 45 passed + 107 deselected`，失败只对应输入/持久化 Schema 与 Service 拒绝空列表、Prompt v6 分区规则/合法示例、配置和当前质量版本；缺字段、null、错误类型和第 21 条继续按预期失败。最小实现只删除 `AIScreeningEvaluationV5Output` 与 `ScreeningEvaluationV5ReportPayload` 共六处 `min_length=1`，Prompt 分区规则改为五类均可诚实为空，并把一个既有虚构时间示例的无内容分区改为 `[]`；固定 10 节、4 个 Few-shot 和最多 20 条上限不变。当前报告 Prompt/Service/Schema 为 v6/v8/5.0，没有新增 Service 语义判断，没有 migration。

实现后精确专项 `55 passed + 107 deselected`，报告完整专项 `162 passed + 16 subtests passed`，Adapter/API/持久化扩大专项 `93 passed + 14 subtests passed`，阶段 7 扩大回归 `390 passed + 3 subtests passed`，前端现有 5.0 合同 `2 passed`，后端全量 `1378 passed + 425 subtests passed + 2 warnings`、0 failures，静态/Prompt 扫描 `55 passed`；`py_compile`、正式样本隔离和 `git diff --check` 通过。I2 正式目录无 Git 差异，没有 I3 正式文件；SQLAlchemy Model、migration、React 业务代码和 PostgreSQL 均未改，Key、真实模型调用、API attempt、token、费用与 PostgreSQL 写入均为 0。本批能证明五个字段的结构与 0—20 项边界、现有链路兼容和 Prompt v6 离线合同成立，不能证明空列表语义一定诚实、真实模型质量改善或 I3 会通过。唯一下一步是等待用户另行确认 CLOSE-06A。

CLOSE-05A—E 与新增 CLOSE-05F 全部完成且自动化为零失败后，才满足 I3 设计入口条件。CLOSE-06A 还必须另行冻结全新未参与 Prompt 调整的 10 份 JD、20 组 JD/Resume、其中 5 组稳定性、逐案 `application_applied_at`、v2 标签、`material_findings[]`、HR 确认计划快照和实际版本，并由用户审核后才能进入 06B 价格门禁；任何真实调用仍需 06C 的独立金额授权。

## 11. 7R5-CLOSE-06A—E：独立 I3 真实质量复验

I3 必须是新 run，不能继续、补跑、覆盖或 finalize I2。CLOSE-05F 完成后由 CLOSE-06A 核对实际实现版本并冻结全新路径、未参与 Prompt 调整的新鲜样本、投递时间、标签与 HR 确认计划快照，预算再由 CLOSE-06B 单独查询和授权。I3 final 继续使用 19 项门槛。

| 批次 | 唯一目标 | 费用与停止点 |
| --- | --- | --- |
| CLOSE-06A | 新路径/生命周期、冻结样本/标签/版本、dry-run/Fake/全量非付费预检 | 0 调用；完成后等价格门禁确认 |
| CLOSE-06B | 查询 DeepSeek 官方实时价格、记录 24 小时快照和请求美元上限 | 不读 Key、不调用；完成后等 real 授权 |
| CLOSE-06C | 唯一一轮 I3 real raw | 只写 raw；失败或成功都停止，不补跑 |
| CLOSE-06D | 用户完成人工审计 | 0 调用；只写 human，Codex 不代审 |
| CLOSE-06E | final 合并全部门槛 | 0 调用；只有明确全部通过才可进入 CLOSE-07 |

五批必须分别确认。任一质量硬门槛失败，返回 CLOSE-04 重新评估总账和产品取舍，不得直接进入 7R5-J。

CLOSE-06A 实施结果（2026-08-31）：新增独立 `7R5-I3` 路径登记、全新 fixture、零调用预检脚本、专项测试和人工复核单。冻结内容为 10 份虚构计划 JD、20 组虚构 JD/Resume、5 个稳定性组、20 个 `application_applied_at == evaluation_reference_at` 时间案例、20 份带确认人/时间/内容指纹的 5.0 计划快照、30 个计划 required 标签和 60 条 `material_findings`；实际版本核对为质量合同 v2、计划 v3/v4/5.0、报告 v6/v8/5.0。I3 preflight 为 write-once，生命周期 `i3_preflight_complete`，raw/human/final 三条冻结路径均不存在。

红灯先表现为新 I3 fixture/预检模块不存在；创建预检文件后的扩大专项又精确暴露“旧 I2 目录扫描器尚未登记 I3 JSON”的 13 个生命周期失败。最小实现只把 I3 preflight 与未来 raw/human/final 路径登记为独立已知路径，陌生 JSON 仍硬拒绝，I2 活动常量、路径、内容和生命周期未改。最终质量专项 `87 passed`，阶段 7 扩大回归 `463 passed + 3 subtests passed`，后端全量 `1384 passed + 425 subtests passed + 2 warnings`；两个 warning 仍为既有 PyPDF2 弃用和异步连接取消提示。`py_compile`、密钥/真实 Adapter 静态扫描、I2 正式文件 Git 差异和 `git diff --check` 通过。真实模型调用、API attempt、输入/输出 token、费用、Key 读取、PostgreSQL 写入和正式结果写入均为 0。

人工复核单明确展示当前方向分布为 `10 high / 0 partial / 10 low`，以及 10 个岗位、20 组映射、时间门槛、重要发现和 5 个稳定性组。该分布尚未被用户接受；用户若认为缺少中间档会降低代表性，必须返回 CLOSE-06A 重新冻结，不能在真实调用后补标签。当前立即停止，唯一下一步是用户审核复核单；接受后也只能另行确认 CLOSE-06B 查询实时价格，不能直接真实调用。

### 11.1 CLOSE-06A-R1：按用户复核修订样本方向分布

2026-08-31，用户明确拒绝 `10 high / 0 partial / 10 low`，确认改为 `8 high / 6 partial / 6 low`，并明确回复“开始修订后的 CLOSE-06A”。本修订仍属于 CLOSE-06A，不进入 CLOSE-06B。

唯一目标与通俗解释：保留原 06A 作为“用户复核后发现覆盖不足”的不可覆盖记录，另建 I3-R1 冻结版本，把真实招聘中最常见、也最容易评分摇摆的部分匹配候选人加入考卷，不能只考明显好和明显差。

固定范围与保护：旧 `7R5-I3` zero-call preflight、旧人工复核单及其中完整 fixture 原样保留，不删除、不覆盖、不改写成通过；新活动身份使用 `7R5-I3-R1` 和全新 R1 preflight/raw/human/final 路径，旧预检登记为 `superseded_by_user_review`，旧预留正式路径永远不得写入。生产 Prompt、Schema、Service、Adapter、API、Model、migration、React、PostgreSQL 和 I2 全部禁止修改。

冻结合同：20 组方向严格为 8 high、6 partial、6 low；partial 必须同时具有真实岗位相关优势和明确 required 缺口，不能只把分数标签改成中间档。5 个稳定性组严格为 2 high、2 partial、1 low。每组继续冻结投递时间、评价参考时间、实际月数、门槛月数、HR 确认计划快照和逐案 `material_findings`；`evaluation_reference_at == application_applied_at`、19 项门槛、稳定性阈值和质量合同 v2 均不变。

红灯、验证和停止点：先让测试精确拒绝旧 `10/0/10`、缺少 R1 独立路径、覆盖旧 preflight、partial 只有标签没有“双面事实”、稳定性不是 `2/2/1` 等情况；再做最小 fixture/生命周期/预检实现。运行 I3/I2 质量专项、阶段 7 扩大回归、后端全量、`py_compile`、密钥/真实 Adapter 静态扫描、I2 和旧 I3 证据差异、正式路径缺失及 `git diff --check`。真实调用、API attempt、token、费用、Key 读取、PostgreSQL 写入和正式结果写入固定为 0。完成后立即停止，由用户审核 R1 复核单；不得自动进入 CLOSE-06B。

实施结果：精确红灯为 `6 failed + 3 passed`，分别锁定旧 `10/0/10`、0 个 partial、旧稳定性 `3 high / 0 partial / 2 low`、旧 run/path、缺少 superseded 证据登记和 payload 未绑定 R1。最小实现把报告重排为 8/6/6；6 个 partial 使用真实核心项目证据，同时按投递时间冻结 24/36 个月 required 缺口；稳定性索引冻结为 R00/R04/R08/R10/R14，即 `2/2/1`。新活动身份为 `7R5-I3-R1`，新 preflight/raw/human/final 均使用 `7r5i3-r1` 路径；旧 preflight 和复核单通过固定身份与字节指纹登记为 `superseded_by_user_review`，原文件未改。

实现后质量专项 `90 passed`，阶段 7 扩大回归 `466 passed + 3 subtests passed`，后端全量 `1387 passed + 425 subtests passed + 2 warnings`；两个 warning 仍为既有 PyPDF2 弃用和异步连接取消提示。`py_compile`、密钥/真实 Adapter 静态扫描、旧 I3 两份证据身份、I2 正式文件 Git 差异、所有 I3 formal 路径缺失和 `git diff --check` 通过。R1 preflight 生命周期为 `i3_preflight_complete`，真实调用、API attempt、token、费用、Key 读取、PostgreSQL 写入和正式结果写入均为 0。本批能证明 R1 题目、标签、时间、快照、版本和本地接线已冻结，不能证明用户已接受逐案业务判断、真实模型质量或 final 会通过。当前停止，唯一下一步是用户审核 R1 复核单；接受后也必须另行确认 CLOSE-06B。

### 11.2 CLOSE-06B：I3-R1 官方价格快照与金额门禁

前置确认与唯一目标：用户已明确接受 I3-R1 冻结样本并单独授权开始 CLOSE-06B。本批只核对活动 preflight 的 `7R5-I3-R1 / i3_preflight_complete` 身份、查询 DeepSeek 官方实时价格、冻结独立 24 小时价格快照，并把 45 次基线业务调用和每次至多一次基础设施重试形成的 90 次最坏 API attempt 换算成美元上界。价格快照和预算估算都不等于真实调用授权。

允许文件与链路位置：只允许修改本剩余计划、`PROJECT_STATE.md`、独立 I3-R1 价格门禁脚本及其测试，并新增 `docs/stages/stage7/2026-08-31-stage7-7r5i3-r1-pricing-snapshot.json`。这些内容位于生产“前端 → API → Schema → Service → Model → PostgreSQL”链路之外，只负责离线验收与费用保护；允许只读导入冻结 fixture、Prompt 构建器和质量合同来计算输入上界，但不得实例化真实 Adapter 或读取运行配置。

固定计价合同：价格来源只能是 DeepSeek 官方价格页；快照固定来源 URL、查询时间、失效时间、模型及供应商展示版本、当前 peak/off-peak 时段、两档单价和官方时段规则。输入 token 上界按 45 份冻结请求序列化后的 UTF-8 字节数保守替代，输出上界继续固定为基线 500,000、含一次基础设施重试 1,000,000；缓存全部按未命中计算。当前费用同时显示当前时段估计和 peak 估计，向用户请求的金额不得低于 peak + 90 attempts 的最坏上界。快照最多 24 小时有效；即使未过 24 小时，06C 执行时若官方价格、模型或时段与快照不一致，也必须返回 06B 重新查询。

红灯、验证与禁止范围：先用精确红灯锁定活动 R1 preflight 身份、45/90 次分母、500,000/1,000,000 输出上限、两档官方单价、当前时段判断、24 小时过期、独占写入、保守费用公式，以及 `real_run_allowed=false`、金额尚未授权和所有外部计数为 0；再做最小价格门禁实现和独立快照。运行 06B 专项、I3/I2 质量专项、阶段 7 扩大回归、后端全量、`py_compile`、密钥/真实 Adapter 静态扫描、I2/旧 I3/R1 preflight 差异、I3 formal 路径缺失和 `git diff --check`。禁止修改生产 Prompt、Schema、Service、Adapter、API、Model、migration、React、冻结 fixture/preflight、I2 或 PostgreSQL；禁止读取 Key、调用模型或创建 I3-R1 raw/human/final。

完成标志、失败返回层与停止点：官方快照可复核、24 小时有效，预算同时覆盖 45 次正常运行和 90 次最坏 attempt，且 Key/Adapter/模型调用/API attempt/token/费用/PostgreSQL/正式结果写入新增均为 0。若 R1 身份或 preflight 不合法，返回 CLOSE-06A-R1；若官方页面、价格、时段或费用公式不确定，留在 CLOSE-06B；若快照过期或执行前价格/时段变化，也返回 CLOSE-06B。完成后立即停止，只向用户展示费用并请求一个明确美元硬上限；不得自动开始 CLOSE-06C。

实施结果（2026-08-31）：DeepSeek 官方价格页在 `2026-08-31T12:27:50.142464+08:00` 显示 `deepseek-v4-flash / DeepSeek-V4-Flash-0731` 的 off-peak 单价为每百万 token `$0.007` 缓存命中输入、`$0.22` 缓存未命中输入、`$0.66` 输出，peak 单价为 `$0.014 / $0.44 / $1.32`；查询时为工作日 UTC 04:27，选择 off-peak。独立 write-once 快照为 `2026-08-31-stage7-7r5i3-r1-pricing-snapshot.json`，有效到 `2026-09-01T12:27:50.142464+08:00`；金额仍为空，`real_run_allowed=false`。

冻结的 45 份请求序列化 UTF-8 字节上界为 759,426，90 attempts 上界为 1,518,852；输出上界分别为 500,000 和 1,000,000。全部输入按缓存未命中保守计算后，off-peak 的 45/90 次费用上界为 `$0.49707372 / $0.99414744`，peak 的 45/90 次上界为 `$0.99414744 / $1.98829488`；金额门禁最低为向上取整到美分的 `$1.99`，建议用户确认整数硬上限 `$2`。

精确红灯为新价格门禁模块缺失导致 1 个 collection error；最小实现后 06B 专项 `5 passed`，I3/I2 质量专项 `95 passed`，阶段 7 相关扩大回归 `805 passed + 92 subtests passed`，后端全量 `1392 passed + 425 subtests passed + 2 warnings`、0 failures。`py_compile`、密钥/真实 Adapter 静态扫描、I3 formal 路径缺失、价格快照二次只读校验和 `git diff --check` 通过；两个 warning 仍为既有 PyPDF2 弃用和异步连接取消提示。生产链、冻结 fixture/preflight、I2、PostgreSQL 均未修改；Key 读取、真实 Adapter、模型调用、API attempt、token、费用和正式结果写入新增均为 0。CLOSE-06B 完成不代表金额或真实调用已经授权；当前立即停止，只等待用户明确确认美元硬上限并单独开始 CLOSE-06C。若确认时快照已过期、官方价格/模型变化或执行时段不再是 off-peak，必须返回 CLOSE-06B 重新查询。

### 11.3 CLOSE-06C：I3-R1 唯一真实 raw

前置授权与唯一目标：用户已明确回复“确认 USD 2 硬上限，开始 CLOSE-06C”。本批只执行 `7R5-I3-R1` 唯一一轮真实质量调用，固定 10 次计划、20 次报告和 15 次稳定性，共 45 次业务调用；每次只允许一次基础设施重试，最多 90 次 API attempt，内容错误不重试。无论完整跑完、部分失败还是费用/运行门禁停止，都必须形成一次不可覆盖 raw 后立即停止，不进入人工审计或 final。

允许文件与链路位置：允许新增独立 I3-R1 真实运行器和专项测试，给质量合同补充 I3 自己的 preflight → raw → human → final 生命周期与 write-once 保护，新增只读绑定本轮用户授权、价格快照和 USD 2 上限的授权记录，并在运行结束后只写登记好的 I3-R1 raw；允许更新本计划和 `PROJECT_STATE.md`。它调用生产 Prompt → Schema → Service → Model，但不经过前端/API，不写业务 Model/PostgreSQL。禁止修改生产 Prompt、Schema、Service、Adapter、API、Model、migration、React、冻结 fixture/preflight、价格快照、I2 或旧 I3 证据。

固定执行合同：计划调用使用 10 份 R1 计划 JD；20 份报告和 15 次稳定性必须使用调用前冻结且 HR 已确认的 `confirmed_plan_snapshot`，不得改用本轮计划生成结果。逐案 `evaluation_reference_at` 必须等于冻结的 `application_applied_at`，经历月份事实按该时间构建。模型、Prompt/Service/Schema 版本、temperature、thinking、JSON 格式和最大输出必须与 R1 preflight 一致。费用守卫必须在每个 attempt 前按保守上界检查 USD 2；真实响应必须保存模型、finish reason、token、费用估算、耗时、稳定错误和原始响应，不保存 Key、请求头、堆栈或思维链。

红灯、非付费预检与真实写入：先建立精确红灯，证明旧 I2 运行入口不能承担 I3 生命周期/路径/fixture/确认计划快照，锁定 USD 2、价格快照身份与当前时段、45/90 分母、内容错误不重试、部分失败也只写一次 raw，以及所有正式写入前置检查必须早于读取 Key。最小实现后先跑 06C 专项、I3/I2 质量专项、阶段 7 扩大回归、后端全量、`py_compile`、静态扫描、I2/旧 I3/R1 preflight/价格快照保护、I3 raw 缺失和 `git diff --check`；全部通过且官方价格/模型/时段仍一致后，才允许读取运行配置、实例化真实 Adapter 并执行唯一 real。

完成标志、失败返回层与停止点：raw 必须为 `7R5-I3-R1 / real_raw`，绑定 R1 preflight/fixture/价格/授权，完整记录实际分母、attempt、token、费用和自动结构结果，`quality_gate_passed=null`、`quality_conclusion_allowed=false`，human/final 仍不存在，PostgreSQL 写入为 0。若 preflight/fixture/确认计划快照不合法，返回 CLOSE-06A-R1；若价格、时段或金额门禁不合法，返回 CLOSE-06B；若运行入口或生命周期保护失败，留在 CLOSE-06C 且不得调用；真实运行一旦开始，任何结果都只封存 raw 并停止，不补跑。完成后唯一下一步是等待用户另行确认 CLOSE-06D 并由用户人工审计，Codex 不代审。

实施结果（2026-08-31）：用户授权记录、独立 I3-R1 运行器、I3 生命周期/write-once 合同和专项测试已建立。初始精确红灯为新运行器模块缺失；最小实现后的 45 次完整 Fake 预检又准确发现 `evaluation_reference_at` 错传字符串而非带时区 datetime 的 1 个接线失败，修复后 10/20/15 全部通过生产 Service 路径。付费前 I3/I2 联合专项 `100 passed`、阶段 7 扩大回归 `811 passed + 92 subtests passed`、后端全量 `1398 passed + 425 subtests passed + 2 warnings`；官方模型、两档价格和当前 off-peak 时段二次核对不变，I3 formal 路径仍空，才读取 Key 并开始唯一 real。

唯一真实运行完整结束并封存 raw：45/45 次业务调用、45 次 API attempt、0 重试、45 成功、0 attempt 失败；输入 182,757 tokens、输出 43,192 tokens，估算费用 `$0.06405111599999999`，未触发 USD 2 上限。计划结构合法且可追溯 `10/10`；报告合法 `20/20`、69/69 个非零评价有 evidence、五分区字段合法 `20/20`、自动方向一致 `17/20`；稳定性合法输出 `15/15`，方向稳定组 `3/5`、分差不超过 10 的组 `3/5`、极端方向翻转 0。后两项低于 final 的 `4/5` 门槛，是必须保留给 06D/06E 的已知风险，不能在 06C 直接改写为 final 结论。

raw 大小 628,370 bytes，生命周期为 `i3_raw_complete`，`quality_gate_passed=null`、`quality_conclusion_allowed=false`；Key 未写入 raw，human/final 不存在，PostgreSQL 写入为 0，I2 正式文件无差异。封存后旧测试如预期出现 10 个“仍要求 raw 不存在”的生命周期失败；只更新测试认识 `i3_raw_complete` 并增加 raw 身份、10/20/15 分母、45/90 调用、金额和停止点校验后，联合专项 `102 passed`、阶段 7 扩大回归 `812 passed + 92 subtests passed`、后端全量 `1399 passed + 425 subtests passed + 2 warnings`。没有补跑或覆盖 raw。CLOSE-06C 至此完成并立即停止；唯一下一步是等待用户另行确认 CLOSE-06D，由用户完成人工审计，Codex 不代审，也不得自动创建 human/final。

### 11.4 CLOSE-04R2：工作年限退出 AI 初筛（已完成文档批次）

用户确认后的大白话规则是：AI 初筛只评价“做过什么、会什么、证据在哪里”，不再算或判断“工作了几年”。纯年限要求不进入评价计划和分数；“3 年以上 Java 经验”这类混合要求只保留 Java 能力主题，忽略 3 年门槛。具体工作年限由 HR 在 AI 初筛之外核对。计划、逐项评分、总分和五个报告分区均不得用年限加分、扣分或下结论。

I3-R1 raw 继续按执行时的 v2 合同只读保留，生命周期仍为 `i3_raw_complete`，不补跑、不覆盖、不回算、不创建 human/final。用户接受其中稳定方向 `3/5`、分差 `3/5` 为已知风险；后续方向和分差继续记录但不再阻塞 final，合法输出 `15/15`、极端翻转 0、敏感评分 0 和非年限严重事实错误 0 仍是硬门槛。

CLOSE-04R2 确认的目标是质量合同 v3、计划 v4/v5/5.0、报告 v7/v9/5.0；后续 CLOSE-05G—05I 已按下方记录依次实现。v3 保持 19 项硬门槛：把原来的稳定方向 `4/5` 和分差 `4/5` 两项替换成“计划纯年限评价点为 0”和“报告年限评分/结论为 0”；两项稳定性数据转为诊断，不删除。旧时间字段和数据库列先保留兼容，但新报告不得消费时间事实，`experience_period_fact_keys=[]`、`calculation_note=null`。

本批只修改 5.0 主设计、本计划和 `PROJECT_STATE.md`，没有进入“前端 → API → Schema → Service → Model → PostgreSQL”生产链，也没有修改测试、质量运行器或证据。模型调用、API attempt、token、费用、Key 读取、PostgreSQL 写入和正式结果写入均为 0。它只能证明产品决定和顺序已经写清，不能证明代码或真实质量已经改变。

### 11.5 修订后的唯一实施顺序

以下批次必须逐批确认，任何一批结束都立即停止：

#### CLOSE-05G：离线质量合同 v3

唯一目标：先改“考卷和判分规则”，不碰生产业务。允许修改离线质量合同、全新 I4 fixture/标签、质量运行器的 I4 分支、专项测试和状态文档；链路位置在生产全链之外。必须先建立红灯，证明旧合同仍把年限和稳定方向/分差当硬门槛，再最小实现 v3：旧 I2/v1 与 I3-R1/v2 永不回算；纯年限不进 required 分母，混合要求保留能力标签；时间计算标签全部退出；稳定方向/分差只诊断；19 项中新增计划和报告两个“年限为零”硬门槛。禁止修改生产 Prompt/Service/Schema/API/Model/migration/React、旧 fixture、I2/I3-R1 证据和 PostgreSQL。完成后跑质量专项、阶段 7 扩大回归、后端全量、`py_compile`、静态扫描和 `git diff --check`，全部外部调用/写入为 0；失败返回质量合同层，成功后停止等待 CLOSE-05H。

实施结果（2026-08-31）：CLOSE-05G 已完成并停止。精确红灯为 `13 failed + 1 passed`：失败只对应 v3/run 路由、I4 fixture、I4 分母/标签校验、I4 19 项判分和零调用审计尚不存在；既有“中文粗略重合只生成复核候选”保护保持通过。最小实现新增 `stage7_v5_quality_contract_v3` 和 `7R5-I4` 离线身份映射，I2 仍固定 v1、I3-R1 仍固定 v2且禁止历史回算；新增 10 份计划、20 组报告、5 组各 3 次稳定性的虚构 I4 离线 fixture。每份计划标签排除一条纯年限 required，并从一条混合要求保留非年限能力，P00 明确保留 Java；报告标签没有 `time_case/evaluation_reference_at/actual_months/threshold_months` 或年限达标结论。

v3 判分继续保持 19 项硬门槛，原稳定方向和分差两项只写入 `blocking=false` 的诊断，原位置替换为 `plan_work_duration_criterion_zero` 和 `report_work_duration_scoring_or_judgment_zero`。稳定性合法输出 15/15 与极端翻转 0 共同保留在原极端翻转硬保护，敏感评分和非年限严重事实错误仍为零容忍；结构、引用、非零分证据、捏造和自动招聘决定等原门槛未降低。实现后 I4 专项 `14 passed`，I2/I3/I4 联合质量专项 `74 passed`，阶段 7 扩大回归 `299 passed + 3 subtests passed`，后端全量 `1413 passed + 425 subtests passed + 2 warnings`、0 failures；两条 warning 仍为既有 PyPDF2 弃用和 asyncpg 测试清理提示。`py_compile`、静态版本/外部入口扫描和 `git diff --check` 通过。

测试进程显式关闭 `.env` 文件加载、把模型 Key 固定为空并使用 mock provider；模型调用、API attempt、token、费用、Key 读取和 PostgreSQL 写入均为 0。I2/I3-R1 后置生命周期分别仍为 `i2_final_complete` / `i3_raw_complete`，九份正式/冻结证据的大小与 UTC 修改时间和实施前一致，后置 SHA-256 已记录，证据目录无 Git 差异；I3-R1 human/final 不存在，I4 正式 preflight/raw/human/final 文件数为 0。本批只能证明离线 v3 考卷、标签、分母和判分规则可用且旧历史未改，不能证明生产计划或报告已经退出年限，也不能证明 I4 真实模型质量。失败应返回质量合同/I4 标签层；当前唯一下一步是等待用户另行确认 CLOSE-05H，不得自动实施。

#### CLOSE-05H：计划链退出工作年限

唯一目标：让新计划只留下可由 AI 评价的能力，不生成纯年限评价点。允许修改计划 Prompt、计划 Service 的确定性边界、相关 Schema 合同测试和状态文档；链路位置为 Schema → Service → Model 输入/输出边界，不改 API、业务 Model、migration、React 或 PostgreSQL。Prompt 升级 v4；Service 升级 v5，但只允许校验明确结构和输出字段，不恢复普通语义裁判。纯年限样本必须没有评价点，混合样本必须保留 Java 等能力主题且去掉年限评分条件，HR 编辑/确认权不变。先建红灯，再跑计划专项、阶段 7 扩大回归、后端全量和静态检查；真实调用和写入为 0。失败返回 Prompt/计划合同层，成功后停止等待 CLOSE-05I。

实施结果（2026-08-31）：CLOSE-05H 已完成并停止。计划 Prompt 升级为 `job_evaluation_plan_lightweight_v4`，新增独立虚构边界示例并明确：纯工作年限不生成评价点；混合要求忽略年数/月数但保留 Go、Java 等能力主题；`name/description/screening_focus` 不得使用年限，逐字可定位的 `source_quote` 可以保留原文年限；具体年限由 HR 在 AI 初筛之外判断。正式 I4 计划要求没有复制进生产 Prompt。

计划 Service 升级为 `lightweight_plan_generation_v5`。新增的确定性边界只检查评价点面向候选人的三个字段，拦截明确中文/英文工作年限、年限达标或持续月份表达；它不扫描 `source_quote`，不静默删除或改写模型内容，不恢复普通语义启发式硬裁判，非工作时长（例如三个月项目交付周期）仍合法。模型内容错误一次调用后直接失败且不重试；HR 编辑、新增、删除、合并和确认权不变，但不能把年限重新放回 AI 评价点。Schema、API、业务 Model、migration、React 和 PostgreSQL 均未修改，Schema 继续为 5.0。

精确红灯为 `13 failed + 61 passed + 16 subtests passed`，失败只对应 Prompt/Service/配置仍是旧版本、缺少年限规则/示例及确定性拦截。最小实现后计划专项 `73 passed + 16 subtests passed`，I2/I3/I4 质量专项 `95 passed`，阶段 7 扩大回归 `502 passed + 3 subtests passed`，后端全量 `1424 passed + 425 subtests passed + 2 warnings`，0 failures；两条 warning 仍为既有 PyPDF2 弃用和 asyncpg 测试清理提示。扩大回归一度发现旧 I3 授权顺序测试会用当前 Prompt 重算冻结价格预算；只修正该测试的历史价格隔离后恢复通过，没有修改旧运行器、价格快照或正式证据。`py_compile`、实际版本核对、外部入口静态扫描和 `git diff --check` 通过。

测试从无 `.env` 的 `backend` 目录启动，全部模型行为使用 Fake/Mock；真实模型调用、API attempt、token、费用、Key 读取和 PostgreSQL 写入均为 0。I2/I3-R1 后置生命周期仍为 `i2_final_complete` / `i3_raw_complete`，正式证据路径无 Git 差异；I3-R1 human/final 不存在，I4 正式 preflight/raw/human/final 文件数为 0。本批能证明生产计划的离线 Prompt/确定性 Service 边界和现有回归已退出工作年限，不能证明真实模型每次遵守、报告链已经退出年限或 I4 真实质量通过。失败应返回计划 Prompt/Service 输出边界；当前唯一下一步是等待用户单独确认 CLOSE-05I，不得自动实施。

#### CLOSE-05I：报告链退出工作年限

唯一目标：报告不再收到或使用工作年限事实。允许修改报告 Prompt、报告 Service 的结构校验、调用输入组装、相关 Schema 合同测试和状态文档；链路位置为 Schema → Service → Model 输入/输出边界，不改变 Schema 5.0 的持久化形状，不改 API、业务 Model、migration、React 或 PostgreSQL。Prompt 升级 v7，Service 升级 v9；新调用不向模型提供时间事实，输出必须为 `experience_period_fact_keys=[]`、`calculation_note=null`。Service 只校验这两个结构结果，不用关键词判断整段自然语言；年限是否偷偷影响评分由 Prompt、v3 冻结标签和人工审计兜底。先建红灯，再跑报告专项、阶段 7 扩大回归、后端全量和静态检查；真实调用和写入为 0。失败返回报告 Prompt/输入合同层，成功后停止等待 CLOSE-06R2-A。

实施结果（2026-08-31）：CLOSE-05I 已完成并停止。报告 Prompt 升级为 `screening_evaluation_lightweight_v7`，明确 AI 不计算、不比较、不判断工作年限，不因年限加分或扣分；总体分、逐项评分、优势、差距、风险、缺失信息、跟进问题和总结均不得使用年限。混合要求仍评价 Java 等非年限能力。模型输入只保留完整 JD、确认计划和脱敏 Resume，不再包含投递时间、时区或经历时间事实。

报告 Service 升级为 `lightweight_report_generation_v9`：旧时间输入参数只保留调用兼容，不再解析并以空值进入共享 Adapter；Prompt builder 不输出时间边界；解析结果要求每项 `experience_period_fact_keys=[]`、`calculation_note=null`。Service 不扫描自然语言中的年/月关键词，隐藏语义使用留给 v3 质量标签和未来人工审计。Schema 和持久化形状保持 5.0，运行/报告时间列继续用于旧数据兼容和审计；API、业务 Model、migration、React 和 PostgreSQL 均未修改。

精确红灯为 `11 failed + 11 passed + 16 subtests passed`。实现后新增合同 `22 passed + 16 subtests passed`、既有报告专项 `138 passed`、I2/I3/I4 质量专项 `95 passed`、阶段 7 扩大回归 `499 passed + 3 subtests passed`。后端全量首轮的 2 个失败均为编排层旧测试仍要求时间进入模型或允许非空时间输出，按新合同修正后全量 `1421 passed + 425 subtests passed + 2 warnings`、0 failures；两条 warning 仍为既有 PyPDF2 弃用和 asyncpg 测试清理提示。`py_compile`、版本/模型输入/外部入口静态扫描通过。

测试使用 Fake/Mock 和 `_env_file=None`，没有读取 `.env` 或 Key；真实模型调用、API attempt、token、费用和 PostgreSQL 写入均为 0。I2/I3-R1 生命周期仍为 `i2_final_complete` / `i3_raw_complete`，证据目录无 Git 差异；I3-R1 human/final 不存在，I4 正式文件数为 0。本批能证明离线报告链输入和结构输出合同已退出工作年限，不能证明真实模型一定不会偷偷在自然语言中使用年限，也不能证明 I4 真实质量或阶段 7 完成。失败应返回报告 Prompt/模型输入/结构输出边界。当前立即停止，唯一下一步是等待用户单独确认 CLOSE-06R2-A，不得自动创建 I4 正式证据或调用模型。

#### CLOSE-06R2-A—E：独立 I4 真实质量复验

I4 使用全新身份、路径、样本和 v3 标签，不能续跑或 finalize I3-R1。A 只冻结并零调用预检；B 只查官方价格并请求美元上限；C 获得单独金额授权后只执行唯一 raw；D 只保存用户人工审计；E 只合并 final。五批分别确认。I4 必须验证纯年限退出、混合能力保留、报告年限评分/结论为零、结构/证据/敏感/捏造/自动决定/极端翻转硬门槛，以及方向/分差诊断值。任一硬门槛失败返回 CLOSE-04R2/对应生产层，不能进入 CLOSE-07；全部通过后仍须停止并等待用户确认 CLOSE-07。

实施结果（2026-08-31，CLOSE-06R2-A）：全新 `7R5-I4` 已登记独立 preflight/raw/human/final 路径和 `i4_not_started` 至 `i4_final_complete` 生命周期；本批只写入 `2026-08-31-stage7-7r5i4-zero-call-preflight.json` 与 `2026-08-31-stage7-7r5i4-fixture-review.md`，生命周期为 `i4_preflight_complete`，raw/human/final 均不存在。preflight 冻结 v3 合同、当前计划 v4/v5/5.0、报告 v7/v9/5.0、I4 fixture 指纹、10/20/5×3 分母、8/6/6 报告方向和 2/2/1 稳定性抽样；明确简历任职日期可以保留为原始经历定位信息，但不得计算、判断或评分工作年限。纯年限要求排除数为 10，混合要求非年限能力保留数为 10。

精确红灯为 `6 failed`，分别证明 I4 路径、生命周期、专用 preflight、正式材料和 write-once 保护原本不存在。最小实现后 I4/CLOSE-05G 专项 `20 passed`，I2/I3/I4 联合质量专项 `122 passed`，阶段 7/v5 扩大回归 `540 passed + 3 subtests passed`，后端全量 `1427 passed + 425 subtests passed + 2 warnings`、0 failures；两条 warning 仍为既有 PyPDF2 弃用和 asyncpg 测试清理提示。`py_compile`、外部入口静态扫描和 `git diff --check` 通过。I2/I3-R1 生命周期仍为 `i2_final_complete` / `i3_raw_complete`，实施前后六份关键历史文件 SHA-256 一致；I3-R1 human/final 不存在。模型调用、API attempt、token、费用、价格查询、Key 读取和 PostgreSQL 写入均为 0。本批只能证明 I4 考卷身份、离线标签、执行版本和零调用前置条件已冻结，不能证明价格、金额授权、真实模型质量或 final 通过。当前立即停止，唯一下一步是用户审核 I4 复核单后另行确认 `CLOSE-06R2-B`；不得自动查价或进入 C—E。

实施结果（2026-08-31，CLOSE-06R2-B）：本批只从 DeepSeek 官方价格页查询并新建 I4 独立、只写一次快照 `2026-08-31-stage7-7r5i4-pricing-snapshot.json`，没有沿用或重算 I3-R1 价格。官方仍支持计划模型 `deepseek-v4-flash`，页面显示版本 `DeepSeek-V4-Flash-0731`。查询时间为 `2026-08-31T19:50:18.531201+08:00`，对应 off-peak；off-peak cache hit / cache miss / output 为 USD 0.007 / 0.22 / 0.66 每百万 token，peak 为 USD 0.014 / 0.44 / 1.32。快照绑定质量合同 v3、I4 preflight SHA-256 `C4FC353B...E513`、fixture review SHA-256 `F8669734...7147` 和当前生产计划 v4/v5/5.0、报告 v7/v9/5.0。

调用预算固定为计划 10、报告 20、稳定性 15，共 45 次基础业务调用；每次最多 1 次基础设施重试，内容错误 0 重试，最大 90 API attempts。计划/报告每 attempt 最大输出分别为 8,000/12,000；以序列化 Prompt UTF-8 字节数作为输入 token 上界并把全部输入按 cache miss 计价后，基础/极端总 token 上限为 1,174,745 / 2,349,490。off-peak 基础/极端费用为 USD 0.47844390 / 0.95688780；为覆盖实际执行落入 peak 的风险，授权下限按 peak 极端 USD 1.91377560 向上取整为 USD 1.92，建议硬上限 USD 2.00。快照 SHA-256 为 `C417C02E...86FD`，24 小时有效，`real_run_allowed=false`。

精确红灯为 `1 error`，唯一原因是 I4 专用价格门禁模块尚不存在；实现后 I4 价格专项 `8 passed + 1 warning`。I2/I3/I4 联合专项 `117 passed + 1 failed + 1 warning`，阶段 7 扩大回归 `310 passed + 3 subtests passed + 2 failed + 1 warning`，后端全量 `1433 passed + 425 subtests passed + 2 failed + 2 warnings`。失败均是旧 I3 preflight 在 Windows `core.autocrlf=true` 下由 LF 展开为 CRLF 造成的既有字节哈希/绑定差异；归一化 LF 后哈希恢复冻结值，且 Git 无旧文件差异，因此本批没有越权重写旧证据或旧 I3 测试。新脚本/测试 `py_compile`、外部入口/密钥加载静态扫描和 `git diff --check` 通过。I2 三份、I3-R1 preflight/raw、I4 preflight/review 的实施前后大小与 SHA-256 一致；I3-R1 human/final 与 I4 raw/human/final 不存在。Key 读取、真实 Adapter、模型调用、API attempt、实际 token/费用、PostgreSQL 写入和 I4 raw/human/final 写入均为 0。本批能证明当前官方价格、保守预算和金额授权门禁已冻结，不能证明未来价格不变、真实模型质量、真实费用或 I4 final 通过。

#### CLOSE-06R2-C：I4 唯一真实 raw（已完成）

用户已明确授权 `7R5-I4` 使用 USD 2.00 不可突破硬上限并要求开始 C。本批唯一目标是按 I4 独立身份执行计划 10、报告 20、稳定性 15 共 45 次业务调用，最多 90 API attempts，并只写一次 raw；无论完整、部分失败或费用/运行门禁停止，只要已有真实 attempt 就封存 raw 后停止，不补跑、不创建 human/final、不进入 D。

允许文件为新的 I4 real runner、I4 real 专项测试、必要的 I4 生命周期/write-once 合同分支、独立 write-once authorization、唯一 I4 raw 和三份权威状态文档。链路只到 Prompt → Schema → Service → Model，不经过前端/API/业务 Model/PostgreSQL。生产 Prompt/Service/Schema/Adapter/API/Model/migration/React、I4 fixture/preflight/review/价格快照、I2、旧 I3/I3-R1 证据均禁止修改。

固定顺序为：C-1 冻结证据并建立身份/金额/价格/45-90/重试/write-once/Key 顺序红灯；C-2 做最小 runner 和 45 次零调用 Fake 生产 Service 接线；C-3 跑 I4-C 专项、联合专项、扩大回归、后端全量及静态/哈希/差异检查后，才写入绑定用户原文、USD 2.00、I4、模型、off-peak 和快照 SHA 的 authorization；C-4 再查官方模型/两档价格/时段不变后才读取配置并检查 Key 非空，然后实例化真实 Adapter，按计划 → 报告 → 稳定性执行，每次最多 1 次基础设施重试，内容错误 0 重试，每 attempt 前检查费用；C-5 封存 raw、验证不可覆盖和 `i4_raw_complete`，复跑回归、更新状态并停止等待 D。

I4-C 新增专项必须零失败，扩大和全量不得出现本批新增失败。当前 Windows `core.autocrlf=true` 造成的两个旧 I3 preflight CRLF 哈希/绑定失败只允许保持已登记基线；归一化 LF 必须仍等于冻结哈希，Git 必须无旧证据差异，禁止为绿灯改写旧文件或旧 I3 测试。报告和稳定性必须使用调用前冻结的 `confirmed_plan_snapshot`，模型输入不含投递时间、时区或经历时间事实；raw 不保存 Key、请求头、堆栈或思维链，`quality_gate_passed=null`、`quality_conclusion_allowed=false`、PostgreSQL 写入 0。第一个 attempt 前失败不创建 raw并返回对应前置层；第一个 attempt 后任何失败均封存部分 raw且不得补跑。详细合同见主设计 32Z.10。

实施结果（2026-08-31）：用户确认后 I4 付费前专项 34 passed，官方模型、价格和 off-peak 档位不变，随后读取配置并执行唯一 real。45 个业务 case 共形成 48 次 API attempts、3 次基础设施重试；43 次 attempt 成功、5 次失败，均为 `SCREENING_EVALUATION_SERVICE_UNAVAILABLE`。计划合法且可追溯 10/10；报告合法 19/20、39/39 个非零评价有 evidence；稳定性合法 13/15，方向稳定 4/5、分差不超过 10 为 4/5、极端翻转 0。成功 attempt 使用 154,218 input tokens、31,710 output tokens；含失败预留的保守费用 USD 0.106405444，未触发 USD 2.00 上限。

raw 为 474,029 bytes、SHA-256 `E4D1E01182EECD29423CCC7E89B20A45968EF52730FF27FC09F77580D19C6C33`，生命周期 `i4_raw_complete`，`quality_gate_passed=null`、`quality_conclusion_allowed=false`；human/final 不存在，PostgreSQL 写入 0。封存专项 `35 passed + 1 warning`，`py_compile` 与 `git diff --check` 通过。用户最新明确要求跳过前面的测试直接调用，因此本批没有再执行扩大回归和后端全量；该缺口如实保留，不能表述为全量回归通过。C 至此停止，不补跑；唯一下一步是等待用户另行确认 D。

#### CLOSE-06R2-D/E 取消与 CLOSE-07 前置修订

用户已明确接受 I4 当前真实结果并取消人工审计与 final。I4 保持 `i4_raw_complete`，human/final 永久不存在，raw 的空质量结论字段不改；19/20 报告、13/15 稳定性合法输出和 R06 结构失败必须进入最终验收说明。CLOSE-07 的前置条件改为“当前 I4 raw 已封存且用户明确接受”，不再要求 I4 final。

## 12. 7R5-CLOSE-07：7R5-J 真实全链收尾

依赖：I4 raw 已封存且用户明确接受，D/E 已取消，用户另行确认开始 CLOSE-07。I3-R1 raw 不能满足本依赖。

唯一目标：用真实 PostgreSQL、真实 `/api/v2` 和真实浏览器证明 5.0 可操作、可恢复、可审计。

允许范围与链路：覆盖“前端 → API → Schema → Service → Model → PostgreSQL”全链；Model 层只引用 I4 真实 raw，不新增调用。允许新增独立 CLOSE-07 runner/专项/结果/浏览器证据和更新权威状态；只允许修复验收发现且不改变已确认合同的最小缺陷。若核心合同、数据或完成标准需要变化，返回专项设计并重新确认。

固定顺序：J-1 冻结 Git/版本/证据/数据库基线；J-2 执行 CLOSE-07 专项、阶段 7 扩大回归、后端全量、前端全量、TypeScript 和生产构建，新增缺陷先建精确红灯再最小修复；J-3 用真实 PostgreSQL 和真实 `/api/v2` 配合 Fake Adapter 验证 5.0 计划/筛选/HR 决策/历史/并发/失败及 migration 往返，隔离夹具且前后计数一致；J-4 用真实 Chromium 验证桌面/平板/手机、键盘/焦点/危险确认、控制台/网络/敏感信息，使用全新证据目录；J-5 复跑并封存不可覆盖 CLOSE-07 结果。详细范围见主设计第 33 节。

完成标志：第 21 节全部项目通过，自动化与 I4 raw 身份仍有效，数据库无夹具残留，Key/模型/API attempt/token/费用新增为 0。完成后停止；唯一下一步是等待确认 CLOSE-08。

### 12.1 CLOSE-07 执行状态（2026-08-31，未完成）

用户已明确授权一次执行 J-1—J-5。J-1 冻结了分支 `2lcj`、HEAD `a612b704500d6e702d4ad691e579b011b3fb22d1`、I2/I3-R1/I4 证据身份、I4 human/final 缺失、Alembic head 和九张业务表基线。J-2 新增独立 CLOSE-07 验收器并按先红后绿完成：初始 1 个收集错误来自 runner 尚不存在，最小实现后 `5 passed`；前端全量 `24/24` 和生产构建通过，后端扩大回归为 `530 passed + 2 个既有 Windows CRLF 基线失败`，当时后端全量为 `1445 passed + 2 个同源既有失败 + 425 subtests passed`。

J-3 新增一条真实 HTTP `/api/v2` → Schema → Service → Model 映射 → PostgreSQL 的 5.0 生命周期测试；模型位置只使用 Fake Adapter。测试自身先因调用不存在的计划异常处理器形成 1 个装配红灯，修正测试后 `1 passed`；计划、筛选、Application/HR 决策和三份 5.0 migration 合跑 `80 passed + 19 subtests passed`。专用空库 `stage7_close07_acceptance` 完成全量 `upgrade head → downgrade c5d7e9f1a323 → upgrade d6e8f0a2b434 → current/head/check`，九张业务表均为 0 后删除；开发库事务用例自身的紧邻前后计数一致，没有 CLOSE-07 虚构夹具残留。

J-4 未通过。生产构建和本地确定性 fixture server 均正常，但 Codex 应用内浏览器运行时在任何页面脚本执行前持续报 `failed to write kernel assets: 系统找不到指定的路径。 (os error 3)`；重置连接、核对插件文件和临时恢复旧工作目录指向均未解决。未打开页面、未产生浏览器 HTTP 请求或截图，也没有使用旧截图、独立 Playwright 或其他工具冒充本批真实 Chromium 证据。阻塞记录写入 `close07-browser-acceptance-evidence/2026-08-31-stage7-close07-browser-blocked.json`，临时服务器和目录联接均已清理。

J-5 的可执行检查已完成：受影响专项 `6 passed`，前端再次 `24/24`、生产构建 3121 modules，后端全量 `1446 passed + 2 个同源既有 CRLF 失败 + 425 subtests passed`；`py_compile`、外部入口/Key 静态扫描和 `git diff --check` 通过。I2/I3-R1/I4 冻结证据 SHA-256 与 J-1 一致，I4 human/final 仍不存在。测试显式使用空 Key/Fake，CLOSE-07 自身新增模型调用、API attempt、token 和费用均为 0；但执行期间另一个应用/用户会话向开发库写入真实候选人、简历、计划、Application、Run 和 StageHistory，故不能声称整个验收时间窗数据库总计数不变，也不能把外部会话可能发生的模型调用计为 CLOSE-07 的调用。

因此未创建 `2026-08-31-stage7-close07-full-chain-acceptance-results.json`，CLOSE-07 保持未完成，CLOSE-08 不得开始。恢复应用内浏览器后只补做 J-4，并选择没有外部数据库写入的窗口复核最终计数，再完成 J-5 只写一次封存；若页面交互失败返回 React/样式/API 映射层，若数据库再次出现无法归因的并发变化先停止外部写入并重建 J-1 数据库基线。

### 12.2 最新验收结论：AI 初筛整改重新打开（2026-08-31）

用户确认已经完成人工界面验收，但同时明确表示“目前阶段 7 还无法验收通过，AI 初筛还是有问题，我们需要去改进”。人工界面验收作为用户体验事实保留，不冒充 12.1 缺失的 Codex Chromium 机器证据；浏览器运行时问题不再是当前首要阻塞。

此前接受 I4 raw 和取消 D/E 的决定继续作为历史事实，I4 raw、价格、授权、统计和生命周期均不得覆盖或回算；但该接受不再构成阶段 7 可以完成的充分条件。当前没有得到具体 AI 初筛失败案例，因此不能可靠选择 Prompt、Schema、Service、模型能力或展示解释层，也不能直接进入实现或付费复验。

新的唯一顺序为：

1. 用户提供具体问题场景：JD/简历背景、实际 AI 输出、期望结果、业务影响和是否可稳定复现；敏感信息应先脱敏。
2. 只读复现并建立问题总账，区分结构错误、证据错误、事实/语义问题、分数解释、稳定性、模型可用性和 UI 表达；不得先改代码迎合单例。
3. 根据问题总账编写新的整改设计和有序批次，明确每批责任层、允许/禁止文件、精确红灯、自动化与人工验收、真实模型预算、证据路径、失败返回层和停止点。
4. 用户明确确认整改设计后，才允许逐批修改生产链；真实模型复验必须重新查询官方价格并取得独立 USD 授权。
5. 全部整改和新质量验收满足最新产品标准后，重新执行尚未封存的 CLOSE-07；完成后另行确认 CLOSE-08。

本轮只更新权威状态文档。禁止修改 Prompt、Schema、Service、Adapter、API、Model、migration、React、测试、I2/I3/I4 正式证据或 PostgreSQL；禁止读取 Key、调用模型、产生 API attempt/token/费用或创建新的真实结果。

## 13. 7R5-CLOSE-08：阶段 7 完成评审

依赖：CLOSE-07 完成，用户另行确认评审。

唯一目标：逐项核对 5.0 主设计第 34 节完成标准，更新阶段状态、实施总计划、文档索引和交接说明。

原完成条件要求产品主链、自动化、真实质量、PostgreSQL/API/浏览器、费用、证据、隐私和 HR 决策边界全部通过。2026-09-01 的最终评审没有回算原始机器门槛，而是由项目负责人明确接受 R12 隐私语境误报和 LLM 评分偏保守为非阻塞已知限制，并确认阶段 7 按当前产品范围完成。阶段 8 仍须重新完成自己的需求确认门禁。

## 14. 阶段 7 未通过时的停止点（历史）

当前 CLOSE-06R2-A—C 已完成。I2 生命周期保持 `i2_final_complete`；I3-R1 保持 `i3_raw_complete`，human/final 不存在且不再继续；I4 已封存唯一 raw，生命周期为 `i4_raw_complete`，human/final 按既有决定保持不存在。当前生产实现是计划 Prompt/Service v4/v5、报告 Prompt/Service v7/v9，计划和报告 Schema 均为 5.0。用户已经完成人工界面验收，但最新判定 AI 初筛仍有问题、阶段 7 不能通过；当前停止点改为问题梳理与整改设计：

- 不重复修改或复验已完成的 Resume R1-B；
- 不再执行 CLOSE-02、CLOSE-07 封存或模型调用；
- 不覆盖、重算或重新 finalize I2 raw/human/final；
- 不重复修改已完成的 Prompt、Service、Schema、数据库或其他生产模块；
- 不修改旧 I3 或 I3-R1 的已冻结样本、标签和 zero-call preflight；
- 不覆盖、补跑、续跑或重新生成 I3-R1 raw；不创建其 human/final，不再次读取 Key 或调用模型；
- 在具体问题和整改设计获得确认前，不修改生产计划或报告 Prompt/Schema/Service，不创建 I4 human/final；
- 不重复或覆盖 CLOSE-06R2-A preflight/复核单、CLOSE-06R2-B 价格快照或 I4 raw，不自动进入阶段 8。

用户此前接受 CLOSE-06R2-C 的唯一 I4 raw 并取消 D/E，但最新验收结论是 AI 初筛仍需改进，阶段 7 不通过。当前唯一下一步是收集具体失败案例并完成只读归因和新的整改设计；不得补跑或覆盖 raw、创建 human/final、读取 Key、调用模型、封存 CLOSE-07 或进入 CLOSE-08。

## 15. 最终关闭决定与当前停止点

2026-09-01，项目负责人对最终 v10/v2 验收结果作出明确取舍：

- R12 的“手机号用户”不含真实号码，但仍会被当前隐私正则保守拒绝；该特殊误报本轮不修。
- R04/R08/R16/R18/R20 等 partial/区间偏低现象，以及五个 high 稳定组均固定为 88，作为 LLM 评分偏严格或分档锚定的已知风险保留；待整个平台主链完成后另立专项，不再阻塞阶段 7。
- 最终 raw 的 `19/20`、`14/19`、`7/19`、`quality_gate_passed=null` 和 `quality_conclusion_allowed=false` 均保持原样；产品验收通过不等于机器质量结果被改为全绿。
- CLOSE-07 未封存的历史事实继续保留，不伪造结果文件；本次以最终 v10/v2 真实证据、现有自动化、真实 PostgreSQL/API、人工界面验收、migration 和 HR 决策边界完成受控例外评审。

阶段 7 到此关闭。当前唯一下一步是阶段 8 的需求确认：讨论公开投递、可靠落库、持久化任务队列/Worker、幂等与重试、失败隔离、任务可观察性以及 HR 正常/异常处理流程，并形成独立阶段 8 设计后再次获得用户确认。不得直接开始阶段 8 生产实现，也不得借阶段 8 顺手修改阶段 7 Prompt、评分或隐私合同。
