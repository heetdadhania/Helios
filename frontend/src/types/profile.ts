export interface UserMe {
  name: string;
  email: string;
  phone: string | null;
  last_login: string | null;
  staff_id?: string | null;
  designation?: string | null;
}

export interface OrganizationProfile {
  business_name: string;
  industry: string | null;
  contact_person: string | null;
  contact_email: string | null;
  phone: string | null;
  full_address: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  pin_code: string | null;
  website: string | null;
  gstin: string | null;
  created_date: string | null;
}

export interface TeamMemberContact {
  name: string;
  email: string;
  phone: string | null;
  designation: string | null;
}

export interface AdminContact {
  name: string;
  email: string;
  phone: string | null;
}

export interface AssignedOrgSummary {
  tenant_id: number;
  business_name: string;
  industry: string | null;
  city: string | null;
  state: string | null;
  contact_person: string | null;
  owner_name: string | null;
  owner_email: string | null;
  owner_phone: string | null;
  last_data_date: string | null;
}

export interface PlatformSummary {
  active_organizations: number;
  active_owners: number;
  active_team_members: number;
}

export interface TeamMemberSummary {
  user_id: number;
  name: string;
  email: string;
  phone: string | null;
  designation: string | null;
  assigned_organizations_count: number;
}

export interface OwnerProfileData {
  role: 'smb_owner';
  me: UserMe;
  organization: OrganizationProfile | null;
  assigned_team_member: TeamMemberContact | null;
  admin_contact: AdminContact | null;
}

export interface TeamMemberProfileData {
  role: 'team_member';
  me: UserMe;
  assigned_organizations: AssignedOrgSummary[];
  admin_contact: AdminContact | null;
}

export interface AdminProfileData {
  role: 'admin';
  me: UserMe;
  platform_summary: PlatformSummary;
  team_members: TeamMemberSummary[];
}

export type ProfileData = OwnerProfileData | TeamMemberProfileData | AdminProfileData;

export interface ProfileUpdateMePayload {
  name?: string;
  phone?: string | null;
}

export interface ProfileUpdateEmailPayload {
  new_email: string;
  current_password: string;
}

export interface ProfileUpdateOrganizationPayload {
  contact_person_name?: string | null;
  phone_number?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  website_url?: string | null;
  tax_id?: string | null;
}
