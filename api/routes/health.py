"""
Routes for get the health status of the application
"""

from api.core.router import EnvelopeRouter

from api.schemas.response import HealthResponseSchema

router = EnvelopeRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthResponseSchema)
async def health():
    """
    Health check endpoint
    """

    return {"status": "ok"}
