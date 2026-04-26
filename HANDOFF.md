# 交接说明

> 最后更新：2026-04-26（第二十七轮，新电脑交付启动与演示数据自动兜底后）

---

## 一、项目概述

这是 **Testin 云测面试题** —— 一个基于 AI 技术的智能招聘管理系统（"Testin云测招聘助手"）。

核心目标：解决 HR 手动录入招聘数据效率低、数据失真、跟进遗漏、批量简历初筛成本高的痛点，通过 AI 实现简历自动解析、候选人智能摘要、自动标签、批量初筛、跟进建议、HR Copilot 对话等功能。

技术栈：FastAPI + React 18 + TypeScript + Ant Design + SQLite + Docker。

---

## 二、当前完成度

**全部 10 个 Phase 已完成 + 新电脑交付启动与演示数据自动兜底已完成 + AI 初筛中心移除备选逻辑已完成 + 候选人列表正式流程备选已完成 + 候选人列表范围筛选简化已完成 + 岗位一致 Demo 数据重置脚本已完成 + 招聘漏斗初筛流转改造已完成 + AI 初筛中心入口处理池已完成 + Dashboard 初筛状态统计已完成 + AI 初筛中心当前筛选统计彻底统一已完成 + AI 初筛统计口径统一已完成 + 演示数据与详情信息增强已完成 + 面试反馈 AI 总结已完成 + 最近新增候选人高亮已完成 + 超时未跟进提醒已完成 + 候选人批量处理已完成 + 候选人列表岗位筛选增强已完成 + Dashboard 岗位分布已完成 + AI 批量初筛中心已完成 + HR 统一新增候选人页已完成**，包括：
- ✅ 后端全栈（FastAPI + 7 组 API 路由 + 7 个服务 + ORM + 种子数据）
- ✅ 前端全栈（React + 6 个页面 + 9 个组件 + 路由）
- ✅ Docker 配置（Dockerfile × 2 + nginx.conf + docker-compose.yml）
- ✅ 文档（README + 5 篇项目文档 + 5 篇 Prompt 文档）
- ✅ 脚本（数据库初始化 + CSV 导出）
- ✅ Python 3.9 兼容性修复
- ✅ 前端 UI 联调验证 + Bug 修复（8 项，详见第八节）
- ✅ Dashboard 最近操作日志同步修复（状态变更 -> 日志写入 -> Dashboard 展示链路打通）
- ✅ 在线投递简历附件详情可见（附件元数据保存 + 候选人详情页查看/下载）
- ✅ `/apply` 简历实际上传修复（前端文件正确进入 FormData）
- ✅ HR 统一新增候选人页（手动录入 + 简历上传合并，`/upload` 兼容跳转 `/form`）
- ✅ AI 批量初筛中心（`/ai-screening`，批量初筛、单人重新初筛、推荐等级筛选、匹配度排序、Dashboard 统计、列表同步展示）
- ✅ 招聘漏斗初筛流转（`screening_status=pending|passed|backup|rejected`，新投递先进 AI 初筛中心，通过初筛后进入候选人列表正式流程）
- ✅ 岗位一致 Demo 数据重置脚本（`python scripts/reset_demo_data.py`，保留岗位管理，清空候选人相关数据，生成 30 条岗位一致候选人和 21 份 TXT 简历）
- ✅ 新电脑交付启动兜底（`scripts/ensure_demo_data.py` 后端启动时执行，候选人表为空才生成完整 Demo；已有候选人不清库）
- ✅ 统一本地路径（默认数据库 `backend/recruit.db`，默认上传目录 `backend/uploads`；相对环境变量解析到 `backend/`）
- ✅ Windows 一键启动脚本（`start_backend.bat`、`start_frontend.bat`；前端使用 Vite，不使用 Python `http.server`）
- ✅ AI 初筛中心 HR 决策按钮（通过初筛、初筛淘汰、重新初筛、查看详情；淘汰要求填写原因并保留主记录；备选已移至候选人列表正式流程）
- ✅ 候选人列表范围筛选简化（只保留正式流程候选人、备选候选人、淘汰候选人，移除全部/待初筛视图）
- ✅ Dashboard 初筛状态统计（总投递、待初筛、通过初筛、正式流程备选、初筛淘汰、正式流程候选人数分开展示）
- ✅ 候选人列表岗位筛选增强（动态岗位选项、岗位/阶段/来源/关键词组合筛选、重置筛选、Dashboard 岗位分布）
- ✅ 候选人批量处理（批量选择、批量标记备选、批量标记待约面、批量淘汰确认、批量导出 CSV、批量生成 AI 跟进建议）
- ✅ 最近新增候选人高亮（今日新增/新投递标签、今日新增筛选、投递时间倒序、Dashboard 最近新增统计和今日新增 Top 5）
- ✅ 面试反馈 AI 总结（详情页录入面试反馈，AI 生成技术/沟通/匹配度/风险点/推荐结论/下一步建议，并保存日志）
- ✅ 演示数据与详情信息增强（新增在线投递候选人、补全岗位描述/要求、详情页展示投递与 AI 初筛信息、AI 初筛中心列名改为“匹配依据”）
- ✅ AI 初筛统计口径统一（Dashboard、候选人列表、AI 初筛中心总人数一致，高/中/低/未初筛加总等于总人数）
- ✅ AI 初筛中心当前筛选统计彻底统一（蓝色统计框、表格当前人数、批量初筛范围均基于当前表格 items）

**已验证可运行**：后端 `compileall` 通过；`python scripts/reset_demo_data.py` 已运行成功；当前 Demo 数据为总候选人 30、AI 初筛中心默认待初筛 11 且不含备选、候选人列表正式流程默认 14、备选视图 3、淘汰视图 2、简历附件 21、岗位不一致 0、今日新增 5、最近 3 天 10、本周 20、历史 10；本地 SQLite 已执行迁移并补齐 `screening_status`；候选人列表正式流程人数与 Dashboard 正式流程人数一致；AI 初筛待处理池只返回 pending；AI 初筛全部/已初筛/未初筛/时间筛选统计闭合，AI 初筛统计与 Dashboard 总数一致、演示候选人补充、默认岗位描述补齐、面试反馈 AI 总结接口、总结保存、操作日志写入、候选人筛选接口、今日新增筛选、默认投递时间倒序、Dashboard 最近新增统计、动态筛选选项、Dashboard 岗位分布、批量状态处理、批量导出 CSV、批量跟进建议已用 FastAPI TestClient 验证；前端 TypeScript 生产构建（`npm.cmd run build`）已通过；新电脑交付路径已统一为 `backend/recruit.db` 和 `backend/uploads`，后端启动会按需执行 `ensure_demo_data()`。
**尚未验证**：Docker 端到端部署。

---

## 三、新对话接手时应先读的文件

按顺序阅读：

1. **`HANDOFF.md`**（本文件）— 快速了解全局
2. **`PROJECT_STATE.md`** — 详细的功能清单、目录结构、已知问题
3. **`TODO_NEXT.md`** — 后续优化方向和优先级
4. **`README.md`** — 项目说明和启动方式
5. **`docs/演示脚本.md`** — 5 分钟演示流程
6. **`docs/答辩讲稿.md`** — 5 分钟答辩结构

如果需要深入代码：
- `backend/app/main.py` — 后端入口，理解路由结构
- `backend/app/services/ai_service.py` — AI 双模架构核心
- `frontend/src/App.tsx` — 前端路由结构
- `frontend/src/api/index.ts` — 前端 API 调用封装

---

## 四、继续开发应遵循的原则

1. **不要重新规划项目**。所有 Phase 已完成，只需要修 Bug 和优化体验
2. **新增业务需求优先小步扩展**。沿用现有模型、路由、服务和页面风格，避免重建项目骨架
3. **不要重构已有模块**。代码结构稳定，改动风险大于收益
4. **Mock 模式优先**。确保 `LLM_PROVIDER=mock` 下所有功能正常，这是演示的基础
5. **先验证再改动**。修改前先启动服务确认现状，改完再验证效果
6. **Python 3.9 兼容**。类型注解必须用 `typing` 模块（`List`, `Dict`, `Optional`, `Tuple`），不能用 `list[str]`、`dict | None` 等 3.10+ 语法

---

## 五、不要重复做的事情

以下工作已完成，**不要重做**：

- ❌ 不要重新生成 Dockerfile、nginx.conf、docker-compose.yml
- ❌ 不要重新写文档（docs/ 下 5 个文件、prompts/ 下 5 个文件、README.md）
- ❌ 不要重新创建脚本（scripts/init_db.py、scripts/export_csv.py）
- ❌ 不要修改种子数据（backend/app/seed_data.py）
- ❌ 不要修改 Prompt 模板（backend/app/prompts/*.txt）
- ❌ 不要修改数据库模型（除非发现 Bug）
- ❌ 不要重新做 Python 3.9 兼容性修复（已完成）
- ❌ 不要重新做前端 UI 联调 Bug 修复（已完成，详见第八节）

---

## 六、启动命令

### 手动启动（开发模式）

```bash
# 先启动后端
cd backend
pip install -r requirements.txt
python run.py
# → http://localhost:8000/docs

# 再启动前端（新终端）
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

前端必须使用 Vite 启动，不要使用 `python -m http.server`。Vite 代理配置在 `frontend/vite.config.ts`，`/api` 会转发到 `http://localhost:8000`。

### Windows 双击脚本

```bash
start_backend.bat
start_frontend.bat
# 前端：http://localhost:5173
# 后端：http://localhost:8000/docs
```

首次启动后端时，如果候选人表为空，会自动生成完整演示数据；已有候选人时不会清空数据库。

### Docker 启动

```bash
docker-compose up --build
# 前端：http://localhost:3000
# 后端：http://localhost:8000/docs
```

---

## 七、演示地址

| 页面 | 开发模式 | Docker 模式 |
|------|---------|------------|
| Dashboard 看板 | http://localhost:5173/ 或 /dashboard | http://localhost:3000/ 或 /dashboard |
| 新增候选人 | http://localhost:5173/form | http://localhost:3000/form |
| /upload 兼容跳转 | http://localhost:5173/upload | http://localhost:3000/upload |
| AI 初筛中心 | http://localhost:5173/ai-screening | http://localhost:3000/ai-screening |
| 候选人列表 | http://localhost:5173/candidates | http://localhost:3000/candidates |
| 候选人详情 | http://localhost:5173/candidates/1 | http://localhost:3000/candidates/1 |
| 投递者在线填写 | http://localhost:5173/apply | http://localhost:3000/apply |
| API 文档 | http://localhost:8000/docs | http://localhost:8000/docs |

---

## 八、历次修改记录

### 第一轮：新建文件

| 文件 | 说明 |
|------|------|
| `backend/Dockerfile` | 后端 Docker 镜像 |
| `frontend/Dockerfile` | 前端多阶段构建镜像 |
| `frontend/nginx.conf` | nginx 配置（SPA + API 反代） |
| `scripts/init_db.py` | 数据库初始化脚本 |
| `scripts/export_csv.py` | CSV 导出脚本 |
| `README.md` | 项目说明文档 |
| `docs/业务方案.md` | 业务方案文档 |
| `docs/Prompt工程与效果验证.md` | Prompt 工程文档 |
| `docs/系统架构说明.md` | 系统架构文档 |
| `docs/演示脚本.md` | 演示流程文档 |
| `docs/答辩讲稿.md` | 答辩讲稿文档 |
| `prompts/*.md` | 5 个 Prompt 设计文档 |
| `HANDOFF.md` | 本交接文件 |

### 第一轮：Python 3.9 兼容 + Docker 修复

| 文件 | 修改内容 |
|------|---------|
| `docker-compose.yml` | 修正 DATABASE_URL 路径（相对→绝对） |
| `backend/app/config.py` | `list[str]` → `List[str]` |
| `backend/app/schemas/candidate.py` | `list[str]`/`list[dict]` → `List[...]` |
| `backend/app/schemas/dashboard.py` | `list[...]` → `List[...]` |
| `backend/app/services/ai_service.py` | `dict \| None` → `Optional[dict]` |
| `backend/app/services/mock_llm.py` | `dict \| None`/`list[...]` → `Optional`/`List` |
| `backend/app/services/candidate_service.py` | `tuple[list[...]]` → `Tuple[List[...]]` |
| `backend/app/services/sync_adapter.py` | `list[dict]` → `List[dict]` |

### 第二轮：前端 UI 联调 + Bug 修复

| 文件 | 修改内容 |
|------|---------|
| `backend/app/services/candidate_service.py` | 修复简历上传手机号/姓名空值导致 422 |
| `frontend/src/pages/CandidateList.tsx` | 修复搜索双重请求 + triggerSync 未 await + 清理未用 imports |
| `frontend/src/pages/CandidateDetail.tsx` | 修复 AI 重新生成无 catch + 跟进建议改为按需 + bodyStyle 适配 |
| `frontend/src/pages/Dashboard.tsx` | 移除 antd v5 不支持的 standalone Spin tip |
| `frontend/src/pages/CandidateForm.tsx` | 删除未使用的 Upload/UploadOutlined imports |
| `frontend/src/components/FollowUpAlerts.tsx` | bodyStyle → styles（antd v5 适配） |
| `frontend/src/components/RecentLogs.tsx` | bodyStyle → styles（antd v5 适配） |

### 第三轮：Dashboard 最近操作日志同步修复

| 文件 | 修改内容 |
|------|---------|
| `backend/app/main.py` | 启动时补跑 `run_migrations()`，确保日志时间修正和历史阶段日志回填生效 |
| `backend/app/database.py` | 修正旧阶段名、清理未来时间日志、将历史 `ActivityLog.stage_changed` 回填到 `StageChangeLog` |
| `backend/app/services/stage_service.py` | 三种来源的状态变更统一写入精确时间戳，ActivityLog 明确带上触发来源和原因 |
| `backend/app/services/candidate_service.py` | Dashboard 最近日志改为合并 `StageChangeLog + ActivityLog`；看板/列表查询前会先触发待执行的系统自动阶段更新 |
| `backend/app/seed_data.py` | 种子数据阶段名统一为当前常量，避免生成未来时间日志，并补充 StageChangeLog 种子记录 |
| `frontend/src/types/index.ts` | `RecentLog` 增加阶段变更结构化字段 |
| `frontend/src/components/RecentLogs.tsx` | Dashboard 最近操作日志支持显示原阶段/新阶段/触发来源/触发原因 |

### 第四轮：在线投递简历附件详情可见

| 文件 | 修改内容 |
|------|---------|
| `backend/app/models/candidate.py` | 候选人模型增加 `resume_filename` / `resume_file_type` / `resume_file_size` / `resume_uploaded_at` |
| `backend/app/database.py` | 启动迁移补齐简历附件元数据字段，并回填旧记录的基础文件名/类型 |
| `backend/app/services/candidate_service.py` | 新增 `attach_resume()`，统一保存简历路径与元数据 |
| `backend/app/routers/apply.py` | `/apply` 上传简历后写入附件元数据，并在重复投递时报错时清理孤儿文件 |
| `backend/app/routers/resume.py` | 简历上传入口同步写入附件原始文件名、类型、大小、上传时间 |
| `backend/app/routers/candidates.py` | 候选人详情接口返回 `resume_filename`、`resume_file_type`、`resume_file_size`、`resume_url`、`resume_uploaded_at` |
| `frontend/src/types/index.ts` | 候选人类型增加简历附件字段 |
| `frontend/src/pages/CandidateDetail.tsx` | 新增“简历附件”区域，支持查看/下载和未上传占位态 |

### 第五轮：修复 /apply 简历未实际上传

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/pages/ApplyForm.tsx` | 修复投递页文件选择后 `originFileObj` 丢失，确保简历真正追加到 `FormData` 并发送到后端 |

### 第六轮：HR 端统一新增候选人页

| 文件 | 修改内容 |
|------|---------|
| `backend/app/routers/candidates.py` | 新增 `POST /api/candidates/hr-create`，统一处理 HR 手动字段、可选简历上传、AI 补全空字段、附件关联 |
| `backend/app/services/candidate_service.py` | HR 后台新增候选人时统一写入更清晰的创建日志，便于 Dashboard 最近操作日志识别 |
| `backend/app/schemas/candidate.py` | 默认来源渠道改为 `HR手动录入`，并补充新的渠道选项 |
| `backend/app/models/candidate.py` | 候选人默认来源渠道与当前统一录入页保持一致 |
| `frontend/src/pages/CandidateForm.tsx` | 改为 HR 统一新增候选人页，支持手动录入 + 简历上传 + AI 补全空字段 |
| `frontend/src/api/index.ts` | 新增 `createHRCandidate()` 多部分表单调用 |
| `frontend/src/components/AppLayout.tsx` | 侧边栏收敛为单一菜单项“新增候选人” |
| `frontend/src/App.tsx` | `/upload` 改为兼容跳转 `/form`，新增 `/dashboard` 别名路由 |
| `frontend/src/utils/constants.ts` | 更新渠道常量，兼容新旧来源值 |

### 第十轮：AI 批量初筛中心

| 文件 | 修改内容 |
|------|---------|
| `backend/app/models/candidate.py` | 增加 `match_score` / `priority_level` / `screening_result` / `screening_reason` / `risk_flags` / `screening_updated_at` |
| `backend/app/database.py` | 启动迁移补齐 AI 初筛字段，并初始化旧数据默认值 |
| `backend/app/services/mock_llm.py` | 增加规则型初筛评分逻辑，避免使用性别、年龄、民族、婚育等敏感信息 |
| `backend/app/services/ai_service.py` | 增加 `screen_candidate()`，真实 LLM 失败自动回退 Mock |
| `backend/app/services/candidate_service.py` | 增加批量初筛、单人重新初筛、初筛结果查询、Dashboard 初筛统计 |
| `backend/app/routers/screening.py` | 新增 `POST /api/screening/run`、`POST /api/screening/run/{candidate_id}`、`GET /api/screening/results` |
| `backend/app/main.py` | 挂载 AI 初筛路由 |
| `frontend/src/pages/AIScreeningCenter.tsx` | 新增 AI 初筛中心页面 |
| `frontend/src/App.tsx` | 新增 `/ai-screening` 路由 |
| `frontend/src/components/AppLayout.tsx` | 侧边栏新增“AI初筛中心”入口 |
| `frontend/src/pages/CandidateList.tsx` | 候选人列表增加 AI 匹配度、推荐等级、初筛建议 |
| `frontend/src/pages/Dashboard.tsx` | Dashboard 增加初筛统计模块 |
| `frontend/src/api/index.ts` / `frontend/src/types/index.ts` / `frontend/src/utils/constants.ts` | 增加初筛 API、类型和推荐等级常量 |

### 第十一轮：候选人列表岗位筛选增强

| 文件 | 修改内容 |
|------|---------|
| `backend/app/services/candidate_service.py` | 候选人列表增加 `target_role` 后端筛选；关键词搜索扩展到专业和技能；新增动态筛选选项和岗位分布统计 |
| `backend/app/routers/candidates.py` | 列表接口新增 `target_role` / `recruiting_stage` / `source_channel` 兼容查询参数；新增 `GET /api/candidates/filter-options` |
| `backend/app/schemas/dashboard.py` | Dashboard 响应模型增加今日建议跟进和岗位分布结构 |
| `backend/app/services/followup_service.py` | 新增规则型跟进建议服务，供 Dashboard 待跟进统计复用 |
| `frontend/src/pages/CandidateList.tsx` | 顶部筛选工具栏增加岗位下拉、阶段下拉、来源下拉、关键词搜索和重置按钮 |
| `frontend/src/pages/Dashboard.tsx` | 新增“今日建议跟进”和“岗位分布”模块 |
| `frontend/src/api/index.ts` / `frontend/src/types/index.ts` | 增加筛选选项 API 和 Dashboard 岗位分布类型 |

### 第十二轮：候选人批量处理

| 文件 | 修改内容 |
|------|---------|
| `backend/app/schemas/candidate.py` | 增加批量状态、批量 ID 请求和批量操作响应模型 |
| `backend/app/services/candidate_service.py` | 增加批量更新阶段、批量生成跟进建议、按 ID 获取候选人、批量导出日志能力 |
| `backend/app/routers/candidates.py` | 新增 `POST /api/candidates/batch/status`、`POST /api/candidates/batch/followup`、`POST /api/candidates/batch/export` |
| `frontend/src/api/index.ts` / `frontend/src/types/index.ts` | 增加批量操作 API 封装和响应类型 |
| `frontend/src/pages/CandidateList.tsx` | 增加复选框选择、批量操作栏、批量淘汰确认弹窗、批量导出和批量跟进建议入口 |

### 第十三轮：招聘岗位管理与投递岗位标准化

| 文件 | 修改内容 |
|------|---------|
| `backend/app/models/job.py` | 新增 `Job` 岗位模型，字段含 title、department、description、requirements、status、created_at、updated_at |
| `backend/app/models/candidate.py` / `backend/app/schemas/candidate.py` | 候选人新增 `job_id`，继续保留 `target_role` 作为提交时岗位名称快照 |
| `backend/app/database.py` | 启动迁移补齐旧库 `candidates.job_id` 字段 |
| `backend/app/schemas/job.py` / `backend/app/services/job_service.py` | 新增岗位 CRUD、状态校验、默认岗位初始化、历史候选人 job_id 回填 |
| `backend/app/routers/jobs.py` / `backend/app/main.py` | 新增岗位管理接口并挂载到 `/api/jobs` |
| `backend/app/routers/apply.py` | `/apply` 提交必须传 `job_id`，后端校验 active 岗位并保存 `job_id + target_role` |
| `backend/app/routers/candidates.py` / `backend/app/services/candidate_service.py` | HR 新增候选人支持 `job_id`；筛选选项合并岗位库标题和历史候选人岗位 |
| `frontend/src/pages/JobManagement.tsx` | 新增 HR `/jobs` 岗位管理页，支持新增、编辑、启用/停用、谨慎删除 |
| `frontend/src/pages/ApplyForm.tsx` | 应聘岗位改为实时调用 `GET /api/jobs/active` 的必填下拉；无开放岗位时提示并禁止提交 |
| `frontend/src/pages/CandidateForm.tsx` | HR 新增候选人页默认选择岗位库，特殊情况提供“其他/手动输入” |
| `frontend/src/App.tsx` / `frontend/src/components/AppLayout.tsx` | 新增 `/jobs` 路由和侧边栏“岗位管理”菜单 |
| `frontend/src/api/index.ts` / `frontend/src/types/index.ts` | 增加岗位 API 封装和 `Job` 类型 |
| `scripts/init_db.py` | 初始化脚本同步创建默认岗位并回填候选人 `job_id` |

### 第十四轮：HR 决策操作业务化

| 文件 | 修改内容 |
|------|---------|
| `backend/app/models/candidate.py` | 新增面试、复试、Offer、入职、淘汰相关结构化字段 |
| `backend/app/database.py` | 启动迁移补齐新增 HR 决策字段 |
| `backend/app/schemas/candidate.py` | `CandidateRead` 和 `HRActionRequest` 增加面试/复试/Offer/入职/淘汰字段 |
| `backend/app/services/stage_service.py` | HR 动作增加阶段限制、终态保护、业务字段保存、阶段日志和 HR 操作日志 |
| `backend/app/services/candidate_service.py` | 透传扩展后的 HR action payload，并在同步数据中包含关键流程字段 |
| `backend/app/routers/candidates.py` | 候选人详情返回 HR 决策字段；HR action 接口返回明确业务错误 |
| `backend/app/services/sync_adapter.py` / `scripts/export_csv.py` | CSV 同步/导出增加面试、Offer、入职、淘汰关键字段 |
| `frontend/src/pages/CandidateDetail.tsx` | HR 决策按钮改为业务弹窗；按阶段禁用不合理动作；新增招聘流程信息展示 |
| `frontend/src/api/index.ts` / `frontend/src/types/index.ts` | 扩展 HR action API 类型和候选人详情类型 |
| `frontend/src/utils/constants.ts` | 更新 HR 操作文案说明 |

### 第十五轮：AI 初筛中心投递时间筛选

| 文件 | 修改内容 |
|------|---------|
| `backend/app/routers/screening.py` | 初筛结果返回 `created_at`；结果查询和批量初筛支持 `date_range`、`start_date`、`end_date`、`sort_by=created_at`、`sort_order` |
| `backend/app/services/candidate_service.py` | 初筛结果查询和待初筛批处理增加投递时间过滤、岗位/推荐等级过滤复用、投递时间排序 |
| `backend/app/schemas/candidate.py` | `ScreeningResultRead` 增加 `created_at` |
| `frontend/src/types/index.ts` | `ScreeningResult` 增加 `created_at` |
| `frontend/src/api/index.ts` | `runBatchScreening()` 支持携带筛选 query 参数 |
| `frontend/src/pages/AIScreeningCenter.tsx` | 新增投递时间列、投递时间筛选、最新/最早投递排序、筛选范围批量初筛确认 |

### 第十六轮：岗位要求配置驱动 AI 初筛

| 文件 | 修改内容 |
|------|---------|
| `backend/app/models/job.py` | `jobs` 表新增 `required_skills`、`bonus_skills`、`education_requirement`、`experience_requirement`、`job_keywords`、`risk_keywords` |
| `backend/app/database.py` | 启动迁移补齐旧库岗位要求字段 |
| `backend/app/schemas/job.py` / `backend/app/services/job_service.py` | 岗位 CRUD 支持岗位要求字段；默认示例岗位补充筛选标准 |
| `backend/app/services/candidate_service.py` | AI 初筛前读取候选人 `job_id` 对应岗位配置，历史数据按岗位名称兜底 |
| `backend/app/services/mock_llm.py` / `backend/app/services/ai_service.py` | 初筛评分优先参考岗位要求配置，并继续避免敏感信息维度 |
| `backend/app/routers/screening.py` / `backend/app/schemas/candidate.py` | 初筛结果返回岗位标准匹配摘要和岗位标准详情 |
| `frontend/src/pages/JobManagement.tsx` | 岗位管理新增岗位要求配置表单和筛选标准摘要列 |
| `frontend/src/pages/AIScreeningCenter.tsx` | 初筛列表新增“匹配依据”列和“查看岗位标准”弹窗 |
| `frontend/src/types/index.ts` | 扩展 `Job` 和 `ScreeningResult` 类型 |

### 第十七轮：超时未跟进提醒

| 文件 | 修改内容 |
|------|---------|
| `backend/app/services/followup_service.py` | 新增阶段超时规则，统一计算 `is_overdue`、`overdue_days`、`overdue_reason`、`last_action_at` 和跟进优先级 |
| `backend/app/services/candidate_service.py` | Dashboard 跟进预警改为基于超时规则；候选人列表/详情复用统一跟进字段 |
| `backend/app/schemas/candidate.py` | 候选人响应补充超时提醒字段 |
| `frontend/src/types/index.ts` / `frontend/src/api/index.ts` | 扩展候选人、跟进摘要、预警和刷新建议的类型 |
| `frontend/src/pages/Dashboard.tsx` | 今日建议跟进模块新增超时未跟进、今日待跟进、高优先级、超过3天未跟进统计 |
| `frontend/src/components/FollowUpAlerts.tsx` | Dashboard 跟进预警展示超时原因、优先级和超时天数 |
| `frontend/src/pages/CandidateList.tsx` | 候选人列表 AI 跟进列展示超时标签、超时天数、优先级和原因 |
| `frontend/src/pages/CandidateDetail.tsx` | 候选人详情页展示超时未跟进 Alert 和系统跟进建议 |

### 第十八轮：最近新增候选人高亮

| 文件 | 修改内容 |
|------|---------|
| `backend/app/schemas/candidate.py` | 候选人响应新增 `new_candidate_label`、`is_today_new`、`is_recent_3_days_new` |
| `backend/app/schemas/dashboard.py` | Dashboard 响应新增最近 3 天新增人数和今日新增候选人列表结构 |
| `backend/app/services/candidate_service.py` | 统一计算最近新增规则；候选人列表支持 `is_today_new` 筛选；Dashboard 统计最近新增和今日新增 Top 5 |
| `backend/app/routers/candidates.py` | 列表接口透传今日新增筛选，并在候选人响应中返回最近新增字段 |
| `frontend/src/types/index.ts` | 扩展候选人和 Dashboard 类型 |
| `frontend/src/pages/CandidateList.tsx` | 新增最近新增标签、投递时间、来源渠道、今日新增标识、今日新增筛选和行高亮 |
| `frontend/src/pages/Dashboard.tsx` | 新增“最近新增候选人”模块，展示今日新增、最近 3 天新增和今日新增 Top 5 |
| `frontend/src/components/StatsCards.tsx` | 统计卡片新增“最近3天新增” |
| `frontend/src/App.css` | 增加最近新增候选人行轻量高亮样式 |

### 第十九轮：面试反馈 AI 总结

| 文件 | 修改内容 |
|------|---------|
| `backend/app/models/candidate.py` | 候选人模型新增面试反馈、轮次、反馈时间和 AI 面试总结字段 |
| `backend/app/database.py` | 启动迁移补齐旧库新增字段，并初始化空值 |
| `backend/app/schemas/candidate.py` | 增加面试反馈请求/响应模型，并扩展候选人响应字段 |
| `backend/app/services/mock_llm.py` | 新增规则型面试反馈总结，避免编造未给出的信息 |
| `backend/app/services/ai_service.py` | 新增 `summarize_interview_feedback()`，真实 LLM 失败回退 mock |
| `backend/app/services/candidate_service.py` | 保存原始反馈和 AI 总结，写入 `ai_interview_summary` 操作日志 |
| `backend/app/routers/ai.py` | 新增 `POST /api/ai/interview-summary/{candidate_id}` |
| `backend/app/routers/candidates.py` | 候选人详情返回面试反馈和 AI 总结字段 |
| `frontend/src/types/index.ts` / `frontend/src/api/index.ts` | 增加面试反馈 AI 总结类型和 API 封装 |
| `frontend/src/pages/CandidateDetail.tsx` | 新增“面试反馈 AI 总结”输入与展示区域 |
| `frontend/src/components/RecentLogs.tsx` | Dashboard 最近操作日志支持 AI 面试总结颜色 |

### 第二十轮：演示数据与详情信息增强

| 文件 | 修改内容 |
|------|---------|
| `backend/app/seed_data.py` | 新增 5 条在线投递演示候选人；已有数据库启动时按手机号补充缺失演示候选人和较短简历信息 |
| `backend/app/services/job_service.py` | 默认岗位补充岗位描述和任职要求；已有岗位空字段会自动补齐 |
| `frontend/src/pages/AIScreeningCenter.tsx` | 初筛中心展示文案统一为“匹配依据”和“查看岗位标准” |
| `frontend/src/pages/CandidateDetail.tsx` | 新增“投递与 AI 初筛信息”卡片，展示匹配度、推荐等级、初筛理由、风险提示和跟进信息 |

### 第二十一轮：AI 初筛统计口径统一

| 文件 | 修改内容 |
|------|---------|
| `backend/app/services/candidate_service.py` | 移除 AI 初筛对 `is_duplicate == False` 的过滤；新增统一初筛统计方法，返回总人数、已初筛、尚未初筛和高/中/低优先级 |
| `backend/app/routers/screening.py` | `/api/screening/results` 返回 `stats`（当前筛选结果）和 `overall_stats`（全部统计） |
| `backend/app/schemas/dashboard.py` | 初筛统计模型补充 `total_candidates` 和 `screened_count` |
| `frontend/src/types/index.ts` | 扩展初筛统计与初筛结果响应类型 |
| `frontend/src/pages/AIScreeningCenter.tsx` | 顶部统计改用后端 `overall_stats`；筛选后单独显示当前筛选结果统计 |

### 第二十二轮：AI 初筛中心当前筛选统计彻底统一

| 文件 | 修改内容 |
|------|---------|
| `backend/app/services/candidate_service.py` | 初筛筛选支持 `screening_status`；已初筛判定统一为有 `match_score` 或非空 `priority_level` |
| `backend/app/routers/screening.py` | `/api/screening/results` 和 `/api/screening/run` 增加 `screening_status=screened|unscreened` |
| `frontend/src/pages/AIScreeningCenter.tsx` | 当前筛选结果统计改为直接基于当前表格 `items` 计算；新增初筛状态筛选；批量初筛范围与当前表格一致 |

### 第二十三轮：招聘漏斗初筛流转改造

| 文件 | 修改内容 |
|------|---------|
| `backend/app/models/candidate.py` / `backend/app/database.py` | 新增并迁移 `screening_status` 字段，取值 pending/passed/backup/rejected；旧库按阶段回填 |
| `backend/app/services/candidate_service.py` | 新增通过初筛、标记备选、初筛淘汰业务方法；候选人列表默认仅查 `passed`；Dashboard 新增初筛状态统计 |
| `backend/app/routers/candidates.py` | 新增 `/screening/pass`、`/screening/backup`、`/screening/reject` 接口；列表接口新增 `candidate_scope` 和 `screening_status` |
| `backend/app/routers/screening.py` | AI 初筛结果/批量初筛新增 `decision_status`，默认处理 pending 初筛池 |
| `frontend/src/pages/AIScreeningCenter.tsx` | 默认展示待初筛候选人；每行保留通过初筛、初筛淘汰、详情、重新初筛按钮和淘汰原因弹窗 |
| `frontend/src/pages/CandidateList.tsx` | 页面改为“候选人管理 / 正式流程候选人”，默认展示已通过初筛候选人；阶段筛选移除新投递/待筛选 |
| `frontend/src/pages/Dashboard.tsx` / `frontend/src/components/StatsCards.tsx` | Dashboard 改为展示总投递、待初筛、通过初筛、正式流程备选、初筛淘汰、正式流程候选人数 |
| `frontend/src/api/index.ts` / `frontend/src/types/index.ts` / `frontend/src/utils/constants.ts` | 新增初筛决策 API、类型字段和正式流程阶段常量 |

### 第二十四轮：岗位一致的 Demo 数据重置脚本

| 文件 | 修改内容 |
|------|---------|
| `scripts/reset_demo_data.py` | 新增可重复运行的演示数据重置脚本；保留岗位管理数据，补齐 8 个 active Demo 岗位和岗位要求，清空候选人/日志/旧附件，生成 30 条候选人和 21 份 TXT 简历 |
| `README.md` | 增加“重置演示数据”说明和运行命令 |
| `PROJECT_STATE.md` / `TODO_NEXT.md` / `HANDOFF.md` | 记录 Demo 数据脚本、生成口径和校验结果 |

### 第二十五轮：候选人列表范围筛选简化

| 文件 | 修改内容 |
|------|---------|
| `backend/app/services/candidate_service.py` | 候选人列表范围口径收敛为 formal/backup/rejected；formal 排除阶段「淘汰」，rejected 包含初筛淘汰和正式流程淘汰 |
| `backend/app/routers/candidates.py` | `candidate_scope` 参数限制为 `formal|backup|rejected` |
| `frontend/src/pages/CandidateList.tsx` | 范围筛选只保留三类；备选/淘汰视图隐藏阶段筛选；批量操作按范围展示 |
| `frontend/src/utils/constants.ts` | 新增正式流程活跃阶段常量，不含「新投递」「待筛选」「淘汰」 |
| `README.md` / `PROJECT_STATE.md` / `TODO_NEXT.md` / `HANDOFF.md` | 同步候选人列表职责边界和三类视图口径 |

### 第二十六轮：AI 初筛中心移除备选逻辑

| 文件 | 修改内容 |
|------|---------|
| `backend/app/services/candidate_service.py` | AI 初筛池状态收敛为 pending；正式流程备选接口只允许已通过初筛且未淘汰候选人调用；备选淘汰时转入 rejected |
| `backend/app/routers/screening.py` | `/api/screening/results` 和 `/api/screening/run` 默认 `decision_status=pending` |
| `backend/app/routers/candidates.py` | `/api/candidates/{id}/screening/backup` 返回 400 业务错误，避免 pending 候选人被标记为备选 |
| `frontend/src/pages/AIScreeningCenter.tsx` | 删除备选统计、备选筛选项和每行“标记备选”按钮；默认只展示待初筛候选人 |
| `frontend/src/pages/CandidateList.tsx` | 正式流程视图新增批量标记备选；备选视图移除“批量通过初筛” |
| `frontend/src/pages/Dashboard.tsx` | Dashboard 文案调整为“正式流程备选人数” |
| `scripts/reset_demo_data.py` | Demo 数据改为 11 名 pending 初筛池 + 3 名正式流程备选，不再生成 AI 初筛中心备选 |
| `README.md` / `PROJECT_STATE.md` / `TODO_NEXT.md` / `HANDOFF.md` | 同步 AI 初筛中心和正式流程备选职责边界 |

### 第二十七轮：新电脑交付启动与演示数据自动兜底

| 文件 | 修改内容 |
|------|---------|
| `backend/app/config.py` | 默认数据库改为明确的 `backend/recruit.db`，默认上传目录为 `backend/uploads`；相对 `DATABASE_URL` / `UPLOAD_DIR` 统一解析到 `backend/` |
| `backend/app/main.py` | 后端 lifespan 调用 `scripts.ensure_demo_data.ensure_demo_data()`，启动时按需补齐空库演示数据 |
| `backend/app/database.py` | SQLite 迁移前确保数据库父目录存在 |
| `scripts/ensure_demo_data.py` | 新增安全兜底脚本：创建库表、上传目录、默认岗位；候选人表为空才复用 `reset_demo_data.py` 生成 Demo |
| `scripts/reset_demo_data.py` | 上传目录解析兼容绝对路径和相对路径 |
| `scripts/init_db.py` | 改为复用 `ensure_demo_data.py`，避免初始化脚本和后端启动逻辑不一致 |
| `backend/app/routers/apply.py` / `backend/app/routers/resume.py` / `backend/app/routers/candidates.py` | 创建上传目录时使用 `parents=True`，目录不存在不会报错 |
| `start_backend.bat` / `start_frontend.bat` | 新增 Windows 双击启动脚本；前端脚本使用 `npm.cmd run dev` 启动 Vite |
| `.env.example` / `README.md` / `PROJECT_STATE.md` / `TODO_NEXT.md` / `HANDOFF.md` | 同步新电脑交付方式、数据库位置、Vite 代理和禁止 Python `http.server` 说明 |
