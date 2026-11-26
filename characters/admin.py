from django.contrib import admin
from django.contrib.auth.models import Group

from . import models

for m in (models.Part, models.ObservationMethod, models.FungusType, models.SourceType):
    admin.site.register(m)

admin.site.register(models.ItemMeta, list_display=("item_type", "item_id", "created_by", "is_hidden"),
                    list_filter=("item_type", "is_hidden"))

# Groups (bundles of permissions for several users) are not used: Will is the only admin (docs/DECISIONS.md).
admin.site.unregister(Group)


@admin.register(models.ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):
    """The "Needs review" list (docs/DECISIONS.md, Admin)."""
    list_display = ("created_at", "item_link", "short_note", "reporter", "resolved")
    list_filter = ("resolved", "item_type")
    search_fields = ("item_label", "note")
    readonly_fields = ("item_type", "item_id", "item_label", "page", "note", "reporter", "created_at")
    fields = ("item_label", "page", "note", "reporter", "created_at", "resolved", "resolved_note")
    actions = ["mark_resolved"]

    @admin.display(description="Item")
    def item_link(self, obj):
        from django.utils.html import format_html
        return format_html('<a href="{}">{}</a>', obj.page, obj.item_label)

    @admin.display(description="Note")
    def short_note(self, obj):
        return (obj.note[:80] + "…") if len(obj.note) > 80 else obj.note

    @admin.action(description="Mark selected as resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(resolved=True)

    def has_add_permission(self, request):
        return False
