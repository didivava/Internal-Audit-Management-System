from rest_framework import serializers

from core.models import AuditPlan


class AuditPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditPlan
        fields = (
            "id",
            "name",
            "fiscal_year",
            "period_start",
            "period_end",
            "status",
            "created_by",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "created_by",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        start = attrs.get("period_start", getattr(self.instance, "period_start", None))
        end = attrs.get("period_end", getattr(self.instance, "period_end", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"period_end": "The plan end date must follow its start date."}
            )
        return attrs
