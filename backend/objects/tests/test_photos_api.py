from pathlib import Path
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject, ObjectPhoto, Tag

FIXTURES = Path(__file__).resolve().parent / 'fixtures'

CLOUDINARY_OK = {
    'public_id': 'cultural-heritage/photos/test123',
    'image_url': 'https://res.cloudinary.com/test123.jpg',
    'thumbnail_url': 'https://res.cloudinary.com/thumb_test123.jpg',
}


def _file(name='test_photo_valid.jpg'):
    with open(FIXTURES / name, 'rb') as f:
        return SimpleUploadedFile(name, f.read(), content_type='image/jpeg')


class ObjectPhotoUploadTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.author = User.objects.create_user('alice', 'a@t.com', 'p')
        self.contributor = User.objects.create_user('bob', 'b@t.com', 'p')
        self.tag = Tag.objects.create(name='T', slug='t', icon='X')
        self.approved_obj = CulturalObject.objects.create(
            title='Approved', latitude=50.0, longitude=30.0,
            author=self.author, status='approved',
        )
        self.approved_obj.tags.add(self.tag)
        self.pending_obj = CulturalObject.objects.create(
            title='Pending', latitude=50.0, longitude=30.0,
            author=self.author, status='pending',
        )
        self.pending_obj.tags.add(self.tag)

    @patch('objects.views.cloudinary_service.upload_photo', return_value=CLOUDINARY_OK)
    def test_author_uploads_to_own_object_returns_201(self, _mock):
        self.client.force_authenticate(user=self.author)
        resp = self.client.post(
            f'/api/objects/{self.approved_obj.id}/photos/',
            {'image': _file(), 'caption': 'fasade'},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['caption'], 'fasade')
        self.assertEqual(resp.data['status'], 'pending')
        self.assertTrue(resp.data['is_author_photo'])

    @patch('objects.views.cloudinary_service.upload_photo', return_value=CLOUDINARY_OK)
    def test_contributor_uploads_to_approved_returns_201(self, _mock):
        self.client.force_authenticate(user=self.contributor)
        resp = self.client.post(
            f'/api/objects/{self.approved_obj.id}/photos/',
            {'image': _file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(resp.data['is_author_photo'])

    def test_anonymous_upload_returns_401(self):
        resp = self.client.post(
            f'/api/objects/{self.approved_obj.id}/photos/',
            {'image': _file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_contributor_to_pending_returns_403(self):
        self.client.force_authenticate(user=self.contributor)
        resp = self.client.post(
            f'/api/objects/{self.pending_obj.id}/photos/',
            {'image': _file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_oversized_file_returns_400(self):
        self.client.force_authenticate(user=self.author)
        resp = self.client.post(
            f'/api/objects/{self.approved_obj.id}/photos/',
            {'image': _file('test_photo_oversized.jpg')},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fake_jpg_returns_400(self):
        self.client.force_authenticate(user=self.author)
        resp = self.client.post(
            f'/api/objects/{self.approved_obj.id}/photos/',
            {'image': _file('test_photo_fake.jpg')},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('objects.views.cloudinary_service.upload_photo', return_value=CLOUDINARY_OK)
    def test_author_exceeds_5_photo_limit(self, _mock):
        self.client.force_authenticate(user=self.author)
        for i in range(5):
            ObjectPhoto.objects.create(
                cultural_object=self.approved_obj, uploaded_by=self.author,
                cloudinary_public_id=f'a{i}', image_url='x', thumbnail_url='y',
                is_author_photo=True, order=i,
            )
        resp = self.client.post(
            f'/api/objects/{self.approved_obj.id}/photos/',
            {'image': _file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data.get('code'), 'user_limit_exceeded')

    @patch('objects.views.cloudinary_service.upload_photo', return_value=CLOUDINARY_OK)
    def test_contributor_exceeds_3_photo_limit(self, _mock):
        self.client.force_authenticate(user=self.contributor)
        for i in range(3):
            ObjectPhoto.objects.create(
                cultural_object=self.approved_obj, uploaded_by=self.contributor,
                cloudinary_public_id=f'c{i}', image_url='x', thumbnail_url='y',
                is_author_photo=False, order=0,
            )
        resp = self.client.post(
            f'/api/objects/{self.approved_obj.id}/photos/',
            {'image': _file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data.get('code'), 'user_limit_exceeded')

    @patch('objects.views.cloudinary_service.upload_photo', return_value=CLOUDINARY_OK)
    def test_object_full_at_20(self, _mock):
        for i in range(5):
            ObjectPhoto.objects.create(
                cultural_object=self.approved_obj, uploaded_by=self.author,
                cloudinary_public_id=f'a{i}', image_url='x', thumbnail_url='y',
                is_author_photo=True, order=i,
            )
        for i in range(15):
            u = User.objects.create_user(f'u{i}', f'u{i}@t.com', 'p')
            ObjectPhoto.objects.create(
                cultural_object=self.approved_obj, uploaded_by=u,
                cloudinary_public_id=f'c{i}', image_url='x', thumbnail_url='y',
                is_author_photo=False, order=0,
            )
        new_user = User.objects.create_user('new', 'n@t.com', 'p')
        self.client.force_authenticate(user=new_user)
        resp = self.client.post(
            f'/api/objects/{self.approved_obj.id}/photos/',
            {'image': _file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data.get('code'), 'object_full')


class ObjectPhotoListTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.author = User.objects.create_user('alice', 'a@t.com', 'p')
        self.contrib = User.objects.create_user('bob', 'b@t.com', 'p')
        self.other = User.objects.create_user('carol', 'c@t.com', 'p')
        self.admin = User.objects.create_user('admin', 'ad@t.com', 'p', is_staff=True)
        self.tag = Tag.objects.create(name='T', slug='t', icon='X')
        self.obj = CulturalObject.objects.create(
            title='T', latitude=50.0, longitude=30.0,
            author=self.author, status='approved',
        )
        self.obj.tags.add(self.tag)
        self.author_approved = ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.author,
            cloudinary_public_id='aa', image_url='x', thumbnail_url='y',
            is_author_photo=True, order=0, status='approved',
        )
        self.author_pending = ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.author,
            cloudinary_public_id='ap', image_url='x', thumbnail_url='y',
            is_author_photo=True, order=1, status='pending',
        )
        self.contrib_approved = ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.contrib,
            cloudinary_public_id='ca', image_url='x', thumbnail_url='y',
            is_author_photo=False, order=0, status='approved',
        )
        self.contrib_pending = ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.contrib,
            cloudinary_public_id='cp', image_url='x', thumbnail_url='y',
            is_author_photo=False, order=0, status='pending',
        )

    def _ids(self, resp):
        return {p['id'] for p in resp.data}

    def test_anonymous_sees_only_approved(self):
        resp = self.client.get(f'/api/objects/{self.obj.id}/photos/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._ids(resp), {self.author_approved.id, self.contrib_approved.id})

    def test_author_sees_own_pending_and_approved(self):
        self.client.force_authenticate(user=self.author)
        resp = self.client.get(f'/api/objects/{self.obj.id}/photos/')
        self.assertEqual(self._ids(resp), {
            self.author_approved.id, self.author_pending.id, self.contrib_approved.id,
        })

    def test_contrib_sees_own_pending(self):
        self.client.force_authenticate(user=self.contrib)
        resp = self.client.get(f'/api/objects/{self.obj.id}/photos/')
        self.assertEqual(self._ids(resp), {
            self.author_approved.id, self.contrib_approved.id, self.contrib_pending.id,
        })

    def test_other_user_does_not_see_others_pending(self):
        self.client.force_authenticate(user=self.other)
        resp = self.client.get(f'/api/objects/{self.obj.id}/photos/')
        self.assertEqual(self._ids(resp), {self.author_approved.id, self.contrib_approved.id})

    def test_admin_sees_all(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f'/api/objects/{self.obj.id}/photos/')
        self.assertEqual(self._ids(resp), {
            self.author_approved.id, self.author_pending.id,
            self.contrib_approved.id, self.contrib_pending.id,
        })
