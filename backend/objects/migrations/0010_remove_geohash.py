"""Видаляє dead-column `geohash` з objects_culturalobject.

Поле було додане експериментальними міграціями (0008_culturalobject_geohash_and_more
та 0009_backfill_geohash для Bundle A — Nearby Search), які пізніше були
відкочені на рівні коду. Файли міграцій видалено, але колонка та її індекс
залишилися у БД. Ця міграція очищає залишковий артефакт.

Безпечна для повторного запуску і для нових інсталяцій, де geohash ніколи
не створювали — використовує IF EXISTS перевірку через information_schema.
"""
from django.db import migrations


def drop_geohash_column(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'objects_culturalobject' "
            "AND column_name = 'geohash'"
        )
        if cursor.fetchone():
            cursor.execute('ALTER TABLE objects_culturalobject DROP COLUMN geohash')


def noop_reverse(apps, schema_editor):
    """Reverse no-op — відновлювати застаріле експериментальне поле не маємо сенсу."""


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0009_alter_objectphoto_options'),
    ]

    operations = [
        migrations.RunPython(drop_geohash_column, noop_reverse, elidable=False),
    ]
