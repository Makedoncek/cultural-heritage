from rest_framework.test import APITestCase
from rest_framework import status
from django.test import TestCase
from django.contrib.auth.models import User
from objects.models import Tag, CulturalObject
from objects.serializers import ObjectWriteSerializer


class BoundaryCoordinateTest(TestCase):
    """Test exact Ukraine boundary values pass validation."""

    def setUp(self):
        self.tag = Tag.objects.create(name="Test", slug="test")

    def _make_data(self, lat, lng):
        return {
            'title': 'Boundary Test',
            'latitude': lat,
            'longitude': lng,
            'tags': [self.tag.id],
        }

    def test_exact_min_latitude_accepted(self):
        s = ObjectWriteSerializer(data=self._make_data(44.0, 30.0))
        self.assertTrue(s.is_valid(), s.errors)

    def test_exact_max_latitude_accepted(self):
        s = ObjectWriteSerializer(data=self._make_data(52.5, 30.0))
        self.assertTrue(s.is_valid(), s.errors)

    def test_exact_min_longitude_accepted(self):
        s = ObjectWriteSerializer(data=self._make_data(50.0, 22.0))
        self.assertTrue(s.is_valid(), s.errors)

    def test_exact_max_longitude_accepted(self):
        s = ObjectWriteSerializer(data=self._make_data(50.0, 40.5))
        self.assertTrue(s.is_valid(), s.errors)


class SearchFilterTest(APITestCase):
    """Test SearchFilter and DjangoFilterBackend on ObjectViewSet."""

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.tag1 = Tag.objects.create(name="Замок", slug="zamok")
        self.tag2 = Tag.objects.create(name="Церква", slug="tserkva")

        self.obj1 = CulturalObject.objects.create(
            title="Підгорецький замок",
            description="Ренесансний палац",
            latitude=49.9,
            longitude=24.9,
            author=self.user,
            status='approved',
        )
        self.obj1.tags.add(self.tag1)

        self.obj2 = CulturalObject.objects.create(
            title="Софійський собор",
            description="Головний храм Київської Русі",
            latitude=50.4,
            longitude=30.5,
            author=self.user,
            status='approved',
        )
        self.obj2.tags.add(self.tag2)

    def _get_titles(self, response):
        return [o['title'] for o in response.data.get('results', response.data)]

    def test_search_by_title(self):
        response = self.client.get('/api/objects/', {'search': 'замок'})
        titles = self._get_titles(response)
        self.assertIn('Підгорецький замок', titles)
        self.assertNotIn('Софійський собор', titles)

    def test_search_by_description(self):
        response = self.client.get('/api/objects/', {'search': 'храм'})
        titles = self._get_titles(response)
        self.assertIn('Софійський собор', titles)
        self.assertNotIn('Підгорецький замок', titles)

    def test_filter_by_tag(self):
        response = self.client.get('/api/objects/', {'tags': self.tag1.id})
        titles = self._get_titles(response)
        self.assertIn('Підгорецький замок', titles)
        self.assertNotIn('Софійський собор', titles)

    def test_filter_by_nonexistent_tag(self):
        response = self.client.get('/api/objects/', {'tags': 9999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results', response.data)), 0)

    def test_search_no_results(self):
        response = self.client.get('/api/objects/', {'search': 'неіснуюче'})
        self.assertEqual(len(response.data.get('results', response.data)), 0)


class VisibilityEdgeCaseTest(APITestCase):
    """Test visibility edge cases for retrieve endpoint."""

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.tag = Tag.objects.create(name="Test", slug="test")

        self.pending = CulturalObject.objects.create(
            title="Pending",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='pending',
        )
        self.pending.tags.add(self.tag)

    def test_guest_cannot_retrieve_pending_object(self):
        response = self.client.get(f'/api/objects/{self.pending.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_author_cannot_retrieve_pending_object(self):
        other = User.objects.create_user('other', 'o@test.com', 'pass')
        self.client.force_authenticate(user=other)
        response = self.client.get(f'/api/objects/{self.pending.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_author_can_retrieve_own_pending_object(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/objects/{self.pending.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CRUDEdgeCaseTest(APITestCase):
    """Test CRUD edge cases."""

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.tag = Tag.objects.create(name="Замок", slug="zamok")
        self.client.force_authenticate(user=self.user)

    def test_edit_pending_object_stays_pending(self):
        obj = CulturalObject.objects.create(
            title="Pending",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='pending',
        )
        obj.tags.add(self.tag)
        response = self.client.patch(f'/api/objects/{obj.id}/', {
            'title': 'Updated Pending'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'pending')

    def test_delete_already_archived_is_idempotent(self):
        obj = CulturalObject.objects.create(
            title="Already Archived",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='approved',
        )
        obj.tags.add(self.tag)

        self.client.delete(f'/api/objects/{obj.id}/')
        obj.refresh_from_db()
        first_archived_at = obj.archived_at

        # Object is now archived and excluded from queryset — returns 404
        response = self.client.delete(f'/api/objects/{obj.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        obj.refresh_from_db()
        self.assertEqual(obj.archived_at, first_archived_at)

    def test_create_object_without_title_fails(self):
        response = self.client.post('/api/objects/', {
            'latitude': 50.0,
            'longitude': 30.0,
            'tags': [self.tag.id],
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_create_object_without_coordinates_fails(self):
        response = self.client.post('/api/objects/', {
            'title': 'No coords',
            'tags': [self.tag.id],
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_my_endpoint_includes_pending_and_approved(self):
        pending = CulturalObject.objects.create(
            title="My Pending",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='pending',
        )
        pending.tags.add(self.tag)

        approved = CulturalObject.objects.create(
            title="My Approved",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='approved',
        )
        approved.tags.add(self.tag)

        response = self.client.get('/api/objects/my/')
        titles = [o['title'] for o in response.data.get('results', response.data)]
        self.assertIn('My Pending', titles)
        self.assertIn('My Approved', titles)
