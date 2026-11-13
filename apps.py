from django.apps import AppConfig


class CmnsdConfig(AppConfig):
    name = 'cmnsd'

    def ready(self):
        from cmnsd import checks  # noqa: F401 - registers system checks
        from cmnsd import login_throttle  # noqa: F401 - counts failed sign-ins (signals)
