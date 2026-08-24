"""Program service module."""

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError
from api.repositories.programs import ProgramsRepository
from api.schemas.pagination import build_paginated_response
from api.schemas.program import ProgramCreate, ProgramFilters, ProgramUpdate
from api.serializers.programs import program_to_dict
from api.services.audit_service import AuditService


class ProgramService:
    """Service for Program operations."""

    def __init__(
        self,
        programs_repository: ProgramsRepository,
        audit_service: AuditService,
    ):
        self.programs_repository = programs_repository
        self.audit_service = audit_service

    async def get_all(
        self, filters: ProgramFilters, pagination: PaginationParams
    ) -> dict:
        """Get all programs with filters and pagination."""

        programs, total = self.programs_repository.search(filters, pagination)
        items = [program_to_dict(program) for program in programs]

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, program_id: int) -> dict | None:
        """Get a program by ID."""

        program = self.programs_repository.get(program_id)
        if not program:
            return None

        return program_to_dict(program)

    async def create(self, data: ProgramCreate, current_user: dict) -> dict:
        """Create a new program."""

        existing = self.programs_repository.get_by_code(data.code)
        if existing:
            raise ResourceAlreadyExistsError("Program", "code", data.code)

        program = self.programs_repository.create_program(data)

        await self.audit_service.log(
            action="CREATE",
            entity_name="programs",
            entity_id=program.id,
            actor_id=current_user.get("id"),
            description=f"Se creó el programa {program.name} (código: {program.code})",
        )

        return program_to_dict(program)

    async def update(
        self, program_id: int, data: ProgramUpdate, current_user: dict
    ) -> dict | None:
        """Update a program."""

        program = self.programs_repository.get(program_id)
        if not program:
            return None

        if data.code is not None and data.code != program.code:
            existing = self.programs_repository.get_by_code(data.code)
            if existing:
                raise ResourceAlreadyExistsError("Program", "code", data.code)

        # Read before the update: afterwards the model already carries the new
        # values and every comparison below would report "no changes".
        old_name = program.name
        old_code = program.code
        old_active = program.active

        updated = self.programs_repository.update_program(program, data)

        changes = []
        if data.name is not None and data.name != old_name:
            changes.append(f"name cambió de {old_name} a {data.name}")
        if data.code is not None and data.code != old_code:
            changes.append(f"code cambió de {old_code} a {data.code}")
        if data.active is not None and data.active != old_active:
            changes.append(f"active cambió de {old_active} a {data.active}")

        desc = "Se actualizó el programa"
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audit_service.log(
            action="UPDATE",
            entity_name="programs",
            entity_id=program_id,
            actor_id=current_user.get("id"),
            description=desc,
        )

        return program_to_dict(updated)

    async def delete(self, program_id: int, current_user: dict) -> dict | None:
        """Delete a program."""

        program = self.programs_repository.get(program_id)
        if not program:
            return None

        program_data = program_to_dict(program)
        self.programs_repository.delete_program(program)

        await self.audit_service.log(
            action="DELETE",
            entity_name="programs",
            entity_id=program_id,
            actor_id=current_user.get("id"),
            description=(
                f"Se eliminó el programa {program_data['name']} "
                f"(código: {program_data['code']})"
            ),
        )

        return program_data
