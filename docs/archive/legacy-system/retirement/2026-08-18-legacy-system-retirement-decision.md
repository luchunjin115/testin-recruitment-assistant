# 旧版系统退役与演示数据放弃决策

> 归档位置说明：本决策已经执行完成，现只用于解释当前为何不保留旧系统兼容边界。

> 日期：2026-08-18
>
> 状态：已获用户明确确认，并于 2026-08-18 全部执行完成
>
> 影响范围：总体架构、阶段 7 数据模型与完成标准、前后端运行入口、开发数据库与演示数据

## 1. 决策背景

仓库当前同时保留两套实现：

- 旧版 React + FastAPI + SQLite + Mock LLM 演示系统。
- 新版 React + FastAPI + PostgreSQL + DeepSeek 主链路。

早期采用并行运行和逐步迁移，是为了在新版尚未形成完整主链路时保护旧演示能力。阶段 4—6 已完成，阶段 7 的 Application 与 AI 初筛主链已进入前端接入阶段；继续维护旧系统会让前端路由、FastAPI 入口、配置、测试和数据约束长期承担两套语义。

用户于 2026-08-18 明确确认：不再保留旧代码，也不再保留或迁移旧演示数据。

## 2. 正式决策

项目从“迁移旧系统”调整为“由新版系统直接替代旧系统”。

1. 旧系统立即冻结，不再增加功能、修复业务缺陷或补充回归测试。
2. 已经在新版重新实现并验证的能力继续使用，不再为了保留文件历史而迁移旧实现。
3. 旧 SQLite 数据、由旧系统导入 PostgreSQL 的演示 Candidate/Job/ScreeningResult、旧上传附件和自动造数逻辑不再属于产品数据，不要求无损迁移。
4. Git 历史承担旧实现的追溯职责；旧代码不需要继续留在运行入口或最终工作树中。
5. 新版 PostgreSQL 只保留符合当前 Schema、能够通过当前业务入口创建或由受控新版 seed 生成的数据。

## 3. 范围边界

### 3.1 退役对象

- 前端旧页面、旧 Layout、旧路由和只服务于旧页面的 API 封装。
- 后端 `routers/` 下的旧 `/api` 业务路由，以及只被这些路由使用的同步 Service、旧 Schema、旧 SQLite Model、Mock LLM 和启动造数逻辑。
- `backend/recruit.db`、旧演示上传附件、`reset_demo_data.py`、`ensure_demo_data.py` 和一次性旧候选人导入工具。
- 阶段 7 为旧演示数据设计的 `legacy_migration` Application 来源、`legacy_stage`、无当前 Resume 例外、旧 ScreeningResult 兼容响应和正式旧数据迁移步骤。

删除前仍须通过引用扫描确认每个具体文件不再被新版代码使用。文件解析、Prompt 或去重等能力如果已被新版真实调用，应保留新版实现，不能按目录名称机械删除。

### 3.2 继续维护的新版对象

- `frontend/src/stage3/` 当前承载的是新版界面。目录名虽然带 `stage3`，但不属于本决策中的旧系统。
- `backend/app/api/`、`backend/app/models/rebuilt/`、`backend/app/schemas/rebuilt/`、`backend/app/services/rebuilt/`、`backend/app/prompts/rebuilt/` 和 `/api/v2` 当前承载新版主链。
- Alembic 历史用于构建新版 PostgreSQL Schema，不因“不要旧数据”而整体删除。
- `legacy_requirements` 等字段必须按真实职责单独判断；如果它是 PostgreSQL Schema 升级或回滚保护，而不是旧 SQLite 产品兼容，不能在本轮机械删除。

## 4. 新版数据合同调整

后续代码清理应把所有正式 Application 收敛到同一合同：

- `current_resume_id` 必填，不再允许 legacy 记录为空。
- `source` 只保留真实新版入口需要的值，不再包含 `legacy_migration`。
- 删除 `legacy_stage` 及其前后端展示、校验和数据库字段。
- 不再把无 Application 的旧 ScreeningResult 暴露为新版兼容结果。
- 不再执行旧 Candidate/ScreeningResult 到 Application 的数据推断或状态映射。
- 阶段 7 的测试数据必须由新版 Model/Service/API 创建，不能依赖旧数据库快照。

2026-08-18 第 3B-1 步只读核对确认，正式开发库实际已升级到阶段 7 revision `e7b1c9d4a206`，旧文档中的“尚未升级”判断不再成立。`e7` 必须作为已执行历史保留；legacy 合同收口由新的 `f8c2d0e5b317` migration 承担。涉及重建数据库、删除附件或执行新 migration 的操作必须依据 `PROJECT_STATE.md` 中的精确目标单独验证，不能使用宽泛目录或未核对的数据库删除命令。

## 5. 分步执行顺序

1. **文档收口（已完成）**：同步总设计、路线图、实施计划、阶段 7 专项设计和项目状态。
2. **运行入口切换（已完成）**：新版前端成为唯一产品路由；FastAPI 只挂载新版业务 API，移除旧启动造数调用。旧文件和旧数据未在本步删除。
3. **Schema 与数据收口（已完成）**：第 3A 步已移除运行代码中的阶段 7 legacy 合同；第 3B-1 步已只读列出精确目标并确认数据库位于已部署的 `e7`；第 3B-2 步已删除旧 SQLite、旧 PostgreSQL 业务数据和旧附件，并从空库成功升级到 `f8c2d0e5b317`。
4. **旧文件删除（已完成）**：第 4A 步在 `2026-08-18-legacy-code-deletion-inventory.md` 核定 70 个待删除文件及保留边界；第 4B 步已按清单删除旧页面、Router、Model、Schema、Service、脚本、测试和旧 Prompt 说明，并通过全量验证。
5. **命名与交付收口（已完成）**：浏览器工作台改为 `/app/*`，公开页改为 `/apply`；前端改为 `features/recruitment` 与 `Recruitment*`，后端代码移出 `rebuilt/`，存储配置改为 `STORAGE_DIR`。正式版本化接口 `/api/v2` 保留；README/使用说明已重写，旧 HANDOFF/TODO 已删除。

## 6. 验收标准

- 前端只有新版产品入口；旧 URL 不再加载旧页面。
- FastAPI 启动不导入旧 Router、不连接 SQLite、不自动生成旧演示数据。
- OpenAPI 不再暴露旧业务 API。
- Application Schema、Model 和 PostgreSQL 约束不存在 legacy 数据例外。
- 新版前端构建、后端全量测试、Alembic 空库升级和真实 PostgreSQL 主链验证通过。
- 新版上传、结构化、岗位、Application 和 AI 初筛流程不依赖旧文件或旧数据。
- 删除清单、数据清理目标和验证结果记录在 `PROJECT_STATE.md`。

## 7. 本次不做

本文档只确认退役方向，不直接删除代码、数据库、上传附件或 Git 历史，也不提前执行 `/stage3`、`rebuilt`、`/api/v2` 的命名重构。
