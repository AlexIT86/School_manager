from datetime import datetime, timedelta, time as time_cls
from django import template


register = template.Library()


@register.filter
def add_minutes(value, minutes):
    """
    Adaugă un număr de minute la un obiect de tip time și returnează un nou time.
    Se folosește în template: {{ some_time|add_minutes:50|time:"H:i" }}
    """
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return value

    if value is None:
        return value

    # Acceptă atât datetime.time cât și string 'HH:MM'
    if isinstance(value, str):
        try:
            hours, mins = map(int, value.split(':')[:2])
            base_time = time_cls(hours, mins)
        except Exception:
            return value
    else:
        base_time = value

    dummy_date = datetime(2000, 1, 1, base_time.hour, base_time.minute, 0)
    new_dt = dummy_date + timedelta(minutes=minutes)
    return time_cls(new_dt.hour, new_dt.minute)


@register.filter
def get_hours(entries):
    """
    Returnează lista numerelor de oră (numar_ora) dintr-o listă/queryset de intrări de orar.
    Permite în template: {% if hour not in day_data.entries|get_hours %}
    """
    try:
        return [getattr(e, 'numar_ora', None) for e in entries]
    except Exception:
        return []


@register.filter
def get_item(mapping, key):
    """Accesează mapping[key] în template-urile Django (fallback la listă goală)."""
    try:
        return mapping.get(key, [])
    except Exception:
        return []


@register.filter
def index(sequence, position):
    """Returnează elementul de pe poziția dată dintr-o listă/tuplu."""
    try:
        pos = int(position)
        return sequence[pos]
    except Exception:
        return None

