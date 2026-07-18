"""
Audit controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate, AuditUpdate
from api.utils.get_audit import get_audit


class AuditsController:
    """
    Audits controller
    """

    def __init__(
        self,
        repository: AuditsRepository,
        users_repository: UsersRepository,
    ):
        self.repository = repository
        self.users_repository = users_repository

    async def create(self, payload: AuditCreate):
        return await self.repository.create(payload)

    async def get_all(
        self,
        page: int = 1,
        limit: int = 10,
        table_name: str | None = None,
        operation: str | None = None,
        search: str | None = None,
    ):
        result = await self.repository.get_all(
            page=page,
            limit=limit,
            table_name=table_name,
            operation=operation,
            search=search,
        )
        items = await self._enrich_with_users(result["items"])
        result["items"] = items
        return result

    async def get_by_id(self, audit_id: int):
        audit = await self.repository.get_by_id(audit_id)

        if not audit:
            return None

        enriched = await self._enrich_with_users([audit])

        return enriched[0]

    async def update(self, audit_id: int, payload: AuditUpdate):
        return await self.repository.update(audit_id, payload)

    async def delete(self, audit_id: int):
        return await self.repository.delete(audit_id)

    async def _enrich_with_users(self, items: list[dict]) -> list[dict]:
        user_ids = [item["user_id"] for item in items if item.get("user_id")]

        if not user_ids:
            return items

        users = self.users_repository.get_by_ids(user_ids)

        users_map = {u.id: u for u in users}

        for item in items:
            user = users_map.get(item.get("user_id"))

            item["user_name"] = user.name if user else None
            item["user_avatar"] = user.avatar_url if user else None

        return items


def get_audits_controller(
    audits_repository=Depends(get_audits_repository),
    users_repository=Depends(get_users_repository),
):
    """
    Get audits controller
    """

    return AuditsController(audits_repository, users_repository)
