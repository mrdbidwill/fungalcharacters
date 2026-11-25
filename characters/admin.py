from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Character, CoreSequence, DisplayOption, FungusType, ObservationMethod,
    Part, Source, SourceType, ValueOption,
)


class ValueOptionInline(admin.TabularInline):
    model = ValueOption
    extra = 0
    fields = ("sort_order", "name", "description", "source", "is_hidden")


@admin.register(Character)
class CharacterAdmin(SimpleHistoryAdmin):
    list_display = ("id", "name", "part", "observation_method", "display_option", "is_hidden")
    list_filter = ("part", "observation_method", "display_option", "is_hidden")
    search_fields = ("name", "description")
    inlines = [ValueOptionInline]


for model in (Part, ObservationMethod, FungusType, DisplayOption, SourceType, Source, ValueOption, CoreSequence):
    admin.site.register(model, SimpleHistoryAdmin)
