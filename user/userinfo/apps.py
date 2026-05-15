from django.apps import AppConfig


class UserinfoConfig(AppConfig):
    name = 'user.userinfo'

    def ready(self):
        import user.userinfo.models
