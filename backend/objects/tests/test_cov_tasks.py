"""Coverage: tasks.cleanup_processed_inaccuracy_reports (periodic maintenance)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from objects.models import CulturalObject, InaccuracyReport
from objects.tasks import cleanup_processed_inaccuracy_reports


class CleanupProcessedReportsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('owner', 'owner@t.com', 'p')
        cls.reporter = User.objects.create_user('reporter', 'reporter@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='O', latitude=50.0, longitude=30.0, author=cls.owner, status='approved')
        cls.ct = ContentType.objects.get_for_model(CulturalObject)

    def _report(self, status, days_ago):
        rep = InaccuracyReport.objects.create(
            content_type=self.ct, object_id=self.obj.id, content_owner=self.owner,
            reporter=self.reporter, reason_type='wrong_coords', status=status)
        if days_ago is not None:
            InaccuracyReport.objects.filter(pk=rep.pk).update(
                resolved_at=timezone.now() - timedelta(days=days_ago))
        return rep

    def test_deletes_only_old_processed_reports(self):
        old_resolved = self._report('resolved', 31)
        old_dismissed = self._report('dismissed', 40)
        recent = self._report('resolved', 5)
        pending = self._report('pending', None)

        deleted = cleanup_processed_inaccuracy_reports()

        self.assertEqual(deleted, 2)
        self.assertFalse(InaccuracyReport.objects.filter(pk=old_resolved.pk).exists())
        self.assertFalse(InaccuracyReport.objects.filter(pk=old_dismissed.pk).exists())
        self.assertTrue(InaccuracyReport.objects.filter(pk=recent.pk).exists())
        self.assertTrue(InaccuracyReport.objects.filter(pk=pending.pk).exists())
