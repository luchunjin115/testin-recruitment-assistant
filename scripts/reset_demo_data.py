"""Reset demo candidates while keeping job management data.

This script is intentionally deterministic so it can be run before a demo:
- keep and enrich jobs
- clear candidate-related records and old uploaded resumes
- generate 30 candidates whose roles all come from active jobs
"""
import json
import os
import shutil
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(str(BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal, init_db, run_migrations  # noqa: E402
from app.models.activity_log import ActivityLog  # noqa: E402
from app.models.candidate import Candidate  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.stage_change_log import StageChangeLog  # noqa: E402
from app.seed_data import ALL_SEED_CANDIDATES  # noqa: E402
from app.services.candidate_service import candidate_service  # noqa: E402


def get_upload_dir():
    upload_dir = Path(get_settings().UPLOAD_DIR)
    if not upload_dir.is_absolute():
        upload_dir = BACKEND_DIR / get_settings().UPLOAD_DIR.replace("./", "")
    return upload_dir


DEMO_JOBS = [
    {
        "title": "测试工程师",
        "department": "质量保障部",
        "description": "负责 Web、移动端和开放接口的功能测试、回归测试与线上质量跟踪，参与需求评审并推动缺陷闭环。",
        "requirements": "能独立设计测试用例，熟悉缺陷生命周期和常见测试方法；具备接口测试经验，能与产品、研发高效沟通；有自动化测试基础优先。",
        "required_skills": "测试用例,接口测试,Postman,SQL",
        "bonus_skills": "Python,Selenium,JMeter,自动化测试",
        "education_requirement": "本科",
        "experience_requirement": "0年以上",
        "job_keywords": "软件测试,质量保障,测试流程,缺陷跟踪",
        "risk_keywords": "无测试经验,缺少接口测试,频繁跳槽",
    },
    {
        "title": "自动化测试工程师",
        "department": "质量保障部",
        "description": "负责自动化测试框架建设、接口/UI 自动化脚本开发、CI/CD 测试流水线接入和质量效率提升。",
        "requirements": "熟悉 Python 或其他脚本语言，能搭建或维护自动化测试框架；理解接口测试、UI 自动化、测试数据管理和持续集成流程。",
        "required_skills": "Python,Selenium,Pytest,自动化测试",
        "bonus_skills": "Appium,Jenkins,CI/CD,JMeter",
        "education_requirement": "本科",
        "experience_requirement": "1年以上",
        "job_keywords": "测试框架,接口自动化,UI自动化,质量效率",
        "risk_keywords": "只会手工测试,缺少编程经验,脚本能力弱",
    },
    {
        "title": "AI应用实习生",
        "department": "AI应用部",
        "description": "参与 AI 应用原型验证、Prompt 调优、数据清洗、效果评估和业务场景落地支持。",
        "requirements": "具备 Python 基础和较强学习能力，了解机器学习或大模型应用；能阅读技术文档，愿意快速试错并沉淀实验记录。",
        "required_skills": "Python,Prompt,LLM,数据处理",
        "bonus_skills": "RAG,LangChain,机器学习,自然语言处理",
        "education_requirement": "本科",
        "experience_requirement": "0年以上",
        "job_keywords": "AI工具,大模型,应用落地,实验评估",
        "risk_keywords": "无编程基础,不了解大模型,缺少学习记录",
    },
    {
        "title": "数据分析师",
        "department": "数据部",
        "description": "负责招聘、运营或产品数据分析，建设指标体系、输出专题分析、支持业务决策和 A/B 实验评估。",
        "requirements": "熟练使用 SQL 和 Excel，具备数据清洗、可视化和统计分析能力；能把分析结论转化为业务建议，有 Python/BI 工具经验优先。",
        "required_skills": "SQL,Python,Excel,数据分析",
        "bonus_skills": "Tableau,PowerBI,A/B测试,统计学",
        "education_requirement": "本科",
        "experience_requirement": "1年以上",
        "job_keywords": "指标体系,数据可视化,用户行为,业务分析",
        "risk_keywords": "缺少SQL经验,只会报表,业务理解弱",
    },
    {
        "title": "前端开发工程师",
        "department": "研发部",
        "description": "负责 HR SaaS 前端业务页面、表单流程、数据看板和组件化能力建设，关注交互体验与工程质量。",
        "requirements": "熟悉 React/TypeScript/CSS，理解组件设计、状态管理和前端工程化；能与后端协作完成接口联调，有复杂表格/表单经验优先。",
        "required_skills": "React,TypeScript,HTML,CSS",
        "bonus_skills": "Vue,Vite,Ant Design,前端工程化",
        "education_requirement": "本科",
        "experience_requirement": "1年以上",
        "job_keywords": "组件化,交互体验,浏览器,接口联调",
        "risk_keywords": "缺少项目经验,不了解工程化,样式基础弱",
    },
    {
        "title": "后端开发工程师",
        "department": "研发部",
        "description": "负责招聘系统后端服务、业务 API、数据模型、权限与任务处理能力建设，保障稳定性和可维护性。",
        "requirements": "熟悉 Java 或 Python 后端开发，理解数据库建模、缓存、接口设计和基础性能优化；有 FastAPI 或 Spring Boot 项目经验优先。",
        "required_skills": "Java,Python,MySQL,Redis",
        "bonus_skills": "FastAPI,Spring Boot,Docker,消息队列",
        "education_requirement": "本科",
        "experience_requirement": "1年以上",
        "job_keywords": "后端服务,API设计,数据库建模,性能优化",
        "risk_keywords": "缺少后端项目,数据库薄弱,接口设计混乱",
    },
    {
        "title": "产品助理",
        "department": "产品部",
        "description": "协助产品经理完成需求调研、竞品分析、PRD 撰写、原型设计、项目推进和上线效果跟踪。",
        "requirements": "具备清晰表达和文档能力，能拆解用户场景并跟进研发落地；有数据分析、用户研究或 B 端工具经验优先。",
        "required_skills": "需求分析,PRD,原型设计,用户调研",
        "bonus_skills": "Axure,Figma,SQL,竞品分析",
        "education_requirement": "本科",
        "experience_requirement": "0年以上",
        "job_keywords": "用户需求,项目协作,产品文档,业务流程",
        "risk_keywords": "表达不清,逻辑薄弱,缺少落地经验",
    },
    {
        "title": "UI设计师",
        "department": "设计部",
        "description": "负责 B 端产品界面设计、设计规范维护、交互细节优化和研发交付标注，提升产品一致性和可用性。",
        "requirements": "熟练使用 Figma 或 Sketch，具备视觉设计、交互设计和设计规范意识；能根据业务场景输出清晰可落地的页面方案。",
        "required_skills": "Figma,Sketch,视觉设计,交互设计",
        "bonus_skills": "设计规范,动效设计,用户体验,可用性测试",
        "education_requirement": "本科",
        "experience_requirement": "1年以上",
        "job_keywords": "B端设计,界面设计,组件规范,设计交付",
        "risk_keywords": "缺少B端经验,作品集薄弱,规范意识弱",
    },
]


NAME_POOL = [
    "林悦", "周子航", "陈思雨", "王浩然", "李嘉宁", "赵一诺", "孙明哲", "钱若溪",
    "吴承泽", "郑雅婷", "冯亦辰", "蒋可欣", "沈博文", "韩雨桐", "杨景行", "何思远",
    "高若琳", "许晨曦", "宋梓涵", "唐亦凡", "彭清越", "吕佳怡", "董明轩", "袁书瑶",
    "邓子墨", "曹安琪", "崔宇航", "程知夏", "罗嘉树", "梁婉宁",
]

SCHOOLS = [
    ("北京交通大学", "本科", "软件工程"),
    ("华东师范大学", "硕士", "计算机科学与技术"),
    ("南京邮电大学", "本科", "信息管理与信息系统"),
    ("深圳大学", "本科", "数据科学与大数据技术"),
    ("武汉理工大学", "本科", "自动化"),
    ("西安电子科技大学", "硕士", "软件工程"),
    ("广东工业大学", "本科", "数字媒体技术"),
    ("浙江工业大学", "本科", "产品设计"),
]

CHANNELS = ["在线投递", "HR手动录入", "Boss直聘", "内推", "拉勾", "猎聘", "企业微信群"]
SEED_PHONE_POOL = [item["phone"] for item in ALL_SEED_CANDIDATES]

ROLE_SKILLS = {
    "测试工程师": ["测试用例", "接口测试", "Postman", "SQL", "缺陷跟踪", "Python"],
    "自动化测试工程师": ["Python", "Selenium", "Pytest", "自动化测试", "Jenkins", "接口测试"],
    "AI应用实习生": ["Python", "Prompt", "LLM", "数据处理", "RAG", "AI工具"],
    "数据分析师": ["SQL", "Python", "Excel", "数据分析", "Tableau", "可视化"],
    "前端开发工程师": ["React", "TypeScript", "HTML", "CSS", "Ant Design", "Vite"],
    "后端开发工程师": ["Java", "Python", "FastAPI", "Spring Boot", "MySQL", "Redis"],
    "产品助理": ["需求分析", "PRD", "原型设计", "用户调研", "Axure", "竞品分析"],
    "UI设计师": ["Figma", "Sketch", "视觉设计", "交互设计", "设计规范", "用户体验"],
}


def ensure_jobs(db):
    existing = {job.title: job for job in db.query(Job).all()}
    for item in DEMO_JOBS:
        job = existing.get(item["title"])
        if job:
            for key, value in item.items():
                setattr(job, key, value)
            job.status = "active"
        else:
            db.add(Job(**item, status="active"))
    db.commit()
    return {job.title: job for job in db.query(Job).filter(Job.status == "active").all()}


def clear_candidate_data(db):
    db.query(StageChangeLog).delete()
    db.query(ActivityLog).delete()
    db.query(Candidate).delete()
    db.commit()

    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    for item in upload_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(str(item))


def pick_time(index):
    now = datetime.now().replace(second=0, microsecond=0)
    today_start = datetime.combine(date.today(), datetime.min.time())
    offsets = [0] * 5 + [1] * 3 + [2] * 2 + [3] * 3 + [4] * 3 + [5] * 2 + [6] * 2
    offsets += [8, 9, 10, 12, 14, 16, 18, 21, 25, 30]
    days = offsets[index]
    if days == 0:
        return max(today_start, now - timedelta(minutes=index * 2))
    return datetime.combine(date.today() - timedelta(days=days), time(14, 0)) + timedelta(minutes=(index * 7) % 50)


def build_plan():
    plan = []
    plan += [("pending", "新投递")] * 7
    plan += [("pending", "待筛选")] * 4
    plan += [("rejected", "淘汰")]
    plan += [("passed", "待约面")] * 3
    plan += [("passed", "已约面")] * 3
    plan += [("passed", "面试中")] * 3
    plan += [("passed", "复试")] * 2
    plan += [("passed", "offer")] * 2
    plan += [("passed", "入职")]
    plan += [("passed", "淘汰")]
    plan += [("backup", "待约面")] * 2
    plan += [("backup", "已约面")]
    return plan


def make_screening(role, status, index):
    skills = ROLE_SKILLS[role]
    if index % 7 == 0 and status == "pending":
        return None, "", "", "", []

    base = 86 if status == "passed" else 72 if status == "backup" else 78 if status == "pending" else 48
    score = max(42, min(96, base + ((index % 5) - 2) * 4))
    priority = "高优先级" if score >= 82 else "中优先级" if score >= 62 else "低优先级"
    if status == "rejected":
        result = "暂缓"
    elif status == "backup":
        result = "备选"
    else:
        result = "建议初筛" if score >= 70 else "暂缓"
    hit = "、".join(skills[:3])
    bonus = "、".join(skills[3:5])
    reason = f"岗位要求命中 {hit}；加分项涉及 {bonus}。候选人与{role}要求匹配度为 {score} 分，建议 HR 结合项目经历复核。"
    risks = ["暂无明显风险"]
    if score < 60:
        risks = ["岗位核心技能不足", "项目经历与目标岗位弱相关"]
    elif index % 6 == 0:
        risks = ["项目深度需面试确认"]
    elif index % 5 == 0:
        risks = ["缺少最近项目细节"]
    return score, priority, result, reason, risks


def build_candidate(job_map, index, status, stage, upload_dir):
    roles = list(ROLE_SKILLS.keys())
    role = roles[index % len(roles)]
    job = job_map[role]
    name = NAME_POOL[index]
    school, degree, major = SCHOOLS[index % len(SCHOOLS)]
    created_at = pick_time(index)
    updated_at = created_at + timedelta(hours=2)

    # Deliberately old timestamps for overdue demo cases.
    if index in [5, 6]:
        created_at = datetime.combine(date.today() - timedelta(days=2), time(12, 0)) + timedelta(minutes=index)
        updated_at = created_at
    if stage == "待约面" and index in [12, 13]:
        created_at = datetime.combine(date.today() - timedelta(days=6), time(12, 0)) + timedelta(minutes=index)
        updated_at = datetime.combine(date.today() - timedelta(days=4), time(12, 0)) + timedelta(minutes=index)
    if stage == "offer" and index == 26:
        created_at = datetime.now() - timedelta(days=10)
        updated_at = datetime.now() - timedelta(days=5)

    skills = ROLE_SKILLS[role][:]
    if status == "rejected":
        skills = skills[:2] + ["基础薄弱"]
    score, priority, result, reason, risks = make_screening(role, status, index)

    resume_path = ""
    resume_filename = ""
    resume_file_type = ""
    resume_file_size = None
    resume_uploaded_at = None
    if index < 21:
        resume_filename = f"demo_resume_{index + 1:02d}_{name}.txt"
        resume_file = upload_dir / resume_filename
        resume_text = "\n".join([
            f"姓名：{name}",
            f"应聘岗位：{role}",
            f"学校：{school}",
            f"学历：{degree}",
            f"专业：{major}",
            f"技能：{'、'.join(skills)}",
            f"经历：参与过{role}相关项目，负责需求理解、方案执行、问题复盘和跨团队沟通。",
            f"自我介绍：关注业务价值和交付质量，希望在 Testin 云测的真实业务场景中持续成长。",
        ])
        resume_file.write_text(resume_text, encoding="utf-8")
        resume_path = str(resume_file)
        resume_file_type = "txt"
        resume_file_size = resume_file.stat().st_size
        resume_uploaded_at = created_at + timedelta(minutes=10)

    reject_reason = ""
    reject_note = ""
    if status == "rejected" or stage == "淘汰":
        reject_reason = "核心岗位技能匹配不足，暂不进入后续流程"
        reject_note = "Demo 数据：保留记录用于展示淘汰历史可追溯"

    interview_time = None
    if stage == "已约面":
        interview_time = datetime.now() + timedelta(days=(index % 3) + 1, hours=2)
        if index == 16:
            interview_time = datetime.now() - timedelta(days=2, hours=1)
            updated_at = datetime.now() - timedelta(days=3)
    elif stage == "面试中":
        interview_time = datetime.now() - timedelta(hours=2 + index % 5)

    candidate = Candidate(
        name=name,
        phone=SEED_PHONE_POOL[index] if index < len(SEED_PHONE_POOL) else f"139{index + 1:08d}",
        email=f"demo{index + 1:02d}@example.com",
        school=school,
        degree=degree,
        major=major,
        job_id=job.id,
        target_role=job.title,
        experience_years=float(index % 6),
        experience_desc=f"曾参与{role}相关项目，使用{'、'.join(skills[:4])}完成需求分析、方案落地和结果复盘。",
        skills=json.dumps(skills, ensure_ascii=False),
        self_intro=f"我对{role}方向有持续投入，熟悉{'、'.join(skills[:3])}，重视沟通、复盘和业务结果。",
        resume_path=resume_path,
        resume_filename=resume_filename,
        resume_file_type=resume_file_type,
        resume_file_size=resume_file_size,
        resume_uploaded_at=resume_uploaded_at,
        source_channel=CHANNELS[index % len(CHANNELS)],
        stage=stage,
        screening_status=status,
        interview_time=interview_time,
        interview_method="线上面试" if interview_time else "",
        interviewer="李HR" if interview_time else "",
        reject_reason=reject_reason,
        reject_note=reject_note,
        offer_position=job.title if stage == "offer" else "",
        salary_range="15k-22k" if stage == "offer" else "",
        expected_onboard_date=date.today() + timedelta(days=14) if stage == "offer" else None,
        onboard_date=date.today() - timedelta(days=3) if stage == "入职" else None,
        onboard_note="已完成入职确认" if stage == "入职" else "",
        stage_source="manual" if stage == "已约面" and index == 16 else "hr_action" if status in ["passed", "backup"] else "system_auto",
        ai_summary=f"{name}来自{school}{major}，具备{role}相关能力，核心技能包括{'、'.join(skills[:4])}。",
        ai_tags=json.dumps([degree, role, skills[0], skills[1], candidate_tag(status)], ensure_ascii=False),
        match_score=score,
        priority_level=priority,
        screening_result=result,
        screening_reason=reason,
        risk_flags=json.dumps(risks, ensure_ascii=False),
        screening_updated_at=created_at + timedelta(hours=1) if score is not None else None,
        hr_notes="Demo 候选人：用于展示招聘漏斗、AI 初筛和跟进提醒。",
        created_at=created_at,
        updated_at=updated_at,
    )
    return candidate


def candidate_tag(status):
    return {
        "pending": "待初筛",
        "passed": "已通过初筛",
        "backup": "备选",
        "rejected": "初筛淘汰",
    }[status]


def add_logs(db, candidate, index):
    created_at = candidate.created_at or datetime.now()
    db.add(ActivityLog(
        candidate_id=candidate.id,
        action="created",
        detail=f"Demo 数据创建：{candidate.name} 投递 {candidate.target_role}",
        created_at=created_at,
    ))

    if candidate.screening_status == "passed":
        stage_time = min(candidate.updated_at or created_at, datetime.now() - timedelta(hours=1))
        db.add(StageChangeLog(
            candidate_id=candidate.id,
            from_stage="新投递",
            to_stage=candidate.stage,
            trigger_reason="通过初筛，进入正式招聘流程",
            trigger_source="hr_action",
            created_at=stage_time,
        ))
        db.add(ActivityLog(
            candidate_id=candidate.id,
            action="screening_passed",
            detail="通过初筛：pending -> passed，候选人进入正式招聘流程",
            created_at=stage_time,
        ))
    elif candidate.screening_status == "backup":
        stage_time = min(candidate.updated_at or created_at, datetime.now() - timedelta(hours=1))
        db.add(StageChangeLog(
            candidate_id=candidate.id,
            from_stage="新投递",
            to_stage=candidate.stage,
            trigger_reason="通过初筛，进入正式招聘流程",
            trigger_source="hr_action",
            created_at=stage_time - timedelta(minutes=20),
        ))
        db.add(ActivityLog(
            candidate_id=candidate.id,
            action="screening_passed",
            detail="通过初筛：pending -> passed，候选人进入正式招聘流程",
            created_at=stage_time - timedelta(minutes=20),
        ))
        db.add(ActivityLog(
            candidate_id=candidate.id,
            action="screening_backup",
            detail="正式流程标记备选：候选人进入候选人列表备选视图",
            created_at=stage_time,
        ))
    elif candidate.screening_status == "rejected":
        db.add(StageChangeLog(
            candidate_id=candidate.id,
            from_stage="新投递",
            to_stage="淘汰",
            trigger_reason=f"初筛淘汰: {candidate.reject_reason}",
            trigger_source="hr_action",
            created_at=created_at + timedelta(hours=1),
        ))
        db.add(ActivityLog(
            candidate_id=candidate.id,
            action="screening_rejected",
            detail=f"初筛淘汰：原因：{candidate.reject_reason}",
            created_at=created_at + timedelta(hours=1),
        ))

    if candidate.stage == "已约面" and candidate.interview_time:
        log_time = candidate.updated_at or created_at
        db.add(ActivityLog(
            candidate_id=candidate.id,
            action="hr_action",
            detail=f"安排面试：{candidate.name}（{candidate.interview_time.strftime('%Y-%m-%d %H:%M')}）",
            created_at=log_time,
        ))
    if candidate.stage == "offer":
        db.add(ActivityLog(
            candidate_id=candidate.id,
            action="hr_action",
            detail=f"发放 Offer：{candidate.name}（{candidate.offer_position}）",
            created_at=candidate.updated_at or created_at,
        ))


def reset_demo_data():
    init_db()
    run_migrations()

    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        job_map = ensure_jobs(db)
        clear_candidate_data(db)

        plan = build_plan()
        candidates = []
        for index, (status, stage) in enumerate(plan):
            candidate = build_candidate(job_map, index, status, stage, upload_dir)
            db.add(candidate)
            candidates.append(candidate)
        db.commit()

        for index, candidate in enumerate(candidates):
            db.refresh(candidate)
            add_logs(db, candidate, index)
        db.commit()

        active_jobs = db.query(Job).filter(Job.status == "active").order_by(Job.id).all()
        total = db.query(Candidate).count()
        ai_pool = db.query(Candidate).filter(Candidate.screening_status == "pending").count()
        _, formal = candidate_service.list_candidates(db, candidate_scope="formal", page_size=100)
        _, backup = candidate_service.list_candidates(db, candidate_scope="backup", page_size=100)
        _, rejected = candidate_service.list_candidates(db, candidate_scope="rejected", page_size=100)
        resumes = len([c for c in candidates if c.resume_path])
        invalid_roles = db.query(Candidate).outerjoin(Job, Candidate.job_id == Job.id).filter(
            (Job.id.is_(None)) | (Candidate.target_role != Job.title)
        ).count()

        print("演示数据重置完成")
        print(f"active 岗位：{', '.join(job.title for job in active_jobs)}")
        print(f"候选人总数：{total}")
        print(f"AI 初筛中心默认待初筛候选人：{ai_pool}")
        print(f"候选人列表默认正式流程：{formal}")
        print(f"候选人列表备选视图：{backup}")
        print(f"淘汰候选人视图：{rejected}")
        print(f"模拟 TXT 简历附件：{resumes}")
        print(f"岗位不一致候选人：{invalid_roles}")
    finally:
        db.close()


if __name__ == "__main__":
    reset_demo_data()
