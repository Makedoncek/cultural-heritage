from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from objects.models import CulturalObject, ObjectPhoto, Tag
from objects.tasks import cleanup_rejected_photos


class CleanupRejectedPhotosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('a', 'a@t.com', 'p')
        self.tag = Tag.objects.create(name='T', slug='t', icon='X')
        self.obj = CulturalObject.objects.create(
            title='T', latitude=50.0, longitude=30.0,
            author=self.user, status='approved',
        )
        self.obj.tags.add(self.tag)

    @patch('objects.tasks.cloudinary_service.delete_photo')
    def test_deletes_expired_rejected(self, mock_delete):
        expired = ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='exp', image_url='x', thumbnail_url='y',
            status='rejected',
            rejected_cleanup_at=timezone.now() - timedelta(days=1),
        )
        cleanup_rejected_photos()
        self.assertFalse(ObjectPhoto.objects.filter(id=expired.id).exists())
        mock_delete.assert_called_once_with('exp')

    @patch('objects.tasks.cloudinary_service.delete_photo')
    def test_does_not_delete_pending(self, mock_delete):
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='pen', image_url='x', thumbnail_url='y',
            status='pending',
        )
        cleanup_rejected_photos()
        self.assertEqual(ObjectPhoto.objects.count(), 1)
        mock_delete.assert_not_called()

    @patch('objects.tasks.cloudinary_service.delete_photo')
    def test_does_not_delete_future_cleanup(self, mock_delete):
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='fut', image_url='x', thumbnail_url='y',
            status='rejected',
            rejected_cleanup_at=timezone.now() + timedelta(days=10),
        )
        cleanup_rejected_photos()
        self.assertEqual(ObjectPhoto.objects.count(), 1)
        mock_delete.assert_not_called()

    @patch('objects.tasks.cloudinary_service.delete_photo', side_effect=Exception('Cloudinary down'))
    def test_continues_on_cloudinary_error(self, _mock):
        photo = ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='err', image_url='x', thumbnail_url='y',
            status='rejected',
            rejected_cleanup_at=timezone.now() - timedelta(days=1),
        )
        cleanup_rejected_photos()
        self.assertTrue(ObjectPhoto.objects.filter(id=photo.id).exists())
