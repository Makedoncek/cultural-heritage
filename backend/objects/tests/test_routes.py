"""Targeted tests for Heritage Routes API."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject, Route, RouteStop, Tag


class RouteFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('alice', 'a@t.com', 'p')
        cls.other = User.objects.create_user('bob', 'b@t.com', 'p')
        cls.admin = User.objects.create_user('admin', 'admin@t.com', 'p', is_staff=True)
        cls.tag = Tag.objects.create(name='Castle', slug='castle', icon='C')

        cls.obj1 = CulturalObject.objects.create(
            title='Lutsk Castle', latitude=50.75, longitude=25.32,
            author=cls.author, status='approved',
        )
        cls.obj2 = CulturalObject.objects.create(
            title='St Sophia', latitude=50.45, longitude=30.52,
            author=cls.author, status='approved',
        )
        cls.obj_archived = CulturalObject.objects.create(
            title='Archived Site', latitude=49.0, longitude=31.0,
            author=cls.author, status='archived',
        )

    def test_user_can_create_route_starts_as_draft(self):
        self.client.force_authenticate(self.author)
        response = self.client.post('/api/routes/', {
            'title': 'Castles of Volyn',
            'description': 'One-day tour through historic castles.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        route = Route.objects.get(title='Castles of Volyn')
        self.assertEqual(route.status, 'draft')
        self.assertEqual(route.author, self.author)

    def test_draft_route_visible_only_to_author(self):
        route = Route.objects.create(title='Secret Draft', description='x', author=self.author)
        url = f'/api/routes/{route.pk}/'

        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_route_id_unique_per_route(self):
        r1 = Route.objects.create(title='Lviv Walking Tour', description='x', author=self.author)
        r2 = Route.objects.create(title='Lviv Walking Tour', description='x', author=self.author)
        self.assertNotEqual(r1.pk, r2.pk)
        self.assertIsInstance(r1.pk, int)

    def test_reorder_stops_bulk(self):
        route = Route.objects.create(title='R', description='x', author=self.author)
        s1 = RouteStop.objects.create(route=route, cultural_object=self.obj1, order=1)
        s2 = RouteStop.objects.create(route=route, cultural_object=self.obj2, order=2)

        self.client.force_authenticate(self.author)
        url = f'/api/routes/{route.pk}/reorder/'
        response = self.client.post(url, {'order': [
            {'id': s1.id, 'order': 2},
            {'id': s2.id, 'order': 1},
        ]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        s1.refresh_from_db(); s2.refresh_from_db()
        self.assertEqual(s1.order, 2)
        self.assertEqual(s2.order, 1)

    def test_only_author_or_admin_can_edit_route(self):
        route = Route.objects.create(title='Author Route', description='x', author=self.author)
        url = f'/api/routes/{route.pk}/'

        self.client.force_authenticate(self.other)
        response = self.client.patch(url, {'title': 'Hacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.author)
        response = self.client.patch(url, {'title': 'New Title', 'description': 'x'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.title, 'New Title')

    def test_max_50_stops_validation(self):
        route = Route.objects.create(title='Big', description='x', author=self.author, status='draft')
        for i in range(50):
            obj = CulturalObject.objects.create(
                title=f'Obj {i}', latitude=50.0 + i * 0.01, longitude=30.0,
                author=self.author, status='approved',
            )
            RouteStop.objects.create(route=route, cultural_object=obj, order=i + 1)

        self.client.force_authenticate(self.author)
        url = f'/api/routes/{route.pk}/stops/'
        response = self.client.post(url, {'cultural_object': self.obj2.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('50', response.data['detail'])

    def test_copy_route_creates_draft_copy(self):
        original = Route.objects.create(title='Original', description='desc', author=self.author, visibility='public', status='approved')
        original.tags.add(self.tag)
        RouteStop.objects.create(route=original, cultural_object=self.obj1, order=1, note='start')
        RouteStop.objects.create(route=original, cultural_object=self.obj2, order=2)

        self.client.force_authenticate(self.other)
        response = self.client.post(f'/api/routes/{original.pk}/copy/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        copy = Route.objects.get(pk=response.data['id'])
        self.assertEqual(copy.author, self.other)
        self.assertEqual(copy.status, 'draft')
        self.assertEqual(copy.copied_from, original)
        self.assertEqual(copy.title, 'Original (копія)')
        self.assertEqual(copy.stops.count(), 2)
        self.assertIn(self.tag, copy.tags.all())

    def test_cannot_copy_non_approved_route(self):
        draft = Route.objects.create(title='Draft', description='x', author=self.author, status='draft')
        self.client.force_authenticate(self.other)
        response = self.client.post(f'/api/routes/{draft.pk}/copy/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_archived_object_stop_marked_unavailable(self):
        route = Route.objects.create(title='R', description='x', author=self.author, visibility='public', status='approved')
        RouteStop.objects.create(route=route, cultural_object=self.obj_archived, order=1)

        response = self.client.get(f'/api/routes/{route.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['stops'][0]['is_unavailable'])

    def test_gpx_export_returns_valid_xml(self):
        route = Route.objects.create(title='Tour', description='x', author=self.author, visibility='public', status='approved')
        RouteStop.objects.create(route=route, cultural_object=self.obj1, order=1)
        RouteStop.objects.create(route=route, cultural_object=self.obj2, order=2)

        response = self.client.get(f'/api/routes/{route.pk}/export/?fmt=gpx')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/gpx+xml')
        body = response.content.decode()
        self.assertIn('<gpx', body)
        self.assertIn('Lutsk Castle', body)
        self.assertIn('St Sophia', body)

    def test_kml_export_returns_valid_xml(self):
        route = Route.objects.create(title='Tour', description='x', author=self.author, visibility='public', status='approved')
        RouteStop.objects.create(route=route, cultural_object=self.obj1, order=1)
        RouteStop.objects.create(route=route, cultural_object=self.obj2, order=2)

        response = self.client.get(f'/api/routes/{route.pk}/export/?fmt=kml')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.google-earth.kml+xml')
        body = response.content.decode()
        self.assertIn('<kml', body)
        self.assertIn('Lutsk Castle', body)

    def test_submit_requires_at_least_two_stops(self):
        route = Route.objects.create(
            title='Single', description='x', author=self.author,
            visibility='public', status='draft',
        )
        RouteStop.objects.create(route=route, cultural_object=self.obj1, order=1)

        self.client.force_authenticate(self.author)
        response = self.client.post(f'/api/routes/{route.pk}/submit/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_changes_status_to_pending(self):
        # Public route in draft can be submitted for moderation.
        route = Route.objects.create(
            title='Ready', description='x', author=self.author,
            visibility='public', status='draft',
        )
        RouteStop.objects.create(route=route, cultural_object=self.obj1, order=1)
        RouteStop.objects.create(route=route, cultural_object=self.obj2, order=2)

        self.client.force_authenticate(self.author)
        response = self.client.post(f'/api/routes/{route.pk}/submit/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.status, 'pending')

    def test_private_route_cannot_be_submitted(self):
        route = Route.objects.create(
            title='Private', description='x', author=self.author,
            visibility='private', status='draft',
        )
        RouteStop.objects.create(route=route, cultural_object=self.obj1, order=1)
        RouteStop.objects.create(route=route, cultural_object=self.obj2, order=2)
        self.client.force_authenticate(self.author)
        response = self.client.post(f'/api/routes/{route.pk}/submit/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_switch_private_to_public_resets_to_draft(self):
        # Previously approved public route → flipped to private → flipped back to public.
        route = Route.objects.create(
            title='Switched', description='x', author=self.author,
            visibility='private', status='draft',
        )
        self.client.force_authenticate(self.author)
        response = self.client.patch(
            f'/api/routes/{route.pk}/',
            {'title': 'Switched', 'description': 'x', 'visibility': 'public'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.visibility, 'public')
        self.assertEqual(route.status, 'draft')
