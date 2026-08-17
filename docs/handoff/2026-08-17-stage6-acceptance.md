# 阶段 6 全量验收记录

> 日期：2026-08-17  
> 分支：`1lcj`  
> 验收结论：技术集成验收通过；真实浏览器人工验收待完成，因此阶段 6 尚未正式完成。

## 1. 验收范围

本次验收按阶段 6 专项设计检查结构化岗位管理的完整链路：

`前端 -> API -> Schema -> Service -> Model -> PostgreSQL`

覆盖一键启动、数据库迁移、全量自动化回归、真实 PostgreSQL/API 状态机、安全删除、旧数据保护、下游开放岗位读取边界和页面可访问性。浏览器真实点击与视觉验收原计划同时执行，但受控浏览器运行时没有可用实例，单独保留为最后的人工验收项。

## 2. 环境与启动验收

- 使用 `scripts/start_project.ps1 -NoBrowser` 完成真实启动。
- Docker Desktop、PostgreSQL、Redis、Chroma、FastAPI 和 Vite 均就绪。
- `GET /api/health` 成功。
- `/stage3/jobs` 返回 HTTP 200。
- 运行中 OpenAPI 包含 `/api/v2/jobs` 以及 open、close、reopen 动作。
- Alembic 当前 revision：`c8e1a6f4d205 (head)`。
- Alembic 自动迁移检查：`No new upgrade operations detected`。

这部分证明启动脚本能够把本项目依赖的服务真正拉起，并且运行中的后端确实包含阶段 6 接口；它不证明按钮布局和浏览器交互正确。

## 3. 自动化回归

| 验收项 | 结果 |
| --- | --- |
| 后端全量测试 | 418/418 通过 |
| 前端脚本测试 | 9/9 通过 |
| 前端生产构建 | 通过，转换 3922 个模块 |

前端 9 项包括简历结构化 Service、状态、草稿合并、经历导入、补充信息、信息识别文案、岗位 Service、岗位 UI 和下游岗位读取边界。自动化结果证明代码规则和编译边界稳定，但不替代真实浏览器视觉验收。

## 4. 真实 PostgreSQL 与 API 集成验收

验收使用独立命名的 `S6-Acceptance-*` 岗位和候选人数据，直接经过真实 FastAPI、SQLAlchemy Model 和 PostgreSQL，不使用 Mock 数据库。

| 场景 | 实际结果 |
| --- | --- |
| 创建不完整草稿 | 成功；保持 `draft`，requirements 为完整空 v1 |
| 不完整草稿开放 | 失败；返回 9 个缺失字段，状态未被部分修改 |
| 补齐后开放 | 成功；进入 `open` 列表 |
| 开放岗位非法编辑 | 失败；数据库旧值保留，事务回滚 |
| 开放岗位合法编辑 | 成功；刷新读取后修改仍存在 |
| 关闭岗位 | 成功；退出 `status=open` 查询结果 |
| 不完整关闭岗位重新开放 | 失败；修复完整性后重新开放成功 |
| 删除开放岗位 | 返回 `409`，岗位保留 |
| 删除无关联草稿/关闭岗位 | 成功 |
| 删除有关联岗位 | Candidate、Resume、ScreeningResult、Report 均阻止删除，并返回准确关联数量 |

关键运行输出：

- `INCOMPLETE_OPEN_ROLLBACK_OK fields=9`
- `OPEN_EDIT_ROLLBACK_OK`
- `OPEN_EDIT_PERSISTED_OK`
- `CLOSE_REOPEN_BOUNDARY_OK`
- `SAFE_DELETE_OK`
- `REFERENCE_DELETE_BLOCKED_OK {"candidates":1,"reports":1,"resumes":1,"screening_results":1}`
- `POSTGRES_JOB_API_ACCEPTANCE_OK`
- `ACCEPTANCE_CLEANUP_OK`

## 5. 旧数据与清理核对

验收前后的表计数完全一致：

| 表 | 验收前 | 验收后 |
| --- | ---: | ---: |
| Candidate | 30 | 30 |
| Job | 8 | 8 |
| Resume | 0 | 0 |
| ScreeningResult | 29 | 29 |
| Report | 0 | 0 |

验收结束后没有残留 `S6-Acceptance-*` 数据。旧数据保护核对结果：

- 岗位 ID 仍为 1—8，岗位身份摘要保持稳定。
- 8 条旧岗位的描述与 legacy snapshot 均存在。
- Candidate 和 ScreeningResult 的岗位关联分别仍为 30、29 条。
- `ck_jobs_headcount_range`、`ck_jobs_status_allowed` 两个 CHECK 约束存在。
- 当前 8 条迁移岗位状态均为 `draft`，符合阶段 6 迁移设计。

## 6. 页面可访问性与未完成项

以下页面均返回 HTTP 200：

- `/stage3/jobs`
- `/stage3/screening`
- `/stage3/apply`
- `/stage3/candidates/new`

但本次受控浏览器运行时返回的可用浏览器列表为空，因此没有执行或宣称完成以下项目：

- 在岗位管理页真实点击创建草稿、开放失败、补齐开放、编辑、刷新持久化、关闭、重新开放和安全删除。
- 在 AI 初筛、投递预览和新增候选人页面视觉确认只有开放岗位可供新选择，关闭岗位历史信息仍可展示。
- 1440 像素桌面布局截图与交互检查。
- 严格 390 像素窄屏布局、抽屉、表格滚动和无整页横向溢出检查。
- 用户最终确认。

HTTP 200 只能证明路由可访问，不能证明真实交互和视觉布局正确。以上项目完成后，才能把阶段 6 标记为正式完成并讨论是否进入阶段 7。
