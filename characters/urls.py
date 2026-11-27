from django.urls import path, register_converter

from . import api, hosted, views


class CodeConverter:
    regex = r"FC[CV]\d{5,}"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(CodeConverter, "code")

app_name = "characters"
urlpatterns = [
    path("", views.home, name="home"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("BingSiteAuth.xml", views.bing_site_auth, name="bing_site_auth"),
    path("characters/", views.character_list, name="list"),
    path("thanks/", views.thanks, name="thanks"),
    path("downloads/", views.downloads, name="downloads"),
    path("documents/", hosted.index, name="documents"),
    path("documents/<slug:slug>/", hosted.page, name="hosted"),
    path("documents/<slug:slug>/images_web/<str:name>", hosted.image, name="hosted_image"),
    path("downloads/<str:version>/<path:name>", views.download_file, name="download_file"),
    path("characters/new/", views.character_create, name="create"),
    path("id/<code:code>", views.by_code, name="by_code"),
    path("id/<code:code>/edit/", views.edit_by_code, name="edit"),
    path("id/<code:code>/delete/", views.delete_by_code, name="delete"),
    path("id/<code:code>/history/", views.history_by_code, name="history_by_code"),
    path("id/<code:code>/values/new/", views.value_create, name="value_create"),
    path("id/<code:code>/translate/", views.translate, name="translate"),
    path("languages/", views.languages, name="languages"),
    path("languages/<str:lang>/next/", views.translate_next, name="translate_next"),
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
    path("review/<slug:kind>/<int:pk>/", views.review_request, name="review_request"),
    path("changes/", views.recent_changes, name="recent_changes"),
    path("api/", views.api_docs, name="api_docs"),
    path("api/v1/characters/", api.characters, name="api_characters"),
    path("api/v1/characters/<code:code>", api.character, name="api_character"),
    path("api/v1/value-options/<code:code>", api.value_option, name="api_value_option"),
    path("api/v1/releases/", api.releases, name="api_releases"),
    path("names/<slug:mode>/", views.set_name_mode, name="set_name_mode"),
    path("account/", views.account, name="account"),
    path("account/agree/", views.agree, name="agree"),
    path("account/delete/", views.delete_account, name="delete_account"),
    path("privacy/", views.privacy, name="privacy"),
    path("accessibility/", views.accessibility, name="accessibility"),
]
