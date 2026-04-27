from django.contrib import admin

from material_mgt.models import *

# Register your models here.
admin.site.register(DigitalMaterial)
admin.site.register(PhysicalMaterial)


@admin.register(MaterialFeedback)
class MaterialFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "rating", "physical_material", "digital_material", "updated_at")
    search_fields = ("user__id_number", "user__first_name", "user__last_name")
    list_filter = ("rating", "created_at", "updated_at")


@admin.register(MaterialFavorite)
class MaterialFavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "physical_material", "digital_material", "created_at")
    search_fields = ("user__id_number", "user__first_name", "user__last_name")
    list_filter = ("created_at",)


@admin.register(MaterialBookmark)
class MaterialBookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "physical_material", "digital_material", "created_at")
    search_fields = ("user__id_number", "user__first_name", "user__last_name")
    list_filter = ("created_at",)
