from typing import List, Optional, Union
from pydantic import BaseModel, Field


class UserMe(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    last_login: Optional[str] = None
    staff_id: Optional[str] = None
    designation: Optional[str] = None


class OrganizationProfile(BaseModel):
    business_name: str
    industry: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    full_address: Optional[str] = None
    pin_code: Optional[str] = None
    website: Optional[str] = None
    gstin: Optional[str] = None
    created_date: Optional[str] = None


class TeamMemberContact(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    designation: Optional[str] = None


class AdminContact(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class AssignedOrgSummary(BaseModel):
    tenant_id: int
    business_name: str
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    contact_person: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    last_data_date: Optional[str] = None


class PlatformSummary(BaseModel):
    active_organizations: int = 0
    active_owners: int = 0
    active_team_members: int = 0


class TeamMemberSummary(BaseModel):
    user_id: int
    name: str
    email: str
    phone: Optional[str] = None
    designation: Optional[str] = None
    assigned_organizations_count: int = 0


class OwnerProfileResponse(BaseModel):
    role: str = "smb_owner"
    me: UserMe
    organization: Optional[OrganizationProfile] = None
    assigned_team_member: Optional[TeamMemberContact] = None
    admin_contact: Optional[AdminContact] = None


class TeamMemberProfileResponse(BaseModel):
    role: str = "team_member"
    me: UserMe
    assigned_organizations: List[AssignedOrgSummary] = Field(default_factory=list)
    admin_contact: Optional[AdminContact] = None


class AdminProfileResponse(BaseModel):
    role: str = "admin"
    me: UserMe
    platform_summary: PlatformSummary
    team_members: List[TeamMemberSummary] = Field(default_factory=list)


ProfileResponse = Union[OwnerProfileResponse, TeamMemberProfileResponse, AdminProfileResponse]
