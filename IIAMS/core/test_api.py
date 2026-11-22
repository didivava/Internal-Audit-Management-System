from datetime import date

from django.contrib.auth.models import Group
from django.middleware.csrf import _get_new_csrf_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from core.models import AuditEvent, AuditPlan, Engagement, EngagementMember, RiskRating
from core.permissions import (
    ROLE_AUDIT_MANAGER,
    ROLE_AUDITOR,
    ROLE_CAE,
    ROLE_EXECUTIVE,
)


class AuditPlanAPITests(TestCase):
    def setUp(self):
        self.manager = self.make_user("manager")
        self.cae = self.make_user("cae")
        self.auditor = self.make_user("auditor")
        self.executive = self.make_user("executive")
        self.add_role(self.manager, ROLE_AUDIT_MANAGER)
        self.add_role(self.cae, ROLE_CAE)
        self.add_role(self.auditor, ROLE_AUDITOR)
        self.add_role(self.executive, ROLE_EXECUTIVE)
        self.url = reverse("audit-plan-list")

    @staticmethod
    def make_user(username):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.test",
            password="test-password-only",
        )

    @staticmethod
    def add_role(user, role):
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)

    def make_plan(
        self,
        name="Annual plan",
        status=AuditPlan.Status.DRAFT,
        fiscal_year=2026,
        **kwargs,
    ):
        if status == AuditPlan.Status.APPROVED:
            kwargs.setdefault("approved_by", self.cae)
            kwargs.setdefault("approved_at", timezone.now())
        return AuditPlan.objects.create(
            name=name,
            fiscal_year=fiscal_year,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
            status=status,
            created_by=self.manager,
            **kwargs,
        )

    def client_as(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_api_requires_authentication_and_an_audit_role(self):
        anonymous = APIClient().get(self.url)
        unassigned = self.make_user("unassigned")
        denied = self.client_as(unassigned).get(self.url)

        self.assertIn(anonymous.status_code, (401, 403))
        self.assertEqual(denied.status_code, 403)

    def test_manager_can_create_plan_and_change_is_audited(self):
        response = self.client_as(self.manager).post(
            self.url,
            {
                "name": "FY 2027 plan",
                "fiscal_year": 2027,
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], AuditPlan.Status.DRAFT)
        self.assertEqual(response.data["created_by"], self.manager.pk)
        event = AuditEvent.objects.get(action="audit_plan.created")
        self.assertEqual(event.actor, self.manager)
        self.assertEqual(event.details, {"fields": ["fiscal_year", "name", "period_end", "period_start"]})

    def test_invalid_plan_dates_are_rejected(self):
        response = self.client_as(self.manager).post(
            self.url,
            {
                "name": "Invalid plan",
                "fiscal_year": 2027,
                "period_start": "2027-12-31",
                "period_end": "2027-01-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("period_end", response.data)

    def test_status_cannot_be_set_directly_in_plan_payload(self):
        response = self.client_as(self.manager).post(
            self.url,
            {
                "name": "Status guard plan",
                "fiscal_year": 2027,
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "status": AuditPlan.Status.APPROVED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], AuditPlan.Status.DRAFT)

    def test_only_approved_plans_are_visible_to_executive_readers(self):
        draft = self.make_plan(name="Draft plan")
        approved = self.make_plan(name="Approved plan", status=AuditPlan.Status.APPROVED)

        response = self.client_as(self.executive).get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [str(approved.pk)])
        self.assertNotEqual(str(draft.pk), response.data["results"][0]["id"])

    def test_auditors_only_see_plans_for_assigned_engagements(self):
        assigned_plan = self.make_plan(name="Assigned plan")
        self.make_plan(name="Unassigned plan", fiscal_year=2027)
        engagement = Engagement.objects.create(
            plan=assigned_plan,
            code="AUD-ASSIGNED",
            title="Assigned engagement",
            objectives="Review assigned scope.",
            risk_rating=RiskRating.HIGH,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            lead=self.manager,
            created_by=self.manager,
        )
        EngagementMember.objects.create(engagement=engagement, user=self.auditor)

        response = self.client_as(self.auditor).get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [str(assigned_plan.pk)])

    def test_manager_submits_and_only_cae_approves_plan(self):
        plan = self.make_plan(name="Approval plan")
        manager_client = self.client_as(self.manager)
        submit_url = reverse("audit-plan-submit-for-review", args=[plan.pk])
        approve_url = reverse("audit-plan-approve", args=[plan.pk])

        manager_submit = manager_client.post(submit_url, {}, format="json")
        manager_approve = manager_client.post(approve_url, {}, format="json")
        cae_approve = self.client_as(self.cae).post(approve_url, {}, format="json")

        self.assertEqual(manager_submit.status_code, 200)
        self.assertEqual(manager_approve.status_code, 403)
        self.assertEqual(cae_approve.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, AuditPlan.Status.APPROVED)
        self.assertEqual(plan.approved_by, self.cae)
        self.assertIsNotNone(plan.approved_at)
        self.assertEqual(
            set(AuditEvent.objects.filter(object_id=str(plan.pk)).values_list("action", flat=True)),
            {"audit_plan.submitted_for_review", "audit_plan.approved"},
        )

    def test_invalid_plan_transition_returns_conflict(self):
        plan = self.make_plan(name="Transition plan")
        response = self.client_as(self.cae).post(
            reverse("audit-plan-approve", args=[plan.pk]), {}, format="json"
        )

        self.assertEqual(response.status_code, 409)
        plan.refresh_from_db()
        self.assertEqual(plan.status, AuditPlan.Status.DRAFT)

    def test_audit_plans_cannot_be_deleted_through_the_api(self):
        plan = self.make_plan(name="Protected plan")
        response = self.client_as(self.manager).delete(
            reverse("audit-plan-detail", args=[plan.pk])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(AuditPlan.objects.filter(pk=plan.pk).exists())

    def test_session_authentication_requires_csrf_for_plan_writes(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.manager)
        payload = {
            "name": "CSRF protected plan",
            "fiscal_year": 2027,
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
        }

        denied = client.post(self.url, payload, format="json")
        self.assertEqual(denied.status_code, 403)

        token = _get_new_csrf_string()
        client.cookies["csrftoken"] = token
        allowed = client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(allowed.status_code, 201)
