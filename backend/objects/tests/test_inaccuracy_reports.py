"""Targeted tests for InaccuracyReport API."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject, InaccuracyReport, Tag


class InaccuracyReportFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author', 'a@t.com', 'p')
        cls.reporter = User.objects.create_user('reporter', 'r@t.com', 'p')
        cls.other = User.objects.create_user('other', 'o@t.com', 'p')
        cls.admin = User.objects.create_user('admin', 'admin@t.com', 'p', is_staff=True)
        cls.tag = Tag.objects.create(name='Castle', slug='castle', icon='C')
        cls.obj = CulturalObject.objects.create(
            title='Test Castle',
            latitude=50.0, longitude=30.0,
            author=cls.author,
            status='approved',
        )
        cls.obj.tags.add(cls.tag)

    def _report_url(self):
        return reverse('objects:report_object', kwargs={'object_pk': self.obj.pk})

    def _make_report(self, reporter, **kwargs):
        """Create a report targeting self.obj via the polymorphic GFK."""
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(CulturalObject)
        return InaccuracyReport.objects.create(
            content_type=ct,
            object_id=self.obj.pk,
            content_owner=self.author,
            reporter=reporter,
            **kwargs,
        )

    def test_authenticated_user_can_create_report(self):
        self.client.force_authenticate(self.reporter)
        response = self.client.post(self._report_url(), {
            'reason_type': 'wrong_coords',
            'note': 'Координати на 200 м відрізняються',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InaccuracyReport.objects.count(), 1)
        report = InaccuracyReport.objects.first()
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.status, 'pending')

    def test_unauthenticated_user_cannot_create_report(self):
        response = self.client.post(self._report_url(), {
            'reason_type': 'wrong_name',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_report_same_object_twice_within_24h(self):
        self.client.force_authenticate(self.reporter)
        self._make_report(self.reporter, reason_type='wrong_name')
        response = self.client.post(self._report_url(), {
            'reason_type': 'wrong_coords',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_user_can_report_again_after_24h(self):
        self.client.force_authenticate(self.reporter)
        old = self._make_report(self.reporter, reason_type='wrong_name')
        InaccuracyReport.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        response = self.client.post(self._report_url(), {
            'reason_type': 'wrong_coords',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_reason_type_rejected(self):
        self.client.force_authenticate(self.reporter)
        response = self.client.post(self._report_url(), {
            'reason_type': 'made_up_reason',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_delete_own_pending_report(self):
        self.client.force_authenticate(self.reporter)
        report = self._make_report(self.reporter, reason_type='wrong_name')
        url = reverse('objects:delete_own_report', kwargs={'report_pk': report.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InaccuracyReport.objects.filter(pk=report.pk).exists())

    def test_user_cannot_delete_others_report(self):
        report = self._make_report(self.reporter, reason_type='wrong_name')
        self.client.force_authenticate(self.other)
        url = reverse('objects:delete_own_report', kwargs={'report_pk': report.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(InaccuracyReport.objects.filter(pk=report.pk).exists())

    def test_user_cannot_delete_resolved_report(self):
        self.client.force_authenticate(self.reporter)
        report = self._make_report(
            self.reporter,
            reason_type='wrong_name',
            status='resolved',
            resolved_by=self.admin,
            resolved_at=timezone.now(),
        )
        url = reverse('objects:delete_own_report', kwargs={'report_pk': report.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_object_author_sees_reports_on_own_objects(self):
        self._make_report(self.reporter, reason_type='wrong_name')
        self.client.force_authenticate(self.author)
        url = reverse('objects:reports_on_my_objects')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['reporter_username'], 'reporter')

    def test_my_reports_returns_only_own(self):
        self._make_report(self.reporter, reason_type='wrong_name')
        self._make_report(self.other, reason_type='wrong_coords')
        self.client.force_authenticate(self.reporter)
        url = reverse('objects:my_reports')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['reporter_username'], 'reporter')
