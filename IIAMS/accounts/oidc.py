import hashlib
import time
from collections.abc import Mapping
from uuid import UUID

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class EntraOIDCBackend(OIDCAuthenticationBackend):
    def verify_token(self, token, **kwargs):
        claims = super().verify_token(token, **kwargs)
        self._validate_id_token_claims(claims)
        return claims

    def _validate_id_token_claims(self, claims):
        if claims.get("iss") != settings.OIDC_EXPECTED_ISSUER:
            raise SuspiciousOperation("The ID token issuer does not match the configured tenant.")

        client_id = settings.OIDC_RP_CLIENT_ID
        audiences = claims.get("aud")
        if isinstance(audiences, str):
            audiences = [audiences]
        if (
            not isinstance(audiences, list)
            or not all(isinstance(audience, str) for audience in audiences)
            or client_id not in audiences
        ):
            raise SuspiciousOperation("The ID token audience does not match this application.")
        if len(audiences) > 1 and claims.get("azp") != client_id:
            raise SuspiciousOperation("The ID token authorized party is invalid.")
        if "azp" in claims and claims["azp"] != client_id:
            raise SuspiciousOperation("The ID token authorized party is invalid.")

        if not self.verify_claims(claims):
            raise SuspiciousOperation("The ID token is missing its stable user identifiers.")

        now = time.time()
        clock_skew = 60
        expiration = claims.get("exp")
        issued_at = claims.get("iat")
        not_before = claims.get("nbf")
        if not self._is_timestamp(expiration) or expiration <= now - clock_skew:
            raise SuspiciousOperation("The ID token is expired or has an invalid expiration.")
        if not self._is_timestamp(issued_at) or issued_at > now + clock_skew:
            raise SuspiciousOperation("The ID token issue time is invalid.")
        if not_before is not None and (
            not self._is_timestamp(not_before) or not_before > now + clock_skew
        ):
            raise SuspiciousOperation("The ID token is not yet valid.")

    @staticmethod
    def _is_timestamp(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def get_userinfo(self, access_token, id_token, payload):
        userinfo = super().get_userinfo(access_token, id_token, payload)
        if not isinstance(userinfo, Mapping) or userinfo.get("sub") != payload.get("sub"):
            raise SuspiciousOperation("The user-info subject does not match the ID token.")

        claims = dict(userinfo)
        for key in ("sub", "tid", "oid", "roles"):
            if key in payload:
                claims[key] = payload[key]
        return claims

    def verify_claims(self, claims):
        try:
            tenant_id = str(UUID(claims.get("tid", "")))
            object_id = str(UUID(claims.get("oid", "")))
        except (AttributeError, TypeError, ValueError):
            return False
        return (
            tenant_id == settings.ENTRA_TENANT_ID
            and bool(object_id)
            and isinstance(claims.get("sub"), str)
            and bool(claims["sub"])
        )

    def _identity_subject(self, claims):
        if not self.verify_claims(claims):
            raise SuspiciousOperation("The identity claims are missing or outside this tenant.")
        return f"{UUID(claims['tid'])}:{UUID(claims['oid'])}"

    def filter_users_by_claims(self, claims):
        try:
            subject = self._identity_subject(claims)
        except SuspiciousOperation:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(oidc_subject=subject)

    @staticmethod
    def _normalized_email(claims):
        email = claims.get("email")
        if not isinstance(email, str):
            return None
        return email.strip().lower() or None

    @staticmethod
    def _text_claim(claims, name, current_value="", max_length=255):
        value = claims.get(name, current_value)
        return value[:max_length] if isinstance(value, str) else current_value

    def _sync_role_groups(self, user, claims):
        mapping = settings.ENTRA_ROLE_GROUP_MAPPING
        if not mapping:
            return

        role_claim = claims.get(settings.ENTRA_ROLE_CLAIM, [])
        if isinstance(role_claim, str):
            roles = {role_claim}
        elif isinstance(role_claim, list) and all(isinstance(role, str) for role in role_claim):
            roles = set(role_claim)
        else:
            raise SuspiciousOperation("The Entra role claim has an invalid format.")

        managed_group_names = set(mapping.values())
        user.groups.remove(*Group.objects.filter(name__in=managed_group_names))
        for role in roles:
            group_name = mapping.get(role)
            if group_name:
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

    @transaction.atomic
    def create_user(self, claims):
        subject = self._identity_subject(claims)
        email = self._normalized_email(claims)
        if email and self.UserModel.objects.filter(email__iexact=email).exists():
            raise SuspiciousOperation(
                "An account with this email already exists; automatic email-based linking is disabled."
            )

        username = f"entra-{hashlib.sha256(subject.encode()).hexdigest()[:40]}"
        user = self.UserModel.objects.create_user(
            username=username,
            email=email,
            password=None,
            oidc_subject=subject,
            display_name=self._text_claim(claims, "name"),
            first_name=self._text_claim(claims, "given_name", max_length=150),
            last_name=self._text_claim(claims, "family_name", max_length=150),
        )
        self._sync_role_groups(user, claims)
        return user

    @transaction.atomic
    def update_user(self, user, claims):
        if not user.is_active:
            raise SuspiciousOperation("This account is disabled.")

        email = self._normalized_email(claims)
        if email and self.UserModel.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise SuspiciousOperation("The Entra email claim is already assigned to another account.")

        user.display_name = self._text_claim(claims, "name", user.display_name)
        user.first_name = self._text_claim(
            claims, "given_name", user.first_name, max_length=150
        )
        user.last_name = self._text_claim(
            claims, "family_name", user.last_name, max_length=150
        )
        if email:
            user.email = email
        user.save(update_fields=["display_name", "first_name", "last_name", "email"])
        self._sync_role_groups(user, claims)
        return user
