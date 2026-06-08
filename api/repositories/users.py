"""
Users repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.user import UserModel
from api.schemas.user import UserCreate, UserUpdate
from api.serializers.users import user_to_dict


class UsersRepository:
    """
    class users repository
    """

    def __init__(self, db: Session):
        self.db = db

    async def save(self, data: UserCreate):
        """
        Save user and create Options and EditorOptions if not exists
        """

        existing_user = (
            self.db.query(UserModel).filter(UserModel.uid == data.uid).first()
        )

        if existing_user:
            return existing_user

        user = UserModel(
            uid=data.uid,
            email=data.email,
            username=data.username,
            name=data.name,
            department_id=data.department_id,
            active=data.active,
            avatar_url=data.avatar_url,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user_to_dict(user)

    async def get_by_uid(self, uid: str):
        """
        Get user by uid and ensure options and editor_options are loaded
        """

        user = self.db.query(UserModel).filter(UserModel.uid == uid).first()

        if not user:
            return None

        return user_to_dict(user)

    async def get_by_username(self, username: str):
        """
        Get user by username and ensure options and editor_options are loaded
        """

        user = self.db.query(UserModel).filter(UserModel.username == username).first()

        if not user:
            return None

        return user_to_dict(user)

    async def get_by_uids(self, uids: list[str]):
        """
        Get multiple users by their uids in a single query
        """

        if not uids:
            return []

        users = self.db.query(UserModel).filter(UserModel.uid.in_(uids)).all()

        def user_to_dict_simple(user: UserModel):
            return dict(
                uid=user.uid,
                institutional_code=user.institutional_code,
                email=user.email,
                username=user.username,
                name=user.name,
                department_id=user.department_id,
                active=user.active,
                avatar_url=user.avatar_url,
            )

        users_dict: dict[str, dict] = {
            str(user.uid): user_to_dict_simple(user) for user in users
        }

        return [users_dict[uid] for uid in uids if uid in users_dict]

    async def update(self, uid: str, data: UserUpdate):
        """
        Update user by uid
        """

        user = self.db.query(UserModel).filter(UserModel.uid == uid).first()

        if not user:
            return None

        if uid != user.uid:
            raise ValueError("Only the owner can update their profile")

        # update fields
        for field, value in data.model_dump().items():
            if field == "username" and value != user.username:
                # check if username is taken
                existing_user = (
                    self.db.query(UserModel)
                    .filter(UserModel.username == value, UserModel.uid != uid)
                    .first()
                )

                if existing_user:
                    raise ValueError("Username already taken")

            if field == "institutional_code" and value != user.institutional_code:
                existing_code = (
                    self.db.query(UserModel)
                    .filter(
                        UserModel.institutional_code == value,
                        UserModel.uid != uid,
                    )
                    .first()
                )

                if existing_code:
                    raise ValueError("Institutional code already taken")

            if field == "email" and value != user.email:
                existing_email = (
                    self.db.query(UserModel)
                    .filter(UserModel.email == value, UserModel.uid != uid)
                    .first()
                )

                if existing_email:
                    raise ValueError("Email already taken")

            if value is not None and field != "uid":
                setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)

        return user_to_dict(user)


def get_users_repository(db: Annotated[Session, Depends(get_db)]):
    """
    Get users repository
    """

    return UsersRepository(db)
