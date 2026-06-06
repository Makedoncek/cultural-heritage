import json

from django.core.management.base import BaseCommand, CommandError

from objects.models import Tag, TagTranslation

VALID_LANGS = {'en', 'pl', 'de'}


class Command(BaseCommand):
    help = 'Імпортує теги з перекладами з JSON-файлу'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Шлях до JSON-файлу з тегами')

    def handle(self, *args, **options):
        path = options['file']
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Файл не знайдено: {path}')
        except json.JSONDecodeError as e:
            raise CommandError(f'Некоректний JSON: {e}')

        items = data.get('tags', data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise CommandError('Очікується масив тегів або {"tags": [...]}')

        created, skipped, translations_added, errors = 0, 0, 0, []

        for i, item in enumerate(items):
            slug = (item.get('slug') or '').strip()
            name = (item.get('name') or '').strip()
            icon = (item.get('icon') or '').strip()
            tag_type = item.get('tag_type', 'object')

            if not slug or not name or not icon:
                errors.append(f'#{i}: відсутні slug/name/icon')
                continue
            if tag_type not in ('object', 'event'):
                errors.append(f'#{i} «{name}»: некоректний tag_type «{tag_type}»')
                continue
            # name теж unique — конфлікт назви з іншим slug ламає get_or_create
            if Tag.objects.filter(name__iexact=name).exclude(slug=slug).exists():
                errors.append(f'#{i} «{name}»: назва вже зайнята іншим тегом')
                continue

            tag, was_created = Tag.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'tag_type': tag_type},
            )
            if was_created:
                created += 1
            else:
                skipped += 1

            for lang, tr_name in (item.get('translations') or {}).items():
                if lang not in VALID_LANGS or not (tr_name or '').strip():
                    errors.append(f'#{i} «{name}»: пропущено переклад [{lang}]')
                    continue
                _, tr_created = TagTranslation.objects.update_or_create(
                    tag=tag,
                    language=lang,
                    defaults={'name': tr_name.strip()},
                )
                if tr_created:
                    translations_added += 1

        self.stdout.write(self.style.SUCCESS(
            f'Тегів створено: {created}, вже існувало: {skipped}, '
            f'перекладів додано: {translations_added}, помилок: {len(errors)}'
        ))
        for err in errors:
            self.stdout.write(self.style.WARNING(f'  {err}'))
