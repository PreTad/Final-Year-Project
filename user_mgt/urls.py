from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import (
    AdminUsersAPIView,
    ChangePasswordAPIView,
    ConfirmResetOTPAPIView,
    CustomTokenObtainPairView,
    ForgotPasswordAPIView,
    LibraryViewSet,
    LibraryPolicyViewSet,
    ResetPasswordAPIView,
    UserMeAPIView,
    UserCreateAPIView,
    UserDeleteAPIView,
    UserListAPIView,
    UserUpdateAPIView,
    AdminUsersAPIView,
)

router = DefaultRouter()
router.register("libraries", LibraryViewSet, basename="library")
router.register("library-policies", LibraryPolicyViewSet, basename="library-policy")
urlpatterns = [
    path("", include(router.urls)),
    path("users/admins/", AdminUsersAPIView.as_view(), name="users-admins"),
    path("users/create/", UserCreateAPIView.as_view(), name="user-create"),
    path("users/all", UserListAPIView.as_view(), name="user-list"),
    path("users/admins/", AdminUsersAPIView.as_view(), name="user-admins"),
    path("users/update/<uuid:pk>/", UserUpdateAPIView.as_view(), name="user-update"),
    path("users/<uuid:pk>/delete/", UserDeleteAPIView.as_view(), name="user-delete"),
    path("auth/password/", ChangePasswordAPIView.as_view(), name="auth-change-password"),
    path("auth/forgot-password/", ForgotPasswordAPIView.as_view(), name="auth-forgot-password"),
    path("auth/forgot-password", ForgotPasswordAPIView.as_view(), name="auth-forgot-password-noslash"),
    path("auth/confirm-reset-otp/", ConfirmResetOTPAPIView.as_view(), name="auth-confirm-reset-otp"),
    path("auth/confirm-reset-otp", ConfirmResetOTPAPIView.as_view(), name="auth-confirm-reset-otp-noslash"),
    path("auth/reset-password/", ResetPasswordAPIView.as_view(), name="auth-reset-password"),
    path("auth/reset-password", ResetPasswordAPIView.as_view(), name="auth-reset-password-noslash"),
    path("auth/me/", UserMeAPIView.as_view(), name="auth-me"),
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
