from django.urls import path, register_converter

from . import views


class CodeConverter:
    regex = r"FC[CV]\d{5,}"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(CodeConverter, "code")

app_name = "characters"
urlpatterns = [
    path("", views.character_list, name="list"),
    path("characters/new/", views.character_create, name="create"),
    path("id/<code:code>", views.by_code, name="by_code"),
    path("id/<code:code>/edit/", views.edit_by_code, name="edit"),
    path("id/<code:code>/delete/", views.delete_by_code, name="delete"),
    path("id/<code:code>/history/", views.history_by_code, name="history_by_code"),
    path("id/<code:code>/values/new/", views.value_create, name="value_create"),
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
    path("hide/<slug:kind>/<int:pk>/", views.toggle_hidden, name="toggle_hidden"),
    path("changes/", views.recent_changes, name="recent_changes"),
    path("names/<slug:mode>/", views.set_name_mode, name="set_name_mode"),
    path("accounts/signup/", views.signup, name="signup"),
]
