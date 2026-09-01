"""Fresh I4 offline fixtures for the Stage 7 v3 quality contract.

All text is fictional.  These cases define only the future I4 exam and human
label denominators; CLOSE-05G does not create an I4 preflight, raw, human audit,
or final result and does not call a model.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


WORK_DURATION_CASES_VERSION = "stage7_work_duration_cases_v1"
WORK_DURATION_STABILITY_RUNS = 3


_ROLE_SPECS: list[dict[str, str]] = [
    {
        "title": "订单平台 Java 工程师",
        "department": "交易平台组",
        "background": "连锁零售订单平台正在拆分结算与履约服务。",
        "responsibility": "负责订单领域服务设计、接口交付和线上问题复盘",
        "pure_duration": "3 年以上工作经验",
        "mixed_requirement": "3 年以上 Java 经验",
        "capability": "Java",
        "secondary": "能够使用 Spring Boot 设计 REST API",
        "preferred": "有高并发订单系统实践优先",
        "notes": "团队每两周举行一次技术分享",
        "strong": "使用 Java 和 Spring Boot 重构订单接口，并通过压测定位慢查询",
        "partial": "使用 Java 维护订单任务，但未说明 Spring Boot API 设计",
        "weak": "负责整理门店订单报表和处理用户咨询",
    },
    {
        "title": "数据管道工程师",
        "department": "数据基础组",
        "background": "分析平台需要统一批处理任务的质量监控。",
        "responsibility": "建设数据管道、质量校验和失败任务恢复机制",
        "pure_duration": "4 年以上工作经验",
        "mixed_requirement": "2 年以上 Spark 经验",
        "capability": "Spark",
        "secondary": "能够使用 Airflow 编排数据任务",
        "preferred": "有数据血缘治理经验优先",
        "notes": "内部数据均按分级制度授权使用",
        "strong": "用 Spark 建设增量管道，并通过 Airflow 编排重跑和质量检查",
        "partial": "用 Spark 开发离线任务，但未体现 Airflow 编排实践",
        "weak": "使用表格汇总每日渠道数据并发送邮件",
    },
    {
        "title": "移动端体验工程师",
        "department": "客户端体验组",
        "background": "会员应用需要降低复杂页面的卡顿和崩溃。",
        "responsibility": "开发移动端功能并持续治理性能与稳定性问题",
        "pure_duration": "3 年以上工作经验",
        "mixed_requirement": "2 年以上 Flutter 经验",
        "capability": "Flutter",
        "secondary": "具备移动端性能分析和优化实践",
        "preferred": "有跨端组件库建设经验优先",
        "notes": "应用发布遵循统一灰度流程",
        "strong": "用 Flutter 交付会员页面，并通过性能分析将首屏耗时降低 28%",
        "partial": "用 Flutter 开发活动页面，但未说明性能分析方法",
        "weak": "负责整理应用商店评论和更新运营素材",
    },
    {
        "title": "风控策略分析师",
        "department": "风险策略部",
        "background": "支付业务需要提升异常交易识别的可解释性。",
        "responsibility": "分析风险样本、设计策略并跟踪上线后的命中效果",
        "pure_duration": "3 年以上工作经验",
        "mixed_requirement": "2 年以上 SQL 分析经验",
        "capability": "SQL 分析",
        "secondary": "能够设计并评估风险规则",
        "preferred": "有支付风险场景经验优先",
        "notes": "策略上线需要经过双人复核",
        "strong": "使用 SQL 分析拒付样本并设计风险规则，使误报率下降 12%",
        "partial": "使用 SQL 提取风险样本，但未体现规则效果评估",
        "weak": "负责登记客户投诉和整理处理进度",
    },
    {
        "title": "制造质量工程师",
        "department": "智能制造部",
        "background": "装配产线需要减少重复缺陷和返工。",
        "responsibility": "分析制程缺陷、推动纠正措施并验证改善效果",
        "pure_duration": "5 年以上工作经验",
        "mixed_requirement": "3 年以上 SPC 实践经验",
        "capability": "SPC",
        "secondary": "能够使用 8D 方法推动缺陷闭环",
        "preferred": "有自动化产线质量改善经验优先",
        "notes": "岗位按工厂安全制度进入现场",
        "strong": "使用 SPC 识别制程波动，并用 8D 推动治具整改降低返工率",
        "partial": "使用 SPC 监控参数，但未说明 8D 缺陷闭环",
        "weak": "负责归档检验表和补充物料标签",
    },
    {
        "title": "企业实施顾问",
        "department": "解决方案交付部",
        "background": "企业客户需要更标准的系统上线与验收流程。",
        "responsibility": "梳理客户流程、配置解决方案并推动上线验收",
        "pure_duration": "3 年以上工作经验",
        "mixed_requirement": "2 年以上 ERP 实施经验",
        "capability": "ERP 实施",
        "secondary": "具备客户需求澄清和方案配置能力",
        "preferred": "有制造行业项目经验优先",
        "notes": "差旅安排以项目计划为准",
        "strong": "完成 ERP 流程调研和方案配置，并组织客户完成上线验收",
        "partial": "参与 ERP 配置，但未体现独立需求澄清",
        "weak": "负责会议预约和项目资料打印",
    },
    {
        "title": "搜索产品经理",
        "department": "内容发现组",
        "background": "知识产品需要改善长尾查询的结果质量。",
        "responsibility": "定义搜索问题、设计迭代方案并验证用户效果",
        "pure_duration": "4 年以上工作经验",
        "mixed_requirement": "2 年以上搜索产品经验",
        "capability": "搜索产品",
        "secondary": "能够设计搜索质量指标和实验",
        "preferred": "有知识类产品经验优先",
        "notes": "用户研究遵循公司隐私规范",
        "strong": "设计搜索质量指标和分流实验，使长尾查询成功率提升 9%",
        "partial": "负责搜索需求排期，但未说明质量指标或实验",
        "weak": "负责内容专题配置和日常运营活动",
    },
    {
        "title": "采购品类经理",
        "department": "采购管理部",
        "background": "通用设备采购需要提升成本透明度和履约稳定性。",
        "responsibility": "制定品类策略、评估供应商并推动采购降本",
        "pure_duration": "5 年以上工作经验",
        "mixed_requirement": "3 年以上品类采购经验",
        "capability": "品类采购",
        "secondary": "能够开展供应商成本分析与谈判",
        "preferred": "有设备类采购经验优先",
        "notes": "供应商准入遵循合规审查流程",
        "strong": "制定设备品类策略并完成成本拆解谈判，年度采购成本下降 7%",
        "partial": "负责品类询价，但未体现供应商成本分析",
        "weak": "负责采购订单录入和发票流转",
    },
    {
        "title": "品牌内容策划",
        "department": "品牌传播部",
        "background": "新业务需要建立一致的专业内容表达。",
        "responsibility": "策划品牌内容、组织制作并复盘传播效果",
        "pure_duration": "3 年以上工作经验",
        "mixed_requirement": "2 年以上 B2B 内容经验",
        "capability": "B2B 内容策划",
        "secondary": "能够基于传播数据迭代内容",
        "preferred": "有企业服务品牌经验优先",
        "notes": "对外发布内容需要完成品牌审核",
        "strong": "策划 B2B 行业专题并根据传播数据迭代选题，线索转化提升 16%",
        "partial": "撰写 B2B 文章，但未体现数据复盘和迭代",
        "weak": "负责活动签到和礼品寄送",
    },
    {
        "title": "仓储流程优化师",
        "department": "履约运营部",
        "background": "多仓作业需要缩短高峰期出库时间。",
        "responsibility": "分析仓内流程、设计改善方案并跟踪落地效果",
        "pure_duration": "4 年以上工作经验",
        "mixed_requirement": "2 年以上 WMS 优化经验",
        "capability": "WMS 优化",
        "secondary": "能够开展仓储流程分析和改善",
        "preferred": "有多仓标准化经验优先",
        "notes": "现场改善须遵守仓库安全规范",
        "strong": "基于 WMS 数据重排拣选路径，使高峰期出库时长下降 14%",
        "partial": "使用 WMS 查询库存，但未体现流程分析和改善",
        "weak": "负责打印出库单和更新值班表",
    },
]


def _plan(case_id: str, spec: dict[str, str]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "title": spec["title"],
        "department": spec["department"],
        "jd": {
            "job_background": spec["background"],
            "job_responsibilities": spec["responsibility"] + "。",
            "candidate_requirements": "；".join(
                (
                    spec["pure_duration"],
                    spec["mixed_requirement"],
                    spec["secondary"],
                )
            )
            + "。",
            "preferred_qualifications": spec["preferred"] + "。",
            "public_notes": spec["notes"] + "。",
        },
        "label_contract_version": WORK_DURATION_CASES_VERSION,
        "labels": {
            "key_required_items": [spec["capability"], spec["secondary"]],
            "excluded_pure_work_duration_requirements": [spec["pure_duration"]],
            "mixed_requirement_capability_items": [
                {
                    "source_requirement": spec["mixed_requirement"],
                    "capability_label": spec["capability"],
                }
            ],
            "non_evaluation_content": [spec["notes"]],
            "forbidden_additions": ["年龄要求", "婚育情况", "自动淘汰建议"],
        },
    }


WORK_DURATION_PLAN_CASES = [
    _plan(f"WD-P{index:02d}", spec) for index, spec in enumerate(_ROLE_SPECS)
]


def _criterion(
    number: int,
    *,
    name: str,
    importance: str,
    source_field: str,
    source_quote: str,
) -> dict[str, Any]:
    return {
        "criterion_id": f"criterion:{number:04d}",
        "name": name,
        "importance": importance,
        "description": name,
        "screening_focus": f"核对简历中是否有可定位证据支持：{name}",
        "origin": "ai_from_jd",
        "sources": [
            {"source_field": source_field, "source_quote": source_quote}
        ],
    }


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _confirmed_snapshot(spec: dict[str, str]) -> dict[str, Any]:
    plan = {
        "schema_version": "5.0",
        "criteria": [
            _criterion(
                1,
                name=spec["capability"],
                importance="required",
                source_field="candidate_requirements",
                source_quote=spec["mixed_requirement"],
            ),
            _criterion(
                2,
                name=spec["secondary"],
                importance="required",
                source_field="candidate_requirements",
                source_quote=spec["secondary"],
            ),
            _criterion(
                3,
                name=spec["responsibility"],
                importance="general",
                source_field="job_responsibilities",
                source_quote=spec["responsibility"],
            ),
            _criterion(
                4,
                name=spec["preferred"],
                importance="preferred",
                source_field="preferred_qualifications",
                source_quote=spec["preferred"],
            ),
        ],
    }
    return {
        "status": "confirmed",
        "confirmed_by": "stage7_i4_offline_fixture_hr_reviewer",
        "confirmed_at": "2026-08-31T16:00:00+08:00",
        "plan": plan,
        "snapshot_sha256": _sha256(plan),
    }


def _report_case(
    report_index: int, plan_index: int, *, direction: str
) -> dict[str, Any]:
    spec = _ROLE_SPECS[plan_index]
    plan_case = WORK_DURATION_PLAN_CASES[plan_index]
    case_id = f"WD-R{report_index:02d}"
    if direction == "high_match":
        evidence = spec["strong"]
        present = [spec["capability"], spec["secondary"]]
        absent: list[str] = []
        score_range = [75, 90]
        material_findings = [
            {
                "finding_id": f"{case_id}-MF01",
                "section": "strengths",
                "label": f"简历有直接证据支持核心能力：{spec['capability']}",
            },
            {
                "finding_id": f"{case_id}-MF02",
                "section": "strengths",
                "label": f"简历有直接证据支持配套能力：{spec['secondary']}",
            },
            {
                "finding_id": f"{case_id}-MF03",
                "section": "missing_info",
                "label": f"简历未明确说明加分项：{spec['preferred']}",
            },
        ]
    elif direction == "partial_match":
        evidence = spec["partial"]
        present = [spec["capability"]]
        absent = [spec["secondary"]]
        score_range = [45, 68]
        material_findings = [
            {
                "finding_id": f"{case_id}-MF01",
                "section": "strengths",
                "label": f"简历有直接证据支持核心能力：{spec['capability']}",
            },
            {
                "finding_id": f"{case_id}-MF02",
                "section": "gaps",
                "label": f"简历没有直接证据支持配套能力：{spec['secondary']}",
            },
            {
                "finding_id": f"{case_id}-MF03",
                "section": "missing_info",
                "label": f"简历未明确说明加分项：{spec['preferred']}",
            },
        ]
    elif direction == "low_match":
        evidence = spec["weak"]
        present = []
        absent = [spec["capability"], spec["secondary"]]
        score_range = [15, 38]
        material_findings = [
            {
                "finding_id": f"{case_id}-MF01",
                "section": "gaps",
                "label": f"简历没有直接证据支持核心能力：{spec['capability']}",
            },
            {
                "finding_id": f"{case_id}-MF02",
                "section": "gaps",
                "label": f"简历没有直接证据支持配套能力：{spec['secondary']}",
            },
            {
                "finding_id": f"{case_id}-MF03",
                "section": "strengths",
                "label": "简历体现了基础协作和记录能力",
            },
        ]
    else:
        raise ValueError(f"unsupported work-duration direction: {direction}")
    return {
        "case_id": case_id,
        "plan_case_id": plan_case["case_id"],
        "title": plan_case["title"],
        "department": plan_case["department"],
        "jd": deepcopy(plan_case["jd"]),
        "resume_text": (
            "工作经历\n"
            f"某虚构企业 项目成员 2023.04-至今\n- {evidence}\n\n"
            "项目说明\n- 与业务和交付同事按周同步进展，并记录问题闭环。\n"
        ),
        "label_contract_version": WORK_DURATION_CASES_VERSION,
        "confirmed_plan_snapshot": _confirmed_snapshot(spec),
        "material_findings": material_findings,
        "labels": {
            "overall_direction": direction,
            "reasonable_score_range": score_range,
            "required_evidence_present": present,
            "required_evidence_absent": absent,
            "sensitive_labels": [],
        },
    }


_REPORT_DIRECTIONS = ["high_match"] * 8 + ["partial_match"] * 6 + ["low_match"] * 6
WORK_DURATION_REPORT_CASES: list[dict[str, Any]] = [
    _report_case(
        report_index,
        report_index % len(WORK_DURATION_PLAN_CASES),
        direction=direction,
    )
    for report_index, direction in enumerate(_REPORT_DIRECTIONS)
]

WORK_DURATION_STABILITY_INDICES = [0, 4, 8, 10, 14]


def compute_i4_fixture_hashes() -> dict[str, str]:
    plan_samples = [
        {key: value for key, value in case.items() if key != "labels"}
        for case in WORK_DURATION_PLAN_CASES
    ]
    plan_labels = [case["labels"] for case in WORK_DURATION_PLAN_CASES]
    report_samples = [
        {
            key: value
            for key, value in case.items()
            if key not in {"labels", "material_findings"}
        }
        for case in WORK_DURATION_REPORT_CASES
    ]
    report_labels = [
        {"labels": case["labels"], "material_findings": case["material_findings"]}
        for case in WORK_DURATION_REPORT_CASES
    ]
    fixture = {
        "plan_jds": WORK_DURATION_PLAN_CASES,
        "report_pairs": WORK_DURATION_REPORT_CASES,
        "stability_indices": WORK_DURATION_STABILITY_INDICES,
        "stability_runs_per_sample": WORK_DURATION_STABILITY_RUNS,
    }
    return {
        "fixture": _sha256(fixture),
        "plan_samples": _sha256(plan_samples),
        "plan_labels": _sha256(plan_labels),
        "report_samples": _sha256(report_samples),
        "report_labels": _sha256(report_labels),
        "stability_selection": _sha256(WORK_DURATION_STABILITY_INDICES),
    }


