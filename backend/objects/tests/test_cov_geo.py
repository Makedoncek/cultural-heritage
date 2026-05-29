"""Coverage: services/geo.py — Haversine distance + nearby-object search."""
from django.contrib.auth.models import User
from django.test import TestCase

from objects.models import CulturalObject
from objects.services.geo import haversine_distance_m, find_nearby_objects


class HaversineTests(TestCase):
    def test_zero_distance_for_same_point(self):
        self.assertAlmostEqual(haversine_distance_m(50.0, 30.0, 50.0, 30.0), 0.0, places=3)

    def test_one_degree_latitude_is_about_111km(self):
        d = haversine_distance_m(50.0, 30.0, 51.0, 30.0)
        self.assertAlmostEqual(d, 111_000, delta=1500)

    def test_distance_is_symmetric(self):
        a = haversine_distance_m(50.0, 30.0, 50.5, 30.5)
        b = haversine_distance_m(50.5, 30.5, 50.0, 30.0)
        self.assertAlmostEqual(a, b, places=6)


class FindNearbyObjectsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('u', 'u@t.com', 'p')
        cls.center = CulturalObject.objects.create(
            title='Center', latitude=50.0, longitude=30.0, author=cls.user, status='approved')
        cls.near = CulturalObject.objects.create(
            title='Near', latitude=50.0004, longitude=30.0004, author=cls.user, status='approved')
        cls.far = CulturalObject.objects.create(
            title='Far', latitude=51.0, longitude=31.0, author=cls.user, status='approved')
        cls.pending = CulturalObject.objects.create(
            title='Pending', latitude=50.0001, longitude=30.0001, author=cls.user, status='pending')

    def test_returns_approved_within_radius_sorted(self):
        results = find_nearby_objects(50.0, 30.0, radius_m=100)
        ids = [o.id for o, _ in results]
        self.assertIn(self.center.id, ids)
        self.assertIn(self.near.id, ids)
        self.assertNotIn(self.far.id, ids)
        self.assertNotIn(self.pending.id, ids)
        distances = [d for _, d in results]
        self.assertEqual(distances, sorted(distances))

    def test_exclude_id_skips_object(self):
        results = find_nearby_objects(50.0, 30.0, radius_m=100, exclude_id=self.center.id)
        self.assertNotIn(self.center.id, [o.id for o, _ in results])
