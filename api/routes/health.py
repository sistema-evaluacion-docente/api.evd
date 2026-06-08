"""
Routes for get the health status of the application
"""

from fastapi import APIRouter

from api.schemas.response import HealthResponseSchema

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthResponseSchema)
async def health():
    """
    Health check endpoint
    """

    return {"status": "ok"}
