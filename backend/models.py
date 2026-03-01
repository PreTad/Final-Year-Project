from django.db import models
from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.core.exceptions import ValidationError
import uuid


class UserManager(BaseUserManager):
    use_in_migrations = True
    
    def _create_user(self, id_number, password, **extra_fields):
        if not id_number:
            raise ValueError("The ID number must be set")
        email = extra_fields.get("email")
        if not email:
            raise ValueError("The email must be set")
        extra_fields["email"] = self.normalize_email(email)

        user = self.model(id_number=id_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, id_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', 'MEMBER')
        extra_fields.setdefault('status', 'ACTIVE')
        return self._create_user(id_number, password, **extra_fields)

    def create_superuser(self, id_number, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'SUPER ADMIN')
        extra_fields.setdefault('status', 'ACTIVE')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(id_number, password, **extra_fields)
    
    
class User(AbstractUser):
    
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    username = None
    id_number = models.CharField(max_length=30,unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100,unique=True)
    ROLE_CHOICES = [
        ('STACK STAFF', 'STACK STAFF'),
        ('TECHNICAL STAFF', 'TECHNICAL STAFF'),
        ('FRONT DESK STAFF', 'FRONT DESK STAFF'),
        ('ADMIN', 'ADMIN'),
        ('DEPARTMENT HEAD', 'DEPARTMENT HEAD'),
        ('MEMBER', 'MEMBER'),
        ('SUPER ADMIN', 'SUPER ADMIN'),
    ]
    role = models.CharField(max_length=30,choices=ROLE_CHOICES, default='MEMBER')
    STATUS_CHOICES = [
        ('ACTIVE', 'ACTIVE'),
        ('INACTIVE', 'INACTIVE'),
        ('SUSPENDED', 'SUSPENDED'),
        ('DEACTIVATED', 'DEACTIVATED'),
    ]
    status = models.CharField(max_length=30,choices=STATUS_CHOICES, default='ACTIVE')
    USERNAME_FIELD = "id_number"
    REQUIRED_FIELDS = ["email"]
    objects = UserManager()
    
    def __str__(self):
        return self.id_number

# Library Members Table
class Member(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='member')
    department = models.CharField(max_length=70)
    photo = models.ImageField(upload_to='profile_photo',blank=True,null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    USER_TYPE = [
        ('TEACHER','TEACHER'),
        ('STUDENT','STUDENT'),
    ]
    user_type = models.CharField(max_length=15,choices=USER_TYPE)

    @property
    def first_name(self):
        return self.user_id.first_name

    @property
    def last_name(self):
        return self.user_id.last_name

    @property
    def email(self):
        return self.user_id.email

    def clean(self):
        super().clean()
        if self.user_id.role != "MEMBER":
            raise ValidationError("Member profile requires user role MEMBER.")
        if DepartmentHead.objects.filter(user_id=self.user_id).exists():
            raise ValidationError("User already has a DepartmentHead profile.")
        if Staff.objects.filter(user_id=self.user_id).exists():
            raise ValidationError("User already has a Staff profile.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    

# Department Head Table
class DepartmentHead(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='department_head')
    department = models.CharField(max_length=70)
    photo = models.ImageField(upload_to='profile_photo',blank=True,null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    @property
    def first_name(self):
        return self.user_id.first_name

    @property
    def last_name(self):
        return self.user_id.last_name

    @property
    def email(self):
        return self.user_id.email

    def clean(self):
        super().clean()
        if self.user_id.role != "DEPARTMENT HEAD":
            raise ValidationError("DepartmentHead profile requires user role DEPARTMENT HEAD.")
        if Member.objects.filter(user_id=self.user_id).exists():
            raise ValidationError("User already has a Member profile.")
        if Staff.objects.filter(user_id=self.user_id).exists():
            raise ValidationError("User already has a Staff profile.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# Staff Table
class Staff(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff')
    photo = models.ImageField(upload_to='profile_photo',blank=True,null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    work_shift = models.CharField(max_length=15, blank=True, null=True)

    @property
    def first_name(self):
        return self.user_id.first_name

    @property
    def last_name(self):
        return self.user_id.last_name

    @property
    def email(self):
        return self.user_id.email

    @property
    def full_name(self):
        return f"{self.user_id.first_name} {self.user_id.last_name}".strip()

    def clean(self):
        super().clean()
        staff_roles = {"STACK STAFF", "TECHNICAL STAFF", "FRONT DESK STAFF", "ADMIN", "SUPER ADMIN"}
        if self.user_id.role not in staff_roles:
            raise ValidationError("Staff profile requires a staff-compatible user role.")
        if Member.objects.filter(user_id=self.user_id).exists():
            raise ValidationError("User already has a Member profile.")
        if DepartmentHead.objects.filter(user_id=self.user_id).exists():
            raise ValidationError("User already has a DepartmentHead profile.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# Digital Material Table
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
        Staff,
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
        Staff,
        on_delete=models.SET_NULL,
        related_name='physical_material',
        null=True, 
        blank=True 
    )
    
    def __str__(self):
        return self.title
    
#Reservation Table
class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='reservation'
    ) 
    material_id = models.ForeignKey(
        PhysicalMaterial,
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
        Member,
        on_delete=models.PROTECT,
        related_name='borrow'
    ) 
    material_id = models.ForeignKey(
        PhysicalMaterial,
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
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True ,
        related_name='borrow'
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
        Staff,
        on_delete=models.SET_NULL,
        null=True, 
        blank=True ,
        related_name='return_material'
    )

# Payment Table
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name='payment'
    ) 
    return_id = models.ForeignKey(
        Return,
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
    
# Notification Table
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='notification'
    ) 
    borrow_id = models.ForeignKey(
        Borrow,
        on_delete=models.CASCADE,
        related_name='notification'
    ) 
    reserve_id = models.ForeignKey(
        Reservation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='notification'
    ) 
    message = models.CharField(max_length=200)
    STATUS = [
        ('SENT','SENT'),
        ('READ','READ'),
        ('UNREAD','UNREAD'),
    ]
    status = models.CharField(max_length=20,choices=STATUS,default='UNREAD')
    sent_at = models.DateTimeField(auto_now_add=True)

# Circulation Table
class Circulation(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name='circulation'
    ) 
    material_id = models.ForeignKey(
        PhysicalMaterial,
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
        Staff,
        on_delete=models.SET_NULL,
        null=True,    
        blank=True 
    )

# Library Table
class Library(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    name = models.CharField(max_length=100,unique=True)
    campus = models.CharField(max_length=100)
    staff_id = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,     
        blank=True ,
        related_name='library'
    ) 

    @property
    def staff_name(self):
        if not self.staff_id:
            return None
        return self.staff_id.full_name or self.staff_id.user_id.id_number
