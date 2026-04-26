from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import relationship

from ..database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False, unique=True, index=True)
    department = Column(String(100), default="")
    description = Column(Text, default="")
    requirements = Column(Text, default="")
    required_skills = Column(Text, default="")
    bonus_skills = Column(Text, default="")
    education_requirement = Column(String(100), default="")
    experience_requirement = Column(String(100), default="")
    job_keywords = Column(Text, default="")
    risk_keywords = Column(Text, default="")
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    candidates = relationship("Candidate", back_populates="job")
