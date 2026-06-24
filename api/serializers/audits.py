"""Serializer for AuditModel to dictionary representation."""


def audit_to_dict(audit) -> dict:
    """Convert AuditModel instance to dictionary."""

    return {
        "id": audit.id,
        "user_id": audit.user_id,
        "table_name": audit.table_name,
        "operation": audit.operation,
        "element": audit.element,
        "description": audit.description,
        "created_at": audit.created_at,
        "updated_at": audit.updated_at,
    }
