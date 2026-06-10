from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate
from api.schemas.user import UserCreate, UserRolesUpdate, UserUpdate


class UsersController:
    def __init__(
        self, repository: UsersRepository, audits_repository: AuditsRepository
    ):
        self.repository = repository
        self.audits_repository = audits_repository

    async def login(self, current_user):
        try:
            user = await self.repository.get_by_uid(current_user.uid)

            if not user:
                username = current_user.email.split("@")[0]

                user = await self.repository.save(
                    UserCreate(
                        uid=current_user.uid,
                        email=current_user.email,
                        username=username,
                        name=current_user.name,
                        department_id=None,
                        active=True,
                        avatar_url=current_user.picture,
                    )
                )

            # create log
            await self.audits_repository.create(
                data=AuditCreate(
                    user_id=current_user.uid,
                    table_name="users",
                    operation="login",
                    created_at=None,
                )
            )

            return user
        except Exception as e:
            print(e)
            return None

    async def get_all(self):
        """Endpoint to get all users."""

        try:
            users = await self.repository.get_all()
        except ValueError as e:
            print(e)
            return None

        return users

    async def get_by_uid(
        self,
        uid: str,
    ):
        """Endpoint to get user information by UID."""

        try:
            user = await self.repository.get_by_uid(uid)

            if not user:
                return None
        except ValueError as e:
            print(e)
            return None

        return user

    async def update(self, payload: UserUpdate, current_user):
        """Endpoint to update user information."""

        try:
            updated_user = await self.repository.update(current_user.uid, payload)
        except ValueError as e:
            print(e)
            return None

        return updated_user

    async def replace_roles(
        self,
        uid: str,
        payload: UserRolesUpdate,
        current_user,
    ):
        """Endpoint to replace all roles for a user."""

        requester = await self.repository.get_by_uid(current_user.uid)

        if not requester:
            return None

        requester_roles = requester.get("roles", [])

        if "ADMIN" not in requester_roles and current_user.uid != uid:
            raise ValueError(
                "You do not have permission to replace roles for this user"
            )

        try:
            updated_user = await self.repository.update(
                uid,
                UserUpdate(roles=payload.roles),
            )
        except ValueError as e:
            print(e)
            raise ValueError("Error updating roles")

        return updated_user or None


def get_users_controller(
    users_repository=Depends(get_users_repository),
    audits_repository=Depends(get_audits_repository),
):
    """
    Get users controller
    """

    return UsersController(users_repository, audits_repository)
