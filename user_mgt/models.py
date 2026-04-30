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
    library = models.ForeignKey(
        "backend.Library",
        on_delete=models.SET_NULL,
        related_name="users",
        null=True,
        blank=True,
    )
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
    @property
    def profile_photo(self):
        for rel in ("member", "department_head", "staff"):
            profile = getattr(self, rel, None)
            if profile and profile.photo:
                return profile.photo
        return None
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

# # Notification Table
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    member_id = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='notification'
    ) 
    borrow_id = models.ForeignKey(
        "transactions.Borrow",
        on_delete=models.CASCADE,
        related_name='notification'
    ) 
    reserve_id = models.ForeignKey(
        "transactions.Reservation",
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


# Library Table
class Library(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4,editable=False)
    name = models.CharField(max_length=100,unique=True)
    campus = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class LibraryPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        related_name="policies",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120, default="Default Library Policy")
    is_active = models.BooleanField(default=True)
    borrow_duration_days = models.PositiveIntegerField(default=7)
    max_active_borrows = models.PositiveIntegerField(default=3)
    reservation_hold_hours = models.PositiveIntegerField(default=24)
    overdue_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fair_condition_penalty_percent = models.DecimalField(max_digits=6, decimal_places=2, default=10)
    damaged_condition_penalty_percent = models.DecimalField(max_digits=6, decimal_places=2, default=35)
    lost_condition_penalty_percent = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    grace_period_days = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["library__name", "-is_active", "-updated_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            queryset = LibraryPolicy.objects.exclude(pk=self.pk).filter(is_active=True)
            if self.library_id:
                queryset = queryset.filter(library_id=self.library_id)
            else:
                queryset = queryset.filter(library__isnull=True)
            queryset.update(is_active=False)

    def __str__(self):
        if self.library_id:
            return f"{self.library.name} - {self.name}"
        return self.name
