from django.core.management.base import BaseCommand
from django.utils import timezone
from objects.models import CulturalObject
from objects.tasks import archive_expired_events


class Command(BaseCommand):
    help = 'Archive events whose end date has passed'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be archived without making changes')

    def handle(self, *args, **options):
        if options['dry_run']:
            expired = CulturalObject.objects.filter(
                object_type=CulturalObject.ObjectType.EVENT,
                event_end_date__lt=timezone.now(),
                status=CulturalObject.Status.APPROVED,
            )
            count = expired.count()
            if count == 0:
                self.stdout.write('No expired events found.')
                return
            self.stdout.write(f'[DRY RUN] Would archive {count} expired event(s):')
            for obj in expired:
                self.stdout.write(f'  - {obj.title} (ended {obj.event_end_date})')
            return

        count = archive_expired_events()
        if count == 0:
            self.stdout.write('No expired events found.')
        else:
            self.stdout.write(self.style.SUCCESS(f'Archived {count} expired event(s).'))
