# 阶段 4：简历上传与文件解析 — 设计文档

> **日期**: 2026-08-07
> **状态**: 设计确认，待实施
> **对应实施计划**: `docs/planning/implementation-plan.md` 阶段 4
> **权威设计文档**: `docs/architecture/2026-07-15-hr-agent-platform-design.md`

---

## 1. 目标

让 HR 能在新版简历管理页上传简历文件（PDF/Word/TXT），系统把文件安全保存下来，提取出文字内容，并自动创建一条候选人记录。

本阶段只做文件接收和文字提取。用 AI 把文字变成结构化数据（姓名、学历、工作经历等）是阶段 5 LangGraph 的事。

## 2. 范围

### 做什么

- 新版简历上传接口：接收文件、校验、保存到磁盘
- 迁移并复用旧版 `file_parser.py`，支持 PDF、DOCX、TXT 文字提取
- 上传时自动创建候选人初始记录
- 创建简历记录，保存文件元数据和提取出的文字
- 记录解析状态：`uploaded` → `parsing` → `parsed` / `failed`
- 前端简历管理页启用上传按钮，对接新接口

### 不做什么

- 不做 AI 结构化解析（阶段 5）
- 不做候选人投递页的上传（阶段 11）
- 不修改旧版 `/api/resume/upload` 接口
- 不移动、删除或覆盖 `backend/uploads/` 中已有的旧文件
- 不调用 LLM 或 LangGraph

## 3. 接口设计

### 3.1 上传接口

```
POST /api/v2/resumes/upload
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | 简历文件 |
| `job_id` | int | 否 | 关联岗位 ID |
| `source` | string | 否 | 来源渠道，默认 "HR上传" |

### 3.2 文件校验规则

- 允许格式：`.pdf`、`.docx`、`.txt`
- 大小上限：10MB
- 格式或大小不通过时，直接拒绝，不保存文件

### 3.3 成功响应

```json
{
  "candidate_id": 31,
  "resume_id": 1,
  "filename": "张三简历.pdf",
  "file_path": "v2/20260807_a3f1b2c4_张三简历.pdf",
  "file_type": "pdf",
  "file_size": 102400,
  "parse_status": "parsed",
  "text_preview": "张三，男，5年Java开发经验...",
  "message": "上传成功"
}
```

### 3.4 失败响应

```json
{
  "detail": "不支持的文件格式，仅允许 PDF、DOCX、TXT"
}
```

## 4. 文件存储规则

### 4.1 存储位置

新版上传的文件统一存放在 `backend/uploads/v2/` 目录下，与旧版文件隔离。

```
backend/uploads/
  ├── demo_resume_01_林悦.txt        ← 旧文件，不动
  ├── demo_resume_02_张明轩.txt
  └── v2/                            ← 新版文件
      ├── 20260807_a3f1b2c4_张三简历.pdf
      └── 20260808_e5d6f7a8_李四简历.docx
```

### 4.2 文件命名

格式：`{日期}_{8位随机ID}_{原始文件名}`

- 日期：`YYYYMMDD`，上传当天
- 随机 ID：UUID 前 8 位，防止同名文件冲突
- 原始文件名：保留 HR 上传时的文件名，方便在磁盘上识别

### 4.3 数据库中的路径

`Resume.file_path` 存储相对路径，如 `v2/20260807_a3f1b2c4_张三简历.pdf`，不存绝对路径。实际读取时拼接 `UPLOAD_DIR` 前缀。

## 5. 业务流程

### 5.1 上传处理流程

```
HR 选择文件并上传
  → 校验文件格式和大小
  → 不通过 → 返回错误，不保存文件
  → 通过 → 保存文件到 uploads/v2/
  → 创建候选人记录（source、applied_job_id）
  → 创建简历记录（状态 uploaded）
  → 数据库写入失败 → 删除已保存的文件，返回错误
  → 提取文字（file_parser）
  → 提取失败 → 更新简历状态为 failed，记录错误原因，返回成功但标记失败
  → 提取成功 → 更新简历状态为 parsed，保存 raw_text，返回成功
```

### 5.2 候选人自动创建

上传文件时自动创建一条候选人记录：

- `name`：从原始文件名尝试提取（如 `张三简历.pdf` → `张三`），提取不到则填"待补充"
- `source`：使用上传时传入的来源，默认 "HR上传"
- `applied_job_id`：使用上传时传入的 job_id（可选）
- `status`：默认 `new`

后续阶段 5 AI 解析后会补全姓名、手机号、学历等信息。

### 5.3 多份简历

一个候选人可以有多份简历记录，全部保留。阶段 4 每次上传都创建新候选人，暂时不会出现一人多简历的情况，但数据模型已支持。

## 6. 失败处理规则

| 失败环节 | 磁盘文件 | 数据库记录 | 响应 |
|---------|---------|-----------|------|
| 格式/大小不通过 | 不保存 | 不创建 | 400 错误原因 |
| 文件保存成功，数据库写入失败 | 删除文件 | 不存在 | 500 错误原因 |
| 都成功，文字提取失败 | 保留 | 保留，parse_status=failed | 200 成功但标记解析失败 |

## 7. 文件解析器迁移

复用旧版 `backend/app/services/file_parser.py`，迁移到新版 `backend/app/core/file_parser.py`。

旧版 `FileParser` 支持：
- PDF：使用 PyPDF2 逐页提取文字
- DOCX：使用 python-docx 提取段落文字
- TXT：使用 chardet 检测编码后读取

迁移时保持核心逻辑不变，调整导入路径即可。旧版 `file_parser.py` 不删除，旧接口继续使用旧版。

## 8. 代码修改范围

### 后端新增

- `backend/app/core/file_parser.py` — 迁移文件解析器
- `backend/app/services/rebuilt/resume_upload_service.py` — 上传业务逻辑（文件保存 + 创建记录 + 文字提取）
- `backend/app/api/resumes.py` — 新增 `POST /upload` 端点（在现有文件中追加）
- `backend/app/schemas/rebuilt/resume.py` — 新增 `ResumeUploadResponse` 响应模型

### 后端不修改

- 旧版 `backend/app/routers/resume.py`
- 旧版 `backend/app/services/file_parser.py`
- 现有 Alembic migration（不需要新 migration，表结构已支持）
- `backend/uploads/` 中的旧文件

### 前端修改

- `frontend/src/stage3/pages/Stage3ResumeList.tsx` — 启用上传按钮，对接新接口
- `frontend/src/stage3/services/` — 新增上传 API 调用封装

## 9. 验证方式

- 上传 PDF、DOCX、TXT 各一个样例文件，确认文字提取成功
- 确认候选人和简历记录写入 PostgreSQL
- 确认上传格式不支持的文件被拒绝
- 确认超过 10MB 的文件被拒绝
- 确认前端上传按钮可用，上传后列表刷新能看到新记录
- 后端回归测试全部通过
