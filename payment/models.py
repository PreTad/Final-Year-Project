from django.db import models
import uuid
# Create your models here.
# Payment Table
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        "backend.Member",
        on_delete=models.PROTECT,
        related_name='payment'
    ) 
    return_id = models.ForeignKey(
        "transactions.Return",
        on_delete=models.PROTECT,
        related_name='payment'
    ) 
    fine_amount = models.DecimalField(max_digits=10,decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    METHOD = [
        ('CASH','CASH'),
        ('TRANSFER','TRANSFER')
    ]
    method = models.CharField(max_length=20,choices=METHOD,default='CASH')
    transaction_reference = models.CharField(max_length=50,unique=True)
    STATUS = [
        ('PENDING','PENDING'),
        ('COMPLETED','COMPLETED'),
        ('FAILED','FAILED'),
    ]
    status = models.CharField(max_length=20,choices=STATUS,default='PENDING')
    
