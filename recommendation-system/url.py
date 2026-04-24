from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services import get_recommendations
from .serializers import MaterialSerializer


class RecommendationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        materials = get_recommendations(request.user)
        return Response(MaterialSerializer(materials, many=True).data)