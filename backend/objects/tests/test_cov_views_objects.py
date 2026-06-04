"""Coverage: views.py — ObjectViewSet actions (restore, hard-delete, duplicates,
with-my-photos/audios, favorite guard), UserProfileViewSet, user preference,
auth edge branches."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from objects.email import make_email_verification_token
from objects.models import (
    CulturalObject, FavoriteAuthor, ObjectAudio, ObjectPhoto, Tag,
)


class AuthEdgeBranchTests(APITestCase):
    def test_verify_email_user_deleted_after_token_issued(self):
        user = User.objects.create_user('ghost', 'g@t.com', 'p', is_active=False)
        token = make_email_verification_token(user)
        user.delete()
        resp = self.client.get('/api/auth/verify-email/', {'token': token})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_missing_fields(self):
        resp = self.client.post('/api/auth/password-reset/confirm/', {
            'uid': 'x', 'token': 'y',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ReportBranchTests(APITestCase):
    def test_delete_own_report_not_found(self):
        user = User.objects.create_user('reporter', 'r@t.com', 'p')
        self.client.force_authenticate(user)
        resp = self.client.delete('/api/reports/999999/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class TagTypeFilterTests(APITestCase):
    def test_tag_type_query_param_filters(self):
        Tag.objects.create(name='Castle', slug='castle', icon='C', tag_type='object')
        Tag.objects.create(name='Festival', slug='festival', icon='F', tag_type='event')
        resp = self.client.get('/api/tags/', {'tag_type': 'event'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [t['name'] for t in resp.data['results']]
        self.assertEqual(names, ['Festival'])


class ObjectActionsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author', 'a@t.com', 'p')
        cls.other = User.objects.create_user('other', 'o@t.com', 'p')
        cls.admin = User.objects.create_user('admin', 'ad@t.com', 'p', is_staff=True)
        cls.tag = Tag.objects.create(name='T', slug='t', icon='T')

    def _make_object(self, **kwargs):
        defaults = dict(title='Obj', latitude=50.0, longitude=30.0,
                        author=self.author, status='approved')
        defaults.update(kwargs)
        return CulturalObject.objects.create(**defaults)

    def test_staff_retrieve_sees_archived(self):
        obj = self._make_object(status='archived')
        self.client.force_authenticate(self.admin)
        resp = self.client.get(f'/api/objects/{obj.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_restore_branches(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.post('/api/objects/999999/restore/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        obj = self._make_object(status='archived')
        self.assertEqual(
            self.client.post(f'/api/objects/{obj.pk}/restore/').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        active = self._make_object(status='approved')
        self.assertEqual(
            self.client.post(f'/api/objects/{active.pk}/restore/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        resp = self.client.post(f'/api/objects/{obj.pk}/restore/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'pending')

    def test_hard_delete_branches(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.delete('/api/objects/999999/hard-delete/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        obj = self._make_object()
        self.assertEqual(
            self.client.delete(f'/api/objects/{obj.pk}/hard-delete/').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.author)
        resp = self.client.delete(f'/api/objects/{obj.pk}/hard-delete/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CulturalObject.objects.filter(pk=obj.pk).exists())

    def test_check_duplicates_branches(self):
        obj = self._make_object(title='Nearby', latitude=50.4500, longitude=30.5200)
        # Missing coordinates → 400
        resp = self.client.post('/api/objects/check-duplicates/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Within 100 m → returned
        resp = self.client.post('/api/objects/check-duplicates/', {
            'latitude': 50.4501, 'longitude': 30.5201,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([n['id'] for n in resp.data['nearby']], [obj.pk])
        # exclude_id removes it; invalid exclude_id is ignored
        resp = self.client.post('/api/objects/check-duplicates/', {
            'latitude': 50.4501, 'longitude': 30.5201, 'exclude_id': obj.pk,
        }, format='json')
        self.assertEqual(resp.data['nearby'], [])
        resp = self.client.post('/api/objects/check-duplicates/', {
            'latitude': 50.4501, 'longitude': 30.5201, 'exclude_id': 'abc',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_submit_translation_object_not_found(self):
        self.client.force_authenticate(self.other)
        resp = self.client.post('/api/objects/999999/translations/', {
            'language': 'en', 'title': 'X',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_favorite_own_object_rejected(self):
        obj = self._make_object()
        self.client.force_authenticate(self.author)
        resp = self.client.post(f'/api/objects/{obj.pk}/favorite/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_same_content_keeps_approved_status(self):
        obj = self._make_object(title='Same')
        obj.tags.add(self.tag)
        self.client.force_authenticate(self.author)
        resp = self.client.patch(f'/api/objects/{obj.pk}/', {'title': 'Same'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'approved')

    def test_patch_changed_tags_resets_to_pending(self):
        obj = self._make_object()
        obj.tags.add(self.tag)
        new_tag = Tag.objects.create(name='T2', slug='t2', icon='2')
        self.client.force_authenticate(self.author)
        resp = self.client.patch(
            f'/api/objects/{obj.pk}/', {'tags': [new_tag.pk]}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'pending')


class WithMyMediaTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author', 'a@t.com', 'p')
        cls.uploader = User.objects.create_user('uploader', 'u@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Obj', latitude=50.0, longitude=30.0,
            author=cls.author, status='approved')
        cls.photo = ObjectPhoto.objects.create(
            cultural_object=cls.obj, uploaded_by=cls.uploader,
            cloudinary_public_id='p1', image_url='http://x/i.jpg',
            thumbnail_url='http://x/t.jpg', status='pending')
        cls.audio = ObjectAudio.objects.create(
            cultural_object=cls.obj, uploaded_by=cls.uploader,
            cloudinary_public_id='a1', cloudinary_url='http://x/a.mp3',
            duration_seconds=10, title='Audio', copyright_confirmed=True)

    def test_with_my_photos(self):
        self.client.force_authenticate(self.uploader)
        resp = self.client.get('/api/objects/with-my-photos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)
        # Status filter: valid value filters, invalid value is ignored
        resp = self.client.get('/api/objects/with-my-photos/', {'status': 'approved'})
        self.assertEqual(resp.data['count'], 0)
        resp = self.client.get('/api/objects/with-my-photos/', {'status': 'bogus'})
        self.assertEqual(resp.data['count'], 1)

    def test_with_my_audios(self):
        self.client.force_authenticate(self.uploader)
        resp = self.client.get('/api/objects/with-my-audios/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)
        item = resp.data['results'][0]
        self.assertEqual(item['id'], self.obj.pk)
        self.assertEqual(len(item['my_audios']), 1)
        resp = self.client.get('/api/objects/with-my-audios/', {'status': 'approved'})
        self.assertEqual(resp.data['count'], 0)
        # Matching status filter reaches the per-object audio filtering branch.
        resp = self.client.get('/api/objects/with-my-audios/', {'status': 'pending'})
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(len(resp.data['results'][0]['my_audios']), 1)


class UserProfileViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('profauthor', 'pa@t.com', 'p')
        cls.viewer = User.objects.create_user('viewer', 'v@t.com', 'p')
        cls.approved = CulturalObject.objects.create(
            title='Approved', latitude=50.0, longitude=30.0,
            author=cls.author, status='approved')
        cls.pending = CulturalObject.objects.create(
            title='Pending', latitude=50.1, longitude=30.1,
            author=cls.author, status='pending')

    def test_retrieve_profile_variants(self):
        # me unauthenticated → 401
        self.assertEqual(
            self.client.get('/api/users/me/').status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        # unknown username → 404
        self.assertEqual(
            self.client.get('/api/users/nosuchuser/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        # public profile with aggregates
        resp = self.client.get(f'/api/users/{self.author.username}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['approved_objects_count'], 1)
        # me authenticated resolves to own profile + is_followed annotation path
        self.client.force_authenticate(self.viewer)
        resp = self.client.get('/api/users/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'viewer')

    def test_author_objects_visibility(self):
        url = f'/api/users/{self.author.username}/objects/'
        # 404 for unknown author
        self.assertEqual(
            self.client.get('/api/users/nosuchuser/objects/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        # guest sees approved only
        resp = self.client.get(url)
        self.assertEqual(len(resp.data), 1)
        # other authenticated user sees approved only (+ is_favorited annotation)
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(url)
        self.assertEqual(len(resp.data), 1)
        # own profile shows pending too
        self.client.force_authenticate(self.author)
        resp = self.client.get(url)
        self.assertEqual(len(resp.data), 2)

    def test_follow_branches(self):
        self.client.force_authenticate(self.viewer)
        # 404
        self.assertEqual(
            self.client.post('/api/users/nosuchuser/follow/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        # self-follow rejected
        self.assertEqual(
            self.client.post(f'/api/users/{self.viewer.username}/follow/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        # toggle on
        resp = self.client.post(f'/api/users/{self.author.username}/follow/')
        self.assertTrue(resp.data['is_followed'])
        self.assertEqual(resp.data['followers_count'], 1)
        # favorite authors list while followed
        resp = self.client.get('/api/users/favorite-authors/')
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['username'], 'profauthor')
        # toggle off
        resp = self.client.post(f'/api/users/{self.author.username}/follow/')
        self.assertFalse(resp.data['is_followed'])
        self.assertEqual(FavoriteAuthor.objects.count(), 0)


class UserPreferenceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('prefuser', 'pr@t.com', 'p')

    def test_patch_branches(self):
        self.client.force_authenticate(self.user)
        # invalid language
        resp = self.client.patch('/api/me/preference/', {'language': 'xx'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # invalid theme
        resp = self.client.patch('/api/me/preference/', {'theme': 'neon'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # valid update of both fields
        resp = self.client.patch(
            '/api/me/preference/', {'language': 'en', 'theme': 'dark'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {'language': 'en', 'theme': 'dark'})
        # GET returns persisted values
        resp = self.client.get('/api/me/preference/')
        self.assertEqual(resp.data['theme'], 'dark')