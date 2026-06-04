"""Coverage: views.py — Visit/PlannedVisit error branches (404s, foreign access,
date validation) and planned-visit editing/conversion."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject, PlannedVisit, Visit


class VisitErrorBranchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('alice', 'a@t.com', 'p')
        cls.other = User.objects.create_user('bob', 'b@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Obj', latitude=50.0, longitude=30.0,
            author=cls.other, status='approved',
        )
        cls.visit = Visit.objects.create(user=cls.user, cultural_object=cls.obj)

    def test_toggle_visit_object_not_found(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post('/api/objects/999999/visit/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_visit_not_found(self):
        self.client.force_authenticate(self.user)
        resp = self.client.patch('/api/visits/999999/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_foreign_visit_forbidden(self):
        self.client.force_authenticate(self.other)
        resp = self.client.patch(f'/api/visits/{self.visit.pk}/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_visit_invalid_date(self):
        self.client.force_authenticate(self.user)
        resp = self.client.patch(
            f'/api/visits/{self.visit.pk}/', {'visited_at': 'not-a-date'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_visit_naive_date_accepted(self):
        self.client.force_authenticate(self.user)
        resp = self.client.patch(
            f'/api/visits/{self.visit.pk}/',
            {'visited_at': '2025-01-15', 'impression': 'nice', 'is_public': True},
            format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.visit.refresh_from_db()
        self.assertTrue(self.visit.is_public)
        self.assertEqual(self.visit.impression, 'nice')

    def test_public_visits_unknown_user(self):
        self.assertEqual(
            self.client.get('/api/users/nosuchuser/visits/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get('/api/users/nosuchuser/visits/map/').status_code,
            status.HTTP_404_NOT_FOUND,
        )


class PlannedVisitBranchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('alice', 'a@t.com', 'p')
        cls.other = User.objects.create_user('bob', 'b@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Obj', latitude=50.0, longitude=30.0,
            author=cls.other, status='approved',
        )

    def _plan(self):
        return PlannedVisit.objects.create(
            user=self.user, cultural_object=self.obj, note='hope to go')

    def test_toggle_planned_object_not_found(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post('/api/objects/999999/plan-visit/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_planned_branches(self):
        self.client.force_authenticate(self.user)
        # 404
        resp = self.client.patch('/api/planned-visits/999999/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        plan = self._plan()
        # foreign → 403
        self.client.force_authenticate(self.other)
        resp = self.client.patch(f'/api/planned-visits/{plan.pk}/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        # own: allowed fields updated, unknown fields ignored
        self.client.force_authenticate(self.user)
        resp = self.client.patch(
            f'/api/planned-visits/{plan.pk}/',
            {'note': 'updated', 'planned_date': '2026-08-01', 'user': self.other.pk},
            format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        plan.refresh_from_db()
        self.assertEqual(plan.note, 'updated')
        self.assertEqual(str(plan.planned_date), '2026-08-01')
        self.assertEqual(plan.user, self.user)

    def test_convert_branches(self):
        self.client.force_authenticate(self.user)
        # 404
        resp = self.client.post('/api/planned-visits/999999/convert-to-visit/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        plan = self._plan()
        # foreign → 403
        self.client.force_authenticate(self.other)
        resp = self.client.post(f'/api/planned-visits/{plan.pk}/convert-to-visit/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        # own → visit created with plan note as impression, plan removed
        self.client.force_authenticate(self.user)
        resp = self.client.post(f'/api/planned-visits/{plan.pk}/convert-to-visit/')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['created'])
        self.assertFalse(PlannedVisit.objects.filter(pk=plan.pk).exists())
        self.assertEqual(Visit.objects.get(user=self.user).impression, 'hope to go')

    def test_convert_when_visit_already_exists(self):
        plan = self._plan()
        Visit.objects.create(user=self.user, cultural_object=self.obj)
        self.client.force_authenticate(self.user)
        resp = self.client.post(f'/api/planned-visits/{plan.pk}/convert-to-visit/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['created'])
        self.assertFalse(PlannedVisit.objects.filter(pk=plan.pk).exists())
