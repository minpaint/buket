from .models import Ticker


def ticker(request):
    items = list(Ticker.objects.filter(is_active=True).order_by('sort_order').values_list('text', flat=True))
    return {'ticker_items': items}
