# 阶段 6 五段式 JD 整改验收记录

> 日期：2026-08-22
> 分支：`2lcj`
> HEAD：`c169c55d2e5a111b6422a8a88dcf857e7fe9388c`
> 验收结论：6R-A—6R-D 通过，阶段 6 五段式 JD 整改完成；阶段 7 继续受控暂停

## 1. 验收范围与结论

本次验收覆盖完整链路：

```text
React 五段式表单与列表
        -> /api/v2 Job API
        -> Pydantic Job Schema
        -> JobService 事务与状态机
        -> SQLAlchemy Job Model
        -> PostgreSQL jobs 五段式列
```

岗位背景、岗位职责、任职要求、加分项和候选人可见备注已经成为当前 Job 的唯一 JD 合同。草稿只要求标题；创建并开放、开放草稿、重新开放和开放岗位编辑均在同一事务中检查职责与任职要求。旧评价计划生成入口在后端和页面两层受控暂停，不会把新 Job 交给旧 Adapter。

本轮没有调用真实 DeepSeek，没有实现新的阶段 7 Prompt、Schema、Service 或 Adapter，也没有进入阶段 8。

## 2. 自动化与构建

| 验收项 | 实际结果 |
| --- | --- |
| 五段式后端定向合同 | 19 passed，48 个参数化子用例通过 |
| 五段式 migration 合同 | 4 passed |
| 后端全量 | 694 passed，411 个子用例通过；1 条既有 PyPDF2 弃用 warning |
| 6R-D 前端定向 | 12/12 通过 |
| 前端全量 | 32/32 通过 |
| TypeScript + Vite 生产构建 | 通过，转换 3121 个模块 |
| `git diff --check` | 通过 |

自动化覆盖五字段归一与长度、草稿/开放规则、非法开放编辑的原子回滚、旧字段和未知字段拒绝、API 读写合同、空/非空 jobs migration、React 五个大型文本框、请求映射、错误定位、列表摘要、搜索、阶段 7 暂停以及 Application、Resume、HR 决策、报告和岗位状态机回归。

## 3. Alembic 与真实 PostgreSQL

- 代码 head：`f2b8c6d1a940`。
- PostgreSQL current：`f2b8c6d1a940 (head)`。
- `alembic check`：`No new upgrade operations detected`。
- 临时 PostgreSQL 已完成空 jobs 表 `upgrade -> downgrade -> upgrade`。
- 临时库非空 jobs 表在任何 DDL 前以 `STAGE6_FIVE_SECTION_JD_REQUIRES_EMPTY_JOBS` 主动停止，旧结构和唯一夹具均保持不变。

正式开发库验收前后只读计数一致：

| 表 | 验收前 | 验收后 |
| --- | ---: | ---: |
| jobs | 0 | 0 |
| applications | 0 | 0 |
| candidates | 2 | 2 |
| resumes | 9 | 9 |
| job_evaluation_plans | 0 | 0 |
| screening_reports | 0 | 0 |
| screening_runs | 0 | 0 |
| stage_histories | 0 | 0 |

API 集成验收使用的 Job #326 和浏览器验收使用的 Job #327 均已删除，没有遗留候选人、申请、评价计划、报告、运行或阶段历史。序列号前进属于正常数据库行为，不等于残留业务数据。

## 4. 真实 API 主链

真实 FastAPI、SQLAlchemy 和 PostgreSQL 已验证：

1. 旧 `description/requirements/legacy_requirements` 和未知字段被拒绝。
2. 标题-only 草稿可创建、读取并保持五段式字段为 `null`。
3. 缺职责或任职要求的创建并开放、开放草稿和重新开放均返回稳定字段错误。
4. 五段式普通文本和内部换行可保存、重载并原样返回。
5. 完整草稿可以开放；合法编辑后仍保持 `open`。
6. 开放岗位被编辑为缺职责或任职要求时整次请求失败，数据库旧值和 `open` 状态不变。
7. 关闭岗位可继续编辑不完整草稿内容，但重新开放前仍必须补齐职责与任职要求。
8. 阶段 7 旧评价计划生成返回 HTTP 503 和 `JOB_EVALUATION_PLAN_CONTRACT_UPGRADE_IN_PROGRESS`，Adapter 调用计数保持 0。

## 5. Microsoft Playwright 浏览器验收

浏览器实际打开 `http://127.0.0.1:5173/app/jobs`，从页面完成：标题-only 草稿、刷新持久化、缺字段开放失败、补齐五段式、开放、编辑、关闭、关闭态编辑、非法重新开放、修复后重新开放和安全删除。

关键结果：

- 五个大型普通多行文本框均可操作，编号、项目符号和内部换行在保存、导航和重新编辑后保持一致。
- 把 `<script>window.__unsafe = true</script>` 当作岗位职责普通文本保存后，页面显示字面文本；`window.__unsafe` 为 `undefined`，DOM 中没有新增 script 节点。
- 开放岗位清空职责后保存得到预期 HTTP 422，抽屉停留并定位字段；重新加载后旧职责仍完整，证明事务回滚。
- 加分项文本可被岗位搜索命中，列表摘要只使用岗位职责与任职要求。
- 关闭态清空任职要求可以保存；重新开放得到预期 HTTP 422 并定位任职要求；恢复后重新开放成功。
- 评价计划抽屉在不存在历史计划时直接显示“五段式评价计划升级中”，没有生成/重新生成按钮。历史计划仍允许只读查看，刷新只执行 GET。
- 负向场景中的 422 会在浏览器记录预期的资源错误；重新导航后控制台为 0 个 error，仅有项目既存的 2 条 React Router v7 future warning。

三档布局均无整页横向溢出，抽屉底部操作区在视口内：

| 视口 | 抽屉宽度 | 可见文本框宽度 | 横向溢出 | 底部按钮 |
| --- | ---: | ---: | ---: | --- |
| 1440×900 | 720 px | 613 px | 0 px | 可见 |
| 820×1180 | 720 px | 613 px | 0 px | 可见 |
| 390×844 | 约 390 px | 291 px | 0 px | 四个按钮整行排列且可见 |

截图证据：

- `browser-acceptance-evidence/6rd-job-form-1440x900.png`
- `browser-acceptance-evidence/6rd-job-form-820x1180.png`
- `browser-acceptance-evidence/6rd-job-form-390x844.png`

## 6. 验收中修复的最小缺陷

1. 岗位保存成功通知原先可能在 Ant Design message 上下文临时卸载时触发。现在先记录待显示消息，列表重新进入 ready 后再显示。
2. 岗位状态和删除确认原先使用静态 `Modal.confirm`，会丢失 React 上下文。现在改为 `Modal.useModal()` 返回的实例。
3. 状态动作完成时原先可能在表单未挂载时执行 `resetFields()`。现在只在真正打开表单时重置。
4. 评价计划页面虽然后端会拒绝旧生成合同，仍曾显示生成按钮。现在页面直接展示受控暂停，移除生成和重新生成动作，同时保留历史计划只读能力。

相应静态合同、32 项前端全量和生产构建均在修复后重新通过；成功关闭和删除岗位的浏览器路径没有再产生 Ant Design message、Modal 或未连接 Form 警告。

## 7. 旧合同扫描与阶段 7 隔离

当前 Job API、JobService、Job Model、五段式 React 页面和 Job 前端 Service 对旧数据字段的运行边界扫描为 0。扫描中出现的 `description` 都是 Ant Design 组件的提示属性，不是 Job 数据字段。

为保证不可改写的历史 revision `c8e1a6f4d205` 仍可从零重放，`app.schemas.job` 保留一个明确标注为 migration-only 的 `JobRequirementsV1` 名称转发；它不属于 Job 请求、响应、Service 或 Model 合同。阶段 7 还保留自有的 `LegacyEvaluationPlanRequirements`，只用于解释历史计划快照。两者均不能读取新 Job 或生成新计划。

后端暂停合同测试通过、浏览器页面移除写入口、最终 `job_evaluation_plans=0` 和 `screening_runs=0` 共同证明本次验收没有实际调用旧 Adapter。未调用真实 DeepSeek。

## 8. 能证明与不能证明

本次能证明：五段式 Job 在前端、API、Schema、Service、Model 和 PostgreSQL 中使用同一合同；草稿与开放规则、事务回滚、状态机、普通文本安全、空库 migration 和旧 AI 暂停在当前环境中按设计工作；Application、Resume、HR 决策和报告等无关能力没有新增自动化回归。

本次不能证明：新的五段式 JD 如何拆成评价事项、真实 DeepSeek 的合法报告率/方向一致性/三次稳定性、生产级招聘准确率、未来 Agent 自动生成 JD、公开投递或阶段 8 能力。历史阶段 7 的 JD18 和下游质量失败也没有被本轮修复或重新计数。

## 9. 停止点

阶段 6 五段式 JD 整改到此完成。阶段 7 继续暂停；唯一下一步是讨论并编写“五段式 JD 如何生成评价计划”的新阶段 7 设计，确认输入、优先级、追溯、去重、指纹、过期和质量样本。设计获得用户明确确认前，不实现新 Prompt、Schema、Service、Adapter，也不调用真实 DeepSeek。
