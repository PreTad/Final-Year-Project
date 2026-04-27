from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Reservation)
admin.site.register(Borrow)
admin.site.register(Return)