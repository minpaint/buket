from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        import os
        import sys
        import atexit
        import subprocess
        from pathlib import Path

        # BOT_AUTOSTART=false — отключает автозапуск бота (для production,
        # где бот запускается отдельным сервисом/воркером).
        # По умолчанию (переменная не задана) — бот запускается автоматически.
        if os.environ.get('BOT_AUTOSTART', '').lower() == 'false':
            return

        # Запускаем бота только в основном процессе Django.
        # При runserver Django запускает два процесса: reloader и основной.
        # RUN_MAIN=true стоит только в основном — именно там запускаем бота.
        is_dev_main = os.environ.get('RUN_MAIN') == 'true'
        # В production (gunicorn и т.д.) RUN_MAIN не устанавливается вообще.
        is_prod_or_cmd = os.environ.get('RUN_MAIN') is None

        if not is_dev_main and not is_prod_or_cmd:
            return

        # Защита от повторного запуска при hot-reload в production
        if os.environ.get('DJANGO_BOT_STARTED') == '1':
            return
        os.environ['DJANGO_BOT_STARTED'] = '1'

        # Не запускаем при служебных командах manage.py
        skip_commands = ('migrate', 'makemigrations', 'shell', 'test',
                         'collectstatic', 'check', 'createsuperuser',
                         'dbshell', 'showmigrations', 'sqlmigrate',
                         'run_bot')
        if any(cmd in sys.argv for cmd in skip_commands):
            return

        # Путь к боту — папка telegram-bot рядом с backend
        bot_dir = Path(__file__).resolve().parent.parent.parent / 'telegram-bot'
        if not bot_dir.exists():
            return

        env_file = bot_dir / '.env'
        if not env_file.exists():
            return

        log_file = bot_dir / 'bot.log'
        log_fh = open(log_file, 'a', encoding='utf-8')

        proc = subprocess.Popen(
            [sys.executable, '-m', 'bot.main'],
            cwd=str(bot_dir),
            stdout=log_fh,
            stderr=log_fh,
        )

        # Останавливаем бота при завершении Django
        def _stop_bot():
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            try:
                log_fh.close()
            except Exception:
                pass

        atexit.register(_stop_bot)
