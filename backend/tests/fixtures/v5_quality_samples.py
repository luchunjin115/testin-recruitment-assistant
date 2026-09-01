"""Fictional five-section JDs used by current v5 plan contract tests."""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Part 1 -- 10 fictional five-section JDs with human labels
# ---------------------------------------------------------------------------

V5_PLAN_JDS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # JD-00  Java backend -- extensive requirements (10-12+)
    # ------------------------------------------------------------------
    {
        "index": 0,
        "title": "Java 高级后端工程师",
        "department": "平台技术部",
        "jd": {
            "job_background": (
                "公司自研电商交易平台日均订单量超百万，核心交易链路正在从单体"
                "迁移到微服务架构，急需有高并发分布式经验的后端工程师。"
            ),
            "job_responsibilities": (
                "负责交易核心服务的设计、开发和性能优化；"
                "参与分布式事务方案选型与落地；"
                "编写技术方案和代码评审；"
                "配合 SRE 完成服务容量评估和故障演练；"
                "指导初中级工程师的技术成长。"
            ),
            "candidate_requirements": (
                "本科及以上学历，计算机相关专业；"
                "至少 5 年 Java 后端开发经验；"
                "熟练掌握 Spring Boot、Spring Cloud 或 Dubbo 微服务框架；"
                "深入理解 MySQL 索引优化和分库分表方案；"
                "熟悉 Redis 缓存设计和常见一致性问题；"
                "具备 Kafka 或 RocketMQ 消息队列实战经验；"
                "有大规模分布式系统设计和故障排查经验；"
                "熟悉 Docker 和 Kubernetes 容器化部署；"
                "良好的技术文档撰写和跨团队沟通能力。"
            ),
            "preferred_qualifications": (
                "有电商或金融交易系统经验优先；"
                "熟悉 TiDB 或其他分布式数据库者加分；"
                "有开源项目贡献经历优先。"
            ),
            "public_notes": (
                "工作地点：杭州滨江；六险一金；弹性工作时间；"
                "团队氛围开放，定期技术分享。"
            ),
        },
        "labels": {
            "key_required_items": [
                "至少 5 年 Java 后端开发经验",
                "Spring Boot / Spring Cloud / Dubbo 微服务框架",
                "MySQL 索引优化和分库分表",
                "Redis 缓存设计",
                "Kafka / RocketMQ 消息队列经验",
                "分布式系统设计和故障排查",
                "Docker 和 Kubernetes",
                "技术文档和跨团队沟通",
                "本科及以上计算机相关专业",
            ],
            "non_evaluation_content": [
                "工作地点：杭州滨江",
                "六险一金",
                "弹性工作时间",
                "团队氛围开放，定期技术分享",
            ],
            "forbidden_additions": [
                "英语能力",
                "前端开发经验",
                "AI / 机器学习经验",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-01  React frontend -- moderate
    # ------------------------------------------------------------------
    {
        "index": 1,
        "title": "前端开发工程师",
        "department": "用户产品部",
        "jd": {
            "job_background": (
                "公司 B 端 SaaS 产品正在进行新一代 UI 升级，"
                "需要熟悉现代前端技术栈的工程师加入。"
            ),
            "job_responsibilities": (
                "负责 B 端工作台核心模块的前端开发；"
                "参与组件库建设和设计系统落地；"
                "优化首屏加载和交互性能；"
                "与产品、设计和后端紧密协作。"
            ),
            "candidate_requirements": (
                "至少 3 年前端开发经验；"
                "精通 React 和 TypeScript；"
                "熟悉 Webpack 或 Vite 构建工具链；"
                "了解 RESTful API 和前后端联调流程；"
                "具备良好的 UI 还原和响应式布局能力。"
            ),
            "preferred_qualifications": (
                "有 Ant Design 或自研组件库经验优先；"
                "了解 Node.js 和 SSR 者加分。"
            ),
            "public_notes": (
                "投递请附带个人作品集或 GitHub 链接。"
            ),
        },
        "labels": {
            "key_required_items": [
                "至少 3 年前端开发经验",
                "React 和 TypeScript",
                "Webpack 或 Vite 构建工具链",
                "RESTful API 和前后端联调",
                "UI 还原和响应式布局",
            ],
            "non_evaluation_content": [
                "投递请附带个人作品集或 GitHub 链接",
            ],
            "forbidden_additions": [
                "后端框架经验",
                "数据库管理",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-02  Data engineer -- moderate
    # ------------------------------------------------------------------
    {
        "index": 2,
        "title": "数据工程师",
        "department": "数据平台部",
        "jd": {
            "job_background": (
                "公司数据中台需要从离线批处理向实时流处理演进，"
                "日志和埋点数据量达 TB 级别。"
            ),
            "job_responsibilities": (
                "设计和维护数据采集、清洗和存储管线；"
                "搭建实时数据流处理链路；"
                "开发和优化 ETL 任务；"
                "保障数据质量和 SLA。"
            ),
            "candidate_requirements": (
                "本科及以上学历；"
                "至少 2 年数据工程或大数据开发经验；"
                "熟练使用 Python 或 Scala 进行数据开发；"
                "熟悉 Spark、Flink 中至少一种大数据计算框架；"
                "掌握 SQL 和常见 OLAP 引擎；"
                "了解数据仓库分层建模方法。"
            ),
            "preferred_qualifications": (
                "有 Kafka + Flink 实时链路实践经验优先；"
                "熟悉 ClickHouse 或 Doris 者加分。"
            ),
            "public_notes": (
                "我们提供丰富的内部培训和技术大会参与机会。"
            ),
        },
        "labels": {
            "key_required_items": [
                "至少 2 年数据工程或大数据开发经验",
                "Python 或 Scala 数据开发",
                "Spark 或 Flink 大数据计算框架",
                "SQL 和 OLAP 引擎",
                "数据仓库分层建模",
            ],
            "non_evaluation_content": [
                "我们提供丰富的内部培训和技术大会参与机会",
            ],
            "forbidden_additions": [
                "机器学习建模经验",
                "前端可视化开发",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-03  Product manager -- mixed evaluation/non-evaluation in
    #        candidate_requirements
    # ------------------------------------------------------------------
    {
        "index": 3,
        "title": "高级产品经理",
        "department": "产品中心",
        "jd": {
            "job_background": None,
            "job_responsibilities": (
                "负责公司核心 SaaS 产品线的规划和迭代；"
                "深入理解客户业务场景，输出产品需求文档；"
                "跟进研发进度，把控产品质量和上线节奏；"
                "建立数据驱动的产品决策机制。"
            ),
            "candidate_requirements": (
                "至少 5 年互联网产品经验，其中 2 年以上 B 端 SaaS 产品经验；"
                "具备从 0 到 1 的产品设计能力；"
                "能够独立完成竞品分析、用户调研和需求拆解；"
                "我们崇尚扁平化管理，鼓励主动思考和创新；"
                "熟练使用 Axure、Figma 等原型工具；"
                "欢迎有创业经历或跨行业经验的人才加入。"
            ),
            "preferred_qualifications": (
                "有 HR SaaS 或企业服务领域产品经验优先。"
            ),
            "public_notes": (
                "薪资面议；年度旅行；节日礼品。"
            ),
        },
        "labels": {
            "key_required_items": [
                "至少 5 年互联网产品经验且 2 年以上 B 端 SaaS",
                "从 0 到 1 产品设计能力",
                "竞品分析、用户调研和需求拆解",
                "Axure / Figma 等原型工具",
            ],
            "non_evaluation_content": [
                "我们崇尚扁平化管理，鼓励主动思考和创新",
                "欢迎有创业经历或跨行业经验的人才加入",
                "薪资面议",
                "年度旅行",
                "节日礼品",
            ],
            "forbidden_additions": [
                "编程能力",
                "数据建模能力",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-04  HRBP -- minimal requirements (< 5 criteria)
    # ------------------------------------------------------------------
    {
        "index": 4,
        "title": "HRBP",
        "department": "人力资源部",
        "jd": {
            "job_background": (
                "公司技术团队快速扩张，需要一位 HRBP 深入业务一线"
                "提供组织和人才支持。"
            ),
            "job_responsibilities": (
                "对接技术部门负责人，理解业务目标并提供人力资源解决方案；"
                "协助完成招聘、绩效和人才盘点工作；"
                "推动企业文化建设和员工关怀活动。"
            ),
            "candidate_requirements": (
                "至少 3 年 HRBP 或人力资源综合工作经验；"
                "具备良好的业务理解和沟通协调能力；"
                "熟悉劳动法和员工关系处理。"
            ),
            "preferred_qualifications": None,
            "public_notes": (
                "公司地址在北京海淀中关村；"
                "五险一金、补充医疗保险、免费午餐。"
            ),
        },
        "labels": {
            "key_required_items": [
                "至少 3 年 HRBP 或人力资源综合工作经验",
                "业务理解和沟通协调能力",
                "劳动法和员工关系处理",
            ],
            "non_evaluation_content": [
                "公司地址在北京海淀中关村",
                "五险一金、补充医疗保险、免费午餐",
            ],
            "forbidden_additions": [
                "薪酬设计经验",
                "英语要求",
                "学历要求",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-05  Finance analyst -- minimal requirements (< 5 criteria)
    # ------------------------------------------------------------------
    {
        "index": 5,
        "title": "财务分析师",
        "department": "财务部",
        "jd": {
            "job_background": None,
            "job_responsibilities": (
                "编制月度和年度财务分析报告；"
                "支持业务部门预算编制和费用管控；"
                "配合外部审计和税务申报。"
            ),
            "candidate_requirements": (
                "财务、会计或相关专业本科及以上学历；"
                "至少 2 年企业财务分析经验；"
                "熟练使用 Excel 进行数据分析和建模。"
            ),
            "preferred_qualifications": (
                "持有 CPA 或 CMA 证书者优先。"
            ),
            "public_notes": (
                "该岗位将有机会参与公司 IPO 准备工作。"
            ),
        },
        "labels": {
            "key_required_items": [
                "财务/会计或相关专业本科及以上学历",
                "至少 2 年企业财务分析经验",
                "熟练使用 Excel 数据分析和建模",
            ],
            "non_evaluation_content": [
                "该岗位将有机会参与公司 IPO 准备工作",
            ],
            "forbidden_additions": [
                "编程能力",
                "金融从业资格",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-06  Marketing manager -- moderate
    # ------------------------------------------------------------------
    {
        "index": 6,
        "title": "市场推广经理",
        "department": "市场部",
        "jd": {
            "job_background": (
                "公司消费品牌正在从线下渠道向全域营销转型，"
                "需要有数字化投放和品牌建设经验的市场推广负责人。"
            ),
            "job_responsibilities": (
                "制定年度市场推广策略和预算方案；"
                "统筹线上线下整合营销活动；"
                "管理媒体投放和 KOL 合作；"
                "追踪 ROI 并持续优化投放效率；"
                "带领 3-5 人的市场团队。"
            ),
            "candidate_requirements": (
                "至少 5 年市场推广或品牌管理经验；"
                "必须有消费品行业从业背景；"
                "具备全域营销策划和执行能力，包括社交媒体、"
                "搜索引擎、信息流和线下活动；"
                "有年度千万级以上投放预算管理经验；"
                "具备团队管理能力；"
                "数据分析驱动，能从投放数据中提炼洞察。"
            ),
            "preferred_qualifications": (
                "有快消或美妆行业经验者优先；"
                "熟悉短视频平台运营和直播电商优先。"
            ),
            "public_notes": (
                "总部在上海静安；年度团建；员工内购折扣。"
            ),
        },
        "labels": {
            "key_required_items": [
                "至少 5 年市场推广或品牌管理经验",
                "消费品行业从业背景",
                "全域营销策划和执行",
                "千万级以上投放预算管理",
                "团队管理能力",
                "数据分析驱动投放优化",
            ],
            "non_evaluation_content": [
                "总部在上海静安",
                "年度团建",
                "员工内购折扣",
            ],
            "forbidden_additions": [
                "英语或海外市场经验",
                "技术开发能力",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-07  Operations manager -- moderate
    # ------------------------------------------------------------------
    {
        "index": 7,
        "title": "运营经理",
        "department": "运营部",
        "jd": {
            "job_background": (
                "公司在线教育平台用户突破五百万，需要运营经理"
                "负责用户增长和课程转化链路优化。"
            ),
            "job_responsibilities": (
                "制定用户增长策略，统筹拉新、留存和转化；"
                "策划和执行社群运营和裂变活动；"
                "搭建运营数据看板，产出周报和月报；"
                "协调产品和客服团队优化用户体验。"
            ),
            "candidate_requirements": (
                "至少 3 年互联网运营经验；"
                "有用户增长或转化漏斗优化实战案例；"
                "熟练使用数据分析工具，例如 Google Analytics 或神策；"
                "优秀的文案撰写和活动策划能力；"
                "有教育或知识付费行业经验者需具备对课程内容质量的判断力。"
            ),
            "preferred_qualifications": (
                "有从 0 到 50 万用户的增长操盘经验优先；"
                "懂得短视频引流或私域运营者加分。"
            ),
            "public_notes": (
                "远程办公友好；每月一次全员线下日；公司提供学习津贴。"
            ),
        },
        "labels": {
            "key_required_items": [
                "至少 3 年互联网运营经验",
                "用户增长或转化漏斗优化实战案例",
                "数据分析工具使用",
                "文案撰写和活动策划",
            ],
            "non_evaluation_content": [
                "远程办公友好",
                "每月一次全员线下日",
                "公司提供学习津贴",
            ],
            "forbidden_additions": [
                "编程开发能力",
                "视频剪辑能力",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-08  UX/UI Designer -- preferred contains "required"-strength
    #        language (priority signal conflict)
    # ------------------------------------------------------------------
    {
        "index": 8,
        "title": "UX/UI 设计师",
        "department": "设计中心",
        "jd": {
            "job_background": (
                "公司医疗健康 App 即将进行全面改版，需要一位"
                "兼具用户研究和视觉设计能力的设计师。"
            ),
            "job_responsibilities": (
                "负责移动端产品的交互设计和视觉设计；"
                "组织和参与用户可用性测试；"
                "输出设计规范并维护设计组件库；"
                "与产品和开发团队协同推动设计落地。"
            ),
            "candidate_requirements": (
                "至少 3 年移动端 UX/UI 设计经验；"
                "精通 Figma，熟悉 Sketch；"
                "具备用户研究和数据驱动设计的能力；"
                "有完整的移动端项目作品集。"
            ),
            "preferred_qualifications": (
                "必须有医疗或健康行业设计经验；"
                "需要掌握 Framer 或 Principle 等高保真原型工具；"
                "有 Design System 从零搭建经历优先。"
            ),
            "public_notes": (
                "请在投递时附上作品集链接；不接受纯平面设计背景。"
            ),
        },
        "labels": {
            "key_required_items": [
                "至少 3 年移动端 UX/UI 设计经验",
                "精通 Figma",
                "用户研究和数据驱动设计",
                "完整移动端项目作品集",
                "医疗或健康行业设计经验（加分项中以必须表述）",
                "Framer 或 Principle 高保真原型工具（加分项中以需要表述）",
            ],
            "non_evaluation_content": [
                "请在投递时附上作品集链接",
                "不接受纯平面设计背景",
            ],
            "forbidden_additions": [
                "编程或前端开发能力",
                "三维建模能力",
            ],
        },
    },

    # ------------------------------------------------------------------
    # JD-09  Legal counsel -- extensive requirements (10-12+)
    # ------------------------------------------------------------------
    {
        "index": 9,
        "title": "高级法务",
        "department": "法务合规部",
        "jd": {
            "job_background": (
                "公司业务覆盖跨境电商和数字支付，面临复杂的国内外"
                "合规要求，法务团队需要扩充核心力量。"
            ),
            "job_responsibilities": (
                "起草、审核和谈判各类商业合同；"
                "提供公司治理和股权架构的法律意见；"
                "跟踪国内外数据合规和支付牌照政策变化；"
                "处理知识产权注册和维权事务；"
                "管理外部律师事务所并控制法律费用；"
                "协助处理争议解决和诉讼事务。"
            ),
            "candidate_requirements": (
                "法学本科及以上学历，持有法律职业资格证书；"
                "至少 5 年企业法务或律师事务所执业经验；"
                "精通合同法、公司法和知识产权法；"
                "熟悉跨境电商和互联网金融相关法规；"
                "具备数据保护和隐私合规经验，熟悉 GDPR 和《个人信息保护法》；"
                "有跨境交易和国际仲裁经验；"
                "英文读写流利，能独立审阅英文合同；"
                "优秀的风险识别和商业判断力；"
                "良好的跨部门沟通和项目管理能力。"
            ),
            "preferred_qualifications": (
                "有支付牌照或金融合规经验者优先；"
                "持有 LLM 学位或海外律所执业经验优先；"
                "熟悉香港或新加坡公司法者加分。"
            ),
            "public_notes": (
                "深圳南山办公；股票期权激励；商业医疗保险；"
                "法律研究资源和外部培训预算。"
            ),
        },
        "labels": {
            "key_required_items": [
                "法学本科及以上学历",
                "法律职业资格证书",
                "至少 5 年企业法务或律所执业经验",
                "合同法、公司法和知识产权法",
                "跨境电商和互联网金融法规",
                "数据保护和隐私合规（GDPR、个人信息保护法）",
                "跨境交易和国际仲裁经验",
                "英文读写流利，能审阅英文合同",
                "风险识别和商业判断力",
                "跨部门沟通和项目管理",
            ],
            "non_evaluation_content": [
                "深圳南山办公",
                "股票期权激励",
                "商业医疗保险",
                "法律研究资源和外部培训预算",
            ],
            "forbidden_additions": [
                "会计或审计经验",
                "技术开发能力",
            ],
        },
    },
]
