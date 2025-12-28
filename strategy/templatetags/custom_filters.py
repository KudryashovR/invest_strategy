from django import template

register = template.Library()

@register.filter
def remove_after_last_underscore(value):
    """Удаляет все символы после последнего симвла _ (включая сам _)"""

    if '_' in value:
        return value.rsplit('_', 1)[0]
    return value