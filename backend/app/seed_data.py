import json
from datetime import datetime, timedelta, date

from sqlalchemy.orm import Session

from .models.activity_log import ActivityLog
from .models.candidate import Candidate
from .models.stage_change_log import StageChangeLog


SEED_CANDIDATES = [
    {
        "name": "张明远",
        "phone": "13812345001",
        "email": "zhangmingyuan@example.com",
        "school": "武汉大学",
        "degree": "硕士",
        "major": "软件工程",
        "target_role": "高级测试工程师",
        "experience_years": 4,
        "experience_desc": "4年自动化测试经验，主导过多个大型项目的测试框架搭建",
        "skills": ["Python", "Selenium", "Appium", "Jenkins", "Docker"],
        "self_intro": "热爱测试技术，对软件质量有极致追求",
        "source_channel": "Boss直聘",
        "stage": "面试中",
        "ai_summary": "候选人张明远，武汉大学硕士软件工程专业，拥有4年高级测试工程师相关经验。在Python、Selenium、Appium方面有突出能力，综合素质较好，建议进入下一轮筛选。",
        "ai_tags": ["985高校", "硕士学历", "3年+经验", "自动化测试", "高匹配度"],
        "days_ago": 1,
    },
    {
        "name": "李思颖",
        "phone": "13812345002",
        "email": "lisyy@example.com",
        "school": "北京大学",
        "degree": "本科",
        "major": "计算机科学与技术",
        "target_role": "前端开发工程师",
        "experience_years": 2,
        "experience_desc": "2年前端开发经验，熟练使用React和Vue",
        "skills": ["React", "Vue", "TypeScript", "Node.js", "CSS"],
        "self_intro": "全栈潜力选手，前端专精",
        "source_channel": "拉勾",
        "stage": "复试",
        "ai_summary": "李思颖毕业于北京大学，本科计算机科学与技术方向。拥有2年前端开发经验，擅长React、Vue、TypeScript，与前端开发工程师匹配度较高。",
        "ai_tags": ["985高校", "有经验", "前端开发", "全栈能力"],
        "days_ago": 2,
    },
    {
        "name": "王浩然",
        "phone": "13812345003",
        "email": "wanghr@example.com",
        "school": "华中科技大学",
        "degree": "硕士",
        "major": "人工智能",
        "target_role": "AI算法工程师",
        "experience_years": 1,
        "experience_desc": "研究生期间专注NLP方向，有实习经验",
        "skills": ["Python", "PyTorch", "机器学习", "自然语言处理", "深度学习"],
        "self_intro": "对AI技术充满热情，希望在工业界实践所学",
        "source_channel": "内推",
        "stage": "offer",
        "ai_summary": "王浩然，华中科技大学硕士人工智能专业。拥有1年AI算法工程师相关经验，核心技能包括Python、PyTorch、机器学习。整体表现出色，建议优先安排面试。",
        "ai_tags": ["985高校", "硕士学历", "有经验", "AI方向", "潜力候选人"],
        "days_ago": 5,
    },
    {
        "name": "陈静怡",
        "phone": "13812345004",
        "email": "chenjy@example.com",
        "school": "浙江大学",
        "degree": "本科",
        "major": "软件工程",
        "target_role": "测试工程师",
        "experience_years": 0,
        "experience_desc": "应届毕业生，有测试相关课程项目经验",
        "skills": ["Python", "Java", "Postman", "MySQL", "Git"],
        "self_intro": "应届生，学习能力强，对测试行业有浓厚兴趣",
        "source_channel": "表单录入",
        "stage": "待筛选",
        "ai_summary": "候选人陈静怡，浙江大学本科软件工程专业，应届毕业生/实习生。在Python、Java、Postman方面有突出能力，综合素质较好，建议进入下一轮筛选。",
        "ai_tags": ["985高校", "应届/实习", "测试方向"],
        "days_ago": 0,
    },
    {
        "name": "刘伟",
        "phone": "13812345005",
        "email": "liuwei@example.com",
        "school": "中山大学",
        "degree": "本科",
        "major": "数据科学",
        "target_role": "数据分析师",
        "experience_years": 3,
        "experience_desc": "3年数据分析经验，擅长用户行为分析和A/B测试",
        "skills": ["Python", "SQL", "Tableau", "数据分析", "机器学习"],
        "self_intro": "数据驱动决策的坚定信仰者",
        "source_channel": "猎聘",
        "stage": "待约面",
        "ai_summary": "刘伟毕业于中山大学，本科数据科学方向。拥有3年数据分析经验，擅长Python、SQL、Tableau，与数据分析师匹配度较高。",
        "ai_tags": ["985高校", "3年+经验", "数据分析"],
        "days_ago": 4,
    },
    {
        "name": "赵雪琳",
        "phone": "13812345006",
        "email": "zhaoxl@example.com",
        "school": "南京大学",
        "degree": "硕士",
        "major": "计算机科学",
        "target_role": "后端开发工程师",
        "experience_years": 5,
        "experience_desc": "5年Java后端开发经验，主导过微服务架构设计",
        "skills": ["Java", "Spring", "MySQL", "Redis", "Docker", "Kubernetes"],
        "self_intro": "技术深度与广度兼备的资深后端工程师",
        "source_channel": "Boss直聘",
        "stage": "已约面",
        "ai_summary": "赵雪琳，南京大学硕士计算机科学专业。拥有5年后端开发经验，核心技能包括Java、Spring、MySQL。整体表现出色，建议优先安排面试。",
        "ai_tags": ["985高校", "硕士学历", "资深经验", "Java", "高匹配度"],
        "days_ago": 1,
    },
    {
        "name": "孙博文",
        "phone": "13812345007",
        "email": "sunbw@example.com",
        "school": "电子科技大学",
        "degree": "本科",
        "major": "信息安全",
        "target_role": "安全测试工程师",
        "experience_years": 2,
        "experience_desc": "2年安全测试经验，熟悉渗透测试和代码审计",
        "skills": ["Python", "安全测试", "Burp Suite", "Linux", "SQL"],
        "self_intro": "专注信息安全领域，致力于构建安全的软件系统",
        "source_channel": "简历上传",
        "stage": "新投递",
        "ai_summary": "候选人孙博文，电子科技大学本科信息安全专业，拥有2年安全测试工程师相关经验。在Python、安全测试、Burp Suite方面有突出能力。",
        "ai_tags": ["985高校", "有经验", "安全测试方向"],
        "days_ago": 0,
    },
    {
        "name": "周明珠",
        "phone": "13812345008",
        "email": "zhoumz@example.com",
        "school": "复旦大学",
        "degree": "硕士",
        "major": "软件工程",
        "target_role": "产品经理",
        "experience_years": 6,
        "experience_desc": "6年互联网产品经验，主导过多款千万级用户产品",
        "skills": ["产品设计", "数据分析", "Axure", "用户研究", "项目管理"],
        "self_intro": "用户需求的洞察者，产品价值的创造者",
        "source_channel": "内推",
        "stage": "入职",
        "ai_summary": "周明珠，复旦大学硕士软件工程专业。拥有6年产品经理经验，擅长产品设计、数据分析、用户研究，与产品经理匹配度极高。",
        "ai_tags": ["985高校", "硕士学历", "资深经验", "产品方向", "高匹配度"],
        "days_ago": 10,
    },
    {
        "name": "吴天宇",
        "phone": "13812345009",
        "email": "wuty@example.com",
        "school": "哈尔滨工业大学",
        "degree": "本科",
        "major": "自动化",
        "target_role": "测试开发工程师",
        "experience_years": 3,
        "experience_desc": "3年测试开发经验，负责测试平台建设",
        "skills": ["Python", "Go", "Docker", "CI/CD", "Selenium"],
        "self_intro": "测试开发一体化实践者",
        "source_channel": "拉勾",
        "stage": "淘汰",
        "ai_summary": "吴天宇毕业于哈尔滨工业大学，本科自动化方向。拥有3年测试开发经验，擅长Python、Go、Docker。",
        "ai_tags": ["985高校", "3年+经验", "自动化测试", "DevOps"],
        "days_ago": 7,
    },
    {
        "name": "郑雅文",
        "phone": "13812345010",
        "email": "zhengyawen@example.com",
        "school": "同济大学",
        "degree": "本科",
        "major": "计算机科学与技术",
        "target_role": "UI设计师",
        "experience_years": 4,
        "experience_desc": "4年UI/UX设计经验，擅长B端产品设计",
        "skills": ["Figma", "Sketch", "设计", "用户研究", "HTML/CSS"],
        "self_intro": "设计与技术的交叉点，让产品更美好",
        "source_channel": "Boss直聘",
        "stage": "新投递",
        "ai_summary": "郑雅文，同济大学本科计算机科学与技术专业。拥有4年UI设计经验，擅长Figma、Sketch、用户研究，与UI设计师匹配度较高。",
        "ai_tags": ["985高校", "3年+经验", "设计方向"],
        "days_ago": 5,
    },
    {
        "name": "黄建华",
        "phone": "13812345011",
        "email": "huangjh@example.com",
        "school": "上海交通大学",
        "degree": "博士",
        "major": "计算机科学",
        "target_role": "算法研究员",
        "experience_years": 2,
        "experience_desc": "博士期间发表顶会论文3篇，研究方向为计算机视觉",
        "skills": ["Python", "PyTorch", "深度学习", "计算机视觉", "C++"],
        "self_intro": "追求技术突破，希望将学术成果转化为产品价值",
        "source_channel": "内推",
        "stage": "新投递",
        "ai_summary": "黄建华，上海交通大学博士计算机科学专业。拥有2年算法研究经验，核心技能包括Python、PyTorch、深度学习。博士学历，整体表现出色。",
        "ai_tags": ["985高校", "博士学历", "有经验", "AI方向", "高匹配度"],
        "days_ago": 0,
    },
    {
        "name": "林小梅",
        "phone": "13812345012",
        "email": "linxm@example.com",
        "school": "厦门大学",
        "degree": "本科",
        "major": "电子信息",
        "target_role": "嵌入式测试工程师",
        "experience_years": 1,
        "experience_desc": "1年嵌入式系统测试经验",
        "skills": ["C", "Python", "嵌入式", "Linux", "测试"],
        "self_intro": "踏实肯干，愿意在嵌入式测试领域深耕",
        "source_channel": "简历上传",
        "stage": "待筛选",
        "ai_summary": "林小梅，厦门大学本科电子信息专业。拥有1年嵌入式测试经验，擅长C、Python、Linux。",
        "ai_tags": ["985高校", "有经验", "测试方向"],
        "days_ago": 6,
    },
    {
        "name": "马志强",
        "phone": "13812345013",
        "email": "mazq@example.com",
        "school": "西安电子科技大学",
        "degree": "硕士",
        "major": "通信工程",
        "target_role": "性能测试工程师",
        "experience_years": 3,
        "experience_desc": "3年性能测试经验，熟练使用JMeter和LoadRunner",
        "skills": ["JMeter", "LoadRunner", "Python", "Linux", "性能测试"],
        "self_intro": "性能测试专家，致力于系统稳定性保障",
        "source_channel": "猎聘",
        "stage": "面试中",
        "ai_summary": "马志强，西安电子科技大学硕士通信工程专业。拥有3年性能测试经验，擅长JMeter、LoadRunner、Python，与性能测试工程师匹配度较高。",
        "ai_tags": ["211高校", "硕士学历", "3年+经验", "性能测试"],
        "days_ago": 2,
    },
    {
        "name": "张明远",
        "phone": "13899999001",
        "email": "zhangmy_dup@example.com",
        "school": "武汉大学",
        "degree": "硕士",
        "major": "软件工程",
        "target_role": "高级测试工程师",
        "experience_years": 4,
        "experience_desc": "同一个人重复投递",
        "skills": ["Python", "Selenium"],
        "self_intro": "",
        "source_channel": "表单录入",
        "stage": "新投递",
        "ai_summary": "",
        "ai_tags": [],
        "days_ago": 0,
        "is_duplicate": True,
        "duplicate_of_index": 0,
    },
]


ADDITIONAL_DEMO_CANDIDATES = [
    {
        "name": "顾安琪",
        "phone": "13822345021",
        "email": "gu.anqi@example.com",
        "school": "南京邮电大学",
        "degree": "本科",
        "major": "软件工程",
        "target_role": "测试工程师",
        "experience_years": 1,
        "experience_desc": (
            "在线投递简历：曾在校企合作项目中负责电商后台订单、库存、退款模块测试，"
            "独立编写 180+ 条功能与异常场景用例；使用 Postman 完成核心接口冒烟测试，"
            "配合研发定位过订单状态流转错误、优惠券重复核销等问题。熟悉缺陷提交流程，"
            "能够用日志、接口响应和复现步骤说明问题。"
        ),
        "skills": ["测试用例", "接口测试", "Postman", "MySQL", "缺陷跟踪", "Python"],
        "self_intro": (
            "我关注业务流程和用户实际使用路径，习惯先画流程图再拆测试点。希望从基础测试做起，"
            "逐步深入接口自动化和质量效率方向。"
        ),
        "source_channel": "在线投递",
        "stage": "新投递",
        "ai_summary": "顾安琪具备测试用例设计、接口测试和缺陷跟踪实践，能描述真实业务问题定位过程，适合测试工程师初筛。",
        "ai_tags": ["在线投递", "测试方向", "接口测试", "应届/初级"],
        "hr_notes": "在线投递信息较完整，建议优先核实接口测试深度。",
        "days_ago": 0,
    },
    {
        "name": "程子航",
        "phone": "13822345022",
        "email": "chengzh@example.com",
        "school": "华南理工大学",
        "degree": "本科",
        "major": "计算机科学与技术",
        "target_role": "自动化测试工程师",
        "experience_years": 2,
        "experience_desc": (
            "在线投递简历：2 年测试开发经验，主要负责 SaaS 管理后台自动化测试。"
            "使用 Python + Pytest 封装接口测试框架，支持环境配置、Token 管理、测试数据初始化和 Allure 报告；"
            "维护 Selenium UI 自动化脚本 120+ 条，接入 Jenkins 夜间构建，帮助回归测试从 2 天缩短到 4 小时。"
        ),
        "skills": ["Python", "Pytest", "Selenium", "Jenkins", "接口测试", "自动化测试"],
        "self_intro": (
            "我更偏测试开发方向，喜欢把重复测试动作工具化。过去做过框架封装和流水线接入，"
            "希望继续在质量平台、自动化覆盖率和稳定性治理上深入。"
        ),
        "source_channel": "在线投递",
        "stage": "待筛选",
        "ai_summary": "程子航有 Pytest、Selenium、Jenkins 经验，能量化自动化测试提效结果，与自动化测试工程师岗位匹配度较高。",
        "ai_tags": ["在线投递", "自动化测试", "Python", "有经验"],
        "hr_notes": "简历提到框架封装和 CI 接入，可在技术面追问稳定性治理细节。",
        "days_ago": 1,
    },
    {
        "name": "梁若溪",
        "phone": "13822345023",
        "email": "liangrx@example.com",
        "school": "北京邮电大学",
        "degree": "硕士",
        "major": "人工智能",
        "target_role": "AI应用实习生",
        "experience_years": 0,
        "experience_desc": (
            "在线投递简历：研究生阶段参与智能客服知识库问答项目，负责 FAQ 数据清洗、Prompt 模板对比、"
            "召回结果人工评估和失败样本归因。熟悉 Python 数据处理，能使用 pandas 清洗多轮对话日志，"
            "了解 RAG、Embedding、Few-shot Prompt 等基础概念。"
        ),
        "skills": ["Python", "数据处理", "Prompt", "大模型", "自然语言处理", "pandas"],
        "self_intro": (
            "我希望参与真实 AI 应用落地，不只停留在模型调用。做项目时比较重视评估表和失败案例沉淀，"
            "也愿意做数据清洗、标注和实验记录这些基础工作。"
        ),
        "source_channel": "在线投递",
        "stage": "新投递",
        "ai_summary": "梁若溪有 AI 应用项目实践，熟悉数据清洗、Prompt 对比和评估记录，适合 AI 应用实习生进一步沟通。",
        "ai_tags": ["在线投递", "硕士学历", "AI方向", "Prompt"],
        "hr_notes": "适合考察实验复盘能力和对 RAG 应用边界的理解。",
        "days_ago": 0,
    },
    {
        "name": "唐启明",
        "phone": "13822345024",
        "email": "tangqm@example.com",
        "school": "湖南大学",
        "degree": "本科",
        "major": "统计学",
        "target_role": "数据分析师",
        "experience_years": 2,
        "experience_desc": (
            "在线投递简历：在教育科技公司负责课程转化漏斗分析、用户分层和投放渠道效果复盘。"
            "熟练使用 SQL 提取业务数据，使用 Python 做清洗和可视化；曾搭建周度经营看板，"
            "通过分析试听课流失节点提出提醒策略，使试听到付费转化率提升约 8%。"
        ),
        "skills": ["SQL", "Python", "数据分析", "Excel", "Tableau", "A/B测试"],
        "self_intro": (
            "我习惯从业务问题出发做分析，不只交付报表。比较擅长漏斗分析、渠道评估和指标拆解，"
            "希望在更复杂的业务场景中提升分析影响力。"
        ),
        "source_channel": "在线投递",
        "stage": "待约面",
        "ai_summary": "唐启明有 SQL、Python 和业务漏斗分析经验，能说明转化提升结果，与数据分析师岗位较匹配。",
        "ai_tags": ["在线投递", "数据分析", "SQL", "有经验"],
        "hr_notes": "建议面试重点追问指标口径、因果判断和 A/B 实验设计。",
        "days_ago": 2,
    },
    {
        "name": "许嘉宁",
        "phone": "13822345025",
        "email": "xujn@example.com",
        "school": "四川大学",
        "degree": "本科",
        "major": "数字媒体技术",
        "target_role": "前端开发工程师",
        "experience_years": 3,
        "experience_desc": (
            "在线投递简历：3 年前端开发经验，参与 CRM、招聘管理和数据看板类 B 端项目。"
            "主要技术栈为 React、TypeScript、Ant Design 和 Vite，负责复杂表单、权限路由、"
            "可配置表格和 ECharts 图表封装；有性能优化经验，曾将首屏加载时间从 4.2s 优化到 2.1s。"
        ),
        "skills": ["React", "TypeScript", "Ant Design", "Vite", "ECharts", "前端工程化"],
        "self_intro": (
            "我偏 B 端业务前端，熟悉表单、表格、看板和权限场景。希望加入重视工程质量的团队，"
            "继续提升组件抽象、性能优化和产品理解能力。"
        ),
        "source_channel": "在线投递",
        "stage": "已约面",
        "ai_summary": "许嘉宁有 React/TypeScript 和 B 端复杂页面经验，能量化性能优化结果，与前端开发工程师岗位匹配度较高。",
        "ai_tags": ["在线投递", "前端开发", "TypeScript", "B端经验"],
        "hr_notes": "适合追问复杂表单状态管理和组件封装边界。",
        "days_ago": 1,
    },
]


ALL_SEED_CANDIDATES = SEED_CANDIDATES + ADDITIONAL_DEMO_CANDIDATES


def seed_database(db: Session):
    existing = db.query(Candidate).count()
    if existing > 0:
        ensure_demo_candidates(db)
        return

    now = datetime.now()
    candidate_ids = {}
    seed_candidates = ALL_SEED_CANDIDATES

    def clamp_to_now(target: datetime) -> datetime:
        return target if target <= now else now

    for i, data in enumerate(seed_candidates):
        days = data.get("days_ago", 0)
        created = now - timedelta(days=days)
        updated = created + timedelta(hours=2) if days > 0 else created

        candidate = Candidate(
            name=data["name"],
            phone=data["phone"],
            email=data["email"],
            school=data["school"],
            degree=data["degree"],
            major=data["major"],
            target_role=data["target_role"],
            experience_years=data["experience_years"],
            experience_desc=data["experience_desc"],
            skills=json.dumps(data["skills"], ensure_ascii=False),
            self_intro=data["self_intro"],
            source_channel=data["source_channel"],
            stage=data["stage"],
            ai_summary=data.get("ai_summary", ""),
            ai_tags=json.dumps(data.get("ai_tags", []), ensure_ascii=False),
            hr_notes=data.get("hr_notes", ""),
            is_duplicate=data.get("is_duplicate", False),
            created_at=created,
            updated_at=updated,
        )
        db.add(candidate)
        db.flush()
        candidate_ids[i] = candidate.id

    dup_index = next(
        (i for i, data in enumerate(seed_candidates) if data.get("duplicate_of_index") is not None),
        None,
    )
    dup_of = seed_candidates[dup_index].get("duplicate_of_index") if dup_index is not None else None
    if dup_index is not None and dup_of is not None and dup_of in candidate_ids:
        dup_candidate = db.query(Candidate).filter(
            Candidate.id == candidate_ids[dup_index]
        ).first()
        if dup_candidate:
            dup_candidate.duplicate_of_id = candidate_ids[dup_of]

    for i, data in enumerate(seed_candidates):
        cid = candidate_ids[i]
        days = data.get("days_ago", 0)
        created = now - timedelta(days=days)

        log = ActivityLog(
            candidate_id=cid,
            action="created",
            detail=f"候选人{data['name']}通过{data['source_channel']}录入系统",
            created_at=created,
        )
        db.add(log)

        if data["stage"] != "新投递" and not data.get("is_duplicate"):
            stage_time = clamp_to_now(created + timedelta(hours=1))
            stage_log = StageChangeLog(
                candidate_id=cid,
                from_stage="新投递",
                to_stage=data["stage"],
                trigger_reason="种子数据初始化",
                trigger_source="system_auto",
                created_at=stage_time,
            )
            db.add(stage_log)

            log2 = ActivityLog(
                candidate_id=cid,
                action="stage_changed",
                detail=(
                    f"{data['name']}的状态从「新投递」变更为「{data['stage']}」"
                    "（系统自动：种子数据初始化）"
                ),
                created_at=stage_time,
            )
            db.add(log2)

        if data.get("ai_summary"):
            ai_time = clamp_to_now(created + timedelta(minutes=5))
            log3 = ActivityLog(
                candidate_id=cid,
                action="ai_processed",
                detail="AI自动生成摘要和标签",
                created_at=ai_time,
            )
            db.add(log3)

    db.commit()


def ensure_demo_candidates(db: Session):
    now = datetime.now()
    phone_to_candidate = {
        candidate.phone: candidate
        for candidate in db.query(Candidate).filter(Candidate.phone.isnot(None)).all()
    }
    inserted = {}
    changed = False

    def should_enrich(value: str) -> bool:
        return not value or len(value.strip()) < 80

    for i, data in enumerate(ALL_SEED_CANDIDATES):
        existing = phone_to_candidate.get(data["phone"])
        if existing:
            if should_enrich(existing.experience_desc or ""):
                existing.experience_desc = data.get("experience_desc", "")
                changed = True
            if should_enrich(existing.self_intro or ""):
                existing.self_intro = data.get("self_intro", "")
                changed = True
            if not existing.hr_notes and data.get("hr_notes"):
                existing.hr_notes = data.get("hr_notes", "")
                changed = True
            if not existing.ai_summary and data.get("ai_summary"):
                existing.ai_summary = data.get("ai_summary", "")
                changed = True
            if (not existing.ai_tags or existing.ai_tags == "[]") and data.get("ai_tags"):
                existing.ai_tags = json.dumps(data.get("ai_tags", []), ensure_ascii=False)
                changed = True
            continue

        days = data.get("days_ago", 0)
        created = now - timedelta(days=days)
        candidate = Candidate(
            name=data["name"],
            phone=data["phone"],
            email=data["email"],
            school=data["school"],
            degree=data["degree"],
            major=data["major"],
            target_role=data["target_role"],
            experience_years=data["experience_years"],
            experience_desc=data["experience_desc"],
            skills=json.dumps(data["skills"], ensure_ascii=False),
            self_intro=data["self_intro"],
            source_channel=data["source_channel"],
            stage=data["stage"],
            ai_summary=data.get("ai_summary", ""),
            ai_tags=json.dumps(data.get("ai_tags", []), ensure_ascii=False),
            hr_notes=data.get("hr_notes", ""),
            is_duplicate=data.get("is_duplicate", False),
            created_at=created,
            updated_at=created + timedelta(hours=2) if days > 0 else created,
        )
        db.add(candidate)
        db.flush()
        phone_to_candidate[data["phone"]] = candidate
        inserted[i] = candidate
        changed = True

        db.add(ActivityLog(
            candidate_id=candidate.id,
            action="created",
            detail=f"候选人{data['name']}通过{data['source_channel']}录入系统",
            created_at=created,
        ))
        if data.get("ai_summary"):
            db.add(ActivityLog(
                candidate_id=candidate.id,
                action="ai_processed",
                detail="AI自动生成摘要和标签",
                created_at=created + timedelta(minutes=5),
            ))
        if data["stage"] != "新投递" and not data.get("is_duplicate"):
            stage_time = created + timedelta(hours=1)
            db.add(StageChangeLog(
                candidate_id=candidate.id,
                from_stage="新投递",
                to_stage=data["stage"],
                trigger_reason="演示数据补充",
                trigger_source="system_auto",
                created_at=stage_time,
            ))
            db.add(ActivityLog(
                candidate_id=candidate.id,
                action="stage_changed",
                detail=(
                    f"{data['name']}的状态从「新投递」变更为「{data['stage']}」"
                    "（系统自动：演示数据补充）"
                ),
                created_at=stage_time,
            ))

    for i, candidate in inserted.items():
        dup_of = ALL_SEED_CANDIDATES[i].get("duplicate_of_index")
        if dup_of is None:
            continue
        original_phone = ALL_SEED_CANDIDATES[dup_of]["phone"]
        original = phone_to_candidate.get(original_phone)
        if original:
            candidate.duplicate_of_id = original.id
            changed = True

    if changed:
        db.commit()
