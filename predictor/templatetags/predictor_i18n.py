from __future__ import annotations

from django import template
from django.utils.translation import gettext


register = template.Library()


@register.filter
def localized_display(value):
    """Translate a runtime display label without changing its stored value."""
    if value is None:
        return ""
    return gettext(str(value))

@register.filter
def localized_structure(value):
    """Translate display-only strings recursively inside JSON-ready structures."""
    if isinstance(value, dict):
        return {
            key: localized_structure(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [localized_structure(item) for item in value]
    if isinstance(value, tuple):
        return tuple(localized_structure(item) for item in value)
    if isinstance(value, str):
        return gettext(value)
    return value
