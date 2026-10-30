from django.core.management.base import BaseCommand
from akun.models import Profile


class Command(BaseCommand):
    help = "Set is_seller=True untuk akun seller*"

    def handle(self, *args, **options):
        n = Profile.objects.filter(user__username__startswith="seller").update(is_seller=True)
        self.stdout.write(f"{n} seller diperbarui")