from django import template

from characters.consumption import needs_consumption_note
from characters.permissions import can_edit

register = template.Library()


@register.filter
def editable_by(obj, user):
    return can_edit(user, obj)


@register.filter
def consumption_note(obj):
    """True if the shared disclaimer rule wants the short note beside this item."""
    return needs_consumption_note(obj)
