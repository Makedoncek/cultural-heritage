from django.contrib.auth.models import User
from django.test import TestCase

from objects.models import CulturalObject, ObjectPhoto, Tag
from objects.serializers import ObjectPhotoSerializer


class ObjectPhotoSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', 'a@t.com', 'p')
        self.tag = Tag.objects.create(name='T', slug='t', icon='X')
        self.obj = CulturalObject.objects.create(
            title='T', latitude=50.0, longitude=30.0,
            author=self.user, status='approved',
        )
        self.obj.tags.add(self.tag)

    def test_serializes_all_required_fields(self):
        photo = ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='p1', image_url='https://img',
            thumbnail_url='https://thumb', caption='cap',
            is_author_photo=True, order=2,
        )
        data = ObjectPhotoSerializer(photo).data

        self.assertEqual(data['id'], photo.id)
        self.assertEqual(data['cultural_object'], self.obj.id)
        self.assertEqual(data['uploaded_by']['username'], 'alice')
        self.assertEqual(data['image_url'], 'https://img')
        self.assertEqual(data['thumbnail_url'], 'https://thumb')
        self.assertEqual(data['caption'], 'cap')
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['order'], 2)
        self.assertTrue(data['is_author_photo'])
        self.assertIn('created_at', data)
