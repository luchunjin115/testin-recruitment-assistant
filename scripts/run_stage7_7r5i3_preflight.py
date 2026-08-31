from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (BACKEND_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.adapters.job_evaluation_plan import (  # noqa: E402
    FakeJobEvaluationPlanAdapter,
    JobEvaluationPlanAdapterResult,
)
from app.adapters.screening_evaluation import (  # noqa: E402
    FakeScreeningEvaluationAdapter,
    ScreeningEvaluationAdapterResult,
)
from app.prompts.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
    build_job_evaluation_plan_v5_messages,
)
from app.prompts.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
    build_screening_evaluation_v5_messages,
)
from app.schemas.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
    V5CriterionItem,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
)
from app.services.experience_period_service import experience_period_service  # noqa: E402
from app.services.job_evaluation_plan_service import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION,
    job_evaluation_plan_service,
)
from app.services.screening_evaluation_service import (  # noqa: E402
    screening_evaluation_service,
)
from stage7_7r5_quality_contract import (  # noqa: E402
    I2_FINAL_RESULT_PATH,
    I2_HUMAN_AUDIT_PATH,
    I2_PREFLIGHT_PATH,
    I2_RAW_RESULT_PATH,
    I3_FINAL_RESULT_PATH,
    I3_HUMAN_AUDIT_PATH,
    I3_PREFLIGHT_PATH,
    I3_QUALITY_CONTRACT_VERSION,
    I3_RAW_RESULT_PATH,
    I3_RUN_ID,
    I3_SUPERSEDED_PREFLIGHT_PATH,
    I3_SUPERSEDED_REVIEW_PATH,
    sha256_value,
    validate_i3_case_inputs,
    validate_i3_material_findings,
    validate_i3_time_case,
)
from tests.fixtures.v5_i3_quality_samples import (  # noqa: E402
    I3_PLAN_JDS,
    I3_REPORT_PAIRS,
    I3_STABILITY_RUNS_PER_SAMPLE,
    I3_STABILITY_SAMPLE_INDICES,
    compute_i3_fixture_hashes,
)
from tests.fixtures.v5_quality_samples import (  # noqa: E402
    V5_PLAN_JDS,
    V5_REPORT_PAIRS,
)


I3_FROZEN_HASHES = {
    "fixture": "f339f76cc6047bf3bfa822a3817392e6b4a20272462b9ab35995eb14aa074946",
    "plan_samples": "4c9dbeae5a9ec69cee306a5bae943140ce85cbd49bdaca187278b5ebfe4b1616",
    "plan_labels": "664d941dde65724ab265eaa399aeff08be5b0f2b4ba094fd17b547977e1bdf39",
    "report_samples": "52604fd168962531b9d3a88645a7e809de5b97580931dd109c495967e05a5fb9",
    "report_labels": "bfb8ad22c7704b3948194f54d155509ae753e07c72cae2da02d252c323d81892",
    "stability_selection": "59c2adb3ce95c083124c3a0eebb931d5175bb5653c37ea829a14e9b9af34a76d",
}
I3_SUPERSEDED_PREFLIGHT_SHA256 = (
    "a458fab4e044f38234935b0135c76cfd0b618e5cc8cad1bc83c2e90155c21e17"
)
I3_SUPERSEDED_REVIEW_SHA256 = (
    "9dc797b83dabfa2bedc7301e7c462ecaeff16d6ace2873eee17a046322a6e3b0"
)
I3_REVIEW_PATH = I3_PREFLIGHT_PATH.with_name(
    "2026-08-31-stage7-7r5i3-r1-fixture-review.md"
)


def i3_paths() -> dict[str, Path]:
    return {
        "superseded_preflight": I3_SUPERSEDED_PREFLIGHT_PATH,
        "preflight": I3_PREFLIGHT_PATH,
        "raw": I3_RAW_RESULT_PATH,
        "human": I3_HUMAN_AUDIT_PATH,
        "final": I3_FINAL_RESULT_PATH,
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_superseded_preflight() -> dict[str, Any]:
    if not I3_SUPERSEDED_PREFLIGHT_PATH.exists() or not I3_SUPERSEDED_REVIEW_PATH.exists():
        raise RuntimeError("用户拒绝的旧 I3 preflight 或复核单缺失")
    if _file_sha256(I3_SUPERSEDED_PREFLIGHT_PATH) != I3_SUPERSEDED_PREFLIGHT_SHA256:
        raise RuntimeError("用户拒绝的旧 I3 preflight 已发生变化")
    if _file_sha256(I3_SUPERSEDED_REVIEW_PATH) != I3_SUPERSEDED_REVIEW_SHA256:
        raise RuntimeError("用户拒绝的旧 I3 复核单已发生变化")
    try:
        old = json.loads(I3_SUPERSEDED_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        raise RuntimeError("用户拒绝的旧 I3 preflight 无法读取") from None
    old_directions = [
        case.get("labels", {}).get("overall_direction")
        for case in old.get("frozen_fixture", {}).get("report_cases", [])
        if isinstance(case, dict)
    ]
    if (
        old.get("stage") != "7R5-I3"
        or old.get("fixture_hashes", {}).get("fixture")
        != "5869bc60504195bd392d7880d93bd6c52a770edba6e6ced35586ad706337b481"
        or old_directions.count("high_match") != 10
        or old_directions.count("partial_match") != 0
        or old_directions.count("low_match") != 10
    ):
        raise RuntimeError("用户拒绝的旧 I3 preflight 身份或 10/0/10 分布不一致")
    return {
        "stage": "7R5-I3",
        "preflight_path": str(I3_SUPERSEDED_PREFLIGHT_PATH),
        "reason": "user_rejected_10_high_0_partial_10_low_distribution",
        "old_fixture_sha256": old["fixture_hashes"]["fixture"],
        "old_evidence_preserved": True,
    }


def _job(case: dict[str, Any], index: int) -> SimpleNamespace:
    jd = case["jd"]
    return SimpleNamespace(
        id=193_000 + index,
        title=case["title"],
        department=case["department"],
        job_background=jd["job_background"],
        job_responsibilities=jd["job_responsibilities"],
        candidate_requirements=jd["candidate_requirements"],
        preferred_qualifications=jd["preferred_qualifications"],
        public_notes=jd["public_notes"],
        status="open",
    )


def _actual_execution_contract() -> dict[str, str]:
    return {
        "plan_prompt_version": JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
        "plan_service_behavior_version": (
            JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION
        ),
        "plan_schema_version": JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
        "report_prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
        "report_service_behavior_version": SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
        "report_schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
    }


def _freshness_checks() -> dict[str, bool]:
    old_jds = {sha256_value(case["jd"]) for case in V5_PLAN_JDS}
    old_resumes = {sha256_value(case["resume_text"]) for case in V5_REPORT_PAIRS}
    return {
        "no_i2_jd_reused": all(
            sha256_value(case["jd"]) not in old_jds for case in I3_PLAN_JDS
        ),
        "no_i2_resume_reused": all(
            sha256_value(case["resume_text"]) not in old_resumes
            for case in I3_REPORT_PAIRS
        ),
    }


async def _run_local_fake_and_prompt_checks() -> dict[str, int]:
    plan_outcome = JobEvaluationPlanAdapterResult(
        content="{}", model="i3-local-fake", finish_reason="stop"
    )
    plan_adapter = FakeJobEvaluationPlanAdapter(
        [plan_outcome for _ in I3_PLAN_JDS]
    )
    plan_prompt_count = 0
    for index, case in enumerate(I3_PLAN_JDS):
        snapshot = job_evaluation_plan_service.build_v5_input_snapshot(
            _job(case, index)
        ).model_dump(mode="json")
        messages = build_job_evaluation_plan_v5_messages(snapshot)
        if len(messages) != 2:
            raise RuntimeError("I3 计划 Prompt 构建结果非法")
        plan_prompt_count += 1
        await plan_adapter.generate_v5(snapshot)

    report_call_count = len(I3_REPORT_PAIRS) + (
        len(I3_STABILITY_SAMPLE_INDICES) * I3_STABILITY_RUNS_PER_SAMPLE
    )
    report_outcome = ScreeningEvaluationAdapterResult(
        content="{}", model="i3-local-fake", finish_reason="stop"
    )
    report_adapter = FakeScreeningEvaluationAdapter(
        [report_outcome for _ in range(report_call_count)]
    )
    report_prompt_count = 0
    prepared_inputs: dict[int, dict[str, Any]] = {}
    for index, case in enumerate(I3_REPORT_PAIRS):
        sanitized = screening_evaluation_service.sanitize_resume_text(
            case["resume_text"]
        )
        reference = datetime.fromisoformat(case["evaluation_reference_at"])
        facts = experience_period_service.build(
            sanitized,
            evaluation_reference_at=reference,
            evaluation_timezone="Asia/Shanghai",
        ).model_dump(mode="json")
        payload = {
            "job_snapshot": case["jd"],
            "evaluation_plan": case["confirmed_plan_snapshot"]["plan"],
            "sanitized_resume": sanitized,
            "evaluation_reference_at": case["evaluation_reference_at"],
            "evaluation_timezone": "Asia/Shanghai",
            "experience_period_facts": facts,
        }
        messages = build_screening_evaluation_v5_messages(**payload)
        if len(messages) != 2:
            raise RuntimeError("I3 报告 Prompt 构建结果非法")
        report_prompt_count += 1
        await report_adapter.evaluate_v5(**payload)
        prepared_inputs[index] = payload
    for sample_index in I3_STABILITY_SAMPLE_INDICES:
        for _ in range(I3_STABILITY_RUNS_PER_SAMPLE):
            await report_adapter.evaluate_v5(**prepared_inputs[sample_index])

    return {
        "plan_prompt_build_count": plan_prompt_count,
        "report_prompt_build_count": report_prompt_count,
        "fake_plan_adapter_call_count": len(plan_adapter.v5_calls),
        "fake_report_adapter_call_count": len(report_adapter.calls),
        "fake_adapter_call_count": len(plan_adapter.v5_calls)
        + len(report_adapter.calls),
    }


def _validate_frozen_cases() -> dict[str, int]:
    plan_ids = [case["case_id"] for case in I3_PLAN_JDS]
    report_ids = [case["case_id"] for case in I3_REPORT_PAIRS]
    if len(plan_ids) != 10 or len(set(plan_ids)) != 10:
        raise RuntimeError("I3 必须冻结 10 个唯一计划 case")
    if len(report_ids) != 20 or len(set(report_ids)) != 20:
        raise RuntimeError("I3 必须冻结 20 个唯一报告 case")
    if len(I3_STABILITY_SAMPLE_INDICES) != 5 or len(
        set(I3_STABILITY_SAMPLE_INDICES)
    ) != 5:
        raise RuntimeError("I3 必须冻结 5 个唯一稳定性组")

    required_label_count = sum(
        len(case["labels"]["key_required_items"]) for case in I3_PLAN_JDS
    )
    material_finding_count = 0
    for case in I3_REPORT_PAIRS:
        validate_i3_case_inputs(case, run_kind="report")
        if case["application_applied_at"] != case["evaluation_reference_at"]:
            raise RuntimeError("I3 case 顶层评价参考时间必须等于投递时间")
        validate_i3_time_case(case["time_case"])
        material_finding_count += len(
            validate_i3_material_findings(case["material_findings"])
        )
        jd = case["jd"]
        for criterion in case["confirmed_plan_snapshot"]["plan"]["criteria"]:
            validated = V5CriterionItem.model_validate(criterion)
            for source in validated.sources:
                if source.source_quote not in jd[source.source_field]:
                    raise RuntimeError("I3 HR 确认计划来源未逐字存在于 JD")
    return {
        "plan_required_label_count": required_label_count,
        "material_finding_count": material_finding_count,
        "time_case_count": len(I3_REPORT_PAIRS),
        "confirmed_plan_snapshot_count": len(I3_REPORT_PAIRS),
    }


async def build_preflight_payload() -> dict[str, Any]:
    paths = i3_paths()
    if any(paths[key].exists() for key in ("raw", "human", "final")):
        raise RuntimeError("I3 正式结果路径必须在 06A 保持不存在")
    if {
        path.resolve() for key, path in paths.items() if key != "superseded_preflight"
    } & {
        I2_PREFLIGHT_PATH.resolve(),
        I2_RAW_RESULT_PATH.resolve(),
        I2_HUMAN_AUDIT_PATH.resolve(),
        I2_FINAL_RESULT_PATH.resolve(),
    }:
        raise RuntimeError("I3 路径不得与 I2 重叠")

    supersedes = _validate_superseded_preflight()

    observed_hashes = compute_i3_fixture_hashes()
    if observed_hashes != I3_FROZEN_HASHES:
        raise RuntimeError("I3 冻结样本或标签指纹不一致")
    freshness = _freshness_checks()
    if not all(freshness.values()):
        raise RuntimeError("I3 不得复用 I2 的 JD 或简历样本")
    execution = _actual_execution_contract()
    expected_execution = {
        "plan_prompt_version": "job_evaluation_plan_lightweight_v3",
        "plan_service_behavior_version": "lightweight_plan_generation_v4",
        "plan_schema_version": "5.0",
        "report_prompt_version": "screening_evaluation_lightweight_v6",
        "report_service_behavior_version": "lightweight_report_generation_v8",
        "report_schema_version": "5.0",
    }
    if execution != expected_execution:
        raise RuntimeError("I3 预检发现生产实际版本与冻结版本不一致")
    label_summary = _validate_frozen_cases()
    directions = [
        case["labels"]["overall_direction"] for case in I3_REPORT_PAIRS
    ]
    direction_distribution = {
        "high_match": directions.count("high_match"),
        "partial_match": directions.count("partial_match"),
        "low_match": directions.count("low_match"),
    }
    stability_directions = [
        I3_REPORT_PAIRS[index]["labels"]["overall_direction"]
        for index in I3_STABILITY_SAMPLE_INDICES
    ]
    stability_direction_distribution = {
        "high_match": stability_directions.count("high_match"),
        "partial_match": stability_directions.count("partial_match"),
        "low_match": stability_directions.count("low_match"),
    }
    if direction_distribution != {
        "high_match": 8,
        "partial_match": 6,
        "low_match": 6,
    }:
        raise RuntimeError("I3-R1 报告方向分布必须为 8/6/6")
    if stability_direction_distribution != {
        "high_match": 2,
        "partial_match": 2,
        "low_match": 1,
    }:
        raise RuntimeError("I3-R1 稳定性方向分布必须为 2/2/1")
    for case in I3_REPORT_PAIRS:
        if case["labels"]["overall_direction"] != "partial_match":
            continue
        sections = {item["section"] for item in case["material_findings"]}
        if (
            not {"strengths", "gaps"}.issubset(sections)
            or not case["labels"]["required_evidence_present"]
            or not case["labels"]["required_evidence_absent"]
        ):
            raise RuntimeError("I3-R1 partial case 必须同时冻结真实优势和 required 缺口")
    local_checks = await _run_local_fake_and_prompt_checks()
    checks = {
        "frozen_hashes_match": True,
        "fresh_samples": all(freshness.values()),
        "actual_versions_match": True,
        "case_counts_and_ids_legal": True,
        "confirmed_plan_snapshots_legal": True,
        "application_time_labels_legal": True,
        "material_findings_frozen": True,
        "production_prompt_builds_legal": True,
        "local_fake_adapter_dry_run_legal": True,
        "formal_i3_results_absent": True,
        "superseded_preflight_preserved": True,
        "direction_distribution_8_6_6": True,
        "partial_cases_have_two_sided_facts": True,
        "stability_distribution_2_2_1": True,
    }
    return {
        "stage": I3_RUN_ID,
        "fixture_revision": "r1",
        "mode": "zero_call_fresh_fixture_preflight",
        "lifecycle": "i3_preflight_complete",
        "quality_contract_version": I3_QUALITY_CONTRACT_VERSION,
        "generated_at": "2026-08-31T12:00:00+08:00",
        "supersedes": supersedes,
        "review_path": str(I3_REVIEW_PATH),
        "paths": {key: str(value) for key, value in paths.items()},
        "protected_i2_paths": [
            str(I2_PREFLIGHT_PATH),
            str(I2_RAW_RESULT_PATH),
            str(I2_HUMAN_AUDIT_PATH),
            str(I2_FINAL_RESULT_PATH),
        ],
        "fixture_hashes": observed_hashes,
        "fixture_summary": {
            "plan_case_count": len(I3_PLAN_JDS),
            "report_case_count": len(I3_REPORT_PAIRS),
            "stability_group_count": len(I3_STABILITY_SAMPLE_INDICES),
            "stability_runs_per_group": I3_STABILITY_RUNS_PER_SAMPLE,
            "stability_run_count": len(I3_STABILITY_SAMPLE_INDICES)
            * I3_STABILITY_RUNS_PER_SAMPLE,
            "direction_distribution": direction_distribution,
            "stability_direction_distribution": stability_direction_distribution,
            **label_summary,
        },
        "stability_sample_indices": I3_STABILITY_SAMPLE_INDICES,
        "freshness_checks": freshness,
        "execution_contract": execution,
        "preflight_checks": {**checks, "all_passed": all(checks.values())},
        "local_dry_run": local_checks,
        "frozen_fixture": {
            "plan_cases": I3_PLAN_JDS,
            "report_cases": I3_REPORT_PAIRS,
        },
        "user_review_required_before_close_06b": True,
        "pricing_gate_allowed": False,
        "real_run_allowed": False,
        "formal_i3_result_created": False,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "input_token_count": 0,
        "output_token_count": 0,
        "estimated_spend_usd": 0,
        "api_key_read": False,
        "postgresql_write_count": 0,
        "formal_result_write_count": 0,
    }


def write_preflight(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("I3 zero-call preflight 已存在，拒绝覆盖") from None


async def main() -> None:
    payload = await build_preflight_payload()
    write_preflight(I3_PREFLIGHT_PATH, payload)
    print(
        json.dumps(
            {
                "path": str(I3_PREFLIGHT_PATH),
                "stage": payload["stage"],
                "lifecycle": payload["lifecycle"],
                "all_passed": payload["preflight_checks"]["all_passed"],
                "real_model_call_count": payload["real_model_call_count"],
                "api_attempt_count": payload["api_attempt_count"],
                "estimated_spend_usd": payload["estimated_spend_usd"],
                "postgresql_write_count": payload["postgresql_write_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the zero-call I3 preflight")
    parser.parse_args()
    asyncio.run(main())
