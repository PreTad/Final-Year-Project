
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/user/", include("user_mgt.urls")),
    path("api/transactions/", include("transactions.urls")),
    path("api/payment/", include("payment.urls")),
    path("api/material/", include("material_mgt.urls")),
]
