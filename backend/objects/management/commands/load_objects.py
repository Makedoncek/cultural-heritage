import io
import json
import random
from decimal import Decimal

import cloudinary
import cloudinary.exceptions
import requests
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from objects import cloudinary_service
from objects.models import (
    LANGUAGE_CHOICES, CulturalObject, CulturalObjectTranslation, ObjectPhoto, Tag, TranslationStatus,
)
from objects.validators import is_within_ukraine

TRANSLATION_LANGS = {code for code, _label in LANGUAGE_CHOICES} - {'uk'}
# Wikimedia відхиляє запити без описового User-Agent.
PHOTO_USER_AGENT = 'CultureMapUkraine/1.0 (https://github.com/Makedoncek/cultural-heritage)'


class Command(BaseCommand):
    help = (
        'Імпортує культурні об\'єкти з JSON-файлу (згенерованого LLM, fetch_wiki_objects або вручну). '
        'Опційно: "translations": {"en": {"title", "description"}} — затверджені переклади; '
        '"photos": [{"source_url", "caption"}] — фото, що завантажуються в Cloudinary з --with-photos.'
    )

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
        parser.add_argument(
            '--with-photos',
            action='store_true',
            help='Завантажити фото з "photos" у Cloudinary (потрібні змінні CLOUDINARY_*)'
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

        with_photos = options['with_photos']
        if with_photos and not cloudinary.config().api_secret:
            raise CommandError('--with-photos потребує CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET')
        self.http = requests.Session()
        self.http.headers['User-Agent'] = PHOTO_USER_AGENT

        tags_by_slug = {t.slug: t for t in Tag.objects.all()}
        created, skipped, errors = 0, 0, []
        translations_created, photos_uploaded = 0, 0

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

            too_long = [f for f in ('wikipedia_url', 'official_website') if len(item.get(f) or '') > 200]
            if too_long:
                errors.append(f'#{i} «{title}»: задовгі посилання (>200 символів): {too_long}')
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
            with transaction.atomic():
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
                translations_created += self._create_translations(obj, item, author, errors, i)
            created += 1

            if with_photos:
                for order, photo in enumerate(item.get('photos') or []):
                    try:
                        self._upload_photo(obj, photo, author, order)
                        photos_uploaded += 1
                    except (requests.RequestException, cloudinary.exceptions.Error, KeyError) as e:
                        errors.append(f'#{i} «{title}»: фото не завантажено ({e})')
            self.stdout.write(f'  + {title}')

        self.stdout.write(self.style.SUCCESS(
            f'Створено: {created}, пропущено (дублікати): {skipped}, перекладів: {translations_created}, '
            f'фото: {photos_uploaded}, помилок: {len(errors)}'
        ))
        for err in errors:
            self.stdout.write(self.style.WARNING(f'  {err}'))

    @staticmethod
    def _create_translations(obj, item, author, errors, i):
        count = 0
        for lang, tr in (item.get('translations') or {}).items():
            tr_title = (tr.get('title') or '').strip()
            tr_description = (tr.get('description') or '').strip()
            if lang not in TRANSLATION_LANGS or not tr_title or not tr_description:
                errors.append(f'#{i} «{obj.title}»: пропущено неповний переклад [{lang}]')
                continue
            CulturalObjectTranslation.objects.create(
                cultural_object=obj,
                language=lang,
                title=tr_title[:200],
                description=tr_description,
                status=TranslationStatus.APPROVED,
                submitted_by=author,
            )
            count += 1
        return count

    def _upload_photo(self, obj, photo, author, order):
        response = self.http.get(photo['source_url'], timeout=60)
        response.raise_for_status()
        uploaded = cloudinary_service.upload_photo(io.BytesIO(response.content))
        ObjectPhoto.objects.create(
            cultural_object=obj,
            uploaded_by=author,
            cloudinary_public_id=uploaded['public_id'],
            image_url=uploaded['image_url'],
            thumbnail_url=uploaded['thumbnail_url'],
            caption=(photo.get('caption') or '')[:200],
            status=ObjectPhoto.Status.APPROVED,
            moderated_at=timezone.now(),
            order=order,
            is_author_photo=True,
        )
