from pydantic import BaseModel, Field
from typing import Optional, List

class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        description="Raw meeting summary or transcript"
    )


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="Natural language question"
    )


class ProjectExtracted(BaseModel):
    name: str
    status: Optional[str] = "unknown"
    description: Optional[str] = None


class ActionItemExtracted(BaseModel):
    task: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = "medium"
    status: Optional[str] = "open"


class EscalationExtracted(BaseModel):
    issue: str
    raised_by: Optional[str] = None
    raised_to: Optional[str] = None
    priority: Optional[str] = "high"
    status: Optional[str] = "open"


class RiskExtracted(BaseModel):
    description: str
    impact: Optional[str] = None
    affected_project: Optional[str] = None
    severity: Optional[str] = "medium"


class DecisionExtracted(BaseModel):
    decision: str
    rationale: Optional[str] = None
    decided_by: Optional[str] = None


class BlockerExtracted(BaseModel):
    issue: str
    affected_team: Optional[str] = None
    dependency: Optional[str] = None


class StakeholderExtracted(BaseModel):
    name: str
    role: Optional[str] = None
    responsibilities: Optional[str] = None


class ExtractionResult(BaseModel):
    meeting_title: str
    summary: str

    projects: List[ProjectExtracted] = Field(default_factory=list)
    action_items: List[ActionItemExtracted] = Field(default_factory=list)
    escalations: List[EscalationExtracted] = Field(default_factory=list)
    risks: List[RiskExtracted] = Field(default_factory=list)
    decisions: List[DecisionExtracted] = Field(default_factory=list)
    blockers: List[BlockerExtracted] = Field(default_factory=list)
    stakeholders: List[StakeholderExtracted] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)


class Counts(BaseModel):
    projects: int = 0
    action_items: int = 0
    escalations: int = 0
    risks: int = 0
    decisions: int = 0
    blockers: int = 0


class MeetingSummary(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    analyzed_at: str

    escalation_count: int = 0
    action_item_count: int = 0
    risk_count: int = 0


class MeetingDetail(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    raw_text: str
    analyzed_at: str

    projects: List[ProjectExtracted] = Field(default_factory=list)
    action_items: List[ActionItemExtracted] = Field(default_factory=list)
    escalations: List[EscalationExtracted] = Field(default_factory=list)
    risks: List[RiskExtracted] = Field(default_factory=list)
    decisions: List[DecisionExtracted] = Field(default_factory=list)
    blockers: List[BlockerExtracted] = Field(default_factory=list)
    stakeholders: List[StakeholderExtracted] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    meeting_id: int
    title: str
    summary: str
    counts: Counts


class QueryResponse(BaseModel):
    question: str
    answer: str


class DashboardResponse(BaseModel):
    total_meetings: int
    open_escalations: int
    open_action_items: int
    high_severity_risks: int

    top_owners: List[dict] = Field(default_factory=list)
    projects_by_status: dict = Field(default_factory=dict)
    recent_escalations: List[dict] = Field(default_factory=list)