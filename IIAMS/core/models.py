import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q


class TimestampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class RiskRating(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class AuditableEntity(TimestampedModel):
    class Category(models.TextChoices):
        FINANCE = "finance", "Finance"
        TECHNOLOGY = "technology", "Technology"
        OPERATIONS = "operations", "Operations"
        COMPLIANCE = "compliance", "Compliance"
        PEOPLE = "people", "People"
        STRATEGY = "strategy", "Strategy"
        OTHER = "other", "Other"

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=24, choices=Category.choices)
    business_unit = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_auditable_entities",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Risk(TimestampedModel):
    entity = models.ForeignKey(AuditableEntity, on_delete=models.PROTECT, related_name="risks")
    code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_audit_risks",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["entity", "is_active"], name="risk_entity_active_idx")]

    def __str__(self) -> str:
        return f"{self.code} — {self.title}"


class RiskAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    risk = models.ForeignKey(Risk, on_delete=models.PROTECT, related_name="assessments")
    likelihood = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    impact = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    residual_likelihood = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    residual_impact = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    rationale = models.TextField(blank=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="risk_assessments",
    )
    assessed_at = models.DateTimeField()
    next_review_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-assessed_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(likelihood__gte=1, likelihood__lte=5),
                name="risk_assessment_likelihood_1_to_5",
            ),
            models.CheckConstraint(
                condition=Q(impact__gte=1, impact__lte=5),
                name="risk_assessment_impact_1_to_5",
            ),
            models.CheckConstraint(
                condition=(
                    Q(residual_likelihood__isnull=True, residual_impact__isnull=True)
                    | Q(
                        residual_likelihood__gte=1,
                        residual_likelihood__lte=5,
                        residual_impact__gte=1,
                        residual_impact__lte=5,
                    )
                ),
                name="risk_assessment_residual_pair",
            ),
        ]

    @property
    def inherent_score(self) -> int:
        return self.likelihood * self.impact

    @property
    def inherent_rating(self) -> RiskRating:
        score = self.inherent_score
        if score >= 20:
            return RiskRating.CRITICAL
        if score >= 12:
            return RiskRating.HIGH
        if score >= 6:
            return RiskRating.MEDIUM
        return RiskRating.LOW

    @property
    def residual_score(self) -> int | None:
        if self.residual_likelihood is None or self.residual_impact is None:
            return None
        return self.residual_likelihood * self.residual_impact

    def clean(self) -> None:
        super().clean()
        if (self.residual_likelihood is None) != (self.residual_impact is None):
            raise ValidationError(
                {"residual_impact": "Provide both residual likelihood and residual impact."}
            )


class AuditPlan(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=160)
    fiscal_year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(9999)]
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_audit_plans",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_audit_plans",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fiscal_year", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["fiscal_year", "name"], name="audit_plan_year_name_unique"
            ),
            models.CheckConstraint(
                condition=Q(period_end__gte=F("period_start")),
                name="audit_plan_period_order",
            ),
            models.CheckConstraint(
                condition=(
                    Q(approved_by__isnull=True, approved_at__isnull=True)
                    | Q(approved_by__isnull=False, approved_at__isnull=False)
                ),
                name="audit_plan_approval_pair",
            ),
            models.CheckConstraint(
                condition=~Q(status="approved")
                | Q(approved_by__isnull=False, approved_at__isnull=False),
                name="approved_audit_plan_has_approver",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.period_end and self.period_start and self.period_end < self.period_start:
            raise ValidationError({"period_end": "The plan end date must follow its start date."})
        if self.status == self.Status.APPROVED and not (self.approved_by_id and self.approved_at):
            raise ValidationError("An approved plan must record its approver and approval time.")

    def __str__(self) -> str:
        return f"{self.name} ({self.fiscal_year})"


class Engagement(TimestampedModel):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        SCHEDULED = "scheduled", "Scheduled"
        FIELDWORK = "fieldwork", "Fieldwork"
        REPORTING = "reporting", "Reporting"
        COMPLETE = "complete", "Complete"
        CANCELLED = "cancelled", "Cancelled"

    plan = models.ForeignKey(AuditPlan, on_delete=models.PROTECT, related_name="engagements")
    code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=200)
    objectives = models.TextField()
    scope = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)
    risk_rating = models.CharField(max_length=12, choices=RiskRating.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    progress = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="led_engagements",
    )
    scope_entities = models.ManyToManyField(AuditableEntity, related_name="engagements", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_engagements",
    )

    class Meta:
        ordering = ["-start_date", "code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="engagement_date_order",
            ),
            models.CheckConstraint(condition=Q(progress__lte=100), name="engagement_progress_max_100"),
            models.CheckConstraint(
                condition=~Q(status="complete") | Q(progress=100),
                name="complete_engagement_has_full_progress",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "The engagement end date must follow its start date."})
        if self.status == self.Status.COMPLETE and self.progress != 100:
            raise ValidationError({"progress": "A completed engagement must be at 100% progress."})

    def __str__(self) -> str:
        return f"{self.code} — {self.title}"


class EngagementMember(models.Model):
    class Role(models.TextChoices):
        AUDITOR = "auditor", "Auditor"
        REVIEWER = "reviewer", "Reviewer"
        OBSERVER = "observer", "Observer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engagement = models.ForeignKey(
        Engagement, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="engagement_memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.AUDITOR)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["engagement", "user"], name="engagement_member_unique"
            )
        ]


class WorkProgram(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETE = "complete", "Complete"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engagement = models.ForeignKey(
        Engagement, on_delete=models.PROTECT, related_name="work_programs"
    )
    reference = models.CharField(max_length=32)
    title = models.CharField(max_length=200)
    objective = models.TextField()
    sequence = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NOT_STARTED)

    class Meta:
        ordering = ["sequence", "reference"]
        constraints = [
            models.UniqueConstraint(
                fields=["engagement", "reference"], name="work_program_reference_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.title}"


class Workpaper(TimestampedModel):
    engagement = models.ForeignKey(Engagement, on_delete=models.PROTECT, related_name="workpapers")
    work_program = models.ForeignKey(
        WorkProgram,
        on_delete=models.PROTECT,
        related_name="workpapers",
        null=True,
        blank=True,
    )
    reference = models.CharField(max_length=32)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    storage_key = models.CharField(max_length=512, unique=True)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=127)
    size_bytes = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    sha256 = models.CharField(
        max_length=64,
        validators=[RegexValidator(r"\A[a-fA-F0-9]{64}\Z", "Enter a valid SHA-256 digest.")],
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_workpapers",
    )

    class Meta:
        ordering = ["engagement", "reference"]
        constraints = [
            models.UniqueConstraint(
                fields=["engagement", "reference"], name="workpaper_reference_unique"
            ),
            models.CheckConstraint(condition=Q(size_bytes__gt=0), name="workpaper_size_positive"),
        ]


class WorkpaperReview(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        CHANGES_REQUESTED = "changes_requested", "Changes requested"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workpaper = models.ForeignKey(
        Workpaper, on_delete=models.PROTECT, related_name="reviews"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="workpaper_reviews"
    )
    decision = models.CharField(max_length=24, choices=Decision.choices)
    comments = models.TextField(blank=True)
    reviewed_at = models.DateTimeField()

    class Meta:
        ordering = ["-reviewed_at"]


class Finding(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        MANAGEMENT_RESPONSE = "management_response", "Management response"
        ACCEPTED = "accepted", "Accepted"
        IN_PROGRESS = "in_progress", "In progress"
        READY_FOR_VALIDATION = "ready_for_validation", "Ready for validation"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engagement = models.ForeignKey(Engagement, on_delete=models.PROTECT, related_name="findings")
    code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=240)
    severity = models.CharField(max_length=12, choices=Severity.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    criteria = models.TextField(blank=True)
    condition = models.TextField()
    cause = models.TextField(blank=True)
    effect = models.TextField(blank=True)
    recommendation = models.TextField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_findings",
    )
    identified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="identified_findings",
    )
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    workpapers = models.ManyToManyField(Workpaper, related_name="findings", blank=True)

    class Meta:
        ordering = ["-created_at", "code"]
        indexes = [
            models.Index(fields=["engagement", "status"], name="finding_engagement_status_idx"),
            models.Index(fields=["severity", "status"], name="finding_severity_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.title}"


class ManagementResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(Finding, on_delete=models.PROTECT, related_name="responses")
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="management_responses"
    )
    response = models.TextField()
    proposed_completion_date = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField()

    class Meta:
        ordering = ["-submitted_at"]


class ActionPlan(TimestampedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        READY_FOR_VALIDATION = "ready_for_validation", "Ready for validation"
        COMPLETE = "complete", "Complete"
        ACCEPTED_RISK = "accepted_risk", "Accepted risk"

    finding = models.ForeignKey(Finding, on_delete=models.PROTECT, related_name="actions")
    reference = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=240)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_action_plans"
    )
    due_date = models.DateField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NOT_STARTED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_action_plans"
    )

    class Meta:
        ordering = ["due_date", "reference"]
        indexes = [models.Index(fields=["status", "due_date"], name="action_status_due_idx")]


class ActionUpdate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.ForeignKey(ActionPlan, on_delete=models.PROTECT, related_name="updates")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="action_updates"
    )
    update = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ActionValidation(models.Model):
    class Decision(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.ForeignKey(ActionPlan, on_delete=models.PROTECT, related_name="validations")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="action_validations"
    )
    decision = models.CharField(max_length=12, choices=Decision.choices)
    notes = models.TextField()
    validated_at = models.DateTimeField()
    workpapers = models.ManyToManyField(Workpaper, related_name="action_validations", blank=True)

    class Meta:
        ordering = ["-validated_at"]

    def clean(self) -> None:
        super().clean()
        if self.decision == self.Decision.REJECTED and not self.notes.strip():
            raise ValidationError({"notes": "Explain why the action was not accepted."})


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit events cannot be updated.")

    def delete(self):
        raise ValidationError("Audit events cannot be deleted.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Audit events cannot be updated.")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Create audit events individually so their immutability is enforced.")


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="audit_events"
    )
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    details = models.JSONField(default=dict, blank=True)
    correlation_id = models.UUIDField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(
                fields=["object_type", "object_id", "occurred_at"],
                name="audit_event_object_time_idx",
            ),
            models.Index(fields=["actor", "occurred_at"], name="audit_event_actor_time_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit events are append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only and cannot be deleted.")
