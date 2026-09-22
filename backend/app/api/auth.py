from fastapi import APIRouter, Depends, status
from databricks.sql.client import Cursor
from app.core.dependencies import get_current_user, get_db_cursor
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user credentials against platform.users and return a signed JWT bearer token.",
)
def login(
    login_data: LoginRequest,
    cursor: Cursor = Depends(get_db_cursor),
) -> TokenResponse:
    """
    Authenticate against platform.users table.
    
    Returns JWT access token with user details: id, name, email, role, tenant_id.
    """
    authenticated_user = AuthService.authenticate_user(
        cursor=cursor,
        email=login_data.email,
        password=login_data.password,
    )
    return AuthService.build_token_response(authenticated_user)


@router.get(
    "/me",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Retrieve profile and tenant boundary details for the currently authenticated user.",
)
def get_current_user_profile(
    current_user: UserOut = Depends(get_current_user),
) -> UserOut:
    """Return the active user profile extracted from the JWT token and platform.users."""
    return current_user
