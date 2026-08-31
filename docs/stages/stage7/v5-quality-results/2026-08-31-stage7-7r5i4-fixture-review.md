# Stage 7 I4 fixture review

## 这张复核单解决什么问题

本文件只用于在真实调用前人工检查 I4 的新考卷和标签。简历中的任职起止日期可以保留，作为原始经历的定位信息；AI 不得计算工作年限，不得判断年限是否达标，也不得据此评分。

- 纯工作年限要求不进入 required 分母。
- 混合要求保留非年限能力，例如“3 年以上 Java 经验”只保留 Java。
- 方向稳定和分差继续记录，但只作为诊断；15/15 合法输出、极端翻转、敏感评分和非年限严重事实错误仍是硬门槛。
- CLOSE-06R2-B 尚未开始；本批不查价格、不读取 Key、不调用真实模型。

## 计划样本

| Case | 岗位 | required 标签 | 排除的纯年限要求 | 混合要求保留能力 |
| --- | --- | --- | --- | --- |
| I4-P00 | 订单平台 Java 工程师 | Java、能够使用 Spring Boot 设计 REST API | 3 年以上工作经验 | Java |
| I4-P01 | 数据管道工程师 | Spark、能够使用 Airflow 编排数据任务 | 4 年以上工作经验 | Spark |
| I4-P02 | 移动端体验工程师 | Flutter、具备移动端性能分析和优化实践 | 3 年以上工作经验 | Flutter |
| I4-P03 | 风控策略分析师 | SQL 分析、能够设计并评估风险规则 | 3 年以上工作经验 | SQL 分析 |
| I4-P04 | 制造质量工程师 | SPC、能够使用 8D 方法推动缺陷闭环 | 5 年以上工作经验 | SPC |
| I4-P05 | 企业实施顾问 | ERP 实施、具备客户需求澄清和方案配置能力 | 3 年以上工作经验 | ERP 实施 |
| I4-P06 | 搜索产品经理 | 搜索产品、能够设计搜索质量指标和实验 | 4 年以上工作经验 | 搜索产品 |
| I4-P07 | 采购品类经理 | 品类采购、能够开展供应商成本分析与谈判 | 5 年以上工作经验 | 品类采购 |
| I4-P08 | 品牌内容策划 | B2B 内容策划、能够基于传播数据迭代内容 | 3 年以上工作经验 | B2B 内容策划 |
| I4-P09 | 仓储流程优化师 | WMS 优化、能够开展仓储流程分析和改善 | 4 年以上工作经验 | WMS 优化 |

## 报告样本

| Case | 计划来源 | 人工方向 | required 有证据 | required 缺证据 |
| --- | --- | --- | --- | --- |
| I4-R00 | I4-P00 confirmed snapshot | high_match | Java、能够使用 Spring Boot 设计 REST API | 无 |
| I4-R01 | I4-P01 confirmed snapshot | high_match | Spark、能够使用 Airflow 编排数据任务 | 无 |
| I4-R02 | I4-P02 confirmed snapshot | high_match | Flutter、具备移动端性能分析和优化实践 | 无 |
| I4-R03 | I4-P03 confirmed snapshot | high_match | SQL 分析、能够设计并评估风险规则 | 无 |
| I4-R04 | I4-P04 confirmed snapshot | high_match | SPC、能够使用 8D 方法推动缺陷闭环 | 无 |
| I4-R05 | I4-P05 confirmed snapshot | high_match | ERP 实施、具备客户需求澄清和方案配置能力 | 无 |
| I4-R06 | I4-P06 confirmed snapshot | high_match | 搜索产品、能够设计搜索质量指标和实验 | 无 |
| I4-R07 | I4-P07 confirmed snapshot | high_match | 品类采购、能够开展供应商成本分析与谈判 | 无 |
| I4-R08 | I4-P08 confirmed snapshot | partial_match | B2B 内容策划 | 能够基于传播数据迭代内容 |
| I4-R09 | I4-P09 confirmed snapshot | partial_match | WMS 优化 | 能够开展仓储流程分析和改善 |
| I4-R10 | I4-P00 confirmed snapshot | partial_match | Java | 能够使用 Spring Boot 设计 REST API |
| I4-R11 | I4-P01 confirmed snapshot | partial_match | Spark | 能够使用 Airflow 编排数据任务 |
| I4-R12 | I4-P02 confirmed snapshot | partial_match | Flutter | 具备移动端性能分析和优化实践 |
| I4-R13 | I4-P03 confirmed snapshot | partial_match | SQL 分析 | 能够设计并评估风险规则 |
| I4-R14 | I4-P04 confirmed snapshot | low_match | 无 | SPC、能够使用 8D 方法推动缺陷闭环 |
| I4-R15 | I4-P05 confirmed snapshot | low_match | 无 | ERP 实施、具备客户需求澄清和方案配置能力 |
| I4-R16 | I4-P06 confirmed snapshot | low_match | 无 | 搜索产品、能够设计搜索质量指标和实验 |
| I4-R17 | I4-P07 confirmed snapshot | low_match | 无 | 品类采购、能够开展供应商成本分析与谈判 |
| I4-R18 | I4-P08 confirmed snapshot | low_match | 无 | B2B 内容策划、能够基于传播数据迭代内容 |
| I4-R19 | I4-P09 confirmed snapshot | low_match | 无 | WMS 优化、能够开展仓储流程分析和改善 |

## 稳定性抽样

- 样本：I4-R00, I4-R04, I4-R08, I4-R10, I4-R14。
- 每个样本重复 3 次，共 15 次。
- 人工方向分布：2 high / 2 partial / 1 low。

## 停止点

CLOSE-06R2-A 完成后停止。只有用户复核这张清单并另行确认，才可进入 CLOSE-06R2-B。
