from difflib import SequenceMatcher
from typing import Optional

from sqlalchemy.orm import Session

from ..models.candidate import Candidate


class DedupService:
    FUZZY_THRESHOLD = 0.85

    def check_duplicate(self, db: Session, data: dict) -> Optional[int]:
        phone = data.get("phone", "")
        if phone:
            existing = db.query(Candidate).filter(
                Candidate.phone == phone,
                Candidate.is_duplicate == False,
            ).first()
            if existing:
                return existing.id

        email = data.get("email", "")
        if email:
            existing = db.query(Candidate).filter(
                Candidate.email == email,
                Candidate.is_duplicate == False,
            ).first()
            if existing:
                return existing.id

        name = data.get("name", "")
        school = data.get("school", "")
        target_role = data.get("target_role", "")
        if name and (school or target_role):
            candidates = db.query(Candidate).filter(
                Candidate.is_duplicate == False,
            ).all()
            for c in candidates:
                combo_new = f"{name}{school}{target_role}"
                combo_existing = f"{c.name}{c.school}{c.target_role}"
                ratio = SequenceMatcher(None, combo_new, combo_existing).ratio()
                if ratio >= self.FUZZY_THRESHOLD:
                    return c.id

        return None

    def mark_duplicate(self, db: Session, new_id: int, existing_id: int):
        candidate = db.query(Candidate).filter(Candidate.id == new_id).first()
        if candidate:
            candidate.is_duplicate = True
            candidate.duplicate_of_id = existing_id
            db.commit()


dedup_service = DedupService()
