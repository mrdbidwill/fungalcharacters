"""Who may edit or delete what (docs/DECISIONS.md, "Users and editing" and "Admin").

- Logged-in users edit only their own work. Items from a data release are
  edited only by the admin (Will), who can edit anything.
- A creator cannot delete an item once others have added to it.
- Value types and sources still in use cannot be deleted by anyone until the
  items using them are changed.
"""
from .forms import item_type_of
from .models import Character, DisplayOption, ItemMeta, Source, ValueOption


def is_admin(user):
    return user.is_authenticated and user.is_active and user.is_superuser


def creator_id(obj):
    return (
        ItemMeta.objects.filter(item_type=item_type_of(obj), item_id=obj.pk)
        .values_list("created_by_id", flat=True).first()
    )


def can_edit(user, obj):
    if not (user.is_authenticated and user.is_active):
        return False
    return user.is_superuser or (creator_id(obj) is not None and creator_id(obj) == user.id)


def delete_blockers(user, obj):
    """Reasons a delete cannot go ahead. Empty list means it is allowed."""
    if isinstance(obj, Character):
        if is_admin(user):
            return []
        reasons = []
        value_ids = list(obj.value_options.values_list("pk", flat=True))
        own = set(ItemMeta.objects.filter(item_type="LookupItem", item_id__in=value_ids, created_by=user)
                  .values_list("item_id", flat=True))
        others = len(set(value_ids) - own)
        if others:
            reasons.append(f"{others} value option(s) on it were added by other users.")
        if obj.core_sequences.exists():
            reasons.append("It is part of a core character order.")
        return reasons
    if isinstance(obj, ValueOption):
        return []
    if isinstance(obj, DisplayOption):
        n = obj.characters.count()
        return [f"{n} character(s) use this value type. Change them first."] if n else []
    if isinstance(obj, Source):
        reasons = []
        n = obj.characters.count()
        if n:
            reasons.append(f"{n} character(s) cite this source. Change them first.")
        n = obj.value_options.count()
        if n:
            reasons.append(f"{n} value option(s) cite this source. Change them first.")
        return reasons
    return ["This kind of item is managed by the admin."]
