from django.db import models
import uuid
import os
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
    file = models.FileField(upload_to="digital_materials/")
    created_by = models.ForeignKey(
        "backend.Staff",
        on_delete=models.SET_NULL,
        related_name='digital_material',
        null=True,         
        blank=True 
    )

    @staticmethod
    def _human_readable_size(size_in_bytes):
        if size_in_bytes < 1024:
            return f"{size_in_bytes} B"
        if size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes / 1024:.1f} KB"
        if size_in_bytes < 1024 * 1024 * 1024:
            return f"{size_in_bytes / (1024 * 1024):.1f} MB"
        return f"{size_in_bytes / (1024 * 1024 * 1024):.1f} GB"

    def save(self, *args, **kwargs):
        if self.file:
            _, extension = os.path.splitext(self.file.name)
            self.format = extension.lstrip(".").upper() or "UNKNOWN"
            self.file_size = self._human_readable_size(self.file.size)
        super().save(*args, **kwargs)

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
    total_copies = models.IntegerField()
    available_copies = models.IntegerField(null=True, blank=True)
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

    def save(self, *args, **kwargs):
        if self.available_copies is None:
            self.available_copies = self.total_copies
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
