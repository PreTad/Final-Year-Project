from django.db import models
import uuid
# Create your models here.
#Reservation Table
class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        "backend.Member",
        on_delete=models.CASCADE,
        related_name='reservation'
    ) 
    material_id = models.ForeignKey(
        "material_mgt.PhysicalMaterial",
        on_delete=models.CASCADE,
        related_name='reservation'
    ) 
    reserve_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    STATUS = [
        ('RESERVED','RESERVED'),
        ('EXPIRED','EXPIRED'),
        ('CANCELLED','CANCELLED'),
    ]
    status = models.CharField(max_length=20,choices=STATUS,default='RESERVED')
    def material_title(self):
        return self.material_id.title
    def material_author(self):
        return self.material_id.author

# Borrow Table
class Borrow(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        "backend.Member",
        on_delete=models.PROTECT,
        related_name='borrow'
    ) 
    material_id = models.ForeignKey(
        "material_mgt.PhysicalMaterial",
        on_delete=models.PROTECT,
        related_name='borrow'
    ) 
    reserve_id = models.ForeignKey(
        Reservation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        # related_name='reservation'
    ) 
    borrow_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    STATUS = [
        ('BORROWED','BORROWED'),
        ('OVERDUE','OVERDUE')
    ]
    status = models.CharField(max_length=20,choices=STATUS,default='BORROWED')
    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True ,
        related_name='borrow'
    )

# Circulation Table
class Circulation(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        "backend.Member",
        on_delete=models.PROTECT,
        related_name='circulation'
    ) 
    material_id = models.ForeignKey(
        "material_mgt.PhysicalMaterial",
        on_delete=models.PROTECT,
        related_name='circulation'
    ) 
    STATUS = [
        ('BORROWED','BORROWED'),
        ('RETURNED','RETURNED')
    ]
    status = models.CharField(max_length=20,choices=STATUS,default='BORROWED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        null=True,    
        blank=True 
    )
# Return Table
class Return(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    borrow_id = models.ForeignKey(
        Borrow,
        on_delete=models.CASCADE,
        related_name='return_material'
    ) 
    return_date = models.DateTimeField(auto_now_add=True)
    fine_amount = models.DecimalField(max_digits=10,decimal_places=2)
    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        null=True, 
        blank=True ,
        related_name='return_material'
    )
