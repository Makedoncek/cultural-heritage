"""Тести полегшеного ендпоінта GET /api/objects/map/."""
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from objects.models import CulturalObject, Tag, Visit

MAP_URL = '/api/objects/map/'
EXPECTED_FIELDS = {
    'id', 'title', 'latitude', 'longitude', 'status', 'object_type',
    'event_start_date', 'event_end_date', 'tags', 'is_visited',
}


class MapEndpointTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('mapuser', 'm@t.com', 'p')
        cls.other = User.objects.create_user('other', 'o@t.com', 'p')
        cls.tag = Tag.objects.create(name='Замок', slug='zamok', icon='🏰')
        cls.tag2 = Tag.objects.create(name='Музей', slug='muzey', icon='🏛️')

        def make(title, status='approved', author=None, **kwargs):
            obj = CulturalObject.objects.create(
                title=title, latitude=50.0, longitude=30.0,
                author=author or cls.user, status=status, **kwargs
            )
            obj.tags.add(cls.tag)
            return obj

        cls.approved = make('Approved Castle')
        cls.own_pending = make('Own Pending', status='pending')
        cls.foreign_pending = make('Foreign Pending', status='pending', author=cls.other)
        cls.archived = make('Archived One', status='archived')
        cls.event = make(
            'Event One',
            object_type='event',
            event_start_date='2026-07-01T10:00:00+03:00',
            event_end_date='2026-07-02T10:00:00+03:00',
        )

    def test_anonymous_sees_only_approved_as_flat_list(self):
        response = self.client.get(MAP_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)  # без пагінаційної обгортки
        titles = {o['title'] for o in response.data}
        self.assertEqual(titles, {'Approved Castle', 'Event One'})

    def test_field_set_is_lightweight(self):
        response = self.client.get(MAP_URL)
        self.assertEqual(set(response.data[0].keys()), EXPECTED_FIELDS)

    def test_tags_are_ids(self):
        response = self.client.get(MAP_URL)
        for obj in response.data:
            self.assertTrue(all(isinstance(t, int) for t in obj['tags']))

    def test_authenticated_sees_own_pending_but_not_foreign(self):
        self.client.force_authenticate(self.user)
        titles = {o['title'] for o in self.client.get(MAP_URL).data}
        self.assertIn('Own Pending', titles)
        self.assertNotIn('Foreign Pending', titles)
        self.assertNotIn('Archived One', titles)

    def test_object_type_filter(self):
        response = self.client.get(MAP_URL, {'object_type': 'event'})
        titles = {o['title'] for o in response.data}
        self.assertEqual(titles, {'Event One'})

    def test_tags_filter(self):
        solo = CulturalObject.objects.create(
            title='Tagged Museum', latitude=49.0, longitude=31.0,
            author=self.user, status='approved',
        )
        solo.tags.add(self.tag2)
        response = self.client.get(MAP_URL, {'tags': str(self.tag2.id)})
        titles = {o['title'] for o in response.data}
        self.assertEqual(titles, {'Tagged Museum'})

    def test_search_filter(self):
        response = self.client.get(MAP_URL, {'search': 'Castle'})
        titles = {o['title'] for o in response.data}
        self.assertEqual(titles, {'Approved Castle'})

    def test_is_visited_annotated_without_n_plus_one(self):
        Visit.objects.create(user=self.user, cultural_object=self.approved)
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(MAP_URL)
        by_title = {o['title']: o for o in response.data}
        self.assertTrue(by_title['Approved Castle']['is_visited'])
        self.assertFalse(by_title['Event One']['is_visited'])
        # кількість запитів не залежить від кількості об'єктів
        self.assertLess(len(ctx.captured_queries), 10)

    def test_is_visited_false_for_anonymous(self):
        response = self.client.get(MAP_URL)
        self.assertFalse(any(o['is_visited'] for o in response.data))
