"""Magic-bytes validation for audio uploads — the client Content-Type is not trusted."""
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from objects.models import CulturalObject, ObjectAudio
from objects.validators import validate_audio_format

# Minimal valid container headers (≥12 bytes each).
WAV = b'RIFF\x00\x00\x00\x00WAVE\x00\x00\x00\x00'
OGG = b'OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00'
MP3_ID3 = b'ID3\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00'
MP3_SYNC = b'\xff\xfb\x90\x64\x00\x00\x00\x00\x00\x00\x00\x00'
MP4 = b'\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00'
WEBM = b'\x1a\x45\xdf\xa3\x01\x00\x00\x00\x00\x00\x00\x00'
JUNK = b'this is plain text, definitely not audio'


class ValidateAudioFormatUnitTests(APITestCase):
    def test_accepts_known_containers(self):
        for name, data in [('wav', WAV), ('ogg', OGG), ('mp3-id3', MP3_ID3),
                           ('mp3-sync', MP3_SYNC), ('mp4', MP4), ('webm', WEBM)]:
            with self.subTest(fmt=name):
                validate_audio_format(BytesIO(data))  # must not raise

    def test_rejects_non_audio(self):
        with self.assertRaises(ValidationError):
            validate_audio_format(BytesIO(JUNK))

    def test_rejects_too_short(self):
        with self.assertRaises(ValidationError):
            validate_audio_format(BytesIO(b'ID'))


class AudioUploadFormatViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('u', 'u@t.com', 'p')
        cls.obj = CulturalObject.objects.create(
            title='Obj', latitude=50.0, longitude=30.0, author=cls.user, status='approved',
        )
        cls.url = f'/api/objects/{cls.obj.pk}/audios/'

    @patch('objects.views.audio.cloudinary_audio_service.upload_audio',
           return_value={'public_id': 'x/y', 'url': 'http://x/y.mp3', 'duration_seconds': 5})
    def test_lying_content_type_is_rejected(self, mock_upload):
        """Non-audio bytes with content_type='audio/mpeg' must be rejected by magic-bytes."""
        self.client.force_authenticate(self.user)
        bogus = SimpleUploadedFile('fake.mp3', JUNK, content_type='audio/mpeg')
        resp = self.client.post(self.url, {
            'audio': bogus, 'language': 'uk', 'title': 't', 'copyright_confirmed': 'true',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ObjectAudio.objects.count(), 0)
        mock_upload.assert_not_called()
