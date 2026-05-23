"""Management command для перевірки використання Cloudinary квоти (фото, аудіо та інші media)."""
from cloudinary import api as cloudinary_api
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Показує поточне використання Cloudinary квоти (storage, bandwidth, transformations) для всіх media — фото, аудіо тощо.'

    def handle(self, *args, **options):
        try:
            usage = cloudinary_api.usage()
        except Exception as e:
            self.stderr.write(f'Помилка отримання usage: {e}')
            return

        plan = usage.get('plan', 'unknown')
        credits_used = usage.get('credits', {}).get('usage', 0)
        credits_limit = usage.get('credits', {}).get('limit', 0)
        storage_bytes = usage.get('storage', {}).get('usage', 0)
        bandwidth_bytes = usage.get('bandwidth', {}).get('usage', 0)
        transformations = usage.get('transformations', {}).get('usage', 0)

        self.stdout.write(self.style.HTTP_INFO(f'Plan: {plan}'))
        self.stdout.write(f'Credits: {credits_used} / {credits_limit}')
        self.stdout.write(f'Storage: {storage_bytes / (1024**3):.2f} GB')
        self.stdout.write(f'Bandwidth (last 30 days): {bandwidth_bytes / (1024**3):.2f} GB')
        self.stdout.write(f'Transformations: {transformations}')

        pct = (credits_used / credits_limit * 100) if credits_limit else 0
        if pct > 80:
            self.stdout.write(self.style.WARNING(f'Використання {pct:.0f}% — наближення до ліміту.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Використання {pct:.0f}%.'))
