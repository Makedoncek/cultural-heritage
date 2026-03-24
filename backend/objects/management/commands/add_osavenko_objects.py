from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from objects.models import Tag, CulturalObject


OBJECTS = [
    {
        'title': 'Софійський собор',
        'description': (
            'Видатний архітектурний пам\'ятник Київської Русі, збудований у XI столітті '
            'за часів князя Ярослава Мудрого. Внесений до Списку всесвітньої спадщини ЮНЕСКО. '
            'Собор зберігає унікальні мозаїки та фрески, серед яких — знаменита Оранта.'
        ),
        'latitude': '50.452778',
        'longitude': '30.514444',
        'tags': ['sobor', 'unesco', 'muzey'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Софійський_собор_(Київ)',
        'google_maps_url': 'https://maps.app.goo.gl/8X1Z4XZJZ1Z4XZJZ',
    },
    {
        'title': 'Києво-Печерська лавра',
        'description': (
            'Один із найбільших православних монастирських комплексів у світі, '
            'заснований у 1051 році монахами Антонієм та Феодосієм. '
            'Об\'єкт Всесвітньої спадщини ЮНЕСКО. Включає підземні печери, '
            'Успенський собор та Велику лаврську дзвіницю.'
        ),
        'latitude': '50.434444',
        'longitude': '30.557222',
        'tags': ['tserkva', 'unesco', 'muzey'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Києво-Печерська_лавра',
    },
    {
        'title': 'Львівський національний академічний театр опери та балету',
        'description': (
            'Один із найкрасивіших театрів Європи, збудований у 1897–1900 роках '
            'за проєктом архітектора Зигмунта Ґорґолевського у стилі неоренесансу. '
            'Фасад прикрашений скульптурами та алегоричними фігурами.'
        ),
        'latitude': '49.844167',
        'longitude': '24.026111',
        'tags': ['teatr', 'pamyatnyk'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Львівський_національний_академічний_театр_опери_та_балету_імені_Соломії_Крушельницької',
    },
    {
        'title': 'Кам\'янець-Подільська фортеця',
        'description': (
            'Середньовічна фортеця на скелястому острові, оточеному каньйоном річки Смотрич. '
            'Один із семи чудес України. Заснована у XII столітті, '
            'перебудовувалася протягом XIV–XVIII століть.'
        ),
        'latitude': '48.674722',
        'longitude': '26.565278',
        'tags': ['fortetsya', 'muzey'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Кам\'янець-Подільська_фортеця',
        'google_maps_url': 'https://maps.app.goo.gl/kamianets',
    },
    {
        'title': 'Хотинська фортеця',
        'description': (
            'Потужна фортифікаційна споруда X–XVIII століть на березі Дністра. '
            'Була свідком численних битв між українськими козаками, '
            'турками та поляками. Популярна локація для зйомок історичних фільмів.'
        ),
        'latitude': '48.519722',
        'longitude': '26.502778',
        'tags': ['fortetsya', 'pamyatnyk'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Хотинська_фортеця',
    },
    {
        'title': 'Олеський замок',
        'description': (
            'Замок XIII століття на пагорбі у Львівській області. '
            'Тут народився польський король Ян III Собеський. '
            'Зараз є філією Львівської галереї мистецтв із колекцією '
            'живопису та скульптури XVI–XVIII століть.'
        ),
        'latitude': '49.960278',
        'longitude': '24.893611',
        'tags': ['zamok', 'muzey'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Олеський_замок',
    },
    {
        'title': 'Підгорецький замок',
        'description': (
            'Ренесансний палац-фортеця XVII століття, побудований '
            'за проєктом архітектора Андреа дель Аква. '
            'Називають «галицьким Версалем» за його пишну архітектуру та терасний парк.'
        ),
        'latitude': '49.945833',
        'longitude': '24.981944',
        'tags': ['zamok', 'palats'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Підгорецький_замок',
    },
    {
        'title': 'Замок Паланок',
        'description': (
            'Середньовічний замок у місті Мукачево на вулканічній горі. '
            'Один із найкраще збережених замків Закарпаття. '
            'Побудований у XIV–XVII століттях, слугував '
            'резиденцією угорських князів та оборонною фортецею.'
        ),
        'latitude': '48.441944',
        'longitude': '22.684722',
        'tags': ['zamok', 'muzey', 'fortetsya'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Замок_Паланок',
    },
    {
        'title': 'Софіївський парк',
        'description': (
            'Дендрологічний парк в Умані, закладений у 1796 році '
            'графом Станіславом Потоцьким як подарунок дружині Софії. '
            'Шедевр садово-паркового мистецтва з гротами, '
            'водоспадами та підземною річкою Стікс.'
        ),
        'latitude': '48.763333',
        'longitude': '30.226944',
        'tags': ['park', 'pamyatnyk'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Софіївський_парк',
    },
    {
        'title': 'Андріївська церква',
        'description': (
            'Бароковий храм XVIII століття на Андріївському узвозі у Києві, '
            'збудований за проєктом архітектора Бартоломео Растреллі. '
            'Один із символів Києва з характерним блакитно-білим фасадом '
            'та п\'ятьма куполами.'
        ),
        'latitude': '50.458889',
        'longitude': '30.517778',
        'tags': ['tserkva', 'pamyatnyk'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Андріївська_церква_(Київ)',
    },
    {
        'title': 'Ужгородський замок',
        'description': (
            'Замок-фортеця у центрі Ужгорода, один із найдавніших '
            'на території України. Перші укріплення на цьому місці '
            'з\'явились у IX столітті. Нині тут розташований '
            'Закарпатський краєзнавчий музей.'
        ),
        'latitude': '48.623889',
        'longitude': '22.302778',
        'tags': ['zamok', 'muzey'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Ужгородський_замок',
    },
    {
        'title': 'Палац Потоцьких',
        'description': (
            'Розкішний палац у стилі французького класицизму у центрі Львова, '
            'побудований у XIX столітті для родини Потоцьких. '
            'Зараз є філією Львівської галереї мистецтв.'
        ),
        'latitude': '49.841667',
        'longitude': '24.030833',
        'tags': ['palats', 'muzey'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Палац_Потоцьких_(Львів)',
    },
    {
        'title': 'Золоті ворота',
        'description': (
            'Головна брама давнього Києва, споруджена за Ярослава Мудрого '
            'у 1037 році. Були частиною оборонних укріплень міста. '
            'Реконструйовані у 1982 році, зараз тут діє музей.'
        ),
        'latitude': '50.448889',
        'longitude': '30.513056',
        'tags': ['pamyatnyk', 'muzey'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Золоті_ворота_(Київ)',
    },
    {
        'title': 'Тунель кохання',
        'description': (
            'Унікальний природний тунель із дерев та кущів довжиною близько 4 км '
            'поблизу селища Клевань на Рівненщині. Утворений залізничною колією, '
            'вздовж якої дерева зімкнулися, створивши зелений коридор. '
            'Популярне романтичне місце.'
        ),
        'latitude': '50.752778',
        'longitude': '26.047222',
        'tags': ['park', 'pamyatnyk'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Тунель_кохання',
    },
    {
        'title': 'Херсонес Таврійський',
        'description': (
            'Руїни стародавнього грецького міста-колонії, заснованого '
            'у V столітті до н. е. на території сучасного Севастополя. '
            'Об\'єкт Всесвітньої спадщини ЮНЕСКО. Тут прийняв хрещення '
            'київський князь Володимир у 988 році.'
        ),
        'latitude': '44.611389',
        'longitude': '33.493333',
        'tags': ['unesco', 'pamyatnyk', 'muzey'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/Херсонес_Таврійський',
    },
]


class Command(BaseCommand):
    help = 'Додає реальні культурні об\'єкти для користувача osavenko'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='osavenko')
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                'Користувач osavenko не знайдений. '
                'Спочатку створіть його через реєстрацію або createsuperuser.'
            ))
            return

        tags_map = {tag.slug: tag for tag in Tag.objects.all()}
        created_count = 0

        for obj_data in OBJECTS:
            if CulturalObject.objects.filter(
                title=obj_data['title'], author=user
            ).exists():
                self.stdout.write(f'  Пропущено (вже існує): {obj_data["title"]}')
                continue

            obj = CulturalObject.objects.create(
                title=obj_data['title'],
                description=obj_data['description'],
                latitude=Decimal(obj_data['latitude']),
                longitude=Decimal(obj_data['longitude']),
                author=user,
                status=CulturalObject.Status.APPROVED,
                wikipedia_url=obj_data.get('wikipedia_url', ''),
                google_maps_url=obj_data.get('google_maps_url', ''),
            )
            obj.tags.set([tags_map[slug] for slug in obj_data['tags']])
            created_count += 1
            self.stdout.write(f'  + {obj_data["title"]}')

        self.stdout.write(self.style.SUCCESS(
            f'\nСтворено {created_count} об\'єктів для osavenko'
        ))