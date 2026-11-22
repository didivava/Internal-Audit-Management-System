from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.models import AuditPlan
from core.permissions import (
    ROLE_AUDIT_MANAGER,
    ROLE_CAE,
    ROLE_EXECUTIVE,
    ROLE_AUDITOR,
    AuditPlanRolePermission,
    has_any_role,
)
from core.serializers import AuditPlanSerializer
from core.services import record_audit_event


class AuditPlanViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = AuditPlanSerializer
    permission_classes = [IsAuthenticated, AuditPlanRolePermission]
    queryset = AuditPlan.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in {"update", "partial_update", "submit_for_review", "approve"}:
            queryset = queryset.select_for_update()

        user = self.request.user
        if has_any_role(user, {ROLE_CAE, ROLE_AUDIT_MANAGER}):
            return queryset

        visible_plans = Q(pk__in=[])
        if has_any_role(user, {ROLE_AUDITOR}):
            visible_plans |= Q(engagements__lead=user) | Q(engagements__members__user=user)
        if has_any_role(user, {ROLE_EXECUTIVE}):
            visible_plans |= Q(status=AuditPlan.Status.APPROVED)
        return queryset.filter(visible_plans).distinct()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @transaction.atomic
    def perform_create(self, serializer):
        plan = serializer.save(created_by=self.request.user)
        record_audit_event(
            self.request.user,
            "audit_plan.created",
            plan,
            {"fields": sorted(serializer.validated_data)},
        )

    @transaction.atomic
    def perform_update(self, serializer):
        plan = serializer.save()
        record_audit_event(
            self.request.user,
            "audit_plan.updated",
            plan,
            {"fields": sorted(serializer.validated_data)},
        )

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    @transaction.atomic
    def submit_for_review(self, request, *args, **kwargs):
        plan = self.get_object()
        if plan.status != AuditPlan.Status.DRAFT:
            return Response(
                {"detail": "Only draft plans can be submitted for review."},
                status=status.HTTP_409_CONFLICT,
            )

        plan.status = AuditPlan.Status.UNDER_REVIEW
        plan.save(update_fields=["status", "updated_at"])
        record_audit_event(request.user, "audit_plan.submitted_for_review", plan)
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"], url_path="approve")
    @transaction.atomic
    def approve(self, request, *args, **kwargs):
        plan = self.get_object()
        if plan.status != AuditPlan.Status.UNDER_REVIEW:
            return Response(
                {"detail": "Only plans under review can be approved."},
                status=status.HTTP_409_CONFLICT,
            )

        plan.status = AuditPlan.Status.APPROVED
        plan.approved_by = request.user
        plan.approved_at = timezone.now()
        plan.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        record_audit_event(request.user, "audit_plan.approved", plan)
        return Response(self.get_serializer(plan).data)
