"""Seed en/pl/de translations for the canonical tags (matched by slug). Idempotent."""
from django.db import migrations

# slug -> {lang: name}
TAG_TRANSLATIONS = {
    'zamok':         {'en': 'Castle',     'pl': 'Zamek',       'de': 'Burg'},
    'tserkva':       {'en': 'Church',     'pl': 'Kościół',     'de': 'Kirche'},
    'muzey':         {'en': 'Museum',     'pl': 'Muzeum',      'de': 'Museum'},
    'pamyatnyk':     {'en': 'Monument',   'pl': 'Pomnik',      'de': 'Denkmal'},
    'park':          {'en': 'Park',       'pl': 'Park',        'de': 'Park'},
    'palats':        {'en': 'Palace',     'pl': 'Pałac',       'de': 'Palast'},
    'fortetsya':     {'en': 'Fortress',   'pl': 'Twierdza',    'de': 'Festung'},
    'teatr':         {'en': 'Theatre',    'pl': 'Teatr',       'de': 'Theater'},
    'sobor':         {'en': 'Cathedral',  'pl': 'Katedra',     'de': 'Kathedrale'},
    'unesco':        {'en': 'UNESCO',     'pl': 'UNESCO',      'de': 'UNESCO'},
    'festyval':      {'en': 'Festival',   'pl': 'Festiwal',    'de': 'Festival'},
    'vystavka':      {'en': 'Exhibition', 'pl': 'Wystawa',     'de': 'Ausstellung'},
    'yarmarok':      {'en': 'Fair',       'pl': 'Jarmark',     'de': 'Jahrmarkt'},
    'kontsert':      {'en': 'Concert',    'pl': 'Koncert',     'de': 'Konzert'},
    'konferentsiya': {'en': 'Conference', 'pl': 'Konferencja', 'de': 'Konferenz'},
}


def seed(apps, schema_editor):
    Tag = apps.get_model('objects', 'Tag')
    TagTranslation = apps.get_model('objects', 'TagTranslation')
    for tag in Tag.objects.all():
        mapping = TAG_TRANSLATIONS.get(tag.slug)
        if not mapping:
            continue
        for lang, name in mapping.items():
            TagTranslation.objects.get_or_create(
                tag=tag, language=lang, defaults={'name': name},
            )


def unseed(apps, schema_editor):
    TagTranslation = apps.get_model('objects', 'TagTranslation')
    slugs = list(TAG_TRANSLATIONS.keys())
    TagTranslation.objects.filter(tag__slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0032_admin_field_labels'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
