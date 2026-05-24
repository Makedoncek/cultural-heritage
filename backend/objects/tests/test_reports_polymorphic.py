"""Tests for polymorphic reports — reporting objects, routes, photos, audio and translations
through the generic /api/reports/create/ endpoint."""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import (
    CulturalObject, Route, ObjectPhoto, ObjectAudio,
    CulturalObjectTranslation, InaccuracyReport,
)

CREATE_URL = '/api/reports/create/'
ON_MY_CONTENT_URL = '/api/users/me/objects/reports/'
MY_REPORTS_URL = '/api/users/me/reports/'


class PolymorphicReportTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author', 'a@t.com', 'p')
        cls.reporter = User.objects.create_user('reporter', 'r@t.com', 'p')
        cls.uploader = User.objects.create_user('uploader', 'u@t.com', 'p')
        cls.translator = User.objects.create_user('translator', 't@t.com', 'p')

        cls.obj = CulturalObject.objects.create(
            title='Object', latitude=50.0, longitude=30.0,
            author=cls.author, status='approved',
        )
        cls.route = Route.objects.create(
            title='Route', description='desc', author=cls.author,
            status='approved', visibility='public',
        )
        cls.photo = ObjectPhoto.objects.create(
            cultural_object=cls.obj, uploaded_by=cls.uploader,
            cloudinary_public_id='pid1', image_url='http://e/i.jpg',
            thumbnail_url='http://e/t.jpg', status='approved',
        )
        cls.audio = ObjectAudio.objects.create(
            cultural_object=cls.obj, uploaded_by=cls.uploader,
            cloudinary_public_id='aid1', cloudinary_url='http://e/a.mp3',
            duration_seconds=12, title='Audio', status='approved',
        )
        cls.translation = CulturalObjectTranslation.objects.create(
            cultural_object=cls.obj, language='en', title='Object EN',
            description='desc', status='approved', submitted_by=cls.translator,
        )

    def _report(self, target_type, target_id, reason='other', note='issue'):
        return self.client.post(CREATE_URL, {
            'target_type': target_type, 'target_id': target_id,
            'reason_type': reason, 'note': note,
        }, format='json')

    def test_report_object_sets_owner(self):
        self.client.force_authenticate(self.reporter)
        resp = self._report('object', self.obj.pk, reason='wrong_coords')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        report = InaccuracyReport.objects.get()
        self.assertEqual(report.content_owner, self.author)
        self.assertEqual(report.content_type, ContentType.objects.get_for_model(CulturalObject))
        self.assertEqual(report.object_id, self.obj.pk)

    def test_report_route(self):
        self.client.force_authenticate(self.reporter)
        resp = self._report('route', self.route.pk, reason='spam')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InaccuracyReport.objects.get().content_owner, self.author)

    def test_report_photo_owner_is_uploader(self):
        self.client.force_authenticate(self.reporter)
        resp = self._report('photo', self.photo.pk, reason='offensive')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InaccuracyReport.objects.get().content_owner, self.uploader)

    def test_report_audio_owner_is_uploader(self):
        self.client.force_authenticate(self.reporter)
        resp = self._report('audio', self.audio.pk, reason='copyright')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InaccuracyReport.objects.get().content_owner, self.uploader)

    def test_report_translation_owner_is_submitter(self):
        self.client.force_authenticate(self.reporter)
        resp = self._report('object_translation', self.translation.pk, reason='wrong_description')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InaccuracyReport.objects.get().content_owner, self.translator)

    def test_unknown_target_type_404(self):
        self.client.force_authenticate(self.reporter)
        resp = self._report('made_up', 1)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_target_404(self):
        self.client.force_authenticate(self.reporter)
        resp = self._report('object', 999999)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_reason_400(self):
        self.client.force_authenticate(self.reporter)
        resp = self._report('object', self.obj.pk, reason='nonsense')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_401(self):
        resp = self._report('object', self.obj.pk)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_throttle_same_target_24h(self):
        self.client.force_authenticate(self.reporter)
        self._report('object', self.obj.pk)
        resp = self._report('object', self.obj.pk)
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_different_targets_not_throttled(self):
        self.client.force_authenticate(self.reporter)
        self._report('object', self.obj.pk)
        resp = self._report('route', self.route.pk)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_serializer_exposes_target_fields(self):
        self.client.force_authenticate(self.reporter)
        self._report('route', self.route.pk)
        resp = self.client.get(MY_REPORTS_URL)
        row = resp.data['results'][0]
        self.assertEqual(row['target_type'], 'route')
        self.assertEqual(row['target_title'], 'Route')
        self.assertEqual(row['target_url'], f'/routes/{self.route.pk}')

    def test_reports_on_my_content_spans_types(self):
        # reporter flags both the author's object and route; author sees both.
        self.client.force_authenticate(self.reporter)
        self._report('object', self.obj.pk)
        self._report('route', self.route.pk)
        self.client.force_authenticate(self.author)
        resp = self.client.get(ON_MY_CONTENT_URL)
        self.assertEqual(resp.data['count'], 2)
