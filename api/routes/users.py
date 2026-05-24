"""
Routes for user-related operations.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from api.middlewares.auth import get_current_user
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.user import UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/auth")
async def login_user(
    current_user=Depends(get_current_user),
    repository: UsersRepository = Depends(get_users_repository),
):
    """Endpoint to verify user login."""

    try:
        user = await repository.get_by_uid(current_user.uid)

        if not user:
            username = current_user.email.split("@")[0]

            user = await repository.save(
                UserCreate(
                    uid=current_user.uid,
                    email=current_user.email,
                    name=current_user.name,
                    username=username,
                    photo_url=current_user.picture,
                )
            )

        # create log
        # await logs_repository.create_log(
        #     level="info",
        #     source="auth",
        #     message=f"User {user.get('username', 'Unknown')} logged in successfully.",
        #     created_at=datetime.now(timezone.utc),
        # )

        return {
            "message": "Authentication successful",
            "data": user,
            "error": None,
            "status": 200,
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/{uid}")
async def get_user_by_uid(
    uid: str,
    repository: UsersRepository = Depends(get_users_repository),
):
    """Endpoint to get user information by UID."""

    try:
        user = await repository.get_by_uid(uid)
    except ValueError as e:
        return {"error": str(e), "status": 404, "timestamp": datetime.now(timezone.utc)}

    return {
        "data": user,
        "error": None,
        "status": 200,
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/")
async def get_user(
    current_user=Depends(get_current_user),
    repository: UsersRepository = Depends(get_users_repository),
):
    """Endpoint to get current user information."""

    try:
        user = await repository.get_by_uid(current_user.uid)
    except ValueError as e:
        return {"error": str(e), "status": 404, "timestamp": datetime.now(timezone.utc)}

    return {"user": user}


@router.put("/")
async def update_user(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    repository: UsersRepository = Depends(get_users_repository),
):
    """Endpoint to update user information."""

    try:
        updated_user = await repository.update(current_user.uid, payload)
    except ValueError as e:
        return {"error": str(e)}

    return {"message": "User updated successfully", "user": updated_user}
