from django.apps import AppConfig
 
 
class DataAwalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "data_awal"
 
    def ready(self):
        from django.db.models.signals import post_migrate
 
        from .seed import seed_dummy_data
 
        post_migrate.connect(seed_dummy_data, sender=self)