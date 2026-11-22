from django.conf import settings
from django.urls import include, path

from core import views

urlpatterns = [
    path("api/v1/", include("core.api_urls")),
    path("health/", include("core.urls")),
    path("", views.home, name="home"),
]

if settings.OIDC_ENABLED:
    from django.urls import include

    urlpatterns.insert(0, path("oidc/", include("mozilla_django_oidc.urls")))

if settings.DEBUG:
    from django.contrib import admin

    urlpatterns.insert(0, path("admin/", admin.site.urls))
