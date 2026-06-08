from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate
from api.schemas.user import UserCreate


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


def get_users_controller(
    users_repository=Depends(get_users_repository),
    audits_repository=Depends(get_audits_repository),
):
    """
    Get users controller
    """

    return UsersController(users_repository, audits_repository)
