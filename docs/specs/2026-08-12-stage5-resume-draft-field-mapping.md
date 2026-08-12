# 阶段 5 第一小步：`ResumeParseDraft` 字段映射说明

> 日期：2026-08-12  
> 范围：只说明经过校验的 AI 草稿怎样对应现有正式创建 Schema；不实现 Service、API、数据库写入或前端合并。

## 1. 映射原则

- `ResumeParseDraft` 是允许信息不完整的 AI 草稿；`CandidateCreate` 是 HR 确认后使用的正式创建请求。两者不能互相替代。
- 草稿中的未知普通字段必须为 `null`，未知列表必须为 `[]`，不能使用空字符串、`未知` 或 `无` 占位。
- 草稿通过校验不代表可以直接入库。HR 仍需检查、修改，并补齐 `CandidateCreate.name` 等正式必填信息。
- `applied_job_id`、`source` 和 `status` 不在草稿中，不能由 AI 猜测。
- 性别和年龄只作为原文基础资料候选值，不得进入后续岗位匹配、评分或淘汰逻辑。

## 2. 基本资料到 `CandidateCreate`

| 草稿字段 | 正式字段 | 规则 |
| --- | --- | --- |
| `basic_info.name` | `CandidateCreate.name` | 只在 HR 表单姓名为空时提供候选值；正式创建时仍必须非空 |
| `basic_info.phone` | `CandidateCreate.phone` | 保留校验后的原格式，不擅自改写国家码或分隔符 |
| `basic_info.email` | `CandidateCreate.email` | 保留校验后的原值 |
| `basic_info.gender` | `CandidateCreate.gender` | 仅原文明示时提取；不得用于筛选决策 |
| `basic_info.age` | `CandidateCreate.age` | 仅原文明示时提取；不得用于筛选决策 |
| `basic_info.location` | `CandidateCreate.location` | 直接候选映射 |
| `basic_info.current_company` | `CandidateCreate.current_company` | 直接候选映射 |
| `basic_info.current_title` | `CandidateCreate.current_title` | 直接候选映射 |
| `basic_info.work_years` | `CandidateCreate.work_years` | 不能根据模糊时间自行推算 |
| `basic_info.education_level` | `CandidateCreate.education_level` | 直接候选映射 |
| `skills` | `CandidateCreate.tags` | 只能作为待确认技能标签；HR 确认后再写入，不自动覆盖现有标签 |

`CandidateCreate.applied_job_id`、`source`、`status`、`resume_file_path`、`resume_text`、`parsed_data` 和 `ai_summary` 没有模型草稿来源。简历路径、原文和快照由服务端可信 Resume 数据处理，不能从模型响应复制。

## 3. 教育经历到 `EducationCreate`

| 草稿字段 | 正式字段 |
| --- | --- |
| `school` | `school` |
| `degree` | `degree` |
| `major` | `major` |
| `start_date` | `start_date` |
| `end_date` | `end_date` |

草稿教育结构故意没有 `is_985` 和 `is_211`。阶段 5 只保存原文学校名称，不能让模型推断院校标签。现有 `EducationCreate.is_985/is_211` 的默认 `false` 只能理解为“尚无经过标准目录验证的标签”，不能据此认定学校不属于相关院校。

## 4. 工作经历到 `WorkExperienceCreate`

`company`、`title`、`start_date`、`end_date`、`description` 和 `tech_stack` 同名映射。AI 结果只是候选条目；表单已有人工工作经历时不得自动覆盖或直接拼接。

## 5. 项目经历到 `ProjectExperienceCreate`

`project_name`、`role`、`start_date`、`end_date`、`description`、`tech_stack` 和 `achievements` 同名映射。AI 结果只是候选条目；表单已有人工项目经历时不得自动覆盖或直接拼接。

## 6. 只保留在草稿快照中的字段

- `schema_version`：标记草稿契约版本，当前固定为 `1.0`。
- `certifications`：当前正式 Candidate 和经历 Schema 没有对应字段，先保留在 `Resume.parsed_snapshot`。
- `self_evaluation`：当前正式新版 Schema 没有专用字段，先保留在草稿快照。
- `warnings`：记录歧义、冲突等需要 HR 检查的事项，不写入正式候选人字段。
- `missing_fields`：记录未识别出的重要字段路径，不写入正式候选人字段。

具体的“只补空字段”和经历冲突选择逻辑属于阶段 5 第六小步前端实现，本文件只固定字段语义，不提前实现合并行为。
