"""Serializer for AuditModel to dictionary representation."""


def audit_to_dict(audit) -> dict:
    """Convert AuditModel instance to dictionary."""

    created_at = audit.created_at

    return {
        "id": audit.id,
        "user_id": audit.user_id,
        "table_name": audit.table_name,
        "operation": audit.operation,
        "created_at": created_at.isoformat() if created_at is not None else None,
    }
