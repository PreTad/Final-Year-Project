from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from user_mgt.models import User
from material_mgt.models import DigitalMaterial, MaterialBookmark, MaterialFavorite, MaterialFeedback, PhysicalMaterial


class MaterialInteractionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            id_number="MEM-100",
            email="member1@example.com",
            password="StrongPass123!",
            first_name="First",
            last_name="User",
            role="MEMBER",
        )
        self.other_user = User.objects.create_user(
            id_number="MEM-200",
            email="member2@example.com",
            password="StrongPass123!",
            first_name="Second",
            last_name="User",
            role="MEMBER",
        )
        self.client.force_authenticate(user=self.user)

        self.physical = PhysicalMaterial.objects.create(
            title="Physical Test Book",
            author="Author One",
            category="BOOK",
            genre="Tech",
            published_date=date(2024, 1, 1),
            department="CS",
            language="English",
            total_copies=5,
            available_copies=5,
            price=100,
            condition="GOOD",
            location="STACK",
            can_borrow=True,
        )

        self.digital = DigitalMaterial.objects.create(
            title="Digital Test Book",
            author="Author Two",
            category="BOOK",
            genre="Science",
            published_date=date(2024, 1, 1),
            department="CS",
            language="English",
            isbn="ISBN-10001",
            format="PDF",
            file_size="1 MB",
            file="digital_materials/test.pdf",
        )

    def test_create_feedback_and_prevent_duplicate_feedback(self):
        url = "/api/material/feedback/"
        payload = {
            "material_type": "physical",
            "material_id": str(self.physical.id),
            "rating": 5,
            "comment": "Great material.",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        duplicate = self.client.post(url, payload, format="json")
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(MaterialFeedback.objects.count(), 1)

    def test_favorite_is_idempotent(self):
        url = "/api/material/favorites/"
        payload = {"material_type": "digital", "material_id": str(self.digital.id)}

        first = self.client.post(url, payload, format="json")
        second = self.client.post(url, payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(MaterialFavorite.objects.count(), 1)

    def test_bookmark_list_returns_only_authenticated_user_data(self):
        MaterialBookmark.objects.create(user=self.user, physical_material=self.physical)
        MaterialBookmark.objects.create(user=self.other_user, digital_material=self.digital)

        response = self.client.get("/api/material/bookmarks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["user_id"], str(self.user.id))

    def test_interaction_stats_endpoint(self):
        MaterialFeedback.objects.create(user=self.user, physical_material=self.physical, rating=4, comment="Useful")
        MaterialFavorite.objects.create(user=self.user, physical_material=self.physical)
        MaterialBookmark.objects.create(user=self.user, physical_material=self.physical)

        response = self.client.get(
            "/api/material/interactions/stats/",
            {"material_type": "physical", "material_id": str(self.physical.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ratings_count"], 1)
        self.assertEqual(response.data["favorites_count"], 1)
        self.assertEqual(response.data["bookmarks_count"], 1)
        self.assertTrue(response.data["is_favorited"])
        self.assertTrue(response.data["is_bookmarked"])
