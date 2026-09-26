"""Видаляє з Cloudinary файли, на які не посилається жоден ObjectPhoto / ObjectAudio у БД."""
import cloudinary
from cloudinary import api as cloudinary_api
from django.core.management.base import BaseCommand, CommandError

from objects.models import ObjectAudio, ObjectPhoto

# Фото — resource_type 'image', аудіо Cloudinary зберігає як 'video'.
RESOURCE_TYPES = ('image', 'video')
DELETE_BATCH = 100  # ліміт delete_resources на один виклик


class Command(BaseCommand):
    help = (
        'Показує (або з --yes видаляє) файли Cloudinary з префіксом --prefix, на які не посилається '
        'жоден ObjectPhoto / ObjectAudio у поточній БД. Файли, що використовуються, ніколи не видаляються.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--prefix', default='cultural-heritage/',
                            help='Префікс public_id (default: cultural-heritage/)')
        parser.add_argument('--yes', action='store_true', help='Справді видалити (без нього — лише список)')

    def handle(self, *args, **options):
        if not cloudinary.config().api_secret:
            raise CommandError('Не налаштовано CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET')

        referenced = set(ObjectPhoto.objects.values_list('cloudinary_public_id', flat=True))
        referenced |= set(ObjectAudio.objects.values_list('cloudinary_public_id', flat=True))

        total_deleted = 0
        for resource_type in RESOURCE_TYPES:
            resources = self._list(resource_type, options['prefix'])
            orphans = [r for r in resources if r['public_id'] not in referenced]
            size_mb = sum(r.get('bytes', 0) for r in orphans) / 1024 ** 2
            self.stdout.write(
                f'{resource_type}: усього {len(resources)}, використовуються {len(resources) - len(orphans)}, '
                f'до видалення {len(orphans)} ({size_mb:.1f} MB)'
            )
            for r in orphans[:10]:
                self.stdout.write(f'  - {r["public_id"]}')
            if len(orphans) > 10:
                self.stdout.write(f'  … і ще {len(orphans) - 10}')

            if options['yes'] and orphans:
                ids = [r['public_id'] for r in orphans]
                for start in range(0, len(ids), DELETE_BATCH):
                    cloudinary_api.delete_resources(ids[start:start + DELETE_BATCH], resource_type=resource_type)
                total_deleted += len(ids)

        if options['yes']:
            self.stdout.write(self.style.SUCCESS(f'Видалено файлів: {total_deleted}'))
        else:
            self.stdout.write(self.style.WARNING('Нічого не видалено. Запустіть з --yes, щоб видалити.'))

    @staticmethod
    def _list(resource_type, prefix):
        resources, cursor = [], None
        while True:
            page = cloudinary_api.resources(
                type='upload', resource_type=resource_type, prefix=prefix, max_results=500,
                next_cursor=cursor,
            )
            resources.extend(page.get('resources', []))
            cursor = page.get('next_cursor')
            if not cursor:
                return resources
