"""Coverage: views.py — breadth smoke tests over read-mostly endpoints
(health, popular, profile aggregates, "me/*" lists, public visits, toggles)."""
from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth.models import User

from objects.models import CulturalObject, Route, Tag


class ViewEndpointSmokeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('viewuser', 'vu@t.com', 'p')
        cls.tag = Tag.objects.create(name='T', slug='t', icon='T')
        cls.obj = CulturalObject.objects.create(
            title='Obj', latitude=50.0, longitude=30.0, author=cls.user, status='approved')
        cls.route = Route.objects.create(
            title='R', description='x', author=cls.user, status='approved', visibility='public')

    def test_public_endpoints(self):
        for url in [
            '/api/health/',
            '/api/objects/popular/',
            f'/api/users/{self.user.username}/visits/',
            f'/api/users/{self.user.username}/visits/map/',
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_authenticated_me_endpoints(self):
        self.client.force_authenticate(self.user)
        for url in [
            '/api/me/preference/',
            '/api/users/me/reports/',
            '/api/users/me/objects/reports/',
            '/api/users/me/translations/',
            '/api/users/me/visits/',
            '/api/users/me/visits/stats/',
            '/api/users/me/planned-visits/',
            '/api/users/me/routes/',
            '/api/users/me/completed-routes/',
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_visit_and_plan_toggles(self):
        self.client.force_authenticate(self.user)
        r_visit = self.client.post(f'/api/objects/{self.obj.id}/visit/')
        self.assertIn(r_visit.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        r_plan = self.client.post(f'/api/objects/{self.obj.id}/plan-visit/')
        self.assertIn(r_plan.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertEqual(
            self.client.get(f'/api/objects/{self.obj.id}/visits-count/').status_code,
            status.HTTP_200_OK,
        )
