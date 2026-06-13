"""Coverage: signals.py — archived_at sync, status-transition emails, photo caption
reset, Cloudinary cleanup on media delete (broker/Cloudinary calls are mocked)."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from objects.models import CulturalObject, ObjectAudio, ObjectPhoto


class SignalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('su', 'su@t.com', 'p')

    def _object(self, status='approved'):
        return CulturalObject.objects.create(
            title='O', latitude=50.0, longitude=30.0, author=self.user, status=status)

    def test_archived_at_reset_when_status_not_archived(self):
        obj = self._object('approved')
        obj.archived_at = timezone.now()
        obj.save()
        obj.refresh_from_db()
        self.assertIsNone(obj.archived_at)

    @patch('objects.email.send_follower_notifications.delay')
    @patch('objects.email.send_status_notification.delay')
    def test_pending_to_approved_triggers_notifications(self, mock_status, mock_follow):
        obj = self._object('pending')
        obj.status = 'approved'
        obj.save()
        mock_status.assert_called_once()
        mock_follow.assert_called_once()

    def test_photo_caption_change_resets_to_pending(self):
        obj = self._object('approved')
        photo = ObjectPhoto.objects.create(
            cultural_object=obj, uploaded_by=self.user, cloudinary_public_id='cap1',
            image_url='http://x/i.jpg', thumbnail_url='http://x/t.jpg',
            status='approved', caption='old')
        photo.caption = 'new caption'
        photo.save()
        photo.refresh_from_db()
        self.assertEqual(photo.status, 'pending')

    @patch('objects.tasks.delete_cloudinary_audio.delay')
    def test_audio_delete_triggers_cloudinary_cleanup(self, mock_delay):
        obj = self._object('approved')
        audio = ObjectAudio.objects.create(
            cultural_object=obj, uploaded_by=self.user, cloudinary_public_id='aud1',
            cloudinary_url='http://x/a.mp3', duration_seconds=12, title='Narrative')
        audio.delete()
        mock_delay.assert_called_once_with('aud1')

    @patch('objects.tasks.delete_cloudinary_file.delay')
    def test_photo_delete_triggers_cloudinary_cleanup(self, mock_delay):
        obj = self._object('approved')
        photo = ObjectPhoto.objects.create(
            cultural_object=obj, uploaded_by=self.user, cloudinary_public_id='del1',
            image_url='http://x/i.jpg', thumbnail_url='http://x/t.jpg', status='approved')
        photo.delete()
        mock_delay.assert_called_once_with('del1')
