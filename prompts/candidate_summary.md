# 候选人摘要生成 Prompt

## 对应模板

`backend/app/prompts/candidate_summary.txt`

## 功能说明

根据候选人结构化信息生成 2-3 句中文摘要，供 HR 快速了解候选人概况。

## 设计要点

1. **角色设定**：专业 HR 助手，确保输出语言符合招聘行业习惯
2. **优先级引导**：教育背景 > 核心技能 > 岗位匹配度，有亮点（名校、稀缺技能）优先提及
3. **长度控制**：2-3 句话，适合 HR 快速阅读，不过度冗长
4. **格式约束**：直接输出文本，不添加标题或 Markdown 标记

## 输入格式

接收候选人结构化 JSON（序列化为字符串传入 Prompt）：

```json
{
  "name": "张明远",
  "school": "北京邮电大学",
  "degree": "本科",
  "major": "计算机科学与技术",
  "target_role": "测试开发工程师",
  "experience_years": 3,
  "skills": ["Python", "Selenium", "Jenkins"]
}
```

## Mock 回退策略

`MockLLM.generate_summary()` 从 3 个预设模板中随机选取：

- 模板 A：强调学历 + 经验年限 + 技能匹配
- 模板 B：强调技能广度 + 岗位契合度
- 模板 C：强调综合素质 + 发展潜力

模板动态填充字段：name、school、degree、major、experience_years、skills（前 3 项）、target_role。

## 效果示例

输出样例：

> 张明远，北京邮电大学计算机科学与技术本科毕业，拥有3年测试开发经验。精通Python、Selenium和Jenkins等自动化测试工具，与测试开发工程师岗位高度匹配。
