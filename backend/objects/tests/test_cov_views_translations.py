"""Coverage: views.py — manage/archive/restore own translation proposals
and the sole-approved-description replacement guard."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import (
    CulturalObject, CulturalObjectTranslation, Route, RouteTranslation,
)


class ManageOwnTranslationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.translator = User.objects.create_user('translator', 't@t.com', 'p')
        cls.other = User.objects.create_user('other', 'o@t.com', 'p')
        cls.author = User.objects.create_user('author', 'a@t.com', 'p')
        # Object with empty canonical description — sole approved translation guard applies.
        cls.obj = CulturalObject.objects.create(
            title='Obj', description='', latitude=50.0, longitude=30.0,
            author=cls.author, status='approved',
        )
        cls.route = Route.objects.create(
            title='Route', description='has canonical text', author=cls.author,
            status='approved', visibility='public',
        )

    def _obj_translation(self, **kwargs):
        defaults = dict(
            cultural_object=self.obj, language='en', title='T',
            description='d', status='pending', submitted_by=self.translator,
        )
        defaults.update(kwargs)
        return CulturalObjectTranslation.objects.create(**defaults)

    def test_unknown_kind_404(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.patch('/api/translations/bogus/1/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_translation_not_found_404(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.patch('/api/translations/object/999999/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_foreign_translation_403(self):
        tr = self._obj_translation()
        self.client.force_authenticate(self.other)
        resp = self.client.patch(f'/api/translations/object/{tr.pk}/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_requires_archived_first(self):
        tr = self._obj_translation(status='pending')
        self.client.force_authenticate(self.translator)
        resp = self.client.delete(f'/api/translations/object/{tr.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        tr.status = 'archived'
        tr.save(update_fields=['status'])
        resp = self.client.delete(f'/api/translations/object/{tr.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CulturalObjectTranslation.objects.filter(pk=tr.pk).exists())

    def test_patch_sole_approved_description_blocked(self):
        tr = self._obj_translation(status='approved')
        self.client.force_authenticate(self.translator)
        resp = self.client.patch(
            f'/api/translations/object/{tr.pk}/', {'title': 'New'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_approved_with_replacement_resubmits_as_pending(self):
        tr = self._obj_translation(status='approved', language='en')
        self._obj_translation(status='approved', language='pl', title='Inny')
        self.client.force_authenticate(self.translator)
        resp = self.client.patch(
            f'/api/translations/object/{tr.pk}/',
            {'title': 'Edited', 'description': 'new text'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tr.refresh_from_db()
        self.assertEqual(tr.status, 'pending')
        self.assertEqual(tr.title, 'Edited')

    def test_patch_route_translation_with_canonical_description(self):
        # Route has a non-empty canonical description → guard passes via parent text.
        tr = RouteTranslation.objects.create(
            route=self.route, language='en', title='T', description='d',
            status='approved', submitted_by=self.translator,
        )
        self.client.force_authenticate(self.translator)
        resp = self.client.patch(
            f'/api/translations/route/{tr.pk}/', {'title': 'Edited'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tr.refresh_from_db()
        self.assertEqual(tr.status, 'pending')


class ArchiveRestoreOwnTranslationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.translator = User.objects.create_user('translator', 't@t.com', 'p')
        cls.author = User.objects.create_user('author', 'a@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Obj', description='', latitude=50.0, longitude=30.0,
            author=cls.author, status='approved',
        )

    def _translation(self, **kwargs):
        defaults = dict(
            cultural_object=self.obj, language='en', title='T',
            description='d', status='pending', submitted_by=self.translator,
        )
        defaults.update(kwargs)
        return CulturalObjectTranslation.objects.create(**defaults)

    def test_archive_sole_approved_blocked(self):
        tr = self._translation(status='approved')
        self.client.force_authenticate(self.translator)
        resp = self.client.post(f'/api/translations/object/{tr.pk}/archive/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_archive_pending_succeeds(self):
        tr = self._translation(status='pending')
        self.client.force_authenticate(self.translator)
        resp = self.client.post(f'/api/translations/object/{tr.pk}/archive/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tr.refresh_from_db()
        self.assertEqual(tr.status, 'archived')

    def test_restore_not_found(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.post('/api/translations/object/999999/restore/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_restore_branches(self):
        self.client.force_authenticate(self.translator)
        # non-archived → 400
        pending = self._translation(status='pending')
        resp = self.client.post(f'/api/translations/object/{pending.pk}/restore/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # archived → back to pending
        archived = self._translation(status='archived', language='pl')
        resp = self.client.post(f'/api/translations/object/{archived.pk}/restore/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        archived.refresh_from_db()
        self.assertEqual(archived.status, 'pending')
