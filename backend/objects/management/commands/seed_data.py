import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from objects.models import Tag, CulturalObject
from objects.validators import is_within_ukraine

TAGS_DATA = [
    {'name': 'Замок', 'slug': 'zamok', 'icon': '🏰', 'tag_type': 'object'},
    {'name': 'Церква', 'slug': 'tserkva', 'icon': '⛪', 'tag_type': 'object'},
    {'name': 'Музей', 'slug': 'muzey', 'icon': '🏛️', 'tag_type': 'object'},
    {'name': 'Пам\'ятник', 'slug': 'pamyatnyk', 'icon': '🗿', 'tag_type': 'object'},
    {'name': 'Парк', 'slug': 'park', 'icon': '🌳', 'tag_type': 'object'},
    {'name': 'Палац', 'slug': 'palats', 'icon': '👑', 'tag_type': 'object'},
    {'name': 'Фортеця', 'slug': 'fortetsya', 'icon': '🛡️', 'tag_type': 'object'},
    {'name': 'Театр', 'slug': 'teatr', 'icon': '🎭', 'tag_type': 'object'},
    {'name': 'Собор', 'slug': 'sobor', 'icon': '⛪', 'tag_type': 'object'},
    {'name': 'UNESCO', 'slug': 'unesco', 'icon': '🌍', 'tag_type': 'object'},
    {'name': 'Фестиваль', 'slug': 'festyval', 'icon': '🎉', 'tag_type': 'event'},
    {'name': 'Виставка', 'slug': 'vystavka', 'icon': '🖼️', 'tag_type': 'event'},
    {'name': 'Ярмарок', 'slug': 'yarmarok', 'icon': '🎪', 'tag_type': 'event'},
    {'name': 'Концерт', 'slug': 'kontsert', 'icon': '🎵', 'tag_type': 'event'},
    {'name': 'Конференція', 'slug': 'konferentsiya', 'icon': '🎤', 'tag_type': 'event'},
]

SAMPLE_TITLES = [
    'Луцький замок', 'Олеський замок', 'Кам\'янець-Подільська фортеця',
    'Софійський собор', 'Києво-Печерська лавра', 'Львівський оперний театр',
    'Палац Потоцьких', 'Музей народної архітектури', 'Шевченківський парк',
    'Андріївська церква', 'Хотинська фортеця', 'Палац Румянцевих',
]


class Command(BaseCommand):
    help = 'Заповнює базу даних тестовими даними (теги, користувач, об\'єкти)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Кількість об\'єктів, яку треба створити'
        )

    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(f'Буде створено об\'єктів: {count}')

        self._create_tags()
        self._create_admin_user()
        user = self._create_test_user()
        self._create_objects(user, count)
        self._create_events(user)
        self._print_stats()

    def _create_tags(self):
        self.stdout.write('Крок 1/5: Створення тегів...')
        tags_created = 0
        for tag_data in TAGS_DATA:
            _, created = Tag.objects.get_or_create(
                slug=tag_data['slug'],
                defaults={'name': tag_data['name'], 'icon': tag_data['icon'], 'tag_type': tag_data.get('tag_type', 'object')}
            )
            if created:
                tags_created += 1
        self.stdout.write(
            self.style.SUCCESS(f'Створено {tags_created} нових тегів')
        )

    def _create_admin_user(self):
        self.stdout.write('Крок 2/5: Створення адміністратора...')
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@culturemap.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write('  Створено адміністратора: admin / admin123')
        else:
            self.stdout.write('  Адміністратор admin вже існує')

    def _create_test_user(self):
        self.stdout.write('Крок 3/5: Створення тестового користувача...')
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@culturemap.com',
                'first_name': 'Тест',
                'last_name': 'Користувач',
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write('  Створено користувача: testuser / testpass123')
        else:
            self.stdout.write('  Користувач testuser вже існує')
        return user

    def _create_objects(self, user, count):
        self.stdout.write('Крок 4/5: Створення культурних об\'єктів...')
        all_tags = list(Tag.objects.filter(tag_type='object'))
        if not all_tags:
            self.stderr.write(self.style.ERROR('Помилка: Теги не створені!'))
            return

        statuses = [
            CulturalObject.Status.APPROVED,
            CulturalObject.Status.APPROVED,
            CulturalObject.Status.APPROVED,
            CulturalObject.Status.PENDING,
        ]

        for i in range(count):
            title = (
                SAMPLE_TITLES[i] if i < len(SAMPLE_TITLES)
                else f"Тестовий об'єкт #{i + 1}"
            )
            # Rejection sampling: generate random point until it falls inside Ukraine
            while True:
                lat = round(random.uniform(44.5, 52.0), 6)
                lng = round(random.uniform(22.5, 40.0), 6)
                if is_within_ukraine(lat, lng):
                    break
            latitude = Decimal(str(lat))
            longitude = Decimal(str(lng))

            obj = CulturalObject.objects.create(
                title=title,
                description=(
                    f"Тестовий культурний об'єкт. "
                    f"Координати: {latitude}, {longitude}."
                ),
                latitude=latitude,
                longitude=longitude,
                author=user,
                status=random.choice(statuses),
            )
            obj.tags.set(random.sample(all_tags, random.randint(1, 3)))

            if (i + 1) % 10 == 0:
                self.stdout.write(f'  ... створено {i + 1}/{count}')

        self.stdout.write(self.style.SUCCESS(f'Створено {count} об\'єктів'))

    def _create_events(self, user):
        self.stdout.write('Крок 5/6: Створення тестових подій...')
        event_tags = list(Tag.objects.filter(tag_type='event'))
        today = timezone.now()

        events = [
            ('Фестиваль вишиванки', 5, 3),
            ('Виставка народного мистецтва', 10, 7),
            ('Ярмарок кераміки', 20, 5),
            ('Фестиваль вуличної музики', 1, 4),
            ('Виставка сучасного мистецтва', 15, 10),
            ('Фестиваль минулого (expired)', -30, 7),
            ('Ярмарок минулого (expired)', -10, 5),
        ]

        for title, start_offset, duration in events:
            while True:
                lat = round(random.uniform(44.5, 52.0), 6)
                lng = round(random.uniform(22.5, 40.0), 6)
                if is_within_ukraine(lat, lng):
                    break

            start = today + timedelta(days=start_offset)
            end = start + timedelta(days=duration)

            obj = CulturalObject.objects.create(
                title=title,
                description=f'Тестова подія: {title}',
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lng)),
                author=user,
                status=CulturalObject.Status.APPROVED,
                object_type=CulturalObject.ObjectType.EVENT,
                event_start_date=start,
                event_end_date=end,
            )
            obj.tags.set(random.sample(event_tags, min(random.randint(1, 2), len(event_tags))))

        self.stdout.write(self.style.SUCCESS(f'Створено {len(events)} подій'))

    def _print_stats(self):
        self.stdout.write('\nКрок 6/6: Фінальна статистика...')
        total = CulturalObject.objects.count()
        approved = CulturalObject.objects.filter(
            status=CulturalObject.Status.APPROVED
        ).count()
        pending = CulturalObject.objects.filter(
            status=CulturalObject.Status.PENDING
        ).count()
        archived = CulturalObject.objects.filter(
            status=CulturalObject.Status.ARCHIVED
        ).count()

        self.stdout.write(f'\n{"=" * 50}')
        self.stdout.write(f'  Тегів: {Tag.objects.count()}')
        self.stdout.write(f'  Користувачів: {User.objects.count()}')
        self.stdout.write(f'  Об\'єктів: {total}')
        self.stdout.write(f'    - Approved: {approved}')
        self.stdout.write(f'    - Pending: {pending}')
        self.stdout.write(f'    - Archived: {archived}')
        events = CulturalObject.objects.filter(object_type=CulturalObject.ObjectType.EVENT).count()
        permanent = CulturalObject.objects.filter(object_type=CulturalObject.ObjectType.PERMANENT).count()
        self.stdout.write(f'    - Permanent: {permanent}')
        self.stdout.write(f'    - Events: {events}')
        self.stdout.write(f'{"=" * 50}')
        self.stdout.write(self.style.SUCCESS('База даних успішно заповнена!'))
