from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from objects.models import CulturalObject, Tag


class PermissionTest(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('user1', 'u1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        self.admin = User.objects.create_user('admin', 'admin@test.com', 'pass', is_staff=True)

        self.tag = Tag.objects.create(name="Замок", slug="zamok")

        self.obj = CulturalObject.objects.create(
            title="Об'єкт користувача 1",
            latitude=50.0,
            longitude=30.0,
            author=self.user1,
            status='approved'
        )

        self.obj.tags.add(self.tag)

    def test_author_can_edit_own_project(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(f'/api/objects/{self.obj.id}/', {
            'title': 'Оновлена назва'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.title, 'Оновлена назва')

    def test_non_author_cannot_edit_object(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(f'/api/objects/{self.obj.id}/', {
            'title': 'Спроба змінити'
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.title, "Об'єкт користувача 1")

    def test_admin_can_edit_any_object(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/objects/{self.obj.id}/', {
            'title': 'Змінено адміном'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.title, 'Змінено адміном')

    def test_author_can_delete_own_object(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f'/api/objects/{self.obj.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_author_cannot_delete_object(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(f'/api/objects/{self.obj.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anyone_can_view_approved_object(self):
        response = self.client.get(f'/api/objects/{self.obj.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f'/api/objects/{self.obj.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
