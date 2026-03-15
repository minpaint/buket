from __future__ import annotations

import json
import logging

from asgiref.sync import async_to_sync
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .telegram_bot_runtime import process_telegram_update

log = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        expected_secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '').strip()
        provided_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '').strip()

        if expected_secret and provided_secret != expected_secret:
            return HttpResponseForbidden('Invalid Telegram webhook secret.')

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'detail': 'Invalid JSON payload.'}, status=400)

        try:
            async_to_sync(process_telegram_update)(payload)
        except Exception:
            log.exception('Telegram webhook processing failed.')
            return JsonResponse({'ok': False}, status=500)

        return JsonResponse({'ok': True})
