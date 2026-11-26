from django.conf import settings
from .models import Release


def data_release(request):
    release = Release.objects.order_by("-released_at", "-id").first()
    return {
        "data_release": release,
        "scientific_names": request.COOKIES.get("names") == "scientific",
        "published_languages": [(c, n) for c, n in settings.LANGUAGES if c in settings.PUBLISHED_LANGUAGES],
    }
