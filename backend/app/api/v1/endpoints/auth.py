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
    summary="User Login (v1)",
)
def login_v1(
    login_data: LoginRequest,
    cursor: Cursor = Depends(get_db_cursor),
) -> TokenResponse:
    """Authenticate user credentials against platform.users and issue JWT."""
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
    summary="Get Current User Profile (v1)",
)
def read_current_user_profile_v1(
    current_user: UserOut = Depends(get_current_user),
) -> UserOut:
    """Retrieve identity and tenant context for the currently authenticated user."""
    return current_user
