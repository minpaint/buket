import sys
import os

# Путь к папке backend на сервере
sys.path.insert(0, '/home/buketby/backend')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flowershop_backend.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
