from typing import List
from pydantic import BaseModel, Field

class CateringPlan(BaseModel):
    plan_id: str = ""
    event_details: str = ""
    guest_count: int = 0
    budget_per_head: float = 0.0
    total_budget: float = 0.0
    menu: str = ""
    structured_menu: List[dict] = Field(default_factory=list)
    inventory_report: str = ""
    shortages_identified: List[str] = Field(default_factory=list)
    logistics_timeline: str = ""
    pricing_breakdown: str = ""
    risk_assessment: str = ""
    compliance_report: str = ""
    proposal_review: str = ""
    system_validation: str = ""