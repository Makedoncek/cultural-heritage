"""Coverage: views.py — RouteViewSet branches (lifecycle actions, stops,
catalog filters, ORS-backed geometry/optimization, export) and _enrich_ors_error."""
from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject, Route, RouteStop, Tag, Visit
from objects.services.ors import ORSError
from objects.views import _enrich_ors_error

ORS_DIRECTIONS_OK = {'geometry': 'encoded_polyline', 'distance_m': 1234.5, 'duration_s': 890.0}


class RouteTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('alice', 'a@t.com', 'p')
        cls.other = User.objects.create_user('bob', 'b@t.com', 'p')
        cls.admin = User.objects.create_user('admin', 'ad@t.com', 'p', is_staff=True)
        cls.objs = [
            CulturalObject.objects.create(
                title=f'Site {i}', latitude=50.0 + i * 0.1, longitude=30.0 + i * 0.1,
                author=cls.author, status='approved',
            )
            for i in range(3)
        ]

    def _route(self, with_stops=0, **kwargs):
        defaults = dict(title='R', description='x', author=self.author,
                        status='draft', visibility='private')
        defaults.update(kwargs)
        route = Route.objects.create(**defaults)
        for i in range(with_stops):
            RouteStop.objects.create(
                route=route, cultural_object=self.objs[i], order=i + 1)
        return route


class RouteLifecycleBranchTests(RouteTestBase):
    def test_destroy_branches(self):
        route = self._route()
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.delete(f'/api/routes/{route.pk}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        resp = self.client.delete(f'/api/routes/{route.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        route.refresh_from_db()
        self.assertEqual(route.status, 'archived')

    def test_restore_branches(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.post('/api/routes/999999/restore/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        archived = self._route(status='archived')
        self.assertEqual(
            self.client.post(f'/api/routes/{archived.pk}/restore/').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        draft = self._route(status='draft')
        self.assertEqual(
            self.client.post(f'/api/routes/{draft.pk}/restore/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        resp = self.client.post(f'/api/routes/{archived.pk}/restore/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        archived.refresh_from_db()
        self.assertEqual(archived.status, 'draft')

    def test_hard_delete_branches(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.delete('/api/routes/999999/hard-delete/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        route = self._route()
        self.assertEqual(
            self.client.delete(f'/api/routes/{route.pk}/hard-delete/').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        resp = self.client.delete(f'/api/routes/{route.pk}/hard-delete/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Route.objects.filter(pk=route.pk).exists())

    def test_submit_branches(self):
        # Non-author cannot submit (admin is not the author either).
        route = self._route(visibility='public', with_stops=2)
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.post(f'/api/routes/{route.pk}/submit/').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        # Non-draft cannot be submitted.
        pending = self._route(visibility='public', status='pending', with_stops=2)
        self.assertEqual(
            self.client.post(f'/api/routes/{pending.pk}/submit/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        resp = self.client.post(f'/api/routes/{route.pk}/submit/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.status, 'pending')

    def test_my_routes_status_filter(self):
        self._route(status='draft')
        self._route(status='archived')
        self.client.force_authenticate(self.author)
        resp = self.client.get('/api/users/me/routes/', {'status': 'draft'})
        self.assertEqual(resp.data['count'], 1)


class RouteCatalogFilterTests(RouteTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tag = Tag.objects.create(name='Castles', slug='castles', icon='C')
        cls.featured = Route.objects.create(
            title='Featured walk', description='castles tour', author=cls.author,
            status='approved', visibility='public', is_featured=True,
            estimated_duration_minutes=120,
        )
        cls.featured.tags.add(cls.tag)
        cls.plain = Route.objects.create(
            title='Plain stroll', description='park', author=cls.author,
            status='approved', visibility='public',
            estimated_duration_minutes=30,
        )

    def test_list_filters(self):
        cases = [
            ({'is_featured': 'true'}, ['Featured walk']),
            ({'tags': str(self.tag.pk)}, ['Featured walk']),
            ({'tags': 'abc'}, ['Featured walk', 'Plain stroll']),
            ({'search': 'castles'}, ['Featured walk']),
            ({'duration_min': '60'}, ['Featured walk']),
            ({'duration_max': '60'}, ['Plain stroll']),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                resp = self.client.get('/api/routes/', params)
                titles = sorted(r['title'] for r in resp.data['results'])
                self.assertEqual(titles, sorted(expected))


class RouteStopBranchTests(RouteTestBase):
    def test_add_stop_branches(self):
        route = self._route(with_stops=1)
        url = f'/api/routes/{route.pk}/stops/'
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.post(url, {'cultural_object': self.objs[1].pk}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        # Unknown object → 400
        resp = self.client.post(url, {'cultural_object': 999999}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Duplicate stop → 400
        resp = self.client.post(url, {'cultural_object': self.objs[0].pk}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Success → order = max+1
        resp = self.client.post(
            url, {'cultural_object': self.objs[1].pk, 'note': 'stop note'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['order'], 2)

    def test_add_stop_limit(self):
        route = self._route()
        RouteStop.objects.create(route=route, cultural_object=self.objs[0], order=1)
        self.client.force_authenticate(self.author)
        with patch('objects.views.MAX_STOPS_PER_ROUTE', 1):
            resp = self.client.post(
                f'/api/routes/{route.pk}/stops/',
                {'cultural_object': self.objs[1].pk}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_branches(self):
        route = self._route(with_stops=2)
        stops = list(route.stops.order_by('order'))
        url = f'/api/routes/{route.pk}/reorder/'
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.post(url, {'order': []}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        # Not a list → 400
        resp = self.client.post(url, {'order': 'x'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Foreign/unknown stop id → 400
        resp = self.client.post(url, {'order': [{'id': 999999, 'order': 1}]}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Success
        resp = self.client.post(url, {'order': [
            {'id': stops[0].pk, 'order': 2}, {'id': stops[1].pk, 'order': 1},
        ]}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        stops[0].refresh_from_db()
        self.assertEqual(stops[0].order, 2)

    def test_stop_detail_branches(self):
        route = self._route(with_stops=3)
        stops = list(route.stops.order_by('order'))
        url = f'/api/routes/{route.pk}/stops/{stops[1].pk}/'
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.patch(url, {'note': 'x'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        # Unknown stop → 404
        resp = self.client.patch(
            f'/api/routes/{route.pk}/stops/999999/', {'note': 'x'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        # PATCH note
        resp = self.client.patch(url, {'note': 'updated'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['note'], 'updated')
        # DELETE → remaining stops recompacted 1..N
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        orders = list(route.stops.order_by('order').values_list('order', flat=True))
        self.assertEqual(orders, [1, 2])


class RouteOrsTests(RouteTestBase):
    def test_compute_geometry_branches(self):
        route = self._route(with_stops=2)
        url = f'/api/routes/{route.pk}/compute-geometry/'
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.author)
        # <2 stops → 400
        short = self._route(with_stops=1)
        self.assertEqual(
            self.client.post(f'/api/routes/{short.pk}/compute-geometry/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        # ORS error → 502 with enriched detail
        with patch('objects.services.ors.get_directions',
                   side_effect=ORSError('coordinate 0: 30.0000000 50.0000000 not routable')):
            resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('Site 0', resp.data['detail'])
        # Success → geometry cached on the route
        with patch('objects.services.ors.get_directions', return_value=ORS_DIRECTIONS_OK):
            resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.route_geometry, 'encoded_polyline')

    def test_optimize_order_branches(self):
        route = self._route(with_stops=3)
        url = f'/api/routes/{route.pk}/optimize-order/'
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.author)
        # <3 stops → 400
        short = self._route(with_stops=2)
        self.assertEqual(
            self.client.post(f'/api/routes/{short.pk}/optimize-order/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        # Optimization error → 502
        with patch('objects.services.ors.optimize_order', side_effect=ORSError('vroom fail')):
            resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)
        # Success + geometry refresh succeeds
        with patch('objects.services.ors.optimize_order', return_value=[2, 0, 1]), \
                patch('objects.services.ors.get_directions', return_value=ORS_DIRECTIONS_OK):
            resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['new_order'], [2, 0, 1])
        route.refresh_from_db()
        self.assertEqual(route.route_geometry, 'encoded_polyline')
        # Success but geometry refresh fails → cached geometry cleared (non-fatal)
        with patch('objects.services.ors.optimize_order', return_value=[0, 1, 2]), \
                patch('objects.services.ors.get_directions', side_effect=ORSError('no route')):
            resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertIsNone(route.route_geometry)


class RouteMarkCompletedTests(RouteTestBase):
    def test_mark_completed_creates_missing_visits(self):
        route = self._route(with_stops=3)
        Visit.objects.create(user=self.other, cultural_object=self.objs[0])
        self.client.force_authenticate(self.other)
        resp = self.client.post(f'/api/routes/{route.pk}/mark-completed/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['created_visits'], 2)
        self.assertEqual(resp.data['total_stops'], 3)
        self.assertEqual(Visit.objects.filter(user=self.other).count(), 3)


class RouteExportTests(RouteTestBase):
    def test_export_formats(self):
        route = self._route(with_stops=2, title='Експорт маршрут')
        self.client.force_authenticate(self.author)
        for fmt, expected_type in [
            ('gpx', 'application/gpx+xml'),
            ('kml', 'application/vnd.google-earth.kml+xml'),
            ('kmz', 'application/vnd.google-earth.kmz'),
        ]:
            with self.subTest(fmt=fmt):
                resp = self.client.get(f'/api/routes/{route.pk}/export/', {'fmt': fmt})
                self.assertEqual(resp.status_code, status.HTTP_200_OK)
                self.assertEqual(resp['Content-Type'], expected_type)
                self.assertIn('attachment;', resp['Content-Disposition'])
        resp = self.client.get(f'/api/routes/{route.pk}/export/', {'fmt': 'pdf'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class EnrichOrsErrorTests(RouteTestBase):
    def setUp(self):
        route = self._route(with_stops=2)
        self.stops = list(route.stops.order_by('order'))

    def test_pattern_coordinate(self):
        msg = _enrich_ors_error('coordinate 0: 30.0000000 50.0000000 not found', self.stops)
        self.assertIn('«Site 0»', msg)

    def test_pattern_points_pair(self):
        msg = _enrich_ors_error(
            'no route between points 0 (30.0000000 50.0000000) and 1 (30.1000000 50.1000000)',
            self.stops,
        )
        self.assertIn('«Site 0»', msg)
        self.assertIn('«Site 1»', msg)

    def test_pattern_location(self):
        msg = _enrich_ors_error('unreachable location [30.100000,50.100000]', self.stops)
        self.assertIn('«Site 1»', msg)

    def test_unmatched_coordinates_kept_verbatim(self):
        original = 'coordinate 5: 11.1111111 22.2222222 not found'
        self.assertEqual(_enrich_ors_error(original, self.stops), original)
