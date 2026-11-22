from rest_framework.routers import SimpleRouter

from core.api_views import AuditPlanViewSet

router = SimpleRouter()
router.register("audit-plans", AuditPlanViewSet, basename="audit-plan")

urlpatterns = router.urls
