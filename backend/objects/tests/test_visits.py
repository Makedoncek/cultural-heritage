"""Targeted tests for Visit and PlannedVisit API."""
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject, PlannedVisit, Tag, Visit


class VisitFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('alice', 'a@t.com', 'p')
        cls.other = User.objects.create_user('bob', 'b@t.com', 'p')
        cls.tag = Tag.objects.create(name='Castle', slug='castle', icon='C')
        cls.obj = CulturalObject.objects.create(
            title='Test Castle',
            latitude=50.0, longitude=30.0,
            author=cls.other,
            status='approved',
        )
        cls.obj.tags.add(cls.tag)

    def _toggle_url(self):
        return reverse('objects:toggle_visit', kwargs={'object_pk': self.obj.pk})

    def test_user_can_toggle_visit(self):
        """Toggle creates on first call, deletes on second."""
        self.client.force_authenticate(self.user)
        r1 = self.client.post(self._toggle_url())
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertTrue(r1.data['is_visited'])
        self.assertEqual(Visit.objects.count(), 1)

        r2 = self.client.post(self._toggle_url())
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertFalse(r2.data['is_visited'])
        self.assertEqual(Visit.objects.count(), 0)

    def test_visit_unique_constraint(self):
        Visit.objects.create(user=self.user, cultural_object=self.obj)
        with self.assertRaises(Exception):
            Visit.objects.create(user=self.user, cultural_object=self.obj)

    def test_user_can_edit_impression_and_privacy(self):
        visit = Visit.objects.create(user=self.user, cultural_object=self.obj)
        self.client.force_authenticate(self.user)
        url = reverse('objects:update_visit', kwargs={'visit_pk': visit.pk})
        response = self.client.patch(url, {
            'impression': 'Чудовий вид з башти',
            'is_public': True,
            'visited_at': '2026-04-15T14:30:00+00:00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visit.refresh_from_db()
        self.assertEqual(visit.impression, 'Чудовий вид з башти')
        self.assertTrue(visit.is_public)
        self.assertEqual(visit.visited_at.date().isoformat(), '2026-04-15')

    def test_future_visited_at_rejected(self):
        from datetime import date, timedelta
        visit = Visit.objects.create(user=self.user, cultural_object=self.obj)
        self.client.force_authenticate(self.user)
        url = reverse('objects:update_visit', kwargs={'visit_pk': visit.pk})
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = self.client.patch(url, {'visited_at': tomorrow}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('visited_at', response.data)

    def test_user_cannot_edit_others_visit(self):
        visit = Visit.objects.create(user=self.user, cultural_object=self.obj)
        self.client.force_authenticate(self.other)
        url = reverse('objects:update_visit', kwargs={'visit_pk': visit.pk})
        response = self.client.patch(url, {'impression': 'hack'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_visits_show_only_is_public_true(self):
        Visit.objects.create(user=self.user, cultural_object=self.obj, is_public=True)
        obj2 = CulturalObject.objects.create(
            title='Other', latitude=51.0, longitude=31.0,
            author=self.other, status='approved',
        )
        Visit.objects.create(user=self.user, cultural_object=obj2, is_public=False)

        url = reverse('objects:public_visits', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['object_title'], 'Test Castle')

    def test_visits_count_public_aggregate(self):
        Visit.objects.create(user=self.user, cultural_object=self.obj)
        Visit.objects.create(user=self.other, cultural_object=self.obj)
        url = reverse('objects:visits_count', kwargs={'object_pk': self.obj.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['visits_count'], 2)

    def test_my_visits_list_requires_auth(self):
        response = self.client.get(reverse('objects:my_visits'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_planned_visit_toggle(self):
        self.client.force_authenticate(self.user)
        url = reverse('objects:toggle_planned_visit', kwargs={'object_pk': self.obj.pk})
        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertTrue(r1.data['is_planned'])
        self.assertEqual(PlannedVisit.objects.count(), 1)

        r2 = self.client.post(url)
        self.assertFalse(r2.data['is_planned'])
        self.assertEqual(PlannedVisit.objects.count(), 0)

    def test_convert_planned_to_visit_removes_plan_creates_visit(self):
        planned = PlannedVisit.objects.create(
            user=self.user, cultural_object=self.obj,
            note='планую на літо',
        )
        self.client.force_authenticate(self.user)
        url = reverse('objects:convert_planned_to_visit', kwargs={'planned_pk': planned.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(PlannedVisit.objects.filter(pk=planned.pk).exists())
        self.assertTrue(Visit.objects.filter(user=self.user, cultural_object=self.obj).exists())
        visit = Visit.objects.get(user=self.user, cultural_object=self.obj)
        self.assertEqual(visit.impression, 'планую на літо')  # carried over from plan note

    def test_visits_stats_aggregates_correctly(self):
        Visit.objects.create(user=self.user, cultural_object=self.obj)
        obj2 = CulturalObject.objects.create(
            title='Castle 2', latitude=51.0, longitude=31.0,
            author=self.other, status='approved',
        )
        obj2.tags.add(self.tag)
        Visit.objects.create(user=self.user, cultural_object=obj2)

        self.client.force_authenticate(self.user)
        response = self.client.get(reverse('objects:my_visits_stats'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_visits'], 2)
        self.assertEqual(len(response.data['by_tag']), 1)
        self.assertEqual(response.data['by_tag'][0]['visited_count'], 2)
        self.assertEqual(response.data['by_tag'][0]['name'], 'Castle')
