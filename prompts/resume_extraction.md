# 简历信息提取 Prompt

## 对应模板

`backend/app/prompts/resume_extraction.txt`

## 功能说明

指导 LLM 从非结构化简历文本中提取 11 个标准化字段，输出严格 JSON 格式。

## 输出 Schema

```json
{
  "name": "姓名",
  "phone": "手机号",
  "email": "邮箱",
  "school": "学校",
  "degree": "学历（大专/本科/硕士/博士）",
  "major": "专业",
  "target_role": "求职意向",
  "experience_years": 0,
  "skills": ["技能1", "技能2"],
  "experience_desc": "工作经历摘要",
  "self_intro": "自我介绍"
}
```

## 设计要点

1. **角色设定**：设定为"专业的简历信息提取助手"，约束输出范围
2. **格式强约束**：要求严格 JSON，缺失字段用空字符串或 0 填充，避免自由发挥
3. **数组字段**：skills 明确指定为数组格式，防止逗号分隔字符串
4. **禁止解释**：明确"不要添加任何额外解释"，减少后处理成本

## Mock 回退策略

当 `LLM_PROVIDER=mock` 时，`MockLLM.extract_resume()` 使用正则提取：

| 字段 | 提取方法 |
|------|---------|
| name | 首行短文本 或 `姓名:` 模式 |
| phone | 正则 `1[3-9]\d{9}` |
| email | 标准邮箱正则 |
| school | 包含"大学/学院"的文本 |
| degree | 匹配"博士/硕士/本科/大专" |
| skills | 37 个预定义技术关键词匹配 |
| experience_years | 年份范围计算 或 `X年经验` 模式 |

## 效果示例

输入 `sample_data/sample_resume_1.txt`（张明远的简历），提取结果：

```json
{
  "name": "张明远",
  "phone": "13800001001",
  "email": "zhangmy@example.com",
  "school": "北京邮电大学",
  "degree": "本科",
  "major": "计算机科学与技术",
  "target_role": "测试开发工程师",
  "experience_years": 3,
  "skills": ["Python", "Selenium", "Jenkins", "Docker", "MySQL"],
  "experience_desc": "3年自动化测试经验...",
  "self_intro": "..."
}
```
