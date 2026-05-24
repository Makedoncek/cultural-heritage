"""Tests for crowdsourced translations — submission, language resolution in the API,
available languages, and the 'my translations' list with status filter."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import (
    CulturalObject, Route, CulturalObjectTranslation, RouteTranslation,
)

MY_TRANSLATIONS_URL = '/api/users/me/translations/'


class TranslationSubmissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author', 'a@t.com', 'p')
        cls.translator = User.objects.create_user('translator', 't@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Замок', description='опис', latitude=50.0, longitude=30.0,
            author=cls.author, status='approved',
        )
        cls.route = Route.objects.create(
            title='Маршрут', description='опис', author=cls.author,
            status='approved', visibility='public',
        )

    def _obj_submit_url(self):
        return f'/api/objects/{self.obj.pk}/translations/'

    def test_submit_object_translation_pending(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.post(self._obj_submit_url(), {
            'language': 'en', 'title': 'Castle', 'description': 'description',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        tr = CulturalObjectTranslation.objects.get()
        self.assertEqual(tr.status, 'pending')
        self.assertEqual(tr.submitted_by, self.translator)
        self.assertEqual(tr.language, 'en')

    def test_submit_route_translation(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.post(f'/api/routes/{self.route.pk}/translations/', {
            'language': 'pl', 'title': 'Trasa', 'description': 'opis',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RouteTranslation.objects.get().language, 'pl')

    def test_original_language_proposal_allowed(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.post(self._obj_submit_url(), {
            'language': 'uk', 'title': 'Замок (виправлено)', 'description': 'новий опис',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_multiple_pending_proposals_allowed(self):
        self.client.force_authenticate(self.translator)
        first = self.client.post(self._obj_submit_url(), {'language': 'en', 'title': 'A', 'description': ''}, format='json')
        second = self.client.post(self._obj_submit_url(), {'language': 'en', 'title': 'B', 'description': ''}, format='json')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CulturalObjectTranslation.objects.filter(language='en', status='pending').count(), 2)

    def test_submit_requires_auth(self):
        resp = self.client.post(self._obj_submit_url(), {'language': 'en', 'title': 'X'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_language_rejected(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.post(self._obj_submit_url(), {'language': 'xx', 'title': 'X'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TranslationResolutionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author2', 'a2@t.com', 'p')
        cls.translator = User.objects.create_user('translator2', 't2@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Замок', description='опис українською', latitude=50.0, longitude=30.0,
            author=cls.author, status='approved',
        )
        cls.en = CulturalObjectTranslation.objects.create(
            cultural_object=cls.obj, language='en', title='Castle',
            description='english description', status='approved', submitted_by=cls.translator,
        )

    def _detail(self, lang=None):
        url = f'/api/objects/{self.obj.pk}/'
        if lang:
            url += f'?lang={lang}'
        return self.client.get(url)

    def test_approved_translation_served(self):
        resp = self._detail('en')
        self.assertEqual(resp.data['title'], 'Castle')
        self.assertEqual(resp.data['description'], 'english description')
        self.assertFalse(resp.data['translation_missing'])
        self.assertEqual(resp.data['current_translation_id'], self.en.id)

    def test_original_served_by_default(self):
        resp = self._detail('uk')
        self.assertEqual(resp.data['title'], 'Замок')
        self.assertFalse(resp.data['translation_missing'])
        self.assertIsNone(resp.data['current_translation_id'])

    def test_missing_translation_falls_back_with_flag(self):
        resp = self._detail('pl')
        self.assertEqual(resp.data['title'], 'Замок')  # falls back to original
        self.assertTrue(resp.data['translation_missing'])
        self.assertIsNone(resp.data['current_translation_id'])

    def test_available_languages(self):
        resp = self._detail()
        self.assertIn('uk', resp.data['available_languages'])
        self.assertIn('en', resp.data['available_languages'])
        self.assertNotIn('pl', resp.data['available_languages'])

    def test_pending_translation_not_served(self):
        CulturalObjectTranslation.objects.create(
            cultural_object=self.obj, language='de', title='Schloss',
            description='', status='pending', submitted_by=self.translator,
        )
        resp = self._detail('de')
        self.assertEqual(resp.data['title'], 'Замок')  # pending is not shown
        self.assertTrue(resp.data['translation_missing'])
        self.assertNotIn('de', resp.data['available_languages'])


class MyTranslationsListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author3', 'a3@t.com', 'p')
        cls.translator = User.objects.create_user('translator3', 't3@t.com', 'p')
        cls.other = User.objects.create_user('other3', 'o3@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Об\'єкт', latitude=50.0, longitude=30.0, author=cls.author, status='approved',
        )
        cls.route = Route.objects.create(
            title='Маршрут', description='опис', author=cls.author, status='approved', visibility='public',
        )
        CulturalObjectTranslation.objects.create(
            cultural_object=cls.obj, language='en', title='Object', description='',
            status='approved', submitted_by=cls.translator,
        )
        CulturalObjectTranslation.objects.create(
            cultural_object=cls.obj, language='pl', title='Obiekt', description='',
            status='pending', submitted_by=cls.translator,
        )
        RouteTranslation.objects.create(
            route=cls.route, language='en', title='Route', description='',
            status='rejected', submitted_by=cls.translator,
        )
        # Another user's translation — must not leak into translator's list.
        CulturalObjectTranslation.objects.create(
            cultural_object=cls.obj, language='de', title='Objekt', description='',
            status='pending', submitted_by=cls.other,
        )

    def test_lists_only_own_across_types(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.get(MY_TRANSLATIONS_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 3)
        kinds = {r['kind'] for r in resp.data['results']}
        self.assertEqual(kinds, {'object', 'route'})

    def test_status_filter(self):
        self.client.force_authenticate(self.translator)
        resp = self.client.get(MY_TRANSLATIONS_URL + '?status=pending')
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['status'], 'pending')

    def test_requires_auth(self):
        resp = self.client.get(MY_TRANSLATIONS_URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TranslationLifecycleTests(APITestCase):
    """Archive → permanent delete, and edit = re-moderation, with the description-replacement guard."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('la', 'la@t.com', 'p')
        cls.sub = User.objects.create_user('ls', 'ls@t.com', 'p')
        cls.other = User.objects.create_user('lo', 'lo@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Замок', description='опис українською', latitude=50.0, longitude=30.0,
            author=cls.author, status='approved', original_language='uk',
        )

    def _mk(self, language='en', status='pending', title='X', user=None):
        return CulturalObjectTranslation.objects.create(
            cultural_object=self.obj, language=language, title=title, description='d',
            status=status, submitted_by=user or self.sub,
        )

    def test_archive_then_delete(self):
        tr = self._mk()
        self.client.force_authenticate(self.sub)
        a = self.client.post(f'/api/translations/object/{tr.id}/archive/')
        self.assertEqual(a.status_code, status.HTTP_200_OK)
        tr.refresh_from_db()
        self.assertEqual(tr.status, 'archived')
        d = self.client.delete(f'/api/translations/object/{tr.id}/')
        self.assertEqual(d.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CulturalObjectTranslation.objects.filter(pk=tr.id).exists())

    def test_delete_requires_archived(self):
        tr = self._mk(status='pending')
        self.client.force_authenticate(self.sub)
        resp = self.client.delete(f'/api/translations/object/{tr.id}/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(CulturalObjectTranslation.objects.filter(pk=tr.id).exists())

    def test_edit_resubmits_for_moderation(self):
        tr = self._mk(status='rejected', title='Old')
        self.client.force_authenticate(self.sub)
        resp = self.client.patch(f'/api/translations/object/{tr.id}/',
                                 {'title': 'New', 'description': 'nd'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tr.refresh_from_db()
        self.assertEqual(tr.title, 'New')
        self.assertEqual(tr.status, 'pending')

    def test_cannot_manage_others_translation(self):
        tr = self._mk()
        self.client.force_authenticate(self.other)
        resp = self.client.post(f'/api/translations/object/{tr.id}/archive/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_archive_approved_blocked_when_no_replacement(self):
        # Object with empty description; the approved EN translation is the only description.
        obj = CulturalObject.objects.create(
            title='NoDesc', description='', latitude=50.0, longitude=30.0,
            author=self.author, status='approved', original_language='uk',
        )
        tr = CulturalObjectTranslation.objects.create(
            cultural_object=obj, language='en', title='Only', description='only desc',
            status='approved', submitted_by=self.sub,
        )
        self.client.force_authenticate(self.sub)
        resp = self.client.post(f'/api/translations/object/{tr.id}/archive/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        tr.refresh_from_db()
        self.assertEqual(tr.status, 'approved')

    def test_archive_approved_allowed_with_canonical_description(self):
        # self.obj has a non-empty canonical description → fallback exists.
        tr = self._mk(language='pl', status='approved')
        self.client.force_authenticate(self.sub)
        resp = self.client.post(f'/api/translations/object/{tr.id}/archive/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class TranslationAdminApprovalTests(APITestCase):
    """The change-page approval must replace an existing approved translation without
    being blocked by the partial unique-approved constraint."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('aa', 'aa@t.com', 'p')
        cls.sub = User.objects.create_user('ss', 'ss@t.com', 'p')
        cls.route = Route.objects.create(
            title='Маршрут', description='опис', author=cls.author,
            status='approved', visibility='public', original_language='uk',
        )

    def _approve_via_admin(self, translation):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from objects.admin import RouteTranslationAdmin
        from objects.models import RouteTranslation
        adm = RouteTranslationAdmin(RouteTranslation, AdminSite())
        request = RequestFactory().post('/admin/')
        request.user = self.author
        translation.status = 'approved'
        adm.save_model(request, translation, form=None, change=True)

    def test_change_page_approve_replaces_existing_approved(self):
        old = RouteTranslation.objects.create(
            route=self.route, language='pl', title='Stara', description='',
            status='approved', submitted_by=self.sub,
        )
        new = RouteTranslation.objects.create(
            route=self.route, language='pl', title='Nowa', description='',
            status='pending', submitted_by=self.sub,
        )
        self._approve_via_admin(new)
        self.assertFalse(RouteTranslation.objects.filter(pk=old.pk).exists())
        new.refresh_from_db()
        self.assertEqual(new.status, 'approved')
        self.assertEqual(
            RouteTranslation.objects.filter(route=self.route, language='pl', status='approved').count(), 1,
        )

    def test_form_skips_constraint_validation(self):
        # With an approved PL translation present, the admin form for a second PL
        # translation set to approved must validate (constraint check deferred to save_model).
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from objects.admin import RouteTranslationAdmin
        from objects.models import RouteTranslation
        RouteTranslation.objects.create(
            route=self.route, language='pl', title='Stara', description='',
            status='approved', submitted_by=self.sub,
        )
        pending = RouteTranslation.objects.create(
            route=self.route, language='pl', title='Nowa', description='',
            status='pending', submitted_by=self.sub,
        )
        request = RequestFactory().post('/admin/')
        request.user = self.author
        FormClass = RouteTranslationAdmin(RouteTranslation, AdminSite()).get_form(request, obj=pending, change=True)
        form = FormClass(
            data={'route': self.route.pk, 'language': 'pl', 'title': 'Nowa',
                  'description': '', 'status': 'approved', 'reviewer_note': ''},
            instance=pending,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())
