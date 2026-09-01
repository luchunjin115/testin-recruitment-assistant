# 项目当前状态

> 最新更新：2026-09-01
>
> 本文件只记录当前结论、风险和下一步；详细过程由 Git 历史恢复。

## 当前结论

- 阶段 4—7 已完成，阶段 8 尚未开始。
- 阶段 7 已于 2026-09-01 通过项目负责人验收并关闭；功能链路已经完成，目前不是“等待继续开发才能交付”的状态。
- 阶段 7 当前生产合同：评价计划 `deepseek-v4-pro` / Prompt v4 / Service v5 / Schema 5.0；初筛报告 `deepseek-v4-pro` / 主 Prompt v10 / Repair Prompt v2 / Service v11 / Schema 5.0。
- `ScreeningRun` 最多保留 3 个 API attempts；当前 Alembic head 为 `e7f9a1b3c545`。
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
3. `docs/stages/stage7/README.md`：阶段 7 单一入口。
4. `docs/stages/stage7/2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`：阶段 7 最终业务合同。
5. `docs/stages/stage7/2026-09-01-stage7-final-v10-v2-acceptance-review.md`：最终验收结论与已知限制。
6. `docs/planning/implementation-plan.md`：跨阶段实施顺序。

## 当前风险与工作区状态

- 阶段 7 收尾整理已完成：当前目录只保留单一入口、最终合同、最终验收和最终原始证据；一次性质量运行器与中间批次测试已删除。
- 整理前的完整恢复点是分支 `2lcj` 上的提交 `f2e77b0`；被删过程材料可从 Git 历史找回。
- 最终 raw 结果没有回算、覆盖或美化。
- 本地 PostgreSQL 已执行既有迁移到 `e7f9a1b3c545 (head)`。

## 唯一下一步

1. 提交并推送阶段 7 整理结果。
2. 与项目负责人讨论阶段 8 的需求、范围和验收标准。
3. 在阶段 8 专项设计确认前，不开始阶段 8 生产实现。

## 新对话恢复方式

先读 `CLAUDE.md`、本文件和 `docs/DOCUMENT_INDEX.md`；涉及阶段 7 时再从 `docs/stages/stage7/README.md` 进入，不默认阅读 Git 历史中的中间实验材料。
