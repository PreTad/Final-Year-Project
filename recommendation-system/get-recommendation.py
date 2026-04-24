from django.db.models import Count, Q
from material_mgt.models import Material
from .models import MaterialInteraction


def get_recommendations(user, limit=10):
    # 1. Get materials user interacted with
    user_materials = MaterialInteraction.objects.filter(user=user)

    liked_ids = user_materials.filter(interaction_type="like").values_list("material_id", flat=True)
    borrowed_ids = user_materials.filter(interaction_type="borrow").values_list("material_id", flat=True)

    # 2. Content-based: same category as liked/borrowed
    category_ids = Material.objects.filter(
        id__in=list(liked_ids) + list(borrowed_ids)
    ).values_list("category_id", flat=True)

    content_based = Material.objects.filter(
        category_id__in=category_ids
    )

    # 3. Popularity-based fallback
    popular = Material.objects.annotate(
        score=Count("materialinteraction")
    ).order_by("-score")

    # 4. Merge + remove already seen
    seen_ids = set(list(liked_ids) + list(borrowed_ids))

    recommendations = list(content_based.exclude(id__in=seen_ids))[:limit]

    if len(recommendations) < limit:
        for m in popular:
            if m.id not in seen_ids and m not in recommendations:
                recommendations.append(m)
            if len(recommendations) >= limit:
                break

    return recommendations