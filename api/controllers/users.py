from webbrowser import get

from fastapi.param_functions import Depends

from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.user import UserCreate


class UsersController:
    def __init__(self, repository: UsersRepository):
        self.repository = repository

    async def login(self, current_user):
        try:
            user = await self.repository.get_by_uid(current_user.uid)

            if not user:
                username = current_user.email.split("@")[0]

                user = await self.repository.save(
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

            return user
        except Exception as e:
            print(e)
            return None


def get_users_controller(users_repository=Depends(get_users_repository)):
    """
    Get users controller
    """

    return UsersController(users_repository)
