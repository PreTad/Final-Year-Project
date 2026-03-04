from django.db import models
import uuid
# Create your models here.
class DigitalMaterial (models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    title = models.CharField(max_length=255)    
    author = models.CharField(max_length=100)
    CATEGORY = [
        ('BOOK','BOOK'),
        ('MAGAZINE','MAGAZINE'),
        ('RESEARCH PAPER','RESEARCH PAPER'),
        ('JOURNALS','JOURNALS'),
        ('THESIS','THESIS')
    ]
    category = models.CharField(max_length=100,choices=CATEGORY)
    genre = models.CharField(max_length=100)
    published_date = models.DateField()
    department = models.CharField(max_length=70)
    language = models.CharField(max_length=70)
    isbn = models.CharField(max_length=70,unique=True,null=True,blank=True)
    format = models.CharField(max_length=20)
    file_size = models.CharField(max_length=10)
    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        related_name='digital_material',
        null=True,         
        blank=True 
    )
    def __str__(self):
        return self.title
    
# Physical Material Table
class PhysicalMaterial (models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    title = models.CharField(max_length=255)    
    author = models.CharField(max_length=100)
    CATEGORY = [
        ('BOOK','BOOK'),
        ('MAGAZINE','MAGAZINE'),
        ('RESEARCH PAPER','RESEARCH PAPER'),
        ('JOURNALS','JOURNALS'),
        ('THESIS','THESIS')
    ]
    category = models.CharField(max_length=100,choices=CATEGORY)
    genre = models.CharField(max_length=100)
    published_date = models.DateField()
    department = models.CharField(max_length=70)
    language = models.CharField(max_length=70)
    isbn = models.CharField(max_length=70,null=True,blank=True)
    copy_number = models.CharField(max_length=100)
    available_copies = models.IntegerField()
    price = models.DecimalField(max_digits=10,decimal_places=2)
    CONDITION = [
        ('NEW','NEW'),
        ('GOOD','GOOD'),
        ('FAIR','FAIR'),
        ('DAMAGED','DAMAGED')
    ]
    condition = models.CharField(max_length=20,choices=CONDITION,default='GOOD')
    LOCATION = [
        ('STACK','STACK'),
        ('SHELF','SHELF')
    ]
    location = models.CharField(max_length=20,choices=LOCATION,default='STACK')
    can_borrow  = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        related_name='physical_material',
        null=True, 
        blank=True 
    )
    
    def __str__(self):
        return self.title
    
