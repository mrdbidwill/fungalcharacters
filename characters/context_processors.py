from .models import Release


def data_release(request):
    release = Release.objects.order_by("-released_at", "-id").first()
    return {
        "data_release": release,
        "scientific_names": request.session.get("names") == "scientific",
    }
