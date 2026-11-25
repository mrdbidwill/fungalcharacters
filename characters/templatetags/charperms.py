from django import template

from characters.permissions import can_edit

register = template.Library()


@register.filter
def editable_by(obj, user):
    return can_edit(user, obj)
