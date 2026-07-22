"""Serializer for AuditModel to dictionary representation."""

from api.models.audit import AuditModel


def audit_to_dict(audit: AuditModel) -> dict:
    """Convert AuditModel instance to dictionary with user info if available."""

    user_data = None
    if audit.user:
        user_data = {
            "id": audit.user.id,
            "name": audit.user.name,
            "email": audit.user.email,
            "avatar_url": audit.user.avatar_url,
        }

    return {
        "id": audit.id,
        "user_id": audit.user_id,
        "user": user_data,
        "table_name": audit.table_name,
        "operation": audit.operation,
        "element": audit.element,
        "description": audit.description,
        "created_at": audit.created_at,
        "updated_at": audit.updated_at,
    }
