import logging
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.tenant import TenantCreate, TenantOut


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user():
    return UserOut(
        id=1,
        name="Admin User",
        email="admin@helios.com",
        role=UserRole.ADMIN,
        tenant_id=None,
    )


@pytest.fixture
def team_user():
    return UserOut(
        id=77,
        name="Ops Member",
        email="ops@helios.com",
        role=UserRole.TEAM_MEMBER,
        tenant_id=None,
    )


@pytest.fixture
def valid_payload():
    return {
        "business_name": "Acme Widgets Ltd",
        "industry": "Manufacturing",
        "contact_person_name": "Jane Doe",
        "contact_email": "jane@acmewidgets.com",
        "phone_number": "+1 (555) 019-2834",
        "address_line1": "100 Industrial Parkway",
        "address_line2": "Suite 400",
        "city": "Austin",
        "state": "Texas",
        "postal_code": "78701",
        "country": "USA",
        "website_url": "https://www.acmewidgets.com",
        "tax_id": "US-987654321",
        "assigned_team_member_id": None,
        "owner_email": "owner@acmewidgets.com",
    }


def test_tenant_create_schema_validation(valid_payload):
    """Verify validation constraints on TenantCreate schema."""
    # 1. Valid payload succeeds
    tc = TenantCreate(**valid_payload)
    assert tc.business_name == "Acme Widgets Ltd"
    assert tc.phone_number == "+1 (555) 019-2834"

    # 2. Invalid phone number (letters, symbols not permitted)
    bad_phone = valid_payload.copy()
    bad_phone["phone_number"] = "123-abc-7890"
    with pytest.raises(ValidationError):
        TenantCreate(**bad_phone)

    # 3. Invalid phone number (too short < 7)
    bad_phone_short = valid_payload.copy()
    bad_phone_short["phone_number"] = "12345"
    with pytest.raises(ValidationError):
        TenantCreate(**bad_phone_short)

    # 4. Invalid website_url (missing http:// or https://)
    bad_url = valid_payload.copy()
    bad_url["website_url"] = "ftp://invalid-url.com"
    with pytest.raises(ValidationError):
        TenantCreate(**bad_url)

    # 5. Invalid email
    bad_email = valid_payload.copy()
    bad_email["contact_email"] = "not-an-email"
    with pytest.raises(ValidationError):
        TenantCreate(**bad_email)


def test_post_tenant_success_admin(client, admin_user, valid_payload):
    """Admin successfully creates a tenant; returns temporary password once."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

    mock_created_tenant = {
        "tenant_id": 105,
        "business_name": "Acme Widgets Ltd",
        "industry": "Manufacturing",
        "contact_person_name": "Jane Doe",
        "contact_email": "jane@acmewidgets.com",
        "phone_number": "+1 (555) 019-2834",
        "address_line1": "100 Industrial Parkway",
        "address_line2": "Suite 400",
        "city": "Austin",
        "state": "Texas",
        "postal_code": "78701",
        "country": "USA",
        "website_url": "https://www.acmewidgets.com",
        "tax_id": "US-987654321",
        "assigned_team_member_id": None,
        "created_by": 1,
        "is_active": True,
    }

    try:
        with patch.object(TenantRepository, "get_by_business_name", return_value=None), \
             patch.object(UserRepository, "get_by_email", return_value=None), \
             patch.object(TenantRepository, "create", return_value=mock_created_tenant) as mock_create_tenant, \
             patch.object(UserRepository, "create") as mock_create_user:

            response = client.post("/api/tenants", json=valid_payload)
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()

            assert data["tenant_id"] == 105
            assert data["business_name"] == "Acme Widgets Ltd"
            assert data["temporary_password"] is not None
            assert len(data["temporary_password"]) >= 12
            assert data["owner_email"] == "owner@acmewidgets.com"

            # Verify tenant repository called
            mock_create_tenant.assert_called_once()

            # Verify user repository created smb_owner with hashed password
            mock_create_user.assert_called_once()
            user_call_kwargs = mock_create_user.call_args.kwargs
            assert user_call_kwargs["role"] == "smb_owner"
            assert user_call_kwargs["tenant_id"] == 105
            assert user_call_kwargs["email"] == "owner@acmewidgets.com"
            assert user_call_kwargs["password_hash"].startswith("$2b$")
    finally:
        app.dependency_overrides.clear()


def test_post_tenant_auto_assign_team_member(client, team_user, valid_payload):
    """When caller is team_member and assigned_team_member_id is None, automatically assign to caller."""
    app.dependency_overrides[get_current_user] = lambda: team_user
    app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

    mock_created_tenant = {
        "tenant_id": 106,
        "business_name": "Acme Widgets Ltd",
        "industry": "Manufacturing",
        "contact_person_name": "Jane Doe",
        "contact_email": "jane@acmewidgets.com",
        "phone_number": "+1 (555) 019-2834",
        "address_line1": "100 Industrial Parkway",
        "city": "Austin",
        "state": "Texas",
        "postal_code": "78701",
        "country": "USA",
        "assigned_team_member_id": 77,
        "created_by": 77,
        "is_active": True,
    }

    try:
        with patch.object(TenantRepository, "get_by_business_name", return_value=None), \
             patch.object(UserRepository, "get_by_email", return_value=None), \
             patch.object(TenantRepository, "create", return_value=mock_created_tenant) as mock_create_tenant, \
             patch.object(TenantRepository, "create_team_assignment") as mock_assign, \
             patch.object(UserRepository, "create"):

            response = client.post("/api/tenants", json=valid_payload)
            assert response.status_code == status.HTTP_201_CREATED

            # Verify tenant repository called with assigned_team_member_id=77 (caller ID)
            assert mock_create_tenant.call_args.kwargs["assigned_team_member_id"] == 77
            # Verify team_assignments row created
            mock_assign.assert_called_once_with(user_id=77, tenant_id=106)
    finally:
        app.dependency_overrides.clear()


def test_post_tenant_duplicate_business_name_returns_409(client, admin_user, valid_payload):
    """Duplicate business_name returns 409 Conflict."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

    try:
        with patch.object(
            TenantRepository,
            "get_by_business_name",
            return_value={"tenant_id": 1, "business_name": "Acme Widgets Ltd", "is_active": True},
        ):
            response = client.post("/api/tenants", json=valid_payload)
            assert response.status_code == status.HTTP_409_CONFLICT
            assert "already exists" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_post_tenant_duplicate_owner_email_returns_409(client, admin_user, valid_payload):
    """Existing owner email in platform.users returns 409 Conflict."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

    try:
        with patch.object(TenantRepository, "get_by_business_name", return_value=None), \
             patch.object(UserRepository, "get_by_email", return_value={"user_id": 99, "email": "owner@acmewidgets.com"}):

            response = client.post("/api/tenants", json=valid_payload)
            assert response.status_code == status.HTTP_409_CONFLICT
            assert "already exists" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_post_tenant_invalid_assigned_team_member_role(client, admin_user, valid_payload):
    """If assigned_team_member_id user is not a team_member, return 400 Bad Request."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

    payload_with_bad_assignee = valid_payload.copy()
    payload_with_bad_assignee["assigned_team_member_id"] = 55

    try:
        with patch.object(TenantRepository, "get_by_business_name", return_value=None), \
             patch.object(UserRepository, "get_by_email", return_value=None), \
             patch.object(UserRepository, "get_by_id", return_value={"user_id": 55, "role": "smb_owner", "is_active": True}):

            response = client.post("/api/tenants", json=payload_with_bad_assignee)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "must be 'team_member'" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_post_tenant_never_logs_temporary_password(client, admin_user, valid_payload, caplog):
    """Verify temporary password is never logged at any log level."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

    mock_created_tenant = {
        "tenant_id": 107,
        "business_name": "Acme Widgets Ltd",
        "contact_email": "jane@acmewidgets.com",
        "created_by": 1,
        "is_active": True,
    }

    try:
        with caplog.at_level(logging.DEBUG), \
             patch.object(TenantRepository, "get_by_business_name", return_value=None), \
             patch.object(UserRepository, "get_by_email", return_value=None), \
             patch.object(TenantRepository, "create", return_value=mock_created_tenant), \
             patch.object(UserRepository, "create"):

            response = client.post("/api/tenants", json=valid_payload)
            assert response.status_code == status.HTTP_201_CREATED
            temp_pwd = response.json()["temporary_password"]

            # Ensure temporary password does NOT appear in any captured log record
            for record in caplog.records:
                assert temp_pwd not in record.message
    finally:
        app.dependency_overrides.clear()
