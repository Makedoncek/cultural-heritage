from rest_framework.test import APITestCase
from objects.models import Tag
from rest_framework import status


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
