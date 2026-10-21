import logging
from typing import Any
from fastapi import APIRouter, Depends, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.team_repository import TeamRepository
from app.schemas.auth import UserOut
from app.schemas.team import TeamHomeResponse

logger = logging.getLogger("helios.api.team_home")

router = APIRouter()


@router.get(
    "/home",
    response_model=TeamHomeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Team Member Home Data",
    description="Retrieve assigned organizations, pipeline status counts, open support messages, and recent activity scoped to assigned organizations.",
)
def get_team_home(
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> TeamHomeResponse:
    """
    Return operational home page overview for authenticated team members.
    Query is strictly scoped to organizations assigned to this team member in platform.team_assignments.
    """
    repo = TeamRepository(cursor)
    data = repo.get_team_home_data(current_user.id)
    return TeamHomeResponse.model_validate(data)
