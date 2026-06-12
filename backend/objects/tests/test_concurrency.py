"""Concurrency regression tests.

Toggle endpoints and route-stop creation must tolerate simultaneous duplicate
requests (double-tap, client retry) without 500s or inconsistent state. Each
test fires several real requests from parallel threads released together by a
barrier, so the inserts race on actually-committed rows. APITransactionTestCase
(not the transaction-wrapped APITestCase) is required for cross-connection
visibility between threads.
"""
import threading

from django.contrib.auth.models import User
from django.db import connection
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from objects.models import CulturalObject, PlannedVisit, Route, RouteStop, Visit

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
