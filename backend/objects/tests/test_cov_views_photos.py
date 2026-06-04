"""Coverage: views.py — ObjectPhotoViewSet error branches (upload failures,
row-locked limit re-check, caption editing, archive/restore, reorder)."""
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from django.conf import settings
from objects.models import CulturalObject, ObjectPhoto

FIXTURES = Path(__file__).resolve().parent / 'fixtures'

CLOUDINARY_OK = {
    'public_id': 'cultural-heritage/photos/cov123',
    'image_url': 'https://res.cloudinary.com/cov123.jpg',
    'thumbnail_url': 'https://res.cloudinary.com/thumb_cov123.jpg',
}


def _file(name='test_photo_valid.jpg'):
    with open(FIXTURES / name, 'rb') as f:
        return SimpleUploadedFile(name, f.read(), content_type='image/jpeg')


def _make_photo(obj, user, public_id, **kwargs):
    defaults = dict(
        cultural_object=obj, uploaded_by=user,
        cloudinary_public_id=public_id,
        image_url='http://x/i.jpg', thumbnail_url='http://x/t.jpg',
        status='approved',
    )
    defaults.update(kwargs)
    return ObjectPhoto.objects.create(**defaults)


class PhotoUploadErrorTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.author = User.objects.create_user('alice', 'a@t.com', 'p')
        self.obj = CulturalObject.objects.create(
            title='Approved', latitude=50.0, longitude=30.0,
            author=self.author, status='approved',
        )
        self.url = f'/api/objects/{self.obj.pk}/photos/'
        self.client.force_authenticate(self.author)

    def test_missing_image_field(self):
        resp = self.client.post(self.url, {}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('objects.views.photos.cloudinary_service.upload_photo', side_effect=Exception('boom'))
    def test_cloudinary_failure_returns_500(self, _mock):
        resp = self.client.post(self.url, {'image': _file()}, format='multipart')
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(ObjectPhoto.objects.count(), 0)

    @patch('objects.views.photos.cloudinary_service.delete_photo')
    @patch('objects.views.photos.cloudinary_service.upload_photo')
    def test_locked_recheck_user_limit_rolls_back_upload(self, mock_upload, mock_delete):
        # Simulate a race: parallel uploads land between the pre-check and the
        # row-locked re-check (the mock creates them during the Cloudinary call).
        def upload_during_race(_image):
            for i in range(settings.PHOTO_MAX_PER_AUTHOR):
                _make_photo(self.obj, self.author, f'race{i}')
            return CLOUDINARY_OK

        mock_upload.side_effect = upload_during_race
        resp = self.client.post(self.url, {'image': _file()}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['code'], 'user_limit_exceeded')
        mock_delete.assert_called_once_with(CLOUDINARY_OK['public_id'])

    @patch('objects.views.photos.cloudinary_service.delete_photo', side_effect=Exception('cleanup fail'))
    @patch('objects.views.photos.cloudinary_service.upload_photo')
    def test_locked_recheck_object_full(self, mock_upload, _del):
        # Race fills the object with other users' photos: pre-check passed,
        # locked re-check raises object_full. Cleanup failure is swallowed.
        def upload_during_race(_image):
            for i in range(settings.PHOTO_MAX_PER_OBJECT):
                u = User.objects.create_user(f'u{i}', f'u{i}@t.com', 'p')
                _make_photo(self.obj, u, f'full{i}')
            return CLOUDINARY_OK

        mock_upload.side_effect = upload_during_race
        resp = self.client.post(self.url, {'image': _file()}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['code'], 'object_full')

    def test_archived_photos_do_not_occupy_limit_slots(self):
        # Regression for the pre-refactor inconsistency: archived photos used to
        # count toward the limit in the locked re-check but not in the pre-check.
        for i in range(settings.PHOTO_MAX_PER_AUTHOR):
            _make_photo(self.obj, self.author, f'arch{i}', status='archived')
        with patch('objects.views.photos.cloudinary_service.upload_photo',
                   return_value=CLOUDINARY_OK):
            resp = self.client.post(self.url, {'image': _file()}, format='multipart')
        self.assertEqual(resp.status_code, 201)


class PhotoCaptionAndModerationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.author = User.objects.create_user('alice', 'a@t.com', 'p')
        self.other = User.objects.create_user('bob', 'b@t.com', 'p')
        self.admin = User.objects.create_user('admin', 'ad@t.com', 'p', is_staff=True)
        self.obj = CulturalObject.objects.create(
            title='Approved', latitude=50.0, longitude=30.0,
            author=self.author, status='approved',
        )
        self.photo = _make_photo(self.obj, self.author, 'cap1', caption='old')
        self.url = f'/api/objects/{self.obj.pk}/photos/{self.photo.pk}/'

    def test_caption_too_long(self):
        self.client.force_authenticate(self.author)
        resp = self.client.patch(self.url, {'caption': 'x' * 201}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_caption_edit_keeps_status(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(self.url, {'caption': 'admin edit'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.status, 'approved')

    def test_archive_restore_flow(self):
        archive_url = f'{self.url}archive/'
        restore_url = f'{self.url}restore/'
        # foreign user → 403
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(archive_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(restore_url).status_code, status.HTTP_403_FORBIDDEN)
        # restore of non-archived → 400
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.post(restore_url).status_code, status.HTTP_400_BAD_REQUEST)
        # archive → archived
        resp = self.client.post(archive_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.status, 'archived')
        # restore → pending
        resp = self.client.post(restore_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.status, 'pending')


class PhotoReorderErrorTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.author = User.objects.create_user('alice', 'a@t.com', 'p')
        self.obj = CulturalObject.objects.create(
            title='Approved', latitude=50.0, longitude=30.0,
            author=self.author, status='approved',
        )
        self.p1 = _make_photo(self.obj, self.author, 'r1', order=0)
        self.p2 = _make_photo(self.obj, self.author, 'r2', order=1)
        self.url = f'/api/objects/{self.obj.pk}/photos/reorder/'
        self.client.force_authenticate(self.author)

    def test_order_must_be_list(self):
        resp = self.client.post(self.url, {'order': 'nope'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_photo_id_rejected(self):
        resp = self.client.post(self.url, {'order': [
            {'id': self.p1.pk, 'order': 1}, {'id': 999999, 'order': 0},
        ]}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_success(self):
        resp = self.client.post(self.url, {'order': [
            {'id': self.p1.pk, 'order': 1}, {'id': self.p2.pk, 'order': 0},
        ]}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.order, 1)
