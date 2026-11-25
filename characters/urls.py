from django.urls import path

from . import views

app_name = "characters"
urlpatterns = [
    path("", views.character_list, name="list"),
    path("characters/new/", views.character_create, name="create"),
    path("characters/<int:pk>/", views.character_detail, name="detail"),
    path("characters/<int:pk>/edit/", views.character_edit, name="edit"),
    path("characters/<int:pk>/delete/", views.character_delete, name="delete"),
    path("characters/<int:pk>/options/new/", views.option_create, name="option_create"),
    path("options/<int:pk>/edit/", views.option_edit, name="option_edit"),
    path("options/<int:pk>/delete/", views.option_delete, name="option_delete"),
    path("value-types/", views.value_type_list, name="value_type_list"),
    path("value-types/new/", views.value_type_create, name="value_type_create"),
    path("value-types/<int:pk>/", views.value_type_detail, name="value_type_detail"),
    path("value-types/<int:pk>/edit/", views.value_type_edit, name="value_type_edit"),
    path("value-types/<int:pk>/delete/", views.value_type_delete, name="value_type_delete"),
    path("sources/", views.source_list, name="source_list"),
    path("sources/new/", views.source_create, name="source_create"),
    path("sources/<int:pk>/", views.source_detail, name="source_detail"),
    path("sources/<int:pk>/edit/", views.source_edit, name="source_edit"),
    path("sources/<int:pk>/delete/", views.source_delete, name="source_delete"),
    path("history/<slug:kind>/<int:pk>/", views.history, name="history"),
    path("changes/", views.recent_changes, name="recent_changes"),
    path("accounts/signup/", views.signup, name="signup"),
]
