from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MaterialInteraction(models.Model):
    VIEW = "view"
    BORROW = "borrow"
    LIKE = "like"

    INTERACTION_TYPES = [
        (VIEW, "View"),
        (BORROW, "Borrow"),
        (LIKE, "Like"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    material = models.ForeignKey("material_mgt.Material", on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    score = models.FloatField(default=1.0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "material", "interaction_type")