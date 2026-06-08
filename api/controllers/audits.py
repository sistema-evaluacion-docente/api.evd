"""
Audit controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.schemas.audit import AuditCreate, AuditUpdate


class AuditsController:
    """
    Audits controller
    """

    def __init__(self, repository: AuditsRepository):
        self.repository = repository

    async def create(self, payload: AuditCreate):
        return await self.repository.create(payload)

    async def get_all(self):
        return await self.repository.get_all()

    async def get_by_id(self, audit_id: int):
        return await self.repository.get_by_id(audit_id)

    async def update(self, audit_id: int, payload: AuditUpdate):
        return await self.repository.update(audit_id, payload)

    async def delete(self, audit_id: int):
        return await self.repository.delete(audit_id)


def get_audits_controller(audits_repository=Depends(get_audits_repository)):
    """
    Get audits controller
    """

    return AuditsController(audits_repository)
