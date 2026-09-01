"""Frozen, realistic and de-identified Stage 7 Pro quality samples.

The reviewed Markdown remains the single source of the long-form JD and resume
text.  This module parses it into stable machine inputs and adds the human
labels that were fixed before any model call.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REVIEW_PATH = (
    PROJECT_ROOT
    / "docs"
    / "stages"
    / "stage7"
    / "2026-09-01-stage7-pro-realistic-test-data-review.md"
)

JOB_FIELD_HEADINGS = {
    "岗位名称": "title",
    "所属部门": "department",
    "岗位背景": "job_background",
    "岗位职责": "job_responsibilities",
    "任职要求": "candidate_requirements",
    "加分项": "preferred_qualifications",
    "候选人可见备注": "public_notes",
}

LABELS: dict[str, dict[str, Any]] = {
    "R01": {
        "expected_direction": "high_match",
        "score_range": [82, 92],
        "key_evidence_quotes": [
            "使用 Spring Boot 设计 18 个 REST API",
            "接口 P95 从 680ms 降至 210ms",
        ],
        "expected_gaps": [],
        "expected_conflicts": [],
    },
    "R02": {
        "expected_direction": "partial_match",
        "score_range": [55, 68],
        "key_evidence_quotes": [
            "独立完成 9 个内部 REST 接口",
            "使用 Redis 保存登录会话和短信验证码",
        ],
        "expected_gaps": ["Spring Boot", "消息队列", "订单领域", "自动化测试"],
        "expected_conflicts": [],
    },
    "R03": {
        "expected_direction": "low_match",
        "score_range": [18, 32],
        "key_evidence_quotes": ["与 Java 后端工程师联调 REST API"],
        "expected_gaps": ["Java 后端生产实践", "MySQL", "Redis", "消息队列"],
        "expected_conflicts": [],
    },
    "R04": {
        "expected_direction": "partial_match",
        "score_range": [42, 58],
        "key_evidence_quotes": ["参与活动报名后台维护，项目使用 Spring Boot 和 MySQL"],
        "expected_gaps": ["数据库性能分析", "消息异常处理", "自动化测试"],
        "expected_conflicts": ["十万级与每分钟 1,800 次请求冲突", "负责人和子模块角色冲突"],
    },
    "R05": {
        "expected_direction": "high_match",
        "score_range": [85, 94],
        "key_evidence_quotes": [
            "基于 Python、pytest、requests 和 SQLAlchemy 维护 320 余条 API 自动化用例",
            "建设 28 条 Playwright 关键链路",
        ],
        "expected_gaps": [],
        "expected_conflicts": [],
    },
    "R06": {
        "expected_direction": "partial_match",
        "score_range": [52, 66],
        "key_evidence_quotes": [
            "使用 Postman 验证登录、单据提交和审批接口",
            "编写约 20 个 Python 脚本批量生成测试单据",
        ],
        "expected_gaps": ["自动化框架", "CI", "UI 自动化", "独立性能分析"],
        "expected_conflicts": [],
    },
    "R07": {
        "expected_direction": "low_match",
        "score_range": [28, 42],
        "key_evidence_quotes": ["为本人开发的方法编写 JUnit 单元测试"],
        "expected_gaps": ["API 测试方案", "UI 自动化", "性能测试", "质量度量"],
        "expected_conflicts": [],
    },
    "R08": {
        "expected_direction": "partial_match",
        "score_range": [38, 54],
        "key_evidence_quotes": [
            "使用 Postman 集合执行接口检查",
            "能使用 SQL 查询用户和课程记录",
        ],
        "expected_gaps": ["代码断言", "测试数据隔离", "自动化框架", "Python 编程"],
        "expected_conflicts": ["95% 覆盖率口径失真", "万人并发与 10 个线程冲突"],
    },
    "R09": {
        "expected_direction": "high_match",
        "score_range": [86, 94],
        "key_evidence_quotes": [
            "使用窗口函数计算首触渠道、转化周期和客户月度活跃",
            "实验组激活率提升 6.8 个百分点",
        ],
        "expected_gaps": [],
        "expected_conflicts": [],
    },
    "R10": {
        "expected_direction": "partial_match",
        "score_range": [58, 70],
        "key_evidence_quotes": [
            "使用 Tableau 制作渠道和品类看板",
            "推动报表口径增加“支付成功且未全额退款”的条件",
        ],
        "expected_gaps": ["复杂 SQL", "正式实验设计", "Python", "SaaS 场景"],
        "expected_conflicts": [],
    },
    "R11": {
        "expected_direction": "low_match",
        "score_range": [22, 36],
        "key_evidence_quotes": ["使用 Excel 透视表、VLOOKUP 和 Power Query 合并多个部门费用文件"],
        "expected_gaps": ["生产 SQL", "BI 看板", "指标体系", "实验分析"],
        "expected_conflicts": [],
    },
    "R12": {
        "expected_direction": "partial_match",
        "score_range": [40, 56],
        "key_evidence_quotes": ["维护 FineBI 日报并检查空值"],
        "expected_gaps": ["复杂 SQL", "规范实验设计", "独立指标定义"],
        "expected_conflicts": ["转化率分母发生变化", "1,240 人与渠道合计 980 人冲突"],
    },
    "R13": {
        "expected_direction": "high_match",
        "score_range": [87, 95],
        "key_evidence_quotes": [
            "独立输出 PRD、泳道图、交互原型、异常状态表和验收标准",
            "首次配置完成率由 61% 提升至 84%",
        ],
        "expected_gaps": [],
        "expected_conflicts": [],
    },
    "R14": {
        "expected_direction": "partial_match",
        "score_range": [57, 70],
        "key_evidence_quotes": [
            "独立编写 PRD、页面原型和验收标准",
            "任务完成率由 36% 提升至 49%",
        ],
        "expected_gaps": ["企业客户研究", "复杂权限", "多租户", "实施协作"],
        "expected_conflicts": [],
    },
    "R15": {
        "expected_direction": "low_match",
        "score_range": [20, 35],
        "key_evidence_quotes": ["维护项目排期、会议纪要、风险清单和周报"],
        "expected_gaps": ["独立 PRD", "产品优先级", "客户研究", "数据迭代"],
        "expected_conflicts": [],
    },
    "R16": {
        "expected_direction": "partial_match",
        "score_range": [36, 52],
        "key_evidence_quotes": ["输出过工单标签功能 PRD 和原型"],
        "expected_gaps": ["复杂异常流程", "直接客户研究", "复杂权限"],
        "expected_conflicts": ["从 0 到 1 与入职前已上线冲突", "续费率与帮助中心访问量混淆"],
    },
    "R17": {
        "expected_direction": "high_match",
        "score_range": [86, 94],
        "key_evidence_quotes": [
            "编制 3 个月滚动主生产计划",
            "订单准时交付率由 89% 提升至 95%",
        ],
        "expected_gaps": [],
        "expected_conflicts": [],
    },
    "R18": {
        "expected_direction": "partial_match",
        "score_range": [50, 64],
        "key_evidence_quotes": [
            "使用 ERP 查询采购订单、生产领料、成品入库和销售出库单据",
            "推动库位调整后拣货时长下降 12%",
        ],
        "expected_gaps": ["生产计划", "需求预测", "MRP 参数", "交付统筹"],
        "expected_conflicts": [],
    },
    "R19": {
        "expected_direction": "low_match",
        "score_range": [20, 34],
        "key_evidence_quotes": ["根据部门申请进行询价、比价、采购下单和发票对账"],
        "expected_gaps": ["生产计划", "物料齐套", "ERP/MRP", "交付改善"],
        "expected_conflicts": [],
    },
    "R20": {
        "expected_direction": "partial_match",
        "score_range": [36, 52],
        "key_evidence_quotes": ["能使用 VLOOKUP 和数据透视表整理订单"],
        "expected_gaps": ["生产计划主责", "MRP 参数", "供应链分析"],
        "expected_conflicts": ["局部包装材料冒充全公司库存", "100% 交付率与 5 个延期订单冲突"],
    },
}

CONFLICT_CASE_IDS = ("R04", "R08", "R12", "R16", "R20")
STABILITY_CASE_IDS = ("R01", "R05", "R09", "R13", "R17")
EXPECTED_NORMALIZED_FINGERPRINT = (
    "91939d52d65b78efa0b9c135c79127d8debd0e19a0a6522fe0de54b7cbccbe18"
)


def _body_between(content: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^### {re.escape(heading)}\s*$\n(.*?)(?=^### |\Z)",
        content,
    )
    if match is None:
        raise ValueError(f"missing reviewed section: {heading}")
    return match.group(1).strip()


def _parse_review() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = REVIEW_PATH.read_text(encoding="utf-8")
    job_matches = list(
        re.finditer(r"(?m)^## [2-6]\. (JD-\d{2})：(.+)$", text)
    )
    jobs: list[dict[str, Any]] = []
    resumes: list[dict[str, Any]] = []

    for index, match in enumerate(job_matches):
        end = job_matches[index + 1].start() if index + 1 < len(job_matches) else len(text)
        content = text[match.end() : end]
        job_case_id = match.group(1)
        job: dict[str, Any] = {"case_id": job_case_id}
        for heading, field_name in JOB_FIELD_HEADINGS.items():
            job[field_name] = _body_between(content, heading)
        jobs.append(job)

        for resume_match in re.finditer(r"(?m)^### (R\d{2})：(.+)$", content):
            resume_end_match = re.search(
                r"(?m)^### (?:R\d{2}：|岗位名称$)",
                content[resume_match.end() :],
            )
            resume_end = (
                resume_match.end() + resume_end_match.start()
                if resume_end_match is not None
                else len(content)
            )
            resume_block = content[resume_match.end() : resume_end]
            resume_text, separator, _ = resume_block.partition("**人工预期草案**")
            if not separator:
                raise ValueError(f"missing pre-call label: {resume_match.group(1)}")
            case_id = resume_match.group(1)
            resumes.append(
                {
                    "case_id": case_id,
                    "job_case_id": job_case_id,
                    "profile_type": resume_match.group(2).strip(),
                    "resume_text": resume_text.strip(),
                    "labels": LABELS[case_id],
                }
            )
    return jobs, resumes


PLAN_JDS, REPORT_PAIRS = _parse_review()


def normalized_fixture_fingerprint() -> str:
    payload = {
        "jobs": PLAN_JDS,
        "reports": REPORT_PAIRS,
        "conflict_case_ids": CONFLICT_CASE_IDS,
        "stability_case_ids": STABILITY_CASE_IDS,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def direction_counts() -> Counter[str]:
    return Counter(item["labels"]["expected_direction"] for item in REPORT_PAIRS)
