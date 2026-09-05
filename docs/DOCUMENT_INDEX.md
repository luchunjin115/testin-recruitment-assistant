# 项目文档索引

> 这是 `docs/` 的唯一导航入口。文档按“规划、架构、阶段、研究、归档”分类；新对话不需要阅读全部文件。

## 1. 新对话默认阅读

1. `../CLAUDE.md`：长期技术规则和架构边界。
2. `../PROJECT_STATE.md`：当前阶段、工作区风险和唯一下一步。
3. 本索引：根据任务选择补充资料。

修改业务代码、测试、数据库或验收材料前，再完整阅读当前阶段专项设计。

## 2. 目录分类

```text
docs/
├── DOCUMENT_INDEX.md
├── planning/                 路线和实施顺序
├── architecture/             长期总体架构
├── stages/                   各阶段设计、映射、交接和验收
│   ├── stage4/
│   ├── stage5/
│   ├── stage6/
│   ├── stage7/
│   ├── stage8/               公开投递与异步自动处理
│   └── stage9/               面试、Offer、录取与招聘流程统计
├── research/                 外部项目与技术研究
└── archive/                  非现行材料
    ├── history/              完整项目流水和详细旧计划
    ├── superseded/           已被新设计替代的旧版本
    └── legacy-system/
        ├── retirement/       旧系统退役决策、清单和总结
        └── demo/             旧 SQLite/Mock LLM 演示资料
```

## 3. 现行规划与架构

| 文档 | 职责 | 什么时候阅读 |
| --- | --- | --- |
| `planning/implementation-plan.md` | 阶段状态、实施顺序和完成标准 | 调整当前执行步骤或跨阶段顺序时 |
| `planning/2026-08-14-post-stage5-product-roadmap.md` | 阶段 6—12 产品目标和依赖 | 讨论后续路线或启动新阶段时 |
| `architecture/2026-07-15-hr-agent-platform-design.md` | 长期分层、对象和技术决策 | 修改总体架构、模块职责或全局数据流时 |

## 4. 阶段资料

### 阶段 4：简历上传与原文提取

- `stages/stage4/2026-08-07-stage4-resume-upload-design.md`

只有修改文件上传、私有存储、PDF/DOCX/TXT 提取或阶段 4 回归时阅读。

### 阶段 5：简历结构化

- `stages/stage5/2026-08-12-stage5-resume-structure-design.md`
- `stages/stage5/2026-08-12-stage5-resume-draft-field-mapping.md`
- `stages/stage5/2026-08-12-stage5-development-handoff.md`

只有修改 DeepSeek 简历结构化、草稿字段映射、辅助填表或排查阶段 5 回归时阅读。

### 阶段 6：结构化岗位

- `stages/stage6/2026-08-15-stage6-structured-job-management-design.md`
- `stages/stage6/2026-08-17-stage6-acceptance.md`
- `stages/stage6/2026-08-21-stage6-five-section-jd-remediation-design.md`
- `stages/stage6/2026-08-22-stage6-five-section-jd-remediation-acceptance.md`

第三份是五段式 JD 字段、开放校验、空库迁移、阶段 7 暂停边界和 6R-A—6R-D 实施顺序的权威设计补充；第四份记录 6R-D 的自动化、真实 PostgreSQL、API、浏览器和截图结果。修改岗位 Schema、表单、数据库或恢复阶段 7 前，必须同时阅读原阶段 6 设计和五段式补充；2026-08-17 原验收只证明旧 `description + JobRequirementsV1` 合同曾通过。

### 阶段 7：Application 与 AI 初筛

- `stages/stage7/README.md`
- `stages/stage7/2026-08-26-stage7-lightweight-evaluation-ai-screening-v5-redesign.md`
- `stages/stage7/2026-09-01-stage7-final-v10-v2-acceptance-review.md`

`README.md` 是单一入口；5.0 设计记录现行产品合同；最终审核卡记录真实结果、已知限制和关闭决定。最终 raw 与 attempt journal 由入口链接，不作为日常阅读材料。中间实验、旧合同和一次性验收过程由 Git 历史恢复。

### 阶段 8：公开投递与异步自动处理

- `stages/stage8/2026-09-02-stage8-public-application-async-processing-design.md`
- `stages/stage8/2026-09-02-stage8-implementation-record.md`

第一份文档已于 2026-09-02 获得项目负责人逐项确认，是阶段 8 当前业务合同，记录作品集演示边界、公开表单、可靠受理、Candidate/Resume/Application 边界、PostgreSQL 持久任务、独立 Worker、幂等重试、失败隔离、HR 正常/异常处理、隐私和验收方案。第二份是阶段 8 唯一实施记录，按 8A—8F 维护实际修改、验证结论、不能证明的边界和剩余风险，不重新定义业务规则。8A—8F、真实模型最小链路和项目负责人浏览器检查均已完成，项目负责人于 2026-09-02 确认阶段 8 最终验收通过。当前进度以 `PROJECT_STATE.md` 为准；修改阶段 8 前必须完整阅读设计，并按任务读取实施记录。

### 阶段 9：面试、Offer、录取与招聘流程统计

- `stages/stage9/2026-09-02-stage9-interview-offer-hiring-pipeline-design.md`
- `stages/stage9/2026-09-02-stage9-implementation-record.md`

第一份是项目负责人已确认的阶段 9 唯一业务设计，统一维护 Application 后半程状态、InterviewRecord、OfferRecord、具体薪资、审计与更正、AI 初筛中心信息收口、确定性 AI 标签和招聘流程统计合同。第二份是阶段 9 唯一实施记录，只维护 9A—9F 实际修改、验证、证明边界、风险和下一步，不复制业务合同。9A—9F 已全部完成，项目负责人于 2026-09-05 确认阶段 9 最终验收通过并关闭；当前进度以 `PROJECT_STATE.md` 为准。

## 5. 研究资料

- `research/2026-08-15-github-recruiting-project-comparison.md`

外部项目只用于产品和架构研究，不能覆盖当前阶段专项设计，也不能绕过阶段门禁。

## 6. 归档资料

### 历史流水

- `archive/history/2026-08-20-project-history.md`
- `archive/history/2026-08-20-implementation-plan-detailed.md`

只在追溯某个旧步骤、验证数字或历史决定时阅读。

### 被替代的设计

- `archive/superseded/2026-07-15-hr-agent-platform-design-v1.md`
- `archive/superseded/2026-08-14-post-stage5-product-roadmap-v1.md`
- `archive/superseded/2026-08-17-stage7-application-ai-screening-design.md`

旧阶段 7 设计仅在盘点、删除旧 Rubric 或追溯历史时阅读，不得作为新增业务实现依据。

### 旧系统退役资料

`archive/legacy-system/retirement/` 保存退役决策、迁移清单、代码删除清单、命名计划和最终总结。

只有排查旧入口、旧数据、已删除文件或退役边界时阅读。

### 旧演示资料

`archive/legacy-system/demo/` 中的业务方案、架构说明、Prompt 文档、演示脚本和答辩讲稿属于旧 SQLite + Mock LLM 系统。

这些材料不能用于当前项目的开发、演示、简历或答辩，只能用于历史对比。

## 7. 按任务快速选择

| 任务 | 补充阅读 |
| --- | --- |
| 查看当前进度 | 不补充；读取 `CLAUDE.md` 和 `PROJECT_STATE.md` 即可 |
| 修改阶段 7 | 阶段 7 `README.md` + 5.0 当前设计 + 与改动直接相关的代码和测试；涉及岗位输入合同再读阶段 6 五段式补充 |
| 追溯阶段 7 中间实验 | 从 Git 历史恢复对应提交，不把旧过程文档重新列为当前入口 |
| 讨论或修改阶段 8 | 阶段 8 当前设计 + 实施记录 + 与改动直接相关的阶段 4/5/7 合同和代码 |
| 讨论或修改阶段 9 | 阶段 9 当前专项设计 + 与改动直接相关的阶段 4—8 合同、实际代码和测试 |
| 修改简历处理 | 对应阶段 4/5 资料 |
| 修改岗位管理 | 阶段 6 原设计 + 五段式 JD 整改补充；旧验收仅作历史基线 |
| 调整总体架构 | architecture + planning 两份现行文档 |
| 启动新阶段 | 产品路线 + 实施计划 + 新阶段专项设计 |
| 追溯旧系统 | 对应 archive 子目录，不读取全部归档 |

## 8. 权威性顺序

1. 当前阶段专项设计负责具体业务合同、数据、状态、失败语义和验收标准。
2. `PROJECT_STATE.md` 只负责当前进度、风险和下一步。
3. `CLAUDE.md` 只负责长期稳定规则。
4. planning 和 architecture 提供跨阶段背景，不能覆盖更新日期更晚的阶段设计。
5. `archive/` 下所有材料都不具有当前业务权威性。

如果代码、状态文档和当前阶段设计互相矛盾，应先停止扩展并完成只读核对。

## 9. 文档维护规则

- 同一业务规则只在当前阶段专项设计中维护，其他文档使用摘要和链接。
- 完成小步骤后更新 `PROJECT_STATE.md`；详细过程进入对应阶段验收或历史归档。
- 阶段完成后仍可能保留在 `stages/`，供回归排查；只有被替代或明确失效的材料才进入 `archive/`。
- 移动文档后必须扫描旧路径、验证当前入口并运行 `git diff --check`。
