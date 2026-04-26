import json
import random
import re
from datetime import datetime
from typing import Dict, List, Optional


class MockLLM:
    def extract_resume(self, text: str) -> dict:
        name = self._extract_name(text)
        phone = self._extract_phone(text)
        email = self._extract_email(text)
        school = self._extract_school(text)
        degree = self._extract_degree(text)
        major = self._extract_major(text)
        target_role = self._extract_target_role(text)
        experience_years = self._extract_experience_years(text)
        skills = self._extract_skills(text)

        return {
            "name": name,
            "phone": phone,
            "email": email,
            "school": school,
            "degree": degree,
            "major": major,
            "target_role": target_role,
            "experience_years": experience_years,
            "experience_desc": self._extract_experience_desc(text),
            "skills": skills,
            "self_intro": self._extract_self_intro(text),
        }

    def generate_summary(self, data: dict) -> str:
        name = data.get("name", "候选人")
        school = data.get("school", "")
        degree = data.get("degree", "")
        major = data.get("major", "")
        target_role = data.get("target_role", "")
        years = data.get("experience_years", 0)
        skills = data.get("skills", [])
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = []

        skill_text = "、".join(skills[:3]) if skills else "相关技术"
        edu_text = f"{school}{degree}{major}专业" if school else "相关专业背景"

        if years and years > 0:
            exp_text = f"拥有{years}年{target_role or '相关'}工作经验"
        else:
            exp_text = "应届毕业生/实习生"

        templates = [
            f"候选人{name}，{edu_text}，{exp_text}。在{skill_text}方面有突出能力，综合素质较好，建议进入下一轮筛选。",
            f"{name}毕业于{school or '知名高校'}，{degree}{major}方向。{exp_text}，擅长{skill_text}，与{target_role or '目标岗位'}匹配度较高。",
            f"{name}，{edu_text}。{exp_text}，核心技能包括{skill_text}。整体表现出色，建议优先安排面试。",
        ]
        return random.choice(templates)

    def generate_tags(self, data: dict) -> List[str]:
        tags = []
        school = data.get("school", "")
        degree = data.get("degree", "")
        years = data.get("experience_years", 0)
        skills = data.get("skills", [])
        target_role = data.get("target_role", "")
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = []

        top_schools = ["北京大学", "清华大学", "复旦大学", "上海交通大学", "浙江大学",
                       "中国科学技术大学", "南京大学", "武汉大学", "华中科技大学", "中山大学"]
        if any(s in school for s in top_schools):
            tags.append("985高校")
        elif "大学" in school:
            tags.append("本科院校")

        if degree == "博士":
            tags.append("博士学历")
        elif degree == "硕士":
            tags.append("硕士学历")

        if years and years >= 5:
            tags.append("资深经验")
        elif years and years >= 3:
            tags.append("3年+经验")
        elif years and years >= 1:
            tags.append("有经验")
        else:
            tags.append("应届/实习")

        skill_tags_map = {
            "Python": "Python", "Java": "Java", "Go": "Go", "React": "前端开发",
            "Vue": "前端开发", "测试": "测试方向", "自动化": "自动化测试",
            "Selenium": "自动化测试", "性能": "性能测试", "AI": "AI方向",
            "机器学习": "AI方向", "数据": "数据分析", "运维": "DevOps",
            "产品": "产品方向", "设计": "设计方向",
        }
        for skill in skills:
            for keyword, tag in skill_tags_map.items():
                if keyword.lower() in skill.lower() and tag not in tags:
                    tags.append(tag)
                    break

        if target_role:
            tags.append(f"{target_role}方向")

        return tags[:6]

    def generate_followup(self, data: dict) -> str:
        stage = data.get("stage", "新投递")
        name = data.get("name", "候选人")
        days = data.get("days_since_update", 0)
        target_role = data.get("target_role", "")

        suggestions = {
            "新投递": f"建议尽快对{name}进行初筛，查看其{target_role}相关经验是否匹配岗位要求。",
            "初筛": f"{name}已通过初筛，建议在2个工作日内安排面试时间。",
            "待约面": f"请尽快联系{name}确认面试时间，避免候选人流失。",
            "已约面": f"{name}面试已安排，请提前准备面试评估表和{target_role}相关问题。",
            "面试中": f"请关注{name}的面试进展，及时更新面试反馈和评分。",
            "复试": f"{name}进入复试阶段，建议安排高级面试官或技术负责人参与。",
            "offer": f"建议尽快向{name}发出正式offer，并跟进入职意向确认。",
        }

        base = suggestions.get(stage, f"请及时跟进{name}的招聘进展。")
        if days and days > 3:
            base += f" 注意：该候选人已{days}天未更新状态，建议立即跟进！"
        return base

    def screen_candidate(self, data: dict) -> dict:
        target_role = (data.get("target_role") or "").strip()
        job_profile = data.get("job_profile") or {}
        school = (data.get("school") or "").strip()
        degree = (data.get("degree") or "").strip()
        major = (data.get("major") or "").strip()
        experience_desc = (data.get("experience_desc") or "").strip()
        self_intro = (data.get("self_intro") or "").strip()
        resume_text = (data.get("resume_text") or "").strip()
        years = data.get("experience_years") or 0
        skills = data.get("skills") or []
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = []

        searchable = " ".join([
            target_role, school, degree, major, experience_desc, self_intro,
            resume_text, " ".join(skills),
        ]).lower()

        score = 30
        risk_flags = []
        matched_keywords = []
        matched_required = []
        matched_bonus = []
        matched_job_keywords = []

        if target_role:
            score += 5
        else:
            risk_flags.append("岗位信息不完整")

        required_keywords = self._split_terms(job_profile.get("required_skills")) or self._screening_keywords(target_role)
        bonus_keywords = self._split_terms(job_profile.get("bonus_skills"))
        job_keywords = self._split_terms(job_profile.get("job_keywords"))
        risk_keywords = self._split_terms(job_profile.get("risk_keywords"))
        education_requirement = (job_profile.get("education_requirement") or "").strip()
        experience_requirement = (job_profile.get("experience_requirement") or "").strip()
        profile_text = " ".join([
            job_profile.get("description") or "",
            job_profile.get("requirements") or "",
            " ".join(job_keywords),
        ]).lower()

        for keyword in required_keywords:
            if self._term_in_text(keyword, searchable):
                matched_keywords.append(keyword)
                matched_required.append(keyword)

        if required_keywords:
            required_ratio = len(set(matched_required)) / len(required_keywords)
            score += int(required_ratio * 34)
            if required_ratio == 0:
                risk_flags.append("必备技能未命中")
            elif required_ratio < 0.5:
                risk_flags.append("必备技能覆盖不足")
        elif skills:
            score += min(18, len(skills) * 4)

        for keyword in bonus_keywords:
            if self._term_in_text(keyword, searchable):
                matched_bonus.append(keyword)
        if bonus_keywords:
            score += min(14, int((len(set(matched_bonus)) / len(bonus_keywords)) * 14))

        for keyword in job_keywords:
            if self._term_in_text(keyword, searchable):
                matched_job_keywords.append(keyword)
        if job_keywords:
            score += min(10, int((len(set(matched_job_keywords)) / len(job_keywords)) * 10))

        major_keywords = ["计算机", "软件", "信息", "电子", "通信", "自动化", "数据", "人工智能", "数学", "测试"]
        if any(keyword in major for keyword in major_keywords):
            score += 8
        elif major:
            score += 4

        degree_scores = {"博士": 10, "硕士": 8, "本科": 6, "大专": 3}
        if education_requirement:
            if self._degree_rank(degree) >= self._degree_rank(education_requirement):
                score += 8
            else:
                score -= 8
                risk_flags.append("学历未满足岗位要求")
        else:
            score += degree_scores.get(degree, 2 if degree else 0)

        top_schools = ["北京大学", "清华大学", "复旦大学", "上海交通大学", "浙江大学",
                       "中国科学技术大学", "南京大学", "武汉大学", "华中科技大学", "中山大学"]
        if any(item in school for item in top_schools):
            score += 6
        elif school:
            score += 3
        else:
            risk_flags.append("信息不完整")

        try:
            years_value = float(years)
        except (TypeError, ValueError):
            years_value = 0
        min_years = self._parse_min_years(experience_requirement)
        if min_years is not None:
            if years_value >= min_years:
                score += 8
            else:
                score -= 8
                risk_flags.append("经验年限未满足岗位要求")
        elif years_value >= 5:
            score += 8
        elif years_value >= 3:
            score += 6
        elif years_value >= 1:
            score += 4
        elif any(word in target_role for word in ["资深", "高级", "专家", "负责人"]):
            risk_flags.append("经验年限偏低")

        if experience_desc or self_intro or resume_text:
            score += 5
        else:
            risk_flags.append("信息不完整")

        if target_role and skills:
            role_terms = self._role_terms(target_role)
            if role_terms and not any(term.lower() in searchable for term in role_terms):
                score -= 10
                risk_flags.append("岗位不匹配")

        for keyword in risk_keywords:
            if self._term_in_text(keyword, searchable):
                score -= 8
                risk_flags.append(f"命中风险关键词：{keyword}")

        if profile_text and not any(
            self._term_in_text(term, searchable) for term in required_keywords + bonus_keywords + job_keywords
        ):
            score -= 6
            risk_flags.append("与岗位要求关联较弱")

        score = max(0, min(100, score))
        if score >= 80:
            priority_level = "高优先级"
            screening_result = "建议初筛"
        elif score >= 60:
            priority_level = "中优先级"
            screening_result = "备选"
        else:
            priority_level = "低优先级"
            screening_result = "暂缓"

        if not risk_flags:
            risk_flags.append("暂无明显风险")

        reason_parts = []
        if required_keywords:
            reason_parts.append(f"必备技能命中{len(set(matched_required))}/{len(required_keywords)}")
        if bonus_keywords:
            reason_parts.append(f"加分技能命中{len(set(matched_bonus))}/{len(bonus_keywords)}")
        if job_keywords:
            reason_parts.append(f"岗位关键词命中{len(set(matched_job_keywords))}/{len(job_keywords)}")
        if school or degree or major:
            reason_parts.append(f"教育背景为{school or '未填写学校'}{degree or ''}{major or ''}")
        if years_value:
            reason_parts.append(f"具备{years_value:g}年相关经验")
        if job_profile.get("title"):
            reason_parts.insert(0, f"参考岗位要求：{job_profile.get('title')}")
        if not reason_parts:
            reason_parts.append("候选人信息较少，建议HR结合原始简历复核")

        return {
            "match_score": score,
            "priority_level": priority_level,
            "screening_result": screening_result,
            "screening_reason": "；".join(reason_parts[:3]) + "。AI初筛仅作辅助参考，最终决策由HR确认。",
            "risk_flags": list(dict.fromkeys(risk_flags))[:4],
        }

    def summarize_interview_feedback(self, data: dict) -> dict:
        feedback = (data.get("interview_feedback_text") or "").strip()
        name = data.get("name") or "候选人"
        target_role = data.get("target_role") or "目标岗位"
        skills = data.get("skills") or []
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = []

        feedback_lower = feedback.lower()
        positive_terms = ["扎实", "熟练", "清晰", "主动", "优秀", "良好", "不错", "完整", "深入", "匹配", "通过"]
        weak_terms = ["不足", "欠缺", "一般", "模糊", "薄弱", "风险", "不熟", "需要提升", "不匹配", "犹豫"]
        strong_hits = [term for term in positive_terms if term in feedback_lower or term in feedback]
        weak_hits = [term for term in weak_terms if term in feedback_lower or term in feedback]
        skill_hits = [
            skill for skill in skills
            if skill and skill.lower() in feedback_lower
        ]

        if skill_hits:
            technical_summary = f"反馈中明确提到{ '、'.join(skill_hits[:4]) }，可作为{name}技术能力的主要依据。"
        elif any(term in feedback for term in ["技术", "代码", "项目", "测试", "开发", "架构", "算法", "接口", "自动化"]):
            technical_summary = "反馈中提到技术/项目相关表现，但未给出非常具体的技能细节，建议后续结合面试记录或作品继续核实。"
        else:
            technical_summary = "原始反馈未明确描述具体技术能力，暂不做超出反馈的信息判断。"

        if any(term in feedback for term in ["表达", "沟通", "逻辑", "清晰", "配合", "主动"]):
            if any(term in feedback for term in ["不清晰", "一般", "欠缺", "模糊"]):
                communication_summary = "反馈显示沟通表达存在一定不确定性，建议后续继续观察表达结构和需求理解能力。"
            else:
                communication_summary = "反馈显示沟通表达或逻辑呈现较为正向，具备继续沟通评估的基础。"
        else:
            communication_summary = "原始反馈未明确提到沟通表达表现。"

        if any(term in feedback for term in ["匹配", "适合", "符合", "相关", "经验"]):
            job_match = f"反馈中出现岗位匹配相关信息，{name}与{target_role}存在一定匹配基础。"
        elif weak_hits:
            job_match = f"反馈中存在不足或风险描述，{name}与{target_role}的匹配度需要谨慎复核。"
        else:
            job_match = "反馈未充分说明岗位匹配度，建议结合岗位要求和技术面结果综合判断。"

        risk_points = []
        if weak_hits:
            risk_points.append("反馈中存在不足描述：" + "、".join(list(dict.fromkeys(weak_hits))[:3]))
        if not skill_hits and skills:
            risk_points.append("反馈未明确验证候选人简历中的核心技能")
        if len(feedback) < 30:
            risk_points.append("原始反馈较短，AI总结依据有限")
        if not risk_points:
            risk_points.append("暂无明显风险点，但仍需由HR结合完整面试记录确认")

        score = len(strong_hits) - len(weak_hits)
        if any(term in feedback for term in ["offer", "录用", "强烈推荐", "建议发放"]):
            recommendation = "建议 offer"
        elif any(term in feedback for term in ["不建议", "淘汰", "不通过"]):
            recommendation = "不建议继续"
        elif score >= 2 or any(term in feedback for term in ["复试", "二面", "继续"]):
            recommendation = "建议复试"
        elif score <= -1:
            recommendation = "待定"
        else:
            recommendation = "待定"

        next_step_map = {
            "建议复试": "建议安排下一轮复试，并重点追问反馈中尚未验证的核心技能和岗位场景问题。",
            "建议 offer": "建议HR结合薪资期望、到岗时间和团队意见推进 Offer 流程。",
            "待定": "建议补充面试评价或安排加面，确认关键能力和风险点后再做决策。",
            "不建议继续": "建议记录淘汰原因，并由HR复核后再结束流程。",
        }

        return {
            "technical_summary": technical_summary,
            "communication_summary": communication_summary,
            "job_match": job_match,
            "risk_points": risk_points[:5],
            "recommendation": recommendation,
            "next_step": next_step_map[recommendation],
        }

    def chat(self, messages: List[dict], context: Optional[dict] = None) -> str:
        if not messages:
            return "您好！我是HR Copilot助手，请问有什么可以帮您？"

        last_msg = messages[-1].get("content", "").lower()
        ctx = context or {}
        total = ctx.get("total_candidates", 0)
        new_today = ctx.get("new_today", 0)

        if any(k in last_msg for k in ["多少", "数量", "总共", "几个"]):
            return f"当前系统中共有{total}位候选人，今日新增{new_today}位。您可以在候选人列表页面查看详细信息。"

        if any(k in last_msg for k in ["跟进", "提醒", "预警"]):
            alerts = ctx.get("follow_up_count", 0)
            return f"目前有{alerts}位候选人超过3天未更新状态，建议优先处理。您可以在看板页面查看预警详情。"

        if any(k in last_msg for k in ["阶段", "漏斗", "流程"]):
            return "当前招聘漏斗显示各阶段分布均衡。建议重点关注'待约面'和'面试中'阶段的候选人转化率，如需详细数据请查看Dashboard看板。"

        if any(k in last_msg for k in ["建议", "优化", "改进"]):
            return "基于当前招聘数据，有以下建议：\n1. 加快初筛到面试的转化速度，当前平均耗时偏长\n2. 关注简历上传渠道的候选人质量\n3. 对超过3天未跟进的候选人及时处理\n4. 建议增加内推渠道的候选人比例"

        if any(k in last_msg for k in ["你好", "在吗", "帮"]):
            return "您好！我是Testin云测招聘助手，可以帮您：\n1. 查询候选人数据和统计\n2. 分析招聘漏斗和渠道效果\n3. 提供跟进建议和预警\n4. 回答招聘流程相关问题\n请问有什么需要帮助的？"

        return f"收到您的问题。当前系统共有{total}位候选人，今日新增{new_today}位。如需更详细的数据分析，请告诉我具体需求，我会为您提供针对性建议。"

    def _screening_keywords(self, target_role: str) -> List[str]:
        role = (target_role or "").lower()
        role_profiles = [
            (["测试", "qa"], ["Python", "自动化测试", "接口测试", "Selenium", "Appium", "JMeter", "Postman", "Jenkins"]),
            (["前端", "frontend"], ["JavaScript", "TypeScript", "React", "Vue", "HTML", "CSS", "Node.js"]),
            (["后端", "服务端", "backend"], ["Java", "Python", "Go", "Spring", "Django", "FastAPI", "MySQL", "Redis"]),
            (["开发", "工程师"], ["Python", "Java", "Go", "JavaScript", "MySQL", "Git", "Docker"]),
            (["数据", "分析"], ["Python", "SQL", "数据分析", "机器学习", "MySQL", "PostgreSQL"]),
            (["算法", "ai", "人工智能", "机器学习"], ["Python", "机器学习", "深度学习", "自然语言处理", "数据分析"]),
            (["产品"], ["产品", "需求", "PRD", "原型", "用户研究", "数据分析"]),
            (["运维", "devops"], ["Linux", "Docker", "Kubernetes", "Jenkins", "CI/CD", "Redis"]),
        ]
        for role_terms, keywords in role_profiles:
            if any(term in role for term in role_terms):
                return keywords
        return ["Python", "Java", "Git", "MySQL", "沟通"]

    def _split_terms(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        parts = re.split(r"[,，;；、\n]+", str(value))
        result = []
        for part in parts:
            term = part.strip()
            if term and term not in result:
                result.append(term)
        return result

    def _term_in_text(self, term: str, text: str) -> bool:
        term = (term or "").strip().lower()
        if not term:
            return False
        return term in text

    def _degree_rank(self, degree: str) -> int:
        text = degree or ""
        if "博士" in text:
            return 4
        if "硕士" in text:
            return 3
        if "本科" in text:
            return 2
        if "大专" in text:
            return 1
        return 0

    def _parse_min_years(self, requirement: str) -> Optional[float]:
        if not requirement:
            return None
        match = re.search(r"(\d+(?:\.\d+)?)", requirement)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    def _role_terms(self, target_role: str) -> List[str]:
        role = target_role or ""
        if "测试" in role:
            return ["测试", "qa", "selenium", "jmeter", "postman", "自动化"]
        if "前端" in role:
            return ["前端", "react", "vue", "javascript", "typescript"]
        if "后端" in role:
            return ["后端", "java", "python", "go", "spring", "django", "fastapi"]
        if "数据" in role:
            return ["数据", "sql", "python", "分析"]
        if "产品" in role:
            return ["产品", "需求", "prd", "原型"]
        return []

    def _extract_name(self, text: str) -> str:
        lines = text.strip().split("\n")
        for line in lines[:3]:
            line = line.strip()
            if 1 <= len(line) <= 4 and not any(c.isdigit() for c in line):
                return line
        m = re.search(r"姓名[：:]\s*(\S+)", text)
        return m.group(1) if m else "未知"

    def _extract_phone(self, text: str) -> str:
        m = re.search(r"1[3-9]\d{9}", text)
        return m.group(0) if m else ""

    def _extract_email(self, text: str) -> str:
        m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        return m.group(0) if m else ""

    def _extract_school(self, text: str) -> str:
        m = re.search(r"([一-龥]+(?:大学|学院|University|College))", text)
        return m.group(1) if m else ""

    def _extract_degree(self, text: str) -> str:
        for d in ["博士", "硕士", "本科", "大专"]:
            if d in text:
                return d
        return "本科"

    def _extract_major(self, text: str) -> str:
        m = re.search(r"专业[：:]\s*(\S+)", text)
        if m:
            return m.group(1)
        major_keywords = ["计算机", "软件工程", "信息", "电子", "通信", "数学", "自动化", "人工智能", "数据科学"]
        for kw in major_keywords:
            if kw in text:
                return kw + ("科学与技术" if kw == "计算机" else "")
        return ""

    def _extract_target_role(self, text: str) -> str:
        m = re.search(r"(?:求职意向|应聘岗位|目标职位)[：:]\s*(.+?)(?:\n|$)", text)
        if m:
            return m.group(1).strip()
        role_keywords = ["测试工程师", "开发工程师", "产品经理", "设计师", "运维工程师", "数据分析师", "前端工程师", "后端工程师"]
        for kw in role_keywords:
            if kw in text:
                return kw
        return ""

    def _extract_experience_years(self, text: str) -> float:
        m = re.search(r"(\d+)\s*年.*(?:经验|工作)", text)
        if m:
            return float(m.group(1))
        m = re.search(r"(\d{4})\s*[-–~至]\s*(?:至今|现在|present)", text)
        if m:
            return max(0, datetime.now().year - int(m.group(1)))
        return 0

    def _extract_skills(self, text: str) -> List[str]:
        all_skills = [
            "Python", "Java", "JavaScript", "TypeScript", "Go", "C++", "C#", "PHP", "Ruby", "Rust",
            "React", "Vue", "Angular", "Node.js", "Spring", "Django", "Flask", "FastAPI",
            "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
            "Docker", "Kubernetes", "AWS", "Linux", "Git",
            "Selenium", "Appium", "JMeter", "Postman", "Jenkins", "CI/CD",
            "机器学习", "深度学习", "自然语言处理", "数据分析", "人工智能",
            "自动化测试", "性能测试", "接口测试", "安全测试",
        ]
        found = [s for s in all_skills if s.lower() in text.lower()]
        return found if found else ["Python", "测试"]

    def _extract_experience_desc(self, text: str) -> str:
        m = re.search(r"(?:工作经[历验]|项目经[历验])[：:]*\n([\s\S]*?)(?:\n\n|\Z)", text)
        if m:
            return m.group(1).strip()[:500]
        return ""

    def _extract_self_intro(self, text: str) -> str:
        m = re.search(r"(?:自我介绍|个人简介|自我评价)[：:]*\n([\s\S]*?)(?:\n\n|\Z)", text)
        if m:
            return m.group(1).strip()[:300]
        return ""


mock_llm = MockLLM()
