from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RESUME_DIR = ROOT / "resumes"
DATASET_VERSION = "portfolio-demo-v1"
DATASET_AS_OF = datetime(2026, 9, 9, 12, 0, tzinfo=timezone(timedelta(hours=8)))
APPLIED_BASE = datetime(2026, 5, 1, 9, 0, tzinfo=timezone(timedelta(hours=8)))
RNG_SEED = 20260909


NAMES = [
    "林知序", "周沐辰", "沈清越", "苏景澄", "顾言川", "许星遥",
    "程予安", "叶闻舟", "江若衡", "唐以宁", "宋砚秋", "韩知远",
    "陆明川", "白予初", "秦书言", "温予宁", "乔沐阳", "夏知微",
    "谢云舟", "方景行", "罗清和", "姜若川", "魏安澜", "余星野",
    "邵闻溪", "蒋知衡", "杜明远", "彭清嘉", "袁以航", "陶予澄",
    "熊知夏", "钟景宁", "廖书辰", "侯清越", "郑星河", "梁安序",
    "何知行", "石予安", "高明澈", "严若宁", "金沐川", "毛景初",
    "范知遥", "潘清言", "邱予舟", "任星澄", "崔明序", "孔若衡",
    "孟知宁", "雷景舟", "黎清远", "龙予川", "段星言", "郝明安",
    "龚若溪", "傅知澄", "武景和", "钱清序", "戴予宁", "莫星舟",
]

SCHOOLS = [
    "云杉理工大学", "江湾科技大学", "北辰工业大学", "海岚大学",
    "星港工程学院", "澄湖科技学院", "远川大学", "青禾理工学院",
]
COMPANIES = [
    "星河协作科技", "云帆数据", "澄明智能", "北辰软件", "远岚网络",
    "青禾数科", "拓界智能", "流光科技", "栖川信息", "原点云创",
    "山海研发", "明澈系统",
]
LOCATIONS = ["深圳", "上海", "杭州", "北京", "成都", "广州", "武汉", "南京", "苏州", "西安"]


JOBS: list[dict[str, Any]] = [
    {
        "demo_job_id": "JOB-AI",
        "desired_status": "open",
        "post_import_actions": [],
        "create_payload": {
            "title": "AI 应用工程师",
            "department": "智能产品研发部",
            "location": "深圳",
            "employment_type": "full_time",
            "headcount": 3,
            "job_background": "团队正在建设面向企业内部场景的大模型应用，需要把需求理解、模型调用、业务规则和可观测性组合成稳定产品。该岗位以可交付的 AI 应用为目标，不以训练基础模型为主要职责。",
            "job_responsibilities": "1. 使用 Python 与 FastAPI 开发大模型应用和业务 API；\n2. 设计 Prompt、结构化输出、检索增强与评估流程；\n3. 接入 PostgreSQL、Redis 等基础设施并处理超时、重试和幂等；\n4. 与产品和前端协作完成需求澄清、上线验证与问题复盘；\n5. 为模型效果、成本和失败路径补充自动化测试与运行记录。",
            "candidate_requirements": "1. 熟练使用 Python，能独立开发和调试 Web API；\n2. 理解 REST、关系数据库和常见事务问题；\n3. 有 LLM API、Prompt 或 RAG 项目实践，并能说明评估方法；\n4. 能通过日志和最小复现定位模型与工程问题；\n5. 能清楚表达方案边界，不把模型输出直接当作业务事实。",
            "preferred_qualifications": "有 FastAPI、SQLAlchemy、PostgreSQL、Docker、向量检索、模型评估或 AI 产品落地经验；有可演示项目、技术文档或复盘材料优先。",
            "public_notes": "请提交可阅读的项目说明，重点描述本人职责、数据流、失败处理、效果验证和已知限制。作品集演示请勿包含真实客户数据。",
            "status": "open",
        },
    },
    {
        "demo_job_id": "JOB-BE",
        "desired_status": "open",
        "post_import_actions": [],
        "create_payload": {
            "title": "Python 后端工程师",
            "department": "平台研发部",
            "location": "上海",
            "employment_type": "full_time",
            "headcount": 2,
            "job_background": "平台为多个业务团队提供统一的流程、数据与审计能力，需要持续提升 API 稳定性、事务一致性和开发效率。",
            "job_responsibilities": "1. 使用 Python 与 FastAPI 维护核心业务服务；\n2. 设计清晰的 API、Schema、Service 和数据库边界；\n3. 使用 PostgreSQL、SQLAlchemy 与 Alembic 完成数据建模和迁移；\n4. 处理并发、幂等、事务回滚和异步任务；\n5. 编写单元、集成和数据库测试并参与代码评审。",
            "candidate_requirements": "1. 具备扎实的 Python 编程基础；\n2. 熟悉至少一种主流 Web 框架和 REST API；\n3. 理解关系数据库、索引、事务和常见查询优化方法；\n4. 能使用 Git、Docker 和自动化测试工具；\n5. 能独立定位接口、服务和数据库之间的问题。",
            "preferred_qualifications": "有 FastAPI、SQLAlchemy 2.0、PostgreSQL、Redis、消息队列、异步 Worker 或高并发项目经验优先。",
            "public_notes": "请在简历中给出具体负责模块、接口规模、性能或稳定性改进证据；课程项目也可以，但需说明本人贡献。",
            "status": "open",
        },
    },
    {
        "demo_job_id": "JOB-QA",
        "desired_status": "open",
        "post_import_actions": [],
        "create_payload": {
            "title": "测试开发工程师",
            "department": "质量工程部",
            "location": "杭州",
            "employment_type": "full_time",
            "headcount": 2,
            "job_background": "团队负责 Web、API 与异步业务链路的质量保障，希望通过自动化、风险分析和持续集成提升发布信心。",
            "job_responsibilities": "1. 设计 Web 与 API 自动化测试；\n2. 使用 Python、Pytest、Playwright 等建设可维护测试工具；\n3. 覆盖事务、并发、幂等、权限和异常恢复场景；\n4. 接入 CI/CD 并分析失败证据；\n5. 与研发共同改进可测试性和缺陷预防机制。",
            "candidate_requirements": "1. 熟悉测试设计方法并能从业务风险拆解用例；\n2. 能使用 Python 编写测试或辅助工具；\n3. 熟悉接口测试、数据库验证和至少一种 UI 自动化工具；\n4. 理解持续集成和缺陷生命周期；\n5. 能提供清晰、可复现的问题证据。",
            "preferred_qualifications": "有 Pytest、Playwright、Selenium、Postman、JMeter、Docker、PostgreSQL 或质量平台建设经验优先。",
            "public_notes": "请描述一项最有代表性的质量改进，包括问题、方案、覆盖范围、结果和没有覆盖的风险。",
            "status": "open",
        },
    },
    {
        "demo_job_id": "JOB-FE",
        "desired_status": "open",
        "post_import_actions": [],
        "create_payload": {
            "title": "前端工程师",
            "department": "企业产品研发部",
            "location": "北京",
            "employment_type": "full_time",
            "headcount": 2,
            "job_background": "团队建设面向企业用户的高信息密度工作台，需要兼顾复杂状态、操作安全、响应式布局和长期可维护性。",
            "job_responsibilities": "1. 使用 React 与 TypeScript 开发企业级工作台；\n2. 设计列表、详情、表单和复杂状态交互；\n3. 与后端协作维护 API 类型与错误处理；\n4. 建设响应式、可访问和可测试的组件；\n5. 参与性能优化、构建发布与前端质量治理。",
            "candidate_requirements": "1. 熟练掌握 JavaScript、TypeScript、React 与现代 CSS；\n2. 理解组件状态、请求生命周期和常见性能问题；\n3. 能实现复杂表单、表格和响应式布局；\n4. 有前端测试和工程化实践；\n5. 能基于业务目标解释交互取舍。",
            "preferred_qualifications": "有 Ant Design、Vite、状态管理、ECharts、无障碍、设计系统或 B 端产品经验优先。",
            "public_notes": "请附上可访问的作品说明或截图，并明确本人完成的组件、交互、性能与测试工作。",
            "status": "open",
        },
    },
    {
        "demo_job_id": "JOB-DA",
        "desired_status": "closed",
        "post_import_actions": ["close_after_historical_applications_created"],
        "create_payload": {
            "title": "数据分析师",
            "department": "经营分析部",
            "location": "成都",
            "employment_type": "full_time",
            "headcount": 2,
            "job_background": "团队通过可信指标和专题分析支持产品与经营决策，需要建立从业务问题、数据口径到结论验证的完整分析链路。",
            "job_responsibilities": "1. 与业务方定义指标和分析口径；\n2. 使用 SQL 与 Python 完成数据提取、清洗和分析；\n3. 建设可复用报表与监控看板；\n4. 开展漏斗、留存、分群和实验分析；\n5. 记录假设、数据限制和可执行建议。",
            "candidate_requirements": "1. 熟练使用 SQL，能处理多表关联与窗口函数；\n2. 能使用 Python/Pandas 完成分析；\n3. 理解指标口径、数据质量和基本统计方法；\n4. 能把分析结论转化为业务建议；\n5. 能清楚说明相关性与因果边界。",
            "preferred_qualifications": "有 Tableau、Power BI、Superset、dbt、A/B 测试、数据仓库或互联网业务分析经验优先。",
            "public_notes": "该岗位已结束接收新投递，保留历史数据用于作品集展示岗位关闭后仍可追溯既有流程。",
            "status": "open",
        },
    },
]


ROLE_SPECS: dict[str, dict[str, Any]] = {
    "JOB-AI": {
        "major": "人工智能应用工程",
        "target_role": "AI 应用工程师",
        "core_skills": ["Python", "FastAPI", "LLM API", "Prompt Engineering", "PostgreSQL", "RAG", "Docker", "Redis"],
        "adjacent_skills": ["PyTorch", "向量检索", "模型评估", "React", "数据标注"],
        "low_skills": ["内容运营", "用户访谈", "Excel", "活动策划", "基础 SQL"],
        "titles": ["AI 应用工程师", "Python 工程师", "算法应用实习生"],
        "projects": ["企业知识问答助手", "客服工单总结系统", "合同条款审阅台", "会议纪要结构化工具", "研发文档检索助手", "智能表单抽取服务"],
        "work_templates": [
            "使用 Python 与 FastAPI 交付 {project} 的核心接口，设计请求校验、超时和安全错误映射。",
            "为模型输出增加 JSON Schema 校验与一次受控修复，使结构化成功率由 {before}% 提升到 {after}%。",
            "建立 {samples} 条离线样例的回归集，记录模型版本、Prompt 版本、token 与失败类型。",
        ],
        "project_template": "完成从业务输入、Prompt/检索、模型 Adapter、结构校验到结果展示的端到端链路，并为引用缺失和模型超时设计降级路径。",
    },
    "JOB-BE": {
        "major": "软件工程",
        "target_role": "Python 后端工程师",
        "core_skills": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "REST API", "Pytest", "Docker", "Redis"],
        "adjacent_skills": ["Alembic", "异步编程", "Celery", "Linux", "Prometheus"],
        "low_skills": ["JavaScript", "平面设计", "用户运营", "Excel", "基础 HTML"],
        "titles": ["Python 后端工程师", "平台研发工程师", "后端开发实习生"],
        "projects": ["订单状态服务", "企业审批平台", "文件处理中心", "任务调度服务", "审计日志平台", "客户资料中台"],
        "work_templates": [
            "负责 {project} 的 API 与 Service 分层，维护 {endpoints} 个业务接口及稳定错误合同。",
            "通过事务边界、唯一约束和幂等键治理重复请求，将重复数据问题降低 {after}%。",
            "为 PostgreSQL 查询补充索引与执行计划分析，核心列表 P95 从 {latency_before}ms 降至 {latency_after}ms。",
        ],
        "project_template": "设计异步任务的领取、租约、失败重试与恢复流程，并用 PostgreSQL 集成测试验证多 Worker 不重复执行。",
    },
    "JOB-QA": {
        "major": "软件质量工程",
        "target_role": "测试开发工程师",
        "core_skills": ["Python", "Pytest", "Playwright", "API 测试", "PostgreSQL", "CI/CD", "Docker", "JMeter"],
        "adjacent_skills": ["Selenium", "Postman", "Allure", "Linux", "GitHub Actions"],
        "low_skills": ["市场调研", "内容编辑", "Excel", "客服运营", "基础 SQL"],
        "titles": ["测试开发工程师", "质量工程师", "测试实习生"],
        "projects": ["招聘流程回归平台", "接口契约测试套件", "移动端自动化框架", "并发一致性测试工具", "发布质量看板", "性能基线平台"],
        "work_templates": [
            "围绕 {project} 建立分层测试策略，覆盖正常路径、边界、权限与失败恢复。",
            "使用 Pytest 和 Playwright 沉淀 {samples} 条自动化用例，将人工回归时间缩短 {after}%。",
            "在 CI 中保存请求、数据库与截图证据，使偶发失败平均定位时间从 {latency_before} 分钟降到 {latency_after} 分钟。",
        ],
        "project_template": "针对并发提交、事务回滚和异步任务恢复设计可重复测试环境，明确自动化能够证明和不能证明的范围。",
    },
    "JOB-FE": {
        "major": "计算机科学与交互技术",
        "target_role": "前端工程师",
        "core_skills": ["TypeScript", "React", "Ant Design", "Vite", "CSS", "REST API", "Vitest", "Zustand"],
        "adjacent_skills": ["ECharts", "Playwright", "可访问性", "性能优化", "Node.js"],
        "low_skills": ["Python 脚本", "数据录入", "内容运营", "Excel", "基础 HTML"],
        "titles": ["前端工程师", "Web 开发工程师", "前端开发实习生"],
        "projects": ["招聘运营工作台", "流程统计看板", "客户配置中心", "审批任务中心", "设计系统组件库", "移动端数据门户"],
        "work_templates": [
            "使用 React 与 TypeScript 开发 {project}，拆分列表、详情和状态操作组件。",
            "统一请求状态与安全错误展示，将重复交互代码减少 {after}%，并修复详情刷新循环。",
            "完成桌面、平板和手机三档响应式适配，核心页面首屏时间由 {latency_before}ms 降至 {latency_after}ms。",
        ],
        "project_template": "围绕高信息密度企业工作台设计可访问交互，补充组件测试、请求契约测试和 production build 验证。",
    },
    "JOB-DA": {
        "major": "数据科学与商业分析",
        "target_role": "数据分析师",
        "core_skills": ["SQL", "Python", "Pandas", "数据可视化", "指标体系", "漏斗分析", "Tableau", "A/B 测试"],
        "adjacent_skills": ["Power BI", "dbt", "Excel", "统计学", "数据仓库"],
        "low_skills": ["行政协调", "内容运营", "基础 Excel", "活动执行", "文案编辑"],
        "titles": ["数据分析师", "经营分析专员", "数据分析实习生"],
        "projects": ["招聘转化漏斗", "用户留存分析", "经营指标看板", "渠道质量分析", "实验效果评估", "异常指标监控"],
        "work_templates": [
            "围绕 {project} 与业务方统一口径，使用 SQL 构建可追溯的分析数据集。",
            "通过 Python/Pandas 完成清洗和分群，识别 {samples} 个关键样本并提出可验证改进假设。",
            "建设自助看板，将周报准备时间缩短 {after}%，同时标注缺失数据与因果解释边界。",
        ],
        "project_template": "从业务问题出发定义指标、核对数据质量、分析漏斗与分群，并把结论拆成可执行建议和后续验证计划。",
    },
}


PRIMARY_COUNTS = {
    "JOB-AI": 14,
    "JOB-BE": 12,
    "JOB-QA": 12,
    "JOB-FE": 11,
    "JOB-DA": 11,
}

FIT_PATTERNS = {
    14: ["high"] * 4 + ["medium"] * 4 + ["transition"] * 2 + ["early_career", "evidence_gap"] + ["low"] * 2,
    12: ["high"] * 3 + ["medium"] * 3 + ["transition"] * 2 + ["early_career", "evidence_gap"] + ["low"] * 2,
    11: ["high"] * 3 + ["medium"] * 3 + ["transition", "early_career", "evidence_gap"] + ["low"] * 2,
}

SCENARIO_COUNTS = {
    "passed_no_interview": 5,
    "scheduled_interview": 4,
    "completed_pending": 3,
    "next_round_pending": 3,
    "offer_draft": 3,
    "offer_sent": 3,
    "offer_accepted": 2,
    "admitted": 2,
    "hired": 3,
    "interview_rejected": 2,
    "offer_declined": 1,
    "candidate_withdrew": 1,
    "backup": 8,
    "rejected": 8,
    "processing_failed": 4,
    "processing_paused": 4,
    "screening_ready_pending": 8,
}

PASSED_SCENARIOS = {
    "passed_no_interview", "scheduled_interview", "completed_pending",
    "next_round_pending", "offer_draft", "offer_sent", "offer_accepted",
    "admitted", "hired", "interview_rejected", "offer_declined",
    "candidate_withdrew",
}
INTERVIEW_ENTERED_SCENARIOS = PASSED_SCENARIOS - {"passed_no_interview"}
INTERVIEW_COMPLETED_SCENARIOS = INTERVIEW_ENTERED_SCENARIOS - {"scheduled_interview"}
OFFER_SENT_SCENARIOS = {"offer_sent", "offer_accepted", "admitted", "hired", "offer_declined"}
OFFER_ACCEPTED_SCENARIOS = {"offer_accepted", "admitted", "hired"}
ADMITTED_SCENARIOS = {"admitted", "hired"}


def iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fit_summary(fit_level: str, role: str) -> str:
    summaries = {
        "high": f"具备较完整的{role}交付经验，能够说明业务目标、核心实现、验证证据和剩余风险。",
        "medium": f"掌握{role}的主要技能并有可复述项目，但复杂场景和系统性验证仍需在面试中确认。",
        "transition": f"从相邻岗位转向{role}，工程基础较好，直接岗位经验需要结合项目细节进一步判断。",
        "early_career": f"以课程和实习项目为主，对{role}方向投入明确，生产环境经验有限。",
        "evidence_gap": f"简历提到多项{role}相关工作，但成果指标和本人职责边界描述不足。",
        "low": f"当前经历与{role}的核心要求重合较少，适合作为低匹配对照样本。",
    }
    return summaries[fit_level]


def candidate_skills(spec: dict[str, Any], fit_level: str, index: int) -> list[str]:
    core = spec["core_skills"]
    adjacent = spec["adjacent_skills"]
    if fit_level == "high":
        return core[:7] + [adjacent[index % len(adjacent)]]
    if fit_level == "medium":
        return core[:5] + adjacent[:2]
    if fit_level == "transition":
        return adjacent[:4] + core[:3]
    if fit_level == "early_career":
        return core[:4] + ["Git", "课程项目"]
    if fit_level == "evidence_gap":
        return core[:5]
    return spec["low_skills"] + [core[0]]


def make_candidate(
    number: int,
    name: str,
    job_id: str,
    local_index: int,
    fit_level: str,
) -> dict[str, Any]:
    spec = ROLE_SPECS[job_id]
    skills = candidate_skills(spec, fit_level, local_index)
    work_years_by_fit = {
        "high": 4 + local_index % 3,
        "medium": 2 + local_index % 3,
        "transition": 3 + local_index % 2,
        "early_career": 0,
        "evidence_gap": 2,
        "low": 1 + local_index % 3,
    }
    work_years = work_years_by_fit[fit_level]
    degree = "硕士" if number % 5 == 0 else "本科"
    end_year = 2026 if work_years == 0 else 2025 - work_years
    start_year = end_year - (3 if degree == "本科" else 2)
    company = COMPANIES[(number - 1) % len(COMPANIES)]
    project = spec["projects"][local_index % len(spec["projects"])]
    title_index = 2 if work_years == 0 else (0 if fit_level in {"high", "medium", "evidence_gap"} else 1)
    current_title = spec["titles"][title_index]
    metrics = {
        "project": project,
        "before": 71 + number % 8,
        "after": 88 + number % 9,
        "samples": 42 + number * 3,
        "endpoints": 12 + number % 19,
        "latency_before": 620 + number * 7,
        "latency_after": 210 + number * 3,
    }
    bullets = [template.format(**metrics) for template in spec["work_templates"]]
    if fit_level == "evidence_gap":
        bullets = [
            f"参与{project}的日常需求实现和问题处理。",
            "与团队成员协作完成开发、测试或分析任务。",
            "整理项目文档并跟进上线后的反馈。",
        ]
    elif fit_level == "low":
        bullets = [
            "负责日常内容、数据整理与跨团队需求跟进。",
            "使用表格工具维护周报并协调活动执行。",
            f"自学 {spec['core_skills'][0]} 并完成一个入门练习。",
        ]
    elif fit_level == "early_career":
        bullets = [
            f"在课程团队中完成{project}，负责需求拆解和核心模块实现。",
            f"使用 {'、'.join(skills[:3])} 完成可运行原型并编写使用说明。",
            "通过单元测试和演示样例验证主要流程，尚未经历生产环境长期运行。",
        ]

    candidate_id = f"CAND-{number:03d}"
    resume_name = f"candidate_{number:03d}.txt"
    work_start = f"{max(2018, 2025 - max(work_years, 1)):04d}-07"
    work_record = {
        "company": company,
        "title": current_title,
        "start_date": work_start,
        "end_date": "至今" if work_years > 0 else "2026-06",
        "description": "\n".join(f"- {bullet}" for bullet in bullets),
        "tech_stack": skills[:6],
    }
    project_record = {
        "project_name": project,
        "role": "核心成员" if fit_level in {"high", "medium"} else "项目成员",
        "start_date": "2025-03",
        "end_date": "2025-11",
        "description": spec["project_template"],
        "tech_stack": skills[:6],
        "achievements": (
            f"完成 {metrics['samples']} 条样例验证并记录限制。"
            if fit_level not in {"low", "evidence_gap"}
            else "完成基础功能演示，量化结果仍待补充。"
        ),
    }
    education_record = {
        "school": SCHOOLS[(number - 1) % len(SCHOOLS)],
        "degree": degree,
        "major": spec["major"] if fit_level != "low" else ["市场传播", "工商管理", "工业设计"][number % 3],
        "start_date": f"{start_year}-09",
        "end_date": f"{end_year}-06",
        "is_985": False,
        "is_211": False,
    }
    return {
        "demo_candidate_id": candidate_id,
        "name": name,
        "phone": f"+999{number:09d}",
        "email": f"candidate{number:03d}@portfolio.example",
        "location": LOCATIONS[(number - 1) % len(LOCATIONS)],
        "current_company": company if work_years > 0 else None,
        "current_title": current_title,
        "work_years": work_years,
        "education_level": degree,
        "primary_job_id": job_id,
        "target_role": spec["target_role"],
        "fit_level": fit_level,
        "profile_summary": fit_summary(fit_level, spec["target_role"]),
        "skills": skills,
        "education_records": [education_record],
        "work_experiences": [work_record],
        "project_experiences": [project_record],
        "resume_file": f"resumes/{resume_name}",
    }


def render_resume(candidate: dict[str, Any]) -> str:
    education = candidate["education_records"][0]
    work = candidate["work_experiences"][0]
    project = candidate["project_experiences"][0]
    company_line = f"{work['start_date']}—{work['end_date']}  {work['company']}  {work['title']}"
    return "\n".join([
        "【HR智聘作品集演示专用｜以下姓名、号码、学校、公司与经历均为虚构】",
        "",
        candidate["name"],
        f"电话：{candidate['phone']}｜邮箱：{candidate['email']}｜所在地：{candidate['location']}",
        f"求职方向：{candidate['target_role']}",
        "",
        "教育背景",
        f"{education['start_date']}—{education['end_date']}  {education['school']}  {education['major']}  {education['degree']}",
        "",
        "工作/实践经历",
        company_line,
        work["description"],
        "",
        "项目经历",
        f"{project['project_name']}｜{project['role']}｜{project['start_date']}—{project['end_date']}",
        project["description"],
        f"- 项目结果：{project['achievements']}",
        "",
        "技能",
        "、".join(candidate["skills"]),
        "",
        "个人说明",
        candidate["profile_summary"],
        "",
    ])


def build_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    number = 1
    for job in JOBS:
        job_id = job["demo_job_id"]
        count = PRIMARY_COUNTS[job_id]
        pattern = FIT_PATTERNS[count]
        for local_index in range(count):
            candidates.append(
                make_candidate(number, NAMES[number - 1], job_id, local_index, pattern[local_index])
            )
            number += 1
    return candidates


def interleaved_primary_applications(candidates: list[dict[str, Any]]) -> list[tuple[str, str, bool]]:
    by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_job[candidate["primary_job_id"]].append(candidate)
    ordered: list[tuple[str, str, bool]] = []
    for offset in range(max(PRIMARY_COUNTS.values())):
        for job in JOBS:
            job_id = job["demo_job_id"]
            if offset < len(by_job[job_id]):
                ordered.append((by_job[job_id][offset]["demo_candidate_id"], job_id, True))
    ordered.extend([
        ("CAND-004", "JOB-BE", False),
        ("CAND-011", "JOB-DA", False),
        ("CAND-018", "JOB-QA", False),
        ("CAND-044", "JOB-AI", False),
    ])
    return ordered


def scenario_pool() -> list[str]:
    values = [name for name, count in SCENARIO_COUNTS.items() for _ in range(count)]
    random.Random(RNG_SEED).shuffle(values)
    return values


def place_closed_job_pauses(
    app_specs: list[tuple[str, str, bool]],
    scenarios: list[str],
) -> list[str]:
    """Keep job_closed pauses on the one historical closed job."""
    result = list(scenarios)
    pause_indexes = [index for index, value in enumerate(result) if value == "processing_paused"]
    closed_job_indexes = [
        index for index, (_, job_id, _) in enumerate(app_specs)
        if job_id == "JOB-DA"
    ]
    for pause_index, target_index in zip(pause_indexes, closed_job_indexes):
        if pause_index == target_index:
            continue
        result[pause_index], result[target_index] = result[target_index], result[pause_index]
    return result


def assign_sources(app_specs: list[tuple[str, str, bool]], scenarios: list[str]) -> list[str]:
    sources = [""] * len(app_specs)
    passed_indexes = [index for index, scenario in enumerate(scenarios) if scenario in PASSED_SCENARIOS]
    for index in passed_indexes[:8]:
        sources[index] = "hr_direct"

    must_public = {
        index for index, scenario in enumerate(scenarios)
        if scenario.startswith("processing_") or scenario == "waiting_screening"
    }
    for index in must_public:
        if not sources[index]:
            sources[index] = "public_apply"

    for index in range(len(sources)):
        if sources.count("public_apply") >= 40:
            break
        if not sources[index]:
            sources[index] = "public_apply"
    for index in range(len(sources)):
        if not sources[index]:
            sources[index] = "hr_screening"
    return sources


def timeline_event(
    at: datetime,
    event: str,
    stage: str,
    actor: str = "system",
    record_type: str = "stage_history",
) -> dict[str, str]:
    return {
        "at": iso(at),
        "event": event,
        "to_recruitment_stage": stage,
        "actor_type": actor,
        "record_type": record_type,
    }


def make_interview(app_id: str, created_at: datetime, scenario: str, sequence: int) -> dict[str, Any]:
    is_scheduled = scenario == "scheduled_interview"
    status = "scheduled" if is_scheduled else "completed"
    decision = "pending"
    if scenario == "next_round_pending":
        decision = "next_round"
    elif scenario in {"offer_draft", "offer_sent", "offer_accepted", "admitted", "hired", "offer_declined"}:
        decision = "proceed_offer"
    elif scenario == "interview_rejected":
        decision = "rejected"
    elif scenario == "candidate_withdrew":
        decision = "candidate_withdrew"
    scheduled_start = (
        DATASET_AS_OF + timedelta(days=2 + sequence % 4, hours=sequence % 3)
        if is_scheduled
        else created_at + timedelta(days=1, hours=sequence % 4)
    )
    feedback_at = None if is_scheduled else scheduled_start + timedelta(hours=2)
    return {
        "demo_interview_id": f"INT-{app_id[-3:]}-01",
        "round_number": 1,
        "interview_type": ["video", "phone", "onsite"][sequence % 3],
        "status": status,
        "scheduled_start_at": iso(scheduled_start),
        "duration_minutes": [45, 60, 75][sequence % 3],
        "timezone": "Asia/Shanghai",
        "interviewer_names": [["陈舟"], ["赵宁", "何川"], ["王澄"]][sequence % 3],
        "location": "星港创新中心 A 座" if sequence % 3 == 2 else None,
        "meeting_link": "https://meeting.portfolio.example/demo-room" if sequence % 3 == 0 else None,
        "decision": decision,
        "feedback_summary": None if is_scheduled else "候选人能够说明本人职责和关键取舍；后续决定仅基于岗位相关证据。",
        "strengths": [] if is_scheduled else ["表达结构清晰", "能够结合实例说明实现与验证"],
        "concerns": [] if is_scheduled else (["复杂场景经验仍需补充"] if decision in {"pending", "next_round"} else []),
        "follow_up_questions": [] if is_scheduled else ["请进一步说明失败路径和监控方案"],
        "feedback_submitted_by_label": None if is_scheduled else "本地 HR（未认证）",
        "feedback_submitted_at": iso(feedback_at) if feedback_at else None,
        "created_at": iso(created_at),
    }


def offer_status_for_scenario(scenario: str) -> str | None:
    return {
        "offer_draft": "draft",
        "offer_sent": "sent",
        "offer_accepted": "accepted",
        "admitted": "accepted",
        "hired": "accepted",
        "offer_declined": "declined",
    }.get(scenario)


def make_offer(app_id: str, job_id: str, created_at: datetime, scenario: str, sequence: int) -> dict[str, Any] | None:
    status = offer_status_for_scenario(scenario)
    if status is None:
        return None
    job_title = next(job["create_payload"]["title"] for job in JOBS if job["demo_job_id"] == job_id)
    salary_base = {"JOB-AI": 26000, "JOB-BE": 24000, "JOB-QA": 21000, "JOB-FE": 23000, "JOB-DA": 19000}[job_id]
    sent_at = None if status == "draft" else created_at + timedelta(hours=12)
    responded_at = sent_at + timedelta(days=2) if status in {"accepted", "declined"} else None
    valid_until = (created_at + timedelta(days=10)).date().isoformat()
    start_date = (created_at + timedelta(days=30)).date().isoformat()
    return {
        "demo_offer_id": f"OFF-{app_id[-3:]}-01",
        "version_number": 1,
        "status": status,
        "position_title": job_title,
        "currency": "CNY",
        "salary_period": "monthly",
        "base_salary_amount": str(salary_base + (sequence % 4) * 1000) + ".00",
        "salary_months": "13.0",
        "bonus_note": "年度绩效奖金按公司虚构演示政策执行",
        "benefits_note": "五险一金、年度体检与学习预算；全部为作品集虚构信息",
        "valid_until": valid_until,
        "expected_start_date": start_date,
        "note": "作品集演示专用虚构 Offer，不构成真实承诺。",
        "created_at": iso(created_at),
        "sent_at": iso(sent_at) if sent_at else None,
        "responded_at": iso(responded_at) if responded_at else None,
        "closed_at": None,
    }


def processing_state(source: str, scenario: str, applied_at: datetime, sequence: int) -> dict[str, Any] | None:
    if source != "public_apply":
        return None
    if scenario == "processing_failed":
        return {
            "status": "failed", "current_step": "extract_text", "attempt_count": 2,
            "started_at": iso(applied_at + timedelta(minutes=2)),
            "completed_at": iso(applied_at + timedelta(minutes=8)),
            "error_code": "RESUME_TEXT_EXTRACTION_FAILED",
            "error_message": "无法从演示文件中提取可用文本，请核对文件后人工重试。",
        }
    if scenario == "processing_paused":
        return {
            "status": "paused", "current_step": "extract_text", "attempt_count": 1,
            "waiting_reason": "job_closed",
        }
    warnings = ["RESUME_STRUCTURE_FAILED"] if sequence % 11 == 0 else []
    return {
        "status": "succeeded_with_warnings" if warnings else "succeeded",
        "current_step": "completed",
        "attempt_count": 1,
        "started_at": iso(applied_at + timedelta(minutes=2)),
        "completed_at": iso(applied_at + timedelta(hours=12, minutes=5)),
        "warning_codes": warnings,
    }


def current_state_for_scenario(scenario: str) -> tuple[str, str, str, str | None]:
    if scenario == "backup":
        return "active", "backup", "backup", None
    if scenario == "rejected":
        return "ended", "rejected", "rejected", "screening_rejected"
    if scenario in {"processing_failed", "processing_paused"}:
        return "active", "applied", "pending", None
    if scenario == "screening_ready_pending":
        return "active", "hr_review", "pending", None
    if scenario == "passed_no_interview":
        return "active", "screening_passed", "passed", None
    if scenario in {"scheduled_interview", "completed_pending", "next_round_pending"}:
        return "active", "interview", "passed", None
    if scenario in {"offer_draft", "offer_sent"}:
        return "active", "offer", "passed", None
    if scenario == "offer_accepted":
        return "active", "offer_accepted", "passed", None
    if scenario == "admitted":
        return "active", "admitted", "passed", None
    if scenario == "hired":
        return "ended", "hired", "passed", "hired"
    if scenario == "interview_rejected":
        return "ended", "rejected", "passed", "interview_rejected"
    if scenario == "offer_declined":
        return "ended", "offer", "passed", "offer_declined"
    if scenario == "candidate_withdrew":
        return "ended", "interview", "passed", "candidate_withdrew"
    raise ValueError(f"unknown scenario: {scenario}")


def build_application(
    sequence: int,
    spec: tuple[str, str, bool],
    scenario: str,
    source: str,
) -> dict[str, Any]:
    candidate_id, job_id, is_primary = spec
    app_id = f"APP-{sequence:03d}"
    applied_at = APPLIED_BASE + timedelta(days=sequence - 1, hours=sequence % 7)
    lifecycle, stage, hr_decision, final_outcome = current_state_for_scenario(scenario)
    initial_event = {
        "public_apply": "public_application_received",
        "hr_direct": "hr_direct_entry",
        "hr_screening": "application_created",
    }[source]
    initial_stage = "screening_passed" if source == "hr_direct" else "applied"
    timeline = [timeline_event(applied_at, initial_event, initial_stage, "hr" if source == "hr_direct" else "system")]
    passed_at = applied_at if source == "hr_direct" else applied_at + timedelta(hours=18 + sequence % 13)
    if (
        source != "hr_direct"
        and scenario not in {"processing_failed", "processing_paused"}
    ):
        timeline.append(
            timeline_event(
                applied_at + timedelta(hours=12),
                "ai_screening_completed",
                "hr_review",
                "system",
            )
        )
    if scenario in PASSED_SCENARIOS and source != "hr_direct":
        timeline.append(timeline_event(passed_at, "meets_requirements", "screening_passed", "hr"))
    elif scenario == "backup":
        timeline.append(timeline_event(applied_at + timedelta(days=1), "minor_capability_gap", "backup", "hr"))
    elif scenario == "rejected":
        timeline.append(timeline_event(applied_at + timedelta(days=1), "required_experience_missing", "rejected", "hr"))
    elif scenario == "screening_ready_pending":
        timeline.append(timeline_event(applied_at + timedelta(hours=8), "ai_screening_completed", "hr_review", "system"))

    interview = None
    offer = None
    if scenario in INTERVIEW_ENTERED_SCENARIOS:
        interview_created = passed_at + timedelta(days=2, hours=sequence % 5)
        interview = make_interview(app_id, interview_created, scenario, sequence)
        timeline.append(timeline_event(interview_created, "interview_scheduled", "interview", "hr"))
        feedback_at = interview.get("feedback_submitted_at")
        if feedback_at:
            feedback_dt = datetime.fromisoformat(feedback_at)
            if scenario == "completed_pending":
                timeline.append(timeline_event(feedback_dt, "interview_round_completed", "interview", "hr", "activity_log"))
            elif scenario == "next_round_pending":
                timeline.append(timeline_event(feedback_dt, "interview_next_round", "interview", "hr", "activity_log"))
            elif scenario == "interview_rejected":
                timeline.append(timeline_event(feedback_dt, "interview_rejected", "rejected", "hr"))
            elif scenario == "candidate_withdrew":
                timeline.append(timeline_event(feedback_dt, "candidate_withdrew", "interview", "hr"))
            elif offer_status_for_scenario(scenario):
                timeline.append(timeline_event(feedback_dt, "interview_proceed_offer", "offer", "hr"))
            if offer_status_for_scenario(scenario):
                offer_created = feedback_dt + timedelta(days=1)
                timeline.append(timeline_event(offer_created, "offer_created", "offer", "hr", "activity_log"))
                offer = make_offer(app_id, job_id, offer_created, scenario, sequence)
                if offer and offer["sent_at"]:
                    sent_dt = datetime.fromisoformat(offer["sent_at"])
                    timeline.append(timeline_event(sent_dt, "offer_sent", "offer", "hr", "activity_log"))
                if offer and offer["responded_at"]:
                    response_dt = datetime.fromisoformat(offer["responded_at"])
                    if scenario == "offer_declined":
                        timeline.append(timeline_event(response_dt, "offer_declined", "offer", "system"))
                    else:
                        timeline.append(timeline_event(response_dt, "offer_accepted", "offer_accepted", "system"))
                        if scenario in ADMITTED_SCENARIOS:
                            admitted_at = response_dt + timedelta(days=1)
                            timeline.append(timeline_event(admitted_at, "application_admitted", "admitted", "hr"))
                            if scenario == "hired":
                                timeline.append(timeline_event(admitted_at + timedelta(days=7), "application_hired", "hired", "hr"))

    screening_plan = "not_generated"
    if source == "hr_direct":
        screening_plan = "not_required_for_hr_direct"
    elif scenario in {"processing_failed", "processing_paused"}:
        screening_plan = "pending_or_failed"
    else:
        screening_plan = "generate_through_real_model_when_imported"

    return {
        "demo_application_id": app_id,
        "demo_candidate_id": candidate_id,
        "demo_job_id": job_id,
        "is_primary_application": is_primary,
        "source": source,
        "applied_at": iso(applied_at),
        "scenario": scenario,
        "lifecycle_status": lifecycle,
        "recruitment_stage": stage,
        "hr_decision": hr_decision,
        "final_outcome": final_outcome,
        "processing_run": processing_state(source, scenario, applied_at, sequence),
        "screening_plan": screening_plan,
        "timeline": sorted(timeline, key=lambda item: item["at"]),
        "interviews": [interview] if interview else [],
        "offers": [offer] if offer else [],
    }


def build_applications(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specs = interleaved_primary_applications(candidates)
    scenarios = place_closed_job_pauses(specs, scenario_pool())
    sources = assign_sources(specs, scenarios)
    return [
        build_application(index, spec, scenario, source)
        for index, (spec, scenario, source) in enumerate(zip(specs, scenarios, sources), start=1)
    ]


def conversion_rate(count: int, previous: int | None) -> float | None:
    if not previous:
        return None
    return round(count * 100 / previous, 2)


def statistics_for(applications: list[dict[str, Any]]) -> dict[str, Any]:
    scenario_counter = Counter(app["scenario"] for app in applications)
    counts = {
        "applications": len(applications),
        "screening_passed": sum(scenario_counter[name] for name in PASSED_SCENARIOS),
        "interview_entered": sum(scenario_counter[name] for name in INTERVIEW_ENTERED_SCENARIOS),
        "interview_completed": sum(scenario_counter[name] for name in INTERVIEW_COMPLETED_SCENARIOS),
        "offer_sent": sum(scenario_counter[name] for name in OFFER_SENT_SCENARIOS),
        "offer_accepted": sum(scenario_counter[name] for name in OFFER_ACCEPTED_SCENARIOS),
        "admitted": sum(scenario_counter[name] for name in ADMITTED_SCENARIOS),
        "hired": scenario_counter["hired"],
    }
    funnel = []
    previous: int | None = None
    for key, count in counts.items():
        funnel.append({"key": key, "count": count, "conversion_rate": conversion_rate(count, previous)})
        previous = count
    todo_map = {
        "scheduled_interviews": scenario_counter["scheduled_interview"],
        "pending_interview_decisions": scenario_counter["completed_pending"],
        "next_round_not_scheduled": scenario_counter["next_round_pending"],
        "draft_offers": scenario_counter["offer_draft"],
        "sent_offers": scenario_counter["offer_sent"],
        "accepted_offers": scenario_counter["offer_accepted"],
        "admitted_applications": scenario_counter["admitted"],
    }
    todo_map["total"] = sum(todo_map.values())
    return {"funnel": funnel, "todos": todo_map}


def duration_statistics(applications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for app in applications:
        events = defaultdict(list)
        for item in app["timeline"]:
            events[item["to_recruitment_stage"]].append(datetime.fromisoformat(item["at"]))
        applied_at = datetime.fromisoformat(app["applied_at"])
        passed_at = min(events["screening_passed"]) if events["screening_passed"] else None
        interviews = app["interviews"]
        first_interview = min((datetime.fromisoformat(row["created_at"]) for row in interviews), default=None)
        completed = [datetime.fromisoformat(row["feedback_submitted_at"]) for row in interviews if row["status"] == "completed" and row["feedback_submitted_at"]]
        last_completed = max(completed) if completed else None
        offer_entered = min(events["offer"]) if events["offer"] else None
        offers = app["offers"]
        sent = min((datetime.fromisoformat(row["sent_at"]) for row in offers if row["sent_at"]), default=None)
        responded = min((datetime.fromisoformat(row["responded_at"]) for row in offers if row["responded_at"]), default=None)
        accepted = min(events["offer_accepted"]) if events["offer_accepted"] else None
        admitted = min(events["admitted"]) if events["admitted"] else None
        hired = min(events["hired"]) if events["hired"] else None
        pairs = {
            "application_to_screening_passed": (applied_at, passed_at),
            "screening_passed_to_first_interview": (passed_at, first_interview),
            "first_interview_to_last_completed": (first_interview, last_completed),
            "offer_entered_to_sent": (offer_entered, sent),
            "offer_sent_to_response": (sent, responded),
            "offer_accepted_to_admitted": (accepted, admitted),
            "admitted_to_hired": (admitted, hired),
        }
        for key, (start, end) in pairs.items():
            if start is not None and end is not None and end >= start:
                buckets[key].append((end - start).total_seconds() / 3600)
    order = [
        "application_to_screening_passed", "screening_passed_to_first_interview",
        "first_interview_to_last_completed", "offer_entered_to_sent",
        "offer_sent_to_response", "offer_accepted_to_admitted", "admitted_to_hired",
    ]
    return [
        {
            "key": key,
            "average_hours": round(sum(buckets[key]) / len(buckets[key]), 2) if buckets[key] else None,
            "sample_count": len(buckets[key]),
        }
        for key in order
    ]


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    candidates = build_candidates()
    applications = build_applications(candidates)
    for candidate in candidates:
        resume_path = ROOT / candidate["resume_file"]
        resume_path.write_text(render_resume(candidate), encoding="utf-8")

    metadata = {
        "dataset_version": DATASET_VERSION,
        "dataset_as_of": iso(DATASET_AS_OF),
        "fictional_data_only": True,
        "automatic_database_write": False,
        "real_model_outputs_included": False,
    }
    write_json(ROOT / "jobs.json", {**metadata, "jobs": JOBS})
    write_json(ROOT / "candidates.json", {**metadata, "candidates": candidates})
    write_json(ROOT / "applications.json", {**metadata, "applications": applications})

    overall = statistics_for(applications)
    overall["durations"] = duration_statistics(applications)
    by_job = {}
    for job in JOBS:
        job_id = job["demo_job_id"]
        rows = [app for app in applications if app["demo_job_id"] == job_id]
        result = statistics_for(rows)
        result["durations"] = duration_statistics(rows)
        by_job[job_id] = result
    write_json(
        ROOT / "expected_statistics.json",
        {
            **metadata,
            "candidate_count": len(candidates),
            "application_count": len(applications),
            "source_counts": dict(sorted(Counter(app["source"] for app in applications).items())),
            "scenario_counts": dict(sorted(Counter(app["scenario"] for app in applications).items())),
            "overall": overall,
            "by_job": by_job,
        },
    )
    print(f"generated {len(JOBS)} jobs, {len(candidates)} candidates, {len(applications)} applications")


if __name__ == "__main__":
    main()
