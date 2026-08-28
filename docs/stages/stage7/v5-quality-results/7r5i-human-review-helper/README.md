# 7R5-I 人工审核辅助清单（不是正式审计结论）

## 先说清楚这是什么

这套文件把冻结人工标签、程序状态和真实模型回答排到了一起，让你能按行核对。它**不会替你判断**，所有“人工填写”列都故意留空；它也不是正式的 `human-audit.json`，不能直接触发 finalize。

> 2026-08-28 审核方式修正：CSV 不适合直接理解完整上下文。计划审核现在必须先打开 [`plan-review-cards/INDEX.md`](plan-review-cards/INDEX.md)，在同一张卡中完整阅读 JD、冻结标签、DeepSeek 评价项及其来源，再把真人确认后的判断写回 CSV。P00、P01 此前仅根据摘要作出的初步值已经恢复为空，过程保留在 [`plan-review-cards/SUMMARY_REVIEW_RESET_LOG.md`](plan-review-cards/SUMMARY_REVIEW_RESET_LOG.md)。

- raw 文件：`docs/stages/stage7/v5-quality-results/2026-08-27-stage7-7r5i-quality-raw-results.json`
- raw SHA-256：`de093654e76ffba4812dd1feb2e093e060dcf325f04a6a8aeec93a0c47ff31ac`
- fixture 文件：`backend/tests/fixtures/v5_quality_samples.py`
- fixture SHA-256：`23d2fddaec8468c00b1bdf1fec836e1f323b110d1bc44fb53fcbedd6fc401e23`
- 冻结 fixture 合同 SHA-256：`2ecc2da188f09883c1b6acaa40d0ca25f2306f2894e7f060a3a26aefb2fa9643`
- 实际调用：29 次业务调用 / 29 次 API attempt

## 你只需要按这个顺序做

1. 先从 `plan-review-cards/INDEX.md` 打开对应计划审核卡，完整阅读 JD、冻结标签和 DeepSeek 全部评价项；真人确认后，再把判断写入 `01-plan-label-review.csv` 和 `02-plan-sensitive-review.csv`。
2. 打开 `02-plan-sensitive-review.csv`。每份计划逐条找敏感属性评分，填数量；没有就填 `0`。
3. 打开 `03-report-review.csv`。每份报告核对简历原文、模型证据和冻结方向，填写 5 个人工判断列。程序状态为 blocked 时填 `未调用`，不要猜。
4. 打开 `04-required-direction-review.csv`。107 条 frozen required 标签逐条判断“一致 / 不一致 / 未调用”。
5. 打开 `05-stability-review.csv`。15 次运行只判断严重事实错误和敏感评分；未调用的写 `未调用`。
6. 如摘要不够，去 `06-model-response-index.csv` 用 `case_id` 查完整 raw 回答。不要修改该文件。
7. 全部审核完，再把 12 个计数填进 `07-metric-summary.csv`，并告诉 Codex 审阅人姓名/标识和带时区时间。此时才可以校验并准备正式人工审计文件；在你明确提交前不会 finalize。

## 三条最重要的判断规则

- “编造事实”：模型写了简历/JD 里没有的具体事实、经历、数字或结论。
- “严重事实错误”：错误足以明显改变匹配方向或核心 required 判断；小措辞问题不算严重。
- “替 HR 作决定”：出现“应录用、应淘汰、通过筛选”等招聘决定；只写匹配度和追问不算。

## blocked 和失败样本怎么办

不要跳过分母，也不要替模型脑补。没有实际模型回答的地方按清单填 `未调用`；有 raw 回答但被程序拒绝的，仍审核它已经返回的内容。自动结构门槛已经失败，人工审核的作用是定位语义问题，不是把自动失败改成通过。

## 文件行数应当固定为

- `01-plan-label-review.csv`：103 行数据 = 55 必备 + 22 禁止新增 + 26 非评价内容。
- `02-plan-sensitive-review.csv`：10 行数据。
- `03-report-review.csv`：20 行数据。
- `04-required-direction-review.csv`：107 行数据。
- `05-stability-review.csv`：15 行数据。
- `06-model-response-index.csv`：45 行数据 = 29 次已调用 + 16 次被门禁阻止。
- `07-metric-summary.csv`：12 行固定人工指标。

## 不能做的事

- 不改 frozen fixture、Prompt、Schema、程序状态或 raw 回答。
- 不把失败样本删出分母，不因模型答案改变原标签。
- 不把这套辅助清单冒充正式人工审计结论。
- 不自行补跑、整改、finalize 或进入 7R5-J。
