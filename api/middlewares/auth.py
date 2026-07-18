"""
Firebase auth middleware.
"""

from typing import Sequence

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials, initialize_app

from api.config import config
from api.services.user_service import UserService
from api.dependencies.users import get_user_service
from api.schemas.user import RoleName, TokenUser

app = initialize_app(credential=credentials.Certificate(config.FIREBASE_CREDENTIALS))
security = HTTPBearer(auto_error=False)


def verify_token(token: str) -> dict:
    """
    Verify a Firebase auth token.

    Args:
        token (str): The Firebase auth token to verify.

    Returns:
        dict: The decoded token information if verification is successful.

    Raises:
        firebase_admin.auth.InvalidIdTokenError: If the token is invalid.
        firebase_admin.auth.ExpiredIdTokenError: If the token has expired.
        firebase_admin.auth.RevokedIdTokenError: If the token has been revoked.
    """

    decoded_token = auth.verify_id_token(token, clock_skew_seconds=2)

    return decoded_token


def get_user(uid: str) -> auth.UserRecord:
    """
    Retrieve a Firebase user by UID.

    Args:
        uid (str): The UID of the user to retrieve.

    Returns:
        auth.UserRecord: The user record corresponding to the given UID.

    Raises:
        firebase_admin.auth.UserNotFoundError: If no user exists for the given UID.
    """

    user_record = auth.get_user(uid)

    return user_record


def is_authenticated(token: str) -> bool:
    """
    Check if a Firebase auth token is valid.

    Args:
        token (str): The Firebase auth token to check.
    Returns:
        bool: True if the token is valid, False otherwise.
    """

    try:
        verify_token(token)
        return True
    except (
        auth.InvalidIdTokenError,
        auth.ExpiredIdTokenError,
        auth.RevokedIdTokenError,
    ):
        return False


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> TokenUser | None:
    """FastAPI dependency to get the current authenticated user."""

    token: str | None = None

    if credentials and credentials.credentials:
        token = credentials.credentials
    elif authorization:
        auth_value = authorization.strip()
        if auth_value.lower().startswith("bearer "):
            token = auth_value[7:].strip()
        else:
            token = auth_value

    if not token:
        return None

    try:
        decoded_token = verify_token(token)
    except (
        auth.InvalidIdTokenError,
        auth.ExpiredIdTokenError,
        auth.RevokedIdTokenError,
    ) as e:
        print(f"[auth] Firebase token error: {type(e).__name__}: {e}")
        return None

    return TokenUser(
        uid=decoded_token["user_id"],
        email=decoded_token["email"],
        name=(
            decoded_token["name"] if "name" in decoded_token else decoded_token["email"]
        ),
        picture=decoded_token["picture"] if "picture" in decoded_token else "",
    )


def require_roles(required_roles: Sequence[RoleName | str]):
    """Dependency factory to authorize users by roles."""

    normalized_required_roles = {
        role.value if isinstance(role, RoleName) else str(role)
        for role in required_roles
    }

    async def dependency(
        current_user: TokenUser | None = Depends(get_current_user),
        user_service: UserService = Depends(get_user_service),
    ):
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user = await user_service.get_by_uid(current_user.uid)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user_roles = set(user.get("roles", []))

        if normalized_required_roles.isdisjoint(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission to access this resource. "
                    f"Required roles: {', '.join(sorted(normalized_required_roles))}"
                ),
            )

        return user

    return dependency
