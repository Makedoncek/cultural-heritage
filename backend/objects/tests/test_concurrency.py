"""Concurrency regression tests.

Toggle endpoints and route-stop creation must tolerate simultaneous duplicate
requests (double-tap, client retry) without 500s or inconsistent state. Each
test fires several real requests from parallel threads released together by a
barrier, so the inserts race on actually-committed rows. APITransactionTestCase
(not the transaction-wrapped APITestCase) is required for cross-connection
visibility between threads.
"""
import threading
import uuid
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from objects.models import CulturalObject, ObjectAudio, PlannedVisit, Route, RouteStop, Visit

# Valid WAV container header so the magic-bytes audio validator accepts the upload.
_WAV = b'RIFF\x00\x00\x00\x00WAVE\x00\x00\x00\x00'

CONCURRENCY = 8


def _hammer(make_request, n=CONCURRENCY):
    """Run make_request() from n threads released simultaneously; return statuses.

    make_request must build its own APIClient (clients are not thread-safe) and
    return the response status code. Each thread closes its DB connection so the
    test DB can be torn down cleanly.
    """
    barrier = threading.Barrier(n)
    statuses = []
    guard = threading.Lock()

    def worker():
        try:
            barrier.wait(timeout=10)
            code = make_request()
            with guard:
                statuses.append(code)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return statuses


class ToggleConcurrencyTests(APITransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', 'a@t.com', 'p')
        self.author = User.objects.create_user('bob', 'b@t.com', 'p')
        self.obj = CulturalObject.objects.create(
            title='Test Castle', latitude=50.0, longitude=30.0,
            author=self.author, status='approved',
        )

    def _poster(self, url):
        def make_request():
            client = APIClient(raise_request_exception=False)
            client.force_authenticate(self.user)
            return client.post(url).status_code
        return make_request

    def test_toggle_visit_survives_simultaneous_requests(self):
        url = reverse('objects:toggle_visit', kwargs={'object_pk': self.obj.pk})
        statuses = _hammer(self._poster(url))
        self.assertNotIn(status.HTTP_500_INTERNAL_SERVER_ERROR, statuses)
        self.assertTrue(set(statuses) <= {status.HTTP_200_OK, status.HTTP_201_CREATED})
        self.assertLessEqual(
            Visit.objects.filter(user=self.user, cultural_object=self.obj).count(), 1)

    def test_toggle_planned_visit_survives_simultaneous_requests(self):
        url = reverse('objects:toggle_planned_visit', kwargs={'object_pk': self.obj.pk})
        statuses = _hammer(self._poster(url))
        self.assertNotIn(status.HTTP_500_INTERNAL_SERVER_ERROR, statuses)
        self.assertTrue(set(statuses) <= {status.HTTP_200_OK, status.HTTP_201_CREATED})
        self.assertLessEqual(
            PlannedVisit.objects.filter(user=self.user, cultural_object=self.obj).count(), 1)


class AddStopConcurrencyTests(APITransactionTestCase):
    def setUp(self):
        self.author = User.objects.create_user('alice', 'a@t.com', 'p')
        self.obj = CulturalObject.objects.create(
            title='Lutsk Castle', latitude=50.75, longitude=25.32,
            author=self.author, status='approved',
        )
        self.route = Route.objects.create(title='Tour', description='x', author=self.author)

    def test_adding_same_stop_simultaneously_creates_exactly_one(self):
        url = f'/api/routes/{self.route.pk}/stops/'

        def make_request():
            client = APIClient(raise_request_exception=False)
            client.force_authenticate(self.author)
            return client.post(url, {'cultural_object': self.obj.pk}, format='json').status_code

        statuses = _hammer(make_request)
        self.assertNotIn(status.HTTP_500_INTERNAL_SERVER_ERROR, statuses)
        self.assertTrue(set(statuses) <= {status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST})
        self.assertEqual(statuses.count(status.HTTP_201_CREATED), 1)
        self.assertEqual(
            RouteStop.objects.filter(route=self.route, cultural_object=self.obj).count(), 1)


class AudioUploadConcurrencyTests(APITransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', 'a@t.com', 'p')
        self.obj = CulturalObject.objects.create(
            title='Obj', latitude=50.0, longitude=30.0, author=self.user, status='approved',
        )

    def _make_audio(self, public_id, **kwargs):
        defaults = dict(
            cultural_object=self.obj, uploaded_by=self.user,
            cloudinary_public_id=public_id, cloudinary_url='http://x/a.mp3',
            duration_seconds=10, title='A', language='uk',
            status='approved', copyright_confirmed=True,
        )
        defaults.update(kwargs)
        return ObjectAudio.objects.create(**defaults)

    def test_concurrent_uploads_respect_object_limit(self):
        # One slot below a (patched) limit of 3; many simultaneous uploads must not overshoot.
        self._make_audio('pre0')
        self._make_audio('pre1')
        url = f'/api/objects/{self.obj.pk}/audios/'

        def fake_upload(file, object_id, uploader_id):
            pid = f'cult/{uuid.uuid4().hex}'
            return {'public_id': pid, 'url': f'http://x/{pid}.mp3', 'duration_seconds': 5}

        def make_request():
            client = APIClient(raise_request_exception=False)
            client.force_authenticate(self.user)
            audio = SimpleUploadedFile('a.mp3', _WAV, content_type='audio/mpeg')
            return client.post(url, {
                'audio': audio, 'language': 'uk', 'title': 't', 'copyright_confirmed': 'true',
            }, format='multipart').status_code

        with patch('objects.views.audio.MAX_AUDIOS_PER_OBJECT', 3), \
                patch('objects.views.audio.cloudinary_audio_service.upload_audio',
                      side_effect=fake_upload):
            statuses = _hammer(make_request)

        self.assertNotIn(status.HTTP_500_INTERNAL_SERVER_ERROR, statuses)
        active = ObjectAudio.objects.filter(cultural_object=self.obj).exclude(
            status__in=['rejected', 'archived']).count()
        self.assertEqual(active, 3)
        self.assertEqual(statuses.count(status.HTTP_201_CREATED), 1)
