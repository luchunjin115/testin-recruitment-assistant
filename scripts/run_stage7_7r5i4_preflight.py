from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (BACKEND_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.prompts.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
)
from app.prompts.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_BEHAVIOR_VERSION,
    SCREENING_EVALUATION_V5_PROMPT_VERSION,
)
from app.schemas.job_evaluation_plan import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
)
from app.schemas.screening_evaluation import (  # noqa: E402
    SCREENING_EVALUATION_V5_SCHEMA_VERSION,
)
from app.services.job_evaluation_plan_service import (  # noqa: E402
    JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION,
)
from stage7_7r5_quality_contract import (  # noqa: E402
    ACTIVE_RUN_ID,
    I3_RUN_ID,
    I4_PREFLIGHT_PATH,
    I4_QUALITY_CONTRACT_VERSION,
    I4_REVIEW_PATH,
    I4_RUN_ID,
    assert_result_write_allowed,
    i4_quality_contract,
    result_paths,
    validate_i4_fixture,
    validate_result_lifecycle,
)
from tests.fixtures.v5_i4_quality_samples import (  # noqa: E402
    I4_PLAN_JDS,
    I4_REPORT_PAIRS,
    I4_STABILITY_RUNS_PER_SAMPLE,
    I4_STABILITY_SAMPLE_INDICES,
    compute_i4_fixture_hashes,
)


I4_FROZEN_HASHES = {
    "fixture": "7193d6885e5147a45d1061a35d9ef34c3aa3e64f2a74b843e908da646bd2ec77",
    "plan_samples": "a201472ddf0dc558caeeb85895b6defcdba2e312182349a977e3eb909f61229e",
    "plan_labels": "e5efc128fbc101fd56d6b2ea228cbe91af5ab5ca3838da5cff43fa31851fbc32",
    "report_samples": "e8695f01f112b918dcb0eba278f81637568d2ee6d0165f74230a079b8f8fd2e9",
    "report_labels": "de76c7dadfde33888b697025fdc61918a635dd367b99b4a55107a8c0ad21f4d3",
    "stability_selection": "59c2adb3ce95c083124c3a0eebb931d5175bb5653c37ea829a14e9b9af34a76d",
}


def _actual_execution_contract() -> dict[str, str]:
    return {
        "plan_prompt_version": JOB_EVALUATION_PLAN_V5_PROMPT_VERSION,
        "plan_service_behavior_version": (
            JOB_EVALUATION_PLAN_V5_BREAKING_CONTRACT_VERSION
        ),
        "plan_schema_version": JOB_EVALUATION_PLAN_V5_SCHEMA_VERSION,
        "report_prompt_version": SCREENING_EVALUATION_V5_PROMPT_VERSION,
        "report_service_behavior_version": (
            SCREENING_EVALUATION_V5_BEHAVIOR_VERSION
        ),
        "report_schema_version": SCREENING_EVALUATION_V5_SCHEMA_VERSION,
    }


def _direction_distribution(indices: list[int] | None = None) -> dict[str, int]:
    cases = (
        I4_REPORT_PAIRS
        if indices is None
        else [I4_REPORT_PAIRS[index] for index in indices]
    )
    directions = [case["labels"]["overall_direction"] for case in cases]
    return {
        "high_match": directions.count("high_match"),
        "partial_match": directions.count("partial_match"),
        "low_match": directions.count("low_match"),
    }


def build_fixture_review() -> str:
    lines = [
        "# Stage 7 I4 fixture review",
        "",
        "## 这张复核单解决什么问题",
        "",
        "本文件只用于在真实调用前人工检查 I4 的新考卷和标签。简历中的任职起止日期可以保留，作为原始经历的定位信息；AI 不得计算工作年限，不得判断年限是否达标，也不得据此评分。",
        "",
        "- 纯工作年限要求不进入 required 分母。",
        "- 混合要求保留非年限能力，例如“3 年以上 Java 经验”只保留 Java。",
        "- 方向稳定和分差继续记录，但只作为诊断；15/15 合法输出、极端翻转、敏感评分和非年限严重事实错误仍是硬门槛。",
        "- CLOSE-06R2-B 尚未开始；本批不查价格、不读取 Key、不调用真实模型。",
        "",
        "## 计划样本",
        "",
        "| Case | 岗位 | required 标签 | 排除的纯年限要求 | 混合要求保留能力 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in I4_PLAN_JDS:
        labels = case["labels"]
        mixed = labels["mixed_requirement_capability_items"][0]
        lines.append(
            "| {case_id} | {title} | {required} | {excluded} | {capability} |".format(
                case_id=case["case_id"],
                title=case["title"],
                required="、".join(labels["key_required_items"]),
                excluded="、".join(
                    labels["excluded_pure_work_duration_requirements"]
                ),
                capability=mixed["capability_label"],
            )
        )
    lines.extend(
        [
            "",
            "## 报告样本",
            "",
            "| Case | 计划来源 | 人工方向 | required 有证据 | required 缺证据 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for case in I4_REPORT_PAIRS:
        labels = case["labels"]
        lines.append(
            "| {case_id} | {plan_case_id} confirmed snapshot | {direction} | {present} | {absent} |".format(
                case_id=case["case_id"],
                plan_case_id=case["plan_case_id"],
                direction=labels["overall_direction"],
                present="、".join(labels["required_evidence_present"]) or "无",
                absent="、".join(labels["required_evidence_absent"]) or "无",
            )
        )
    stability_ids = [
        I4_REPORT_PAIRS[index]["case_id"]
        for index in I4_STABILITY_SAMPLE_INDICES
    ]
    lines.extend(
        [
            "",
            "## 稳定性抽样",
            "",
            f"- 样本：{', '.join(stability_ids)}。",
            f"- 每个样本重复 {I4_STABILITY_RUNS_PER_SAMPLE} 次，共 15 次。",
            "- 人工方向分布：2 high / 2 partial / 1 low。",
            "",
            "## 停止点",
            "",
            "CLOSE-06R2-A 完成后停止。只有用户复核这张清单并另行确认，才可进入 CLOSE-06R2-B。",
            "",
        ]
    )
    return "\n".join(lines)


def build_preflight_payload() -> dict[str, Any]:
    validate_result_lifecycle(
        run_id=I4_RUN_ID,
        expected_state="i4_not_started",
    )
    paths = {key: Path(value) for key, value in result_paths(I4_RUN_ID).items()}
    if any(paths[key].exists() for key in ("raw", "human_audit", "final")):
        raise RuntimeError("I4 raw/human/final 必须在 CLOSE-06R2-A 保持不存在")
    if I4_REVIEW_PATH.exists() or paths["preflight"].exists():
        raise RuntimeError("I4 preflight 或复核单已经存在，拒绝覆盖")

    observed_hashes = compute_i4_fixture_hashes()
    if observed_hashes != I4_FROZEN_HASHES:
        raise RuntimeError("I4 样本或标签指纹与冻结值不一致")
    fixture_summary = validate_i4_fixture()
    fixture_summary.pop("formal_i4_evidence_created", None)

    execution = _actual_execution_contract()
    expected_execution = {
        "plan_prompt_version": "job_evaluation_plan_lightweight_v4",
        "plan_service_behavior_version": "lightweight_plan_generation_v5",
        "plan_schema_version": "5.0",
        "report_prompt_version": "screening_evaluation_lightweight_v7",
        "report_service_behavior_version": "lightweight_report_generation_v9",
        "report_schema_version": "5.0",
    }
    if execution != expected_execution:
        raise RuntimeError("I4 预检发现生产版本与冻结执行合同不一致")

    direction_distribution = _direction_distribution()
    stability_distribution = _direction_distribution(I4_STABILITY_SAMPLE_INDICES)
    if direction_distribution != {
        "high_match": 8,
        "partial_match": 6,
        "low_match": 6,
    }:
        raise RuntimeError("I4 报告方向分布必须为 8/6/6")
    if stability_distribution != {
        "high_match": 2,
        "partial_match": 2,
        "low_match": 1,
    }:
        raise RuntimeError("I4 稳定性方向分布必须为 2/2/1")

    i2_state = validate_result_lifecycle(run_id=ACTIVE_RUN_ID)["state"]
    i3_state = validate_result_lifecycle(run_id=I3_RUN_ID)["state"]
    if i2_state != "i2_final_complete" or i3_state != "i3_raw_complete":
        raise RuntimeError("I2 或 I3-R1 历史生命周期发生漂移")

    checks = {
        "quality_contract_v3_bound": (
            i4_quality_contract()["version"] == I4_QUALITY_CONTRACT_VERSION
        ),
        "frozen_hashes_match": True,
        "actual_versions_match": True,
        "fresh_case_counts_and_ids_legal": True,
        "confirmed_plan_snapshots_legal": True,
        "pure_work_duration_excluded_from_required_denominator": (
            fixture_summary["pure_work_duration_excluded_count"] == 10
        ),
        "mixed_non_duration_capability_retained": (
            fixture_summary["mixed_capability_retained_count"] == 10
        ),
        "time_calculation_and_duration_threshold_labels_absent": True,
        "resume_dates_allowed_as_source_evidence": True,
        "direction_distribution_8_6_6": True,
        "stability_distribution_2_2_1": True,
        "stability_direction_and_spread_diagnostic_only": True,
        "historical_lifecycles_unchanged": True,
        "formal_i4_raw_human_final_absent": True,
        "external_activity_zero": True,
    }
    if not all(checks.values()):
        raise RuntimeError("I4 zero-call preflight 存在未通过检查")

    fixture_summary.update(
        {
            "stability_run_count": (
                len(I4_STABILITY_SAMPLE_INDICES)
                * I4_STABILITY_RUNS_PER_SAMPLE
            ),
            "stability_direction_distribution": stability_distribution,
        }
    )
    return {
        "stage": I4_RUN_ID,
        "mode": "zero_call_fresh_fixture_preflight",
        "lifecycle": "i4_preflight_complete",
        "quality_contract_version": I4_QUALITY_CONTRACT_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "review_path": str(I4_REVIEW_PATH),
        "paths": {key: str(value) for key, value in paths.items()},
        "fixture_hashes": observed_hashes,
        "fixture_summary": fixture_summary,
        "execution_contract": execution,
        "historical_lifecycles": {
            ACTIVE_RUN_ID: i2_state,
            I3_RUN_ID: i3_state,
        },
        "historical_recalculation_allowed": False,
        "preflight_checks": {**checks, "all_passed": True},
        "frozen_fixture": {
            "plan_cases": I4_PLAN_JDS,
            "report_cases": I4_REPORT_PAIRS,
            "stability_sample_indices": I4_STABILITY_SAMPLE_INDICES,
            "stability_runs_per_sample": I4_STABILITY_RUNS_PER_SAMPLE,
        },
        "user_review_required_before_close_06r2_b": True,
        "pricing_gate_allowed": False,
        "real_run_allowed": False,
        "formal_i4_preflight_write_count": 1,
        "formal_raw_human_final_write_count": 0,
        "real_model_call_count": 0,
        "api_attempt_count": 0,
        "input_token_count": 0,
        "output_token_count": 0,
        "estimated_spend_usd": 0,
        "api_key_read": False,
        "postgresql_write_count": 0,
        "pricing_lookup_count": 0,
    }


def write_preflight_bundle(
    *,
    preflight_path: Path,
    review_path: Path,
    payload: dict[str, Any],
    review: str,
) -> None:
    if preflight_path.exists() or review_path.exists():
        raise RuntimeError("I4 preflight 或复核单已经存在，拒绝覆盖")
    preflight_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with review_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(review)
        with preflight_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        raise RuntimeError("I4 preflight 或复核单已经存在，拒绝覆盖") from None


def main() -> None:
    payload = build_preflight_payload()
    assert_result_write_allowed(
        run_id=I4_RUN_ID,
        target=I4_PREFLIGHT_PATH,
        expected_state="i4_not_started",
    )
    write_preflight_bundle(
        preflight_path=I4_PREFLIGHT_PATH,
        review_path=I4_REVIEW_PATH,
        payload=payload,
        review=build_fixture_review(),
    )
    lifecycle = validate_result_lifecycle(
        run_id=I4_RUN_ID,
        expected_state="i4_preflight_complete",
    )
    print(
        json.dumps(
            {
                "path": str(I4_PREFLIGHT_PATH),
                "review_path": str(I4_REVIEW_PATH),
                "stage": payload["stage"],
                "lifecycle": lifecycle["state"],
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
    parser = argparse.ArgumentParser(description="Run the zero-call I4 preflight")
    parser.parse_args()
    main()
