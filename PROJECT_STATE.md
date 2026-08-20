# 项目当前状态

> 最新更新：2026-08-20
>
> 本文件只记录“现在是什么状态、下一步做什么”。完整开发过程已归档到 `docs/archive/history/2026-08-20-project-history.md`，不再作为新对话的默认阅读材料。

## 1. 当前结论

- 项目正在建设新版招聘主链，旧 React + FastAPI + SQLite + Mock LLM 演示系统已经退役。
- 阶段 4“简历上传与原文提取”、阶段 5“AI 结构化草稿”、阶段 6“结构化岗位管理”已经完成。
- 阶段 7“Application 与 AI 初筛底座”正在按重设计方案逐步实施。
- Application、Resume 隔离、HR 内部录入和 HR 决策等公共能力继续保留。
- 旧 Rubric、五维权重、确定性评分、`unknown`、证据覆盖率、Python 加权总分和多报告历史方案已经废弃。
- 阶段 7 当前业务方案已经确认；旧 Rubric 全链盘点和删除已经完成，下一步实现新版 `JobEvaluationPlan`。

## 2. 当前权威文档

文档职责和按任务阅读规则统一见 `docs/DOCUMENT_INDEX.md`。

当前阶段的权威顺序是：

1. 阶段 7 当前设计：`docs/stages/stage7/2026-08-20-stage7-jd-driven-ai-screening-redesign.md`
2. 本文件：只负责当前进度、工作区风险和下一步
3. `CLAUDE.md`：项目长期架构、技术栈和稳定约束
4. `docs/planning/implementation-plan.md`：跨阶段实施顺序
5. `docs/planning/2026-08-14-post-stage5-product-roadmap.md`：阶段 5 后产品路线
6. `docs/architecture/2026-07-15-hr-agent-platform-design.md`：总体架构背景

发生冲突时，当前阶段专项设计优先于旧总体示例和历史记录。归档文档不具有当前业务权威性。

## 3. 当前阶段 7 方案摘要

### 3.1 固定流程

```text
HR 填写并发布 JD
        ↓
DeepSeek 拆解自由文本 + 程序补齐结构化 JobRequirements
        ↓
生成同一 JD 版本下稳定、只读的基础评价事项
        ↓
读取当前 Application 绑定的当前 Resume
        ↓
DeepSeek 单次综合评价
        ↓
后端严格校验结构、事项、证据和安全边界
        ↓
保存一份当前 AI 初筛报告
        ↓
React 渲染完整报告，HR 独立决定通过、备选或淘汰
```

本流程是固定的 Service 工作流，不是自然语言 Agent，也不使用 LangGraph。

### 3.2 评分与报告边界

- 基础事项按 `required/preferred/general` 标记，逐项使用 `0—10` 整数，不使用 `unknown`。
- 0 分表示当前简历没有体现，不代表候选人事实上不会。
- 1—10 分必须有可定位的简历证据。
- 每份简历可以有 0—5 个有证据、7—10 分、只产生正向影响的额外亮点。
- DeepSeek 直接给出 `0—100` AI 岗位匹配建议分；Python 不按固定权重重新计算。
- 程序只根据综合分生成五档展示标签，不生成通过、淘汰或录用建议。
- 每个 Application 只保留最近一次成功报告和必要运行日志；重新评估失败时保留旧成功报告。
- 姓名、联系方式、性别、出生日期、婚育、民族、籍贯和照片等内容在模型输入前移除。
- 学校和公司名称可以结合真实专业、职责、项目和成果作为语境，不能只按品牌判断能力。

完整字段、状态、失败语义、验收场景和实施顺序以阶段 7 当前设计为准，本文件不重复维护第二套详细合同。

## 4. 已完成且继续保留的能力

- 新版唯一前端业务目录：`frontend/src/features/recruitment/`
- 新版工作台路由：`/app/*`；公开投递入口：`/apply`
- 正式后端接口：`/api/v2/*`
- PostgreSQL + SQLAlchemy 2.0 + Pydantic v2 + Alembic 主链
- PDF、DOCX、TXT 安全上传、私有存储和原文提取
- `Resume.raw_text` 与 `Resume.parsed_snapshot`
- DeepSeek 简历结构化草稿、严格校验和 HR 确认创建
- 结构化 JobRequirements、岗位草稿/开放/关闭状态
- Candidate 稳定身份与去重
- Application 按岗位独立绑定 Resume、独立 HR 决策和阶段历史
- HR 直通录入与 AI 初筛中心待审核录入

## 5. 已完成删除的旧阶段 7 能力

- `JobScreeningRubric` 及模板、草稿、编辑、生成、发布和版本流程
- `standard/technical/non_technical` Rubric 模板
- 五维权重、维度内部占比和 AI 占比优化
- HR 手动维护 Rubric 语义项及 AI 单项辅助
- Python 年限、学历、技能和关键词确定性评分
- `unknown`、证据覆盖率、推荐上限和 Python 加权总分
- 同一 Application 多份完整 ScreeningResult 历史
- 旧 Rubric 页面、API、Schema、Service、Prompt、Adapter、Model 字段和相关测试

已执行的 Alembic 历史保持不变；新迁移 `c4a9d8e7f621` 已向前删除旧表、字段、索引和约束。它的 downgrade 只恢复空结构，不能恢复已删除的数据。

旧设计已经归档到 `docs/archive/superseded/2026-08-17-stage7-application-ai-screening-design.md`，只在盘点旧 Rubric 或追溯历史时阅读。

## 6. 当前工作区状态与风险

- 工作区存在本轮尚未提交的旧 Rubric 删除和公共链路解耦修改；`AGENTS.md` 另有用户原有修改，必须继续保留。
- 禁止使用 `git reset --hard`、`git clean`、`git checkout --` 或其他方式整体覆盖这些修改。
- 后续不得恢复旧 Rubric、旧 ScreeningResult 或嵌入 Application 的 AI 状态字段。
- 新功能应复用 Candidate、Application、Resume、Job、StageHistory、Report 和通用 DeepSeek/数据库基础设施。

## 7. 当前唯一下一步

执行阶段 7 当前设计的小步骤 4：实现 `JobEvaluationPlan`。

开始前仍须按当前设计核对 `JobEvaluationPlan` 的字段、JD 版本绑定、生成/校验/只读边界和验收测试。本轮小步骤 3 没有提前创建该模型，也没有实现新版 AI 初筛报告。

## 8. 最近验证基线

- 开发库旧 `job_screening_rubrics` 与 `screening_results` 均为 0 行后执行删除迁移，最终位于 Alembic `c4a9d8e7f621 (head)`。
- 迁移已实际完成“升级 → 回退到 `f8c2d0e5b317` → 再升级”；回退时旧表、字段、索引和约束恢复为空结构，最终再次删除。
- 后端 460 项 `unittest` 通过；前端 16 个 Node/Vite 测试脚本通过；Vite 生产构建 3116 个模块通过。
- 这些结果证明旧引用已移除、公共链路可回归、迁移可执行；不代表新版 `JobEvaluationPlan` 或 AI 初筛报告已经实现。

开始下一步前仍须重新检查实际 Git 状态、测试数量、Alembic revision 和数据库状态，不能只依赖这里的历史基线。

## 9. 新对话恢复方式

1. 阅读 `CLAUDE.md`。
2. 阅读本文件。
3. 根据 `docs/DOCUMENT_INDEX.md` 判断任务需要哪些补充文档。
4. 修改阶段 7 业务代码前，完整阅读阶段 7 当前设计。
5. 执行任何修改前检查 `git status` 和相关差异，保护现有工作区修改。
