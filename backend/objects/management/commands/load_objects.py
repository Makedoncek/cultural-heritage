import json
import random
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from objects.models import CulturalObject, Tag
from objects.validators import is_within_ukraine


class Command(BaseCommand):
    help = 'Імпортує культурні об\'єкти з JSON-файлу (згенерованого LLM або вручну)'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Шлях до JSON-файлу з об\'єктами')
        parser.add_argument(
            '--username',
            default='testuser',
            help='Автор імпортованих об\'єктів (default: testuser)'
        )
        parser.add_argument(
            '--pending-ratio',
            type=float,
            default=0.0,
            help='Частка об\'єктів зі статусом pending, 0..1 (default: 0 — усі approved)'
        )

    def handle(self, *args, **options):
        path = options['file']
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Файл не знайдено: {path}')
        except json.JSONDecodeError as e:
            raise CommandError(f'Некоректний JSON: {e}')

        items = data.get('objects', data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise CommandError('Очікується масив об\'єктів або {"objects": [...]}')

        try:
            author = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            raise CommandError(f'Користувача "{options["username"]}" не існує')

        tags_by_slug = {t.slug: t for t in Tag.objects.all()}
        created, skipped, errors = 0, 0, []

        for i, item in enumerate(items):
            title = (item.get('title') or '').strip()
            if not title:
                errors.append(f'#{i}: відсутній title')
                continue
            if CulturalObject.objects.filter(title__iexact=title).exists():
                skipped += 1
                continue

            try:
                lat, lng = Decimal(str(item['latitude'])), Decimal(str(item['longitude']))
            except (KeyError, ArithmeticError):
                errors.append(f'#{i} «{title}»: некоректні координати')
                continue
            if not is_within_ukraine(lat, lng):
                errors.append(f'#{i} «{title}»: координати поза межами України ({lat}, {lng})')
                continue

            slugs = item.get('tags', [])
            unknown = [s for s in slugs if s not in tags_by_slug]
            if unknown or not slugs:
                errors.append(f'#{i} «{title}»: невідомі або відсутні теги {unknown}')
                continue

            object_type = item.get('object_type', 'permanent')
            start = parse_datetime(item['event_start_date']) if item.get('event_start_date') else None
            end = parse_datetime(item['event_end_date']) if item.get('event_end_date') else None
            if object_type == 'event' and not (start and end):
                errors.append(f'#{i} «{title}»: подія без дат початку/завершення')
                continue

            status = (
                CulturalObject.Status.PENDING
                if random.random() < options['pending_ratio']
                else CulturalObject.Status.APPROVED
            )
            obj = CulturalObject.objects.create(
                title=title,
                description=item.get('description', ''),
                latitude=lat,
                longitude=lng,
                author=author,
                status=status,
                object_type=object_type,
                original_language='uk',
                event_start_date=start,
                event_end_date=end,
                wikipedia_url=item.get('wikipedia_url') or None,
                official_website=item.get('official_website') or None,
                google_maps_url=f'https://www.google.com/maps?q={lat},{lng}',
            )
            obj.tags.set(tags_by_slug[s] for s in slugs)
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Створено: {created}, пропущено (дублікати): {skipped}, помилок: {len(errors)}'
        ))
        for err in errors:
            self.stdout.write(self.style.WARNING(f'  {err}'))
