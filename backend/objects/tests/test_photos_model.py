from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase

from objects.models import CulturalObject, ObjectPhoto, Tag


class ObjectPhotoModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', 'a@test.com', 'pass')
        self.tag = Tag.objects.create(name='Замок', slug='zamok', icon='🏰')
        self.obj = CulturalObject.objects.create(
            title='Test', latitude=50.0, longitude=30.0,
            author=self.user, status='approved',
        )
        self.obj.tags.add(self.tag)

    def test_create_photo_with_minimal_fields(self):
        p = ObjectPhoto.objects.create(
            cultural_object=self.obj,
            uploaded_by=self.user,
            cloudinary_public_id='abc',
            image_url='https://test/img.jpg',
            thumbnail_url='https://test/thumb.jpg',
        )
        self.assertEqual(p.status, ObjectPhoto.Status.PENDING)
        self.assertEqual(p.caption, '')
        self.assertEqual(p.order, 0)
        self.assertFalse(p.is_author_photo)

    def test_unique_cloudinary_public_id(self):
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='dup', image_url='x', thumbnail_url='y',
        )
        with self.assertRaises(IntegrityError):
            ObjectPhoto.objects.create(
                cultural_object=self.obj, uploaded_by=self.user,
                cloudinary_public_id='dup', image_url='x2', thumbnail_url='y2',
            )

    def test_ordering_by_order_then_created(self):
        # Сортування лише за `order` і потім `created_at` — без преференції
        # автору, щоб admin/object-author міг змішувати community-фото у будь-якому порядку.
        contrib = User.objects.create_user('bob', 'b@test.com', 'pass')
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=contrib,
            cloudinary_public_id='c0', image_url='x', thumbnail_url='y',
            is_author_photo=False, order=0,
        )
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='a2', image_url='x', thumbnail_url='y',
            is_author_photo=True, order=2,
        )
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='a1', image_url='x', thumbnail_url='y',
            is_author_photo=True, order=1,
        )

        public_ids = list(self.obj.photos.values_list('cloudinary_public_id', flat=True))
        self.assertEqual(public_ids, ['c0', 'a1', 'a2'])


class CoverUrlPropertyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('a', 'a@t.com', 'p')
        self.tag = Tag.objects.create(name='T', slug='t', icon='X')
        self.obj = CulturalObject.objects.create(
            title='T', latitude=50.0, longitude=30.0,
            author=self.user, status='approved',
        )
        self.obj.tags.add(self.tag)

    def test_cover_url_none_when_no_photos(self):
        self.assertIsNone(self.obj.cover_url)

    def test_cover_url_returns_first_approved_thumbnail(self):
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='p1', image_url='x',
            thumbnail_url='https://thumb1', is_author_photo=True,
            order=0, status='approved',
        )
        self.assertEqual(self.obj.cover_url, 'https://thumb1')

    def test_cover_url_excludes_pending(self):
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='p1', image_url='x',
            thumbnail_url='https://thumb1', is_author_photo=True,
            order=0, status='pending',
        )
        self.assertIsNone(self.obj.cover_url)

    def test_cover_url_excludes_rejected(self):
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='p1', image_url='x',
            thumbnail_url='https://thumb1', is_author_photo=True,
            order=0, status='rejected',
        )
        self.assertIsNone(self.obj.cover_url)

    def test_cover_url_annotated_null_makes_no_query(self):
        """NULL-анотація (об'єкт без фото) не має падати у fallback-запит — N+1 на списку."""
        from django.db.models import OuterRef, Subquery
        sq = ObjectPhoto.objects.filter(
            cultural_object=OuterRef('pk'), status='approved',
        ).values('thumbnail_url')[:1]
        obj = CulturalObject.objects.annotate(
            _cover_thumbnail_url=Subquery(sq)
        ).get(pk=self.obj.pk)
        with self.assertNumQueries(0):
            self.assertIsNone(obj.cover_url)

    def test_cover_url_annotated_value_used_without_query(self):
        ObjectPhoto.objects.create(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id='p1', image_url='x',
            thumbnail_url='https://thumb1', is_author_photo=True,
            order=0, status='approved',
        )
        from django.db.models import OuterRef, Subquery
        sq = ObjectPhoto.objects.filter(
            cultural_object=OuterRef('pk'), status='approved',
        ).values('thumbnail_url')[:1]
        obj = CulturalObject.objects.annotate(
            _cover_thumbnail_url=Subquery(sq)
        ).get(pk=self.obj.pk)
        with self.assertNumQueries(0):
            self.assertEqual(obj.cover_url, 'https://thumb1')
