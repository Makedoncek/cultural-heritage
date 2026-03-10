from django.test import TestCase
from objects.serializers import ObjectWriteSerializer
from objects.models import Tag


class ObjectWriteSerializerTest(TestCase):
    def setUp(self):
        self.tag1 = Tag.objects.create(name="Замок", slug="zamok")
        self.tag2 = Tag.objects.create(name="Церква", slug="tserkva")
        self.tag3 = Tag.objects.create(name="Музей", slug="muzey")

    def test_valid_object_passes_validation(self):
        data = {
            'title': 'Тестовий замок',
            'description': "Опис",
            'latitude': 50.0,
            'longitude': 30.0,
            'tags': [self.tag1.id, self.tag2.id]
        }

        serializer = ObjectWriteSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_latitude_too_low_rejected(self):
        data = {
            'title': 'Test',
            'latitude': 43.0,
            'longitude': 30.0,
            'tags': [self.tag1.id]
        }

        serializer = ObjectWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('coordinates', serializer.errors)

    def test_latitude_too_high_rejected(self):
        data = {
            'title': 'Test',
            'latitude': 53.0,
            'longitude': 30.0,
            'tags': [self.tag1.id]
        }

        serializer = ObjectWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('coordinates', serializer.errors)

    def test_longitude_too_low_rejected(self):
        data = {
            'title': 'Test',
            'latitude': 50.0,
            'longitude': 21.0,
            'tags': [self.tag1.id]
        }

        serializer = ObjectWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('coordinates', serializer.errors)

    def test_longitude_too_high_rejected(self):
        data = {
            'title': 'Test',
            'latitude': 50.0,
            'longitude': 42.0,
            'tags': [self.tag1.id]
        }
        serializer = ObjectWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('coordinates', serializer.errors)

    def test_coordinates_in_neighboring_country_rejected(self):
        data = {
            'title': 'Test',
            'latitude': 45.0,
            'longitude': 23.0,
            'tags': [self.tag1.id]
        }
        serializer = ObjectWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('coordinates', serializer.errors)

    def test_less_than_one_tag_rejected(self):
        data = {
            'title': 'Test',
            'latitude': 50.0,
            'longitude': 30.0,
            'tags': []
        }

        serializer = ObjectWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('tags', serializer.errors)

    def test_more_than_five_tags_rejected(self):
        tag4 = Tag.objects.create(name="Tag4", slug="tag4")
        tag5 = Tag.objects.create(name="Tag5", slug="tag5")
        tag6 = Tag.objects.create(name="Tag6", slug="tag6")

        data = {
            'title': 'Test',
            'latitude': 50.0,
            'longitude': 30.0,
            'tags': [
                self.tag1.id, self.tag2.id, self.tag3.id,
                tag4.id, tag5.id, tag6.id  # 6 тегів
            ]
        }

        serializer = ObjectWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('tags', serializer.errors)

    def test_valid_coordinates_passes(self):
        test_cases = [
            {'latitude': 50.4501, 'longitude': 30.5234},  # Kyiv
            {'latitude': 49.8397, 'longitude': 24.0297},  # Lviv
            {'latitude': 46.4825, 'longitude': 30.7233},  # Odesa
            {'latitude': 49.9935, 'longitude': 36.2304},  # Kharkiv
        ]

        for coordinates in test_cases:
            data = {
                'title': 'Test',
                'latitude': coordinates['latitude'],
                'longitude': coordinates['longitude'],
                'tags': [self.tag1.id]
            }

            serializer = ObjectWriteSerializer(data=data)
            self.assertTrue(serializer.is_valid())
