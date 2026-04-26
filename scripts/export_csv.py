"""候选人数据 CSV 导出脚本"""
import csv
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "backend"))
os.chdir(os.path.join(project_root, "backend"))

from app.database import SessionLocal
from app.models.candidate import Candidate

COLUMNS = [
    "id", "name", "phone", "email", "school", "degree", "major",
    "target_role", "experience_years", "skills", "source_channel",
    "stage", "interview_time", "interview_method", "interviewer",
    "offer_position", "salary_range", "expected_onboard_date",
    "onboard_date", "reject_reason", "ai_summary", "ai_tags",
    "created_at", "updated_at",
]


def export_csv(output_path: str):
    db = SessionLocal()
    try:
        candidates = db.query(Candidate).order_by(Candidate.created_at.desc()).all()
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            for c in candidates:
                writer.writerow({col: getattr(c, col, "") for col in COLUMNS})
        print(f"成功导出 {len(candidates)} 条候选人数据到 {output_path}")
    finally:
        db.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "candidates_export.csv"
    export_csv(path)
