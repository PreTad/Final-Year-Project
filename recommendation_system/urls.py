from django.urls import path

from .views import RecommendationForUserAPIView, SimilarMaterialRecommendationAPIView


urlpatterns = [
    path("for-you/", RecommendationForUserAPIView.as_view(), name="recommendation-for-you"),
    path("similar/<uuid:material_id>/", SimilarMaterialRecommendationAPIView.as_view(), name="recommendation-similar"),
]
