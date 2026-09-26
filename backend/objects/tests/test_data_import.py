"""Data import commands: load_objects (translations + photos), cloudinary_cleanup, fetch_wiki_objects helpers."""
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from objects.management.commands.fetch_wiki_objects import Command as FetchCommand
from objects.models import CulturalObject, CulturalObjectTranslation, ObjectPhoto, Tag

KYIV = {'latitude': 50.452778, 'longitude': 30.514444}


def _item(title='Софійський собор', **extra):
    return {
        'title': title,
        'description': 'Опис. Джерело: Вікіпедія, ліцензія CC BY-SA 4.0.',
        **KYIV,
        'tags': ['sobor'],
        'wikipedia_url': 'https://uk.wikipedia.org/wiki/X',
        **extra,
    }


class LoadObjectsTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user('importer', password='pass')
        Tag.objects.create(name='Собор', slug='sobor', icon='⛪')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _run(self, items, *args):
        path = Path(self.tmp.name) / 'objects.json'
        path.write_text(json.dumps({'objects': items}, ensure_ascii=False), encoding='utf-8')
        out = StringIO()
        call_command('load_objects', str(path), '--username', 'importer', *args, stdout=out)
        return out.getvalue()

    def test_creates_approved_object_with_translation(self):
        self._run([_item(translations={'en': {'title': 'Saint Sophia Cathedral', 'description': 'Text.'}})])
        obj = CulturalObject.objects.get(title='Софійський собор')
        self.assertEqual(obj.status, 'approved')
        self.assertEqual(obj.original_language, 'uk')
        self.assertEqual(list(obj.tags.values_list('slug', flat=True)), ['sobor'])
        tr = CulturalObjectTranslation.objects.get(cultural_object=obj)
        self.assertEqual((tr.language, tr.title, tr.status, tr.submitted_by), ('en', 'Saint Sophia Cathedral', 'approved', self.author))

    def test_incomplete_translation_skipped_with_warning(self):
        output = self._run([_item(translations={'en': {'title': 'Only title', 'description': ''}})])
        self.assertTrue(CulturalObject.objects.filter(title='Софійський собор').exists())
        self.assertFalse(CulturalObjectTranslation.objects.exists())
        self.assertIn('неповний переклад [en]', output)

    def test_duplicates_skipped(self):
        self._run([_item()])
        output = self._run([_item()])
        self.assertEqual(CulturalObject.objects.count(), 1)
        self.assertIn('пропущено (дублікати): 1', output)

    def test_overlong_url_skipped_not_crashing(self):
        output = self._run([_item(wikipedia_url='https://uk.wikipedia.org/wiki/' + '%D0%90' * 40), _item(title='Інший')])
        self.assertFalse(CulturalObject.objects.filter(title='Софійський собор').exists())
        self.assertTrue(CulturalObject.objects.filter(title='Інший').exists())
        self.assertIn('задовгі посилання', output)

    def test_photos_ignored_without_flag(self):
        self._run([_item(photos=[{'source_url': 'https://example.com/a.jpg', 'caption': 'Фото'}])])
        self.assertFalse(ObjectPhoto.objects.exists())

    @patch('objects.management.commands.load_objects.cloudinary.config')
    def test_with_photos_requires_cloudinary_credentials(self, mock_config):
        mock_config.return_value = MagicMock(api_secret='')
        with self.assertRaises(CommandError):
            self._run([_item()], '--with-photos')

    @patch('objects.management.commands.load_objects.cloudinary.config')
    @patch('objects.management.commands.load_objects.cloudinary_service.upload_photo')
    @patch('objects.management.commands.load_objects.requests.Session.get')
    def test_with_photos_uploads_approved_photo(self, mock_get, mock_upload, mock_config):
        mock_config.return_value = MagicMock(api_secret='secret')
        mock_get.return_value = MagicMock(content=b'jpeg-bytes', raise_for_status=MagicMock())
        mock_upload.return_value = {
            'public_id': 'cultural-heritage/photos/abc', 'image_url': 'https://img', 'thumbnail_url': 'https://thumb',
        }
        self._run([_item(photos=[{'source_url': 'https://upload.wikimedia.org/a.jpg', 'caption': 'Фото: Автор, CC BY-SA 4.0'}])],
                  '--with-photos')

        photo = ObjectPhoto.objects.get()
        self.assertEqual(photo.status, 'approved')
        self.assertIsNotNone(photo.moderated_at)
        self.assertEqual(photo.caption, 'Фото: Автор, CC BY-SA 4.0')
        self.assertEqual(photo.uploaded_by, self.author)
        self.assertTrue(photo.is_author_photo)
        self.assertEqual(mock_upload.call_args[0][0].read(), b'jpeg-bytes')

    @patch('objects.management.commands.load_objects.cloudinary.config')
    @patch('objects.management.commands.load_objects.requests.Session.get')
    def test_photo_download_failure_keeps_object(self, mock_get, mock_config):
        import requests
        mock_config.return_value = MagicMock(api_secret='secret')
        mock_get.side_effect = requests.ConnectionError('offline')
        output = self._run([_item(photos=[{'source_url': 'https://x/a.jpg', 'caption': ''}])], '--with-photos')
        self.assertTrue(CulturalObject.objects.filter(title='Софійський собор').exists())
        self.assertFalse(ObjectPhoto.objects.exists())
        self.assertIn('фото не завантажено', output)


@patch('objects.management.commands.cloudinary_cleanup.cloudinary.config')
@patch('objects.management.commands.cloudinary_cleanup.cloudinary_api')
class CloudinaryCleanupTest(TestCase):
    def setUp(self):
        user = User.objects.create_user('u', password='pass')
        obj = CulturalObject.objects.create(title='O', author=user, status='approved', **KYIV)
        ObjectPhoto.objects.create(
            cultural_object=obj, uploaded_by=user, cloudinary_public_id='cultural-heritage/photos/keep',
            image_url='https://x', thumbnail_url='https://y',
        )

    def _resources(self, resource_type, **kwargs):
        if resource_type == 'image':
            return {'resources': [
                {'public_id': 'cultural-heritage/photos/keep', 'bytes': 100},
                {'public_id': 'cultural-heritage/photos/orphan', 'bytes': 200},
            ]}
        return {'resources': [{'public_id': 'cultural-heritage/audio/old', 'bytes': 300}]}

    def test_dry_run_deletes_nothing(self, mock_api, mock_config):
        mock_config.return_value = MagicMock(api_secret='secret')
        mock_api.resources.side_effect = lambda **kw: self._resources(**kw)
        out = StringIO()
        call_command('cloudinary_cleanup', stdout=out)
        mock_api.delete_resources.assert_not_called()
        self.assertIn('до видалення 1', out.getvalue())

    def test_deletes_only_unreferenced(self, mock_api, mock_config):
        mock_config.return_value = MagicMock(api_secret='secret')
        mock_api.resources.side_effect = lambda **kw: self._resources(**kw)
        call_command('cloudinary_cleanup', '--yes', stdout=StringIO())
        deleted = {(tuple(c.args[0]), c.kwargs['resource_type']) for c in mock_api.delete_resources.call_args_list}
        self.assertEqual(deleted, {
            (('cultural-heritage/photos/orphan',), 'image'),
            (('cultural-heritage/audio/old',), 'video'),
        })

    def test_requires_credentials(self, mock_api, mock_config):
        mock_config.return_value = MagicMock(api_secret='')
        with self.assertRaises(CommandError):
            call_command('cloudinary_cleanup', stdout=StringIO())


class FetchWikiHelpersTest(TestCase):
    def test_short_intro_extended_from_sections_skipping_references(self):
        text = ('Короткий вступ про замок, який має достатньо символів для абзацу.\n'
                '== Історія ==\n' + 'Історичний абзац із подробицями про будівництво замку. ' * 12 + '\n'
                '== Примітки ==\nПримітка, яку не треба включати до опису об\'єкта взагалі.')
        result = FetchCommand._clean_extract(text)
        self.assertTrue(result.startswith('Короткий вступ'))
        self.assertIn('Історичний абзац', result)
        self.assertNotIn('Примітка', result)
        self.assertNotIn('==', result)

    def test_long_text_truncated_and_stress_marks_removed(self):
        result = FetchCommand._clean_extract('Оле́ський за́мок. ' + 'Речення про замок. ' * 200)
        self.assertLessEqual(len(result), 1500)
        self.assertTrue(result.startswith('Олеський замок.'))
        self.assertNotIn('́', result)

    def test_tags(self):
        self.assertEqual(FetchCommand._tags('Олеський замок', '', []), ['zamok'])
        self.assertEqual(FetchCommand._tags('Софійський собор (Київ)', '', ['unesco']), ['sobor', 'unesco'])
        self.assertEqual(FetchCommand._tags('Антонієві печери', '', ['tserkva']), ['tserkva'])
        self.assertEqual(FetchCommand._tags('Щось', 'без ключових слів', []), ['pamyatnyk'])


class LoadRoutesTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user('importer', password='pass')
        Tag.objects.create(name='Замок', slug='zamok', icon='🏰')
        for title, lat in (('Олеський замок', 49.968), ('Підгорецький замок', 49.943)):
            CulturalObject.objects.create(title=title, author=self.author, status='approved',
                                          latitude=lat, longitude=24.9)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _route(self, **extra):
        return {
            'title': 'Золота підкова', 'description': 'Опис', 'tags': ['zamok'], 'is_featured': True,
            'estimated_duration_minutes': 480, 'profile': 'driving-car',
            'stops': [{'object_title': 'Олеський замок'}, {'object_title': 'Підгорецький замок'}],
            'translations': {'en': {'title': 'Golden Horseshoe', 'description': 'Description'}},
            **extra,
        }

    def _run(self, routes, *args):
        path = Path(self.tmp.name) / 'routes.json'
        path.write_text(json.dumps({'routes': routes}, ensure_ascii=False), encoding='utf-8')
        out = StringIO()
        call_command('load_routes', str(path), '--username', 'importer', *args, stdout=out)
        return out.getvalue()

    def test_creates_public_approved_route_with_stops_and_translation(self):
        from objects.models import Route, RouteTranslation
        self._run([self._route()])
        route = Route.objects.get()
        self.assertEqual((route.status, route.visibility, route.is_featured), ('approved', 'public', True))
        self.assertEqual([s.cultural_object.title for s in route.stops.order_by('order')],
                         ['Олеський замок', 'Підгорецький замок'])
        tr = RouteTranslation.objects.get(route=route)
        self.assertEqual((tr.language, tr.title, tr.status), ('en', 'Golden Horseshoe', 'approved'))
        self.assertIsNone(route.route_geometry)

    def test_too_few_resolved_stops_skipped(self):
        from objects.models import Route
        output = self._run([self._route(stops=[{'object_title': 'Олеський замок'}, {'object_title': 'Немає такого'}])])
        self.assertFalse(Route.objects.exists())
        self.assertIn('замало знайдених зупинок', output)

    @override_settings(ORS_API_KEY='')
    def test_with_geometry_requires_ors_key(self):
        with self.assertRaises(CommandError):
            self._run([self._route()], '--with-geometry')

    @override_settings(ORS_API_KEY='key')
    @patch('objects.management.commands.load_routes.get_directions')
    def test_with_geometry_uses_profile_and_stores_result(self, mock_directions):
        from objects.models import Route
        mock_directions.return_value = {'geometry': [[24.9, 49.968], [24.9, 49.943]], 'distance_m': 7000, 'duration_s': 600}
        self._run([self._route()], '--with-geometry')
        route = Route.objects.get()
        self.assertEqual(mock_directions.call_args.kwargs['profile'], 'driving-car')
        self.assertEqual((route.route_distance_m, route.route_duration_s), (7000, 600))
        self.assertIsNotNone(route.geometry_updated_at)

    @override_settings(ORS_API_KEY='key')
    @patch('objects.management.commands.load_routes.get_directions')
    def test_geometry_failure_keeps_route(self, mock_directions):
        from objects.models import Route
        from objects.services.ors import ORSError
        mock_directions.side_effect = ORSError('quota exceeded')
        output = self._run([self._route()], '--with-geometry')
        self.assertTrue(Route.objects.exists())
        self.assertIn('геометрію не розраховано', output)
