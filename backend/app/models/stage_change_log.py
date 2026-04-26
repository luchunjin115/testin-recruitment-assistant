from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from ..database import Base


class StageChangeLog(Base):
    __tablename__ = "stage_change_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    from_stage = Column(String(20), nullable=False)
    to_stage = Column(String(20), nullable=False)
    trigger_reason = Column(String(200), nullable=False)
    trigger_source = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=func.now())

    candidate = relationship("Candidate", back_populates="stage_change_logs")
