from django.apps import AppConfig
from django.core.checks import register, Error, Warning, Info, Tags

class CmnsdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cmnsd'
    
    def ready(self):
        # Register checks when app is ready
        from . import checks