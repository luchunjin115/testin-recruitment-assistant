"""Offline test fixtures for v5.0 lightweight evaluation checklist AI screening.

All JDs and resumes are fictional/anonymized and have never been used for
Prompt tuning.  Human-annotated labels were frozen BEFORE any model call.

Layout
------
Part 1 : 10 five-section JDs  (plan acceptance)
Part 2 : 20 JD+Resume pairs   (report acceptance)
Part 3 : stability indices     (indices 0-4, each run 3x)
Part 4 : metadata constants
Part 5 : helper functions
"""

from __future__ import annotations

import hashlib
import json
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


# ---------------------------------------------------------------------------
# Part 2 -- 20 JD+Resume pairs with human labels
# ---------------------------------------------------------------------------
# Distribution: 8 high_match, 6 partial_match, 6 low_match
# Indices 0-4 are also stability samples (Part 3).

V5_REPORT_PAIRS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # Pair-00  Java backend, high_match  (stability)
    # ------------------------------------------------------------------
    {
        "index": 0,
        "jd": V5_PLAN_JDS[0]["jd"],
        "jd_title": "Java 高级后端工程师",
        "jd_department": "平台技术部",
        "resume_text": (
            "教育背景\n"
            "浙大计算机科学与技术 本科 2014-2018\n\n"
            "工作经历\n"
            "杭州某电商公司 高级 Java 工程师 2019.03-至今\n"
            "- 负责交易核心链路微服务化改造，使用 Spring Cloud 和 Dubbo 双注册中心\n"
            "- 主导 MySQL 分库分表方案落地，支撑日均 200 万订单\n"
            "- 设计 Redis 分布式锁和多级缓存体系，缓存命中率达 98%\n"
            "- 搭建 Kafka 异步消费链路处理支付回调和库存扣减\n"
            "- 完成全量服务 Docker 化并迁移至 K8s 集群\n\n"
            "某互联网公司 Java 开发工程师 2018.07-2019.02\n"
            "- 参与内容社区后端开发，使用 Spring Boot + MyBatis\n\n"
            "技能\n"
            "Java, Spring Boot, Spring Cloud, Dubbo, MySQL, Redis, "
            "Kafka, Docker, Kubernetes, Git"
        ),
        "labels": {
            "overall_direction": "high_match",
            "reasonable_score_range": (78, 92),
            "key_gaps": [],
            "key_strengths": [
                "电商交易系统高并发经验",
                "微服务、分库分表、缓存、消息队列全面覆盖",
                "K8s 容器化实践",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "至少 5 年 Java 后端开发经验",
                "Spring Boot / Spring Cloud / Dubbo",
                "MySQL 分库分表",
                "Redis 缓存设计",
                "Kafka 消息队列",
                "Docker 和 Kubernetes",
            ],
            "required_evidence_absent": [
                "技术文档撰写和跨团队沟通（无直接证据）",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-01  React frontend, high_match  (stability)
    # ------------------------------------------------------------------
    {
        "index": 1,
        "jd": V5_PLAN_JDS[1]["jd"],
        "jd_title": "前端开发工程师",
        "jd_department": "用户产品部",
        "resume_text": (
            "教育背景\n"
            "华中某大学 软件工程 本科 2017-2021\n\n"
            "工作经历\n"
            "深圳某 SaaS 公司 前端工程师 2021.07-至今\n"
            "- 独立负责工作台订单管理模块，使用 React 18 + TypeScript\n"
            "- 参与公司内部 UI 组件库建设，基于 Ant Design 二次封装 30+ 组件\n"
            "- 使用 Vite 替换 Webpack，首屏加载时间降低 40%\n"
            "- 对接后端 RESTful API，封装统一请求层和错误处理\n"
            "- 适配桌面和平板两种视口，实现响应式布局\n\n"
            "技能\n"
            "React, TypeScript, Vite, Webpack, Ant Design, CSS-in-JS, Git"
        ),
        "labels": {
            "overall_direction": "high_match",
            "reasonable_score_range": (80, 93),
            "key_gaps": [],
            "key_strengths": [
                "React + TypeScript SaaS 项目实战",
                "Vite 和 Webpack 双工具链经验",
                "组件库建设经验",
                "响应式布局能力",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "至少 3 年前端开发经验",
                "React 和 TypeScript",
                "Webpack 或 Vite",
                "RESTful API 联调",
                "响应式布局",
            ],
            "required_evidence_absent": [],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-02  Data engineer, partial_match  (stability)
    # ------------------------------------------------------------------
    {
        "index": 2,
        "jd": V5_PLAN_JDS[2]["jd"],
        "jd_title": "数据工程师",
        "jd_department": "数据平台部",
        "resume_text": (
            "教育背景\n"
            "某理工大学 统计学 本科 2018-2022\n\n"
            "工作经历\n"
            "北京某数据公司 数据分析师 2022.07-至今\n"
            "- 使用 Python 和 Pandas 进行日常数据清洗和分析\n"
            "- 编写 SQL 查询报表，使用 MySQL 和 Hive\n"
            "- 搭建基于 Airflow 的 ETL 调度任务\n"
            "- 参与数据仓库 DWD/DWS 层表设计\n\n"
            "技能\n"
            "Python, SQL, Pandas, Hive, Airflow, MySQL, Tableau"
        ),
        "labels": {
            "overall_direction": "partial_match",
            "reasonable_score_range": (45, 62),
            "key_gaps": [
                "缺乏 Spark 或 Flink 等大数据计算框架实战",
                "经验年限偏短",
                "无 Scala 经验",
                "无 OLAP 引擎经验",
            ],
            "key_strengths": [
                "Python 数据开发能力",
                "SQL 和数据仓库分层建模",
                "ETL 工作流经验",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "Python 数据开发",
                "SQL",
                "数据仓库分层建模",
            ],
            "required_evidence_absent": [
                "Spark 或 Flink 大数据计算框架",
                "OLAP 引擎经验",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-03  Product manager, low_match  (stability)
    # ------------------------------------------------------------------
    {
        "index": 3,
        "jd": V5_PLAN_JDS[3]["jd"],
        "jd_title": "高级产品经理",
        "jd_department": "产品中心",
        "resume_text": (
            "教育背景\n"
            "某师范大学 市场营销 本科 2016-2020\n\n"
            "工作经历\n"
            "上海某广告公司 客户执行 2020.07-2022.06\n"
            "- 对接品牌客户需求，协调创意和媒介团队\n"
            "- 撰写客户提案和活动执行方案\n\n"
            "某电商平台 运营助理 2022.07-至今\n"
            "- 协助运营经理策划促销活动\n"
            "- 整理用户反馈并提交产品需求单\n"
            "- 使用 Excel 统计活动数据\n\n"
            "技能\n"
            "Excel, PowerPoint, 文案撰写"
        ),
        "labels": {
            "overall_direction": "low_match",
            "reasonable_score_range": (15, 33),
            "key_gaps": [
                "无互联网产品经理经验",
                "无 B 端 SaaS 产品经验",
                "无从 0 到 1 产品设计经验",
                "无原型工具使用经验",
                "无需求拆解和竞品分析证据",
            ],
            "key_strengths": [
                "有用户反馈收集经验（非常初级）",
            ],
            "conflicts": [],
            "required_evidence_present": [],
            "required_evidence_absent": [
                "至少 5 年互联网产品经验",
                "B 端 SaaS 产品经验",
                "从 0 到 1 产品设计",
                "竞品分析、用户调研、需求拆解",
                "Axure / Figma 原型工具",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-04  HRBP, high_match  (stability)
    # ------------------------------------------------------------------
    {
        "index": 4,
        "jd": V5_PLAN_JDS[4]["jd"],
        "jd_title": "HRBP",
        "jd_department": "人力资源部",
        "resume_text": (
            "教育背景\n"
            "某大学 人力资源管理 本科 2015-2019\n\n"
            "工作经历\n"
            "某科技公司 HRBP 2021.06-至今\n"
            "- 对接研发中心约 200 人，负责招聘、绩效和人才盘点\n"
            "- 处理员工关系纠纷 15+ 起，涉及调岗、离职和劳动仲裁前调解\n"
            "- 推动季度文化活动和新员工融入计划\n\n"
            "某制造企业 人事专员 2019.07-2021.05\n"
            "- 负责入离职办理和社保公积金操作\n"
            "- 协助更新员工手册并参与劳动法培训\n\n"
            "证书\n"
            "人力资源管理师（二级）"
        ),
        "labels": {
            "overall_direction": "high_match",
            "reasonable_score_range": (75, 90),
            "key_gaps": [],
            "key_strengths": [
                "HRBP 对接研发团队经验",
                "员工关系和劳动法实践",
                "招聘、绩效、人才盘点全覆盖",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "至少 3 年 HRBP 或人力资源综合经验",
                "业务理解和沟通协调",
                "劳动法和员工关系处理",
            ],
            "required_evidence_absent": [],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-05  Finance analyst, high_match
    # ------------------------------------------------------------------
    {
        "index": 5,
        "jd": V5_PLAN_JDS[5]["jd"],
        "jd_title": "财务分析师",
        "jd_department": "财务部",
        "resume_text": (
            "教育背景\n"
            "中南某大学 会计学 本科 2016-2020\n\n"
            "工作经历\n"
            "某互联网公司 财务分析师 2020.07-至今\n"
            "- 编制月度和季度管理报告，覆盖收入、成本和利润分析\n"
            "- 协助业务部门完成年度预算编制，管理预算执行偏差\n"
            "- 使用 Excel 建立动态财务模型和敏感性分析工具\n"
            "- 配合年度审计出具审计底稿\n"
            "- 参与增值税和企业所得税申报\n\n"
            "证书\n"
            "初级会计师"
        ),
        "labels": {
            "overall_direction": "high_match",
            "reasonable_score_range": (76, 90),
            "key_gaps": [],
            "key_strengths": [
                "财务分析报告和预算管理经验",
                "Excel 财务建模能力",
                "审计和税务配合经验",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "财务/会计相关专业本科",
                "至少 2 年企业财务分析经验",
                "Excel 数据分析和建模",
            ],
            "required_evidence_absent": [],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-06  Marketing manager, partial_match
    # ------------------------------------------------------------------
    {
        "index": 6,
        "jd": V5_PLAN_JDS[6]["jd"],
        "jd_title": "市场推广经理",
        "jd_department": "市场部",
        "resume_text": (
            "教育背景\n"
            "某大学 广告学 本科 2013-2017\n\n"
            "工作经历\n"
            "某日化公司 品牌主管 2020.03-至今\n"
            "- 负责旗下洗护品牌的社交媒体内容策划和投放\n"
            "- 管理年度投放预算约 500 万元\n"
            "- 策划线上直播带货活动，单场 GMV 最高 120 万\n"
            "- 与 KOL 和 MCN 机构建立合作关系\n\n"
            "某 4A 广告公司 文案策划 2017.07-2020.02\n"
            "- 为快消和汽车客户撰写广告文案和社媒内容\n\n"
            "技能\n"
            "品牌策划, 社交媒体运营, KOL 合作, 数据分析"
        ),
        "labels": {
            "overall_direction": "partial_match",
            "reasonable_score_range": (48, 65),
            "key_gaps": [
                "投放预算管理规模仅 500 万，远低于千万级要求",
                "无明确团队管理经验",
                "搜索引擎和信息流投放经验不明",
                "线下活动经验证据不足",
            ],
            "key_strengths": [
                "消费品行业品牌经验",
                "社交媒体和 KOL 运营能力",
                "直播电商实操经验",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "消费品行业从业背景",
                "社交媒体营销策划和执行",
            ],
            "required_evidence_absent": [
                "千万级以上投放预算管理经验",
                "团队管理能力",
                "搜索引擎和信息流投放",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-07  Operations manager, partial_match
    # ------------------------------------------------------------------
    {
        "index": 7,
        "jd": V5_PLAN_JDS[7]["jd"],
        "jd_title": "运营经理",
        "jd_department": "运营部",
        "resume_text": (
            "教育背景\n"
            "某大学 电子商务 本科 2017-2021\n\n"
            "工作经历\n"
            "某内容平台 社区运营 2021.07-至今\n"
            "- 负责社区话题策划和 UGC 引导，日均新增帖子从 200 提升到 800\n"
            "- 策划裂变活动，一个月拉新 3 万用户\n"
            "- 使用神策分析用户行为漏斗，优化注册到发帖的转化率\n"
            "- 撰写活动文案和社群推送内容\n\n"
            "技能\n"
            "社区运营, 用户增长, 活动策划, 神策数据分析, 文案"
        ),
        "labels": {
            "overall_direction": "partial_match",
            "reasonable_score_range": (50, 66),
            "key_gaps": [
                "仅约 3 年经验，偏经验下限",
                "无教育或知识付费行业经验",
                "用户增长规模和转化漏斗优化案例有但深度有限",
            ],
            "key_strengths": [
                "用户增长和裂变活动实操",
                "神策数据分析工具使用",
                "文案撰写和活动策划",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "互联网运营经验",
                "用户增长实战案例",
                "数据分析工具（神策）",
                "文案撰写和活动策划",
            ],
            "required_evidence_absent": [
                "教育或知识付费行业经验",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-08  UX/UI Designer, high_match
    # ------------------------------------------------------------------
    {
        "index": 8,
        "jd": V5_PLAN_JDS[8]["jd"],
        "jd_title": "UX/UI 设计师",
        "jd_department": "设计中心",
        "resume_text": (
            "教育背景\n"
            "某美术学院 视觉传达设计 本科 2014-2018\n\n"
            "工作经历\n"
            "某医疗健康科技公司 高级 UX 设计师 2021.01-至今\n"
            "- 主导健康管理 App 2.0 改版，覆盖 iOS 和 Android\n"
            "- 组织 12 轮用户可用性测试，迭代核心健康记录流程\n"
            "- 从零搭建公司移动端 Design System，包含 80+ 组件\n"
            "- 使用 Figma 和 Framer 完成交互设计和高保真原型\n\n"
            "某互联网公司 UI 设计师 2018.07-2020.12\n"
            "- 负责电商 App 详情页和支付流程设计\n"
            "- 使用 Sketch 输出设计稿并整理设计规范\n\n"
            "作品集\n"
            "在线作品集包含医疗 App、电商和出行 3 个完整移动端项目"
        ),
        "labels": {
            "overall_direction": "high_match",
            "reasonable_score_range": (82, 95),
            "key_gaps": [],
            "key_strengths": [
                "医疗健康行业 UX 设计经验",
                "Design System 从零搭建",
                "Figma 和 Framer 精通",
                "用户可用性测试经验丰富",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "至少 3 年移动端 UX/UI 设计经验",
                "精通 Figma",
                "用户研究和数据驱动设计",
                "完整移动端项目作品集",
                "医疗健康行业设计经验",
                "Framer 高保真原型工具",
            ],
            "required_evidence_absent": [],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-09  Legal counsel, partial_match
    # ------------------------------------------------------------------
    {
        "index": 9,
        "jd": V5_PLAN_JDS[9]["jd"],
        "jd_title": "高级法务",
        "jd_department": "法务合规部",
        "resume_text": (
            "教育背景\n"
            "某政法大学 法学 本科 2012-2016\n"
            "某大学 经济法学 硕士 2016-2019\n\n"
            "工作经历\n"
            "某律师事务所 律师 2019.07-2023.06\n"
            "- 处理民商事诉讼和仲裁案件约 60 件\n"
            "- 为企业客户提供合同审核和公司设立法律服务\n\n"
            "某科技公司 法务 2023.07-至今\n"
            "- 审核公司商业合同和 NDA\n"
            "- 协助处理劳动争议和行政许可事务\n"
            "- 跟踪《个人信息保护法》合规要求\n\n"
            "证书\n"
            "法律职业资格证书（A 类）"
        ),
        "labels": {
            "overall_direction": "partial_match",
            "reasonable_score_range": (42, 58),
            "key_gaps": [
                "缺乏跨境电商和互联网金融法规经验",
                "无 GDPR 经验",
                "无跨境交易和国际仲裁经验",
                "英文合同审阅能力未提及",
                "缺乏知识产权注册和维权经验",
            ],
            "key_strengths": [
                "法学硕士学历和法律职业资格",
                "合同审核和诉讼仲裁经验",
                "个人信息保护法合规跟踪",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "法学本科及以上学历",
                "法律职业资格证书",
                "合同法和公司法经验",
                "个人信息保护法合规",
            ],
            "required_evidence_absent": [
                "跨境电商和互联网金融法规",
                "GDPR 经验",
                "跨境交易和国际仲裁",
                "英文合同审阅",
                "知识产权法实践",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-10  Java backend, low_match (frontend person)
    # ------------------------------------------------------------------
    {
        "index": 10,
        "jd": V5_PLAN_JDS[0]["jd"],
        "jd_title": "Java 高级后端工程师",
        "jd_department": "平台技术部",
        "resume_text": (
            "教育背景\n"
            "某大学 数字媒体 本科 2018-2022\n\n"
            "工作经历\n"
            "某创业公司 前端开发 2022.07-至今\n"
            "- 使用 Vue 3 和 Element Plus 开发管理后台\n"
            "- 配合后端完成接口联调\n"
            "- 使用 Git 进行版本管理\n\n"
            "技能\n"
            "Vue 3, JavaScript, HTML, CSS, Element Plus, Git"
        ),
        "labels": {
            "overall_direction": "low_match",
            "reasonable_score_range": (5, 20),
            "key_gaps": [
                "无 Java 开发经验",
                "无后端开发经验",
                "无微服务、数据库、缓存、消息队列经验",
                "经验年限严重不足",
                "非计算机相关专业",
            ],
            "key_strengths": [
                "有软件开发基础",
            ],
            "conflicts": [],
            "required_evidence_present": [],
            "required_evidence_absent": [
                "至少 5 年 Java 后端开发经验",
                "Spring Boot / Spring Cloud / Dubbo",
                "MySQL 分库分表",
                "Redis 缓存设计",
                "Kafka / RocketMQ 消息队列",
                "分布式系统设计",
                "Docker 和 Kubernetes",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-11  Frontend, low_match (backend person, no frontend)
    # ------------------------------------------------------------------
    {
        "index": 11,
        "jd": V5_PLAN_JDS[1]["jd"],
        "jd_title": "前端开发工程师",
        "jd_department": "用户产品部",
        "resume_text": (
            "教育背景\n"
            "某大学 信息管理 本科 2015-2019\n\n"
            "工作经历\n"
            "某公司 Python 后端开发 2019.07-至今\n"
            "- 使用 Django 和 Flask 开发内部管理系统\n"
            "- 编写 RESTful API 和数据库模型\n"
            "- 使用 PostgreSQL 和 Redis 进行数据存储\n"
            "- 部署应用到阿里云 ECS\n\n"
            "技能\n"
            "Python, Django, Flask, PostgreSQL, Redis, Linux"
        ),
        "labels": {
            "overall_direction": "low_match",
            "reasonable_score_range": (8, 22),
            "key_gaps": [
                "无前端开发经验",
                "无 React 或 TypeScript 经验",
                "无构建工具经验",
                "无 UI 还原和响应式布局经验",
            ],
            "key_strengths": [
                "有 RESTful API 开发经验（后端视角）",
                "有软件工程基础",
            ],
            "conflicts": [],
            "required_evidence_present": [],
            "required_evidence_absent": [
                "前端开发经验",
                "React 和 TypeScript",
                "Webpack 或 Vite",
                "UI 还原和响应式布局",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-12  Data engineer, high_match
    # ------------------------------------------------------------------
    {
        "index": 12,
        "jd": V5_PLAN_JDS[2]["jd"],
        "jd_title": "数据工程师",
        "jd_department": "数据平台部",
        "resume_text": (
            "教育背景\n"
            "某理工大学 计算机科学 硕士 2016-2019\n\n"
            "工作经历\n"
            "某电商公司 大数据工程师 2019.07-至今\n"
            "- 使用 Spark 和 Scala 开发离线数仓 ETL 任务，日处理数据量 5TB\n"
            "- 基于 Flink + Kafka 搭建实时数据流处理链路\n"
            "- 设计数据仓库 ODS/DWD/DWS/ADS 分层模型\n"
            "- 使用 ClickHouse 建设实时分析 OLAP 平台\n"
            "- 编写 Python 数据质量监控脚本\n"
            "- 负责 Airflow 任务调度和 SLA 告警\n\n"
            "技能\n"
            "Spark, Flink, Scala, Python, SQL, Kafka, ClickHouse, "
            "Hive, Airflow"
        ),
        "labels": {
            "overall_direction": "high_match",
            "reasonable_score_range": (83, 95),
            "key_gaps": [],
            "key_strengths": [
                "Spark + Flink 双框架精通",
                "Scala 和 Python 双语言",
                "完整数据仓库分层建模",
                "ClickHouse OLAP 实践",
                "Kafka 实时链路经验",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "至少 2 年数据工程经验",
                "Python 和 Scala 数据开发",
                "Spark 和 Flink",
                "SQL 和 OLAP 引擎",
                "数据仓库分层建模",
            ],
            "required_evidence_absent": [],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-13  Product manager, high_match
    # ------------------------------------------------------------------
    {
        "index": 13,
        "jd": V5_PLAN_JDS[3]["jd"],
        "jd_title": "高级产品经理",
        "jd_department": "产品中心",
        "resume_text": (
            "教育背景\n"
            "某大学 工商管理 本科 2012-2016\n\n"
            "工作经历\n"
            "某 HR SaaS 公司 高级产品经理 2022.01-至今\n"
            "- 从 0 到 1 设计并上线智能招聘模块，覆盖 JD 管理和简历筛选\n"
            "- 主导竞品分析报告，覆盖 5 家主要竞争对手\n"
            "- 完成 50+ 客户深度调研，推动产品 NPS 从 35 提升至 52\n"
            "- 使用 Figma 输出低保真原型并与设计师协作\n\n"
            "某互联网公司 产品经理 2018.03-2021.12\n"
            "- 负责 B 端客户管理系统，从需求调研到上线全链路\n"
            "- 拆解季度 OKR 为产品迭代计划\n"
            "- 使用 Axure 输出高保真原型并组织评审\n\n"
            "某移动互联网公司 产品助理 2016.07-2018.02\n"
            "- 整理需求并撰写 PRD\n\n"
            "技能\n"
            "Axure, Figma, SQL, 竞品分析, 用户调研"
        ),
        "labels": {
            "overall_direction": "high_match",
            "reasonable_score_range": (80, 93),
            "key_gaps": [],
            "key_strengths": [
                "HR SaaS 行业产品经验",
                "从 0 到 1 产品设计",
                "B 端全链路产品管理",
                "竞品分析和用户调研",
                "Axure 和 Figma 工具",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "至少 5 年互联网产品经验且 B 端 SaaS",
                "从 0 到 1 产品设计",
                "竞品分析、用户调研、需求拆解",
                "Axure 和 Figma 原型工具",
            ],
            "required_evidence_absent": [],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-14  Legal counsel, low_match (HR person)
    # ------------------------------------------------------------------
    {
        "index": 14,
        "jd": V5_PLAN_JDS[9]["jd"],
        "jd_title": "高级法务",
        "jd_department": "法务合规部",
        "resume_text": (
            "教育背景\n"
            "某大学 行政管理 本科 2014-2018\n\n"
            "工作经历\n"
            "某公司 行政人事主管 2020.03-至今\n"
            "- 负责公司行政事务和办公用品采购\n"
            "- 管理员工入离职手续和社保办理\n"
            "- 协助组织年会和团建活动\n\n"
            "某公司 前台行政 2018.07-2020.02\n"
            "- 接待来访客户和处理文件收发\n\n"
            "技能\n"
            "Office 办公软件, 行政管理"
        ),
        "labels": {
            "overall_direction": "low_match",
            "reasonable_score_range": (3, 15),
            "key_gaps": [
                "无法学学历",
                "无法律职业资格证书",
                "无企业法务或律师执业经验",
                "无合同法、公司法、知识产权法经验",
                "无跨境或合规经验",
                "无英文能力证据",
            ],
            "key_strengths": [],
            "conflicts": [],
            "required_evidence_present": [],
            "required_evidence_absent": [
                "法学本科及以上学历",
                "法律职业资格证书",
                "企业法务或律所经验",
                "合同法、公司法和知识产权法",
                "跨境电商和互联网金融法规",
                "数据保护和隐私合规",
                "跨境交易和国际仲裁",
                "英文读写",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-15  Java backend, partial_match (some match but gaps)
    # ------------------------------------------------------------------
    {
        "index": 15,
        "jd": V5_PLAN_JDS[0]["jd"],
        "jd_title": "Java 高级后端工程师",
        "jd_department": "平台技术部",
        "resume_text": (
            "教育背景\n"
            "某大学 软件工程 本科 2016-2020\n\n"
            "工作经历\n"
            "某金融科技公司 Java 开发工程师 2020.07-至今\n"
            "- 使用 Spring Boot 开发风控规则引擎后端服务\n"
            "- 维护 MySQL 数据库并进行慢查询优化\n"
            "- 使用 Redis 做会话缓存和热数据缓存\n"
            "- 编写单元测试和接口自动化测试\n"
            "- 参与代码评审和技术分享\n\n"
            "技能\n"
            "Java, Spring Boot, MySQL, Redis, JUnit, Git"
        ),
        "labels": {
            "overall_direction": "partial_match",
            "reasonable_score_range": (40, 56),
            "key_gaps": [
                "仅约 4 年经验，低于至少 5 年要求",
                "无微服务框架（Spring Cloud / Dubbo）经验",
                "无分库分表经验",
                "无消息队列经验",
                "无分布式系统和故障排查经验",
                "无 Docker / K8s 容器化经验",
            ],
            "key_strengths": [
                "Spring Boot 和 MySQL 基础扎实",
                "Redis 使用经验",
                "有代码评审和技术分享习惯",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "Spring Boot 经验",
                "MySQL 优化",
                "Redis 缓存",
            ],
            "required_evidence_absent": [
                "至少 5 年 Java 后端开发经验",
                "Spring Cloud / Dubbo 微服务框架",
                "MySQL 分库分表",
                "Kafka / RocketMQ 消息队列",
                "分布式系统设计和故障排查",
                "Docker 和 Kubernetes",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-16  Marketing manager, low_match (tech person)
    # ------------------------------------------------------------------
    {
        "index": 16,
        "jd": V5_PLAN_JDS[6]["jd"],
        "jd_title": "市场推广经理",
        "jd_department": "市场部",
        "resume_text": (
            "教育背景\n"
            "某大学 电子信息工程 本科 2015-2019\n\n"
            "工作经历\n"
            "某科技公司 嵌入式工程师 2019.07-至今\n"
            "- 基于 STM32 开发工业传感器数据采集固件\n"
            "- 使用 C 语言和 FreeRTOS 进行实时系统开发\n"
            "- 调试硬件通信协议包括 SPI、I2C 和 UART\n"
            "- 编写技术文档和测试报告\n\n"
            "技能\n"
            "C, STM32, FreeRTOS, PCB 基础, 示波器调试"
        ),
        "labels": {
            "overall_direction": "low_match",
            "reasonable_score_range": (2, 12),
            "key_gaps": [
                "无市场推广或品牌管理经验",
                "无消费品行业背景",
                "无营销策划和投放经验",
                "无团队管理经验",
                "无数据分析驱动投放经验",
                "完全不相关的技术背景",
            ],
            "key_strengths": [],
            "conflicts": [],
            "required_evidence_present": [],
            "required_evidence_absent": [
                "市场推广或品牌管理经验",
                "消费品行业从业背景",
                "全域营销策划和执行",
                "千万级投放预算管理",
                "团队管理",
                "数据分析驱动投放",
            ],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-17  Operations manager, high_match
    # ------------------------------------------------------------------
    {
        "index": 17,
        "jd": V5_PLAN_JDS[7]["jd"],
        "jd_title": "运营经理",
        "jd_department": "运营部",
        "resume_text": (
            "教育背景\n"
            "某大学 新闻传播 本科 2014-2018\n\n"
            "工作经历\n"
            "某在线教育公司 高级运营经理 2022.01-至今\n"
            "- 统筹用户增长体系，一年内付费用户从 8 万增至 25 万\n"
            "- 设计课程试听转正价的转化漏斗，转化率提升 35%\n"
            "- 搭建 20 个微信社群，完成裂变和续费运营\n"
            "- 使用 Google Analytics 和神策分析监控关键指标\n"
            "- 撰写增长实验报告和运营周报\n\n"
            "某知识付费平台 运营 2018.07-2021.12\n"
            "- 策划专栏上线活动和限时优惠\n"
            "- 维护核心用户社群和 KOL 合作\n"
            "- 日常文案撰写和公众号运营\n\n"
            "技能\n"
            "用户增长, 社群运营, 数据分析, Google Analytics, "
            "神策, 文案, 活动策划"
        ),
        "labels": {
            "overall_direction": "high_match",
            "reasonable_score_range": (80, 94),
            "key_gaps": [],
            "key_strengths": [
                "在线教育行业深度增长经验",
                "转化漏斗优化有量化成果",
                "社群运营和裂变实操",
                "Google Analytics 和神策双工具",
                "文案撰写能力",
            ],
            "conflicts": [],
            "required_evidence_present": [
                "至少 3 年互联网运营经验",
                "用户增长和转化漏斗优化实战",
                "数据分析工具",
                "文案撰写和活动策划",
            ],
            "required_evidence_absent": [],
            "sensitive_labels": [],
        },
    },

    # ------------------------------------------------------------------
    # Pair-18  HRBP, low_match (fresh graduate, sensitive labels)
    # ------------------------------------------------------------------
    {
        "index": 18,
        "jd": V5_PLAN_JDS[4]["jd"],
        "jd_title": "HRBP",
        "jd_department": "人力资源部",
        "resume_text": (
            "教育背景\n"
            "某大学 英语翻译 本科 2020-2024\n\n"
            "实习经历\n"
            "某外企 HR 实习生 2023.09-2024.01\n"
            "- 协助筛选简历和安排面试\n"
            "- 翻译内部培训材料\n\n"
            "校园经历\n"
            "学生会外联部部长\n\n"
            "个人信息\n"
            "已婚，育有一子\n"
            "籍贯：湖南长沙\n"
            "民族：汉"
        ),
        "labels": {
            "overall_direction": "low_match",
            "reasonable_score_range": (8, 22),
            "key_gaps": [
                "无正式 HRBP 或人力资源工作经验",
                "仅有短期 HR 实习",
                "无劳动法和员工关系处理经验",
                "无业务理解和沟通协调的职场证据",
            ],
            "key_strengths": [
                "有短期 HR 实习经验",
            ],
            "conflicts": [],
            "required_evidence_present": [],
            "required_evidence_absent": [
                "至少 3 年 HRBP 或人力资源综合经验",
                "业务理解和沟通协调",
                "劳动法和员工关系处理",
            ],
            "sensitive_labels": [
                "已婚，育有一子",
                "籍贯：湖南长沙",
                "民族：汉",
            ],
        },
    },

    # ------------------------------------------------------------------
    # Pair-19  Finance analyst, partial_match (timeline conflict)
    # ------------------------------------------------------------------
    {
        "index": 19,
        "jd": V5_PLAN_JDS[5]["jd"],
        "jd_title": "财务分析师",
        "jd_department": "财务部",
        "resume_text": (
            "教育背景\n"
            "某大学 财务管理 本科 2019-2023\n\n"
            "工作经历\n"
            "某公司 财务专员 2023.07-至今\n"
            "- 编制月度费用报表\n"
            "- 使用 Excel 制作数据透视表分析部门费用趋势\n"
            "- 配合季度审计准备材料\n\n"
            "自述\n"
            "拥有 5 年企业财务分析经验，精通高级财务建模和预测分析。"
        ),
        "labels": {
            "overall_direction": "partial_match",
            "reasonable_score_range": (35, 52),
            "key_gaps": [
                "实际工作经验仅约 1 年，低于 2 年要求",
                "Excel 使用仅限基础数据透视，非建模层面",
                "无预算编制和费用管控的深度经验",
            ],
            "key_strengths": [
                "财务管理专业本科",
                "基本的费用报表和审计配合经验",
                "有 Excel 使用基础",
            ],
            "conflicts": [
                "自述 5 年企业财务分析经验，但本科 2023 年毕业，"
                "实际工作时间仅约 1 年",
            ],
            "required_evidence_present": [
                "财务相关专业本科",
                "Excel 基础使用",
            ],
            "required_evidence_absent": [
                "至少 2 年企业财务分析经验（实际约 1 年）",
                "Excel 高级数据分析和建模",
            ],
            "sensitive_labels": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Part 3 -- Stability sample indices
# ---------------------------------------------------------------------------

V5_STABILITY_SAMPLE_INDICES: list[int] = [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Part 4 -- Metadata constants
# ---------------------------------------------------------------------------

V5_PLAN_JD_COUNT = 10
V5_REPORT_PAIR_COUNT = 20
V5_STABILITY_SAMPLE_COUNT = 5
V5_STABILITY_RUNS_PER_SAMPLE = 3
V5_PLAN_CALL_BUDGET = 10   # one call per JD
V5_REPORT_CALL_BUDGET = 20  # one call per pair
V5_STABILITY_CALL_BUDGET = 15  # 5 * 3
V5_RESULT_PATH_PREFIX = "docs/stages/stage7/v5-quality-results/"


# ---------------------------------------------------------------------------
# Part 5 -- Helper functions
# ---------------------------------------------------------------------------

def get_v5_plan_jd(index: int) -> dict[str, Any]:
    """Return a single plan JD fixture with labels by index."""
    if not 0 <= index < V5_PLAN_JD_COUNT:
        raise IndexError(
            f"JD index {index} out of range [0, {V5_PLAN_JD_COUNT})"
        )
    return V5_PLAN_JDS[index]


def get_v5_report_pair(index: int) -> dict[str, Any]:
    """Return a single JD+Resume pair fixture with labels by index."""
    if not 0 <= index < V5_REPORT_PAIR_COUNT:
        raise IndexError(
            f"Pair index {index} out of range [0, {V5_REPORT_PAIR_COUNT})"
        )
    return V5_REPORT_PAIRS[index]


def get_v5_stability_pairs() -> list[dict[str, Any]]:
    """Return the 5 stability test pairs."""
    return [V5_REPORT_PAIRS[i] for i in V5_STABILITY_SAMPLE_INDICES]


def compute_v5_fixture_hash() -> str:
    """Compute a deterministic SHA-256 hash of ALL fixture data.

    Uses stable JSON serialization (sorted keys, ensure_ascii=False,
    no trailing whitespace) of the complete JD list, pair list, and
    stability indices.
    """
    payload = {
        "plan_jds": V5_PLAN_JDS,
        "report_pairs": [
            {
                k: v
                for k, v in pair.items()
                # Exclude the embedded jd reference to avoid circular
                # duplication -- the JD content is already in plan_jds.
                # Instead serialize the jd_title and jd_department which
                # identify the JD, plus the resume and labels.
            }
            for pair in V5_REPORT_PAIRS
        ],
        "stability_indices": V5_STABILITY_SAMPLE_INDICES,
        "constants": {
            "plan_jd_count": V5_PLAN_JD_COUNT,
            "report_pair_count": V5_REPORT_PAIR_COUNT,
            "stability_sample_count": V5_STABILITY_SAMPLE_COUNT,
            "stability_runs_per_sample": V5_STABILITY_RUNS_PER_SAMPLE,
            "plan_call_budget": V5_PLAN_CALL_BUDGET,
            "report_call_budget": V5_REPORT_CALL_BUDGET,
            "stability_call_budget": V5_STABILITY_CALL_BUDGET,
        },
    }
    # Convert tuples to lists for JSON serialization stability.
    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _json_default(obj: Any) -> Any:
    """Handle non-JSON-native types for fixture hashing."""
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
