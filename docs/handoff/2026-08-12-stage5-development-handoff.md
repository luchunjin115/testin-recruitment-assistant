# 阶段 5 完整开发方案与换电脑交接手册

> 项目：AI 招聘助手（`testin-recruitment-assistant`）  
> 日期：2026-08-12  
> 当前分支：`1lcj`  
> 当前进度：阶段 5 第一、第二小步已完成；下一步只实现 DeepSeek Adapter  
> 适用对象：在另一台电脑继续开发的本人、协作者或新的编码 Agent

## 0. 最重要的交接提醒

### 0.1 当前阶段 5 修改可能尚未提交

编写本文件时，阶段 5 相关代码和文档仍在 Git 工作区中，不能假设它们已经存在于远程仓库。换电脑前必须选择一种安全方式把这些修改带过去：

1. 当前计划：核对 diff 后创建正常 Git commit，再 push 到自己的远程分支。
2. 或者：完整复制整个项目目录，包括未跟踪文件和 `.git`。
3. 不要只复制 Git 已跟踪文件；阶段 5 的多个新文件当前可能仍是未跟踪状态。

禁止使用 `git reset --hard`、`git clean`、`git checkout -- <file>` 丢弃当前修改。

推送完成后，在原电脑核对：

```powershell
git status --short
git branch --show-current
git log --oneline -3
git status -sb
```

理想结果是工作区没有待提交文件，`git status -sb` 显示当前分支已经与远端对应分支同步。若仍有文件，不要删除，先确认是否漏提交或漏推送。

在另一台电脑恢复时，应拉取同一个远端和同一个分支。不要只根据分支名字猜测，先检查：

```powershell
git remote -v
git branch --show-current
git status -sb
git log --oneline -5
```

### 0.2 新电脑开始修改前必须阅读

按以下顺序完整阅读：

1. `AGENTS.md`
2. `CLAUDE.md`
3. `PROJECT_STATE.md`
4. `docs/implementation-plan.md`
5. `docs/specs/2026-07-15-hr-agent-platform-design.md`
6. `docs/specs/2026-08-12-stage5-resume-structure-design.md`
7. `docs/specs/2026-08-12-stage5-resume-draft-field-mapping.md`
8. 本文件

然后执行只读检查：

```powershell
git branch --show-current
git status --short
git diff --stat
git diff
```

### 0.3 Resume 38 与自动清理规则

阶段 4 已实现正常业务规则：未绑定 Candidate 且超过 24 小时的 Resume 会被自动清理。Resume 38 在最后核对时仍是：

```text
id = 38
candidate_id = NULL
parse_status = parsed
raw_text = 已存在
structure_status = not_started
```

它已经可能符合 24 小时自动清理条件。自动清理它属于产品预期，不是程序错误；但开发和集成测试不得把 Resume 38 当成删除、回滚或破坏性测试数据。

需要保留它进行人工验收时，启动正式 FastAPI 前显式使用：

```powershell
$env:RESUME_CLEANUP_ENABLED='false'
```

这只是人工验收期间的临时保护，不能静默修改正式产品默认规则。数据库 migration 本身不需要启动 FastAPI，因此不应为了迁移而启动清理器。

## 1. 阶段 5 要解决的问题

阶段 4 已经能把 PDF、DOCX、TXT 安全转换为 `Resume.raw_text`。阶段 5 只负责把原文变成经过严格检查的结构化草稿，并辅助 HR 填写新增候选人表单。

完整业务链路：

```text
Resume.raw_text
→ 一次 DeepSeek 调用
→ 检查响应非空和 finish_reason
→ json.loads
→ Pydantic v2 严格 Schema 校验
→ 业务规则校验
→ 保存 Resume.parsed_snapshot 草稿
→ 只补充前端空字段
→ HR 检查、修改、选择经历
→ HR 确认
→ 创建 Candidate、Education、WorkExperience、ProjectExperience
→ 绑定 Resume
```

这里的关键区别是：

```text
AI 输出 = 草稿
HR 确认后的数据 = 正式业务数据
```

AI 永远不能直接创建或修改正式 Candidate 和三类经历。

## 2. 已确定且不能随意改变的技术决定

1. 第一版不使用 Agent、LangGraph 或 MCP。
2. 通过项目内部 DeepSeek Adapter 直接调用 DeepSeek 的 OpenAI 兼容 API。
3. 一次正常识别只调用一次 DeepSeek。
4. 网络失败、超时、限流、空响应、JSON 截断或校验失败时不自动连续调用模型。
5. 只有 HR 明确点击“重新识别”，才允许产生一次新的调用。
6. 使用 DeepSeek JSON Output：`response_format={"type": "json_object"}`。
7. JSON Output 不是可信保证；返回内容仍必须依次通过响应检查、`json.loads`、严格 Schema 和业务校验。
8. 所有草稿 Schema 使用 `extra="forbid"`，禁止未知字段静默进入系统。
9. 成功结果保存为 `ResumeParseDraft` 草稿；不能直接创建正式候选人。
10. 成功草稿未来保存到 `Resume.parsed_snapshot`。
11. 阶段 5 使用独立结构化状态，不能复用阶段 4 的 `parse_status/parse_error/parsed_at`。
12. 外部 DeepSeek 请求期间不能长期占用 PostgreSQL 事务、连接或行锁。
13. 使用 `structure_attempt_id` 和处理租约防止并发双调用及旧响应覆盖新结果。
14. 已有成功草稿且 `force=false` 时直接返回旧草稿，不再调用模型或收费。
15. `force=true` 只代表 HR 主动重新识别。
16. 重新识别失败时保留上一次成功 `parsed_snapshot` 和 `structured_at`。
17. 前端普通字段只补充空值，不覆盖 HR 已填写内容。
18. HR 已有教育、工作或项目经历时，不自动覆盖、不删除、不直接拼接，必须展示 AI 候选条目让 HR 选择。
19. 应聘岗位、来源渠道、招聘状态不能由 AI 猜测。
20. 不确定信息返回 `null`，没有列表内容返回 `[]`，禁止用“未知”“无”等文本占位。
21. 性别和年龄即使从原文提取，也不能用于后续岗位匹配、评分或淘汰。
22. 阶段 5 只提取学校名称，不让模型判断 985/211。
23. 后续院校标签必须来自“学校名称标准化 + 可追溯标准院校目录”，不能依赖模型记忆。
24. 阶段 5 不实现 OCR、岗位匹配、AI 初筛、报告、自动去重、批量解析或自动淘汰。

## 3. 后端分层与职责

项目链路：

```text
前端
→ API
→ Schema
→ Service
→ DeepSeek Adapter
→ DeepSeek API
→ PostgreSQL
```

每层职责必须保持单一：

| 层 | 阶段 5 职责 | 禁止事项 |
| --- | --- | --- |
| 前端 | 展示进度、草稿、冲突；只填空字段；收集 HR 确认 | 不保存 API Key，不直接相信模型，不覆盖人工内容 |
| API | 接收 `force`，调用 Service，转换稳定 HTTP 状态码 | 不直接调 DeepSeek，不自己管理事务状态机 |
| Schema | 验证模型 JSON 和 API 草稿响应 | 不访问数据库，不调用网络 |
| Service | 前置条件、幂等、并发、租约、短事务、保存成功或错误 | 等待 DeepSeek 时不持有事务或行锁 |
| Adapter | 构造并发送一次 DeepSeek 请求，返回原始响应元数据 | 不写数据库，不创建 Candidate，不自动重试模型 |
| PostgreSQL | 保存 Resume 状态、最新成功草稿和服务端元数据 | 不把失败模型输出保存成成功草稿 |

## 4. `ResumeParseDraft` v1 契约

当前版本固定为：

```text
schema_version = "1.0"
```

完整结构：

```json
{
  "schema_version": "1.0",
  "basic_info": {
    "name": null,
    "phone": null,
    "email": null,
    "gender": null,
    "age": null,
    "location": null,
    "current_company": null,
    "current_title": null,
    "work_years": null,
    "education_level": null
  },
  "education_records": [],
  "work_experiences": [],
  "project_experiences": [],
  "skills": [],
  "certifications": [],
  "self_evaluation": null,
  "warnings": [],
  "missing_fields": []
}
```

### 4.1 五类 Schema

- `ResumeBasicInfoDraft`
- `ResumeEducationDraft`
- `ResumeWorkExperienceDraft`
- `ResumeProjectExperienceDraft`
- `ResumeParseDraft`

实现文件：`backend/app/schemas/rebuilt/resume_parse.py`。

### 4.2 空值和列表规则

- 单个信息无法确定：使用 `null`。
- 没有某类经历或技能：使用空数组 `[]`。
- 契约中的字段必须明确出现；不能因为允许 `null` 就省略字段。
- 数组本身不能为 `null`。
- `""`、纯空格、`"未知"`、`"无"` 不能代替 `null`。

没有工作或项目经历是合法情况：

```json
{
  "work_experiences": [],
  "project_experiences": []
}
```

被拒绝的是列表中存在一条所有字段都为空的假记录，而不是拒绝没有经历的候选人。

### 4.3 日期规则

只允许：

```text
YYYY
YYYY-MM
至今（只能作为结束时间）
```

月份必须为 `01..12`。开始年份晚于结束年份，或年月精度相同且开始月份晚于结束月份时拒绝。若同年但一侧只有年份，不能凭空猜测月份，因此不判为明显冲突。

### 4.4 列表清理

技能、证书和工作/项目技术栈执行确定性清理：

1. 去除首尾空白。
2. 删除空项。
3. 删除完全相同的重复项。
4. 保留第一次出现的顺序。
5. 不做大小写或同义词模糊合并，例如 `Python` 和 `python` 暂时视为不同值。

### 4.5 学校边界

教育草稿只有：

```text
school
degree
major
start_date
end_date
```

没有 `is_985`、`is_211`。现有正式 `EducationCreate` 的相关默认 `false` 只能解释为“没有经过标准目录验证的标签”，不能解释为学校一定不是 985/211。

### 4.6 字段映射

详细映射见 `docs/specs/2026-08-12-stage5-resume-draft-field-mapping.md`。核心规则：

- `basic_info` 对应 `CandidateCreate` 的同义基础字段。
- `education_records` 对应 `EducationCreate`。
- `work_experiences` 对应 `WorkExperienceCreate`。
- `project_experiences` 对应 `ProjectExperienceCreate`。
- `skills` 只能作为 HR 待确认标签，不能自动覆盖 `CandidateCreate.tags`。
- `certifications`、`self_evaluation`、`warnings`、`missing_fields` 暂时只保留在草稿快照。
- `applied_job_id`、`source`、`status` 没有 AI 映射。

## 5. Resume 独立结构化状态

当前已增加六个数据库字段：

| 字段 | 类型 | 默认/可空 | 含义 |
| --- | --- | --- | --- |
| `structure_status` | `VARCHAR(30)` | `not_started`，非空，有索引 | 最近一次结构化处理状态 |
| `structure_error` | `TEXT` | 可空 | 最近一次失败的稳定脱敏错误 |
| `structure_attempt_id` | `VARCHAR(36)` | 可空 | 当前尝试的服务端 UUID |
| `structure_started_at` | 带时区时间 | 可空 | 最近一次尝试开始时间 |
| `structured_at` | 带时区时间 | 可空 | 最近一次成功草稿保存时间 |
| `structure_schema_version` | `VARCHAR(20)` | 可空 | 最近成功草稿的 Schema 版本 |

合法状态：

```text
not_started
processing
succeeded
failed
```

阶段 4 与阶段 5 状态示例：

```text
parse_status = parsed
structure_status = not_started
```

表示文件已成功转成原文，但还没有进行 AI 结构化。

当前 migration：

```text
f5a7c9e2d104_add_resume_structure_state.py
```

正式开发数据库已经只向前升级到 `f5a7c9e2d104`，没有在正式库做 downgrade。

## 6. `parsed_snapshot` 持久化格式

成功结果未来保存为服务端信封，而不是直接把模型 JSON 裸存入数据库：

```json
{
  "draft": {
    "schema_version": "1.0",
    "basic_info": {},
    "education_records": [],
    "work_experiences": [],
    "project_experiences": [],
    "skills": [],
    "certifications": [],
    "self_evaluation": null,
    "warnings": [],
    "missing_fields": []
  },
  "metadata": {
    "model": "实际响应模型名",
    "prompt_version": "resume_structure_v1",
    "schema_version": "1.0",
    "structured_at": "服务端时间",
    "input_characters": 0,
    "input_tokens": null,
    "output_tokens": null,
    "attempt_id": "服务端生成的 UUID"
  }
}
```

`metadata` 必须由服务端生成，不能接受模型提供或覆盖。普通日志不能记录完整简历原文、完整 Prompt、原始模型响应、手机号或邮箱。

## 7. 第三小步：DeepSeek Adapter 详细方案

这是换电脑后的下一步，只做 Adapter，不实现 Service、API、数据库状态流转或前端。

### 7.1 Adapter 输入

建议输入：

- `raw_text`
- 固定的版本化 Prompt
- 配置中的模型名、超时、最大输入字符和最大输出 token

### 7.2 Adapter 输出

建议返回一个内部结果对象：

```text
content            原始响应文本
model              实际响应模型名
finish_reason      结束原因
input_tokens       可空
output_tokens      可空
```

Adapter 不在此步执行 `json.loads` 或 `ResumeParseDraft` 校验；这些属于 Service 组合流程。但 Adapter 必须检查响应对象、choice、content 和 finish reason 是否存在，并转换为稳定内部异常。

### 7.3 调用约束

- 非流式请求。
- `response_format={"type": "json_object"}`。
- Prompt 中必须出现 JSON 要求和完整契约示例。
- 温度保持较低。
- SDK 自动重试设置为 0。
- 一次 Adapter 方法调用最多发出一次真实模型请求。
- 输入超过配置上限时在本地失败，不静默截断。
- 不在日志中输出 API Key、完整 Prompt、完整简历原文或完整模型响应。

### 7.4 稳定异常建议

至少区分：

```text
认证失败
余额/配额不足
限流
超时
服务暂不可用
空响应
输出截断或非正常 finish_reason
其他上游错误
```

不要把上游响应体、内部路径或密钥写入 `structure_error` 或返回前端。

### 7.5 Adapter 测试

全部使用 Fake/Mock 客户端，不调用真实 DeepSeek，不产生费用。至少验证：

1. 正常响应只调用 SDK 一次。
2. 请求包含 JSON Output。
3. 请求使用配置中的模型、超时和 token 上限。
4. SDK 自动重试为 0。
5. 超长输入在调用前失败，SDK 调用次数为 0。
6. 超时、限流、认证、余额和服务异常映射正确。
7. choices 为空、content 为空或空白时失败。
8. `finish_reason=length` 等截断情况失败。
9. 日志和异常文案不包含简历原文、邮箱、手机号或 API Key。

## 8. 第四小步：`ResumeStructureService` 详细方案

Service 是整个阶段 5 最关键的业务层。

### 8.1 `force=false` 行为

```text
已有成功 parsed_snapshot
→ 直接返回旧草稿
→ 不调用 Adapter
→ from_cache = true
```

没有成功草稿时才开始新识别。

### 8.2 `force=true` 行为

只表示 HR 明确要求重新识别。每次点击最多产生一次新模型调用。新尝试失败时：

```text
structure_status = failed
structure_error = 最近失败原因
parsed_snapshot = 保留上一次成功内容
structured_at = 保留上一次成功时间
```

### 8.3 两段短事务

不能在等待 DeepSeek 时一直持有 PostgreSQL 事务或行锁。正确流程：

#### 第一段短事务

1. `SELECT ... FOR UPDATE` 锁定 Resume。
2. 检查 Resume 存在。
3. 检查 `parse_status == parsed` 且 `raw_text` 非空。
4. 检查缓存、处理中状态和租约。
5. 生成新的服务端 UUID `attempt_id`。
6. 原子写入：

```text
structure_status = processing
structure_error = null
structure_attempt_id = 新 UUID
structure_started_at = 当前时间
```

7. 提交并释放事务、连接和行锁。

#### 事务外

8. 调用 Adapter 一次。
9. 检查响应非空和 `finish_reason`。
10. 执行 `json.loads`。
11. 执行 `ResumeParseDraft.model_validate(...)`。
12. 完成业务规则校验。

#### 第二段短事务

13. 再次锁定 Resume。
14. 检查数据库中的 `structure_attempt_id` 仍等于本次 attempt ID。
15. 不相等说明本请求已过期，禁止覆盖更新结果。
16. 相等时原子保存成功草稿和元数据，或保存稳定失败状态。

### 8.4 租约

如果进程在模型调用期间崩溃，Resume 可能永久停在 `processing`。因此需要处理租约，例如 180 秒：

```text
processing 且未超过租约
→ 返回 409，不产生第二次调用

processing 且已超过租约
→ 新请求可以生成新 attempt ID 并接管
```

旧请求即使稍后返回，也会因 attempt ID 不匹配而不能保存。

阶段 4 清理器未来必须跳过租约内 `processing` 的未绑定 Resume；超过租约后仍可按原 24 小时规则处理，避免崩溃任务永久阻止清理。

### 8.5 Service 前置条件

- Resume 必须存在。
- 阶段 4 必须已经成功得到非空 `raw_text`。
- 输入字符数不能超过安全上限。
- 同一 Resume 的有效租约内不能再启动第二次识别。
- 自动化测试不得调用真实 DeepSeek。

## 9. 第五小步：结构化 API 方案

端点：

```http
POST /api/v2/resumes/{resume_id}/structure
Content-Type: application/json

{
  "force": false
}
```

成功响应建议：

```json
{
  "resume_id": 32,
  "structure_status": "succeeded",
  "from_cache": false,
  "has_previous_draft": false,
  "draft": {
    "schema_version": "1.0",
    "basic_info": {},
    "education_records": [],
    "work_experiences": [],
    "project_experiences": [],
    "skills": [],
    "certifications": [],
    "self_evaluation": null,
    "warnings": [],
    "missing_fields": []
  }
}
```

错误状态建议：

| HTTP | 场景 |
| --- | --- |
| `404` | Resume 不存在 |
| `409` | 阶段 4 尚未成功得到原文，或同一 Resume 正在有效租约内处理 |
| `422` | 原文超过本地安全输入上限等前置条件失败 |
| `429` | DeepSeek 限流 |
| `502` | 空响应、截断、JSON/Schema/业务校验失败 |
| `503` | 认证、余额或服务暂不可用 |
| `504` | 模型调用超时 |

API 测试使用依赖覆盖和 Mock Service，不连接真实模型。必须验证 `force=false` 缓存、`force=true` 重识别、处理中 `409`、各异常状态码及错误响应脱敏。

## 10. 第六小步：新增候选人页面辅助填表

目标页面：`/stage3/candidates/new`。

### 10.1 普通字段合并

只有表单当前值为以下情况时才写入 AI 值：

```text
undefined
null
空白字符串
```

人工已有内容必须保留。若 AI 值不同，显示“AI 识别到另一结果”，由 HR 主动采用。

不得由草稿写入：

```text
应聘岗位
来源渠道
招聘状态
```

### 10.2 经历列表合并

```text
对应人工列表为空
→ 展示 AI 识别条数
→ 允许 HR 导入

对应人工列表已有任何记录
→ 不自动覆盖
→ 不自动删除
→ 不直接拼接
→ 展示 AI 候选条目
→ HR 逐条选择
```

第一版不使用模糊自动去重决定覆盖。

### 10.3 页面状态

至少展示：

- 正在识别
- 识别成功及各类条数
- 识别失败但可以继续手填
- 存在旧成功草稿但最近重识别失败
- AI 填充标记
- 人工修改/确认状态
- 主动重新识别入口
- 未绑定 Resume 的 24 小时保留边界

HR 最终确认时继续复用现有单事务候选人创建和 Resume 绑定链路。

## 11. 第七小步：样本评估与最终验收

### 11.1 去隐私样本

准备至少 15～20 份去隐私真实简历，覆盖：

- 应届生、实习生、有多年经验者
- 中文、英文和中英混合简历
- 有/无项目经历
- 多段教育和工作经历
- 只有年份、年月混合、至今
- PDF、DOCX、TXT 来源
- 字段缺失、联系方式国际格式
- 简历中包含类似提示词或指令的文本

不得把真实手机号、邮箱、姓名、住址、证件号等隐私提交到测试仓库。

### 11.2 评估指标

- 字段完整性
- 字段准确性
- JSON/Schema 失败率
- 日期冲突率
- 空白经历率
- 响应时间
- 输入/输出 token
- 单次费用
- HR 修改量

只有真实评估证明一次调用存在稳定局部遗漏时，才重新评估多步骤或 LangGraph；不能为了展示概念提前引入。

### 11.3 最终真实链路

最后才执行一次真实：

```text
DeepSeek
→ Adapter
→ Service
→ FastAPI
→ PostgreSQL
→ Vite 页面
→ HR 人工确认
```

真实调用前确认 API Key、模型名和 DeepSeek 当前官方 JSON Output 支持；一次验证只发一次请求，不自动重试。

## 12. 配置计划

后续预计增加：

```env
RESUME_STRUCTURE_ENABLED=true
RESUME_STRUCTURE_MODEL=<实现 Adapter 时按官方文档确认>
RESUME_STRUCTURE_TIMEOUT_SECONDS=90
RESUME_STRUCTURE_PROCESSING_LEASE_SECONDS=180
RESUME_STRUCTURE_MAX_INPUT_CHARS=100000
RESUME_STRUCTURE_MAX_OUTPUT_TOKENS=12000
RESUME_STRUCTURE_PROMPT_VERSION=resume_structure_v1
RESUME_STRUCTURE_SCHEMA_VERSION=1.0
```

模型名和接口参数可能变化，第三小步实现 Adapter 时必须按 DeepSeek 官方文档重新核对，不凭记忆写死。

## 13. 已完成工作

### 13.1 第一小步：严格草稿 Schema

已完成：

- 五类 `ResumeParseDraft` Schema
- `schema_version=1.0`
- `extra="forbid"`
- 严格类型
- null/空数组规则
- 长度限制
- 年龄和工作年限范围
- 日期格式及前后关系
- 空经历拒绝
- 技能、技术栈、证书清理去重
- 邮箱和电话合理边界
- 学校无 985/211 推断字段
- 字段映射文档
- 统一导出

验证结果：22 项 Schema 测试通过；当时后端全量 315 项通过。

### 13.2 第二小步：独立结构化状态迁移

已完成：

- Resume Model 六个字段
- `ResumeRead` 状态响应
- 普通 `ResumeCreate/ResumeUpdate` 不开放状态写入
- migration `f5a7c9e2d104`
- Model/Schema/migration 隔离测试
- PostgreSQL 专用临时数据库真实往返
- 正式开发数据库安全向前升级

验证结果：新增 8 项测试；Resume 定向 44 项通过；后端全量 323 项通过；`alembic check` 无差异。

正式数据库最后核对：

```text
Resume 32: candidate_id=64, parse_status=parsed, structure_status=not_started
Resume 38: candidate_id=NULL, parse_status=parsed, structure_status=not_started
Alembic head: f5a7c9e2d104
```

## 14. 尚未实现的工作

以下内容仍不存在，不要误认为已经完成：

- DeepSeek Adapter
- 阶段 5 版本化 Prompt
- 结构化 Service
- JSON 解析与 Schema 在 Service 中的组合
- attempt ID 并发接管逻辑
- 处理租约
- 成功草稿持久化信封
- 失败状态和旧草稿保护
- `POST /api/v2/resumes/{id}/structure`
- 前端识别进度和辅助填表
- 去隐私样本评估
- 真实 DeepSeek 调用
- 最终全链路人工验收

## 15. 固定实施顺序

不得跳步：

1. ✅ ResumeParseDraft Schema 和业务校验
2. ✅ Resume 独立结构化状态及 Alembic 迁移
3. ⏭ DeepSeek Adapter
4. ResumeStructureService
5. 结构化 API
6. 新增候选人页面辅助填表
7. 去隐私样本评估、真实全链路和人工验收

每个小步都必须：

1. 开始前用大白话解释缺什么、做什么、怎么做、为什么做，以及在完整链路中的位置。
2. 只完成当前小步。
3. 运行当前小步的定向测试。
4. 运行后端全量回归；涉及前端时运行生产构建。
5. 涉及 migration 时在专用临时数据库做往返，正式业务库只安全向前升级。
6. 明确测试能证明什么、不能证明什么。
7. 更新 `PROJECT_STATE.md`。
8. 说明如何如实写进简历和面试可能追问。

## 16. 新电脑恢复步骤

### 16.1 确认文件完整

项目根目录应为：

```text
C:\Users\<你的用户名>\Desktop\AI招聘助手\testin-recruitment-assistant
```

实际路径可以不同，但所有相对目录必须完整。重点检查：

```powershell
Test-Path backend/app/schemas/rebuilt/resume_parse.py
Test-Path backend/migrations/versions/f5a7c9e2d104_add_resume_structure_state.py
Test-Path backend/tests/schemas/rebuilt/test_resume_parse.py
Test-Path backend/tests/models/rebuilt/test_resume_structure_state.py
Test-Path backend/tests/migrations/test_resume_structure_state_migration.py
Test-Path docs/specs/2026-08-12-stage5-resume-structure-design.md
Test-Path docs/specs/2026-08-12-stage5-resume-draft-field-mapping.md
Test-Path docs/handoff/2026-08-12-stage5-development-handoff.md
```

### 16.2 检查 Git

```powershell
git branch --show-current
git status --short
git diff --stat
git log --oneline -5
```

如果阶段 5 文件没有出现在提交历史或工作区，先找回文件，不要重新从旧文档猜着实现。

### 16.3 Python 环境

推荐使用 Python 3.11。若 `.venv` 没有随项目复制或不可用：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 16.4 基础测试

不启动 FastAPI，先运行：

```powershell
cd backend
..\.venv\Scripts\python.exe -m unittest tests.schemas.rebuilt.test_resume_parse -v
..\.venv\Scripts\python.exe -m unittest tests.models.rebuilt.test_resume_structure_state tests.migrations.test_resume_structure_state_migration -v
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

预期基线为 323 项全部通过；如果后续新增测试，总数可以增加，但不能少于当前基线且不能有失败。

### 16.5 PostgreSQL 与 migration

启动 Docker Desktop 和项目 PostgreSQL 后：

```powershell
cd backend
..\.venv\Scripts\alembic.exe current
..\.venv\Scripts\alembic.exe heads
..\.venv\Scripts\alembic.exe check
```

当前代码 head 应为 `f5a7c9e2d104`。如果新电脑连接的是全新数据库，执行：

```powershell
..\.venv\Scripts\alembic.exe upgrade head
```

如果数据库已有用户数据，只做向前升级。不要直接在正式业务库执行 downgrade；迁移往返必须使用名称明确的专用临时数据库。

### 16.6 启动后端前的清理风险

仅做单元测试、编译和 Alembic 时不需要启动 FastAPI。需要人工页面验收并希望临时保留 Resume 38 时：

```powershell
$env:RESUME_CLEANUP_ENABLED='false'
```

然后再启动后端。验收结束应停止进程，不把临时环境变量写成永久产品默认值。

## 17. 第三小步开始时的建议修改边界

预计新增或修改：

```text
backend/app/adapters/（若项目最终采用该目录，先核对现有结构）
backend/app/prompts/rebuilt/resume_structure.py
backend/app/core/config.py
.env.example
backend/tests/...adapter...
PROJECT_STATE.md
```

开始前必须先扫描现有 Adapter/LLM 客户端目录，避免创建重复层。第三小步不要修改：

```text
Resume 数据库状态流转
ResumeStructureService
结构化 API
前端页面
Candidate 创建逻辑
自动清理逻辑
```

## 18. 失败时必须保持的数据

任何模型或校验失败都必须保证：

```text
原始文件              保留
Resume.raw_text       保留
HR 已填写表单          保留
上一次成功 parsed_snapshot  保留
上一次成功 structured_at    保留
本次错误模型输出       不保存为成功草稿
Candidate/三类经历     不自动创建或修改
```

数据库保存失败必须回滚，不能出现半份 JSON 或错误的 `succeeded` 状态。

## 19. 隐私和审计要求

- API Key 只放后端环境变量。
- 不提交 `.env`。
- 不记录完整简历、完整 Prompt 或完整模型响应。
- 不在错误响应中暴露上游响应体、内部路径或凭据。
- ActivityLog 后续可以记录 Resume ID、结果、模型、Prompt/Schema 版本、耗时和 token，但不能记录简历正文。
- 去隐私样本不能包含真实姓名、电话、邮箱、住址、身份证号等。
- 性别、年龄、民族、婚姻、生育信息不能进入匹配、评分或淘汰逻辑。

## 20. 阶段 5 完成标准

只有同时满足以下条件才能宣布阶段 5 完成：

1. 正常一次识别只调用一次 DeepSeek。
2. 没有 Agent 或 LangGraph。
3. 非 JSON、空响应、截断、额外字段、错误类型和业务矛盾无法进入成功草稿。
4. 草稿保存到 `Resume.parsed_snapshot`，结构化状态与文件解析状态分离。
5. 默认重复请求返回旧草稿，不重复调用和收费。
6. 同一 Resume 并发请求不能双调用，等待外部 API 时不长期持有事务。
7. 重新识别失败保留旧成功草稿。
8. 前端只补空字段，已有经历不静默合并。
9. AI 不猜岗位、来源、招聘状态或院校标签。
10. AI 不直接创建 Candidate，HR 最终确认才写正式数据。
11. 自动化测试、migration 往返、前端构建全部通过。
12. 至少 15～20 份去隐私样本完成评估。
13. 真实 DeepSeek、FastAPI、PostgreSQL、Vite 全链路和人工验收通过。

## 21. 简历与面试表达

阶段 5 全部完成后可以如实描述：

> 基于 DeepSeek JSON Output 实现单次调用的简历结构化提取服务，通过 Pydantic 严格校验、业务规则校验、幂等与并发保护、草稿持久化和人工确认机制，把 PDF/DOCX/TXT 原文安全转换为候选人结构化草稿并辅助填写招聘表单。

常见面试追问：

- 为什么不用 Agent 或 LangGraph？
- 为什么 JSON Output 后还要 `json.loads` 和 Pydantic？
- 为什么 AI 草稿不能直接创建 Candidate？
- 怎样确保一次操作只调用一次模型？
- 如何避免两个并发请求重复收费？
- 为什么使用 attempt ID 和租约？
- 为什么等待 DeepSeek 时不能持有数据库事务？
- 重新识别失败为什么要保留旧草稿？
- 前端怎样避免覆盖 HR 输入？
- 为什么不让模型判断 985/211？
- migration 如何避免破坏用户数据？
