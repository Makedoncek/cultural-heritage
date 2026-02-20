from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from objects.models import Tag, CulturalObject
import random

TAGS_DATA = [
    {'name': 'Замок', 'slug': 'zamok', 'icon': '🏰'},
    {'name': 'Церква', 'slug': 'tserkva', 'icon': '⛪'},
    {'name': 'Музей', 'slug': 'muzey', 'icon': '🏛️'},
    {'name': 'Пам\'ятник', 'slug': 'pamyatnyk', 'icon': '🗿'},
    {'name': 'Парк', 'slug': 'park', 'icon': '🌳'},
    {'name': 'Палац', 'slug': 'palats', 'icon': '👑'},
    {'name': 'Фортеця', 'slug': 'fortetsya', 'icon': '🛡️'},
    {'name': 'Театр', 'slug': 'teatr', 'icon': '🎭'},
    {'name': 'Собор', 'slug': 'sobor', 'icon': '⛪'},
    {'name': 'UNESCO', 'slug': 'unesco', 'icon': '🌍'},
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
        if not settings.DEBUG:
            self.stderr.write(
                self.style.ERROR('Seed data can only run with DEBUG=True')
            )
            return

        count = options['count']
        self.stdout.write(f'Буде створено об\'єктів: {count}')

        self._create_tags()
        user = self._create_test_user()
        self._create_objects(user, count)
        self._print_stats()

    def _create_tags(self):
        self.stdout.write('Крок 1/4: Створення тегів...')
        tags_created = 0
        for tag_data in TAGS_DATA:
            _, created = Tag.objects.get_or_create(
                slug=tag_data['slug'],
                defaults={'name': tag_data['name'], 'icon': tag_data['icon']}
            )
            if created:
                tags_created += 1
        self.stdout.write(
            self.style.SUCCESS(f'Створено {tags_created} нових тегів')
        )

    def _create_test_user(self):
        self.stdout.write('Крок 2/4: Створення тестового користувача...')
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
        self.stdout.write('Крок 3/4: Створення культурних об\'єктів...')
        all_tags = list(Tag.objects.all())
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
            latitude = Decimal(str(round(random.uniform(44.5, 52.0), 6)))
            longitude = Decimal(str(round(random.uniform(22.5, 40.0), 6)))

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

    def _print_stats(self):
        self.stdout.write('\nКрок 4/4: Фінальна статистика...')
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
        self.stdout.write(f'{"=" * 50}')
        self.stdout.write(self.style.SUCCESS('База даних успішно заповнена!'))
