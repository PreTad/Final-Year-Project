from django.urls import path

from .views import ChapaInitializePaymentView, ChapaVerifyPaymentView

urlpatterns = [
    path("chapa/initialize/", ChapaInitializePaymentView.as_view(), name="chapa-initialize-payment"),
    path("chapa/verify/<str:tx_ref>/", ChapaVerifyPaymentView.as_view(), name="chapa-verify-payment"),
]
