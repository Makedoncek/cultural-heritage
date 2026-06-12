"""Periodic cleanup of rejected audio narratives (mirrors cleanup_rejected_photos)."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from objects.models import CulturalObject, ObjectAudio
from objects.tasks import AUDIO_REJECTED_RETENTION_DAYS, cleanup_rejected_audios


class CleanupRejectedAudiosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('a', 'a@t.com', 'p')
        self.obj = CulturalObject.objects.create(
            title='T', latitude=50.0, longitude=30.0, author=self.user, status='approved',
        )

    def _audio(self, public_id, **kwargs):
        defaults = dict(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id=public_id, cloudinary_url='http://x/a.mp3',
            duration_seconds=10, title='A', language='uk', copyright_confirmed=True,
        )
        defaults.update(kwargs)
        return ObjectAudio.objects.create(**defaults)

    @patch('objects.cloudinary_audio_service.delete_audio')
    def test_deletes_expired_rejected(self, mock_delete):
        a = self._audio(
            'exp', status='rejected',
            moderated_at=timezone.now() - timedelta(days=AUDIO_REJECTED_RETENTION_DAYS + 1),
        )
        cleanup_rejected_audios()
        self.assertFalse(ObjectAudio.objects.filter(id=a.id).exists())
        mock_delete.assert_called_once_with('exp')

    @patch('objects.cloudinary_audio_service.delete_audio')
    def test_keeps_recently_rejected(self, mock_delete):
        self._audio('recent', status='rejected', moderated_at=timezone.now())
        cleanup_rejected_audios()
        self.assertEqual(ObjectAudio.objects.count(), 1)
        mock_delete.assert_not_called()

    @patch('objects.cloudinary_audio_service.delete_audio')
    def test_keeps_approved(self, mock_delete):
        self._audio(
            'appr', status='approved',
            moderated_at=timezone.now() - timedelta(days=AUDIO_REJECTED_RETENTION_DAYS + 5),
        )
        cleanup_rejected_audios()
        self.assertEqual(ObjectAudio.objects.count(), 1)
        mock_delete.assert_not_called()
