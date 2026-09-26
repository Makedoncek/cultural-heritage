import json

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from objects.models import (
    LANGUAGE_CHOICES, CulturalObject, Route, RouteStop, RouteTranslation, Tag, TranslationStatus,
)
from objects.services.ors import ORSError, get_directions

TRANSLATION_LANGS = {code for code, _label in LANGUAGE_CHOICES} - {'uk'}
PROFILES = ('foot-walking', 'cycling-regular', 'driving-car')


class Command(BaseCommand):
    help = (
        'Імпортує туристичні маршрути з JSON-файлу (зупинки задаються назвами об\'єктів). '
        'Опційно: "translations": {"en": {"title", "description"}}, "is_featured", '
        '"profile" (foot-walking / cycling-regular / driving-car) для --with-geometry.'
    )

    def add_arguments(self, parser):
        parser.add_argument('file', help='Шлях до JSON-файлу з маршрутами')
        parser.add_argument(
            '--username',
            default='osavenko',
            help='Автор маршрутів (default: osavenko)'
        )
        parser.add_argument(
            '--with-geometry',
            action='store_true',
            help='Одразу розрахувати геометрію реальними дорогами через OpenRouteService (потрібен ORS_API_KEY)'
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

        with_geometry = options['with_geometry']
        if with_geometry and not settings.ORS_API_KEY:
            raise CommandError('--with-geometry потребує ORS_API_KEY')

        tags_by_slug = {t.slug: t for t in Tag.objects.all()}
        created, skipped, errors = 0, 0, []
        translations_created, geometries = 0, 0

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

            with transaction.atomic():
                route = Route.objects.create(
                    title=title,
                    description=item.get('description', '')[:2000],
                    visibility=Route.Visibility.PUBLIC,
                    status=Route.Status.APPROVED,
                    author=author,
                    estimated_duration_minutes=item.get('estimated_duration_minutes'),
                    is_featured=bool(item.get('is_featured')),
                    original_language='uk',
                )
                route.tags.set(tags_by_slug[s] for s in item.get('tags', []))
                for order, (obj, note) in enumerate(resolved, start=1):
                    RouteStop.objects.create(
                        route=route, cultural_object=obj, order=order, note=note[:500]
                    )
                translations_created += self._create_translations(route, item, author, errors, i)
            created += 1
            if missing:
                errors.append(f'#{i} «{title}»: створено без відсутніх зупинок {missing}')

            if with_geometry:
                try:
                    self._compute_geometry(route, resolved, item.get('profile'))
                    geometries += 1
                except ORSError as e:
                    errors.append(f'#{i} «{title}»: геометрію не розраховано ({e})')

        self.stdout.write(self.style.SUCCESS(
            f'Маршрутів створено: {created}, пропущено (дублікати): {skipped}, перекладів: {translations_created}, '
            f'геометрій: {geometries}, зауважень: {len(errors)}'
        ))
        for err in errors:
            self.stdout.write(self.style.WARNING(f'  {err}'))

    @staticmethod
    def _create_translations(route, item, author, errors, i):
        count = 0
        for lang, tr in (item.get('translations') or {}).items():
            tr_title = (tr.get('title') or '').strip()
            tr_description = (tr.get('description') or '').strip()
            if lang not in TRANSLATION_LANGS or not tr_title or not tr_description:
                errors.append(f'#{i} «{route.title}»: пропущено неповний переклад [{lang}]')
                continue
            RouteTranslation.objects.create(
                route=route,
                language=lang,
                title=tr_title[:200],
                description=tr_description[:2000],
                status=TranslationStatus.APPROVED,
                submitted_by=author,
            )
            count += 1
        return count

    @staticmethod
    def _compute_geometry(route, resolved, profile):
        coords = [(float(obj.longitude), float(obj.latitude)) for obj, _note in resolved]
        result = get_directions(coords, profile=profile if profile in PROFILES else 'foot-walking')
        route.route_geometry = result['geometry']
        route.route_distance_m = result['distance_m']
        route.route_duration_s = result['duration_s']
        route.geometry_updated_at = timezone.now()
        route.save(update_fields=['route_geometry', 'route_distance_m', 'route_duration_s',
                                  'geometry_updated_at', 'updated_at'])
