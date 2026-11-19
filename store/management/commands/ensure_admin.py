import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = "Create the initial staff user if credentials are provided and no such user exists."
    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")
        if not username or not password:
            self.stdout.write("Admin bootstrap skipped: set DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD.")
            return
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write("Configured admin user already exists.")
            return
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created admin user: {username}"))
