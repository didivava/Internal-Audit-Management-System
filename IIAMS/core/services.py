from django.contrib.auth import get_user_model

from core.models import AuditEvent


def record_audit_event(actor, action: str, instance, details: dict | None = None) -> AuditEvent:
    if not actor.is_authenticated:
        raise ValueError("Audit events require an authenticated actor.")
    if not isinstance(details, (dict, type(None))):
        raise TypeError("Audit event details must be a JSON object.")

    user_model = get_user_model()
    if not isinstance(actor, user_model):
        raise TypeError("The audit event actor must be an application user.")

    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        object_type=instance._meta.label_lower,
        object_id=str(instance.pk),
        details=details or {},
    )
