# 阶段 7：Application 与 AI 初筛

> 状态：已于 2026-09-01 完成产品验收并关闭。

## 当前入口

- [最终业务设计](2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md)：当前产品合同、完整链路、状态、失败语义和安全边界。
- [最终验收审核卡](2026-09-01-stage7-final-v10-v2-acceptance-review.md)：最终真实质量数据、产品负责人接受的限制和完成结论。
- `2026-09-01-stage7-final-v10-v2-raw-results.json`：最终 20 份报告与 15 次稳定性原始结果。
- `2026-09-01-stage7-final-v10-v2-attempt-journal.jsonl`：最终 35 次真实调用的逐 attempt 审计。

## 一条主线

```text
Application 与 Resume 隔离
→ AI 根据完整 JD 生成轻量评价清单
→ HR 编辑并确认清单
→ 异步 AI 初筛与一次受控 Repair
→ Service 校验结构、引用和安全
→ 当前报告与历史报告
→ HR 独立作出通过 / 备选 / 淘汰决定
```

阶段 7 后半段的主要整改方向是：从复杂 Rubric 和程序语义裁判，收缩为 HR 可编辑的轻量评价清单；普通语义由 LLM 和 HR 负责，Service 只保留确定性的结构、引用、安全和事务保护；工作年限退出 AI 初筛；报告允许诚实空列表；模型结构错误最多进行一次完整 Repair。

## 最终版本

- 评价计划：`deepseek-v4-pro` / Prompt v4 / Service v5 / Schema 5.0
- 初筛报告：`deepseek-v4-pro` / 主 Prompt v10 / Repair Prompt v2 / Service v11 / Schema 5.0
- 数据库：Alembic `e7f9a1b3c545`

## 已知限制

- R12 中“手机号用户”这一普通业务语境会被当前隐私规则保守拒绝。
- 部分匹配样本的 LLM 分数可能系统性偏低；五个 high 稳定组均为 88。

以上限制由项目负责人接受为非阻塞项。原始机器统计保持 `19/20` 合法、方向 `14/19`、分数区间 `7/19`、`quality_gate_passed=null`，没有被回算成机器全绿。

## 历史恢复

旧 Rubric、Step 9、3.0/4.0、I2、I3、I4、P5R 和逐批停止点已经从当前目录删除。需要追溯时使用 2026-09-01 阶段关闭前的 Git 提交历史，不再把历史流水作为当前开发入口。
