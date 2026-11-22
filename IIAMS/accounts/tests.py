from urllib.parse import parse_qs, urlsplit
import time
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.exceptions import SuspiciousOperation
from django.test import TestCase, override_settings

from accounts.models import User
from accounts.oidc import EntraOIDCBackend
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

TENANT_ID = "12345678-1234-1234-1234-123456789012"
OBJECT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"


@override_settings(
    ENTRA_TENANT_ID=TENANT_ID,
    OIDC_EXPECTED_ISSUER=ISSUER,
    OIDC_RP_CLIENT_ID="northstar-test-client",
    OIDC_RP_CLIENT_SECRET="test-only-secret",
    OIDC_RP_SIGN_ALGO="RS256",
    OIDC_OP_JWKS_ENDPOINT="https://login.microsoftonline.com/test/keys",
    OIDC_OP_TOKEN_ENDPOINT="https://login.microsoftonline.com/test/token",
    OIDC_OP_USER_ENDPOINT="https://graph.microsoft.com/oidc/userinfo",
    OIDC_OP_AUTHORIZATION_ENDPOINT="https://login.microsoftonline.com/test/authorize",
    OIDC_USE_NONCE=True,
    OIDC_USE_PKCE=True,
    ROOT_URLCONF="accounts.oidc_test_urls",
    ENTRA_ROLE_CLAIM="roles",
    ENTRA_ROLE_GROUP_MAPPING={"Audit.Manager": "audit_manager"},
)
class EntraOIDCBackendTests(TestCase):
    def setUp(self):
        self.backend = EntraOIDCBackend()
        self.claims = {
            "iss": ISSUER,
            "aud": "northstar-test-client",
            "tid": TENANT_ID,
            "oid": OBJECT_ID,
            "sub": "provider-specific-subject",
            "exp": int(time.time()) + 300,
            "iat": int(time.time()),
        }

    def test_login_redirect_uses_authorization_code_nonce_and_pkce(self):
        response = self.client.get("/oidc/authenticate/")

        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertTrue(location.startswith("https://login.microsoftonline.com/test/authorize?"))
        parameters = parse_qs(urlsplit(location).query)
        self.assertEqual(parameters["client_id"], ["northstar-test-client"])
        self.assertEqual(parameters["response_type"], ["code"])
        self.assertEqual(parameters["code_challenge_method"], ["S256"])
        self.assertTrue(parameters["state"][0])
        self.assertTrue(parameters["nonce"][0])
        self.assertNotIn("test-only-secret", location)

        state = self.client.session["oidc_states"][parameters["state"][0]]
        self.assertTrue(state["code_verifier"])
        self.assertEqual(state["nonce"], parameters["nonce"][0])

    def test_valid_id_token_claims_are_accepted_after_signature_verification(self):
        with patch.object(OIDCAuthenticationBackend, "verify_token", return_value=self.claims):
            self.assertEqual(self.backend.verify_token("test-token"), self.claims)

    def test_id_tokens_with_wrong_issuer_audience_or_tenant_are_rejected(self):
        invalid_claims = [
            {**self.claims, "iss": "https://attacker.example/"},
            {**self.claims, "aud": "another-client"},
            {**self.claims, "tid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
            {**self.claims, "aud": ["northstar-test-client", "another-client"]},
            {**self.claims, "exp": int(time.time()) - 120},
            {**self.claims, "iat": True},
        ]

        for claims in invalid_claims:
            with self.subTest(claims=claims), patch.object(
                OIDCAuthenticationBackend, "verify_token", return_value=claims
            ), self.assertRaises(SuspiciousOperation):
                self.backend.verify_token("test-token")

    def test_multi_audience_token_requires_this_client_as_authorized_party(self):
        claims = {
            **self.claims,
            "aud": ["northstar-test-client", "another-client"],
            "azp": "northstar-test-client",
        }
        with patch.object(OIDCAuthenticationBackend, "verify_token", return_value=claims):
            self.assertEqual(self.backend.verify_token("test-token"), claims)

    def test_userinfo_must_match_the_signed_token_subject(self):
        with patch.object(
            OIDCAuthenticationBackend, "get_userinfo", return_value={"sub": "different-subject"}
        ), self.assertRaises(SuspiciousOperation):
            self.backend.get_userinfo("access-token", "id-token", self.claims)

    def test_verified_identity_and_role_claims_are_merged_from_the_id_token(self):
        claims = {**self.claims, "roles": ["Audit.Manager"]}
        with patch.object(
            OIDCAuthenticationBackend,
            "get_userinfo",
            return_value={"sub": self.claims["sub"], "email": "Jordan@Example.test"},
        ):
            result = self.backend.get_userinfo("access-token", "id-token", claims)

        self.assertEqual(result["tid"], TENANT_ID)
        self.assertEqual(result["oid"], OBJECT_ID)
        self.assertEqual(result["roles"], ["Audit.Manager"])
        self.assertEqual(result["email"], "Jordan@Example.test")

    def test_user_lookup_uses_tenant_and_object_ids_not_email(self):
        user = User.objects.create_user(
            username="entra-existing",
            email="different@example.test",
            password=None,
            oidc_subject=f"{TENANT_ID}:{OBJECT_ID}",
        )
        matches = self.backend.filter_users_by_claims(self.claims)

        self.assertEqual(list(matches), [user])

    def test_user_creation_uses_stable_identity_and_configured_role_mapping(self):
        claims = {
            **self.claims,
            "name": "Jordan Davis",
            "email": None,
            "roles": ["Audit.Manager"],
        }
        user = self.backend.create_user(claims)

        self.assertEqual(user.oidc_subject, f"{TENANT_ID}:{OBJECT_ID}")
        self.assertIsNone(user.email)
        self.assertEqual(user.preferred_name, "Jordan Davis")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.groups.filter(name="audit_manager").exists())

    def test_unknown_roles_do_not_grant_mapped_application_groups(self):
        user = self.backend.create_user(
            {
                **self.claims,
                "email": "auditor@example.test",
                "roles": ["Unmapped.Role"],
            }
        )

        self.assertFalse(user.groups.exists())

    def test_email_collision_does_not_link_another_account(self):
        User.objects.create_user(
            username="preexisting",
            email="jordan@example.test",
            password=None,
        )

        with self.assertRaises(SuspiciousOperation):
            self.backend.create_user(
                {
                    **self.claims,
                    "email": "Jordan@Example.test",
                }
            )

    def test_disabled_users_cannot_sign_in(self):
        user = User.objects.create_user(
            username="entra-disabled",
            email="disabled@example.test",
            password=None,
            oidc_subject=f"{TENANT_ID}:{OBJECT_ID}",
            is_active=False,
        )

        with self.assertRaises(SuspiciousOperation):
            self.backend.update_user(user, {**self.claims, "name": "Disabled"})

    def test_managed_groups_are_removed_when_the_provider_role_is_removed(self):
        user = self.backend.create_user(
            {
                **self.claims,
                "email": "auditor@example.test",
                "roles": ["Audit.Manager"],
            }
        )
        self.backend.update_user(user, {**self.claims, "roles": []})

        self.assertFalse(Group.objects.filter(user=user, name="audit_manager").exists())
