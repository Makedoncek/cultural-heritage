"""Finalize the polymorphic report: drop the legacy cultural_object FK and tighten the
generic target fields to non-null (all rows backfilled in 0029)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0029_report_backfill_targets'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inaccuracyreport',
            name='cultural_object',
        ),
        migrations.AlterField(
            model_name='inaccuracyreport',
            name='content_type',
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                to='contenttypes.contenttype',
            ),
        ),
        migrations.AlterField(
            model_name='inaccuracyreport',
            name='object_id',
            field=models.PositiveIntegerField(),
        ),
    ]
