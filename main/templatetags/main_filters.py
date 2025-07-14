from django import template

register = template.Library()


@register.filter
def replace(value, arg):
    """
    Replaces all occurrences of a substring with another string in a given string.
    Usage: {{ value|replace:"old,new" }}
    """
    if isinstance(value, str) and isinstance(arg, str):
        try:
            old, new = arg.split(",", 1)  # Split only on the first comma
            return value.replace(old, new)
        except ValueError:
            # Handle cases where arg is not in "old,new" format
            return value  # Return original value if arg is malformed
    return value  # Return original value if not a string
