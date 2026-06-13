"""Coverage: admin.py — changelist/change rendering (display methods), moderation
actions and save_model. Broker (.delay) and Cloudinary calls are mocked."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from objects.models import (
    CulturalObject, CulturalObjectTranslation, FavoriteAuthor, Favorite,
    InaccuracyReport, ObjectAudio, ObjectPhoto, PlannedVisit, Route, RouteStop,
    RouteTranslation, Tag, Visit,
)


class AdminTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('root', 'root@t.com', 'p')
        cls.author = User.objects.create_user('author', 'author@t.com', 'p')
        cls.reporter = User.objects.create_user('reporter', 'reporter@t.com', 'p')

        cls.tag = Tag.objects.create(name='Castle', slug='castle', icon='C')
        cls.pending = CulturalObject.objects.create(
            title='Pending Obj', latitude=50.0, longitude=30.0, author=cls.author, status='pending')
        cls.approved = CulturalObject.objects.create(
            title='Approved Obj', latitude=50.1, longitude=30.1, author=cls.author, status='approved')
        cls.archived = CulturalObject.objects.create(
            title='Archived Obj', latitude=50.2, longitude=30.2, author=cls.author, status='archived')

        cls.photo = ObjectPhoto.objects.create(
            cultural_object=cls.approved, uploaded_by=cls.author, cloudinary_public_id='ph1',
            image_url='http://x/i.jpg', thumbnail_url='http://x/t.jpg', status='pending')
        cls.audio = ObjectAudio.objects.create(
            cultural_object=cls.approved, uploaded_by=cls.author, cloudinary_public_id='au1',
            cloudinary_url='http://x/a.mp3', duration_seconds=30, title='Narrative', status='pending')

        cls.ct = ContentType.objects.get_for_model(CulturalObject)
        cls.report = InaccuracyReport.objects.create(
            content_type=cls.ct, object_id=cls.approved.id, content_owner=cls.author,
            reporter=cls.reporter, reason_type='wrong_coords', status='pending', note='wrong')

        cls.route = Route.objects.create(
            title='Tour', description='x', author=cls.author, visibility='public', status='pending')
        RouteStop.objects.create(route=cls.route, cultural_object=cls.approved, order=1)
        RouteStop.objects.create(route=cls.route, cultural_object=cls.pending, order=2)

        cls.obj_tr = CulturalObjectTranslation.objects.create(
            cultural_object=cls.approved, language='en', title='Approved Obj EN',
            status='pending', submitted_by=cls.author)
        cls.route_tr = RouteTranslation.objects.create(
            route=cls.route, language='en', title='Tour EN', status='pending', submitted_by=cls.author)

        Favorite.objects.create(user=cls.reporter, cultural_object=cls.approved)
        FavoriteAuthor.objects.create(user=cls.reporter, author=cls.author)
        Visit.objects.create(user=cls.reporter, cultural_object=cls.approved)
        PlannedVisit.objects.create(user=cls.reporter, cultural_object=cls.approved)

    def setUp(self):
        # Block all async/broker/cloudinary side effects triggered by admin actions.
        for target in (
            'objects.email.send_status_notification.delay',
            'objects.email.send_follower_notifications.delay',
            'objects.email.send_inaccuracy_outcome_email.delay',
            'objects.email.send_translation_outcome_email.delay',
            'objects.tasks.delete_cloudinary_file.delay',
            'objects.tasks.delete_cloudinary_audio.delay',
        ):
            p = patch(target)
            p.start()
            self.addCleanup(p.stop)
        self.client.force_login(self.admin)

    def _action(self, model, action, pks):
        url = reverse(f'admin:objects_{model}_changelist')
        return self.client.post(url, {'action': action, '_selected_action': pks, 'index': 0})


class AdminRenderingTests(AdminTestBase):
    CHANGELIST_MODELS = [
        'tag', 'culturalobject', 'favorite', 'favoriteauthor', 'visit', 'plannedvisit',
        'objectphoto', 'objectaudio', 'inaccuracyreport', 'route',
        'culturalobjecttranslation', 'routetranslation',
    ]

    def test_changelists_render(self):
        for model in self.CHANGELIST_MODELS:
            with self.subTest(model=model):
                resp = self.client.get(reverse(f'admin:objects_{model}_changelist'))
                self.assertEqual(resp.status_code, 200)

    def test_change_pages_render(self):
        pages = [
            ('culturalobject', self.approved.pk),
            ('objectphoto', self.photo.pk),
            ('objectaudio', self.audio.pk),
            ('inaccuracyreport', self.report.pk),
            ('route', self.route.pk),
            ('culturalobjecttranslation', self.obj_tr.pk),
            ('routetranslation', self.route_tr.pk),
        ]
        for model, pk in pages:
            with self.subTest(model=model):
                resp = self.client.get(reverse(f'admin:objects_{model}_change', args=[pk]))
                self.assertEqual(resp.status_code, 200)


class AdminActionTests(AdminTestBase):
    def test_object_moderation_actions(self):
        self._action('culturalobject', 'approve_objects', [self.pending.pk])
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, 'approved')

        self._action('culturalobject', 'archive_objects', [self.approved.pk])
        self.approved.refresh_from_db()
        self.assertEqual(self.approved.status, 'archived')

        self._action('culturalobject', 'restore_objects', [self.archived.pk])
        self.archived.refresh_from_db()
        self.assertEqual(self.archived.status, 'pending')

    def test_photo_actions(self):
        self._action('objectphoto', 'approve_photos', [self.photo.pk])
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.status, 'approved')
        self._action('objectphoto', 'reject_photos', [self.photo.pk])
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.status, 'rejected')
        self.assertIsNotNone(self.photo.rejected_cleanup_at)

    def test_audio_actions(self):
        self._action('objectaudio', 'approve_audios', [self.audio.pk])
        self.audio.refresh_from_db()
        self.assertEqual(self.audio.status, 'approved')
        self._action('objectaudio', 'reject_audios', [self.audio.pk])
        self.audio.refresh_from_db()
        self.assertEqual(self.audio.status, 'rejected')

    def test_route_actions(self):
        self._action('route', 'approve_routes', [self.route.pk])
        self.route.refresh_from_db()
        self.assertEqual(self.route.status, 'approved')
        self._action('route', 'archive_routes', [self.route.pk])
        self.route.refresh_from_db()
        self.assertEqual(self.route.status, 'archived')

    def test_report_actions(self):
        self._action('inaccuracyreport', 'resolve_reports', [self.report.pk])
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'resolved')
        self.assertEqual(self.report.resolved_by, self.admin)

    def test_report_dismiss_action(self):
        self._action('inaccuracyreport', 'dismiss_reports', [self.report.pk])
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'dismissed')

    def test_translation_actions_object(self):
        self._action('culturalobjecttranslation', 'approve_translations', [self.obj_tr.pk])
        self.obj_tr.refresh_from_db()
        self.assertEqual(self.obj_tr.status, 'approved')
        # original language (en != uk) is not original here, so parent text unchanged
        self.approved.refresh_from_db()

    def test_translation_reject_object(self):
        self._action('culturalobjecttranslation', 'reject_translations', [self.obj_tr.pk])
        self.obj_tr.refresh_from_db()
        self.assertEqual(self.obj_tr.status, 'rejected')

    def test_route_translation_actions(self):
        self._action('routetranslation', 'approve_translations', [self.route_tr.pk])
        self.route_tr.refresh_from_db()
        self.assertEqual(self.route_tr.status, 'approved')


class AdminSaveModelTests(AdminTestBase):
    def test_report_change_save_resolves(self):
        url = reverse('admin:objects_inaccuracyreport_change', args=[self.report.pk])
        self.client.post(url, {'status': 'resolved', 'admin_response': 'Підтверджено'})
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'resolved')
        self.assertEqual(self.report.resolved_by, self.admin)

    def test_translation_change_save_approves(self):
        url = reverse('admin:objects_culturalobjecttranslation_change', args=[self.obj_tr.pk])
        self.client.post(url, {
            'cultural_object': self.approved.pk,
            'language': 'en',
            'title': 'Approved Obj EN v2',
            'description': 'desc',
            'status': 'approved',
            'reviewer_note': '',
        })
        self.obj_tr.refresh_from_db()
        self.assertEqual(self.obj_tr.status, 'approved')


class AdminTagFilteringTests(AdminTestBase):
    """Change-форма обʼєкта показує лише теги відповідного tag_type."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from django.utils import timezone
        from datetime import timedelta
        cls.obj_tag = Tag.objects.create(name='ObjOnlyTag', slug='obj-only', icon='O', tag_type='object')
        cls.evt_tag = Tag.objects.create(name='EvtOnlyTag', slug='evt-only', icon='E', tag_type='event')
        cls.event_obj = CulturalObject.objects.create(
            title='Evt Obj', latitude=50.3, longitude=30.3, author=cls.author,
            status='approved', object_type='event',
            event_start_date=timezone.now(),
            event_end_date=timezone.now() + timedelta(days=1),
        )

    def test_permanent_change_view_shows_only_object_tags(self):
        url = reverse('admin:objects_culturalobject_change', args=[self.approved.pk])
        html = self.client.get(url).content.decode()
        self.assertIn('ObjOnlyTag', html)
        self.assertNotIn('EvtOnlyTag', html)

    def test_event_change_view_shows_only_event_tags(self):
        url = reverse('admin:objects_culturalobject_change', args=[self.event_obj.pk])
        html = self.client.get(url).content.decode()
        self.assertIn('EvtOnlyTag', html)
        self.assertNotIn('ObjOnlyTag', html)

    def test_add_view_shows_all_tags(self):
        url = reverse('admin:objects_culturalobject_add')
        html = self.client.get(url).content.decode()
        self.assertIn('ObjOnlyTag', html)
        self.assertIn('EvtOnlyTag', html)

    def test_change_form_includes_tag_filter_script(self):
        url = reverse('admin:objects_culturalobject_change', args=[self.approved.pk])
        html = self.client.get(url).content.decode()
        self.assertIn('admin/js/tag_type_filter.js', html)
