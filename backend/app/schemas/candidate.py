from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

VALID_STAGES = [
    "新投递", "待筛选", "待约面", "已约面", "面试中", "复试",
    "offer", "入职", "淘汰",
]

VALID_CHANNELS = [
    "HR手动录入", "企业微信群", "内推", "Boss直聘", "拉勾", "猎聘", "其他",
    "在线投递", "表单录入", "简历上传",
]

VALID_DEGREES = ["大专", "本科", "硕士", "博士", "其他"]

VALID_SCREENING_STATUSES = ["pending", "passed", "backup", "rejected"]


class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    email: Optional[str] = ""
    school: Optional[str] = ""
    degree: Optional[str] = ""
    major: Optional[str] = ""
    job_id: Optional[int] = None
    target_role: Optional[str] = ""
    experience_years: Optional[float] = 0
    experience_desc: Optional[str] = ""
    skills: Optional[List[str]] = []
    self_intro: Optional[str] = ""
    source_channel: Optional[str] = "HR手动录入"
    hr_notes: Optional[str] = ""


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    job_id: Optional[int] = None
    target_role: Optional[str] = None
    experience_years: Optional[float] = None
    experience_desc: Optional[str] = None
    skills: Optional[List[str]] = None
    self_intro: Optional[str] = None
    source_channel: Optional[str] = None
    hr_notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    interview_time: Optional[datetime] = None
    interview_method: Optional[str] = None
    interviewer: Optional[str] = None
    interview_note: Optional[str] = None
    interview_feedback_text: Optional[str] = None
    interview_round: Optional[str] = None
    feedback_time: Optional[datetime] = None
    recheck_note: Optional[str] = None
    second_interview_time: Optional[datetime] = None
    second_interviewer: Optional[str] = None
    offer_position: Optional[str] = None
    salary_range: Optional[str] = None
    expected_onboard_date: Optional[date] = None
    offer_note: Optional[str] = None
    onboard_date: Optional[date] = None
    onboard_note: Optional[str] = None
    reject_reason: Optional[str] = None
    reject_note: Optional[str] = None


class StageUpdate(BaseModel):
    stage: str

    def validate_stage(self):
        if self.stage not in VALID_STAGES:
            raise ValueError(f"无效阶段: {self.stage}，有效值: {VALID_STAGES}")
        return self


class CandidateRead(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    school: str
    degree: str
    major: str
    job_id: Optional[int] = None
    target_role: str
    experience_years: float
    experience_desc: str
    skills: List[str]
    self_intro: str
    resume_path: str
    resume_filename: Optional[str] = ""
    resume_file_type: Optional[str] = ""
    resume_file_size: Optional[int] = None
    resume_url: Optional[str] = ""
    resume_uploaded_at: Optional[datetime] = None
    source_channel: str
    new_candidate_label: Optional[str] = ""
    is_today_new: Optional[bool] = False
    is_recent_3_days_new: Optional[bool] = False
    stage: str
    screening_status: str = "pending"
    interview_time: Optional[datetime] = None
    interview_method: Optional[str] = ""
    interviewer: Optional[str] = ""
    interview_note: Optional[str] = ""
    interview_feedback_text: Optional[str] = ""
    interview_round: Optional[str] = ""
    feedback_time: Optional[datetime] = None
    interview_ai_technical_summary: Optional[str] = ""
    interview_ai_communication_summary: Optional[str] = ""
    interview_ai_job_match: Optional[str] = ""
    interview_ai_risk_points: List[str] = []
    interview_ai_recommendation: Optional[str] = ""
    interview_ai_next_step: Optional[str] = ""
    interview_ai_generated_at: Optional[datetime] = None
    recheck_note: Optional[str] = ""
    second_interview_time: Optional[datetime] = None
    second_interviewer: Optional[str] = ""
    offer_position: Optional[str] = ""
    salary_range: Optional[str] = ""
    expected_onboard_date: Optional[date] = None
    offer_note: Optional[str] = ""
    onboard_date: Optional[date] = None
    onboard_note: Optional[str] = ""
    reject_reason: Optional[str] = ""
    reject_note: Optional[str] = ""
    stage_source: Optional[str] = None
    ai_summary: str
    ai_tags: List[str]
    match_score: Optional[int] = None
    priority_level: Optional[str] = ""
    screening_result: Optional[str] = ""
    screening_reason: Optional[str] = ""
    risk_flags: List[str] = []
    screening_updated_at: Optional[datetime] = None
    followup_suggestion: Optional[str] = ""
    followup_priority: Optional[str] = ""
    followup_reason: Optional[str] = ""
    followup_days_since_update: Optional[int] = 0
    is_overdue: Optional[bool] = False
    overdue_days: Optional[int] = 0
    overdue_reason: Optional[str] = ""
    last_action_at: Optional[datetime] = None
    hr_notes: str
    follow_up_date: Optional[date] = None
    is_duplicate: bool
    duplicate_of_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ActivityLogRead(BaseModel):
    id: int
    candidate_id: int
    action: str
    detail: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateDetailRead(CandidateRead):
    activity_logs: List[ActivityLogRead] = []


class ChatRequest(BaseModel):
    messages: List[Dict]


class ChatResponse(BaseModel):
    reply: str


class StageChangeLogRead(BaseModel):
    id: int
    candidate_id: int
    from_stage: str
    to_stage: str
    trigger_reason: str
    trigger_source: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HRActionRequest(BaseModel):
    interview_time: Optional[datetime] = None
    interview_method: Optional[str] = ""
    interviewer: Optional[str] = ""
    interview_note: Optional[str] = ""
    recheck_note: Optional[str] = ""
    second_interview_time: Optional[datetime] = None
    second_interviewer: Optional[str] = ""
    offer_position: Optional[str] = ""
    salary_range: Optional[str] = ""
    expected_onboard_date: Optional[date] = None
    offer_note: Optional[str] = ""
    onboard_date: Optional[date] = None
    onboard_note: Optional[str] = ""
    reject_reason: Optional[str] = ""
    reject_note: Optional[str] = ""
    reason: Optional[str] = ""


class InterviewSummaryRequest(BaseModel):
    interview_feedback_text: str = Field(..., min_length=1)
    interviewer: Optional[str] = ""
    interview_round: Optional[str] = ""
    feedback_time: Optional[datetime] = None


class InterviewSummaryResponse(BaseModel):
    interview_feedback_text: str
    interviewer: Optional[str] = ""
    interview_round: Optional[str] = ""
    feedback_time: Optional[datetime] = None
    technical_summary: str
    communication_summary: str
    job_match: str
    risk_points: List[str]
    recommendation: str
    next_step: str
    generated_at: Optional[datetime] = None


class BatchStatusRequest(BaseModel):
    candidate_ids: List[int]
    target_stage: str
    reason: str = "批量修改阶段"
    source: str = "hr_action"


class BatchIdsRequest(BaseModel):
    candidate_ids: List[int]


class BatchOperationItem(BaseModel):
    candidate_id: int
    name: str
    success: bool
    message: str
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None


class BatchOperationResponse(BaseModel):
    success_count: int
    failed_count: int
    items: List[BatchOperationItem]


VALID_HR_ACTIONS = [
    "pass_screening",
    "set_interview_time",
    "advance_to_retest",
    "send_offer",
    "mark_onboarded",
    "mark_eliminated",
]


class ScreeningResultRead(BaseModel):
    id: int
    name: str
    school: str
    degree: str
    major: str
    target_role: str
    skills: List[str]
    stage: str
    screening_status: str = "pending"
    match_score: Optional[int] = None
    priority_level: Optional[str] = ""
    screening_result: Optional[str] = ""
    screening_reason: Optional[str] = ""
    risk_flags: List[str] = []
    screening_updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    job_match_summary: Optional[str] = ""
    job_requirement_profile: Optional[Dict] = {}


class ScreeningRunResponse(BaseModel):
    processed_count: int
    items: List[ScreeningResultRead]
