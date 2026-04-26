from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class FunnelStage(BaseModel):
    stage: str
    count: int


class ChannelDistribution(BaseModel):
    channel: str
    count: int


class ScreeningStats(BaseModel):
    total_candidates: int
    screened_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    average_match_score: float
    unscreened_count: int
    pending_count: int = 0
    passed_count: int = 0
    backup_count: int = 0
    rejected_count: int = 0
    formal_candidate_count: int = 0


class FollowupSuggestionItem(BaseModel):
    candidate_id: int
    name: str
    target_role: str
    stage: str
    followup_suggestion: str
    followup_priority: str
    followup_reason: str
    followup_days_since_update: int


class FollowupSummary(BaseModel):
    high_priority_count: int
    stale_count: int
    items: List[FollowupSuggestionItem]


class RoleDistributionItem(BaseModel):
    target_role: str
    count: int
    high_priority_count: int
    followup_count: int


class RecentNewCandidateItem(BaseModel):
    candidate_id: int
    name: str
    target_role: str
    source_channel: str
    created_at: Optional[datetime] = None
    new_candidate_label: str


class DashboardStats(BaseModel):
    total_candidates: int
    new_today: int
    new_last_3_days: int
    in_pipeline: int
    offer_count: int
    pending_screening_count: int = 0
    passed_screening_count: int = 0
    backup_screening_count: int = 0
    rejected_screening_count: int = 0
    formal_candidate_count: int = 0
    funnel: List[FunnelStage]
    channels: List[ChannelDistribution]
    screening_stats: ScreeningStats
    followup_summary: FollowupSummary
    role_distribution: List[RoleDistributionItem]
    today_new_candidates: List[RecentNewCandidateItem]


class FollowUpAlert(BaseModel):
    candidate_id: int
    name: str
    target_role: str
    stage: str
    days_since_update: int


class DailySummaryResponse(BaseModel):
    date: str
    new_count: int
    stage_changes: int
    summary_text: str


class RecentLogItem(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str
    action: str
    detail: str
    created_at: Optional[datetime] = None
