# main/apps.py

from django.apps import AppConfig

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        # IMPORTANT: Import your signals here to ensure they are registered
        # when Django starts. Do NOT put this import at the top level of the file.
        import main.signals
