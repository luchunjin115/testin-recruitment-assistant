# 7R5-I 计划人工审核卡索引

## 为什么重新整理

此前P00、P01只展示了摘要，用户无法同时看到完整JD、冻结标签和DeepSeek完整评价项，因此原确认不足以构成知情人工审核。辅助CSV中的P00、P01人工值已恢复为空，并留下撤回说明；正式人工审计从未创建。

## 正确阅读顺序

每张卡都按同一顺序展示：完整JD → 冻结人工标签 → DeepSeek完整评价项及来源 → 空白人工填写区。先独立阅读三份证据，再作判断，不以程序成功或失败反推人工答案。

## 不可变来源

- raw：`../2026-08-27-stage7-7r5i-quality-raw-results.json`
- raw SHA-256：`de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`
- 冻结 fixture 合同 SHA-256：`2ecc2da188f09883c1b6acaa40d0ca25f2306f2894e7f060a3a26aefb2fa9643`

## 审核卡

- [P00 · Java 高级后端工程师](P00-plan-review-card.md) — 程序 `succeeded`；冻结标签 9/3/4；DeepSeek 17 项
- [P01 · 前端开发工程师](P01-plan-review-card.md) — 程序 `failed`；冻结标签 5/2/1；DeepSeek 11 项
- [P02 · 数据工程师](P02-plan-review-card.md) — 程序 `failed`；冻结标签 5/2/1；DeepSeek 12 项
- [P03 · 高级产品经理](P03-plan-review-card.md) — 程序 `failed`；冻结标签 4/2/5；DeepSeek 10 项
- [P04 · HRBP](P04-plan-review-card.md) — 程序 `succeeded`；冻结标签 3/3/2；DeepSeek 6 项
- [P05 · 财务分析师](P05-plan-review-card.md) — 程序 `succeeded`；冻结标签 3/2/1；DeepSeek 7 项
- [P06 · 市场推广经理](P06-plan-review-card.md) — 程序 `succeeded`；冻结标签 6/2/3；DeepSeek 13 项
- [P07 · 运营经理](P07-plan-review-card.md) — 程序 `succeeded`；冻结标签 4/2/3；DeepSeek 11 项
- [P08 · UX/UI 设计师](P08-plan-review-card.md) — 程序 `failed`；冻结标签 6/2/2；DeepSeek 11 项
- [P09 · 高级法务](P09-plan-review-card.md) — 程序 `succeeded`；冻结标签 10/2/4；DeepSeek 18 项

## 停止点

这些卡只是人工阅读材料，不是正式结论。必须由真人确认，之后才将判断写入CSV；全部人工指标完成前，不创建正式human audit，不执行finalize。
