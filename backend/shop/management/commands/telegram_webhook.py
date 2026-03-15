from __future__ import annotations

import asyncio

from aiogram import Bot
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from shop.telegram_bot_runtime import ensure_telegram_bot_path


class Command(BaseCommand):
    help = 'Manage Telegram webhook for the store manager bot.'

    def add_arguments(self, parser):
        action = parser.add_mutually_exclusive_group()
        action.add_argument('--set', action='store_true', help='Register or update webhook.')
        action.add_argument('--delete', action='store_true', help='Delete webhook.')
        action.add_argument('--info', action='store_true', help='Show current webhook info.')
        parser.add_argument('--url', help='Explicit webhook URL override.')
        parser.add_argument(
            '--drop-pending-updates',
            action='store_true',
            help='Drop pending updates when setting or deleting webhook.',
        )

    def handle(self, *args, **options):
        action = 'info'
        if options['set']:
            action = 'set'
        elif options['delete']:
            action = 'delete'

        asyncio.run(self._run(action=action, options=options))

    async def _run(self, action: str, options: dict) -> None:
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '').strip()
        if not bot_token:
            raise CommandError('Set BOT_TOKEN in backend/.env before managing Telegram webhook.')

        ensure_telegram_bot_path()
        from bot.main import BOT_COMMANDS

        bot = Bot(token=bot_token)
        try:
            if action == 'set':
                webhook_url = self._resolve_webhook_url(options.get('url'))
                secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '').strip()
                if not secret:
                    raise CommandError(
                        'Set TELEGRAM_WEBHOOK_SECRET (or BOT_SECRET/TELEGRAM_BOT_SECRET fallback) in backend/.env.'
                    )

                await bot.set_my_commands(BOT_COMMANDS)
                await bot.set_webhook(
                    url=webhook_url,
                    secret_token=secret,
                    drop_pending_updates=options['drop_pending_updates'],
                    allowed_updates=['message', 'callback_query'],
                )
                self.stdout.write(self.style.SUCCESS(f'Webhook set: {webhook_url}'))

            elif action == 'delete':
                await bot.delete_webhook(drop_pending_updates=options['drop_pending_updates'])
                self.stdout.write(self.style.SUCCESS('Webhook deleted.'))

            info = await bot.get_webhook_info()
            self._print_info(info)
        finally:
            await bot.session.close()

    def _resolve_webhook_url(self, override: str | None) -> str:
        if override:
            return override.strip()

        configured_url = getattr(settings, 'TELEGRAM_WEBHOOK_URL', '').strip()
        if configured_url:
            return configured_url

        for host in settings.ALLOWED_HOSTS:
            normalized = host.lstrip('.').strip()
            if not normalized or normalized in {'localhost', '127.0.0.1'}:
                continue
            return f'https://{normalized}/api/v1/telegram/webhook/'

        raise CommandError('Unable to infer webhook URL. Set TELEGRAM_WEBHOOK_URL in backend/.env.')

    def _print_info(self, info) -> None:
        self.stdout.write(f'Webhook URL: {info.url or "not set"}')
        self.stdout.write(f'Pending updates: {info.pending_update_count}')
        self.stdout.write(f'Last error date: {info.last_error_date or "-"}')
        self.stdout.write(f'Last error message: {info.last_error_message or "-"}')
        self.stdout.write(f'Max connections: {info.max_connections}')
