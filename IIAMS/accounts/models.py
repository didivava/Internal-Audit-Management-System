from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    @classmethod
    def normalize_email(cls, email):
        if email is None:
            return None
        return super().normalize_email(email)


class User(AbstractUser):
    email = models.EmailField(unique=True, null=True, blank=True)
    oidc_subject = models.CharField(max_length=255, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    objects = UserManager()

    @property
    def preferred_name(self) -> str:
        return self.display_name or self.get_full_name() or self.get_username()
