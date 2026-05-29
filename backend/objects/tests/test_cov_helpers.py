"""Coverage: filters.py (EventStatusFilter), permissions.py, report_targets.py."""
from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from objects.filters import EventStatusFilter
from objects.models import CulturalObject, ObjectPhoto
from objects.permissions import (
    IsAuthorOrReadOnly, IsObjectAuthor, IsPhotoCaptionEditor, IsPhotoUploaderOrAdmin,
)
from objects.report_targets import describe_target, resolve_target


class EventStatusFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('u', 'u@t.com', 'p')
        now = timezone.now()
        cls.active = CulturalObject.objects.create(
            title='Active', latitude=50.0, longitude=30.0, author=cls.user, status='approved',
            object_type='event', event_start_date=now - timedelta(days=1), event_end_date=now + timedelta(days=1))
        cls.upcoming = CulturalObject.objects.create(
            title='Upcoming', latitude=50.0, longitude=30.0, author=cls.user, status='approved',
            object_type='event', event_start_date=now + timedelta(days=5), event_end_date=now + timedelta(days=6))

    def test_active_filter(self):
        qs = EventStatusFilter().filter(CulturalObject.objects.all(), 'active')
        self.assertIn(self.active, qs)
        self.assertNotIn(self.upcoming, qs)

    def test_upcoming_filter(self):
        qs = EventStatusFilter().filter(CulturalObject.objects.all(), 'upcoming')
        self.assertIn(self.upcoming, qs)
        self.assertNotIn(self.active, qs)

    def test_empty_and_unknown_value_return_all(self):
        base = CulturalObject.objects.all()
        self.assertEqual(EventStatusFilter().filter(base, '').count(), base.count())
        self.assertEqual(EventStatusFilter().filter(base, 'whatever').count(), base.count())


class PermissionUnitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author', 'a@t.com', 'p')
        cls.other = User.objects.create_user('other', 'o@t.com', 'p')
        cls.staff = User.objects.create_user('staff', 's@t.com', 'p', is_staff=True)
        cls.obj = CulturalObject.objects.create(
            title='O', latitude=50.0, longitude=30.0, author=cls.author, status='approved')
        cls.own_photo = ObjectPhoto.objects.create(
            cultural_object=cls.obj, uploaded_by=cls.author,
            cloudinary_public_id='p_own', image_url='http://x/i', thumbnail_url='http://x/t')
        cls.foreign_photo = ObjectPhoto.objects.create(
            cultural_object=cls.obj, uploaded_by=cls.other,
            cloudinary_public_id='p_foreign', image_url='http://x/i', thumbnail_url='http://x/t')
        cls.factory = APIRequestFactory()

    def _req(self, method, user):
        r = getattr(self.factory, method)('/')
        r.user = user
        return r

    def test_is_author_or_readonly(self):
        perm = IsAuthorOrReadOnly()
        self.assertTrue(perm.has_object_permission(self._req('get', self.other), None, self.obj))
        self.assertFalse(perm.has_object_permission(self._req('patch', self.other), None, self.obj))
        self.assertTrue(perm.has_object_permission(self._req('patch', self.author), None, self.obj))
        self.assertTrue(perm.has_object_permission(self._req('patch', self.staff), None, self.obj))

    def test_photo_uploader_or_admin(self):
        perm = IsPhotoUploaderOrAdmin()
        self.assertTrue(perm.has_object_permission(self._req('get', self.other), None, self.own_photo))
        self.assertFalse(perm.has_object_permission(self._req('delete', self.other), None, self.own_photo))
        self.assertTrue(perm.has_object_permission(self._req('delete', self.staff), None, self.own_photo))

    def test_photo_caption_editor(self):
        perm = IsPhotoCaptionEditor()
        self.assertTrue(perm.has_object_permission(self._req('get', self.other), None, self.own_photo))
        self.assertTrue(perm.has_object_permission(self._req('patch', self.staff), None, self.own_photo))
        # uploader of the photo
        self.assertTrue(perm.has_object_permission(self._req('patch', self.other), None, self.foreign_photo))
        # parent-object author (not uploader, not staff) — foreign_photo on author's object
        self.assertTrue(perm.has_object_permission(self._req('patch', self.author), None, self.foreign_photo))

    def test_is_object_author(self):
        perm = IsObjectAuthor()
        view_ok = type('V', (), {'kwargs': {'object_pk': self.obj.id}})()
        view_none = type('V', (), {'kwargs': {}})()
        view_missing = type('V', (), {'kwargs': {'object_pk': 999999}})()

        anon = self._req('post', AnonymousUser())
        self.assertFalse(perm.has_permission(anon, view_ok))

        author_req = self._req('post', self.author)
        self.assertFalse(perm.has_permission(author_req, view_none))
        self.assertFalse(perm.has_permission(author_req, view_missing))
        self.assertTrue(perm.has_permission(author_req, view_ok))


class ReportTargetsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('u', 'u@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Site', latitude=50.0, longitude=30.0, author=cls.user, status='approved')

    def test_describe_registered_target(self):
        d = describe_target(self.obj)
        self.assertEqual(d['target_type'], 'object')
        self.assertEqual(d['target_title'], 'Site')
        self.assertEqual(d['target_url'], f'/objects/{self.obj.id}')

    def test_describe_none_target(self):
        d = describe_target(None)
        self.assertIsNone(d['target_type'])
        self.assertEqual(d['target_title'], '(видалено)')

    def test_describe_unknown_type(self):
        d = describe_target(self.user)
        self.assertIsNone(d['target_type'])

    def test_resolve_target(self):
        inst, cfg = resolve_target('object', self.obj.id)
        self.assertEqual(inst, self.obj)
        self.assertIsNotNone(cfg)
        none_inst, none_cfg = resolve_target('nope', 1)
        self.assertIsNone(none_inst)
        self.assertIsNone(none_cfg)
