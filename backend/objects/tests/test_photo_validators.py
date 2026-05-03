from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from objects.validators import validate_image_size, validate_image_format

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


class ImageSizeValidatorTests(TestCase):
    def test_valid_size_passes(self):
        path = FIXTURES / 'test_photo_valid.jpg'
        with open(path, 'rb') as f:
            file = SimpleUploadedFile('test.jpg', f.read(), content_type='image/jpeg')
        validate_image_size(file)

    def test_oversized_raises_validation_error(self):
        path = FIXTURES / 'test_photo_oversized.jpg'
        with open(path, 'rb') as f:
            file = SimpleUploadedFile('big.jpg', f.read(), content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            validate_image_size(file)


class ImageFormatValidatorTests(TestCase):
    def test_valid_jpeg_passes(self):
        path = FIXTURES / 'test_photo_valid.jpg'
        with open(path, 'rb') as f:
            file = SimpleUploadedFile('test.jpg', f.read(), content_type='image/jpeg')
        validate_image_format(file)

    def test_pdf_with_jpg_extension_raises(self):
        path = FIXTURES / 'test_photo_fake.jpg'
        with open(path, 'rb') as f:
            file = SimpleUploadedFile('fake.jpg', f.read(), content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            validate_image_format(file)
