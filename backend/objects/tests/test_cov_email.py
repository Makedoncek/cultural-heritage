"""Coverage: email.py — language helpers + notification tasks (status, translation,
inaccuracy, follower). Django test runner uses the locmem backend, so sent mail
lands in mail.outbox."""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from objects import email as email_mod
from objects.models import (
    CulturalObject, CulturalObjectTranslation, FavoriteAuthor, InaccuracyReport,
    Route, RouteTranslation, UserPreference,
)


class EmailHelperTests(TestCase):
    def test_user_language_defaults_to_uk_without_preference(self):
        u = User.objects.create_user('np', 'np@t.com', 'p')
        UserPreference.objects.filter(user=u).delete()
        u.refresh_from_db()
        self.assertEqual(email_mod._user_language(u), 'uk')

    def test_template_for_language_variants(self):
        self.assertEqual(email_mod._template_for('verify_email', 'uk'), 'emails/verify_email.html')
        self.assertEqual(email_mod._template_for('verify_email', 'en'), 'emails/verify_email_en.html')

    def test_approved_subject_both_languages(self):
        self.assertIn('затверджено', email_mod._approved_subject('uk', 'Замок'))
        self.assertIn('approved', email_mod._approved_subject('en', 'Castle'))

    def test_follower_subject_and_labels_both_languages(self):
        subj_uk, label_uk, _ = email_mod._follower_subject_and_labels('uk', 'alice', 'Замок', False)
        self.assertIn('alice', subj_uk)
        self.assertIn('об', label_uk)
        subj_en, label_en, _ = email_mod._follower_subject_and_labels('en', 'alice', 'Castle', True)
        self.assertEqual(label_en, 'event')


class NotificationEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('author', 'author@t.com', 'p')
        cls.follower = User.objects.create_user('follower', 'follower@t.com', 'p')
        cls.submitter = User.objects.create_user('submitter', 'submitter@t.com', 'p')
        cls.reporter = User.objects.create_user('reporter', 'reporter@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Lviv Opera', latitude=49.84, longitude=24.03, author=cls.author, status='approved')
        cls.route = Route.objects.create(
            title='City Tour', description='x', author=cls.author, status='approved')
        cls.ct = ContentType.objects.get_for_model(CulturalObject)

    def setUp(self):
        mail.outbox = []

    def test_status_notification_sends_on_approved(self):
        email_mod.send_status_notification(self.obj.id, 'approved')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Lviv Opera', mail.outbox[0].subject)

    def test_status_notification_noop_for_non_approved(self):
        email_mod.send_status_notification(self.obj.id, 'archived')
        self.assertEqual(len(mail.outbox), 0)

    def test_status_notification_missing_object_is_safe(self):
        email_mod.send_status_notification(999999, 'approved')
        self.assertEqual(len(mail.outbox), 0)

    def test_object_translation_outcome_email(self):
        tr = CulturalObjectTranslation.objects.create(
            cultural_object=self.obj, language='en', title='Lviv Opera House',
            status='approved', submitted_by=self.submitter)
        email_mod.send_translation_outcome_email('object', tr.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.submitter.email, mail.outbox[0].to)

    def test_route_translation_outcome_email(self):
        tr = RouteTranslation.objects.create(
            route=self.route, language='en', title='City Tour EN',
            status='rejected', submitted_by=self.submitter)
        email_mod.send_translation_outcome_email('route', tr.id)
        self.assertEqual(len(mail.outbox), 1)

    def test_translation_outcome_noop_when_pending(self):
        tr = CulturalObjectTranslation.objects.create(
            cultural_object=self.obj, language='en', title='X',
            status='pending', submitted_by=self.submitter)
        email_mod.send_translation_outcome_email('object', tr.id)
        self.assertEqual(len(mail.outbox), 0)

    def test_inaccuracy_outcome_email(self):
        report = InaccuracyReport.objects.create(
            content_type=self.ct, object_id=self.obj.id, content_owner=self.author,
            reporter=self.reporter, reason_type='wrong_coords', status='resolved',
            resolved_at=timezone.now(), admin_response='Дякуємо за повідомлення')
        email_mod.send_inaccuracy_outcome_email(report.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.reporter.email, mail.outbox[0].to)

    def test_follower_notifications_to_subscribers(self):
        FavoriteAuthor.objects.create(user=self.follower, author=self.author)
        email_mod.send_follower_notifications(self.obj.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.follower.email, mail.outbox[0].to)
