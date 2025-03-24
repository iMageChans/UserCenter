from django.apps import AppConfig


class VoiceHubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'voice_hub'

    def ready(self):
        import voice_hub.signals
