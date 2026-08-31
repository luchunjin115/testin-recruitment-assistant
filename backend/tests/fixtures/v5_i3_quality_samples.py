"""Fresh, deterministic I3 fixtures frozen before any I3 model call.

The text in this module is fictional.  It is separate from the I/I2 fixture and
was introduced only after the production Prompt/Service remediation stopped.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


I3_LABEL_CONTRACT_VERSION = "stage7_v5_quality_contract_v2"
I3_STABILITY_RUNS_PER_SAMPLE = 3


_ROLE_SPECS: list[dict[str, str]] = [
    {
        "title": "质量自动化工程师",
        "department": "交付质量组",
        "background": "企业协作产品正在统一 Web 与移动端发布质量标准。",
        "responsibility": "建设接口和端到端自动化回归，并分析流水线失败原因",
        "experience": "至少 3 年软件测试或质量工程经验",
        "primary": "熟练使用 Python 编写自动化测试",
        "secondary": "具备 Playwright 或同类端到端测试工具实践",
        "preferred": "有持续集成质量门禁建设经验优先",
        "notes": "该岗位每月安排一次内部质量案例分享",
        "strong": "使用 Python 与 Playwright 建设 260 条回归用例，并接入发布流水线",
        "weak": "负责整理手工测试清单并跟踪缺陷关闭情况",
    },
    {
        "title": "云平台可靠性工程师",
        "department": "基础设施组",
        "background": "内部云平台需要降低核心服务的故障恢复时间。",
        "responsibility": "维护容器平台可用性并组织容量评估和故障演练",
        "experience": "至少 3 年平台运维或可靠性工程经验",
        "primary": "能够使用 Kubernetes 排查生产环境问题",
        "secondary": "掌握 Prometheus 指标监控与告警治理",
        "preferred": "有服务等级目标治理经验优先",
        "notes": "值班安排按团队轮换制度执行",
        "strong": "维护 Kubernetes 集群并用 Prometheus 重构告警，平均恢复时间降低 35%",
        "weak": "在开发环境维护 Docker Compose 并处理日常账号申请",
    },
    {
        "title": "商家产品运营",
        "department": "商家增长部",
        "background": "商家工作台新功能需要建立可量化的采用和留存机制。",
        "responsibility": "设计功能运营方案，跟踪采用数据并推动跨团队改进",
        "experience": "至少 3 年 B 端产品运营经验",
        "primary": "能够独立设计用户分层和运营实验",
        "secondary": "熟练使用 SQL 完成运营数据分析",
        "preferred": "有商家工具产品经验优先",
        "notes": "岗位不承担销售签约指标",
        "strong": "为商家工具设计分层实验并用 SQL 复盘，使月活采用率提升 18%",
        "weak": "负责社交媒体内容排期和线下活动物料协调",
    },
    {
        "title": "物流路径算法工程师",
        "department": "履约算法组",
        "background": "同城配送网络需要优化高峰期车辆调度和路径成本。",
        "responsibility": "开发路径优化模型并与调度系统完成在线联调",
        "experience": "至少 3 年运筹优化或算法工程经验",
        "primary": "掌握整数规划或启发式优化方法",
        "secondary": "能够使用 Python 完成算法工程化",
        "preferred": "有车辆路径问题项目经验优先",
        "notes": "业务数据均在脱敏环境内使用",
        "strong": "用整数规划和局部搜索优化车辆路径，Python 服务上线后里程下降 11%",
        "weak": "使用 Excel 汇总配送站点的周度成本数据",
    },
    {
        "title": "嵌入式固件工程师",
        "department": "智能硬件部",
        "background": "环境传感终端正在升级低功耗通信和远程诊断能力。",
        "responsibility": "开发设备固件并定位通信、功耗和现场稳定性问题",
        "experience": "至少 3 年嵌入式固件开发经验",
        "primary": "熟练使用 C 语言进行 MCU 开发",
        "secondary": "具备 I2C、SPI 或 UART 外设调试经验",
        "preferred": "有低功耗设备量产经验优先",
        "notes": "实验室提供标准硬件调试设备",
        "strong": "使用 C 开发 MCU 固件并调试 SPI 传感器，使待机功耗下降 22%",
        "weak": "编写上位机配置页面并维护设备使用说明",
    },
    {
        "title": "安全运营分析师",
        "department": "信息安全部",
        "background": "公司需要统一终端、网络和云环境的安全告警处置流程。",
        "responsibility": "研判安全告警、完成事件响应并沉淀检测规则",
        "experience": "至少 3 年安全运营或事件响应经验",
        "primary": "能够分析日志并完成攻击链调查",
        "secondary": "具备 SIEM 检测规则编写经验",
        "preferred": "有云环境安全事件处置经验优先",
        "notes": "所有案例必须遵守内部数据分级规范",
        "strong": "通过日志关联完成攻击链调查，并为 SIEM 新增 40 条可复用检测规则",
        "weak": "执行办公终端补丁安装并登记资产编号",
    },
    {
        "title": "用户研究员",
        "department": "体验策略部",
        "background": "多端内容产品需要用持续研究支持信息架构调整。",
        "responsibility": "独立规划研究项目并把洞察转化为可验证的产品建议",
        "experience": "至少 3 年用户研究经验",
        "primary": "能够设计并主持深度访谈和可用性测试",
        "secondary": "具备定性资料编码和洞察归纳能力",
        "preferred": "有复杂工具类产品研究经验优先",
        "notes": "研究参与者均按公司规范获得知情说明",
        "strong": "主持 32 场深度访谈和两轮可用性测试，编码结果推动导航改版",
        "weak": "协助发放问卷并整理会议纪要和竞品截图",
    },
    {
        "title": "业务财务伙伴",
        "department": "经营分析部",
        "background": "订阅业务快速增长，需要提升预算预测和经营复盘质量。",
        "responsibility": "负责滚动预测、经营差异分析并支持业务资源决策",
        "experience": "至少 3 年财务分析或业务财务经验",
        "primary": "能够搭建收入成本预测模型",
        "secondary": "具备跨部门经营分析和沟通经验",
        "preferred": "有订阅制业务分析经验优先",
        "notes": "岗位不负责法定审计签字",
        "strong": "搭建订阅收入和成本预测模型，并主持月度差异复盘支持资源调整",
        "weak": "负责费用单据审核和月末凭证归档",
    },
    {
        "title": "企业客户成功经理",
        "department": "客户价值部",
        "background": "企业软件续约规模增长，需要建立标准化价值交付机制。",
        "responsibility": "制定客户成功计划、识别使用风险并协调解决关键问题",
        "experience": "至少 3 年企业软件客户成功经验",
        "primary": "能够用产品使用数据开展健康度管理",
        "secondary": "具备跨团队推动复杂客户问题解决的经验",
        "preferred": "有续约风险管理经验优先",
        "notes": "该岗位不拥有自动续约审批权限",
        "strong": "基于使用数据建立客户健康度分层，并协调三方团队降低续约风险",
        "weak": "负责接听个人用户咨询并按知识库回复常见问题",
    },
    {
        "title": "供应链计划专员",
        "department": "供应链运营部",
        "background": "多仓库存结构需要减少缺货与长期积压并存的问题。",
        "responsibility": "制定需求计划、监控库存水位并协调采购与仓储执行",
        "experience": "至少 3 年需求计划或库存计划经验",
        "primary": "能够使用预测结果制定补货计划",
        "secondary": "具备库存周转和缺货原因分析能力",
        "preferred": "有多仓协同计划经验优先",
        "notes": "工作地点由正式岗位页面另行展示",
        "strong": "根据预测结果制定多仓补货计划，使缺货率下降 9% 且周转天数下降 6 天",
        "weak": "负责仓库到货登记和每日发运表更新",
    },
]


def _plan(case_id: str, spec: dict[str, str]) -> dict[str, Any]:
    jd = {
        "job_background": spec["background"],
        "job_responsibilities": spec["responsibility"] + "。",
        "candidate_requirements": "；".join(
            (spec["experience"], spec["primary"], spec["secondary"])
        )
        + "。",
        "preferred_qualifications": spec["preferred"] + "。",
        "public_notes": spec["notes"] + "。",
    }
    labels = {
        "key_required_items": [
            spec["experience"],
            spec["primary"],
            spec["secondary"],
        ],
        "non_evaluation_content": [spec["notes"]],
        "forbidden_additions": ["年龄要求", "婚育情况", "自动淘汰建议"],
    }
    return {
        "case_id": case_id,
        "title": spec["title"],
        "department": spec["department"],
        "jd": jd,
        "label_contract_version": I3_LABEL_CONTRACT_VERSION,
        "labels": labels,
    }


I3_PLAN_JDS = [
    _plan(f"I3-P{index:02d}", spec) for index, spec in enumerate(_ROLE_SPECS)
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


def _confirmed_snapshot(spec: dict[str, str]) -> dict[str, Any]:
    plan = {
        "schema_version": "5.0",
        "criteria": [
            _criterion(
                1,
                name=spec["experience"],
                importance="required",
                source_field="candidate_requirements",
                source_quote=spec["experience"],
            ),
            _criterion(
                2,
                name=spec["primary"],
                importance="required",
                source_field="candidate_requirements",
                source_quote=spec["primary"],
            ),
            _criterion(
                3,
                name=spec["secondary"],
                importance="required",
                source_field="candidate_requirements",
                source_quote=spec["secondary"],
            ),
            _criterion(
                4,
                name=spec["responsibility"],
                importance="general",
                source_field="job_responsibilities",
                source_quote=spec["responsibility"],
            ),
            _criterion(
                5,
                name=spec["preferred"],
                importance="preferred",
                source_field="preferred_qualifications",
                source_quote=spec["preferred"],
            ),
        ],
    }
    snapshot_sha256 = hashlib.sha256(
        json.dumps(
            plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return {
        "status": "confirmed",
        "confirmed_by": "stage7_i3_fixture_hr_reviewer",
        "confirmed_at": "2026-07-31T10:00:00+08:00",
        "plan": plan,
        "snapshot_sha256": snapshot_sha256,
    }


def _report_case(
    report_index: int,
    plan_index: int,
    *,
    direction: str,
) -> dict[str, Any]:
    spec = _ROLE_SPECS[plan_index]
    plan_case = I3_PLAN_JDS[plan_index]
    case_id = f"I3-R{report_index:02d}"
    if direction == "high_match":
        start_month = "2022-08"
        actual_months = 48
        evidence = spec["strong"]
    elif direction == "partial_match":
        start_month = "2024-08"
        actual_months = 24
        evidence = spec["strong"]
    elif direction == "low_match":
        start_month = "2025-02"
        actual_months = 18
        evidence = spec["weak"]
    else:
        raise ValueError(f"unsupported I3 direction: {direction}")
    applied_at = f"2026-08-{report_index + 1:02d}T09:00:00+08:00"
    resume_text = (
        "工作经历\n"
        f"某行业服务企业 项目成员 {start_month.replace('-', '.')}-至今\n"
        f"- {evidence}\n\n"
        "项目说明\n"
        "- 与产品和交付同事按周同步进展，并记录问题闭环。\n"
    )
    if direction == "high_match":
        material_findings = [
            {
                "finding_id": f"{case_id}-MF01",
                "section": "strengths",
                "label": f"简历有直接证据支持核心要求：{evidence}",
            },
            {
                "finding_id": f"{case_id}-MF02",
                "section": "strengths",
                "label": "按投递时间计算的相关经历达到 3 年门槛",
            },
            {
                "finding_id": f"{case_id}-MF03",
                "section": "missing_info",
                "label": f"简历未明确说明加分项：{spec['preferred']}",
            },
        ]
        score_range = [75, 90]
        present = [spec["experience"], spec["primary"], spec["secondary"]]
        absent = [spec["preferred"]]
    elif direction == "partial_match":
        material_findings = [
            {
                "finding_id": f"{case_id}-MF01",
                "section": "strengths",
                "label": f"简历有直接证据支持核心能力：{evidence}",
            },
            {
                "finding_id": f"{case_id}-MF02",
                "section": "gaps",
                "label": "按投递时间计算的相关经历只有 24 个月，未达到 3 年门槛",
            },
            {
                "finding_id": f"{case_id}-MF03",
                "section": "missing_info",
                "label": f"简历未明确说明加分项：{spec['preferred']}",
            },
        ]
        score_range = [45, 68]
        present = [spec["primary"], spec["secondary"]]
        absent = [spec["experience"], spec["preferred"]]
    else:
        material_findings = [
            {
                "finding_id": f"{case_id}-MF01",
                "section": "gaps",
                "label": "按投递时间计算的相关经历未达到 3 年门槛",
            },
            {
                "finding_id": f"{case_id}-MF02",
                "section": "gaps",
                "label": f"简历没有直接证据支持核心要求：{spec['primary']}",
            },
            {
                "finding_id": f"{case_id}-MF03",
                "section": "strengths",
                "label": "简历体现了基础协作和记录能力",
            },
        ]
        score_range = [15, 38]
        present = []
        absent = [spec["experience"], spec["primary"], spec["secondary"]]
    return {
        "case_id": case_id,
        "plan_case_id": plan_case["case_id"],
        "title": plan_case["title"],
        "department": plan_case["department"],
        "jd": deepcopy(plan_case["jd"]),
        "resume_text": resume_text,
        "application_applied_at": applied_at,
        "evaluation_reference_at": applied_at,
        "label_contract_version": I3_LABEL_CONTRACT_VERSION,
        "confirmed_plan_snapshot": _confirmed_snapshot(spec),
        "time_case": {
            "time_case_id": f"{case_id}-T01",
            "application_applied_at": applied_at,
            "evaluation_reference_at": applied_at,
            "periods": [{"start_month": start_month, "end_month": "present"}],
            "actual_months": actual_months,
            "threshold_months": 36,
        },
        "material_findings": material_findings,
        "labels": {
            "overall_direction": direction,
            "reasonable_score_range": score_range,
            "required_evidence_present": present,
            "required_evidence_absent": absent,
            "sensitive_labels": [],
        },
    }


_REPORT_DIRECTIONS = (
    ["high_match"] * 8
    + ["partial_match"] * 6
    + ["low_match"] * 6
)
I3_REPORT_PAIRS: list[dict[str, Any]] = [
    _report_case(
        report_index,
        report_index % len(I3_PLAN_JDS),
        direction=direction,
    )
    for report_index, direction in enumerate(_REPORT_DIRECTIONS)
]

I3_STABILITY_SAMPLE_INDICES = [0, 4, 8, 10, 14]


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def compute_i3_fixture_hashes() -> dict[str, str]:
    plan_samples = [
        {key: value for key, value in case.items() if key != "labels"}
        for case in I3_PLAN_JDS
    ]
    plan_labels = [case["labels"] for case in I3_PLAN_JDS]
    report_samples = [
        {
            key: value
            for key, value in case.items()
            if key not in {"labels", "material_findings"}
        }
        for case in I3_REPORT_PAIRS
    ]
    report_labels = [
        {"labels": case["labels"], "material_findings": case["material_findings"]}
        for case in I3_REPORT_PAIRS
    ]
    fixture = {
        "plan_jds": I3_PLAN_JDS,
        "report_pairs": I3_REPORT_PAIRS,
        "stability_indices": I3_STABILITY_SAMPLE_INDICES,
        "stability_runs_per_sample": I3_STABILITY_RUNS_PER_SAMPLE,
    }
    return {
        "fixture": _sha256(fixture),
        "plan_samples": _sha256(plan_samples),
        "plan_labels": _sha256(plan_labels),
        "report_samples": _sha256(report_samples),
        "report_labels": _sha256(report_labels),
        "stability_selection": _sha256(I3_STABILITY_SAMPLE_INDICES),
    }
