from fastapi import APIRouter, Depends, HTTPException, status
from databricks.sql.client import Cursor
from app.core.dependencies import get_current_user, get_db_cursor
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserOut
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


@router.post(
    "/change-password",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Change User Password",
    description="Verify current password, hash new password, and clear must_change_password requirement.",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> dict:
    """
    Update password for the currently authenticated user.
    
    Verifies current password, applies new password (minimum 10 characters),
    and resets must_change_password to false.
    """
    from app.core import security
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(cursor)
    user_record = user_repo.get_by_id(current_user.id)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    stored_hash = str(user_record.get("password_hash", ""))
    if not AuthService.verify_password(payload.current_password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    new_hash = security.get_password_hash(payload.new_password)
    user_repo.update_password(
        user_id=current_user.id,
        password_hash=new_hash,
        must_change_password=False,
    )

    return {
        "success": True,
        "message": "Password changed successfully.",
    }
