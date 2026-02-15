from django.utils import translation


class ForceRussianAdminLocaleMiddleware:
    """
    Enforce Russian locale in Django admin regardless of browser cookies.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin'):
            translation.activate('ru')
            request.LANGUAGE_CODE = 'ru'
        response = self.get_response(request)
        if request.path.startswith('/admin'):
            translation.deactivate()
        return response

