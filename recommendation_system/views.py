from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import recommend_for_user, recommend_similar_materials


class RecommendationForUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = request.query_params.get("limit", 8)
        material_type = request.query_params.get("type", "all")
        exclude_material_id = request.query_params.get("exclude_material_id")

        payload = recommend_for_user(
            request.user,
            limit=limit,
            material_type=material_type,
            exclude_material_id=exclude_material_id,
        )
        return Response(payload)


class SimilarMaterialRecommendationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, material_id):
        limit = request.query_params.get("limit", 6)
        payload = recommend_similar_materials(material_id, limit=limit)
        if not payload:
            return Response({"detail": "Material not found."}, status=404)
        return Response(payload)

