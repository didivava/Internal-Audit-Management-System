import uuid
from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from core.models import (
    AuditEvent,
    AuditPlan,
    AuditableEntity,
    Engagement,
    EngagementMember,
    Risk,
    RiskAssessment,
    RiskRating,
)


class AuditDomainModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="auditor",
            email="auditor@example.test",
            password="test-password-only",
        )
        self.plan = AuditPlan.objects.create(
            name="Annual plan",
            fiscal_year=2026,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
            created_by=self.user,
        )
        self.engagement = Engagement.objects.create(
            plan=self.plan,
            code="AUD-001",
            title="Procure to Pay",
            objectives="Assess procurement controls.",
            risk_rating=RiskRating.HIGH,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            lead=self.user,
            created_by=self.user,
        )
        self.entity = AuditableEntity.objects.create(
            code="ENT-001",
            name="Procurement",
            category=AuditableEntity.Category.FINANCE,
            owner=self.user,
        )
        self.risk = Risk.objects.create(
            entity=self.entity,
            code="RISK-001",
            title="Unauthorized supplier changes",
            category="Finance",
            owner=self.user,
        )

    def test_risk_scores_use_the_confirmed_prototype_thresholds(self):
        examples = [
            (1, 1, 1, RiskRating.LOW),
            (3, 2, 6, RiskRating.MEDIUM),
            (3, 4, 12, RiskRating.HIGH),
            (4, 5, 20, RiskRating.CRITICAL),
        ]

        for likelihood, impact, score, rating in examples:
            with self.subTest(score=score):
                assessment = RiskAssessment(
                    risk=self.risk,
                    likelihood=likelihood,
                    impact=impact,
                    assessed_by=self.user,
                    assessed_at=timezone.now(),
                )
                self.assertEqual(assessment.inherent_score, score)
                self.assertEqual(assessment.inherent_rating, rating)

    def test_residual_risk_requires_both_likelihood_and_impact(self):
        assessment = RiskAssessment(
            risk=self.risk,
            likelihood=3,
            impact=4,
            residual_likelihood=2,
            assessed_by=self.user,
            assessed_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            assessment.full_clean()

    def test_approved_plan_requires_a_recorded_approver_and_time(self):
        plan = AuditPlan(
            name="Unapproved",
            fiscal_year=2027,
            period_start=date(2027, 1, 1),
            period_end=date(2027, 12, 31),
            status=AuditPlan.Status.APPROVED,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_completed_engagement_requires_full_progress(self):
        self.engagement.status = Engagement.Status.COMPLETE
        self.engagement.progress = 50

        with self.assertRaises(ValidationError):
            self.engagement.full_clean()

    def test_engagement_member_is_unique_per_user(self):
        EngagementMember.objects.create(engagement=self.engagement, user=self.user)

        with self.assertRaises(IntegrityError), transaction.atomic():
            EngagementMember.objects.create(engagement=self.engagement, user=self.user)

    def test_audit_events_cannot_be_updated_or_deleted_through_model_apis(self):
        event = AuditEvent.objects.create(
            actor=self.user,
            action="finding.created",
            object_type="finding",
            object_id=str(uuid.uuid4()),
            details={"source": "test"},
        )
        event.action = "finding.changed"

        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=event.pk).update(action="finding.changed")
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=event.pk).delete()
        with self.assertRaises(ValidationError):
            event.delete()
