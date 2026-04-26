# Testin云测招聘助手

基于 AI 技术的智能招聘管理系统，解决 HR 手动录入、数据失真、跟进遗漏等痛点，实现招聘数据的自动化记录与智能化跟踪。

## 核心功能

- **智能简历解析**：上传 PDF/DOCX/TXT 简历，AI 自动提取 11 个标准化字段
- **AI 候选人摘要**：一键生成 2-3 句专业候选人概况
- **自动标签分类**：多维度自动打标（学历/经验/技能/岗位/特殊标记）
- **AI 批量初筛中心**：基于岗位要求对候选人批量生成岗位匹配度、推荐等级、初筛建议、风险提示，并支持按匹配度、投递时间排序和按投递时间范围筛选
- **真实招聘漏斗流转**：新投递候选人先进入 AI 初筛中心；只有 HR 点击“通过初筛”后，才进入候选人列表正式流程
- **AI 初筛入口处理池**：AI 初筛中心默认只展示待初筛候选人，并支持通过初筛、初筛淘汰、重新初筛、查看详情
- **统一统计口径**：Dashboard 区分总投递、待初筛、通过初筛、正式流程备选、初筛淘汰和正式流程候选人数；候选人列表默认人数不等于总投递人数
- **智能跟进建议**：基于招聘阶段生成具体行动建议 + 超时预警
- **面试反馈 AI 总结**：HR 输入面试反馈后，AI 整理技术能力、沟通表达、岗位匹配度、风险点、推荐结论和下一步建议
- **超时未跟进提醒**：按招聘阶段自动识别长期未处理候选人，在 Dashboard、候选人列表和详情页提醒 HR
- **HR Copilot**：自然语言对话查询招聘数据和获取建议
- **HR 决策操作**：候选人详情页支持安排面试、进入复试、发放 Offer、确认入职、淘汰等业务化动作，自动更新阶段、保存结构化信息并写入日志
- **招聘看板**：漏斗图、渠道饼图、统计卡片、最近新增候选人、跟进预警
- **招聘岗位管理**：HR 后台统一维护岗位库和岗位要求，支持新增、修改、启用/停用，投递端只展示当前启用岗位
- **候选人组合筛选**：候选人列表支持按应聘岗位、招聘阶段、来源渠道、今日新增和关键词组合筛选，岗位选项从真实数据动态生成
- **最近新增候选人高亮**：今日新增显示“今日新增”，最近 3 天新增显示“新投递”；列表默认按投递时间倒序，并显示投递时间、来源渠道和今日新增标识
- **丰富演示数据**：内置更多在线投递候选人简历信息，默认岗位包含岗位描述、任职要求和 AI 初筛标准
- **候选人批量处理**：候选人列表支持批量标记备选、批量标记待约面、批量淘汰确认、批量导出 CSV、批量生成 AI 跟进建议
- **三级去重**：手机号 → 邮箱 → 姓名+学校+岗位，防止重复录入
- **HR 统一新增候选人**：后台统一使用 `/form` 完成手动录入 + 可选简历上传，AI 只补全空字段
- **投递者在线填写**：独立页面（/apply），投递者自助填写信息+上传简历，岗位下拉实时读取开放岗位并自动入库
- **数据同步**：支持 CSV 导出，预留腾讯文档 API 接口

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + Vite + Recharts |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 数据库 | SQLite（零运维，可迁移 PostgreSQL） |
| AI | Mock LLM（内置）/ OpenAI / DeepSeek / 智谱（可选） |
| 部署 | Docker Compose + nginx |

## 环境要求

- Python 3.9+（推荐 3.10 或 3.11）
- Node.js 18+ 和 npm
- Windows 可直接使用根目录 `start_backend.bat`、`start_frontend.bat`
- 默认使用 Mock LLM，不需要真实 API Key；如需接入真实模型，请复制 `.env.example` 为 `.env` 并填写自己的 Key，`.env` 不应提交到 GitHub

## 快速启动

### 方式一：Docker（推荐）

```bash
docker-compose up --build
```

- 前端：http://localhost:3000
- 后端 API 文档：http://localhost:8000/docs

### 方式二：手动启动

```bash
# 后端
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env
python run.py
# → http://localhost:8000/docs

# 前端（新终端）
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

系统启动后会自动创建数据库表、上传目录和默认岗位，**无需任何 API Key**。如果候选人表为空，后端会自动生成约 30 条完整演示候选人和简历附件；如果已有候选人，则不会重复初始化或清空数据。默认岗位不会重复创建，可在 HR 后台“岗位管理”页面新增或修改。

## 新电脑打开方式

解压项目压缩包后，必须使用 Vite 开发服务器启动前端。不要使用 `python -m http.server` 或 Python `http.server` 打开 `frontend` 静态文件；静态服务器无法代理 `/api` 请求到后端，页面会看不到候选人、Dashboard、AI 初筛等演示数据。

### 方式一：双击脚本启动

第一步：双击项目根目录的 `start_backend.bat`

第二步：双击项目根目录的 `start_frontend.bat`

第三步：打开浏览器访问：

```bash
http://localhost:5173
```

后端接口文档：

```bash
http://localhost:8000/docs
```

### 方式二：手动启动

```bash
# 终端 1：后端
cd backend
pip install -r requirements.txt
python run.py

# 终端 2：前端，必须使用 Vite
cd frontend
npm install
npm run dev
```

访问：

```bash
http://localhost:5173
```

如果 PowerShell 执行 `npm` 有权限问题，可以改用：

```bash
npm.cmd install
npm.cmd run dev
```

首次启动后端时，如果数据库为空，系统会自动生成完整演示数据：Dashboard 有统计，AI 初筛中心有待初筛候选人，候选人列表有正式流程候选人，岗位管理和 `/apply` 岗位下拉都有岗位数据。数据库默认位置为 `backend/recruit.db`，上传附件默认目录为 `backend/uploads`；如果数据库文件或上传目录不存在，后端会自动创建。

前端 Vite 代理配置在 `frontend/vite.config.ts`：

```ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## 重置演示数据

Demo 前可运行脚本恢复一套干净、岗位一致的演示环境：

```bash
python scripts/reset_demo_data.py
```

该脚本会清空当前候选人测试数据、候选人日志和旧上传简历附件，但会保留岗位管理数据；如果岗位库缺少示例岗位，会初始化或补齐 active 岗位及岗位要求配置。脚本会重新生成约 30 条候选人数据，所有候选人的 `job_id` 和 `target_role` 都来自岗位管理范围。新投递/待初筛候选人会进入 AI 初筛中心，通过初筛候选人才会进入候选人列表；备选候选人只从已通过初筛的正式流程候选人中生成，适合 Demo 前恢复招聘漏斗数据。

## 主要页面

- `http://localhost:5173/` 或 `/dashboard`：Dashboard 数据看板，含今日新增、最近 3 天新增和今日新增候选人列表
- `http://localhost:5173/form`：HR 后台“新增候选人”统一入口，支持手动录入 + 可选简历上传
- `http://localhost:5173/jobs`：HR 岗位管理，维护投递者可选择的岗位库
- `http://localhost:5173/upload`：兼容旧地址，会自动跳转到 `/form`
- `http://localhost:5173/ai-screening`：AI 初筛中心，默认只展示待初筛候选人，支持批量初筛、通过初筛、初筛淘汰、单人重新初筛、推荐等级筛选、投递时间筛选、匹配度排序、投递时间排序和“匹配依据”查看
- `http://localhost:5173/candidates`：候选人管理，范围筛选只保留正式流程候选人、备选候选人、淘汰候选人；新投递和待初筛候选人请在 AI 初筛中心处理。正式流程阶段筛选保留待约面、已约面、面试中、复试、offer、入职
- `http://localhost:5173/candidates/:id`：候选人详情，含更完整的简历信息、投递与 AI 初筛信息、面试反馈 AI 总结
- `http://localhost:5173/apply`：投递者公开填写页，继续保留

## 项目结构

```
testin云测面试题/
├── backend/                 # FastAPI 后端
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py              # 启动入口
│   └── app/
│       ├── main.py          # FastAPI app
│       ├── config.py        # 配置管理
│       ├── database.py      # 数据库连接
│       ├── seed_data.py     # 种子数据
│       ├── models/          # ORM 模型
│       ├── schemas/         # Pydantic 模型
│       ├── routers/         # API 路由（含候选人、岗位、简历、AI、初筛、看板、同步、投递）
│       ├── services/        # 业务服务（7个）
│       └── prompts/         # Prompt 模板（5个）
├── frontend/                # React 前端
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── pages/           # 页面
│       ├── components/      # 组件（9个）
│       ├── api/             # API 封装
│       └── types/           # TypeScript 类型
├── docs/                    # 项目文档
│   ├── 业务方案.md
│   ├── Prompt工程与效果验证.md
│   ├── 系统架构说明.md
│   ├── 演示脚本.md
│   └── 答辩讲稿.md
├── prompts/                 # Prompt 设计文档
├── scripts/                 # 工具脚本
│   ├── init_db.py           # 数据库初始化
│   ├── ensure_demo_data.py  # 启动时按需补齐演示数据
│   ├── reset_demo_data.py   # 手动重置演示数据
│   └── export_csv.py        # CSV 导出
├── sample_data/             # 示例数据
├── start_backend.bat        # Windows 后端一键启动
├── start_frontend.bat       # Windows 前端 Vite 一键启动
├── docker-compose.yml
├── .env.example
└── README.md
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| LLM_PROVIDER | mock | LLM 模式：mock / openai / deepseek / zhipu |
| OPENAI_API_KEY | - | LLM API Key（mock 模式不需要） |
| OPENAI_BASE_URL | https://api.openai.com/v1 | API 地址 |
| OPENAI_MODEL | gpt-4o-mini | 模型名称 |
| DATABASE_URL | sqlite:///./recruit.db | 数据库连接；相对路径会解析到 `backend/`，默认实际文件为 `backend/recruit.db` |
| CORS_ORIGINS | http://localhost:5173,http://localhost:3000 | 跨域白名单 |
| UPLOAD_DIR | ./uploads | 上传目录；相对路径会解析到 `backend/`，默认实际目录为 `backend/uploads` |

## 工具脚本

```bash
# 初始化数据库（独立于服务启动）
python scripts/init_db.py

# 按需补齐演示数据：候选人表为空才生成，不会重复清库
python scripts/ensure_demo_data.py

# 导出候选人数据为 CSV
python scripts/export_csv.py [output_path]
```

## AI 初筛接口

- `POST /api/screening/run`：对当前筛选范围内的候选人执行批量 AI 初筛；支持 `target_role`、`priority_level`、`screening_status=screened|unscreened`、`date_range`、`start_date`、`end_date`，已初筛候选人会重新生成结果
- `POST /api/screening/run/{candidate_id}`：对单个候选人重新执行 AI 初筛
- `GET /api/screening/results`：获取初筛结果，支持 `target_role`、`priority_level`、`screening_status=screened|unscreened`、`date_range=today|this_week|last_7_days|last_30_days`、`start_date`、`end_date`、`sort_by=score_desc|score_asc|updated_desc|created_at`、`sort_order=desc|asc`

AI 初筛结果仅作为 HR 辅助参考，不会自动淘汰候选人。

AI 初筛中心列表的“投递时间”来自候选人真实创建时间 `created_at`。默认按最新投递优先展示；选择时间筛选后，批量初筛会处理当前筛选结果中的候选人，已初筛候选人会重新生成结果。

AI 初筛统计口径与 Dashboard 候选人总数一致：当前项目没有归档字段，因此以 `candidates` 主表全部记录作为有效候选人总数。高优先级 + 中优先级 + 低优先级 + 尚未初筛 = 总候选人数。缺少 `target_role`、缺少 `job_id`、没有简历附件或尚未生成 AI 初筛结果的候选人不会从总数中排除，会计入“尚未初筛”或当前筛选结果。

AI 初筛中心的“当前筛选结果”统计直接由当前表格数据计算，因此表格右侧“当前 X 人”、蓝色统计框、批量初筛提示使用同一份候选人列表。筛选条件包括岗位搜索、推荐等级、初筛状态、投递时间范围和排序方式。

## 候选人筛选接口

- `GET /api/candidates/`：支持 `target_role`、`stage`、`channel`、`is_today_new`、`keyword` 组合筛选；也兼容 `recruiting_stage`、`source_channel`
- `GET /api/candidates/filter-options`：从岗位库和当前候选人历史数据动态返回岗位和来源筛选选项

关键词搜索覆盖姓名、学校、专业、技能关键词、邮箱、手机号和应聘岗位。

候选人列表默认按 `created_at` 投递时间倒序返回。后端统一计算最近新增标记：

- `is_today_new=true`：投递日期为系统今天，前端显示“今日新增”
- `is_recent_3_days_new=true`：投递时间在今天、昨天、前天 3 个自然日内
- `new_candidate_label`：今日返回“今日新增”；最近 3 天但非今日返回“新投递”；更早为空

Dashboard `/api/dashboard/stats` 同步返回 `new_today`、`new_last_3_days` 和 `today_new_candidates`，其中今日新增候选人列表最多 5 条。

## 岗位管理接口

- `GET /api/jobs`：获取岗位列表，支持 `status=active|inactive`
- `GET /api/jobs/active`：获取投递者页面可选择的启用岗位
- `POST /api/jobs`：新增岗位，避免重复岗位名称
- `PUT /api/jobs/{job_id}`：修改岗位名称、部门、描述、要求和状态
- `PATCH /api/jobs/{job_id}/status`：启用或停用岗位
- `DELETE /api/jobs/{job_id}`：无候选人时删除；已有候选人时自动停用以保留历史数据

候选人提交时会同时保存 `job_id` 和当时选择的岗位名称 `target_role`。岗位改名或停用不会回写历史候选人的 `target_role`，Dashboard 岗位分布和候选人列表筛选仍基于真实历史岗位数据展示。

岗位库还支持维护 AI 初筛使用的筛选标准：

- `required_skills`：必备技能，逗号/顿号/标签分隔
- `bonus_skills`：加分技能
- `education_requirement`：学历要求
- `experience_requirement`：经验要求
- `job_keywords`：岗位关键词
- `risk_keywords`：风险提示关键词
- `description` / `requirements`：岗位描述和岗位要求

AI 初筛会优先读取候选人 `job_id` 对应岗位要求；历史候选人如果没有 `job_id`，会按 `target_role` 与岗位标题尝试匹配。评分会参考必备技能命中率、加分技能、学历/经验要求、岗位关键词和风险关键词，不使用性别、年龄、民族、婚育等敏感信息。

## 候选人批量接口

- `POST /api/candidates/batch/status`：批量修改候选人阶段，支持批量标记待约面、批量淘汰；正式流程候选人可在列表页批量标记备选
- `POST /api/candidates/batch/followup`：批量生成 AI 跟进建议并写入操作日志
- `POST /api/candidates/batch/export`：只导出选中候选人的 CSV

批量阶段操作会写入阶段变更日志和操作日志，Dashboard 阶段统计和最近操作日志会同步更新。

## HR 决策操作

候选人详情页的 HR 决策按钮按当前阶段动态启用：

- 新投递 / 待筛选：通过筛选、淘汰
- 待约面：安排面试、淘汰
- 已约面 / 面试中：进入复试、淘汰，也支持直接发放 Offer
- 复试：发放 Offer、淘汰
- offer：确认入职、淘汰
- 入职 / 淘汰：流程推进按钮禁用，仅保留阶段人工修正和日志查看

动作提交后会调用 `POST /api/candidates/{candidate_id}/hr-action/{action_name}`，更新候选人阶段和对应业务字段，写入阶段变更日志与 HR 操作日志，并同步 Dashboard 统计、最近操作日志和本地 CSV 数据。

关键动作字段：

- 安排面试：面试时间（必填）、面试方式、面试官、面试备注
- 进入复试：复试原因 / 一面反馈、复试时间、复试面试官
- 发放 Offer：Offer 岗位、薪资范围、预计入职时间、Offer 备注
- 确认入职：实际入职时间、入职备注
- 淘汰：淘汰原因（必填）、淘汰备注

## 面试反馈 AI 总结

候选人详情页提供“面试反馈 AI 总结”区域，HR 可输入：

- `interview_feedback_text`：面试原始反馈，必填
- `interviewer`：面试官，可选
- `interview_round`：面试轮次，可选，例如一面 / 复试
- `feedback_time`：反馈时间

点击“生成 AI 面试总结”会调用 `POST /api/ai/interview-summary/{candidate_id}`。系统会基于候选人已有信息和 HR 输入反馈生成：

- 技术能力总结
- 沟通表达总结
- 岗位匹配度判断
- 风险点
- 推荐结论：建议复试 / 建议 offer / 待定 / 不建议继续
- 下一步建议

AI 总结仅作为辅助参考，不会自动改变候选人阶段，也不会自动淘汰候选人。生成结果保存到候选人记录字段中，包括 `interview_feedback_text`、`interview_round`、`feedback_time`、`interview_ai_technical_summary`、`interview_ai_communication_summary`、`interview_ai_job_match`、`interview_ai_risk_points`、`interview_ai_recommendation`、`interview_ai_next_step`、`interview_ai_generated_at`。生成后会写入 `ai_interview_summary` 操作日志。

## 超时未跟进规则

系统会根据候选人当前阶段和最近动作时间自动计算超时状态，返回 `is_overdue`、`overdue_days`、`overdue_reason`、`followup_priority`、`last_action_at` 等字段，并在 Dashboard、候选人列表和候选人详情页展示。

当前规则：

- 新投递超过 1 天未处理：请尽快完成初筛
- 待筛选超过 1 天未处理：请尽快完成筛选判断
- 待约面超过 2 天未安排面试：请尽快联系候选人安排面试
- 已约面 / 面试中且面试时间已过超过 1 天未录入反馈：请尽快录入面试反馈
- 复试超过 2 天未处理：请尽快确认复试结果
- offer 超过 3 天未确认：请跟进 offer 接受情况
- 入职 / 淘汰：流程已结束，不再提醒

Dashboard 会展示超时未跟进人数、今日待跟进人数、高优先级跟进人数和最需要处理的候选人列表。候选人列表会展示超时标签、超时天数和优先级；候选人详情页会展示当前超时原因和系统跟进建议。

## 文档

- [业务方案](docs/业务方案.md) — 痛点分析与解决方案
- [Prompt 工程与效果验证](docs/Prompt工程与效果验证.md) — Prompt 设计与双模架构
- [系统架构说明](docs/系统架构说明.md) — 技术栈、数据库、API 路由
- [演示脚本](docs/演示脚本.md) — 5 分钟演示流程
- [答辩讲稿](docs/答辩讲稿.md) — 5 分钟答辩结构与 Q&A 预案
