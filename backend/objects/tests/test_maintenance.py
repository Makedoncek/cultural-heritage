"""Hosting without a Celery worker/beat or shell (Render free): the token-protected
maintenance endpoint and the idempotent ensure_superuser command."""
import os
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject

URL = '/api/internal/maintenance/'
TOKEN = 'test-maintenance-token'


@override_settings(MAINTENANCE_TOKEN=TOKEN)
class MaintenanceEndpointTest(APITestCase):

    def _create_event(self, end_offset_days):
        now = timezone.now()
        return CulturalObject.objects.create(
            title='Event', latitude=50.0, longitude=30.0,
            author=User.objects.create_user(f'author{end_offset_days}', password='pass'),
            status='approved', object_type='event',
            event_start_date=now + timedelta(days=end_offset_days - 5),
            event_end_date=now + timedelta(days=end_offset_days),
        )

    @override_settings(MAINTENANCE_TOKEN='')
    def test_disabled_without_configured_token(self):
        response = self.client.post(URL, HTTP_X_MAINTENANCE_TOKEN='anything')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_token_forbidden(self):
        response = self.client.post(URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_token_forbidden(self):
        response = self.client.post(URL, HTTP_X_MAINTENANCE_TOKEN='wrong')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_not_allowed(self):
        response = self.client.get(URL, HTTP_X_MAINTENANCE_TOKEN=TOKEN)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_runs_periodic_tasks(self):
        expired = self._create_event(-3)
        upcoming = self._create_event(10)

        response = self.client.post(URL, HTTP_X_MAINTENANCE_TOKEN=TOKEN)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'archived_events': 1,
            'deleted_photos': 0,
            'deleted_audios': 0,
            'deleted_reports': 0,
        })
        expired.refresh_from_db()
        upcoming.refresh_from_db()
        self.assertEqual(expired.status, 'archived')
        self.assertEqual(upcoming.status, 'approved')

    def test_ignores_bearer_auth_header(self):
        # JWT authentication is disabled here: a stray/invalid Bearer header must not 401.
        response = self.client.post(
            URL, HTTP_X_MAINTENANCE_TOKEN=TOKEN, HTTP_AUTHORIZATION='Bearer not-a-jwt',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EnsureSuperuserCommandTest(TestCase):
    ENV = {
        'DJANGO_SUPERUSER_USERNAME': 'boss',
        'DJANGO_SUPERUSER_EMAIL': 'boss@example.com',
        'DJANGO_SUPERUSER_PASSWORD': 'S3cret-pass!',
    }

    def _run(self, env):
        out = StringIO()
        with patch.dict(os.environ, env, clear=False):
            call_command('ensure_superuser', stdout=out)
        return out.getvalue()

    def test_creates_superuser(self):
        self._run(self.ENV)
        user = User.objects.get(username='boss')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertEqual(user.email, 'boss@example.com')
        self.assertTrue(user.check_password('S3cret-pass!'))

    def test_idempotent_and_keeps_existing_password(self):
        self._run(self.ENV)
        output = self._run({**self.ENV, 'DJANGO_SUPERUSER_PASSWORD': 'another-pass'})
        self.assertIn('already exists', output)
        self.assertEqual(User.objects.filter(username='boss').count(), 1)
        self.assertTrue(User.objects.get(username='boss').check_password('S3cret-pass!'))

    def test_skips_without_credentials(self):
        output = self._run({'DJANGO_SUPERUSER_USERNAME': '', 'DJANGO_SUPERUSER_PASSWORD': ''})
        self.assertIn('skipping', output)
        self.assertFalse(User.objects.filter(is_superuser=True).exists())
