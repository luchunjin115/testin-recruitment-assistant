from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from ..database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())

    candidate = relationship("Candidate", back_populates="activity_logs")
