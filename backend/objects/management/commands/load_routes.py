import json

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from objects.models import CulturalObject, Route, RouteStop, Tag


class Command(BaseCommand):
    help = 'Імпортує туристичні маршрути з JSON-файлу (зупинки задаються назвами об\'єктів)'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Шлях до JSON-файлу з маршрутами')
        parser.add_argument(
            '--username',
            default='osavenko',
            help='Автор маршрутів (default: osavenko)'
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

        items = data.get('routes', data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise CommandError('Очікується масив маршрутів або {"routes": [...]}')

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
            if Route.objects.filter(title__iexact=title).exists():
                skipped += 1
                continue

            stops_data = item.get('stops', [])
            resolved, missing = [], []
            for stop in stops_data:
                obj_title = (stop.get('object_title') or '').strip()
                obj = (
                    CulturalObject.objects
                    .filter(title__iexact=obj_title, status='approved', object_type='permanent')
                    .first()
                )
                if obj and obj.id not in [o.id for o, _ in resolved]:
                    resolved.append((obj, stop.get('note', '')))
                else:
                    missing.append(obj_title)

            if len(resolved) < 2:
                errors.append(f'#{i} «{title}»: замало знайдених зупинок ({len(resolved)}), відсутні: {missing}')
                continue

            unknown_tags = [s for s in item.get('tags', []) if s not in tags_by_slug]
            if unknown_tags:
                errors.append(f'#{i} «{title}»: невідомі теги {unknown_tags}')
                continue

            route = Route.objects.create(
                title=title,
                description=item.get('description', '')[:2000],
                visibility=Route.Visibility.PUBLIC,
                status=Route.Status.APPROVED,
                author=author,
                estimated_duration_minutes=item.get('estimated_duration_minutes'),
                original_language='uk',
            )
            route.tags.set(tags_by_slug[s] for s in item.get('tags', []))
            for order, (obj, note) in enumerate(resolved, start=1):
                RouteStop.objects.create(
                    route=route, cultural_object=obj, order=order, note=note[:500]
                )
            created += 1
            if missing:
                errors.append(f'#{i} «{title}»: створено без відсутніх зупинок {missing}')

        self.stdout.write(self.style.SUCCESS(
            f'Маршрутів створено: {created}, пропущено (дублікати): {skipped}, зауважень: {len(errors)}'
        ))
        for err in errors:
            self.stdout.write(self.style.WARNING(f'  {err}'))
