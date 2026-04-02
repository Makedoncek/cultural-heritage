from django.core.management.base import BaseCommand
from django.utils import timezone
from objects.models import CulturalObject


class Command(BaseCommand):
    help = 'Archive events whose end date has passed'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be archived without making changes')

    def handle(self, *args, **options):
        expired = CulturalObject.objects.filter(
            object_type=CulturalObject.ObjectType.EVENT,
            event_end_date__lt=timezone.now(),
            status=CulturalObject.Status.APPROVED,
        )

        count = expired.count()
        if count == 0:
            self.stdout.write('No expired events found.')
            return

        if options['dry_run']:
            self.stdout.write(f'[DRY RUN] Would archive {count} expired event(s):')
            for obj in expired:
                self.stdout.write(f'  - {obj.title} (ended {obj.event_end_date})')
            return

        for obj in expired:
            obj.archive()

        self.stdout.write(self.style.SUCCESS(f'Archived {count} expired event(s).'))
