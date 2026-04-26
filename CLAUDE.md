# CLAUDE.md — 项目指令

## 项目概览
Testin云测招聘助手（testin云测面试题），FastAPI + React + Ant Design。
**最权威的进度文档是 `PROJECT_STATE.md`，每次新对话先读它。**

## 工作原则
1. 先阅读 PROJECT_STATE.md 和 TODO_NEXT.md 了解当前进度
2. 不要重新规划整个项目，不要重复已完成工作
3. 只补齐剩余部分
4. 完成工作后必须同步更新 PROJECT_STATE.md 和 TODO_NEXT.md

## 自动保存进度规则
**每当对话上下文接近容量上限（感知到压缩或对话过长）时，必须执行以下步骤：**
1. 将当前已完成的工作写入 `PROJECT_STATE.md`（更新功能列表、修复记录等）
2. 将未完成的待办更新到 `TODO_NEXT.md`
3. 更新记忆文件 `memory/project_progress.md` 中的进度快照
4. 告知用户"进度已保存，可以在新对话中继续"

## 启动方式
```bash
# 后端
cd backend && python run.py  # → http://localhost:8000

# 前端
cd frontend && npm run dev   # → http://localhost:5173
```

## 关键页面
- `/` — Dashboard 看板
- `/form` — HR 候选人录入
- `/upload` — 简历上传解析
- `/candidates` — 候选人列表
- `/candidates/:id` — 候选人详情
- `/apply` — 投递者在线填写页（独立全屏，无侧边栏）
