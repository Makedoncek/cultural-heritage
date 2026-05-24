"""Backfill the polymorphic target (content_type/object_id) and content_owner for
existing reports, all of which targeted a CulturalObject."""
from django.db import migrations


def backfill_targets(apps, schema_editor):
    InaccuracyReport = apps.get_model('objects', 'InaccuracyReport')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    CulturalObject = apps.get_model('objects', 'CulturalObject')

    ct = ContentType.objects.get_for_model(CulturalObject)
    owner_by_object = dict(CulturalObject.objects.values_list('id', 'author_id'))

    for report in InaccuracyReport.objects.filter(cultural_object__isnull=False):
        report.content_type = ct
        report.object_id = report.cultural_object_id
        report.content_owner_id = owner_by_object.get(report.cultural_object_id)
        report.save(update_fields=['content_type', 'object_id', 'content_owner'])


def reverse_backfill(apps, schema_editor):
    # Restore the legacy FK from the generic target for CulturalObject reports.
    InaccuracyReport = apps.get_model('objects', 'InaccuracyReport')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    CulturalObject = apps.get_model('objects', 'CulturalObject')

    ct = ContentType.objects.get_for_model(CulturalObject)
    for report in InaccuracyReport.objects.filter(content_type=ct):
        report.cultural_object_id = report.object_id
        report.save(update_fields=['cultural_object'])


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0028_report_polymorphic_step1'),
    ]

    operations = [
        migrations.RunPython(backfill_targets, reverse_backfill),
    ]
