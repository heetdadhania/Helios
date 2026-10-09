from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core import security
from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.team import TeamMemberCreate, TeamMemberOut


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
        must_change_password=False,
    )


@pytest.fixture
def team_user():
    return UserOut(
        id=5,
        name="Ops Member",
        email="ops@helios.com",
        role=UserRole.TEAM_MEMBER,
        tenant_id=None,
        must_change_password=False,
    )


@pytest.fixture
def valid_team_payload():
    return {
        "name": "Sarah Connor",
        "email": "sarah.connor@helios.io",
        "phone_number": "+1 (555) 234-5678",
        "role": "team_member",
        "staff_id": "EMP-1049",
        "designation": "Customer Success Lead",
        "tenant_ids": [10, 20],
    }


def test_team_member_create_schema_validation(valid_team_payload):
    """Test schema validation rules for TeamMemberCreate."""
    # 1. Valid payload succeeds
    member = TeamMemberCreate(**valid_team_payload)
    assert member.name == "Sarah Connor"
    assert member.role == UserRole.TEAM_MEMBER
    assert member.tenant_ids == [10, 20]

    # 2. Invalid role fails (smb_owner is forbidden for team members)
    invalid_role_payload = {**valid_team_payload, "role": "smb_owner"}
    with pytest.raises(ValidationError):
        TeamMemberCreate(**invalid_role_payload)

    # 3. Invalid phone format fails
    invalid_phone_payload = {**valid_team_payload, "phone_number": "abc1234"}
    with pytest.raises(ValidationError):
        TeamMemberCreate(**invalid_phone_payload)

    # 4. Short phone fails
    short_phone_payload = {**valid_team_payload, "phone_number": "123"}
    with pytest.raises(ValidationError):
        TeamMemberCreate(**short_phone_payload)


def test_admin_can_create_team_member(client, admin_user, valid_team_payload):
    """Admin successfully creates team member; receives temporary password once."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with patch.object(TeamRepository, "get_by_email", return_value=None), \
             patch.object(TeamRepository, "verify_tenants_exist", return_value=[]), \
             patch.object(
                 TeamRepository,
                 "create_user",
                 return_value={
                     "user_id": 42,
                     "name": valid_team_payload["name"],
                     "email": valid_team_payload["email"],
                     "role": valid_team_payload["role"],
                     "phone_number": valid_team_payload["phone_number"],
                     "staff_id": valid_team_payload["staff_id"],
                     "designation": valid_team_payload["designation"],
                     "must_change_password": True,
                     "is_active": True,
                 },
             ) as mock_create_user, \
             patch.object(TeamRepository, "add_assignments") as mock_add_assignments, \
             patch.object(
                 TeamRepository,
                 "get_by_id",
                 return_value={
                     "user_id": 42,
                     "name": valid_team_payload["name"],
                     "email": valid_team_payload["email"],
                     "role": valid_team_payload["role"],
                     "phone_number": valid_team_payload["phone_number"],
                     "staff_id": valid_team_payload["staff_id"],
                     "designation": valid_team_payload["designation"],
                     "must_change_password": True,
                     "is_active": True,
                     "tenant_ids": [10, 20],
                 },
             ):

            response = client.post("/api/team-members", json=valid_team_payload)
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()

            assert data["user_id"] == 42
            assert data["email"] == valid_team_payload["email"]
            assert data["must_change_password"] is True
            assert "temporary_password" in data
            assert len(data["temporary_password"]) >= 12
            assert data["tenant_ids"] == [10, 20]

            # Verify repository called with must_change_password=True
            mock_create_user.assert_called_once()
            _, kwargs = mock_create_user.call_args
            assert kwargs["must_change_password"] is True
            assert kwargs["role"] == "team_member"

            # Verify assignments added
            mock_add_assignments.assert_called_once_with(42, [10, 20])
    finally:
        app.dependency_overrides.clear()


def test_non_admin_cannot_create_team_member(client, team_user, valid_team_payload):
    """Non-admin callers receive 403 Forbidden when creating team members."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: team_user

    try:
        response = client.post("/api/team-members", json=valid_team_payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides.clear()


def test_create_team_member_duplicate_email(client, admin_user, valid_team_payload):
    """Duplicate email yields 409 Conflict."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with patch.object(
            TeamRepository,
            "get_by_email",
            return_value={"user_id": 99, "email": valid_team_payload["email"]},
        ):
            response = client.post("/api/team-members", json=valid_team_payload)
            assert response.status_code == status.HTTP_409_CONFLICT
            assert "already exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_create_team_member_nonexistent_tenants(client, admin_user, valid_team_payload):
    """Nonexistent tenant IDs yield 400 Bad Request."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with patch.object(TeamRepository, "get_by_email", return_value=None), \
             patch.object(TeamRepository, "verify_tenants_exist", return_value=[999]):
            response = client.post("/api/team-members", json=valid_team_payload)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "999" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_admin_list_team_members(client, admin_user):
    """Admin can list team members including tenant_ids."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: admin_user

    dummy_members = [
        {
            "user_id": 1,
            "name": "Admin One",
            "email": "admin@helios.com",
            "role": "admin",
            "phone_number": "1234567890",
            "staff_id": "ADM-01",
            "designation": "Principal Admin",
            "is_active": True,
            "must_change_password": False,
            "tenant_ids": [1, 2, 3],
        },
        {
            "user_id": 2,
            "name": "Team Member Two",
            "email": "member2@helios.com",
            "role": "team_member",
            "phone_number": "9876543210",
            "staff_id": "OPS-02",
            "designation": "Analyst",
            "is_active": True,
            "must_change_password": True,
            "tenant_ids": [5],
        },
    ]

    try:
        with patch.object(TeamRepository, "list_team_members", return_value=dummy_members):
            response = client.get("/api/team-members")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["tenant_ids"] == [1, 2, 3]
            assert data[1]["tenant_ids"] == [5]
            # Ensure no password field leaked
            for member in data:
                assert "password" not in member
                assert "password_hash" not in member
                assert "temporary_password" not in member
    finally:
        app.dependency_overrides.clear()


def test_replace_assignments(client, admin_user):
    """Admin can replace assigned tenant IDs for a team member."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: admin_user

    user_id = 42
    updated_user = {
        "user_id": user_id,
        "name": "Member",
        "email": "member@helios.com",
        "role": "team_member",
        "phone_number": "1234567890",
        "is_active": True,
        "tenant_ids": [30, 40],
    }

    try:
        with patch.object(TeamRepository, "get_by_id", side_effect=[{"user_id": user_id}, updated_user]), \
             patch.object(TeamRepository, "verify_tenants_exist", return_value=[]), \
             patch.object(TeamRepository, "replace_assignments") as mock_replace:

            response = client.put(f"/api/team-members/{user_id}/assignments", json={"tenant_ids": [30, 40]})
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["tenant_ids"] == [30, 40]
            mock_replace.assert_called_once_with(user_id, [30, 40])
    finally:
        app.dependency_overrides.clear()


def test_toggle_active_status(client, admin_user):
    """Admin can activate or deactivate team member."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: admin_user

    user_id = 42
    updated_user = {
        "user_id": user_id,
        "name": "Member",
        "email": "member@helios.com",
        "role": "team_member",
        "is_active": False,
        "tenant_ids": [],
    }

    try:
        with patch.object(TeamRepository, "get_by_id", side_effect=[{"user_id": user_id}, updated_user]), \
             patch.object(TeamRepository, "set_active_status") as mock_set_active:

            response = client.patch(f"/api/team-members/{user_id}/active", json={"is_active": False})
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_active"] is False
            mock_set_active.assert_called_once_with(user_id, False)
    finally:
        app.dependency_overrides.clear()


def test_change_password_success(client, team_user):
    """Authenticated user successfully changes their password."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: team_user

    current_pwd = "OldTempPassword123!"
    current_hash = security.get_password_hash(current_pwd)
    new_pwd = "NewSecurePassword2026!"

    try:
        with patch.object(
            UserRepository,
            "get_by_id",
            return_value={"user_id": team_user.id, "password_hash": current_hash},
        ), patch.object(UserRepository, "update_password") as mock_update_password:

            response = client.post(
                "/api/auth/change-password",
                json={"current_password": current_pwd, "new_password": new_pwd},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

            mock_update_password.assert_called_once()
            call_args = mock_update_password.call_args[1]
            assert call_args["user_id"] == team_user.id
            assert call_args["must_change_password"] is False
            assert security.verify_password(new_pwd, call_args["password_hash"])
    finally:
        app.dependency_overrides.clear()


def test_change_password_incorrect_current_password(client, team_user):
    """Incorrect current password returns 400 Bad Request."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: team_user

    current_hash = security.get_password_hash("CorrectPassword1!")

    try:
        with patch.object(
            UserRepository,
            "get_by_id",
            return_value={"user_id": team_user.id, "password_hash": current_hash},
        ):
            response = client.post(
                "/api/auth/change-password",
                json={"current_password": "WrongPassword!", "new_password": "NewSecurePassword2026!"},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "incorrect" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_change_password_short_new_password(client, team_user):
    """New password shorter than 10 characters returns 422 Unprocessable Entity."""
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: team_user

    try:
        response = client.post(
            "/api/auth/change-password",
            json={"current_password": "OldPassword1!", "new_password": "short"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    finally:
        app.dependency_overrides.clear()
