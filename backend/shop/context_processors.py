from .models import Ticker, SiteSettings


def ticker(request):
    items = list(Ticker.objects.filter(is_active=True).order_by('sort_order').values_list('text', flat=True))
    settings = SiteSettings.objects.first()
    metrika = settings.metrika_counter if settings else ''
    return {'ticker_items': items, 'metrika_counter': metrika}
