from django.contrib import admin

from . import models

for m in (models.Part, models.ObservationMethod, models.FungusType, models.SourceType):
    admin.site.register(m)

admin.site.register(models.ItemMeta, list_display=("item_type", "item_id", "created_by", "is_hidden"),
                    list_filter=("item_type", "is_hidden"))
