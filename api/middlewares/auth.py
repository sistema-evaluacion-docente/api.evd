"""
Firebase auth middleware.
"""


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from firebase_admin import auth, initialize_app
from firebase_admin import credentials
from api.config import config
from api.schemas.user import TokenUser

app = initialize_app(credential=credentials.Certificate(
    config.FIREBASE_CREDENTIALS))

security = HTTPBearer()


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

    decoded_token = auth.verify_id_token(token)

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
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenUser:
    """
    FastAPI dependency to get the current authenticated user.

    Args:
        credentials: HTTP Bearer token credentials from the Authorization header.

    Returns:
        TokenUser: The decoded token information if authentication is successful.

    Raises:
        HTTPException: If authentication fails.
    """

    token = credentials.credentials

    if not is_authenticated(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    decoded_token = verify_token(token)

    return TokenUser(
        uid=decoded_token["user_id"],
        email=decoded_token["email"],
        name=decoded_token["name"] if "name" in decoded_token else decoded_token["email"],
        picture=decoded_token["picture"] if "picture" in decoded_token else "",
    )
