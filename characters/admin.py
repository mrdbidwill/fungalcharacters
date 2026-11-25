from django.contrib import admin
from django.contrib.auth.models import Group

from . import models

for m in (models.Part, models.ObservationMethod, models.FungusType, models.SourceType):
    admin.site.register(m)

admin.site.register(models.ItemMeta, list_display=("item_type", "item_id", "created_by", "is_hidden"),
                    list_filter=("item_type", "is_hidden"))

# Groups (bundles of permissions for several users) are not used: Will is the only admin (docs/DECISIONS.md).
admin.site.unregister(Group)
