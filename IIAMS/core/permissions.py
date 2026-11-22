from django.contrib.auth.base_user import AbstractBaseUser
from rest_framework.permissions import BasePermission

ROLE_CAE = "chief_audit_executive"
ROLE_AUDIT_MANAGER = "audit_manager"
ROLE_AUDITOR = "auditor"
ROLE_CONTROL_OWNER = "control_owner"
ROLE_EXECUTIVE = "executive_read_only"

PLAN_READ_ROLES = {ROLE_CAE, ROLE_AUDIT_MANAGER, ROLE_AUDITOR, ROLE_EXECUTIVE}
PLAN_WRITE_ROLES = {ROLE_CAE, ROLE_AUDIT_MANAGER}


def has_any_role(user: AbstractBaseUser, roles: set[str]) -> bool:
    return bool(user.is_authenticated and user.groups.filter(name__in=roles).exists())


class AuditPlanRolePermission(BasePermission):
    action_roles = {
        "list": PLAN_READ_ROLES,
        "retrieve": PLAN_READ_ROLES,
        "create": PLAN_WRITE_ROLES,
        "update": PLAN_WRITE_ROLES,
        "partial_update": PLAN_WRITE_ROLES,
        "submit_for_review": PLAN_WRITE_ROLES,
        "approve": {ROLE_CAE},
    }

    def has_permission(self, request, view) -> bool:
        action = getattr(view, "action", None)
        if action is None:
            return True

        allowed_roles = self.action_roles.get(action)
        return bool(allowed_roles and has_any_role(request.user, allowed_roles))
