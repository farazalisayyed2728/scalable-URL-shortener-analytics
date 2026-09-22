import os
from django.core.wsgi import get_wsgi_application

# Default to development settings if not explicitly specified
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_wsgi_application()