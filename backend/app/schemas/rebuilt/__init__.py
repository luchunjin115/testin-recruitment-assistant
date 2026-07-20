from app.schemas.rebuilt.activity_log import ActivityLogCreate, ActivityLogRead
from app.schemas.rebuilt.candidate import CandidateCreate, CandidateRead, CandidateUpdate
from app.schemas.rebuilt.education import EducationCreate, EducationRead, EducationUpdate
from app.schemas.rebuilt.job import JobCreate, JobRead, JobUpdate
from app.schemas.rebuilt.project_experience import (
    ProjectExperienceCreate,
    ProjectExperienceRead,
    ProjectExperienceUpdate,
)
from app.schemas.rebuilt.report import ReportCreate, ReportRead, ReportUpdate
from app.schemas.rebuilt.resume import ResumeCreate, ResumeRead, ResumeUpdate
from app.schemas.rebuilt.screening_result import (
    ScreeningResultCreate,
    ScreeningResultRead,
    ScreeningResultUpdate,
)
from app.schemas.rebuilt.work_experience import (
    WorkExperienceCreate,
    WorkExperienceRead,
    WorkExperienceUpdate,
)

__all__ = [
    "ActivityLogCreate",
    "ActivityLogRead",
    "CandidateCreate",
    "CandidateRead",
    "CandidateUpdate",
    "EducationCreate",
    "EducationRead",
    "EducationUpdate",
    "JobCreate",
    "JobRead",
    "JobUpdate",
    "ProjectExperienceCreate",
    "ProjectExperienceRead",
    "ProjectExperienceUpdate",
    "ReportCreate",
    "ReportRead",
    "ReportUpdate",
    "ResumeCreate",
    "ResumeRead",
    "ResumeUpdate",
    "ScreeningResultCreate",
    "ScreeningResultRead",
    "ScreeningResultUpdate",
    "WorkExperienceCreate",
    "WorkExperienceRead",
    "WorkExperienceUpdate",
]
