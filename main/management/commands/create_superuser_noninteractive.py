# main/management/commands/create_superuser_noninteractive.py
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Creates a superuser non-interactively using environment variables.'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.getenv('DJANGO_SUPERUSER_USERNAME')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

        if not all([username, email, password]):
            self.stdout.write(self.style.ERROR(
                'Environment variables DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD must be set.'
            ))
            return

        try:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, email=email, password=password) # type: ignore
                self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully.'))
            else:
                self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists. Skipping creation.'))
        except IntegrityError:
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists (IntegrityError). Skipping creation.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {e}'))

