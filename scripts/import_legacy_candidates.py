from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.rebuilt.legacy_candidate_import import (  # noqa: E402
    get_target_counts,
    import_legacy_snapshot,
    load_legacy_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只读旧 SQLite，并把岗位与候选人安全复制到空的新版 PostgreSQL。",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=BACKEND_DIR / "recruit.db",
        help="旧版 SQLite 路径；始终以只读模式打开。",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正写入；省略时只做预览和安全检查。",
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    snapshot = load_legacy_snapshot(args.source)
    target_counts = await get_target_counts()
    occupied = {name: count for name, count in target_counts.items() if count}

    print("旧版数据预览（SQLite 只读）：")
    print(f"  岗位：{len(snapshot.jobs)}")
    print(f"  候选人：{len(snapshot.candidates)}")
    print(f"  教育经历：{snapshot.education_count}")
    print(f"  工作描述：{snapshot.work_experience_count}")
    print(f"  已有初筛结果：{snapshot.screening_result_count}")
    print("新版 PostgreSQL 当前业务表记录数：")
    for table_name, count in target_counts.items():
        print(f"  {table_name}：{count}")

    if not args.apply:
        print("预览完成：未写入任何数据库。确认后使用 --apply 执行一次性导入。")
        return 0
    if occupied:
        details = ", ".join(f"{name}={count}" for name, count in occupied.items())
        print(f"拒绝导入：新版业务表不是空库（{details}）。未写入任何数据。")
        return 2

    result = await import_legacy_snapshot(
        snapshot,
        backend_dir=BACKEND_DIR,
        uploads_dir=BACKEND_DIR / "uploads",
    )
    print("导入完成：")
    print(f"  岗位：{result.jobs}")
    print(f"  候选人：{result.candidates}")
    print(f"  教育经历：{result.education_records}")
    print(f"  工作经历：{result.work_experiences}")
    print(f"  初筛结果：{result.screening_results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
