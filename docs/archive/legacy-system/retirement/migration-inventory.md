# 架构重建迁移清单

> 日期：2026-07-15  
> 依据：`docs/specs/2026-07-15-hr-agent-platform-design.md` 第 9 节，以及当前仓库文件扫描结果。
>
> **状态：已停止执行。** 用户于 2026-08-18 明确放弃旧代码和旧演示数据；本文只保留为历史决策记录，不能再作为待迁移任务清单。当前退役边界以 `docs/specs/2026-08-18-legacy-system-retirement-decision.md` 为准。

## 当前判断

现有项目是一套旧版可演示系统，已经包含候选人管理、简历上传、AI 初筛、投递页、Dashboard 和 Mock/真实 LLM 双模能力。新目标不是在旧系统上继续小修小补，而是在保留有价值资产的基础上重建分层架构。

迁移原则：

- 能直接提供业务价值的资产迁移。
- 和新架构冲突的模块重写。
- 复杂但有参考价值的旧逻辑保留为 fallback 或规则参考。
- 历史文档保留，但新开发以 `docs/specs/2026-07-15-hr-agent-platform-design.md` 为准。

## 可迁移资产

| 现有文件 | 新位置 | 处理方式 | 原因 |
| --- | --- | --- | --- |
| `backend/app/prompts/resume_extraction.txt` | `backend/app/agents/prompts/resume_extraction.py` 或 `.md` | 优化后迁移 | 简历提取 Prompt 是核心资产，但要改成更严格的 JSON/schema 输出 |
| `backend/app/prompts/candidate_summary.txt` | `backend/app/agents/prompts/candidate_summary.py` 或 `.md` | 优化后迁移 | 候选人摘要可用于详情页和报告 |
| `backend/app/prompts/auto_tagging.txt` | `backend/app/agents/prompts/` | 优化后迁移 | 自动标签可作为候选人画像能力 |
| `backend/app/prompts/followup_suggestion.txt` | `backend/app/agents/prompts/` | 延后迁移 | 跟进建议不是 MVP 主链路，可在后续迭代使用 |
| `backend/app/prompts/copilot_system.txt` | `backend/app/agents/prompts/smart_assistant.py` 或 `.md` | 优化后迁移 | 智能助手需要系统提示，但要适配 LangGraph 意图路由 |
| `prompts/*.md` | `backend/app/agents/prompts/` | 作为更完整版本参考 | 根目录 Prompt 文档比 app 内 txt 更长，适合做重写参考 |
| `backend/app/services/file_parser.py` | `backend/app/core/file_parser.py` | 迁移并增强 | PDF/DOCX/TXT 解析是简历入口能力 |
| `backend/app/services/dedup_service.py` | `backend/app/services/dedup_service.py` | 迁移 | 手机、邮箱、姓名学校岗位去重逻辑有直接价值 |
| `frontend/src/pages/ApplyForm.tsx` | `frontend/src/pages/Apply/` | 迁移并 UI 升级 | 候选人投递页是公开入口，业务价值明确 |
| `frontend/src/pages/ApplyForm.css` | `frontend/src/pages/Apply/` 或主题样式 | 部分迁移 | 样式需改成 Ant Design 5 主题体系 |
| `sample_data/*` | `sample_data/` 或 `backend/app/seed/` | 保留并整理 | 用于演示和测试上传解析 |

## 参考但需重写

| 现有文件 | 新实现 | 处理方式 | 原因 |
| --- | --- | --- | --- |
| `backend/app/services/ai_service.py` | `backend/app/agents/graphs/*` + `backend/app/core/llm.py` | 重写 | 旧服务直接调用 AI，新架构需要 LangGraph 工作流编排 |
| `backend/app/services/mock_llm.py` | 各 workflow fallback / rule helpers | 拆分重写 | 文件较大，职责混杂，但规则评分逻辑值得参考 |
| `backend/app/routers/ai.py` | `backend/app/api/chat.py`、`backend/app/api/reports.py` 等 | 重写 | API 要按新业务边界拆分 |
| `backend/app/routers/screening.py` | `backend/app/api/screening.py` | 重写 | 旧初筛逻辑要接入 `jd_match` graph |
| `backend/app/models/candidate.py` | 新 SQLAlchemy 2.0 models | 重写 | 新版要支持 PostgreSQL、JSONB、候选人关联表 |
| `backend/app/database.py` | `backend/app/core/database.py` | 重写 | 旧版偏 SQLite，新版目标 PostgreSQL + Alembic |
| `frontend/src/pages/Dashboard.tsx` | `frontend/src/pages/Dashboard/` | 重写为新工作台 | 旧版可参考信息布局，但视觉和交互要升级 |
| `frontend/src/pages/AIScreeningCenter.tsx` | `frontend/src/pages/Screening/Center/` | 重写 | 新版筛选中心要展示 LangGraph 结果和报告入口 |
| `frontend/src/pages/CandidateList.tsx` | `frontend/src/pages/Resume/List/` 或 `Candidates/` | 重写 | 新版要围绕简历管理和结构化信息展示 |
| `frontend/src/api/index.ts` | `frontend/src/services/` | 重写/迁移 | API 封装应按模块拆分 |

## 暂时保留为历史参考

| 文件或目录 | 说明 |
| --- | --- |
| `PROJECT_STATE.md` 旧内容 | 记录旧版演示系统完成度，不能作为新架构完成度 |
| `HANDOFF.md` | 旧版交接资料，后续可抽取有用内容 |
| `TODO_NEXT.md` | 旧版后续建议，和新实施计划可能不一致 |
| `docs/业务方案.md`、`docs/系统架构说明.md` 等 | 旧版答辩/演示文档，可作为业务背景 |
| `scripts/reset_demo_data.py`、`scripts/ensure_demo_data.py` | 旧演示数据脚本，迁移 PostgreSQL 后需要重写 |
| `start_backend.bat`、`start_frontend.bat` | 本地启动脚本，等新架构稳定后再更新 |

## 需要新增的新架构目录

后端：

```text
backend/app/
  api/
  core/
  agents/
    graphs/
    nodes/
    states/
    prompts/
  rag/
  models/
  schemas/
  services/
```

前端：

```text
frontend/src/
  components/
  pages/
    Dashboard/
    Resume/
    Screening/
    Jobs/
    Apply/
  services/
  stores/
  theme/
  types/
  hooks/
  utils/
```

## 第一批迁移优先级

1. `file_parser.py`：没有文本提取就没有后续 AI。
2. Prompt 模板：先迁移简历提取和 JD 匹配相关 Prompt。
3. `dedup_service.py`：候选人入库前需要去重。
4. `mock_llm.py` 中的评分规则：只抽规则，不整文件搬迁。
5. `ApplyForm.tsx`：等后台投递 API 稳定后迁移。

## 当前风险

- 旧版依赖中还没有 `langgraph`、`asyncpg`、`alembic`、`chromadb`、`redis` 等新架构关键依赖。
- 当前 `docker-compose.yml` 需要按 PostgreSQL/Redis/Chroma 重写或扩展。
- 旧版 `PROJECT_STATE.md` 内容非常完整，但会误导后续开发者认为新架构已经完成。
- 工作区已有未提交改动，后续每次改动前都要注意不要覆盖用户现有修改。
