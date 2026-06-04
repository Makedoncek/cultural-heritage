"""Coverage: views.py — ObjectAudioViewSet (visibility matrix, upload with limit,
metadata editing with re-moderation, archive/restore, play counter)."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject, ObjectAudio

CLOUDINARY_AUDIO_OK = {
    'public_id': 'cultural-heritage/audio/cov1',
    'url': 'https://res.cloudinary.com/cov1.mp3',
    'duration_seconds': 42,
}


def _audio_file():
    return SimpleUploadedFile('narrative.mp3', b'ID3fakecontent', content_type='audio/mpeg')


class AudioTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uploader = User.objects.create_user('uploader', 'u@t.com', 'p')
        cls.other = User.objects.create_user('other', 'o@t.com', 'p')
        cls.admin = User.objects.create_user('admin', 'ad@t.com', 'p', is_staff=True)
        cls.obj = CulturalObject.objects.create(
            title='Obj', latitude=50.0, longitude=30.0,
            author=cls.uploader, status='approved',
        )
        cls.base_url = f'/api/objects/{cls.obj.pk}/audios/'

    @classmethod
    def _audio(cls, public_id, **kwargs):
        defaults = dict(
            cultural_object=cls.obj, uploaded_by=cls.uploader,
            cloudinary_public_id=public_id, cloudinary_url='http://x/a.mp3',
            duration_seconds=10, title='Audio', language='uk',
            status='approved', copyright_confirmed=True,
        )
        defaults.update(kwargs)
        return ObjectAudio.objects.create(**defaults)


class AudioVisibilityTests(AudioTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.approved = cls._audio('vis-appr', status='approved', language='en')
        cls.pending = cls._audio('vis-pend', status='pending')
        cls.archived = cls._audio('vis-arch', status='archived')
        cls.foreign_pending = cls._audio('vis-forp', status='pending', uploaded_by=cls.other)

    def _ids(self, resp):
        return {a['id'] for a in resp.data}

    def test_list_visibility_matrix(self):
        # Guest: approved only
        self.assertEqual(self._ids(self.client.get(self.base_url)), {self.approved.pk})
        # Uploader: approved + own pending (not archived)
        self.client.force_authenticate(self.uploader)
        self.assertEqual(
            self._ids(self.client.get(self.base_url)),
            {self.approved.pk, self.pending.pk},
        )
        # Staff: everything except archived
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self._ids(self.client.get(self.base_url)),
            {self.approved.pk, self.pending.pk, self.foreign_pending.pk},
        )

    def test_list_language_filter(self):
        resp = self.client.get(self.base_url, {'language': 'uk'})
        self.assertEqual(self._ids(resp), set())
        resp = self.client.get(self.base_url, {'language': 'en'})
        self.assertEqual(self._ids(resp), {self.approved.pk})

    def test_retrieve_visibility(self):
        approved_url = f'{self.base_url}{self.approved.pk}/'
        pending_url = f'{self.base_url}{self.pending.pk}/'
        # Guest: approved OK, pending hidden
        self.assertEqual(self.client.get(approved_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(pending_url).status_code, status.HTTP_404_NOT_FOUND)
        # Foreign user: pending hidden
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(pending_url).status_code, status.HTTP_404_NOT_FOUND)
        # Owner and staff see pending
        self.client.force_authenticate(self.uploader)
        self.assertEqual(self.client.get(pending_url).status_code, status.HTTP_200_OK)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(pending_url).status_code, status.HTTP_200_OK)


class AudioUploadTests(AudioTestBase):
    @patch('objects.views.cloudinary_audio_service.upload_audio',
           return_value=CLOUDINARY_AUDIO_OK)
    def test_upload_success(self, mock_upload):
        self.client.force_authenticate(self.uploader)
        resp = self.client.post(self.base_url, {
            'audio': _audio_file(), 'language': 'uk', 'title': 'Розповідь',
            'narrator_name': 'Гід', 'copyright_confirmed': 'true',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        audio = ObjectAudio.objects.get()
        self.assertEqual(audio.status, 'pending')
        self.assertEqual(audio.duration_seconds, 42)
        self.assertTrue(audio.copyright_confirmed)
        mock_upload.assert_called_once()

    @patch('objects.views.cloudinary_audio_service.upload_audio',
           return_value=CLOUDINARY_AUDIO_OK)
    def test_upload_limit_10_active(self, _mock):
        for i in range(10):
            self._audio(f'lim{i}', status='pending')
        self.client.force_authenticate(self.uploader)
        resp = self.client.post(self.base_url, {
            'audio': _audio_file(), 'language': 'uk', 'title': 'Over limit',
            'copyright_confirmed': 'true',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('objects.views.cloudinary_audio_service.upload_audio',
           return_value=CLOUDINARY_AUDIO_OK)
    def test_rejected_and_archived_free_the_slot(self, _mock):
        for i in range(5):
            self._audio(f'rej{i}', status='rejected')
        for i in range(5):
            self._audio(f'arc{i}', status='archived')
        self.client.force_authenticate(self.uploader)
        resp = self.client.post(self.base_url, {
            'audio': _audio_file(), 'language': 'uk', 'title': 'Re-submission',
            'copyright_confirmed': 'true',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class AudioEditDeleteTests(AudioTestBase):
    def test_partial_update_branches(self):
        audio = self._audio('edit1', status='approved')
        url = f'{self.base_url}{audio.pk}/'
        # Foreign user → 403
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.patch(url, {'title': 'X'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        # No editable fields → returns current data, status untouched
        self.client.force_authenticate(self.uploader)
        resp = self.client.patch(url, {'status': 'approved'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        audio.refresh_from_db()
        self.assertEqual(audio.status, 'approved')
        # Owner edit of approved → back to pending
        resp = self.client.patch(url, {'title': 'Нова назва'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        audio.refresh_from_db()
        self.assertEqual(audio.status, 'pending')
        self.assertEqual(audio.title, 'Нова назва')

    def test_admin_edit_keeps_status(self):
        audio = self._audio('edit2', status='approved')
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            f'{self.base_url}{audio.pk}/', {'narrator_name': 'Narrator'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        audio.refresh_from_db()
        self.assertEqual(audio.status, 'approved')

    @patch('objects.signals.cloudinary_audio_service', create=True)
    def test_destroy_branches(self, _mock_signal):
        audio = self._audio('del1')
        url = f'{self.base_url}{audio.pk}/'
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.uploader)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ObjectAudio.objects.filter(pk=audio.pk).exists())


class AudioArchiveRestorePlayTests(AudioTestBase):
    def test_archive_restore_flow(self):
        audio = self._audio('arc-flow')
        archive_url = f'{self.base_url}{audio.pk}/archive/'
        restore_url = f'{self.base_url}{audio.pk}/restore/'
        # Foreign user → 403
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(archive_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(restore_url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.uploader)
        # Restore of non-archived → 400
        self.assertEqual(self.client.post(restore_url).status_code, status.HTTP_400_BAD_REQUEST)
        # Archive → archived; restore → pending
        self.assertEqual(self.client.post(archive_url).status_code, status.HTTP_200_OK)
        audio.refresh_from_db()
        self.assertEqual(audio.status, 'archived')
        self.assertEqual(self.client.post(restore_url).status_code, status.HTTP_200_OK)
        audio.refresh_from_db()
        self.assertEqual(audio.status, 'pending')

    def test_play_branches(self):
        pending = self._audio('play-pend', status='pending')
        resp = self.client.post(f'{self.base_url}{pending.pk}/play/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        approved = self._audio('play-appr', status='approved')
        play_url = f'{self.base_url}{approved.pk}/play/'
        # Self-play not counted
        self.client.force_authenticate(self.uploader)
        self.assertEqual(self.client.post(play_url).status_code, status.HTTP_200_OK)
        approved.refresh_from_db()
        self.assertEqual(approved.plays_count, 0)
        # Guest play counted
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(play_url).status_code, status.HTTP_200_OK)
        approved.refresh_from_db()
        self.assertEqual(approved.plays_count, 1)
