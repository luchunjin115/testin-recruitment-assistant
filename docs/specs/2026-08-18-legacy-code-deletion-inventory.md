# 旧版代码删除清单

> 日期：2026-08-18
>
> 状态：第 4A 步只读引用扫描与第 4B 步物理删除均已完成
>
> 依据：`2026-08-18-legacy-system-retirement-decision.md`

## 1. 判断方法

本清单从当前唯一运行入口反向核对调用链：

- 前端入口：`frontend/src/App.tsx`，只加载 `frontend/src/stage3/`、`frontend/src/services/http.ts` 和 `frontend/src/theme/`。
- 后端入口：`backend/app/main.py`，只挂载 `backend/app/api/`，业务实现进入 `core/`、`models/rebuilt/`、`schemas/rebuilt/`、`services/rebuilt/`、`adapters/rebuilt/` 和 `prompts/rebuilt/`。
- 启动入口：`scripts/start_project.ps1` 与 `launch/start_project.bat`，使用 PostgreSQL、Alembic、当前 FastAPI 和 Vite。
- 测试入口：后端 `unittest discover` 与前端 `package.json` 中 14 个当前脚本。

扫描结果：下列 70 个文件没有新版调用者；它们只在旧系统内部互相引用、被一次性旧迁移工具引用，或仅作为旧系统说明存在。

## 2. 第 4B 步精确删除目标

### 2.1 旧后端运行模块（36 个）

旧同步 SQLite 配置、数据库与造数：

- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/seed_data.py`

旧 Router 目录全部 10 个文件：

- `backend/app/routers/__init__.py`
- `backend/app/routers/actions.py`
- `backend/app/routers/ai.py`
- `backend/app/routers/apply.py`
- `backend/app/routers/candidates.py`
- `backend/app/routers/dashboard.py`
- `backend/app/routers/jobs.py`
- `backend/app/routers/resume.py`
- `backend/app/routers/screening.py`
- `backend/app/routers/sync.py`

旧 SQLite Model：

- `backend/app/models/activity_log.py`
- `backend/app/models/candidate.py`
- `backend/app/models/job.py`
- `backend/app/models/stage_change_log.py`

旧 Schema：

- `backend/app/schemas/candidate.py`
- `backend/app/schemas/dashboard.py`
- `backend/app/schemas/job.py`

旧 Service 与已取消的一次性迁移 Service：

- `backend/app/services/ai_service.py`
- `backend/app/services/candidate_service.py`
- `backend/app/services/dedup_service.py`
- `backend/app/services/file_parser.py`
- `backend/app/services/followup_service.py`
- `backend/app/services/job_service.py`
- `backend/app/services/mock_llm.py`
- `backend/app/services/stage_service.py`
- `backend/app/services/sync_adapter.py`
- `backend/app/services/rebuilt/legacy_candidate_import.py`

只被旧 AI Service 使用的 Prompt：

- `backend/app/prompts/auto_tagging.txt`
- `backend/app/prompts/candidate_summary.txt`
- `backend/app/prompts/copilot_system.txt`
- `backend/app/prompts/followup_suggestion.txt`
- `backend/app/prompts/resume_extraction.txt`
- `backend/app/prompts/screening.txt`

### 2.2 旧脚本与测试（7 个）

- `scripts/ensure_demo_data.py`
- `scripts/evaluate_screening_prompt.py`
- `scripts/export_csv.py`
- `scripts/import_legacy_candidates.py`
- `scripts/init_db.py`
- `scripts/reset_demo_data.py`
- `backend/tests/services/rebuilt/test_legacy_candidate_import.py`

### 2.3 旧前端（22 个）

旧 API 与旧公共类型/常量：

- `frontend/src/api/index.ts`
- `frontend/src/types/index.ts`
- `frontend/src/utils/constants.ts`

旧组件目录全部 9 个文件：

- `frontend/src/components/AppLayout.tsx`
- `frontend/src/components/ChannelPieChart.tsx`
- `frontend/src/components/CopilotChat.tsx`
- `frontend/src/components/DailySummary.tsx`
- `frontend/src/components/FollowUpAlerts.tsx`
- `frontend/src/components/FunnelChart.tsx`
- `frontend/src/components/RecentLogs.tsx`
- `frontend/src/components/StageTag.tsx`
- `frontend/src/components/StatsCards.tsx`

旧页面目录全部 10 个文件：

- `frontend/src/pages/AIScreeningCenter.tsx`
- `frontend/src/pages/ApplyForm.css`
- `frontend/src/pages/ApplyForm.tsx`
- `frontend/src/pages/CandidateDetail.tsx`
- `frontend/src/pages/CandidateForm.tsx`
- `frontend/src/pages/CandidateList.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/JobManagement.tsx`
- `frontend/src/pages/ResumeUpload.tsx`
- `frontend/src/pages/Stage3Preview.tsx`

### 2.4 只描述旧 Prompt 系统的根目录说明（5 个）

这些文件直接指向本清单中待删除的旧 `.txt` Prompt，并描述旧 `MockLLM` 回退，不是新版 Prompt 工程文档：

- `prompts/auto_tagging.md`
- `prompts/candidate_summary.md`
- `prompts/copilot_system.md`
- `prompts/followup_suggestion.md`
- `prompts/resume_extraction.md`

## 3. 删除时同步修改，但不删除

- `frontend/package.json` 与 `frontend/package-lock.json`：移除只被旧前端使用的直接依赖 `dayjs`、`recharts`。
- `frontend/tests/new-runtime-entry.test.mjs`：从“入口不导入旧文件”升级为“旧文件物理不存在”的回归保护。
- `backend/app/models/__init__.py`：删除“旧 SQLite Model 仍等待删除”的过渡说明，继续保留父 package，避免影响 `app.models.rebuilt` 导入。
- 新增后端旧文件物理不存在回归测试，固定 Router、SQLite Model/Schema/Service、造数脚本和一次性迁移工具不得重新出现。
- `.gitignore`：移除只为旧 `backend/uploads/` 和旧 recovery data 目录保留的规则；继续忽略新版 `backend/storage/`、通用本地数据库和构建产物。
- `PROJECT_STATE.md`、实施计划与退役决策：记录实际删除数量、验证结果和下一步。

## 4. 明确保留

- `backend/app/api/`、`core/`、`models/rebuilt/`、`schemas/rebuilt/`、`services/rebuilt/`（除 `legacy_candidate_import.py`）、`adapters/rebuilt/`、`prompts/rebuilt/`。
- `backend/app/models/__init__.py`、`schemas/__init__.py`、`services/__init__.py` 等父 package 文件。
- `backend/migrations/` 全部历史，包括已执行的 `e7` 和当前 head `f8`。
- `backend/scripts/validate_*_live.py`，用于新版真实模型与评分链验证。
- `scripts/start_project.ps1`、`launch/start_project.bat`、`launch/start_backend.bat`、`launch/start_frontend.bat`；它们当前调用新版 `run.py`、Alembic 和 Vite，不调用 SQLite 或旧 Router。
- `frontend/src/stage3/`、`frontend/src/services/http.ts`、`frontend/src/theme/`、`App.tsx`、`App.css`、`main.tsx`、`index.css`。
- `sample_data/` 受控测试样例、`docs/Prompt工程与效果验证.md` 及权威设计文档。
- `agents/`、`rag/` 等后续阶段新版骨架。

## 5. 延后到第 5 步的文档收口

`README.md`、`HANDOFF.md`、`TODO_NEXT.md`、`使用说明.md` 和历史 `PROJECT_STATE.md` 段落仍记录过旧系统。它们不参与运行，也不阻塞第 4B 步删除；第 5 步命名与交付收口时统一改写当前 README/使用说明，并明确区分历史记录与现行操作，避免本步把代码删除和大规模文档重写混在一起。

## 6. 第 4B 步验证标准

- 上述 70 个目标全部不存在，保留清单全部存在。
- 新版前后端 import/reference 扫描没有指向已删除路径。
- 后端全量测试、前端 14 个脚本、TypeScript/Vite 生产构建通过。
- FastAPI OpenAPI 仍只包含 `/api/health` 与 `/api/v2/*`。
- Alembic 仍位于 `f8c2d0e5b317`，`alembic check` 无结构差异，业务表保持 0 行。
- PostgreSQL、Redis、Chroma、新版私有存储和 `sample_data/` 不被删除或改写。

## 7. 第 4B 步实际结果

- 清单中的 70 个目标全部删除，旧空目录与旧 Python 字节码缓存同步清理；明确保留项未删除。
- 后端新增旧路径防回流测试后，全量 593 项测试通过；前端扩展物理路径防回流测试后，14 个测试脚本全部通过。
- 前端生产构建通过，Vite 转换 3116 个模块；OpenAPI 的 46 个 path 全部属于 `/api/health` 或 `/api/v2/*`。
- Alembic 位于 `f8c2d0e5b317 (head)`，`alembic check` 无差异；PostgreSQL 12 张业务表仍为 0 行。
- Redis 仍为 0 个键，Chroma 仍为 0 个 collection，`backend/storage` 仍为空，`sample_data/` 4 个受控文件保留。
- 下一步是第 5 步命名与交付收口，不在本步混入 `/stage3`、`rebuilt`、`/api/v2` 重命名和大规模 README 改写。
