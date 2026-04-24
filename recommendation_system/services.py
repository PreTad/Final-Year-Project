from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.utils import timezone

from material_mgt.models import DigitalMaterial, PhysicalMaterial
from transactions.models import Borrow, Reservation, Return


def _normalize_text(value):
    return str(value or "").strip()


def _normalize_upper(value):
    return _normalize_text(value).upper()


def _safe_decimal(value):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


@dataclass
class RecommendationContext:
    material_type: str
    material_id: str
    title: str
    author: str
    category: str
    genre: str
    department: str
    language: str
    published_date: object
    available_copies: int
    total_copies: int
    format: str
    file_size: str
    price: Decimal
    can_borrow: bool
    source: object


def _material_to_context(material, material_type: str) -> RecommendationContext:
    if material_type == "DIGITAL":
        available_copies = 1
        total_copies = 1
        format_value = _normalize_upper(getattr(material, "format", ""))
        file_size = _normalize_text(getattr(material, "file_size", ""))
        price = Decimal("0")
        can_borrow = False
    else:
        available_copies = _safe_int(getattr(material, "available_copies", 0))
        total_copies = _safe_int(getattr(material, "total_copies", 0))
        format_value = ""
        file_size = ""
        price = _safe_decimal(getattr(material, "price", 0))
        can_borrow = bool(getattr(material, "can_borrow", False))

    return RecommendationContext(
        material_type=material_type,
        material_id=str(material.id),
        title=_normalize_text(getattr(material, "title", "")),
        author=_normalize_text(getattr(material, "author", "")),
        category=_normalize_upper(getattr(material, "category", "")),
        genre=_normalize_upper(getattr(material, "genre", "")),
        department=_normalize_upper(getattr(material, "department", "")),
        language=_normalize_upper(getattr(material, "language", "")),
        published_date=getattr(material, "published_date", None),
        available_copies=available_copies,
        total_copies=total_copies,
        format=format_value,
        file_size=file_size,
        price=price,
        can_borrow=can_borrow,
        source=material,
    )


def _load_materials(material_type="all") -> list[RecommendationContext]:
    normalized = _normalize_upper(material_type)
    materials: list[RecommendationContext] = []

    if normalized in {"ALL", "PHYSICAL", ""}:
        materials.extend(
            _material_to_context(material, "PHYSICAL")
            for material in PhysicalMaterial.objects.all()
        )

    if normalized in {"ALL", "DIGITAL", ""}:
        materials.extend(
            _material_to_context(material, "DIGITAL")
            for material in DigitalMaterial.objects.all()
        )

    return materials


def _borrow_weights_for_user(user):
    weights = Counter()
    material_ids = set()
    if not user or not getattr(user, "is_authenticated", False):
        return weights, material_ids

    for borrow in Borrow.objects.select_related("material").filter(member=user):
        material = getattr(borrow, "material", None)
        if not material:
            continue

        base_weight = 3
        if _normalize_upper(getattr(borrow, "status", "")) == "OVERDUE":
            base_weight = 1

        material_ids.add(str(material.id))
        weights[("category", _normalize_upper(material.category))] += base_weight
        weights[("genre", _normalize_upper(material.genre))] += base_weight
        weights[("department", _normalize_upper(material.department))] += base_weight
        weights[("language", _normalize_upper(material.language))] += base_weight
        weights[("author", _normalize_upper(material.author))] += base_weight

    return weights, material_ids


def _reservation_weights_for_user(user):
    weights = Counter()
    material_ids = set()
    if not user or not getattr(user, "is_authenticated", False):
        return weights, material_ids

    for reservation in Reservation.objects.select_related("material_id").filter(member=user):
        material = getattr(reservation, "material_id", None)
        if not material:
            continue

        base_weight = 2
        if _normalize_upper(getattr(reservation, "status", "")) == "CANCELLED":
            base_weight = 1

        material_ids.add(str(material.id))
        weights[("category", _normalize_upper(material.category))] += base_weight
        weights[("genre", _normalize_upper(material.genre))] += base_weight
        weights[("department", _normalize_upper(material.department))] += base_weight
        weights[("language", _normalize_upper(material.language))] += base_weight
        weights[("author", _normalize_upper(material.author))] += base_weight

    return weights, material_ids


def _return_weights_for_user(user):
    weights = Counter()
    material_ids = set()
    if not user or not getattr(user, "is_authenticated", False):
        return weights, material_ids

    for returned in Return.objects.select_related("borrow__material").filter(borrow__member=user):
        material = getattr(getattr(returned, "borrow", None), "material", None)
        if not material:
            continue

        base_weight = 2
        if _safe_decimal(getattr(returned, "fine_amount", 0)) > 0:
            base_weight = 1

        material_ids.add(str(material.id))
        weights[("category", _normalize_upper(material.category))] += base_weight
        weights[("genre", _normalize_upper(material.genre))] += base_weight
        weights[("department", _normalize_upper(material.department))] += base_weight
        weights[("language", _normalize_upper(material.language))] += base_weight
        weights[("author", _normalize_upper(material.author))] += base_weight

    return weights, material_ids


def build_user_preference_profile(user):
    borrow_weights, borrowed_ids = _borrow_weights_for_user(user)
    reservation_weights, reserved_ids = _reservation_weights_for_user(user)
    return_weights, returned_ids = _return_weights_for_user(user)

    weights = Counter()
    weights.update(borrow_weights)
    weights.update(reservation_weights)
    weights.update(return_weights)

    excluded_material_ids = borrowed_ids | reserved_ids | returned_ids
    interaction_count = len(borrowed_ids) + len(reserved_ids) + len(returned_ids)

    return {
        "weights": weights,
        "excluded_material_ids": excluded_material_ids,
        "interaction_count": interaction_count,
    }


def _global_popularity_maps():
    borrow_counter = Counter(
        str(material_id)
        for material_id in Borrow.objects.values_list("material_id", flat=True)
        if material_id
    )
    reservation_counter = Counter(
        str(material_id)
        for material_id in Reservation.objects.values_list("material_id", flat=True)
        if material_id
    )
    overdue_counter = Counter(
        str(material_id)
        for material_id in Borrow.objects.filter(status="OVERDUE").values_list("material_id", flat=True)
        if material_id
    )

    return {
        "borrow": borrow_counter,
        "reservation": reservation_counter,
        "overdue": overdue_counter,
    }


def _published_year_score(published_date):
    if not published_date:
        return Decimal("0")
    try:
        year_gap = max(timezone.now().year - published_date.year, 0)
    except Exception:
        return Decimal("0")
    return Decimal("1.5") if year_gap <= 2 else Decimal("0.5") if year_gap <= 5 else Decimal("0")


def _material_matches(material: RecommendationContext, field: str, expected_value: str) -> bool:
    candidate = getattr(material, field, "")
    return bool(candidate and expected_value and candidate == expected_value)


def _recommendation_reason(material: RecommendationContext, weights: Counter) -> list[str]:
    reasons = []
    reason_map = {
        "category": "Matches categories you often use",
        "genre": "Matches genres you prefer",
        "department": "Relevant to your department interests",
        "language": "Matches your reading language",
        "author": "Includes an author you interact with often",
    }

    for field, message in reason_map.items():
        if weights.get((field, getattr(material, field, "")), 0) > 0:
            reasons.append(message)

    if material.material_type == "PHYSICAL" and material.available_copies > 0:
        reasons.append("Available now for borrowing")
    if material.material_type == "DIGITAL":
        reasons.append("Available instantly as a digital resource")

    return reasons[:3]


def _score_material(
    material: RecommendationContext,
    weights: Counter,
    popularity_maps: dict[str, Counter],
) -> Decimal:
    score = Decimal("0")

    for field in ("category", "genre", "department", "language", "author"):
        score += Decimal(weights.get((field, getattr(material, field, "")), 0))

    material_id = material.material_id
    borrow_popularity = popularity_maps["borrow"].get(material_id, 0)
    reservation_popularity = popularity_maps["reservation"].get(material_id, 0)
    overdue_count = popularity_maps["overdue"].get(material_id, 0)

    score += Decimal(borrow_popularity) * Decimal("1.2")
    score += Decimal(reservation_popularity) * Decimal("0.8")
    score -= Decimal(overdue_count) * Decimal("0.4")

    if material.material_type == "PHYSICAL":
        if material.available_copies > 0:
            score += Decimal("2")
        if material.can_borrow:
            score += Decimal("1")
    else:
        score += Decimal("1.5")
        if material.format == "PDF":
            score += Decimal("0.5")

    score += _published_year_score(material.published_date)
    return score


def _serialize_material(material: RecommendationContext, score: Decimal, reasons: Iterable[str]):
    return {
        "id": material.material_id,
        "material_type": material.material_type,
        "title": material.title,
        "author": material.author,
        "category": material.category,
        "genre": material.genre,
        "department": material.department,
        "language": material.language,
        "published_date": material.published_date,
        "available_copies": material.available_copies,
        "total_copies": material.total_copies,
        "format": material.format,
        "file_size": material.file_size,
        "price": str(material.price),
        "can_borrow": material.can_borrow,
        "score": float(round(score, 2)),
        "reasons": list(reasons),
    }


def recommend_for_user(user, *, limit=8, material_type="all", exclude_material_id=None):
    materials = _load_materials(material_type)
    profile = build_user_preference_profile(user)
    popularity_maps = _global_popularity_maps()
    exclude_ids = set(profile["excluded_material_ids"])

    if exclude_material_id:
        exclude_ids.add(str(exclude_material_id))

    ranked = []
    for material in materials:
        if material.material_id in exclude_ids:
            continue

        score = _score_material(material, profile["weights"], popularity_maps)
        if score <= 0 and profile["interaction_count"] > 0:
            continue

        reasons = _recommendation_reason(material, profile["weights"])
        if not reasons:
            reasons = ["Popular with other library users"]

        ranked.append((score, material, reasons))

    ranked.sort(
        key=lambda item: (
            item[0],
            item[1].available_copies,
            item[1].title.lower(),
        ),
        reverse=True,
    )

    strategy = "personalized" if profile["interaction_count"] > 0 else "popular"
    results = [
        _serialize_material(material, score, reasons)
        for score, material, reasons in ranked[: max(_safe_int(limit), 1)]
    ]

    return {
        "strategy": strategy,
        "interaction_count": profile["interaction_count"],
        "results": results,
    }


def _find_material_by_id(material_id):
    material_id = str(material_id)
    physical = PhysicalMaterial.objects.filter(id=material_id).first()
    if physical:
        return _material_to_context(physical, "PHYSICAL")

    digital = DigitalMaterial.objects.filter(id=material_id).first()
    if digital:
        return _material_to_context(digital, "DIGITAL")

    return None


def recommend_similar_materials(material_id, *, limit=6):
    target = _find_material_by_id(material_id)
    if not target:
        return None

    ranked = []
    for candidate in _load_materials("all"):
        if candidate.material_id == target.material_id:
            continue

        score = Decimal("0")
        reasons = []

        if candidate.category and candidate.category == target.category:
            score += Decimal("4")
            reasons.append("Same category")
        if candidate.genre and candidate.genre == target.genre:
            score += Decimal("3")
            reasons.append("Same genre")
        if candidate.department and candidate.department == target.department:
            score += Decimal("2")
            reasons.append("Same department")
        if candidate.language and candidate.language == target.language:
            score += Decimal("1")
            reasons.append("Same language")
        if candidate.author and candidate.author == target.author:
            score += Decimal("2.5")
            reasons.append("Same author")
        if candidate.material_type == target.material_type:
            score += Decimal("1")

        if candidate.material_type == "PHYSICAL" and candidate.available_copies > 0:
            score += Decimal("1")

        if score <= 0:
            continue

        ranked.append((score, candidate, reasons[:3] or ["Related to this material"]))

    ranked.sort(
        key=lambda item: (
            item[0],
            item[1].available_copies,
            item[1].title.lower(),
        ),
        reverse=True,
    )

    return {
        "target": _serialize_material(target, Decimal("0"), ["Reference material"]),
        "results": [
            _serialize_material(material, score, reasons)
            for score, material, reasons in ranked[: max(_safe_int(limit), 1)]
        ],
    }

