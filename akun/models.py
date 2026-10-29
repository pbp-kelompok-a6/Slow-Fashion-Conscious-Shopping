from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
# nyimpen data
class Profile(models.Model): 
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_seller = models.BooleanField(default=False)
    bio = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User, dispatch_uid="akun.ensure_profile")
def ensure_profile(sender, instance, raw=False, **kwargs):
    if not raw:
        Profile.objects.get_or_create(user=instance)
