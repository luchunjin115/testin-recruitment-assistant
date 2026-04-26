from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.candidate import Candidate
from ..models.job import Job
from ..schemas.job import JobCreate, JobUpdate, VALID_JOB_STATUSES


DEFAULT_JOBS = [
    {
        "title": "测试工程师",
        "department": "质量保障部",
        "description": "负责 Web、移动端和开放接口的功能测试、回归测试与线上质量跟踪，参与需求评审并推动缺陷闭环。",
        "requirements": "能独立设计测试用例，熟悉缺陷生命周期和常见测试方法；具备接口测试经验，能与产品、研发高效沟通；有自动化测试基础优先。",
        "required_skills": "测试用例,接口测试,Postman,缺陷跟踪",
        "bonus_skills": "Python,Selenium,JMeter,自动化测试",
        "education_requirement": "本科",
        "experience_requirement": "0年以上",
        "job_keywords": "软件测试,质量保障,测试流程,沟通",
        "risk_keywords": "无测试经验,频繁跳槽",
    },
    {
        "title": "自动化测试工程师",
        "department": "质量保障部",
        "description": "负责自动化测试框架建设、接口/UI 自动化脚本开发、CI/CD 测试流水线接入和质量效率提升。",
        "requirements": "熟悉 Python 或其他脚本语言，能搭建或维护自动化测试框架；理解接口测试、UI 自动化、测试数据管理和持续集成流程。",
        "required_skills": "Python,自动化测试,Selenium,接口测试",
        "bonus_skills": "Appium,Jenkins,Pytest,JMeter",
        "education_requirement": "本科",
        "experience_requirement": "1年以上",
        "job_keywords": "测试框架,CI/CD,质量效率,脚本开发",
        "risk_keywords": "只会手工测试,缺少编程经验",
    },
    {
        "title": "AI应用实习生",
        "department": "AI应用部",
        "description": "参与 AI 应用原型验证、Prompt 调优、数据清洗、效果评估和业务场景落地支持。",
        "requirements": "具备 Python 基础和较强学习能力，了解机器学习或大模型应用；能阅读技术文档，愿意快速试错并沉淀实验记录。",
        "required_skills": "Python,AI应用,数据处理",
        "bonus_skills": "机器学习,Prompt,大模型,自然语言处理",
        "education_requirement": "本科",
        "experience_requirement": "0年以上",
        "job_keywords": "AI,大模型,应用落地,学习能力",
        "risk_keywords": "无编程基础",
    },
    {
        "title": "数据分析师",
        "department": "数据部",
        "description": "负责招聘、运营或产品数据分析，建设指标体系、输出专题分析、支持业务决策和 A/B 实验评估。",
        "requirements": "熟练使用 SQL 和 Excel，具备数据清洗、可视化和统计分析能力；能把分析结论转化为业务建议，有 Python/BI 工具经验优先。",
        "required_skills": "SQL,数据分析,Excel,Python",
        "bonus_skills": "Tableau,机器学习,A/B测试,统计学",
        "education_requirement": "本科",
        "experience_requirement": "1年以上",
        "job_keywords": "指标体系,用户行为,数据驱动,报表",
        "risk_keywords": "缺少SQL经验",
    },
    {
        "title": "前端开发工程师",
        "department": "研发部",
        "description": "负责 HR SaaS 前端业务页面、表单流程、数据看板和组件化能力建设，关注交互体验与工程质量。",
        "requirements": "熟悉 React/TypeScript/CSS，理解组件设计、状态管理和前端工程化；能与后端协作完成接口联调，有复杂表格/表单经验优先。",
        "required_skills": "JavaScript,TypeScript,React,CSS",
        "bonus_skills": "Vue,Node.js,Vite,工程化",
        "education_requirement": "本科",
        "experience_requirement": "1年以上",
        "job_keywords": "前端工程化,组件化,交互体验,浏览器",
        "risk_keywords": "缺少项目经验",
    },
    {
        "title": "产品助理",
        "department": "产品部",
        "description": "协助产品经理完成需求调研、竞品分析、PRD 撰写、原型设计、项目推进和上线效果跟踪。",
        "requirements": "具备清晰表达和文档能力，能拆解用户场景并跟进研发落地；有数据分析、用户研究或 B 端工具经验优先。",
        "required_skills": "需求分析,文档撰写,沟通,数据分析",
        "bonus_skills": "Axure,Figma,用户研究,SQL",
        "education_requirement": "本科",
        "experience_requirement": "0年以上",
        "job_keywords": "PRD,用户需求,项目协作,原型",
        "risk_keywords": "表达不清,缺少逻辑",
    },
]


class JobService:
    def list_jobs(self, db: Session, status: Optional[str] = None) -> List[Job]:
        query = db.query(Job)
        if status:
            query = query.filter(Job.status == status)
        return query.order_by(Job.status.asc(), Job.updated_at.desc(), Job.id.desc()).all()

    def list_active_jobs(self, db: Session) -> List[Job]:
        return db.query(Job).filter(Job.status == "active").order_by(Job.title.asc()).all()

    def get_job(self, db: Session, job_id: int) -> Optional[Job]:
        return db.query(Job).filter(Job.id == job_id).first()

    def get_active_job(self, db: Session, job_id: int) -> Optional[Job]:
        return db.query(Job).filter(Job.id == job_id, Job.status == "active").first()

    def create_job(self, db: Session, data: JobCreate) -> Job:
        title = self._clean_title(data.title)
        self._validate_status(data.status)
        self._ensure_title_available(db, title)

        job = Job(
            title=title,
            department=self._clean(data.department),
            description=self._clean(data.description),
            requirements=self._clean(data.requirements),
            required_skills=self._clean(data.required_skills),
            bonus_skills=self._clean(data.bonus_skills),
            education_requirement=self._clean(data.education_requirement),
            experience_requirement=self._clean(data.experience_requirement),
            job_keywords=self._clean(data.job_keywords),
            risk_keywords=self._clean(data.risk_keywords),
            status=data.status,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def update_job(self, db: Session, job_id: int, data: JobUpdate) -> Optional[Job]:
        job = self.get_job(db, job_id)
        if not job:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data and update_data["status"] is not None:
            self._validate_status(update_data["status"])

        if "title" in update_data and update_data["title"] is not None:
            title = self._clean_title(update_data["title"])
            self._ensure_title_available(db, title, exclude_id=job_id)
            job.title = title

        for field in [
            "department", "description", "requirements", "required_skills",
            "bonus_skills", "education_requirement", "experience_requirement",
            "job_keywords", "risk_keywords", "status",
        ]:
            if field in update_data and update_data[field] is not None:
                setattr(job, field, self._clean(update_data[field]) if field != "status" else update_data[field])

        db.commit()
        db.refresh(job)
        return job

    def update_status(self, db: Session, job_id: int, status: str) -> Optional[Job]:
        self._validate_status(status)
        job = self.get_job(db, job_id)
        if not job:
            return None
        job.status = status
        db.commit()
        db.refresh(job)
        return job

    def delete_or_deactivate(self, db: Session, job_id: int) -> tuple[bool, str]:
        job = self.get_job(db, job_id)
        if not job:
            return False, "not_found"
        candidate_count = self.count_candidates(db, job.id)
        if candidate_count > 0:
            job.status = "inactive"
            db.commit()
            return True, "deactivated"
        db.delete(job)
        db.commit()
        return True, "deleted"

    def count_candidates(self, db: Session, job_id: int) -> int:
        return db.query(Candidate).filter(Candidate.job_id == job_id).count()

    def to_read(self, db: Session, job: Job) -> dict:
        return {
            "id": job.id,
            "title": job.title,
            "department": job.department or "",
            "description": job.description or "",
            "requirements": job.requirements or "",
            "required_skills": job.required_skills or "",
            "bonus_skills": job.bonus_skills or "",
            "education_requirement": job.education_requirement or "",
            "experience_requirement": job.experience_requirement or "",
            "job_keywords": job.job_keywords or "",
            "risk_keywords": job.risk_keywords or "",
            "status": job.status,
            "candidate_count": self.count_candidates(db, job.id),
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    def seed_default_jobs(self, db: Session):
        for item in DEFAULT_JOBS:
            title = self._clean_title(item["title"])
            exists = db.query(Job).filter(func.lower(Job.title) == title.lower()).first()
            if exists:
                for field in [
                    "description", "requirements", "required_skills", "bonus_skills",
                    "education_requirement", "experience_requirement", "job_keywords", "risk_keywords",
                ]:
                    if not getattr(exists, field):
                        setattr(exists, field, item.get(field, ""))
                continue
            db.add(Job(
                title=title,
                department=item.get("department", ""),
                description=item.get("description", ""),
                requirements=item.get("requirements", ""),
                required_skills=item.get("required_skills", ""),
                bonus_skills=item.get("bonus_skills", ""),
                education_requirement=item.get("education_requirement", ""),
                experience_requirement=item.get("experience_requirement", ""),
                job_keywords=item.get("job_keywords", ""),
                risk_keywords=item.get("risk_keywords", ""),
                status="active",
            ))
        db.commit()

    def backfill_candidate_job_ids(self, db: Session):
        jobs = db.query(Job).all()
        title_map = {job.title.strip(): job.id for job in jobs}
        candidates = db.query(Candidate).filter(
            Candidate.job_id.is_(None),
            Candidate.target_role.isnot(None),
            Candidate.target_role != "",
        ).all()
        changed = False
        for candidate in candidates:
            job_id = title_map.get((candidate.target_role or "").strip())
            if job_id:
                candidate.job_id = job_id
                changed = True
        if changed:
            db.commit()

    def _ensure_title_available(self, db: Session, title: str, exclude_id: Optional[int] = None):
        query = db.query(Job).filter(func.lower(Job.title) == title.lower())
        if exclude_id:
            query = query.filter(Job.id != exclude_id)
        if query.first():
            raise ValueError("岗位名称已存在，请勿重复创建")

    def _validate_status(self, status: str):
        if status not in VALID_JOB_STATUSES:
            raise ValueError("岗位状态必须为 active 或 inactive")

    def _clean_title(self, value: str) -> str:
        title = self._clean(value)
        if not title:
            raise ValueError("岗位名称不能为空")
        return title

    def _clean(self, value: Optional[str]) -> str:
        return value.strip() if isinstance(value, str) else ""


job_service = JobService()
