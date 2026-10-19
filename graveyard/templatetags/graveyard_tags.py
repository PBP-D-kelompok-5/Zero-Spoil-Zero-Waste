from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter(name='rupiah')
def rupiah(value):
    """Format nominal angka ke format mata uang Rupiah dengan pemisah ribuan titik.

    Contoh:
        12000 -> 'Rp 12.000'
        55000.0 -> 'Rp 55.000'
        0 -> 'Rp 0'
    """
    if value is None or value == '':
        return 'Rp 0'
    try:
        num = int(round(Decimal(str(value))))
        formatted = f"{num:,}".replace(',', '.')
        return f"Rp {formatted}"
    except (ValueError, TypeError, InvalidOperation):
        return f"Rp {value}"
