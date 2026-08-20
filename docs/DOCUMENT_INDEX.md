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
│   └── stage7/
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

只有修改 JobRequirements、岗位状态或排查阶段 6 回归时阅读。

### 阶段 7：Application 与 AI 初筛

- `stages/stage7/2026-08-20-stage7-jd-driven-ai-screening-redesign.md`

这是当前阶段的权威业务和技术合同。修改阶段 7 业务前必须完整阅读。

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
| 修改阶段 7 | 当前阶段 7 设计 + 相关代码和测试 |
| 盘点旧 Rubric | 当前阶段 7 设计第 2、19、23 节 + 旧阶段 7 归档 |
| 修改简历处理 | 对应阶段 4/5 资料 |
| 修改岗位管理 | 阶段 6 设计与验收记录 |
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
