from datetime import timedelta

from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from django.utils import timezone
from objects.models import CulturalObject, Tag


class ArchiveExpiredEventsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.tag = Tag.objects.create(name='Замок', slug='zamok')

    def _create_event(self, title, end_offset_days, status='approved'):
        now = timezone.now()
        start = now + timedelta(days=end_offset_days - 5)
        end = now + timedelta(days=end_offset_days)
        obj = CulturalObject.objects.create(
            title=title,
            latitude=50.0, longitude=30.0,
            author=self.user,
            status=status,
            object_type='event',
            event_start_date=start,
            event_end_date=end,
        )
        obj.tags.add(self.tag)
        return obj

    def test_archive_expired_events(self):
        event = self._create_event('Expired', -3)
        call_command('archive_expired_events')
        event.refresh_from_db()
        self.assertEqual(event.status, 'archived')

    def test_does_not_archive_future_events(self):
        event = self._create_event('Future', 10)
        call_command('archive_expired_events')
        event.refresh_from_db()
        self.assertEqual(event.status, 'approved')

    def test_does_not_archive_permanent_objects(self):
        obj = CulturalObject.objects.create(
            title='Permanent',
            latitude=50.0, longitude=30.0,
            author=self.user,
            status='approved',
            object_type='permanent',
        )
        call_command('archive_expired_events')
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'approved')

    def test_dry_run(self):
        event = self._create_event('Expired', -3)
        call_command('archive_expired_events', dry_run=True)
        event.refresh_from_db()
        self.assertEqual(event.status, 'approved')
