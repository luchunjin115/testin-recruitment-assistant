# 项目进度状态

> 最后更新：2026-04-26（第二十七轮，新电脑交付启动与演示数据自动兜底）

## 项目状态：✅ 全部完成 + 新电脑解压后可按脚本/Vite 启动看到演示数据 + AI 初筛中心移除备选逻辑 + 候选人列表正式流程备选 + 岗位一致 Demo 数据重置脚本 + 招聘漏斗初筛流转改造 + Dashboard 初筛状态统计 + TypeScript 构建通过，可运行、可演示、可答辩

---

## 一、已实现功能

### 后端功能
- **候选人 CRUD**：完整的增删改查 + 分页 + 组合筛选（岗位/阶段/渠道/关键词）+ 排序
- **动态筛选选项**：`/api/candidates/filter-options` 从真实候选人数据生成岗位和来源选项，不写死岗位名称
- **候选人批量处理**：支持批量标记备选、批量标记待约面、批量淘汰、批量导出 CSV、批量生成 AI 跟进建议
- **批量操作日志同步**：批量阶段变更复用 StageChangeLog + ActivityLog，Dashboard 最近操作日志可见，阶段统计自动更新
- **候选人删除**：列表页可删除候选人，带确认弹窗，删除后关联日志级联清理
- **HR 决策触发阶段流转**：6 种 HR 操作（通过筛选/安排面试/进入复试/发放offer/确认入职/淘汰）自动推进阶段
- **自动阶段推进**：简历上传自动进入「待筛选」；面试时间到达自动进入「面试中」
- **三种触发源追踪**：system_auto（系统自动）、hr_action（HR操作）、manual（人工修正），人工修正具有最高优先级
- **阶段变更审计日志**：StageChangeLog 记录每次变更的来源、原因、前后状态
- **Dashboard 最近操作日志同步**：状态变更后统一展示最新阶段日志，包含原阶段/新阶段/触发原因/触发来源/更新时间
- **简历解析**：上传 PDF/DOCX/TXT，AI 自动提取 11 个结构化字段
- **AI 候选人摘要**：一键生成 2-3 句专业摘要
- **AI 自动标签**：生成 3-6 个多维度分类标签（学历/经验/技能/岗位/特殊）
- **AI 跟进建议**：基于招聘阶段生成具体下一步行动建议
- **面试反馈 AI 总结**：HR 在候选人详情页录入面试反馈后，可生成技术能力、沟通表达、岗位匹配度、风险点、推荐结论和下一步建议，并保存到候选人记录
- **AI 批量初筛**：支持对未初筛候选人批量生成岗位匹配度、推荐等级、初筛建议、初筛理由、风险提示和初筛时间
- **AI 初筛结果查询**：`/api/screening/results` 支持按岗位、推荐等级筛选，并按匹配度或更新时间排序
- **招聘漏斗初筛流转**：候选人主表新增 `screening_status`（pending/passed/backup/rejected）；/apply 与 HR 新增默认进入 pending，新投递候选人先进入 AI 初筛中心，通过初筛后进入候选人列表正式流程
- **岗位一致 Demo 数据重置**：新增 `scripts/reset_demo_data.py`，保留岗位管理数据，补齐 8 个 active Demo 岗位及岗位要求，清空候选人相关测试数据并重建 30 条候选人、21 份 TXT 简历附件；所有候选人 `job_id/target_role` 均来自岗位库
- **启动时演示数据兜底**：新增 `scripts/ensure_demo_data.py`，后端启动时自动创建数据库、上传目录和默认岗位；只有候选人表为空时才复用 `reset_demo_data.py` 生成完整演示数据，已有候选人时不清空、不重复导入
- **统一本地 SQLite 路径**：默认数据库明确为 `backend/recruit.db`，默认上传目录为 `backend/uploads`；相对 `DATABASE_URL` / `UPLOAD_DIR` 会解析到 `backend/`，避免脚本写一个库、后端读另一个库
- **Windows 一键启动**：新增根目录 `start_backend.bat` 和 `start_frontend.bat`；前端必须通过 Vite `npm run dev` / `npm.cmd run dev` 启动，使用 `frontend/vite.config.ts` 代理 `/api -> http://localhost:8000`
- **AI 初筛 HR 决策接口**：新增 `POST /api/candidates/{id}/screening/pass`、`/backup`、`/reject`；通过初筛写入 passed 并推进到「待约面」，`/backup` 仅允许已通过初筛的正式流程候选人进入备选视图，初筛淘汰写入原因并推进到「淘汰」
- **候选人列表范围简化**：`GET /api/candidates` 仅支持 `candidate_scope=formal|backup|rejected` 三类视图；正式流程默认展示 `screening_status=passed` 且阶段未淘汰的候选人，备选展示 `backup`，淘汰展示 `rejected` 或阶段为「淘汰」的候选人
- **Dashboard 初筛状态统计**：区分总投递人数、待初筛、通过初筛、正式流程备选、初筛淘汰、正式流程候选人数，避免候选人列表默认人数与总投递人数混淆
- **AI 初筛统计口径统一**：候选人列表、Dashboard、AI 初筛中心均以候选人主表全部记录作为总候选人数；缺少岗位、简历或未初筛结果不会从总数中排除；AI 初筛中心当前筛选统计直接由当前表格数据计算
- **单人重新初筛**：支持对候选人重新执行 AI 初筛，不自动淘汰候选人，最终决策仍由 HR 确认
- **HR Copilot**：自然语言对话查询招聘数据
- **三级去重**：手机号 → 邮箱 → 姓名+学校+岗位
- **招聘看板统计**：漏斗数据、渠道分布、岗位分布、今日新增、最近 3 天新增、今日新增候选人列表、跟进预警、今日建议跟进
- **最近新增规则**：候选人响应统一返回 `new_candidate_label`、`is_today_new`、`is_recent_3_days_new`；列表默认按投递时间倒序排列，并支持今日新增筛选
- **数据同步**：CSV 导出 + 腾讯文档 Adapter 预留接口
- **操作日志**：全操作记录（创建/阶段变更/AI处理等）
- **在线投递**：投递者自助填写表单 + 简历上传，自动入库（source_channel="在线投递"），手机号去重
- **HR 统一新增候选人**：`/form` 同时支持手动录入 + 可选简历上传，默认阶段为「新投递」，默认来源为「HR手动录入」
- **简历附件元数据**：候选人记录关联保存简历文件名、文件类型、文件大小、上传时间，并返回下载/查看地址
- **种子数据**：启动时自动导入 14 条候选人数据
- **演示数据增强**：已有库启动时会补充 5 条在线投递候选人，并补全默认岗位描述/要求，候选人详情展示更完整的投递、简历和 AI 初筛信息

### 前端功能
- **Dashboard 看板**：统计卡片 + 最近新增候选人（今日新增、最近 3 天新增、今日新增 Top 5）+ 招聘漏斗图 + 渠道饼图 + 岗位分布 + 今日建议跟进 + 跟进预警 + 今日摘要 + 最近操作日志
- **新增候选人统一页**：手动录入 + 可选简历上传 + AI 补全空字段 + 自动去重 + 创建后跳转详情
- **候选人列表**：范围筛选只保留正式流程候选人、备选候选人、淘汰候选人；新投递/待初筛候选人只在 AI 初筛中心处理；正式流程阶段筛选保留「待约面、已约面、面试中、复试、offer、入职」
- **AI 初筛中心**：`/ai-screening` 默认只展示待初筛候选人，展示 AI 匹配度、推荐等级、初筛建议、风险提示、投递时间、应聘岗位，并提供通过初筛/初筛淘汰/重新初筛/查看详情；备选移至候选人列表正式流程管理
- **候选人列表初筛展示**：列表中用紧凑列展示 AI 匹配度、推荐等级和初筛建议
- **候选人详情**：完整信息 + AI 摘要/标签/跟进建议（按需生成） + HR 决策按钮 + 阶段变更记录（含触发来源） + 人工修正下拉框 + 面试时间设置弹窗 + 操作日志
- **候选人详情面试反馈**：详情页支持录入面试原始反馈、面试官、面试轮次、反馈时间，并生成/重新生成 AI 面试总结
- **候选人详情简历附件区**：展示文件名/类型/大小/上传时间，并提供查看、下载按钮；未上传时显示占位提示
- **HR Copilot 聊天**：嵌入式对话组件
- **投递者在线填写页**：独立全屏表单页（/apply），无需登录，支持基本信息/教育背景/求职信息/简历上传，提交后自动入库
- **兼容路由保留**：`/upload` 仍可访问，但会自动跳转到 `/form`，避免 HR 端存在两个分散入口

### AI 特性
- **双模架构**：Mock LLM（零成本）/ 真实 LLM（OpenAI/DeepSeek/智谱）
- **自动回退**：任何 LLM 调用失败自动回退到 Mock 模式
- **5 套 Prompt 模板**：简历提取、摘要生成、标签生成、跟进建议、Copilot 系统指令
- **AI 初筛规则**：基于岗位、学校、学历、专业、技能、工作经历、自我介绍和简历文本进行岗位匹配度评分；不使用性别、年龄、民族、婚育等敏感信息作为筛选依据

---

## 二、项目目录结构

```
testin云测面试题/
├── .gitignore
├── .env.example                # 环境变量模板
├── docker-compose.yml          # Docker 编排
├── README.md                   # 项目说明
├── PROJECT_STATE.md            # 本文件
├── TODO_NEXT.md                # 后续优化建议
├── HANDOFF.md                  # 交接说明
├── 项目.txt                    # 原始面试题目
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py                  # 启动入口
│   ├── uploads/.gitkeep
│   └── app/
│       ├── __init__.py
│       ├── main.py             # FastAPI app（lifespan + CORS + 路由挂载）
│       ├── config.py           # pydantic-settings 配置
│       ├── database.py         # SQLAlchemy engine + init_db()
│       ├── seed_data.py        # 14 条种子数据
│       ├── models/
│       │   ├── candidate.py    # Candidate ORM（35 列）
│       │   └── activity_log.py # ActivityLog ORM（5 列）
│       ├── schemas/
│       │   ├── candidate.py    # 请求/响应 Pydantic 模型
│       │   └── dashboard.py    # 看板数据模型
│       ├── routers/
│       │   ├── candidates.py   # 候选人 CRUD
│       │   ├── resume.py       # 简历上传
│       │   ├── ai.py           # AI 功能
│       │   ├── screening.py    # AI 批量初筛
│       │   ├── dashboard.py    # 看板统计
│       │   ├── sync.py         # 数据同步
│       │   └── apply.py        # 在线投递（投递者表单提交）
│       ├── services/
│       │   ├── ai_service.py       # 统一 AI 网关（双模）
│       │   ├── mock_llm.py         # Mock LLM（正则+模板+规则引擎）
│       │   ├── candidate_service.py # 候选人业务逻辑
│       │   ├── followup_service.py  # AI 跟进建议与 Dashboard 跟进统计
│       │   ├── file_parser.py      # 文件解析（PDF/DOCX/TXT）
│       │   ├── dedup_service.py    # 三级去重
│       │   └── sync_adapter.py     # 数据同步 Adapter
│       └── prompts/
│           ├── resume_extraction.txt
│           ├── candidate_summary.txt
│           ├── auto_tagging.txt
│           ├── followup_suggestion.txt
│           └── copilot_system.txt
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts          # 代理 /api → localhost:8000
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx            # React 入口
│       ├── App.tsx             # 路由配置
│       ├── App.css
│       ├── index.css
│       ├── api/index.ts        # Axios API 封装
│       ├── types/index.ts      # TypeScript 类型定义
│       ├── utils/constants.ts  # 常量定义
│       ├── components/
│       │   ├── AppLayout.tsx       # 侧边栏布局
│       │   ├── StatsCards.tsx      # 统计卡片
│       │   ├── FunnelChart.tsx     # 招聘漏斗图
│       │   ├── ChannelPieChart.tsx # 渠道饼图
│       │   ├── FollowUpAlerts.tsx  # 跟进预警
│       │   ├── RecentLogs.tsx      # 操作日志
│       │   ├── DailySummary.tsx    # 今日摘要
│       │   ├── StageTag.tsx        # 阶段标签
│       │   └── CopilotChat.tsx     # Copilot 聊天
│       └── pages/
│           ├── Dashboard.tsx       # 主看板
│           ├── CandidateForm.tsx   # HR 统一新增候选人（手动录入 + 简历上传）
│           ├── ResumeUpload.tsx    # 旧简历上传页逻辑保留（当前路由已跳转 /form）
│           ├── CandidateList.tsx   # 候选人列表
│           ├── AIScreeningCenter.tsx # AI 初筛中心
│           ├── CandidateDetail.tsx # 候选人详情
│           ├── ApplyForm.tsx      # 投递者在线填写页
│           └── ApplyForm.css      # 投递页样式
│
├── docs/
│   ├── 业务方案.md
│   ├── Prompt工程与效果验证.md
│   ├── 系统架构说明.md
│   ├── 演示脚本.md
│   └── 答辩讲稿.md
│
├── prompts/                    # Prompt 设计文档（5 个 .md）
├── scripts/
│   ├── init_db.py              # 数据库初始化
│   ├── ensure_demo_data.py     # 后端启动时按需补齐演示数据
│   ├── reset_demo_data.py      # 手动重置演示数据
│   └── export_csv.py           # CSV 导出
├── start_backend.bat           # Windows 后端一键启动
├── start_frontend.bat          # Windows 前端 Vite 一键启动
│
└── sample_data/
    ├── sample_resume_1.txt
    ├── sample_resume_2.txt
    ├── sample_resume_3.txt
    └── sample_candidates.json
```

---

## 三、启动方式

### 方式 A：手动启动（开发模式）

```bash
# 终端 1 - 后端（先启动）
cd backend
pip install -r requirements.txt
python run.py
# → http://localhost:8000/docs (Swagger API 文档)

# 终端 2 - 前端
cd frontend
npm install
npm run dev
# → http://localhost:5173 (前端页面)
```

前端必须使用 Vite 开发服务器启动，不要使用 `python -m http.server` 打开 `frontend` 静态文件。`frontend/vite.config.ts` 已配置 `/api` 代理到 `http://localhost:8000`，否则页面无法访问后端演示数据。

### 方式 A-1：Windows 双击脚本

```bash
start_backend.bat
start_frontend.bat
# 前端：http://localhost:5173
# 后端 API：http://localhost:8000/docs
```

首次启动后端时，如果 `backend/recruit.db` 不存在或候选人表为空，系统会自动生成完整演示数据；已有候选人时不会清空数据库。

### 方式 B：Docker

```bash
docker-compose up --build
# 前端：http://localhost:3000
# 后端 API：http://localhost:8000/docs
```

### 独立脚本

```bash
python scripts/init_db.py        # 初始化数据库 + 种子数据
python scripts/export_csv.py     # 导出候选人 CSV
```

---

## 四、可访问页面和入口

| 页面 | 手动模式地址 | Docker 地址 | 说明 |
|------|-------------|-------------|------|
| Dashboard 看板 | http://localhost:5173/ 或 /dashboard | http://localhost:3000/ 或 /dashboard | 首页，统计+漏斗+预警 |
| 新增候选人 | http://localhost:5173/form | http://localhost:3000/form | HR 统一录入页，支持手动填写 + 简历上传 |
| /upload 兼容跳转 | http://localhost:5173/upload | http://localhost:3000/upload | 自动跳转到 `/form` |
| AI 初筛中心 | http://localhost:5173/ai-screening | http://localhost:3000/ai-screening | 批量初筛、推荐等级筛选、匹配度排序 |
| 候选人列表 | http://localhost:5173/candidates | http://localhost:3000/candidates | 岗位/阶段/来源/关键词组合筛选、分页 |
| 候选人详情 | http://localhost:5173/candidates/:id | http://localhost:3000/candidates/:id | AI 摘要/标签/建议 |
| 投递者在线填写 | http://localhost:5173/apply | http://localhost:3000/apply | 投递者自助填写表单 |
| Swagger API | http://localhost:8000/docs | http://localhost:8000/docs | 后端 API 文档 |

---

## 五、已修复的问题

### 第一轮：Python 3.9 兼容 + Docker 修复

1. **docker-compose.yml DATABASE_URL 路径错误**：`sqlite:///./recruit.db`（相对路径）改为 `sqlite:////app/data/recruit.db`（绝对路径），确保数据库在 Docker 持久卷内
2. **Python 3.9 兼容性**：将全部 `dict | None`、`list[str]`、`tuple[list[...], int]` 等 Python 3.10+ 语法改为 `Optional[dict]`、`List[str]`、`Tuple[List[...], int]`（使用 `typing` 模块），涉及 7 个文件

### 第二轮：前端 UI 联调 + Bug 修复

3. **[HIGH] 简历上传手机号空值导致 422**：mock LLM 提取不到手机号时返回空字符串 `""`，`.get("phone", "13800000000")` 拿到 `""` 而非默认值，正则校验失败。修复：改用 `or` 运算符 `.get("phone") or "13800000000"`
4. **[HIGH] CandidateList 搜索双重请求**：`setPage(1); loadData()` 中 setState 异步导致 loadData 用旧 page 值发请求，然后 useEffect 又发一次。修复：移除显式 `loadData()` 调用
5. **[HIGH] triggerSync 未 await**：`triggerSync()` 返回 Promise 但未 await，立即显示"同步成功"。修复：await + try/catch + 失败提示
6. **[MEDIUM] AI 重新生成无 catch**：`handleRegenSummary` 和 `handleRegenTags` 使用 try/finally 无 catch，API 失败时无用户反馈。修复：增加 catch + message.error
7. **[MEDIUM] getFollowup 每次加载时调用**：每次进入详情页都 POST AI 跟进建议，阻塞页面加载。修复：改为按需调用（"生成建议"按钮）
8. **[MEDIUM] Antd Spin tip 不显示**：antd v5 standalone Spin 不渲染 tip 文字。修复：移除 tip prop
9. **[LOW] 废弃的 bodyStyle 属性（3 处）**：antd v5 中 bodyStyle 已废弃。修复：改为 `styles={{ body: {...} }}`
10. **[LOW] 未使用的 imports（2 处）**：CandidateForm 中 Upload/UploadOutlined 未使用，CandidateList 中 STAGE_COLORS/StageTag 未使用。修复：删除

### 第三轮：Dashboard 统计刷新 + 候选人删除功能

11. **[HIGH] Dashboard 统计数据不随新增候选人更新**：`useEffect` 依赖数组为 `[]`，仅在组件首次挂载时拉取数据。当用户从其他页面导航回 Dashboard 时，某些场景下组件未重新挂载导致数据不刷新。修复：引入 `useLocation`，将 `location.key` 作为 `useEffect` 依赖，确保每次导航到 Dashboard 都重新拉取全部看板数据
12. **[MEDIUM] 候选人列表无删除功能**：后端 `DELETE /candidates/{id}` 接口和 `deleteCandidate` API 已存在，但前端列表页未提供删除按钮。修复：在列表增加「操作」列，含 `Popconfirm` 确认弹窗 + 删除按钮，删除成功后自动刷新列表

### 第四轮：TypeScript 构建修复 + HR 决策自动阶段流转

13. **[HIGH] TypeScript 构建失败**：`tsconfig.node.json` 缺少 `composite: true` 且 `noEmit: true` 与 composite 引用冲突。修复：添加 `composite: true`，将 `noEmit` 改为 `emitDeclarationOnly`
14. **[HIGH] 前后端阶段常量不一致**：后端用 `"待筛选"`、前端用 `"初筛"`，前端多了 `"待定"` 后端会返回 400。修复：前端 STAGES 统一为后端 VALID_STAGES，移除 `"待定"`
15. **[HIGH] HR 操作无法从前端触发**：`stage_service.execute_hr_action()` 和 `HR_ACTION_MAP` 已实现但无 HTTP 端点暴露。修复：添加 `POST /candidates/{id}/hr-action/{action_name}` 路由 + `candidate_service.execute_hr_action()` 方法
16. **[HIGH] `_to_read` 未返回 `stage_source` 和 `interview_time`**：前端无法显示阶段触发来源和面试时间。修复：在 `_to_read` 中补充这两个字段
17. **[MEDIUM] 简历上传后阶段停留在「新投递」**：上传解析完成后应自动推进到「待筛选」。修复：在 `create_from_resume` 末尾调用 `stage_service.change_stage` 自动推进
18. **[MEDIUM] 候选人详情页缺少 HR 决策入口**：只有手动下拉框选择阶段，没有语义化的 HR 操作按钮。修复：添加 6 个 HR 决策按钮 + 面试时间设置弹窗 + 阶段变更记录展示 + 触发来源标签
19. **[MEDIUM] 无阶段变更记录展示**：StageChangeLog 表已记录数据但前端无展示入口。修复：添加 `GET /candidates/{id}/stage-logs` 端点 + 前端阶段变更记录卡片

### 第五轮：Dashboard 最近操作日志同步修复

20. **[HIGH] 改状态后 Dashboard 最近操作日志不同步**：看板最近日志读的是 `ActivityLog`，阶段审计读的是 `StageChangeLog`，两条链路未统一；同时旧种子日志存在未来时间戳，导致新状态日志可能排不到最前。修复：Dashboard 最近日志改为统一合并 `StageChangeLog + 非阶段类 ActivityLog`，阶段变更统一返回结构化字段；启动时执行日志迁移，回填历史阶段日志、修正旧阶段名并清理未来时间戳
21. **[HIGH] 系统自动阶段更新只在详情页触发**：`check_auto_interview_start()` 仅在 `get_candidate()` 执行，导致列表页和 Dashboard 访问时看不到最新自动阶段和对应日志。修复：在候选人列表、Dashboard 统计、跟进预警、最近日志、今日摘要查询前统一补跑待执行的自动阶段更新
22. **[MEDIUM] 新状态日志在同秒内可能被旧日志压住**：SQLite 默认时间戳为秒级，新日志和旧日志同秒时排序不稳定。修复：阶段变更与普通操作日志统一改为写入 Python 精确时间戳，保证最新状态变更在 Dashboard 置顶
23. **[MEDIUM] 种子数据阶段名和阶段日志不完全一致**：seed 中仍有 `"初筛"`/`"待定"` 旧值，且当天种子日志可能写到未来时间。修复：种子数据阶段名统一为当前常量，同时补充 StageChangeLog 种子记录并将日志时间钳制到当前时间

### 第六轮：在线投递简历附件详情可见

24. **[HIGH] /apply 上传的简历在候选人详情页不可见**：在线投递虽然已保存文件并写入 `resume_path`，但候选人详情接口未返回原始文件名、文件类型、文件大小、查看/下载地址，前端也没有附件展示区。修复：候选人模型新增 `resume_filename`、`resume_file_type`、`resume_file_size`、`resume_uploaded_at` 字段，详情接口统一返回 `resume_url`
25. **[MEDIUM] 简历上传与在线投递两条入口附件元数据不一致**：`/resume/upload` 和 `/apply` 原先都只保留存储路径。修复：新增 `candidate_service.attach_resume()`，统一写入简历路径、原始文件名、类型、大小、上传时间，复用现有 `/uploads` 静态访问
26. **[MEDIUM] 候选人详情页缺少附件查看/下载入口**：HR 无法在详情页直观看到简历。修复：新增“简历附件”区域，支持 PDF/TXT 新标签页查看，PDF/DOCX/TXT 下载；未上传简历时显示“未上传简历”

### 第七轮：修复 /apply 简历未实际上传

27. **[HIGH] 投递页选择了简历但提交时未真正上传文件**：`ApplyForm` 在 `beforeUpload` 中把原始 `RcFile` 直接强转成 `UploadFile` 放入 `fileList`，导致 `originFileObj` 丢失；提交时 `FormData` 判断 `fileList[0].originFileObj` 为 `undefined`，后端实际收不到文件。修复：在 `beforeUpload` 中显式构造带 `originFileObj` 的 `UploadFile`，提交时稳定从该字段追加到 `FormData`

### 第八轮：HR 端统一新增候选人页

28. **[HIGH] HR 端存在“候选人录入”和“简历上传”两个分散入口**：容易造成流程分裂，也无法保证文件与候选人记录统一关联。修复：将 `/form` 改为“新增候选人”统一页，支持手动录入 + 可选简历上传；侧边栏合并为单一菜单项“新增候选人”
29. **[HIGH] HR 后台上传简历时无法同时提交手动字段并关联附件**：旧 `/upload` 仅做 AI 预览确认，不会复用手动录入字段，也不保证简历文件与最终候选人记录绑定。修复：新增 `POST /api/candidates/hr-create` 多部分表单接口，统一创建候选人、保存简历附件并返回详情字段
30. **[MEDIUM] AI 简历解析会与 HR 手填内容冲突**：合并录入页后需要避免覆盖 HR 已填信息。修复：前后端都改为“AI 只补全空字段”，保留已填写内容不被覆盖
31. **[MEDIUM] HR 新增候选人日志不够直观**：Dashboard 最近日志中难以区分后台手动新增。修复：HR 后台新增统一写入 `HR新增候选人：姓名（渠道：xxx）`，创建后 Dashboard / 列表 / 详情数据保持一致

### 第十轮：AI 批量初筛中心

32. **[HIGH] HR 无法批量处理大量简历初筛**：新增候选人初筛字段 `match_score`、`priority_level`、`screening_result`、`screening_reason`、`risk_flags`、`screening_updated_at`，启动迁移自动补齐旧库字段
33. **[HIGH] 缺少岗位匹配度评分能力**：新增 Mock/LLM 初筛服务，基于岗位、学校、学历、专业、技能、工作经历、自我介绍和简历文本生成 0-100 分匹配度；80+ 为高优先级，60-79 为中优先级，60 以下为低优先级
34. **[HIGH] 缺少批量初筛 API 和结果查询 API**：新增 `POST /api/screening/run`、`POST /api/screening/run/{candidate_id}`、`GET /api/screening/results`
35. **[MEDIUM] HR 缺少高匹配候选人处理入口**：新增 `/ai-screening` 页面，支持批量初筛、单人重新初筛、按推荐等级筛选、按匹配度排序、跳转候选人详情，高优先级候选人突出展示
36. **[MEDIUM] 主列表和看板缺少初筛信息**：候选人列表增加紧凑 AI 初筛列；Dashboard 增加高/中/低优先级、平均匹配度和尚未初筛统计

### 第十一轮：候选人列表岗位筛选增强

37. **[HIGH] 候选人列表无法按岗位分类查看**：后端候选人列表接口新增 `target_role` 查询参数，支持与阶段、来源、关键词组合筛选，筛选后分页总数正确
38. **[MEDIUM] 岗位筛选选项不能写死**：新增 `GET /api/candidates/filter-options`，从当前候选人数据动态返回岗位和来源选项
39. **[MEDIUM] 关键词搜索覆盖字段不足**：关键词搜索扩展为姓名、手机号、邮箱、学校、专业、应聘岗位、技能关键词
40. **[MEDIUM] Dashboard 缺少岗位维度视图**：Dashboard 新增“岗位分布”模块，展示每个岗位候选人数、高优先级人数和待跟进人数；新增“今日建议跟进”轻量模块

### 第十二轮：候选人批量处理

41. **[HIGH] HR 无法一次处理多个候选人**：候选人列表新增行复选框、表头全选/取消全选、已选择人数和批量操作栏
42. **[HIGH] 缺少批量阶段处理接口**：新增 `POST /api/candidates/batch/status`，支持批量通过初筛、批量标记待约面、批量淘汰，操作来源为 `hr_action`
43. **[HIGH] 批量淘汰需要高风险确认**：前端新增批量淘汰二次确认弹窗，可填写淘汰原因，取消后不会修改数据
44. **[MEDIUM] 缺少选中候选人导出能力**：新增 `POST /api/candidates/batch/export`，只导出当前选中候选人 CSV，字段包含基础信息、阶段、来源、AI 摘要、AI 跟进建议和创建时间
45. **[MEDIUM] 批量生成跟进建议缺少操作入口**：新增 `POST /api/candidates/batch/followup`，对选中候选人生成最新跟进建议并写入操作日志

### 第十三轮：招聘岗位管理与投递岗位标准化

46. **[HIGH] /apply 应聘岗位自由输入导致数据失真**：新增 `jobs` 岗位表和 `job_id` 候选人字段；投递者端 `/apply` 改为从 `GET /api/jobs/active` 实时加载启用岗位下拉，提交时必须传 `job_id`，后端校验岗位存在且为 `active`
47. **[HIGH] 缺少 HR 岗位选项统一维护入口**：新增 `/jobs` 岗位管理页，支持查看、新增、编辑、启用/停用、谨慎删除；所有操作写入后端数据库并刷新列表
48. **[HIGH] 岗位改名可能影响历史候选人展示**：候选人提交时同时保存 `job_id` 和当时岗位名称快照 `target_role`；岗位后续改名/停用不回写历史候选人的 `target_role`
49. **[MEDIUM] HR 新增候选人仍可随意输入岗位**：HR 统一新增候选人页默认优先从岗位库选择岗位，特殊情况保留“其他/手动输入”；选岗位时同样保存 `job_id + target_role`
50. **[MEDIUM] 筛选和看板需兼容岗位库与历史数据**：候选人列表岗位筛选选项合并岗位库标题和真实候选人历史岗位，Dashboard 岗位分布继续基于候选人 `target_role` 快照统计，停用岗位不影响历史显示和筛选

### 第十四轮：HR 决策操作业务化

51. **[HIGH] HR 决策按钮过于简单，缺少业务表单**：候选人详情页的安排面试、进入复试、发放 Offer、确认入职、淘汰均改为弹窗提交；安排面试必填面试时间，淘汰必填淘汰原因
52. **[HIGH] 关键招聘动作缺少结构化数据落库**：候选人模型新增面试方式/面试官/面试备注、复试反馈/复试时间/复试面试官、Offer 岗位/薪资/预计入职/Offer 备注、实际入职时间/入职备注、淘汰原因/淘汰备注等字段，并通过启动迁移补齐旧库
53. **[HIGH] 终态候选人仍可继续推进流程**：后端禁止对「入职」「淘汰」候选人继续执行 HR 流程推进；前端同步禁用全部流程推进按钮，只保留阶段人工修正和日志查看
54. **[MEDIUM] 当前阶段可执行动作缺少限制**：前后端均按阶段限制 HR 动作：新投递/待筛选可通过筛选或淘汰，待约面可安排面试，已约面/面试中可进入复试或淘汰，复试可发 Offer 或淘汰，offer 可确认入职或淘汰
55. **[MEDIUM] 详情页缺少面试/Offer/入职/淘汰信息展示**：候选人详情页新增“招聘流程信息”区域，仅在存在对应数据时展示，避免空表格
56. **[MEDIUM] CSV 同步未包含关键流程字段**：LocalSheetAdapter 和导出脚本增加面试、Offer、入职、淘汰关键字段，HR 动作后同步数据更完整

### 第十五轮：AI 初筛中心投递时间筛选

57. **[HIGH] AI 初筛中心缺少投递时间信息**：初筛结果接口和前端列表新增候选人 `created_at`，页面展示“投递时间”列，格式为 `YYYY-MM-DD HH:mm`
58. **[HIGH] 无法按投递时间处理候选人**：`GET /api/screening/results` 支持 `date_range`、`start_date`、`end_date`、`sort_by=created_at`、`sort_order=desc|asc`；前端新增“全部时间 / 今日投递 / 本周投递 / 最近 7 天 / 最近 30 天”筛选
59. **[MEDIUM] 初筛排序只偏向匹配度**：AI 初筛中心排序下拉新增“最新投递优先”和“最早投递优先”，默认改为最新投递优先，同时保留匹配度从高到低、匹配度从低到高、最近初筛优先
60. **[HIGH] 批量初筛未联动筛选范围**：`POST /api/screening/run` 支持与结果列表相同的岗位、推荐等级和投递时间筛选参数；前端批量初筛只处理当前筛选范围内未初筛候选人，并在执行前二次确认

### 第十六轮：岗位要求配置驱动 AI 初筛

61. **[HIGH] AI 初筛缺少岗位要求依据**：`jobs` 表新增必备技能、加分技能、学历要求、经验要求、岗位关键词、风险提示关键词字段；岗位管理页可维护这些字段并写入后端数据库
62. **[HIGH] 初筛评分未优先参考岗位标准**：AI 初筛时通过候选人 `job_id` 读取对应岗位配置，历史数据无 `job_id` 时按岗位名称兜底匹配；Mock/回退评分逻辑基于必备技能命中率、加分技能、学历/经验要求、岗位关键词和风险关键词计算分数
63. **[MEDIUM] 初筛理由不够可追溯**：初筛理由增加岗位要求来源、必备技能命中、加分技能命中和岗位关键词命中说明；风险提示会标记必备技能不足、学历/经验未达标、风险关键词命中等
64. **[MEDIUM] AI 初筛中心无法查看岗位标准**：初筛列表新增“匹配依据”列，并提供“查看岗位标准”弹窗，展示当前岗位的必备技能、加分技能、学历/经验要求、岗位关键词、风险关键词、岗位描述和岗位要求

### 第十七轮：超时未跟进提醒

65. **[HIGH] HR 容易遗漏长期未处理候选人**：`followup_service` 新增统一超时规则，按候选人当前阶段和最近动作时间计算 `is_overdue`、`overdue_days`、`overdue_reason`、`last_action_at`
66. **[HIGH] Dashboard 缺少超时跟进概览**：Dashboard 今日建议跟进模块新增“超时未跟进”“今日待跟进”“高优先级跟进”“超过3天未跟进”统计；跟进预警模块改为展示真实超时候选人
67. **[MEDIUM] 候选人列表无法快速识别超时项**：候选人列表 AI 跟进列新增“超时”标签、超时天数、跟进优先级和超时原因
68. **[MEDIUM] 候选人详情缺少当前超时说明**：详情页 AI 跟进建议卡片新增超时提醒，展示超时天数、超时原因和系统跟进建议
69. **[MEDIUM] 终态候选人仍可能误提醒**：入职/淘汰阶段统一不再触发超时提醒；状态变化、备注更新、安排面试、HR 决策操作后通过 `updated_at`/阶段日志自动重新计算

### 第十八轮：最近新增候选人高亮

70. **[HIGH] HR 难以从大量候选人中快速识别新投递**：候选人列表新增“今日新增 / 新投递”标签，最近新增行轻微高亮，并保留表格可读性
71. **[HIGH] 列表缺少今日新增筛选与明确投递时间**：候选人列表新增“今日新增”筛选，明确展示投递时间、来源渠道和是否今日新增；默认继续按投递时间倒序排列
72. **[MEDIUM] Dashboard 缺少最近新增入口**：Dashboard 新增“最近新增候选人”模块，展示今日新增人数、最近 3 天新增人数和今日新增候选人列表（最多 5 条）
73. **[MEDIUM] 在线投递/HR录入来源识别不够直观**：来源列对 `在线投递` 显示绿色“在线投递”标签，对 `HR手动录入` 显示蓝色“HR录入”标签

### 第十九轮：面试反馈 AI 总结

74. **[HIGH] 面试后反馈零散，HR 需要手动整理结论**：候选人详情页新增“面试反馈 AI 总结”区域，可录入原始反馈、面试官、面试轮次和反馈时间
75. **[HIGH] 缺少结构化面试反馈总结能力**：新增 AI/mock 面试反馈总结，输出技术能力总结、沟通表达总结、岗位匹配度判断、风险点、推荐结论和下一步建议
76. **[MEDIUM] AI 总结需要可追溯保存**：候选人模型新增面试反馈与 AI 总结字段，生成结果保存到候选人记录；重新进入详情页仍可查看
77. **[MEDIUM] 生成 AI 面试总结缺少日志**：生成后写入操作日志 `ai_interview_summary`，详情页操作日志和 Dashboard 最近操作日志可见

### 第二十轮：演示数据与详情信息增强

78. **[MEDIUM] 演示候选人详情信息偏少**：新增 5 条在线投递候选人，补充更完整的工作经历、自我介绍、技能、AI 摘要和 HR 备注
79. **[MEDIUM] 默认岗位缺少业务描述**：默认岗位补充岗位描述和任职要求；已有数据库启动时会自动补齐空缺描述
80. **[LOW] AI 初筛中心匹配依据命名优化**：前端列名统一为“匹配依据”，弹窗入口改为“查看岗位标准”
81. **[LOW] 候选人详情可读信息密度不足**：详情页新增“投递与 AI 初筛信息”卡片，集中展示匹配度、推荐等级、初筛理由、风险提示、跟进日期和最近动作时间

### 第二十一轮：AI 初筛统计口径统一

82. **[HIGH] Dashboard 与 AI 初筛中心人数不一致**：根因是 AI 初筛列表和统计过滤了 `is_duplicate == False`，而 Dashboard 候选人总数按候选人主表全部记录统计；修复后 AI 初筛不再排除重复标记候选人
83. **[HIGH] AI 初筛统计缺少总人数与已初筛人数**：后端 `get_screening_stats()` 统一返回总候选人数、已初筛人数、尚未初筛人数、高/中/低优先级人数和平均匹配度
84. **[MEDIUM] 前端 AI 初筛统计由当前列表临时计算，容易与后端口径不一致**：`/api/screening/results` 返回 `overall_stats` 与 `stats`；前端顶部展示全部统计，筛选后单独展示当前筛选结果统计
85. **[MEDIUM] 未初筛候选人口径不稳定**：统一按 `总候选人数 - 高优先级 - 中优先级 - 低优先级` 计算尚未初筛，确保四类加总等于总候选人数

### 第二十二轮：AI 初筛中心当前筛选统计彻底统一

86. **[HIGH] 表格有候选人但蓝色统计框显示 0 人**：前端不再依赖后端 `stats` 渲染当前筛选统计，而是直接基于当前表格 `items` 计算，保证“当前 X 人”和蓝色统计框同源
87. **[HIGH] 批量初筛范围与当前筛选结果可能不一致**：批量初筛提示和执行参数改为当前筛选结果范围；当前结果 14 人时提示处理 14 人，已初筛候选人会重新生成结果
88. **[MEDIUM] 缺少初筛状态筛选**：AI 初筛中心新增“已初筛 / 尚未初筛”筛选；后端 `/api/screening/results` 和 `/api/screening/run` 支持 `screening_status`
89. **[MEDIUM] screened/unscreened 判定不统一**：统一为有 `match_score` 或非空 `priority_level` 算已初筛；两者都为空算尚未初筛；有分数但无等级时计入低优先级，确保加总闭合

### 第二十三轮：招聘漏斗初筛流转改造

90. **[HIGH] 新投递候选人直接进入候选人列表，业务漏斗不真实**：新增 `screening_status` 主状态，/apply 与 HR 新增默认 `pending` + 「新投递」，候选人先进入 AI 初筛中心；候选人列表默认只展示 `passed`
91. **[HIGH] AI 初筛中心缺少 HR 最终初筛动作**：新增通过初筛、初筛淘汰接口和前端按钮；通过初筛后 `screening_status=passed`、阶段进入「待约面」，初筛淘汰要求填写原因并保留主记录
92. **[HIGH] Dashboard 总投递人数和候选人列表人数容易混淆**：Dashboard 新增待初筛、通过初筛、正式流程备选、初筛淘汰、正式流程候选人数；总投递人数继续按候选人主表全部记录统计
93. **[MEDIUM] 候选人列表阶段筛选包含新投递/待筛选**：候选人列表阶段筛选改为正式流程阶段：待约面、已约面、面试中、复试、offer、入职、淘汰
94. **[MEDIUM] 历史数据缺少初筛流转状态**：启动迁移自动补齐 `screening_status`；新投递/待筛选回填 pending，正式流程阶段回填 passed，淘汰回填 rejected

### 第二十四轮：岗位一致的 Demo 数据重置脚本

95. **[HIGH] 演示候选人岗位可能与岗位管理不一致**：新增 `scripts/reset_demo_data.py`，候选人只从 active 岗位库选择岗位，并同时写入 `job_id` 与岗位标题快照 `target_role`
96. **[HIGH] Demo 前缺少一键恢复干净数据能力**：脚本会清空候选人主表、阶段日志、操作日志和旧上传附件，保留岗位表与系统配置，然后生成 30 条候选人和 21 份 TXT 简历附件
97. **[MEDIUM] 岗位库 Demo 覆盖不足**：脚本按同名不重复规则补齐并激活测试工程师、自动化测试工程师、AI应用实习生、数据分析师、前端开发工程师、后端开发工程师、产品助理、UI设计师，并补充岗位要求字段
98. **[MEDIUM] Demo 数据不能展示招聘漏斗差异**：脚本生成 pending 11 人、formal backup 3 人、rejected 1 人、passed 15 人；AI 初筛中心默认只显示 11 名 pending，候选人列表正式流程默认展示 14 人，备选视图 3 人，淘汰视图展示初筛淘汰和正式流程淘汰共 2 人
99. **[MEDIUM] 最近新增、投递时间筛选、超时未跟进缺少演示数据**：脚本生成今日新增 5 人、最近 3 天 10 人、本周 20 人、历史 10 人，并构造新投递/待约面/已约面/offer 超时提醒场景

### 第二十五轮：候选人列表范围筛选简化

100. **[MEDIUM] 候选人列表范围筛选包含全部/待初筛，容易与 AI 初筛中心职责混淆**：前端范围筛选只保留正式流程候选人、备选候选人、淘汰候选人，移除全部候选人和待初筛候选人
101. **[MEDIUM] 正式流程默认视图混入淘汰候选人**：后端 `candidate_scope=formal` 改为 `screening_status=passed AND stage != 淘汰`；淘汰视图统一展示 `screening_status=rejected OR stage=淘汰`
102. **[LOW] 阶段筛选仍出现不属于候选人列表的初筛阶段**：候选人列表正式流程阶段筛选只保留待约面、已约面、面试中、复试、offer、入职；备选/淘汰视图隐藏阶段筛选
103. **[LOW] 批量操作与当前视图不匹配**：正式流程视图保留批量标记备选、批量标记待约面、批量淘汰、导出、生成跟进建议；备选视图保留批量淘汰、导出；淘汰视图仅保留导出

### 第二十六轮：AI 初筛中心移除备选逻辑

104. **[MEDIUM] AI 初筛中心出现备选统计和标记备选按钮，职责边界不清**：AI 初筛中心移除备选统计、备选筛选项和每行“标记备选”按钮，默认查询改为 `decision_status=pending`，只处理新投递/待初筛候选人
105. **[MEDIUM] 备选应属于正式流程管理**：`/api/candidates/{id}/screening/backup` 改为仅允许 `screening_status=passed` 且未淘汰候选人调用；候选人列表正式流程视图新增批量标记备选，备选视图展示正式流程备选候选人
106. **[LOW] Demo 数据仍把 backup 放在 AI 初筛池**：`scripts/reset_demo_data.py` 改为生成 11 名 pending 待初筛、3 名已通过后标记的正式流程备选；AI 初筛默认池不再包含 backup

### 第二十七轮：新电脑交付启动与演示数据自动兜底

107. **[HIGH] 前端用 Python http.server 无法代理 API**：明确交付启动方式必须使用 Vite；`frontend/vite.config.ts` 已配置 `/api -> http://localhost:8000`，README 新增禁止使用 `python -m http.server` 的说明
108. **[HIGH] 新电脑空库启动看不到演示数据**：新增 `scripts/ensure_demo_data.py`，后端 lifespan 调用该脚本；候选人表为空时复用 `reset_demo_data.py` 生成 30 条候选人和简历附件，已有候选人时跳过
109. **[HIGH] SQLite 相对路径可能读写不一致**：`backend/app/config.py` 将默认数据库固定到 `backend/recruit.db`，并把相对 `DATABASE_URL` / `UPLOAD_DIR` 解析到 `backend/`
110. **[MEDIUM] 缺少 Windows 交付启动入口**：新增 `start_backend.bat` 与 `start_frontend.bat`，分别安装依赖并启动 `python run.py`、`npm.cmd run dev`

---

## 六、当前已知问题

1. ~~**TypeScript 生产构建未验证**~~：✅ 已修复并验证通过（第四轮）
2. **Docker 端到端部署未验证**：`docker-compose up --build` 未实际执行过（本机未安装 Docker，配置已审查无问题）
3. **根目录多余的 package-lock.json**：项目根目录存在一个 `package-lock.json`，应该只在 `frontend/` 下才对，可能是误生成的
4. **种子数据日期固定**：seed_data 中的日期按 `days_ago` 计算，每次重新初始化时日期会变化
5. **后端部分代码质量问题**（不影响功能）：
   - Dashboard 路由未使用 response_model，OpenAPI 文档不显示响应模型
   - `_run_ai` 和 `_sync` 中 bare `except Exception: pass` 吞掉所有异常
   - StageUpdate.validate_stage() 是死代码（普通方法而非 Pydantic validator）

---

## 七、适合演示的页面

按推荐演示顺序：

1. **Dashboard 看板**（/ 或 /dashboard）— 最直观，一眼看到全局数据
2. **新增候选人**（/form）— 演示 HR 手动录入和上传简历补全空字段
3. **候选人详情**（/candidates/1）— 展示 AI 摘要、标签、跟进建议、简历附件
4. **岗位管理**（/jobs）— 展示 HR 维护岗位库，并联动投递者岗位下拉
5. **候选人列表**（/candidates）— 展示筛选、最近新增高亮、分页、内联编辑
6. **Copilot 聊天** — 在任意页面底部展示自然语言问答
7. **投递者在线填写**（/apply）— 独立页面，模拟投递者视角自助填写

详细演示流程见 `docs/演示脚本.md`。
