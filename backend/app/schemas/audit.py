"""Schemas for system audit trail."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AuditLogItem(BaseModel):
    """Schema representing an immutable audit trail entry."""

    audit_id: int = Field(..., description="Unique sequential audit identifier")
    occurred_at: str = Field(..., description="Timestamp of when the audited event occurred")
    actor_user_id: Optional[int] = Field(None, description="User ID of the actor who performed the action")
    actor_name: Optional[str] = Field(None, description="Display name of the actor")
    actor_email: Optional[str] = Field(None, description="Email of the actor")
    actor_role: Optional[str] = Field(None, description="Role of the actor (admin, team_member, smb_owner, system)")
    action: str = Field(..., description="Audited action descriptor")
    tenant_id: Optional[int] = Field(None, description="Organization ID associated with the action, if applicable")
    tenant_name: Optional[str] = Field(None, description="Organization business name, if applicable")
    batch_id: Optional[str] = Field(None, description="Optional batch UUID for pipeline/upload actions")
    reason: Optional[str] = Field(None, description="Justification or description for the action")
    details_json: Optional[str] = Field(None, description="JSON string containing structured payload or diffs")

    model_config = {"from_attributes": True}

