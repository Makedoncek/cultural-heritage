"""Збирає дані про культурні об'єкти з української Вікіпедії у JSON для `load_objects`.

Для кожної статті: координати (зі статті або Wikidata P625), вступ статті як опис,
англійська назва (з міжмовних посилань або Wikidata), фото з Wikimedia Commons
(лише вільні ліцензії) з автором і ліцензією для підпису. Англійський опис
заповнюється окремо (переклад українського опису) — скрипт залишає його порожнім
і не перезаписує вже наявні переклади при повторному запуску.

Базу даних не змінює.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import requests
from django.core.management.base import BaseCommand, CommandError

UK_API = 'https://uk.wikipedia.org/w/api.php'
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
# Політика Wikimedia вимагає описовий User-Agent з контактом.
USER_AGENT = 'CultureMapUkraine/1.0 (https://github.com/Makedoncek/cultural-heritage)'
PHOTO_WIDTH = 1600
MAX_DESCRIPTION_CHARS = 1500
# Короткий вступ доповнюється абзацами з наступних розділів статті до цієї довжини.
MIN_DESCRIPTION_CHARS = 500
SKIP_SECTIONS = ('примітки', 'джерела', 'література', 'посилання', 'див. також', 'галерея',
                 'виноски', 'зовнішні посилання', 'бібліографія')

DEFAULT_TITLES = Path(__file__).resolve().parents[2] / 'data' / 'wiki_titles.txt'
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / 'data' / 'wiki_objects.json'

UK_SOURCE_NOTE = 'Джерело: Вікіпедія, ліцензія CC BY-SA 4.0.'

# Порядок важливий: перше збігле правило визначає основний тег.
TAG_RULES = [
    ('fortetsya', ('фортец', 'цитадел', 'бастіон')),
    ('zamok', ('замок', 'замку', 'паланок', 'сент-міклош')),
    ('palats', ('палац', 'резиденці', 'садиб', 'маєток')),
    ('sobor', ('собор',)),
    ('tserkva', ('церкв', 'монастир', 'лавр', 'скит', 'костел', 'костьол', 'синагог', 'каплиц')),
    ('teatr', ('театр', 'опер')),
    ('muzey', ('музей', 'заповідник', 'скансен')),
    ('park', ('парк', 'сад', 'дендро', 'софіївка', 'хортиця', 'гора', 'могила')),
    ('pamyatnyk', ('пам\'ятник', 'монумент', 'ворота', 'вежа', 'ратуш', 'будинок', 'держпром',
                   'сходи', 'площа', 'пасаж', 'ротонда', 'альтанка', 'гніздо', 'ольвія', 'херсонес')),
]

HTML_TAG_RE = re.compile(r'<[^>]+>')
HEADING_RE = re.compile(r'^(=+)\s*(.*?)\s*\1$')
PAREN_NOISE_RE = re.compile(r'\s*\((?:[^()]*?(?:вимова|МФА|англ\.|пол\.|рос\.|лат\.|нім\.)[^()]*?)\)')
# Службові позначки редакторів: [джерело?], [уточнити], [коли?] …
MAINTENANCE_TAG_RE = re.compile(r'\s*\[(?:джерело\?|уточнити|[^\]\s]{1,20}\?)\]')
# Залишки шаблонів, які extracts API віддає як текст.
TEMPLATE_JUNK_RE = re.compile(r'^Шаблон:|\|\s*\w+\s*=')
LAST_SENTENCE_RE = re.compile(r'(?<=[.!?…»)])\s+(?=[^.!?…]*:$)')


def drop_dangling_lead_in(paragraph):
    """Прибирає кінцеве речення на кшталт «…складається з:», чий список відфільтровано.

    Повертає '' якщо весь абзац — лише такий вступ до списку.
    """
    if not paragraph.rstrip().endswith(':'):
        return paragraph
    parts = LAST_SENTENCE_RE.split(paragraph.rstrip(), maxsplit=1)
    return parts[0].rstrip() if len(parts) == 2 else ''


class Command(BaseCommand):
    help = 'Збирає об\'єкти з української Вікіпедії у JSON для load_objects (БД не змінює)'

    def add_arguments(self, parser):
        parser.add_argument('--titles', default=str(DEFAULT_TITLES),
                            help='Файл зі списком назв статей uk.wikipedia (рядок = стаття; '
                                 '"Назва | tserkva unesco" задає теги вручну; # — коментар)')
        parser.add_argument('--output', default=str(DEFAULT_OUTPUT), help='Куди записати JSON')
        parser.add_argument('--delay', type=float, default=0.3, help='Пауза між запитами, с')

    def handle(self, *args, **options):
        entries = self._read_titles(options['titles'])
        output = Path(options['output'])
        previous = self._load_previous(output)

        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        self.delay = options['delay']

        objects, problems = [], []
        for n, (title, manual_tags) in enumerate(entries, 1):
            self.stdout.write(f'[{n}/{len(entries)}] {title}')
            try:
                item, warning = self._fetch_object(title, manual_tags)
            except requests.RequestException as e:
                problems.append(f'{title}: мережева помилка {e}')
                continue
            if item is None:
                problems.append(f'{title}: {warning}')
                continue
            if warning:
                problems.append(f'{title}: {warning}')
            old_en = previous.get(item['wikipedia_url'], {}).get('translations', {}).get('en', {})
            if old_en.get('description'):
                item['translations']['en']['description'] = old_en['description']
            if old_en.get('title'):
                item['translations']['en']['title'] = old_en['title']
            if any(o['wikipedia_url'] == item['wikipedia_url'] for o in objects):
                problems.append(f'{title}: дублікат (редирект на вже додану статтю)')
                continue
            objects.append(item)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({'objects': objects}, ensure_ascii=False, indent=2) + '\n',
                          encoding='utf-8')

        without_photo = sum(1 for o in objects if not o['photos'])
        without_en = sum(1 for o in objects if not o['translations']['en']['description'])
        self.stdout.write(self.style.SUCCESS(
            f'Записано {len(objects)} об\'єктів у {output} '
            f'(без фото: {without_photo}, без англ. опису: {without_en})'
        ))
        for p in problems:
            self.stdout.write(self.style.WARNING(f'  {p}'))

    # --- input/output ---

    def _read_titles(self, path):
        try:
            lines = Path(path).read_text(encoding='utf-8').splitlines()
        except FileNotFoundError:
            raise CommandError(f'Файл не знайдено: {path}')
        entries = []
        for line in lines:
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            title, _sep, tags = line.partition('|')
            entries.append((title.strip(), tags.split()))
        if not entries:
            raise CommandError('Список статей порожній')
        return entries

    def _load_previous(self, output):
        if not output.exists():
            return {}
        data = json.loads(output.read_text(encoding='utf-8'))
        return {o['wikipedia_url']: o for o in data.get('objects', [])}

    # --- Wikipedia / Wikidata / Commons ---

    def _get(self, url, **params):
        time.sleep(self.delay)
        response = self.session.get(url, params={'format': 'json', 'formatversion': 2, **params},
                                    timeout=30)
        response.raise_for_status()
        return response.json()

    def _fetch_object(self, title, manual_tags):
        data = self._get(
            UK_API, action='query', titles=title, redirects=1,
            prop='coordinates|extracts|pageimages|langlinks|info|pageprops',
            explaintext=1, exsectionformat='wiki', piprop='name', lllang='en', inprop='url',
            ppprop='wikibase_item|disambiguation',
        )
        page = data['query']['pages'][0]
        if page.get('missing'):
            return None, 'статтю не знайдено'
        if 'disambiguation' in page.get('pageprops', {}):
            return None, 'сторінка неоднозначності — уточніть назву'

        qid = page.get('pageprops', {}).get('wikibase_item')
        entity = self._wikidata_entity(qid) if qid else {}

        coords = self._coordinates(page, entity)
        if coords is None:
            return None, 'немає координат ні в статті, ні у Wikidata'

        description = self._clean_extract(page.get('extract', ''))
        if not description:
            return None, 'порожній вступ статті'

        en_title = next((l['title'] for l in page.get('langlinks', []) if l.get('lang') == 'en'), '')
        if not en_title:
            en_title = entity.get('labels', {}).get('en', {}).get('value', '')

        warnings = []
        photo = self._photo(page.get('pageimage') or self._wikidata_image(entity))
        if photo is None:
            warnings.append('немає вільного фото')

        uk_title = page['title']
        return {
            'title': uk_title,
            'description': f'{description}\n\n{UK_SOURCE_NOTE}',
            'latitude': round(coords[0], 6),
            'longitude': round(coords[1], 6),
            'tags': self._tags(uk_title, description, manual_tags),
            # Декодована (кирилична) адреса: закодована перевищує max_length=200 поля URLField.
            'wikipedia_url': unquote(page['fullurl']),
            'translations': {'en': {'title': en_title, 'description': ''}},
            'photos': [photo] if photo else [],
        }, '; '.join(warnings)

    def _wikidata_entity(self, qid):
        data = self._get(WIKIDATA_API, action='wbgetentities', ids=qid,
                         props='claims|labels', languages='en')
        return data.get('entities', {}).get(qid, {})

    @staticmethod
    def _claim_value(entity, prop):
        for claim in entity.get('claims', {}).get(prop, []):
            value = claim.get('mainsnak', {}).get('datavalue', {}).get('value')
            if value:
                return value
        return None

    def _coordinates(self, page, entity):
        for c in page.get('coordinates', []):
            return c['lat'], c['lon']
        value = self._claim_value(entity, 'P625')
        if value:
            return value['latitude'], value['longitude']
        return None

    def _wikidata_image(self, entity):
        return self._claim_value(entity, 'P18')

    def _photo(self, file_name):
        if not file_name:
            return None
        data = self._get(COMMONS_API, action='query', titles=f'File:{file_name}', prop='imageinfo',
                         iiprop='url|extmetadata|mime', iiurlwidth=PHOTO_WIDTH)
        page = data['query']['pages'][0]
        info = (page.get('imageinfo') or [None])[0]
        if not info or info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
            return None
        meta = info.get('extmetadata', {})
        license_name = self._meta(meta, 'LicenseShortName')
        # Лише вільні ліцензії (Commons не приймає fair use; локальні файли uk.wiki сюди не потрапляють).
        if meta.get('NonFree', {}).get('value') == 'true' or not license_name:
            return None
        artist = self._meta(meta, 'Artist') or 'невідомий автор'
        caption = f'Фото: {artist}, {license_name}, Wikimedia Commons'
        if len(caption) > 200:
            caption = f'Фото: {artist[:200 - len(license_name) - 30].rstrip()}…, {license_name}, Wikimedia Commons'
        return {
            'source_url': info.get('thumburl') or info['url'],
            'source_page': info.get('descriptionurl', ''),
            'caption': caption,
        }

    @staticmethod
    def _meta(meta, key):
        value = meta.get(key, {}).get('value', '')
        return re.sub(r'\s+', ' ', HTML_TAG_RE.sub('', value)).strip()

    # --- text & tags ---

    @staticmethod
    def _clean_extract(text):
        """Вступ статті; якщо він коротший за MIN_DESCRIPTION_CHARS — плюс абзаци наступних розділів."""
        text = PAREN_NOISE_RE.sub('', text).replace('́', '')  # знаки наголосу заважають пошуку
        text = MAINTENANCE_TAG_RE.sub('', text)
        intro, extra, section = [], [], None
        for line in text.split('\n'):
            line = re.sub(r'\s+', ' ', line).strip()
            heading = HEADING_RE.match(line)
            if heading:
                section = heading.group(2).lower()
                continue
            if TEMPLATE_JUNK_RE.search(line) or line.endswith(';'):  # шаблони та пункти списків
                continue
            line = drop_dangling_lead_in(line)
            if len(line) < 40:  # порожні рядки, підписи, залишки списків
                continue
            if section is None:
                intro.append(line)
            elif not section.startswith(SKIP_SECTIONS):
                extra.append(line)
        paragraphs = intro[:]
        if sum(len(p) for p in intro) < MIN_DESCRIPTION_CHARS:
            for p in extra:
                paragraphs.append(p)
                if sum(len(x) for x in paragraphs) >= MIN_DESCRIPTION_CHARS:
                    break
        result = ''
        for p in paragraphs:
            candidate = f'{result}\n\n{p}' if result else p
            if len(candidate) <= MAX_DESCRIPTION_CHARS:
                result = candidate
                continue
            if not result:
                # Перший абзац задовгий — обрізаємо по межі речення.
                cut = p[:MAX_DESCRIPTION_CHARS]
                end = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
                result = cut[:end + 1] if end > 200 else cut.rstrip() + '…'
            break
        return result

    @staticmethod
    def _tags(title, description, manual_tags):
        if any(t != 'unesco' for t in manual_tags):
            return list(dict.fromkeys(manual_tags))
        haystack = title.lower()
        tags = [slug for slug, keys in TAG_RULES if any(k in haystack for k in keys)]
        if not tags:
            lead = description.lower()[:300]
            tags = [slug for slug, keys in TAG_RULES if any(k in lead for k in keys)][:1]
        tags = list(dict.fromkeys(tags[:2] + manual_tags))
        return tags or ['pamyatnyk']
