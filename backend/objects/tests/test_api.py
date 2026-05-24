from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase
from objects.models import Tag, CulturalObject, Favorite
from rest_framework import status
from django.contrib.auth.models import User


class TagAPITest(APITestCase):
    def setUp(self):
        Tag.objects.create(name="Замок", slug="zamok", icon="🏰")
        Tag.objects.create(name="Церква", slug="tserkva", icon="⛪")

    def test_list_tags_without_auth(self):
        response = self.client.get('/api/tags/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['name'], "Замок")

    def test_retrieve_single_tag(self):
        tag = Tag.objects.get(slug="zamok")
        response = self.client.get(f'/api/tags/{tag.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Замок")

    def test_cannot_create_tag_via_api(self):
        response = self.client.post('/api/tags/', {
            'name': 'Новий тег',
            'slug': 'novyy-teg'
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ObjectVisibilityTest(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('user1', 'u1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        self.admin = User.objects.create_user('admin', 'a@test.com', 'pass', is_staff=True)

        self.tag = Tag.objects.create(name="Замок", slug="zamok")

        self.approved = CulturalObject.objects.create(
            title="Approved object",
            latitude=50.0,
            longitude=30.0,
            author=self.user1,
            status='approved'
        )
        self.approved.tags.add(self.tag)

        self.pending = CulturalObject.objects.create(
            title="Pending object",
            latitude=50.0,
            longitude=30.0,
            author=self.user1,
            status='pending'
        )
        self.pending.tags.add(self.tag)

        self.archived = CulturalObject.objects.create(
            title="Archived object",
            latitude=50.0,
            longitude=30.0,
            author=self.user1,
            status='archived'
        )
        self.archived.tags.add(self.tag)

    def test_guest_sees_only_approved(self):
        response = self.client.get('/api/objects/')
        titles = [obj['title'] for obj in response.data.get('results', response.data)]

        self.assertIn('Approved object', titles)
        self.assertNotIn('Pending object', titles)
        self.assertNotIn('Archived object', titles)

    def test_user_sees_approved_and_own_pending(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/objects/')
        titles = [obj['title'] for obj in response.data.get('results', response.data)]

        self.assertIn('Approved object', titles)
        self.assertIn('Pending object', titles)
        self.assertNotIn('Archived object', titles)

    def test_user_does_not_see_others_pending(self):
        other_pending = CulturalObject.objects.create(
            title="Other user pending",
            latitude=50.0,
            longitude=30.0,
            author=self.user2,
            status='pending'
        )
        other_pending.tags.add(self.tag)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/objects/')
        titles = [obj['title'] for obj in response.data.get('results', response.data)]
        self.assertNotIn('Other user pending', titles)

    def test_admin_sees_all_except_archived(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/objects/')
        titles = [obj['title'] for obj in response.data.get('results', response.data)]

        self.assertIn('Approved object', titles)
        self.assertIn('Pending object', titles)
        self.assertNotIn('Archived object', titles)

    def test_nobody_sees_archived(self):
        response = self.client.get('/api/objects/')
        titles = [obj['title'] for obj in response.data.get('results', response.data)]
        self.assertNotIn('Archived object', titles)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/objects/')
        titles = [obj['title'] for obj in response.data.get('results', response.data)]
        self.assertNotIn('Archived object', titles)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/objects/')
        titles = [obj['title'] for obj in response.data.get('results', response.data)]
        self.assertNotIn('Archived object', titles)


class ObjectCRUDTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.tag = Tag.objects.create(name="Замок", slug="zamok")
        self.client.force_authenticate(user=self.user)

    def test_create_object_sets_author_and_pending_status(self):
        response = self.client.post('/api/objects/', {
            'title': 'Новий замок',
            'description': 'Опис',
            'latitude': 50.0,
            'longitude': 30.0,
            'tags': [self.tag.id]
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        obj = CulturalObject.objects.get(title='Новий замок')
        self.assertEqual(obj.author, self.user)
        self.assertEqual(obj.status, 'pending')

    def test_create_without_auth_fails(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/objects/', {
            'title': 'Новий замок',
            'description': 'Опис',
            'latitude': 50.0,
            'longitude': 30.0,
            'tags': [self.tag.id]
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_edit_approved_object_returns_to_pending(self):
        obj = CulturalObject.objects.create(
            title="Original",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='approved'
        )
        obj.tags.add(self.tag)
        response = self.client.patch(f'/api/objects/{obj.id}/', {
            'title': 'Updated Title'
        })
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'pending')

    def test_admin_edit_does_not_change_status(self):
        admin = User.objects.create_user('admin', 'a@test.com', 'pass', is_staff=True)
        obj = CulturalObject.objects.create(
            title="Original",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='approved'
        )
        obj.tags.add(self.tag)
        self.client.force_authenticate(user=admin)
        response = self.client.patch(f'/api/objects/{obj.id}/', {
            'title': 'Updated Title'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'approved')

    def test_delete_archives_object(self):
        obj = CulturalObject.objects.create(
            title="To Archive",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='approved'
        )
        obj.tags.add(self.tag)
        response = self.client.delete(f'/api/objects/{obj.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Об\'єкт архівовано')
        self.assertTrue(CulturalObject.objects.filter(id=obj.id).exists())
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'archived')
        self.assertIsNotNone(obj.archived_at)

    def test_archived_object_not_in_list(self):
        obj = CulturalObject.objects.create(
            title="To Archive",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='approved'
        )
        obj.tags.add(self.tag)

        response = self.client.get('/api/objects/')
        titles = [o['title'] for o in response.data.get('results', response.data)]
        self.assertIn('To Archive', titles)

        self.client.delete(f'/api/objects/{obj.id}/')

        response = self.client.get('/api/objects/')
        titles = [o['title'] for o in response.data.get('results', response.data)]
        self.assertNotIn('To Archive', titles)

    def test_my_objects_returns_only_own_objects(self):
        user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        obj1 = CulturalObject.objects.create(
            title="My Object 1",
            latitude=50.0,
            longitude=30.0,
            author=self.user
        )
        obj1.tags.add(self.tag)
        obj2 = CulturalObject.objects.create(
            title="Other User Object",
            latitude=50.0,
            longitude=30.0,
            author=user2
        )
        obj2.tags.add(self.tag)
        response = self.client.get('/api/objects/my/')
        titles = [o['title'] for o in response.data.get('results', response.data)]

        self.assertIn('My Object 1', titles)
        self.assertNotIn('Other User Object', titles)

    def test_my_objects_includes_archived(self):
        """Author should see own archived objects in /my/ so they can restore or hard-delete them."""
        obj1 = CulturalObject.objects.create(
            title="Active",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='approved'
        )
        obj1.tags.add(self.tag)

        obj2 = CulturalObject.objects.create(
            title="Archived",
            latitude=50.0,
            longitude=30.0,
            author=self.user,
            status='archived'
        )
        obj2.tags.add(self.tag)

        response = self.client.get('/api/objects/my/')

        titles = [o['title'] for o in response.data.get('results', response.data)]

        self.assertIn('Active', titles)
        self.assertIn('Archived', titles)

    def test_my_objects_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/objects/my/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class EventObjectTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.tag = Tag.objects.create(name='Замок', slug='zamok')
        self.client.force_authenticate(user=self.user)
        self.base_data = {
            'title': 'Фестиваль',
            'latitude': 50.45,
            'longitude': 30.52,
            'tags': [self.tag.id],
        }

    def test_create_event_object(self):
        data = {
            **self.base_data,
            'object_type': 'event',
            'event_start_date': str(timezone.now() + timedelta(days=5)),
            'event_end_date': str(timezone.now() + timedelta(days=10)),
        }
        response = self.client.post('/api/objects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['object_type'], 'event')

    def test_create_event_missing_dates(self):
        data = {**self.base_data, 'object_type': 'event'}
        response = self.client.post('/api/objects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_event_end_before_start(self):
        data = {
            **self.base_data,
            'object_type': 'event',
            'event_start_date': str(timezone.now() + timedelta(days=10)),
            'event_end_date': str(timezone.now() + timedelta(days=5)),
        }
        response = self.client.post('/api/objects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_event_start_in_past_allowed(self):
        """Events that started in the past but haven't ended are valid (ongoing events)."""
        data = {
            **self.base_data,
            'object_type': 'event',
            'event_start_date': str(timezone.now() - timedelta(days=5)),
            'event_end_date': str(timezone.now() + timedelta(days=5)),
        }
        response = self.client.post('/api/objects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_event_already_ended(self):
        """Events that have already ended cannot be created."""
        data = {
            **self.base_data,
            'object_type': 'event',
            'event_start_date': str(timezone.now() - timedelta(days=10)),
            'event_end_date': str(timezone.now() - timedelta(days=2)),
        }
        response = self.client.post('/api/objects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_object_type(self):
        CulturalObject.objects.create(
            title='Permanent', latitude=50.0, longitude=30.0,
            author=self.user, status='approved', object_type='permanent',
        )
        event = CulturalObject.objects.create(
            title='Event', latitude=50.0, longitude=30.0,
            author=self.user, status='approved', object_type='event',
            event_start_date=timezone.now(), event_end_date=timezone.now() + timedelta(days=5),
        )
        event.tags.add(self.tag)

        response = self.client.get('/api/objects/?object_type=event')
        titles = [obj['title'] for obj in response.data['results']]
        self.assertIn('Event', titles)
        self.assertNotIn('Permanent', titles)

    def test_permanent_object_no_dates(self):
        data = {**self.base_data, 'object_type': 'permanent'}
        response = self.client.post('/api/objects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['event_start_date'])
        self.assertIsNone(response.data['event_end_date'])


class FavoriteTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        self.tag = Tag.objects.create(name='Замок', slug='zamok')
        self.obj = CulturalObject.objects.create(
            title='Test', latitude=50.0, longitude=30.0,
            author=self.user, status='approved',
        )
        self.obj.tags.add(self.tag)

    def test_toggle_favorite_on(self):
        # user2 favorites user's object (self-favorite is forbidden).
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f'/api/objects/{self.obj.id}/favorite/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_favorited'])
        self.assertEqual(response.data['favorites_count'], 1)

    def test_toggle_favorite_off(self):
        Favorite.objects.create(user=self.user2, cultural_object=self.obj)
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f'/api/objects/{self.obj.id}/favorite/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_favorited'])
        self.assertEqual(response.data['favorites_count'], 0)

    def test_favorites_list(self):
        Favorite.objects.create(user=self.user, cultural_object=self.obj)
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/objects/favorites/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test')

    def test_favorites_list_only_own(self):
        Favorite.objects.create(user=self.user2, cultural_object=self.obj)
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/objects/favorites/')
        self.assertEqual(len(response.data['results']), 0)

    def test_favorite_requires_auth(self):
        response = self.client.post(f'/api/objects/{self.obj.id}/favorite/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_is_favorited_on_detail(self):
        Favorite.objects.create(user=self.user, cultural_object=self.obj)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/objects/{self.obj.id}/')
        self.assertTrue(response.data['is_favorited'])
        self.assertEqual(response.data['favorites_count'], 1)
