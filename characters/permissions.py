"""Who may edit or delete what (docs/DECISIONS.md, "Users and editing" and "Admin").

- Logged-in users edit only their own work. The admin (Will) can edit anything.
- A creator cannot delete an item once others have added to it.
- Value types and sources still in use cannot be deleted by anyone until the
  items using them are changed (nothing is silently removed from others' work).
"""
from .models import Character, DisplayOption, Source, ValueOption


def is_admin(user):
    return user.is_authenticated and user.is_active and user.is_superuser


def can_edit(user, obj):
    if not (user.is_authenticated and user.is_active):
        return False
    return user.is_superuser or obj.created_by_id == user.id


def delete_blockers(user, obj):
    """Reasons a delete cannot go ahead. Empty list means it is allowed."""
    if isinstance(obj, Character):
        if is_admin(user):
            return []
        reasons = []
        others = obj.value_options.exclude(created_by=user).count()
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


def can_delete(user, obj):
    return can_edit(user, obj) and not delete_blockers(user, obj)
