import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Creates an admin superuser from environment variables if one does not exist'

    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD')
        email    = os.environ.get('ADMIN_EMAIL', '')

        if not password:
            self.stdout.write('ADMIN_PASSWORD not set — skipping.')
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Admin user "{username}" already exists — skipping.')
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(f'Superuser "{username}" created.')
