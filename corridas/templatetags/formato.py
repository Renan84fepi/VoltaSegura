"""Filtros de exibição no padrão brasileiro (RNF14)."""
from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter
def reais(valor):
    """Decimal('1234.5') → 'R$ 1.234,50'."""
    if valor in (None, ""):
        return "—"
    return f"R$ {number_format(valor, 2, use_l10n=True, force_grouping=True)}"


@register.filter
def km(valor):
    """Decimal('0.45') → '450 m'; Decimal('5.29') → '5,3 km'."""
    if valor in (None, ""):
        return "—"
    if valor < 1:
        return f"{round(valor * 1000)} m"
    return f"{number_format(valor, 1, use_l10n=True)} km"


@register.filter
def estrelas(nota):
    """4 → '★★★★☆'."""
    if not nota:
        return ""
    nota = int(nota)
    return "★" * nota + "☆" * (5 - nota)
