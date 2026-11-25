from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Character, Part


def character_list(request):
    q = request.GET.get("q", "").strip()
    part = request.GET.get("part", "")
    qs = (
        Character.objects.filter(is_hidden=False)
        .select_related("part", "observation_method", "display_option", "created_by")
        .annotate(n_options=Count("value_options"))
        .order_by("name", "id")
    )
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if part.isdigit():
        qs = qs.filter(part_id=int(part))
    page = Paginator(qs, 100).get_page(request.GET.get("page"))
    return render(request, "characters/list.html", {
        "page": page, "q": q, "part": part, "parts": Part.objects.order_by("name"),
        "total": Character.objects.filter(is_hidden=False).count(),
    })


def character_detail(request, pk):
    c = get_object_or_404(
        Character.objects.select_related(
            "part", "observation_method", "display_option", "fungus_type", "source", "created_by"
        ),
        pk=pk, is_hidden=False,
    )
    return render(request, "characters/detail.html", {
        "c": c,
        "options": c.value_options.filter(is_hidden=False).select_related("source"),
        "core_sequences": c.core_sequences.select_related("fungus_type"),
        "duplicates": c.possible_duplicates().filter(is_hidden=False),
        "history": c.history.select_related("history_user").order_by("-history_date"),
    })
