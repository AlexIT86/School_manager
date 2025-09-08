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

    # Normalizează valoarea de intrare la un obiect time
    base_time = None

    # 1) Dacă e deja datetime.time
    if hasattr(value, 'hour') and hasattr(value, 'minute'):
        base_time = value
    # 2) Dacă e datetime, extrage time-ul
    elif hasattr(value, 'time') and callable(getattr(value, 'time')):
        try:
            base_time = value.time()
        except Exception:
            base_time = None
    # 3) Dacă e int/float -> interpretăm ca oră întreagă (HH:00)
    elif isinstance(value, (int, float)):
        try:
            base_time = time_cls(int(value), 0)
        except Exception:
            base_time = None
    # 4) Dacă e string
    elif isinstance(value, str):
        v = value.strip()
        # format HH:MM
        if ':' in v:
            try:
                hours, mins = map(int, v.split(':')[:2])
                base_time = time_cls(hours, mins)
            except Exception:
                base_time = None
        # format numeric '8' -> 08:00
        elif v.isdigit():
            try:
                base_time = time_cls(int(v), 0)
            except Exception:
                base_time = None

    if base_time is None:
        return value

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


@register.filter
def to_time(value):
    """Normalizează valori (int/float/str) la un obiect datetime.time pentru folosire în template-uri."""
    try:
        # Dacă are atribute hour/minute, presupunem că e time/datetime
        if hasattr(value, 'hour') and hasattr(value, 'minute'):
            # datetime.time
            return value
        if hasattr(value, 'time') and callable(getattr(value, 'time')):
            # datetime -> time
            return value.time()
        if isinstance(value, (int, float)):
            from datetime import time as time_cls
            return time_cls(int(value), 0)
        if isinstance(value, str):
            v = value.strip()
            from datetime import time as time_cls
            if ':' in v:
                hours, mins = map(int, v.split(':')[:2])
                return time_cls(hours, mins)
            if v.isdigit():
                return time_cls(int(v), 0)
    except Exception:
        return value
    return value
