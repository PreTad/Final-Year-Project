from django.db import models
import uuid
from django.utils import timezone


# Reservation Table
class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        "backend.User",
        on_delete=models.PROTECT,
        related_name="reservations"
    )
    material_id = models.ForeignKey(
        "material_mgt.PhysicalMaterial",
        on_delete=models.DO_NOTHING,
        related_name="reservations"
    )
    reserve_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    STATUS = [
        ("RESERVED", "RESERVED"),
        ("EXPIRED", "EXPIRED"),
        ("CANCELLED", "CANCELLED"),
    ]
    status = models.CharField(max_length=20, choices=STATUS, default="RESERVED")
    availability_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["reserve_date"]

    def __str__(self):
        return f"{self.member} reserved {self.material_id}"
    

# Borrow Table
class Borrow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        "backend.User",
        on_delete=models.PROTECT,
        related_name="borrows"
    )

    material = models.ForeignKey(
        "material_mgt.PhysicalMaterial",
        on_delete=models.PROTECT,
        related_name="borrows"
    )

    reservation = models.ForeignKey(
        Reservation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="borrows"
    )

    borrow_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    STATUS = [
        ("BORROWED", "BORROWED"),
        ("OVERDUE", "OVERDUE"),
        ("RETURNED", "RETURNED"),
    ]
    # ovrrdue_amount = 
    status = models.CharField(max_length=20, choices=STATUS, default="BORROWED")
    overdue_notified_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_borrows"
    )

    def __str__(self):
        return f"{self.member} borrowed {self.material}"

# Circulation Table
class Circulation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    member = models.ForeignKey(
        "backend.User",
        on_delete=models.PROTECT,
        related_name="circulations"
    )

    material = models.ForeignKey(
        "material_mgt.PhysicalMaterial",
        on_delete=models.PROTECT,
        related_name="circulations"
    )

    STATUS = [
        ("BORROWED", "BORROWED"),
        ("RETURNED", "RETURNED"),
    ]

    status = models.CharField(max_length=20, choices=STATUS, default="BORROWED")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="circulations_created"
    )

# Return Table
class Return(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    borrow = models.ForeignKey(
        Borrow,
        on_delete=models.CASCADE,
        related_name="returns"
    )
    return_date = models.DateTimeField(auto_now_add=True)
    fine_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="returns_created"
    )
