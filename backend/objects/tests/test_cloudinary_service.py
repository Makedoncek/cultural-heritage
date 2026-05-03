from unittest.mock import patch, MagicMock
from django.test import TestCase

from objects import cloudinary_service


class CloudinaryServiceTests(TestCase):
    @patch('objects.cloudinary_service.cloudinary.uploader.upload')
    def test_upload_photo_returns_public_id_and_urls(self, mock_upload):
        mock_upload.return_value = {
            'public_id': 'cultural-heritage/photos/abc123',
            'secure_url': 'https://res.cloudinary.com/demo/image/upload/v1/abc123.jpg',
            'format': 'jpg',
            'width': 1920,
            'height': 1080,
        }

        result = cloudinary_service.upload_photo(file=b'fake-bytes')

        self.assertEqual(result['public_id'], 'cultural-heritage/photos/abc123')
        self.assertIn('image_url', result)
        self.assertIn('thumbnail_url', result)
        self.assertIn('w_300,h_200,c_fill', result['thumbnail_url'])
        self.assertIn('f_auto,q_auto', result['image_url'])

    @patch('objects.cloudinary_service.cloudinary.uploader.upload')
    def test_upload_photo_uses_correct_folder(self, mock_upload):
        mock_upload.return_value = {
            'public_id': 'cultural-heritage/photos/xyz',
            'secure_url': 'https://res.cloudinary.com/x.jpg',
            'format': 'jpg',
        }
        cloudinary_service.upload_photo(file=b'data')

        kwargs = mock_upload.call_args.kwargs
        self.assertEqual(kwargs['folder'], 'cultural-heritage/photos')

    @patch('objects.cloudinary_service.cloudinary.uploader.destroy')
    def test_delete_photo_calls_destroy(self, mock_destroy):
        mock_destroy.return_value = {'result': 'ok'}

        cloudinary_service.delete_photo('cultural-heritage/photos/abc123')

        mock_destroy.assert_called_once_with('cultural-heritage/photos/abc123')
