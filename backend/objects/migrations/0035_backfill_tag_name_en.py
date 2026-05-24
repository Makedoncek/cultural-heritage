"""Preserve any Tag.name_en values into TagTranslation('en') before the legacy field is dropped."""
from django.db import migrations


def backfill(apps, schema_editor):
    Tag = apps.get_model('objects', 'Tag')
    TagTranslation = apps.get_model('objects', 'TagTranslation')
    for tag in Tag.objects.exclude(name_en='').exclude(name_en__isnull=True):
        TagTranslation.objects.get_or_create(
            tag=tag, language='en', defaults={'name': tag.name_en},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0034_add_archived_status'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
