from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from material_mgt.models import PhysicalMaterial
from user_mgt.models import Staff, User

from .models import Borrow, Return
from .services import sync_overdue_borrow_statuses


class OverdueBorrowSyncTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            id_number="MEM-300",
            email="member300@example.com",
            password="StrongPass123!",
            first_name="Member",
            last_name="ThreeHundred",
            role="MEMBER",
        )
        self.client.force_authenticate(user=self.user)

        self.material = PhysicalMaterial.objects.create(
            title="Distributed Systems",
            author="Tanenbaum",
            category="BOOK",
            genre="CS",
            published_date=date(2024, 1, 1),
            department="CS",
            language="English",
            total_copies=3,
            available_copies=2,
            price=150,
            condition="GOOD",
            location="STACK",
            can_borrow=True,
        )

    def test_service_marks_overdue_borrow(self):
        borrow = Borrow.objects.create(
            member=self.user,
            material=self.material,
            due_date=timezone.now() - timedelta(days=2),
            status="BORROWED",
        )

        updated = sync_overdue_borrow_statuses()
        borrow.refresh_from_db()

        self.assertEqual(updated, 1)
        self.assertEqual(borrow.status, "OVERDUE")

    def test_borrow_list_auto_syncs_overdue_status(self):
        borrow = Borrow.objects.create(
            member=self.user,
            material=self.material,
            due_date=timezone.now() - timedelta(days=1),
            status="BORROWED",
        )

        response = self.client.get("/api/transactions/borrow/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        borrow.refresh_from_db()
        self.assertEqual(borrow.status, "OVERDUE")


class ReturnPaymentGateTests(APITestCase):
    def setUp(self):
        self.stack_staff_user = User.objects.create_user(
            id_number="STF-100",
            email="stackstaff100@example.com",
            password="StrongPass123!",
            first_name="Stack",
            last_name="Staff",
            role="STACK STAFF",
        )
        self.stack_staff_profile = Staff.objects.create(user_id=self.stack_staff_user)

        self.member_user = User.objects.create_user(
            id_number="MEM-101",
            email="member101@example.com",
            password="StrongPass123!",
            first_name="Member",
            last_name="OneZeroOne",
            role="MEMBER",
        )

        self.material = PhysicalMaterial.objects.create(
            title="Clean Architecture",
            author="Robert C. Martin",
            category="BOOK",
            genre="Software",
            published_date=date(2018, 1, 1),
            department="CS",
            language="English",
            total_copies=2,
            available_copies=0,
            price=200,
            condition="GOOD",
            location="STACK",
            can_borrow=True,
        )

        self.client.force_authenticate(user=self.stack_staff_user)

    def test_return_without_fine_marks_borrow_returned_immediately(self):
        borrow = Borrow.objects.create(
            member=self.member_user,
            material=self.material,
            due_date=timezone.now() + timedelta(days=1),
            status="BORROWED",
            created_by=self.stack_staff_profile,
        )

        response = self.client.post(
            "/api/transactions/return/",
            {"borrow": str(borrow.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        borrow.refresh_from_db()
        self.material.refresh_from_db()
        return_record = Return.objects.get(borrow=borrow)

        self.assertEqual(return_record.fine_amount, 0)
        self.assertEqual(borrow.status, "RETURNED")
        self.assertEqual(self.material.available_copies, 1)

    def test_return_with_fine_stays_unreturned_until_payment(self):
        borrow = Borrow.objects.create(
            member=self.member_user,
            material=self.material,
            due_date=timezone.now() - timedelta(days=2),
            status="OVERDUE",
            created_by=self.stack_staff_profile,
        )

        response = self.client.post(
            "/api/transactions/return/",
            {"borrow": str(borrow.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        borrow.refresh_from_db()
        self.material.refresh_from_db()
        return_record = Return.objects.get(borrow=borrow)

        self.assertGreater(return_record.fine_amount, 0)
        self.assertNotEqual(borrow.status, "RETURNED")
        self.assertEqual(self.material.available_copies, 0)
